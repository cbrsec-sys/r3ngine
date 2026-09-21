from django.test import SimpleTestCase
from reNgine.task_plan import build_scan_task_plan, get_task_tier
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

    def test_vigolium_discovery_is_labelled_with_the_tier_that_runs_it(self):
        """Both workflows schedule it in Tier 2, so the timeline must say Tier 2.

        The timeline groups activity rows by this tier, and the tier retry
        endpoint selects the rows of a tier by it — a Tier 1 label files the row
        under a tier that never ran the task.
        """
        self.assertEqual(get_task_tier('vigolium_discovery'), 2)

    def test_vigolium_discovery_shares_its_tier_with_http_crawl_and_port_scan(self):
        self.assertEqual(
            get_task_tier('vigolium_discovery'), get_task_tier('http_crawl')
        )
        self.assertEqual(
            get_task_tier('vigolium_discovery'), get_task_tier('port_scan')
        )

    def test_vigolium_harvest_stays_in_tier_1(self):
        """Only discovery moved — harvest still runs alongside subdomain enumeration."""
        self.assertEqual(get_task_tier('vigolium_harvest'), 1)
        self.assertEqual(get_task_tier('subdomain_discovery'), 1)

    def test_planned_vigolium_discovery_entry_carries_tier_2(self):
        plan = build_scan_task_plan(FULL_TASKS, FULL_YAML)
        entry = next(e for e in plan if e['name'] == 'vigolium_discovery')
        self.assertEqual(entry['tier'], 2)

    def test_plan_stays_sorted_by_tier(self):
        """The entry moved tier, so its position in the sorted plan moves with it."""
        tiers = [e['tier'] for e in build_scan_task_plan(FULL_TASKS, FULL_YAML)]
        self.assertEqual(tiers, sorted(tiers))

    def test_tier_7_always_present(self):
        plan = build_scan_task_plan([], {})
        names = [t['name'] for t in plan]
        for expected in [
            'correlate_vulnerabilities', 'calculate_risk_scores',
            'generate_impact_assessment', 'sync_graph', 'run_apme',
        ]:
            self.assertIn(expected, names)
