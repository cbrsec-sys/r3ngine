from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from startScan.models import ScanHistory, EngineType, Domain
from .serializers import ScanHistorySerializer
import logging
import os
import shutil

logger = logging.getLogger(__name__)

class ScanHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = ScanHistorySerializer

    def get_queryset(self):
        queryset = ScanHistory.objects.all().order_by('-id')
        project = self.request.query_params.get('project')
        target_id = self.request.query_params.get('target_id')
        if project:
            queryset = queryset.filter(domain__project__slug=project)
        if target_id:
            queryset = queryset.filter(domain__id=target_id)
        return queryset

    @action(detail=True, methods=['post'])
    def stop_scan(self, request, pk=None):
        from reNgine.utils.scan_cancellation import abort_scan_history
        scan = self.get_object()
        try:
            result = abort_scan_history(scan, aborted_by=request.user)
            if result.get('status'):
                return Response({'status': True, 'message': 'Scan successfully stopped'})
            return Response({'status': False, 'message': result.get('message', 'Unknown error')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Error stopping scan {pk}: {str(e)}")
            return Response({'status': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def delete_scan(self, request, pk=None):
        scan = self.get_object()
        try:
            if scan.results_dir and os.path.exists(scan.results_dir):
                shutil.rmtree(scan.results_dir)
            scan.delete()
            return Response({'status': True, 'message': 'Scan history deleted'})
        except Exception as e:
            logger.error(f"Error deleting scan {pk}: {str(e)}")
            return Response({'status': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def bulk_stop(self, request):
        from reNgine.utils.scan_cancellation import abort_scan_history
        ids = request.data.get('ids', [])
        scans = ScanHistory.objects.filter(id__in=ids)
        for scan in scans:
            try:
                abort_scan_history(scan, aborted_by=request.user)
            except Exception:
                pass
        return Response({'status': True, 'message': f'{scans.count()} scans stopped'})

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        scans = ScanHistory.objects.filter(id__in=ids)
        count = scans.count()
        for scan in scans:
            if scan.results_dir and os.path.exists(scan.results_dir):
                try:
                    shutil.rmtree(scan.results_dir)
                except Exception:
                    pass
            scan.delete()
        return Response({'status': True, 'message': f'{count} scans deleted'})
