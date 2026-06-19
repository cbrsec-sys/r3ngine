from django.test import TestCase
from django.utils import timezone
from startScan.models import ScanHistory, Domain, Subdomain, EndPoint, Screenshot, Vulnerability, Exposure, ExposureEvidence, Technology, IpAddress, Port
from scanEngine.models import EngineType
from reNgine.exposure_correlation import ExposureCorrelationEngine

class ExposureCorrelationEngineTests(TestCase):
    def setUp(self):
        self.domain = Domain.objects.create(name="example.com")
        self.engine = EngineType.objects.create(
            engine_name="Test Engine",
            yaml_configuration="{}"
        )
        self.scan_history = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now(),
            scan_status=2
        )
        self.subdomain = Subdomain.objects.create(
            scan_history=self.scan_history,
            target_domain=self.domain,
            name="vpn.example.com",
            http_status=200,
            http_url="https://vpn.example.com",
            page_title="GlobalProtect Portal",
            webserver="nginx"
        )
        self.tech_vpn = Technology.objects.create(name="Pulse Secure")
        self.subdomain.technologies.add(self.tech_vpn)

    def test_classify_vpn_gateway(self):
        engine = ExposureCorrelationEngine(scan_history=self.scan_history)
        engine.correlate_exposures()
        
        exposure = Exposure.objects.get(subdomain=self.subdomain)
        self.assertIn("VPN Gateway", exposure.type)
        self.assertEqual(exposure.status, "open")

    def test_collect_evidence_and_link_vulns(self):
        vuln = Vulnerability.objects.create(
            scan_history=self.scan_history,
            target_domain=self.domain,
            subdomain=self.subdomain,
            name="Open Port Info",
            severity=0,
            http_url="https://vpn.example.com"
        )
        
        engine = ExposureCorrelationEngine(scan_history=self.scan_history)
        engine.correlate_exposures()
        
        exposure = Exposure.objects.get(subdomain=self.subdomain)
        
        # Check evidence
        evidence_count = ExposureEvidence.objects.filter(exposure=exposure).count()
        self.assertGreater(evidence_count, 0)
        
        # Check linked vuln
        vuln.refresh_from_db()
        self.assertEqual(vuln.exposure_id, exposure.id)

    def test_database_classification(self):
        db_sub = Subdomain.objects.create(
            scan_history=self.scan_history,
            target_domain=self.domain,
            name="db.example.com"
        )
        ip = IpAddress.objects.create(address="10.0.0.1")
        port = Port.objects.create(number=5432)
        ip.ports.add(port)
        db_sub.ip_addresses.add(ip)
        
        engine = ExposureCorrelationEngine(scan_history=self.scan_history)
        engine.correlate_exposures()
        
        exposure = Exposure.objects.get(subdomain=db_sub)
        self.assertIn("Database", exposure.type)
