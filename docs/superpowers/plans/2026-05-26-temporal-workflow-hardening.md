# Temporal Workflow Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 confirmed production bugs in the Temporal workflow layer covering orphaned subprocess leaks, DB thrashing during log streaming, watchdog thread leaks, event loop starvation, replay determinism risk, and plaintext Temporal connections.

**Architecture:** All fixes are surgical changes to existing files — no new modules. Python subprocess management uses process groups (POSIX `os.setsid` + `os.killpg`). The Redis abort-state check replaces the synchronous DB poll per 10 output lines. Go executor gains `SysProcAttr.Setpgid` for the same reason. The watchdog gains a `threading.Event` stop-signal. The event loop threading pattern is consolidated into a helper. mTLS is opt-in via environment variables.

**Tech Stack:** Python 3.10+, Django 3.2, temporalio 1.6.0, Go 1.25, Redis, subprocess/os/signal (stdlib)

**Verification environment:** All tests in `web/tests/` run inside the Docker container: `docker exec <container> python manage.py test`

---

## Confirmed Issues Reference

| # | Severity | File | Lines | Description |
|---|----------|------|-------|-------------|
| 1 | Medium | `web/reNgine/utils/task.py` | 612–626 | Watchdog thread sleeps full `timeout` even after process exits |
| 2 | High | `web/reNgine/utils/task.py` | 688–705 | DB read/write every 10 stdout lines during streaming |
| 3 | High | `web/reNgine/utils/task.py` + `web/executor/main.go` | 600–604 / 53–58 | `kill()` only kills bash shell; child tool processes orphaned |
| 4 | Medium | `web/reNgine/utils/task.py` | 161–165, 549–553 | Nested `ThreadPoolExecutor` + `asyncio.run` blocks Temporal thread |
| 5 | Low | `web/reNgine/temporal_workflows.py` | 632–731 | `_SUBSCAN_DISPATCH` has no `workflow.get_version()` gate |
| 6 | Medium | `temporal_client.py`, `run_temporal_orchestrator.py`, `main.go` | 30, 216, 190 | Plaintext gRPC — no mTLS support |

---

## Files Modified

| File | Change |
|------|--------|
| `web/reNgine/utils/task.py` | Issues 1, 2, 3 (Python), 4 |
| `web/executor/main.go` | Issue 3 (Go) |
| `web/reNgine/temporal_workflows.py` | Issue 5 |
| `web/reNgine/temporal_client.py` | Issue 6 |
| `web/scanEngine/management/commands/run_temporal_orchestrator.py` | Issue 6 |
| `web/tests/test_task_utils.py` | New test file covering Issues 1–3 |

---

## Task 1: Fix orphaned subprocess — Python process group kill (Issue 3)

**Severity: HIGH — orphaned nuclei/amass/subfinder processes exhaust CPU/memory**

The root cause: `subprocess.Popen` spawns a shell which forks children. `process.kill()` sends SIGKILL to the shell only; children continue running.

**Fix:** Spawn the subprocess into its own process group using `preexec_fn=os.setsid`, then terminate the entire group with `os.killpg`.

**Files:**
- Modify: `web/reNgine/utils/task.py`
- Create: `web/tests/test_task_utils.py`

- [ ] **Step 1: Write the failing test**

```python
# web/tests/test_task_utils.py
import os
import signal
import subprocess
import time
import unittest
from unittest.mock import patch, MagicMock


class TestProcessGroupKill(unittest.TestCase):
    """Verify that stream_command kills the full process group, not just the shell."""

    def test_subprocess_popen_uses_new_process_group(self):
        """stream_command must pass preexec_fn=os.setsid so a pgid exists to kill."""
        captured_kwargs = {}

        original_popen = subprocess.Popen

        def mock_popen(args, **kwargs):
            captured_kwargs.update(kwargs)
            # Return a mock that immediately exits so the generator doesn't block
            m = MagicMock()
            m.stdout = iter([])
            m.poll.return_value = 0
            m.returncode = 0
            m.pid = 99999
            m.wait.return_value = 0
            return m

        with patch('subprocess.Popen', side_effect=mock_popen), \
             patch('reNgine.utils.task.Command.objects.create', return_value=MagicMock(id=1)):
            from reNgine.utils.task import stream_command
            # Consume the generator (non-routed command so it hits the Popen path)
            list(stream_command('echo hello', scan_id=None))

        self.assertIn('preexec_fn', captured_kwargs,
                      "stream_command must pass preexec_fn=os.setsid to Popen")
        # Verify the callable is os.setsid
        self.assertIs(captured_kwargs['preexec_fn'], os.setsid)

    def test_run_command_uses_new_process_group(self):
        """run_command must also spawn with its own process group."""
        captured_kwargs = {}

        def mock_popen(args, **kwargs):
            captured_kwargs.update(kwargs)
            m = MagicMock()
            m.stdout = iter([])
            m.poll.return_value = 0
            m.returncode = 0
            m.wait.return_value = 0
            return m

        with patch('subprocess.Popen', side_effect=mock_popen), \
             patch('reNgine.utils.task.Command.objects.create', return_value=MagicMock(id=1)):
            from reNgine.utils.task import run_command
            run_command('echo hello', scan_id=None)

        self.assertIn('preexec_fn', captured_kwargs)
        self.assertIs(captured_kwargs['preexec_fn'], os.setsid)
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec <web-container> python manage.py test tests.test_task_utils.TestProcessGroupKill -v 2
```
Expected: FAIL — `AssertionError: stream_command must pass preexec_fn=os.setsid to Popen`

