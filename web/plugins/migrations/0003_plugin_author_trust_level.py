from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plugins', '0002_plugin_tools_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='plugin',
            name='author',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='plugin',
            name='trust_level',
            field=models.CharField(default='unsigned', max_length=20),
        ),
    ]
