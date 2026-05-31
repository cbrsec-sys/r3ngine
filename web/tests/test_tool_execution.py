import os
import json
import unittest
from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase
from django.utils import timezone

# Mocking Celery tasks and project imports
from reNgine.tasks import *
from reNgine.wpscan_tasks import *
from reNgine.vulnerability_tasks import *
from reNgine.osint_tasks import *
from startScan.models import *
from targetApp.models import *
from scanEngine.models import EngineType, OpSec, Proxy
from dashboard.models import AcunetixAPIKey, WpScanAPIKey

class ToolExecutionTest(TransactionTestCase):
    def setUp(self):
        self.domain_name = "defijn.io"
        self.domain = Domain.objects.create(name=self.domain_name)
        # Create an engine as it's required by ScanHistory
        self.engine = EngineType.objects.create(engine_name="Test Engine")
        
        # Create OpSec and Proxy records to avoid errors
        OpSec.objects.get_or_create(id=1)
        Proxy.objects.get_or_create(id=1)
        
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_status=1,
            start_scan_date=timezone.now(),
            scan_type=self.engine
        )
        self.results_dir = f"/tmp/rengine_results/{self.scan.id}"
        os.makedirs(self.results_dir, exist_ok=True)
        self.scan.results_dir = self.results_dir
        self.scan.save()
        
        self.subdomain = Subdomain.objects.create(
            name=self.domain_name,
            scan_history=self.scan,
            target_domain=self.domain
        )
        
        self.ctx = {
            'scan_history_id': self.scan.id,
            'domain_id': self.domain.id,
            'results_dir': self.results_dir,
            'yaml_configuration': {},
            'track': False
        }
        
        self.real_target = os.environ.get('TEST_REAL_TARGET', 'defijn.io')
        self.is_real_mode = os.environ.get('TEST_REAL_MODE', 'false').lower() == 'true'
        
        self.task = MagicMock()
        self.task.scan = self.scan
        self.task.scan_id = self.scan.id
        self.task.domain = self.domain
        self.task.yaml_configuration = self.ctx['yaml_configuration']
        self.task.activity_id = 1
        self.task.subscan = None
        self.task.subdomain = None
        self.task.starting_point_path = ""

    def test_wpscan_execution(self):
        print(f"\n[DEBUG] Starting WPScan test. Real mode: {self.is_real_mode}")
        if self.is_real_mode:
            res = wpscan_scan(self.task, urls=[f"http://{self.real_target}"], ctx=self.ctx)
            print(f"[DEBUG] WPScan real result: {res}")
        else:
            sample_file = "web/tests/sample_data/wpscan_sample.json"
            if not os.path.exists(sample_file):
                 sample_file = "tests/sample_data/wpscan_sample.json"
                
            output_file = f"{self.results_dir}/vulnerability/wpscan/{self.domain_name}_wpscan.json"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(sample_file, 'r') as f:
                with open(output_file, 'w') as out:
                    out.write(f.read())
            
            print(f"[DEBUG] Subdomains for scan: {Subdomain.objects.filter(scan_history=self.scan).count()}")
            
            # Patch in tasks module
            with patch('reNgine.tasks.stream_command') as mock_stream:
                res = wpscan_scan(self.task, urls=[f"http://{self.domain_name}"], ctx=self.ctx)
                print(f"[DEBUG] wpscan_scan result: {res}")
            
            vulns = Vulnerability.objects.filter(scan_history=self.scan, type='WordPress')
            print(f"[DEBUG] Vulnerabilities found: {vulns.count()}")
            self.assertTrue(vulns.exists())
            self.assertIn("WP Core Vuln", [v.name for v in vulns])

    def test_cpanel_execution(self):
        print(f"\n[DEBUG] Starting cPanel test. Real mode: {self.is_real_mode}")
        if self.is_real_mode:
            res = cpanel_scan(self.task, ctx=self.ctx)
            print(f"[DEBUG] cPanel real result: {res}")
        else:
            sample_file = "web/tests/sample_data/cpanel_sample.json"
            if not os.path.exists(sample_file):
                sample_file = "tests/sample_data/cpanel_sample.json"
                
            output_file = f"{self.results_dir}/vulnerability/cpanel/{self.domain_name}_cpanel.json"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(sample_file, 'r') as f:
                with open(output_file, 'w') as out:
                    out.write(f.read())
            
            # Patch in tasks module
            with patch('reNgine.tasks.stream_command') as mock_stream:
                res = cpanel_scan(self.task, ctx=self.ctx)
                print(f"[DEBUG] cpanel_scan result: {res}")
            
            vulns = Vulnerability.objects.filter(scan_history=self.scan, type='cPanel')
            print(f"[DEBUG] Vulnerabilities found: {vulns.count()}")
            self.assertTrue(vulns.exists())
            self.assertIn("cPanel User Exposure", [v.name for v in vulns])

    def test_maigret_execution(self):
        username = "scott"
        print(f"\n[DEBUG] Starting Maigret test. Real mode: {self.is_real_mode}")
        if self.is_real_mode:
            res = run_maigret(username, self.scan.id)
            print(f"[DEBUG] Maigret real result: {res}")
        else:
            sample_file = "web/tests/sample_data/maigret_sample.json"
            if not os.path.exists(sample_file):
                sample_file = "tests/sample_data/maigret_sample.json"
                
            output_file = f"{self.results_dir}/osint/maigret/{username}.json"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(sample_file, 'r') as f:
                with open(output_file, 'w') as out:
                    out.write(f.read())
            
            with patch('reNgine.osint_tasks.subprocess.run') as mock_run:
                res = run_maigret(username, self.scan.id)
                print(f"[DEBUG] run_maigret result: {res}")
            
            employee = Employee.objects.filter(name=username).first()
            self.assertIsNotNone(employee)
            self.assertIn('maigret', employee.metadata)
            self.assertEqual(len(employee.metadata['maigret']), 2)

    def test_trufflehog_execution(self):
        print(f"\n[DEBUG] Starting Trufflehog test.")
        if self.is_real_mode:
            pass
        else:
            # Mock JS endpoint
            ep = EndPoint.objects.create(
                scan_history=self.scan,
                target_domain=self.domain,
                http_url="http://defijn.io/app.js"
            )
            print(f"[DEBUG] Created EndPoint: {ep.http_url}")
            print(f"[DEBUG] EndPoint count for scan: {EndPoint.objects.filter(scan_history=self.scan).count()}")
            
            # Mock subprocess for Trufflehog
            sample_file = "web/tests/sample_data/trufflehog_sample.txt"
            if not os.path.exists(sample_file):
                sample_file = "tests/sample_data/trufflehog_sample.txt"
                
            with open(sample_file, 'rb') as f:
                mock_stdout = f.read()
            
            with patch('reNgine.tasks.subprocess.Popen') as mock_popen, \
                 patch('reNgine.tasks.requests.get') as mock_get:
                
                # Mock requests.get for JS download
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.text = "console.log('test');"
                mock_get.return_value = mock_resp
                
                process_mock = MagicMock()
                process_mock.communicate.return_value = (mock_stdout, b"")
                mock_popen.return_value = process_mock
                
                # Update ctx for trufflehog
                self.ctx['yaml_configuration'] = {'vulnerability_scan': {'trufflehog': True}}
                res = secret_scanning(self.task, config={'trufflehog': True}, ctx=self.ctx)
                print(f"[DEBUG] secret_scanning result: {res}")
            
            leaks = SecretLeak.objects.filter(scan_history=self.scan, tool_name='trufflehog')
            print(f"[DEBUG] Secret leaks found in DB for current scan: {leaks.count()}")
            # If leaks is 0, let's check all secret leaks
            if leaks.count() == 0:
                 all_leaks = SecretLeak.objects.all()
                 print(f"[DEBUG] TOTAL Secret leaks count in DB: {all_leaks.count()}")
                 for l in all_leaks:
                     print(f"  - {l.tool_name} | Scan ID: {l.scan_history.id} | Content: {l.match_content[:20]}...")
                     
            self.assertTrue(leaks.exists())
            self.assertEqual(leaks.count(), 2)

    def test_acunetix_execution(self):
        print(f"\n[DEBUG] Starting Acunetix test.")
        if self.is_real_mode:
            # Use real credentials provided by user
            AcunetixAPIKey.objects.update_or_create(
                id=1,
                defaults={
                    'server_url': "https://acunetix-instance:3443",
                    'api_key': "1986ad8c0a5b3df4d7028d5f3c06e936c09609203fb71403f82b9c499552f1186"
                }
            )
            print("[DEBUG] Updated Acunetix API Key with real credentials.")
            # We patch time.sleep to avoid waiting too long during polling
            with patch('reNgine.tasks.time.sleep', return_value=None):
                res = acunetix_scan(self.task, self.domain.id, self.scan.id, self.ctx)
                print(f"[DEBUG] Real Acunetix scan result: {res}")
        else:
            # Setup Acunetix API Key
            AcunetixAPIKey.objects.create(
                server_url="https://acunetix-instance:3443",
                api_key="test_key"
            )
            
            # Patch Acunetix and requests in reNgine.tasks
            with patch('reNgine.tasks.Acunetix') as mock_acunetix_cls, \
                 patch('reNgine.tasks.requests.get') as mock_requests_get:
                
                mock_acunetix = MagicMock()
                mock_acunetix_cls.return_value = mock_acunetix
                mock_acunetix.trigger_scan.return_value = True
                
                # Mock requests responses for target and scan status
                mock_targets_resp = MagicMock()
                mock_targets_resp.status_code = 200
                mock_targets_resp.json.return_value = {
                    'targets': [{'address': self.domain_name, 'target_id': 'test-target-id'}]
                }
                
                mock_scans_resp = MagicMock()
                mock_scans_resp.status_code = 200
                mock_scans_resp.json.return_value = {
                    'scans': [{'current_session': {'status': 'completed'}}]
                }
                
                mock_requests_get.side_effect = [mock_targets_resp, mock_scans_resp]
                
                res = acunetix_scan(self.task, self.domain.id, self.scan.id, self.ctx)
                print(f"[DEBUG] acunetix_scan result: {res}")
                
                mock_acunetix.start_scan.assert_called()

    def test_holehe_execution(self):
        email = "test@defijn.io"
        print(f"\n[DEBUG] Starting Holehe test.")
        if self.is_real_mode:
            res = run_holehe(email, self.scan.id)
            print(f"[DEBUG] Holehe real result: {res}")
        else:
            # holehe parsing is based on stdout lines
            with patch('reNgine.osint_tasks.subprocess.Popen') as mock_popen:
                process_mock = MagicMock()
                process_mock.communicate.return_value = ("[+] twitter\n[+] github\n", "")
                mock_popen.return_value = process_mock
                
                res = run_holehe(email, self.scan.id)
                print(f"[DEBUG] run_holehe result: {res}")
                
                email_obj = Email.objects.filter(address=email).first()
                self.assertIsNotNone(email_obj)
                self.assertIn('holehe', email_obj.metadata)
                self.assertIn('twitter', email_obj.metadata['holehe'])

    def test_enrich_identities_execution(self):
        email = "test.user@defijn.io"
        print(f"\n[DEBUG] Starting enrich_identities test.")
        if self.is_real_mode:
            pass
        else:
            with patch('reNgine.osint_tasks.subprocess.Popen') as mock_popen:
                process_mock = MagicMock()
                # Mock username-anarchy output (one username per line) and gosearch output
                process_mock.communicate.side_effect = [
                    ("testuser\ntest.user\ntuser\n", ""), # For username-anarchy
                    ("http://twitter.com/testuser\n", ""),   # For gosearch 1
                    ("http://twitter.com/testuser\n", ""),   # For gosearch 2
                    ("http://twitter.com/testuser\n", ""),   # For gosearch 3
                    ("http://twitter.com/testuser\n", "")    # For gosearch 4
                ]
                mock_popen.return_value = process_mock
                
                # Mock OsintStaging to avoid DB constraint failures if any
                res = enrich_identities_task(email, 'email', self.scan.id)
                print(f"[DEBUG] enrich_identities_task result: {res}")
                
                # Check that staging object was created
                staging = OsintStaging.objects.filter(scan_history=self.scan).first()
                self.assertIsNotNone(staging)
                self.assertEqual(staging.content, "http://twitter.com/testuser")
                self.assertEqual(staging.source, "gosearch")
