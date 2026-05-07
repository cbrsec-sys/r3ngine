from rest_framework import serializers
from .models import Plugin

class PluginSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plugin
        fields = [
            'id', 'name', 'slug', 'version', 'description', 
            'is_enabled', 'anchor_step', 'runtime_position', 
            'order_weight', 'manifest', 'installed_at', 
            'updated_at', 'icon_path'
        ]
        read_only_fields = ['id', 'slug', 'installed_at', 'updated_at', 'manifest']
