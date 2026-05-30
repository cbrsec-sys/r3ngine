from django.test import SimpleTestCase
from reNgine.task_plan import build_scan_task_plan
from reNgine.definitions import INITIATED_TASK

MINIMAL_YAML = {
    'subdomain_discovery': {'uses_tools': ['subfinder']},
    'port_scan': {},
}
MINIMAL_TASKS = ['subdomain_discovery', 'port_scan']

FULL_YAML = {
    'subdomain_discovery': {},
    'http_crawl': {},
    'port_scan': {},
    'vulnerability_scan': {
        'run_nuclei': True,
        'run_dalfox': True,
        'run_crlfuzz': False,
        'run_wpscan': True,
        'run_s3scanner': True,
        'run_vigolium': True,
        'run_acunetix': False,
        'vigolium_discovery': {'run_vigolium_discovery': True},
        'vigolium_analysis': {'run_vigolium_analysis': True},
    },
    'fetch_url': {},
    'screenshot': {},
    'dir_file_fuzz': {},
    'web_api_discovery': {},
    'waf_detection': {},
    'secret_scanning': {},
}
FULL_TASKS = list(FULL_YAML.keys())


class TestBuildScanTaskPlan(SimpleTestCase):

    def test_minimal_config_produces_expected_tasks(self):
        plan = build_scan_task_plan(MINIMAL_TASKS, MINIMAL_YAML)
        names = [t['name'] for t in plan]
        self.assertIn('subdomain_discovery', names)
        self.assertIn('port_scan', names)
        # Tier-7 tasks always present
        self.assertIn('correlate_vulnerabilities', names)
        self.assertIn('calculate_risk_scores', names)
        # Sub-tasks not present if vulnerability_scan not in tasks
        self.assertNotIn('nuclei_scan', names)

    def test_all_entries_have_required_keys(self):
        plan = build_scan_task_plan(MINIMAL_TASKS, MINIMAL_YAML)
        for entry in plan:
            self.assertIn('name', entry)
            self.assertIn('title', entry)
            self.assertIn('tier', entry)
            self.assertIn('status', entry)
            self.assertEqual(entry['status'], INITIATED_TASK)

    def test_vuln_sub_tasks_included_when_enabled(self):
        plan = build_scan_task_plan(FULL_TASKS, FULL_YAML)
        names = [t['name'] for t in plan]
        self.assertIn('nuclei_scan', names)
        self.assertIn('dalfox_xss_scan', names)
        self.assertIn('wpscan_scan', names)
        self.assertIn('s3scanner', names)
        self.assertIn('vigolium_scan', names)

    def test_vuln_sub_tasks_excluded_when_disabled(self):
        plan = build_scan_task_plan(FULL_TASKS, FULL_YAML)
        names = [t['name'] for t in plan]
        self.assertNotIn('crlfuzz_scan', names)   # run_crlfuzz=False
        self.assertNotIn('acunetix_scan', names)  # run_acunetix=False

    def test_tiers_in_correct_range(self):
        plan = build_scan_task_plan(FULL_TASKS, FULL_YAML)
        for entry in plan:
            self.assertGreaterEqual(entry['tier'], 0)
            self.assertLessEqual(entry['tier'], 7)

    def test_tier_7_always_present(self):
        plan = build_scan_task_plan([], {})
        names = [t['name'] for t in plan]
        for expected in [
            'correlate_vulnerabilities', 'calculate_risk_scores',
            'generate_impact_assessment', 'sync_graph', 'run_apme',
        ]:
            self.assertIn(expected, names)
