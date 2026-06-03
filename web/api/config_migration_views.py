import os
import re
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
    AcunetixAPIKey, LinkedInCredentials, HunterIOAPIKey, WpScanAPIKey,
    SOCConfiguration
)

from scanEngine.models import (
    EngineType, Wordlist, Configuration, InterestingLookupModel,
    Notification, Proxy, OpSec, Hackerone, VulnerabilityReportSetting,
    InstalledExternalTool
)

DASHBOARD_MODELS = [
    OpenAiAPIKey, OllamaSettings, NetlasAPIKey, ChaosAPIKey, HackerOneAPIKey,
    ShodanAPIKey, CensysAPIKey, LLMConfig, SpiderfootAPIKey, LeakLookupAPIKey,
    AcunetixAPIKey, LinkedInCredentials, HunterIOAPIKey, WpScanAPIKey,
    SOCConfiguration
]

SCANENGINE_MODELS = [
    EngineType, Wordlist, Configuration, InterestingLookupModel,
    Notification, Proxy, OpSec, Hackerone, VulnerabilityReportSetting,
    InstalledExternalTool
]

SINGLETON_MODELS = (
    OpenAiAPIKey, OllamaSettings, NetlasAPIKey, ChaosAPIKey, HackerOneAPIKey,
    ShodanAPIKey, CensysAPIKey, LeakLookupAPIKey, AcunetixAPIKey,
    LinkedInCredentials, HunterIOAPIKey, WpScanAPIKey, SOCConfiguration,
    InterestingLookupModel, Notification, Proxy, OpSec, Hackerone,
    VulnerabilityReportSetting
)

# Only these model classes may be deserialized during config import
_ALLOWED_IMPORT_MODELS = frozenset(DASHBOARD_MODELS + SCANENGINE_MODELS)

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

            # 4. Export Spiderfoot and theHarvester Tool Configs
            harvester_config_path = '/usr/src/github/theHarvester/api-keys.yaml'
            if os.path.exists(harvester_config_path):
                with open(harvester_config_path, 'rb') as f:
                    zip_file.writestr('tool_configs/theharvester_api-keys.yaml', f.read())

            spiderfoot_config_path = '/usr/src/github/spiderfoot/spiderfoot.cfg'
            if os.path.exists(spiderfoot_config_path):
                with open(spiderfoot_config_path, 'rb') as f:
                    zip_file.writestr('tool_configs/spiderfoot.cfg', f.read())

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

                safe_wordlist_dir = os.path.realpath(wordlist_dir)
                for file_info in zip_file.infolist():
                    if file_info.filename.startswith('wordlists/') and file_info.filename.endswith('.txt'):
                        filename = os.path.basename(file_info.filename)
                        if not filename or not re.fullmatch(r'[a-zA-Z0-9_\-\.]+\.txt', filename):
                            continue
                        file_path = os.path.realpath(os.path.join(wordlist_dir, filename))
                        if not file_path.startswith(safe_wordlist_dir + os.sep):
                            continue
                        # Only overwrite wordlists if overwrite_existing is true, or if file doesn't exist
                        if overwrite_existing or not os.path.exists(file_path):
                            with open(file_path, 'wb') as f:
                                f.write(zip_file.read(file_info.filename))

                # 4. Restore Spiderfoot and theHarvester Tool Configs
                for file_info in zip_file.infolist():
                    if file_info.filename.startswith('tool_configs/'):
                        dest_path = None
                        if file_info.filename == 'tool_configs/theharvester_api-keys.yaml':
                            dest_path = '/usr/src/github/theHarvester/api-keys.yaml'
                        elif file_info.filename == 'tool_configs/spiderfoot.cfg':
                            dest_path = '/usr/src/github/spiderfoot/spiderfoot.cfg'
                        
                        if dest_path:
                            if overwrite_existing or not os.path.exists(dest_path):
                                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                with open(dest_path, 'wb') as f:
                                    f.write(zip_file.read(file_info.filename))

            return Response({'status': True, 'message': 'Configuration imported successfully.'})
        except zipfile.BadZipFile:
            return Response({'status': False, 'message': 'Invalid zip file.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'status': False, 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def restore_models(self, data, overwrite_existing):
        """Restore serialized models from a data dictionary.

        For models identified as singletons (e.g., settings, proxies, API keys),
        this function updates the existing first record in the database instead
        of creating duplicates, ensuring that the application continues to use
        the imported settings.

        Args:
            data (dict): Serialized objects grouped by model name.
            overwrite_existing (bool): True to overwrite existing records, False to skip.
        """
        for model_name, objects_data in data.items():
            for obj_data in objects_data:
                try:
                    # obj_data is a serialized dict representation
                    # Convert to json string for `deserialize`
                    json_str = json.dumps([obj_data])
                    for deserialized_obj in deserialize('json', json_str):
                        model_class = type(deserialized_obj.object)
                        if model_class not in _ALLOWED_IMPORT_MODELS:
                            print(f"Skipping disallowed model type during import: {model_class.__name__}")
                            continue
                        
                        if model_class in SINGLETON_MODELS:
                            existing_obj = model_class.objects.first()
                            if existing_obj:
                                if overwrite_existing:
                                    # Copy fields (except ID) to the existing first instance
                                    for field in model_class._meta.fields:
                                        if field.name != 'id':
                                            setattr(existing_obj, field.name, getattr(deserialized_obj.object, field.name))
                                    existing_obj.save()
                            else:
                                deserialized_obj.save()
                        else:
                            if overwrite_existing:
                                deserialized_obj.save()
                            else:
                                # Only save if an object with this primary key does not exist
                                if not model_class.objects.filter(pk=deserialized_obj.object.pk).exists():
                                    deserialized_obj.save()
                except Exception as e:
                    # Log exception and continue
                    print(f"Error restoring {model_name}: {e}")
