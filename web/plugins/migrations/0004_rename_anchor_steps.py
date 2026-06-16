# web/plugins/migrations/0004_rename_anchor_steps.py
from django.db import migrations

RENAMES = {
    'subdomain_discovery': 'tier_1',
    'fetch_url': 'tier_3',
    'dir_file_fuzz': 'tier_4',
    'web_api_discovery': 'tier_5',
    'vulnerability_scan': 'tier_6',
    'vulnerability_correlation': 'tier_7',
    # tier_2 and standalone are already correct — no rename needed
}

REVERSE_RENAMES = {v: k for k, v in RENAMES.items()}


def rename_anchor_steps(apps, schema_editor):
    Plugin = apps.get_model('plugins', 'Plugin')
    for old, new in RENAMES.items():
        Plugin.objects.filter(anchor_step=old).update(anchor_step=new)


def reverse_rename_anchor_steps(apps, schema_editor):
    Plugin = apps.get_model('plugins', 'Plugin')
    for old, new in REVERSE_RENAMES.items():
        Plugin.objects.filter(anchor_step=old).update(anchor_step=new)


class Migration(migrations.Migration):

    dependencies = [
        ('plugins', '0003_plugin_author_trust_level'),
    ]

    operations = [
        migrations.RunPython(rename_anchor_steps, reverse_code=reverse_rename_anchor_steps),
    ]
