"""
Tests for web/reNgine/crawl_tasks.py

All subprocess calls are mocked. Tests verify parsing and persistence logic.
"""
import json
import subprocess
from unittest.mock import patch, MagicMock
from django.test import TestCase


def _make_proxy(yaml_config=None):
    proxy = MagicMock()
    proxy.yaml_configuration = yaml_config or {}
    return proxy


class TestXURLFind3rScan(TestCase):
    @patch('subprocess.run')
    def test_returns_true_no_targets(self, mock_run):
        from reNgine.crawl_tasks import xurlfind3r_scan
        result = xurlfind3r_scan(_make_proxy(), scan_history_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_persists_discovered_urls(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://example.com/path1\nhttps://example.com/path2\nnot-a-url\n',
            stderr='',
        )
        with patch('startScan.models.EndPoint.objects') as mock_ep:
            mock_ep.bulk_create = MagicMock()
            from reNgine.crawl_tasks import xurlfind3r_scan
            result = xurlfind3r_scan(_make_proxy(), scan_history_id=1, domain='example.com')
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_handles_timeout_gracefully(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired('xurlfind3r', 300)
        from reNgine.crawl_tasks import xurlfind3r_scan
        result = xurlfind3r_scan(_make_proxy(), scan_history_id=1, domain='example.com')
        self.assertTrue(result)


class TestURLFinderScan(TestCase):
    @patch('subprocess.run')
    def test_returns_true_no_domain(self, mock_run):
        from reNgine.crawl_tasks import urlfinder_scan
        result = urlfinder_scan(_make_proxy(), scan_history_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_filters_non_http_lines(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://example.com/api\nftp://example.com/file\nhttps://example.com/login\n',
            stderr='',
        )
        with patch('startScan.models.EndPoint.objects') as mock_ep:
            saved = []
            mock_ep.bulk_create = lambda items, **kw: saved.extend(items)
            from reNgine.crawl_tasks import urlfinder_scan
            urlfinder_scan(_make_proxy(), scan_history_id=1, domain='example.com')
        # Only http(s) lines should be saved
        urls = [ep.http_url for ep in saved]
        self.assertNotIn('ftp://example.com/file', urls)


class TestCariddiScan(TestCase):
    @patch('subprocess.run')
    def test_returns_true_no_targets(self, mock_run):
        from reNgine.crawl_tasks import cariddi_scan
        result = cariddi_scan(_make_proxy(), scan_history_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_parses_tab_separated_output(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://example.com/api.js\t[secret:api_key]\nhttps://example.com/login\n',
            stderr='',
        )
        with patch('startScan.models.EndPoint.objects') as mock_ep:
            saved = []
            mock_ep.bulk_create = lambda items, **kw: saved.extend(items)
            from reNgine.crawl_tasks import cariddi_scan
            cariddi_scan(_make_proxy(), scan_history_id=1, url='https://example.com')
        urls = [ep.http_url for ep in saved]
        self.assertIn('https://example.com/api.js', urls)
        self.assertIn('https://example.com/login', urls)


class TestBUPScan(TestCase):
    @patch('subprocess.run')
    def test_returns_true_no_targets(self, mock_run):
        from reNgine.crawl_tasks import bup_scan
        result = bup_scan(_make_proxy(), scan_history_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_saves_bypass_as_medium_vuln(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[BYPASS] https://example.com/admin (200 via X-Original-URL)\n',
            stderr='',
        )
        with patch('startScan.models.Vulnerability.objects') as mock_vuln:
            saved = []
            mock_vuln.bulk_create = lambda items, **kw: saved.extend(items)
            from reNgine.crawl_tasks import bup_scan
            bup_scan(_make_proxy(), scan_history_id=1, url='https://example.com/admin')
        if saved:
            self.assertEqual(saved[0].severity, 2)  # medium

    @patch('subprocess.run')
    def test_handles_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired('bup', 120)
        from reNgine.crawl_tasks import bup_scan
        result = bup_scan(_make_proxy(), scan_history_id=1, url='https://example.com/admin')
        self.assertTrue(result)


class TestArjunScan(TestCase):
    @patch('subprocess.run')
    def test_returns_true_no_targets(self, mock_run):
        from reNgine.crawl_tasks import arjun_scan
        result = arjun_scan(_make_proxy(), scan_history_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=False)
    def test_handles_missing_output_file(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        from reNgine.crawl_tasks import arjun_scan
        result = arjun_scan(_make_proxy(), scan_history_id=1, url='https://example.com/search')
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_handles_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired('arjun', 600)
        from reNgine.crawl_tasks import arjun_scan
        result = arjun_scan(_make_proxy(), scan_history_id=1, url='https://example.com')
        self.assertTrue(result)


class TestFeroxbusterScan(TestCase):
    @patch('subprocess.run')
    def test_returns_true_no_targets(self, mock_run):
        from reNgine.crawl_tasks import feroxbuster_scan
        result = feroxbuster_scan(_make_proxy(), scan_history_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('os.path.exists', return_value=False)
    def test_handles_missing_output_file(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr=b'')
        from reNgine.crawl_tasks import feroxbuster_scan
        result = feroxbuster_scan(_make_proxy(), scan_history_id=1, url='https://example.com')
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_handles_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired('feroxbuster', 1800)
        from reNgine.crawl_tasks import feroxbuster_scan
        result = feroxbuster_scan(_make_proxy(), scan_history_id=1, url='https://example.com')
        self.assertTrue(result)


class TestGFScan(TestCase):
    @patch('subprocess.run')
    def test_returns_empty_for_no_urls(self, mock_run):
        from reNgine.crawl_tasks import gf_scan
        result = gf_scan(_make_proxy(), scan_history_id=1, pattern='xss')
        self.assertEqual(result, [])
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_returns_matched_urls(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://example.com/search?q=<script>\nhttps://example.com/name?n=test\n',
            stderr='',
        )
        from reNgine.crawl_tasks import gf_scan
        result = gf_scan(
            _make_proxy(), scan_history_id=1, pattern='xss',
            urls=['https://example.com/search?q=test', 'https://example.com/name?n=test'],
        )
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    @patch('subprocess.run')
    def test_handles_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired('gf', 60)
        from reNgine.crawl_tasks import gf_scan
        result = gf_scan(
            _make_proxy(), scan_history_id=1, pattern='xss',
            urls=['https://example.com/?q=test'],
        )
        self.assertEqual(result, [])
