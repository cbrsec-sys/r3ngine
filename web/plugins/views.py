from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Plugin
from .serializers import PluginSerializer
from .utils import AtomicInstaller, PluginManager, MarketplaceManager
import os

class PluginViewSet(viewsets.ModelViewSet):
    queryset = Plugin.objects.all()
    serializer_class = PluginSerializer
    lookup_field = 'slug'
    pagination_class = None
    
    @action(detail=False, methods=['post'], url_path='upload')
    def upload_plugin(self, request):
        if 'file' not in request.FILES:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
            
        zip_file = request.FILES['file']
        # Save temp zip
        temp_zip_path = os.path.join(PluginManager.BASE_PLUGINS_DIR, 'upload_' + zip_file.name)
        PluginManager.ensure_dirs()
        
        with open(temp_zip_path, 'wb+') as destination:
            for chunk in zip_file.chunks():
                destination.write(chunk)
                
        try:
            plugin = AtomicInstaller.install(temp_zip_path)
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
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
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
