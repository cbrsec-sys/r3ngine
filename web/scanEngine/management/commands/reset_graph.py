from django.core.management.base import BaseCommand
from reNgine.utils.graph import Neo4jManager

class Command(BaseCommand):
    help = 'Resets the Neo4j graph and re-syncs all scan data from the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Do not prompt for confirmation.',
        )

    def handle(self, *args, **options):
        if not options['no_input']:
            confirm = input("This will DELETE ALL data in Neo4j and re-sync from scratch. Are you sure? (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        manager = Neo4jManager()
        if not manager.driver:
            self.stdout.write(self.style.ERROR('Neo4j connection failed. Please check your credentials.'))
            return

        self.stdout.write(self.style.MIGRATE_LABEL('Resetting Neo4j database...'))
        manager.reset_database()

        self.stdout.write(self.style.MIGRATE_LABEL('Re-syncing all scans...'))
        manager.sync_all_scans()

        self.stdout.write(self.style.SUCCESS('Neo4j graph reset and re-sync completed successfully.'))
