"""Store remote worker tokens as SHA-256 hashes instead of plaintext.

Existing workers keep working: they present the same token, and its hash is
what the heartbeat now compares against.
"""
import hashlib

from django.db import migrations, models


def hash_existing_tokens(apps, schema_editor):
    ScanWorker = apps.get_model('scanEngine', 'ScanWorker')
    for worker in ScanWorker.objects.all():
        worker.auth_token_hash = hashlib.sha256(worker.auth_token.encode('utf-8')).hexdigest()
        worker.save(update_fields=['auth_token_hash'])


class Migration(migrations.Migration):

    dependencies = [
        ('scanEngine', '0018_tool_inventory_and_arg_cache'),
    ]

    operations = [
        migrations.AddField(
            model_name='scanworker',
            name='auth_token_hash',
            field=models.CharField(max_length=64, null=True),
        ),
        # No reverse: the plaintext tokens cannot be recovered from their hashes.
        migrations.RunPython(hash_existing_tokens),
        migrations.RemoveField(
            model_name='scanworker',
            name='auth_token',
        ),
        migrations.AlterField(
            model_name='scanworker',
            name='auth_token_hash',
            field=models.CharField(max_length=64, unique=True),
        ),
    ]
