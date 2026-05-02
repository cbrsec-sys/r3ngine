from rest_framework import serializers

class DashboardKPISerializer(serializers.Serializer):
    domain_count = serializers.IntegerField()
    subdomain_count = serializers.IntegerField()
    endpoint_count = serializers.IntegerField()
    vulnerability_count = serializers.IntegerField()
    critical_count = serializers.IntegerField()
    high_count = serializers.IntegerField()
    medium_count = serializers.IntegerField()
    low_count = serializers.IntegerField()
    info_count = serializers.IntegerField()
    unknown_count = serializers.IntegerField()
    secret_leak_count = serializers.IntegerField()
    alive_count = serializers.IntegerField()
    endpoint_alive_count = serializers.IntegerField()
    total_vul_count = serializers.IntegerField()

class DashboardTrendsSerializer(serializers.Serializer):
    targets_in_last_week = serializers.ListField(child=serializers.IntegerField())
    subdomains_in_last_week = serializers.ListField(child=serializers.IntegerField())
    endpoints_in_last_week = serializers.ListField(child=serializers.IntegerField())
    vulns_in_last_week = serializers.ListField(child=serializers.IntegerField())
    leaks_in_last_week = serializers.ListField(child=serializers.IntegerField())
    last_7_dates = serializers.ListField(child=serializers.DateField())

class DashboardDistributionItemSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    address = serializers.CharField(required=False)
    number = serializers.IntegerField(required=False)
    service_name = serializers.CharField(required=False)
    count = serializers.IntegerField()
    nused = serializers.IntegerField(required=False)

class DashboardGeoSerializer(serializers.Serializer):
    name = serializers.CharField()
    iso = serializers.CharField()
    count = serializers.IntegerField()

class DashboardDataSerializer(serializers.Serializer):
    project_info = serializers.DictField()
    kpis = DashboardKPISerializer()
    trends = DashboardTrendsSerializer()
    most_used_port = DashboardDistributionItemSerializer(many=True)
    most_used_ip = DashboardDistributionItemSerializer(many=True)
    most_used_tech = DashboardDistributionItemSerializer(many=True)
    most_common_cve = DashboardDistributionItemSerializer(many=True)
    most_common_cwe = DashboardDistributionItemSerializer(many=True)
    most_common_tags = DashboardDistributionItemSerializer(many=True)
    asset_countries = DashboardGeoSerializer(many=True)
    most_vulnerable_targets = serializers.ListField()
    most_common_vulnerabilities = serializers.ListField()
    activity_feed = serializers.ListField()

    vulnerability_feed = serializers.ListField()

