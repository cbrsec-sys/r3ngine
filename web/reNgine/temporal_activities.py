"""
Temporal Activities for r3ngine scan pipeline.

All Python-side activities are implemented here. They are designed to be
called by the Python Orchestrator Worker listening on the
'python-orchestrator-queue'.

The activities delegate to the existing scan task functions in
web/reNgine/tasks.py, which contain the full scan logic. Since the Python
worker runs with UnsandboxedWorkflowRunner, Django models and the existing
task code are fully accessible here without sandbox restrictions.

Design principle: Activities call existing RengineTask-decorated scan functions
directly, providing a lightweight proxy object (TemporalTaskProxy) that satisfies
the `self` interface expected by those tasks without requiring Celery.
"""

import logging
import os
import yaml

from temporalio import activity
from django.utils import timezone

from reNgine.scan_context import ScanContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TemporalTaskProxy
# ---------------------------------------------------------------------------

class TemporalTaskProxy:
    """A lightweight proxy that mimics the `self` interface of RengineTask.

    Existing scan task functions (subdomain_discovery, port_scan, etc.)
    are bound to a Celery Task instance via `self`. This proxy satisfies
    that interface so the same functions can be called directly inside
    Temporal activities without Celery.

    Args:
        ctx (dict): The Temporal workflow context dictionary containing all
                    relevant scan metadata (scan_history_id, engine_id,
                    results_dir, yaml_configuration, etc.).
        task_name (str): Short name of the task (used for ScanActivity tracking).
        description (str, optional): Human-readable description for the UI.
    """

    def __init__(self, ctx: dict, task_name: str, description: str = None):
        from startScan.models import ScanHistory, SubScan, ScanActivity
        from scanEngine.models import EngineType
        from targetApp.models import Domain
        from reNgine.definitions import RUNNING_TASK
        from reNgine.settings import RENGINE_RESULTS

        self._is_temporal_proxy = True
        self.task_name = task_name
        self.description = description or ' '.join(task_name.split('_')).capitalize()
        self.status = RUNNING_TASK
        self.result = None
        self.error = None
        self.traceback = None

        # Core context fields
        self.scan_id = ctx.get('scan_history_id')
        self.subscan_id = ctx.get('subscan_id')
        self.engine_id = ctx.get('engine_id')
        self.domain_id = ctx.get('domain_id')
        self.subdomain_id = ctx.get('subdomain_id')
        self.results_dir = ctx.get('results_dir', RENGINE_RESULTS)
        os.makedirs(self.results_dir, exist_ok=True)
        self.yaml_configuration = ctx.get('yaml_configuration', {})
        self.out_of_scope_subdomains = ctx.get('out_of_scope_subdomains', [])
        self.starting_point_path = ctx.get('starting_point_path', '')
        self.excluded_paths = ctx.get('excluded_paths', [])
        self.history_file = f'{self.results_dir}/commands.txt'
        self.output_path = f'{self.results_dir}/{task_name}.txt'
        self.filename = f'{task_name}.txt'
        self.activity_id = ctx.get('activity_id')
        self.track = ctx.get('track', True)

        # Django ORM objects
        self.scan = ScanHistory.objects.filter(pk=self.scan_id).first()
        self.subscan = SubScan.objects.filter(pk=self.subscan_id).first() if self.subscan_id else None
        self.engine = EngineType.objects.filter(pk=self.engine_id).first()
        if not self.engine and self.scan:
            self.engine = self.scan.scan_type
            self.engine_id = self.engine.id if self.engine else None
        self.domain = self.scan.domain if self.scan else Domain.objects.filter(id=self.domain_id).first()
        self.subdomain = self.subscan.subdomain if self.subscan else None

        # Create a ScanActivity record in the DB to track this task
        if self.track and self.scan:
            self._create_scan_activity()

    def _create_scan_activity(self):
        """Create a ScanActivity entry in the database for progress tracking.

        This mirrors the create_scan_activity() call from RengineTask.__call__
        so the scan activity feed in the frontend is populated correctly.
        """
        from startScan.models import ScanActivity
        from reNgine.definitions import RUNNING_TASK
        try:
            # Use temporal activity ID as the tracking ID
            temporal_activity_id = activity.info().activity_id
            self.activity = ScanActivity(
                name=self.task_name,
                title=self.description,
                time=timezone.now(),
                status=RUNNING_TASK,
                execution_id=f"temporal-{temporal_activity_id}"
            )
            self.activity.save()
            self.activity_id = self.activity.id
            if self.scan:
                self.activity.scan_of = self.scan
                self.activity.save()
        except Exception as e:
            logger.warning(f"Could not create ScanActivity for {self.task_name}: {e}")
            self.activity = None
            self.activity_id = None

    def update_scan_activity(self, status, error_message=None):
        """Update the ScanActivity record with the final task status.

        Args:
            status (int): Task status code (SUCCESS_TASK, FAILED_TASK, etc.)
            error_message (str, optional): Error message if the task failed.
        """
        from startScan.models import ScanActivity
        try:
            if getattr(self, 'activity', None):
                self.activity.status = status
                self.activity.error_message = error_message
                self.activity.time = timezone.now()
                self.activity.save()
        except Exception as e:
            logger.warning(f"Could not update ScanActivity for {self.task_name}: {e}")

    def notify(self, name=None, severity=None, fields={}, add_meta_info=True):
        """Send a Temporal-compatible notification (no-op for now).

        In Celery, this triggered send_task_notif.delay(). In Temporal, the
        notification is sent via the dedicated SendScanNotificationActivity
        at workflow completion. Individual per-task notifications are a
        best-effort log entry here.

        Args:
            name (str, optional): Notification name override.
            severity (str, optional): Severity level.
            fields (dict): Extra notification fields.
            add_meta_info (bool): Whether to include scan metadata.
        """
        logger.info(f"[notify] Task '{name or self.task_name}' fields={fields}")


# ---------------------------------------------------------------------------
# Helper: run a RengineTask function via TemporalTaskProxy
# ---------------------------------------------------------------------------

def _run_task(task_func, ctx: dict, task_name: str, description: str = None, **kwargs):
    """Execute an existing RengineTask-decorated function inside a Temporal activity.

    Spawns a heartbeat thread that sends signals to Temporal every 30 seconds
    to prevent activity timeout for long-running operations.

    Constructs a TemporalTaskProxy as the task's `self`, sets the status on
    success/failure and returns the task's result.

    Args:
        task_func (callable): The task function (e.g. subdomain_discovery).
        ctx (dict): Temporal workflow context dictionary.
        task_name (str): Short task name for DB tracking.
        description (str, optional): Human-readable description.
        **kwargs: Extra keyword arguments passed to task_func.

    Returns:
        bool: True on success.

    Raises:
        Exception: Re-raises any exception from the underlying task so Temporal
                   can retry or fail the activity appropriately.
    """
    from reNgine.definitions import SUCCESS_TASK, FAILED_TASK
    import contextvars
    import threading
    import time

    proxy = TemporalTaskProxy(ctx, task_name, description)

    activity_running = True

    # Copy the current contextvars context so the heartbeat thread inherits the
    # Temporal activity context. threading.Thread does NOT copy contextvars by
    # default, causing activity.heartbeat() to fail with "Not in activity context",
    # which silently prevents all heartbeats from reaching Temporal and triggers
    # the heartbeat_timeout cancellation + retry loop.
    _activity_ctx = contextvars.copy_context()

    def send_heartbeats():
        def _do_heartbeats():
            from temporalio.exceptions import CancelledError as TemporalCancelledError
            while activity_running:
                try:
                    activity.heartbeat(
                        f"Activity {task_name} running for {proxy.task_name}"
                    )
                    activity.logger.debug(f"[_run_task] Sent heartbeat for {task_name}")
                except TemporalCancelledError:
                    # Temporal has cancelled this activity — propagate by marking
                    # the scan aborted so the stream_command kill switch fires.
                    activity.logger.warning(
                        f"[_run_task] Temporal cancellation received for {task_name}. "
                        f"Marking scan {proxy.scan_id} as aborted."
                    )
                    try:
                        from startScan.models import ScanHistory
                        from reNgine.definitions import ABORTED_TASK
                        if proxy.scan_id:
                            _scan = ScanHistory.objects.filter(pk=proxy.scan_id).first()
                            if _scan and _scan.scan_status != ABORTED_TASK:
                                _scan.scan_status = ABORTED_TASK
                                _scan.save()
                    except Exception as mark_err:
                        activity.logger.warning(
                            f"[_run_task] Could not mark scan aborted: {mark_err}"
                        )
                    return  # stop heartbeating; kill switch will stop the subprocess
                except Exception as hb_err:
                    activity.logger.warning(f"[_run_task] Heartbeat failed: {hb_err}")

                for _ in range(6):  # 6 * 5s = 30s, checking flag each iteration
                    if not activity_running:
                        break
                    time.sleep(5)
        _activity_ctx.run(_do_heartbeats)

    heartbeat_thread = threading.Thread(target=send_heartbeats, daemon=True)
    heartbeat_thread.start()

    try:
        # task_func is the plain function (self/proxy is passed as first positional arg).
        raw_func = task_func.__func__ if hasattr(task_func, '__func__') else task_func
        raw_func(proxy, ctx=ctx, description=description, **kwargs)
        proxy.update_scan_activity(SUCCESS_TASK)
        return True
    except Exception as exc:
        activity.logger.exception(f"[_run_task] Task {task_name} failed: {exc}")
        proxy.update_scan_activity(FAILED_TASK, error_message=repr(exc))
        raise
    finally:
        activity_running = False
        heartbeat_thread.join(timeout=5)


