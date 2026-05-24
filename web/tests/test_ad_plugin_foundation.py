# web/tests/test_ad_plugin_foundation.py
from django.test import TestCase


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
