from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from scanEngine.models import EngineType
from startScan.models import (
    ScanHistory, Subdomain, EndPoint, Screenshot
)
from targetApp.models import Domain
from reNgine.screenshot.tasks import take_screenshot_and_save


class TestTakeScreenshotAndSaveUrlOverride(TestCase):
    """Tests for url_override parameter in take_screenshot_and_save."""

    def setUp(self):
        self.domain = Domain.objects.create(name='screenshot-test.example.com')
        self.engine = EngineType.objects.create(
            engine_name='screenshot-test-engine',
            yaml_configuration='screenshot: {}',
        )
        self.scan = ScanHistory.objects.create(
            scan_status=0,
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
        )
        self.subdomain = Subdomain.objects.create(
            name='app.screenshot-test.example.com',
            scan_history=self.scan,
            target_domain=self.domain,
            http_url='https://app.screenshot-test.example.com/admin/panel',
            http_status=200,
        )

    @patch('reNgine.screenshot.tasks.run_capture')
    def test_url_override_uses_provided_url_not_base(self, mock_capture):
        """When url_override is provided, that exact URL is captured — no path stripping."""
        mock_capture.return_value = {
            'screenshot_path': '/results/screenshots/abc123.png',
            'html_path': '/results/html/abc123.html',
            'title': 'Admin Panel',
            'status_code': 200,
            'response_headers': {},
            'tags': [],
        }
        full_url = 'https://app.screenshot-test.example.com/admin/panel'

        result = take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
            url_override=full_url,
        )

        self.assertTrue(result)
        mock_capture.assert_called_once()
        called_url = mock_capture.call_args[0][0]
        self.assertEqual(called_url, full_url)
        # Must NOT strip path to base URL
        self.assertNotEqual(called_url, 'https://app.screenshot-test.example.com')

    @patch('reNgine.screenshot.tasks.run_capture')
    def test_url_override_does_not_query_endpoints(self, mock_capture):
        """url_override path skips querying EndPoint objects."""
        mock_capture.return_value = {
            'screenshot_path': '/results/screenshots/abc.png',
            'html_path': None,
            'title': 'Test',
            'status_code': 200,
            'response_headers': {},
            'tags': [],
        }
        # No endpoints created — if it tries to query them and fall back,
        # it would use http://app.screenshot-test.example.com or https://...
        full_url = 'https://app.screenshot-test.example.com/admin/panel'

        take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
            url_override=full_url,
        )

        called_url = mock_capture.call_args[0][0]
        # Confirms it used url_override, not a synthesised root URL
        self.assertEqual(called_url, 'https://app.screenshot-test.example.com/admin/panel')

    @patch('reNgine.screenshot.tasks.run_capture')
    def test_screenshot_saved_with_override_url_in_db(self, mock_capture):
        """Screenshot model is created with the full url_override URL."""
        mock_capture.return_value = {
            'screenshot_path': '/results/screenshots/full_path.png',
            'html_path': None,
            'title': 'Panel',
            'status_code': 200,
            'response_headers': {},
            'tags': [],
        }
        full_url = 'https://app.screenshot-test.example.com/admin/panel'

        take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
            url_override=full_url,
        )

        saved = Screenshot.objects.filter(subdomain=self.subdomain, scan_history=self.scan).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.url, full_url)

    @patch('reNgine.screenshot.tasks.run_capture')
    def test_no_override_still_works_legacy_path(self, mock_capture):
        """Without url_override, existing endpoint-query behaviour is preserved."""
        mock_capture.return_value = {
            'screenshot_path': '/results/screenshots/legacy.png',
            'html_path': None,
            'title': 'Home',
            'status_code': 200,
            'response_headers': {},
            'tags': [],
        }
        # Create an endpoint so the legacy path has something to query
        EndPoint.objects.create(
            http_url='https://app.screenshot-test.example.com',
            scan_history=self.scan,
            subdomain=self.subdomain,
            target_domain=self.domain,
        )

        result = take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
        )

        self.assertTrue(result)
        # Legacy path strips to base URL
        called_url = mock_capture.call_args[0][0]
        self.assertEqual(called_url, 'https://app.screenshot-test.example.com')
