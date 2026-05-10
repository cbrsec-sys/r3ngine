import redis
import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from startScan.models import ScanHistory

logger = logging.getLogger(__name__)

try:
    redis_client = redis.StrictRedis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0
    )
except:
    redis_client = None

class StressTestControlAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, scan_id):
        """Start or Stop a stress test."""
        action = request.data.get('action')
        
        if action == 'stop':
            if redis_client:
                redis_client.set(f"kill_switch_{scan_id}", "1", ex=3600)
                return Response({"status": "stopping"}, status=status.HTTP_200_OK)
            return Response({"error": "Redis not available"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        elif action == 'start':
            # In a real scenario, this would trigger the celery task
            # For the dashboard, we might want to re-run with new params
            config = request.data.get('config', {})
            scan = ScanHistory.objects.filter(id=scan_id).first()
            if not scan:
                return Response({"error": "Scan not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Clear kill switch if it was set
            if redis_client:
                redis_client.delete(f"kill_switch_{scan_id}")
            
            # Trigger task
            from reNgine.stress_testing_tasks import run_stress_testing
            run_stress_testing.delay(scan.id, scan.domain.name, {"stress_test": config})
            return Response({"status": "started"}, status=status.HTTP_200_OK)
        
        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

class StressTestStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, scan_id):
        """Get the current status of the stress test (e.g., if kill switch is active)."""
        is_killed = False
        if redis_client:
            is_killed = redis_client.get(f"kill_switch_{scan_id}") == b"1"
        
        return Response({
            "scan_id": scan_id,
            "kill_switch_active": is_killed,
        })
