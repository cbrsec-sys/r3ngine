"""
Tests for the Celery → Temporal stress testing migration.

Covers:
  1. stress_cmd_builder — unit tests for sanitize() and build_stress_command()
  2. InitStressTestActivity / FinalizeStressTestActivity — DB-integrated activity tests
  3. RunStressToolActivity — subprocess and kill-switch tests with mocks
  4. StressTestWorkflow — Temporal workflow happy-path, kill-switch, no-endpoint edge case
  5. StressTestControlAPI — REST API start/stop with Temporal mock + Celery fallback
  6. StressTelemetryConsumer._is_scan_running — DB-backed authoritative status check
"""

import asyncio
import os
import time
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, call

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from django.test import TestCase as DjangoTestCase, RequestFactory
from django.utils import timezone
from startScan.models import ScanHistory, EndPoint, StressTestResult
from targetApp.models import Domain
from scanEngine.models import EngineType


# ---------------------------------------------------------------------------
# Helpers — shared DB fixture factories
# ---------------------------------------------------------------------------

def _make_domain(name="stress-test.local"):
    domain, _ = Domain.objects.get_or_create(name=name)
    return domain


def _make_engine():
    return EngineType.objects.create(
        engine_name=f"Stress Test Engine {time.time()}",
        yaml_configuration="stress_test:\n  uses_tools: [k6]\n  duration: 5s\n",
    )


def _make_scan(domain, engine, status=2):  # 2 = RUNNING_TASK
    return ScanHistory.objects.create(
        domain=domain,
        scan_type=engine,
        start_scan_date=timezone.now(),
        scan_status=status,
        tasks=[],
    )


def _make_endpoint(scan, domain, url="http://stress-test.local/"):
    from startScan.models import Subdomain
    sub, _ = Subdomain.objects.get_or_create(
        name=domain.name,
        scan_history=scan,
        defaults={"target_domain": domain},
    )
    ep, _ = EndPoint.objects.get_or_create(
        scan_history=scan,
        http_url=url,
        defaults={"subdomain": sub},
    )
    return ep


# ===========================================================================
# 1. stress_cmd_builder — pure unit tests (no DB, no Django models)
# ===========================================================================

class TestSanitize(unittest.TestCase):
    """sanitize() blocks shell-unsafe characters and handles edge cases."""

    def setUp(self):
        from reNgine.stress.cmd_builder import sanitize
        self.sanitize = sanitize

    def test_safe_value_passes_through(self):
        self.assertEqual(self.sanitize("30s"), "30s")

    def test_safe_url_passes_through(self):
        self.assertEqual(self.sanitize("http://example.com/path"), "http://example.com/path")

    def test_semicolon_blocked(self):
        self.assertEqual(self.sanitize("30s; rm -rf /"), "")

    def test_backtick_blocked(self):
        self.assertEqual(self.sanitize("`whoami`"), "")

    def test_dollar_blocked(self):
        self.assertEqual(self.sanitize("$(id)"), "")

    def test_none_returns_default(self):
        self.assertEqual(self.sanitize(None, default="fallback"), "fallback")

    def test_empty_string_returns_default(self):
        # Empty string fails the regex match → default returned
        self.assertEqual(self.sanitize("  ", default="default"), "default")

    def test_integer_value_is_stringified(self):
        self.assertEqual(self.sanitize(50), "50")

    def test_custom_allowed_chars(self):
        result = self.sanitize("hello world", allowed_chars=r"^[a-zA-Z0-9 ]+$")
        self.assertEqual(result, "hello world")


