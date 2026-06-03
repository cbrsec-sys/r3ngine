"""
Django management command for the Temporal Python Orchestrator Worker.

This command starts the Python-side Temporal worker which:
  - Hosts the MasterScanWorkflow and NucleiPlannerWorkflow workflow definitions.
  - Registers all Python-based activities (Django DB reads/writes, Neo4j sync).
  - Listens on the 'python-orchestrator-queue' task queue.

The worker runs with UnsandboxedWorkflowRunner to allow transitive Django and
Celery imports that use custom threading.local proxied objects, which would
otherwise trigger sandbox validation failures.

Usage (inside the container):
    python manage.py run_temporal_orchestrator
"""

import asyncio
import datetime
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import connections
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleState,
)
from temporalio.worker import Worker, UnsandboxedWorkflowRunner

logger = logging.getLogger(__name__)


class DjangoAwareThreadPoolExecutor(ThreadPoolExecutor):
    """Thread pool executor that manages Django DB connections per activity thread."""

    def submit(self, fn, *args, **kwargs):
        def wrapped_fn():
            from django.db import close_old_connections
            close_old_connections()
            try:
                return fn(*args, **kwargs)
            finally:
                connections.close_all()
        return super().submit(wrapped_fn)

# Workflows
from reNgine.temporal_workflows import (
    MasterScanWorkflow,
    NucleiPlannerWorkflow,
    SubScanWorkflow,
    StressTestWorkflow,
    StartupSyncWorkflow,
    ScheduledScanWorkflow,
    MonitoringWorkflow,
    GoExecutorTaskWorkflow,
    ApmeTaskWorkflow,
    IdentityEnrichmentWorkflow,
    GeoLocalizeWorkflow,
    HackerOneImportWorkflow,
    HackerOneSyncBookmarkedWorkflow,
    ProxyFetchWorkflow,
)

# Activities (all Python-side activities are registered here)
from reNgine.temporal_activities import (
    run_generic_task_activity,
    finalize_subscan_activity,
    finalize_failed_scan_activity,
    # Step 0: Task initialization & Target Profiling
    initialize_scan_tasks_activity,
    load_checkpoint_activity,
    save_checkpoint_activity,
    target_profiling_activity,
    check_scan_queue_status_activity,
    get_enabled_plugins_for_tier_activity,

    # Tier 1: Discovery
    run_subdomain_discovery_activity,
    run_amass_intel_discovery_activity,
    run_firewall_vpn_scan_activity,
    run_dns_security_activity,
    parse_discovery_results_activity,
    seed_endpoints_for_crawl_activity,

    # TOR
    run_tor_new_circuit_activity,

    # Tier 2: Enumeration
    run_http_crawl_activity,
    parse_http_crawl_results_activity,
    run_port_scan_activity,
    run_screenshot_activity,
    run_fetch_url_activity,
    parse_enumeration_results_activity,

    # Tier 3/4: Fuzzing
    run_dir_file_fuzz_activity,
    parse_fuzz_results_activity,

    # Tier 5: Analysis
    run_web_api_discovery_activity,
    run_waf_detection_activity,
    run_secret_scanning_activity,
    parse_analysis_results_activity,

    # Tier 6: Assessment
    run_nuclei_activity,
    run_crlfuzz_activity,
    run_dalfox_activity,
    run_s3scanner_activity,
    run_acunetix_activity,
    run_cpanel_scan_activity,
    run_react2shell_activity,
    run_wpscan_activity,
    run_semgrep_activity,
    run_vigolium_scan_activity,
    run_vigolium_discovery_activity,
    run_vigolium_analysis_activity,
    mark_vulnerability_scan_complete_activity,
    run_waf_bypass_activity,
    run_brute_force_scan_activity,
    parse_assessment_results_activity,

    # Tier 7: Post-Processing & Intel
    correlate_vulnerabilities_activity,
    calculate_risk_scores_activity,
    generate_impact_assessment_activity,
    sync_graph_activity,
    send_scan_notification_activity,

    # Stress Testing
    init_stress_test_activity,
    run_stress_tool_activity,
    finalize_stress_test_activity,

    # Startup sync
    run_startup_sync_activity,

    # Scheduled scan setup
    setup_scheduled_scan_activity,
    run_monitoring_check_activity,
    run_llm_apme_activity,
    enrich_identities_activity,
    geo_localize_activity,
    import_hackerone_programs_activity,
    sync_bookmarked_programs_activity,
    fetch_proxies_activity,
)


