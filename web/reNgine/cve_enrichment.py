"""
CVE Enrichment Service

Fetches vulnerability metadata from official sources (NVD, EPSS, CISA KEV)
and updates the local CveId database with enriched data.

Supports:
- NVD API v2.0 for CVSS scores and metadata
- FIRST EPSS API for exploitation probability scores
- CISA KEV catalog for known exploited vulnerabilities
"""

import logging
import re
import requests
from typing import Optional, Dict, List
from datetime import timedelta
from functools import lru_cache

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive, make_aware
from django.core.cache import cache

from startScan.models import CveId

logger = logging.getLogger(__name__)


class CVEEnrichmentService:
    """
    Service for enriching CVE records with official metadata.
    
    Caches API responses to minimize external API calls.
    Gracefully degrades if external services are unavailable.
    """
    
    # API Endpoints
    NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    EPSS_API_BASE = "https://api.first.org/data/v1/epss"
    CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    
    # Cache TTLs (seconds)
    CACHE_TTL_CVE = 86400 * 7  # 7 days for individual CVEs
    CACHE_TTL_KEV = 3600  # 1 hour for KEV catalog
    
    # Request settings
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 2
    
    def __init__(self):
        """Initialize the enrichment service."""
        self.nvd_api_key = getattr(settings, 'NVD_API_KEY', None)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'r3ngine/1.0 (+https://github.com/whiterabb17/r3ngine)'
        })
    
    # ==================== Public API ====================
    
    def enrich_cve(self, cve_name: str) -> Optional[CveId]:
        """
        Fetch and store CVE metadata from NVD and EPSS APIs.
        
        This is the primary entry point for CVE enrichment.
        
        Args:
            cve_name (str): CVE identifier, e.g., 'CVE-2024-1234'
        
        Returns:
            CveId: Updated or created CveId object, or None if enrichment fails
        
        Example:
            >>> service = CVEEnrichmentService()
            >>> cve = service.enrich_cve('CVE-2024-1234')
            >>> print(f"CVSS: {cve.cvss_v31_base_score}")
        """
        # Normalize CVE name
        cve_name = cve_name.upper().strip()
        if not cve_name.startswith('CVE-'):
            # Accept bare YYYY-NNNNN format and prepend the required prefix
            if re.match(r'^\d{4}-\d+$', cve_name):
                cve_name = 'CVE-' + cve_name
            else:
                logger.warning("Invalid CVE format: %s", cve_name)
                return None
        
        # Get or create CVE record
        cve_obj, created = CveId.objects.get_or_create(name=cve_name)
        
        # Skip re-enrichment if recently updated (within 7 days)
        if not created and cve_obj.last_modified_date:
            days_old = (timezone.now() - cve_obj.last_modified_date).days
            if days_old < 7 and cve_obj.cvss_v31_base_score is not None:
                logger.debug(f"CVE {cve_name} recently enriched, skipping")
                return cve_obj
        
        # Attempt enrichment (graceful degradation)
        try:
            self._enrich_from_nvd(cve_obj)
        except Exception as e:
            logger.warning(f"NVD enrichment failed for {cve_name}: {e}")
        
        try:
            self._enrich_from_epss(cve_obj)
        except Exception as e:
            logger.warning(f"EPSS enrichment failed for {cve_name}: {e}")
        
        # Save and return
        cve_obj.save()
        return cve_obj
    
    def enrich_multiple_cves(self, cve_names: List[str]) -> Dict[str, CveId]:
        """
        Batch enrich multiple CVEs.
        
        Args:
            cve_names (List[str]): List of CVE identifiers
        
        Returns:
            Dict[str, CveId]: Mapping of CVE name to enriched object
        """
        results = {}
        for cve_name in cve_names:
            try:
                cve_obj = self.enrich_cve(cve_name)
                if cve_obj:
                    results[cve_name] = cve_obj
            except Exception as e:
                logger.error(f"Failed to enrich {cve_name}: {e}")
        
        return results
    
    def sync_cisa_kev_catalog(self) -> Dict[str, int]:
        """
        Synchronize local CveId records with official CISA Known Exploited 
        Vulnerabilities (KEV) catalog.
        
        This should be called periodically (e.g., daily) to keep KEV status 
        up-to-date.
        
        Returns:
            Dict with keys 'updated', 'new', 'errors'
        
        Example:
            >>> service = CVEEnrichmentService()
            >>> result = service.sync_cisa_kev_catalog()
            >>> print(f"Updated {result['updated']} CVEs as KEV")
        """
        logger.info("Synchronizing CISA KEV catalog...")
        
        try:
            # Check cache first
            cache_key = 'cisa_kev_catalog'
            kev_data = cache.get(cache_key)
            
            if not kev_data:
                # Fetch from official source
                response = requests.get(
                    self.CISA_KEV_URL, 
                    timeout=self.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                kev_data = response.json()
                
                # Cache for 1 hour
                cache.set(cache_key, kev_data, self.CACHE_TTL_KEV)
            
            # Extract CVE names from catalog
            vulns = kev_data.get("vulnerabilities", [])
            cve_names = [v["cveID"] for v in vulns if "cveID" in v]
            
            logger.info(f"CISA KEV catalog contains {len(cve_names)} vulnerabilities")
            
            # Batch update all matching CveIds
            updated_count = CveId.objects.filter(
                name__in=cve_names
            ).update(is_cisa_kev=True)
            
            # Count new KEV entries (not yet in database)
            existing_names = set(
                CveId.objects.filter(name__in=cve_names).values_list('name', flat=True)
            )
            new_count = len([c for c in cve_names if c not in existing_names])
            
            logger.info(f"CISA KEV sync: {updated_count} updated, {new_count} new")
            
            return {
                'updated': updated_count,
                'new': new_count,
                'total': len(cve_names),
                'errors': 0
            }
        
        except Exception as e:
            logger.error(f"Failed to synchronize CISA KEV catalog: {e}")
            return {
                'updated': 0,
                'new': 0,
                'total': 0,
                'errors': 1
            }
    
    # ==================== Private Methods ====================
    
    def _enrich_from_nvd(self, cve_obj: CveId) -> None:
        """
        Fetch CVE metadata from NVD API v2.0.
        
        Args:
            cve_obj (CveId): CVE object to enrich in-place
        
        Raises:
            requests.RequestException: If API call fails
            ValueError: If response format is unexpected
        """
        # Build request with API key if available
        headers = {}
        if self.nvd_api_key:
            headers['apiKey'] = self.nvd_api_key
        
        params = {'cveId': cve_obj.name}
        
        logger.debug(f"Fetching NVD data for {cve_obj.name}...")
        
        response = requests.get(
            self.NVD_API_BASE,
            params=params,
            headers=headers,
            timeout=self.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        vulns = data.get("vulnerabilities", [])
        
        if not vulns:
            logger.debug(f"No NVD data found for {cve_obj.name}")
            return
        
        # Extract CVE data from first result
        cve_data = vulns[0].get("cve", {})
        
        # Parse dates
        if cve_data.get("published"):
            cve_obj.published_date = self._parse_timezone_aware(cve_data["published"])
        
        if cve_data.get("lastModified"):
            cve_obj.last_modified_date = self._parse_timezone_aware(cve_data["lastModified"])
        
        # Parse CVSS v3.1 metrics
        metrics = cve_data.get("metrics", {})
        cvss_v31_list = metrics.get("cvssMetricV31", [])
        
        if cvss_v31_list:
            cvss_data = cvss_v31_list[0].get("cvssData", {})
            cve_obj.cvss_v31_base_score = cvss_data.get("baseScore")
            cve_obj.attack_vector = cvss_data.get("attackVector")
            cve_obj.attack_complexity = cvss_data.get("attackComplexity")
            cve_obj.privileges_required = cvss_data.get("privilegesRequired")
            cve_obj.user_interaction = cvss_data.get("userInteraction")
            cve_obj.confidentiality_impact = cvss_data.get("confidentialityImpact")
            cve_obj.integrity_impact = cvss_data.get("integrityImpact")
            cve_obj.availability_impact = cvss_data.get("availabilityImpact")
            
            logger.debug(
                f"NVD enrichment successful: {cve_obj.name} "
                f"CVSS={cve_obj.cvss_v31_base_score}"
            )
    
    def _enrich_from_epss(self, cve_obj: CveId) -> None:
        """
        Fetch EPSS (Exploit Prediction Scoring System) data from FIRST API.
        
        EPSS provides a probability score of a vulnerability being exploited
        in the wild (0-1 scale, higher = more likely to be exploited).
        
        Args:
            cve_obj (CveId): CVE object to enrich in-place
        
        Raises:
            requests.RequestException: If API call fails
        """
        params = {'cve': cve_obj.name}
        
        logger.debug(f"Fetching EPSS data for {cve_obj.name}...")
        
        response = requests.get(
            self.EPSS_API_BASE,
            params=params,
            timeout=self.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        epss_list = data.get("data", [])
        
        if not epss_list:
            logger.debug(f"No EPSS data found for {cve_obj.name}")
            return
        
        epss_data = epss_list[0]
        
        # EPSS score is 0-1, percentile is already percentage
        if epss_data.get("epss"):
            cve_obj.epss_score = float(epss_data["epss"])
        
        if epss_data.get("percentile"):
            # FIRST API returns percentile as 0-1, convert to 0-100
            cve_obj.epss_percentile = float(epss_data["percentile"]) * 100.0
        
        logger.debug(
            f"EPSS enrichment successful: {cve_obj.name} "
            f"EPSS={cve_obj.epss_score} percentile={cve_obj.epss_percentile}"
        )
    
    def _parse_timezone_aware(self, date_str: str) -> Optional[timezone.datetime]:
        """
        Parse ISO 8601 datetime string and ensure timezone awareness.
        
        Args:
            date_str (str): ISO 8601 formatted datetime
        
        Returns:
            datetime: Timezone-aware datetime, or None if parsing fails
        """
        if not date_str:
            return None
        
        try:
            dt = parse_datetime(date_str)
            if dt and is_naive(dt):
                return make_aware(dt)
            return dt
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse datetime '{date_str}': {e}")
            return None


class CVEBatchEnricher:
    """
    Utility for background enrichment of CVEs in batches.
    
    Useful for periodic synchronization tasks.
    """
    
    def __init__(self):
        self.service = CVEEnrichmentService()
    
    def enrich_unenriched_cves(self, limit: int = 100) -> int:
        """
        Enrich CVEs that haven't been enriched yet.
        
        Args:
            limit (int): Maximum number to enrich in this run
        
        Returns:
            int: Number of CVEs successfully enriched
        """
        # Find CVEs with no enrichment data
        cves_to_enrich = CveId.objects.filter(
            cvss_v31_base_score__isnull=True
        ).order_by('name')[:limit]
        
        count = 0
        for cve in cves_to_enrich:
            try:
                self.service.enrich_cve(cve.name)
                count += 1
            except Exception as e:
                logger.error(f"Failed to enrich {cve.name}: {e}")
        
        logger.info(f"Batch enrichment completed: {count}/{len(list(cves_to_enrich))} successful")
        return count
    
    def refresh_recent_cves(self, days: int = 30) -> int:
        """
        Re-enrich CVEs modified in last N days to get latest data.
        
        Args:
            days (int): Lookback period in days
        
        Returns:
            int: Number of CVEs re-enriched
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        cves_to_refresh = CveId.objects.filter(
            last_modified_date__gte=cutoff
        ).order_by('-last_modified_date')
        
        count = 0
        for cve in cves_to_refresh:
            try:
                self.service.enrich_cve(cve.name)
                count += 1
            except Exception as e:
                logger.error(f"Failed to refresh {cve.name}: {e}")
        
        logger.info(f"Refresh completed: {count} CVEs")
        return count
