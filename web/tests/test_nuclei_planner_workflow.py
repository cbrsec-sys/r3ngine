"""
Integration tests for NucleiPlannerWorkflow sequential severity scanning.

Uses WorkflowEnvironment (time-skipping) from temporalio.testing to execute
the workflow against mocked activities and verify:

  1. Each configured severity triggers its own RunNucleiActivity call.
  2. Severities execute in the configured order (sequential, not concurrent).
  3. NUCLEI_DEFAULT_SEVERITIES applies when no severity list is configured.
  4. run_nuclei=False suppresses all RunNucleiActivity calls.
  5. MarkVulnerabilityScanCompleteActivity fires exactly once on every run.

These tests validate the sequential fix introduced to prevent orphaned
NucleiPlannerWorkflow child workflows in the Tier 6 gather (FIXES.md Fix 2).
"""

import asyncio
import os
import unittest
from typing import Any, Dict, List
from unittest import IsolatedAsyncioTestCase

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reNgine.settings")
django.setup()

from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from reNgine.temporal_workflows import NucleiPlannerWorkflow
from reNgine.definitions import NUCLEI_DEFAULT_SEVERITIES


# ---------------------------------------------------------------------------
# Mock activities — registered under their production names so the workflow
# can dispatch by name without touching real infrastructure.
# ---------------------------------------------------------------------------

@activity.defn(name="RunCRLFuzzActivity")
async def _mock_crlfuzz(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="RunDalfoxActivity")
async def _mock_dalfox(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="RunS3ScannerActivity")
async def _mock_s3scanner(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="RunAcunetixActivity")
async def _mock_acunetix(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="RunCpanelScanActivity")
async def _mock_cpanel(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="RunWpscanActivity")
async def _mock_wpscan(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="RunReact2ShellActivity")
async def _mock_react2shell(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="RunSemgrepActivity")
async def _mock_semgrep(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="RunVigoliumScanActivity")
async def _mock_vigolium(ctx: Dict[str, Any]) -> Dict:
    return {}


@activity.defn(name="MarkVulnerabilityScanCompleteActivity")
async def _mock_mark_complete(ctx: Dict[str, Any]) -> Dict:
    return {}


_NOOP_SUPPORT_ACTIVITIES = [
    _mock_crlfuzz,
    _mock_dalfox,
    _mock_s3scanner,
    _mock_acunetix,
    _mock_cpanel,
    _mock_wpscan,
    _mock_react2shell,
    _mock_semgrep,
    _mock_vigolium,
    _mock_mark_complete,
]


def _ctx(severities=None, run_nuclei: bool = True) -> Dict[str, Any]:
    """Minimal scan context for NucleiPlannerWorkflow tests.

    All optional scanners (crlfuzz, dalfox, s3scanner, etc.) are disabled so
    only RunNucleiActivity calls appear in the tracking log.
    """
    nuclei_cfg: Dict[str, Any] = {}
    if severities is not None:
        nuclei_cfg["severity"] = severities

    return {
        "scan_history_id": 1,
        "yaml_configuration": {
            "vulnerability_scan": {
                "run_nuclei": run_nuclei,
                "nuclei": nuclei_cfg,
                "run_crlfuzz": False,
                "run_dalfox": False,
                "run_s3scanner": False,
                "run_acunetix": False,
                "cpanel_scanner": {"run_cpanel2shell": False},
                "run_wpscan": False,
                "react_scanner": {"run_react2shell": False},
                "run_vigolium": False,
            },
            "leaks_and_secrets": {"run_semgrep": False},
        },
    }


