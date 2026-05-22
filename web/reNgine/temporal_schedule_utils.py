"""
Temporal Schedule helpers for scan scheduling.

Called from synchronous Django views (schedule_scan, schedule_organization_scan)
to create Temporal Schedules in place of django_celery_beat PeriodicTask rows.

Each helper:
  1. Creates a Temporal Schedule via asyncio.run() (sync→async bridge).
  2. Writes a TemporalSchedule DB record for the management views (Phase 4E).
  3. Returns the TemporalSchedule instance.
"""

import asyncio
import datetime
import logging
import uuid

from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleCalendarSpec,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleRange,
    ScheduleSpec,
    ScheduleState,
)
from temporalio.common import WorkflowIDReusePolicy

from reNgine.temporal_client import TemporalClientProvider

logger = logging.getLogger(__name__)

_FREQUENCY_TO_SECONDS = {
    'minutes': 60,
    'hours': 3600,
    'days': 86400,
    'weeks': 7 * 86400,
    'months': 30 * 86400,
}


def interval_to_seconds(frequency_value: int, frequency_type: str) -> int:
    """Convert a (value, type) pair from the schedule form to total seconds."""
    return frequency_value * _FREQUENCY_TO_SECONDS.get(frequency_type, 3600)


def _create_periodic_temporal_schedule(
    name: str,
    interval_seconds: int,
    workflow_args: dict,
    domain_id: int = None,
) -> object:
    """Create a repeating Temporal Schedule and a TemporalSchedule DB record.

    The schedule fires every `interval_seconds` seconds and starts
    ScheduledScanWorkflow with `workflow_args` as its input.

    Args:
        name: Human-readable schedule name (shown in UI).
        interval_seconds: Repeat interval in seconds.
        workflow_args: Dict passed to ScheduledScanWorkflow (domain_id, engine_id, etc.).
        domain_id: Optional FK for the TemporalSchedule DB record.

    Returns:
        TemporalSchedule: The newly created DB record.
    """
    from startScan.models import TemporalSchedule

    schedule_id = f"scan-periodic-{uuid.uuid4().hex[:12]}"

    async def _create():
        client = await TemporalClientProvider.get_client()
        await client.create_schedule(
            schedule_id,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    "ScheduledScanWorkflow",
                    args=[workflow_args],
                    id=f"{schedule_id}-run",
                    task_queue="python-orchestrator-queue",
                    id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
                ),
                spec=ScheduleSpec(
                    intervals=[ScheduleIntervalSpec(
                        every=datetime.timedelta(seconds=interval_seconds)
                    )],
                ),
                policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
                state=ScheduleState(note=f"Periodic scan: {name}"),
            ),
        )

    TemporalClientProvider.reset()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_create())
    finally:
        loop.close()

    domain = None
    if domain_id:
        from targetApp.models import Domain
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            pass

    record = TemporalSchedule.objects.create(
        schedule_id=schedule_id,
        name=name,
        workflow_type='ScheduledScanWorkflow',
        workflow_args=workflow_args,
        interval_seconds=interval_seconds,
        is_active=True,
        domain=domain,
    )
    logger.info(f"[ScheduleUtils] Created periodic schedule '{schedule_id}' every {interval_seconds}s")
    return record


def _create_clocked_temporal_schedule(
    name: str,
    clocked_time,
    workflow_args: dict,
    domain_id: int = None,
) -> object:
    """Create a one-shot clocked Temporal Schedule and a TemporalSchedule DB record.

    The schedule fires once at `clocked_time` then exhausts itself.

    Args:
        name: Human-readable schedule name.
        clocked_time: datetime or ISO-format string for when to fire.
        workflow_args: Dict passed to ScheduledScanWorkflow.
        domain_id: Optional FK for the TemporalSchedule DB record.

    Returns:
        TemporalSchedule: The newly created DB record.
    """
    from startScan.models import TemporalSchedule

    if isinstance(clocked_time, str):
        clocked_dt = datetime.datetime.fromisoformat(clocked_time)
    else:
        clocked_dt = clocked_time

    # Strip timezone for ScheduleCalendarSpec (uses server-side timezone)
    if hasattr(clocked_dt, 'tzinfo') and clocked_dt.tzinfo is not None:
        clocked_dt = clocked_dt.replace(tzinfo=None)

    schedule_id = f"scan-clocked-{uuid.uuid4().hex[:12]}"

    async def _create():
        client = await TemporalClientProvider.get_client()
        await client.create_schedule(
            schedule_id,
            Schedule(
                action=ScheduleActionStartWorkflow(
                    "ScheduledScanWorkflow",
                    args=[workflow_args],
                    id=f"{schedule_id}-run",
                    task_queue="python-orchestrator-queue",
                    id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
                ),
                spec=ScheduleSpec(
                    calendars=[ScheduleCalendarSpec(
                        year=[ScheduleRange(clocked_dt.year)],
                        month=[ScheduleRange(clocked_dt.month)],
                        day_of_month=[ScheduleRange(clocked_dt.day)],
                        hour=[ScheduleRange(clocked_dt.hour)],
                        minute=[ScheduleRange(clocked_dt.minute)],
                    )],
                ),
                policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
                state=ScheduleState(
                    limited_actions=True,
                    remaining_actions=1,
                    note=f"Clocked scan: {name}",
                ),
            ),
        )

    TemporalClientProvider.reset()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_create())
    finally:
        loop.close()

    domain = None
    if domain_id:
        from targetApp.models import Domain
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            pass

    record = TemporalSchedule.objects.create(
        schedule_id=schedule_id,
        name=name,
        workflow_type='ScheduledScanWorkflow',
        workflow_args=workflow_args,
        clocked_time=clocked_dt,
        one_off=True,
        is_active=True,
        domain=domain,
    )
    logger.info(f"[ScheduleUtils] Created clocked schedule '{schedule_id}' at {clocked_dt}")
    return record