class TestBuildStressCommandK6(unittest.TestCase):
    def setUp(self):
        from reNgine.stress.cmd_builder import build_stress_command
        self.build = build_stress_command

    def tearDown(self):
        # Remove any temp files left by the builder
        import glob
        for f in glob.glob("/tmp/k6_script_999_*.js") + glob.glob("/tmp/k6_summary_999_*.json"):
            try:
                os.remove(f)
            except OSError:
                pass

    def test_k6_returns_k6_run_prefix(self):
        cmd_str, temp_files = self.build(
            tool="k6",
            tool_config={},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=999,
            concurrency=10,
            duration="5s",
        )
        self.assertTrue(cmd_str.startswith("k6 run"), msg=f"Got: {cmd_str}")

    def test_k6_creates_temp_script_file(self):
        _, temp_files = self.build(
            tool="k6",
            tool_config={},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=999,
            concurrency=10,
            duration="5s",
        )
        js_files = [f for f in temp_files if f.endswith(".js")]
        self.assertTrue(len(js_files) == 1)
        self.assertTrue(os.path.exists(js_files[0]))

    def test_k6_insecure_flag_included(self):
        cmd_str, _ = self.build(
            tool="k6",
            tool_config={"insecure_skip_tls": True},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=999,
            concurrency=5,
            duration="5s",
        )
        self.assertIn("--insecure-skip-tls-verify", cmd_str)

    def test_k6_slowloris_attack_type(self):
        cmd_str, temp_files = self.build(
            tool="k6",
            tool_config={"attack_type": "slowloris"},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=999,
            concurrency=5,
            duration="5s",
        )
        # Script should contain sleep(10) for slowloris
        js_files = [f for f in temp_files if f.endswith(".js")]
        if js_files and os.path.exists(js_files[0]):
            content = open(js_files[0]).read()
            self.assertIn("sleep(10)", content)


class TestBuildStressCommandWrk(unittest.TestCase):
    def setUp(self):
        from reNgine.stress.cmd_builder import build_stress_command
        self.build = build_stress_command

    def test_wrk_returns_wrk_prefix(self):
        cmd_str, temp_files = self.build(
            tool="wrk",
            tool_config={},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=1,
            concurrency=10,
            duration="5s",
        )
        self.assertTrue(cmd_str.startswith("wrk"), msg=f"Got: {cmd_str}")
        self.assertEqual(temp_files, [])

    def test_wrk_latency_flag(self):
        cmd_str, _ = self.build(
            tool="wrk",
            tool_config={"latency": True},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=1,
            concurrency=5,
            duration="5s",
        )
        self.assertIn("--latency", cmd_str)

    def test_wrk_endpoint_at_end(self):
        cmd_str, _ = self.build(
            tool="wrk",
            tool_config={},
            endpoint_url="http://example.com/api",
            target_domain="example.com",
            scan_id=1,
            concurrency=5,
            duration="5s",
        )
        self.assertTrue(cmd_str.endswith("http://example.com/api"))


class TestBuildStressCommandHping3(unittest.TestCase):
    def setUp(self):
        from reNgine.stress.cmd_builder import build_stress_command
        self.build = build_stress_command

    def test_hping3_syn_mode(self):
        cmd_str, temp_files = self.build(
            tool="hping3",
            tool_config={"attack_mode": "syn"},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=1,
            concurrency=10,
            duration="5s",
        )
        self.assertTrue(cmd_str.startswith("hping3"))
        self.assertIn("--syn", cmd_str)
        self.assertEqual(temp_files, [])

    def test_hping3_udp_mode(self):
        cmd_str, _ = self.build(
            tool="hping3",
            tool_config={"attack_mode": "udp"},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=1,
            concurrency=10,
            duration="5s",
        )
        self.assertIn("--udp", cmd_str)

    def test_hping3_target_domain_at_end(self):
        cmd_str, _ = self.build(
            tool="hping3",
            tool_config={},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=1,
            concurrency=10,
            duration="5s",
        )
        self.assertTrue(cmd_str.endswith("example.com"))


class TestBuildStressCommandLocust(unittest.TestCase):
    def setUp(self):
        from reNgine.stress.cmd_builder import build_stress_command
        self.build = build_stress_command

    def tearDown(self):
        import glob
        for f in glob.glob("/tmp/locustfile_888_*.py"):
            try:
                os.remove(f)
            except OSError:
                pass

    def test_locust_returns_locust_prefix(self):
        cmd_str, temp_files = self.build(
            tool="locust",
            tool_config={},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=888,
            concurrency=10,
            duration="5s",
        )
        self.assertTrue(cmd_str.startswith("locust"), msg=f"Got: {cmd_str}")

    def test_locust_creates_script_file(self):
        _, temp_files = self.build(
            tool="locust",
            tool_config={},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=888,
            concurrency=10,
            duration="5s",
        )
        py_files = [f for f in temp_files if f.endswith(".py")]
        self.assertTrue(len(py_files) == 1)
        self.assertTrue(os.path.exists(py_files[0]))

    def test_locust_headless_flag(self):
        cmd_str, _ = self.build(
            tool="locust",
            tool_config={},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=888,
            concurrency=5,
            duration="5s",
        )
        self.assertIn("--headless", cmd_str)


