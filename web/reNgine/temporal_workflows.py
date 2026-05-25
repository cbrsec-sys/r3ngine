"""
Temporal Workflow definitions for the r3ngine scan pipeline.

Workflows define the durable orchestration logic — the "what runs when" in the
scan pipeline. All workflows are pure Python and must be deterministic (no I/O,
no random, no datetime.now()). Side-effecting work is delegated to activities.

The Python Orchestrator Worker hosts these workflow classes and listens on the
'python-orchestrator-queue' task queue.

Design principles:
  - Workflows are thin orchestrators: they gather, sequence, and fork activities.
  - All actual scan logic lives in activities (temporal_activities.py).
  - Activities on the 'go-executor-queue' are dispatched to the Go binary
    (web/executor/main.go) for heavy subprocess-based tool execution.
  - Activities on the 'python-orchestrator-queue' are dispatched back to this
    Python worker for Django DB reads/writes and Neo4j sync.
"""

import asyncio
from datetime import timedelta
from typing import Any, Dict, List
from temporalio import workflow
from temporalio.common import RetryPolicy

# All imports that touch Django or any non-deterministic module must be wrapped
# in workflow.unsafe.imports_passed_through() to prevent sandbox errors.
with workflow.unsafe.imports_passed_through():
    from reNgine.temporal_activities import _PERMITTED_GENERIC_TASKS
    from reNgine.scan_context import ScanContext


# Retry policy presets — applied explicitly to every execute_activity call.
# Default Temporal policy (unlimited, backoff to 100s) is intentionally overridden.

_RETRY_LONG_SCAN = RetryPolicy(
    maximum_attempts=2,
    initial_interval=timedelta(minutes=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
)
_RETRY_NETWORK_SCAN = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
)
_RETRY_INTERNAL = RetryPolicy(
    maximum_attempts=5,
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=1.5,
    maximum_interval=timedelta(seconds=30),
)
_RETRY_LLM = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
)


