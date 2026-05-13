import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from apme.orchestrator import APMEOrchestrator

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)

scan_id = 60
orchestrator = APMEOrchestrator()
print(f"Running APME Orchestrator for Scan {scan_id}...")
results = orchestrator.run(scan_id)

print("\nResults:")
print(f"Total Paths Found: {results.get('total_paths')}")
print(f"Returned Paths: {results.get('returned_paths')}")

if results.get('paths'):
    print("\nSample Path ID from first result:")
    print(results['paths'][0]['apme_path_id'])
