#!/usr/bin/env python3
"""
migrate_monitoring_to_temporal.py
----------------------------------
Standalone migration script for existing r3ngine installations.

Migrates domain monitoring schedules from django_celery_beat PeriodicTask
rows to native Temporal Schedules (Phase 4F of the Celery → Temporal migration).

Run this AFTER `python manage.py migrate` has applied all schema migrations.
Temporal must be running and reachable (default: temporal:7233).

Usage (inside the web container):
    python3 scripts/migrate_monitoring_to_temporal.py [--dry-run] [--domain-id ID]

Options:
    --dry-run       Preview which domains would be migrated, make no changes.
    --domain-id ID  Migrate only the domain with the given ID (retry a single domain).
    --reverse       Remove Temporal monitoring schedules and clear temporal_schedule FKs.
                    Does NOT restore monitor_periodic_task rows.

Exit codes:
    0   All domains migrated successfully (or nothing to migrate).
    1   One or more domains failed to migrate.
    2   Temporal server unreachable / environment error.
"""

import os
import sys
import argparse
import logging

# ── Bootstrap Django ──────────────────────────────────────────────────────────
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


def check_temporal_reachable() -> bool:
    """Return True if the Temporal server is reachable."""
    import asyncio
    from reNgine.temporal_client import TemporalClientProvider
    try:
        TemporalClientProvider.reset()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(TemporalClientProvider.get_client())
        loop.close()
        return True
    except Exception as e:
        logger.error(f"Cannot connect to Temporal: {e}")
        return False


def migrate_domain(domain, dry_run: bool) -> bool:
    """Migrate a single domain. Returns True on success."""
    from reNgine.temporal_schedule_utils import _upsert_monitoring_temporal_schedule

    status = "[DRY-RUN]" if dry_run else ""
    logger.info(f"{status} Migrating domain_id={domain.id} name={domain.name!r} "
                f"frequency={domain.monitor_frequency}")
    if dry_run:
        return True
    try:
        ts = _upsert_monitoring_temporal_schedule(domain)
        domain.temporal_schedule = ts
        domain.save(update_fields=['temporal_schedule'])
        logger.info(f"  ✓ schedule_id={ts.schedule_id}")
        return True
    except Exception as e:
        logger.error(f"  ✗ {e}")
        return False


def reverse_domain(domain, dry_run: bool) -> bool:
    """Remove Temporal monitoring schedule for a single domain."""
    from reNgine.temporal_schedule_utils import _delete_temporal_schedule_by_id

    if not domain.temporal_schedule:
        logger.info(f"  skip domain_id={domain.id} — no temporal_schedule set")
        return True

    status = "[DRY-RUN]" if dry_run else ""
    logger.info(f"{status} Reversing domain_id={domain.id} name={domain.name!r} "
                f"schedule_id={domain.temporal_schedule.schedule_id}")
    if dry_run:
        return True
    try:
        ts = domain.temporal_schedule
        _delete_temporal_schedule_by_id(ts.schedule_id)
        domain.temporal_schedule = None
        domain.save(update_fields=['temporal_schedule'])
        ts.delete()
        logger.info(f"  ✓ removed")
        return True
    except Exception as e:
        logger.error(f"  ✗ {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dry-run', action='store_true', help='Preview only — make no changes')
    parser.add_argument('--domain-id', type=int, metavar='ID', help='Migrate only this domain ID')
    parser.add_argument('--reverse', action='store_true', help='Remove Temporal monitoring schedules')
    args = parser.parse_args()

    from targetApp.models import Domain

    # ── Build candidate queryset ──────────────────────────────────────────────
    if args.reverse:
        qs = Domain.objects.filter(
            temporal_schedule__isnull=False,
            temporal_schedule__workflow_type='MonitoringWorkflow',
        )
    else:
        qs = Domain.objects.filter(
            is_monitored=True,
            temporal_schedule__isnull=True,
        )

    if args.domain_id:
        qs = qs.filter(id=args.domain_id)

    domains = list(qs.select_related('temporal_schedule'))
    total = len(domains)

    if total == 0:
        logger.info("Nothing to migrate — no eligible domains found.")
        sys.exit(0)

    action = "reverse" if args.reverse else "migrate"
    logger.info(f"{'[DRY-RUN] ' if args.dry_run else ''}Will {action} {total} domain(s).")

    # ── Check Temporal connectivity (skip for dry-run) ────────────────────────
    if not args.dry_run:
        logger.info("Checking Temporal server connectivity...")
        if not check_temporal_reachable():
            logger.error(
                "Temporal server unreachable. Ensure the temporal service is running "
                "and TEMPORAL_HOST is set correctly."
            )
            sys.exit(2)
        logger.info("Temporal server reachable — proceeding.")

    # ── Process each domain ───────────────────────────────────────────────────
    succeeded = 0
    failed = 0
    fn = reverse_domain if args.reverse else migrate_domain

    for domain in domains:
        ok = fn(domain, args.dry_run)
        if ok:
            succeeded += 1
        else:
            failed += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    if args.dry_run:
        logger.info(f"[DRY-RUN] Would {action} {total} domain(s). Re-run without --dry-run to apply.")
    else:
        logger.info(f"Done — succeeded={succeeded} failed={failed} total={total}")

    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