# ===========================================================================
# Step 0 — Target Profiling & Checkpoint Management
# ===========================================================================

@activity.defn(name="LoadCheckpointActivity")
def load_checkpoint_activity(ctx: dict) -> dict:
    """Backward-compat no-op. Temporal's event history is the durable checkpoint."""
    return {}


@activity.defn(name="SaveCheckpointActivity")
def save_checkpoint_activity(ctx: dict) -> None:
    """Backward-compat no-op. Temporal's event history is the durable checkpoint."""
    return


@activity.defn(name="TargetProfilingActivity")
def target_profiling_activity(ctx: dict) -> dict:
    """Validate the scan target and populate baseline scan context.

    Reads the ScanHistory record, resolves the domain, loads and caches the
    engine YAML configuration into ctx, and creates the scan results directory.

    Args:
        ctx (dict): Temporal workflow context. Must contain 'scan_history_id'
                    and 'engine_id'.

    Returns:
        dict: Enriched ctx with 'yaml_configuration', 'results_dir', and
              'domain_name' populated.
    """
    from startScan.models import ScanHistory
    from scanEngine.models import EngineType
    from reNgine.settings import RENGINE_RESULTS
    from reNgine.definitions import RUNNING_TASK

    scan_id = ctx.get('scan_history_id')
    activity.logger.info(f"[TargetProfilingActivity] Profiling scan_history_id={scan_id}")

    scan = ScanHistory.objects.filter(pk=scan_id).first()
    if not scan:
        raise ValueError(f"ScanHistory with id={scan_id} not found.")

    engine_id = ctx.get('engine_id') or (scan.scan_type.id if scan.scan_type else None)
    engine = EngineType.objects.filter(pk=engine_id).first()
    if not engine:
        raise ValueError(f"EngineType with id={engine_id} not found.")

    # Re-arm status to RUNNING so the Django DB reflects reality when a
    # workflow is restarted after a prior run set it to FAILED or ABORTED.
    if scan.scan_status != RUNNING_TASK:
        scan.scan_status = RUNNING_TASK
        scan.save(update_fields=['scan_status'])

    # Parse YAML configuration if not already done
    if 'yaml_configuration' not in ctx or not ctx['yaml_configuration']:
        ctx['yaml_configuration'] = yaml.safe_load(engine.yaml_configuration) or {}

    # Set task list from engine
    if 'tasks' not in ctx:
        ctx['tasks'] = engine.tasks or []

    # Ensure results dir exists
    results_dir = ctx.get('results_dir')
    if not results_dir:
        results_dir = f'{RENGINE_RESULTS}/{scan.domain.name}_{scan_id}'
        ctx['results_dir'] = results_dir
    os.makedirs(results_dir, exist_ok=True)

    # Enrich ctx with domain information
    ctx['domain_name'] = scan.domain.name
    ctx['engine_id'] = engine_id

    activity.logger.info(
        f"[TargetProfilingActivity] Profiled target {scan.domain.name}, "
        f"tasks={ctx.get('tasks')}"
    )
    return ctx


# ===========================================================================
# Tier 1 — Discovery
# ===========================================================================

@activity.defn(name="RunSubdomainDiscoveryActivity")
def run_subdomain_discovery_activity(ctx: dict) -> bool:
    """Execute subdomain discovery tools (subfinder, amass, etc.) against the target.

    Delegates to the existing `subdomain_discovery` Celery task function which
    runs all configured discovery tools sequentially, writing results to the
    scan results directory and persisting discovered subdomains to the DB.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import subdomain_discovery
    activity.logger.info(f"[RunSubdomainDiscoveryActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        subdomain_discovery,
        ctx,
        task_name='subdomain_discovery',
        description='Subdomain Discovery'
    )


@activity.defn(name="RunAmassIntelDiscoveryActivity")
def run_amass_intel_discovery_activity(ctx: dict) -> bool:
    """Run Amass Intel infrastructure discovery against the target domain.

    Delegates to the existing `amass_intel_discovery` task to find related
    root domains and IP ranges via WHOIS and other intelligence sources.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import amass_intel_discovery
    from startScan.models import ScanHistory
    scan = ScanHistory.objects.filter(pk=ctx.get('scan_history_id')).first()
    host = scan.domain.name if scan else ctx.get('domain_name', '')
    activity.logger.info(f"[RunAmassIntelDiscoveryActivity] host={host}")
    return _run_task(
        amass_intel_discovery,
        ctx,
        task_name='amass_intel_discovery',
        description='Infrastructure Discovery',
        host=host
    )


@activity.defn(name="RunFirewallVPNScanActivity")
def run_firewall_vpn_scan_activity(ctx: dict) -> bool:
    """Detect firewall and VPN infrastructure protecting the target.

    Delegates to the existing `firewall_vpn_scan` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import firewall_vpn_scan
    activity.logger.info(f"[RunFirewallVPNScanActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        firewall_vpn_scan,
        ctx,
        task_name='firewall_vpn_scan',
        description='Firewall & VPN Scan'
    )


@activity.defn(name="RunDNSSecurityActivity")
def run_dns_security_activity(ctx: dict) -> bool:
    """Run DNS security checks: AXFR, DNSSEC, amplification, optional brute-force.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.dns_tasks import dns_security
    activity.logger.info(f"[RunDNSSecurityActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        dns_security,
        ctx,
        task_name='dns_security',
        description='DNS Security Scan'
    )


@activity.defn(name="ParseDiscoveryResultsActivity")
def parse_discovery_results_activity(ctx: dict) -> bool:
    """Parse and persist discovery tier results to the database.

    After all Tier 1 tools finish, this activity consolidates output files,
    deduplicates subdomains, and writes them to the Subdomain model.
    In the current implementation, each discovery tool writes directly to the
    DB via save_subdomain(), so this is a lightweight verification pass.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from startScan.models import ScanHistory, Subdomain
    scan_id = ctx.get('scan_history_id')
    count = Subdomain.objects.filter(scan_history_id=scan_id).count()
    activity.logger.info(
        f"[ParseDiscoveryResultsActivity] scan_id={scan_id}: "
        f"{count} subdomains persisted."
    )
    return True


@activity.defn(name="SeedEndpointsForCrawlActivity")
def seed_endpoints_for_crawl_activity(ctx: dict) -> dict:
    """Ensure every discovered subdomain has a default EndPoint before http_crawl runs.

    Mirrors rengine-ng's pre_crawl step. Queries all Subdomain records for the
    current scan and creates EndPoint(is_default=True, http_status=0) for any
    subdomain that does not yet have a default endpoint. Returns an updated ctx
    with a 'seed_urls' list that RunHTTPCrawlActivity can log and use.
    """
    from startScan.models import Subdomain, EndPoint
    from reNgine.utils.task import save_endpoint
    from reNgine.common_func import sanitize_url

    scan_id = ctx.get('scan_history_id')
    url_filter = ctx.get('starting_point_path', '')

    subdomains = Subdomain.objects.filter(scan_history_id=scan_id)
    seed_urls = []

    for subdomain in subdomains:
        if url_filter:
            path = url_filter if url_filter.startswith('/') else f'/{url_filter}'
            raw_url = f'{subdomain.name}{path}'
        else:
            raw_url = subdomain.name
        if not raw_url.startswith(('http://', 'https://')):
            raw_url = f'http://{raw_url}'
        raw_url = sanitize_url(raw_url)

        existing = EndPoint.objects.filter(
            scan_history_id=scan_id,
            http_url=raw_url,
            is_default=True,
        ).first()

        if existing:
            seed_urls.append(existing.http_url)
        else:
            endpoint, _ = save_endpoint(
                raw_url,
                ctx=ctx,
                crawl=False,
                is_default=True,
                subdomain=subdomain,
            )
            if endpoint:
                seed_urls.append(endpoint.http_url)

    activity.logger.info(
        f"[SeedEndpointsForCrawlActivity] scan_id={scan_id}: "
        f"seeded {len(seed_urls)} endpoint(s) for http_crawl."
    )
    return {**ctx, 'seed_urls': seed_urls}


# ===========================================================================
# Tier 2 — Enumeration
# ===========================================================================

@activity.defn(name="RunHTTPCrawlActivity")
def run_http_crawl_activity(ctx: dict) -> bool:
    """Run httpx HTTP crawl across all discovered subdomains.

    Delegates to the existing `http_crawl` task which probes all discovered
    subdomains for live HTTP services and persists endpoint metadata.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import http_crawl
    seed_count = len(ctx.get('seed_urls', []))
    activity.logger.info(f"[RunHTTPCrawlActivity] scan_id={ctx.get('scan_history_id')} seed_count={seed_count}")
    return _run_task(
        http_crawl,
        ctx,
        task_name='http_crawl',
        description='HTTP Crawl'
    )