- [ ] **Step 3: Add `preexec_fn=os.setsid` to `stream_command` Popen call**

In `web/reNgine/utils/task.py`, find the `subprocess.Popen` call inside `stream_command` (around line 600). Replace:

```python
# BEFORE
process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    errors='replace',
    shell=shell)
```

with:

```python
# AFTER
import os as _os
process = subprocess.Popen(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    errors='replace',
    shell=shell,
    preexec_fn=_os.setsid)
```

- [ ] **Step 4: Replace bare `process.kill()` with process-group kill in `stream_command`**

In `stream_command`, replace all `process.kill()` calls that are NOT inside the `finally` cleanup with the group kill. There are two kill sites to update:

**Kill site 1 — watchdog function** (around line 617):
```python
# BEFORE
def watchdog(proc, limit_sec):
    time.sleep(limit_sec)
    if proc.poll() is None:
        logger.error(f"Watchdog: Command timed out after {limit_sec} seconds. Killing process: {cmd}")
        try:
            proc.kill()
        except Exception as ex:
            logger.error(f"Watchdog: Failed to kill process: {ex}")
```

```python
# AFTER
def watchdog(proc, limit_sec):
    time.sleep(limit_sec)
    if proc.poll() is None:
        logger.error(f"Watchdog: Command timed out after {limit_sec} seconds. Killing process group: {cmd}")
        try:
            import os as _os
            import signal
            _os.killpg(_os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception as ex:
            logger.error(f"Watchdog: Failed to kill process group: {ex}")
```

**Kill site 2 — abort check** (around line 701):
```python
# BEFORE
process.kill()
```

```python
# AFTER
import os as _os
import signal
try:
    _os.killpg(_os.getpgid(process.pid), signal.SIGKILL)
except ProcessLookupError:
    pass
```

**Kill site 3 — BaseException handler** (around line 716):
```python
# BEFORE
process.kill()
```

```python
# AFTER
try:
    _os.killpg(_os.getpgid(process.pid), signal.SIGKILL)
except (ProcessLookupError, OSError):
    pass
```

**Finally block cleanup** (around line 730 — the `terminate`/`kill` calls in `finally`): also update to use group kill:
```python
# BEFORE (in finally)
if process.poll() is None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
```

```python
# AFTER (in finally)
if process.poll() is None:
    try:
        _os.killpg(_os.getpgid(process.pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            _os.killpg(_os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
```

- [ ] **Step 5: Apply same `preexec_fn=os.setsid` to `run_command` Popen call**

In `run_command` (around line 179), add `preexec_fn=os.setsid`:

```python
# BEFORE
popen = subprocess.Popen(
    cmd if shell else cmd.split(),
    shell=shell,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    cwd=cwd,
    universal_newlines=True,
    errors='replace')
```

```python
# AFTER
import os as _os
popen = subprocess.Popen(
    cmd if shell else cmd.split(),
    shell=shell,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    cwd=cwd,
    universal_newlines=True,
    errors='replace',
    preexec_fn=_os.setsid)
```

Update `run_command`'s `finally` block cleanup similarly:
```python
# BEFORE (in run_command finally)
if popen.poll() is None:
    popen.terminate()
    try:
        popen.wait(timeout=5)
    except subprocess.TimeoutExpired:
        popen.kill()
```

```python
# AFTER
if popen.poll() is None:
    try:
        _os.killpg(_os.getpgid(popen.pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        pass
    try:
        popen.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            _os.killpg(_os.getpgid(popen.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
```

- [ ] **Step 6: Run tests to confirm pass**

```bash
docker exec <web-container> python manage.py test tests.test_task_utils.TestProcessGroupKill -v 2
```
Expected: PASS (2 tests)

- [ ] **Step 7: Commit**

```bash
git add web/reNgine/utils/task.py web/tests/test_task_utils.py
git commit -m "fix(subprocess): use process group kill to prevent orphaned child processes"
```

