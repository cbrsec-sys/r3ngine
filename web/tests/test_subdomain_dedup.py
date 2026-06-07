"""Tests for idempotent subdomain persistence across discovery retries."""
from django.test import TestCase
from django.utils import timezone

from reNgine.utils.task import save_subdomain
from scanEngine.models import EngineType
from startScan.models import ScanHistory, Subdomain
from targetApp.models import Domain


class SubdomainDedupTests(TestCase):
    def setUp(self):
        self.domain = Domain.objects.create(name='example.com')
        self.engine = EngineType.objects.create(
            engine_name='dedup-test-engine',
            yaml_configuration='subdomain_discovery: {}',
        )
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
        )
        self.ctx = {
            'scan_history_id': self.scan.id,
            'domain_id': self.domain.id,
        }

    def test_rediscovery_updates_existing_subdomain(self):
        first, created_first = save_subdomain('api.example.com', ctx=self.ctx)
        self.assertTrue(created_first)
        first_id = first.id
        first.discovered_date = timezone.now()
        first.http_status = 200
        first.save()

        second, created_second = save_subdomain('API.EXAMPLE.COM', ctx=self.ctx)
        self.assertFalse(created_second)
        self.assertEqual(second.id, first_id)
        self.assertEqual(second.name, 'api.example.com')
        self.assertEqual(Subdomain.objects.filter(scan_history=self.scan).count(), 1)

    def test_rediscovery_backfills_target_domain_and_discovered_date(self):
        subdomain, created = save_subdomain('www.example.com', ctx=self.ctx)
        self.assertTrue(created)
        subdomain.discovered_date = None
        subdomain.save(update_fields=['discovered_date'])

        rediscovered, created_again = save_subdomain('www.example.com', ctx=self.ctx)
        self.assertFalse(created_again)
        self.assertEqual(rediscovered.id, subdomain.id)
        self.assertIsNotNone(rediscovered.discovered_date)
        self.assertEqual(rediscovered.target_domain_id, self.domain.id)

    def test_unique_constraint_blocks_duplicate_rows(self):
        Subdomain.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            name='dup.example.com',
        )
        subdomain, created = save_subdomain('dup.example.com', ctx=self.ctx)
        self.assertFalse(created)
        self.assertEqual(Subdomain.objects.filter(scan_history=self.scan).count(), 1)
        self.assertEqual(subdomain.name, 'dup.example.com')