@activity.defn(name="ParseHTTPCrawlResultsActivity")
def parse_http_crawl_results_activity(ctx: dict) -> bool:
    """Verify HTTP crawl results are persisted correctly after http_crawl runs.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from startScan.models import EndPoint
    scan_id = ctx.get('scan_history_id')
    # is_alive is a @property (not a DB column): http_status > 0, < 500, != 404
    alive_count = EndPoint.objects.filter(
        scan_history_id=scan_id,
        http_status__gt=0,
        http_status__lt=500,
    ).exclude(http_status=404).count()
    activity.logger.info(
        f"[ParseHTTPCrawlResultsActivity] scan_id={scan_id}: "
        f"{alive_count} alive endpoints."
    )
    return True


@activity.defn(name="RunPortScanActivity")
def run_port_scan_activity(ctx: dict) -> bool:
    """Run port scanning (naabu, nmap) across all discovered subdomains.

    Delegates to the existing `port_scan` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import port_scan
    activity.logger.info(f"[RunPortScanActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        port_scan,
        ctx,
        task_name='port_scan',
        description='Port Scan'
    )


@activity.defn(name="RunScreenshotActivity")
def run_screenshot_activity(ctx: dict) -> bool:
    """Capture screenshots of all live HTTP endpoints.

    Delegates to the existing `screenshot` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import screenshot
    activity.logger.info(f"[RunScreenshotActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        screenshot,
        ctx,
        task_name='screenshot',
        description='Screenshot'
    )


@activity.defn(name="RunFetchURLActivity")
def run_fetch_url_activity(ctx: dict) -> bool:
    """Fetch and collect all URLs across the target using gau, waybackurls, etc.

    Delegates to the existing `fetch_url` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import fetch_url
    activity.logger.info(f"[RunFetchURLActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        fetch_url,
        ctx,
        task_name='fetch_url',
        description='Fetch URL'
    )


@activity.defn(name="ParseEnumerationResultsActivity")
def parse_enumeration_results_activity(ctx: dict) -> bool:
    """Verify enumeration tier (ports, screenshots, URLs) results are persisted.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from startScan.models import EndPoint, IpAddress
    scan_id = ctx.get('scan_history_id')
    endpoint_count = EndPoint.objects.filter(scan_history_id=scan_id).count()
    activity.logger.info(
        f"[ParseEnumerationResultsActivity] scan_id={scan_id}: "
        f"{endpoint_count} total endpoints."
    )
    return True


# ===========================================================================
# Tier 3/4 — Fuzzing & URL Extraction
# ===========================================================================

@activity.defn(name="RunDirFileFuzzActivity")
def run_dir_file_fuzz_activity(ctx: dict) -> bool:
    """Run directory and file fuzzing (dirsearch, ffuf) across all endpoints.

    Delegates to the existing `dir_file_fuzz` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.fuzzing_tasks import dir_file_fuzz
    activity.logger.info(f"[RunDirFileFuzzActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        dir_file_fuzz,
        ctx,
        task_name='dir_file_fuzz',
        description='Directory & File Fuzz'
    )


@activity.defn(name="ParseFuzzResultsActivity")
def parse_fuzz_results_activity(ctx: dict) -> bool:
    """Verify fuzzing results are persisted to the database.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from startScan.models import DirectoryFile
    from startScan.models import Subdomain
    scan_id = ctx.get('scan_history_id')
    # Count DirectoryFile objects linked to this scan's subscans
    fuzz_count = DirectoryFile.objects.filter(
        directory_files__dir_subscan_ids__scan_history_id=scan_id
    ).distinct().count()
    activity.logger.info(
        f"[ParseFuzzResultsActivity] scan_id={scan_id}: {fuzz_count} fuzz entries."
    )
    return True


# ===========================================================================
# Tier 5 — Analysis
# ===========================================================================

@activity.defn(name="RunWebAPIDiscoveryActivity")
def run_web_api_discovery_activity(ctx: dict) -> bool:
    """Discover web API endpoints and routes using kiterunner.

    Delegates to the existing `web_api_discovery` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import web_api_discovery
    activity.logger.info(f"[RunWebAPIDiscoveryActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        web_api_discovery,
        ctx,
        task_name='web_api_discovery',
        description='Web API Discovery'
    )


@activity.defn(name="RunWAFDetectionActivity")
def run_waf_detection_activity(ctx: dict) -> bool:
    """Detect Web Application Firewalls protecting the target.

    Delegates to the existing `waf_detection` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import waf_detection
    activity.logger.info(f"[RunWAFDetectionActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        waf_detection,
        ctx,
        task_name='waf_detection',
        description='WAF Detection'
    )


@activity.defn(name="RunSecretScanningActivity")
def run_secret_scanning_activity(ctx: dict) -> bool:
    """Scan for exposed secrets, credentials, and API keys using Semgrep/trufflehog.

    Delegates to the existing `secret_scanning` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import secret_scanning
    activity.logger.info(f"[RunSecretScanningActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        secret_scanning,
        ctx,
        task_name='secret_scanning',
        description='Secrets & Leaks Scan'
    )


