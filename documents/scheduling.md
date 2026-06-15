# r3ngine — Scheduling

## Overview

r3ngine uses **Temporal Schedules** to replace the previous `django_celery_beat` periodic task system. Two types of scheduled scans are supported:

1. **Periodic scans** — repeat at a fixed interval (e.g., every 24 hours).
2. **Clocked scans** — run once at a specific date/time.

Domain monitoring uses a deterministic schedule ID keyed to the domain.

**File:** `web/reNgine/temporal_schedule_utils.py`

---

## How Temporal Schedules Work

A Temporal Schedule is a server-side object that fires `ScheduledScanWorkflow` at the configured interval. Unlike cron jobs or Celery beat:

- Schedules are durable — they survive server restarts.
- A `TemporalSchedule` DB record is always created alongside the Temporal Schedule for management UI queries.
- The `ScheduleOverlapPolicy.SKIP` policy ensures a new scan doesn't start if the previous one is still running.

---

## Periodic Scans

### `_create_periodic_temporal_schedule(name, interval_seconds, workflow_args, domain_id=None)`

Creates a Temporal Schedule that fires `ScheduledScanWorkflow` every `interval_seconds`.

**Example:**
```python
from reNgine.temporal_schedule_utils import _create_periodic_temporal_schedule

record = _create_periodic_temporal_schedule(
    name="Daily Scan — example.com",
    interval_seconds=86400,
    workflow_args={"domain_id": 1, "engine_id": 3},
    domain_id=1,
)
```

**Schedule ID format:** `scan-periodic-{12-char-hex}`

---

## Clocked (One-Shot) Scans

### `_create_clocked_temporal_schedule(name, clocked_time, workflow_args, domain_id=None)`

Creates a Temporal Schedule that fires once at `clocked_time` and then exhausts itself (`remaining_actions=1`).

**Example:**
```python
from reNgine.temporal_schedule_utils import _create_clocked_temporal_schedule
import datetime

record = _create_clocked_temporal_schedule(
    name="One-off Scan — example.com",
    clocked_time=datetime.datetime(2025, 6, 1, 12, 0),
    workflow_args={"domain_id": 1, "engine_id": 3},
    domain_id=1,
)
```

**Schedule ID format:** `scan-clocked-{12-char-hex}`

---

## Domain Monitoring

### `_upsert_monitoring_temporal_schedule(domain)`

Creates or replaces the monitoring schedule for a domain. Uses a deterministic ID:

**Schedule ID:** `monitoring-{domain.id}`

This ensures each domain has exactly one schedule, and changing the frequency simply recreates it.

**Supported frequencies:**

| Value | Interval |
|---|---|
| `hourly` | 3600s |
| `daily` | 86400s |
| `weekly` | 604800s |
| `monthly` | 2592000s |

### `_delete_monitoring_temporal_schedule(domain)`

Deletes the monitoring schedule and the `TemporalSchedule` DB record.

---

## Schedule Management

### Pausing a Schedule

```python
from reNgine.temporal_schedule_utils import _pause_temporal_schedule

_pause_temporal_schedule("scan-periodic-a1b2c3d4e5f6")
```

### Resuming a Schedule

```python
from reNgine.temporal_schedule_utils import _unpause_temporal_schedule

_unpause_temporal_schedule("scan-periodic-a1b2c3d4e5f6")
```

### Deleting a Schedule

```python
from reNgine.temporal_schedule_utils import _delete_temporal_schedule_by_id

_delete_temporal_schedule_by_id("scan-periodic-a1b2c3d4e5f6")
```

---

## `TemporalSchedule` Model (`startScan/models.py`)

Mirrors each Temporal Schedule with a Django DB record for management views.

| Field | Type | Description |
|---|---|---|
| `schedule_id` | `CharField` | Temporal Schedule ID |
| `name` | `CharField` | Human-readable name |
| `workflow_type` | `CharField` | e.g., `ScheduledScanWorkflow` |
| `workflow_args` | `JSONField` | Args passed to the workflow |
| `interval_seconds` | `IntegerField` | Repeat interval (null for clocked) |
| `clocked_time` | `DateTimeField` | Fire-at time (null for periodic) |
| `one_off` | `BooleanField` | True for clocked one-shot |
| `is_active` | `BooleanField` | Whether schedule is active |
| `domain` | `ForeignKey` | Associated domain (optional) |

---

## `ScheduledScanWorkflow`

```python
@workflow.defn(name="ScheduledScanWorkflow")
class ScheduledScanWorkflow:
    async def run(self, params: dict) -> dict:
        ctx = await workflow.execute_activity("SetupScheduledScanActivity", args=[params], ...)
        result = await workflow.execute_child_workflow("MasterScanWorkflow", args=[ctx], ...)
        return result
```

1. `SetupScheduledScanActivity` creates the `ScanHistory` record, sets up initial subdomain/endpoint data, and returns a complete `ctx`.
2. `MasterScanWorkflow` runs the full scan pipeline as a child workflow with the prepared context.

---

## Frequency Conversion

```python
from reNgine.temporal_schedule_utils import interval_to_seconds

seconds = interval_to_seconds(frequency_value=7, frequency_type='days')
# Returns: 604800
```

Supported `frequency_type` values: `'minutes'`, `'hours'`, `'days'`, `'weeks'`, `'months'`.
