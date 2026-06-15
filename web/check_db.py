import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import Vulnerability, ScanHistory, SubScan

print("=== DB CHECK ===")
print(f"Total vulnerabilities: {Vulnerability.objects.count()}")
print(f"Acunetix vulnerabilities: {Vulnerability.objects.filter(source='Acunetix').count()}")
print("\nRecent SubScans:")
for sub in SubScan.objects.order_by('-id')[:5]:
    print(f"SubScan ID: {sub.id}, Domain: {sub.subdomain.name}, Task: {sub.type}, Status: {sub.status}")
    vulns = Vulnerability.objects.filter(vuln_subscan_ids=sub)
    print(f" -> Linked vulnerabilities (via ManyToMany): {vulns.count()}")

print("\nRecent Vulnerabilities:")
for v in Vulnerability.objects.order_by('-id')[:5]:
    print(f"Vuln: {v.name}, Source: {v.source}, Scan ID: {v.scan_history_id}, Severity: {v.severity}")
