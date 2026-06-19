import logging
from django.db import transaction
from django.db.models import Prefetch, Q
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

		subdomains = Subdomain.objects.filter(
			scan_history=self.scan_history
		).prefetch_related(
			'ip_addresses__ports',
			'technologies',
			'screenshots',
			Prefetch(
				'endpoint_set',
				queryset=EndPoint.objects.filter(
					scan_history=self.scan_history
				).prefetch_related('techs'),
			),
			Prefetch(
				'vulnerability_set',
				queryset=Vulnerability.objects.filter(
					scan_history=self.scan_history
				),
			),
		)

		for subdomain in subdomains:
			self._process_subdomain(subdomain)

	def _process_subdomain(self, subdomain):
		endpoints = subdomain.endpoint_set.all()
		screenshots = subdomain.screenshots.all()
		vulns = subdomain.vulnerability_set.all()

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
			logger.error("Error correlating exposure for subdomain %s: %s", subdomain.name, e, exc_info=True)

	@staticmethod
	def _has_keyword(text_corpus: str, keywords: list[str]) -> bool:
		return any(kw in text_corpus for kw in keywords)

	@staticmethod
	def _has_tech(tech_corpus: set[str], candidates: list[str]) -> bool:
		return any(
			candidate in tech
			for tech in tech_corpus
			for candidate in candidates
		)

	def _classify_exposure(self, subdomain, endpoints, screenshots):
		"""
		Deterministically classify the type of exposure based on titles, tech, and ports.
		Returns a list of exposure categories.
		"""
		text_corpus = ""
		tech_corpus = []
		ports = set()

		if subdomain.page_title:
			text_corpus += f" {subdomain.page_title.lower()}"
		for tech in subdomain.technologies.all():
			tech_corpus.append(tech.name.lower())
		for ip in subdomain.ip_addresses.all():
			for port in ip.ports.all():
				ports.add(port.number)

		for ep in endpoints:
			if ep.page_title:
				text_corpus += f" {ep.page_title.lower()}"
			if ep.http_url:
				text_corpus += f" {ep.http_url.lower()}"
			for tech in ep.techs.all():
				tech_corpus.append(tech.name.lower())

		for sc in screenshots:
			if sc.title:
				text_corpus += f" {sc.title.lower()}"

		tech_corpus = set(tech_corpus)
		has_kw = self._has_keyword
		has_tech = self._has_tech
		classifications = []

		# 1. Access & Security
		if has_kw(text_corpus, ['vpn', 'fortigate', 'pulse secure', 'cisco anyconnect', 'globalprotect', 'citrix gateway']) or has_tech(tech_corpus, ['vpn']):
			classifications.append("VPN Gateway")

		if ports.intersection({22, 3389, 5900, 23, 5985}) or has_tech(tech_corpus, ['ssh', 'rdp', 'vnc']):
			classifications.append("Remote Access Protocol")

		if has_kw(text_corpus, ['sso', 'okta', 'keycloak', 'auth0', 'saml', 'single sign-on']):
			classifications.append("Identity & SSO")

		if has_tech(tech_corpus, ['cloudflare', 'f5', 'imperva', 'akamai', 'fastly']):
			classifications.append("WAF / Edge")

		# 2. Infrastructure & DevOps
		if has_kw(text_corpus, ['jenkins', 'gitlab', 'bamboo', 'teamcity', 'github actions']) or has_tech(tech_corpus, ['jenkins']):
			classifications.append("CI/CD & Automation")

		if has_kw(text_corpus, ['kubernetes', 'rancher', 'portainer']) or has_tech(tech_corpus, ['docker', 'kubernetes']):
			classifications.append("Container / Orchestration")

		if has_kw(text_corpus, ['bitbucket', 'gitea', 'svn', 'gitlab']):
			classifications.append("Source Code Repository")

		if has_kw(text_corpus, ['s3', 'minio', 'azure blob', 'bucket']):
			classifications.append("Cloud Storage")

		# 3. Data & Storage
		if ports.intersection({3306, 5432, 27017, 1433, 1521, 9200, 6379, 11211}) or has_tech(tech_corpus, ['mysql', 'postgres', 'mongodb', 'redis', 'elasticsearch', 'mssql', 'oracle']):
			classifications.append("Database")

		if ports.intersection({21, 445, 2049, 139}) or has_tech(tech_corpus, ['ftp', 'smb', 'nfs', 'owncloud', 'nextcloud']):
			classifications.append("File Sharing")

		if ports.intersection({5672, 9092}) or has_tech(tech_corpus, ['rabbitmq', 'kafka']):
			classifications.append("Message Queue")

		# 4. Services
		if ports.intersection({25, 110, 143, 465, 587, 993, 995}) or has_tech(tech_corpus, ['exchange', 'postfix', 'zimbra']):
			classifications.append("Email Server")

		if ports.intersection({5060, 5061}) or has_tech(tech_corpus, ['sip', 'asterisk']):
			classifications.append("VoIP / Communication")

		# 5. Web Applications
		if has_kw(text_corpus, ['admin', 'dashboard', 'control panel', 'cpanel', 'plesk']):
			classifications.append("Admin Portal")

		if has_kw(text_corpus, ['graphql', 'swagger', 'openapi']) or has_tech(tech_corpus, ['graphql', 'swagger', 'openapi']):
			classifications.append("API Endpoint")

		# Word-boundary prefixes to avoid false positives on e.g. "developer", "attestation"
		subdomain_name = subdomain.name.lower() if subdomain.name else ""
		staging_prefixes = ['dev.', 'staging.', 'test.', 'uat.', 'sandbox.', 'stg.', 'qa.']
		if any(subdomain_name.startswith(p) or f".{p}" in subdomain_name for p in staging_prefixes):
			classifications.append("Staging / Dev")

		if not classifications:
			web_ports = {80, 443, 8080, 8443}
			if ports.intersection(web_ports) or tech_corpus or text_corpus.strip():
				classifications.append("Web Application")

		if not classifications:
			classifications.append("Unclassified Asset")

		return classifications

	def _collect_evidence(self, exposure, subdomain, endpoints, screenshots, vulns):
		"""
		Rebuild ExposureEvidence records for an exposure.
		Deletes stale evidence and bulk-creates fresh records to avoid
		JSONField-based get_or_create duplicates on re-scans.
		"""
		ExposureEvidence.objects.filter(exposure=exposure).delete()

		evidence_batch = []

		if subdomain.http_status:
			evidence_batch.append(ExposureEvidence(
				exposure=exposure,
				source_tool="HTTP Probe",
				evidence_data={
					'url': subdomain.http_url,
					'status': subdomain.http_status,
					'title': subdomain.page_title,
					'webserver': subdomain.webserver,
				},
			))

		for ep in endpoints[:5]:
			evidence_batch.append(ExposureEvidence(
				exposure=exposure,
				source_tool="Crawler",
				evidence_data={
					'url': ep.http_url,
					'status': ep.http_status,
					'title': ep.page_title,
				},
			))

		for sc in screenshots[:3]:
			evidence_batch.append(ExposureEvidence(
				exposure=exposure,
				source_tool="Screenshot",
				evidence_data={
					'url': sc.url,
					'screenshot_path': sc.screenshot_path,
					'title': sc.title,
				},
			))

		for vuln in [v for v in vulns if v.severity == 0][:5]:
			evidence_batch.append(ExposureEvidence(
				exposure=exposure,
				source_tool="Vulnerability Scanner (Info)",
				evidence_data={
					'name': vuln.name,
					'template': vuln.template_id,
					'matched_at': vuln.http_url,
				},
			))

		if evidence_batch:
			ExposureEvidence.objects.bulk_create(evidence_batch)