class TestBuildStressCommandStressor(unittest.TestCase):
    def setUp(self):
        from reNgine.stress.cmd_builder import build_stress_command
        self.build = build_stress_command

    @patch("reNgine.stress.cmd_builder._build_stressor_cmd")
    def test_stressor_dispatches_correctly(self, mock_builder):
        mock_builder.return_value = (["python3", "stressor.py", "GET", "example.com:80", "10", "5"], [])
        cmd_str, temp_files = self.build(
            tool="stressor",
            tool_config={"method": "GET"},
            endpoint_url="http://example.com/",
            target_domain="example.com",
            scan_id=1,
            concurrency=10,
            duration="5s",
            base_dir="/app",
        )
        mock_builder.assert_called_once()
        self.assertIn("python3", cmd_str)

    def test_invalid_tool_raises_value_error(self):
        with self.assertRaises(ValueError):
            self.build(
                tool="notarealtool",
                tool_config={},
                endpoint_url="http://example.com/",
                target_domain="example.com",
                scan_id=1,
                concurrency=10,
                duration="5s",
            )

    def test_returns_string_not_list(self):
        """build_stress_command must return a str cmd_str, not a list."""
        from reNgine.stress.cmd_builder import build_stress_command
        with patch("reNgine.stress.cmd_builder._build_wrk_cmd") as mock_wrk:
            mock_wrk.return_value = (["wrk", "-t", "2", "http://x.com"], [])
            cmd_str, _ = build_stress_command(
                tool="wrk",
                tool_config={},
                endpoint_url="http://x.com",
                target_domain="x.com",
                scan_id=1,
                concurrency=10,
                duration="5s",
            )
        self.assertIsInstance(cmd_str, str)


# ===========================================================================
# 2. InitStressTestActivity — DB-integrated tests
# ===========================================================================

class TestInitStressTestActivity(DjangoTestCase):
    def setUp(self):
        self.domain = _make_domain("init-activity.local")
        self.engine = _make_engine()
        self.scan = _make_scan(self.domain, self.engine)
        self.endpoint = _make_endpoint(self.scan, self.domain, "http://init-activity.local/")

    def tearDown(self):
        StressTestResult.objects.filter(scan_history=self.scan).delete()
        EndPoint.objects.filter(scan_history=self.scan).delete()
        from startScan.models import Subdomain
        Subdomain.objects.filter(scan_history=self.scan).delete()
        self.scan.delete()
        self.engine.delete()
        self.domain.delete()

    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.clear_stream")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_creates_stress_result_record(self, mock_publish, mock_clear):
        from reNgine.temporal_activities import init_stress_test_activity

        ctx = {
            "scan_history_id": self.scan.id,
            "target_domain_name": self.domain.name,
            "stress_config": {
                "uses_tools": ["k6"],
                "concurrency": 10,
                "duration": "5s",
            },
        }

        result_ctx = init_stress_test_activity(ctx)

        self.assertIn("stress_result_id", result_ctx)
        db_result = StressTestResult.objects.filter(id=result_ctx["stress_result_id"]).first()
        self.assertIsNotNone(db_result)
        self.assertEqual(db_result.scan_history_id, self.scan.id)

    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.clear_stream")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_resolves_endpoints(self, mock_publish, mock_clear):
        from reNgine.temporal_activities import init_stress_test_activity

        ctx = {
            "scan_history_id": self.scan.id,
            "target_domain_name": self.domain.name,
            "stress_config": {
                "uses_tools": ["wrk"],
                "concurrency": 5,
                "duration": "5s",
            },
        }

        result_ctx = init_stress_test_activity(ctx)

        self.assertIn("resolved_endpoints", result_ctx)
        self.assertIsInstance(result_ctx["resolved_endpoints"], list)
        self.assertGreater(len(result_ctx["resolved_endpoints"]), 0)

    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.clear_stream")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_clear_stream_called(self, mock_publish, mock_clear):
        from reNgine.temporal_activities import init_stress_test_activity

        ctx = {
            "scan_history_id": self.scan.id,
            "target_domain_name": self.domain.name,
            "stress_config": {"uses_tools": ["k6"], "concurrency": 5, "duration": "5s"},
        }

        init_stress_test_activity(ctx)

        mock_clear.assert_called_once()

    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.clear_stream")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_publishes_running_status(self, mock_publish, mock_clear):
        from reNgine.temporal_activities import init_stress_test_activity

        ctx = {
            "scan_history_id": self.scan.id,
            "target_domain_name": self.domain.name,
            "stress_config": {"uses_tools": ["k6"], "concurrency": 5, "duration": "5s"},
        }

        init_stress_test_activity(ctx)

        running_calls = [
            c for c in mock_publish.call_args_list
            if c[0][0].get("status") == "running"
        ]
        self.assertTrue(len(running_calls) >= 1)

    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.clear_stream")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_no_endpoints_returns_empty_list(self, mock_publish, mock_clear):
        from reNgine.temporal_activities import init_stress_test_activity

        # Use a domain name for which there are no endpoints in the DB
        ctx = {
            "scan_history_id": self.scan.id,
            "target_domain_name": self.domain.name,
            "stress_config": {
                "uses_tools": ["k6"],
                "concurrency": 5,
                "duration": "5s",
                "selected_endpoints": ["http://nonexistent.local/nope"],
            },
        }

        result_ctx = init_stress_test_activity(ctx)
        self.assertEqual(result_ctx["resolved_endpoints"], [])


