import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()


class TestLaunchADAssessmentEndpoint(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='ad_test_user_ph13', password='testpass', is_staff=True
        )

    def tearDown(self):
        self.user.delete()

    def test_view_has_correct_permission(self):
        from api.views import LaunchADAssessmentFromSubdomain
        from api.permissions import HasPermission
        from reNgine.definitions import PERM_INITATE_SCANS_SUBSCANS
        self.assertIn(HasPermission, LaunchADAssessmentFromSubdomain.permission_classes)
        self.assertEqual(
            LaunchADAssessmentFromSubdomain.permission_required,
            PERM_INITATE_SCANS_SUBSCANS,
        )

    def test_missing_subdomain_id_returns_400(self):
        from api.views import LaunchADAssessmentFromSubdomain
        req = RequestFactory().post(
            '/api/action/ad-assessment/from-subdomain/',
            data={},
            content_type='application/json',
        )
        req.user = self.user
        view = LaunchADAssessmentFromSubdomain.as_view()
        # Bypass permission check for unit test
        with patch.object(LaunchADAssessmentFromSubdomain, 'permission_classes', []):
            response = view(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_plugin_not_installed_returns_400(self):
        from api.views import LaunchADAssessmentFromSubdomain
        from startScan.models import Subdomain
        from unittest.mock import MagicMock
        req = RequestFactory().post(
            '/api/action/ad-assessment/from-subdomain/',
            data={'subdomain_id': 99999},
            content_type='application/json',
        )
        req.user = self.user
        req.data = {'subdomain_id': 99999}
        view_instance = LaunchADAssessmentFromSubdomain()
        view_instance.request = req
        # Patch Subdomain.objects.get to return a mock subdomain
        mock_sub = MagicMock()
        mock_sub.scan_history.domain.name = 'corp.local'
        with patch('api.views.Subdomain.objects.select_related') as mock_sr:
            mock_sr.return_value.get.return_value = mock_sub
            # Simulate plugin not installed
            import builtins
            real_import = builtins.__import__
            def mock_import(name, *args, **kwargs):
                if 'plugins_data.active_directory.backend.models' in name:
                    raise ImportError('not installed')
                return real_import(name, *args, **kwargs)
            with patch('builtins.__import__', side_effect=mock_import):
                response = view_instance.post(req)
        self.assertEqual(response.status_code, 400)
        self.assertIn('plugin', response.data['error'].lower())

    def test_successful_creation_returns_201(self):
        from api.views import LaunchADAssessmentFromSubdomain
        from unittest.mock import MagicMock, patch

        req = RequestFactory().post(
            '/api/action/ad-assessment/from-subdomain/',
            data={'subdomain_id': 1},
            content_type='application/json',
        )
        req.user = self.user

        mock_sub = MagicMock()
        mock_sub.scan_history.domain.name = 'corp.local'

        mock_assessment = MagicMock()
        mock_assessment.id = 42
        mock_assessment.name = 'AD Assessment — corp.local'

        mock_ad_class = MagicMock()
        mock_ad_class.objects.create.return_value = mock_assessment

        view_instance = LaunchADAssessmentFromSubdomain()
        view_instance.request = req

        with patch('api.views.Subdomain.objects.select_related') as mock_sr, \
             patch.dict('sys.modules', {
                 'plugins_data': MagicMock(),
                 'plugins_data.active_directory': MagicMock(),
                 'plugins_data.active_directory.backend': MagicMock(),
                 'plugins_data.active_directory.backend.models': MagicMock(ADAssessment=mock_ad_class),
             }):
            mock_sr.return_value.get.return_value = mock_sub
            response = view_instance.post(req)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['assessment_id'], 42)
        self.assertEqual(response.data['target_domain'], 'corp.local')
        self.assertEqual(response.data['status'], 'created')