_STARTUP_SYNC_TASKS = [
    "sync_all_scans_to_graph",
    "sync_cisa_kev_catalog",
    "sync_semgrep_rules",
    "recover_stuck_scans",
]


async def _register_startup_schedule(client: Client, task_name: str, today: str) -> None:
    """Create (or recreate) a one-shot Temporal Schedule for a startup sync task.

    The schedule is deleted first so each orchestrator restart gets a fresh one-shot
    trigger. The workflow ID embeds today's date so successful runs are not repeated
    within the same calendar day (workflow ID embeds today's date).
    """
    schedule_id = f"startup-sync-{task_name.replace('_', '-')}"
    workflow_id = f"{schedule_id}-{today}"

    # Remove stale schedule from the previous run (idempotent — ignore if absent)
    try:
        handle = client.get_schedule_handle(schedule_id)
        await handle.delete()
    except Exception:
        pass

    await client.create_schedule(
        schedule_id,
        Schedule(
            action=ScheduleActionStartWorkflow(
                StartupSyncWorkflow.run,
                args=[task_name],
                id=workflow_id,
                task_queue="python-orchestrator-queue",
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=datetime.timedelta(seconds=30))],
            ),
            policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
            state=ScheduleState(
                limited_actions=True,
                remaining_actions=1,
                note=f"One-shot startup sync: {task_name}",
            ),
        ),
    )
    logger.info(f"[Startup] Registered one-shot schedule '{schedule_id}' → workflow '{workflow_id}'")


