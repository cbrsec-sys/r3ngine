"""
Shared building blocks for the r3ngine Temporal workflow modules.

Retry policy presets and the helper coroutines used by more than one workflow
live here so every workflow module imports a single definition. This module
must stay deterministic like the workflows that import it (see
.claude/rules/r3ngine-temporal.md).
"""

import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError


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


# Tier 6 scanners signal failure by returning False, which _run_task converts into
# an exception. Without an explicit policy Temporal retries such an activity forever,
# so a scanner whose backend is unreachable floods the timeline for hours.
_RETRY_SCANNER = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(minutes=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
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


async def _isolated_tool(name: str, call):
    """Await a scanning tool's activity; if it fails, log it and let the scan go on.

    One tool that exhausts its retries (a fuzzer past its time limit, a crawler
    whose backend is down) used to fail the whole MasterScanWorkflow, so every
    later tier was marked FAILED without having run. Its own timeline row already
    records the failure, the scan still ends FAILED, and Retry re-runs just that
    tool. Cancellation (a user abort) is not an ActivityError and still propagates.
    """
    try:
        return await call
    except ActivityError as exc:
        workflow.logger.error(
            "%s failed in workflow %s — continuing with the rest of the scan: %s",
            name, workflow.info().workflow_id, exc,
        )
        return None


async def _dispatch_tier_plugins(ctx: dict, tier: str, wf_id_prefix: str) -> None:
    """Dispatch selected plugins anchored to `tier` as child workflows.

    Called after every scan tier completes. Valid tier values:
      tier_1 (subdomain discovery), tier_2 (port scan / HTTP crawl),
      tier_3 (URL fetch / screenshot), tier_4 (dir/file fuzz),
      tier_5 (API discovery / secrets / WAF), tier_6 (vulnerability scan),
      tier_7 (correlation / risk / APME), standalone (not injected).

    Only runs if the scan explicitly selected at least one plugin slug.
    An empty or absent `selected_plugin_slugs` in ctx means no plugins were
    chosen for this scan — the activity is skipped entirely in that case.

    Args:
        ctx: Scan context dict passed through to each plugin workflow.
        tier: Anchor tier string, e.g. "tier_2", "tier_7".
        wf_id_prefix: Unique prefix for child workflow IDs (scan or subscan ID).
    """
    selected_slugs = ctx.get("selected_plugin_slugs") or []
    if not selected_slugs:
        return

    plugin_list = await workflow.execute_activity(
        "GetEnabledPluginsForTierActivity",
        {"tier": tier, "selected_plugin_slugs": selected_slugs},
        start_to_close_timeout=timedelta(seconds=15),
        heartbeat_timeout=timedelta(seconds=15),
        retry_policy=_RETRY_INTERNAL,
        task_queue="python-orchestrator-queue",
    )
    for plugin_meta in plugin_list:
        wf_name = plugin_meta.get("workflow_name")
        slug = plugin_meta.get("slug")
        plugin_name = plugin_meta.get("name", slug)
        if not wf_name:
            continue
            
        log_res = await workflow.execute_activity(
            "LogPluginStartActivity",
            {
                "scan_id": ctx.get("scan_history_id"),
                "name": wf_name,
                "title": f"Plugin: {plugin_name}",
                "tier": tier,
            },
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue",
        )
        act_id = log_res.get("activity_id")

        try:
            await workflow.execute_child_workflow(
                wf_name,
                ctx,
                id=f"{wf_id_prefix}-plugin-{slug}",
                task_queue="python-orchestrator-queue",
                execution_timeout=timedelta(days=7),
            )
            await workflow.execute_activity(
                "LogPluginEndActivity",
                {"activity_id": act_id, "status": 2}, # SUCCESS_TASK
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
        except Exception as e:
            await workflow.execute_activity(
                "LogPluginEndActivity",
                {"activity_id": act_id, "status": 0, "error": str(e)}, # FAILED_TASK
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
            # We don't re-raise here so other plugins/tiers can still run


async def _fan_out_search_vulns(ctx: dict, services: list) -> None:
    """Fan out concurrent per-service CVE + exploit lookups.

    Reads a list of {host, port, service, version} dicts and launches one
    RunSearchVulnsActivity per service,
    all gathered concurrently with return_exceptions=True so a single
    lookup failure never aborts the scan.

    Called from MasterScanWorkflow after GetDiscoveredServicesActivity and
    from HostReconWorkflow after RunPortScanActivity.
    """
    if not services:
        return

    lookup_tasks = []
    for svc in services:
        service_name = (svc.get('service') or '').strip()
        if not service_name:
            continue
        svc_ctx = {
            **ctx,
            'host': svc.get('host', ''),
            'port': svc.get('port', 0),
            'service': service_name,
            'version': svc.get('version'),
        }
        lookup_tasks.append(
            workflow.execute_activity(
                "RunSearchVulnsActivity",
                svc_ctx,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
        )

    if lookup_tasks:
        await asyncio.gather(*lookup_tasks, return_exceptions=True)
