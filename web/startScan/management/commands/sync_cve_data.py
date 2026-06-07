"""
Django management command for CVE data synchronization.

Usage:
    python manage.py sync_cve_data              # Enrich unenriched CVEs
    python manage.py sync_cve_data --kev        # Sync CISA KEV catalog
    python manage.py sync_cve_data --refresh 30 # Refresh CVEs from last 30 days
    python manage.py sync_cve_data --all        # Full sync
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from reNgine.cve_enrichment import CVEEnrichmentService, CVEBatchEnricher
from startScan.models import CveId

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to synchronize CVE records with official threat intel feeds
    including NVD API v2.0, FIRST EPSS, and CISA KEV catalog.
    """
    help = 'Synchronize CVE data from official sources (NVD, EPSS, CISA KEV)'
    
    def add_arguments(self, parser):
        """
        Define command line options for the management command.

        Args:
            parser: ArgumentParser instance.
        """
        parser.add_argument(
            '--kev',
            action='store_true',
            help='Synchronize CISA Known Exploited Vulnerabilities catalog'
        )
        parser.add_argument(
            '--refresh',
            type=int,
            metavar='DAYS',
            help='Re-enrich CVEs modified in last N days'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of CVEs to process (default: 100)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Perform full synchronization (KEV + unenriched CVEs)'
        )
    
    def handle(self, *args, **options):
        """
        Handle execution of the sync_cve_data command based on provided arguments.

        Args:
            *args: Variable length argument list.
            **options: Arbitrary keyword arguments representing the command options.
        """
        service = CVEEnrichmentService()
        enricher = CVEBatchEnricher()
        
        self.stdout.write(
            self.style.SUCCESS(f'🔄 CVE Synchronization started at {timezone.now()}')
        )
        
        try:
            # Option 1: Sync CISA KEV catalog
            if options['kev'] or options['all']:
                self.stdout.write('📋 Synchronizing CISA KEV catalog...')
                result = service.sync_cisa_kev_catalog()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {result['updated']} updated, "
                        f"{result['new']} new from {result['total']} total KEV entries"
                    )
                )
            
            # Option 2: Refresh recent CVEs
            if options['refresh']:
                self.stdout.write(
                    f"🔃 Refreshing CVEs from last {options['refresh']} days..."
                )
                count = enricher.refresh_recent_cves(days=options['refresh'])
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Re-enriched {count} CVEs")
                )
            
            # Option 3: Enrich unenriched CVEs
            if options['all'] or not (options['kev'] or options['refresh']):
                limit = options['limit']
                unenriched_count = CveId.objects.filter(
                    cvss_v31_base_score__isnull=True
                ).count()
                
                self.stdout.write(
                    f"🆕 Enriching unenriched CVEs (limit: {limit}, "
                    f"total: {unenriched_count})..."
                )
                
                count = enricher.enrich_unenriched_cves(limit=limit)
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Enriched {count} CVEs")
                )
            
            # Summary metrics and progress output
            total_cves = CveId.objects.count()
            enriched_cves = CveId.objects.filter(
                cvss_v31_base_score__isnull=False
            ).count()
            kev_cves = CveId.objects.filter(is_cisa_kev=True).count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Synchronization complete!\n'
                    f'   Total CVEs: {total_cves}\n'
                    f'   Enriched: {enriched_cves} ({enriched_cves*100//max(total_cves,1)}%)\n'
                    f'   CISA KEV: {kev_cves}'
                )
            )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Synchronization failed: {e}')
            )
            logger.exception(e)
            raise
