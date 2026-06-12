from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0016_projectdiscoveryapikey'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='linkedincredentials',
            name='password',
        ),
        migrations.AddField(
            model_name='linkedincredentials',
            name='cookies_json',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='linkedincredentials',
            name='state_file_path',
            field=models.CharField(blank=True, default='', max_length=1000),
        ),
        migrations.AddField(
            model_name='linkedincredentials',
            name='last_validated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='linkedincredentials',
            name='is_valid',
            field=models.BooleanField(default=False),
        ),
    ]
