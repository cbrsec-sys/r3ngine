import os
import io
import json
import zipfile
from django.http import FileResponse
from django.core.serializers import serialize, deserialize
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from reNgine.definitions import PERM_MODIFY_SYSTEM_CONFIGURATIONS
from api.permissions import HasPermission  # Assuming this exists based on api/views.py

from dashboard.models import (
    OpenAiAPIKey, OllamaSettings, NetlasAPIKey, ChaosAPIKey, HackerOneAPIKey,
    ShodanAPIKey, CensysAPIKey, LLMConfig, SpiderfootAPIKey, LeakLookupAPIKey,
    AcunetixAPIKey, LinkedInCredentials, HunterIOAPIKey, WpScanAPIKey
)

from scanEngine.models import (
    EngineType, Wordlist, Configuration, InterestingLookupModel,
    Notification, Proxy, OpSec, Hackerone, VulnerabilityReportSetting,
    InstalledExternalTool
)

DASHBOARD_MODELS = [
    OpenAiAPIKey, OllamaSettings, NetlasAPIKey, ChaosAPIKey, HackerOneAPIKey,
    ShodanAPIKey, CensysAPIKey, LLMConfig, SpiderfootAPIKey, LeakLookupAPIKey,
    AcunetixAPIKey, LinkedInCredentials, HunterIOAPIKey, WpScanAPIKey
]

SCANENGINE_MODELS = [
    EngineType, Wordlist, Configuration, InterestingLookupModel,
    Notification, Proxy, OpSec, Hackerone, VulnerabilityReportSetting,
    InstalledExternalTool
]

class ExportConfig(APIView):
    permission_classes = [IsAuthenticated, HasPermission]
    permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS

    def get(self, request):
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Export Dashboard Models
            dashboard_data = {}
            for model in DASHBOARD_MODELS:
                model_name = model.__name__
                dashboard_data[model_name] = json.loads(serialize('json', model.objects.all()))
            
            zip_file.writestr('dashboard_models.json', json.dumps(dashboard_data, indent=4))

            # 2. Export ScanEngine Models
            scanengine_data = {}
            for model in SCANENGINE_MODELS:
                model_name = model.__name__
                scanengine_data[model_name] = json.loads(serialize('json', model.objects.all()))
            
            zip_file.writestr('scanengine_models.json', json.dumps(scanengine_data, indent=4))

            # 3. Export Wordlists from Filesystem
            wordlist_dir = '/usr/src/wordlist/'
            if os.path.exists(wordlist_dir):
                for filename in os.listdir(wordlist_dir):
                    if filename.endswith('.txt'):
                        file_path = os.path.join(wordlist_dir, filename)
                        with open(file_path, 'rb') as f:
                            zip_file.writestr(f'wordlists/{filename}', f.read())

        zip_buffer.seek(0)
        
        response = FileResponse(zip_buffer, as_attachment=True, filename='r3ngine_config_backup.zip')
        return response


class ImportConfig(APIView):
    permission_classes = [IsAuthenticated, HasPermission]
    permission_required = PERM_MODIFY_SYSTEM_CONFIGURATIONS

    def post(self, request):
        upload_file = request.FILES.get('file')
        overwrite_existing = request.data.get('overwrite_existing', 'false').lower() == 'true'

        if not upload_file:
            return Response({'status': False, 'message': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with zipfile.ZipFile(upload_file, 'r') as zip_file:
                # 1. Restore Dashboard Models
                if 'dashboard_models.json' in zip_file.namelist():
                    dashboard_data = json.loads(zip_file.read('dashboard_models.json'))
                    self.restore_models(dashboard_data, overwrite_existing)

                # 2. Restore ScanEngine Models
                if 'scanengine_models.json' in zip_file.namelist():
                    scanengine_data = json.loads(zip_file.read('scanengine_models.json'))
                    self.restore_models(scanengine_data, overwrite_existing)

                # 3. Restore Wordlists to Filesystem
                wordlist_dir = '/usr/src/wordlist/'
                if not os.path.exists(wordlist_dir):
                    os.makedirs(wordlist_dir)

                for file_info in zip_file.infolist():
                    if file_info.filename.startswith('wordlists/') and file_info.filename.endswith('.txt'):
                        filename = os.path.basename(file_info.filename)
                        if filename:
                            file_path = os.path.join(wordlist_dir, filename)
                            # Only overwrite wordlists if overwrite_existing is true, or if file doesn't exist
                            if overwrite_existing or not os.path.exists(file_path):
                                with open(file_path, 'wb') as f:
                                    f.write(zip_file.read(file_info.filename))

            return Response({'status': True, 'message': 'Configuration imported successfully.'})
        except zipfile.BadZipFile:
            return Response({'status': False, 'message': 'Invalid zip file.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def restore_models(self, data, overwrite_existing):
        for model_name, objects_data in data.items():
            for obj_data in objects_data:
                try:
                    # obj_data is a serialized dict representation
                    # To allow deserializing into potentially different pk, we might need to handle it carefully.
                    # Usually `deserialize` handles JSON string from `serialize` directly.
                    # Since we loaded it into python dict, we need to convert to json string for `deserialize`
                    json_str = json.dumps([obj_data])
                    for deserialized_obj in deserialize('json', json_str):
                        model_class = type(deserialized_obj.object)
                        # To support overwrite, we check if an object with the same PK exists, or handle uniquely.
                        # For singletons like Proxy, OpSec, we usually only have one row (pk=1)
                        if overwrite_existing:
                            deserialized_obj.save()
                        else:
                            # If it doesn't exist, create it.
                            # For some models, checking PK is enough.
                            if not model_class.objects.filter(pk=deserialized_obj.object.pk).exists():
                                deserialized_obj.save()
                except Exception as e:
                    # Log exception and continue
                    print(f"Error restoring {model_name}: {e}")
