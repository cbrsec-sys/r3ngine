import os
import django
import logging

# Configure logging to see APME logs
logging.basicConfig(level=logging.INFO)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

from apme.engine.pathfinder import Pathfinder
from startScan.models import ScanHistory

scan_id = 60
try:
    print(f"Testing Pathfinder for scan {scan_id}...")
    pf = Pathfinder()
    
    # Debug: Check raw BFS paths
    from apme.engine.pathfinder import HIGH_VALUE_TARGET_SUBTYPES
    entries = pf._get_internet_entry_points(scan_id)
    print(f"Found {len(entries)} entry points")
    for entry_id in entries[:5]:
        raw = pf._bfs_query(scan_id, entry_id, list(HIGH_VALUE_TARGET_SUBTYPES))
        print(f"  Entry {entry_id}: Raw paths found = {len(raw)}")
        if raw:
            for r in raw:
                print(f"    Path with {len(r['nodes'])} nodes and {len(r['rels'])} rels")

    paths = pf.find_all_paths(scan_id=scan_id)
    print(f"Total paths found: {len(paths)}")
    for i, path in enumerate(paths):
        print(f"Path {i}: ID={path.id}, Steps={len(path.steps)}, Risk={path.risk}")
        for j, step in enumerate(path.steps):
            print(f"  Step {j}: {step.from_id} -> {step.to_id} ({step.action})")
    pf.close()
except Exception as e:
    print(f"Error: {e}")
