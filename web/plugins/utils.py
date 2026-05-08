import os
import shutil
import zipfile
import yaml
import json
import subprocess
from datetime import datetime
from django.conf import settings
from django.utils.text import slugify
from django.db import transaction
import logging
from .models import Plugin

logger = logging.getLogger(__name__)

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
        """Extracts a plugin zip and returns the path to the extracted content."""
        temp_dir = os.path.join(cls.BASE_PLUGINS_DIR, 'temp_' + datetime.now().strftime('%Y%m%d%H%M%S'))
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
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
                
        # Validate runtime keys
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
    def install(cls, zip_path):
        """Performs the full atomic installation."""
        PluginManager.ensure_dirs()
        temp_dir = None
        backup_file = None
        plugin_slug = None
        
        try:
            temp_dir = PluginManager.extract_plugin(zip_path)
            # If the zip had a subfolder, we should adjust temp_dir
            # For simplicity, we assume files are at the root or we find the manifest
            manifest = PluginManager.validate_manifest(temp_dir)
            plugin_name = manifest['name']
            plugin_slug = slugify(plugin_name)
            
            # 1. Backup DB
            backup_file = cls.backup_db(plugin_slug)
            
            with transaction.atomic():
                # 2. Register in DB
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
                
                # 3. Handle migrations if custom_models.py exists
                # This part is complex because we need to dynamically load models
                # For v1, we might skip full dynamic model registration or use a hook
                
                # 4. Finalize file placement
                final_dir = os.path.join(PluginManager.BASE_PLUGINS_DIR, plugin_slug)
                if os.path.exists(final_dir):
                    shutil.rmtree(final_dir)
                shutil.move(temp_dir, final_dir)
                
                # 5. Copy UI assets to MEDIA_ROOT for frontend access
                media_plugin_dir = os.path.join(settings.MEDIA_ROOT, 'plugins', plugin_slug)
                if os.path.exists(media_plugin_dir):
                    shutil.rmtree(media_plugin_dir)
                
                ui_src = os.path.join(final_dir, 'ui')
                if os.path.exists(ui_src):
                    os.makedirs(media_plugin_dir, exist_ok=True)
                    # We copy the 'ui' directory into the plugin's media folder
                    shutil.copytree(ui_src, os.path.join(media_plugin_dir, 'ui'))
                
            return plugin
            
        except Exception as e:
            if backup_file:
                cls.rollback_db(backup_file)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise e
