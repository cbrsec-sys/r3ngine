"""Tests for WPScan gating logic added in v3.5.0.

wpscan_scan() must only run when WordPress indicators are present — either
via technology fingerprinting on a subdomain, or via wp-like paths discovered
by fetch_url / dir_file_fuzz and stored in EndPoint.http_url.

These are unit tests; they call the task function directly with a mock
self-proxy and patch stream_command to prevent real subprocess execution.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.utils import timezone

from startScan.models import ScanHistory, Subdomain, Technology, EndPoint
from targetApp.models import Domain
from scanEngine.models import EngineType


def _make_proxy(scan, subdomain=None, subscan=None, yaml_config=None):
    """Build a minimal task-proxy mock for wpscan_scan."""
    proxy = MagicMock()
    proxy.scan = scan
    proxy.scan.results_dir = '/tmp/rengine_test_wpscan'
    proxy.scan_id = scan.id
    proxy.subdomain = subdomain
    proxy.subscan = subscan
    proxy.yaml_configuration = yaml_config or {
        'vulnerability_scan': {
            'run_wpscan': True,
        }
    }
    proxy.results_dir = '/tmp/rengine_test_wpscan'
    proxy.activity_id = None
    return proxy


class TestWpscanGating(TestCase):
    def setUp(self):
        self.domain = Domain.objects.create(name='wpscan-gate.example.com')
        self.engine = EngineType.objects.create(engine_name='WPScan Gate Test Engine')
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_status=1,
            start_scan_date=timezone.now(),
            scan_type=self.engine,
        )

    def _make_subdomain(self, name):
        return Subdomain.objects.create(
            name=name,
            scan_history=self.scan,
            target_domain=self.domain,
        )

    def _add_tech(self, subdomain, tech_name):
        tech, _ = Technology.objects.get_or_create(name=tech_name)
        subdomain.technologies.add(tech)
        subdomain.save()

    def _make_endpoint(self, subdomain, path):
        return EndPoint.objects.create(
            scan_history=self.scan,
            subdomain=subdomain,
            http_url=f'https://{subdomain.name}/{path}',
            target_domain=self.domain,
        )

    # ------------------------------------------------------------------
    # Skipped — no WordPress indicators
    # ------------------------------------------------------------------

    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_skips_when_no_wordpress_indicators(self, mock_stream):
        """No WP tech and no wp-like paths → scan skipped."""
        self._make_subdomain('app.wpscan-gate.example.com')
        proxy = _make_proxy(self.scan)

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNone(result)
        mock_stream.assert_not_called()

    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_skips_when_disabled_in_config(self, mock_stream):
        """run_wpscan=False skips immediately even when WordPress is detected."""
        sub = self._make_subdomain('blog.wpscan-gate.example.com')
        self._add_tech(sub, 'WordPress')
        proxy = _make_proxy(self.scan, yaml_config={
            'vulnerability_scan': {'run_wpscan': False},
        })

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNone(result)
        mock_stream.assert_not_called()

    # ------------------------------------------------------------------
    # Runs — WordPress detected via technology fingerprint
    # ------------------------------------------------------------------

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_runs_when_wordpress_tech_detected(self, mock_stream, mock_parse):
        """Subdomain with WordPress technology triggers WPScan."""
        sub = self._make_subdomain('blog.wpscan-gate.example.com')
        self._add_tech(sub, 'WordPress')
        proxy = _make_proxy(self.scan)

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNotNone(result)
        # stream_command is called twice (1. update, 2. scan)
        self.assertEqual(mock_stream.call_count, 2)
        cmd_update = mock_stream.call_args_list[0][0][0]
        cmd_scan = mock_stream.call_args_list[1][0][0]
        self.assertIn('wpscan --update', cmd_update)
        self.assertIn('https://blog.wpscan-gate.example.com', cmd_scan)
        self.assertNotIn('https://blog.wpscan-gate.example.com/', cmd_scan)

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_only_wordpress_subdomains_are_targeted(self, mock_stream, mock_parse):
        """Only WordPress-positive subdomains appear in scan targets."""
        wp_sub = self._make_subdomain('blog.wpscan-gate.example.com')
        self._add_tech(wp_sub, 'WordPress')
        # Non-WP subdomain should not be targeted
        self._make_subdomain('api.wpscan-gate.example.com')
        proxy = _make_proxy(self.scan)

        from reNgine.wpscan_tasks import wpscan_scan
        wpscan_scan(proxy, urls=[])

        # stream_command called 2 times (1. update, 2. target)
        self.assertEqual(mock_stream.call_count, 2)
        cmd_update = mock_stream.call_args_list[0][0][0]
        self.assertIn('wpscan --update', cmd_update)
        cmd_scan = mock_stream.call_args_list[1][0][0]
        self.assertIn('blog.wpscan-gate.example.com', cmd_scan)
        self.assertNotIn('api.wpscan-gate.example.com', cmd_scan)

    # ------------------------------------------------------------------
    # Runs — WordPress detected via wp-like paths in EndPoint
    # ------------------------------------------------------------------

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_runs_when_wp_login_path_discovered(self, mock_stream, mock_parse):
        """Subdomain with /wp-login.php endpoint triggers WPScan even without tech tag."""
        sub = self._make_subdomain('site.wpscan-gate.example.com')
        self._make_endpoint(sub, 'wp-login.php')
        proxy = _make_proxy(self.scan)

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNotNone(result)
        # stream_command called 2 times (1. update, 2. target)
        self.assertEqual(mock_stream.call_count, 2)
        cmd_update = mock_stream.call_args_list[0][0][0]
        self.assertIn('wpscan --update', cmd_update)
        cmd_scan = mock_stream.call_args_list[1][0][0]
        self.assertIn('site.wpscan-gate.example.com', cmd_scan)

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_runs_when_wp_admin_path_discovered(self, mock_stream, mock_parse):
        """Subdomain with /wp-admin endpoint triggers WPScan."""
        sub = self._make_subdomain('site2.wpscan-gate.example.com')
        self._make_endpoint(sub, 'wp-admin/')
        proxy = _make_proxy(self.scan)

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNotNone(result)
        self.assertEqual(mock_stream.call_count, 2)
        cmd_scan = mock_stream.call_args_list[1][0][0]
        self.assertIn('site2.wpscan-gate.example.com', cmd_scan)

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_runs_when_xmlrpc_path_discovered(self, mock_stream, mock_parse):
        """Subdomain with /xmlrpc.php endpoint triggers WPScan."""
        sub = self._make_subdomain('site3.wpscan-gate.example.com')
        self._make_endpoint(sub, 'xmlrpc.php')
        proxy = _make_proxy(self.scan)

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNotNone(result)
        self.assertEqual(mock_stream.call_count, 2)
        cmd_scan = mock_stream.call_args_list[1][0][0]
        self.assertIn('site3.wpscan-gate.example.com', cmd_scan)

    # ------------------------------------------------------------------
    # Subscan mode
    # ------------------------------------------------------------------

    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_subscan_non_wordpress_subdomain_skipped(self, mock_stream):
        """In subscan mode, a subdomain with no WP indicators is skipped."""
        sub = self._make_subdomain('api.wpscan-gate.example.com')
        subscan_mock = MagicMock()
        proxy = _make_proxy(self.scan, subdomain=sub, subscan=subscan_mock)

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNone(result)
        mock_stream.assert_not_called()

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_subscan_wordpress_subdomain_runs(self, mock_stream, mock_parse):
        """In subscan mode, a WordPress subdomain triggers the scan."""
        sub = self._make_subdomain('blog.wpscan-gate.example.com')
        self._add_tech(sub, 'WordPress')
        subscan_mock = MagicMock()
        proxy = _make_proxy(self.scan, subdomain=sub, subscan=subscan_mock)

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNotNone(result)
        self.assertEqual(mock_stream.call_count, 2)
        cmd_scan = mock_stream.call_args_list[1][0][0]
        self.assertIn('blog.wpscan-gate.example.com', cmd_scan)

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command', return_value=iter([]))
    def test_subscan_wp_path_endpoint_runs(self, mock_stream, mock_parse):
        """In subscan mode, a subdomain with a wp-like endpoint triggers the scan."""
        sub = self._make_subdomain('site.wpscan-gate.example.com')
        self._make_endpoint(sub, 'wp-content/uploads/file.jpg')
        subscan_mock = MagicMock()
        proxy = _make_proxy(self.scan, subdomain=sub, subscan=subscan_mock)

        from reNgine.wpscan_tasks import wpscan_scan
        result = wpscan_scan(proxy, urls=[])

        self.assertIsNotNone(result)
        self.assertEqual(mock_stream.call_count, 2)
        cmd_scan = mock_stream.call_args_list[1][0][0]
        self.assertIn('site.wpscan-gate.example.com', cmd_scan)

    # ------------------------------------------------------------------
    # WPScan Update & Retry Logic Tests
    # ------------------------------------------------------------------

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command')
    def test_wpscan_ssl_error_retry_and_success(self, mock_stream, mock_parse):
        """WPScan retries on SSL metadata fetch error and then succeeds."""
        sub = self._make_subdomain('blog.wpscan-gate.example.com')
        self._add_tech(sub, 'WordPress')
        proxy = _make_proxy(self.scan)
        
        attempts = []
        
        def stream_command_side_effect(cmd, *args, **kwargs):
            if '--update' in cmd:
                return iter([])
            
            attempts.append(cmd)
            output_file = '/tmp/rengine_test_wpscan/vulnerability/wpscan/blog.wpscan-gate.example.com_wpscan.json'
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            if len(attempts) == 1:
                # First attempt: SSL/metadata error JSON
                error_data = {
                    "db_update_started": True,
                    "scan_aborted": "Unable to get https://data.wpscan.org/metadata.json.sha512 (SSL peer certificate or SSH remote key was not OK)",
                    "target_url": "https://blog.wpscan-gate.example.com"
                }
                with open(output_file, 'w') as f:
                    json.dump(error_data, f)
            else:
                # Second attempt: Successful dummy scan result
                success_data = {
                    "start_time": 12345,
                    "interesting_findings": []
                }
                with open(output_file, 'w') as f:
                    json.dump(success_data, f)
            return iter([])

        mock_stream.side_effect = stream_command_side_effect

        from reNgine.wpscan_tasks import wpscan_scan
        wpscan_scan(proxy, urls=[])

        # Total calls to stream_command: 1 (update) + 2 (scans) = 3 calls
        self.assertEqual(mock_stream.call_count, 3)
        self.assertEqual(len(attempts), 2)
        self.assertIn('https://blog.wpscan-gate.example.com', attempts[0])
        self.assertNotIn('https://blog.wpscan-gate.example.com/', attempts[0])
        self.assertIn('https://blog.wpscan-gate.example.com', attempts[1])

    @patch('reNgine.wpscan_tasks.parse_wpscan_results')
    @patch('reNgine.tasks.stream_command')
    @patch('reNgine.wpscan_tasks.get_random_proxy', return_value='127.0.0.1:8080')
    def test_wpscan_ssl_error_max_retries_fail(self, mock_get_proxy, mock_stream, mock_parse):
        """WPScan retries up to max attempts, and final attempt runs without proxy."""
        sub = self._make_subdomain('blog.wpscan-gate.example.com')
        self._add_tech(sub, 'WordPress')
        proxy = _make_proxy(self.scan)

        attempts = []

        def stream_command_side_effect(cmd, *args, **kwargs):
            if '--update' in cmd:
                return iter([])

            attempts.append(cmd)
            output_file = '/tmp/rengine_test_wpscan/vulnerability/wpscan/blog.wpscan-gate.example.com_wpscan.json'
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # Always write SSL error JSON
            error_data = {
                "db_update_started": True,
                "scan_aborted": "Unable to get https://data.wpscan.org/metadata.json.sha512 (SSL peer certificate or SSH remote key was not OK)",
                "target_url": "https://blog.wpscan-gate.example.com"
            }
            with open(output_file, 'w') as f:
                json.dump(error_data, f)
            return iter([])

        mock_stream.side_effect = stream_command_side_effect

        from reNgine.wpscan_tasks import wpscan_scan
        wpscan_scan(proxy, urls=[])

        # Total calls to stream_command: 1 (update) + 4 (scans) = 5 calls
        self.assertEqual(mock_stream.call_count, 5)
        self.assertEqual(len(attempts), 4)

        # Verify first 3 scan attempts included proxy
        for i in range(3):
            self.assertIn('--proxy 127.0.0.1:8080', attempts[i])

        # Verify 4th (final) attempt did NOT include proxy
        self.assertNotIn('--proxy', attempts[3])


class TestWpscanParser(TestCase):
    def setUp(self):
        self.domain = Domain.objects.create(name='parser-test.example.com')
        self.engine = EngineType.objects.create(engine_name='Parser Test Engine')
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_status=1,
            start_scan_date=timezone.now(),
            scan_type=self.engine,
        )
        self.subdomain = Subdomain.objects.create(
            name='parser-test.example.com',
            scan_history=self.scan,
            target_domain=self.domain,
        )
        self.proxy = MagicMock()
        self.proxy.scan = self.scan
        self.proxy.domain = self.domain

    def _write_json(self, data):
        f = tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w')
        json.dump(data, f)
        f.close()
        return f.name

    def test_xmlrpc_finding_maps_to_high_severity(self):
        payload = {
            'interesting_findings': [{
                'type': 'xmlrpc',
                'to_s': 'XML-RPC seems to be enabled: https://parser-test.example.com/xmlrpc.php',
                'found_by': 'Direct Access',
                'confidence': 100,
                'confirmed_by': {},
                'references': {'url': ['http://codex.wordpress.org/XML-RPC_Pingback_API']},
                'interesting_entries': [],
            }],
        }
        path = self._write_json(payload)
        try:
            from reNgine.wpscan_tasks import parse_wpscan_results
            parse_wpscan_results(self.proxy, path, self.subdomain)
        finally:
            os.unlink(path)

        from startScan.models import Vulnerability
        vuln = Vulnerability.objects.filter(scan_history=self.scan, name__icontains='XML-RPC').first()
        self.assertIsNotNone(vuln, "Expected XML-RPC finding to be stored")
        self.assertEqual(vuln.severity, 3, "XML-RPC should map to High (3)")
        self.assertNotEqual(vuln.name, 'WPScan Finding', "Name must not be generic fallback")

    def test_upload_directory_listing_maps_to_medium(self):
        payload = {
            'interesting_findings': [{
                'type': 'upload_directory_listing',
                'to_s': 'Upload directory has listing enabled: https://parser-test.example.com/wp-content/uploads/',
                'found_by': 'Direct Access',
                'confidence': 100,
                'confirmed_by': {},
                'references': {},
                'interesting_entries': [],
            }],
        }
        path = self._write_json(payload)
        try:
            from reNgine.wpscan_tasks import parse_wpscan_results
            parse_wpscan_results(self.proxy, path, self.subdomain)
        finally:
            os.unlink(path)

        from startScan.models import Vulnerability
        vuln = Vulnerability.objects.filter(scan_history=self.scan, name__icontains='Upload Directory').first()
        self.assertIsNotNone(vuln)
        self.assertEqual(vuln.severity, 2)

    def test_readme_maps_to_info(self):
        payload = {
            'interesting_findings': [{
                'type': 'readme',
                'to_s': 'WordPress readme found: https://parser-test.example.com/readme.html',
                'found_by': 'Direct Access',
                'confidence': 100,
                'confirmed_by': {},
                'references': {},
                'interesting_entries': [],
            }],
        }
        path = self._write_json(payload)
        try:
            from reNgine.wpscan_tasks import parse_wpscan_results
            parse_wpscan_results(self.proxy, path, self.subdomain)
        finally:
            os.unlink(path)

        from startScan.models import Vulnerability
        vuln = Vulnerability.objects.filter(scan_history=self.scan, name__icontains='Readme').first()
        self.assertIsNotNone(vuln)
        self.assertEqual(vuln.severity, 0)

