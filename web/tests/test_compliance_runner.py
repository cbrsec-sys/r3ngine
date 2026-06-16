# web/tests/test_compliance_runner.py
import unittest

try:
    from plugins_data.compliance_assessment.backend.engine.runner import run_framework
    PLUGIN_AVAILABLE = True
except ImportError:
    PLUGIN_AVAILABLE = False


@unittest.skipUnless(PLUGIN_AVAILABLE, 'compliance_assessment plugin not installed')
class TestRunner(unittest.TestCase):
    pass  # Runner tests require DB setup — deferred until plugin installed
