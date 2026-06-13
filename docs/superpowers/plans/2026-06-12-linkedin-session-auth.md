# LinkedIn Session Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the password-based `launch_persistent_context()` LinkedIn scraper with a `storage_state` + cookie-injection approach that never stores a password, and gracefully skips LinkedIn OSINT on auth failure without stopping the scan.

**Architecture:** `LinkedInCredentials` model gains session-state fields (`cookies_json`, `state_file_path`, `is_valid`, `last_validated_at`) and loses `password`. `LinkedInScraper` is rewritten to try `storage_state` first, then cookie injection, then return empty with notes. Three new API endpoints manage upload/status/revocation. A downloadable helper script lets users capture session state locally. `run_linkedint()` never raises — always returns a list.

**Tech Stack:** Django 5.2.3, Playwright sync API, playwright-stealth, React 18 + TypeScript, Axios

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `web/dashboard/models.py` | Modify | Remove `password`, add session fields |
| `web/dashboard/migrations/0017_linkedin_session_fields.py` | Create | Schema migration |
| `web/reNgine/osint/linkedin_intelligence.py` | Rewrite | Session-based `LinkedInScraper` |
| `web/reNgine/osint_tasks.py` | Modify | Update `run_linkedint()` caller |
| `web/api/views.py` | Modify | Add 4 new session management views + helper script constant |
| `web/api/urls.py` | Modify | Register 4 new URL patterns |
| `web/scanEngine/views.py` | Modify | Remove `password` from LinkedIn credential save |
| `web/tests/test_linkedin_session.py` | Create | All tests for this feature |
| `frontend/src/api/linkedin.ts` | Create | Typed API client for LinkedIn session endpoints |
| `frontend/src/components/LinkedInSessionCard.tsx` | Create | Session status + upload UI card |

---

## Task 1: Model — Add Session Fields, Remove Password

**Files:**
- Modify: `web/dashboard/models.py`
- Create: `web/dashboard/migrations/0017_linkedin_session_fields.py`
- Test: `web/tests/test_linkedin_session.py`

- [ ] **Step 1: Write failing tests for the model**

Create `web/tests/test_linkedin_session.py`:

```python
from django.test import TestCase
from dashboard.models import LinkedInCredentials


class TestLinkedInCredentialsModel(TestCase):

    def test_model_has_session_fields(self):
        session = LinkedInCredentials.objects.create(
            username='operator@example.com',
            cookies_json='[]',
            state_file_path='/tmp/state.json',
            is_valid=False,
        )
        self.assertEqual(session.username, 'operator@example.com')
        self.assertEqual(session.cookies_json, '[]')
        self.assertEqual(session.state_file_path, '/tmp/state.json')
        self.assertFalse(session.is_valid)
        self.assertIsNone(session.last_validated_at)

    def test_model_has_no_password_field(self):
        field_names = [f.name for f in LinkedInCredentials._meta.get_fields()]
        self.assertNotIn('password', field_names)
        self.assertIn('cookies_json', field_names)
        self.assertIn('state_file_path', field_names)
        self.assertIn('is_valid', field_names)
        self.assertIn('last_validated_at', field_names)
```

- [ ] **Step 2: Run tests — expect failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session.TestLinkedInCredentialsModel -v 2"
```

Expected: `FieldError` or `AttributeError` — `password` exists, new fields don't.

- [ ] **Step 3: Update the model**

In `web/dashboard/models.py`, replace the `LinkedInCredentials` class (lines 165–171) with:

```python
class LinkedInCredentials(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=500, blank=True, default='')
    cookies_json = models.TextField(blank=True, default='')
    state_file_path = models.CharField(max_length=1000, blank=True, default='')
    last_validated_at = models.DateTimeField(null=True, blank=True)
    is_valid = models.BooleanField(default=False)

    def __str__(self):
        return self.username
```

- [ ] **Step 4: Write the migration**

Create `web/dashboard/migrations/0017_linkedin_session_fields.py`:

```python
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0016_projectdiscoveryapikey'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='linkedincredentials',
            name='password',
        ),
        migrations.AddField(
            model_name='linkedincredentials',
            name='cookies_json',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='linkedincredentials',
            name='state_file_path',
            field=models.CharField(blank=True, default='', max_length=1000),
        ),
        migrations.AddField(
            model_name='linkedincredentials',
            name='last_validated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='linkedincredentials',
            name='is_valid',
            field=models.BooleanField(default=False),
        ),
    ]
```

- [ ] **Step 5: Apply migration**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py migrate dashboard"
```

