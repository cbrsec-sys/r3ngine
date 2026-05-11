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
        print(f"Vulnerability subtypes for Scan {scan_id}:")
        subtypes = session.run(
            """
            MATCH (n:APMENode {scan_id: $scan_id, type: 'Vulnerability'})
            RETURN n.subtype, count(n) as count
            """,
            scan_id=scan_id
        )
        for r in subtypes:
            print(f"  - {r['n.subtype']}: {r['count']}")
    driver.close()
except Exception as e:
    print(f"Error: {e}")
