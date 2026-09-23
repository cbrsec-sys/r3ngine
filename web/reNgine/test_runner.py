"""Test runner that turns off persistent database connections.

`CONN_MAX_AGE` is set for production, where a reused connection saves a TCP and
TLS handshake per request. Under test it buys nothing: every test opens and
discards its own state, and a connection carried across a `TransactionTestCase`
boundary is one more thing that can be stale when the next test picks it up.

Honest caveat on why this exists: it was added while chasing a wave of
`OperationalError: could not receive data from server: Bad file descriptor`
failures that appeared after CONN_MAX_AGE was raised. Those failures were later
reproduced and traced to interactions between individual tests, not to
persistent connections, and Django has no connection pool that could have
handed a closed connection back — the original explanation was wrong. The
setting is still right for tests on its own merits, so it stays, but it should
not be credited with fixing anything.

Django has no setting for "persistent connections except in tests", so the
runner is the explicit place to say it once, for every way tests are started.
"""
from django.conf import settings
from django.db import connections
from django.test.runner import DiscoverRunner


class RengineTestRunner(DiscoverRunner):
    """DiscoverRunner with CONN_MAX_AGE forced to 0 for every alias."""

    def setup_databases(self, **kwargs):
        for alias in connections:
            # settings_dict is the same object as settings.DATABASES[alias], so
            # one assignment would do; both are written to keep the intent
            # obvious if Django ever stops sharing them.
            settings.DATABASES[alias]['CONN_MAX_AGE'] = 0
            connections[alias].settings_dict['CONN_MAX_AGE'] = 0
            # Production Postgres sets statement_timeout=5m. TransactionTestCase
            # teardown TRUNCATE of a freshly migrated schema can exceed that on a
            # busy host and cancel the flush mid-suite.
            db_options = settings.DATABASES[alias].setdefault('OPTIONS', {})
            existing = db_options.get('options', '')
            if 'statement_timeout' not in existing:
                extra = '-c statement_timeout=0'
                db_options['options'] = f'{existing} {extra}'.strip()
            connections[alias].settings_dict['OPTIONS'] = db_options
        connections.close_all()
        return super().setup_databases(**kwargs)
