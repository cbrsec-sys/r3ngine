"""
Phase 4G — Remove Domain.monitor_periodic_task FK.

This field was replaced by Domain.temporal_schedule (added in 4A).
All monitored domains were migrated to Temporal Schedules in 4F.

Uses SeparateDatabaseAndState + IF EXISTS so this is safe for both:
  - Existing installs: the column exists and is dropped.
  - Fresh installs: 0002 skipped creating the column (SeparateDatabaseAndState
    with no database_operations); IF EXISTS prevents a "column not found" error.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('targetApp', '0007_migrate_monitoring_to_temporal'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE "targetApp_domain" DROP COLUMN IF EXISTS monitor_periodic_task_id',
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name='domain',
                    name='monitor_periodic_task',
                ),
            ],
        ),
    ]