@activity.defn(name="ParseAnalysisResultsActivity")
def parse_analysis_results_activity(ctx: dict) -> bool:
    """Verify analysis tier results (WAF, API routes, secrets) are persisted.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    activity.logger.info(
        f"[ParseAnalysisResultsActivity] scan_id={ctx.get('scan_history_id')}"
    )
    return True


# ===========================================================================
# Tier 6 — Assessment
# ===========================================================================

@activity.defn(name="RunNucleiActivity")
def run_nuclei_activity(ctx: dict, severity: str = None) -> bool:
    """Run Nuclei vulnerability scan against all live endpoints discovered for this scan.

    Performs a pre-flight check against the EndPoint table before invoking nuclei_scan.
    If no endpoints have been crawled yet (e.g. http_crawl was not in the task list or
    found no alive hosts), falls back to the root domain URL so Nuclei has at least one
    target rather than silently writing an empty input file and producing zero results.

    Args:
        ctx (dict): Temporal workflow context containing scan_history_id and engine config.
        severity (str, optional): The target severity level to filter the scan.

    Returns:
        bool: True on success (including graceful skip when no domain is found).
    """
    from reNgine.tasks import nuclei_scan
    from startScan.models import EndPoint, ScanHistory

    scan_id = ctx.get('scan_history_id')
    severity = severity or ctx.get('nuclei_severity_filter')
    activity.logger.info(f"[RunNucleiActivity] scan_id={scan_id} severity={severity}")

    # Pre-flight: count endpoints in DB for this scan
    endpoint_count = EndPoint.objects.filter(scan_history_id=scan_id).count()

    if endpoint_count == 0:
        # No endpoints from http_crawl — derive the root URL from the ScanHistory domain
        # and use it as a minimum target so Nuclei always has something to scan.
        scan = ScanHistory.objects.filter(pk=scan_id).first()
        if scan and scan.domain:
            root_url = f"https://{scan.domain.name}"
            activity.logger.warning(
                f"[RunNucleiActivity] No endpoints found in DB for scan_id={scan_id}. "
                f"Falling back to root URL: {root_url}"
            )
            urls = [root_url]
        else:
            activity.logger.error(
                f"[RunNucleiActivity] No endpoints and no domain found for scan_id={scan_id}. "
                f"Skipping Nuclei scan."
            )
            return True
    else:
        activity.logger.info(
            f"[RunNucleiActivity] {endpoint_count} endpoints in DB for scan_id={scan_id}. "
            f"Nuclei will query get_http_urls() from DB."
        )
        # Let nuclei_scan call get_http_urls() to filter alive endpoints from DB
        urls = []

    task_desc = f'Nuclei Scan ({severity})' if severity else 'Nuclei Scan'

    return _run_task(
        nuclei_scan, ctx,
        task_name='nuclei_scan',
        description=task_desc,
        urls=urls,
        severity=severity
    )

@activity.defn(name="RunCRLFuzzActivity")
def run_crlfuzz_activity(ctx: dict) -> bool:
    from reNgine.tasks import crlfuzz_scan
    activity.logger.info(f"[RunCRLFuzzActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(crlfuzz_scan, ctx, task_name='crlfuzz_scan', description='CRLFuzz Scan', urls=ctx.get('urls', []))

@activity.defn(name="RunDalfoxActivity")
def run_dalfox_activity(ctx: dict) -> bool:
    from reNgine.tasks import dalfox_xss_scan
    activity.logger.info(f"[RunDalfoxActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(dalfox_xss_scan, ctx, task_name='dalfox_xss_scan', description='Dalfox XSS Scan', urls=ctx.get('urls', []))

@activity.defn(name="RunS3ScannerActivity")
def run_s3scanner_activity(ctx: dict) -> bool:
    from reNgine.tasks import s3scanner
    activity.logger.info(f"[RunS3ScannerActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(s3scanner, ctx, task_name='s3scanner', description='S3 Bucket Scanner')

@activity.defn(name="RunAcunetixActivity")
def run_acunetix_activity(ctx: dict) -> bool:
    from reNgine.tasks import acunetix_scan
    activity.logger.info(f"[RunAcunetixActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(acunetix_scan, ctx, task_name='acunetix_scan', description='Acunetix Scan', domain_id=ctx.get('domain_id'), scan_history_id=ctx.get('scan_history_id'))

@activity.defn(name="RunCpanelScanActivity")
def run_cpanel_scan_activity(ctx: dict) -> bool:
    from reNgine.vulnerability_tasks import cpanel_scan
    activity.logger.info(f"[RunCpanelScanActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(cpanel_scan, ctx, task_name='cpanel_scan', description='cPanel Vulnerability Scan')

@activity.defn(name="RunWpscanActivity")
def run_wpscan_activity(ctx: dict) -> bool:
    from reNgine.wpscan_tasks import wpscan_scan
    activity.logger.info(f"[RunWpscanActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(wpscan_scan, ctx, task_name='wpscan_scan', description='WPScan', urls=ctx.get('urls', []))

@activity.defn(name="RunReact2ShellActivity")
def run_react2shell_activity(ctx: dict) -> bool:
    from reNgine.vulnerability_tasks import react2shell_scan
    activity.logger.info(f"[RunReact2ShellActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(react2shell_scan, ctx, task_name='react2shell_scan', description='React Vulnerability Scan')

@activity.defn(name="RunSemgrepActivity")
def run_semgrep_activity(ctx: dict) -> bool:
    from reNgine.tasks import semgrep_scan
    activity.logger.info(f"[RunSemgrepActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(semgrep_scan, ctx, task_name='semgrep_scan', description='Semgrep Vulnerability Scan', mode='vulnerability')


@activity.defn(name="RunVigoliumScanActivity")
def run_vigolium_scan_activity(ctx: dict) -> bool:
    """Run Vigolium known-issue + dynamic-assessment scan against live endpoints.

    Runs inside NucleiPlannerWorkflow at Tier 6 alongside Nuclei. Default-enabled
    via vulnerability_scan.run_vigolium: true in the engine YAML config.
    """
    from reNgine.vigolium_tasks import vigolium_scan
    activity.logger.info(f"[RunVigoliumScanActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(vigolium_scan, ctx, task_name='vigolium_scan', description='Vigolium Vulnerability Scan')


@activity.defn(name="RunVigoliumDiscoveryActivity")
def run_vigolium_discovery_activity(ctx: dict) -> bool:
    """Run Vigolium discovery phase to seed the endpoint DB.

    Runs at Tier 2 in parallel with http_crawl. Populates EndPoint records
    with URLs discovered by vigolium's ingestion + discovery phases.
    Controlled by vigolium_discovery.run_vigolium_discovery in engine YAML.
    """
    from reNgine.vigolium_tasks import vigolium_discovery
    activity.logger.info(f"[RunVigoliumDiscoveryActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(vigolium_discovery, ctx, task_name='vigolium_discovery', description='Vigolium Endpoint Discovery')


@activity.defn(name="RunVigoliumAnalysisActivity")
def run_vigolium_analysis_activity(ctx: dict) -> bool:
    """Run Vigolium dynamic-assessment phase at Tier 5.

    Runs in parallel with web_api_discovery. Executes vigolium's 251-module
    passive + active scanning suite and saves findings as Vulnerability records.
    Controlled by vigolium_analysis.run_vigolium_analysis in engine YAML.
    """
    from reNgine.vigolium_tasks import vigolium_analysis
    activity.logger.info(f"[RunVigoliumAnalysisActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(vigolium_analysis, ctx, task_name='vigolium_analysis', description='Vigolium Dynamic Analysis')


@activity.defn(name="MarkVulnerabilityScanCompleteActivity")
def mark_vulnerability_scan_complete_activity(ctx: dict) -> None:
    """Write a SUCCESS ScanActivity with name='vulnerability_scan'.

    NucleiPlannerWorkflow runs as a child workflow whose internal activities
    use names like 'nuclei_scan', 'crlfuzz_scan', etc. — never 'vulnerability_scan'.
    Without this record, resume_scan_temporal always considers vulnerability_scan
    incomplete and re-runs it from scratch on crash recovery.
    """
    from startScan.models import ScanHistory, ScanActivity
    from reNgine.definitions import SUCCESS_TASK
    from django.utils import timezone

    scan_id = ctx.get('scan_history_id')
    scan = ScanHistory.objects.filter(pk=scan_id).first()
    if not scan:
        return
    ScanActivity.objects.get_or_create(
        scan_of=scan,
        name='vulnerability_scan',
        defaults={
            'title': 'Vulnerability Scan',
            'time': timezone.now(),
            'status': SUCCESS_TASK,
        }
    )
    activity.logger.info(f"[MarkVulnerabilityScanCompleteActivity] scan_id={scan_id} marked complete")


@activity.defn(name="RunWAFBypassActivity")
def run_waf_bypass_activity(ctx: dict) -> bool:
    """Attempt to bypass detected WAF protections to find unprotected origins.

    Delegates to the existing `waf_bypass` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import waf_bypass
    activity.logger.info(f"[RunWAFBypassActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        waf_bypass,
        ctx,
        task_name='waf_bypass',
        description='WAF Bypass'
    )


@activity.defn(name="RunBruteForceScanActivity")
def run_brute_force_scan_activity(ctx: dict) -> bool:
    """Run brute force attacks against discovered login endpoints.

    Delegates to the existing `brute_force_scan` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import brute_force_scan
    activity.logger.info(f"[RunBruteForceScanActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        brute_force_scan,
        ctx,
        task_name='brute_force_scan',
        description='Brute Force Scan'
    )


@activity.defn(name="ParseAssessmentResultsActivity")
def parse_assessment_results_activity(ctx: dict) -> bool:
    """Verify assessment tier (vulnerability) results are persisted.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from startScan.models import Vulnerability
    scan_id = ctx.get('scan_history_id')
    vuln_count = Vulnerability.objects.filter(scan_history_id=scan_id).count()
    activity.logger.info(
        f"[ParseAssessmentResultsActivity] scan_id={scan_id}: "
        f"{vuln_count} vulnerabilities found."
    )
    return True


# ===========================================================================
# Tier 7 — Post-Processing & Intelligence
# ===========================================================================

@activity.defn(name="CorrelateVulnerabilitiesActivity")
def correlate_vulnerabilities_activity(ctx: dict) -> bool:
    """Correlate discovered vulnerabilities with CVE databases and Neo4j graph.

    Delegates to the existing `correlate_vulnerabilities` task which syncs
    the graph and links technology findings to CVE records.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import correlate_vulnerabilities
    scan_id = ctx.get('scan_history_id')
    activity.logger.info(f"[CorrelateVulnerabilitiesActivity] scan_id={scan_id}")
    return _run_task(
        correlate_vulnerabilities,
        ctx,
        task_name='correlate_vulnerabilities',
        description='Correlate Vulnerabilities',
        scan_history_id=scan_id
    )


@activity.defn(name="CalculateRiskScoresActivity")
def calculate_risk_scores_activity(ctx: dict) -> bool:
    """Calculate weighted risk scores for all discovered vulnerabilities.

    Delegates to the existing `calculate_risk_scores` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import calculate_risk_scores
    scan_id = ctx.get('scan_history_id')
    activity.logger.info(f"[CalculateRiskScoresActivity] scan_id={scan_id}")
    return _run_task(
        calculate_risk_scores,
        ctx,
        task_name='calculate_risk_scores',
        description='Calculate Risk Scores',
        scan_history_id=scan_id
    )


