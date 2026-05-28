from django.test import TestCase
from unittest.mock import MagicMock, patch


class VigoliumDefinitionsTest(TestCase):
    def test_vigolium_constants_defined(self):
        from reNgine.definitions import (
            RUN_VIGOLIUM,
            RUN_VIGOLIUM_DISCOVERY,
            RUN_VIGOLIUM_ANALYSIS,
            VIGOLIUM,
            VIGOLIUM_STRATEGY,
            VIGOLIUM_CONCURRENCY,
            VIGOLIUM_RATE_LIMIT,
            VIGOLIUM_TIMEOUT,
            VIGOLIUM_MODULES,
            VIGOLIUM_SEVERITY_FILTER,
            VIGOLIUM_DEFAULT_CONFIG,
        )
        self.assertEqual(RUN_VIGOLIUM, 'run_vigolium')
        self.assertEqual(RUN_VIGOLIUM_DISCOVERY, 'run_vigolium_discovery')
        self.assertEqual(RUN_VIGOLIUM_ANALYSIS, 'run_vigolium_analysis')
        self.assertEqual(VIGOLIUM, 'vigolium')
        self.assertIn('run_vigolium', VIGOLIUM_DEFAULT_CONFIG)
        self.assertTrue(VIGOLIUM_DEFAULT_CONFIG['run_vigolium'])
