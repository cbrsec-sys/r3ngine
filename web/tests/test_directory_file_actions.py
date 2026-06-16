from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
from startScan.models import ScanHistory
from targetApp.models import Domain
from scanEngine.models import EngineType


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