class TestNucleiPlannerWorkflowSequential(IsolatedAsyncioTestCase):
    """Verify per-severity sequential execution in NucleiPlannerWorkflow.

    Uses WorkflowEnvironment with time-skipping so tests complete in
    milliseconds regardless of configured scan durations.
    """

    async def _run_workflow(self, ctx, nuclei_activity, wf_id):
        """Helper: spin up a time-skipping WorkflowEnvironment, execute the
        workflow, and return the result."""
        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="python-orchestrator-queue",
                workflows=[NucleiPlannerWorkflow],
                activities=[nuclei_activity, *_NOOP_SUPPORT_ACTIVITIES],
            ):
                return await env.client.execute_workflow(
                    NucleiPlannerWorkflow.run,
                    ctx,
                    id=wf_id,
                    task_queue="python-orchestrator-queue",
                )

    async def test_each_severity_gets_own_activity_call_in_order(self):
        """RunNucleiActivity is called once per severity in the configured order."""
        call_log: List[str] = []

        @activity.defn(name="RunNucleiActivity")
        async def track_nuclei(ctx: Dict[str, Any], severity: str) -> Dict:
            call_log.append(severity)
            return {}

        result = await self._run_workflow(
            _ctx(severities=["critical", "high", "medium"]),
            track_nuclei,
            "test-nuclei-ordered",
        )

        self.assertEqual(result, {"status": "SUCCESS"})
        self.assertEqual(
            call_log,
            ["critical", "high", "medium"],
            msg=f"Expected severities in order ['critical','high','medium']; got {call_log}",
        )

    async def test_default_severities_applied_when_none_configured(self):
        """NUCLEI_DEFAULT_SEVERITIES is used when no severity list is in yaml config."""
        call_log: List[str] = []

        @activity.defn(name="RunNucleiActivity")
        async def track_nuclei(ctx: Dict[str, Any], severity: str) -> Dict:
            call_log.append(severity)
            return {}

        result = await self._run_workflow(
            _ctx(severities=None),  # no explicit list → defaults
            track_nuclei,
            "test-nuclei-defaults",
        )

        self.assertEqual(result, {"status": "SUCCESS"})
        self.assertEqual(
            call_log,
            list(NUCLEI_DEFAULT_SEVERITIES),
            msg=(
                f"Expected default severities {list(NUCLEI_DEFAULT_SEVERITIES)}; "
                f"got {call_log}"
            ),
        )

    async def test_run_nuclei_false_skips_all_nuclei_activity_calls(self):
        """RunNucleiActivity must not fire when run_nuclei=False in yaml config."""
        call_log: List[str] = []

        @activity.defn(name="RunNucleiActivity")
        async def track_nuclei(ctx: Dict[str, Any], severity: str) -> Dict:
            call_log.append(severity)
            return {}

        result = await self._run_workflow(
            _ctx(severities=["critical", "high"], run_nuclei=False),
            track_nuclei,
            "test-nuclei-disabled",
        )

        self.assertEqual(result, {"status": "SUCCESS"})
        self.assertEqual(
            call_log,
            [],
            msg=f"RunNucleiActivity must not be called when run_nuclei=False; got {call_log}",
        )

    async def test_single_severity_produces_single_call(self):
        """Configuring one severity results in exactly one RunNucleiActivity call."""
        call_log: List[str] = []

        @activity.defn(name="RunNucleiActivity")
        async def track_nuclei(ctx: Dict[str, Any], severity: str) -> Dict:
            call_log.append(severity)
            return {}

        result = await self._run_workflow(
            _ctx(severities=["critical"]),
            track_nuclei,
            "test-nuclei-single",
        )

        self.assertEqual(result, {"status": "SUCCESS"})
        self.assertEqual(
            call_log,
            ["critical"],
            msg=f"Expected exactly one call for 'critical'; got {call_log}",
        )

    async def test_mark_complete_activity_always_fires(self):
        """MarkVulnerabilityScanCompleteActivity must be called exactly once."""
        mark_count: List[int] = []

        @activity.defn(name="RunNucleiActivity")
        async def noop_nuclei(ctx: Dict[str, Any], severity: str) -> Dict:
            return {}

        @activity.defn(name="MarkVulnerabilityScanCompleteActivity")
        async def track_mark(ctx: Dict[str, Any]) -> Dict:
            mark_count.append(1)
            return {}

        # Exclude the noop mark-complete; use the tracking version instead
        support = [a for a in _NOOP_SUPPORT_ACTIVITIES
                   if a is not _mock_mark_complete]

        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(
                env.client,
                task_queue="python-orchestrator-queue",
                workflows=[NucleiPlannerWorkflow],
                activities=[noop_nuclei, track_mark, *support],
            ):
                await env.client.execute_workflow(
                    NucleiPlannerWorkflow.run,
                    _ctx(severities=["high"]),
                    id="test-nuclei-mark-complete",
                    task_queue="python-orchestrator-queue",
                )

        self.assertEqual(
            sum(mark_count),
            1,
            msg=(
                f"MarkVulnerabilityScanCompleteActivity must be called exactly once; "
                f"called {sum(mark_count)} time(s)"
            ),
        )
