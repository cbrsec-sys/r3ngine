# web/tests/test_cve_details_view.py
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rolepermissions.roles import assign_role

from startScan.models import CveId

User = get_user_model()


def _make_circl_response(data=None, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data or {}
    return mock


class CVEDetailsNormalizationTestCase(TestCase):
    """
    Verify CVEDetails API view normalises bare YYYY-NNNNN CVE IDs to CVE-YYYY-NNNNN
    before DB lookup and before building the CIRCL.LU request URL.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='pentester', password='pass', email='t@test.com',
            is_staff=True, is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)
        self.client.force_login(self.user)
        assign_role(self.user, 'penetration_tester')

        self.cve = CveId.objects.create(
            name='CVE-2026-6127',
            cvss_v31_base_score=7.5,
            attack_vector='NETWORK',
            attack_complexity='LOW',
            user_interaction='NONE',
            confidentiality_impact='HIGH',
            integrity_impact='HIGH',
            availability_impact='HIGH',
        )

    @patch('requests.get')
    def test_bare_format_resolves_to_prefixed_db_record(self, mock_get):
        """Passing '2026-6127' should find the record stored as 'CVE-2026-6127'."""
        mock_get.return_value = _make_circl_response({'summary': 'Test CVE', 'assigner': 'acme'})

        url = reverse('api:cve_details') + '?cve_id=2026-6127'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['status'])
        self.assertEqual(data['result']['attack_vector'], 'NETWORK')

    @patch('requests.get')
    def test_circl_url_uses_normalized_id(self, mock_get):
        """CIRCL.LU must be called with CVE-YYYY-NNNNN, never bare YYYY-NNNNN."""
        mock_get.return_value = _make_circl_response({})

        url = reverse('api:cve_details') + '?cve_id=2026-6127'
        self.client.get(url)

        called_url = mock_get.call_args[0][0]
        self.assertIn('CVE-2026-6127', called_url)
        self.assertNotIn('/api/cve/2026-6127', called_url)

    @patch('requests.get')
    def test_prefixed_format_still_works(self, mock_get):
        """Passing 'CVE-2026-6127' directly must also work."""
        mock_get.return_value = _make_circl_response({'summary': 'Test CVE'})

        url = reverse('api:cve_details') + '?cve_id=CVE-2026-6127'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['status'])

    @patch('reNgine.cve_enrichment.CVEEnrichmentService.enrich_cve')
    @patch('requests.get')
    def test_lazy_reenrichment_triggered_when_cvss_is_null(self, mock_get, mock_enrich):
        """When the DB record has no CVSS score, enrich_cve must be called."""
        unenriched = CveId.objects.create(name='CVE-2026-9999')
        mock_get.return_value = _make_circl_response({})
        mock_enrich.return_value = unenriched

        url = reverse('api:cve_details') + '?cve_id=CVE-2026-9999'
        self.client.get(url)

        mock_enrich.assert_called_once_with('CVE-2026-9999')

    @patch('requests.get')
    def test_no_reenrichment_when_cvss_present(self, mock_get):
        """When the DB record already has CVSS data, enrich_cve must NOT be called."""
        mock_get.return_value = _make_circl_response({})

        with patch('reNgine.cve_enrichment.CVEEnrichmentService.enrich_cve') as mock_enrich:
            url = reverse('api:cve_details') + '?cve_id=CVE-2026-6127'
            self.client.get(url)
            mock_enrich.assert_not_called()

    @patch('requests.get')
    def test_response_shape(self, mock_get):
        """Response must contain the expected keys in result."""
        mock_get.return_value = _make_circl_response({
            'summary': 'Buffer overflow in libfoo',
            'assigner': 'cve@mitre.org',
            'references': ['https://example.com/advisory'],
        })

        url = reverse('api:cve_details') + '?cve_id=CVE-2026-6127'
        response = self.client.get(url)
        result = response.json()['result']

        for key in ('id', 'summary', 'assigner', 'cvss_v31_base_score',
                    'attack_vector', 'attack_complexity', 'user_interaction',
                    'confidentiality_impact', 'integrity_impact', 'availability_impact',
                    'epss_score', 'is_cisa_kev', 'references'):
            self.assertIn(key, result, f"Missing key: {key}")
