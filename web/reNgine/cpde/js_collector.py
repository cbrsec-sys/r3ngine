"""
js_collector.py — JavaScript File Collection

Reads the Katana URL output file produced by fetch_url and downloads any
discovered .js files for downstream AST analysis. Deduplicates by SHA-256
so each unique bundle is only analysed once per scan.

This module does NOT re-run Katana or any other crawler. It is a pure
post-processing step on files already produced by fetch_url.
"""

import hashlib
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

# Katana output file name (relative to results_dir) — matches fetch_url task
KATANA_OUTPUT_FILENAME = 'urls_katana.txt'

# Request timeout for downloading individual JS files
_JS_DOWNLOAD_TIMEOUT = 20  # seconds

# Maximum JS file size to download and analyse (10 MB)
_MAX_JS_SIZE_BYTES = 10 * 1024 * 1024

# Regex to match JS file URLs (including .mjs, .ts bundles)
_JS_URL_RE = re.compile(r'https?://[^\s]+\.(?:js|mjs|jsx|ts|tsx)(?:\?[^\s]*)?$', re.IGNORECASE)


def get_js_urls_from_katana_output(results_dir: str) -> list[str]:
    """Read the Katana output file and return all discovered JS file URLs.

    Args:
        results_dir (str): Path to the scan results directory.

    Returns:
        list[str]: Deduplicated list of JS file URLs found in Katana output.
    """
    katana_file = os.path.join(results_dir, KATANA_OUTPUT_FILENAME)
    if not os.path.isfile(katana_file):
        logger.warning('[CPDE:js_collector] Katana output not found at %s', katana_file)
        return []

    js_urls = []
    seen = set()
    try:
        with open(katana_file, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                url = line.strip()
                if url and url not in seen and _JS_URL_RE.match(url):
                    seen.add(url)
                    js_urls.append(url)
    except OSError as exc:
        logger.error('[CPDE:js_collector] Failed to read Katana output: %s', exc)

    logger.info('[CPDE:js_collector] Found %d unique JS URLs in Katana output', len(js_urls))
    return js_urls


def download_js_files(
    js_urls: list[str],
    session: requests.Session | None = None,
    proxy: str | None = None,
) -> list[dict]:
    """Download JS files and return their content with metadata.

    Skips files that exceed _MAX_JS_SIZE_BYTES or fail to download.
    Deduplicates identical files by SHA-256 hash so minified bundles
    served from multiple CDN paths are only analysed once.

    Args:
        js_urls (list[str]): JS file URLs to download.
        session (requests.Session | None): Optional shared session for connection reuse.
        proxy (str | None): Optional HTTP proxy URL.

    Returns:
        list[dict]: Each dict has keys:
            url (str), content (str), size (int), hash (str), content_type (str)
    """
    if session is None:
        session = requests.Session()

    proxies = {'http': proxy, 'https': proxy} if proxy else None
    seen_hashes: set[str] = set()
    results: list[dict] = []

    for url in js_urls:
        try:
            # HEAD first to check Content-Length before downloading
            try:
                head = session.head(
                    url,
                    timeout=_JS_DOWNLOAD_TIMEOUT,
                    proxies=proxies,
                    allow_redirects=True,
                )
                content_length = int(head.headers.get('Content-Length', 0))
                if content_length > _MAX_JS_SIZE_BYTES:
                    logger.info(
                        '[CPDE:js_collector] Skipping %s — too large (%d bytes)', url, content_length
                    )
                    continue
            except Exception:
                # HEAD not supported by all servers; proceed with GET
                pass

            resp = session.get(
                url,
                timeout=_JS_DOWNLOAD_TIMEOUT,
                proxies=proxies,
                stream=False,
            )
            resp.raise_for_status()

            if len(resp.content) > _MAX_JS_SIZE_BYTES:
                logger.info('[CPDE:js_collector] Skipping %s — content too large', url)
                continue

            content = resp.text
            file_hash = hashlib.sha256(content.encode('utf-8', errors='replace')).hexdigest()

            if file_hash in seen_hashes:
                logger.debug('[CPDE:js_collector] Skipping duplicate JS at %s', url)
                continue
            seen_hashes.add(file_hash)

            results.append({
                'url': url,
                'content': content,
                'size': len(resp.content),
                'hash': file_hash,
                'content_type': resp.headers.get('Content-Type', ''),
            })
            logger.debug('[CPDE:js_collector] Downloaded %s (%d bytes)', url, len(resp.content))

        except requests.RequestException as exc:
            logger.warning('[CPDE:js_collector] Failed to download %s: %s', url, exc)

    logger.info(
        '[CPDE:js_collector] Downloaded %d unique JS files from %d URLs',
        len(results), len(js_urls),
    )
    return results