@workflow.defn(name="MasterScanWorkflow")
class MasterScanWorkflow:
    """Master workflow orchestrating the full 7-tier scan pipeline.

    Handles:
      - Target profiling and context enrichment (Step 0)
      - Tier 1: Subdomain discovery, Amass Intel, Firewall detection
      - Tier 2: HTTP crawl, Port scan, Screenshot, URL fetch
      - Tier 3/4: Directory/file fuzzing
      - Tier 5: Web API discovery, WAF detection, Secret scanning
      - Tier 6: Vulnerability scan (via NucleiPlannerWorkflow), WAF bypass, Brute force
      - Tier 7: Vulnerability correlation, risk scoring, AI impact, Neo4j APME sync
      - Scan completion notification

    The workflow supports pause/resume via Temporal signals and exposes the
    current checkpoint state via a query handler for the frontend to read.
    """

    def __init__(self) -> None:
        self._paused = False

    @workflow.run
    async def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full scan pipeline.

        Args:
            ctx (dict): Scan context dict. Must include at minimum:
                - scan_history_id (int)
                - engine_id (int)
                - domain_id (int)
                - results_dir (str)
                - tasks (list[str]): Task names enabled by the engine.
                - yaml_configuration (dict): Parsed engine YAML config.

        Returns:
            dict: {'status': 'SUCCESS', 'scan_history_id': int}
        """
        workflow.logger.info(
            f"Starting MasterScanWorkflow for scan_id={ctx.get('scan_history_id')}"
        )

        # ------------------------------------------------------------------
        # STEP 0: Target Profiling — validate scan, enrich context, set up dirs
        # ------------------------------------------------------------------
        ctx = await workflow.execute_activity(
            "TargetProfilingActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue"
        )

        # Backward-compat: preserve event-history position for workflows started
        # before the checkpoint stubs were removed. No-op; returns immediately.
        await workflow.execute_activity(
            "LoadCheckpointActivity",
            ctx,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue"
        )

        tasks = ctx.get("tasks", [])
        yaml_config = ctx.get("yaml_configuration", {})

        # ------------------------------------------------------------------
        # TIER 1: Discovery (parallel — all discovery tools run concurrently)
        # All must complete before Tier 2 begins (subdomains must be in DB).
        # osint runs in this group (mirrors Celery t1_background parallel group).
        # spiderfoot_scan runs here only when its YAML config block is present.
        # ------------------------------------------------------------------
        discovery_futures = []
        if "subdomain_discovery" in tasks:
            discovery_futures.append(
                workflow.execute_activity(
                    "RunSubdomainDiscoveryActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=2),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )
        if "amass_intel_discovery" in tasks:
            discovery_futures.append(
                workflow.execute_activity(
                    "RunAmassIntelDiscoveryActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=2),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )
        if "firewall_vpn_scan" in tasks:
            discovery_futures.append(
                workflow.execute_activity(
                    "RunFirewallVPNScanActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=30),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )
        if "osint" in tasks:
            discovery_futures.append(
                workflow.execute_activity(
                    "RunGenericTaskActivity",
                    args=[ctx, "osint", "OSINT Scan"],
                    start_to_close_timeout=timedelta(hours=2),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )
        if "spiderfoot_scan" in tasks and yaml_config.get("spiderfoot_scan"):
            discovery_futures.append(
                workflow.execute_activity(
                    "RunGenericTaskActivity",
                    args=[ctx, "spiderfoot_scan", "SpiderFoot Attack Surface Intelligence"],
                    start_to_close_timeout=timedelta(hours=4),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )

        if discovery_futures:
            await asyncio.gather(*discovery_futures)
            # Verify / log discovery results persisted to DB
            await workflow.execute_activity(
                "ParseDiscoveryResultsActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue"
            )

        await self._check_paused()

        # ------------------------------------------------------------------
        # TIER 2: HTTP Crawl + Port Scan + Screenshot (all parallel)
        #
        # http_crawl is a global config — it runs here and populates the
        # endpoint DB, which Tier 3 and Tier 4 depend on.
        # ------------------------------------------------------------------
        async def _http_crawl_branch():
            if "http_crawl" in tasks:
                await workflow.execute_activity(
                    "RunHTTPCrawlActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=3),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue"
                )
                await workflow.execute_activity(
                    "ParseHTTPCrawlResultsActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=_RETRY_INTERNAL,
                    task_queue="python-orchestrator-queue"
                )

        tier2_futures = [_http_crawl_branch()]

        if "port_scan" in tasks:
            tier2_futures.append(
                workflow.execute_activity(
                    "RunPortScanActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=2),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )

        await asyncio.gather(*tier2_futures)

        # ------------------------------------------------------------------
        # TIER 3: URL Fetching (sequential — needs Tier 2 http_crawl endpoints)
        # ------------------------------------------------------------------
        if "fetch_url" in tasks:
            await workflow.execute_activity(
                "RunFetchURLActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=2),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue"
            )

        # ------------------------------------------------------------------
        # TIER 4: Directory & File Fuzzing (sequential — needs Tier 3 URLs)
        # ------------------------------------------------------------------
        if "dir_file_fuzz" in tasks:
            await workflow.execute_activity(
                "RunDirFileFuzzActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=4),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue"
            )
            await workflow.execute_activity(
                "ParseFuzzResultsActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue"
            )

        # Consolidation: log total endpoint count after Tiers 2-4 complete
        await workflow.execute_activity(
            "ParseEnumerationResultsActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue"
        )

        await self._check_paused()

        # ------------------------------------------------------------------
        # TIER 5: Analysis (parallel — API discovery, WAF detection, secrets)
        # ------------------------------------------------------------------
        analysis_futures = []
        if "web_api_discovery" in tasks:
            analysis_futures.append(
                workflow.execute_activity(
                    "RunWebAPIDiscoveryActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=1),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )
        if "waf_detection" in tasks:
            analysis_futures.append(
                workflow.execute_activity(
                    "RunWAFDetectionActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=30),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )
        if "secret_scanning" in tasks:
            analysis_futures.append(
                workflow.execute_activity(
                    "RunSecretScanningActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=2),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )

        if analysis_futures:
            await asyncio.gather(*analysis_futures)
            await workflow.execute_activity(
                "ParseAnalysisResultsActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue"
            )

        await self._check_paused()

        # ------------------------------------------------------------------
        # TIER 6: Security Assessment (parallel — vulnerability, WAF bypass, brute force)
        # ------------------------------------------------------------------
        assessment_futures = []
        if "vulnerability_scan" in tasks:
            # Spawn as a child workflow so Nuclei execution has its own
            # independent Temporal history and can be tracked separately.
            assessment_futures.append(
                workflow.execute_child_workflow(
                    "NucleiPlannerWorkflow",
                    ctx,
                    id=f"{workflow.info().workflow_id}-nuclei",
                    task_queue="python-orchestrator-queue"
                )
            )
        if "screenshot" in tasks:
            assessment_futures.append(
                workflow.execute_activity(
                    "RunScreenshotActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=1),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )
        if "waf_bypass" in tasks:
            assessment_futures.append(
                workflow.execute_activity(
                    "RunWAFBypassActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=1),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )
        if "brute_force_scan" in tasks:
            assessment_futures.append(
                workflow.execute_activity(
                    "RunBruteForceScanActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=2),
                    heartbeat_timeout=timedelta(minutes=2),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue"
                )
            )

        if assessment_futures:
            await asyncio.gather(*assessment_futures)
            await workflow.execute_activity(
                "ParseAssessmentResultsActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue"
            )

        await self._check_paused()

        # ------------------------------------------------------------------
        # TIER 7: Post-Processing & Intelligence (sequential — ordering matters)
        # ------------------------------------------------------------------
        # MANDATORY TASKS: These must run for ALL scans unconditionally.
        
        await workflow.execute_activity(
            "CorrelateVulnerabilitiesActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue"
        )
        await workflow.execute_activity(
            "CalculateRiskScoresActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue"
        )

        # AI Impact Assessment
        await workflow.execute_activity(
            "GenerateImpactAssessmentActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=_RETRY_LLM,
            task_queue="python-orchestrator-queue"
        )

        # Neo4j graph sync (must precede APME so graph nodes exist)
        await workflow.execute_activity(
            "SyncGraphActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue"
        )

        # MANDATORY: Attack Path Modeling Engine — must be the final analysis step
        await workflow.execute_activity(
            "RunGenericTaskActivity",
            args=[ctx, "run_apme", "Attack Path Modeling Engine", {"scan_history_id": ctx.get("scan_history_id")}],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue"
        )

        # ------------------------------------------------------------------
        # FINAL: Mark scan complete and send notification
        # ------------------------------------------------------------------
        await workflow.execute_activity(
            "SendScanNotificationActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue"
        )

        workflow.logger.info(
            f"MasterScanWorkflow COMPLETE for scan_id={ctx.get('scan_history_id')}"
        )
        return {"status": "SUCCESS", "scan_history_id": ctx.get("scan_history_id")}

    # ------------------------------------------------------------------
    # Signal Handlers
    # ------------------------------------------------------------------

    @workflow.signal(name="pause")
    def pause_workflow(self) -> None:
        """Signal handler: pause the scan pipeline at the next tier boundary.

        The pipeline will save a checkpoint and wait until a 'resume' signal
        is received before proceeding to the next tier.
        """
        workflow.logger.info("MasterScanWorkflow received PAUSE signal.")
        self._paused = True

    @workflow.signal(name="resume")
    def resume_workflow(self) -> None:
        """Signal handler: resume a paused scan pipeline.

        Clears the paused flag so the workflow continues from the last
        completed tier.
        """
        workflow.logger.info("MasterScanWorkflow received RESUME signal.")
        self._paused = False

    # ------------------------------------------------------------------
    # Query Handlers
    # ------------------------------------------------------------------

    @workflow.query(name="get_current_state")
    def get_current_state(self) -> Dict[str, Any]:
        """Query handler: return the current workflow state for the frontend."""
        return {"paused": self._paused}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _check_paused(self) -> None:
        """Block at a tier boundary if a pause signal was received.

        Temporal's event history handles durability — no explicit checkpoint
        is needed. The workflow simply waits for the resume signal.
        """
        if self._paused:
            workflow.logger.info("MasterScanWorkflow PAUSED — waiting for resume signal.")
            await workflow.wait_condition(lambda: not self._paused)
            workflow.logger.info("MasterScanWorkflow RESUMED.")


@workflow.defn(name="NucleiPlannerWorkflow")
class NucleiPlannerWorkflow:
    """Child workflow managing vulnerability scan orchestration via Nuclei.

    Spawned as a child of MasterScanWorkflow when 'vulnerability_scan' is in
    the engine's task list. Running this as a child workflow gives the
    vulnerability scan its own independent Temporal history, making it easier
    to trace failures, retries, and individual template results separately.

    Args (via ctx):
        scan_history_id (int): Parent scan history ID.
        yaml_configuration (dict): Full engine config including nuclei settings.
    """

    @workflow.run
    async def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full vulnerability scan pipeline.

        Args:
            ctx (dict): Temporal workflow context (passed from MasterScanWorkflow).

        Returns:
            dict: {'status': 'SUCCESS'} on completion.
        """
        workflow.logger.info(
            f"Starting NucleiPlannerWorkflow for scan_id={ctx.get('scan_history_id')}"
        )
        
        yaml_config = ctx.get('yaml_configuration', {})
        vuln_config = yaml_config.get('vulnerability_scan', {})
        
        # --- Stage 1: Primary scanners ---
        if vuln_config.get('nuclei', True):
            await workflow.execute_activity("RunNucleiActivity", ctx, start_to_close_timeout=timedelta(hours=6), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")
        
        if vuln_config.get('crlfuzz', False):
            await workflow.execute_activity("RunCRLFuzzActivity", ctx, start_to_close_timeout=timedelta(hours=2), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")
            
        if vuln_config.get('dalfox', False):
            await workflow.execute_activity("RunDalfoxActivity", ctx, start_to_close_timeout=timedelta(hours=2), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")
            
        if vuln_config.get('s3scanner', True):
            await workflow.execute_activity("RunS3ScannerActivity", ctx, start_to_close_timeout=timedelta(hours=2), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")
            
        # --- Stage 2: Additional scanners ---
        if vuln_config.get('acunetix', False):
            await workflow.execute_activity("RunAcunetixActivity", ctx, start_to_close_timeout=timedelta(hours=2), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")
            
        cpanel_cfg = vuln_config.get('cpanel_scanner', {})
        if cpanel_cfg.get('run_cpanel_scanner', True):
            await workflow.execute_activity("RunCpanelScanActivity", ctx, start_to_close_timeout=timedelta(hours=2), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")
            
        if vuln_config.get('wpscan', True):
            await workflow.execute_activity("RunWpscanActivity", ctx, start_to_close_timeout=timedelta(hours=2), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")
            
        react_cfg = vuln_config.get('react_scanner', {})
        if react_cfg.get('run_react_scanner', True):
            await workflow.execute_activity("RunReact2ShellActivity", ctx, start_to_close_timeout=timedelta(hours=2), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")
            
        await workflow.execute_activity("RunSemgrepActivity", ctx, start_to_close_timeout=timedelta(hours=2), heartbeat_timeout=timedelta(minutes=5), task_queue="python-orchestrator-queue")

        workflow.logger.info(
            f"NucleiPlannerWorkflow COMPLETE for scan_id={ctx.get('scan_history_id')}"
        )
        return {"status": "SUCCESS"}


# Registry for SubScanWorkflow dispatch.
# value=None means the scan type has special handling and is coded inline.
# value=dict means standard dispatch: call `activity` with args from `args_builder`.
_SUBSCAN_DISPATCH = {
    "osint": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "osint", "OSINT Scan", {"host": ctx.get("subdomain_name", "")}
        ],
    },
    "subdomain_discovery": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "subdomain_discovery", "Subdomain Discovery",
            {"host": ctx.get("subdomain_name", "")},
        ],
    },
    "port_scan": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "port_scan", "Port Scan",
            {"hosts": [ctx.get("subdomain_name", "")]},
        ],
    },
    "fetch_url": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "fetch_url", "Fetch URL",
            {"urls": [ctx.get("subdomain_http_url") or f"http://{ctx.get('subdomain_name', '')}/"]},
        ],
    },
    "dir_file_fuzz": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [ctx, "dir_file_fuzz", "Dir File Fuzz", {}],
    },
    "screenshot": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=1),
        "args_builder": lambda ctx: [ctx, "screenshot", "Screenshot", {}],
    },
    "waf_detection": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(minutes=30),
        "args_builder": lambda ctx: [ctx, "waf_detection", "WAF Detection", {}],
    },
    "http_crawl": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "http_crawl", "HTTP Crawl",
            {"urls": [ctx.get("subdomain_http_url") or f"http://{ctx.get('subdomain_name', '')}/"]},
        ],
    },
    "web_api_discovery": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "web_api_discovery", "Web API Discovery",
            {"urls": [ctx.get("subdomain_http_url") or f"http://{ctx.get('subdomain_name', '')}/"]},
        ],
    },
    "waf_bypass": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=1),
        "args_builder": lambda ctx: [ctx, "waf_bypass", "WAF Bypass", {}],
    },
    "brute_force_scan": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [
            ctx, "brute_force_scan", "Brute Force Scan",
            {"targets": [ctx.get("subdomain_name", "")]},
        ],
    },
    "firewall_vpn_scan": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=1),
        "args_builder": lambda ctx: [ctx, "firewall_vpn_scan", "Firewall/VPN Scan", {}],
    },
    "spiderfoot_scan": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=4),
        "args_builder": lambda ctx: [ctx, "spiderfoot_scan", "SpiderFoot Scan", {}],
    },
    "secret_scanning": {
        "activity": "RunGenericTaskActivity",
        "timeout": timedelta(hours=2),
        "args_builder": lambda ctx: [ctx, "secret_scanning", "Secret Scanning", {}],
    },
    # Special cases — handled with inline logic in SubScanWorkflow.run():
    "vulnerability_scan": None,  # Has Tier 7 post-steps (correlation, risk, APME)
    "baddns": None,              # Modifies ctx before dispatch
}


