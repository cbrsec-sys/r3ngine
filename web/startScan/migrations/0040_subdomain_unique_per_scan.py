from django.db import migrations, models
from django.db.models import Count, Min
from django.db.models.functions import Lower


def dedupe_subdomains(apps, schema_editor):
    """Merge duplicate subdomain rows before adding the unique constraint."""
    Subdomain = apps.get_model('startScan', 'Subdomain')
    EndPoint = apps.get_model('startScan', 'EndPoint')

    duplicate_groups = (
        Subdomain.objects
        .filter(scan_history_id__isnull=False)
        .annotate(norm_name=Lower('name'))
        .values('scan_history_id', 'norm_name')
        .annotate(cnt=Count('id'), keep_id=Min('id'))
        .filter(cnt__gt=1)
    )

    for group in duplicate_groups:
        scan_history_id = group['scan_history_id']
        norm_name = group['norm_name']
        keep_id = group['keep_id']
        duplicate_ids = list(
            Subdomain.objects
            .filter(scan_history_id=scan_history_id)
            .annotate(norm_name=Lower('name'))
            .filter(norm_name=norm_name)
            .exclude(id=keep_id)
            .values_list('id', flat=True)
        )
        if not duplicate_ids:
            continue
        EndPoint.objects.filter(subdomain_id__in=duplicate_ids).update(subdomain_id=keep_id)
        Subdomain.objects.filter(id__in=duplicate_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('startScan', '0039_cveid_is_poc_cveid_is_template'),
    ]

    operations = [
        migrations.RunPython(dedupe_subdomains, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='subdomain',
            constraint=models.UniqueConstraint(
                fields=('scan_history', 'name'),
                name='unique_subdomain_per_scan',
            ),
        ),
    ]
