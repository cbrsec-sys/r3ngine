import json
import os
import tempfile
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.utils import timezone
from dashboard.models import LinkedInCredentials, HunterIOAPIKey
from targetApp.models import Domain
from startScan.models import ScanHistory
from scanEngine.models import EngineType


class TestLinkedInCredentialsModel(TestCase):

    def test_model_has_session_fields(self):
        session = LinkedInCredentials.objects.create(
            username='operator@example.com',
            cookies_json='[]',
            state_file_path='/var/scan_results/context/linkedin/storage_state.json',
            is_valid=False,
        )
        self.assertEqual(session.username, 'operator@example.com')
        self.assertEqual(session.cookies_json, '[]')
        self.assertEqual(session.state_file_path, '/var/scan_results/context/linkedin/storage_state.json')
        self.assertFalse(session.is_valid)
        self.assertIsNone(session.last_validated_at)

    def test_model_has_no_password_field(self):
        field_names = [f.name for f in LinkedInCredentials._meta.get_fields()]
        self.assertNotIn('password', field_names)
        self.assertIn('cookies_json', field_names)
        self.assertIn('state_file_path', field_names)
        self.assertIn('is_valid', field_names)
        self.assertIn('last_validated_at', field_names)


class TestLinkedInScraperAuth(TestCase):

    def setUp(self):
        self.session = LinkedInCredentials.objects.create(
            username='operator@example.com',
            cookies_json='',
            state_file_path='',
            is_valid=False,
        )

    def test_authenticate_returns_false_when_no_state_or_cookies(self):
        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright'):
                from reNgine.osint.linkedin_intelligence import LinkedInScraper
                scraper = LinkedInScraper(session=self.session, hunter_key='key')
                scraper._browser = MagicMock()
                result = scraper.authenticate()

        self.assertFalse(result)
        self.assertFalse(LinkedInCredentials.objects.get(pk=self.session.pk).is_valid)
        self.assertEqual(len(scraper.notes), 1)
        self.assertIn('LinkedIn intelligence skipped', scraper.notes[0])

    def test_try_storage_state_returns_false_when_file_missing(self):
        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright'):
                from reNgine.osint.linkedin_intelligence import LinkedInScraper
                scraper = LinkedInScraper(session=self.session, hunter_key='key')
                scraper._browser = MagicMock()
                self.session.state_file_path = '/nonexistent/path/state.json'
                result = scraper._try_storage_state()
        self.assertFalse(result)

    def test_try_cookie_injection_returns_false_when_no_cookies(self):
        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright'):
                from reNgine.osint.linkedin_intelligence import LinkedInScraper
                scraper = LinkedInScraper(session=self.session, hunter_key='key')
                scraper._browser = MagicMock()
                result = scraper._try_cookie_injection()
        self.assertFalse(result)

    def test_try_cookie_injection_returns_false_on_invalid_json(self):
        self.session.cookies_json = 'not-valid-json'
        self.session.save()
        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright'):
                from reNgine.osint.linkedin_intelligence import LinkedInScraper
                scraper = LinkedInScraper(session=self.session, hunter_key='key')
                scraper._browser = MagicMock()
                result = scraper._try_cookie_injection()
        self.assertFalse(result)

    def test_try_cookie_injection_calls_add_cookies_and_validates(self):
        cookies = [{'name': 'li_at', 'value': 'tok', 'domain': '.linkedin.com', 'path': '/'}]
        self.session.cookies_json = json.dumps(cookies)
        self.session.save()

        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.url = 'https://www.linkedin.com/feed/'
        mock_page.query_selector.return_value = None

        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright'):
                from reNgine.osint.linkedin_intelligence import LinkedInScraper
                scraper = LinkedInScraper(session=self.session, hunter_key='key')
                scraper._browser = mock_browser
                with patch.object(scraper, '_save_state'):
                    result = scraper._try_cookie_injection()

        mock_context.add_cookies.assert_called_once_with(cookies)
        self.assertTrue(result)

    def test_discover_employees_returns_empty_on_auth_failure(self):
        scan_history = MagicMock()
        scan_history.results_dir = tempfile.mkdtemp()

        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright'):
                from reNgine.osint.linkedin_intelligence import LinkedInScraper
                scraper = LinkedInScraper(session=self.session, hunter_key='key')
                scraper._browser = MagicMock()
                employees = scraper.discover_employees('TestCorp', 'testcorp.com', scan_history)

        self.assertEqual(employees, [])

    def test_format_email_first_last_pattern(self):
        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright'):
                from reNgine.osint.linkedin_intelligence import LinkedInScraper
                scraper = LinkedInScraper(session=self.session, hunter_key='key')
        self.assertEqual(scraper.format_email('John Doe', '{first}.{last}', 'example.com'), 'john.doe@example.com')

    def test_format_email_initial_pattern(self):
        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright'):
                from reNgine.osint.linkedin_intelligence import LinkedInScraper
                scraper = LinkedInScraper(session=self.session, hunter_key='key')
        self.assertEqual(scraper.format_email('Jane Smith', '{f}{last}', 'corp.com'), 'jsmith@corp.com')


