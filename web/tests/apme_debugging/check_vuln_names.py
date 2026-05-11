import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from startScan.models import Vulnerability

scan_id = 60
vulns = Vulnerability.objects.filter(scan_history_id=scan_id)[:20]
for v in vulns:
    print(f"Name: {v.name}, Type: {v.type}")
