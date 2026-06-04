import logging
import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive, make_aware
from startScan.models import CveId

logger = logging.getLogger(__name__)

class CVEEnrichmentService:
	"""
	Enriches local CveId records with metadata from official databases (NVD, EPSS, CISA KEV).
	"""
	def __init__(self):
		"""
		Initialize the service, checking for configured API keys.
		"""
		self.nvd_api_key = getattr(settings, 'NVD_API_KEY', None)

	def _parse_timezone_aware(self, date_str):
		if not date_str:
			return None
		dt = parse_datetime(date_str)
		if dt and is_naive(dt):
			return make_aware(dt)
		return dt

	def enrich_cve(self, cve_name: str) -> CveId:
		"""
		Query external feeds (NVD / EPSS) for CVE details and update CveId model.

		Args:
			cve_name (str): The CVE identifier (e.g., 'CVE-2024-1234').

		Returns:
			CveId: The database record.
		"""
		cve_obj, _ = CveId.objects.get_or_create(name=cve_name)
		
		# 1. Fetch from NVD API v2
		try:
			nvd_url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_name}"
			headers = {}
			if self.nvd_api_key:
				headers["apiKey"] = self.nvd_api_key
			
			response = requests.get(nvd_url, headers=headers, timeout=10)
			if response.status_code == 200:
				data = response.json()
				vulns = data.get("vulnerabilities", [])
				if vulns:
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
		except Exception as e:
			logger.warning(f"Failed to fetch NVD data for {cve_name}: {e}")

		# 2. Fetch from EPSS API
		try:
			epss_url = f"https://api.first.org/data/v1/epss?cve={cve_name}"
			response = requests.get(epss_url, timeout=10)
			if response.status_code == 200:
				data = response.json()
				epss_list = data.get("data", [])
				if epss_list:
					epss_data = epss_list[0]
					if epss_data.get("epss"):
						cve_obj.epss_score = float(epss_data["epss"])
					if epss_data.get("percentile"):
						cve_obj.epss_percentile = float(epss_data["percentile"]) * 100.0
		except Exception as e:
			logger.warning(f"Failed to fetch EPSS data for {cve_name}: {e}")

		cve_obj.save()
		return cve_obj

	def sync_cisa_kev_catalog(self):
		"""
		Sync local catalog with official CISA KEV catalog feed.
		"""
		try:
			kev_url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
			response = requests.get(kev_url, timeout=15)
			if response.status_code == 200:
				data = response.json()
				vulns = data.get("vulnerabilities", [])
				cve_names = [v["cveID"] for v in vulns if "cveID" in v]
				
				# Update all matching CveIds to True
				CveId.objects.filter(name__in=cve_names).update(is_cisa_kev=True)
				logger.info(f"Successfully synchronized {len(cve_names)} CISA KEV entries.")
		except Exception as e:
			logger.error(f"Failed to synchronize CISA KEV catalog: {e}")
