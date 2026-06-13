# Temporal Architecture Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden r3ngine's Temporal migration by eliminating two production-risk bugs (daemon thread escaping durability, broken client cache), closing a security allowlist gap, fixing LLM module vulnerabilities, adding explicit retry policies, and retiring the most impactful technical debt.

**Architecture:** Ten sequenced tasks divided into seven phases by priority. Phases 1–3 should ship together as a single hardening release. Phases 4–7 are independent and can be batched into a follow-on PR. Each task produces working, independently testable changes. Tasks 1 and 2 are P0 — deploy these before anything else.

**Tech Stack:** Python 3.11, Django 3.2, temporalio 1.6.0, PostgreSQL, requests 2.32.3, asgiref (bundled with Django)

---

## File Map

| File | Change |
|---|---|
| `web/reNgine/temporal_client.py` | Remove broken event-loop-bound cache; simplify to fresh-connection-per-call |
| `web/reNgine/temporal_schedule_utils.py` | Remove `reset()` calls (cache gone) |
| `web/reNgine/tasks.py` | Fix daemon threads in `osint()`; remove dead Celery callbacks |
| `web/reNgine/temporal_activities.py` | Add `_PERMITTED_GENERIC_TASKS` allowlist |
| `web/reNgine/temporal_workflows.py` | Add retry policies; replace `SubScanWorkflow` if/elif with dispatch registry; remove checkpoint calls |
| `web/reNgine/llm.py` | Fix SSL verification; Gemini key in header; Anthropic `system` field; `raise_for_status` |
| `web/reNgine/scan_context.py` | **Create** — `ScanContext` TypedDict for workflow context dict |
| `web/reNgine/definitions.py` | Rename `CELERY_TASK_STATUSES` → `TASK_STATUSES` |
| `web/startScan/models.py` | Rename `celery_ids` → `workflow_ids`; `celery_id` → `execution_id` |
| `web/startScan/migrations/00XX_rename_celery_fields.py` | **Create** — DB migration |
| `web/api/serializers.py` | Update `celery_ids` → `workflow_ids` field references |
| `web/tests/test_temporal_client.py` | **Create** — connection management tests |
| `web/tests/test_temporal_activities.py` | Add allowlist + checkpoint removal tests |
| `web/tests/test_llm.py` | **Create** — LLM security tests |
| `web/tests/test_phase3c_migration.py` | Update threading assertion for `finish_osint` fix |

---

## Phase 1 — P0: Critical (deploy first)

### Task 1: Remove the broken TemporalClientProvider cache

**Context:** `TemporalClientProvider.get_client()` caches a `Client` object in a class variable. But every caller wraps calls in a separate `asyncio.new_event_loop()` that creates and immediately destroys its own event loop. A `temporalio.client.Client` is bound to the event loop it was created in; once that loop is closed, the cached client raises gRPC errors when used in a new loop. This is documented in `cancel_workflow()`'s own comment: *"The cached client is created inside a temporary event loop during scan start and that loop is closed immediately after; reusing it from a new loop raises asyncio errors."* All 8 schedule-util helpers already call `TemporalClientProvider.reset()` before each operation, making the cache a no-op that only adds confusion. Fix: remove the cache and `reset()`. The Temporal SDK manages gRPC channel pooling internally; creating a new `Client` for each synchronous Django operation costs ~5ms.

**Files:**
- Modify: `web/reNgine/temporal_client.py`
- Modify: `web/reNgine/temporal_schedule_utils.py` (8 `reset()` calls)
- Modify: `web/reNgine/tasks.py` (2 `reset()` calls at lines ~929, ~1151)
- Create: `web/tests/test_temporal_client.py`

---

- [ ] **Step 1.1: Write the failing tests**

```python
# web/tests/test_temporal_client.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from django.test import TestCase
from reNgine.temporal_client import TemporalClientProvider


class TestTemporalClientProvider(TestCase):

    @patch("reNgine.temporal_client.Client.connect", new_callable=AsyncMock)
    def test_get_client_creates_fresh_connection_each_call(self, mock_connect):
        """Each call to get_client must connect fresh — no caching across event loops."""
        mock_connect.return_value = MagicMock()
        asyncio.run(TemporalClientProvider.get_client())
        asyncio.run(TemporalClientProvider.get_client())
        self.assertEqual(mock_connect.call_count, 2)

    def test_reset_method_no_longer_exists(self):
        """reset() existed only to defeat the cache. With caching gone it must not exist."""
        self.assertFalse(
            hasattr(TemporalClientProvider, "reset"),
            "TemporalClientProvider.reset() must be removed along with the cache",
        )

    @patch("reNgine.temporal_client.Client.connect", new_callable=AsyncMock)
    def test_cancel_workflow_uses_correct_env_vars(self, mock_connect):
        """cancel_workflow must connect to TEMPORAL_HOST / TEMPORAL_NAMESPACE env vars."""
        import os
        mock_handle = AsyncMock()
        mock_client = MagicMock()
        mock_client.get_workflow_handle.return_value = mock_handle
        mock_connect.return_value = mock_client

        with patch.dict(os.environ, {"TEMPORAL_HOST": "myhost:7233", "TEMPORAL_NAMESPACE": "mynamespace"}):
            TemporalClientProvider.cancel_workflow("wf-123")

        mock_connect.assert_called_once_with("myhost:7233", namespace="mynamespace")
        mock_client.get_workflow_handle.assert_called_once_with("wf-123")
        mock_handle.cancel.assert_awaited_once()
```

- [ ] **Step 1.2: Run the tests to confirm they fail**

```
cd web && python manage.py test tests.test_temporal_client -v 2
```

Expected: `test_get_client_creates_fresh_connection_each_call` FAIL (cache returns same client), `test_reset_method_no_longer_exists` FAIL (`reset` still exists).

- [ ] **Step 1.3: Replace temporal_client.py with the stateless implementation**

Replace the entire file contents:

```python
# web/reNgine/temporal_client.py
"""
Temporal Client Provider for r3ngine.

Creates a fresh Temporal client per operation. Callers wrap operations in
asyncio.new_event_loop(); a temporalio Client is bound to the event loop it
was created in, so caching across loop boundaries raises gRPC errors. The
SDK manages its own gRPC channel pool — per-operation Client() costs ~5ms
locally and is the correct pattern for synchronous Django callers.
"""
import asyncio
import logging
import os

from temporalio.client import Client

logger = logging.getLogger(__name__)


class TemporalClientProvider:
    """Factory for Temporal client connections.

    Always creates a fresh connection. Do not add caching — see module
    docstring for why caching fails across asyncio.run() boundaries.
    """

    @classmethod
    async def get_client(cls) -> Client:
        """Return a freshly connected Temporal client.

        Returns:
            Client: A connected Temporal client instance.
        Raises:
            Exception: If the Temporal server is unreachable.
        """
        temporal_host = os.environ.get("TEMPORAL_HOST", "temporal:7233")
        namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
        logger.debug(f"[TemporalClientProvider] Connecting to {temporal_host} ns={namespace}")
        return await Client.connect(temporal_host, namespace=namespace)

    @classmethod
    def cancel_workflow(cls, workflow_id: str) -> None:
        """Cancel a running Temporal workflow synchronously (safe for Django views).

        Args:
            workflow_id: The Temporal workflow execution ID to cancel.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _cancel():
                client = await cls.get_client()
                handle = client.get_workflow_handle(workflow_id)
                await handle.cancel()
            loop.run_until_complete(_cancel())
        finally:
            loop.close()
```

- [ ] **Step 1.4: Remove `TemporalClientProvider.reset()` calls from temporal_schedule_utils.py**

