import os
import mimetypes
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, FileResponse
from django.conf import settings

from reNgine.utilities import is_safe_path

logger = logging.getLogger(__name__)

@login_required
def serve_protected_media(request, path):
    logger.info(f"serve_protected_media hit for path: {path}")
    logger.info(f"Headers: {request.headers}")
    # 1. Normalize path
    # If the path is already absolute, try to make it relative to MEDIA_ROOT
    if path.startswith(settings.MEDIA_ROOT):
        path = os.path.relpath(path, settings.MEDIA_ROOT)
    elif path.startswith('/usr/src/scan_results'):
        path = os.path.relpath(path, '/usr/src/scan_results')
    
    # Ensure path doesn't start with /
    path = path.lstrip('/')
    file_path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, path))
    
    # Security check
    if not is_safe_path(settings.MEDIA_ROOT, file_path):
        logger.error(f"is_safe_path failed for {file_path}")
        raise Http404("File not found")
        
    if os.path.exists(file_path):
        # Prevent serving directories
        if os.path.isdir(file_path):
            raise Http404("File not found")
            
        content_type, _ = mimetypes.guess_type(file_path)
        
        # We use FileResponse for universal compatibility (Dev + Prod).
        # This works correctly even when the app is accessed directly (bypassing Nginx)
        # or via the Vite dev-server proxy.
        return FileResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        logger.error(f"File not found: {file_path}")
        raise Http404("File not found")