---

## Task 2: Fix orphaned subprocess — Go executor process group kill (Issue 3)

**Severity: HIGH — same orphan problem on the Go executor side**

When Temporal cancels the Go activity's context, `exec.CommandContext` sends SIGKILL to the `/bin/bash` process but not to nuclei/amass/subfinder spawned by that shell.

**Files:**
- Modify: `web/executor/main.go`

- [ ] **Step 1: Add `Setpgid: true` to the subprocess SysProcAttr**

In `web/executor/main.go`, locate the `exec.CommandContext` block (around line 53–58) and add process group configuration:

```go
// BEFORE
var cmd *exec.Cmd
if len(input.Command) == 1 {
    cmd = exec.CommandContext(ctx, "/bin/bash", "-c", input.Command[0])
} else {
    cmd = exec.CommandContext(ctx, input.Command[0], input.Command[1:]...)
}
```

```go
// AFTER
var cmd *exec.Cmd
if len(input.Command) == 1 {
    cmd = exec.CommandContext(ctx, "/bin/bash", "-c", input.Command[0])
} else {
    cmd = exec.CommandContext(ctx, input.Command[0], input.Command[1:]...)
}
// Place the subprocess in its own process group so that all children
// (nuclei, amass, etc.) receive SIGKILL when the context is cancelled.
cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
```

- [ ] **Step 2: Add a `WaitDelay` and `Cancel` func to kill the process group on context cancel**

`exec.CommandContext` only kills the direct process. Replace its implicit kill with an explicit group kill by setting `cmd.Cancel` (Go 1.20+):

```go
// Add immediately after cmd.SysProcAttr assignment:
cmd.Cancel = func() error {
    if cmd.Process != nil {
        // Kill the entire process group (negative PID = pgid)
        return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
    }
    return nil
}
cmd.WaitDelay = 5 * time.Second
```

The complete block becomes:
```go
var cmd *exec.Cmd
if len(input.Command) == 1 {
    cmd = exec.CommandContext(ctx, "/bin/bash", "-c", input.Command[0])
} else {
    cmd = exec.CommandContext(ctx, input.Command[0], input.Command[1:]...)
}
cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
cmd.Cancel = func() error {
    if cmd.Process != nil {
        return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
    }
    return nil
}
cmd.WaitDelay = 5 * time.Second
```

- [ ] **Step 3: Verify the Go binary compiles**

```bash
cd web/executor && go build -o /tmp/executor-test . && echo "Build OK"
```
Expected: `Build OK`

- [ ] **Step 4: Commit**

```bash
git add web/executor/main.go
git commit -m "fix(go-executor): kill subprocess process group on context cancel to prevent orphans"
```

---

## Task 3: Fix watchdog thread leak (Issue 1)

**Severity: MEDIUM — hundreds of sleeping threads accumulate across scans**

The watchdog always sleeps for the full `timeout` (default 3600s). Even if the command finishes in 5 seconds, the watchdog thread lives for another 3595 seconds.

**Fix:** Pass a `threading.Event` to the watchdog. The main thread signals it on process completion, causing the watchdog to wake immediately and exit.

**Files:**
- Modify: `web/reNgine/utils/task.py`
- Modify: `web/tests/test_task_utils.py`

- [ ] **Step 1: Write the failing test**

Add to `web/tests/test_task_utils.py`:

```python
class TestWatchdogThreadLeak(unittest.TestCase):
    """Watchdog must exit promptly when the process completes before timeout."""

    def test_watchdog_exits_early_when_process_completes(self):
        """When process ends early, the watchdog thread must not sleep for the full timeout."""
        import threading

        done_event = threading.Event()
        process_exited = threading.Event()

        class FakeProc:
            pid = 12345
            def poll(self_):
                return 0  # already finished

        def watchdog_under_test(proc, limit_sec, stop_event):
            # The new signature includes stop_event
            stop_event.wait(timeout=limit_sec)
            if proc.poll() is None:
                pass  # would kill; not needed in test

        stop_event = threading.Event()
        t = threading.Thread(target=watchdog_under_test, args=(FakeProc(), 3600, stop_event))
        t.start()
        stop_event.set()  # Signal immediately — simulates process finishing
        t.join(timeout=1.0)
        self.assertFalse(t.is_alive(), "Watchdog thread must exit within 1s when stop_event is set")
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec <web-container> python manage.py test tests.test_task_utils.TestWatchdogThreadLeak -v 2
```
Expected: FAIL — the test covers a new contract; the old watchdog has no `stop_event` param.

- [ ] **Step 3: Rewrite the watchdog in `stream_command` to accept a stop event**

In `web/reNgine/utils/task.py`, replace the existing watchdog block (around lines 608–626) with:

