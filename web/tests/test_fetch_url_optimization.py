from django.test import TestCase
from django.utils import timezone

from reNgine.common_func import get_http_urls, parse_fetched_url_line
from scanEngine.models import EngineType
from startScan.models import EndPoint, ScanHistory, Subdomain
from targetApp.models import Domain


class ParseFetchedUrlLineTests(TestCase):
    def test_gospider_line_reconstructs_full_path(self):
        line = 'https://example.com] - /admin/login'
        url = parse_fetched_url_line(line)
        self.assertEqual(url, 'https://example.com/admin/login')

    def test_invalid_gospider_line_returns_none(self):
        self.assertIsNone(parse_fetched_url_line('not-a-url'))

    def test_starting_point_filter(self):
        line = 'https://example.com/api/v1/users'
        url = parse_fetched_url_line(line, starting_point_path='/api/')
        self.assertEqual(url, 'https://example.com/api/v1/users')
        self.assertIsNone(parse_fetched_url_line('https://example.com/other', '/api/'))


class GetHttpUrlsAliveFilterTests(TestCase):
    def setUp(self):
        self.domain = Domain.objects.create(name='alive-filter.example.com')
        self.engine = EngineType.objects.create(engine_name='Alive Filter Engine')
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_status=1,
            start_scan_date=timezone.now(),
            scan_type=self.engine,
        )
        self.sub = Subdomain.objects.create(
            name='alive-filter.example.com',
            scan_history=self.scan,
            target_domain=self.domain,
        )

    def _make_ctx(self):
        return {
            'domain_id': self.domain.id,
            'scan_history_id': self.scan.id,
        }

    def test_is_alive_uses_database_filter(self):
        EndPoint.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            subdomain=self.sub,
            http_url='https://alive-filter.example.com/ok',
            http_status=200,
        )
        EndPoint.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            subdomain=self.sub,
            http_url='https://alive-filter.example.com/dead',
            http_status=404,
        )
        urls = get_http_urls(is_alive=True, ctx=self._make_ctx())
        self.assertEqual(urls, ['https://alive-filter.example.com/ok'])
