import os
import unittest
import django
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
os.environ['RENGINE_SECRET_KEY'] = 'secret'
django.setup()

from startScan.models import *
from reNgine.correlation import VulnerabilityCorrelationEngine

class TestVulnerabilityCorrelation(unittest.TestCase):
    def setUp(self):
        # Setup basic data
        self.domain, _ = Domain.objects.get_or_create(name='test-correlation.com')
        self.engine, _ = EngineType.objects.get_or_create(engine_name='test_engine', yaml_configuration='')
        self.scan, _ = ScanHistory.objects.get_or_create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now()
        )
        self.subdomain, _ = Subdomain.objects.get_or_create(
            name='app.test-correlation.com',
            target_domain=self.domain,
            scan_history=self.scan
        )
        self.correlator = VulnerabilityCorrelationEngine(scan_history=self.scan)

    def tearDown(self):
        # Clean up in reverse order to respect foreign keys
        ImpactAssessment.objects.filter(scan_history=self.scan).delete()
        Vulnerability.objects.filter(scan_history=self.scan).delete()
        self.subdomain.delete()
        self.scan.delete()
        self.domain.delete()
        self.engine.delete()

    def test_correlation_score_calculation(self):
        # Create a vulnerability
        vuln = Vulnerability.objects.create(
            name="SQL Injection",
            severity=3, # High
            subdomain=self.subdomain,
            scan_history=self.scan,
            type="DAST"
        )
        
        self.correlator.correlate_findings(subdomain_id=self.subdomain.id)
        vuln.refresh_from_db()
        
        # Expected calculation:
        # Severity (3/4 * 0.4) = 0.3
        # Multi-tool (0.5 * 0.3) = 0.15 (Default boost since no other tool found it)
        # Exploit (0.5 * 0.2) = 0.1 (No exploit_url)
        # Criticality (1/5 * 0.1) = 0.02 (Default criticality level 1)
        # Total = 0.57 * 100 = 57.0
        self.assertEqual(vuln.correlation_score, 57.0)

    def test_multi_tool_boost(self):
        # Create a CVE
        cve, _ = CveId.objects.get_or_create(name="CVE-2024-TEST")
        
        # Vuln 1: Nuclei (DAST)
        vuln1 = Vulnerability.objects.create(
            name="Nuclei: CVE-2024-TEST",
            severity=4,
            subdomain=self.subdomain,
            scan_history=self.scan,
            type="DAST"
        )
        vuln1.cve_ids.add(cve)
        
        # Vuln 2: Trivy (SCA)
        vuln2 = Vulnerability.objects.create(
            name="Trivy: CVE-2024-TEST",
            severity=4,
            subdomain=self.subdomain,
            scan_history=self.scan,
            type="SCA"
        )
        vuln2.cve_ids.add(cve)
        
        # Run correlation
        self.correlator.correlate_findings(subdomain_id=self.subdomain.id)
        
        vuln1.refresh_from_db()
        
        # Expected calculation with boost:
        # Severity (4/4 * 0.4) = 0.4
        # Multi-tool boost (1.0 * 0.3) = 0.3 (Two tools found the same CVE)
        # Exploit (0.5 * 0.2) = 0.1
        # Criticality (1/5 * 0.1) = 0.02
        # Total = 0.82 * 100 = 82.0
        self.assertEqual(vuln1.correlation_score, 82.0)

    def test_attack_chain_generation(self):
        vuln = Vulnerability.objects.create(
            name="Insecure Library",
            severity=2,
            subdomain=self.subdomain,
            scan_history=self.scan,
            type="SCA"
        )
        
        self.correlator.correlate_findings(subdomain_id=self.subdomain.id)
        
        from startScan.models import ImpactAssessment
        impact = ImpactAssessment.objects.filter(vulnerability=vuln).first()
        
        self.assertIsNotNone(impact)
        self.assertIsNotNone(impact.potential_attack_chain)
        self.assertEqual(impact.potential_attack_chain['confidence'], 'Medium')
        
        phases = [step['phase'] for step in impact.potential_attack_chain['steps']]
        self.assertIn('Discovery', phases)
        self.assertIn('Exploitation', phases)
        self.assertIn('Post-Exploitation', phases)