# ===========================================================================
# 3. FinalizeStressTestActivity — DB-integrated tests
# ===========================================================================

class TestFinalizeStressTestActivity(DjangoTestCase):
    def setUp(self):
        self.domain = _make_domain("finalize-activity.local")
        self.engine = _make_engine()
        self.scan = _make_scan(self.domain, self.engine)
        self.stress_result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used="k6",
            concurrency_used=10,
            duration="5s",
        )

    def tearDown(self):
        StressTestResult.objects.filter(scan_history=self.scan).delete()
        self.scan.delete()
        self.engine.delete()
        self.domain.delete()

    @patch("reNgine.tasks.send_scan_notif")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_updates_stress_result_metrics(self, mock_publish, mock_notif):
        from reNgine.temporal_activities import finalize_stress_test_activity

        ctx = {
            "scan_history_id": self.scan.id,
            "stress_result_id": self.stress_result.id,
            "aborted": False,
            "total_requests": 1000,
            "successful_requests": 950,
            "failed_requests": 50,
            "avg_latency_ms": 120.0,
            "p95_latency_ms": 250.0,
            "p99_latency_ms": 400.0,
            "max_rps": 333.3,
        }

        result = finalize_stress_test_activity(ctx)
        self.assertTrue(result)

        updated = StressTestResult.objects.get(id=self.stress_result.id)
        self.assertEqual(updated.total_requests, 1000)
        self.assertEqual(updated.successful_requests, 950)
        self.assertAlmostEqual(updated.avg_latency_ms, 120.0, places=1)
        self.assertAlmostEqual(updated.max_requests_per_second, 333.3, places=1)

    @patch("reNgine.tasks.send_scan_notif")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_sets_scan_status_success(self, mock_publish, mock_notif):
        from reNgine.temporal_activities import finalize_stress_test_activity
        from reNgine.definitions import SUCCESS_TASK

        ctx = {
            "scan_history_id": self.scan.id,
            "stress_result_id": self.stress_result.id,
            "aborted": False,
            "total_requests": 100,
            "successful_requests": 100,
            "failed_requests": 0,
            "avg_latency_ms": 50.0,
            "p95_latency_ms": 100.0,
            "p99_latency_ms": 150.0,
            "max_rps": 50.0,
        }

        finalize_stress_test_activity(ctx)

        self.scan.refresh_from_db()
        self.assertEqual(self.scan.scan_status, SUCCESS_TASK)

    @patch("reNgine.tasks.send_scan_notif")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_sets_scan_status_aborted(self, mock_publish, mock_notif):
        from reNgine.temporal_activities import finalize_stress_test_activity
        from reNgine.definitions import ABORTED_TASK

        ctx = {
            "scan_history_id": self.scan.id,
            "stress_result_id": self.stress_result.id,
            "aborted": True,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "max_rps": 0.0,
        }

        finalize_stress_test_activity(ctx)

        self.scan.refresh_from_db()
        self.assertEqual(self.scan.scan_status, ABORTED_TASK)

    @patch("reNgine.tasks.send_scan_notif")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_publishes_completed_status(self, mock_publish, mock_notif):
        from reNgine.temporal_activities import finalize_stress_test_activity

        ctx = {
            "scan_history_id": self.scan.id,
            "stress_result_id": self.stress_result.id,
            "aborted": False,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "max_rps": 0.0,
        }

        finalize_stress_test_activity(ctx)

        completed_calls = [
            c for c in mock_publish.call_args_list
            if c[0][0].get("status") == "completed"
        ]
        self.assertTrue(len(completed_calls) >= 1, "Expected 'completed' status published")

    @patch("reNgine.tasks.send_scan_notif")
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    def test_marks_kill_switch_triggered_when_aborted(self, mock_publish, mock_notif):
        from reNgine.temporal_activities import finalize_stress_test_activity

        ctx = {
            "scan_history_id": self.scan.id,
            "stress_result_id": self.stress_result.id,
            "aborted": True,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "max_rps": 0.0,
        }

        finalize_stress_test_activity(ctx)

        updated = StressTestResult.objects.get(id=self.stress_result.id)
        self.assertTrue(updated.is_kill_switch_triggered)


