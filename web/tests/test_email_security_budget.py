"""The email security activity must return partial results, never overrun its timeout.

Probing every SMTP host costs up to ~2.5 minutes (relay, STARTTLS, certificate, VRFY
enumeration). On a target with many mail hosts the activity used to outlive its
start_to_close_timeout: Temporal discarded the finished run, retried from scratch, and
each killed attempt left a thread holding one of the worker's ten activity slots until
the whole scan stalled.
"""
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from scanEngine.models import EngineType
from startScan.models import IpAddress, Port, ScanHistory, Subdomain
from targetApp.models import Domain

_CLEAN_SPF = {'found': True, 'record': 'v=spf1 -all', 'weak': False}
_CLEAN_DMARC = {'found': True, 'record': 'v=DMARC1; p=reject', 'policy': 'reject'}
_CLEAN_DKIM = {'found': True, 'selector': 'default', 'record': 'v=DKIM1'}
_NO_RELAY = {'open_relay': False, 'banner': None}


class EmailSecurityBudgetTests(TestCase):

    def setUp(self) -> None:
        self.domain = Domain.objects.create(
            name='test.example', insert_date=timezone.now()
        )
        engine = EngineType.objects.create(engine_name='es-engine', yaml_configuration='')
        self.scan = ScanHistory.objects.create(
            domain=self.domain, scan_type=engine, scan_status=1,
            start_scan_date=timezone.now(),
        )
        self.ctx = {'scan_history_id': self.scan.id, 'domain_name': self.domain.name}

        # Two mail hosts on port 25, the shape that made the activity overrun.
        for index, host in enumerate(('mx1.test.example', 'mx2.test.example'), start=1):
            port = Port.objects.create(number=25, service_name='smtp')
            ip = IpAddress.objects.create(address='192.0.2.%d' % index)
            ip.ports.add(port)
            subdomain = Subdomain.objects.create(
                scan_history=self.scan, target_domain=self.domain, name=host,
                discovered_date=timezone.now(),
            )
            subdomain.ip_addresses.add(ip)

    def _run(self) -> dict:
        from reNgine.temporal.activities import _run_email_security_sync
        with patch('reNgine.tasks.email_security.check_spf', return_value=_CLEAN_SPF), \
                patch('reNgine.tasks.email_security.check_dmarc', return_value=_CLEAN_DMARC), \
                patch('reNgine.tasks.email_security.check_dkim', return_value=_CLEAN_DKIM), \
                patch('reNgine.tasks.email_security.assess_spoofability', return_value=[]):
            return _run_email_security_sync(self.ctx)

    @patch('reNgine.temporal.activities.EMAIL_SECURITY_BUDGET_SECONDS', 0)
    @patch('reNgine.tasks.email_security.smtp_user_enum')
    @patch('reNgine.tasks.email_security.swaks_relay_test')
    def test_spent_budget_stops_before_probing(self, mock_relay, mock_enum) -> None:
        result = self._run()

        mock_relay.assert_not_called()
        mock_enum.assert_not_called()
        self.assertTrue(result['partial'])
        self.assertEqual(result['smtp_hosts_checked'], 0)

    @patch('reNgine.tasks.email_security.smtp_user_enum', return_value={'users_found': {}, 'raw': ''})
    @patch('reNgine.tasks.email_security.swaks_starttls_check', return_value={'starttls_supported': True})
    @patch('reNgine.tasks.email_security.swaks_relay_test', return_value=_NO_RELAY)
    def test_within_budget_probes_every_host(self, mock_relay, _mock_tls, mock_enum) -> None:
        result = self._run()

        self.assertEqual(mock_relay.call_count, 2)
        mock_enum.assert_called_once()
        self.assertFalse(result['partial'])
        self.assertEqual(result['smtp_hosts_checked'], 2)
