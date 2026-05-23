import os
from django.core.asgi import get_asgi_application
from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from reNgine.consumers import StressTelemetryConsumer, ScanLogConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django_asgi_app = get_asgi_application()

websocket_urlpatterns = [
    re_path(r'ws/stress/(?P<scan_id>\d+)/$', StressTelemetryConsumer.as_asgi()),
    re_path(r'ws/logs/(?P<scan_id>\d+)/$', ScanLogConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
