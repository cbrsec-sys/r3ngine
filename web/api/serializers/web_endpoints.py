from rest_framework import serializers

from api.serializers.hosts import TechnologySerializer
from startScan.models import AuthCandidate, EndPoint, Parameter


class EndPointChangesSerializer(serializers.ModelSerializer):

	change = serializers.SerializerMethodField('get_change')

	class Meta:
		model = EndPoint
		fields = '__all__'

	def get_change(self, EndPoint):
		return EndPoint.change


class InterestingEndPointSerializer(serializers.ModelSerializer):

	class Meta:
		model = EndPoint
		fields = ['http_url']


class ParameterEndpointSerializer(serializers.ModelSerializer):
	class Meta:
		model = EndPoint
		fields = ['id', 'http_url']


class ParameterSerializer(serializers.ModelSerializer):
	endpoint = ParameterEndpointSerializer(read_only=True)

	class Meta:
		model = Parameter
		fields = [
			'id', 'name', 'value', 'type',
			'confidence', 'sources', 'param_location',
			'data_type', 'is_auth_related',
			'observed_in_js', 'observed_in_openapi', 'observed_in_graphql',
			'endpoint',
		]


class AuthCandidateSerializer(serializers.ModelSerializer):
	class Meta:
		model = AuthCandidate
		fields = '__all__'


class EndpointSerializer(serializers.ModelSerializer):

	techs = TechnologySerializer(many=True)
	parameters = ParameterSerializer(many=True, read_only=True)
	auth_candidates = AuthCandidateSerializer(many=True, read_only=True, source='authcandidate_set')

	class Meta:
		model = EndPoint
		fields = '__all__'


class EndpointOnlyURLsSerializer(serializers.ModelSerializer):

	class Meta:
		model = EndPoint
		fields = ['http_url']
