from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from scanEngine.models import EngineType, Configuration
from api.serializers import EngineTypeSerializer, ConfigurationSerializer
from reNgine.definitions import DEFAULT_EXCLUDED_PATHS

class ScanConfigurationAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        engines = EngineType.objects.all()
        configurations = Configuration.objects.all()
        
        engine_serializer = EngineTypeSerializer(engines, many=True)
        config_serializer = ConfigurationSerializer(configurations, many=True)
        
        return Response({
            "engines": engine_serializer.data,
            "configurations": config_serializer.data,
            "default_excluded_paths": DEFAULT_EXCLUDED_PATHS,
            "scan_types": [
                {"id": 1, "name": "Full Scan"},
                {"id": 2, "name": "Subdomain Discovery"},
                {"id": 3, "name": "Vulnerability Scan"}
            ]
        })
