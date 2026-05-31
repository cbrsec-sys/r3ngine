"""Phase 3B migration tests — verify Celery scan entry points have been replaced with Temporal."""
import os
from unittest import TestCase

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relative_path):
    """Read a file from web/ root and return its contents."""
    with open(os.path.join(WEB_DIR, relative_path), 'r', encoding='utf-8') as f:
        return f.read()


class TestPhase3B1OrgScanTrigger(TestCase):
    """3B-1: start_organization_scan must use initiate_scan_temporal, not initiate_scan.apply_async."""

    def test_org_scan_view_does_not_use_apply_async(self):
        """startScan/views.py must not contain initiate_scan.apply_async anywhere."""
        source = _read('startScan/views.py')
        self.assertNotIn(
            'initiate_scan.apply_async(',
            source,
            "start_organization_scan must call initiate_scan_temporal — not initiate_scan.apply_async"
        )

    def test_org_scan_view_calls_initiate_scan_temporal(self):
        """The start_organization_scan view body must contain initiate_scan_temporal(**kwargs)."""
        source = _read('startScan/views.py')
        # Slice out the start_organization_scan function body
        start = source.find('def start_organization_scan(')
        self.assertNotEqual(start, -1, "start_organization_scan function not found")
        # Find the next top-level decorator or function
        next_marker = source.find('\n@has_permission_decorator', start + 1)
        if next_marker == -1:
            next_marker = source.find('\ndef ', start + len('def start_organization_scan('))
        body = source[start:next_marker if next_marker != -1 else len(source)]
        self.assertIn(
            'initiate_scan_temporal(**kwargs)',
            body,
            "start_organization_scan must call initiate_scan_temporal(**kwargs)"
        )


class TestPhase3B2MonitorRecoveryScan(TestCase):
    """3B-2: monitor_target_task must use initiate_scan_temporal, not initiate_scan.delay."""

    def test_monitor_tasks_does_not_use_initiate_scan_delay(self):
        """reNgine/monitor_tasks.py must not contain initiate_scan.delay anywhere."""
        source = _read('reNgine/monitor_tasks.py')
        self.assertNotIn(
            'initiate_scan.delay(',
            source,
            "monitor_target_task must call initiate_scan_temporal — not initiate_scan.delay"
        )

    def test_monitor_tasks_imports_initiate_scan_temporal(self):
        """The follow-up scan block must import initiate_scan_temporal (not initiate_scan)."""
        source = _read('reNgine/monitor_tasks.py')
        self.assertIn(
            'from reNgine.tasks import initiate_scan_temporal',
            source,
            "monitor_tasks.py must import initiate_scan_temporal for the follow-up scan path"
        )

    def test_monitor_tasks_calls_initiate_scan_temporal(self):
        """monitor_target_task body must contain initiate_scan_temporal( calls."""
        source = _read('reNgine/monitor_tasks.py')
        self.assertIn(
            'initiate_scan_temporal(',
            source,
            "monitor_target_task must call initiate_scan_temporal() for follow-up scans"
        )

    def test_monitor_recovery_scans_wrapped_in_try_except(self):
        """Both follow-up scan paths must be wrapped in try/except to preserve non-fatal semantics."""
        source = _read('reNgine/monitor_tasks.py')
        self.assertIn(
            'Failed to start targeted recovery scan',
            source,
            "targeted recovery scan must be wrapped in try/except with a warning log"
        )
        self.assertIn(
            'Failed to start full recovery scan',
            source,
            "full recovery scan must be wrapped in try/except with a warning log"
        )


class TestPhase3B4BruteForceChaining(TestCase):
    """3B-4: brute_force_scan must be called via .apply() not .delay() inside nmap (auth portal chaining) and firewall_vpn_scan.

    Note: the auth-portal brute-force chain lives inside the `nmap` task function, not inside a function
    literally named `nuclei_scan`.  The `nuclei_scan` Celery task delegates to
    `nuclei_individual_severity_module` and contains no brute-force chaining of its own.
    """

    def _get_function_body(self, source, func_name):
        """Slice a function body from source up to the next @app.task decorator."""
        start = source.find(f'def {func_name}(')
        if start == -1:
            return ''
        next_task = source.find('\n@app.task', start + 1)
        return source[start:next_task if next_task != -1 else len(source)]

    def test_nmap_does_not_use_brute_force_delay(self):
        """nmap (auth portal chaining site) must not call brute_force_scan.delay — it must use .apply()."""
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'nmap')
        self.assertNotIn(
            'brute_force_scan.delay(',
            body,
            "nmap must not call brute_force_scan.delay — use .apply()"
        )

    def test_nmap_uses_brute_force_apply(self):
        """nmap (auth portal chaining site) must call brute_force_scan(...) for in-task chaining."""
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'nmap')
        self.assertIn(
            'brute_force_scan(self,',
            body,
            "nmap must call brute_force_scan(self, ...) for in-task chaining"
        )

    def test_firewall_vpn_scan_does_not_use_brute_force_delay(self):
        """firewall_vpn_scan must not call brute_force_scan.delay — it must call it directly."""
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'firewall_vpn_scan')
        self.assertNotIn(
            'brute_force_scan.delay(',
            body,
            "firewall_vpn_scan must not call brute_force_scan.delay"
        )

    def test_firewall_vpn_scan_uses_brute_force_apply(self):
        """firewall_vpn_scan must call brute_force_scan(...) directly for in-task chaining."""
        source = _read('reNgine/tasks.py')
        body = self._get_function_body(source, 'firewall_vpn_scan')
        self.assertIn(
            'brute_force_scan(self,',
            body,
            "firewall_vpn_scan must call brute_force_scan(self, ...) for in-task chaining"
        )
