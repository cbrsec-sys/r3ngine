from django.test import TestCase
from unittest.mock import MagicMock, patch


class VigoliumDefinitionsTest(TestCase):
    def test_vigolium_constants_defined(self):
        from reNgine.definitions import (
            RUN_VIGOLIUM,
            RUN_VIGOLIUM_DISCOVERY,
            RUN_VIGOLIUM_ANALYSIS,
            VIGOLIUM,
            VIGOLIUM_STRATEGY,
            VIGOLIUM_CONCURRENCY,
            VIGOLIUM_RATE_LIMIT,
            VIGOLIUM_TIMEOUT,
            VIGOLIUM_MODULES,
            VIGOLIUM_SEVERITY_FILTER,
            VIGOLIUM_DEFAULT_CONFIG,
            VIGOLIUM_DEFAULT_DISCOVERY_CONFIG,
            VIGOLIUM_DEFAULT_ANALYSIS_CONFIG,
        )
        self.assertEqual(RUN_VIGOLIUM, 'run_vigolium')
        self.assertEqual(RUN_VIGOLIUM_DISCOVERY, 'run_vigolium_discovery')
        self.assertEqual(RUN_VIGOLIUM_ANALYSIS, 'run_vigolium_analysis')
        self.assertEqual(VIGOLIUM, 'vigolium')
        self.assertEqual(VIGOLIUM_STRATEGY, 'strategy')
        self.assertEqual(VIGOLIUM_CONCURRENCY, 'concurrency')
        self.assertEqual(VIGOLIUM_RATE_LIMIT, 'rate_limit')
        self.assertEqual(VIGOLIUM_TIMEOUT, 'timeout')
        self.assertEqual(VIGOLIUM_MODULES, 'modules')
        self.assertEqual(VIGOLIUM_SEVERITY_FILTER, 'severity_filter')
        self.assertIn('run_vigolium', VIGOLIUM_DEFAULT_CONFIG)
        self.assertTrue(VIGOLIUM_DEFAULT_CONFIG['run_vigolium'])
        self.assertIn('run_vigolium_discovery', VIGOLIUM_DEFAULT_DISCOVERY_CONFIG)
        self.assertTrue(VIGOLIUM_DEFAULT_DISCOVERY_CONFIG['run_vigolium_discovery'])
        self.assertIn('run_vigolium_analysis', VIGOLIUM_DEFAULT_ANALYSIS_CONFIG)
        self.assertTrue(VIGOLIUM_DEFAULT_ANALYSIS_CONFIG['run_vigolium_analysis'])


class VigoliumParserTest(TestCase):
    def _make_task(self):
        task = MagicMock()
        task.scan_id = 1
        task.activity_id = 1
        task.domain_id = 1
        task.scan = MagicMock()
        task.scan.results_dir = '/tmp/test_scan'
        task.domain = MagicMock()
        task.domain.id = 1
        task.subscan = None
        task.subdomain = None
        task.yaml_configuration = {
            'vulnerability_scan': {
                'run_vigolium': True,
                'vigolium': {'strategy': 'balanced', 'concurrency': 50},
            },
            'vigolium_discovery': {'run_vigolium_discovery': True},
            'vigolium_analysis': {'run_vigolium_analysis': True},
        }
        return task

    def test_parse_finding_saves_vulnerability(self):
        """parse_vigolium_finding maps confirmed JSONL fields to save_vulnerability."""
        from reNgine.vigolium_tasks import parse_vigolium_finding

        # Real schema from live vigolium output
        finding_data = {
            'url': 'https://www.defijn.io/',
            'hostname': 'www.defijn.io',
            'module_id': 'xss-reflected',
            'module_name': 'Reflected XSS',
            'module_type': 'active',
            'finding_source': 'dynamic-assessment',
            'module_short': 'Detects reflected XSS via parameter injection',
            'description': 'User input is reflected unescaped in the response.',
            'severity': 'high',
            'confidence': 'firm',
            'status': 'triaged',
            'cvss_score': 6.1,
            'matched_at': ['https://www.defijn.io/search?q=test'],
            'extracted_results': ['<script>alert(1)</script>'],
            'tags': ['xss', 'injection'],
            'request': 'GET /search?q=test HTTP/1.1\nHost: www.defijn.io\n',
            'response': '',
            'finding_hash': 'abc123',
            'found_at': '2026-05-28T07:36:53Z',
        }
        task = self._make_task()
        subdomain = MagicMock()
        subdomain.name = 'www.defijn.io'

        with patch('reNgine.vigolium_tasks.save_vulnerability') as mock_save:
            parse_vigolium_finding(task, finding_data, subdomain)
            mock_save.assert_called_once()
            kwargs = mock_save.call_args[1]
            self.assertEqual(kwargs['name'], 'Reflected XSS')
            self.assertEqual(kwargs['severity'], 3)   # 'high' → 3
            self.assertEqual(kwargs['type'], 'Vigolium')
            self.assertEqual(kwargs['template_id'], 'xss-reflected')
            self.assertEqual(kwargs['http_url'], 'https://www.defijn.io/search?q=test')
            self.assertEqual(kwargs['description'], 'User input is reflected unescaped in the response.')

    def test_parse_finding_uses_url_when_matched_at_empty(self):
        """parse_vigolium_finding falls back to data.url when matched_at is empty."""
        from reNgine.vigolium_tasks import parse_vigolium_finding

        finding_data = {
            'url': 'https://www.defijn.io/',
            'hostname': 'www.defijn.io',
            'module_id': 'headers-missing',
            'module_name': 'Security Headers Missing',
            'severity': 'info',
            'description': 'Missing security headers.',
            'matched_at': [],
            'tags': None,
        }
        task = self._make_task()
        subdomain = MagicMock()
        with patch('reNgine.vigolium_tasks.save_vulnerability') as mock_save:
            parse_vigolium_finding(task, finding_data, subdomain)
            mock_save.assert_called_once()
            kwargs = mock_save.call_args[1]
            self.assertEqual(kwargs['http_url'], 'https://www.defijn.io/')
            self.assertEqual(kwargs['severity'], 0)  # 'info' → 0

    def test_parse_finding_skips_missing_name(self):
        """parse_vigolium_finding skips records with no module_name."""
        from reNgine.vigolium_tasks import parse_vigolium_finding

        task = self._make_task()
        subdomain = MagicMock()
        with patch('reNgine.vigolium_tasks.save_vulnerability') as mock_save:
            parse_vigolium_finding(task, {'severity': 'high'}, subdomain)
            mock_save.assert_not_called()

    def test_parse_http_record_saves_endpoint(self):
        """parse_vigolium_http_record saves a discovered URL as an EndPoint."""
        from reNgine.vigolium_tasks import parse_vigolium_http_record

        record_data = {
            'url': 'https://www.defijn.io/login',
            'hostname': 'www.defijn.io',
            'method': 'GET',
            'status_code': 200,
        }
        task = self._make_task()
        with patch('reNgine.vigolium_tasks.save_endpoint') as mock_save:
            parse_vigolium_http_record(task, record_data)
            mock_save.assert_called_once()
            kwargs = mock_save.call_args[1]
            self.assertEqual(kwargs['http_url'], 'https://www.defijn.io/login')

    def test_parse_http_record_skips_missing_url(self):
        """parse_vigolium_http_record skips records with no url field."""
        from reNgine.vigolium_tasks import parse_vigolium_http_record

        task = self._make_task()
        with patch('reNgine.vigolium_tasks.save_endpoint') as mock_save:
            parse_vigolium_http_record(task, {'method': 'GET'})
            mock_save.assert_not_called()


