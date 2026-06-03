from django.conf import settings as _settings
from dashboard.models import UserPreferences


class ContentSecurityPolicyMiddleware:
	"""Sets a Content-Security-Policy header on every response."""

	_CSP = (
		"default-src 'self'; "
		"script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
		"style-src 'self' 'unsafe-inline'; "
		"img-src 'self' data: blob:; "
		"font-src 'self' data:; "
		"connect-src 'self' ws: wss:; "
		"frame-ancestors 'none';"
	)

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		response = self.get_response(request)
		if 'Content-Security-Policy' not in response:
			response['Content-Security-Policy'] = self._CSP
		return response

class UserPreferencesMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		# print(f"DEBUG: Request {request.method} {request.path}", flush=True)
		if request.user.is_authenticated:
			from django.utils.functional import SimpleLazyObject
			request.user_preferences = SimpleLazyObject(lambda: UserPreferences.objects.get_or_create(user=request.user)[0])
		return self.get_response(request)


import os
from django.conf import settings

class SystemVersionMiddleware:
    """
    Middleware to inject the X-System-Version header into all HTTP responses.
    The version is read once on initialization from the web/.version file.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.system_version = "Unknown"
        
        # Read the version from web/.version file
        version_file_path = os.path.join(settings.BASE_DIR, '.version')
        if os.path.exists(version_file_path):
            try:
                with open(version_file_path, 'r') as f:
                    self.system_version = f.read().strip()
            except Exception:
                pass

    def __call__(self, request):
        response = self.get_response(request)
        response['X-System-Version'] = self.system_version
        
        # Also expose the header to the frontend via CORS if needed
        # (Useful if the frontend is making cross-origin requests)
        expose_headers = response.get('Access-Control-Expose-Headers', '')
        if 'X-System-Version' not in expose_headers:
            if expose_headers:
                response['Access-Control-Expose-Headers'] = f"{expose_headers}, X-System-Version"
            else:
                response['Access-Control-Expose-Headers'] = "X-System-Version"
                
        return response
