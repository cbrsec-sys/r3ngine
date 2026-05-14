from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_celery_beat.models import PeriodicTask, IntervalSchedule, ClockedSchedule
from rest_framework.permissions import IsAuthenticated
from .permissions import HasPermission
from reNgine.definitions import PERM_INITATE_SCANS_SUBSCANS, PERM_MODIFY_SCAN_RESULTS
import json

class PeriodicTaskSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()
    frequency = serializers.SerializerMethodField()
    
    class Meta:
        model = PeriodicTask
        fields = [
            'id', 'name', 'task', 'description', 'frequency', 
            'enabled', 'last_run_at', 'total_run_count', 
            'one_off', 'kwargs', 'date_changed'
        ]

    def get_description(self, obj):
        if ":" in obj.name:
            return obj.name.split(":")[0]
        return obj.name

    def get_frequency(self, obj):
        if obj.interval:
            return f"Every {obj.interval.every} {obj.interval.period}"
        if obj.clocked:
            return f"Once at {obj.clocked.clocked_time}"
        if obj.crontab:
            return str(obj.crontab)
        return "N/A"

class ScheduledScanViewSet(viewsets.ModelViewSet):
    queryset = PeriodicTask.objects.all().exclude(name='celery.backend_cleanup').order_by('-date_changed')
    serializer_class = PeriodicTaskSerializer
    permission_classes = [IsAuthenticated, HasPermission]
    permission_required = PERM_INITATE_SCANS_SUBSCANS

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        task = self.get_object()
        task.enabled = not task.enabled
        task.save()
        return Response({'status': True, 'enabled': task.enabled})

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'status': False, 'message': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        PeriodicTask.objects.filter(id__in=ids).delete()
        return Response({'status': True, 'message': f'Deleted {len(ids)} tasks'})
