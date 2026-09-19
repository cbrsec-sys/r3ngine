import uuid
from django.conf import settings
from django.db import models


class McpInstanceSettings(models.Model):
    TRANSPORT_STDIO = 'stdio'
    TRANSPORT_HTTP = 'http'
    TRANSPORT_BOTH = 'both'
    TRANSPORT_CHOICES = (
        (TRANSPORT_STDIO, 'stdio'),
        (TRANSPORT_HTTP, 'http'),
        (TRANSPORT_BOTH, 'both'),
    )
    transport_mode = models.CharField(
        max_length=8, choices=TRANSPORT_CHOICES, default=TRANSPORT_STDIO
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class McpApiKey(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mcp_api_keys'
    )
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=16)
    key_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'name')

    def is_active(self) -> bool:
        return self.revoked_at is None


class McpSession(models.Model):
    CONNECTED_WINDOW_SECONDS = 120

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.ForeignKey(McpApiKey, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mcp_sessions'
    )
    transport = models.CharField(max_length=8, choices=(('stdio', 'stdio'), ('http', 'http')))
    client_name = models.CharField(max_length=200, blank=True, default='')
    client_version = models.CharField(max_length=100, blank=True, default='')
    user_agent = models.CharField(max_length=300, blank=True, default='')
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def is_connected(self) -> bool:
        from datetime import timedelta
        from django.utils import timezone
        if self.revoked_at or self.ended_at:
            return False
        return self.last_seen_at >= timezone.now() - timedelta(seconds=self.CONNECTED_WINDOW_SECONDS)


class McpAuditEvent(models.Model):
    session = models.ForeignKey(
        McpSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='events'
    )
    key = models.ForeignKey(
        McpApiKey, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_events'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='mcp_audit_events'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    tool_name = models.CharField(max_length=120, blank=True, default='')
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=300)
    status_code = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField(default=0)
    request_body = models.JSONField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    truncated = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
