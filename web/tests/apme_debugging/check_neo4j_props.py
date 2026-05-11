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
        # Check a few nodes
        print("Sample Nodes:")
        nodes = session.run(
            "MATCH (n:APMENode {scan_id: $scan_id}) RETURN n LIMIT 3",
            scan_id=scan_id
        )
        for r in nodes:
            print(f"  {r['n']}")

        # Check a few edges
        print("\nSample Edges:")
        edges = session.run(
            "MATCH (a:APMENode {scan_id: $scan_id})-[r:APME_EDGE]->(b:APMENode {scan_id: $scan_id}) RETURN a.apme_id, type(r), r, b.apme_id LIMIT 3",
            scan_id=scan_id
        )
        for r in edges:
            print(f"  {r['a.apme_id']} -[{r['type(r)']}]-> {r['b.apme_id']}")
            print(f"    Properties: {dict(r['r'])}")

    driver.close()
except Exception as e:
    print(f"Error: {e}")
