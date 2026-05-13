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
        print(f"Goal Nodes for Scan {scan_id}:")
        goals = session.run(
            "MATCH (n:APMENode {scan_id: $scan_id}) WHERE n.subtype IN ['db_access', 'data_exfil', 'rce_execution'] RETURN n",
            scan_id=scan_id
        )
        count = 0
        for r in goals:
            count += 1
            print(f"  {r['n']}")
        print(f"Total goal nodes for scan {scan_id}: {count}")
    driver.close()
except Exception as e:
    print(f"Error: {e}")
