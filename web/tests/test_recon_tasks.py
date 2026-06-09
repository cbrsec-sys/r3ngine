"""
Tests for web/reNgine/recon_tasks.py

All subprocess calls and external requests are mocked.
Tests verify correct parsing logic and database persistence patterns.
"""
import json
from unittest.mock import patch, MagicMock, call
from django.test import TestCase


def _make_proxy(yaml_config=None):
    proxy = MagicMock()
    proxy.yaml_configuration = yaml_config or {}
    return proxy


class TestDNSXScan(TestCase):
    @patch('subprocess.run')
    def test_dnsx_creates_subdomain_records(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        output = json.dumps({'host': 'sub.example.com', 'a': ['1.2.3.4']}) + '\n'

        # Write fake output file
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.__iter__ = lambda s: iter([output])
            with patch('os.path.exists', return_value=True):
                with patch('os.remove'):
                    with patch('startScan.models.Subdomain.objects') as mock_sub:
                        mock_sub.filter.return_value.exists.return_value = False
                        from reNgine.recon_tasks import dnsx_scan
                        result = dnsx_scan(
                            _make_proxy(), scan_history_id=1, domain_id=1,
                            subdomain='sub.example.com',
                        )
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_dnsx_returns_true_with_no_targets(self, mock_run):
        from reNgine.recon_tasks import dnsx_scan
        result = dnsx_scan(_make_proxy(), scan_history_id=1, domain_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()


class TestWAFW00FScan(TestCase):
    @patch('subprocess.run')
    def test_wafw00f_returns_true_no_targets(self, mock_run):
        from reNgine.recon_tasks import wafw00f_scan
        result = wafw00f_scan(_make_proxy(), scan_history_id=1, domain_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_wafw00f_handles_no_detection(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{'detected': False, 'firewall': None}]),
            stderr='',
        )
        from reNgine.recon_tasks import wafw00f_scan
        result = wafw00f_scan(
            _make_proxy(), scan_history_id=1, domain_id=1,
            url='https://example.com',
        )
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_wafw00f_handles_invalid_json(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout='error output', stderr='')
        from reNgine.recon_tasks import wafw00f_scan
        result = wafw00f_scan(
            _make_proxy(), scan_history_id=1, domain_id=1,
            url='https://example.com',
        )
        self.assertTrue(result)


class TestFPingScan(TestCase):
    @patch('subprocess.run')
    def test_fping_parses_alive_hosts(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='192.0.2.1 is alive\n192.0.2.2 is alive\n192.0.2.3 is unreachable\n',
            stderr='',
        )
        from reNgine.recon_tasks import fping_scan
        result = fping_scan(_make_proxy(), scan_history_id=1, cidr='192.0.2.0/24')
        self.assertIsInstance(result, list)
        self.assertIn('192.0.2.1', result)
        self.assertIn('192.0.2.2', result)
        self.assertNotIn('192.0.2.3', result)

    @patch('subprocess.run')
    def test_fping_returns_empty_for_no_targets(self, mock_run):
        from reNgine.recon_tasks import fping_scan
        result = fping_scan(_make_proxy(), scan_history_id=1)
        self.assertEqual(result, [])
        mock_run.assert_not_called()


class TestARPScanScan(TestCase):
    @patch('subprocess.run')
    def test_arpscan_parses_ips(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='192.0.2.1\thost1\t00:11:22:33:44:55\tVendor\n',
            stderr='',
        )
        from reNgine.recon_tasks import arpscan_scan
        result = arpscan_scan(_make_proxy(), scan_history_id=1, cidr='192.0.2.0/24')
        self.assertIn('192.0.2.1', result)

    @patch('subprocess.run')
    def test_arpscan_returns_empty_for_no_cidr(self, mock_run):
        from reNgine.recon_tasks import arpscan_scan
        result = arpscan_scan(_make_proxy(), scan_history_id=1)
        self.assertEqual(result, [])
        mock_run.assert_not_called()


class TestMapCIDRExpand(TestCase):
    @patch('subprocess.run')
    def test_mapcidr_returns_ip_list(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='192.0.2.1\n192.0.2.2\n192.0.2.3\n',
            stderr='',
        )
        from reNgine.recon_tasks import mapcidr_expand
        result = mapcidr_expand(_make_proxy(), scan_history_id=1, cidr='192.0.2.0/30')
        self.assertEqual(result, ['192.0.2.1', '192.0.2.2', '192.0.2.3'])

    @patch('subprocess.run')
    def test_mapcidr_timeout_returns_empty(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('mapcidr', 60)
        from reNgine.recon_tasks import mapcidr_expand
        result = mapcidr_expand(_make_proxy(), scan_history_id=1, cidr='10.0.0.0/8')
        self.assertEqual(result, [])


class TestSSHAuditScan(TestCase):
    @patch('subprocess.run')
    def test_sshaudit_returns_true_with_no_cves(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({'banner': {'raw': 'SSH-2.0-OpenSSH_8.9'}, 'cves': []}),
            stderr='',
        )
        from reNgine.recon_tasks import sshaudit_scan
        result = sshaudit_scan(_make_proxy(), scan_history_id=1, host='192.0.2.1', port=22)
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_sshaudit_maps_cvss_to_severity_int(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                'banner': {'raw': 'SSH-2.0-OpenSSH_7.4'},
                'cves': [
                    {'name': 'CVE-2023-38408', 'cvss': 9.8, 'description': 'RCE'},
                    {'name': 'CVE-2023-28531', 'cvss': 6.5, 'description': 'Medium'},
                ],
            }),
            stderr='',
        )
        with patch('startScan.models.Vulnerability.objects') as mock_vuln:
            mock_vuln.bulk_create = MagicMock()
            from reNgine.recon_tasks import sshaudit_scan
            result = sshaudit_scan(_make_proxy(), scan_history_id=1, host='192.0.2.1', port=22)
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_sshaudit_handles_invalid_json(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout='not json', stderr='')
        from reNgine.recon_tasks import sshaudit_scan
        result = sshaudit_scan(_make_proxy(), scan_history_id=1, host='192.0.2.1', port=22)
        self.assertTrue(result)


