from django.core.management.base import BaseCommand
import os
import shutil
from django.conf import settings
from plugins.models import Plugin
from plugins.utils import PluginManager

class Command(BaseCommand):
    help = 'Synchronizes plugin UI assets from plugins_data to MEDIA_ROOT for frontend access'

    def handle(self, *args, **options):
        active_plugins = Plugin.objects.all()
        synced_count = 0
        
        for plugin in active_plugins:
            self.stdout.write(f"Syncing UI assets for: {plugin.name}...")
            
            # Source directory in plugins_data
            plugin_data_dir = os.path.join(PluginManager.BASE_PLUGINS_DIR, plugin.slug)
            ui_src = os.path.join(plugin_data_dir, 'ui')
            
            if not os.path.exists(ui_src):
                self.stdout.write(self.style.WARNING(f"  No 'ui' directory found for {plugin.name} in plugins_data."))
                continue
                
            # Target directory in MEDIA_ROOT
            media_plugin_dir = os.path.join(settings.MEDIA_ROOT, 'plugins', plugin.slug)
            media_ui_target = os.path.join(media_plugin_dir, 'ui')
            
            try:
                # Ensure target parent exists
                os.makedirs(media_plugin_dir, exist_ok=True)
                
                # Remove existing target if it exists to ensure clean sync
                if os.path.exists(media_ui_target):
                    if os.path.islink(media_ui_target):
                        os.unlink(media_ui_target)
                    else:
                        shutil.rmtree(media_ui_target)
                
                # Copy assets
                shutil.copytree(ui_src, media_ui_target)
                self.stdout.write(self.style.SUCCESS(f"  Successfully synced UI assets for {plugin.name}"))
                synced_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed to sync assets for {plugin.name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Total plugins synced: {synced_count}"))
