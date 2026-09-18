"""Automatic submission of live subdomains to Acunetix.

Covers which subdomains qualify as "live and externally reachable", the
re-submission window that stops a daily scan re-registering the same host, and
the timeline record written for every decision.
"""
import unittest
from datetime import timedelta
from unittest.mock import patch

import requests
from django.db import IntegrityError
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


class _FakeResponse:
    """Stand-in for a `requests` response — only what the task reads."""

    def __init__(self, status_code: int, payload: dict = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = ''

    def json(self) -> dict:
        return self._payload


def _creds(server_url: str = 'https://acu.local', api_key: str = 'k'):
    return type('Creds', (), {'server_url': server_url, 'api_key': api_key})()


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


class _SubmissionTestBase(TestCase):
    """Two live subdomains, a planned timeline row, and the task plumbing."""

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
        self.ctx = self._ctx()

    def _ctx(self, **acunetix_overrides) -> dict:
        config = {'resubmit_after_days': 3}
        config.update(acunetix_overrides)
        return {
            'scan_history_id': self.scan.id,
            'yaml_configuration': {'vulnerability_scan': {'acunetix': config}},
        }

    def _task(self) -> _FakeTask:
        return _FakeTask(scan=self.scan, activity=self.activity)

    def _run(self, task: _FakeTask, ctx: dict = None):
        from reNgine.tasks import acunetix_submit_live_subdomains
        return acunetix_submit_live_subdomains(task, ctx=ctx or self.ctx)


class AcunetixSubmissionTests(_SubmissionTestBase):

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


class AcunetixSubmissionIsolationTests(_SubmissionTestBase):
    """One host that fails must not take the rest of the submission run with it."""

    @patch('reNgine.tasks.acunetix._start_acunetix_scan_direct')
    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target', return_value='tgt-1')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_a_failing_scan_start_does_not_skip_the_remaining_hosts(
            self, mock_keys, mock_create, mock_start) -> None:
        mock_keys.objects.first.return_value = _creds()
        mock_start.side_effect = [
            requests.exceptions.ReadTimeout('Read timed out'),
            {'scan_id': 'scan-2'},
        ]

        task = self._task()
        self.assertTrue(self._run(task, self._ctx(start_scan_on_submit=True)))

        self.assertEqual(mock_start.call_count, 2, 'the second host is still attempted')
        self.assertEqual(
            [r.host for r in AcunetixTargetSubmission.objects.all()],
            ['b.sub.example'],
        )
        failed = Command.objects.filter(activity=self.activity, output__startswith='FAILED')
        self.assertEqual(failed.count(), 1)
        self.assertIn('a.sub.example', failed.first().command)
        self.assertIn('ReadTimeout', failed.first().output)

    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target', return_value='tgt-1')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_a_colliding_submission_row_does_not_skip_the_remaining_hosts(
            self, mock_keys, mock_create) -> None:
        mock_keys.objects.first.return_value = _creds()
        real_get_or_create = AcunetixTargetSubmission.objects.get_or_create

        def _collide_on_the_first_host(**kwargs):
            # What a concurrent scan submitting the same host looks like:
            # `host` is unique, so the loser of the race gets an IntegrityError.
            if kwargs.get('host') == 'a.sub.example':
                raise IntegrityError('duplicate key value violates unique constraint')
            return real_get_or_create(**kwargs)

        task = self._task()
        with patch.object(
            AcunetixTargetSubmission.objects, 'get_or_create',
            side_effect=_collide_on_the_first_host,
        ):
            self.assertTrue(self._run(task))

        self.assertEqual(
            [r.host for r in AcunetixTargetSubmission.objects.all()],
            ['b.sub.example'],
        )
        outputs = {
            c.command: c.output
            for c in Command.objects.filter(activity=self.activity)
        }
        self.assertTrue(outputs['acunetix submit a.sub.example'].startswith('FAILED'))
        self.assertIn('IntegrityError', outputs['acunetix submit a.sub.example'])
        self.assertTrue(outputs['acunetix submit b.sub.example'].startswith('SUBMITTED'))

    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_the_task_fails_only_when_every_host_failed(self, mock_keys, mock_create) -> None:
        mock_keys.objects.first.return_value = _creds()
        mock_create.side_effect = requests.exceptions.ConnectionError('unreachable')

        task = self._task()
        self.assertFalse(self._run(task))
        self.assertIn('All 2', task.error or '')
        self.assertEqual(AcunetixTargetSubmission.objects.count(), 0)


class ResubmitWindowTests(_SubmissionTestBase):
    """The window is the only thing stopping a daily scan re-flooding Acunetix."""

    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target', return_value='tgt-1')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_a_zero_window_is_clamped_instead_of_resubmitting_everything(
            self, mock_keys, mock_create) -> None:
        mock_keys.objects.first.return_value = _creds()
        AcunetixTargetSubmission.objects.create(
            host='a.sub.example', acunetix_target_id='old-1',
            last_submitted_at=timezone.now() - timedelta(hours=1),
        )

        task = self._task()
        self.assertTrue(self._run(task, self._ctx(resubmit_after_days=0)))

        self.assertEqual(
            mock_create.call_count, 1,
            'a 0 day window would put the cutoff at "now" and re-submit every host',
        )
        skipped = Command.objects.filter(activity=self.activity, output__startswith='SKIPPED')
        self.assertEqual(skipped.count(), 1)
        self.assertIn('a.sub.example', skipped.first().command)

    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target', return_value='tgt-1')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_a_malformed_window_falls_back_to_the_default(self, mock_keys, mock_create) -> None:
        mock_keys.objects.first.return_value = _creds()
        AcunetixTargetSubmission.objects.create(
            host='a.sub.example', acunetix_target_id='old-1',
            last_submitted_at=timezone.now() - timedelta(days=2),
        )

        task = self._task()
        self.assertTrue(self._run(task, self._ctx(resubmit_after_days='soon')))

        self.assertIsNone(task.error, 'a bad yaml value must not kill the task')
        self.assertEqual(
            mock_create.call_count, 1,
            'the 3 day default still covers a host submitted 2 days ago',
        )