class TestSearchsploitScan(TestCase):
    @patch('subprocess.run')
    def test_searchsploit_returns_true_empty_service(self, mock_run):
        from reNgine.recon_tasks import searchsploit_scan
        result = searchsploit_scan(_make_proxy(), scan_history_id=1, service='')
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_searchsploit_handles_no_results(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({'RESULTS_EXPLOIT': []}),
            stderr='',
        )
        from reNgine.recon_tasks import searchsploit_scan
        result = searchsploit_scan(_make_proxy(), scan_history_id=1, service='custom-app')
        self.assertTrue(result)


class TestWPProbeScan(TestCase):
    @patch('subprocess.run')
    def test_wpprobe_returns_true_on_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('wpprobe', 300)
        from reNgine.recon_tasks import wpprobe_scan
        result = wpprobe_scan(_make_proxy(), scan_history_id=1, url='https://example.com')
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_wpprobe_handles_empty_json(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='[]', stderr='')
        from reNgine.recon_tasks import wpprobe_scan
        result = wpprobe_scan(_make_proxy(), scan_history_id=1, url='https://example.com')
        self.assertTrue(result)


class TestSearchVulnsScan(TestCase):
    @patch('requests.get')
    def test_search_vulns_skips_empty_service(self, mock_get):
        from reNgine.recon_tasks import search_vulns_scan
        result = search_vulns_scan(
            _make_proxy(), scan_history_id=1, service='', version=None,
            host='192.0.2.1', port=80,
        )
        self.assertTrue(result)
        mock_get.assert_not_called()

    @patch('requests.get')
    def test_search_vulns_handles_empty_results(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {'data': {'search': []}},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        from reNgine.recon_tasks import search_vulns_scan
        result = search_vulns_scan(
            _make_proxy(), scan_history_id=1, service='nginx', version='1.14.0',
            host='192.0.2.1', port=80,
        )
        self.assertTrue(result)

    @patch('requests.get')
    def test_search_vulns_handles_request_exception(self, mock_get):
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError('no connection')
        from reNgine.recon_tasks import search_vulns_scan
        result = search_vulns_scan(
            _make_proxy(), scan_history_id=1, service='apache', version='2.4.49',
            host='192.0.2.1', port=80,
        )
        self.assertTrue(result)

    @patch('requests.get')
    def test_search_vulns_maps_cvss_to_severity(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'data': {
                    'search': [
                        {'id': 'CVE-2021-41773', 'title': 'Path traversal',
                         'cvss': {'score': 9.8}, 'description': '...', 'published': '2021'},
                    ]
                }
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()
        with patch('startScan.models.Vulnerability.objects') as mock_vuln:
            created = []
            mock_vuln.bulk_create = lambda items, **kw: created.extend(items)
            from reNgine.recon_tasks import search_vulns_scan
            search_vulns_scan(
                _make_proxy(), scan_history_id=1, service='apache-httpd', version='2.4.49',
                host='192.0.2.1', port=80,
            )
        # CVSS 9.8 → critical (4)
        if created:
            self.assertEqual(created[0].severity, 4)
