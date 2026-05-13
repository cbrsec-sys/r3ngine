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
        print("Goal Nodes:")
        goals = session.run(
            "MATCH (n:APMENode) WHERE n.subtype IN ['db_access', 'data_exfil', 'rce_execution'] RETURN n LIMIT 5"
        )
        for r in goals:
            print(f"  {r['n']}")
    driver.close()
except Exception as e:
    print(f"Error: {e}")
