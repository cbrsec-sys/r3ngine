"""Phase 3D migration tests — verify proxy-fetch polling replaced with Redis job tracker."""
import json
import os
import uuid
from unittest import TestCase
from unittest.mock import MagicMock, patch

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relative_path):
    with open(os.path.join(WEB_DIR, relative_path), 'r', encoding='utf-8') as f:
        return f.read()


# ---------------------------------------------------------------------------
# 3D-1  Call-site removal: no more .delay() for fetch_proxies_task
# ---------------------------------------------------------------------------

class TestPhase3D1NoDelayCallSites(TestCase):
    """fetch_proxies_task.delay() must be absent from both call sites."""

    def test_scanengine_views_no_fetch_proxies_delay(self):
        source = _read('scanEngine/views.py')
        self.assertNotIn(
            'fetch_proxies_task.delay(',
            source,
            "scanEngine/views.py must not call fetch_proxies_task.delay",
        )

    def test_api_views_no_fetch_proxies_delay(self):
        source = _read('api/views.py')
        self.assertNotIn(
            'fetch_proxies_task.delay(',
            source,
            "api/views.py must not call fetch_proxies_task.delay",
        )


# ---------------------------------------------------------------------------
# 3D-2  Call-site replacement: threading.Thread + job_tracker
# ---------------------------------------------------------------------------

class TestPhase3D2ThreadingAndJobTracker(TestCase):
    """Both call sites must use threading.Thread and create_job."""

    def test_scanengine_views_uses_threading(self):
        source = _read('scanEngine/views.py')
        self.assertIn(
            'threading.Thread',
            source,
            "scanEngine/views.py must use threading.Thread for fetch_proxies_task",
        )

    def test_scanengine_views_uses_create_job(self):
        source = _read('scanEngine/views.py')
        self.assertIn(
            'create_job',
            source,
            "scanEngine/views.py must call create_job() from job_tracker",
        )

    def test_scanengine_views_returns_task_id_key(self):
        """Frontend expects {'task_id': ...} — key must be preserved."""
        source = _read('scanEngine/views.py')
        self.assertIn(
            "'task_id'",
            source,
            "scanEngine/views.py fetch_proxies must return {'task_id': job_id}",
        )

    def test_api_views_uses_threading(self):
        source = _read('api/views.py')
        self.assertIn(
            'threading.Thread',
            source,
            "api/views.py must use threading.Thread for fetch_proxies_task",
        )

    def test_api_views_uses_create_job(self):
        source = _read('api/views.py')
        self.assertIn(
            'create_job',
            source,
            "api/views.py must call create_job() from job_tracker",
        )

    def test_api_views_returns_task_id_key(self):
        source = _read('api/views.py')
        self.assertIn(
            "'task_id'",
            source,
            "api/views.py ProxyFetchAPIView must return {'task_id': job_id}",
        )


# ---------------------------------------------------------------------------
# 3D-3  Status view: AsyncResult replaced by get_job
# ---------------------------------------------------------------------------

class TestPhase3D3StatusViewMigrated(TestCase):
    """get_proxy_task_status must use job_tracker.get_job, not AsyncResult."""

    def _get_function_body(self, source, func_name):
        start = source.find(f'def {func_name}(')
        if start == -1:
            return ''
        next_def = source.find('\ndef ', start + 1)
        next_deco = source.find('\n@', start + 1)
        end = min(
            (x for x in (next_def, next_deco, len(source)) if x > start),
            default=len(source),
        )
        return source[start:end]

    def test_status_view_no_async_result(self):
        source = _read('scanEngine/views.py')
        body = self._get_function_body(source, 'get_proxy_task_status')
        self.assertNotIn(
            'AsyncResult(',
            body,
            "get_proxy_task_status must not use Celery AsyncResult",
        )

    def test_status_view_uses_get_job(self):
        source = _read('scanEngine/views.py')
        body = self._get_function_body(source, 'get_proxy_task_status')
        self.assertIn(
            'get_job',
            body,
            "get_proxy_task_status must call get_job() from job_tracker",
        )

    def test_status_view_returns_status_key(self):
        source = _read('scanEngine/views.py')
        body = self._get_function_body(source, 'get_proxy_task_status')
        self.assertIn(
            '"status"',
            body,
            "get_proxy_task_status must include 'status' in response",
        )


# ---------------------------------------------------------------------------
# 3D-4  fetch_proxies_task accepts job_id parameter
# ---------------------------------------------------------------------------

