import os
import shutil
import threading
import time
import zipfile
import yaml
import json
import subprocess
from datetime import datetime
from django.conf import settings
from django.utils.text import slugify
from django.db import transaction
from django.core.management import call_command
import requests
from django.core.cache import cache
import logging
from .models import Plugin

logger = logging.getLogger(__name__)

class MarketplaceManager:
    MARKETPLACE_YAML_URL = "https://raw.githubusercontent.com/whiterabb17/r3ngine-plugins/main/plugins.yaml"
    CACHE_KEY = "marketplace_plugins"
    CACHE_TIMEOUT = 3600  # 1 hour

    @classmethod
    def get_available_plugins(cls, force_refresh=False):
        if not force_refresh:
            cached_data = cache.get(cls.CACHE_KEY)
            if cached_data:
                return cached_data

        try:
            response = requests.get(cls.MARKETPLACE_YAML_URL, timeout=10)
            if response.status_code == 200:
                data = yaml.safe_load(response.text)
                plugins = data.get('marketplace', [])
                # Add installation status
                installed_slugs = list(Plugin.objects.values_list('slug', flat=True))
                for plugin in plugins:
                    plugin['is_installed'] = plugin['slug'] in installed_slugs
                
                cache.set(cls.CACHE_KEY, plugins, cls.CACHE_TIMEOUT)
                return plugins
            else:
                raise Exception(f"Marketplace unreachable: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch marketplace: {str(e)}")
            return []

    @classmethod
    def download_plugin(cls, slug):
        download_url = f"https://raw.githubusercontent.com/whiterabb17/r3ngine-plugins/main/{slug}/{slug}.zip"
        temp_zip_path = os.path.join(PluginManager.BASE_PLUGINS_DIR, f"download_{slug}.zip")
        PluginManager.ensure_dirs()
        
        response = requests.get(download_url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(temp_zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return temp_zip_path
        else:
            raise Exception(f"Failed to download plugin {slug}: {response.status_code}")

class PluginManager:
    """Handles file operations for plugins: extraction, validation, and deletion."""
    
    BASE_PLUGINS_DIR = os.path.join(settings.BASE_DIR, 'plugins_data')
    BACKUPS_DIR = os.path.join(BASE_PLUGINS_DIR, 'backups')
    
    @classmethod
    def ensure_dirs(cls):
        os.makedirs(cls.BASE_PLUGINS_DIR, exist_ok=True)
        os.makedirs(cls.BACKUPS_DIR, exist_ok=True)
        
    @classmethod
    def extract_plugin(cls, zip_path):
        """Extracts a plugin zip and returns the path to the actual plugin content (flattening root dir if needed)."""
        temp_dir = os.path.join(cls.BASE_PLUGINS_DIR, 'temp_' + datetime.now().strftime('%Y%m%d%H%M%S'))
        os.makedirs(temp_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # If there's only one directory and no files in the root, move everything up
        items = os.listdir(temp_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(temp_dir, items[0])):
            root_item = os.path.join(temp_dir, items[0])
            # Move all contents of the root_item to temp_dir
            for sub_item in os.listdir(root_item):
                shutil.move(os.path.join(root_item, sub_item), temp_dir)
            # Remove the now-empty root_item
            os.rmdir(root_item)
            
        return temp_dir

    @classmethod
    def validate_manifest(cls, plugin_dir):
        """Validates the manifest.yaml file."""
        manifest_path = os.path.join(plugin_dir, 'manifest.yaml')
        if not os.path.exists(manifest_path):
            raise Exception("Manifest.yaml not found in plugin archive.")
            
        with open(manifest_path, 'r') as f:
            manifest = yaml.safe_load(f)
            
        required_fields = ['name', 'version', 'runtime']
        for field in required_fields:
            if field not in manifest:
                raise Exception(f"Missing required field '{field}' in manifest.yaml")
                
        # Validate runtime keys.
        # Valid anchor values: any real scan task name (e.g. "subdomain_discovery")
        # or "standalone" for plugins that operate independently of the main scan pipeline.
        runtime = manifest.get('runtime', {})
        if not any(k in runtime for k in ['run after', 'run before']):
            raise Exception("Manifest must specify 'run after' or 'run before' in runtime section.")
            
        return manifest

    @classmethod
    def delete_plugin_files(cls, plugin_slug):
        """Deletes all files associated with a plugin."""
        # 1. Delete from plugins_data
        final_dir = os.path.join(cls.BASE_PLUGINS_DIR, plugin_slug)
        if os.path.exists(final_dir):
            shutil.rmtree(final_dir)
            
        # 2. Delete from media root
        media_plugin_dir = os.path.join(settings.MEDIA_ROOT, 'plugins', plugin_slug)
        if os.path.exists(media_plugin_dir):
            shutil.rmtree(media_plugin_dir)

class AtomicInstaller:
    """Handles the safe installation of plugins with backup and rollback."""
    
    @classmethod
    def backup_db(cls, plugin_slug):
        """Creates a database backup before installation."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        backup_file = os.path.join(PluginManager.BACKUPS_DIR, f"pre_{plugin_slug}_{timestamp}.sql")
        
        db_config = settings.DATABASES['default']
        cmd = [
            'pg_dump',
            '-h', str(db_config.get('HOST', 'db')),
            '-p', str(db_config.get('PORT', '5432')),
            '-U', str(db_config.get('USER')),
            '-d', str(db_config.get('NAME')),
            '-f', str(backup_file)
        ]
        
        try:
            env = os.environ.copy()
            if db_config.get('PASSWORD'):
                env['PGPASSWORD'] = str(db_config.get('PASSWORD'))
            
            logger.info(f"Creating database backup: {backup_file}")
            subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
            return backup_file
        except subprocess.CalledProcessError as e:
            logger.error(f"Database backup failed: {e.stderr}")
            raise Exception(f"Database backup failed: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error during backup: {str(e)}")
            raise e

    @classmethod
    def rollback_db(cls, backup_file):
        """Restores the database from a backup."""
        if not os.path.exists(backup_file):
            return
            
        db_config = settings.DATABASES['default']
        cmd = [
            'psql',
            '-h', str(db_config.get('HOST', 'db')),
            '-p', str(db_config.get('PORT', '5432')),
            '-U', str(db_config.get('USER')),
            '-d', str(db_config.get('NAME')),
            '-f', str(backup_file)
        ]
        
        try:
            env = os.environ.copy()
            if db_config.get('PASSWORD'):
                env['PGPASSWORD'] = str(db_config.get('PASSWORD'))
            
            logger.info(f"Rolling back database from: {backup_file}")
            subprocess.run(cmd, check=True, env=env, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"CRITICAL: Rollback failed! {e.stderr}")
        except Exception as e:
            logger.error(f"CRITICAL: Rollback failed! {str(e)}")

    @classmethod
    def install(cls, zip_path: str):
        """Performs the full atomic installation."""
        PluginManager.ensure_dirs()
        temp_dir = None
        backup_db_file = None
        backup_fs_dir = None
        backup_media_dir = None
        plugin_slug = None
        
        try:
            temp_dir = PluginManager.extract_plugin(zip_path)
            manifest = PluginManager.validate_manifest(temp_dir)
            plugin_name = manifest['name']
            plugin_slug = slugify(plugin_name).replace('-', '_')
            
            # 1. Backup DB
            backup_db_file = cls.backup_db(plugin_slug)
            
            # 2. Prepare FS Backups
            final_dir = os.path.join(PluginManager.BASE_PLUGINS_DIR, plugin_slug)
            media_plugin_dir = os.path.join(settings.MEDIA_ROOT, 'plugins', plugin_slug)
            
            if os.path.exists(final_dir):
                backup_fs_dir = f"{final_dir}_bak_{int(time.time())}"
                shutil.copytree(final_dir, backup_fs_dir)
                
            if os.path.exists(media_plugin_dir):
                backup_media_dir = f"{media_plugin_dir}_bak_{int(time.time())}"
                shutil.copytree(media_plugin_dir, backup_media_dir)

            with transaction.atomic():
                # 3. Register in DB
                runtime = manifest.get('runtime', {})
                anchor = runtime.get('run after') or runtime.get('run before')
                position = 'AFTER' if 'run after' in runtime else 'BEFORE'
                
                plugin, created = Plugin.objects.update_or_create(
                    slug=plugin_slug,
                    defaults={
                        'name': plugin_name,
                        'version': manifest['version'],
                        'description': manifest.get('description', ''),
                        'manifest': manifest,
                        'anchor_step': anchor,
                        'runtime_position': position,
                    }
                )
                
                # 4. Finalize file placement
                if os.path.exists(final_dir):
                    shutil.rmtree(final_dir)
                shutil.move(temp_dir, final_dir)
                
                # 5. Ingest Engine Fixtures and Run Migrations
                # Run dynamic migrations if the plugin has models
                backend_dir = os.path.join(final_dir, 'backend')
                if os.path.exists(os.path.join(backend_dir, 'models.py')):
                    # Ensure package directories have __init__.py files present
                    for d in [final_dir, backend_dir]:
                        init_f = os.path.join(d, '__init__.py')
                        if not os.path.exists(init_f):
                            try:
                                with open(init_f, 'w') as f:
                                    pass
                            except Exception:
                                pass

                    app_label = f"{plugin_slug}_backend"
                    logger.info(f"Running migrations for plugin app: {app_label}")
                    try:
                        import sys
                        # Run makemigrations in a clean subprocess to auto-load the new app config
                        makemigrate_res = subprocess.run(
                            [sys.executable, "manage.py", "makemigrations", app_label],
                            cwd=settings.BASE_DIR,
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        logger.info(f"Subprocess makemigrations stdout: {makemigrate_res.stdout}")
                        
                        # Run migrate in a clean subprocess
                        migrate_res = subprocess.run(
                            [sys.executable, "manage.py", "migrate", app_label],
                            cwd=settings.BASE_DIR,
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        logger.info(f"Subprocess migrate stdout: {migrate_res.stdout}")
                        logger.info(f"Successfully migrated plugin: {plugin_slug}")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to run migrations for {plugin_slug} (exit {e.returncode}):\nStdout: {e.stdout}\nStderr: {e.stderr}")
                        raise Exception(f"Migration subprocess failed for {app_label}: {e.stderr or e.stdout}")
                    except Exception as e:
                        logger.error(f"Unexpected error running migrations for {plugin_slug}: {str(e)}")
                        raise e

                from scanEngine.models import EngineType
                for file in os.listdir(final_dir):
                    if file.endswith('_engine.yaml'):
                        fixture_path = os.path.join(final_dir, file)
                        logger.info(f"Ingesting engine fixture: {fixture_path}")
                        try:
                            with open(fixture_path, 'r') as f:
                                fixture_data = yaml.safe_load(f)
                                if isinstance(fixture_data, list):
                                    for item in fixture_data:
                                        if item.get('model') == 'scanEngine.enginetype':
                                            fields = item.get('fields', {})
                                            name = fields.get('engine_name')
                                            if name:
                                                obj, created = EngineType.objects.update_or_create(
                                                    engine_name=name,
                                                    defaults=fields
                                                )
                                                logger.info(f"{'Created' if created else 'Updated'} engine: {name}")
                                            else:
                                                logger.warning(f"Engine fixture item missing engine_name: {item}")
                                        else:
                                            # Fallback for other models (e.g. Wordlist, etc.)
                                            call_command('loaddata', fixture_path, format='yaml')
                                            logger.info(f"Fallback loaddata used for: {file}")
                                else:
                                    logger.error(f"Invalid fixture format in {file}")
                        except Exception as e:
                            logger.error(f"CRITICAL: Failed to ingest engine fixture {file}: {str(e)}")

                # 6. Parse tools.yaml
                tools_path = os.path.join(final_dir, 'tools.yaml')
                if os.path.exists(tools_path):
                    try:
                        with open(tools_path, 'r') as f:
                            tools_config = yaml.safe_load(f)
                            plugin.tools_config = tools_config
                            plugin.save()
                        
                        # Trigger background installation
                        from .tasks import install_plugin_tools
                        transaction.on_commit(
                            lambda: threading.Thread(
                                target=install_plugin_tools,
                                args=(plugin_slug,),
                                daemon=True
                            ).start()
                        )
                    except Exception as e:
                        logger.error(f"Failed to parse tools.yaml for {plugin_slug}: {str(e)}")

                # Set needs_restart to True in cache
                from django.core.cache import cache
                cache.set(f"plugin_{plugin_slug}_needs_restart", True, timeout=None)

                # 7. Copy built UI assets (ui/dist/ or ui/ directly) to MEDIA_ROOT
                if os.path.exists(media_plugin_dir):
                    shutil.rmtree(media_plugin_dir)

                ui_dist_src = os.path.join(final_dir, 'ui', 'dist')
                ui_src = os.path.join(final_dir, 'ui')
                media_ui_target = os.path.join(media_plugin_dir, 'ui')

                if os.path.exists(ui_dist_src):
                    shutil.copytree(ui_dist_src, media_ui_target)
                elif os.path.exists(ui_src):
                    shutil.copytree(ui_src, media_ui_target)
                else:
                    logger.warning(
                        f"No ui/ or ui/dist/ found for {plugin_slug}. "
                        "UI unavailable until plugin is built and re-installed."
                    )
                
                # 8. Cleanup backups on success
                if backup_fs_dir and os.path.exists(backup_fs_dir):
                    shutil.rmtree(backup_fs_dir)
                if backup_media_dir and os.path.exists(backup_media_dir):
                    shutil.rmtree(backup_media_dir)
                if backup_db_file and os.path.exists(backup_db_file):
                    os.remove(backup_db_file)
                
                return plugin
                
        except Exception as e:
            logger.error(f"Installation failed for {plugin_slug}: {str(e)}")
            # Rollback DB
            if backup_db_file:
                cls.rollback_db(backup_db_file)
            
            # Rollback FS
            if backup_fs_dir and os.path.exists(backup_fs_dir):
                if os.path.exists(final_dir):
                    shutil.rmtree(final_dir)
                shutil.move(backup_fs_dir, final_dir)
            else:
                if final_dir and os.path.exists(final_dir):
                    shutil.rmtree(final_dir)
            
            # Rollback Media
            if backup_media_dir and os.path.exists(backup_media_dir):
                if os.path.exists(media_plugin_dir):
                    shutil.rmtree(media_plugin_dir)
                shutil.move(backup_media_dir, media_plugin_dir)
            else:
                if media_plugin_dir and os.path.exists(media_plugin_dir):
                    shutil.rmtree(media_plugin_dir)
                
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e
