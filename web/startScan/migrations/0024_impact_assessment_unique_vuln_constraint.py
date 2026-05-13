"""
Migration: 0024_impact_assessment_unique_vuln_constraint

Deduplicates existing ImpactAssessment rows before adding the unique constraint.
The correlation engine and APME could previously both create rows for the same
vulnerability, leaving multiple duplicates in the database.

Strategy:
  1. For each vulnerability_id that has more than one ImpactAssessment row,
     keep only the most recently updated record and delete the rest.
  2. Add a UniqueConstraint on vulnerability_id (non-null only) so this
     cannot happen again.
"""

from django.db import migrations, models
from django.db.models import Count


def deduplicate_impact_assessments(apps, schema_editor):
    """
    Remove duplicate ImpactAssessment rows per vulnerability, keeping the
    most recently updated record for each vulnerability_id.
    """
    ImpactAssessment = apps.get_model('startScan', 'ImpactAssessment')

    # Find all vulnerability_ids that have duplicates
    duplicated_vuln_ids = (
        ImpactAssessment.objects
        .filter(vulnerability__isnull=False)
        .values('vulnerability_id')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
        .values_list('vulnerability_id', flat=True)
    )

    deleted_total = 0
    for vuln_id in duplicated_vuln_ids:
        # Fetch all rows for this vulnerability ordered newest-first
        rows = list(
            ImpactAssessment.objects
            .filter(vulnerability_id=vuln_id)
            .order_by('-updated_at')
            .values_list('id', flat=True)
        )
        # Keep the first (most recent), delete all others
        ids_to_delete = rows[1:]
        count, _ = ImpactAssessment.objects.filter(id__in=ids_to_delete).delete()
        deleted_total += count

    if deleted_total:
        print(f"\n  Deduplicated ImpactAssessment: deleted {deleted_total} duplicate row(s).")


def noop_reverse(apps, schema_editor):
    """No-op: deduplication cannot be meaningfully reversed."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('startScan', '0023_auto_20260511_1949'),
    ]

    operations = [
        # Step 1: Deduplicate existing rows so the constraint can be created cleanly.
        migrations.RunPython(deduplicate_impact_assessments, noop_reverse),

        # Step 2: Add the uniqueness constraint now that the data is clean.
        migrations.AddConstraint(
            model_name='impactassessment',
            constraint=models.UniqueConstraint(
                fields=['vulnerability'],
                condition=models.Q(vulnerability__isnull=False),
                name='unique_impact_assessment_per_vulnerability',
            ),
        ),
    ]