Expected output ends with: `Applying dashboard.0017_linkedin_session_fields... OK`

- [ ] **Step 6: Run model tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session.TestLinkedInCredentialsModel -v 2"
```

Expected: `OK (2 tests)`

- [ ] **Step 7: Commit**

```bash
git add web/dashboard/models.py web/dashboard/migrations/0017_linkedin_session_fields.py web/tests/test_linkedin_session.py
git commit -m "feat(linkedin): replace password field with session state fields on LinkedInCredentials"
```

---

## Task 2: Rewrite LinkedInScraper

**Files:**
- Rewrite: `web/reNgine/osint/linkedin_intelligence.py`
- Test: `web/tests/test_linkedin_session.py`

- [ ] **Step 1: Add scraper tests to `web/tests/test_linkedin_session.py`**

Append the following to `web/tests/test_linkedin_session.py`:

```python
import json
import os
import tempfile
from unittest.mock import MagicMock, patch, call
from django.test import TestCase
from django.utils import timezone
from dashboard.models import LinkedInCredentials


class TestLinkedInScraperAuth(TestCase):

    def setUp(self):
        self.session = LinkedInCredentials.objects.create(
            username='operator@example.com',
            cookies_json='',
            state_file_path='',
            is_valid=False,
        )

    @patch('reNgine.osint.linkedin_intelligence.os.makedirs')
    @patch('reNgine.osint.linkedin_intelligence.sync_playwright')
    def _make_scraper(self, mock_pw, mock_makedirs, session=None):
        from reNgine.osint.linkedin_intelligence import LinkedInScraper
        s = session or self.session
        scraper = LinkedInScraper(session=s, hunter_key='hunter-test-key')
        mock_browser = MagicMock()
        scraper._playwright = MagicMock()
        scraper._browser = mock_browser
        return scraper, mock_browser

    def test_authenticate_returns_false_when_no_state_or_cookies(self):
        with patch('reNgine.osint.linkedin_intelligence.os.makedirs'):
            with patch('reNgine.osint.linkedin_intelligence.sync_playwright') as mock_pw:
                mock_pw.return_value.start.return_value = MagicMock()
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
```

- [ ] **Step 2: Run scraper tests — expect import error or failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session.TestLinkedInScraperAuth -v 2"
```

Expected: Tests fail — `LinkedInScraper` still has old signature.

- [ ] **Step 3: Rewrite `web/reNgine/osint/linkedin_intelligence.py`**

Replace the entire file with:

```python
import json
import logging
import os
import random
import re
import time
import urllib.parse
from typing import Optional

from django.conf import settings
from django.utils import timezone
from playwright.sync_api import BrowserContext, sync_playwright
from playwright_stealth import stealth_sync

import requests as req

logger = logging.getLogger(__name__)

LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
STATE_DIR = os.path.join(settings.RENGINE_RESULTS, "context", "linkedin")
STATE_FILE_NAME = "storage_state.json"


class LinkedInScraper:
    def __init__(self, session, hunter_key: str):
        self.session = session
        self.hunter_key = hunter_key
        self.notes: list = []
        self._playwright = None
        self._browser = None
        self._context: Optional[BrowserContext] = None
        self._page = None
        os.makedirs(STATE_DIR, exist_ok=True)
        if not self.session.state_file_path:
            self.session.state_file_path = os.path.join(STATE_DIR, STATE_FILE_NAME)

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
            ],
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for resource in (self._context, self._browser, self._playwright):
            if resource:
                try:
                    resource.close() if hasattr(resource, 'close') else resource.stop()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> bool:
        if self._try_storage_state():
            return True
        if self._try_cookie_injection():
            return True
        self.session.is_valid = False
        self.session.save(update_fields=["is_valid"])
        self.notes.append(
            "[OSINT][LinkedIn] Session invalid and cookie injection failed — "
            "LinkedIn intelligence skipped. Re-authenticate via Settings → API Keys."
        )
        return False

    def _try_storage_state(self) -> bool:
        state_path = self.session.state_file_path
        if not state_path or not os.path.isfile(state_path):
            return False
        try:
            self._context = self._browser.new_context(storage_state=state_path)
            self._page = self._context.new_page()
            stealth_sync(self._page)
            if self._validate_session():
                self.session.is_valid = True
                self.session.last_validated_at = timezone.now()
                self.session.save(update_fields=["is_valid", "last_validated_at"])
                return True
            self._close_context()
            return False
        except Exception as exc:
            logger.warning("LinkedIn storage_state load failed: %s", exc)
            self._close_context()
            return False

    def _try_cookie_injection(self) -> bool:
        if not self.session.cookies_json:
            return False
        try:
            cookies = json.loads(self.session.cookies_json)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("LinkedIn cookies_json parse failed: %s", exc)
            return False
        try:
            self._context = self._browser.new_context()
            self._context.add_cookies(cookies)
            self._page = self._context.new_page()
            stealth_sync(self._page)
            if self._validate_session():
                self._save_state()
                return True
            self._close_context()
            return False
        except Exception as exc:
            logger.warning("LinkedIn cookie injection failed: %s", exc)
            self._close_context()
            return False

    def _validate_session(self) -> bool:
        try:
            self._page.goto(LINKEDIN_FEED_URL, wait_until="networkidle", timeout=30000)
            if "login" in self._page.url:
                return False
            if self._page.query_selector('button:has-text("Sign in")'):
                return False
            return True
        except Exception as exc:
            logger.warning("LinkedIn session validation error: %s", exc)
            return False

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.session.state_file_path), exist_ok=True)
            self._context.storage_state(path=self.session.state_file_path)
            self.session.is_valid = True
            self.session.last_validated_at = timezone.now()
            self.session.save(update_fields=["state_file_path", "is_valid", "last_validated_at"])
        except Exception as exc:
            logger.warning("LinkedIn state save failed: %s", exc)

    def _close_context(self):
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        self._page = None

    # ------------------------------------------------------------------
    # Scraping helpers
    # ------------------------------------------------------------------

    def random_sleep(self, min_s: float = 2, max_s: float = 5):
        time.sleep(random.uniform(min_s, max_s))

    def human_scroll(self):
        for _ in range(random.randint(3, 6)):
            self._page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
            self.random_sleep(1, 3)

    def get_hunter_pattern(self, domain: str) -> str:
        try:
            url = (
                f"https://api.hunter.io/v2/domain-search"
                f"?domain={domain}&api_key={self.hunter_key}"
            )
            res = req.get(url, timeout=10)
            data = res.json()
            if "data" in data and "pattern" in data["data"]:
                return data["data"]["pattern"]
        except Exception as exc:
            logger.warning("Failed to fetch Hunter.io pattern: %s", exc)
        return "{first}.{last}"

    def format_email(self, name: str, pattern: str, domain: str) -> str:
        parts = name.split()
        first = parts[0] if parts else ""
        last = parts[-1] if len(parts) > 1 else ""
        email = pattern.replace("{first}", first.lower())
        email = email.replace("{last}", last.lower())
        email = email.replace("{f}", first[0].lower() if first else "")
        email = email.replace("{l}", last[0].lower() if last else "")
        if "@" not in email:
            email = f"{email}@{domain}"
        return email

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def discover_employees(self, company_name: str, domain: str, scan_history) -> list:
        if not self.authenticate():
            return []

        pattern = self.get_hunter_pattern(domain)
        employees_data: list = []

        try:
            search_query = urllib.parse.quote_plus(company_name)
            self._page.goto(
                f"https://www.linkedin.com/search/results/all/?keywords={search_query}",
                wait_until="networkidle",
            )
            self.random_sleep()

            company_link = self._page.query_selector('a[href*="/company/"]')
            if company_link:
                company_url = company_link.get_attribute("href").split("?")[0]
                self._page.goto(f"{company_url}people/", wait_until="networkidle")
                self.random_sleep()
                self.human_scroll()
                for card in self._page.query_selector_all(".org-people-profile-card__profile-info"):
                    name_elem = card.query_selector(".lt-line-clamp--single-line")
                    title_elem = card.query_selector(".lt-line-clamp--multi-line")
                    if name_elem:
                        name = name_elem.inner_text().strip()
                        title = title_elem.inner_text().strip() if title_elem else "Employee"
                        employees_data.append({
                            "name": name,
                            "designation": title,
                            "email": self.format_email(name, pattern, domain),
                        })

            if not employees_data:
                self._page.goto(
                    f"https://www.linkedin.com/search/results/people/?keywords={search_query}",
                    wait_until="networkidle",
                )
                self.random_sleep()
                self.human_scroll()
                for card in self._page.query_selector_all(".entity-result__item"):
                    name_elem = card.query_selector(
                        '.entity-result__title-text a span[aria-hidden="true"]'
                    )
                    title_elem = card.query_selector(".entity-result__primary-subtitle")
                    if name_elem:
                        name = name_elem.inner_text().strip()
                        title = title_elem.inner_text().strip() if title_elem else "Employee"
                        employees_data.append({
                            "name": name,
                            "designation": title,
                            "email": self.format_email(name, pattern, domain),
                        })

        except Exception as exc:
            logger.error("Error during LinkedIn employee discovery: %s", exc)
            self.notes.append(f"[OSINT][LinkedIn] Discovery error: {type(exc).__name__}")

        try:
            safe_name = re.sub(r"[^a-zA-Z0-9]", "_", company_name).lower()
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(
                scan_history.results_dir, "osint",
                f"linkedin_{safe_name}_{timestamp}.png",
            )
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            self._page.screenshot(path=screenshot_path)
        except Exception as exc:
            logger.warning("LinkedIn screenshot failed: %s", exc)

        return employees_data
```