class VigoliumTaskGatingTest(TestCase):
    def _make_task(self, vuln_enabled=True, discovery_enabled=True, analysis_enabled=True):
        task = MagicMock()
        task.scan_id = 1
        task.activity_id = 1
        task.domain_id = 1
        task.scan = MagicMock()
        task.scan.results_dir = '/tmp/test_scan'
        task.scan.domain = MagicMock()
        task.scan.domain.name = 'example.com'
        task.domain = MagicMock()
        task.subscan = None
        task.subdomain = None
        task.yaml_configuration = {
            'vulnerability_scan': {
                'run_vigolium': vuln_enabled,
                'vigolium': {'strategy': 'balanced', 'concurrency': 50, 'rate_limit': 100, 'timeout': '15s'},
            },
            'vigolium_discovery': {'run_vigolium_discovery': discovery_enabled},
            'vigolium_analysis': {'run_vigolium_analysis': analysis_enabled},
        }
        return task

    def test_vigolium_scan_skips_when_disabled(self):
        from reNgine.vigolium_tasks import vigolium_scan
        task = self._make_task(vuln_enabled=False)
        with patch('reNgine.vigolium_tasks._run_vigolium_phase') as mock_run:
            vigolium_scan(task)
            mock_run.assert_not_called()

    def test_vigolium_discovery_skips_when_disabled(self):
        from reNgine.vigolium_tasks import vigolium_discovery
        task = self._make_task(discovery_enabled=False)
        with patch('reNgine.vigolium_tasks._run_vigolium_phase') as mock_run:
            vigolium_discovery(task)
            mock_run.assert_not_called()

    def test_vigolium_analysis_skips_when_disabled(self):
        from reNgine.vigolium_tasks import vigolium_analysis
        task = self._make_task(analysis_enabled=False)
        with patch('reNgine.vigolium_tasks._run_vigolium_phase') as mock_run:
            vigolium_analysis(task)
            mock_run.assert_not_called()

    def test_vigolium_scan_calls_phase_runner(self):
        from reNgine.vigolium_tasks import vigolium_scan
        task = self._make_task(vuln_enabled=True)
        with patch('reNgine.vigolium_tasks._run_vigolium_phase') as mock_run, \
             patch('os.makedirs'), \
             patch('reNgine.vigolium_tasks.Subdomain'):
            vigolium_scan(task, urls=['https://example.com'])
            mock_run.assert_called_once()
            # Verify the command includes the correct phases
            call_args = mock_run.call_args
            cmd = call_args[0][1]
            self.assertIn('--only known-issue-scan,dynamic-assessment', cmd)
            self.assertIn('--stateless', cmd)
            self.assertIn('--skip-dependency-check', cmd)
            self.assertIn('--omit-response', cmd)
