"""
Migration: 0041_parameter_cpde_fields

Adds CPDE (Custom Parameter Discovery Engine) intelligence fields to the
Parameter model. All new columns are either nullable or carry Django-level
defaults, making this migration safe to run against existing data with zero
downtime on PostgreSQL (each is a single ADD COLUMN with a DEFAULT).
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('startScan', '0040_subdomain_unique_per_scan'),
    ]

    operations = [
        # ── Confidence score ──────────────────────────────────────────────────
        migrations.AddField(
            model_name='parameter',
            name='confidence',
            field=models.IntegerField(
                default=0,
                help_text='0-100 confidence score aggregated from all evidence sources',
            ),
        ),
        # ── Evidence sources (JSON list of tool labels) ───────────────────────
        migrations.AddField(
            model_name='parameter',
            name='sources',
            field=models.JSONField(
                default=list,
                help_text="Evidence source labels e.g. ['arjun','js_ast','openapi']",
            ),
        ),
        # ── Parameter location ────────────────────────────────────────────────
        migrations.AddField(
            model_name='parameter',
            name='param_location',
            field=models.CharField(
                blank=True,
                max_length=50,
                null=True,
                help_text='json_body|query_string|header|graphql_var|form_data|path',
            ),
        ),
        # ── JS-inferred data type ─────────────────────────────────────────────
        migrations.AddField(
            model_name='parameter',
            name='data_type',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                help_text='Inferred JS type: string, number, boolean, object, array',
            ),
        ),
        # ── Auth-related flag ─────────────────────────────────────────────────
        migrations.AddField(
            model_name='parameter',
            name='is_auth_related',
            field=models.BooleanField(
                default=False,
                help_text='True when name matches auth header/token patterns',
            ),
        ),
        # ── Source-type observation flags ─────────────────────────────────────
        migrations.AddField(
            model_name='parameter',
            name='observed_in_js',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parameter',
            name='observed_in_openapi',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parameter',
            name='observed_in_graphql',
            field=models.BooleanField(default=False),
        ),
        # ── Direct scan FK (denormalized for efficient scan-scoped queries) ───
        migrations.AddField(
            model_name='parameter',
            name='scan_history',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='parameters',
                to='startScan.scanhistory',
                help_text='Direct scan FK — denormalized for efficient scan-scoped queries',
            ),
        ),
    ]
