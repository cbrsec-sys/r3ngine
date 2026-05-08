import os
import mimetypes
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.conf import settings

from reNgine.utilities import is_safe_path

logger = logging.getLogger(__name__)

@login_required
def serve_protected_media(request, path):
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    if not is_safe_path(settings.MEDIA_ROOT, file_path):
        logger.error(f"is_safe_path failed for {file_path} with base {settings.MEDIA_ROOT}")
        raise Http404("File not found")
        
    if os.path.isdir(file_path):
        logger.error(f"Path is a directory, not a file: {file_path}")
        raise Http404("File not found")
        
    if os.path.exists(file_path):
        content_type, _ = mimetypes.guess_type(file_path)
        response = HttpResponse()
        # response['Content-Disposition'] = f'attachment; filename={os.path.basename(file_path)}'
        response['Content-Type'] = content_type
        response['X-Accel-Redirect'] = f'/protected_media/{path}'
        return response
    else:
        logger.error(f"File does not exist: {file_path}")
        raise Http404("File not found")

