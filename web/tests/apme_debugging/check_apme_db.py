import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import ImpactAssessment, ScanHistory

scan_id = 60 # From screenshot
try:
    scan = ScanHistory.objects.get(id=scan_id)
    print(f"Scan found: {scan.domain.name}")
    assessments = ImpactAssessment.objects.filter(scan_history=scan)
    print(f"Total ImpactAssessments: {assessments.count()}")
    for a in assessments:
        print(f"ID: {a.id}, Vuln: {a.vulnerability}, Chain: {a.potential_attack_chain is not None}")
        if a.potential_attack_chain:
            print(f"  Path ID: {a.potential_attack_chain.get('apme_path_id')}")
except Exception as e:
    print(f"Error: {e}")
