from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from startScan.models import ScanHistory
from targetApp.models import Domain
from scanEngine.models import EngineType
from django.contrib.auth.models import User
from rest_framework.test import APIClient


class TestExtractAuthForURLActivity(TestCase):

    def setUp(self):
        self.domain = Domain.objects.create(name='test.example.com')
        self.engine = EngineType.objects.create(
            engine_name='test-engine-auth-extract',
            yaml_configuration='{}',
        )
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            scan_status=0,
            start_scan_date=timezone.now(),
        )

    @patch('reNgine.temporal_activities._fetch_with_proxy_retry')
    @patch('reNgine.temporal_activities._extract_login_forms')
    @patch('reNgine.temporal_activities.get_proxy_list', return_value=[])
    @patch('reNgine.temporal_activities.get_random_proxy', return_value=None)
    def test_extract_auth_saves_candidates(
        self, mock_rand_proxy, mock_proxy_list, mock_extract_forms, mock_fetch
    ):
        mock_response = MagicMock()
        mock_response.text = '<html></html>'
        mock_fetch.return_value = (mock_response, None)
        mock_extract_forms.return_value = [{
            'action': 'http://example.com/login',
            'method': 'POST',
            'user_field': 'username',
            'pass_field': 'password',
            'hidden_fields': {},
            'all_fields': ['username', 'password'],
        }]

        from reNgine.temporal_activities import extract_auth_for_url_activity
        result = extract_auth_for_url_activity({
            'url': 'http://example.com/login',
            'scan_id': self.scan.id,
        })

        self.assertEqual(result['found'], 1)

    @patch('reNgine.temporal_activities._fetch_with_proxy_retry')
    @patch('reNgine.temporal_activities.get_proxy_list', return_value=[])
    @patch('reNgine.temporal_activities.get_random_proxy', return_value=None)
    def test_extract_auth_no_forms_returns_zero(
        self, mock_rand_proxy, mock_proxy_list, mock_fetch
    ):
        mock_response = MagicMock()
        mock_response.text = '<html><body>No forms here</body></html>'
        mock_fetch.return_value = (mock_response, None)

        from reNgine.temporal_activities import extract_auth_for_url_activity
        with patch('reNgine.temporal_activities._extract_login_forms', return_value=[]):
            result = extract_auth_for_url_activity({
                'url': 'http://example.com/page',
                'scan_id': self.scan.id,
            })

        self.assertEqual(result['found'], 0)

    @patch('reNgine.temporal_activities._fetch_with_proxy_retry',
           side_effect=Exception("connection refused"))
    @patch('reNgine.temporal_activities.get_proxy_list', return_value=[])
    @patch('reNgine.temporal_activities.get_random_proxy', return_value=None)
    def test_extract_auth_fetch_failure_raises(
        self, mock_rand_proxy, mock_proxy_list, mock_fetch
    ):
        from reNgine.temporal_activities import extract_auth_for_url_activity
        with self.assertRaises(Exception):
            extract_auth_for_url_activity({
                'url': 'http://example.com/login',
                'scan_id': self.scan.id,
            })


class TestDirectoryFileDispatchView(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('dispatchuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('api.views.run_and_close')
    @patch('api.views.TemporalClientProvider')
    def test_dispatch_scan_vuln_returns_dispatched(self, mock_tc, mock_run):
        mock_run.return_value = 'wf-test-123'
        response = self.client.post('/api/action/directory-file/dispatch/', {
            'url': 'http://example.com/admin/',
            'action': 'scan_vuln',
            'scan_id': 1,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'dispatched')
        self.assertIn('workflow_id', response.data)

    @patch('api.views.run_and_close')
    @patch('api.views.TemporalClientProvider')
    def test_dispatch_extract_auth_returns_dispatched(self, mock_tc, mock_run):
        mock_run.return_value = 'wf-auth-123'
        response = self.client.post('/api/action/directory-file/dispatch/', {
            'url': 'http://example.com/login.php',
            'action': 'extract_auth',
            'scan_id': 1,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'dispatched')

    def test_dispatch_unknown_action_returns_400(self):
        response = self.client.post('/api/action/directory-file/dispatch/', {
            'url': 'http://example.com/',
            'action': 'do_something_invalid',
            'scan_id': 1,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_dispatch_missing_fields_returns_400(self):
        response = self.client.post('/api/action/directory-file/dispatch/', {
            'url': 'http://example.com/',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_dispatch_brute_test_without_plugin_returns_403(self):
        response = self.client.post('/api/action/directory-file/dispatch/', {
            'url': 'http://example.com/login',
            'action': 'brute_test',
            'scan_id': 1,
        }, format='json')
        self.assertEqual(response.status_code, 403)

    @patch('api.views.run_and_close')
    @patch('api.views.TemporalClientProvider')
    def test_dispatch_brute_test_with_plugin_enabled(self, mock_tc, mock_run):
        from plugins.models import Plugin
        Plugin.objects.create(
            name='Credential Intelligence',
            slug='credential_intelligence',
            version='1.4.0',
            is_enabled=True,
            anchor_step='web_api_discovery',
        )
        mock_run.return_value = 'wf-brute-123'
        response = self.client.post('/api/action/directory-file/dispatch/', {
            'url': 'http://example.com/login',
            'action': 'brute_test',
            'scan_id': 1,
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'dispatched')

    def test_dispatch_requires_authentication(self):
        unauthenticated = APIClient()
        response = unauthenticated.post('/api/action/directory-file/dispatch/', {
            'url': 'http://example.com/',
            'action': 'scan_vuln',
            'scan_id': 1,
        }, format='json')
        self.assertIn(response.status_code, [401, 403])
