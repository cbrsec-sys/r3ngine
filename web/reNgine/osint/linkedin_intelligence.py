import os
import random
import time
import logging
import re
import urllib.parse
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from django.conf import settings
from startScan.models import ScanHistory, Email, Employee
from dashboard.models import LinkedInCredentials, HunterIOAPIKey
import requests

logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self, username, password, hunter_key, context_path=None):
        self.username = username
        self.password = password
        self.hunter_key = hunter_key
        # Default path within the container volume
        self.context_path = context_path or "/usr/src/reNgine/scan_results/context/linkedin"
        os.makedirs(self.context_path, exist_ok=True)
        self.playwright = None
        self.context = None
        self.page = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        # Using persistent context for session survival
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.context_path,
            headless=True,
            args=[
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
            ]
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        stealth_sync(self.page)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()

    def random_sleep(self, min_s=2, max_s=5):
        time.sleep(random.uniform(min_s, max_s))

    def human_scroll(self):
        """Perform a human-like scroll down the page."""
        for _ in range(random.randint(3, 6)):
            scroll_amount = random.randint(300, 700)
            self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            self.random_sleep(1, 3)

    def is_logged_in(self):
        try:
            self.page.goto("https://www.linkedin.com/feed/", wait_until="networkidle")
            # If redirected to login or see login buttons, we are not logged in
            if "login" in self.page.url or self.page.query_selector('button:has-text("Sign in")'):
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False

    def login(self):
        if self.is_logged_in():
            logger.info("Already logged in to LinkedIn via persistent context.")
            return True

        logger.info("Attempting fresh LinkedIn login...")
        try:
            self.page.goto("https://www.linkedin.com/login", wait_until="networkidle")
            self.page.fill('input[name="session_key"]', self.username)
            self.random_sleep(1, 2)
            self.page.fill('input[name="session_password"]', self.password)
            self.random_sleep(1, 2)
            self.page.click('button[type="submit"]')
            self.page.wait_for_load_state("networkidle")
            
            if self.is_logged_in():
                logger.info("LinkedIn login successful.")
                return True
            else:
                logger.error("LinkedIn login failed. Check credentials or 2FA.")
                return False
        except Exception as e:
            logger.error(f"LinkedIn login exception: {e}")
            return False

    def get_hunter_pattern(self, domain):
        try:
            url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={self.hunter_key}"
            res = requests.get(url, timeout=10)
            data = res.json()
            if 'data' in data and 'pattern' in data['data']:
                return data['data']['pattern']
        except Exception as e:
            logger.warning(f"Failed to fetch Hunter.io pattern: {e}")
        return "{first}.{last}"

    def format_email(self, name, pattern, domain):
        # Very basic pattern formatter
        parts = name.split()
        first = parts[0] if len(parts) > 0 else ""
        last = parts[-1] if len(parts) > 1 else ""
        
        email = pattern.replace('{first}', first.lower())
        email = email.replace('{last}', last.lower())
        email = email.replace('{f}', first[0].lower() if first else '')
        email = email.replace('{l}', last[0].lower() if last else '')
        
        if '@' not in email:
            email = f"{email}@{domain}"
        return email

    def discover_employees(self, company_name, domain, scan_history):
        if not self.login():
            return []

        pattern = self.get_hunter_pattern(domain)
        employees_data = []

        try:
            # 1. Try direct company people page
            # This requires knowing the company ID or slug, so we search for it first
            search_query = urllib.parse.quote_plus(company_name)
            self.page.goto(f"https://www.linkedin.com/search/results/all/?keywords={search_query}", wait_until="networkidle")
            self.random_sleep()

            # Find the first company result
            company_link = self.page.query_selector('a[href*="/company/"]')
            if company_link:
                company_url = company_link.get_attribute("href")
                # Strip query params
                company_url = company_url.split('?')[0]
                people_url = f"{company_url}people/"
                logger.info(f"Navigating to company people page: {people_url}")
                self.page.goto(people_url, wait_until="networkidle")
                self.random_sleep()
                self.human_scroll()
                
                # Extract cards
                # Note: Selectors are approximations and may need updates
                cards = self.page.query_selector_all('.org-people-profile-card__profile-info')
                for card in cards:
                    name_elem = card.query_selector('.lt-line-clamp--single-line')
                    title_elem = card.query_selector('.lt-line-clamp--multi-line')
                    
                    if name_elem:
                        name = name_elem.inner_text().strip()
                        title = title_elem.inner_text().strip() if title_elem else "Employee"
                        email = self.format_email(name, pattern, domain)
                        employees_data.append({
                            'name': name,
                            'designation': title,
                            'email': email
                        })

            # 2. Fallback to global people search if needed
            if not employees_data:
                logger.info("Falling back to global people search.")
                search_url = f"https://www.linkedin.com/search/results/people/?keywords={search_query}"
                self.page.goto(search_url, wait_until="networkidle")
                self.random_sleep()
                self.human_scroll()
                
                # Global search selectors
                cards = self.page.query_selector_all('.entity-result__item')
                for card in cards:
                    name_elem = card.query_selector('.entity-result__title-text a span[aria-hidden="true"]')
                    title_elem = card.query_selector('.entity-result__primary-subtitle')
                    
                    if name_elem:
                        name = name_elem.inner_text().strip()
                        title = title_elem.inner_text().strip() if title_elem else "Employee"
                        email = self.format_email(name, pattern, domain)
                        employees_data.append({
                            'name': name,
                            'designation': title,
                            'email': email
                        })

        except Exception as e:
            logger.error(f"Error during employee discovery: {e}")

        # Visual Verification with unique naming
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Clean company name for filename
            safe_name = re.sub(r'[^a-zA-Z0-9]', '_', company_name).lower()
            screenshot_path = f"{scan_history.results_dir}/osint/linkedin_{safe_name}_{timestamp}.png"
            
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            self.page.screenshot(path=screenshot_path)
            logger.info(f"LinkedIn discovery screenshot saved to: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Failed to capture discovery screenshot: {e}")

        return employees_data