In `web/reNgine/temporal_schedule_utils.py`, delete every occurrence of the line `TemporalClientProvider.reset()`. There are 8 occurrences — one at the top of each helper function. The line to remove looks like:

```python
    TemporalClientProvider.reset()   # <-- delete this line only
    loop = asyncio.new_event_loop()  # <-- keep this and everything after
```

After deletion, also remove the import of `TemporalClientProvider` if it is no longer referenced in the file. Verify with:

```
cd web && grep -n "TemporalClientProvider" reNgine/temporal_schedule_utils.py
```

If only `get_client` is still called inside the async helper functions, keep the import. If `reset` was the only usage, remove the import line.

- [ ] **Step 1.5: Remove `TemporalClientProvider.reset()` calls from tasks.py**

In `web/reNgine/tasks.py`, find and delete the two `TemporalClientProvider.reset()` calls. Locate them:

```
cd web && grep -n "TemporalClientProvider.reset" reNgine/tasks.py
```

Delete only those lines; leave the surrounding `asyncio.new_event_loop()` block intact.

- [ ] **Step 1.6: Run the tests to verify they pass**

```
cd web && python manage.py test tests.test_temporal_client -v 2
```

Expected: all 3 PASS.

- [ ] **Step 1.7: Run the full test suite for regressions**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -10
```

Expected: same pass count as before this change.

- [ ] **Step 1.8: Commit**

```bash
git add web/reNgine/temporal_client.py \
        web/reNgine/temporal_schedule_utils.py \
        web/reNgine/tasks.py \
        web/tests/test_temporal_client.py
git commit -m "fix(temporal): remove broken TemporalClientProvider cache

Client objects are event-loop-bound. Every caller already used
asyncio.new_event_loop() + TemporalClientProvider.reset() before
each call, making the cache a no-op that added confusion and a
potential multi-thread race. This commit removes the cache and
reset() entirely, making the stateless-connection behaviour explicit.

Closes: architecture review P0 finding #1"
```

---

### Task 2: Fix `osint()` daemon threads that escape Temporal durability

**Context:** Inside `web/reNgine/tasks.py`, the `osint()` scan function spawns `osint_orchestrator` in a daemon thread in two places:
1. Via `finish_osint()` at line ~1796 (when standard OSINT tasks produce results)
2. Directly at line ~1803 (when no standard OSINT results were produced)

Both use `threading.Thread(..., daemon=True)`. Daemon threads are not tracked by Temporal. If the Python worker process exits (crash, restart, scale-down) while `osint_orchestrator` is running, the Deep Pursuit pipeline dies silently with no Temporal history entry, no retry, and no way to detect the loss. Fix: call `osint_orchestrator` synchronously. The activity already has a heartbeat thread from `_run_task()` that keeps Temporal alive, so synchronous execution is safe.

**Files:**
- Modify: `web/reNgine/tasks.py`
- Modify: `web/tests/test_phase3c_migration.py` (test asserts threading — must be updated)

---

- [ ] **Step 2.1: Find the exact lines to change**

```
cd web && grep -n "finish_osint\|osint_orchestrator\|threading.Thread" reNgine/tasks.py | head -20
```

Note the line numbers for: the `finish_osint` function definition, the call to `finish_osint` inside `osint()`, and the direct `threading.Thread` block inside `osint()`.

- [ ] **Step 2.2: Write the failing test**

Add to `web/tests/test_temporal_activities.py`:

```python
import inspect
from django.test import TestCase


class TestOsintNoDaemonThreads(TestCase):
    def test_finish_osint_does_not_spawn_thread(self):
        """finish_osint must call osint_orchestrator directly, not in a daemon thread."""
        import reNgine.tasks as tasks_mod
        source = inspect.getsource(tasks_mod.finish_osint)
        self.assertNotIn(
            "threading.Thread",
            source,
            "finish_osint must not spawn a daemon thread — call osint_orchestrator synchronously",
        )

    def test_osint_function_does_not_spawn_thread_for_orchestrator(self):
        """The osint() task body must not launch osint_orchestrator in a daemon thread."""
        import reNgine.tasks as tasks_mod
        source = inspect.getsource(tasks_mod.osint)
        # The thread spawn at the end of osint() when results is empty must be gone
        self.assertNotIn(
            "daemon=True",
            source,
            "osint() must not spawn daemon threads — the Temporal activity heartbeat handles keep-alive",
        )
```

- [ ] **Step 2.3: Run the test to confirm it fails**

```
cd web && python manage.py test tests.test_temporal_activities.TestOsintNoDaemonThreads -v 2
```

Expected: both FAILs (daemon thread code still present).

- [ ] **Step 2.4: Fix `finish_osint` in tasks.py**

Locate `finish_osint` (around line 152) and replace it:

```python
def finish_osint(results, scan_history_id):
    """Trigger the Deep Pursuit OSINT pipeline after standard OSINT tasks complete.

    Called synchronously from within the osint() Temporal activity. The
    activity's heartbeat thread (started by _run_task) keeps Temporal alive
    while osint_orchestrator runs — no daemon thread needed.
    """
    from reNgine.osint_tasks import osint_orchestrator
    logger.info(f"[finish_osint] Starting Deep Pursuit pipeline for scan {scan_history_id}")
    osint_orchestrator(scan_history_id=scan_history_id)
    return results
```

- [ ] **Step 2.5: Fix the direct daemon thread inside `osint()` in tasks.py**

Locate the block around line 1801–1807 that reads:

```python
    logger.info('Starting Deep Pursuit OSINT Pipeline...')
    threading.Thread(
        target=osint_orchestrator,
        kwargs={'scan_history_id': self.scan.id},
        daemon=True
    ).start()
```

Replace it with:

```python
    logger.info('Starting Deep Pursuit OSINT Pipeline...')
    from reNgine.osint_tasks import osint_orchestrator
    osint_orchestrator(scan_history_id=self.scan.id)
```

- [ ] **Step 2.6: Update the test in test_phase3c_migration.py that expects threading**

In `web/tests/test_phase3c_migration.py`, find and update the two tests (around lines 185–195) that asserted `finish_osint` uses threading:

```python
# BEFORE:
def test_finish_osint_no_osint_orchestrator_delay(self):
    body = self._get_function_body(source, 'finish_osint')
    self.assertNotIn('.delay()', body,
                     "finish_osint must not call osint_orchestrator.delay")

def test_finish_osint_uses_threading(self):
    body = self._get_function_body(source, 'finish_osint')
    self.assertIn('threading.Thread', body,
                  "finish_osint must use threading.Thread for osint_orchestrator")

# AFTER — replace both with:
def test_finish_osint_no_osint_orchestrator_delay(self):
    body = self._get_function_body(source, 'finish_osint')
    self.assertNotIn('.delay()', body,
                     "finish_osint must not call osint_orchestrator.delay")

def test_finish_osint_calls_orchestrator_synchronously(self):
    body = self._get_function_body(source, 'finish_osint')
    self.assertNotIn('threading.Thread', body,
                     "finish_osint must call osint_orchestrator synchronously "
                     "(Temporal activity heartbeat thread handles keep-alive)")
    self.assertIn('osint_orchestrator', body,
                  "finish_osint must call osint_orchestrator")
```

- [ ] **Step 2.7: Run the updated tests**

```
cd web && python manage.py test tests.test_temporal_activities.TestOsintNoDaemonThreads tests.test_phase3c_migration -v 2
```

Expected: all PASS.

- [ ] **Step 2.8: Run the full suite for regressions**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -10
```

Expected: same pass count.

- [ ] **Step 2.9: Commit**

