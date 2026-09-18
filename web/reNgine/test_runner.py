"""Test runner that turns off persistent database connections.

`CONN_MAX_AGE` is set for production, where a reused connection saves a TCP and
TLS handshake per request. It is actively harmful under test: `TransactionTestCase`
truncates tables and closes connections between tests, while the persistent
connection pool keeps handing the closed one back, which surfaces as
`OperationalError: could not receive data from server: Bad file descriptor` and
`InterfaceError: connection already closed` across whole test classes.

Django has no setting for "persistent connections except in tests", so the runner
is the explicit place to say it once, for every way tests are started.
"""
from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner


class RengineTestRunner(DiscoverRunner):
    """DiscoverRunner with CONN_MAX_AGE forced to 0 for every alias."""

    def setup_databases(self, **kwargs):
        for alias in connections:
            settings.DATABASES[alias]['CONN_MAX_AGE'] = 0
            # Connections created before this point carry their own copy of the
            # settings dict, so update those too rather than only the template.
            connections[alias].settings_dict['CONN_MAX_AGE'] = 0
        connections.close_all()
        return super().setup_databases(**kwargs)
