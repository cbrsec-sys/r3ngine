import os

import django
from celery import Celery
from celery.signals import setup_logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')

# Celery app
app = Celery('reNgine')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Only initialize Django and autodiscover tasks if we're running a Celery/Beat process
# This prevents circular imports when manage.py or gunicorn imports reNgine.settings
import sys
from django.apps import apps
if any(x in sys.argv[0] for x in ['celery', 'beat']):
    if not apps.ready and not apps.loading:
        django.setup()
    app.autodiscover_tasks()


@setup_logging.connect()
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    dictConfig(app.conf['LOGGING'])


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # This can also be used for startup tasks
    pass


@app.on_after_configure.connect
def setup_startup_tasks(sender, **kwargs):
    pass


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


@app.on_after_finalize.connect
def setup_startup_sync(sender, **kwargs):
    """
    Trigger essential sync tasks on startup. 
    Uses Redis locks to ensure each task only runs once across all workers/processes.
    """
    try:
        import redis
        from django.conf import settings
        import logging
        
        startup_logger = logging.getLogger("reNgine.startup")
        
        # Connect to Redis
        r = redis.from_url(settings.CELERY_BROKER_URL)
        
        # 1. Graph Synchronization
        graph_lock_key = "rengine:startup_graph_sync_lock"
        if r.set(graph_lock_key, "locked", nx=True, ex=3600):
            startup_logger.info(">>> [STARTUP] Triggering global graph synchronization...")
            from reNgine.tasks import sync_all_scans_to_graph
            sync_all_scans_to_graph.delay()
        else:
            startup_logger.debug(">>> [STARTUP] Graph sync already triggered or lock active.")

        # 2. CISA KEV Catalog Synchronization
        kev_lock_key = "rengine:startup_kev_sync_lock"
        if r.set(kev_lock_key, "locked", nx=True, ex=3600):
            startup_logger.info(">>> [STARTUP] Triggering CISA KEV catalog synchronization...")
            from reNgine.tasks import sync_cisa_kev_catalog
            sync_cisa_kev_catalog.delay()
        else:
            startup_logger.debug(">>> [STARTUP] CISA KEV sync already triggered or lock active.")

        # 3. Semgrep Rule Synchronization
        semgrep_lock_key = "rengine:startup_semgrep_sync_lock"
        if r.set(semgrep_lock_key, "locked", nx=True, ex=3600):
            startup_logger.info(">>> [STARTUP] Triggering Semgrep rule synchronization...")
            from reNgine.tasks import sync_semgrep_rules
            sync_semgrep_rules.delay()
        else:
            startup_logger.debug(">>> [STARTUP] Semgrep rule sync already triggered or lock active.")
            
    except Exception as e:
        # Avoid crashing startup if Redis or task dispatch fails
        import logging
        logging.error(f"Failed to trigger startup tasks: {e}")
