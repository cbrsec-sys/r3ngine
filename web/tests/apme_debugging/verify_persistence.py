import os
import django
import sys

# Ensure the project root is in sys.path
sys.path.append('/usr/src/app')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import ImpactAssessment

scan_id = 60
assessments = ImpactAssessment.objects.filter(scan_history_id=scan_id)
print(f"Total assessments for scan 60: {assessments.count()}")

found_apme = 0
for a in assessments:
    if a.potential_attack_chain and 'apme_path_id' in a.potential_attack_chain:
        found_apme += 1
        print(f"Assessment {a.id}: APME Path ID = {a.potential_attack_chain['apme_path_id']}")

print(f"Total APME paths found in DB: {found_apme}")