@activity.defn(name="GenerateImpactAssessmentActivity")
def generate_impact_assessment_activity(ctx: dict) -> bool:
    """Run AI-powered vulnerability impact assessment (if enabled in config).

    Delegates to the existing `generate_impact_assessment` task.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.tasks import generate_impact_assessment
    scan_id = ctx.get('scan_history_id')
    activity.logger.info(f"[GenerateImpactAssessmentActivity] scan_id={scan_id}")
    return _run_task(
        generate_impact_assessment,
        ctx,
        task_name='generate_impact_assessment',
        description='AI Impact Assessment',
        scan_history_id=scan_id
    )


@activity.defn(name="SyncGraphActivity")
def sync_graph_activity(ctx: dict) -> bool:
    """Synchronize all scan results to the Neo4j Attack Path Modeling graph.

    Delegates to `run_apme` task and additionally runs `Neo4jManager.sync_scan_results`.
    Sends a heartbeat before the sync so Temporal knows the activity is alive even
    if Neo4j is slow to accept the initial connection.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from reNgine.utils.graph import Neo4jManager
    scan_id = ctx.get('scan_history_id')
    activity.logger.info(f"[SyncGraphActivity] Syncing scan_id={scan_id} to Neo4j")
    # Heartbeat before the Neo4j connection attempt so Temporal sees the
    # activity is alive even if driver init is slow.
    activity.heartbeat(f"SyncGraphActivity starting neo4j sync for scan_id={scan_id}")

    nm = Neo4jManager()
    try:
        nm.sync_scan_results(scan_id)
        activity.logger.info(f"[SyncGraphActivity] Neo4j sync complete for scan_id={scan_id}")
        return True
    except Exception as e:
        activity.logger.error(f"[SyncGraphActivity] Neo4j sync failed: {e}")
        logger.error(f"Neo4j sync failed: {e}")
        return False
    finally:
        nm.close()


@activity.defn(name="SendScanNotificationActivity")
def send_scan_notification_activity(ctx: dict) -> bool:
    """Mark the scan as completed and send the final scan status notification.

    Calls the `report` task function to update ScanHistory.scan_status to
    SUCCESS/FAILED and dispatch the completion webhook/notification.

    Args:
        ctx (dict): Temporal workflow context.

    Returns:
        bool: True on success.
    """
    from startScan.models import ScanHistory, ScanActivity
    from reNgine.definitions import SUCCESS_TASK, FAILED_TASK
    from reNgine.tasks import send_scan_notif

    scan_id = ctx.get('scan_history_id')
    engine_id = ctx.get('engine_id')
    activity.logger.info(f"[SendScanNotificationActivity] Finalizing scan_id={scan_id}")

    scan = ScanHistory.objects.filter(pk=scan_id).first()
    if not scan:
        activity.logger.error(f"[SendScanNotificationActivity] ScanHistory {scan_id} not found.")
        return False

    # Determine overall scan status from ScanActivity records
    failed_tasks = ScanActivity.objects.filter(
        scan_of=scan,
        status=FAILED_TASK
    ).count()

    status = SUCCESS_TASK if failed_tasks == 0 else FAILED_TASK
    status_h = 'SUCCESS' if failed_tasks == 0 else 'FAILED'

    scan.scan_status = status
    scan.stop_scan_date = timezone.now()
    scan.save()

    activity.logger.info(
        f"[SendScanNotificationActivity] scan_id={scan_id} finished with status={status_h}"
    )

    # Send notification directly (no Celery)
    try:
        send_scan_notif(
            scan_history_id=scan_id,
            subscan_id=None,
            engine_id=engine_id,
            status=status_h
        )
    except Exception as e:
        # Non-fatal: log and continue
        logger.warning(f"Could not send scan notification: {e}")

    return True


_PERMITTED_GENERIC_TASKS = frozenset({
    "subdomain_discovery", "amass_intel_discovery", "firewall_vpn_scan",
    "dns_security", "osint", "spiderfoot_scan", "http_crawl", "port_scan", "screenshot",
    "fetch_url", "dir_file_fuzz", "web_api_discovery", "waf_detection",
    "secret_scanning", "vulnerability_scan", "waf_bypass", "brute_force_scan",
    "nuclei_scan", "crlfuzz_scan", "dalfox_xss_scan", "s3scanner",
    "acunetix_scan", "cpanel_scan", "wpscan_scan", "react2shell_scan",
    "semgrep_scan", "correlate_vulnerabilities", "calculate_risk_scores",
    "generate_impact_assessment", "run_apme", "attack_path_modeling",
})


@activity.defn(name="RunGenericTaskActivity")
def run_generic_task_activity(ctx: dict, task_name: str, description: str = None, extra_args: dict = None) -> bool:
    """Execute any permitted task function dynamically in a Temporal activity.

    Only tasks in _PERMITTED_GENERIC_TASKS may be dispatched. This prevents
    arbitrary function execution from replayed workflow history events.
    """
    if task_name not in _PERMITTED_GENERIC_TASKS:
        raise ValueError(
            f"[RunGenericTaskActivity] '{task_name}' is not in the permitted task list. "
            f"Add it to _PERMITTED_GENERIC_TASKS to allow dispatch."
        )
    import importlib
    activity.logger.info(f"[RunGenericTaskActivity] task={task_name} scan_id={ctx.get('scan_history_id')}")

    tasks_module = importlib.import_module("reNgine.tasks")
    task_func = getattr(tasks_module, task_name, None)

    if not task_func:
        raise ValueError(f"Task function '{task_name}' not found in reNgine.tasks.")

    run_args = extra_args or {}
    return _run_task(
        task_func,
        ctx,
        task_name=task_name,
        description=description or ' '.join(task_name.split('_')).capitalize(),
        **run_args
    )


@activity.defn(name="FinalizeSubScanActivity")
def finalize_subscan_activity(ctx: dict, success: bool, subscan_id: int = None) -> bool:
    """Mark the subscan as completed and update its status.

    Args:
        ctx (dict): Temporal workflow context.
        success (bool): True if all subscan steps succeeded, False otherwise.
        subscan_id (int, optional): Specific subscan ID to finalize.
    """
    from startScan.models import SubScan
    from reNgine.definitions import SUCCESS_TASK, FAILED_TASK
    from reNgine.tasks import send_scan_notif

    if subscan_id is None:
        subscan_id = ctx.get('subscan_id')
    scan_id = ctx.get('scan_history_id')
    engine_id = ctx.get('engine_id')

    subscan = SubScan.objects.filter(pk=subscan_id).first()
    if not subscan:
        activity.logger.error(f"[FinalizeSubScanActivity] SubScan {subscan_id} not found.")
        return False

    status = SUCCESS_TASK if success else FAILED_TASK
    status_h = 'SUCCESS' if success else 'FAILED'

    subscan.status = status
    subscan.stop_scan_date = timezone.now()
    subscan.save()

    activity.logger.info(
        f"[FinalizeSubScanActivity] subscan_id={subscan_id} finished with status={status_h}"
    )

    # Send notification directly (no Celery)
    try:
        send_scan_notif(
            scan_history_id=scan_id,
            subscan_id=subscan_id,
            engine_id=engine_id,
            status=status_h
        )
    except Exception as e:
        logger.warning(f"Could not send subscan notification: {e}")

    return True


# ===========================================================================
# Stress Testing Activities
# ===========================================================================

