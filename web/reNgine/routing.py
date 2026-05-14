from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from reNgine.consumers import StressTelemetryConsumer, ScanLogConsumer

websocket_urlpatterns = [
    re_path(r'ws/stress/(?P<scan_id>\d+)/$', StressTelemetryConsumer.as_asgi()),
    re_path(r'ws/logs/(?P<scan_id>\d+)/$', ScanLogConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
