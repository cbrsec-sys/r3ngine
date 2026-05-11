from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from startScan.models import ScanHistory, EngineType, Domain
from .serializers import ScanHistorySerializer
import logging

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
        from startScan.views import stop_scan as legacy_stop_scan
        # We can reuse the logic but call it via a clean API
        # Or better, implement it here to avoid dependency on legacy views if possible
        # But legacy stop_scan handles a lot of celery revocation
        # I'll implement a clean version here
        scan = self.get_object()
        try:
            from reNgine.celery import app
            from startScan.models import ScanActivity, ABORTED_TASK, RUNNING_TASK
            from startScan.views import create_scan_activity
            from django.utils import timezone

            for task_id in scan.celery_ids:
                app.control.revoke(task_id, terminate=True, signal='SIGKILL')
            
            scan.scan_status = ABORTED_TASK
            scan.save()

            tasks = ScanActivity.objects.filter(scan_of=scan, status=RUNNING_TASK)
            for task in tasks:
                app.control.revoke(task.celery_id, terminate=True, signal='SIGKILL')
                task.status = ABORTED_TASK
                task.time = timezone.now()
                task.save()
            
            create_scan_activity(scan.id, "Scan aborted via Tactical API", ABORTED_TASK)
            return Response({'status': True, 'message': 'Scan successfully stopped'})
        except Exception as e:
            logger.error(f"Error stopping scan {pk}: {str(e)}")
            return Response({'status': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def delete_scan(self, request, pk=None):
        scan = self.get_object()
        try:
            import os
            import shutil
            if scan.results_dir and os.path.exists(scan.results_dir):
                shutil.rmtree(scan.results_dir)
            scan.delete()
            return Response({'status': True, 'message': 'Scan history deleted'})
        except Exception as e:
            logger.error(f"Error deleting scan {pk}: {str(e)}")
            return Response({'status': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def bulk_stop(self, request):
        ids = request.data.get('ids', [])
        scans = ScanHistory.objects.filter(id__in=ids)
        for scan in scans:
            # Reusing the stop logic
            try:
                from reNgine.celery import app
                from startScan.models import ScanActivity, ABORTED_TASK, RUNNING_TASK
                from startScan.views import create_scan_activity
                from django.utils import timezone
                for task_id in scan.celery_ids:
                    app.control.revoke(task_id, terminate=True, signal='SIGKILL')
                scan.scan_status = ABORTED_TASK
                scan.save()
                tasks = ScanActivity.objects.filter(scan_of=scan, status=RUNNING_TASK)
                for task in tasks:
                    app.control.revoke(task.celery_id, terminate=True, signal='SIGKILL')
                    task.status = ABORTED_TASK
                    task.time = timezone.now()
                    task.save()
                create_scan_activity(scan.id, "Scan aborted via Bulk Action", ABORTED_TASK)
            except:
                pass
        return Response({'status': True, 'message': f'{len(scans)} scans stopped'})

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        scans = ScanHistory.objects.filter(id__in=ids)
        import os
        import shutil
        count = 0
        for scan in scans:
            if scan.results_dir and os.path.exists(scan.results_dir):
                try:
                    shutil.rmtree(scan.results_dir)
                except:
                    pass
            scan.delete()
            count += 1
        return Response({'status': True, 'message': f'{count} scans deleted'})
