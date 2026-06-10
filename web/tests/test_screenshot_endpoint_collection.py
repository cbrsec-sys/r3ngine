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
    def test_url_override_rejects_invalid_scheme(self, mock_capture):
        """url_override with non-http/https scheme is rejected before reaching Playwright."""
        result = take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
            url_override='javascript:alert(1)',
        )
        self.assertFalse(result)
        mock_capture.assert_not_called()

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


class TestScreenshotEndpointQuery(TestCase):
    """Tests for the screenshot() task — endpoint collection logic."""

    def _make_mock_proxy(self, scan, yaml_config=None):
        from unittest.mock import MagicMock
        proxy = MagicMock()
        proxy.scan = scan
        proxy.scan_id = scan.id
        proxy.results_dir = '/tmp/test_results'
        proxy.activity_id = None
        proxy.yaml_configuration = yaml_config or {}
        proxy.notify = MagicMock()
        return proxy

    def setUp(self):
        from django.utils import timezone
        from scanEngine.models import EngineType
        self.domain = Domain.objects.create(name='target.com')
        self.engine = EngineType.objects.create(
            engine_name='screenshot-endpoint-query-engine',
            yaml_configuration='screenshot: {}',
        )
        self.scan = ScanHistory.objects.create(
            scan_status=0,
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
        )

    def _make_subdomain(self, name, http_status=200):
        return Subdomain.objects.create(
            name=name,
            scan_history=self.scan,
            target_domain=self.domain,
            http_url=f'https://{name}',
            http_status=http_status,
        )

    def _make_default_endpoint(self, subdomain, http_url=None, http_status=200):
        url = http_url or f'https://{subdomain.name}'
        return EndPoint.objects.create(
            http_url=url,
            http_status=http_status,
            scan_history=self.scan,
            target_domain=self.domain,
            subdomain=subdomain,
            is_default=True,
        )

    @patch('reNgine.screenshot.tasks.take_screenshot_and_save')
    def test_screenshots_all_default_endpoints_normal_intensity(self, mock_save):
        """Normal intensity: all is_default=True endpoints with http_status > 0 are screenshotted."""
        mock_save.return_value = True

        sub1 = self._make_subdomain('a.target.com', http_status=200)
        sub2 = self._make_subdomain('b.target.com', http_status=403)
        sub3 = self._make_subdomain('c.target.com', http_status=200)
        self._make_default_endpoint(sub1, 'https://a.target.com', http_status=200)
        self._make_default_endpoint(sub2, 'https://b.target.com', http_status=403)
        self._make_default_endpoint(sub3, 'https://c.target.com', http_status=200)

        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        # All 3 endpoints have http_status > 0, so all 3 pass
        self.assertEqual(mock_save.call_count, 3)
        called_urls = {c.kwargs['url_override'] for c in mock_save.call_args_list}
        self.assertIn('https://a.target.com', called_urls)
        self.assertIn('https://b.target.com', called_urls)
        self.assertIn('https://c.target.com', called_urls)

    @patch('reNgine.screenshot.tasks.take_screenshot_and_save')
    def test_normal_intensity_excludes_zero_status_endpoints(self, mock_save):
        """Normal intensity excludes default endpoints where http_status == 0 (unreachable)."""
        mock_save.return_value = True

        alive_sub = self._make_subdomain('alive.target.com', http_status=200)
        dead_sub = self._make_subdomain('dead.target.com', http_status=0)
        self._make_default_endpoint(alive_sub, 'https://alive.target.com', http_status=200)
        self._make_default_endpoint(dead_sub, 'https://dead.target.com', http_status=0)

        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        self.assertEqual(mock_save.call_count, 1)
        called_url = mock_save.call_args.kwargs['url_override']
        self.assertEqual(called_url, 'https://alive.target.com')

    @patch('reNgine.screenshot.tasks.take_screenshot_and_save')
    def test_non_default_endpoints_are_skipped(self, mock_save):
        """Endpoints with is_default=False are never passed to screenshot capture."""
        mock_save.return_value = True

        sub = self._make_subdomain('sub.target.com', http_status=200)
        self._make_default_endpoint(sub, 'https://sub.target.com/root', http_status=200)
        # Non-default endpoint — should be ignored
        EndPoint.objects.create(
            http_url='https://sub.target.com/api/v1',
            http_status=200,
            scan_history=self.scan,
            target_domain=self.domain,
            subdomain=sub,
            is_default=False,
        )

        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        self.assertEqual(mock_save.call_count, 1)
        called_url = mock_save.call_args.kwargs['url_override']
        self.assertEqual(called_url, 'https://sub.target.com/root')

    @patch('reNgine.screenshot.tasks.take_screenshot_and_save')
    def test_full_url_with_path_is_passed(self, mock_save):
        """The full http_url including path is passed as url_override — not stripped to scheme://netloc."""
        mock_save.return_value = True

        sub = self._make_subdomain('panel.target.com', http_status=200)
        self._make_default_endpoint(sub, 'https://panel.target.com/admin/login', http_status=200)

        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        called_url = mock_save.call_args.kwargs['url_override']
        self.assertEqual(called_url, 'https://panel.target.com/admin/login')
        self.assertNotEqual(called_url, 'https://panel.target.com')

    @patch('reNgine.screenshot.tasks.take_screenshot_and_save')
    def test_no_endpoints_no_screenshots(self, mock_save):
        """With no default endpoints, screenshot() completes without calling capture."""
        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        mock_save.assert_not_called()
