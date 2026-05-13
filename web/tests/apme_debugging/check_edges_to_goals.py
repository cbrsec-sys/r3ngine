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
        print(f"Edges leading to Goal Nodes for Scan {scan_id}:")
        edges = session.run(
            """
            MATCH (a:APMENode {scan_id: $scan_id})-[r:APME_EDGE]->(b:APMENode {scan_id: $scan_id})
            WHERE b.subtype IN ['db_access', 'data_exfil', 'rce_execution']
            RETURN a.apme_id, b.apme_id, r.edge_type
            """,
            scan_id=scan_id
        )
        count = 0
        for r in edges:
            count += 1
            print(f"  {r['a.apme_id']} -[{r['r.edge_type']}]-> {r['b.apme_id']}")
        print(f"Total edges to goals for scan {scan_id}: {count}")
    driver.close()
except Exception as e:
    print(f"Error: {e}")
