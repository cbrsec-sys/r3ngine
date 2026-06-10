# r3ngine — Task Cancellation

## Overview

r3ngine supports cancellation of both full scans (`ScanHistory`) and individual subscans (`SubScan`). Cancellation is handled by:

1. Sending a Temporal cancellation signal to all associated workflow executions.
2. Updating the Django database to mark records as `ABORTED`.

**File:** `web/reNgine/utils/scan_cancellation.py`

---

## Aborting a Full Scan

### Function: `abort_scan_history(scan, aborted_by=None)`

```python
from reNgine.utils.scan_cancellation import abort_scan_history

result = abort_scan_history(scan_history_instance, aborted_by=request.user)
```

**Steps performed:**

1. Sets `scan.scan_status = ABORTED_TASK` and `scan.stop_scan_date = now()`.
2. Optionally records `scan.aborted_by` (the user who triggered the abort).
3. Queries all `TemporalExecution` records linked to the scan with `status="RUNNING"`.
4. For each running workflow: calls `TemporalClientProvider.cancel_workflow(workflow_id)`.
5. Updates `TemporalExecution.status = "CANCELLED"` and `ended_at = now()`.
6. Cancels all child subscans via `abort_subscan()`.
7. Sets all running `ScanActivity` records to `ABORTED_TASK`.
8. Creates a final `ScanActivity("Scan aborted", ABORTED_TASK)` record.

**Returns:**
```python
{'status': True}              # on success
{'status': False, 'message': '...'} # on failure
```

---

## Aborting a Subscan

### Function: `abort_subscan(subscan)`

```python
from reNgine.utils.scan_cancellation import abort_subscan

result = abort_subscan(subscan_instance)
```

**Steps performed:**

1. Iterates `subscan.workflow_ids` (list of Temporal workflow IDs for this subscan).
2. Cancels each workflow via `TemporalClientProvider.cancel_workflow(wf_id)`.
3. Sets `subscan.status = ABORTED_TASK` and `subscan.stop_scan_date = now()`.
4. Creates a `ScanActivity("Subscan aborted", ABORTED_TASK)` record.

> **Order matters:** Workflows are cancelled **before** the DB state is updated to prevent race conditions where the worker reads the old "RUNNING" state and tries to continue.

---

## Temporal Cancellation Mechanism

**File:** `web/reNgine/temporal_client.py`

```python
@classmethod
def cancel_workflow(cls, workflow_id: str) -> None:
    """Cancel a running Temporal workflow synchronously."""
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

This sends a `RequestCancelExternalWorkflow` command to Temporal. The workflow receives a cancellation signal and will:
- Stop dispatching new activities.
- Wait for the current running activity to reach a cancellation checkpoint.
- Execute any cleanup logic before terminating.

---

## StressTestWorkflow: Kill Switch Signal

The `StressTestWorkflow` uses a custom **kill switch** signal instead of standard Temporal cancellation:

```python
@workflow.signal(name="kill_switch")
def kill_switch(self) -> None:
    """Signal the workflow to abort at the next endpoint/tool boundary."""
    self._kill_requested = True
    self._kill_event.set()
```

**Why a signal instead of cancellation?**
- The stress test is sequential across (endpoint × tool) pairs.
- The kill switch stops at the **next tool boundary** — it does not interrupt a running tool mid-execution.
- This is safer for stress tests where abrupt process termination could leave zombie processes.

### Sending the Kill Switch

```python
client = await TemporalClientProvider.get_client()
handle = client.get_workflow_handle(stress_workflow_id)
await handle.signal("kill_switch")
```

The workflow will stop at the next `if self._kill_requested` check, finalize the results it has so far, and return `{"status": "ABORTED"}`.

---

## API Endpoint for Scan Abort

Located in `api/views.py` (or `startScan/views.py`):

```http
POST /api/stopScan/{scan_history_id}/
```

This endpoint calls `abort_scan_history(scan)` internally.

---

## Status Constants (`reNgine/definitions.py`)

| Constant | Value | Description |
|---|---|---|
| `ABORTED_TASK` | `4` | Terminal state for aborted tasks |
| `RUNNING_TASK` | `1` | Running state |
| `SUCCESS_TASK` | `2` | Successful completion |
| `FAILED_TASK` | `3` | Failed state |
