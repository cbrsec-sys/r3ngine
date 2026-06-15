"""
Tests for Phase 3: Extended Target Types.

Covers:
  - TARGET_TYPE_* constants in definitions.py
  - Domain.target_type model field
  - AddTargetSerializer per-type validation
  - target_router.route_target_to_workflow dispatch table
  - target_router.infer_target_type auto-detection
"""
from unittest.mock import patch

from django.test import TestCase

from dashboard.models import Project


# ---------------------------------------------------------------------------
# Task 1 — constants
# ---------------------------------------------------------------------------

class TestTargetTypeConstants(TestCase):
    def test_all_target_type_constants_defined(self):
        from reNgine.definitions import (
            TARGET_TYPE_DOMAIN,
            TARGET_TYPE_HOST,
            TARGET_TYPE_IP,
            TARGET_TYPE_CIDR,
            TARGET_TYPE_URL,
            TARGET_TYPE_EMAIL,
            TARGET_TYPE_USERNAME,
            TARGET_TYPE_PHONE,
            TARGET_TYPE_CRYPTO_ADDRESS,
            TARGET_TYPE_SUBDOMAIN,
            TARGET_TYPE_CODE_PATH,
        )
        self.assertEqual(TARGET_TYPE_DOMAIN, 'domain')
        self.assertEqual(TARGET_TYPE_HOST, 'host')
        self.assertEqual(TARGET_TYPE_IP, 'ip')
        self.assertEqual(TARGET_TYPE_CIDR, 'cidr')
        self.assertEqual(TARGET_TYPE_URL, 'url')
        self.assertEqual(TARGET_TYPE_EMAIL, 'email')
        self.assertEqual(TARGET_TYPE_USERNAME, 'username')
        self.assertEqual(TARGET_TYPE_PHONE, 'phone')
        self.assertEqual(TARGET_TYPE_CRYPTO_ADDRESS, 'crypto_address')
        self.assertEqual(TARGET_TYPE_SUBDOMAIN, 'subdomain')
        self.assertEqual(TARGET_TYPE_CODE_PATH, 'code_path')

    def test_target_type_choices_has_all_types(self):
        from reNgine.definitions import TARGET_TYPE_CHOICES
        codes = [c for c, _ in TARGET_TYPE_CHOICES]
        for expected in [
            'domain', 'host', 'subdomain', 'url', 'ip',
            'cidr', 'email', 'username', 'phone', 'crypto_address', 'code_path',
        ]:
            self.assertIn(expected, codes)


# ---------------------------------------------------------------------------
# Task 2 — Domain model
# ---------------------------------------------------------------------------

class TestTargetModel(TestCase):
    def setUp(self):
        self.project = Project.objects.create(
            name='TestProject',
            slug='test-project',
            insert_date='2026-01-01T00:00:00Z',
        )

    def test_domain_has_target_type_field(self):
        from targetApp.models import Domain
        domain = Domain(name='example.com', target_type='domain', project=self.project)
        self.assertEqual(domain.target_type, 'domain')

    def test_domain_target_type_defaults_to_domain(self):
        from targetApp.models import Domain
        import django.utils.timezone as tz
        domain = Domain.objects.create(
            name='default-type.com',
            project=self.project,
            insert_date=tz.now(),
        )
        self.assertEqual(domain.target_type, 'domain')
        domain.delete()

    def test_cidr_target_can_be_created(self):
        from targetApp.models import Domain
        import django.utils.timezone as tz
        target = Domain.objects.create(
            name='10.0.0.0/8',
            target_type='cidr',
            project=self.project,
            insert_date=tz.now(),
        )
        self.assertEqual(target.target_type, 'cidr')
        target.delete()

    def test_email_target_can_be_created(self):
        from targetApp.models import Domain
        import django.utils.timezone as tz
        target = Domain.objects.create(
            name='user@example.com',
            target_type='email',
            project=self.project,
            insert_date=tz.now(),
        )
        self.assertEqual(target.target_type, 'email')
        target.delete()

    def test_username_target_can_be_created(self):
        from targetApp.models import Domain
        import django.utils.timezone as tz
        target = Domain.objects.create(
            name='johndoe',
            target_type='username',
            project=self.project,
            insert_date=tz.now(),
        )
        self.assertEqual(target.target_type, 'username')
        target.delete()


# ---------------------------------------------------------------------------
# Task 3 — Serializer validation
# ---------------------------------------------------------------------------