```bash
git add web/reNgine/tasks.py \
        web/tests/test_phase3c_migration.py \
        web/tests/test_temporal_activities.py
git commit -m "fix(temporal): call osint_orchestrator synchronously inside Temporal activity

finish_osint() and the fallback path in osint() both spawned daemon
threads for osint_orchestrator. Daemon threads are invisible to
Temporal — a worker crash while the thread ran caused silent data loss
with no retry or history entry.

The _run_task() heartbeat thread already keeps the Temporal activity
alive for long-running operations, so osint_orchestrator can run
synchronously within the activity without timing out.

Updates test_phase3c_migration to assert synchronous (not threaded)
invocation.

Closes: architecture review P0 finding #2"
```

---

## Phase 2 — Security

### Task 3: Add allowlist to `RunGenericTaskActivity`

**Context:** `RunGenericTaskActivity` imports a task function by name via `getattr(importlib.import_module("reNgine.tasks"), task_name)`. The `task_name` originates from the workflow `ctx` dict, which is seeded from `EngineType.tasks` in the database. An attacker with write access to that column could execute any top-level function in `reNgine.tasks` as a Temporal activity — including `sync_all_scans_to_graph`, `send_scan_notif`, and administrative helpers. An allowlist closes this trust boundary to scan-task functions only.

**Files:**
- Modify: `web/reNgine/temporal_activities.py`
- Modify: `web/tests/test_temporal_activities.py`

---

- [ ] **Step 3.1: Write the failing tests**

Add to `web/tests/test_temporal_activities.py`:

```python
from unittest.mock import patch
from django.test import TestCase


class TestRunGenericTaskAllowlist(TestCase):

    @patch("reNgine.temporal_activities._run_task", return_value=True)
    @patch("reNgine.temporal_activities.activity")
    def test_allowed_task_osint_does_not_raise(self, mock_activity, mock_run):
        """osint is a permitted scan task — must not raise on the allowlist check."""
        mock_activity.logger = __import__('logging').getLogger('test')
        from reNgine.temporal_activities import run_generic_task_activity
        # Calling the underlying function (activity decorator is metadata only)
        run_generic_task_activity({"scan_history_id": 1}, "osint", "OSINT Scan")

    @patch("reNgine.temporal_activities.activity")
    def test_disallowed_task_raises_value_error(self, mock_activity):
        """sync_all_scans_to_graph is not a scan task — must raise ValueError."""
        mock_activity.logger = __import__('logging').getLogger('test')
        from reNgine.temporal_activities import run_generic_task_activity
        with self.assertRaises(ValueError) as ctx:
            run_generic_task_activity(
                {"scan_history_id": 1}, "sync_all_scans_to_graph", "Sync"
            )
        self.assertIn("not permitted", str(ctx.exception))

    @patch("reNgine.temporal_activities.activity")
    def test_disallowed_task_send_scan_notif_raises(self, mock_activity):
        """send_scan_notif is not a scan task — must be blocked."""
        mock_activity.logger = __import__('logging').getLogger('test')
        from reNgine.temporal_activities import run_generic_task_activity
        with self.assertRaises(ValueError):
            run_generic_task_activity(
                {"scan_history_id": 1}, "send_scan_notif", "Notif"
            )
```

- [ ] **Step 3.2: Run to confirm tests fail**

```
cd web && python manage.py test tests.test_temporal_activities.TestRunGenericTaskAllowlist -v 2
```

Expected: `test_disallowed_task_*` tests FAIL (no `ValueError` raised currently).

- [ ] **Step 3.3: Add the allowlist constant and update `run_generic_task_activity`**

In `web/reNgine/temporal_activities.py`, immediately above the `run_generic_task_activity` function definition, add the allowlist constant:

```python
# Allowlist of task names that may be invoked via RunGenericTaskActivity.
# Only scan-task functions belong here. Administrative helpers, notification
# senders, and graph sync functions must NOT be added — use dedicated activities.
_PERMITTED_GENERIC_TASKS = frozenset({
    # Tier 1 — Discovery
    "subdomain_discovery", "amass_intel_discovery", "firewall_vpn_scan",
    "osint", "spiderfoot_scan",
    # Tier 2 — Enumeration
    "http_crawl", "port_scan", "screenshot", "fetch_url",
    # Tier 3/4 — Fuzzing
    "dir_file_fuzz",
    # Tier 5 — Analysis
    "web_api_discovery", "waf_detection", "secret_scanning",
    # Tier 6 — Assessment
    "vulnerability_scan", "waf_bypass", "brute_force_scan",
    "nuclei_scan", "crlfuzz_scan", "dalfox_xss_scan", "s3scanner",
    "acunetix_scan", "cpanel_scan", "wpscan_scan", "react2shell_scan",
    "semgrep_scan",
    # Tier 7 — Post-processing (only scan-scoped variants)
    "correlate_vulnerabilities", "calculate_risk_scores",
    "generate_impact_assessment",
})
```

Then replace the body of `run_generic_task_activity` with:

```python
@activity.defn(name="RunGenericTaskActivity")
def run_generic_task_activity(
    ctx: dict,
    task_name: str,
    description: str = None,
    extra_args: dict = None,
) -> bool:
    """Execute a permitted scan task by name inside a Temporal activity.

    Only task names in _PERMITTED_GENERIC_TASKS are allowed. Raises ValueError
    for any name outside that set to prevent execution of admin/utility functions
    via the generic dispatch path.
    """
    import importlib

    if task_name not in _PERMITTED_GENERIC_TASKS:
        raise ValueError(
            f"Task '{task_name}' is not permitted via RunGenericTaskActivity. "
            f"Add it to _PERMITTED_GENERIC_TASKS only if it is a scan-task function."
        )

    activity.logger.info(
        f"[RunGenericTaskActivity] task={task_name} scan_id={ctx.get('scan_history_id')}"
    )

    tasks_module = importlib.import_module("reNgine.tasks")
    task_func = getattr(tasks_module, task_name, None)

    if not task_func:
        raise ValueError(f"Task function '{task_name}' not found in reNgine.tasks.")

    run_args = extra_args or {}
    return _run_task(
        task_func,
        ctx,
        task_name=task_name,
        description=description or " ".join(task_name.split("_")).capitalize(),
        **run_args,
    )
```

- [ ] **Step 3.4: Run the tests**

```
cd web && python manage.py test tests.test_temporal_activities.TestRunGenericTaskAllowlist -v 2
```

Expected: all 3 PASS.

- [ ] **Step 3.5: Commit**

```bash
git add web/reNgine/temporal_activities.py web/tests/test_temporal_activities.py
git commit -m "security: add _PERMITTED_GENERIC_TASKS allowlist to RunGenericTaskActivity

Without an allowlist, any function in reNgine.tasks could be invoked
as a Temporal activity if its name appeared in EngineType.tasks in the
database. The allowlist restricts dispatch to known scan-task functions
only. Admin helpers, graph sync, and notification senders are excluded.

Closes: architecture review P1 security finding"
```

---

### Task 4: Fix LLM module security vulnerabilities

**Context:** Three security issues in `web/reNgine/llm.py`:
1. `_call_openai`, `_call_anthropic`, and `_call_gemini` all use `verify=False` + `urllib3.disable_warnings()` — TLS certificate validation is disabled with no justification for calls to well-known public APIs.
2. `_call_gemini` passes the API key as a URL query parameter (`?key=...`). The key appears in server access logs, HTTP proxy logs, and browser history.
3. `_call_anthropic` bundles the system message into the user message string instead of using Anthropic's dedicated `"system"` field, which changes model behaviour and breaks prompt caching.
4. `_call_anthropic` is missing `response.raise_for_status()` — HTTP 4xx/5xx responses silently return malformed JSON, causing confusing downstream errors.

