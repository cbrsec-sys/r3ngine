from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from rolepermissions.roles import assign_role

from dashboard.models import Project
from targetApp.models import Domain
from startScan.models import ScanHistory, Vulnerability, CveId, CweId
from scanEngine.models import EngineType

User = get_user_model()


class DashboardCveCweTestCase(TestCase):
    """
    Test suite to verify that the DashboardAPIView correctly retrieves 
    CWE and CVE statistics aggregated across all assessments (scans) 
    within a specific project, and does not bleed data from other projects.
    """

    def setUp(self):
        """
        Set up user authentication and project data with multiple scan 
        histories and associated vulnerabilities.
        """
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='dashboarduser', 
            password='dashboardpassword',
            email='dash@example.com',
            is_staff=True,
            is_superuser=True
        )
        self.client.force_authenticate(user=self.user)
        self.client.force_login(self.user)
        assign_role(self.user, 'sys_admin')

        # Create main test project
        self.project = Project.objects.create(
            name='Test Project A',
            slug='test-project-a',
            insert_date=timezone.now()
        )

        # Create other project to test isolation
        self.other_project = Project.objects.create(
            name='Other Project B',
            slug='other-project-b',
            insert_date=timezone.now()
        )

        self.engine = EngineType.objects.create(
            engine_name='test_engine', 
            yaml_configuration=''
        )

        # Main project setup: two assessments (scans)
        self.domain = Domain.objects.create(
            name='example.com', 
            project=self.project,
            insert_date=timezone.now()
        )

        self.scan1 = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now()
        )

        self.scan2 = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now()
        )

        # Enriched CVEs and CWEs
        self.cve1 = CveId.objects.create(
            name='CVE-2026-9999', 
            cvss_v31_base_score=9.8
        )
        self.cve2 = CveId.objects.create(
            name='CVE-2026-8888', 
            cvss_v31_base_score=7.5
        )

        self.cwe1 = CweId.objects.create(name='CWE-79')
        self.cwe2 = CweId.objects.create(name='CWE-89')

        # Scan 1 vulnerabilities
        self.vuln1 = Vulnerability.objects.create(
            name='Vulnerability 1',
            severity=3,
            scan_history=self.scan1,
            target_domain=self.domain,
            discovered_date=timezone.now()
        )
        self.vuln1.cve_ids.add(self.cve1)
        self.vuln1.cwe_ids.add(self.cwe1)

        # Scan 2 vulnerabilities (different assessment, same project)
        self.vuln2 = Vulnerability.objects.create(
            name='Vulnerability 2',
            severity=4,
            scan_history=self.scan2,
            target_domain=self.domain,
            discovered_date=timezone.now()
        )
        self.vuln2.cve_ids.add(self.cve1)
        self.vuln2.cve_ids.add(self.cve2)
        self.vuln2.cwe_ids.add(self.cwe1)
        self.vuln2.cwe_ids.add(self.cwe2)

        # Isolation project setup
        self.other_domain = Domain.objects.create(
            name='other.com', 
            project=self.other_project,
            insert_date=timezone.now()
        )

        self.other_scan = ScanHistory.objects.create(
            domain=self.other_domain,
            scan_type=self.engine,
            start_scan_date=timezone.now()
        )

        self.other_vuln = Vulnerability.objects.create(
            name='Other Vulnerability',
            severity=2,
            scan_history=self.other_scan,
            target_domain=self.other_domain,
            discovered_date=timezone.now()
        )
        # Add cve2 to other project's vuln
        self.other_vuln.cve_ids.add(self.cve2)

    def test_dashboard_cve_cwe_counts_aggregate_across_all_assessments(self):
        """
        Verify that fetching the dashboard API returns the correct count 
        of CVEs and CWEs aggregated across multiple scan histories in the project,
        excluding data from other projects.
        """
        url = reverse('api:dashboard_api', kwargs={'slug': self.project.slug})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('most_common_cve', data)
        self.assertIn('most_common_cwe', data)

        # Verify CVE counts:
        # CVE-2026-9999 should have a count of 2 (found in vuln1 and vuln2 of project A)
        # CVE-2026-8888 should have a count of 1 (found in vuln2 of project A; the occurrence in Project B should not be added)
        cve_counts = {item['name']: item['count'] for item in data['most_common_cve']}
        
        self.assertEqual(cve_counts.get('CVE-2026-9999'), 2)
        self.assertEqual(cve_counts.get('CVE-2026-8888'), 1)

        # Verify CWE counts:
        # CWE-79 should have a count of 2 (found in vuln1 and vuln2 of project A)
        # CWE-89 should have a count of 1 (found in vuln2 of project A)
        cwe_counts = {item['name']: item['count'] for item in data['most_common_cwe']}
        
        self.assertEqual(cwe_counts.get('CWE-79'), 2)
        self.assertEqual(cwe_counts.get('CWE-89'), 1)