class Command(BaseCommand):
    help = 'Runs the Python Temporal Orchestrator Worker on python-orchestrator-queue.'

    def handle(self, *args, **options):
        # Install plugin tools in THIS container before starting the worker.
        # Tools must be present in the orchestrator — not the web container — because
        # activities (swaks, smtp-user-enum, etc.) run here. This is the only place
        # tool installation should be triggered; AppConfig.ready() must not do it.
        try:
            from plugins.tasks import verify_all_plugin_tools
            import threading
            t = threading.Thread(target=verify_all_plugin_tools, daemon=True)
            t.start()
            t.join(timeout=120)  # wait up to 2 min for apt installs before starting worker
        except Exception as tool_err:
            logger.error(f"Plugin tool installation failed at startup: {tool_err}")

        # Clear needs_restart flags synchronously before entering the async event loop.
        try:
            from django.core.cache import cache
            from plugins.models import Plugin
            for plugin in Plugin.objects.all():
                cache.set(f"plugin_{plugin.slug}_needs_restart", False, timeout=None)
            self.stdout.write(self.style.SUCCESS("Cleared needs_restart flags for all plugins."))
        except Exception as cache_err:
            logger.error(f"Failed to clear needs_restart flags: {cache_err}")

        async def main():

            temporal_host = os.environ.get("TEMPORAL_HOST", "temporal:7233")
            namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")

            self.stdout.write(self.style.MIGRATE_LABEL(
                f"Connecting to Temporal Server at {temporal_host} (namespace: {namespace})..."
            ))

            # -------------------------------------------------------------------
            # Connect with exponential-style retry backoff
            # -------------------------------------------------------------------
            client = None
            max_retries = 30
            retry_interval = 2
            for attempt in range(1, max_retries + 1):
                try:
                    client = await Client.connect(temporal_host, namespace=namespace)
                    break
                except Exception as conn_err:
                    if attempt == max_retries:
                        raise conn_err
                    self.stdout.write(self.style.WARNING(
                        f"Failed to connect to Temporal (attempt {attempt}/{max_retries}): "
                        f"{conn_err}. Retrying in {retry_interval}s..."
                    ))
                    await asyncio.sleep(retry_interval)

            # -------------------------------------------------------------------
            # Register the 'default' namespace (idempotent — ignores if already exists)
            # -------------------------------------------------------------------
            from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest
            from google.protobuf.duration_pb2 import Duration
            try:
                await client.workflow_service.register_namespace(
                    RegisterNamespaceRequest(
                        namespace=namespace,
                        workflow_execution_retention_period=Duration(
                            seconds=7 * 24 * 60 * 60  # 7-day retention
                        )
                    )
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully registered Temporal namespace: '{namespace}'"
                ))
            except Exception as ns_err:
                # NamespaceAlreadyExistsError is expected on subsequent starts
                self.stdout.write(self.style.WARNING(
                    f"Namespace '{namespace}' registration check (might already exist): {ns_err}"
                ))

            # -------------------------------------------------------------------
            # Register one-shot startup sync schedules (Phase 4B)
            # -------------------------------------------------------------------
            today = datetime.date.today().isoformat()
            for task_name in _STARTUP_SYNC_TASKS:
                try:
                    await _register_startup_schedule(client, task_name, today)
                except Exception as sched_err:
                    # Non-fatal: log and continue — don't block worker startup
                    logger.error(f"[Startup] Failed to register schedule for '{task_name}': {sched_err}")

            # -------------------------------------------------------------------
            # Collect all registered activities
            # -------------------------------------------------------------------
            all_activities = [
                # Generic & Dynamic
                run_generic_task_activity,
                finalize_subscan_activity,
                finalize_failed_scan_activity,

                # Step 0
                initialize_scan_tasks_activity,
                load_checkpoint_activity,
                save_checkpoint_activity,
                target_profiling_activity,
                check_scan_queue_status_activity,
                get_enabled_plugins_for_tier_activity,

                # Tier 1
                run_subdomain_discovery_activity,
                run_amass_intel_discovery_activity,
                run_firewall_vpn_scan_activity,
                run_dns_security_activity,
                parse_discovery_results_activity,
                seed_endpoints_for_crawl_activity,

                # TOR
                run_tor_new_circuit_activity,

                # Tier 2
                run_http_crawl_activity,
                parse_http_crawl_results_activity,
                run_port_scan_activity,
                run_screenshot_activity,
                run_fetch_url_activity,
                parse_enumeration_results_activity,

                # Tier 3/4
                run_dir_file_fuzz_activity,
                parse_fuzz_results_activity,

                # Tier 5
                run_web_api_discovery_activity,
                run_waf_detection_activity,
                run_secret_scanning_activity,
                parse_analysis_results_activity,

                # Tier 6
                run_nuclei_activity,
                run_crlfuzz_activity,
                run_dalfox_activity,
                run_s3scanner_activity,
                run_acunetix_activity,
                run_cpanel_scan_activity,
                run_react2shell_activity,
                run_wpscan_activity,
                run_semgrep_activity,
                run_vigolium_scan_activity,
                run_vigolium_discovery_activity,
                run_vigolium_analysis_activity,
                mark_vulnerability_scan_complete_activity,
                run_waf_bypass_activity,
                run_brute_force_scan_activity,
                parse_assessment_results_activity,

                # Tier 7
                correlate_vulnerabilities_activity,
                calculate_risk_scores_activity,
                generate_impact_assessment_activity,
                sync_graph_activity,
                send_scan_notification_activity,

                # Stress Testing
                init_stress_test_activity,
                run_stress_tool_activity,
                finalize_stress_test_activity,

                # Startup sync
                run_startup_sync_activity,

                # Scheduled scan setup (Phase 4C)
                setup_scheduled_scan_activity,

                # Domain monitoring (Phase 4D)
                run_monitoring_check_activity,
                
                # New utility / integration activities
                run_llm_apme_activity,
                enrich_identities_activity,
                geo_localize_activity,
                import_hackerone_programs_activity,
                sync_bookmarked_programs_activity,
                fetch_proxies_activity,
            ]

            # -------------------------------------------------------------------
            # -------------------------------------------------------------------
            # Load dynamic plugins from the Temporal Registry
            # -------------------------------------------------------------------
            from asgiref.sync import sync_to_async
            from plugins.temporal_registry import PluginTemporalRegistry
            try:
                plugin_workflows = await sync_to_async(PluginTemporalRegistry.get_all_plugin_workflows)()
                plugin_activities = await sync_to_async(PluginTemporalRegistry.get_all_plugin_activities)()
                
                # Append to existing
                all_workflows = [MasterScanWorkflow, NucleiPlannerWorkflow, SubScanWorkflow, StressTestWorkflow, StartupSyncWorkflow, ScheduledScanWorkflow, MonitoringWorkflow, GoExecutorTaskWorkflow, ApmeTaskWorkflow, IdentityEnrichmentWorkflow, GeoLocalizeWorkflow, HackerOneImportWorkflow, HackerOneSyncBookmarkedWorkflow, ProxyFetchWorkflow] + plugin_workflows
                all_activities.extend(plugin_activities)
            except Exception as e:
                logger.error(f"Failed to load dynamic plugin temporal exports: {e}")
                all_workflows = [MasterScanWorkflow, NucleiPlannerWorkflow, SubScanWorkflow, StressTestWorkflow, StartupSyncWorkflow, ScheduledScanWorkflow, MonitoringWorkflow, GoExecutorTaskWorkflow, ApmeTaskWorkflow, IdentityEnrichmentWorkflow, GeoLocalizeWorkflow, HackerOneImportWorkflow, HackerOneSyncBookmarkedWorkflow, ProxyFetchWorkflow]

            # -------------------------------------------------------------------
            # Start the Temporal Worker
            # -------------------------------------------------------------------
            with DjangoAwareThreadPoolExecutor(max_workers=10) as executor:
                worker = Worker(
                    client,
                    task_queue="python-orchestrator-queue",
                    workflows=all_workflows,
                    activities=all_activities,
                    activity_executor=executor,
                    workflow_runner=UnsandboxedWorkflowRunner(),
                    max_concurrent_activities=10
                )

                self.stdout.write(self.style.SUCCESS(
                    f"Temporal Python Worker started. "
                    f"Listening on python-orchestrator-queue "
                    f"with {len(all_activities)} registered activities..."
                ))

                loop = asyncio.get_event_loop()

                def handle_shutdown():
                    self.stdout.write(self.style.WARNING("\nShutdown signal received, stopping worker..."))
                    logger.info("Temporal worker shutdown initiated")

                for sig in (signal.SIGTERM, signal.SIGINT):
                    try:
                        loop.add_signal_handler(sig, handle_shutdown)
                    except (NotImplementedError, RuntimeError):
                        pass  # Windows doesn't support add_signal_handler

                try:
                    await worker.run()
                except KeyboardInterrupt:
                    pass
                finally:
                    self.stdout.write(self.style.SUCCESS("Temporal worker stopped."))

        def start_redis_listener():
            import redis
            import time
            import signal
            import os
            from django.conf import settings

            def listen():
                while True:
                    try:
                        rdb = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
                        pubsub = rdb.pubsub()
                        pubsub.subscribe('orchestrator_control')
                        logger.info("[Control] Subscribed to orchestrator_control Redis channel.")
                        for message in pubsub.listen():
                            if message['type'] == 'message':
                                data = message['data'].decode('utf-8')
                                if data == 'restart':
                                    logger.warning("[Control] Received restart command. Terminating process...")
                                    os.kill(os.getpid(), signal.SIGTERM)
                                    time.sleep(2)
                                    os._exit(0)
                    except Exception as e:
                        logger.error(f"[Control] Redis listener error: {e}. Retrying in 5 seconds...")
                        time.sleep(5)

            import threading
            t = threading.Thread(target=listen, daemon=True)
            t.start()

        start_redis_listener()

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nWorker stopped by user request."))
            sys.exit(0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running worker: {e}"))
            sys.exit(1)