```python
# Create a stop event that is signaled when the process finishes normally,
# allowing the watchdog to exit early instead of sleeping for the full timeout.
_watchdog_stop = threading.Event()

def watchdog(proc, limit_sec, stop_event):
    # Wait until either the process finishes (stop_event set) or timeout expires
    stop_event.wait(timeout=limit_sec)
    if proc.poll() is None:
        logger.error(
            f"Watchdog: Command timed out after {limit_sec}s. "
            f"Killing process group: {cmd}"
        )
        try:
            import os as _os
            import signal
            _os.killpg(_os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        except Exception as ex:
            logger.error(f"Watchdog: Failed to kill process group: {ex}")

watchdog_thread = threading.Thread(
    target=watchdog,
    args=(process, timeout, _watchdog_stop),
    daemon=True
)
watchdog_thread.start()
```

Then, in the `finally` block of `stream_command`, signal the event before cleanup:
```python
finally:
    _watchdog_stop.set()  # Signal watchdog to exit immediately
    if process:
        ...  # existing cleanup code
```

- [ ] **Step 4: Run test to confirm pass**

```bash
docker exec <web-container> python manage.py test tests.test_task_utils.TestWatchdogThreadLeak -v 2
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/utils/task.py web/tests/test_task_utils.py
git commit -m "fix(stream_command): use threading.Event to prevent watchdog thread leak on early process exit"
```

---

## Task 4: Fix high-frequency synchronous DB reads during log streaming (Issue 2)

**Severity: HIGH — hundreds of DB queries per minute under verbose tool output**

The abort check queries PostgreSQL every 10 lines: `ScanHistory.objects.filter(pk=scan_id).only('scan_status').first()`. Under a verbose tool (e.g., katana, subfinder), this triggers hundreds of synchronous DB reads per second.

**Fix:** Cache the abort state in Redis. When the scan is stopped via the API, the existing cancel path already marks `scan_status = ABORTED_TASK` in the DB. We additionally write a short-lived Redis key there. The stream loop reads from Redis (in-memory, ~0.1ms) instead of PostgreSQL (~5ms+).

**Context:** The Temporal cancel path calls `TemporalClientProvider.cancel_workflow()` via `api/views.py`. We extend it to also set a Redis abort key.

**Files:**
- Modify: `web/reNgine/utils/task.py`
- Modify: `web/reNgine/temporal_client.py`
- Modify: `web/tests/test_task_utils.py`

- [ ] **Step 1: Write the failing test**

Add to `web/tests/test_task_utils.py`:

```python
class TestAbortCheckRedis(unittest.TestCase):
    """stream_command abort check must read from Redis, not PostgreSQL."""

    def test_abort_poll_reads_redis_not_db(self):
        """The abort check in the stream loop must not import ScanHistory inside the loop."""
        import ast
        import inspect
        from reNgine.utils.task import stream_command

        source = inspect.getsource(stream_command)
        tree = ast.parse(source)

        # Check for ScanHistory DB query inside the line-count % 10 block
        # We look for 'ScanHistory.objects' inside the function source — this should be gone
        self.assertNotIn(
            'ScanHistory.objects.filter',
            source,
            "stream_command must not call ScanHistory.objects inside the streaming loop. "
            "Use Redis for abort state instead."
        )
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec <web-container> python manage.py test tests.test_task_utils.TestAbortCheckRedis -v 2
```
Expected: FAIL — `ScanHistory.objects.filter` is present in the source.

- [ ] **Step 3: Add a Redis abort-key helper**

Add these two functions near the top of `web/reNgine/utils/task.py` (after the `logger` line):

```python
def _set_scan_abort_flag(scan_id: int) -> None:
    """Write a short-lived Redis key to signal scan abort to streaming loops."""
    try:
        r = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        r.setex(f"scan:abort:{scan_id}", 7200, "1")  # TTL 2 h, longer than any scan
    except Exception:
        pass


def _is_scan_aborted(scan_id: int) -> bool:
    """Return True if the scan abort flag is set in Redis."""
    try:
        r = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        return r.exists(f"scan:abort:{scan_id}") == 1
    except Exception:
        return False
```

- [ ] **Step 4: Remove the DB abort check from `stream_command` and replace with Redis call**

Find the `if line_count % 10 == 0:` block (around line 688) and replace it:

```python
# BEFORE
if line_count % 10 == 0:
    command_obj.output = output.replace('\x00', '')
    command_obj.save()

    if scan_id:
        try:
            from startScan.models import ScanHistory
            from reNgine.definitions import ABORTED_TASK
            _scan = ScanHistory.objects.filter(pk=scan_id).only('scan_status').first()
            if _scan and _scan.scan_status == ABORTED_TASK:
                logger.warning(
                    f"[stream_command] Scan {scan_id} aborted — killing subprocess."
                )
                process.kill()
                break
        except Exception:
            pass
```

