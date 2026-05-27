"""
Phase 4F Data Migration — Move domain monitoring from Celery Beat to Temporal Schedules.

For each Domain row where:
  - is_monitored = True
  - monitor_periodic_task is NOT NULL  (had a Celery Beat schedule)
  - temporal_schedule IS NULL          (not yet migrated by the 4D UI path)

...this migration:
  1. Creates a Temporal Schedule on the Temporal server.
  2. Creates a TemporalSchedule DB record.
  3. Sets Domain.temporal_schedule FK to that record.

REQUIRES: Temporal server must be reachable when this migration runs.

If Temporal is unreachable, each domain is skipped (with an error log) and the
migration still completes — run scripts/migrate_monitoring_to_temporal.py
manually once Temporal is available to finish any skipped domains.

Rollback (reverse_migration): deletes the Temporal Schedules and DB records
created by this migration, restoring Domain.temporal_schedule to NULL.
The monitor_periodic_task FK is NOT touched by either direction — it is
removed in Phase 4G.
"""

import logging
from django.db import migrations

logger = logging.getLogger(__name__)


def forward_migration(apps, schema_editor):
    from targetApp.models import Domain
    from reNgine.temporal_schedule_utils import _upsert_monitoring_temporal_schedule

    candidates = Domain.objects.filter(
        is_monitored=True,
        temporal_schedule__isnull=True,
    )
    total = candidates.count()
    if total == 0:
        logger.info("[4F Migration] No domains to migrate.")
        return

    logger.info(f"[4F Migration] Migrating {total} monitored domain(s) to Temporal Schedules...")
    migrated = 0
    failed = 0

    for domain in candidates:
        try:
            ts = _upsert_monitoring_temporal_schedule(domain)
            domain.temporal_schedule = ts
            domain.save(update_fields=['temporal_schedule'])
            migrated += 1
            logger.info(f"[4F Migration] ✓ domain_id={domain.id} name={domain.name} schedule={ts.schedule_id}")
        except Exception as e:
            failed += 1
            logger.error(
                f"[4F Migration] ✗ domain_id={domain.id} name={domain.name} error={e}\n"
                f"  Run scripts/migrate_monitoring_to_temporal.py to retry this domain."
            )

    logger.info(
        f"[4F Migration] Complete — migrated={migrated} failed={failed} total={total}"
    )
    if failed:
        logger.warning(
            f"[4F Migration] {failed} domain(s) could not be migrated. "
            "Ensure Temporal is running and execute: "
            "docker compose exec web python3 scripts/migrate_monitoring_to_temporal.py"
        )


def reverse_migration(apps, schema_editor):
    from targetApp.models import Domain
    from reNgine.temporal_schedule_utils import _delete_temporal_schedule_by_id

    # Only reverse monitoring schedules (workflow_type='MonitoringWorkflow')
    # to avoid touching scan schedules created via 4C/4D
    candidates = Domain.objects.filter(
        temporal_schedule__isnull=False,
        temporal_schedule__workflow_type='MonitoringWorkflow',
    )
    total = candidates.count()
    logger.info(f"[4F Reverse] Removing {total} Temporal monitoring schedule(s)...")

    reversed_count = 0
    for domain in candidates:
        try:
            ts = domain.temporal_schedule
            _delete_temporal_schedule_by_id(ts.schedule_id)
            domain.temporal_schedule = None
            domain.save(update_fields=['temporal_schedule'])
            ts.delete()
            reversed_count += 1
        except Exception as e:
            logger.error(f"[4F Reverse] Failed for domain_id={domain.id}: {e}")

    logger.info(f"[4F Reverse] Complete — reversed={reversed_count}")


class Migration(migrations.Migration):
    # Non-atomic so partial per-domain progress is committed even if some
    # domains fail (Temporal unreachable, network timeout, etc.)
    atomic = False

    dependencies = [
        ('targetApp', '0006_temporal_schedule_model'),
    ]

    operations = [
        migrations.RunPython(forward_migration, reverse_migration),
    ]
