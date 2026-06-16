import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

from startScan.models import EndPoint, AuthCandidate
from reNgine.utilities import save_auth_candidate
from reNgine.common_func import get_proxy_list, get_random_proxy, get_random_user_agent

import logging
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTERESTING_KEYWORDS = [
    'login', 'signin', 'sign-in', 'auth', 'admin', 'portal',
    'account', 'manage', 'config', 'setup', 'dashboard', 'user',
    'wp-login', 'wp-admin', 'session', 'oauth', 'sso', 'saml',
]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_with_proxy_retry(url: str, proxy_list: list, timeout: int = 10):
    """
    Fetch *url* attempting up to 3 proxies in sequence, then fall back to a
    direct (no-proxy) connection on the 4th attempt.

    Returns:
        tuple[requests.Response, str | None]: the response and the proxy URL
            that succeeded, or None if the direct-connection attempt succeeded.

    Raises:
        requests.exceptions.RequestException: if all 4 attempts fail.
    """
    headers = {'User-Agent': get_random_user_agent()}

    # Build attempt list: up to 3 proxies then one direct attempt (proxy=None)
    attempts = [(p, {"http": p, "https": p}) for p in proxy_list[:3]]
    attempts.append((None, None))

    last_exc = None
    for proxy_url, proxies in attempts:
        try:
            response = requests.get(
                url,
                proxies=proxies,
                timeout=timeout,
                verify=False,
                headers=headers,
                allow_redirects=True,
            )
            return response, proxy_url
        except Exception as exc:
            last_exc = exc
            if proxy_url:
                logger.warning("Proxy %s failed for %s: %s", proxy_url, url, type(exc).__name__)
            else:
                logger.warning("Direct connection failed for %s: %s", url, type(exc).__name__)

    raise last_exc


def _extract_login_forms(html_content: str, base_url: str) -> list:
    """
    Parse *html_content* and return a list of dicts, one per form that
    contains a password field (or autocomplete="current-password").

    Each dict has:
        action       (str)  – absolute URL the form submits to
        method       (str)  – HTTP verb in uppercase ('POST' or 'GET')
        user_field   (str)  – best-guess username input name
        pass_field   (str)  – password input name
        hidden_fields (dict) – {name: value} for hidden inputs (CSRF tokens etc.)
        all_fields   (list) – all input/select/textarea names in the form
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    results = []

    _user_keywords = ('user', 'email', 'login', 'name', 'account', 'id', 'handle')

    for form in soup.find_all('form'):
        # Identify password fields: explicit type="password" or autocomplete hint
        password_inputs = [
            inp for inp in form.find_all('input')
            if (inp.get('type') or 'text').lower() == 'password'
            or (inp.get('autocomplete') or '').lower() in ('current-password', 'new-password')
        ]

        if not password_inputs:
            continue

        # Resolve action URL
        action_raw = (form.get('action') or '').strip()
        action = urljoin(base_url, action_raw) if action_raw else base_url
        method = (form.get('method') or 'post').upper()

        all_fields = []
        hidden_fields = {}
        user_field = None
        pass_field = None

        _skip_types = {'submit', 'button', 'reset', 'image', 'checkbox', 'radio', 'file'}

        for inp in form.find_all(['input', 'select', 'textarea']):
            name = (inp.get('name') or '').strip()
            if not name:
                continue
            inp_type = (inp.get('type') or 'text').lower()
            autocomplete = (inp.get('autocomplete') or '').lower()
            all_fields.append(name)

            if inp_type == 'hidden':
                hidden_fields[name] = inp.get('value', '')
            elif inp_type == 'password' or autocomplete in ('current-password', 'new-password'):
                if pass_field is None:
                    pass_field = name
            elif inp_type not in _skip_types:
                # Prefer field names containing username-like keywords
                if user_field is None and any(kw in name.lower() for kw in _user_keywords):
                    user_field = name
                elif user_field is None and inp_type in ('text', 'email'):
                    user_field = name

        if user_field is None:
            user_field = 'username'
        if pass_field is None:
            pass_field = (password_inputs[0].get('name') or '').strip() or 'password'

        results.append({
            'action': action,
            'method': method,
            'user_field': user_field,
            'pass_field': pass_field,
            'hidden_fields': hidden_fields,
            'all_fields': all_fields,
        })

    return results


# ---------------------------------------------------------------------------
# Public task function
# ---------------------------------------------------------------------------

def extract_auth_candidates(self, ctx={}, description=None):
    """
    Tier 3 Auth Discovery: Fetch endpoints likely to host login forms, parse
    their HTML with BeautifulSoup, and save any discovered login forms as
    AuthCandidate records.

    Retries up to 3 configured proxies before falling back to a direct
    connection.  If all four attempts fail the endpoint is skipped and the
    error is logged.
    """
    logger.info("Starting Intelligent Auth Form Extraction for Scan %s", self.scan_id)

    endpoints = EndPoint.objects.filter(
        subdomain__scan_history=self.scan,
        http_status__gt=0,
        http_status__lt=500,
    ).exclude(http_status=404)

    existing_candidate_urls = set(
        AuthCandidate.objects.filter(scan_history=self.scan).values_list('target', flat=True)
    )

    potential_endpoints = []
    for ep in endpoints:
        if ep.http_url in existing_candidate_urls:
            continue
        parsed = urlparse(ep.http_url)
        if any(kw in ep.http_url.lower() for kw in INTERESTING_KEYWORDS) or parsed.path in ('', '/'):
            potential_endpoints.append(ep)

    if not potential_endpoints:
        logger.info("No new potential auth endpoints found for extraction.")
        return

    logger.info(
        "Found %d potential auth endpoints. Attempting form extraction...",
        len(potential_endpoints),
    )

    # Build the proxy list.  TOR mode: get_proxy_list() returns [] but
    # get_random_proxy() returns 'socks5://tor:9050', so we use it as the
    # single proxy in the rotation so TOR traffic is respected.
    proxy_list = get_proxy_list()
    if not proxy_list:
        tor_or_single = get_random_proxy()
        if tor_or_single:
            proxy_list = [tor_or_single]

    for ep in potential_endpoints:
        try:
            response, _ = _fetch_with_proxy_retry(ep.http_url, proxy_list)
            forms = _extract_login_forms(response.text, ep.http_url)

            if not forms:
                continue

            parsed = urlparse(ep.http_url)
            protocol = parsed.scheme or 'http'
            port = parsed.port or (443 if protocol == 'https' else 80)

            for form in forms:
                logger.info(
                    "Login form found on %s (action=%s method=%s)",
                    ep.http_url, form['action'], form['method'],
                )
                save_auth_candidate(
                    scan_history=self.scan,
                    target=form['action'],
                    protocol=protocol,
                    port=port,
                    source_tool='Intelligent Form Extraction',
                    metadata={
                        'type': 'form',
                        'method': form['method'],
                        'user_field': form['user_field'],
                        'pass_field': form['pass_field'],
                        'hidden_fields': form['hidden_fields'],
                        'all_fields': form['all_fields'],
                    },
                    subdomain=ep.subdomain,
                    endpoint=ep,
                )
        except Exception as exc:
            logger.error(
                "Error extracting form from %s: %s",
                ep.http_url, type(exc).__name__,
            )

    return True