@workflow.defn(name="SubScanWorkflow")
class SubScanWorkflow:
    """Workflow orchestrating a target subdomain subscan.

    Subscans are scoped to a single subdomain and run a specific scan type
    (e.g., 'osint', 'port_scan', 'fetch_url', etc.) inside a Temporal workflow.
    """

    @workflow.run
    async def run(self, ctx: Dict[str, Any], scan_type: str) -> Dict[str, Any]:
        """Execute the subscan workflow.

        Args:
            ctx (dict): Subscan context dict.
            scan_type (str): Short name of the task/scan type (e.g. 'osint').

        Returns:
            dict: {'status': 'SUCCESS'} on completion.
        """
        workflow.logger.info(
            f"Starting SubScanWorkflow for subdomain_id={ctx.get('subdomain_id')} scan_type={scan_type}"
        )

        # Validate scan_type against the permitted task list before any dispatch
        known_explicit = set(_SUBSCAN_DISPATCH.keys())
        if scan_type not in known_explicit and scan_type not in _PERMITTED_GENERIC_TASKS:
            raise ValueError(
                f"[SubScanWorkflow] '{scan_type}' is not a recognized subscan type. "
                f"Add it to _PERMITTED_GENERIC_TASKS in temporal_activities.py to enable dispatch."
            )

        is_cancelled = False
        success = False
        try:
            subdomain_name = ctx.get('subdomain_name', '')
            yaml_configuration = ctx.get('yaml_configuration', {})

            # Determine target url
            subdomain_http_url = ctx.get('subdomain_http_url')
            target_url = subdomain_http_url or f"http://{subdomain_name}/"

            # Execute the primary activity step
            dispatch = _SUBSCAN_DISPATCH.get(scan_type)

            if scan_type == "baddns":
                ctx_baddns = {
                    **ctx,
                    "yaml_configuration": {
                        **ctx.get("yaml_configuration", {}),
                        "subdomain_discovery": {
                            **ctx.get("yaml_configuration", {}).get("subdomain_discovery", {}),
                            "uses_tools": ["baddns"],
                        },
                    },
                }
                await workflow.execute_activity(
                    "RunGenericTaskActivity",
                    args=[ctx_baddns, "subdomain_discovery", "Baddns Scan", {"host": subdomain_name}],
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                )

            elif scan_type == "vulnerability_scan":
                await workflow.execute_activity(
                    "RunGenericTaskActivity",
                    args=[ctx, "vulnerability_scan", "Vulnerability Scan", {"urls": [target_url]}],
                    start_to_close_timeout=timedelta(hours=6),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue",
                )

            elif dispatch is not None:
                args = dispatch["args_builder"](ctx)
                await workflow.execute_activity(
                    dispatch["activity"],
                    args=args,
                    start_to_close_timeout=dispatch["timeout"],
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                )

            else:
                # Generic fallback: any _PERMITTED_GENERIC_TASKS entry not in the
                # explicit dispatch table runs with ctx only. The task function
                # derives its target from yaml_configuration / ctx internals.
                await workflow.execute_activity(
                    "RunGenericTaskActivity",
                    args=[ctx, scan_type, scan_type.replace("_", " ").title()],
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                )

            success = True
        except asyncio.CancelledError:
            workflow.logger.info("SubScanWorkflow was cancelled. Skipping post-scan tasks.")
            is_cancelled = True
            raise
        except Exception as e:
            workflow.logger.error(f"SubScanWorkflow failed during execution: {e}")
            success = False
            raise

        finally:
            if not is_cancelled:
                # First, run mandatory post-scan tasks for ALL subscans unconditionally
                try:
                    await workflow.execute_activity(
                        "CorrelateVulnerabilitiesActivity",
                        ctx,
                        start_to_close_timeout=timedelta(minutes=15),
                        retry_policy=_RETRY_INTERNAL,
                        task_queue="python-orchestrator-queue",
                    )
                    await workflow.execute_activity(
                        "CalculateRiskScoresActivity",
                        ctx,
                        start_to_close_timeout=timedelta(minutes=15),
                        retry_policy=_RETRY_INTERNAL,
                        task_queue="python-orchestrator-queue",
                    )
                    await workflow.execute_activity(
                        "GenerateImpactAssessmentActivity",
                        ctx,
                        start_to_close_timeout=timedelta(minutes=30),
                        retry_policy=_RETRY_LLM,
                        task_queue="python-orchestrator-queue"
                    )
                    await workflow.execute_activity(
                        "SyncGraphActivity",
                        ctx,
                        start_to_close_timeout=timedelta(minutes=30),
                        retry_policy=_RETRY_NETWORK_SCAN,
                        task_queue="python-orchestrator-queue",
                    )
                    # MANDATORY: Attack Path Modeling Engine — required before subscan completes
                    await workflow.execute_activity(
                        "RunGenericTaskActivity",
                        args=[ctx, "run_apme", "Attack Path Modeling Engine", {"scan_history_id": ctx.get("scan_history_id")}],
                        start_to_close_timeout=timedelta(minutes=30),
                        retry_policy=_RETRY_INTERNAL,
                        task_queue="python-orchestrator-queue",
                    )
                except Exception as post_e:
                    workflow.logger.error(f"SubScanWorkflow post-scan tasks failed: {post_e}")
    
                # Finalize SubScan record in the database
                await workflow.execute_activity(
                    "FinalizeSubScanActivity",
                    args=[ctx, success],
                    start_to_close_timeout=timedelta(seconds=60),
                    task_queue="python-orchestrator-queue"
                )

        return {"status": "SUCCESS"}


