from django.forms.models import model_to_dict
from rest_framework import serializers

from api.serializers.users import MinimalUserSerializer
from startScan.models import Exposure, ExposureEvidence, ValidationResult, Vulnerability


class ValidationResultSerializer(serializers.ModelSerializer):
	class Meta:
		model = ValidationResult
		fields = '__all__'


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