- [ ] **Step 4: Run scraper tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session.TestLinkedInScraperAuth -v 2"
```

Expected: `OK (8 tests)`

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/osint/linkedin_intelligence.py web/tests/test_linkedin_session.py
git commit -m "feat(linkedin): rewrite LinkedInScraper with session-state + cookie injection auth"
```

---

## Task 3: Update `run_linkedint()` Caller

**Files:**
- Modify: `web/reNgine/osint_tasks.py`
- Test: `web/tests/test_linkedin_session.py`

- [ ] **Step 1: Add caller tests to `web/tests/test_linkedin_session.py`**

Append to `web/tests/test_linkedin_session.py`:

```python
from unittest.mock import MagicMock, patch
from django.test import TestCase
from dashboard.models import LinkedInCredentials, HunterIOAPIKey
from targetApp.models import Domain
from startScan.models import ScanHistory


class TestRunLinkedint(TestCase):

    def _make_scan(self):
        domain = Domain.objects.create(name='target.example.com')
        return ScanHistory.objects.create(domain=domain, scan_status='running')

    def test_returns_empty_list_when_no_session_configured(self):
        HunterIOAPIKey.objects.create(key='hunter-key')
        scan = self._make_scan()
        from reNgine.osint_tasks import run_linkedint
        result = run_linkedint('TargetCorp', scan.id)
        self.assertEqual(result, [])

    def test_returns_empty_list_when_no_hunter_key(self):
        LinkedInCredentials.objects.create(id=1, username='u', cookies_json='[]', is_valid=False)
        scan = self._make_scan()
        from reNgine.osint_tasks import run_linkedint
        result = run_linkedint('TargetCorp', scan.id)
        self.assertEqual(result, [])

    @patch('reNgine.osint_tasks.LinkedInScraper')
    def test_returns_result_string_on_success(self, mock_cls):
        LinkedInCredentials.objects.create(id=1, username='u', cookies_json='[]', is_valid=False)
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
        LinkedInCredentials.objects.create(id=1, username='u', cookies_json='', is_valid=False)
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
        LinkedInCredentials.objects.create(id=1, username='u', cookies_json='[]', is_valid=False)
        HunterIOAPIKey.objects.create(key='hunter-key')
        scan = self._make_scan()
        mock_cls.side_effect = RuntimeError("Playwright crashed unexpectedly")

        from reNgine.osint_tasks import run_linkedint
        result = run_linkedint('TargetCorp', scan.id)
        self.assertEqual(result, [])
```

- [ ] **Step 2: Run caller tests — expect failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session.TestRunLinkedint -v 2"
```

Expected: Tests fail — `run_linkedint` still uses `username`/`password`.

- [ ] **Step 3: Update `run_linkedint()` in `web/reNgine/osint_tasks.py`**

Replace the `run_linkedint` function (lines 107–150) with:

```python
def run_linkedint(company_name, scan_history_id):
    """
    Run LinkedIn Scraper (Playwright) to scrape employees for a company.
    Returns a list of result strings. Never raises — logs notes on auth failure.
    """
    try:
        scan_history = ScanHistory.objects.get(pk=scan_history_id)
        domain = scan_history.domain.name

        session = LinkedInCredentials.objects.first()
        hunter_key = HunterIOAPIKey.objects.first()

        if not session:
            logger.warning("LinkedIn session not configured for %s. Skipping.", company_name)
            return []

        if not hunter_key or not hunter_key.key:
            logger.warning("Hunter.io API key not configured for %s. Skipping.", company_name)
            return []

        with LinkedInScraper(session=session, hunter_key=hunter_key.key) as scraper:
            employees = scraper.discover_employees(company_name, domain, scan_history)

            for note in scraper.notes:
                logger.warning("%s", note)

            if employees:
                for emp_data in employees:
                    emp, _ = save_employee(emp_data['name'], scan_history=scan_history)
                    emp.designation = emp_data['designation']
                    emp.save()
                    if 'email' in emp_data:
                        save_email(emp_data['email'], scan_history=scan_history, employee=emp)

            return [f"LinkedIn Intelligence processed {len(employees)} employees for {company_name}"]

    except Exception as exc:
        logger.error("Error running LinkedIn Intelligence for %s: %s", company_name, type(exc).__name__)
        return []
