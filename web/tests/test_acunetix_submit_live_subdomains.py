"""Automatic submission of live subdomains to Acunetix.

Covers which subdomains qualify as "live and externally reachable", the
re-submission window that stops a daily scan re-registering the same host, and
the timeline record written for every decision.
"""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dashboard.models import AcunetixTargetSubmission
from scanEngine.models import EngineType
from startScan.models import Command, IpAddress, ScanActivity, ScanHistory, Subdomain
from targetApp.models import Domain


class _FakeTask:
    """Minimal stand-in for the Temporal task proxy passed as `self`."""

    def __init__(self, scan=None, activity=None) -> None:
        self.scan = scan
        self.activity = activity
        self.error = None
        self.yaml_configuration = {}


class LiveSubdomainSelectionTests(TestCase):

    def setUp(self) -> None:
        self.domain = Domain.objects.create(name='test.example', insert_date=timezone.now())
        engine = EngineType.objects.create(engine_name='acu-engine', yaml_configuration='')
        self.scan = ScanHistory.objects.create(
            domain=self.domain, scan_type=engine, scan_status=1,
            start_scan_date=timezone.now(),
        )

    def _subdomain(self, name: str, http_status: int = 200, http_url: str = None, ip: str = None,
                   is_private: bool = False) -> Subdomain:
        sub = Subdomain.objects.create(
            scan_history=self.scan, target_domain=self.domain, name=name,
            http_status=http_status,
            http_url=http_url if http_url is not None else f'https://{name}',
            discovered_date=timezone.now(),
        )
        if ip:
            address = IpAddress.objects.create(address=ip, is_private=is_private)
            sub.ip_addresses.add(address)
        return sub

    def test_only_live_reachable_subdomains_are_selected(self) -> None:
        from reNgine.tasks import get_live_subdomains_for_submission

        alive = self._subdomain('www.test.example', 200, ip='192.0.2.10')
        redirect = self._subdomain('old.test.example', 301, ip='192.0.2.11')
        no_ip = self._subdomain('cdn.test.example', 200)
        self._subdomain('dead.test.example', 0, ip='192.0.2.12')
        self._subdomain('gone.test.example', 404, ip='192.0.2.13')
        self._subdomain('broken.test.example', 500, ip='192.0.2.14')
        self._subdomain('internal.test.example', 200, ip='10.0.0.5', is_private=True)
        self._subdomain('nourl.test.example', 200, http_url='', ip='192.0.2.15')

        selected = {s.name for s in get_live_subdomains_for_submission(self.scan.id)}

        self.assertEqual(
            selected,
            {alive.name, redirect.name, no_ip.name},
            'live = HTTP answered with 0 < status < 500 and not 404, has a URL, '
            'and is not resolved only to private addresses',
        )


class AcunetixSubmissionTests(TestCase):

    def setUp(self) -> None:
        self.domain = Domain.objects.create(name='sub.example', insert_date=timezone.now())
        engine = EngineType.objects.create(engine_name='acu-engine2', yaml_configuration='')
        self.scan = ScanHistory.objects.create(
            domain=self.domain, scan_type=engine, scan_status=1,
            start_scan_date=timezone.now(),
        )
        self.activity = ScanActivity.objects.create(
            scan_of=self.scan, name='acunetix_submit', title='Acunetix Target Submission',
            tier=2, status=1, time=timezone.now(), time_started=timezone.now(),
        )
        for name in ('a.sub.example', 'b.sub.example'):
            Subdomain.objects.create(
                scan_history=self.scan, target_domain=self.domain, name=name,
                http_status=200, http_url=f'https://{name}', discovered_date=timezone.now(),
            )
        self.ctx = {
            'scan_history_id': self.scan.id,
            'yaml_configuration': {
                'vulnerability_scan': {'acunetix': {'resubmit_after_days': 3}}
            },
        }

    def _task(self) -> _FakeTask:
        return _FakeTask(scan=self.scan, activity=self.activity)

    def _run(self, task: _FakeTask):
        from reNgine.tasks import acunetix_submit_live_subdomains
        return acunetix_submit_live_subdomains(task, ctx=self.ctx)

    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target', return_value='tgt-1')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_each_live_subdomain_is_submitted_once_and_recorded(self, mock_keys, mock_create) -> None:
        mock_keys.objects.first.return_value = type(
            'Creds', (), {'server_url': 'https://acu.local', 'api_key': 'k'}
        )()

        task = self._task()
        self.assertTrue(self._run(task))

        self.assertEqual(mock_create.call_count, 2)
        self.assertEqual(AcunetixTargetSubmission.objects.count(), 2)
        commands = Command.objects.filter(activity=self.activity)
        self.assertEqual(commands.count(), 2)
        self.assertTrue(all('SUBMITTED' in c.output for c in commands))

    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target', return_value='tgt-1')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_host_submitted_inside_the_window_is_skipped(self, mock_keys, mock_create) -> None:
        mock_keys.objects.first.return_value = type(
            'Creds', (), {'server_url': 'https://acu.local', 'api_key': 'k'}
        )()
        AcunetixTargetSubmission.objects.create(
            host='a.sub.example', acunetix_target_id='old-1',
            last_submitted_at=timezone.now() - timedelta(days=1),
        )

        self._run(self._task())

        self.assertEqual(mock_create.call_count, 1, 'only the host outside the window is sent')
        skipped = Command.objects.filter(activity=self.activity, output__startswith='SKIPPED')
        self.assertEqual(skipped.count(), 1)
        self.assertIn('a.sub.example', skipped.first().command)

    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target', return_value='tgt-2')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_host_submitted_before_the_window_is_sent_again(self, mock_keys, mock_create) -> None:
        mock_keys.objects.first.return_value = type(
            'Creds', (), {'server_url': 'https://acu.local', 'api_key': 'k'}
        )()
        stale = AcunetixTargetSubmission.objects.create(
            host='a.sub.example', acunetix_target_id='old-1',
            last_submitted_at=timezone.now() - timedelta(days=5),
        )

        self._run(self._task())

        self.assertEqual(mock_create.call_count, 2)
        stale.refresh_from_db()
        self.assertEqual(stale.acunetix_target_id, 'tgt-2')
        self.assertEqual(stale.submission_count, 2)

    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_missing_credentials_fail_with_a_reason(self, mock_keys) -> None:
        mock_keys.objects.first.return_value = None

        task = self._task()
        self.assertFalse(self._run(task))
        self.assertIn('Acunetix API keys', task.error or '')


class AcunetixSubmitTaskPlanTests(TestCase):
    """The timeline row must be planned up front, so it shows as pending."""

    def test_planned_only_when_enabled_and_http_crawl_runs(self) -> None:
        from reNgine.task_plan import build_scan_task_plan, get_task_tier

        enabled = {'vulnerability_scan': {'acunetix': {'submit_live_subdomains': True}}}
        names = [e['name'] for e in build_scan_task_plan(['http_crawl'], enabled)]
        self.assertIn('acunetix_submit', names)

        disabled = {'vulnerability_scan': {'acunetix': {'submit_live_subdomains': False}}}
        names = [e['name'] for e in build_scan_task_plan(['http_crawl'], disabled)]
        self.assertNotIn('acunetix_submit', names)

        names = [e['name'] for e in build_scan_task_plan(['port_scan'], enabled)]
        self.assertNotIn('acunetix_submit', names, 'liveness comes from http_crawl')

        self.assertEqual(get_task_tier('acunetix_submit'), 2)
