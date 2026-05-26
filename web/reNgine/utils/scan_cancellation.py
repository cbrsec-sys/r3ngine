import logging

from django.utils import timezone

from startScan.models import ScanActivity, ScanHistory, SubScan
from reNgine.temporal_client import TemporalClientProvider
from reNgine.definitions import ABORTED_TASK, RUNNING_TASK

logger = logging.getLogger(__name__)


def abort_subscan(subscan):
    try:
        subscan.status = ABORTED_TASK
        subscan.stop_scan_date = timezone.now()
        subscan.save()

        for wf_id in subscan.workflow_ids:
            try:
                TemporalClientProvider.cancel_workflow(wf_id)
            except Exception as e:
                logger.error(f"Failed to cancel workflow {wf_id} for subscan {subscan.id}: {e}")

        from reNgine.tasks import create_scan_activity
        create_scan_activity(subscan.scan_history.id, "Subscan aborted", ABORTED_TASK)

        return {'status': True}
    except Exception as e:
        logger.error(f"abort_subscan failed for subscan {subscan.id}: {e}")
        return {'status': False, 'message': str(e)}


def abort_scan_history(scan, aborted_by=None):
    try:
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

        for subscan in SubScan.objects.filter(scan_history=scan, status=RUNNING_TASK):
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
