from django.db import models
from django.utils import timezone

class Plugin(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    version = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    is_enabled = models.BooleanField(default=True)
    
    # Sequencing details
    anchor_step = models.CharField(max_length=255, help_text="Core engine task name this plugin attaches to")
    RUNTIME_POSITION_CHOICES = [
        ('BEFORE', 'Before'),
        ('AFTER', 'After'),
    ]
    runtime_position = models.CharField(max_length=10, choices=RUNTIME_POSITION_CHOICES, default='AFTER')
    order_weight = models.IntegerField(default=0, help_text="Used for relative sorting within the same anchor/position")
    
    # Metadata
    manifest = models.JSONField(default=dict)
    installed_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Logo or icon path relative to plugin dir
    icon_path = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['anchor_step', 'runtime_position', 'order_weight', 'name']

    def __str__(self):
        return f"{self.name} ({self.version})"
