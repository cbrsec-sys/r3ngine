from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scanEngine', '0010_alter_vulnerabilityreportsetting_executive_summary_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='installedexternaltool',
            name='install_command',
            field=models.CharField(max_length=500),
        ),
        migrations.AlterField(
            model_name='installedexternaltool',
            name='update_command',
            field=models.CharField(max_length=500, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='installedexternaltool',
            name='version_lookup_command',
            field=models.CharField(max_length=500, null=True, blank=True),
        ),
    ]