# ===========================================================================
# Stress Test Workflow
# ===========================================================================

@workflow.defn(name="StressTestWorkflow")
class StressTestWorkflow:
    """Durable stress test orchestrator replacing the run_stress_testing Celery task.

    Executes configured stress tools (k6, wrk, hping3, locust, stressor) against
    resolved target endpoints sequentially.  Supports instant cancellation via the
    'kill_switch' signal — the workflow stops at the next endpoint/tool boundary
    without needing a Redis poll.

    Input ctx keys (passed as the first workflow argument):
        scan_history_id  (int)   — ScanHistory PK
        target_domain_name (str) — bare hostname for the target
        stress_config    (dict)  — full stress_test config from the API payload
    """

    def __init__(self) -> None:
        self._kill_requested: bool = False
        self._kill_event = asyncio.Event()

    @workflow.run
    async def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        scan_id = ctx.get("scan_history_id")
        workflow.logger.info(f"[StressTestWorkflow] Starting for scan_id={scan_id}")

        # Step 1 — Resolve endpoints, create DB record, publish 'running' to telemetry
        ctx = await workflow.execute_activity(
            "InitStressTestActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=2),
            task_queue="python-orchestrator-queue",
        )

        endpoints: List[str] = ctx.get("resolved_endpoints", [])
        tools: List[str] = ctx.get("stress_config", {}).get("uses_tools", ["k6"])

        if not endpoints:
            workflow.logger.warning(
                f"[StressTestWorkflow] No endpoints resolved for scan_id={scan_id}. "
                "Finalising immediately."
            )

        # Step 2 — Run each (endpoint x tool) pair sequentially.
        # Matches current Celery behaviour; promote to asyncio.gather() per endpoint
        # in a future iteration if parallelism is required.
        aggregate: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_latencies": [],
            "p95_latencies": [],
            "p99_latencies": [],
            "max_rps_values": [],
        }

        outer_break = False
        for endpoint_url in endpoints:
            if outer_break:
                break
            for tool in tools:
                if self._kill_requested:
                    workflow.logger.info(
                        f"[StressTestWorkflow] Kill signal — aborting before "
                        f"tool={tool} endpoint={endpoint_url}"
                    )
                    outer_break = True
                    break

                tool_ctx = {**ctx, "current_endpoint": endpoint_url, "current_tool": tool}
                try:
                    activity_task = asyncio.create_task(
                        workflow.execute_activity(
                            "RunStressToolActivity",
                            tool_ctx,
                            # Allow up to 15 minutes per slot:
                            # longest supported duration is 10 min + 5 min overhead.
                            start_to_close_timeout=timedelta(minutes=15),
                            heartbeat_timeout=timedelta(seconds=30),
                            # Stress tests are not idempotent — never auto-retry.
                            retry_policy=RetryPolicy(maximum_attempts=1),
                            task_queue="python-orchestrator-queue",
                        )
                    )
                    kill_task = asyncio.create_task(self._kill_event.wait())
                    
                    done, pending = await asyncio.wait(
                        [activity_task, kill_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    if kill_task in done:
                        activity_task.cancel()
                        workflow.logger.info(f"[StressTestWorkflow] Kill signal received. Cancelling activity.")
                        outer_break = True
                        break
                    
                    metrics = activity_task.result()
                    aggregate["total_requests"] += metrics.get("total_requests", 0)
                    aggregate["successful_requests"] += metrics.get("successful_requests", 0)
                    aggregate["failed_requests"] += metrics.get("failed_requests", 0)
                    if metrics.get("avg_latency_ms", 0) > 0:
                        aggregate["avg_latencies"].append(metrics["avg_latency_ms"])
                    if metrics.get("p95_latency_ms", 0) > 0:
                        aggregate["p95_latencies"].append(metrics["p95_latency_ms"])
                    if metrics.get("p99_latency_ms", 0) > 0:
                        aggregate["p99_latencies"].append(metrics["p99_latency_ms"])
                    if metrics.get("max_requests_per_second", 0) > 0:
                        aggregate["max_rps_values"].append(metrics["max_requests_per_second"])
                except Exception as exc:
                    workflow.logger.error(
                        f"[StressTestWorkflow] tool={tool} endpoint={endpoint_url} "
                        f"failed: {exc}"
                    )
                    # Continue to next tool/endpoint rather than aborting the whole
                    # workflow — mirrors the Celery task's try/except per subprocess.

        # Step 3 — Aggregate + finalise DB records + send notification
        avgs = aggregate["avg_latencies"]
        p95s = aggregate["p95_latencies"]
        p99s = aggregate["p99_latencies"]
        maxrps = aggregate["max_rps_values"]

        final_ctx = {
            **ctx,
            "aborted": self._kill_requested,
            "total_requests": aggregate["total_requests"],
            "successful_requests": aggregate["successful_requests"],
            "failed_requests": aggregate["failed_requests"],
            "avg_latency_ms": sum(avgs) / len(avgs) if avgs else 0.0,
            "p95_latency_ms": sum(p95s) / len(p95s) if p95s else 0.0,
            "p99_latency_ms": sum(p99s) / len(p99s) if p99s else 0.0,
            "max_rps": max(maxrps) if maxrps else 0.0,
        }

        await workflow.execute_activity(
            "FinalizeStressTestActivity",
            final_ctx,
            start_to_close_timeout=timedelta(minutes=5),
            task_queue="python-orchestrator-queue",
        )

        status = "ABORTED" if self._kill_requested else "SUCCESS"
        workflow.logger.info(
            f"[StressTestWorkflow] Complete — scan_id={scan_id} status={status}"
        )
        return {"status": status, "scan_id": scan_id}

    @workflow.signal(name="kill_switch")
    def kill_switch(self) -> None:
        """Signal the workflow to abort at the next endpoint/tool boundary."""
        workflow.logger.info("[StressTestWorkflow] KILL SWITCH signal received.")
        self._kill_requested = True
        self._kill_event.set()

    @workflow.query(name="is_running")
    def is_running(self) -> bool:
        """Return True if the workflow has not yet received a kill signal."""
        return not self._kill_requested


@workflow.defn(name="MonitoringWorkflow")
class MonitoringWorkflow:
    """Periodic workflow launched by a Temporal Schedule for domain monitoring.

    Runs RunMonitoringCheckActivity for a single domain on the configured
    frequency (hourly/daily/weekly/monthly). The schedule is created/deleted
    by manage_monitoring_task() in targetApp/views.py.
    """

    @workflow.run
    async def run(self, domain_id: int) -> None:
        await workflow.execute_activity(
            "RunMonitoringCheckActivity",
            args=[domain_id],
            start_to_close_timeout=timedelta(hours=6),
            # Don't retry — if a monitoring check fails, wait for next scheduled run
            retry_policy=RetryPolicy(maximum_attempts=1),
            task_queue="python-orchestrator-queue",
        )


@workflow.defn(name="ScheduledScanWorkflow")
class ScheduledScanWorkflow:
    """Durable workflow launched by a Temporal Schedule for periodic/clocked scans.

    Step 1: SetupScheduledScanActivity creates ScanHistory + initial subdomain/endpoint
            and returns a complete workflow ctx.
    Step 2: MasterScanWorkflow runs the full scan pipeline as a child workflow.
    """

    @workflow.run
    async def run(self, params: dict) -> dict:
        ctx = await workflow.execute_activity(
            "SetupScheduledScanActivity",
            args=[params],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
            task_queue="python-orchestrator-queue",
        )
        scan_id = ctx.get("scan_history_id", "unknown")
        result = await workflow.execute_child_workflow(
            "MasterScanWorkflow",
            args=[ctx],
            id=f"scheduled-master-{scan_id}",
            task_queue="python-orchestrator-queue",
            execution_timeout=timedelta(days=30),
        )
        return result


@workflow.defn(name="StartupSyncWorkflow")
class StartupSyncWorkflow:
    """One-shot workflow that runs a single named startup sync task as an activity.

    Launched by a one-shot Temporal Schedule created on each orchestrator startup.
    The schedule fires once (limited_actions=1) then exhausts itself.
    """

    @workflow.run
    async def run(self, task_name: str) -> None:
        await workflow.execute_activity(
            "RunStartupSyncActivity",
            args=[task_name],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
            task_queue="python-orchestrator-queue",
        )