class ResolveResubmitWindowTests(unittest.TestCase):

    def test_values_are_clamped_and_sanitised(self) -> None:
        from reNgine.tasks.acunetix import (
            DEFAULT_RESUBMIT_AFTER_DAYS, MIN_RESUBMIT_AFTER_DAYS,
            _resolve_resubmit_after_days,
        )

        self.assertEqual(_resolve_resubmit_after_days(7), 7)
        self.assertEqual(_resolve_resubmit_after_days('7'), 7)
        self.assertEqual(_resolve_resubmit_after_days(0), MIN_RESUBMIT_AFTER_DAYS)
        self.assertEqual(_resolve_resubmit_after_days(-5), MIN_RESUBMIT_AFTER_DAYS)
        self.assertEqual(_resolve_resubmit_after_days(None), DEFAULT_RESUBMIT_AFTER_DAYS)
        self.assertEqual(_resolve_resubmit_after_days('soon'), DEFAULT_RESUBMIT_AFTER_DAYS)
        self.assertEqual(_resolve_resubmit_after_days([3]), DEFAULT_RESUBMIT_AFTER_DAYS)


class AcunetixScanFailureTests(TestCase):
    """`acunetix_scan` error handling.

    `error_message` is served to every role by the scan summary API (unlike
    `traceback`), so the reason stored there must not carry the AWVS server URL
    or credential material — security rule 8.1.
    """

    def setUp(self) -> None:
        self.domain = Domain.objects.create(name='scan.example', insert_date=timezone.now())
        engine = EngineType.objects.create(engine_name='acu-engine3', yaml_configuration='')
        self.scan = ScanHistory.objects.create(
            domain=self.domain, scan_type=engine, scan_status=1,
            start_scan_date=timezone.now(),
        )

    def _run(self, task: _FakeTask):
        from reNgine.tasks import acunetix_scan
        return acunetix_scan(task, domain_id=self.domain.id, scan_history_id=self.scan.id)

    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_request_failure_does_not_expose_the_server_url(self, mock_keys, mock_create) -> None:
        mock_keys.objects.first.return_value = _creds(
            server_url='https://acu.internal.example:3443', api_key='sekret-api-key',
        )
        mock_create.side_effect = requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='acu.internal.example', port=3443): Max retries "
            "exceeded with url: /api/v1/targets (apikey=sekret-api-key)"
        )

        task = _FakeTask(scan=self.scan)
        self.assertFalse(self._run(task))

        self.assertIn('ConnectionError', task.error)
        for leaked in (
            'acu.internal.example', '3443', 'sekret-api-key', 'HTTPSConnectionPool',
        ):
            self.assertNotIn(leaked, task.error)

    @patch('reNgine.tasks.acunetix.save_vulnerability')
    @patch('reNgine.tasks.acunetix._fetch_acunetix_vulnerabilities')
    @patch('reNgine.tasks.acunetix.requests.get')
    @patch('reNgine.tasks.acunetix._start_acunetix_scan_direct',
           return_value={'scan_id': 'scan-1'})
    @patch('reNgine.tasks.acunetix._create_or_reuse_acunetix_target', return_value='tgt-1')
    @patch('reNgine.tasks.acunetix.AcunetixAPIKey')
    def test_findings_collected_before_a_pagination_failure_are_kept(
            self, mock_keys, mock_create, mock_start, mock_get, mock_fetch, mock_save) -> None:
        mock_keys.objects.first.return_value = _creds()

        def _responses(url, **kwargs):
            if '/vulnerabilities/' in url:
                return _FakeResponse(200, {
                    'vt_name': 'Partial finding',
                    'severity': 2,
                    'references': [],
                })
            return _FakeResponse(200, {
                'current_session': {'status': 'completed', 'scan_session_id': 'sess-1'},
            })

        mock_get.side_effect = _responses
        # Page 1 of the primary URL succeeded, page 2 returned 400; neither
        # fallback URL knows this scan, so nothing replaces the partial list.
        mock_fetch.side_effect = [
            (_FakeResponse(400), [{'vuln_id': 'v-1'}]),
            (_FakeResponse(400), []),
            (_FakeResponse(404), []),
        ]

        self.assertTrue(self._run(_FakeTask(scan=self.scan)))

        self.assertEqual(mock_fetch.call_count, 3)
        self.assertEqual(
            mock_save.call_count, 1,
            'the finding read before the pagination failure must not be discarded',
        )
        self.assertEqual(mock_save.call_args.kwargs['name'], 'Partial finding')


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
