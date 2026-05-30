from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scanEngine', '0011_installedexternaltool_increase_command_lengths'),
    ]

    operations = [
        migrations.AddField(
            model_name='proxy',
            name='use_tor',
            field=models.BooleanField(default=False),
        ),
    ]
