"""Tests for Temporal activity correctness — focus on durability constraints."""
import inspect
from django.test import TestCase


class TestOsintNoDaemonThreads(TestCase):
    def test_finish_osint_does_not_spawn_thread(self):
        """finish_osint must call osint_orchestrator directly, not in a daemon thread."""
        import reNgine.tasks as tasks_mod
        source = inspect.getsource(tasks_mod.finish_osint)
        self.assertNotIn(
            "threading.Thread",
            source,
            "finish_osint must not spawn a daemon thread — call osint_orchestrator synchronously",
        )

    def test_osint_function_does_not_spawn_thread_for_orchestrator(self):
        """The osint() task body must not launch osint_orchestrator in a daemon thread."""
        import reNgine.tasks as tasks_mod
        source = inspect.getsource(tasks_mod.osint)
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'daemon=True' in line:
                context = '\n'.join(lines[max(0, i-3):i+2])
                if 'osint_orchestrator' in context:
                    self.fail(
                        f"osint() must not spawn daemon threads for osint_orchestrator.\nContext:\n{context}"
                    )


class TestRunGenericTaskAllowlist(TestCase):

    def test_permitted_task_names_accepted(self):
        """Tasks in the allowlist must not raise ValueError."""
        from reNgine.temporal_activities import _PERMITTED_GENERIC_TASKS
        # spot-check a few known tasks
        for name in ("subdomain_discovery", "http_crawl", "vulnerability_scan"):
            self.assertIn(name, _PERMITTED_GENERIC_TASKS)

    def test_unknown_task_name_raises(self):
        """A task name not in the allowlist must raise ValueError before any import."""
        from unittest.mock import patch, MagicMock
        from reNgine.temporal_activities import run_generic_task_activity
        fake_ctx = {"scan_history_id": 1, "domain_id": 1, "engine_id": 1}
        with self.assertRaises(ValueError) as cm:
            with patch("temporalio.activity.logger"):
                run_generic_task_activity(fake_ctx, "exec_shell_command")
        self.assertIn("exec_shell_command", str(cm.exception))

    def test_allowlist_check_before_import(self):
        """Allowlist must be checked BEFORE attempting to import from tasks module."""
        import importlib
        from unittest.mock import patch, MagicMock
        from reNgine.temporal_activities import run_generic_task_activity
        fake_ctx = {"scan_history_id": 1, "domain_id": 1, "engine_id": 1}
        with patch("importlib.import_module") as mock_import:
            with patch("temporalio.activity.logger"):
                try:
                    run_generic_task_activity(fake_ctx, "not_in_allowlist")
                except ValueError:
                    pass
        mock_import.assert_not_called()
