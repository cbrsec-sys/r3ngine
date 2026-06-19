import logging
from django.db import transaction
from django.db.models import Q
from startScan.models import (
	Subdomain, EndPoint, Screenshot, Vulnerability,
	Exposure, ExposureEvidence
)

logger = logging.getLogger(__name__)

class ExposureCorrelationEngine:
	"""
	Aggregates data from Subdomains, EndPoints, Screenshots, Ports, and Vulnerabilities
	into unified 'Exposure' records representing attack surface assets.
	"""
	
	def __init__(self, scan_history=None):
		self.scan_history = scan_history

	def correlate_exposures(self):
		"""
		Main entry point to perform the correlation process for the given scan_history.
		"""
		if not self.scan_history:
			logger.warning("ExposureCorrelationEngine: No scan_history provided.")
			return

		# Fetch all subdomains associated with this scan
		subdomains = Subdomain.objects.filter(scan_history=self.scan_history).prefetch_related(
			'ip_addresses__ports', 'technologies', 'screenshots'
		)

		for subdomain in subdomains:
			self._process_subdomain(subdomain)

	def _process_subdomain(self, subdomain):
		endpoints = EndPoint.objects.filter(
			scan_history=self.scan_history, subdomain=subdomain
		).prefetch_related('techs')
		
		screenshots = Screenshot.objects.filter(
			scan_history=self.scan_history, subdomain=subdomain
		)

		vulns = Vulnerability.objects.filter(
			scan_history=self.scan_history, subdomain=subdomain
		)

		# Group by host/endpoint base URL or just create one primary exposure per Subdomain
		# For a robust MVP, we will create an Exposure for the Subdomain itself,
		# and potentially distinct Exposures for significantly different EndPoints (e.g. APIs on specific paths).
		# We'll start with one Exposure per Subdomain (the Host level), aggregating port and tech info.

		exposure_type = self._classify_exposure(subdomain, endpoints, screenshots)
		
		try:
			with transaction.atomic():
				exposure, created = Exposure.objects.update_or_create(
					scan_history=self.scan_history,
					subdomain=subdomain,
					target_domain=subdomain.target_domain,
					defaults={
						'type': exposure_type,
						'status': 'open', # Or potentially logic to check if remediated
					}
				)

				# Gather evidence
				self._collect_evidence(exposure, subdomain, endpoints, screenshots, vulns)

				# Link vulnerabilities to this exposure
				vulns.update(exposure=exposure)
				
		except Exception as e:
			logger.error(f"Error correlating exposure for subdomain {subdomain.name}: {e}")

	def _classify_exposure(self, subdomain, endpoints, screenshots):
		"""
		Deterministically classify the type of exposure based on titles, tech, and ports.
		Returns a list of exposure categories.
		"""
		text_corpus = ""
		tech_corpus = []
		ports = set()

		# Collect from Subdomain
		if subdomain.page_title:
			text_corpus += f" {subdomain.page_title.lower()}"
		for tech in subdomain.technologies.all():
			tech_corpus.append(tech.name.lower())
		for ip in subdomain.ip_addresses.all():
			for port in ip.ports.all():
				ports.add(port.number)

		# Collect from Endpoints
		for ep in endpoints:
			if ep.page_title:
				text_corpus += f" {ep.page_title.lower()}"
			if ep.http_url:
				text_corpus += f" {ep.http_url.lower()}"
			for tech in ep.techs.all():
				tech_corpus.append(tech.name.lower())

		# Collect from Screenshots
		for sc in screenshots:
			if sc.title:
				text_corpus += f" {sc.title.lower()}"

		tech_corpus = set(tech_corpus)
		classifications = []

		# 1. Access & Security
		vpn_keywords = ['vpn', 'fortigate', 'pulse secure', 'cisco anyconnect', 'globalprotect', 'citrix gateway']
		if any(kw in text_corpus for kw in vpn_keywords) or any('vpn' in tech for tech in tech_corpus):
			classifications.append("VPN Gateway")
			
		ra_ports = {22, 3389, 5900, 23, 5985}
		ra_techs = ['ssh', 'rdp', 'vnc']
		if ports.intersection(ra_ports) or any(t in tech for t in ra_techs for tech in tech_corpus):
			classifications.append("Remote Access Protocol")
			
		sso_keywords = ['sso', 'okta', 'keycloak', 'auth0', 'saml', 'single sign-on']
		if any(kw in text_corpus for kw in sso_keywords):
			classifications.append("Identity & SSO")
			
		waf_techs = ['cloudflare', 'f5', 'imperva', 'akamai', 'fastly']
		if any(t in tech for t in waf_techs for tech in tech_corpus):
			classifications.append("WAF / Edge")

		# 2. Infrastructure & DevOps
		cicd_keywords = ['jenkins', 'gitlab', 'bamboo', 'teamcity', 'github actions']
		if any(kw in text_corpus for kw in cicd_keywords) or any('jenkins' in tech for tech in tech_corpus):
			classifications.append("CI/CD & Automation")
			
		container_keywords = ['kubernetes', 'rancher', 'portainer']
		container_techs = ['docker', 'kubernetes']
		if any(kw in text_corpus for kw in container_keywords) or any(t in tech for t in container_techs for tech in tech_corpus):
			classifications.append("Container / Orchestration")
			
		repo_keywords = ['bitbucket', 'gitea', 'svn', 'gitlab']
		if any(kw in text_corpus for kw in repo_keywords):
			classifications.append("Source Code Repository")
			
		cloud_keywords = ['s3', 'minio', 'azure blob', 'bucket']
		if any(kw in text_corpus for kw in cloud_keywords):
			classifications.append("Cloud Storage")

		# 3. Data & Storage
		db_ports = {3306, 5432, 27017, 1433, 1521, 9200, 6379, 11211}
		db_techs = ['mysql', 'postgres', 'mongodb', 'redis', 'elasticsearch', 'mssql', 'oracle']
		if ports.intersection(db_ports) or any(db in tech for db in db_techs for tech in tech_corpus):
			classifications.append("Database")
			
		fs_ports = {21, 445, 2049, 139}
		fs_techs = ['ftp', 'smb', 'nfs', 'owncloud', 'nextcloud']
		if ports.intersection(fs_ports) or any(fs in tech for fs in fs_techs for tech in tech_corpus):
			classifications.append("File Sharing")
			
		mq_ports = {5672, 9092}
		mq_techs = ['rabbitmq', 'kafka']
		if ports.intersection(mq_ports) or any(mq in tech for mq in mq_techs for tech in tech_corpus):
			classifications.append("Message Queue")

		# 4. Services
		email_ports = {25, 110, 143, 465, 587, 993, 995}
		email_techs = ['exchange', 'postfix', 'zimbra']
		if ports.intersection(email_ports) or any(e in tech for e in email_techs for tech in tech_corpus):
			classifications.append("Email Server")
			
		voip_ports = {5060, 5061}
		voip_techs = ['sip', 'asterisk']
		if ports.intersection(voip_ports) or any(v in tech for v in voip_techs for tech in tech_corpus):
			classifications.append("VoIP / Communication")

		# 5. Web Applications
		admin_keywords = ['admin', 'dashboard', 'control panel', 'login', 'cpanel', 'plesk']
		if any(kw in text_corpus for kw in admin_keywords):
			classifications.append("Admin Portal")
			
		api_keywords = ['api', 'graphql', 'swagger', 'openapi']
		if any(kw in text_corpus for kw in api_keywords) or any(kw in tech for kw in api_keywords for tech in tech_corpus):
			classifications.append("API Endpoint")
			
		staging_keywords = ['dev', 'staging', 'test', 'uat', 'sandbox']
		if any(kw in text_corpus for kw in staging_keywords):
			classifications.append("Staging / Dev")
			
		web_ports = {80, 443, 8080, 8443}
		if "Admin Portal" not in classifications and "API Endpoint" not in classifications and "Staging / Dev" not in classifications:
			if ports.intersection(web_ports) or tech_corpus or text_corpus.strip():
				classifications.append("Web Application")

		if not classifications:
			classifications.append("Unclassified Asset")
			
		return classifications

	def _collect_evidence(self, exposure, subdomain, endpoints, screenshots, vulns):
		"""
		Create ExposureEvidence records based on the underlying data.
		"""
		# Subdomain HTTP details (often from httpx)
		if subdomain.http_status:
			ExposureEvidence.objects.get_or_create(
				exposure=exposure,
				source_tool="HTTP Probe",
				defaults={
					'evidence_data': {
						'url': subdomain.http_url,
						'status': subdomain.http_status,
						'title': subdomain.page_title,
						'webserver': subdomain.webserver
					}
				}
			)

		# Endpoints (e.g., from Katana)
		for ep in endpoints[:5]: # Limit to top 5 to avoid blowing up DB
			ExposureEvidence.objects.get_or_create(
				exposure=exposure,
				source_tool="Crawler",
				evidence_data={
					'url': ep.http_url,
					'status': ep.http_status,
					'title': ep.page_title
				}
			)

		# Screenshots
		for sc in screenshots[:3]:
			ExposureEvidence.objects.get_or_create(
				exposure=exposure,
				source_tool="Screenshot",
				evidence_data={
					'url': sc.url,
					'screenshot_path': sc.screenshot_path,
					'title': sc.title
				}
			)

		# Info-level Vulnerabilities (Nuclei info templates)
		for vuln in vulns.filter(severity=0)[:5]:
			ExposureEvidence.objects.get_or_create(
				exposure=exposure,
				source_tool="Vulnerability Scanner (Info)",
				evidence_data={
					'name': vuln.name,
					'template': vuln.template_id,
					'matched_at': vuln.http_url
				}
			)

