from rest_framework import serializers

from reNgine.common_func import extract_path_from_url, get_interesting_subdomains
from startScan.models import (
    DirectoryFile, DirectoryScan, EndPoint, IpAddress, Port, Screenshot, Subdomain,
    Technology, Waf, WafBypassFinding,
)


class OnlySubdomainNameSerializer(serializers.ModelSerializer):
	class Meta:
		model = Subdomain
		fields = ['name', 'id']


class OnlySubdomainNameSerializer(serializers.ModelSerializer):
	class Meta:
		model = Subdomain
		fields = ['name', 'id']


class SubdomainChangesSerializer(serializers.ModelSerializer):

	change = serializers.SerializerMethodField('get_change')
	is_interesting = serializers.SerializerMethodField('get_is_interesting')

	class Meta:
		model = Subdomain
		fields = '__all__'

	def get_change(self, Subdomain):
		return Subdomain.change

	def get_is_interesting(self, Subdomain):
		return (
			get_interesting_subdomains(Subdomain.scan_history.id)
			.filter(name=Subdomain.name)
			.exists()
		)


class InterestingSubdomainSerializer(serializers.ModelSerializer):

	class Meta:
		model = Subdomain
		fields = ['name']


class TechnologyCountSerializer(serializers.Serializer):
	count = serializers.CharField()
	name = serializers.CharField()


class TechnologySerializer(serializers.ModelSerializer):
	class Meta:
		model = Technology
		fields = '__all__'


class PortSerializer(serializers.ModelSerializer):
	class Meta:
		model = Port
		fields = '__all__'


class IpSerializer(serializers.ModelSerializer):
	ports = PortSerializer(many=True)
	geo_iso_name = serializers.ReadOnlyField(source='geo_iso.name')

	class Meta:
		model = IpAddress
		fields = '__all__'


class DirectoryFileSerializer(serializers.ModelSerializer):

	class Meta:
		model = DirectoryFile
		fields = '__all__'


class EndPointDirectorySerializer(serializers.ModelSerializer):
	url = serializers.CharField(source='http_url')
	length = serializers.IntegerField(source='content_length', default=0)
	lines = serializers.SerializerMethodField()
	words = serializers.SerializerMethodField()
	name = serializers.SerializerMethodField()
	content_type = serializers.CharField(default='text/html')

	class Meta:
		model = EndPoint
		fields = ['id', 'length', 'lines', 'http_status', 'words', 'name', 'url', 'content_type']

	def get_lines(self, obj):
		return 0

	def get_words(self, obj):
		return 0

	def get_name(self, obj):
		import base64
		path = extract_path_from_url(obj.http_url) or '/'
		return base64.b64encode(path.encode('utf-8')).decode('utf-8')


class DirectoryScanSerializer(serializers.ModelSerializer):
	scanned_date = serializers.SerializerMethodField()
	formatted_date_for_id = serializers.SerializerMethodField()
	directory_files = DirectoryFileSerializer(many=True)

	class Meta:
		model = DirectoryScan
		fields = '__all__'

	def get_scanned_date(self, DirectoryScan):
		if DirectoryScan.scanned_date:
			return DirectoryScan.scanned_date.strftime("%b %d, %Y %H:%M")
		return None

	def get_formatted_date_for_id(self, DirectoryScan):
		if DirectoryScan.scanned_date:
			return DirectoryScan.scanned_date.strftime("%b_%d_%Y_%H_%M")
		return None


class IpSubdomainSerializer(serializers.ModelSerializer):

	class Meta:
		model = Subdomain
		fields = ['name', 'ip_addresses']
		depth = 1


class WafSerializer(serializers.ModelSerializer):

	class Meta:
		model = Waf
		fields = '__all__'


class WafBypassFindingSerializer(serializers.ModelSerializer):
	class Meta:
		model = WafBypassFinding
		fields = '__all__'


class ScreenshotSerializer(serializers.ModelSerializer):
	screenshot_path = serializers.SerializerMethodField('get_screenshot_path')
	subdomain_name = serializers.CharField(source='subdomain.name', read_only=True)

	class Meta:
		model = Screenshot
		fields = '__all__'

	def get_screenshot_path(self, screenshot):
		path = screenshot.screenshot_path
		if path:
			from django.conf import settings
			import os
			# If the path is already absolute (starts with /), try to make it relative to MEDIA_ROOT
			if os.path.isabs(path) and path.startswith(settings.MEDIA_ROOT):
				path = os.path.relpath(path, settings.MEDIA_ROOT)

			# If the path doesn't contain the results_dir prefix, add it
			results_dir = screenshot.scan_history.results_dir if screenshot.scan_history else ""
			if results_dir and results_dir.startswith(settings.MEDIA_ROOT):
				rel_results_dir = os.path.relpath(results_dir, settings.MEDIA_ROOT)
				# Check if rel_results_dir is already a prefix of path
				if not path.startswith(rel_results_dir):
					path = os.path.join(rel_results_dir, path)

			return path.replace('\\', '/')
		return None


class SubdomainSerializer(serializers.ModelSerializer):

	vuln_count = serializers.SerializerMethodField('get_vuln_count')

	is_interesting = serializers.SerializerMethodField('get_is_interesting')

	endpoint_count = serializers.SerializerMethodField('get_endpoint_count')
	info_count = serializers.SerializerMethodField('get_info_count')
	low_count = serializers.SerializerMethodField('get_low_count')
	medium_count = serializers.SerializerMethodField('get_medium_count')
	high_count = serializers.SerializerMethodField('get_high_count')
	critical_count = serializers.SerializerMethodField('get_critical_count')
	todos_count = serializers.SerializerMethodField('get_todos_count')
	directories_count = serializers.SerializerMethodField('get_directories_count')
	subscan_count = serializers.SerializerMethodField('get_subscan_count')
	ip_addresses = IpSerializer(many=True)
	waf = WafSerializer(many=True)
	technologies = TechnologySerializer(many=True)
	directories = DirectoryScanSerializer(many=True)
	waf_bypass_findings = WafBypassFindingSerializer(many=True, read_only=True)
	screenshots = ScreenshotSerializer(many=True, read_only=True)
	screenshot_path = serializers.SerializerMethodField('get_screenshot_path')


	class Meta:
		model = Subdomain
		fields = '__all__'

	def get_screenshot_path(self, subdomain):
		from reNgine.utilities import get_screenshot_path
		return get_screenshot_path(subdomain)


	def get_is_interesting(self, subdomain):
		scan_id = subdomain.scan_history.id if subdomain.scan_history else None
		return (
			get_interesting_subdomains(scan_id)
			.filter(name=subdomain.name)
			.exists()
		)

	def get_endpoint_count(self, subdomain):
		return subdomain.get_endpoint_count

	def get_info_count(self, subdomain):
		return subdomain.get_info_count

	def get_low_count(self, subdomain):
		return subdomain.get_low_count

	def get_medium_count(self, subdomain):
		return subdomain.get_medium_count

	def get_high_count(self, subdomain):
		return subdomain.get_high_count

	def get_critical_count(self, subdomain):
		return subdomain.get_critical_count

	def get_directories_count(self, subdomain):
		return subdomain.get_directories_count

	def get_subscan_count(self, subdomain):
		return subdomain.get_subscan_count

	def get_todos_count(self, subdomain):
		return len(subdomain.get_todos.filter(is_done=False))

	def get_vuln_count(self, obj):
		try:
			return obj.vuln_count
		except:
			return None