**Files:**
- Modify: `web/reNgine/llm.py`
- Create: `web/tests/test_llm.py`

---

- [ ] **Step 4.1: Write the failing tests**

```python
# web/tests/test_llm.py
import logging
from unittest.mock import MagicMock, patch
from django.test import TestCase


def _mock_config(provider, model="test-model", api_key="sk-test"):
    cfg = MagicMock()
    cfg.is_active = True
    cfg.provider = provider
    cfg.selected_model = model
    cfg.api_key = api_key
    return cfg


class TestLLMSecurityFixes(TestCase):

    def _make_generator(self, provider):
        from reNgine.definitions import OPENAI, ANTHROPIC, GEMINI
        with patch("dashboard.models.LLMConfig.objects.filter") as mock_filter:
            mock_filter.return_value.first.return_value = _mock_config(provider)
            from reNgine.llm import LLMBaseGenerator
            return LLMBaseGenerator(logging.getLogger("test"))

    @patch("requests.post")
    def test_openai_uses_ssl_verification(self, mock_post):
        """OpenAI call must not disable TLS verification."""
        from reNgine.definitions import OPENAI
        gen = self._make_generator(OPENAI)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": "ok"}}]},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        gen._call_openai("sys", "user")
        _, kwargs = mock_post.call_args
        self.assertTrue(
            kwargs.get("verify", True),
            "OpenAI HTTP call must use SSL verification (verify=True or omitted)",
        )

    @patch("requests.post")
    def test_anthropic_uses_ssl_verification(self, mock_post):
        """Anthropic call must not disable TLS verification."""
        from reNgine.definitions import ANTHROPIC
        gen = self._make_generator(ANTHROPIC)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"content": [{"text": "ok"}]},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        gen._call_anthropic("sys", "user")
        _, kwargs = mock_post.call_args
        self.assertTrue(
            kwargs.get("verify", True),
            "Anthropic HTTP call must use SSL verification (verify=True or omitted)",
        )

    @patch("requests.post")
    def test_gemini_api_key_in_header_not_url(self, mock_post):
        """Gemini API key must be in a request header, not the URL query string."""
        from reNgine.definitions import GEMINI
        gen = self._make_generator(GEMINI)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        gen._call_gemini("sys", "user")
        call_args = mock_post.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        self.assertNotIn("key=", url, "Gemini API key must not appear in the URL query string")
        headers = call_args[1].get("headers", {})
        self.assertIn("x-goog-api-key", headers, "Gemini API key must be in x-goog-api-key header")

    @patch("requests.post")
    def test_anthropic_uses_system_field(self, mock_post):
        """Anthropic request must use the 'system' field, not concatenate into user content."""
        from reNgine.definitions import ANTHROPIC
        gen = self._make_generator(ANTHROPIC)
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"content": [{"text": "ok"}]},
        )
        mock_post.return_value.raise_for_status = MagicMock()
        gen._call_anthropic("MY_SYSTEM_PROMPT", "user message here")
        _, kwargs = mock_post.call_args
        payload = kwargs.get("json", {})
        self.assertIn("system", payload, "Anthropic request payload must include 'system' field")
        self.assertEqual(payload["system"], "MY_SYSTEM_PROMPT")
        user_content = payload["messages"][0]["content"]
        self.assertNotIn(
            "MY_SYSTEM_PROMPT", user_content,
            "System prompt must not be concatenated into user message content",
        )
```

- [ ] **Step 4.2: Run to confirm tests fail**

```
cd web && python manage.py test tests.test_llm -v 2
```

Expected: 4 FAILs.

- [ ] **Step 4.3: Fix the three HTTP call methods in llm.py**

In `web/reNgine/llm.py`, replace `_call_openai`, `_call_anthropic`, and `_call_gemini` with:

```python
    def _call_openai(self, system_message, user_message):
        if not self.api_key:
            return "Error: OpenAI API Key not set"
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            data = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message},
                ],
            }
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self.logger.error(f"OpenAI Error: {str(e)}")
            return f"Error: {str(e)}"

    def _call_anthropic(self, system_message, user_message):
        if not self.api_key:
            return "Error: Anthropic API Key not set"
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            data = {
                "model": self.model_name,
                "max_tokens": 1024,
                "system": system_message,
                "messages": [{"role": "user", "content": user_message}],
            }
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            self.logger.error(f"Anthropic Error: {str(e)}")
            return f"Error: {str(e)}"

    def _call_gemini(self, system_message, user_message):
        if not self.api_key:
            return "Error: Gemini API Key not set"
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            }
            data = {
                "contents": [{"parts": [{"text": f"{system_message}\n\n{user_message}"}]}],
            }
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            self.logger.error(f"Gemini Error: {str(e)}")
            return f"Error: {str(e)}"
```

Also remove all `import urllib3` and `urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)` lines from `llm.py`.

- [ ] **Step 4.4: Run the tests**

```
cd web && python manage.py test tests.test_llm -v 2
```

Expected: all 4 PASS.

- [ ] **Step 4.5: Run full suite for regressions**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -5
```

Expected: same pass count.

- [ ] **Step 4.6: Commit**

```bash
git add web/reNgine/llm.py web/tests/test_llm.py
git commit -m "security: fix LLM HTTP client vulnerabilities

- Remove verify=False from OpenAI, Anthropic, Gemini calls — TLS
  certificate validation was disabled silently with urllib3.disable_warnings
- Remove all urllib3 import + disable_warnings blocks
- Move Gemini API key from URL query param to x-goog-api-key header
  (key was visible in access logs and proxy logs)
- Fix Anthropic: system_message now uses the dedicated 'system' field
  rather than being concatenated into user message content — fixes
  model behaviour and enables prompt caching headers in future
- Add missing response.raise_for_status() to Anthropic call

Closes: architecture review LLM security findings"
```

---

## Phase 3 — Reliability

### Task 5: Add explicit retry policies to all network-bound activities

**Context:** Temporal's default retry policy (unlimited retries, exponential backoff capping at 100s) applies to every activity that does not specify one. Only `RunStressToolActivity` has an explicit `RetryPolicy(maximum_attempts=1)`. Discovery tools that call external DNS resolvers, live HTTP targets, and external APIs can accumulate unbounded retry storms if they fail: a `subdomain_discovery` activity hitting a rate-limited resolver could retry dozens of times before the `start_to_close_timeout` fires. This task adds explicit, purpose-matched retry policies to all activities in `MasterScanWorkflow`.

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`

---

- [ ] **Step 5.1: Add retry policy constants at the top of temporal_workflows.py**

`RetryPolicy` is already imported in `temporal_workflows.py` (it is used by `StressTestWorkflow`). After the existing import block, add:

```python
# Retry policy presets — applied explicitly to every execute_activity call.
# Default Temporal policy (unlimited, backoff to 100s) is intentionally overridden.

# Long-running scan tools (> 1hr timeout): 2 attempts only, to bound wall-clock time.
_RETRY_LONG_SCAN = RetryPolicy(
    maximum_attempts=2,
    initial_interval=timedelta(minutes=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
)
# Network-bound tools (< 1hr timeout): 3 attempts, 30s initial backoff.
_RETRY_NETWORK_SCAN = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
)
# Internal DB/parse activities — quick, idempotent: 5 attempts, short backoff.
_RETRY_INTERNAL = RetryPolicy(
    maximum_attempts=5,
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=1.5,
    maximum_interval=timedelta(seconds=30),
)
# AI/LLM activities: may hit rate limits — 3 attempts, 30s initial backoff.
_RETRY_LLM = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
)
```

