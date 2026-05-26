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
            
            # Source: only the built files (from dist or root ui folder)
            plugin_data_dir = os.path.join(PluginManager.BASE_PLUGINS_DIR, plugin.slug)
            ui_dist_src = os.path.join(plugin_data_dir, 'ui', 'dist')
            ui_src = os.path.join(plugin_data_dir, 'ui')

            src_to_copy = None
            if os.path.exists(ui_dist_src):
                src_to_copy = ui_dist_src
            elif os.path.exists(ui_src):
                src_to_copy = ui_src

            if not src_to_copy:
                self.stdout.write(self.style.WARNING(
                    f"  No 'ui' or 'ui/dist' directory found for {plugin.name}. "
                    "Build the plugin UI first: npm run build"
                ))
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

                # Copy only the built files
                shutil.copytree(src_to_copy, media_ui_target)
                self.stdout.write(self.style.SUCCESS(f"  Successfully synced UI assets for {plugin.name}"))
                synced_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed to sync assets for {plugin.name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(f"Total plugins synced: {synced_count}"))
