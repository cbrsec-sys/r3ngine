from django.db import models
from django.db.models import prefetch_related_objects
from django.forms.models import model_to_dict
from rest_framework import serializers

from api.serializers.users import MinimalUserSerializer
from startScan.models import Exposure, ExposureEvidence, ValidationResult, Vulnerability


class ValidationResultSerializer(serializers.ModelSerializer):
	class Meta:
		model = ValidationResult
		fields = '__all__'


def _nested(prefix: str, names: tuple[str, ...]) -> tuple[str, ...]:
	return tuple(f'{prefix}__{name}' for name in names)


# Many-to-many fields a depth-0 nested object renders as primary-key lists.
_SCAN_M2M = ('emails', 'employees', 'buckets', 'dorks')
_SUBDOMAIN_M2M = ('technologies', 'ip_addresses', 'directories', 'waf')
_ENDPOINT_M2M = ('techs', 'endpoint_subscan_ids')
_DOMAIN_INFO_M2M = (
	'status', 'name_servers', 'dns_records', 'related_domains',
	'related_tlds', 'similar_domains', 'historical_ips',
)


class VulnerabilityListSerializer(serializers.ListSerializer):
	"""Load VulnerabilitySerializer's nested graph once for the whole list.

	The serializer uses depth=2 over five foreign keys and five many-to-many
	fields, so each vulnerability drags in its subdomain, endpoint, exposure
	and target with their own relations: about fifty queries per row. Every
	path that nesting reaches is prefetched here over the rows being
	serialized (one page, in the list view), which makes the cost a fixed
	number of queries per page instead.
	"""

	PREFETCHES = (
		# get_scan_history
		'scan_history', 'scan_history__domain',
		'scan_history__initiated_by', 'scan_history__aborted_by',
		'validation_results',
		'tags', 'references', 'cwe_ids', 'cve_ids', 'cve_ids__related_cves',
		'cve_ids__related_cves__related_cves',
		'target_domain', 'target_domain__project', 'target_domain__monitor_engine',
		'target_domain__temporal_schedule', 'target_domain__domain_info',
		*_nested('target_domain__domain_info', _DOMAIN_INFO_M2M),
		'subdomain', 'subdomain__target_domain', 'subdomain__technologies',
		'subdomain__waf', 'subdomain__scan_history',
		*_nested('subdomain__scan_history', _SCAN_M2M),
		'subdomain__ip_addresses',
		*_nested('subdomain__ip_addresses', ('ports', 'ip_subscan_ids')),
		'subdomain__directories',
		*_nested('subdomain__directories', ('directory_files', 'dir_subscan_ids')),
		'endpoint', 'endpoint__target_domain', 'endpoint__techs',
		'endpoint__scan_history', *_nested('endpoint__scan_history', _SCAN_M2M),
		'endpoint__subdomain', *_nested('endpoint__subdomain', _SUBDOMAIN_M2M),
		'endpoint__endpoint_subscan_ids',
		'endpoint__endpoint_subscan_ids__subdomain_subscan_ids',
		'exposure', 'exposure__target_domain',
		'exposure__scan_history', *_nested('exposure__scan_history', _SCAN_M2M),
		'exposure__subdomain', *_nested('exposure__subdomain', _SUBDOMAIN_M2M),
		'exposure__endpoint', *_nested('exposure__endpoint', _ENDPOINT_M2M),
		'vuln_subscan_ids', 'vuln_subscan_ids__assessment', 'vuln_subscan_ids__engine',
		'vuln_subscan_ids__subdomain_subscan_ids',
		*_nested('vuln_subscan_ids__subdomain_subscan_ids', _SUBDOMAIN_M2M),
		'vuln_subscan_ids__scan_history', *_nested('vuln_subscan_ids__scan_history', _SCAN_M2M),
		'vuln_subscan_ids__subdomain', *_nested('vuln_subscan_ids__subdomain', _SUBDOMAIN_M2M),
	)

	def to_representation(self, data) -> list:
		rows = list(data.all() if isinstance(data, models.manager.BaseManager) else data)
		prefetch_related_objects(rows, *self.PREFETCHES)
		return super().to_representation(rows)


class VulnerabilitySerializer(serializers.ModelSerializer):

	discovered_date = serializers.SerializerMethodField()
	severity = serializers.SerializerMethodField()
	scan_history = serializers.SerializerMethodField()
	validation_results = ValidationResultSerializer(many=True, read_only=True)

	def get_discovered_date(self, Vulnerability):
		if Vulnerability.discovered_date:
			return Vulnerability.discovered_date.strftime("%b %d, %Y %H:%M")
		return None

	def get_severity(self, Vulnerability):
		if Vulnerability.severity == 0:
			return "Info"
		elif Vulnerability.severity == 1:
			return "Low"
		elif Vulnerability.severity == 2:
			return "Medium"
		elif Vulnerability.severity == 3:
			return "High"
		elif Vulnerability.severity == 4:
			return "Critical"
		elif Vulnerability.severity == -1:
			return "Unknown"
		else:
			return "Unknown"
		
	def get_scan_history(self, vulnerability):
		scan_history_dict = {}
		scan_history = vulnerability.scan_history
		if scan_history:
			scan_history_dict = model_to_dict(
				scan_history, 
				exclude=['emails', 'employees', 'buckets', 'dorks']
			)
			scan_history_dict['domain'] = {
				'name': scan_history.domain.name,
			}
			scan_history_dict['initiated_by'] = MinimalUserSerializer(scan_history.initiated_by).data if scan_history.initiated_by else None
			scan_history_dict['aborted_by'] = MinimalUserSerializer(scan_history.aborted_by).data if scan_history.aborted_by else None
			scan_history_dict['completed_ago'] = scan_history.get_completed_ago()
		return scan_history_dict

	class Meta:
		model = Vulnerability
		fields = '__all__'
		depth = 2
		list_serializer_class = VulnerabilityListSerializer


class ExposureEvidenceSerializer(serializers.ModelSerializer):
	class Meta:
		model = ExposureEvidence
		fields = '__all__'


class ExposureStatusUpdateSerializer(serializers.ModelSerializer):
	"""Write-only serializer for status transitions on an Exposure."""
	class Meta:
		model = Exposure
		fields = ['status']


class ExposureSerializer(serializers.ModelSerializer):
	evidence = ExposureEvidenceSerializer(many=True, read_only=True)
	scan_history = serializers.SerializerMethodField()
	discovered_date = serializers.SerializerMethodField()

	class Meta:
		model = Exposure
		fields = '__all__'
		depth = 2

	def get_discovered_date(self, obj):
		if obj.first_seen:
			return obj.first_seen.strftime("%b %d, %Y %H:%M")
		return None

	def get_scan_history(self, obj):
		scan_history_dict = {}
		scan_history = obj.scan_history
		if scan_history:
			scan_history_dict = model_to_dict(
				scan_history, 
				exclude=['emails', 'employees', 'buckets', 'dorks']
			)
			if scan_history.domain:
				scan_history_dict['domain'] = {
					'name': scan_history.domain.name,
				}
			scan_history_dict['initiated_by'] = MinimalUserSerializer(scan_history.initiated_by).data if scan_history.initiated_by else None
			scan_history_dict['aborted_by'] = MinimalUserSerializer(scan_history.aborted_by).data if scan_history.aborted_by else None
			scan_history_dict['completed_ago'] = scan_history.get_completed_ago()
		return scan_history_dict
