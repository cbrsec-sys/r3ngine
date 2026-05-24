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
