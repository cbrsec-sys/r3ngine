"""
APME API Views

Exposes attack paths stored in ImpactAssessment to the frontend.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class AttackPathsAPIView(APIView):
    """
    GET /api/apme/paths/?scan_id=<id>

    Returns top attack paths computed by the APME for a given scan.
    Paths are ordered by score descending (highest risk first).
    Each step is tagged as 'validated' or 'inferred'.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from startScan.models import ImpactAssessment
        scan_id = request.query_params.get('scan_id')
        project_slug = request.query_params.get('project')

        if not scan_id and not project_slug:
            return Response(
                {'error': 'scan_id or project query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        assessments = ImpactAssessment.objects.all()

        if scan_id:
            try:
                scan_id = int(scan_id)
                assessments = assessments.filter(scan_history_id=scan_id)
            except (ValueError, TypeError):
                return Response({'error': 'scan_id must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        if project_slug:
            assessments = assessments.filter(scan_history__domain__project__slug=project_slug)

        # Fetch ImpactAssessments that have APME path data
        assessments = (
            assessments
            .exclude(potential_attack_chain__isnull=True)
            .exclude(potential_attack_chain={})
            .order_by('-remediation_priority', '-scan_history__start_scan_date')
        )

        paths = []
        for a in assessments:
            chain = a.potential_attack_chain or {}
            if not chain.get('apme_path_id'):
                continue

            paths.append({
                'path_id': chain.get('apme_path_id'),
                'risk': chain.get('risk', 'unknown'),
                'score': chain.get('score', 0.0),
                'step_count': len(chain.get('steps', [])),
                'steps': chain.get('steps', []),
                'potential_impact': a.potential_impact,
                'remediation_priority': a.remediation_priority,
                'vulnerability_id': a.vulnerability_id,
            })

        return Response({
            'total_paths': len(paths),
            'paths': paths,
        }, status=status.HTTP_200_OK)


class TriggerLLMAPMEAPIView(APIView):
    """
    POST /api/apme/trigger/
    Body: { "scan_id": <id> }

    Triggers an on-demand LLM-assisted attack path modeling task.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        scan_id = request.data.get('scan_id')
        if not scan_id:
            return Response(
                {'error': 'scan_id is required in request body'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from startScan.models import ScanHistory
            scan = ScanHistory.objects.get(id=scan_id)
        except ScanHistory.DoesNotExist:
            return Response({'error': 'Scan not found'}, status=status.HTTP_404_NOT_FOUND)

        # Trigger Celery Task
        from apme.apme_tasks import run_llm_apme
        task = run_llm_apme.delay(scan_id)

        return Response({
            'status': 'triggered',
            'task_id': task.id,
            'message': 'AI Attack Path Modeling task has been initiated.'
        }, status=status.HTTP_202_ACCEPTED)
