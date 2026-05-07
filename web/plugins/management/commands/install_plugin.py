from django.core.management.base import BaseCommand
from plugins.utils import AtomicInstaller
import os

class Command(BaseCommand):
    help = 'Installs a plugin from a zip file'

    def add_arguments(self, parser):
        parser.add_argument('zip_path', type=str, help='Path to the plugin zip file')

    def handle(self, *args, **options):
        zip_path = options['zip_path']
        if not os.path.exists(zip_path):
            self.stderr.write(self.style.ERROR(f"File not found: {zip_path}"))
            return

        try:
            self.stdout.write(f"Installing plugin from {zip_path}...")
            plugin = AtomicInstaller.install(zip_path)
            self.stdout.write(self.style.SUCCESS(f"Successfully installed plugin: {plugin.name} ({plugin.version})"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Installation failed: {str(e)}"))
            import traceback
            self.stderr.write(traceback.format_exc())
