"""Persistent database connections belong to the worker, not to the web process.

The web process serves ASGI under a uvicorn worker and does not reuse its
database connections: each is opened, used once and abandoned. On a production
instance 150 of them accumulated and exhausted max_connections, at which point
`manage.py` could not connect and running scans could not write results.

The Temporal worker is the opposite case — DjangoAwareThreadPoolExecutor closes
every activity's connection — so it keeps the persistent default.
"""
import os
import unittest

import yaml
from django.test import SimpleTestCase, override_settings

COMPOSE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'docker', 'docker-compose.yml',
)


def _service_env(service: str) -> dict:
    with open(COMPOSE_FILE, encoding='utf-8') as handle:
        compose = yaml.safe_load(handle)
    entries = compose['services'][service].get('environment') or []
    env = {}
    for entry in entries:
        if '=' in entry:
            key, _, value = entry.partition('=')
            env[key] = value
    return env


class TestComposeWiring(unittest.TestCase):

    def test_web_disables_persistent_connections(self):
        self.assertEqual(_service_env('web').get('DJANGO_CONN_MAX_AGE'), '0')

    def test_orchestrator_keeps_the_default(self):
        """It closes connections per activity, so reuse is safe there."""
        self.assertIsNone(
            _service_env('temporal-python-orchestrator').get('DJANGO_CONN_MAX_AGE')
        )

    def test_go_executor_keeps_the_default(self):
        self.assertIsNone(
            _service_env('temporal-go-executor').get('DJANGO_CONN_MAX_AGE')
        )


class TestSettingReadsTheEnvironment(unittest.TestCase):
    """The value has to come from the environment, or the split cannot exist."""

    def test_settings_source_reads_the_variable(self):
        settings_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'reNgine', 'settings.py',
        )
        with open(settings_file, encoding='utf-8') as handle:
            source = handle.read()
        self.assertIn("env.int('DJANGO_CONN_MAX_AGE', default=60)", source)
        self.assertNotIn("'CONN_MAX_AGE': 60,", source)


class TestEffectiveValue(SimpleTestCase):

    def test_conn_max_age_is_an_integer(self):
        from django.conf import settings
        self.assertIsInstance(settings.DATABASES['default']['CONN_MAX_AGE'], int)

    @override_settings(DATABASES={'default': {'CONN_MAX_AGE': 0}})
    def test_zero_is_a_valid_value(self):
        """Django treats 0 as close-at-end-of-request, not as unset."""
        from django.conf import settings
        self.assertEqual(settings.DATABASES['default']['CONN_MAX_AGE'], 0)
