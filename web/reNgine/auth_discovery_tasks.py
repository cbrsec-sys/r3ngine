import os
import json
import re
import requests
from urllib.parse import urlparse
from django.conf import settings
from startScan.models import EndPoint, AuthCandidate, Subdomain
from reNgine.celery import app
from reNgine.tasks import RengineTask
from reNgine.utilities import save_auth_candidate
from reNgine.common_func import get_random_proxy
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@app.task(name='extract_auth_candidates', queue='main_scan_queue', base=RengineTask, bind=True)
def extract_auth_candidates(self, ctx={}, description=None):
    """
    Tier 3 Auth Discovery: Extract login forms from endpoints using httpx and regex
    if no high-confidence auth portal was found via Nuclei/Nmap.
    """
    logger.info(f"Starting Intelligent Auth Form Extraction for Scan {self.scan_id}")
    
    # Get all alive endpoints for this scan
    endpoints = EndPoint.objects.filter(subdomain__scan_history=self.scan, http_status__gt=0, http_status__lt=500).exclude(http_status=404)
    
    # Filter for interesting keywords if they are not already candidates
    existing_candidate_urls = AuthCandidate.objects.filter(scan_history=self.scan).values_list('target', flat=True)
    
    interesting_keywords = ['login', 'signin', 'auth', 'admin', 'portal', 'account', 'manage', 'config', 'setup']
    
    potential_endpoints = []
    for ep in endpoints:
        if ep.http_url in existing_candidate_urls:
            continue
        
        # Check if URL contains keywords or if it's a root domain (often has login)
        parsed = urlparse(ep.http_url)
        if any(kw in ep.http_url.lower() for kw in interesting_keywords) or parsed.path in ['', '/']:
            potential_endpoints.append(ep)
            
    if not potential_endpoints:
        logger.info("No new potential auth endpoints found for extraction.")
        return
        
    logger.info(f"Found {len(potential_endpoints)} potential auth endpoints. Attempting form extraction...")
    
    for ep in potential_endpoints:
        try:
            proxy = get_random_proxy()
            proxies = {"http": proxy, "https": proxy} if proxy else None
            
            # Fetch the page content
            response = requests.get(ep.http_url, proxies=proxies, timeout=10, verify=False, headers={'User-Agent': 'Mozilla/5.0'})
            content = response.text
            
            # Look for forms with password fields
            # Regex to find <form ...> ... <input ... type="password" ...> ... </form>
            # This is a simplified approach. In a real scenario, we might use BeautifulSoup.
            if 'type="password"' in content.lower() or 'type=\'password\'' in content.lower():
                logger.info(f"Confirmed login form found on {ep.http_url}")
                
                # Extract form parameters (very basic extraction)
                # We look for input names
                input_names = re.findall(r'name=["\'](.*?)["\']', content)
                
                # Try to guess user/pass fields
                user_field = next((n for n in input_names if any(x in n.lower() for x in ['user', 'email', 'login', 'name'])), 'username')
                pass_field = next((n for n in input_names if 'pass' in n.lower()), 'password')
                
                save_auth_candidate(
                    scan_history=self.scan,
                    target=ep.http_url,
                    protocol='http',
                    port=int(urlparse(ep.http_url).port or (443 if 'https' in ep.http_url else 80)),
                    source_tool='Intelligent Form Extraction',
                    metadata={
                        'type': 'form',
                        'user_field': user_field,
                        'pass_field': pass_field,
                        'all_fields': input_names
                    },
                    subdomain=ep.subdomain,
                    endpoint=ep
                )
        except Exception as e:
            logger.error(f"Error extracting form from {ep.http_url}: {e}")

    return True
