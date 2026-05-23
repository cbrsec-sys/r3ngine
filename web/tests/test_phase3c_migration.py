"""Phase 3C migration tests — verify fire-and-forget .delay() calls replaced with threading.Thread."""
import os
from unittest import TestCase

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relative_path):
    with open(os.path.join(WEB_DIR, relative_path), 'r', encoding='utf-8') as f:
        return f.read()


class TestPhase3C1ViewLayerThreading(TestCase):
    """3C-1: View-layer fire-and-forget tasks must use threading.Thread, not .delay()."""

    def test_dashboard_generate_impact_no_delay(self):
        source = _read('dashboard/views.py')
        self.assertNotIn(
            'generate_impact_assessment.delay(',
            source,
            "dashboard/views.py must not call generate_impact_assessment.delay"
        )

    def test_dashboard_generate_impact_uses_thread(self):
        source = _read('dashboard/views.py')
        self.assertIn(
            'threading.Thread',
            source,
            "dashboard/views.py must use threading.Thread for generate_impact_assessment"
        )

    def test_startscan_generate_report_no_delay(self):
        source = _read('startScan/views.py')
        self.assertNotIn(
            'generate_report_task.delay(',
            source,
            "startScan/views.py must not call generate_report_task.delay"
        )

    def test_startscan_generate_report_uses_thread(self):
        source = _read('startScan/views.py')
        self.assertIn(
            'threading.Thread',
            source,
        )

    def test_stress_views_generate_report_no_delay(self):
        source = _read('reNgine/stress_views.py')
        self.assertNotIn(
            'generate_report_task.delay(',
            source,
            "stress_views.py must not call generate_report_task.delay"
        )

    def test_scanengine_pull_ollama_no_delay(self):
        source = _read('scanEngine/views.py')
        self.assertNotIn(
            'pull_ollama_model.delay(',
            source,
            "scanEngine/views.py must not call pull_ollama_model.delay"
        )

    def test_scanengine_pull_ollama_uses_thread(self):
        source = _read('scanEngine/views.py')
        self.assertIn(
            'threading.Thread',
            source,
            "scanEngine/views.py must use threading.Thread for pull_ollama_model"
        )


class TestPhase3C2LLMVulnDirectCall(TestCase):
    """3C-2: llm_vulnerability_description must be called directly, not via apply_async."""

    def test_api_views_llm_vuln_no_apply_async(self):
        source = _read('api/views.py')
        self.assertNotIn(
            'llm_vulnerability_description.apply_async(',
            source,
            "api/views.py must not call llm_vulnerability_description.apply_async"
        )

    def test_api_views_llm_vuln_direct_call(self):
        source = _read('api/views.py')
        self.assertIn(
            'llm_vulnerability_description(vulnerability_id)',
            source,
            "api/views.py must call llm_vulnerability_description(vulnerability_id) directly"
        )


class TestPhase3C3HackerOneThreading(TestCase):
    """3C-3: HackerOne import tasks must use threading.Thread, not .delay()."""

    def test_api_views_import_h1_no_delay(self):
        source = _read('api/views.py')
        self.assertNotIn(
            'import_hackerone_programs_task.delay(',
            source,
            "api/views.py must not call import_hackerone_programs_task.delay"
        )

    def test_api_views_sync_bookmarked_no_delay(self):
        source = _read('api/views.py')
        self.assertNotIn(
            'sync_bookmarked_programs_task.delay(',
            source,
            "api/views.py must not call sync_bookmarked_programs_task.delay"
        )

    def test_api_views_h1_uses_thread(self):
        source = _read('api/views.py')
        self.assertIn(
            'threading.Thread',
            source,
            "api/views.py must use threading.Thread for HackerOne tasks"
        )

    def test_shared_api_tasks_import_h1_no_delay(self):
        source = _read('api/shared_api_tasks.py')
        self.assertNotIn(
            'import_hackerone_programs_task.delay(',
            source,
            "api/shared_api_tasks.py must not call import_hackerone_programs_task.delay"
        )

    def test_shared_api_tasks_uses_thread(self):
        source = _read('api/shared_api_tasks.py')
        self.assertIn(
            'threading.Thread',
            source,
            "api/shared_api_tasks.py must use threading.Thread for import_hackerone_programs_task"
        )