# ===========================================================================
# 4. RunStressToolActivity — subprocess + kill-switch tests (mocked subprocess)
# ===========================================================================

class TestRunStressToolActivity(DjangoTestCase):
    def setUp(self):
        self.domain = _make_domain("run-tool-activity.local")
        self.engine = _make_engine()
        self.scan = _make_scan(self.domain, self.engine)

    def tearDown(self):
        from startScan.models import Command
        Command.objects.filter(scan_history=self.scan).delete()
        self.scan.delete()
        self.engine.delete()
        self.domain.delete()

    def _make_ctx(self, tool="wrk"):
        return {
            "scan_history_id": self.scan.id,
            "target_domain_name": self.domain.name,
            "current_endpoint": f"http://{self.domain.name}/",
            "current_tool": tool,
            "stress_config": {
                "uses_tools": [tool],
                "concurrency": 5,
                "duration": "5s",
            },
        }

    def _mock_process(self, output_lines=None, returncode=0):
        """Create a mock Popen process that yields given output lines."""
        mock_proc = MagicMock()
        mock_proc.returncode = returncode
        mock_proc.pid = 12345

        lines = list(output_lines or []) + [""]
        line_iter = iter(lines)

        def _readline():
            try:
                return next(line_iter)
            except StopIteration:
                return ""

        mock_proc.stdout.readline.side_effect = _readline
        # After lines are exhausted, poll() returns non-None to exit the loop
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        return mock_proc

    @patch("reNgine.utils.opsec.ProxychainsWrapper.should_wrap", return_value=False)
    @patch("reNgine.common_func.get_random_user_agent", return_value="TestAgent/1.0")
    @patch("reNgine.common_func.get_random_proxy", return_value=None)
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    @patch("reNgine.stress.cmd_builder.build_stress_command")
    @patch("subprocess.Popen")
    def test_returns_metrics_dict(
        self, mock_popen, mock_build, mock_publish, mock_proxy,
        mock_ua, mock_should_wrap
    ):
        from reNgine.temporal_activities import run_stress_tool_activity

        mock_build.return_value = ("wrk -t 2 -c 5 -d 5s http://run-tool-activity.local/", [])
        mock_popen.return_value = self._mock_process(output_lines=["Running 5s test @ http://run-tool-activity.local/"])

        ctx = self._make_ctx("wrk")
        result = run_stress_tool_activity(ctx)

        self.assertIsInstance(result, dict)
        self.assertIn("total_requests", result)

    @patch("reNgine.utils.opsec.ProxychainsWrapper.should_wrap", return_value=False)
    @patch("reNgine.common_func.get_random_user_agent", return_value="TestAgent/1.0")
    @patch("reNgine.common_func.get_random_proxy", return_value=None)
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    @patch("reNgine.stress.cmd_builder.build_stress_command")
    @patch("subprocess.Popen")
    def test_kills_process_when_redis_kill_switch_active(
        self, mock_popen, mock_build, mock_publish, mock_proxy,
        mock_ua, mock_should_wrap
    ):
        """When the Redis kill switch is active before the first line, the process is SIGTERM'd."""
        import os as _os
        from reNgine.temporal_activities import run_stress_tool_activity

        mock_build.return_value = ("wrk -t 2 -c 5 -d 5s http://run-tool-activity.local/", [])

        mock_proc = self._mock_process(output_lines=["line1"])
        mock_popen.return_value = mock_proc

        with patch("redis.StrictRedis") as mock_redis_cls:
            mock_rdb = MagicMock()
            mock_rdb.get.return_value = b"1"  # kill switch active
            mock_redis_cls.return_value = mock_rdb

            with patch("os.killpg") as mock_killpg, patch("os.getpgid", return_value=99):
                ctx = self._make_ctx("wrk")
                run_stress_tool_activity(ctx)
                mock_killpg.assert_called()

    @patch("reNgine.utils.opsec.ProxychainsWrapper.should_wrap", return_value=False)
    @patch("reNgine.common_func.get_random_user_agent", return_value="TestAgent/1.0")
    @patch("reNgine.common_func.get_random_proxy", return_value=None)
    @patch("reNgine.stress.telemetry.StressTelemetryPublisher.publish")
    @patch("reNgine.stress.cmd_builder.build_stress_command")
    @patch("subprocess.Popen")
    def test_temp_files_cleaned_up(
        self, mock_popen, mock_build, mock_publish, mock_proxy,
        mock_ua, mock_should_wrap
    ):
        """Temp files listed by the command builder are removed after subprocess exits."""
        import tempfile
        from reNgine.temporal_activities import run_stress_tool_activity

        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".js")
        tf.write(b"// temp")
        tf.close()
        temp_path = tf.name

        mock_build.return_value = (f"k6 run {temp_path}", [temp_path])
        mock_popen.return_value = self._mock_process()

        ctx = self._make_ctx("k6")
        run_stress_tool_activity(ctx)

        self.assertFalse(os.path.exists(temp_path), "Temp file should have been removed")

    @patch("reNgine.stress.cmd_builder.build_stress_command")
    def test_unknown_tool_raises_value_error(self, mock_build):
        from reNgine.temporal_activities import run_stress_tool_activity

        ctx = {
            "scan_history_id": self.scan.id,
            "target_domain_name": self.domain.name,
            "current_endpoint": "http://run-tool-activity.local/",
            "current_tool": "notarealtool",
            "stress_config": {"uses_tools": ["notarealtool"], "concurrency": 5, "duration": "5s"},
        }

        with self.assertRaises(ValueError):
            run_stress_tool_activity(ctx)


