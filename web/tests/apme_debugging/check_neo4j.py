import os
import django
from neo4j import GraphDatabase
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
django.setup()

scan_id = 60
try:
    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    with driver.session() as session:
        node_count = session.run(
            "MATCH (n:APMENode {scan_id: $scan_id}) RETURN count(n) as count",
            scan_id=scan_id
        ).single()["count"]
        
        edge_count = session.run(
            "MATCH (:APMENode {scan_id: $scan_id})-[r:APME_EDGE]->(:APMENode {scan_id: $scan_id}) RETURN count(r) as count",
            scan_id=scan_id
        ).single()["count"]
        
        entry_points = session.run(
            "MATCH (n:APMENode {scan_id: $scan_id}) WHERE n.subtype IN ['domain', 'ip', 'service', 'endpoint'] RETURN n.apme_id, n.subtype",
            scan_id=scan_id
        )
        eps = [(r["n.apme_id"], r["n.subtype"]) for r in entry_points]

        print(f"Scan {scan_id}: Nodes={node_count}, Edges={edge_count}")
        print(f"Entry Points: {len(eps)}")
        for ep in eps[:5]:
            print(f"  - {ep[0]} ({ep[1]})")
            
        targets = session.run(
            "MATCH (n:APMENode {scan_id: $scan_id}) WHERE n.subtype IN ['domain_admin', 'root', 'admin', 'db_access', 'data_exfil', 'rce_execution', 'cloud_access', 'authenticated_access', 'pivot'] RETURN n.apme_id, n.subtype",
            scan_id=scan_id
        )
        ts = [(r["n.apme_id"], r["n.subtype"]) for r in targets]
        print(f"Targets: {len(ts)}")
        for t in ts[:5]:
            print(f"  - {t[0]} ({t[1]})")

    driver.close()
except Exception as e:
    print(f"Error: {e}")
