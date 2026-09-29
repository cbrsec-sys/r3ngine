from django.db.models.signals import pre_delete
from django.dispatch import receiver
import logging
from startScan.models import ScanHistory, SubScan
from reNgine.temporal_client import TemporalClientProvider
from reNgine.utils.results_fs import remove_results_dir

logger = logging.getLogger(__name__)

@receiver(pre_delete, sender=ScanHistory)
def cancel_scan_workflows_and_cleanup(sender, instance, **kwargs):
    """Cancel all running Temporal workflows associated with this ScanHistory and delete results directory."""
    logger.info(f"Pre-delete signal triggered for ScanHistory ID: {instance.id}")
    # Cancel running workflows
    try:
        if hasattr(instance, 'temporal_executions'):
            for te in instance.temporal_executions.filter(status="RUNNING"):
                try:
                    logger.info(f"Cancelling Temporal workflow {te.workflow_id} for ScanHistory ID {instance.id}")
                    TemporalClientProvider.cancel_workflow(te.workflow_id)
                    te.status = "CANCELLED"
                    te.save()
                except Exception as e:
                    logger.warning(f"Failed to cancel workflow {te.workflow_id} during ScanHistory deletion: {e}")
    except Exception as e:
        logger.warning(f"Failed to query temporal executions for ScanHistory ID {instance.id}: {e}")

    # The one place a scan's results directory is removed; views only delete the row.
    try:
        if remove_results_dir(instance.results_dir):
            logger.info("Removed scan results directory %s", instance.results_dir)
    except OSError:
        logger.warning(
            "Failed to remove results directory %s during ScanHistory deletion",
            instance.results_dir, exc_info=True,
        )


@receiver(pre_delete, sender=SubScan)
def cancel_subscan_workflows(sender, instance, **kwargs):
    """Cancel running Temporal workflows associated with this SubScan."""
    logger.info(f"Pre-delete signal triggered for SubScan ID: {instance.id}")
    if instance.workflow_ids:
        for wf_id in instance.workflow_ids:
            try:
                logger.info(f"Cancelling Temporal workflow {wf_id} for SubScan ID {instance.id}")
                TemporalClientProvider.cancel_workflow(wf_id)
            except Exception as e:
                logger.warning(f"Failed to cancel subscan workflow {wf_id} during SubScan deletion: {e}")