# ===========================================================================
# 5. StressTestWorkflow — workflow-level unit tests using mocked activities
# ===========================================================================

class TestStressTestWorkflow(unittest.TestCase):
    """Test StressTestWorkflow decision logic by patching Temporal workflow internals.

    workflow.logger is a Temporal-SDK-specific object whose isEnabledFor() method
    requires the Temporal workflow event loop. We replace it with a standard Python
    logger in setUp so that workflow.logger.info/warning/error calls work outside
    the Temporal sandbox during unit tests.

    workflow.execute_activity is patched per-test with an AsyncMock so we can
    control what each activity returns without a real Temporal server.
    """

    def setUp(self):
        import temporalio.workflow as _wf_mod
        import logging
        self._wf_mod = _wf_mod
        self._orig_logger = _wf_mod.logger
        # Swap the Temporal proxy-logger for a plain Python logger.
        # This makes workflow.logger.info/warning/error work without the
        # Temporal runtime event loop being present.
        _wf_mod.logger = logging.getLogger("test_stress_workflow")

    def tearDown(self):
        # Restore the original Temporal logger so other tests are unaffected.
        self._wf_mod.logger = self._orig_logger

    def _run_workflow(self, ctx, activity_map):
        """Run StressTestWorkflow.run() with per-name mocked activity responses.

        activity_map: dict mapping activity name → return value (or callable).
        """
        from reNgine.temporal_workflows import StressTestWorkflow

        async def mock_execute_activity(name, *args, **kwargs):
            val = activity_map.get(name)
            return val(*args) if callable(val) else val

        async def run():
            with patch.object(self._wf_mod, "execute_activity",
                               side_effect=mock_execute_activity):
                wf = StressTestWorkflow()
                return await wf.run(ctx)

        return asyncio.run(run())

    def test_happy_path_returns_success(self):
        ctx = {
            "scan_history_id": 1,
            "target_domain_name": "example.com",
            "stress_config": {"uses_tools": ["wrk"], "concurrency": 5, "duration": "5s"},
        }
        init_return = {**ctx, "resolved_endpoints": ["http://example.com/"], "stress_result_id": 42}
        run_return = {
            "total_requests": 100, "successful_requests": 95, "failed_requests": 5,
            "avg_latency_ms": 50.0, "p95_latency_ms": 100.0,
            "p99_latency_ms": 150.0, "max_requests_per_second": 33.3,
        }

        result = self._run_workflow(ctx, {
            "InitStressTestActivity": init_return,
            "RunStressToolActivity": run_return,
            "FinalizeStressTestActivity": True,
        })

        self.assertEqual(result["status"], "SUCCESS")

    def test_no_endpoints_skips_run_activity(self):
        """When InitStressTestActivity resolves no endpoints, RunStressToolActivity is never called."""
        ctx = {
            "scan_history_id": 2,
            "target_domain_name": "empty.local",
            "stress_config": {"uses_tools": ["k6"], "concurrency": 5, "duration": "5s"},
        }
        init_return = {**ctx, "resolved_endpoints": [], "stress_result_id": 43}
        call_log = []

        from reNgine.temporal_workflows import StressTestWorkflow

        async def mock_execute_activity(name, *args, **kwargs):
            call_log.append(name)
            if name == "InitStressTestActivity":
                return init_return
            if name == "FinalizeStressTestActivity":
                return True
            raise AssertionError(f"Unexpected activity call: {name}")

        async def run():
            with patch.object(self._wf_mod, "execute_activity",
                               side_effect=mock_execute_activity):
                wf = StressTestWorkflow()
                return await wf.run(ctx)

        asyncio.run(run())
        self.assertNotIn("RunStressToolActivity", call_log)

    def test_kill_switch_stops_loop(self):
        """After kill_switch signal is received, the endpoint/tool loop stops immediately."""
        ctx = {
            "scan_history_id": 3,
            "target_domain_name": "target.local",
            "stress_config": {"uses_tools": ["wrk", "k6"], "concurrency": 5, "duration": "5s"},
        }
        init_return = {
            **ctx,
            "resolved_endpoints": ["http://target.local/a", "http://target.local/b"],
            "stress_result_id": 44,
        }
        run_call_count = [0]

        from reNgine.temporal_workflows import StressTestWorkflow
        wf = StressTestWorkflow()

        async def mock_execute_activity(name, *args, **kwargs):
            if name == "InitStressTestActivity":
                # Signal kill BEFORE the loop starts — no RunStressToolActivity should run.
                wf.kill_switch()
                return init_return
            if name == "RunStressToolActivity":
                run_call_count[0] += 1
                return {"total_requests": 0, "successful_requests": 0, "failed_requests": 0,
                        "avg_latency_ms": 0, "p95_latency_ms": 0, "p99_latency_ms": 0,
                        "max_requests_per_second": 0}
            if name == "FinalizeStressTestActivity":
                return True
            raise AssertionError(f"Unexpected: {name}")

        async def run():
            with patch.object(self._wf_mod, "execute_activity",
                               side_effect=mock_execute_activity):
                return await wf.run(ctx)

        result = asyncio.run(run())
        self.assertEqual(result["status"], "ABORTED")
        self.assertEqual(run_call_count[0], 0,
                         "RunStressToolActivity must not execute after kill signal")

    def test_kill_switch_and_is_running_query(self):
        """is_running() reflects kill_switch signal state correctly."""
        from reNgine.temporal_workflows import StressTestWorkflow
        wf = StressTestWorkflow()
        self.assertTrue(wf.is_running())
        # kill_switch() now works because setUp replaced workflow.logger.
        wf.kill_switch()
        self.assertFalse(wf.is_running())