```

- [ ] **Step 4: Run caller tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session.TestRunLinkedint -v 2"
```

Expected: `OK (5 tests)`

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/osint_tasks.py web/tests/test_linkedin_session.py
git commit -m "feat(linkedin): update run_linkedint to use session object, never raise, log notes"
```

---

## Task 4: Backend API Endpoints

**Files:**
- Modify: `web/api/views.py`
- Modify: `web/api/urls.py`
- Test: `web/tests/test_linkedin_session.py`

- [ ] **Step 1: Add API tests to `web/tests/test_linkedin_session.py`**

Append to `web/tests/test_linkedin_session.py`:

```python
import json
import tempfile
import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from dashboard.models import LinkedInCredentials
from django.conf import settings


class TestLinkedInSessionAPI(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('apitest', 'api@example.com', 'password123')
        self.client = Client()
        self.client.force_login(self.user)

    def test_status_returns_empty_shape_when_no_session(self):
        res = self.client.get('/api/linkedin/session/status/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data['is_valid'])
        self.assertFalse(data['has_state_file'])
        self.assertFalse(data['has_cookies'])
        self.assertIsNone(data['last_validated_at'])
        self.assertEqual(data['username'], '')

    def test_status_returns_correct_shape_with_session(self):
        LinkedInCredentials.objects.create(
            id=1, username='op@example.com',
            cookies_json='[]', state_file_path='', is_valid=True
        )
        res = self.client.get('/api/linkedin/session/status/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['is_valid'])
        self.assertTrue(data['has_cookies'])
        self.assertEqual(data['username'], 'op@example.com')

    def test_upload_cookies_json_saves_to_db(self):
        cookies = json.dumps([
            {'name': 'li_at', 'value': 'token123',
             'domain': '.linkedin.com', 'path': '/'}
        ])
        res = self.client.post(
            '/api/linkedin/session/upload/',
            data=json.dumps({'cookies_json': cookies}),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)
        session = LinkedInCredentials.objects.first()
        self.assertIsNotNone(session)
        self.assertEqual(session.cookies_json, cookies)

    def test_upload_invalid_cookies_json_returns_400(self):
        res = self.client.post(
            '/api/linkedin/session/upload/',
            data=json.dumps({'cookies_json': 'not-valid-json'}),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)

    def test_upload_state_file_saves_to_disk(self):
        valid_state = json.dumps({"cookies": [], "origins": []})
        from io import BytesIO
        file_data = BytesIO(valid_state.encode())
        file_data.name = 'storage_state.json'
        res = self.client.post(
            '/api/linkedin/session/upload/',
            data={'state_file': file_data},
            format='multipart',
        )
        self.assertEqual(res.status_code, 200)
        session = LinkedInCredentials.objects.first()
        self.assertIsNotNone(session)
        self.assertTrue(os.path.isfile(session.state_file_path))

    def test_upload_invalid_json_file_returns_400(self):
        from io import BytesIO
        bad_file = BytesIO(b'not valid json at all')
        bad_file.name = 'storage_state.json'
        res = self.client.post(
            '/api/linkedin/session/upload/',
            data={'state_file': bad_file},
            format='multipart',
        )
        self.assertEqual(res.status_code, 400)

    def test_delete_clears_session_fields(self):
        LinkedInCredentials.objects.create(
            id=1, username='op@example.com',
            cookies_json='[]', state_file_path='', is_valid=True,
        )
        res = self.client.delete('/api/linkedin/session/')
        self.assertEqual(res.status_code, 200)
        session = LinkedInCredentials.objects.get(id=1)
        self.assertFalse(session.is_valid)
        self.assertEqual(session.cookies_json, '')
        self.assertEqual(session.state_file_path, '')

    def test_unauthenticated_status_returns_401_or_403(self):
        unauthenticated = Client()
        res = unauthenticated.get('/api/linkedin/session/status/')
        self.assertIn(res.status_code, [401, 403])

    def test_helper_script_download_returns_python_file(self):
        res = self.client.get('/api/linkedin/session/helper/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('text/x-python', res['Content-Type'])
        self.assertIn('attachment', res['Content-Disposition'])
        self.assertIn(b'sync_playwright', res.content)
```

- [ ] **Step 2: Run API tests — expect 404s (routes not yet registered)**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session.TestLinkedInSessionAPI -v 2"
```

Expected: Tests fail with `404` or routing errors.

- [ ] **Step 3: Add the helper script constant and four views to `web/api/views.py`**

At the top of `web/api/views.py`, ensure these imports are present (add if missing):

```python
import json
import os
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
```

Add the helper script constant near the top of `web/api/views.py` (after imports):

```python
_LINKEDIN_CAPTURE_SCRIPT = '''\
#!/usr/bin/env python3
"""
LinkedIn Session Capture Helper — r3ngine
==========================================
Run this script on your LOCAL machine (not inside Docker) to capture a LinkedIn
authenticated session state file for upload to r3ngine.

Requirements (local machine):
    pip install playwright playwright-stealth
    playwright install chromium

Usage:
    python linkedin_capture.py
    # A browser window opens. Log in to LinkedIn (including any MFA steps).
    # The script saves storage_state.json once you reach the feed.
    # Upload that file in r3ngine: Settings -> API Keys -> LinkedIn.
"""
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "storage_state.json"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        print("Opening LinkedIn login...")
        page.goto("https://www.linkedin.com/login")
        print("Complete login in the browser (including MFA if prompted).")
        print("Waiting for feed page...")
        page.wait_for_url("**/feed/**", timeout=0)
        print("Login confirmed. Saving session...")
        context.storage_state(path=OUTPUT_FILE)
        browser.close()
        print(f"Done. Upload '{OUTPUT_FILE}' to r3ngine via Settings -> API Keys -> LinkedIn.")

if __name__ == "__main__":
    main()
'''
```

Then add the four view classes at the end of `web/api/views.py`:

```python
class LinkedInSessionUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from dashboard.models import LinkedInCredentials

        cookies_json = request.data.get('cookies_json')
        if cookies_json:
            try:
                json.loads(cookies_json)
            except (json.JSONDecodeError, TypeError, ValueError):
                return Response({'error': 'Invalid cookies_json — must be a valid JSON array.'}, status=400)
            session, _ = LinkedInCredentials.objects.get_or_create(id=1)
            session.cookies_json = cookies_json
            session.is_valid = False
            session.save(update_fields=['cookies_json', 'is_valid'])
            return Response({'status': 'cookies saved'})

        state_file = request.FILES.get('state_file')
        if not state_file:
            return Response({'error': 'Provide state_file (multipart) or cookies_json (JSON).'}, status=400)

        try:
            content = state_file.read()
            json.loads(content)
        except (json.JSONDecodeError, Exception):
            return Response({'error': 'Uploaded file is not valid JSON.'}, status=400)

        state_dir = os.path.join(settings.RENGINE_RESULTS, 'context', 'linkedin')
        os.makedirs(state_dir, exist_ok=True)
        state_path = os.path.join(state_dir, 'storage_state.json')
        with open(state_path, 'wb') as fh:
            fh.write(content)

        session, _ = LinkedInCredentials.objects.get_or_create(id=1)
        session.state_file_path = state_path
        session.is_valid = False
        session.save(update_fields=['state_file_path', 'is_valid'])
        return Response({'status': 'state file saved'})


class LinkedInSessionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from dashboard.models import LinkedInCredentials
        session = LinkedInCredentials.objects.first()
        if not session:
            return Response({
                'is_valid': False,
                'last_validated_at': None,
                'username': '',
                'has_state_file': False,
                'has_cookies': False,
            })
        return Response({
            'is_valid': session.is_valid,
            'last_validated_at': session.last_validated_at,
            'username': session.username,
            'has_state_file': bool(
                session.state_file_path and os.path.isfile(session.state_file_path)
            ),
            'has_cookies': bool(session.cookies_json),
        })


class LinkedInSessionDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        import logging as _logging
        from dashboard.models import LinkedInCredentials
        _logger = _logging.getLogger(__name__)
        session = LinkedInCredentials.objects.first()
        if session:
            if session.state_file_path and os.path.isfile(session.state_file_path):
                try:
                    os.remove(session.state_file_path)
                except OSError as exc:
                    _logger.warning("Could not delete LinkedIn state file: %s", exc)
            session.cookies_json = ''
            session.state_file_path = ''
            session.is_valid = False
            session.last_validated_at = None
            session.save()
        return Response({'status': 'session cleared'})


class LinkedInHelperScriptView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(_LINKEDIN_CAPTURE_SCRIPT, content_type='text/x-python')
        response['Content-Disposition'] = 'attachment; filename="linkedin_capture.py"'
        return response
```

- [ ] **Step 4: Register the four URL patterns in `web/api/urls.py`**

In the `from .views import *` section, also add explicit imports for the new views at the top of `urlpatterns` additions. Then add these four `path()` entries inside `urlpatterns` (add before the closing bracket):

```python
    path(
        'linkedin/session/upload/',
        LinkedInSessionUploadView.as_view(),
        name='linkedin-session-upload'),
    path(
        'linkedin/session/status/',
        LinkedInSessionStatusView.as_view(),
        name='linkedin-session-status'),
    path(
        'linkedin/session/',
        LinkedInSessionDeleteView.as_view(),
        name='linkedin-session-delete'),
    path(
        'linkedin/session/helper/',
        LinkedInHelperScriptView.as_view(),
        name='linkedin-session-helper'),
```

- [ ] **Step 5: Run API tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session.TestLinkedInSessionAPI -v 2"
```

Expected: `OK (9 tests)`

- [ ] **Step 6: Commit**

```bash
git add web/api/views.py web/api/urls.py web/tests/test_linkedin_session.py
git commit -m "feat(linkedin): add session upload/status/delete/helper API endpoints"
```

---

## Task 5: Remove Password from `scanEngine/views.py`

**Files:**
- Modify: `web/scanEngine/views.py`

- [ ] **Step 1: Update the LinkedIn credential save block**

In `web/scanEngine/views.py`, find the block around line 1118 and replace:

```python
        if (linkedin_username is not None) or (linkedin_password is not None):
            LinkedInCredentials.objects.update_or_create(
                id=1,
                defaults={
                    'username': linkedin_username or "",
                    'password': linkedin_password or ""
                }
            )
```

with:

```python
        if linkedin_username is not None:
            LinkedInCredentials.objects.update_or_create(
                id=1,
                defaults={'username': linkedin_username or ""}
            )
```

- [ ] **Step 2: Find and remove the `linkedin_password` POST variable read**

Search for `linkedin_password` in `web/scanEngine/views.py` and remove the line that reads it from `request.POST` (e.g. `linkedin_password = request.POST.get('linkedin_password')`). Remove only that variable assignment — do not touch surrounding code.

- [ ] **Step 3: Verify the existing scanEngine test suite still passes**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests -v 2 2>&1 | tail -20"
```

Expected: All previously passing tests still pass. No new failures.

- [ ] **Step 4: Commit**

```bash
git add web/scanEngine/views.py
git commit -m "feat(linkedin): remove password field from scanEngine API vault save"
```

---

## Task 6: Frontend API Client

**Files:**
- Create: `frontend/src/api/linkedin.ts`

- [ ] **Step 1: Create `frontend/src/api/linkedin.ts`**

```typescript
import axios from './axiosConfig';

export interface LinkedInSessionStatus {
  is_valid: boolean;
  last_validated_at: string | null;
  username: string;
  has_state_file: boolean;
  has_cookies: boolean;
}

export const getLinkedInSessionStatus = async (): Promise<LinkedInSessionStatus> => {
  const res = await axios.get<LinkedInSessionStatus>('/api/linkedin/session/status/');
  return res.data;
};

export const uploadLinkedInStateFile = async (file: File): Promise<void> => {
  const formData = new FormData();
  formData.append('state_file', file);
  await axios.post('/api/linkedin/session/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const uploadLinkedInCookiesJson = async (cookiesJson: string): Promise<void> => {
  await axios.post('/api/linkedin/session/upload/', { cookies_json: cookiesJson });
};

export const revokeLinkedInSession = async (): Promise<void> => {
  await axios.delete('/api/linkedin/session/');
};

export const downloadLinkedInHelperScript = (): void => {
  window.location.href = '/api/linkedin/session/helper/';
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npx tsc --noEmit"
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/linkedin.ts
git commit -m "feat(linkedin): add typed API client for LinkedIn session endpoints"
```

---

## Task 7: Frontend `LinkedInSessionCard` Component

**Files:**
- Create: `frontend/src/components/LinkedInSessionCard.tsx`

- [ ] **Step 1: Create `frontend/src/components/LinkedInSessionCard.tsx`**

```tsx
import React, { useEffect, useRef, useState } from 'react';
import {
  downloadLinkedInHelperScript,
  getLinkedInSessionStatus,
  LinkedInSessionStatus,
  revokeLinkedInSession,
  uploadLinkedInStateFile,
} from '../api/linkedin';

const StatusDot: React.FC<{ status: LinkedInSessionStatus | null }> = ({ status }) => {
  if (!status) return <span style={{ color: '#6b7280' }}>⬤</span>;
  if (status.is_valid) return <span style={{ color: '#22c55e' }}>⬤</span>;
  if (status.has_state_file || status.has_cookies) return <span style={{ color: '#f59e0b' }}>⬤</span>;
  return <span style={{ color: '#ef4444' }}>⬤</span>;
};

const statusLabel = (status: LinkedInSessionStatus | null): string => {
  if (!status) return 'Unknown';
  if (status.is_valid) {
    const when = status.last_validated_at
      ? new Date(status.last_validated_at).toLocaleString()
      : 'recently';
    return `Active — last validated ${when}`;
  }
  if (status.has_state_file || status.has_cookies) return 'Session present — not yet validated';
  return 'No session — authentication required';
};

const LinkedInSessionCard: React.FC = () => {
  const [status, setStatus] = useState<LinkedInSessionStatus | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchStatus = async () => {
    try {
      setStatus(await getLinkedInSessionStatus());
    } catch {
      setError('Failed to fetch LinkedIn session status.');
    }
  };

  useEffect(() => { fetchStatus(); }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadLinkedInStateFile(file);
      await fetchStatus();
    } catch {
      setError('Upload failed. Ensure the file is a valid storage_state.json.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRevoke = async () => {
    setError(null);
    try {
      await revokeLinkedInSession();
      await fetchStatus();
    } catch {
      setError('Failed to revoke session.');
    }
  };

  const canRevoke = Boolean(status?.has_state_file || status?.has_cookies);

  return (
    <div className="card mb-3">
      <div className="card-header fw-semibold">LinkedIn Intelligence</div>
      <div className="card-body">
        <p className="mb-1">
          <strong>Status:</strong>{' '}
          <StatusDot status={status} /> {statusLabel(status)}
        </p>
        {status?.username && (
          <p className="mb-2 text-muted small">Account: {status.username}</p>
        )}
        {error && <div className="alert alert-danger py-2 small">{error}</div>}
        <div className="d-flex gap-2 flex-wrap mb-3">
          <button
            className="btn btn-primary btn-sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Uploading…' : 'Upload session state'}
          </button>
          <input
            type="file"
            accept=".json,application/json"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <button
            className="btn btn-outline-danger btn-sm"
            onClick={handleRevoke}
            disabled={!canRevoke}
          >
            Revoke session
          </button>
        </div>
        <p className="text-muted small mb-2">
          Run the helper script on your local machine, log in to LinkedIn in the browser
          that opens (including any MFA steps), then upload the exported{' '}
          <code>storage_state.json</code> here.
        </p>
        <button
          className="btn btn-outline-secondary btn-sm"
          onClick={downloadLinkedInHelperScript}
        >
          Download helper script
        </button>
      </div>
    </div>
  );
};

export default LinkedInSessionCard;
```

- [ ] **Step 2: Build the frontend to verify no TypeScript errors**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -20"
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/LinkedInSessionCard.tsx
git commit -m "feat(linkedin): add LinkedInSessionCard component for session management UI"
```

---

## Task 8: Full Test Run

- [ ] **Step 1: Run the full LinkedIn test suite**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_linkedin_session -v 2"
```

Expected: All tests pass (22+ tests, `OK`).

- [ ] **Step 2: Run the full project test suite to check for regressions**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests -v 1 2>&1 | tail -10"
```

Expected: No new failures.

- [ ] **Step 3: Verify frontend build is clean**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app/frontend && npm run build 2>&1 | tail -5"
```

Expected: `built in Xs` — no errors.

---

## Self-Review Checklist

**Spec coverage:**
- ✅ `storage_state` first, cookie injection second, graceful skip third → Task 2 (`authenticate()`)
- ✅ No password stored → Task 1 (model), Task 5 (scanEngine)
- ✅ `is_valid` updated on both auth paths → Task 2 (`_try_storage_state`, `_try_cookie_injection`)
- ✅ Notes logged on failure, scan never stopped → Task 3 (`run_linkedint`)
- ✅ Upload endpoint (file + cookies_json) → Task 4
- ✅ Status endpoint → Task 4
- ✅ Delete endpoint (removes file from disk + clears DB) → Task 4
- ✅ Downloadable helper script → Task 4
- ✅ Frontend API client → Task 6
- ✅ Frontend card component → Task 7
- ✅ Migration → Task 1

**Type consistency:** `LinkedInScraper(session=..., hunter_key=...)` used consistently across Tasks 2, 3, and all tests. `LinkedInSessionStatus` interface matches the `LinkedInSessionStatusView` response shape exactly.