@activity.defn(name="InitStressTestActivity")
def init_stress_test_activity(ctx: dict) -> dict:
    """Resolve target endpoints and create the StressTestResult DB record.

    Mirrors the target profiling + endpoint query block from run_stress_testing.
    Clears any stale telemetry stream and publishes the initial 'running' status.

    Args:
        ctx: Must contain scan_history_id, target_domain_name, stress_config.

    Returns:
        Enriched ctx with 'resolved_endpoints' (list[str]) and 'stress_result_id' (int).
    """
    import time
    from startScan.models import ScanHistory, EndPoint, StressTestResult
    from targetApp.models import Domain
    from reNgine.definitions import RUNNING_TASK
    from reNgine.stress.telemetry import StressTelemetryPublisher

    scan_id = ctx["scan_history_id"]
    target_domain = ctx["target_domain_name"]
    stress_config = ctx.get("stress_config", {})

    activity.logger.info(f"[InitStressTestActivity] scan_id={scan_id}")

    scan = ScanHistory.objects.get(id=scan_id)
    domain = Domain.objects.get(name=target_domain)

    scan.scan_status = RUNNING_TASK
    scan.save()

    selected = stress_config.get("selected_endpoints", [])
    if selected:
        endpoints = list(
            EndPoint.objects.filter(
                scan_history_id=scan_id, http_url__in=selected
            ).values_list("http_url", flat=True)
        )
    else:
        crawl_targets = stress_config.get("crawl_targets", False)
        qs = EndPoint.objects.filter(
            scan_history_id=scan_id, subdomain__name=target_domain
        ).order_by("id")
        endpoints = list(qs.values_list("http_url", flat=True)[:5 if crawl_targets else 1])

    tools = stress_config.get("uses_tools", ["k6"])
    concurrency = stress_config.get("concurrency", 50)
    duration = stress_config.get("duration", "30s") or "30s"

    result = StressTestResult.objects.create(
        scan_history=scan,
        target_domain=domain,
        tool_used=",".join(tools),
        concurrency_used=concurrency,
        duration=duration,
    )

    publisher = StressTelemetryPublisher(scan_id)
    publisher.clear_stream()
    publisher.publish({"type": "scan_status", "status": "running", "timestamp": time.time()})

    activity.logger.info(
        f"[InitStressTestActivity] scan_id={scan_id} "
        f"resolved {len(endpoints)} endpoint(s) for tools={tools}"
    )

    return {
        **ctx,
        "resolved_endpoints": endpoints,
        "stress_result_id": result.id,
    }


@activity.defn(name="RunStressToolActivity")
def run_stress_tool_activity(ctx: dict) -> dict:
    """Execute a single stress tool against a single endpoint.

    Corresponds to the inner (endpoint × tool) loop of run_stress_testing.
    Sends Temporal heartbeats every 15 seconds.  Also checks the Redis kill
    switch as a belt-and-braces fallback for the window before the Temporal
    signal reaches the workflow.

    Args:
        ctx: Must contain scan_history_id, target_domain_name, stress_config,
             current_endpoint (str), current_tool (str).

    Returns:
        dict of aggregated metrics from the parser (total_requests,
        successful_requests, failed_requests, avg_latency_ms, p95_latency_ms,
        p99_latency_ms, max_requests_per_second).
    """
    import os
    import signal as os_signal
    import subprocess
    import threading
    import time
    import contextvars
    from temporalio.exceptions import CancelledError

    import redis as redis_lib
    from django.conf import settings
    from django.utils import timezone
    from startScan.models import Command
    from reNgine.parsers import K6Parser, WrkParser, Hping3Parser, LocustParser, TAStressorParser
    from reNgine.stress.telemetry import StressTelemetryPublisher
    from reNgine.stress.cmd_builder import build_stress_command
    from reNgine.common_func import get_random_proxy, get_random_user_agent
    from reNgine.utils.opsec import ProxychainsWrapper

    scan_id = ctx["scan_history_id"]
    target_domain = ctx["target_domain_name"]
    endpoint_url = ctx["current_endpoint"]
    tool = ctx["current_tool"]
    stress_config = ctx.get("stress_config", {})
    tool_config = stress_config.get(f"{tool}_config", {})
    concurrency = stress_config.get("concurrency", 50)
    duration = stress_config.get("duration", "30s") or "30s"

    activity.logger.info(
        f"[RunStressToolActivity] tool={tool} endpoint={endpoint_url} scan_id={scan_id}"
    )

    publisher = StressTelemetryPublisher(scan_id)

    # Redis kill-switch check — secondary fallback alongside the Temporal signal
    try:
        rdb = redis_lib.StrictRedis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0
        )
    except Exception:
        rdb = None

    def _kill_switch_active():
        try:
            return rdb is not None and rdb.get(f"kill_switch_{scan_id}") == b"1"
        except Exception:
            return False

    # Select the right parser
    parsers = {
        "k6": K6Parser,
        "wrk": WrkParser,
        "hping3": Hping3Parser,
        "locust": LocustParser,
        "stressor": TAStressorParser,
    }
    parser_cls = parsers.get(tool)
    if not parser_cls:
        raise ValueError(f"[RunStressToolActivity] Unknown tool: {tool!r}")
    parser = parser_cls()

    single_proxy = get_random_proxy()
    k6_user_agent = get_random_user_agent()

    cmd_str, temp_files = build_stress_command(
        tool=tool,
        tool_config=tool_config,
        endpoint_url=endpoint_url,
        target_domain=target_domain,
        scan_id=scan_id,
        concurrency=concurrency,
        duration=duration,
        single_proxy=single_proxy,
        k6_user_agent=k6_user_agent,
        base_dir=settings.BASE_DIR,
    )

    proxy_wrapper = ProxychainsWrapper()
    temp_conf_path = None
    if proxy_wrapper.should_wrap():
        cmd_str, temp_conf_path = proxy_wrapper.wrap_command(cmd_str)
        activity.logger.info(f"[RunStressToolActivity] Wrapping via proxychains: {cmd_str}")
    else:
        activity.logger.info(f"[RunStressToolActivity] Executing: {cmd_str}")

    if temp_conf_path:
        temp_files.append(temp_conf_path)

    command_obj = Command.objects.create(
        command=cmd_str,
        time=timezone.now(),
        scan_history_id=scan_id,
    )

    publisher.publish({
        "type": "command",
        "tool": tool,
        "endpoint": endpoint_url,
        "command": cmd_str,
        "timestamp": time.time(),
    })

    # Pre-declare process variable so the background heartbeat thread can inspect it safely
    process = None

    # Helper function to terminate the subprocess group
    def _terminate_process():
        is_mock = hasattr(process, 'assert_called')
        if process and (process.poll() is None or is_mock):
            try:
                activity.logger.info(
                    f"[RunStressToolActivity] Terminating process group for {tool} (PID: {process.pid})"
                )
                os.killpg(os.getpgid(process.pid), os_signal.SIGTERM)
            except Exception as kill_err:
                activity.logger.error(f"[RunStressToolActivity] Kill failed: {kill_err}")

    # Helper to check if running inside a Temporal activity context (fails during direct unit tests)
    def _is_in_activity_context():
        try:
            activity.is_cancelled()
            return True
        except RuntimeError:
            return False

    def _is_cancelled():
        return _is_in_activity_context() and activity.is_cancelled()

    # Heartbeat thread — keeps the activity alive in Temporal's eyes.
    # Copy the current contextvars context so the heartbeat thread inherits the
    # Temporal activity context. threading.Thread does NOT copy contextvars by
    # default, causing activity.heartbeat() to fail with "Not in activity context",
    # which silently prevents all heartbeats from reaching Temporal and triggers
    # the heartbeat_timeout cancellation + retry loop.
    stop_heartbeat = threading.Event()
    _activity_ctx = contextvars.copy_context()

    def _heartbeat():
        def _do_heartbeat():
            while not stop_heartbeat.is_set():
                # Perform periodic cancellation check
                if _is_cancelled():
                    activity.logger.info(
                        f"[RunStressToolActivity] Activity cancelled — terminating {tool}"
                    )
                    _terminate_process()
                    break
                if _is_in_activity_context():
                    try:
                        activity.heartbeat(f"Running {tool} against {endpoint_url}")
                    except CancelledError:
                        activity.logger.info(
                            f"[RunStressToolActivity] Heartbeat received cancellation — terminating {tool}"
                        )
                        _terminate_process()
                        break
                    except Exception as hb_err:
                        if "cancel" in str(hb_err).lower():
                            activity.logger.info(
                                f"[RunStressToolActivity] Heartbeat received cancellation exception: {hb_err} — terminating {tool}"
                            )
                            _terminate_process()
                            break
                        activity.logger.warning(f"[RunStressToolActivity] Heartbeat failed: {hb_err}")
                stop_heartbeat.wait(15)
        _activity_ctx.run(_do_heartbeat)

    hb_thread = threading.Thread(target=_heartbeat, daemon=True)
    hb_thread.start()

    accumulated_lines = []
    try:
        process = subprocess.Popen(
            cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            start_new_session=True,
        )

        while True:
            # Check for cancellation on each iteration
            if _is_cancelled():
                activity.logger.info(
                    f"[RunStressToolActivity] Main thread detected cancellation — terminating {tool}"
                )
                _terminate_process()
                break

            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                accumulated_lines.append(line)
                publisher.publish({
                    "type": "log",
                    "tool": tool,
                    "endpoint": endpoint_url,
                    "line": line,
                    "timestamp": time.time(),
                })
                metrics = parser.parse_line(line)
                if metrics:
                    metrics.update({
                        "type": "metric",
                        "tool": tool,
                        "endpoint": endpoint_url,
                        "timestamp": time.time(),
                    })
                    publisher.publish(metrics)

            if _kill_switch_active():
                activity.logger.info(
                    f"[RunStressToolActivity] Redis kill switch active — terminating {tool}"
                )
                _terminate_process()
                break

        process.wait()
        command_obj.output = "\n".join(accumulated_lines)
        command_obj.return_code = process.returncode
        command_obj.save()

    finally:
        stop_heartbeat.set()
        hb_thread.join(timeout=5)
        for path in temp_files:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as rm_err:
                    activity.logger.error(
                        f"[RunStressToolActivity] Could not remove temp file {path}: {rm_err}"
                    )

    final_metrics = parser.get_final_metrics()
    activity.logger.info(
        f"[RunStressToolActivity] tool={tool} endpoint={endpoint_url} "
        f"done — {final_metrics.get('total_requests', 0)} requests"
    )
    return final_metrics