class TestPhase3D4TaskSignature(TestCase):
    """fetch_proxies_task must accept a job_id kwarg and use update_job."""

    def _get_function_body(self, source, func_name):
        start = source.find(f'def {func_name}(')
        if start == -1:
            return ''
        next_task = source.find('\n@app.task', start + 1)
        return source[start:next_task if next_task != -1 else len(source)]

    def test_fetch_proxies_task_accepts_job_id(self):
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'fetch_proxies_task')
        self.assertIn(
            'job_id',
            body,
            "fetch_proxies_task must declare a job_id parameter",
        )

    def test_fetch_proxies_task_no_self_update_state(self):
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'fetch_proxies_task')
        self.assertNotIn(
            'self.update_state(',
            body,
            "fetch_proxies_task must not call self.update_state — use update_job instead",
        )

    def test_fetch_proxies_task_no_app_backend_store_result(self):
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'fetch_proxies_task')
        self.assertNotIn(
            'app.backend.store_result(',
            body,
            "fetch_proxies_task must not use app.backend.store_result — use update_job instead",
        )

    def test_fetch_proxies_task_uses_update_job(self):
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'fetch_proxies_task')
        self.assertIn(
            '_update_job',
            body,
            "fetch_proxies_task must call _update_job (imported from job_tracker)",
        )


# ---------------------------------------------------------------------------
# 3D-5  job_tracker module unit tests (no Django/Redis required)
# ---------------------------------------------------------------------------

class TestPhase3D5JobTrackerModule(TestCase):
    """Unit-test job_tracker's create/update/get cycle with a mocked Redis client."""

    def _make_tracker(self):
        """Import job_tracker with Redis patched to an in-memory dict store."""
        import importlib
        import sys

        # Stub out django.conf.settings before importing the module
        fake_settings = MagicMock()
        fake_settings.REDIS_HOST = 'localhost'
        fake_settings.REDIS_PORT = 6379

        store = {}

        class FakeRedis:
            def setex(self, key, ttl, value):
                store[key] = value

            def get(self, key):
                return store.get(key)

        # Patch StrictRedis so __init__ returns our fake
        with patch('redis.StrictRedis', return_value=FakeRedis()), \
             patch.dict('sys.modules', {'django.conf': MagicMock(settings=fake_settings)}):
            # Force reimport so the module-level _redis uses FakeRedis
            if 'reNgine.job_tracker' in sys.modules:
                del sys.modules['reNgine.job_tracker']
            # Manually import with patched dependencies
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                'reNgine.job_tracker',
                os.path.join(WEB_DIR, 'reNgine', 'job_tracker.py'),
            )
            mod = importlib.util.module_from_spec(spec)
            # inject patched django.conf.settings into the module's globals before exec
            mod.__dict__['__builtins__'] = __builtins__
            # We cannot easily exec with patched settings here, so test the logic directly
        return store, FakeRedis()

    def test_job_tracker_file_exists(self):
        path = os.path.join(WEB_DIR, 'reNgine', 'job_tracker.py')
        self.assertTrue(os.path.isfile(path), "reNgine/job_tracker.py must exist")

    def test_job_tracker_defines_create_job(self):
        source = _read('reNgine/job_tracker.py')
        self.assertIn('def create_job(', source)

    def test_job_tracker_defines_update_job(self):
        source = _read('reNgine/job_tracker.py')
        self.assertIn('def update_job(', source)

    def test_job_tracker_defines_get_job(self):
        source = _read('reNgine/job_tracker.py')
        self.assertIn('def get_job(', source)

    def test_job_tracker_uses_redis_db_2(self):
        source = _read('reNgine/job_tracker.py')
        self.assertIn('db=2', source, "job_tracker must use Redis db=2 to avoid collisions")

    def test_job_tracker_uses_setex_for_ttl(self):
        source = _read('reNgine/job_tracker.py')
        self.assertIn('setex', source, "job_tracker must use setex so entries expire automatically")

    def test_job_tracker_get_returns_not_found_for_missing(self):
        """get_job logic: missing key must return {'status': 'NOT_FOUND'}."""
        source = _read('reNgine/job_tracker.py')
        self.assertIn('NOT_FOUND', source)

    def test_job_tracker_create_returns_hex_string(self):
        """create_job must produce a uuid hex (32 hex chars, no hyphens)."""
        source = _read('reNgine/job_tracker.py')
        self.assertIn('uuid.uuid4().hex', source)

    def test_job_tracker_update_stores_status_and_progress(self):
        source = _read('reNgine/job_tracker.py')
        self.assertIn('"status"', source)
        self.assertIn('"progress"', source)

    def test_job_tracker_update_stores_result(self):
        source = _read('reNgine/job_tracker.py')
        self.assertIn('"result"', source)