class TestTargetSerializer(TestCase):
    def test_cidr_requires_valid_cidr_format(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'not-a-cidr', 'target_type': 'cidr'})
        self.assertFalse(s.is_valid())
        self.assertIn('name', s.errors)

    def test_valid_cidr_passes(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': '192.168.1.0/24', 'target_type': 'cidr'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_valid_ipv6_cidr_passes(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': '2001:db8::/32', 'target_type': 'cidr'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_email_requires_email_format(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'not-an-email', 'target_type': 'email'})
        self.assertFalse(s.is_valid())

    def test_valid_email_passes(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'user@example.com', 'target_type': 'email'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_username_accepts_valid_chars(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'valid_user123', 'target_type': 'username'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_username_accepts_special_chars(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'user.name-handle@plus+ok', 'target_type': 'username'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_username_rejects_spaces(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'bad user name', 'target_type': 'username'})
        self.assertFalse(s.is_valid())

    def test_ip_requires_valid_ip(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'not.an.ip.here', 'target_type': 'ip'})
        self.assertFalse(s.is_valid())

    def test_valid_ipv4_passes(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': '192.0.2.1', 'target_type': 'ip'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_valid_ipv6_passes(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': '::1', 'target_type': 'ip'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_code_path_accepts_git_url(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={
            'name': 'https://github.com/user/repo.git',
            'target_type': 'code_path',
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_domain_type_passes_any_name(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'example.com', 'target_type': 'domain'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_phone_type_passes_any_non_empty_name(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': '+1-555-0100', 'target_type': 'phone'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_invalid_target_type_rejected(self):
        from targetApp.serializers import AddTargetSerializer
        s = AddTargetSerializer(data={'name': 'example.com', 'target_type': 'unknown_type'})
        self.assertFalse(s.is_valid())
        self.assertIn('target_type', s.errors)


# ---------------------------------------------------------------------------
# Task 4 — Target router
# ---------------------------------------------------------------------------

class TestTargetRouter(TestCase):
    def test_domain_routes_to_master_scan(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('example.com', 'domain')
        self.assertEqual(workflow_name, 'MasterScanWorkflow')
        self.assertEqual(ctx['domain'], 'example.com')

    def test_cidr_routes_to_cidr_recon(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('192.168.0.0/24', 'cidr')
        self.assertEqual(workflow_name, 'CIDRReconWorkflow')
        self.assertEqual(ctx['cidr'], '192.168.0.0/24')

    def test_email_routes_to_user_hunt(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('user@example.com', 'email')
        self.assertEqual(workflow_name, 'UserHuntWorkflow')
        self.assertEqual(ctx['target_type'], 'email')

    def test_username_routes_to_user_hunt(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('johndoe', 'username')
        self.assertEqual(workflow_name, 'UserHuntWorkflow')
        self.assertEqual(ctx['target_type'], 'username')

    def test_ip_routes_to_host_recon(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('1.2.3.4', 'ip')
        self.assertEqual(workflow_name, 'HostReconWorkflow')
        self.assertEqual(ctx['target'], '1.2.3.4')

    def test_url_routes_to_url_crawl(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('https://example.com', 'url')
        self.assertEqual(workflow_name, 'URLCrawlWorkflow')
        self.assertIn('urls', ctx)
        self.assertEqual(ctx['urls'], ['https://example.com'])

    def test_code_path_routes_to_code_scan(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('/path/to/code', 'code_path')
        self.assertEqual(workflow_name, 'CodeScanWorkflow')

    def test_phone_routes_to_user_hunt(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('+15550100', 'phone')
        self.assertEqual(workflow_name, 'UserHuntWorkflow')

    def test_crypto_address_routes_to_user_hunt(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow(
            '1A1zP1eP5QGefi2DMPTfTL5SLmv7Divf8', 'crypto_address'
        )
        self.assertEqual(workflow_name, 'UserHuntWorkflow')

    def test_unknown_type_defaults_to_master_scan(self):
        from reNgine.target_router import route_target_to_workflow
        workflow_name, ctx = route_target_to_workflow('example.com', 'nonexistent_type')
        self.assertEqual(workflow_name, 'MasterScanWorkflow')

    def test_scan_history_id_in_context(self):
        from reNgine.target_router import route_target_to_workflow
        _, ctx = route_target_to_workflow('example.com', 'domain', scan_history_id=42)
        self.assertEqual(ctx['scan_history_id'], 42)

    def test_yaml_configuration_in_context(self):
        from reNgine.target_router import route_target_to_workflow
        cfg = {'subdomain_discovery': True}
        _, ctx = route_target_to_workflow('example.com', 'domain', yaml_configuration=cfg)
        self.assertEqual(ctx['yaml_configuration'], cfg)


# ---------------------------------------------------------------------------
# Task 4 — infer_target_type auto-detection
# ---------------------------------------------------------------------------

class TestInferTargetType(TestCase):
    def test_ipv4_inferred_as_ip(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type('1.2.3.4'), 'ip')

    def test_ipv6_inferred_as_ip(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type('::1'), 'ip')

    def test_cidr_inferred(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type('10.0.0.0/8'), 'cidr')

    def test_http_url_inferred(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type('https://example.com'), 'url')

    def test_email_inferred(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type('user@example.com'), 'email')

    def test_git_url_inferred_as_code_path(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type('https://github.com/user/repo.git'), 'code_path')

    def test_absolute_path_inferred_as_code_path(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type('/home/user/project'), 'code_path')

    def test_domain_name_inferred(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type('example.com'), 'domain')

    def test_empty_string_defaults_to_domain(self):
        from reNgine.target_router import infer_target_type
        self.assertEqual(infer_target_type(''), 'domain')
