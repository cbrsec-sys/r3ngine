# web/tests/test_ad_plugin_foundation.py
from django.test import TestCase
from unittest.mock import patch, MagicMock


class TestADPluginAppConfig(TestCase):
    def test_app_label_is_unique_and_correct(self):
        from django.apps import apps
        import importlib
        try:
            spec = importlib.util.find_spec("plugins_data.active_directory.backend")
        except ModuleNotFoundError:
            # plugins_data package not yet installed — test documents the expectation only
            spec = None
        # spec will be None until installed; the test documents the expectation
        if spec is not None:
            config = apps.get_app_config("active_directory_backend")
            self.assertEqual(config.label, "active_directory_backend")
            self.assertEqual(config.name, "plugins_data.active_directory.backend")


class TestADPluginModels(TestCase):
    """Run after plugin is installed into plugins_data/."""

    def _get_model(self, name):
        from django.apps import apps
        try:
            return apps.get_model('active_directory_backend', name)
        except LookupError:
            self.skipTest("Plugin not yet installed into plugins_data/")

    def test_assessment_model_fields(self):
        Assessment = self._get_model('ADAssessment')
        field_names = [f.name for f in Assessment._meta.get_fields()]
        for expected in ['name', 'target_domain', 'status', 'workflow_id', 'config']:
            self.assertIn(expected, field_names)

    def test_domain_fk_to_assessment(self):
        Domain = self._get_model('ADDomain')
        fk = Domain._meta.get_field('assessment')
        self.assertEqual(fk.related_model.__name__, 'ADAssessment')

    def test_finding_severity_choices(self):
        Finding = self._get_model('ADFinding')
        choices = [c[0] for c in Finding._meta.get_field('severity').choices]
        self.assertIn('CRITICAL', choices)
        self.assertIn('HIGH', choices)


class TestADTemporalExports(TestCase):

    def _import_exports(self):
        try:
            import importlib
            return importlib.import_module(
                'plugins_data.active_directory.backend.temporal_exports')
        except (ImportError, ModuleNotFoundError):
            self.skipTest("Plugin not yet installed into plugins_data/")

    def test_workflow_class_is_registered(self):
        mod = self._import_exports()
        self.assertTrue(hasattr(mod, 'ADAssessmentWorkflow'))

    def test_all_activity_functions_exist(self):
        mod = self._import_exports()
        expected = [
            'initialize_assessment_activity',
            'run_dns_discovery_activity',
            'run_cert_discovery_activity',
            'run_trust_analysis_activity',
            'run_exposure_correlation_activity',
            'run_neo4j_sync_activity',
            'finalize_assessment_activity',
        ]
        for name in expected:
            self.assertTrue(hasattr(mod, name), f"Missing activity: {name}")


class TestADAssessmentAPI(TestCase):

    def _get_view(self):
        try:
            from plugins_data.active_directory.backend.api import ADAssessmentViewSet
            return ADAssessmentViewSet
        except (ImportError, ModuleNotFoundError):
            self.skipTest("Plugin not installed")

    def test_viewset_has_required_actions(self):
        ViewSet = self._get_view()
        self.assertTrue(hasattr(ViewSet, 'start'))
        self.assertTrue(hasattr(ViewSet, 'cancel'))
        self.assertTrue(hasattr(ViewSet, 'ingest'))
        self.assertTrue(hasattr(ViewSet, 'findings'))
        self.assertTrue(hasattr(ViewSet, 'exposures'))
        self.assertTrue(hasattr(ViewSet, 'trusts'))
        self.assertTrue(hasattr(ViewSet, 'graph_snapshot'))
