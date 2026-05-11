import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import Vulnerability

scan_id = 60
print("Potentially Impactful Vulns:")
vulns = Vulnerability.objects.filter(scan_history_id=scan_id).filter(
    django.db.models.Q(name__icontains='SQL') | 
    django.db.models.Q(name__icontains='Execution') |
    django.db.models.Q(name__icontains='Bypass') |
    django.db.models.Q(name__icontains='Leak')
)
for v in vulns:
    print(f"Name: {v.name}, Type: {v.type}")
print(f"Total: {vulns.count()}")