# ===========================================================================
# 6. StressTestControlAPI — REST API view tests
# ===========================================================================

class TestStressTestControlAPIStart(DjangoTestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.factory = RequestFactory()
        self.domain = _make_domain("api-test.local")
        self.engine = _make_engine()
        self.scan = _make_scan(self.domain, self.engine)
        self.user = User.objects.create_user("apitestuser", password="pass")

    def tearDown(self):
        self.scan.delete()
        self.engine.delete()
        self.domain.delete()
        self.user.delete()

    def _authenticated_request(self, data):
        from rest_framework.test import APIRequestFactory, force_authenticate
        factory = APIRequestFactory()
        request = factory.post(f"/api/stress/{self.scan.id}/control/", data, format="json")
        force_authenticate(request, user=self.user)
        return request

    @patch("reNgine.stress.views._start_stress_workflow", new_callable=AsyncMock)
    def test_start_action_calls_temporal(self, mock_start):
        from reNgine.stress.views import StressTestControlAPI

        request = self._authenticated_request({"action": "start", "config": {}})
        view = StressTestControlAPI.as_view()
        response = view(request, scan_id=self.scan.id)

        self.assertEqual(response.status_code, 200)
        mock_start.assert_called_once_with({
            "scan_history_id": self.scan.id,
            "target_domain_name": self.domain.name,
            "stress_config": {},
        }, self.scan.id)

    @patch("reNgine.stress.views._start_stress_workflow", new_callable=AsyncMock)
    def test_start_returns_500_when_temporal_fails(self, mock_start):
        """When Temporal is unavailable, the API returns HTTP 500 — no Celery fallback."""
        from reNgine.stress.views import StressTestControlAPI
        mock_start.side_effect = Exception("Temporal unavailable")

        request = self._authenticated_request({"action": "start", "config": {}})
        view = StressTestControlAPI.as_view()
        response = view(request, scan_id=self.scan.id)

        self.assertEqual(response.status_code, 500)

    @patch("reNgine.stress.views._signal_stress_workflow", new_callable=AsyncMock)
    def test_stop_action_sends_temporal_signal(self, mock_signal):
        from reNgine.stress.views import StressTestControlAPI

        request = self._authenticated_request({"action": "stop"})
        view = StressTestControlAPI.as_view()
        response = view(request, scan_id=self.scan.id)

        self.assertEqual(response.status_code, 200)
        mock_signal.assert_called_once_with(self.scan.id)

    def test_invalid_action_returns_400(self):
        from reNgine.stress.views import StressTestControlAPI

        request = self._authenticated_request({"action": "explode"})
        view = StressTestControlAPI.as_view()
        response = view(request, scan_id=self.scan.id)

        self.assertEqual(response.status_code, 400)

    def test_start_with_unknown_scan_returns_404(self):
        from reNgine.stress.views import StressTestControlAPI

        request = self._authenticated_request({"action": "start", "config": {}})
        view = StressTestControlAPI.as_view()
        response = view(request, scan_id=999999)

        self.assertEqual(response.status_code, 404)


# ===========================================================================
# 7. StressTelemetryConsumer._is_scan_running — authoritative status check
# ===========================================================================

class TestStressTelemetryConsumerIsRunning(unittest.TestCase):
    """Unit tests for _is_scan_running().

    We mock ScanHistory.objects so we don't hit the database at all.
    This avoids the Django test transaction isolation problem where
    database_sync_to_async runs the query in a thread pool thread that
    opens a separate DB connection and cannot see uncommitted test data.
    """

    def _make_consumer(self, scan_id):
        from reNgine.consumers import StressTelemetryConsumer
        consumer = StressTelemetryConsumer()
        consumer.scan_id = str(scan_id)
        return consumer

    def _run(self, coro):
        return asyncio.run(coro)

    def test_returns_true_for_running_scan(self):
        from reNgine.definitions import RUNNING_TASK
        mock_scan = MagicMock()
        mock_scan.scan_status = RUNNING_TASK

        consumer = self._make_consumer(42)
        with patch("startScan.models.ScanHistory.objects") as mock_mgr:
            mock_mgr.filter.return_value.first.return_value = mock_scan
            result = self._run(consumer._is_scan_running())

        self.assertTrue(result)

    def test_returns_false_for_completed_scan(self):
        from reNgine.definitions import SUCCESS_TASK
        mock_scan = MagicMock()
        mock_scan.scan_status = SUCCESS_TASK

        consumer = self._make_consumer(42)
        with patch("startScan.models.ScanHistory.objects") as mock_mgr:
            mock_mgr.filter.return_value.first.return_value = mock_scan
            result = self._run(consumer._is_scan_running())

        self.assertFalse(result)

    def test_returns_false_for_nonexistent_scan(self):
        consumer = self._make_consumer(999999)
        with patch("startScan.models.ScanHistory.objects") as mock_mgr:
            mock_mgr.filter.return_value.first.return_value = None
            result = self._run(consumer._is_scan_running())

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