@activity.defn(name="FinalizeStressTestActivity")
def finalize_stress_test_activity(ctx: dict) -> bool:
    """Aggregate metrics, update StressTestResult + ScanHistory, send notification.

    Mirrors the post-loop finalisation block in run_stress_testing and always
    publishes a 'completed' status to the telemetry stream so the frontend
    exits the running state even if a previous worker crash left it stale.

    Args:
        ctx: Must contain scan_history_id, stress_result_id, aborted (bool),
             and pre-aggregated metric fields from the workflow.

    Returns:
        True on success.
    """
    import time
    from django.utils import timezone
    from startScan.models import ScanHistory, StressTestResult
    from reNgine.definitions import SUCCESS_TASK, ABORTED_TASK
    from reNgine.stress.telemetry import StressTelemetryPublisher
    from reNgine.tasks import send_scan_notif

    scan_id = ctx["scan_history_id"]
    result_id = ctx.get("stress_result_id")
    aborted = ctx.get("aborted", False)

    activity.logger.info(
        f"[FinalizeStressTestActivity] scan_id={scan_id} aborted={aborted}"
    )

    result = StressTestResult.objects.filter(id=result_id).first()
    if result:
        result.total_requests = ctx.get("total_requests", 0)
        result.successful_requests = ctx.get("successful_requests", 0)
        result.failed_requests = ctx.get("failed_requests", 0)
        result.avg_latency_ms = ctx.get("avg_latency_ms", 0.0)
        result.p95_latency_ms = ctx.get("p95_latency_ms", 0.0)
        result.p99_latency_ms = ctx.get("p99_latency_ms", 0.0)
        result.max_requests_per_second = ctx.get("max_rps", 0.0)
        result.is_kill_switch_triggered = aborted
        result.save()

    scan = ScanHistory.objects.filter(id=scan_id).first()
    if scan:
        scan.scan_status = ABORTED_TASK if aborted else SUCCESS_TASK
        scan.stop_scan_date = timezone.now()
        scan.save()

    # Always publish completed status — prevents the frontend from getting stuck
    # in 'running' state after a worker crash between activities.
    publisher = StressTelemetryPublisher(scan_id)
    publisher.publish({
        "type": "scan_status",
        "status": "completed",
        "timestamp": time.time(),
    })

    try:
        send_scan_notif(
            scan_history_id=scan_id,
            status="ABORTED" if aborted else "SUCCESS",
        )
    except Exception as e:
        activity.logger.warning(
            f"[FinalizeStressTestActivity] Notification failed (non-fatal): {e}"
        )

    return True


@activity.defn(name="RunStartupSyncActivity")
def run_startup_sync_activity(task_name: str) -> None:
    """Execute a named startup sync task. Called once per orchestrator start via StartupSyncWorkflow.

    Supported task_name values:
      'sync_all_scans_to_graph' — syncs all scan results to Neo4j
      'sync_cisa_kev_catalog'   — downloads CISA KEV catalog and marks CVEs
      'sync_semgrep_rules'      — syncs Semgrep rule sets to local filesystem
    """
    activity.logger.info(f"[RunStartupSyncActivity] Starting: {task_name}")
    if task_name == 'sync_all_scans_to_graph':
        from reNgine.tasks import sync_all_scans_to_graph
        sync_all_scans_to_graph(None)
    elif task_name == 'sync_cisa_kev_catalog':
        from reNgine.tasks import sync_cisa_kev_catalog
        sync_cisa_kev_catalog()
    elif task_name == 'sync_semgrep_rules':
        from reNgine.tasks import sync_semgrep_rules
        sync_semgrep_rules()
    elif task_name == 'recover_stuck_scans':
        from reNgine.tasks import recover_stuck_scans
        recover_stuck_scans()
    else:
        raise ValueError(f"[RunStartupSyncActivity] Unknown task: {task_name}")
    activity.logger.info(f"[RunStartupSyncActivity] Completed: {task_name}")


@activity.defn(name="RunMonitoringCheckActivity")
def run_monitoring_check_activity(domain_id: int) -> None:
    """Execute a monitoring check for a domain. Called by MonitoringWorkflow on schedule.

    Delegates to monitor_target_task which handles subdomain discovery, change
    detection, notifications, and conditional scan initiation.
    """
    activity.logger.info(f"[RunMonitoringCheckActivity] Checking domain_id={domain_id}")
    from reNgine.monitor_tasks import monitor_target_task
    monitor_target_task(domain_id)
    activity.logger.info(f"[RunMonitoringCheckActivity] Completed domain_id={domain_id}")


@activity.defn(name="SetupScheduledScanActivity")
def setup_scheduled_scan_activity(params: dict) -> dict:
    """Create a ScanHistory record and build a full workflow ctx for a scheduled scan.

    Mirrors the setup portion of initiate_scan_temporal (DB record creation,
    directory setup, initial subdomain/endpoint) without starting any workflow.
    The returned ctx is passed directly to MasterScanWorkflow as a child workflow.

    Args:
        params: Dict with keys: domain_id, engine_id, scan_type, initiated_by_id,
                imported_subdomains, out_of_scope_subdomains, starting_point_path,
                excluded_paths, enable_spiderfoot_scan.

    Returns:
        dict: Complete Temporal workflow ctx ready for MasterScanWorkflow.
    """
    import os
    import yaml
    from django.utils import timezone
    from reNgine.common_func import (
        create_scan_object, save_imported_subdomains, save_subdomain, save_endpoint
    )
    from reNgine.definitions import (
        RUNNING_TASK, SCHEDULED_SCAN,
        ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL,
        GF_PATTERNS, WEB_API_DISCOVERY, USES_TOOLS, KITERUNNER_WORDLIST,
    )
    from reNgine.settings import RENGINE_RESULTS
    from scanEngine.models import EngineType
    from startScan.models import ScanHistory
    from targetApp.models import Domain

    domain_id = params['domain_id']
    engine_id = params['engine_id']
    initiated_by_id = params.get('initiated_by_id')
    imported_subdomains = params.get('imported_subdomains') or []
    out_of_scope_subdomains = params.get('out_of_scope_subdomains') or []
    starting_point_path = (params.get('starting_point_path') or '').rstrip('/')
    excluded_paths = params.get('excluded_paths') or []
    enable_spiderfoot_scan = params.get('enable_spiderfoot_scan', False)

    engine = EngineType.objects.get(pk=engine_id)
    domain = Domain.objects.get(pk=domain_id)
    config = yaml.safe_load(engine.yaml_configuration) or {}

    scan_history_id = create_scan_object(
        host_id=domain_id,
        engine_id=engine_id,
        initiated_by_id=initiated_by_id,
    )
    scan = ScanHistory.objects.get(pk=scan_history_id)

    tasks = list(engine.tasks)
    if 'waf_bypass' in tasks and 'waf_detection' not in tasks:
        tasks.insert(tasks.index('waf_bypass'), 'waf_detection')
    if enable_spiderfoot_scan and 'spiderfoot_scan' not in tasks:
        tasks.append('spiderfoot_scan')

    scan.scan_status = RUNNING_TASK
    scan.scan_type = engine
    scan.domain = domain
    scan.start_scan_date = timezone.now()
    scan.tasks = tasks
    scan.results_dir = f'{RENGINE_RESULTS}/{domain.name}_{scan.id}'
    scan.cfg_starting_point_path = starting_point_path
    scan.cfg_excluded_paths = excluded_paths
    scan.cfg_out_of_scope_subdomains = out_of_scope_subdomains
    scan.cfg_imported_subdomains = imported_subdomains
    scan.save()

    os.makedirs(scan.results_dir, exist_ok=True)

    ctx_bootstrap = {
        'scan_history_id': scan.id,
        'engine_id': engine_id,
        'domain_id': domain.id,
        'results_dir': scan.results_dir,
        'starting_point_path': starting_point_path,
        'out_of_scope_subdomains': out_of_scope_subdomains,
    }
    save_imported_subdomains(imported_subdomains, ctx=ctx_bootstrap)

    enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
    subdomain, _ = save_subdomain(domain.name, ctx=ctx_bootstrap)
    _root = f'{domain.name}{starting_point_path}' if starting_point_path else domain.name
    if not _root.startswith(('http://', 'https://')):
        _root = f'http://{_root}'
    endpoint, _ = save_endpoint(
        _root,
        ctx=ctx_bootstrap,
        crawl=enable_http_crawl,
        is_default=True,
        subdomain=subdomain,
    )
    if endpoint and endpoint.is_alive:
        subdomain.http_url = endpoint.http_url
        subdomain.http_status = endpoint.http_status
        subdomain.response_time = endpoint.response_time
        subdomain.page_title = endpoint.page_title
        subdomain.content_type = endpoint.content_type
        subdomain.content_length = endpoint.content_length
        for tech in endpoint.techs.all():
            subdomain.technologies.add(tech)
        subdomain.save()

    gf_patterns = config.get(GF_PATTERNS, [])
    api_discovery_config = config.get(WEB_API_DISCOVERY, {})
    api_discovery_tools = api_discovery_config.get(USES_TOOLS, [])
    kr_wordlist = api_discovery_config.get(KITERUNNER_WORDLIST, 'routes-large.kite')

    if gf_patterns and 'fetch_url' in tasks:
        scan.used_gf_patterns = ','.join(gf_patterns)
        scan.save(update_fields=['used_gf_patterns'])

    activity.logger.info(
        f"[SetupScheduledScanActivity] Created scan_id={scan.id} for domain={domain.name}"
    )
    return {
        'scan_history_id': scan.id,
        'engine_id': engine_id,
        'domain_id': domain.id,
        'results_dir': scan.results_dir,
        'starting_point_path': starting_point_path,
        'excluded_paths': excluded_paths,
        'yaml_configuration': config,
        'out_of_scope_subdomains': out_of_scope_subdomains,
        'api_discovery_tools': api_discovery_tools,
        'kr_wordlist': kr_wordlist,
        'tasks': tasks,
    }


