from rest_framework import serializers
from .models import Plugin


class PluginSerializer(serializers.ModelSerializer):
    needs_restart = serializers.SerializerMethodField()

    class Meta:
        model = Plugin
        fields = [
            'id', 'name', 'slug', 'version', 'description',
            'is_enabled', 'anchor_step', 'runtime_position',
            'order_weight', 'manifest', 'installed_at',
            'updated_at', 'icon_path', 'needs_restart',
            'author', 'trust_level',
        ]
        read_only_fields = [
            'id', 'slug', 'installed_at', 'updated_at',
            'manifest', 'author', 'trust_level',
        ]

    def get_needs_restart(self, obj):
        from django.core.cache import cache
        return cache.get(f"plugin_{obj.slug}_needs_restart", True)
