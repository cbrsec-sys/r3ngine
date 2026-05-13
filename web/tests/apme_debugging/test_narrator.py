import os
import django
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from apme.engine.pathfinder import Pathfinder
from apme.output.llm_narrator import LLMNarrator
from apme.engine.scorer import Scorer
from apme.orchestrator import APMEOrchestrator

scan_id = 60
try:
    print(f"Testing Narrator and Scorer for scan {scan_id}...")
    pf = Pathfinder()
    paths = pf.find_all_paths(scan_id=scan_id)
    
    # Manually gather graph data as Orchestrator does
    from apme.ingestion.assets import ingest_subdomains, ingest_endpoints
    from apme.ingestion.vulnerabilities import ingest_vulnerabilities
    from apme.ingestion.credentials import ingest_credentials
    from startScan.models import ScanHistory
    
    scan = ScanHistory.objects.get(id=scan_id)
    target_id = scan.domain_id
    
    asset_nodes, _ = ingest_subdomains(target_id)
    ep_nodes, _ = ingest_endpoints(target_id)
    vuln_nodes, _ = ingest_vulnerabilities(target_id)
    cred_nodes, _ = ingest_credentials(target_id)
    
    orch = APMEOrchestrator()
    goal_nodes = orch._generate_virtual_goal_nodes(scan_id)
    
    all_nodes = asset_nodes + ep_nodes + vuln_nodes + cred_nodes + goal_nodes
    node_index = {n.id: n for n in all_nodes}
    
    narrator = LLMNarrator()
    scorer = Scorer()
    
    for i, path in enumerate(paths[:3]):  # Just first 3
        # Recalculate score with metadata
        meta = orch._build_path_metadata(path, node_index)
        score = scorer.score(path, meta)
        
        print(f"\n--- Path {i} (ID: {path.id}) ---")
        print(f"Score: {score} | Risk: {path.risk}")
        print(f"Metadata: {meta}")
        
        narrative = narrator.narrate(path, node_index)
        print(f"Narrative:\n{narrative}")
        
    pf.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
