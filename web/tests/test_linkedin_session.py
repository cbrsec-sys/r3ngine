import json
import os
import tempfile
from unittest.mock import MagicMock, patch
from django.test import TestCase
from dashboard.models import LinkedInCredentials


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
