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
import logging
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import connections
from temporalio.client import Client
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
)

# Activities (all Python-side activities are registered here)
from reNgine.temporal_activities import (
    run_generic_task_activity,
    finalize_subscan_activity,
    # Step 0: Target Profiling & Checkpoint Management
    target_profiling_activity,
    load_checkpoint_activity,
    save_checkpoint_activity,

    # Tier 1: Discovery
    run_subdomain_discovery_activity,
    run_amass_intel_discovery_activity,
    run_firewall_vpn_scan_activity,
    parse_discovery_results_activity,

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
    run_vulnerability_scan_activity,
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
)


class Command(BaseCommand):
    help = 'Runs the Python Temporal Orchestrator Worker on python-orchestrator-queue.'

    def handle(self, *args, **options):
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
            # Collect all registered activities
            # -------------------------------------------------------------------
            all_activities = [
                # Generic & Dynamic
                run_generic_task_activity,
                finalize_subscan_activity,

                # Step 0
                target_profiling_activity,
                load_checkpoint_activity,
                save_checkpoint_activity,

                # Tier 1
                run_subdomain_discovery_activity,
                run_amass_intel_discovery_activity,
                run_firewall_vpn_scan_activity,
                parse_discovery_results_activity,

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
                run_vulnerability_scan_activity,
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
            ]

            # -------------------------------------------------------------------
            # Start the Temporal Worker
            #
            # Key configuration notes:
            #   - workflow_runner=UnsandboxedWorkflowRunner(): Disables the
            #     Temporal workflow sandbox, which would otherwise reject
            #     Django/Celery transitive imports that use threading.local
            #     proxy subclasses. Safe because all non-determinism is
            #     isolated to activities, not workflow code.
            #   - max_concurrent_activities=10: Aligned with ThreadPoolExecutor
            #     max_workers to prevent the "activity executor capacity mismatch"
            #     warning from Temporal SDK.
            # -------------------------------------------------------------------
            with DjangoAwareThreadPoolExecutor(max_workers=10) as executor:
                worker = Worker(
                    client,
                    task_queue="python-orchestrator-queue",
                    workflows=[MasterScanWorkflow, NucleiPlannerWorkflow, SubScanWorkflow, StressTestWorkflow],
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

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nWorker stopped by user request."))
            sys.exit(0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running worker: {e}"))
            sys.exit(1)