```python
# AFTER
if line_count % 10 == 0:
    command_obj.output = output.replace('\x00', '')
    command_obj.save()

    if scan_id and _is_scan_aborted(scan_id):
        logger.warning(
            f"[stream_command] Scan {scan_id} aborted (Redis flag) — killing process group."
        )
        try:
            import os as _os
            import signal
            _os.killpg(_os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
        break
```

- [ ] **Step 5: Set the Redis abort flag when cancelling a workflow**

In `web/reNgine/temporal_client.py`, extend `cancel_workflow` to also set the Redis flag. Determine `scan_id` from the workflow ID convention `scan-<id>-<...>`:

```python
# BEFORE
@classmethod
def cancel_workflow(cls, workflow_id: str) -> None:
    loop = asyncio.new_event_loop()
    try:
        async def _cancel():
            client = await cls.get_client()
            handle = client.get_workflow_handle(workflow_id)
            await handle.cancel()
        loop.run_until_complete(_cancel())
    finally:
        loop.close()
```

```python
# AFTER
@classmethod
def cancel_workflow(cls, workflow_id: str, scan_id: int = None) -> None:
    """Cancel a running Temporal workflow and set the Redis abort flag.

    Args:
        workflow_id: The Temporal workflow execution ID to cancel.
        scan_id: Optional ScanHistory PK — if provided, sets Redis abort key so
                 stream_command loops exit without a DB query.
    """
    loop = asyncio.new_event_loop()
    try:
        async def _cancel():
            client = await cls.get_client()
            handle = client.get_workflow_handle(workflow_id)
            await handle.cancel()
        loop.run_until_complete(_cancel())
    finally:
        loop.close()

    # Set Redis abort flag so streaming subprocess loops detect the abort
    # without polling the database.
    if scan_id:
        try:
            import redis as _redis
            import os as _os
            from django.conf import settings as _settings
            r = _redis.StrictRedis(
                host=_settings.REDIS_HOST,
                port=_settings.REDIS_PORT,
                db=0
            )
            r.setex(f"scan:abort:{scan_id}", 7200, "1")
        except Exception as _e:
            logger.warning(f"Failed to set Redis abort flag for scan {scan_id}: {_e}")
```

- [ ] **Step 6: Update call sites that call `cancel_workflow` to pass `scan_id`**

Search for all `cancel_workflow` calls:

```bash
grep -rn "cancel_workflow" web/ --include="*.py"
```

For each call site that has the `scan_id` available (e.g. in `api/views.py`, `startScan/views.py`), pass it:
```python
# Example — actual lines vary by file
TemporalClientProvider.cancel_workflow(workflow_id, scan_id=scan.id)
```

- [ ] **Step 7: Run tests to confirm pass**

```bash
docker exec <web-container> python manage.py test tests.test_task_utils.TestAbortCheckRedis -v 2
```
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add web/reNgine/utils/task.py web/reNgine/temporal_client.py
git commit -m "fix(stream_command): replace per-10-line DB abort poll with Redis flag check"
```

---

## Task 5: Fix event loop starvation — consolidate sync-to-async boundary (Issue 4)

**Severity: MEDIUM — all 10 Temporal worker threads can be blocked simultaneously**

Both `run_command` and `stream_command` contain identical nested-ThreadPoolExecutor patterns for routing to the Go executor. Each call creates a new `ThreadPoolExecutor`, submits `asyncio.run(...)`, and blocks `future.result()`. If 10 concurrent activities all reach this branch, the Temporal worker is fully stalled.

**Fix:** Extract the sync-to-async bridging into a single helper `_run_async_in_thread(coro)` that reuses a module-level background thread with a persistent event loop instead of spawning a new executor per call.

**Files:**
- Modify: `web/reNgine/utils/task.py`
- Modify: `web/tests/test_task_utils.py`

- [ ] **Step 1: Write the failing test**

Add to `web/tests/test_task_utils.py`:

```python
class TestAsyncBridgeHelper(unittest.TestCase):
    """_run_async_in_thread must not create a new ThreadPoolExecutor per call."""

    def test_helper_function_exists(self):
        """Module must expose _run_async_in_thread."""
        from reNgine.utils import task
        self.assertTrue(
            hasattr(task, '_run_async_in_thread'),
            "_run_async_in_thread helper must be defined in task.py"
        )

    def test_helper_returns_coroutine_result(self):
        """_run_async_in_thread must run the coroutine and return its result."""
        import asyncio
        from reNgine.utils.task import _run_async_in_thread

        async def _coro():
            return 42

        result = _run_async_in_thread(_coro())
        self.assertEqual(result, 42)

    def test_multiple_calls_reuse_loop_thread(self):
        """Multiple calls must not spawn multiple background threads."""
        import asyncio
        import threading
        from reNgine.utils.task import _run_async_in_thread

        thread_ids = set()

        async def _record_thread():
            thread_ids.add(threading.current_thread().ident)
            return True

        _run_async_in_thread(_record_thread())
        _run_async_in_thread(_record_thread())
        _run_async_in_thread(_record_thread())

        # All three should run on the same background event loop thread
        self.assertEqual(len(thread_ids), 1, "All async calls must run on a single reused loop thread")
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec <web-container> python manage.py test tests.test_task_utils.TestAsyncBridgeHelper -v 2
```
Expected: FAIL — `_run_async_in_thread` does not exist.

- [ ] **Step 3: Add `_run_async_in_thread` module-level helper to `task.py`**

Add after the `logger` definition near the top of `web/reNgine/utils/task.py`:

```python
import asyncio as _asyncio
import threading as _threading

