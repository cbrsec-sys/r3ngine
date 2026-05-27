from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("startScan", "0029_temporal_schedule_model"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scanhistory",
            old_name="celery_ids",
            new_name="workflow_ids",
        ),
        migrations.RenameField(
            model_name="subscan",
            old_name="celery_ids",
            new_name="workflow_ids",
        ),
        migrations.RenameField(
            model_name="scanactivity",
            old_name="celery_id",
            new_name="execution_id",
        ),
    ]
