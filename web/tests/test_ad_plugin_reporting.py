# web/tests/test_ad_plugin_reporting.py
from django.test import TestCase


def _skip_if_not_installed(tc):
    try:
        from django.apps import apps
        apps.get_model('active_directory_backend', 'ADAssessment')
    except LookupError:
        tc.skipTest("Plugin not installed")


class TestReportingEngine(TestCase):

    def setUp(self):
        _skip_if_not_installed(self)
        from plugins_data.active_directory.backend.models import ADAssessment
        self.assessment = ADAssessment.objects.create(
            name="Test Corp", target_domain="corp.test.local", status="COMPLETED"
        )

    def tearDown(self):
        self.assessment.delete()

    def test_compile_returns_required_keys(self):
        from plugins_data.active_directory.backend.reporting.engine import ReportingEngine
        report = ReportingEngine.compile(self.assessment.id)
        for key in ['metadata', 'executive_summary', 'domain_inventory',
                    'trust_analysis', 'exposure_analysis', 'findings', 'timeline']:
            self.assertIn(key, report, f"Report missing key: {key}")

    def test_compile_metadata_target_domain(self):
        from plugins_data.active_directory.backend.reporting.engine import ReportingEngine
        report = ReportingEngine.compile(self.assessment.id)
        self.assertEqual(report['metadata']['target_domain'], 'corp.test.local')

    def test_compile_finding_counts(self):
        from plugins_data.active_directory.backend.models import ADFinding
        ADFinding.objects.create(
            assessment=self.assessment,
            title="Kerberoastable SPN", description="desc",
            severity="HIGH", finding_type="KERBEROAST",
        )
        from plugins_data.active_directory.backend.reporting.engine import ReportingEngine
        report = ReportingEngine.compile(self.assessment.id)
        self.assertEqual(report['executive_summary']['finding_counts']['HIGH'], 1)
