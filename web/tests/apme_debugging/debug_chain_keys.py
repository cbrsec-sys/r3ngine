import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import ImpactAssessment, ScanHistory

scan_id = 60
try:
    scan = ScanHistory.objects.get(id=scan_id)
    assessment = ImpactAssessment.objects.filter(scan_history=scan).first()
    if assessment:
        print(f"ID: {assessment.id}")
        print(f"Chain keys: {assessment.potential_attack_chain.keys() if assessment.potential_attack_chain else 'None'}")
        print(f"Chain content: {assessment.potential_attack_chain}")
    else:
        print("No assessment found")
except Exception as e:
    print(f"Error: {e}")
