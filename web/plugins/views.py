from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.http import FileResponse, Http404
from django.views import View
from django.core.cache import cache
from .models import Plugin
from .serializers import PluginSerializer
from .utils import AtomicInstaller, PluginManager, MarketplaceManager
import os
import mimetypes
import threading
import uuid

class PluginViewSet(viewsets.ModelViewSet):
    queryset = Plugin.objects.all()
    serializer_class = PluginSerializer
    lookup_field = 'slug'
    pagination_class = None

    def get_permissions(self):
        # Read-only actions (list, retrieve, registry, install-status) require only authentication.
        # All mutating or privileged actions require admin/staff.
        read_only_actions = {'list', 'retrieve', 'registry', 'install_status'}
        if self.action in read_only_actions:
            return [IsAuthenticated()]
        return [IsAdminUser()]
    
    @action(detail=False, methods=['post'], url_path='upload')
    def upload_plugin(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        zip_file = request.FILES['file']
        PluginManager.ensure_dirs()
        temp_zip_path = os.path.join(PluginManager.BASE_PLUGINS_DIR, f'upload_{uuid.uuid4().hex[:8]}_{zip_file.name}')

        with open(temp_zip_path, 'wb+') as destination:
            for chunk in zip_file.chunks():
                destination.write(chunk)

        install_id = uuid.uuid4().hex[:12]
        cache.set(f'plugin:install:{install_id}', {
            'steps': [{'key': 'upload', 'label': 'Saving plugin archive', 'status': 'completed', 'message': ''}],
            'status': 'running',
            'plugin_name': None,
        }, timeout=300)

        def _run_install(path, iid):
            import django.db
            django.db.close_old_connections()
            try:
                AtomicInstaller.install(path, install_id=iid)
            except Exception:
                pass  # AtomicInstaller already writes 'failed' state to cache
            finally:
                if os.path.exists(path):
                    os.remove(path)
                django.db.close_old_connections()

        threading.Thread(target=_run_install, args=(temp_zip_path, install_id), daemon=True).start()

        return Response({'install_id': install_id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='install-status')
    def install_status(self, request):
        install_id = request.GET.get('id', '')
        if not install_id:
            return Response({'error': 'id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        data = cache.get(f'plugin:install:{install_id}')
        if data is None:
            return Response({'error': 'install session not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(data)

    def perform_update(self, serializer):
        instance = serializer.save()
        from django.core.cache import cache
        cache.set(f"plugin_{instance.slug}_needs_restart", True, timeout=None)

    @action(detail=False, methods=['post'], url_path='restart-orchestrator')
    def restart_orchestrator(self, request):
        import redis
        from django.conf import settings
        try:
            rdb = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
            rdb.publish('orchestrator_control', 'restart')
            return Response({'success': True, 'message': 'Restart command sent to orchestrator.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='registry')
    def registry(self, request):
        """Returns the UI component registry for the frontend."""
        active_plugins = Plugin.objects.filter(is_enabled=True)
        registry_data = []
        for plugin in active_plugins:
            # Check for UI components in manifest
            ui_config = plugin.manifest.get('ui', {})
            if ui_config:
                registry_data.append({
                    'slug': plugin.slug,
                    'name': plugin.name,
                    'components': ui_config # Should contain list of {name, file, type}
                })
        return Response(registry_data)

    @action(detail=False, methods=['get'], url_path='marketplace')
    def marketplace(self, request):
        """Returns available plugins from the marketplace."""
        force_refresh = request.query_params.get('refresh', 'false').lower() == 'true'
        plugins = MarketplaceManager.get_available_plugins(force_refresh=force_refresh)
        return Response(plugins)

    @action(detail=False, methods=['post'], url_path='marketplace/install')
    def marketplace_install(self, request):
        """Installs a plugin from the marketplace."""
        slug = request.data.get('slug')
        if not slug:
            return Response({'error': 'No slug provided'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # 1. Download
            temp_zip_path = MarketplaceManager.download_plugin(slug)
            
            # 2. Install
            plugin = AtomicInstaller.install(temp_zip_path)
            
            # 3. Cleanup
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
                
            return Response({
                'success': True,
                'plugin': {
                    'name': plugin.name,
                    'slug': plugin.slug,
                    'version': plugin.version
                }
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='marketplace/refresh')
    def marketplace_refresh(self, request):
        """Force refreshes the marketplace cache."""
        plugins = MarketplaceManager.get_available_plugins(force_refresh=True)
        return Response(plugins)


class PluginUIView(View):
    """Serves built plugin UI assets from plugins_data/{slug}/ui/dist/."""

    def get(self, request, slug, path):
        ui_dir = os.path.join(PluginManager.BASE_PLUGINS_DIR, slug, 'ui')
        file_path = os.path.normpath(os.path.join(ui_dir, path))

        # Guard against path traversal
        if not file_path.startswith(os.path.abspath(ui_dir)):
            raise Http404

        if not os.path.isfile(file_path):
            raise Http404

        content_type, _ = mimetypes.guess_type(file_path)
        return FileResponse(open(file_path, 'rb'), content_type=content_type or 'application/octet-stream')