class TestRunLinkedint(TestCase):

    def _make_scan(self):
        domain = Domain.objects.create(name='target.example.com')
        engine = EngineType.objects.create(engine_name='LinkedIn Test Engine')
        return ScanHistory.objects.create(
            domain=domain,
            scan_status=1,  # 1 = RUNNING_TASK
            start_scan_date=timezone.now(),
            scan_type=engine,
        )

    def test_returns_empty_list_when_no_session_configured(self):
        HunterIOAPIKey.objects.create(key='hunter-key')
        scan = self._make_scan()
        from reNgine.osint_tasks import run_linkedint
        result = run_linkedint('TargetCorp', scan.id)
        self.assertEqual(result, [])

    def test_returns_empty_list_when_no_hunter_key(self):
        LinkedInCredentials.objects.create(
            id=1, username='u', cookies_json='[]', is_valid=False
        )
        scan = self._make_scan()
        from reNgine.osint_tasks import run_linkedint
        result = run_linkedint('TargetCorp', scan.id)
        self.assertEqual(result, [])

    @patch('reNgine.osint_tasks.LinkedInScraper')
    def test_returns_result_string_on_success(self, mock_cls):
        LinkedInCredentials.objects.create(
            id=1, username='u', cookies_json='[]', is_valid=False
        )
        HunterIOAPIKey.objects.create(key='hunter-key')
        scan = self._make_scan()

        mock_scraper = MagicMock()
        mock_scraper.__enter__ = MagicMock(return_value=mock_scraper)
        mock_scraper.__exit__ = MagicMock(return_value=False)
        mock_scraper.discover_employees.return_value = [
            {'name': 'Alice Smith', 'designation': 'Engineer', 'email': 'a.smith@target.example.com'}
        ]
        mock_scraper.notes = []
        mock_cls.return_value = mock_scraper

        from reNgine.osint_tasks import run_linkedint
        result = run_linkedint('TargetCorp', scan.id)
        self.assertEqual(result, ['LinkedIn Intelligence processed 1 employees for TargetCorp'])

    @patch('reNgine.osint_tasks.LinkedInScraper')
    def test_notes_are_logged_on_auth_failure(self, mock_cls):
        LinkedInCredentials.objects.create(
            id=1, username='u', cookies_json='', is_valid=False
        )
        HunterIOAPIKey.objects.create(key='hunter-key')
        scan = self._make_scan()

        mock_scraper = MagicMock()
        mock_scraper.__enter__ = MagicMock(return_value=mock_scraper)
        mock_scraper.__exit__ = MagicMock(return_value=False)
        mock_scraper.discover_employees.return_value = []
        mock_scraper.notes = [
            '[OSINT][LinkedIn] Session invalid and cookie injection failed — LinkedIn intelligence skipped.'
        ]
        mock_cls.return_value = mock_scraper

        from reNgine.osint_tasks import run_linkedint
        with self.assertLogs('reNgine.osint_tasks', level='WARNING') as cm:
            result = run_linkedint('TargetCorp', scan.id)
        self.assertIn('[OSINT][LinkedIn]', ' '.join(cm.output))
        self.assertEqual(result, ['LinkedIn Intelligence processed 0 employees for TargetCorp'])

    @patch('reNgine.osint_tasks.LinkedInScraper')
    def test_never_raises_on_unexpected_exception(self, mock_cls):
        LinkedInCredentials.objects.create(
            id=1, username='u', cookies_json='[]', is_valid=False
        )
        HunterIOAPIKey.objects.create(key='hunter-key')
        scan = self._make_scan()
        mock_cls.side_effect = RuntimeError("Playwright crashed unexpectedly")

        from reNgine.osint_tasks import run_linkedint
        result = run_linkedint('TargetCorp', scan.id)
        self.assertEqual(result, [])