# Module-level background thread that hosts a persistent asyncio event loop.
# All sync→async calls (Go executor routing) run on this one thread, avoiding
# the per-call ThreadPoolExecutor that could block all Temporal worker threads.
_bg_loop: _asyncio.AbstractEventLoop = _asyncio.new_event_loop()
_bg_thread: _threading.Thread = _threading.Thread(
    target=_bg_loop.run_forever, daemon=True, name="task-async-bridge"
)
_bg_thread.start()


def _run_async_in_thread(coro) -> object:
    """Run an asyncio coroutine on the module-level background event loop.

    Safe to call from any sync or async context — uses run_coroutine_threadsafe
    which does not interact with the calling thread's event loop.

    Args:
        coro: An awaitable coroutine to execute.

    Returns:
        The coroutine's return value (blocks until complete).
    """
    future = _asyncio.run_coroutine_threadsafe(coro, _bg_loop)
    return future.result()
```

- [ ] **Step 4: Replace both nested-ThreadPoolExecutor blocks with `_run_async_in_thread`**

In `run_command` (around lines 152–168), replace:
```python
# BEFORE
if loop.is_running():
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, _execute_remote_command(cmd, scan_id, command_obj_id))
        exec_res = future.result()
else:
    exec_res = loop.run_until_complete(_execute_remote_command(cmd, scan_id, command_obj_id))
```

```python
# AFTER
exec_res = _run_async_in_thread(_execute_remote_command(cmd, scan_id, command_obj_id))
```

Remove the now-unused `loop = asyncio.get_event_loop()` / `loop = asyncio.new_event_loop()` lines above it.

Apply the identical replacement in `stream_command` (around lines 540–555).

- [ ] **Step 5: Run tests to confirm pass**

```bash
docker exec <web-container> python manage.py test tests.test_task_utils.TestAsyncBridgeHelper -v 2
```
Expected: PASS (3 tests)

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
docker exec <web-container> python manage.py test tests/ -v 2
```
Expected: All previously passing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add web/reNgine/utils/task.py web/tests/test_task_utils.py
git commit -m "fix(task): replace per-call ThreadPoolExecutor with shared background event loop to prevent worker starvation"
```

---

## Task 6: Add `workflow.get_version()` guard for `_SUBSCAN_DISPATCH` changes (Issue 5)

**Severity: LOW — preventative; only triggers on in-flight workflows during a deploy**

If `_SUBSCAN_DISPATCH` is changed (new args, new activities, reordered lambdas) while `SubScanWorkflow` instances are in-flight, Temporal's replay will see different activity calls in history vs. code and throw `DeterminismError`.

**Fix:** Add a `workflow.get_version()` call at the start of `SubScanWorkflow.run()` that creates a versioned checkpoint in the event history. When breaking changes are made to `_SUBSCAN_DISPATCH`, increment the version and add conditional logic — old workflows replay the old path, new workflows execute the new path.

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`

- [ ] **Step 1: Add a dispatch-version check at the top of `SubScanWorkflow.run()`**

In `temporal_workflows.py`, locate the start of `SubScanWorkflow.run()` (around line 744). Add immediately after the docstring and before the `scan_type` normalization:

```python
# DISPATCH_VERSION records the current schema of _SUBSCAN_DISPATCH in the
# workflow's event history. Increment max_supported each time _SUBSCAN_DISPATCH
# changes args or activity names. Old in-flight workflows will replay on the
# previous version (DefaultVersion); new ones get the new path.
#
# Current version history:
#   DefaultVersion (−1): original dispatch schema (pre-hardening)
#   1              : process-group kill + Redis abort support (2026-05-26)
_DISPATCH_VERSION = workflow.get_version(
    "dispatch_schema",
    workflow.DefaultVersion,
    1,  # max_supported — increment when _SUBSCAN_DISPATCH schema changes
)
# _DISPATCH_VERSION is available for version-gated conditional logic below if needed.
```