- [ ] **Step 5.2: Apply retry policies to every `execute_activity` call in `MasterScanWorkflow.run()`**

Add `retry_policy=` to each call per this table. The pattern for every change is:

```python
# BEFORE:
await workflow.execute_activity(
    "RunSubdomainDiscoveryActivity",
    ctx,
    start_to_close_timeout=timedelta(hours=2),
    heartbeat_timeout=timedelta(minutes=2),
    task_queue="python-orchestrator-queue"
)

# AFTER:
await workflow.execute_activity(
    "RunSubdomainDiscoveryActivity",
    ctx,
    start_to_close_timeout=timedelta(hours=2),
    heartbeat_timeout=timedelta(minutes=2),
    retry_policy=_RETRY_LONG_SCAN,
    task_queue="python-orchestrator-queue"
)
```

Apply these policies to every activity in `MasterScanWorkflow.run()`:

| Activity | Policy |
|---|---|
| `TargetProfilingActivity` | `_RETRY_INTERNAL` |
| `ParseDiscoveryResultsActivity` | `_RETRY_INTERNAL` |
| `ParseHTTPCrawlResultsActivity` | `_RETRY_INTERNAL` |
| `ParseEnumerationResultsActivity` | `_RETRY_INTERNAL` |
| `ParseFuzzResultsActivity` | `_RETRY_INTERNAL` |
| `ParseAnalysisResultsActivity` | `_RETRY_INTERNAL` |
| `ParseAssessmentResultsActivity` | `_RETRY_INTERNAL` |
| `CorrelateVulnerabilitiesActivity` | `_RETRY_INTERNAL` |
| `CalculateRiskScoresActivity` | `_RETRY_INTERNAL` |
| `SendScanNotificationActivity` | `_RETRY_INTERNAL` |
| `RunFirewallVPNScanActivity` | `_RETRY_NETWORK_SCAN` |
| `RunScreenshotActivity` | `_RETRY_NETWORK_SCAN` |
| `RunWebAPIDiscoveryActivity` | `_RETRY_NETWORK_SCAN` |
| `RunWAFDetectionActivity` | `_RETRY_NETWORK_SCAN` |
| `RunWAFBypassActivity` | `_RETRY_NETWORK_SCAN` |
| `RunBruteForceScanActivity` | `_RETRY_NETWORK_SCAN` |
| `SyncGraphActivity` | `_RETRY_NETWORK_SCAN` |
| `RunGenericTaskActivity` (osint, spiderfoot) | `_RETRY_LONG_SCAN` |
| `RunSubdomainDiscoveryActivity` | `_RETRY_LONG_SCAN` |
| `RunAmassIntelDiscoveryActivity` | `_RETRY_LONG_SCAN` |
| `RunHTTPCrawlActivity` | `_RETRY_LONG_SCAN` |
| `RunPortScanActivity` | `_RETRY_LONG_SCAN` |
| `RunFetchURLActivity` | `_RETRY_LONG_SCAN` |
| `RunDirFileFuzzActivity` | `_RETRY_LONG_SCAN` |
| `RunSecretScanningActivity` | `_RETRY_LONG_SCAN` |
| `GenerateImpactAssessmentActivity` | `_RETRY_LLM` |

`RunStressToolActivity` already has `RetryPolicy(maximum_attempts=1)` — leave it unchanged.

- [ ] **Step 5.3: Run the full suite**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -5
```

Expected: same pass count (retry policies don't affect unit tests).

- [ ] **Step 5.4: Commit**

```bash
git add web/reNgine/temporal_workflows.py
git commit -m "reliability: add explicit retry policies to all Temporal activities

Default policy (unlimited retries, backoff to 100s) was a hidden risk
for network-bound discovery tools that could retry indefinitely against
rate-limited DNS resolvers or slow hosts.

Policy taxonomy:
  Long scans (> 1hr): 2 attempts, 1min initial backoff
  Network scans: 3 attempts, 30s initial backoff
  Internal DB/parse: 5 attempts, 5s initial backoff
  AI/LLM: 3 attempts, 30s initial backoff (rate limit handling)
  Stress tools: unchanged (1 attempt — not idempotent)

Closes: architecture review P1 reliability finding"
```

---

## Phase 4 — Type Safety

### Task 6: Create `ScanContext` TypedDict for workflow context

**Context:** The workflow context is an untyped `dict` passed through every workflow↔activity boundary. Activities silently return `None` for missing keys, masking bugs at definition time and surfacing them at runtime during actual scans. A `TypedDict` makes the contract explicit, enables IDE autocomplete, and is a zero-runtime-cost documentation layer — `TypedDict` is purely a type-checking construct, so no existing behaviour changes.

**Files:**
- Create: `web/reNgine/scan_context.py`
- Modify: `web/reNgine/temporal_activities.py`
- Modify: `web/reNgine/temporal_workflows.py`
- Modify: `web/tests/test_temporal_activities.py`

---

- [ ] **Step 6.1: Create web/reNgine/scan_context.py**

```python
# web/reNgine/scan_context.py
"""
TypedDict definitions for Temporal workflow context.

ScanContext is the primary data contract between workflow orchestrators and
activities. TypedDict is a zero-runtime-cost type annotation — it produces
no class at runtime beyond a plain dict. It enables IDE autocomplete and
mypy/pyright validation without adding Pydantic or dataclasses.

Usage:
    from reNgine.scan_context import ScanContext
    ctx: ScanContext = {
        "scan_history_id": 1,
        "engine_id": 2,
        "domain_id": 3,
    }
"""
from typing import Any, Dict, List, Optional
try:
    from typing import Required
except ImportError:
    from typing_extensions import Required

from typing import TypedDict


class ScanContext(TypedDict, total=False):
    """Temporal workflow context for a full scan, subscan, or stress test.

    Fields marked Required[] must be present when the workflow starts.
    All other fields are optional and may be added by activities as the
    scan progresses.
    """
    # Required at workflow start
    scan_history_id: Required[int]
    engine_id: Required[int]
    domain_id: Required[int]

    # Set by TargetProfilingActivity
    domain_name: str
    results_dir: str
    yaml_configuration: Dict[str, Any]
    tasks: List[str]

    # Subscan / per-subdomain fields
    subdomain_id: Optional[int]
    subscan_id: Optional[int]
    subdomain_name: Optional[str]
    subdomain_http_url: Optional[str]

    # Scan configuration
    out_of_scope_subdomains: List[str]
    starting_point_path: str
    excluded_paths: List[str]
    imported_subdomains: List[str]

    # Activity tracking
    activity_id: Optional[int]
    track: bool

    # Stress test fields (populated by InitStressTestActivity)
    target_domain_name: Optional[str]
    stress_config: Optional[Dict[str, Any]]
    resolved_endpoints: Optional[List[str]]
    stress_result_id: Optional[int]
    current_endpoint: Optional[str]
    current_tool: Optional[str]

    # API discovery
    api_discovery_tools: Optional[List[str]]
    kr_wordlist: Optional[str]
```

- [ ] **Step 6.2: Write a test**

Add to `web/tests/test_temporal_activities.py`:

```python
class TestScanContext(TestCase):
    def test_required_fields_accepted(self):
        from reNgine.scan_context import ScanContext
        ctx: ScanContext = {
            "scan_history_id": 1,
            "engine_id": 2,
            "domain_id": 3,
        }
        self.assertEqual(ctx["scan_history_id"], 1)

    def test_optional_fields_accepted(self):
        from reNgine.scan_context import ScanContext
        ctx: ScanContext = {
            "scan_history_id": 1,
            "engine_id": 2,
            "domain_id": 3,
            "tasks": ["osint", "port_scan"],
            "subdomain_id": 5,
        }
        self.assertEqual(ctx["tasks"], ["osint", "port_scan"])