class TestPhase3C4OsintFanouts(TestCase):
    """3C-4: OSINT fan-out tasks must use threading.Thread, not .delay()."""

    def test_osint_tasks_no_run_holehe_delay(self):
        source = _read('reNgine/osint_tasks.py')
        self.assertNotIn('run_holehe.delay(', source,
                         "osint_tasks.py must not call run_holehe.delay")

    def test_osint_tasks_no_run_maigret_delay(self):
        source = _read('reNgine/osint_tasks.py')
        self.assertNotIn('run_maigret.delay(', source,
                         "osint_tasks.py must not call run_maigret.delay")

    def test_osint_tasks_no_run_linkedint_delay(self):
        source = _read('reNgine/osint_tasks.py')
        self.assertNotIn('run_linkedint.delay(', source,
                         "osint_tasks.py must not call run_linkedint.delay")

    def test_osint_tasks_no_enrich_delay(self):
        source = _read('reNgine/osint_tasks.py')
        self.assertNotIn('enrich_identities_task.delay(', source,
                         "osint_tasks.py must not call enrich_identities_task.delay")

    def test_osint_tasks_uses_threading(self):
        source = _read('reNgine/osint_tasks.py')
        self.assertIn('threading.Thread', source,
                      "osint_tasks.py must use threading.Thread for OSINT fan-outs")

    def test_task_utils_no_enrich_delay(self):
        source = _read('reNgine/task_utils.py')
        self.assertNotIn('enrich_identities_task.delay(', source,
                         "task_utils.py must not call enrich_identities_task.delay")

    def test_task_utils_uses_threading(self):
        source = _read('reNgine/task_utils.py')
        self.assertIn('threading.Thread', source,
                      "task_utils.py must use threading.Thread for enrich_identities_task")


class TestPhase3C5TasksOsintOrchestrator(TestCase):
    """3C-5: osint_orchestrator.delay() in tasks.py must be replaced with threading.Thread."""

    def _get_function_body(self, source, func_name):
        start = source.find(f'def {func_name}(')
        if start == -1:
            return ''
        next_task = source.find('\n@app.task', start + 1)
        return source[start:next_task if next_task != -1 else len(source)]

    def test_finish_osint_no_osint_orchestrator_delay(self):
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'finish_osint')
        self.assertNotIn('osint_orchestrator.delay(', body,
                         "finish_osint must not call osint_orchestrator.delay")

    def test_finish_osint_uses_threading(self):
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'finish_osint')
        self.assertIn('threading.Thread', body,
                      "finish_osint must use threading.Thread for osint_orchestrator")

    def test_osint_task_no_osint_orchestrator_delay(self):
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'osint')
        self.assertNotIn('osint_orchestrator.delay(', body,
                         "osint task must not call osint_orchestrator.delay")

    def test_osint_task_uses_threading(self):
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'osint')
        self.assertIn('threading.Thread', body,
                      "osint task must use threading.Thread for osint_orchestrator")


class TestPhase3C6PluginManagementThreading(TestCase):
    """3C-6: Plugin install/verify tasks must use threading.Thread, not .delay()."""

    def test_plugins_apps_no_verify_delay(self):
        source = _read('plugins/apps.py')
        self.assertNotIn('verify_all_plugin_tools.delay(', source,
                         "plugins/apps.py must not call verify_all_plugin_tools.delay")

    def test_plugins_apps_uses_thread(self):
        source = _read('plugins/apps.py')
        self.assertIn('threading.Thread', source,
                      "plugins/apps.py must use threading.Thread for verify_all_plugin_tools")

    def test_plugins_tasks_no_install_delay(self):
        source = _read('plugins/tasks.py')
        self.assertNotIn('install_plugin_tools.delay(', source,
                         "plugins/tasks.py must not call install_plugin_tools.delay")

    def test_plugins_tasks_uses_thread(self):
        source = _read('plugins/tasks.py')
        self.assertIn('threading.Thread', source,
                      "plugins/tasks.py must use threading.Thread for install_plugin_tools")

    def test_plugins_utils_no_install_delay(self):
        source = _read('plugins/utils.py')
        self.assertNotIn('install_plugin_tools.delay(', source,
                         "plugins/utils.py must not call install_plugin_tools.delay")

    def test_plugins_utils_uses_thread(self):
        source = _read('plugins/utils.py')
        self.assertIn('threading.Thread', source,
                      "plugins/utils.py must use threading.Thread for install_plugin_tools")


class TestPhase3C7TaskNotifThreading(TestCase):
    """3C-7: celery_custom_task.py removed in Phase 5 (Celery fully removed)."""

    def test_celery_custom_task_deleted(self):
        path = os.path.join(WEB_DIR, 'reNgine', 'celery_custom_task.py')
        self.assertFalse(os.path.isfile(path),
                         "celery_custom_task.py must be deleted — Phase 5 removed all Celery infrastructure")