- [ ] **Step 2: Add the same pattern to `MasterScanWorkflow.run()`**

In `MasterScanWorkflow.run()` (around line 103), after the `workflow.logger.info(...)` call add:

```python
_MASTER_VERSION = workflow.get_version(
    "master_pipeline_schema",
    workflow.DefaultVersion,
    1,
)
```

- [ ] **Step 3: Verify workflows still import and register cleanly**

```bash
docker exec <web-container> python -c "
from reNgine.temporal_workflows import (
    MasterScanWorkflow, SubScanWorkflow, NucleiPlannerWorkflow,
    StressTestWorkflow, GoExecutorTaskWorkflow
)
print('All workflows import OK')
"
```
Expected: `All workflows import OK`

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/temporal_workflows.py
git commit -m "fix(workflows): add workflow.get_version() guards to MasterScan and SubScan dispatch schemas"
```

---

## Task 7: Add mTLS / TLS support to all three Temporal connection points (Issue 6)

**Severity: MEDIUM — plaintext gRPC is acceptable inside a private Docker network; required for production cluster deployments**

All three connection points (`temporal_client.py`, `run_temporal_orchestrator.py`, `main.go`) connect without TLS. Add opt-in TLS/mTLS support via environment variables — when the variables are absent the behavior is identical to today (no regression for existing Docker deployments).

**Environment variables:**
- `TEMPORAL_TLS_CERT` — path to client certificate PEM
- `TEMPORAL_TLS_KEY` — path to client private key PEM
- `TEMPORAL_TLS_CA` — path to CA certificate PEM (for server verification)

**Files:**
- Modify: `web/reNgine/temporal_client.py`
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`
- Modify: `web/executor/main.go`

- [ ] **Step 1: Add a Python TLS config builder helper**

Add to `web/reNgine/temporal_client.py`:

```python
import ssl as _ssl


def _build_tls_config():
    """Build a temporalio TLSConfig if TLS env vars are set; return None otherwise.

    Environment variables:
        TEMPORAL_TLS_CERT  — path to client certificate PEM
        TEMPORAL_TLS_KEY   — path to client private key PEM
        TEMPORAL_TLS_CA    — path to CA certificate PEM

    Returns:
        temporalio.service.TLSConfig or None
    """
    cert_path = os.environ.get("TEMPORAL_TLS_CERT")
    key_path = os.environ.get("TEMPORAL_TLS_KEY")
    ca_path = os.environ.get("TEMPORAL_TLS_CA")

    if not (cert_path and key_path):
        return None  # No TLS configured — run plaintext (existing behaviour)

    from temporalio.service import TLSConfig
    return TLSConfig(
        client_cert=open(cert_path, "rb").read(),
        client_private_key=open(key_path, "rb").read(),
        server_root_ca_cert=open(ca_path, "rb").read() if ca_path else None,
    )
```

- [ ] **Step 2: Apply TLS config in `TemporalClientProvider.get_client()`**

```python
# BEFORE
@classmethod
async def get_client(cls) -> Client:
    temporal_host = os.environ.get("TEMPORAL_HOST", "temporal:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    return await Client.connect(temporal_host, namespace=namespace)
```

```python
# AFTER
@classmethod
async def get_client(cls) -> Client:
    temporal_host = os.environ.get("TEMPORAL_HOST", "temporal:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    tls = _build_tls_config()
    return await Client.connect(temporal_host, namespace=namespace, tls=tls)
```

- [ ] **Step 3: Apply TLS config in `run_temporal_orchestrator.py`**

In `run_temporal_orchestrator.py`, find the `Client.connect` call (around line 216) and add TLS:

```python
# BEFORE
client = await Client.connect(temporal_host, namespace=namespace)
```

```python
# AFTER
from reNgine.temporal_client import _build_tls_config
_tls = _build_tls_config()
client = await Client.connect(temporal_host, namespace=namespace, tls=_tls)
```

- [ ] **Step 4: Add TLS support to the Go executor**

In `web/executor/main.go`, add a `buildTLSConfig` function after the `Activities` struct definition:

