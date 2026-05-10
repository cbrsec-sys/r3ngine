import os
import django
from unittest import TestCase
from unittest.mock import patch, MagicMock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from reNgine.tasks import initiate_scan
from startScan.models import ScanHistory, EngineType
from targetApp.models import Domain
from django.utils import timezone
import yaml

class TestPipelineOrchestration(TestCase):
    def setUp(self):
        self.domain, _ = Domain.objects.get_or_create(name='test.local')
        self.engine = EngineType.objects.create(
            engine_name='Full Test Engine',
            yaml_configuration=yaml.dump({
                'subdomain_discovery': {},
                'osint': {},
                'spiderfoot_scan': {},
                'firewall_vpn_scan': {},
                'http_crawl': {},
                'port_scan': {},
                'screenshot': {},
                'dir_file_fuzz': {},
                'fetch_url': {},
                'web_api_discovery': {},
                'waf_detection': {},
                'vulnerability_scan': {},
                'brute_force_scan': {},
                'stress_test': {'enabled': True}
            })
        )
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
            tasks=[]
        )

    def tearDown(self):
        self.scan.delete()
        self.engine.delete()
        self.domain.delete()

    @patch('reNgine.tasks.chain')
    @patch('reNgine.tasks.group')
    @patch('reNgine.tasks.PluginOrchestrator.inject_tasks')
    @patch('reNgine.tasks.send_scan_notif')
    def test_pipeline_tier_construction(self, mock_notif, mock_inject, mock_group, mock_chain):
        # Setup mocks to return themselves so we can track them
        mock_inject.side_effect = lambda name, si, ctx: si if si else MagicMock(name=f"Plugin_{name}")
        mock_group.side_effect = lambda tasks: MagicMock(name="Group", tasks=tasks)
        
        # We need to mock the .si() methods of all tasks used in initiate_scan
        with patch('reNgine.tasks.subdomain_discovery.si') as m_sub, \
             patch('reNgine.tasks.osint.si') as m_osint, \
             patch('reNgine.tasks.spiderfoot_scan.si') as m_sf, \
             patch('reNgine.tasks.firewall_vpn_scan.si') as m_fw, \
             patch('reNgine.tasks.http_crawl.si') as m_crawl, \
             patch('reNgine.tasks.port_scan.si') as m_port, \
             patch('reNgine.tasks.screenshot.si') as m_shot, \
             patch('reNgine.tasks.dir_file_fuzz.si') as m_fuzz, \
             patch('reNgine.tasks.fetch_url.si') as m_fetch, \
             patch('reNgine.tasks.web_api_discovery.si') as m_api, \
             patch('reNgine.tasks.waf_detection.si') as m_waf, \
             patch('reNgine.tasks.waf_bypass.si') as m_bypass, \
             patch('reNgine.tasks.vulnerability_scan.si') as m_vuln, \
             patch('reNgine.tasks.brute_force_scan.si') as m_brute, \
             patch('reNgine.tasks.correlate_vulnerabilities.si') as m_corr, \
             patch('reNgine.tasks.calculate_risk_scores.si') as m_risk, \
             patch('reNgine.tasks.generate_impact_assessment.si') as m_ai, \
             patch('reNgine.tasks.run_stress_testing.si') as m_stress, \
             patch('reNgine.tasks.run_apme.si') as m_apme:
             
            # Set descriptive names for the signatures
            m_sub.return_value = MagicMock(name='subdomain_discovery_si')
            m_osint.return_value = MagicMock(name='osint_si')
            m_sf.return_value = MagicMock(name='spiderfoot_scan_si')
            m_fw.return_value = MagicMock(name='firewall_vpn_scan_si')
            m_crawl.return_value = MagicMock(name='http_crawl_si')
            m_port.return_value = MagicMock(name='port_scan_si')
            m_shot.return_value = MagicMock(name='screenshot_si')
            m_fuzz.return_value = MagicMock(name='dir_file_fuzz_si')
            m_fetch.return_value = MagicMock(name='fetch_url_si')
            m_api.return_value = MagicMock(name='web_api_discovery_si')
            m_waf.return_value = MagicMock(name='waf_detection_si')
            m_bypass.return_value = MagicMock(name='waf_bypass_si')
            m_vuln.return_value = MagicMock(name='vulnerability_scan_si')
            m_brute.return_value = MagicMock(name='brute_force_scan_si')
            m_corr.return_value = MagicMock(name='correlate_vulnerabilities_si')
            m_risk.return_value = MagicMock(name='calculate_risk_scores_si')
            m_ai.return_value = MagicMock(name='generate_impact_assessment_si')
            m_stress.return_value = MagicMock(name='run_stress_testing_si')
            m_apme.return_value = MagicMock(name='run_apme_si')
                                    
            initiate_scan(
                scan_history_id=self.scan.id,
                domain_id=self.domain.id,
                engine_id=self.engine.id
            )

        # Verify chain was called
        self.assertTrue(mock_chain.called)
        
        # We want to find the chain call that builds the 'workflow'
        # initiate_scan calls chain(*workflow_steps)
        workflow_steps = None
        for call in mock_chain.call_args_list:
            if len(call.args) > 1 and any('Plugin' in str(s) for s in call.args):
                workflow_steps = call.args
                break
        
        if not workflow_steps:
            # Fallback to the last call if we can't find it easily
            workflow_steps = mock_chain.call_args_list[0].args

        step_names = [str(s) for s in workflow_steps]

        # The structure is now: [Tier_1_Start, Group(Background + MainBranch), Tier_7_End]
        self.assertTrue(any('Plugin_Tier_1_Start' in s for s in step_names))
        
        # Verify the Group contains the background tasks
        t1_group_tasks = None
        for call in mock_group.call_args_list:
            tasks_str = [str(t) for t in call.args[0]]
            # Search for background tasks only (osint or spiderfoot)
            if any(x in t.lower() for t in tasks_str for x in ['osint', 'spiderfoot']):
                t1_group_tasks = tasks_str
                break
        
        self.assertIsNotNone(t1_group_tasks, "Could not find Tier 1 background group")
        
        # Background tasks should be in the group
        self.assertTrue(any('osint' in t.lower() for t in t1_group_tasks))
        self.assertTrue(any('spiderfoot' in t.lower() for t in t1_group_tasks))
        
        # The main branch should also be in the group
        self.assertTrue(any('chain' in t.lower() for t in t1_group_tasks))

    @patch('reNgine.tasks.chain')
    @patch('reNgine.tasks.group')
    @patch('reNgine.tasks.PluginOrchestrator.inject_tasks')
    @patch('reNgine.tasks.send_scan_notif')
    def test_configuration_extraction(self, mock_notif, mock_inject, mock_group, mock_chain):
        # Update engine with specific API discovery config
        self.engine.yaml_configuration = yaml.dump({
            'web_api_discovery': {
                'uses_tools': ['kiterunner', 'arjun'],
                'kr_wordlist': 'custom-wordlist.kr'
            }
        })
        self.engine.save()

        with patch('reNgine.tasks.web_api_discovery.si') as m_api:
            initiate_scan(
                scan_history_id=self.scan.id,
                domain_id=self.domain.id,
                engine_id=self.engine.id
            )
            
            # Check the context passed to any task
            self.assertTrue(m_api.called)
            args, kwargs = m_api.call_args
            ctx = kwargs.get('ctx')
            self.assertIsNotNone(ctx)
            self.assertEqual(ctx.get('api_discovery_tools'), ['kiterunner', 'arjun'])
            self.assertEqual(ctx.get('kr_wordlist'), 'custom-wordlist.kr')

    @patch('reNgine.tasks.chain')
    @patch('reNgine.tasks.report')
    @patch('reNgine.tasks.send_scan_notif')
    @patch('reNgine.tasks.save_endpoint')
    def test_initiate_subscan_extraction(self, mock_save, mock_notif, mock_report, mock_chain):
        from reNgine.tasks import initiate_subscan
        from startScan.models import Subdomain
        
        subdomain = Subdomain.objects.create(name='sub.test.local', target_domain=self.domain, scan_history=self.scan)
        
        self.engine.yaml_configuration = yaml.dump({
            'web_api_discovery': {
                'uses_tools': ['kiterunner', 'arjun'],
                'kr_wordlist': 'custom-wordlist.kr'
            }
        })
        self.engine.save()
        
        mock_method = MagicMock()
        # Mock .si() call
        mock_sig = MagicMock()
        mock_method.si.return_value = mock_sig
        
        mock_endpoint = MagicMock(is_alive=True)
        mock_endpoint.http_url = "http://sub.test.local"
        mock_endpoint.http_status = 200
        mock_endpoint.response_time = 0.1
        mock_endpoint.page_title = "Test"
        mock_endpoint.content_type = "text/html"
        mock_endpoint.content_length = 100
        mock_endpoint.techs.all.return_value = []
        
        mock_save.return_value = (mock_endpoint, True)

        # Mock chain and delay
        mock_chain_obj = MagicMock()
        mock_chain.return_value = mock_chain_obj
        mock_chain_obj.on_error.return_value.delay.return_value = MagicMock(id='test_task_id')

        with patch.dict('reNgine.tasks.__dict__', {'web_api_discovery': mock_method}):
            initiate_subscan(
                scan_history_id=self.scan.id,
                subdomain_id=subdomain.id,
                engine_id=self.engine.id,
                scan_type='web_api_discovery'
            )
        
        # Check if the method's .si() was called with the correct ctx
        self.assertTrue(mock_method.si.called)
        args, kwargs = mock_method.si.call_args
        ctx = kwargs.get('ctx')
        self.assertEqual(ctx.get('api_discovery_tools'), ['kiterunner', 'arjun'])
        self.assertEqual(ctx.get('kr_wordlist'), 'custom-wordlist.kr')
        
        subdomain.delete()
