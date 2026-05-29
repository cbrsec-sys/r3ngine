import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from unittest import skipUnless
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

User = get_user_model()

try:
    from plugins_data.active_directory.backend.models import ADAssessment
    AD_PLUGIN_AVAILABLE = True
except ImportError:
    AD_PLUGIN_AVAILABLE = False


def _make_mock_manager(nodes=None, edges=None, truncated=False, total_nodes=None):
    nodes = nodes or [{'data': {'id': f'n{i}'}} for i in range(5)]
    total = total_nodes if total_nodes is not None else len(nodes)
    mock_mgr = MagicMock()
    mock_mgr.__enter__ = MagicMock(return_value=mock_mgr)
    mock_mgr.__exit__ = MagicMock(return_value=False)
    mock_mgr.get_domain_graph.return_value = {
        'nodes': nodes,
        'edges': edges or [],
        'truncated': truncated,
        'total_nodes': total,
    }
    return mock_mgr


@skipUnless(AD_PLUGIN_AVAILABLE, 'AD Intelligence plugin not installed')
class TestADGraphEndpoint(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='graph_test_user_t6', password='pass', is_staff=True
        )
        self.assessment = ADAssessment.objects.create(
            name='Graph Test',
            target_domain='graph.local',
            created_by=self.user,
        )

    def tearDown(self):
        self.assessment.delete()
        self.user.delete()

    def _call_graph_domains(self, limit_param=None, mock_mgr=None):
        from rest_framework.test import APIRequestFactory
        from plugins_data.active_directory.backend.api import ADAssessmentViewSet

        params = {}
        if limit_param is not None:
            params['limit'] = str(limit_param)

        req = APIRequestFactory().get('/graph/domains/', params)
        req.user = self.user

        view = ADAssessmentViewSet.as_view({'get': 'graph_domains'})

        mgr = mock_mgr or _make_mock_manager()
        with patch(
            'plugins_data.active_directory.backend.graph.manager.ADGraphManager',
            return_value=mgr,
        ):
            return view(req, pk=self.assessment.pk)

    def test_default_limit_returns_200(self):
        response = self._call_graph_domains()
        self.assertEqual(response.status_code, 200)

    def test_invalid_limit_returns_400(self):
        from rest_framework.test import APIRequestFactory
        from plugins_data.active_directory.backend.api import ADAssessmentViewSet

        req = APIRequestFactory().get('/graph/domains/', {'limit': 'abc'})
        req.user = self.user
        view = ADAssessmentViewSet.as_view({'get': 'graph_domains'})

        response = view(req, pk=self.assessment.pk)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

    def test_negative_limit_is_clamped_not_400(self):
        # limit < 0 → clamped to 0 → maps to 5000 (load-all cap), NOT a 400
        response = self._call_graph_domains(limit_param=-5)
        self.assertNotEqual(response.status_code, 400)

    def test_limit_zero_calls_get_domain_graph_with_5000(self):
        mgr = _make_mock_manager()
        self._call_graph_domains(limit_param=0, mock_mgr=mgr)
        mgr.get_domain_graph.assert_called_once_with(
            self.assessment.id, limit=5000
        )

    def test_limit_above_5000_is_capped_at_5000(self):
        mgr = _make_mock_manager()
        self._call_graph_domains(limit_param=9999, mock_mgr=mgr)
        mgr.get_domain_graph.assert_called_once_with(
            self.assessment.id, limit=5000
        )

    def test_default_limit_is_300(self):
        mgr = _make_mock_manager()
        self._call_graph_domains(mock_mgr=mgr)
        mgr.get_domain_graph.assert_called_once_with(
            self.assessment.id, limit=300
        )
