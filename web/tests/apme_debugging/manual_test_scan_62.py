import os
import django
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from apme.orchestrator import APMEOrchestrator
from startScan.models import ScanHistory, ImpactAssessment

scan_id = 62
try:
    print(f"Manual Test: Running full APME Orchestrator for scan {scan_id}...")
    
    # 1. Check scan existence
    try:
        scan = ScanHistory.objects.get(id=scan_id)
        print(f"Found scan {scan_id} for domain: {scan.domain.name}")
    except ScanHistory.DoesNotExist:
        print(f"Error: Scan {scan_id} not found.")
        exit(1)

    # 2. Run Orchestrator
    orch = APMEOrchestrator(top_n=10)
    results = orch.run(scan_id)
    
    print(f"\nAPME Run completed.")
    print(f"Total paths found: {results.get('total_paths', 0)}")
    
    # 3. Check Persisted Results
    # Filter for records that have an APME path ID in the potential_attack_chain
    findings = ImpactAssessment.objects.filter(
        scan_history_id=scan_id,
        potential_attack_chain__apme_path_id__isnull=False
    )
    print(f"Persisted APME Attack Paths: {findings.count()}")
    
    for i, finding in enumerate(findings):
        chain = finding.potential_attack_chain
        print(f"\n--- Finding {i+1} ---")
        print(f"Path ID: {chain.get('apme_path_id')}")
        print(f"Risk: {chain.get('risk')} (Score: {chain.get('score')})")
        print(f"Metadata: {chain.get('metadata', 'N/A')}")
        print(f"Narrative Preview: {finding.potential_impact[:200]}...")
        print(f"Steps:")
        for step in chain.get('steps', []):
            f_id = step.get('from_id')
            t_id = step.get('to_id')
            action = step.get('action')
            print(f"  {f_id} -> {t_id} ({action})")

except Exception as e:
    print(f"Error during manual test: {e}")
    import traceback
    traceback.print_exc()
