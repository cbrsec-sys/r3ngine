import logging

import redis
from django.utils import timezone
from django.conf import settings

from startScan.models import ScanActivity, SubScan
from reNgine.temporal_client import TemporalClientProvider
from reNgine.definitions import ABORTED_TASK, RUNNING_TASK, PAUSED_TASK

logger = logging.getLogger(__name__)


def _scan_stop_key(scan_id: int) -> str:
    return f"scan_stop_{scan_id}"


def set_scan_stop_kill_switch(scan_id: int, enabled: bool, ttl_seconds: int = 24 * 60 * 60) -> None:
    """Best-effort kill switch used by executor workers to hard-stop orphaned tools."""
    if not scan_id:
        return

    try:
        redis_client = redis.Redis.from_url(getattr(settings, "REDIS_URL", "redis://redis:6379/0"))
        key = _scan_stop_key(scan_id)
        if enabled:
            redis_client.set(key, "1", ex=ttl_seconds)
        else:
            redis_client.delete(key)
    except Exception as exc:
        logger.warning("Failed to update scan stop kill switch for scan %s: %s", scan_id, exc)


def abort_subscan(subscan):
    try:
        set_scan_stop_kill_switch(subscan.scan_history_id, enabled=True)

        # Cancel all workflows FIRST, then update DB state
        for wf_id in subscan.workflow_ids:
            try:
                TemporalClientProvider.cancel_workflow(wf_id)
            except Exception as e:
                logger.error(f"Failed to cancel workflow {wf_id} for subscan {subscan.id}: {e}")

        # Now update DB state after workflows are cancelled
        subscan.status = ABORTED_TASK
        subscan.stop_scan_date = timezone.now()
        subscan.save()

        from reNgine.tasks import create_scan_activity
        create_scan_activity(subscan.scan_history.id, "Subscan aborted", ABORTED_TASK)

        return {'status': True}
    except Exception as e:
        logger.error(f"abort_subscan failed for subscan {subscan.id}: {e}")
        return {'status': False, 'message': str(e)}


def abort_scan_history(scan, aborted_by=None):
    try:
        set_scan_stop_kill_switch(scan.id, enabled=True)

        scan.scan_status = ABORTED_TASK
        scan.stop_scan_date = timezone.now()
        if aborted_by is not None:
            scan.aborted_by = aborted_by
        scan.save()

        for te in scan.temporal_executions.filter(status="RUNNING"):
            try:
                TemporalClientProvider.cancel_workflow(te.workflow_id)
                te.status = "CANCELLED"
                te.ended_at = timezone.now()
                te.save()
            except Exception as e:
                logger.error(f"Failed to cancel workflow {te.workflow_id} for scan {scan.id}: {e}")

        for subscan in SubScan.objects.filter(scan_history=scan, status__in=[RUNNING_TASK, PAUSED_TASK]):
            abort_subscan(subscan)

        for task in ScanActivity.objects.filter(scan_of=scan, status=RUNNING_TASK).order_by('-pk'):
            task.status = ABORTED_TASK
            task.time = timezone.now()
            task.save()

        from reNgine.tasks import create_scan_activity
        create_scan_activity(scan.id, "Scan aborted", ABORTED_TASK)

        return {'status': True}
    except Exception as e:
        logger.error(f"abort_scan_history failed for scan {scan.id}: {e}")
        return {'status': False, 'message': str(e)}
