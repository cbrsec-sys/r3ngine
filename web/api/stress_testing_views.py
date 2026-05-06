from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from startScan.models import ScanHistory
from reNgine.graph_utils import Neo4jManager
from rest_framework.permissions import IsAuthenticated


class StressTestingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            scan = ScanHistory.objects.get(id=id)
        except ScanHistory.DoesNotExist:
            return Response(
                {"error": "Scan not found"}, status=status.HTTP_404_NOT_FOUND
            )

        neo4j = Neo4jManager()
        data = neo4j.get_stress_telemetry(id)
        neo4j.close()

        return Response({"status": True, "results": data}, status=status.HTTP_200_OK)