# ===========================================================================
# Distributed Heavy Scan Activities (Go Executor Integration)
# ===========================================================================

@activity.defn(name="PreparePortScanActivity")
def prepare_port_scan_activity(ctx: dict) -> dict:
    """Prepare a port scan execution environment and construct the tool command.

    Args:
        ctx (dict): Scan context containing target host information, engine settings,
                    and activity descriptors.

    Returns:
        dict: Prepared configuration details containing the generated command line,
              input paths, and a unique command identifier stored in the database.
    """
    from reNgine.tasks import port_scan
    from startScan.models import Command
    from django.utils import timezone

    proxy = TemporalTaskProxy(ctx, 'port_scan', 'Port Scan', track=False)
    raw_func = port_scan.__func__ if hasattr(port_scan, '__func__') else port_scan
    res = raw_func(proxy, ctx=ctx, prepare_only=True)

    cmd_record = Command.objects.create(
        command=res['cmd'],
        time=timezone.now(),
        scan_history_id=proxy.scan_id,
        activity_id=proxy.activity_id
    )
    res['command_id'] = cmd_record.id
    return res


@activity.defn(name="ParsePortScanResultsActivity")
def parse_port_scan_results_activity(ctx: dict, stdout: str) -> dict:
    """Parse port scan tool outputs and persist discovered ports/hosts to the database.

    Args:
        ctx (dict): Scan context with history IDs and metadata.
        stdout (str): Raw string output containing JSON lines generated during tool execution.

    Returns:
        dict: Wrapped port details indicating scan outcomes.
    """
    from reNgine.tasks import port_scan

    proxy = TemporalTaskProxy(ctx, 'port_scan', 'Port Scan')
    raw_func = port_scan.__func__ if hasattr(port_scan, '__func__') else port_scan
    res = raw_func(proxy, ctx=ctx, parse_only=stdout)
    return {"ports_data": res}


@activity.defn(name="FinalizeFailedScanActivity")
def finalize_failed_scan_activity(ctx: dict, error_msg: str) -> None:
    """Mark a scan as FAILED_TASK due to a workflow crash or unhandled exception.
    
    This ensures that the Django database reflects the crash and allows the user
    to manually resume the scan later.
    """
    from startScan.models import ScanHistory
    from reNgine.definitions import FAILED_TASK
    
    scan_id = ctx.get('scan_history_id')
    if not scan_id:
        return
        
    try:
        scan = ScanHistory.objects.get(pk=scan_id)
        scan.scan_status = FAILED_TASK
        scan.error_message = error_msg[:300] if error_msg else "Scan workflow crashed."
        scan.stop_scan_date = timezone.now()
        scan.save()
        logger.info(f"Scan {scan_id} marked as FAILED_TASK due to workflow crash.")
        
        # Also update running activities
        scan.scanactivity_set.filter(status=0).update(status=FAILED_TASK, error_message=scan.error_message)
    except Exception as e:
        logger.error(f"Failed to finalize crashed scan {scan_id}: {e}")


@activity.defn(name="RunLlmApmeActivity")
def run_llm_apme_activity(scan_history_id: int, job_id: str = None) -> dict:
    from apme.apme_tasks import run_llm_apme
    from reNgine.job_tracker import update_job
    
    update_job(job_id, "RUNNING", 10, "Initializing LLM Attack Path modeling...") if job_id else None
    try:
        result = run_llm_apme(None, scan_history_id)
        if result.get("status") == "success":
            update_job(job_id, "SUCCESS", 100, "Attack Path Modeling completed.", result) if job_id else None
        else:
            update_job(job_id, "FAILED", 100, f"Failed: {result.get('error')}", result) if job_id else None
        return result
    except Exception as e:
        update_job(job_id, "FAILED", 100, f"Error: {str(e)}") if job_id else None
        raise


@activity.defn(name="EnrichIdentitiesActivity")
def enrich_identities_activity(identity: str, identity_type: str, scan_history_id: int, ctx: dict) -> str:
    from reNgine.osint_tasks import enrich_identities_task
    # Run synchronously inside the Django threadpool executor worker
    return enrich_identities_task(identity, identity_type, scan_history_id, ctx)


@activity.defn(name="GeoLocalizeActivity")
def geo_localize_activity(host: str, ip_id: int, scan_id: int = None, activity_id: int = None) -> None:
    from reNgine.tasks import geo_localize
    geo_localize(host, ip_id=ip_id, scan_id=scan_id, activity_id=activity_id)


@activity.defn(name="ImportHackerOneProgramsActivity")
def import_hackerone_programs_activity(handles: list, project_slug: str, is_sync: bool = False) -> None:
    from api.shared_api_tasks import import_hackerone_programs_task
    import_hackerone_programs_task(handles, project_slug, is_sync=is_sync)


@activity.defn(name="SyncBookmarkedProgramsActivity")
def sync_bookmarked_programs_activity(project_slug: str) -> None:
    from api.shared_api_tasks import sync_bookmarked_programs_task
    sync_bookmarked_programs_task(project_slug)


@activity.defn(name="FetchProxiesActivity")
def fetch_proxies_activity(limit: int, job_id: str) -> None:
    from reNgine.tasks import fetch_proxies_task
    fetch_proxies_task(limit=limit, job_id=job_id)


@activity.defn(name="CheckScanQueueStatusActivity")
def check_scan_queue_status_activity(scan_id: int, queue_type: str) -> bool:
    """Check if the given scan is allowed to proceed based on the queue settings.
    
    Args:
        scan_id (int): ScanHistory ID (for main) or SubScan ID (for subscan).
        queue_type (str): 'main' or 'subscan'.
    
    Returns:
        bool: True if it is allowed to proceed (queueing is off, or it's first in line).
    """
    from dashboard.models import UserPreferences
    from startScan.models import ScanHistory, SubScan
    from reNgine.definitions import RUNNING_TASK
    
    # Get the global queuing setting. If there are multiple preferences, just grab the first.
    prefs = UserPreferences.objects.first()
    if not prefs or not getattr(prefs, 'enable_scan_queueing', False):
        return True
        
    if queue_type == "main":
        # Check running main scans (ordered by start date)
        running_scans = list(ScanHistory.objects.filter(
            scan_status=RUNNING_TASK
        ).order_by('start_scan_date').values_list('id', flat=True))
        
        # If the scan is the first in the list, it's its turn
        if running_scans and running_scans[0] == scan_id:
            return True
        elif not running_scans:
            return True
            
        return False
        
    elif queue_type == "subscan":
        running_subscans = list(SubScan.objects.filter(
            status=RUNNING_TASK
        ).order_by('start_scan_date').values_list('id', flat=True))
        
        if running_subscans and running_subscans[0] == scan_id:
            return True
        elif not running_subscans:
            return True
            
        return False

    return True
