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
