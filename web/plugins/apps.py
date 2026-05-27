import threading
from django.apps import AppConfig


class PluginsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins'

    def ready(self):
        import plugins.signals
        from .tasks import verify_all_plugin_tools
        try:
            threading.Thread(target=verify_all_plugin_tools, daemon=True).start()
        except Exception:
            pass
