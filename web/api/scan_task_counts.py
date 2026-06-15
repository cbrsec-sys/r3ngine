from reNgine.definitions import SUCCESS_TASK, FAILED_TASK


def get_task_counts(scan):
    """Return (successful, failed, total) task counts for a ScanHistory instance.

    A task is counted as failed only if it has a FAILED_TASK record with no
    matching SUCCESS_TASK record for the same name — this excludes Temporal
    retry artifacts where an activity fails then succeeds on a later attempt.
    """
    success_names = set(
        scan.scanactivity_set.filter(status=SUCCESS_TASK)
        .values_list('name', flat=True)
    )
    successful = len(success_names)
    failed = (
        scan.scanactivity_set
        .filter(status=FAILED_TASK)
        .exclude(name__in=success_names)
        .values('name').distinct().count()
    )
    db_total = scan.scanactivity_set.values('name').distinct().count()
    total = db_total if db_total > 0 else len(scan.tasks or [])
    return successful, failed, total

