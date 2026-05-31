from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
	"""
	Migration 0014: Add MobilePushToken model.

	Creates the dashboard_mobilepushtoken table to store Expo push notification
	tokens registered by authenticated mobile users. Tokens are used by the
	backend to dispatch push notifications via the Expo Push Notification Service
	without requiring Firebase / FCM setup.
	"""

	dependencies = [
		('auth', '0012_alter_user_first_name_max_length'),
		('dashboard', '0013_userpreferences_enable_scan_queueing'),
	]

	operations = [
		migrations.CreateModel(
			name='MobilePushToken',
			fields=[
				('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				# The Expo push token string, must be unique per token value
				('token', models.CharField(max_length=500, unique=True)),
				# Optional human-readable label for the device
				('device_label', models.CharField(blank=True, max_length=100, null=True)),
				# Flag to soft-disable a token without deleting it
				('is_active', models.BooleanField(default=True)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
				# FK to the auth user who owns this token
				('user', models.ForeignKey(
					on_delete=django.db.models.deletion.CASCADE,
					related_name='push_tokens',
					to='auth.user',
				)),
			],
			options={
				'verbose_name': 'Mobile Push Token',
				'verbose_name_plural': 'Mobile Push Tokens',
				'ordering': ['-updated_at'],
			},
		),
	]
