import os
import django
from unittest import TestCase
from unittest.mock import patch, MagicMock, AsyncMock

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import ScanHistory, EngineType, SubScan, Subdomain
from targetApp.models import Domain
from django.utils import timezone
import yaml

class TestTemporalOrchestration(TestCase):
    """Integration and unit tests for the Temporal workflow initiation handlers."""

    def setUp(self):
        """Set up test targets, scan engines, and scan history records in the DB."""
        self.domain, _ = Domain.objects.get_or_create(name='temporal-test.local')
        self.engine = EngineType.objects.create(
            engine_name='Temporal Test Engine',
            yaml_configuration=yaml.dump({
                'enable_http_crawl': True,
                'subdomain_discovery': {},
                'port_scan': {},
                'fetch_url': {},
                'web_api_discovery': {
                    'uses_tools': ['kiterunner'],
                    'kr_wordlist': 'routes-small.kite'
                }
            })
        )
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
            tasks=[]
        )

    def tearDown(self):
        """Clean up all created database models."""
        from startScan.models import ScanActivity, Subdomain, SubScan
        ScanActivity.objects.filter(scan_of=self.scan).delete()
        SubScan.objects.filter(scan_history=self.scan).delete()
        Subdomain.objects.filter(scan_history=self.scan).delete()
        self.scan.delete()
        self.engine.delete()
        self.domain.delete()

    @patch('reNgine.temporal_client.TemporalClientProvider.get_client', new_callable=AsyncMock)
    @patch('reNgine.tasks.save_endpoint')
    @patch('reNgine.tasks.send_scan_notif')
    def test_initiate_scan_temporal(self, mock_send_notif, mock_save_endpoint, mock_get_client):
        """Test that initiate_scan_temporal correctly sets up scan history and starts the MasterScanWorkflow."""
        from reNgine.tasks import initiate_scan_temporal

        # Mock Temporal Client and Workflow Handle
        mock_handle = MagicMock()
        mock_handle.id = "mock-scan-workflow-id"
        mock_client = AsyncMock()
        mock_client.start_workflow.return_value = mock_handle
        mock_get_client.return_value = mock_client

        # Mock Endpoint save
        mock_endpoint = MagicMock(is_alive=True)
        mock_endpoint.http_url = "http://temporal-test.local"
        mock_endpoint.http_status = 200
        mock_endpoint.response_time = 0.5
        mock_endpoint.page_title = "Temporal Test"
        mock_endpoint.content_type = "text/html"
        mock_endpoint.content_length = 1234
        mock_endpoint.techs.all.return_value = []
        mock_save_endpoint.return_value = (mock_endpoint, True)

        # Trigger temporal scan initiation
        result = initiate_scan_temporal(
            scan_history_id=self.scan.id,
            domain_id=self.domain.id,
            engine_id=self.engine.id
        )

        # Verify function output
        self.assertTrue(result['success'])
        self.assertEqual(result['workflow_id'], 'mock-scan-workflow-id')

        # Verify start_workflow was called with correct parameters
        mock_client.start_workflow.assert_called_once()
        args, kwargs = mock_client.start_workflow.call_args
        self.assertEqual(args[0], "MasterScanWorkflow")
        self.assertEqual(kwargs['task_queue'], "python-orchestrator-queue")
        
        # Verify the context dictionary
        temporal_ctx = args[1]
        self.assertEqual(temporal_ctx['scan_history_id'], self.scan.id)
        self.assertEqual(temporal_ctx['domain_id'], self.domain.id)
        self.assertEqual(temporal_ctx['engine_id'], self.engine.id)

    @patch('reNgine.temporal_client.TemporalClientProvider.get_client', new_callable=AsyncMock)
    @patch('reNgine.tasks.save_endpoint')
    @patch('reNgine.tasks.send_scan_notif')
    def test_initiate_subscan_temporal(self, mock_send_notif, mock_save_endpoint, mock_get_client):
        """Test that initiate_subscan_temporal sets up subscan record and triggers SubScanWorkflow on Temporal."""
        from reNgine.tasks import initiate_subscan_temporal

        # Setup subdomain
        subdomain = Subdomain.objects.create(
            name='sub.temporal-test.local',
            target_domain=self.domain,
            scan_history=self.scan
        )

        # Mock Temporal Client and Workflow Handle
        mock_handle = MagicMock()
        mock_handle.id = "mock-subscan-workflow-id"
        mock_client = AsyncMock()
        mock_client.start_workflow.return_value = mock_handle
        mock_get_client.return_value = mock_client

        # Mock Endpoint save
        mock_endpoint = MagicMock(is_alive=True)
        mock_endpoint.http_url = "http://sub.temporal-test.local"
        mock_endpoint.http_status = 200
        mock_endpoint.response_time = 0.5
        mock_endpoint.page_title = "Temporal Subscan Test"
        mock_endpoint.content_type = "text/html"
        mock_endpoint.content_length = 5678
        mock_endpoint.techs.all.return_value = []
        mock_save_endpoint.return_value = (mock_endpoint, True)

        # Trigger subscan initiation
        result = initiate_subscan_temporal(
            scan_history_id=self.scan.id,
            subdomain_id=subdomain.id,
            engine_id=self.engine.id,
            scan_type='port_scan'
        )

        # Verify function output
        self.assertTrue(result['success'])
        self.assertEqual(result['workflow_id'], 'mock-subscan-workflow-id')

        # Verify start_workflow parameters
        mock_client.start_workflow.assert_called_once()
        args, kwargs = mock_client.start_workflow.call_args
        self.assertEqual(args[0], "SubScanWorkflow")
        self.assertEqual(kwargs['task_queue'], "python-orchestrator-queue")
        
        # Verify arguments passed to SubScanWorkflow
        workflow_args = kwargs['args']
        self.assertEqual(len(workflow_args), 2)
        temporal_ctx, scan_type = workflow_args
        self.assertEqual(scan_type, 'port_scan')

        # Verify SubScan DB entry has correct status and workflow ID stored in workflow_ids
        subscan = SubScan.objects.filter(subdomain=subdomain).first()
        self.assertIsNotNone(subscan)
        self.assertEqual(temporal_ctx['subscan_id'], subscan.id)
        self.assertEqual(temporal_ctx['subdomain_id'], subdomain.id)
        self.assertEqual(subscan.workflow_ids, ['mock-subscan-workflow-id'])