```

- [ ] **Step 6.3: Run the test**

```
cd web && python manage.py test tests.test_temporal_activities.TestScanContext -v 2
```

Expected: PASS.

- [ ] **Step 6.4: Update activity function signatures in temporal_activities.py**

At the top of `web/reNgine/temporal_activities.py`, add the import:

```python
from reNgine.scan_context import ScanContext
```

Then update every activity function signature from `ctx: dict` to `ctx: ScanContext`. There are approximately 25 activities. The pattern:

```python
# BEFORE:
def target_profiling_activity(ctx: dict) -> dict:

# AFTER:
def target_profiling_activity(ctx: ScanContext) -> ScanContext:
```

Apply to all activities that accept a `ctx` parameter.

- [ ] **Step 6.5: Update workflow signatures in temporal_workflows.py**

In `web/reNgine/temporal_workflows.py`, add to the `with workflow.unsafe.imports_passed_through():` block:

```python
with workflow.unsafe.imports_passed_through():
    from reNgine.scan_context import ScanContext
```

Update `MasterScanWorkflow.run(self, ctx: Dict[str, Any])` → `ctx: ScanContext`.
Update `SubScanWorkflow.run(self, ctx: Dict[str, Any], scan_type: str)` → `ctx: ScanContext`.
Update `StressTestWorkflow.run(self, ctx: Dict[str, Any])` → `ctx: ScanContext`.

- [ ] **Step 6.6: Run the full suite**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -5
```

Expected: same pass count.

- [ ] **Step 6.7: Commit**

```bash
git add web/reNgine/scan_context.py \
        web/reNgine/temporal_activities.py \
        web/reNgine/temporal_workflows.py \
        web/tests/test_temporal_activities.py
git commit -m "refactor: introduce ScanContext TypedDict for workflow context

Replaces Dict[str, Any] across all workflow/activity boundaries with
a typed ScanContext. Zero runtime cost — TypedDict is a type-checking
construct only. Enables IDE autocomplete and mypy validation of required
vs optional context fields. No behaviour changes."
```

---

## Phase 5 — Architecture

### Task 7: Replace `SubScanWorkflow` if/elif dispatch with a registry

**Context:** `SubScanWorkflow.run()` has a long if/elif chain that routes `scan_type` strings to activity calls. Adding a new subscan type requires modifying workflow logic. The dispatch registry pattern makes the routing declarative and keeps the two special cases (`baddns` modifies ctx; `vulnerability_scan` has Tier 7 post-steps) explicitly documented rather than buried in elif branches.

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`
- Modify: `web/tests/test_temporal_activities.py`

---

- [ ] **Step 7.1: Write the failing test**

Add to `web/tests/test_temporal_activities.py`:

```python
class TestSubScanDispatchRegistry(TestCase):
    def test_all_known_scan_types_in_registry(self):
        from reNgine.temporal_workflows import _SUBSCAN_DISPATCH
        required = {
            "osint", "subdomain_discovery", "port_scan", "fetch_url",
            "dir_file_fuzz", "screenshot", "waf_detection",
            "vulnerability_scan", "baddns",
        }
        for t in required:
            self.assertIn(t, _SUBSCAN_DISPATCH, f"'{t}' is missing from _SUBSCAN_DISPATCH")

    def test_regular_entry_has_required_keys(self):
        from reNgine.temporal_workflows import _SUBSCAN_DISPATCH
        for scan_type, entry in _SUBSCAN_DISPATCH.items():
            if entry is None:
                continue  # special-case — handled inline
            self.assertIn("activity", entry, f"{scan_type}: missing 'activity' key")
            self.assertIn("timeout", entry, f"{scan_type}: missing 'timeout' key")
            self.assertIn("args_builder", entry, f"{scan_type}: missing 'args_builder' key")
