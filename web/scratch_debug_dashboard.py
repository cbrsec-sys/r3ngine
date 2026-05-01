import os
import django
import sys
import json
from django.core.serializers.json import DjangoJSONEncoder

# Setup Django inside container
sys.path.append('/usr/src/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from dashboard.models import Project
from api.dashboard_views import DashboardAPIView
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth.models import User

def test_dashboard_api(slug):
    factory = APIRequestFactory()
    request = factory.get(f'/api/dashboard/{slug}/')
    
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
        
    force_authenticate(request, user=user)
    
    view = DashboardAPIView.as_view()
    try:
        response = view(request, slug=slug)
        if response.status_code == 200:
            vulns = response.data.get('vulnerability_feed', [])
            if vulns:
                # Print only first item keys and some fields
                item = vulns[0]
                print("Keys:", list(item.keys()))
                print("Severity:", item.get('severity'))
                print("Name:", item.get('name'))
                print("Type:", item.get('type'))
                print("Scan History Keys:", list(item.get('scan_history', {}).keys()) if item.get('scan_history') else "None")
            else:
                print("Vulnerability feed is empty")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dashboard_api('default')
