#!/usr/bin/env python3
"""
clear_failed_plugins.py
------------------------
Utility script to clean up orphaned or failed plugin directories from the backend
filesystem (plugins_data/ and media/plugins/).

Orphaned plugins are directories present on disk but not registered in the database,
usually caused by installation failures before the database transaction committed.

Usage (inside the web container):
    python3 scripts/clear_failed_plugins.py [--dry-run]
"""

import os
import sys
import shutil
import argparse
import logging

# ── Bootstrap Django ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')

import django
django.setup()
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help='Preview folders to delete without making changes')
    args = parser.parse_args()

    from django.conf import settings
    from plugins.models import Plugin

    # 1. Fetch all registered slugs from database
    try:
        registered_slugs = set(Plugin.objects.values_list('slug', flat=True))
        logger.info(f"Registered plugins in database: {list(registered_slugs)}")
    except Exception as e:
        logger.error(f"Failed to query Plugin database table: {e}")
        logger.warning("Proceeding in safe-mode (will not delete folders if DB check failed entirely).")
        sys.exit(1)

    # 2. Check plugins_data/
    plugins_data_dir = os.path.join(settings.BASE_DIR, 'plugins_data')
    orphaned_folders = []

    if os.path.exists(plugins_data_dir):
        for item in os.listdir(plugins_data_dir):
            # Skip non-slug metadata and folders
            if item in ['backups', '__init__.py'] or item.startswith('.'):
                continue
            item_path = os.path.join(plugins_data_dir, item)
            if os.path.isdir(item_path):
                if item not in registered_slugs:
                    orphaned_folders.append(('fs', item, item_path))

    # 3. Check media/plugins/
    media_plugins_dir = os.path.join(settings.MEDIA_ROOT, 'plugins')
    if os.path.exists(media_plugins_dir):
        for item in os.listdir(media_plugins_dir):
            if item.startswith('.'):
                continue
            item_path = os.path.join(media_plugins_dir, item)
            if os.path.isdir(item_path):
                if item not in registered_slugs:
                    orphaned_folders.append(('media', item, item_path))

    # 4. Perform Cleanup
    if not orphaned_folders:
        logger.info("No orphaned or failed plugin files detected. System is clean.")
        sys.exit(0)

    logger.info(f"Found {len(orphaned_folders)} orphaned directory/directories.")
    
    for category, slug, path in orphaned_folders:
        status = "[DRY-RUN]" if args.dry_run else "[DELETING]"
        logger.info(f"{status} Removing {category} directory for failed/unregistered plugin '{slug}': {path}")
        
        if not args.dry_run:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                    logger.info(f"  ✓ Successfully removed: {path}")
                elif os.path.exists(path):
                    os.remove(path)
                    logger.info(f"  ✓ Successfully removed file: {path}")
            except Exception as e:
                logger.error(f"  ✗ Failed to delete {path}: {e}")

    if args.dry_run:
        logger.info("Dry-run complete. Re-run without --dry-run to apply cleanup.")


if __name__ == '__main__':
    main()