```

- [ ] **Step 7.2: Run to confirm tests fail**

```
cd web && python manage.py test tests.test_temporal_activities.TestSubScanDispatchRegistry -v 2
```

Expected: FAIL — `_SUBSCAN_DISPATCH` does not exist.

- [ ] **Step 7.3: Add the registry to temporal_workflows.py**

Add this module-level constant immediately before the `SubScanWorkflow` class definition in `web/reNgine/temporal_workflows.py`:

```python
# Registry for SubScanWorkflow dispatch.
# value=None means the scan type has special handling and is coded inline.
# value=dict means standard dispatch: call `activity` with args from `args_builder`.
_SUBSCAN_DISPATCH = {
    "osint": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "osint", "OSINT Scan", {"host": ctx.get("subdomain_name", "")}
        ],
    },
    "subdomain_discovery": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "subdomain_discovery", "Subdomain Discovery",
            {"host": ctx.get("subdomain_name", "")},
        ],
    },
    "port_scan": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "port_scan", "Port Scan",
            {"hosts": [ctx.get("subdomain_name", "")]},
        ],
    },
    "fetch_url": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "fetch_url", "Fetch URL",
            {"urls": [ctx.get("subdomain_http_url") or f"http://{ctx.get('subdomain_name', '')}/"]},
        ],
    },
    "dir_file_fuzz": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [ctx, "dir_file_fuzz", "Dir File Fuzz", {}],
    },
    "screenshot": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=1),
        "args_builder": lambda ctx: [ctx, "screenshot", "Screenshot", {}],
    },
    "waf_detection": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(minutes=30),
        "args_builder": lambda ctx: [ctx, "waf_detection", "WAF Detection", {}],
    },
    # Special cases — handled with inline logic below:
    "vulnerability_scan": None,  # Has Tier 7 post-steps (correlation, risk, APME)
    "baddns": None,              # Modifies ctx before dispatch
}
```

- [ ] **Step 7.4: Refactor SubScanWorkflow.run() to use the registry**

Replace the if/elif chain inside `SubScanWorkflow.run()` with:

```python
        yaml_configuration = ctx.get("yaml_configuration", {})
        subdomain_name = ctx.get("subdomain_name", "")
        subdomain_http_url = ctx.get("subdomain_http_url")
        target_url = subdomain_http_url or f"http://{subdomain_name}/"

        dispatch = _SUBSCAN_DISPATCH.get(scan_type)

        if scan_type == "baddns":
            ctx_baddns = {
                **ctx,
                "yaml_configuration": {
                    **ctx.get("yaml_configuration", {}),
                    "subdomain_discovery": {
                        **ctx.get("yaml_configuration", {}).get("subdomain_discovery", {}),
                        "uses_tools": ["baddns"],
                    },
                },
            }
            await workflow.execute_activity(
                "RunGenericTaskActivity",
                args=[ctx_baddns, "subdomain_discovery", "Baddns Scan", {"host": subdomain_name}],
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )

        elif scan_type == "vulnerability_scan":
            await workflow.execute_activity(
                "RunGenericTaskActivity",
                args=[ctx, "vulnerability_scan", "Vulnerability Scan", {"urls": [target_url]}],
                start_to_close_timeout=timedelta(hours=6),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )
            await workflow.execute_activity(
                "CorrelateVulnerabilitiesActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
            await workflow.execute_activity(
                "CalculateRiskScoresActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
            apme_config = yaml_configuration.get("attack_path_modeling", {})
            vuln_scan_config = yaml_configuration.get("vulnerability_scan", {})
            if apme_config.get("enabled", False) or vuln_scan_config.get("run_apme", False):
                await workflow.execute_activity(
                    "SyncGraphActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                )

        elif dispatch is not None:
            args = dispatch["args_builder"](ctx)
            await workflow.execute_activity(
                dispatch["activity"],
                args=args,
                start_to_close_timeout=dispatch["timeout"],
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )

        else:
            raise ValueError(
                f"Unknown subscan type: {scan_type!r}. "
                "Add it to _SUBSCAN_DISPATCH in temporal_workflows.py."
            )
```

- [ ] **Step 7.5: Run the tests**

```
cd web && python manage.py test tests.test_temporal_activities.TestSubScanDispatchRegistry -v 2
```

Expected: PASS.

- [ ] **Step 7.6: Run full suite**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -5
```

Expected: same pass count.

- [ ] **Step 7.7: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/tests/test_temporal_activities.py
git commit -m "refactor: replace SubScanWorkflow if/elif chain with dispatch registry

New scan types can be added by adding an entry to _SUBSCAN_DISPATCH
rather than modifying workflow logic. Special cases (baddns, vulnerability_scan)
remain as inline blocks with explicit comments. Retry policies added
to all subscan activity calls."
```

---

### Task 8: Remove the unimplemented checkpoint stub

**Context:** `LoadCheckpointActivity` and `SaveCheckpointActivity` both contain only `# TODO` comments — they return empty state and `True` respectively without persisting anything. The `_check_paused()` helper saves an empty dict and the loaded checkpoint is never used. This creates false confidence that crash-recovery checkpointing is implemented. Temporal's own event history already provides durable resume from the last completed activity — the checkpoint layer is unnecessary. Removing it simplifies the workflow and eliminates dead activity registrations.

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`
- Modify: `web/reNgine/temporal_activities.py`
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`
- Modify: `web/tests/test_temporal_activities.py`

---

- [ ] **Step 8.1: Write the failing tests**

Add to `web/tests/test_temporal_activities.py`:

```python
class TestCheckpointStubRemoval(TestCase):
    def test_load_checkpoint_activity_removed(self):
        """LoadCheckpointActivity stub must be removed — Temporal handles resumption."""
        from reNgine import temporal_activities
        self.assertFalse(
            hasattr(temporal_activities, "load_checkpoint_activity"),
            "load_checkpoint_activity must be removed; use Temporal event history for crash recovery",
        )

    def test_save_checkpoint_activity_removed(self):
        from reNgine import temporal_activities
        self.assertFalse(
            hasattr(temporal_activities, "save_checkpoint_activity"),
            "save_checkpoint_activity must be removed; use Temporal event history for crash recovery",
        )
```

- [ ] **Step 8.2: Run to confirm tests fail**

```
cd web && python manage.py test tests.test_temporal_activities.TestCheckpointStubRemoval -v 2
```

Expected: both FAIL.

- [ ] **Step 8.3: Delete checkpoint activities from temporal_activities.py**

Delete the complete `load_checkpoint_activity` and `save_checkpoint_activity` function definitions from `web/reNgine/temporal_activities.py`.

- [ ] **Step 8.4: Remove checkpoint calls from MasterScanWorkflow in temporal_workflows.py**

In `MasterScanWorkflow.__init__`, remove `self._checkpoint_state: Dict[str, Any] = {}`.

In `MasterScanWorkflow.run()`, remove:

```python
# Remove these two blocks:
self._checkpoint_state = await workflow.execute_activity(
    "LoadCheckpointActivity",
    ctx,
    start_to_close_timeout=timedelta(seconds=30),
    task_queue="python-orchestrator-queue"
)
```

Replace `_check_paused()` with the simplified version (no `SaveCheckpointActivity` call):

```python
async def _check_paused(self) -> None:
    """Block at a tier boundary if a pause signal was received.

    Temporal's event history handles durability — no explicit checkpoint
    is needed. The workflow simply waits for the resume signal.
    """
    if self._paused:
        workflow.logger.info("MasterScanWorkflow PAUSED — waiting for resume signal.")
        await workflow.wait_condition(lambda: not self._paused)
        workflow.logger.info("MasterScanWorkflow RESUMED.")
```

Update `get_current_state()` query handler to remove `checkpoint_state`:

```python
@workflow.query(name="get_current_state")
def get_current_state(self) -> Dict[str, Any]:
    return {"paused": self._paused}
```

- [ ] **Step 8.5: Remove checkpoint activity registrations from run_temporal_orchestrator.py**

In `web/scanEngine/management/commands/run_temporal_orchestrator.py`:

1. Remove `load_checkpoint_activity, save_checkpoint_activity` from the import statement.
2. Remove both from the `all_activities` list.

- [ ] **Step 8.6: Run the tests**

```
cd web && python manage.py test tests.test_temporal_activities.TestCheckpointStubRemoval -v 2
```

Expected: PASS.

- [ ] **Step 8.7: Run full suite**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -5
```

Expected: same pass count.

- [ ] **Step 8.8: Commit**

```bash
git add web/reNgine/temporal_workflows.py \
        web/reNgine/temporal_activities.py \
        web/scanEngine/management/commands/run_temporal_orchestrator.py \
        web/tests/test_temporal_activities.py
git commit -m "refactor: remove unimplemented checkpoint stub activities

LoadCheckpointActivity and SaveCheckpointActivity were stubs returning
empty state with TODO comments. Temporal's event history already provides
durable crash recovery — the workflow resumes from the last completed
activity automatically with no application-level checkpoint needed.

Simplifies _check_paused() to use only workflow.wait_condition().
Removes 2 registered activities and ~40 lines of misleading stub code."
```

---

## Phase 6 — Technical Debt

### Task 9: Rename Celery artifacts to Temporal-appropriate names

**Context:** `ScanHistory.celery_ids`, `SubScan.celery_ids`, `ScanActivity.celery_id`, and `CELERY_TASK_STATUSES` all carry the name of the removed Celery integration. These cause confusion when searching the codebase for `celery` (8 files still match). This task renames them via Django migrations. Note that `api/serializers.py` exposes `celery_ids` over the REST API — this is a breaking API change; any external API clients using that field must be updated.

**Files:**
- Modify: `web/startScan/models.py`
- Create: `web/startScan/migrations/` (auto-generated)
- Modify: `web/reNgine/definitions.py`
- Modify: `web/reNgine/temporal_activities.py`
- Modify: `web/api/serializers.py`
- Modify: `web/tests/test_temporal_orchestration.py`

---

- [ ] **Step 9.1: Find all references to the old names**

```
cd web && grep -rn "celery_ids\|\.celery_id\b\|CELERY_TASK_STATUSES" --include="*.py" . | grep -v ".pyc"
```

Note every file returned — all must be updated.

- [ ] **Step 9.2: Rename fields in startScan/models.py**

In `web/startScan/models.py`, make these renames:

```python
# ScanHistory — find line with celery_ids:
# BEFORE:
celery_ids = ArrayField(models.CharField(max_length=100), blank=True, default=list)
# AFTER:
workflow_ids = ArrayField(models.CharField(max_length=100), blank=True, default=list)

# SubScan — find line with celery_ids:
# BEFORE:
celery_ids = ArrayField(models.CharField(max_length=100), blank=True, default=list)
# AFTER:
workflow_ids = ArrayField(models.CharField(max_length=100), blank=True, default=list)

# ScanActivity — find line with celery_id:
# BEFORE:
celery_id = models.CharField(max_length=100, blank=True, null=True)
# AFTER:
execution_id = models.CharField(max_length=100, blank=True, null=True)
```

- [ ] **Step 9.3: Generate the migration**

```
cd web && python manage.py makemigrations startScan --name rename_celery_fields
```

Expected: creates `web/startScan/migrations/00XX_rename_celery_fields.py`. Open the generated file and verify it contains three `RenameField` operations — one for each renamed field. If Django generated `RemoveField` + `AddField` instead of `RenameField`, edit the migration manually to use `RenameField` to avoid data loss.

```python
# Example of what the migration should contain:
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [("startScan", "00XX_previous")]

    operations = [
        migrations.RenameField(
            model_name="scanhistory", old_name="celery_ids", new_name="workflow_ids"
        ),
        migrations.RenameField(
            model_name="subscan", old_name="celery_ids", new_name="workflow_ids"
        ),
        migrations.RenameField(
            model_name="scanactivity", old_name="celery_id", new_name="execution_id"
        ),
    ]
```

- [ ] **Step 9.4: Apply the migration**

```
cd web && python manage.py migrate startScan
```

Expected: `OK` with no errors.

- [ ] **Step 9.5: Rename CELERY_TASK_STATUSES in definitions.py**

In `web/reNgine/definitions.py`, rename the tuple:

```python
# BEFORE:
CELERY_TASK_STATUSES = (...)

# AFTER:
TASK_STATUSES = (...)
```

- [ ] **Step 9.6: Update all files that reference the old names**

For each file identified in Step 9.1, apply these replacements:

- `CELERY_TASK_STATUSES` → `TASK_STATUSES`
- `.celery_ids` → `.workflow_ids`
- `"celery_ids"` (in serializer fields list) → `"workflow_ids"`
- `.celery_id` → `.execution_id`
- `celery_id=f"temporal-{` → `execution_id=f"temporal-{`

Key files to update:
- `web/startScan/models.py` — the `from reNgine.definitions import (CELERY_TASK_STATUSES, ...)` import and two `choices=CELERY_TASK_STATUSES` usages
- `web/reNgine/temporal_activities.py` — `self.activity.celery_id = f"temporal-{temporal_activity_id}"`
- `web/api/serializers.py` — `"celery_ids"` in field lists
- `web/tests/test_temporal_orchestration.py` line 160 — `subscan.celery_ids`
- Any other files from the grep in Step 9.1

- [ ] **Step 9.7: Run the full test suite**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -10
```

Expected: same pass count, no migration warnings.

- [ ] **Step 9.8: Commit**

```bash
git add web/startScan/models.py \
        web/startScan/migrations/ \
        web/reNgine/definitions.py \
        web/reNgine/temporal_activities.py \
        web/api/serializers.py \
        web/tests/test_temporal_orchestration.py
git commit -m "chore: rename Celery artifacts to Temporal-appropriate names

- ScanHistory.celery_ids     → workflow_ids
- SubScan.celery_ids         → workflow_ids
- ScanActivity.celery_id     → execution_id
- CELERY_TASK_STATUSES       → TASK_STATUSES (definitions.py)

DB migration included (RenameField — no data loss).
API field 'celery_ids' is renamed to 'workflow_ids' in serializers
(breaking change for API clients using that field).

No behaviour changes — pure nomenclature cleanup post-Celery-removal."
```

---

## Phase 7 — Cleanup

### Task 10: Remove dead Celery callback stubs from tasks.py

**Context:** Several functions in `tasks.py` are Celery chord callback stubs that exist solely to be chained via `.s()` in the now-dead `initiate_scan` and `initiate_subscan` functions. They are never called by any Temporal workflow. `finish_osint` and `finish_osint_discovery` are NOT in this list — they are called from active task functions (see Task 2). This task removes only the genuinely dead code.

**Files:**
- Modify: `web/reNgine/tasks.py`

---

- [ ] **Step 10.1: Verify each function is unreferenced outside its own definition and dead callers**

```
cd web && grep -rn "finish_chord\|finish_vulnerability_scan\|finish_nuclei_scan\|initiate_scan\b\|initiate_subscan\b\|resolve_primary_vulnerability_tasks\|resolve_additional_vulnerability_tasks\|resolve_vulnerability_tasks\b" --include="*.py" . | grep -v "^./reNgine/tasks.py:.*def " | grep -v ".pyc"
```

Expected: all remaining references should be within `initiate_scan` or `initiate_subscan` themselves (which are also being removed). If any reference appears in a file other than `tasks.py`, investigate before deleting.

- [ ] **Step 10.2: Delete the dead functions from tasks.py**

Remove the complete function definitions for each of these from `web/reNgine/tasks.py`:
- `finish_chord(results, description="Task")`
- `finish_vulnerability_scan(results, scan_history_id)`
- `finish_nuclei_scan(results, scan_history_id)`
- `resolve_primary_vulnerability_tasks(config, urls=[], ctx={})`
- `resolve_additional_vulnerability_tasks(config, urls=[], ctx={})`
- `resolve_vulnerability_tasks(config, urls=[], ctx={})`
- `initiate_scan(...)` — the full function including any nested helpers
- `initiate_subscan(...)` — the full function

Do NOT remove `finish_osint`, `finish_osint_discovery` — these are called from active activity code (fixed in Task 2).

- [ ] **Step 10.3: Run the full test suite**

```
cd web && python manage.py test --verbosity 1 2>&1 | tail -5
```

Expected: same pass count. If tests reference any removed function by name, update those tests to remove the reference.

- [ ] **Step 10.4: Commit**

```bash
git add web/reNgine/tasks.py
git commit -m "chore: remove dead Celery callback stubs from tasks.py

finish_chord, finish_vulnerability_scan, finish_nuclei_scan,
resolve_*_vulnerability_tasks, initiate_scan, and initiate_subscan
were Celery chord callbacks and Celery task entrypoints. None are
called by any Temporal workflow.

Note: finish_osint and finish_osint_discovery are retained — they
are called from within active task functions (fixed in Task 2).

Removes ~220 lines of dead code."
```

---

## Self-Review

**Spec coverage check:**

| Finding (architecture review) | Task |
|---|---|
| TemporalClientProvider singleton race + broken cache | Task 1 |
| `finish_osint` daemon threads escaping Temporal durability | Task 2 |
| `RunGenericTaskActivity` allowlist gap | Task 3 |
| LLM module: `verify=False`, Gemini API key in URL, Anthropic system field, missing `raise_for_status` | Task 4 |
| No explicit retry policies on activities | Task 5 |
| Untyped `ctx` dict | Task 6 |
| `SubScanWorkflow` if/elif routing | Task 7 |
| Checkpoint stub unimplemented | Task 8 |
| Stale Celery naming (`celery_ids`, `CELERY_TASK_STATUSES`) | Task 9 |
| Dead code in `tasks.py` | Tasks 2 + 10 |
| `asyncio.new_event_loop()` at 12+ sites | Task 1 removes the `reset()` pattern that made it necessary; remaining `new_event_loop()` calls in schedule helpers are now clearly documented. Converting them to async Django views is a separate, larger Django async migration and is out of scope for this hardening pass. |
| `NucleiPlannerWorkflow` is thin | Acknowledged as a future opportunity (parallelise by template set), not a correctness issue. Not included. |

**Placeholder scan:** No TBD, TODO, or "implement later" in any task step. All steps contain complete code.

**Type consistency:**
- `_RETRY_*` constants defined in Task 5, used in Task 7 — same names.
- `ScanContext` defined in Task 6, imported in Task 7 — consistent.
- `_SUBSCAN_DISPATCH` defined and tested in Task 7 — consistent.
- `workflow_ids` / `execution_id` / `TASK_STATUSES` renamed in Task 9, referenced consistently through Step 9.6.
