import os
import django
import json
import yaml
from unittest import TestCase
from unittest.mock import patch, MagicMock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import ScanHistory, EngineType, Subdomain, Vulnerability
from targetApp.models import Domain
from django.utils import timezone

class TestSubscanSeverityStability(TestCase):
    """
    Test suite to verify stabilizing changes made to:
    1. initiate_subscan celery task signature argument mapping.
    2. save_vulnerability centralized severity string conversion.
    3. parse_react2shell_results severity integer normalization.
    """

    def setUp(self):
        self.domain, _ = Domain.objects.get_or_create(name='stability.test.local')
        self.engine = EngineType.objects.create(
            engine_name='Subscan Stability Test Engine',
            yaml_configuration=yaml.dump({
                'subdomain_discovery': {},
                'port_scan': {},
                'vulnerability_scan': {
                    'enabled': True,
                    'run_apme': False
                },
                'fetch_url': {},
                'dir_file_fuzz': {}
            })
        )
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
            results_dir='/tmp/stability_tests',
            tasks=[]
        )
        self.subdomain = Subdomain.objects.create(
            name='target.stability.test.local',
            target_domain=self.domain,
            scan_history=self.scan,
            http_url='http://target.stability.test.local'
        )

    def tearDown(self):
        Vulnerability.objects.filter(scan_history=self.scan).delete()
        Subdomain.objects.filter(scan_history=self.scan).delete()
        self.scan.delete()
        self.engine.delete()
        self.domain.delete()

    @patch('reNgine.tasks.save_endpoint')
    @patch('reNgine.tasks.send_scan_notif')
    @patch('reNgine.tasks.chain')
    @patch('reNgine.tasks.report')
    @patch('reNgine.tasks.PluginOrchestrator.inject_tasks')
    def test_initiate_subscan_signature_mapping(self, mock_inject, mock_report, mock_chain, mock_send_notif, mock_save_endpoint):
        """
        Ensure initiate_subscan maps correct task arguments based on the expected 
        signature definitions (e.g. hosts for port_scan, urls for fetch_url/vulnerability_scan).
        """
        from reNgine.tasks import initiate_subscan
        
        # Mock endpoint response to prevent actual network crawler run
        mock_endpoint = MagicMock(is_alive=True)
        mock_endpoint.http_url = "http://target.stability.test.local"
        mock_endpoint.http_status = 200
        mock_endpoint.response_time = 0.1
        mock_endpoint.page_title = "Test"
        mock_endpoint.content_type = "text/html"
        mock_endpoint.content_length = 100
        mock_endpoint.techs.all.return_value = []
        mock_save_endpoint.return_value = (mock_endpoint, True)

        # Mock global tasks in reNgine
        from reNgine import tasks
        
        with patch.object(tasks.dir_file_fuzz, 'si') as mock_fuzz_si, \
             patch.object(tasks.port_scan, 'si') as mock_port_si, \
             patch.object(tasks.fetch_url, 'si') as mock_fetch_si, \
             patch.object(tasks.vulnerability_scan, 'si') as mock_vuln_si, \
             patch.object(tasks.wpscan_scan, 'si') as mock_wpscan_si, \
             patch.object(tasks.cpanel_scan, 'si') as mock_cpanel_si, \
             patch.object(tasks.correlate_vulnerabilities, 'si') as mock_correlate_si, \
             patch.object(tasks.calculate_risk_scores, 'si') as mock_risk_si:
            
            # Setup signature mock returns
            mock_fuzz_si.return_value = MagicMock(name='dir_file_fuzz_si')
            mock_port_si.return_value = MagicMock(name='port_scan_si')
            mock_fetch_si.return_value = MagicMock(name='fetch_url_si')
            mock_vuln_si.return_value = MagicMock(name='vulnerability_scan_si')
            mock_wpscan_si.return_value = MagicMock(name='wpscan_si')
            mock_cpanel_si.return_value = MagicMock(name='cpanel_si')
            mock_correlate_si.return_value = MagicMock(name='correlate_si')
            mock_risk_si.return_value = MagicMock(name='risk_si')
            
            # Mock Celery chain and delay
            mock_chain_obj = MagicMock()
            mock_chain.return_value = mock_chain_obj
            mock_chain_obj.on_error.return_value.delay.return_value = MagicMock(id='dummy_task_id')

            # 1. Test dir_file_fuzz (expects only ctx)
            initiate_subscan(
                scan_history_id=self.scan.id,
                subdomain_id=self.subdomain.id,
                engine_id=self.engine.id,
                scan_type='dir_file_fuzz'
            )
            mock_fuzz_si.assert_called_once()
            _, kwargs = mock_fuzz_si.call_args
            self.assertIn('ctx', kwargs)
            self.assertNotIn('host', kwargs)
            self.assertNotIn('hosts', kwargs)
            self.assertNotIn('urls', kwargs)

            # 2. Test port_scan (expects hosts list)
            initiate_subscan(
                scan_history_id=self.scan.id,
                subdomain_id=self.subdomain.id,
                engine_id=self.engine.id,
                scan_type='port_scan'
            )
            mock_port_si.assert_called_once()
            _, kwargs = mock_port_si.call_args
            self.assertIn('ctx', kwargs)
            self.assertEqual(kwargs.get('hosts'), [self.subdomain.name])
            self.assertNotIn('host', kwargs)
            self.assertNotIn('urls', kwargs)

            # 3. Test fetch_url (expects urls list)
            initiate_subscan(
                scan_history_id=self.scan.id,
                subdomain_id=self.subdomain.id,
                engine_id=self.engine.id,
                scan_type='fetch_url'
            )
            mock_fetch_si.assert_called_once()
            _, kwargs = mock_fetch_si.call_args
            self.assertIn('ctx', kwargs)
            self.assertEqual(kwargs.get('urls'), [self.subdomain.http_url])
            self.assertNotIn('host', kwargs)
            self.assertNotIn('hosts', kwargs)

            # 4. Test vulnerability_scan (expects urls list)
            initiate_subscan(
                scan_history_id=self.scan.id,
                subdomain_id=self.subdomain.id,
                engine_id=self.engine.id,
                scan_type='vulnerability_scan'
            )
            mock_vuln_si.assert_called_once()
            _, kwargs = mock_vuln_si.call_args
            self.assertIn('ctx', kwargs)
            self.assertEqual(kwargs.get('urls'), [self.subdomain.http_url])
            self.assertNotIn('host', kwargs)
            self.assertNotIn('hosts', kwargs)

    def test_save_vulnerability_severity_guard(self):
        """
        Verify that save_vulnerability converts string severities to correct integers,
        preventing ValueError database layer crashes during save operations.
        """
        from reNgine.common_func import save_vulnerability
        
        # Test distinct string/integer severity inputs and verify mapped integer outcomes
        test_cases = [
            ('info', 0),
            ('INFO', 0),
            ('low', 1),
            ('Low', 1),
            ('medium', 2),
            ('Medium', 2),
            ('high', 3),
            ('High', 3),
            ('critical', 4),
            ('CRITICAL', 4),
            ('unknown_or_invalid_string', 2),  # Should default to Medium (2)
            (3, 3),                            # Integer should pass through unchanged
            (1, 1)                             # Integer should pass through unchanged
        ]
        
        for input_severity, expected_int in test_cases:
            vuln_name = f"Test Severity Normalization - {input_severity}"
            
            save_vulnerability(
                target_domain=self.domain,
                scan_history=self.scan,
                http_url='http://target.stability.test.local',
                subdomain=self.subdomain,
                name=vuln_name,
                severity=input_severity,
                description=f"Testing severity conversion for {input_severity}",
                remediation="None",
                type="Test"
            )
            
            # Fetch from DB and verify correctness
            vuln = Vulnerability.objects.get(scan_history=self.scan, name=vuln_name)
            self.assertEqual(vuln.severity, expected_int)

    @patch('reNgine.vulnerability_tasks.logger')
    def test_parse_react2shell_results_severity(self, mock_logger):
        """
        Verify that parse_react2shell_results successfully parses severity strings and
        correctly invokes save_vulnerability with corresponding integer values.
        """
        from reNgine.vulnerability_tasks import parse_react2shell_results
        
        mock_task = MagicMock()
        mock_task.domain = self.domain
        mock_task.scan = self.scan
        
        # Define mock findings payload
        findings = [
            {
                'vulnerability': 'React Component Source Leak A',
                'severity': 'high',
                'details': 'Found source map leak A',
                'remediation': 'Fix build settings A'
            },
            {
                'vulnerability': 'React Component Source Leak B',
                'severity': 'CRITICAL',
                'details': 'Found source map leak B',
                'remediation': 'Fix build settings B'
            },
            {
                'vulnerability': 'React Component Source Leak C',
                'severity': 'info',
                'details': 'Found source map leak C',
                'remediation': 'Fix build settings C'
            }
        ]
        
        # Write to temporary file
        temp_file = '/tmp/react2shell_test_findings.json'
        os.makedirs(os.path.dirname(temp_file), exist_ok=True)
        with open(temp_file, 'w') as f:
            json.dump(findings, f)
            
        try:
            parse_react2shell_results(mock_task, temp_file, self.subdomain)
            
            # Fetch saved vulnerabilities and assert fields
            vuln_a = Vulnerability.objects.get(scan_history=self.scan, name='React Component Source Leak A')
            self.assertEqual(vuln_a.severity, 3)
            self.assertEqual(vuln_a.description, 'Found source map leak A')
            
            vuln_b = Vulnerability.objects.get(scan_history=self.scan, name='React Component Source Leak B')
            self.assertEqual(vuln_b.severity, 4)
            self.assertEqual(vuln_b.description, 'Found source map leak B')
            
            vuln_c = Vulnerability.objects.get(scan_history=self.scan, name='React Component Source Leak C')
            self.assertEqual(vuln_c.severity, 0)
            self.assertEqual(vuln_c.description, 'Found source map leak C')
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    @patch('reNgine.task_utils.Command')
    @patch('reNgine.task_utils.SOCConfiguration')
    def test_stream_command_watchdog_timeout(self, mock_soc_config, mock_command_model):
        """
        Verify that stream_command properly enforces a watchdog timeout,
        killing hung subprocesses using the background watchdog thread.
        """
        from reNgine.task_utils import stream_command
        import time

        # Mock SOCConfiguration
        mock_soc = MagicMock()
        mock_soc.enable_live_log_streaming = False
        mock_soc_config.objects.get_or_create.return_value = (mock_soc, False)

        # Mock Command database object
        mock_cmd_obj = MagicMock()
        mock_command_model.objects.create.return_value = mock_cmd_obj

        # Execute a command that would sleep indefinitely, but with a very small timeout (1s)
        start_time = time.time()
        lines = list(stream_command("sleep 10", timeout=1, shell=False))
        duration = time.time() - start_time

        # The command should have been killed by the watchdog after 1 second
        self.assertLess(duration, 4.0) # Allow slight buffer for thread scheduling
        # Also confirm the Command database object was updated with a return code indicating termination/killed status
        mock_cmd_obj.save.assert_called()