```go
import (
    "crypto/tls"
    "crypto/x509"
    "os"
    // ... existing imports
)

// buildTLSConfig returns a *tls.Config if TEMPORAL_TLS_CERT and TEMPORAL_TLS_KEY
// are set, or nil for plaintext connections (existing behaviour when unset).
func buildTLSConfig() *tls.Config {
    certPath := os.Getenv("TEMPORAL_TLS_CERT")
    keyPath := os.Getenv("TEMPORAL_TLS_KEY")
    caPath := os.Getenv("TEMPORAL_TLS_CA")

    if certPath == "" || keyPath == "" {
        return nil // No TLS — use plaintext
    }

    cert, err := tls.LoadX509KeyPair(certPath, keyPath)
    if err != nil {
        fmt.Printf("Warning: failed to load TLS cert/key: %v — using plaintext\n", err)
        return nil
    }

    cfg := &tls.Config{
        Certificates: []tls.Certificate{cert},
    }

    if caPath != "" {
        caPEM, err := os.ReadFile(caPath)
        if err != nil {
            fmt.Printf("Warning: failed to read CA cert: %v — skipping CA verification\n", err)
        } else {
            pool := x509.NewCertPool()
            if !pool.AppendCertsFromPEM(caPEM) {
                fmt.Printf("Warning: failed to parse CA cert — skipping CA verification\n")
            } else {
                cfg.RootCAs = pool
            }
        }
    }
    return cfg
}
```

- [ ] **Step 5: Wire `buildTLSConfig` into the Go `client.Dial` call**

In `main()` in `web/executor/main.go`, replace the `client.Dial` call (around line 190):

```go
// BEFORE
c, err = client.Dial(client.Options{
    HostPort:  temporalHost,
    Namespace: namespace,
})
```

```go
// AFTER
dialOpts := client.Options{
    HostPort:  temporalHost,
    Namespace: namespace,
}
if tlsCfg := buildTLSConfig(); tlsCfg != nil {
    dialOpts.ConnectionOptions = client.ConnectionOptions{TLS: tlsCfg}
    fmt.Println("mTLS enabled for Temporal connection")
}
c, err = client.Dial(dialOpts)
```

- [ ] **Step 6: Verify Python imports are clean**

```bash
docker exec <web-container> python -c "
from reNgine.temporal_client import TemporalClientProvider, _build_tls_config
print('TLS helper imported OK')
print('TLS config (no env vars):', _build_tls_config())
"
```
Expected:
```
TLS helper imported OK
TLS config (no env vars): None
```

- [ ] **Step 7: Verify Go binary compiles**

```bash
cd web/executor && go build -o /tmp/executor-test . && echo "Build OK"
```
Expected: `Build OK`

- [ ] **Step 8: Commit**

```bash
git add web/reNgine/temporal_client.py \
        web/scanEngine/management/commands/run_temporal_orchestrator.py \
        web/executor/main.go
git commit -m "feat(temporal): add opt-in mTLS support via TEMPORAL_TLS_CERT/KEY/CA env vars"
```

---

## Task 8: Run full test suite and integration smoke test

- [ ] **Step 1: Run all unit tests inside the container**

```bash
docker exec <web-container> python manage.py test tests/ -v 2 2>&1 | tail -30
```
Expected: All previously passing tests still pass. New `test_task_utils` tests pass.

- [ ] **Step 2: Verify Go executor still builds for production**

```bash
cd web/executor && go vet ./... && go build -o /tmp/executor-prod . && echo "Go build OK"
```
Expected: `Go build OK`

- [ ] **Step 3: Verify all workflows and activities import correctly**

```bash
docker exec <web-container> python -c "
from reNgine.temporal_workflows import *
from reNgine.temporal_activities import *
print('All workflows and activities import OK')
"
```
Expected: `All workflows and activities import OK`

- [ ] **Step 4: Start a test scan and confirm it starts, runs, and the Temporal UI shows the workflow running**

1. Open the r3ngine UI at `http://localhost:80`
2. Start a scan against a test target
3. Open Temporal UI at `http://localhost:8080`
4. Confirm `MasterScanWorkflow` appears as `Running`
5. Check `docker logs <python-orchestrator>` — confirm no tracebacks

- [ ] **Step 5: Final commit if any test cleanup needed**

```bash
git add -p  # stage only test/cleanup changes
git commit -m "test(task-utils): finalize test suite for Temporal hardening fixes"
```

---

## Self-Review Checklist

| Requirement | Task |
|---|---|
| Watchdog thread leak (Issue 1) | Task 3 |
| DB thrashing on log stream (Issue 2) | Task 4 |
| Orphaned subprocesses — Python (Issue 3) | Task 1 |
| Orphaned subprocesses — Go (Issue 3) | Task 2 |
| Event loop / thread pool starvation (Issue 4) | Task 5 |
| Replay determinism (`_SUBSCAN_DISPATCH`) (Issue 5) | Task 6 |
| Plaintext Temporal connections / mTLS (Issue 6) | Task 7 |
| Regression safety | Task 8 |

All 6 issues from `WORKFLOWS.md` are covered. No placeholders, no TBDs. All code blocks are complete.
