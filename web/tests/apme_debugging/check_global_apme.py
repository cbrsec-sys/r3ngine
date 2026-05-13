import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import ImpactAssessment

total = ImpactAssessment.objects.count()
with_apme = 0
for a in ImpactAssessment.objects.all():
    if a.potential_attack_chain and a.potential_attack_chain.get('apme_path_id'):
        with_apme += 1

print(f"Total ImpactAssessments: {total}")
print(f"ImpactAssessments with apme_path_id: {with_apme}")
