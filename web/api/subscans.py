from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from startScan.models import SubScan
from .serializers import SubScanSerializer
from .permissions import HasPermission
from reNgine.definitions import PERM_INITATE_SCANS_SUBSCANS, ABORTED_TASK
from reNgine.celery import app

class SubScanViewSet(viewsets.ModelViewSet):
    queryset = SubScan.objects.all().order_by('-start_scan_date')
    serializer_class = SubScanSerializer
    permission_classes = [HasPermission]
    permission_required = PERM_INITATE_SCANS_SUBSCANS

    def get_queryset(self):
        project_slug = self.request.query_params.get('project')
        if project_slug:
            return self.queryset.filter(scan_history__domain__project__slug=project_slug)
        return self.queryset

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'status': False, 'message': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        SubScan.objects.filter(id__in=ids).delete()
        return Response({'status': True, 'message': f'Successfully deleted {len(ids)} subscans'})

    @action(detail=False, methods=['post'])
    def bulk_stop(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'status': False, 'message': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        subscans = SubScan.objects.filter(id__in=ids)
        for subscan in subscans:
            for task_id in subscan.celery_ids:
                app.control.revoke(task_id, terminate=True, signal='SIGKILL')
            subscan.status = ABORTED_TASK
            subscan.stop_scan_date = timezone.now()
            subscan.save()
        return Response({'status': True, 'message': f'Stopped {len(ids)} subscans'})
