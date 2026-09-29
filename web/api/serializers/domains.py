from django.apps import apps
from django.contrib.humanize.templatetags.humanize import naturalday, naturaltime
from rest_framework import serializers

from targetApp.models import Domain, Organization


class DomainSerializer(serializers.ModelSerializer):
	vuln_count = serializers.SerializerMethodField()
	subdomain_count = serializers.SerializerMethodField()
	vulnerability_count = serializers.SerializerMethodField()
	organization = serializers.SerializerMethodField()
	most_recent_scan = serializers.SerializerMethodField()
	insert_date = serializers.SerializerMethodField()
	insert_date_humanized = serializers.SerializerMethodField()
	start_scan_date = serializers.SerializerMethodField()
	start_scan_date_humanized = serializers.SerializerMethodField()
	most_recent_scan_status = serializers.SerializerMethodField()
	most_recent_scan_progress = serializers.SerializerMethodField()

	class Meta:
		model = Domain
		fields = '__all__'
		depth = 2

	def _get_recent_scan(self, obj):
		ScanHistory = apps.get_model('startScan.ScanHistory')
		return (
			ScanHistory.objects
			.filter(domain__id=obj.id)
			.order_by('-id')
			.first()
		)

	def get_vuln_count(self, obj):
		from startScan.models import Vulnerability
		return Vulnerability.objects.filter(target_domain=obj).count()

	def get_vulnerability_count(self, obj):
		from startScan.models import Vulnerability
		return Vulnerability.objects.filter(target_domain=obj).count()

	def get_subdomain_count(self, obj):
		from startScan.models import Subdomain
		return Subdomain.objects.filter(target_domain=obj).values('name').distinct().count()

	def get_organization(self, obj):
		if Organization.objects.filter(domains__id=obj.id).exists():
			return [org.name for org in Organization.objects.filter(domains__id=obj.id)]

	def get_most_recent_scan(self, obj):
		recent_scan = self._get_recent_scan(obj)
		return recent_scan.id if recent_scan else None

	def get_insert_date(self, obj):
		if obj.insert_date:
			return naturalday(obj.insert_date).title()

	def get_insert_date_humanized(self, obj):
		if obj.insert_date:
			return naturaltime(obj.insert_date).title()

	def get_start_scan_date(self, obj):
		if obj.start_scan_date:
			return naturalday(obj.start_scan_date).title()

	def get_start_scan_date_humanized(self, obj):
		if obj.start_scan_date:
			return naturaltime(obj.start_scan_date).title()

	def get_most_recent_scan_status(self, obj):
		recent_scan = self._get_recent_scan(obj)
		if recent_scan:
			from reNgine.definitions import CELERY_TASK_STATUS_MAP
			return CELERY_TASK_STATUS_MAP.get(recent_scan.scan_status, 'UNKNOWN')
		return 'NEVER_SCANNED'

	def get_most_recent_scan_progress(self, obj):
		recent_scan = self._get_recent_scan(obj)
		if recent_scan:
			return recent_scan.get_progress() or 0
		return 0


class OrganizationSerializer(serializers.ModelSerializer):

	class Meta:
		model = Organization
		fields = '__all__'


class OrganizationTargetsSerializer(serializers.ModelSerializer):

	class Meta:
		model = Domain
		fields = [
			'name',
			'id'
		]
