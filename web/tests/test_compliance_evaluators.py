# web/tests/test_compliance_evaluators.py
import unittest
from django.utils import timezone

try:
    from plugins_data.compliance_assessment.backend.engine.evaluators.vuln_evaluator import VulnEvaluator
    PLUGIN_AVAILABLE = True
except ImportError:
    PLUGIN_AVAILABLE = False


@unittest.skipUnless(PLUGIN_AVAILABLE, 'compliance_assessment plugin not installed')
class TestVulnEvaluator(unittest.TestCase):
    """Tests for VulnEvaluator — requires plugin installed and DB access."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from startScan.models import Domain, ScanHistory
        from scanEngine.models import EngineType
        cls.domain = Domain.objects.create(name='test-eval.example.com')
        cls.engine = EngineType.objects.first()
        cls.scan = ScanHistory.objects.create(
            domain=cls.domain,
            scan_type=cls.engine,
            scan_status=2,
            start_scan_date=timezone.now(),
        )

    @classmethod
    def tearDownClass(cls):
        from startScan.models import ScanHistory, Domain
        ScanHistory.objects.filter(id=cls.scan.id).delete()
        Domain.objects.filter(id=cls.domain.id).delete()
        super().tearDownClass()

    def test_matches_critical_vulnerability(self):
        from startScan.models import Vulnerability
        v = Vulnerability.objects.create(
            scan_history=self.scan,
            name='Critical CVE',
            severity=4,
            cvss_score=9.8,
            target_domain=self.domain,
        )
        try:
            result = VulnEvaluator().check(self.scan.id, {'severity': 'critical'})
            self.assertTrue(result.matches)
            self.assertEqual(result.confidence, 'HIGH')
            self.assertGreaterEqual(len(result.evidence), 1)
        finally:
            v.delete()

    def test_no_match_when_no_critical_vulns(self):
        from startScan.models import Vulnerability
        v = Vulnerability.objects.create(
            scan_history=self.scan,
            name='Low CVE',
            severity=0,
            cvss_score=1.0,
            target_domain=self.domain,
        )
        try:
            result = VulnEvaluator().check(self.scan.id, {'severity': 'critical'})
            self.assertFalse(result.matches)
        finally:
            v.delete()

    def test_min_cvss_filter(self):
        from startScan.models import Vulnerability
        v = Vulnerability.objects.create(
            scan_history=self.scan,
            name='High CVSS',
            severity=3,
            cvss_score=9.5,
            target_domain=self.domain,
        )
        try:
            result = VulnEvaluator().check(self.scan.id, {'min_cvss': 9.0})
            self.assertTrue(result.matches)
        finally:
            v.delete()

    def test_empty_scan_returns_no_match(self):
        """A scan with no vulnerabilities returns matches=False."""
        from startScan.models import Domain, ScanHistory
        from scanEngine.models import EngineType
        empty_domain = Domain.objects.create(name='empty-eval.example.com')
        try:
            empty_scan = ScanHistory.objects.create(
                domain=empty_domain,
                scan_type=self.engine,
                scan_status=2,
                start_scan_date=timezone.now(),
            )
            try:
                result = VulnEvaluator().check(empty_scan.id, {})
                self.assertFalse(result.matches)
                self.assertEqual(result.evidence, [])
            finally:
                ScanHistory.objects.filter(id=empty_scan.id).delete()
        finally:
            Domain.objects.filter(id=empty_domain.id).delete()
