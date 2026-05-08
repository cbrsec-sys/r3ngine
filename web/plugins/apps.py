from django.apps import AppConfig


class PluginsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins'

    def ready(self):
        import plugins.signals
        # Trigger background verification of all plugin tools on startup
        from .tasks import verify_all_plugin_tools
        try:
            verify_all_plugin_tools.delay()
        except Exception:
            # Celery might not be ready yet in some management commands
            pass
