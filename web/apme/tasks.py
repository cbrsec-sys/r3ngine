"""
APME Celery Tasks Entrypoint.

This module acts as the entrypoint for Celery's autodiscover_tasks mechanism.
It imports and exposes the on-demand LLM-assisted attack path modeling tasks.
"""

from apme.apme_tasks import run_llm_apme

# Expose tasks for Celery's autodiscovery
__all__ = ['run_llm_apme']
