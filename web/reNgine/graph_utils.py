from neo4j import GraphDatabase
import logging
from django.conf import settings
from startScan.models import Subdomain, EndPoint
from targetApp.models import Domain

logger = logging.getLogger(__name__)

class Neo4jManager:
    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def sync_scan_results(self, scan_history_id):
        """Syncs scan results from PostgreSQL to Neo4j."""
        if not self.driver:
            return

        from startScan.models import ScanHistory
        try:
            scan = ScanHistory.objects.get(id=scan_history_id)
            project_id = scan.domain.project.id
            project_name = scan.domain.project.name
            target_name = scan.domain.name
            scan_date = scan.start_scan_date.isoformat() if scan.start_scan_date else None
        except Exception as e:
            logger.error(f"Failed to fetch scan details for sync: {e}")
            return

        with self.driver.session() as session:
            # Create Project and Scan nodes
            session.execute_write(self._initialize_scan_context, project_id, project_name, scan_history_id, target_name, scan_date)

            # Sync Subdomains
            subdomains = Subdomain.objects.filter(scan_history_id=scan_history_id)
            for sub in subdomains:
                domain_name = sub.target_domain.name
                subdomain_name = sub.name
                ip_address = sub.ip_addresses if hasattr(sub, 'ip_addresses') else None
                
                session.execute_write(self._merge_assets, domain_name, subdomain_name, ip_address, scan_history_id)

            # Sync Endpoints and Parameters
            endpoints = EndPoint.objects.filter(scan_history_id=scan_history_id)
            for endpoint in endpoints:
                session.execute_write(self._merge_endpoints, endpoint.subdomain.name, endpoint.http_url, scan_history_id)
                
                # Sync Parameters
                parameters = endpoint.parameters.all()
                for param in parameters:
                    session.execute_write(self._merge_parameters, endpoint.http_url, param.name, param.type, scan_history_id)

    @staticmethod
    def _initialize_scan_context(tx, project_id, project_name, scan_id, target_name, scan_date):
        # Create Project
        tx.run("MERGE (p:Project {id: $id}) SET p.name = $name", id=project_id, name=project_name)
        # Create Target (Domain)
        tx.run("MERGE (d:Domain {name: $name})", name=target_name)
        # Create Scan
        tx.run("MERGE (s:Scan {id: $id}) SET s.date = $date", id=scan_id, date=scan_date)
        # Link Scan to Project and Target
        tx.run("""
            MATCH (p:Project {id: $project_id}), (s:Scan {id: $scan_id}), (d:Domain {name: $target_name})
            MERGE (s)-[:BELONGS_TO]->(p)
            MERGE (s)-[:TARGETS]->(d)
        """, project_id=project_id, scan_id=scan_id, target_name=target_name)

    @staticmethod
    def _merge_assets(tx, domain_name, subdomain_name, ip_address, scan_id):
        # Create Domain
        tx.run("MERGE (d:Domain {name: $name})", name=domain_name)
        
        # Create Subdomain and link to Domain
        tx.run("""
            MERGE (s:Subdomain {name: $sub_name})
            WITH s
            MATCH (d:Domain {name: $dom_name}), (sc:Scan {id: $scan_id})
            MERGE (d)-[:HAS_SUBDOMAIN]->(s)
            MERGE (sc)-[:FOUND]->(s)
            MERGE (sc)-[:FOUND]->(d)
        """, sub_name=subdomain_name, dom_name=domain_name, scan_id=scan_id)
        
        # If IP address exists, link it
        if ip_address:
            ips = [ip.strip() for ip in str(ip_address).split(',')]
            for ip in ips:
                tx.run("""
                    MERGE (i:IPAddress {address: $ip})
                    WITH i
                    MATCH (s:Subdomain {name: $sub_name}), (sc:Scan {id: $scan_id})
                    MERGE (s)-[:RESOLVES_TO]->(i)
                    MERGE (sc)-[:FOUND]->(i)
                """, ip=ip, sub_name=subdomain_name, scan_id=scan_id)

    @staticmethod
    def _merge_endpoints(tx, subdomain_name, http_url, scan_id):
        tx.run("""
            MERGE (e:Endpoint {url: $url})
            WITH e
            MATCH (s:Subdomain {name: $sub_name}), (sc:Scan {id: $scan_id})
            MERGE (s)-[:HAS_ENDPOINT]->(e)
            MERGE (sc)-[:FOUND]->(e)
        """, url=http_url, sub_name=subdomain_name, scan_id=scan_id)

    @staticmethod
    def _merge_parameters(tx, endpoint_url, param_name, param_type, scan_id):
        tx.run("""
            MERGE (p:Parameter {name: $name, type: $type})
            WITH p
            MATCH (e:Endpoint {url: $url}), (sc:Scan {id: $scan_id})
            MERGE (e)-[:HAS_PARAMETER]->(p)
            MERGE (sc)-[:FOUND]->(p)
        """, name=param_name, type=param_type, url=endpoint_url, scan_id=scan_id)

    def sync_all_scans(self):
        """Syncs all scan results from PostgreSQL to Neo4j."""
        from startScan.models import ScanHistory
        scans = ScanHistory.objects.all()
        total_scans = scans.count()
        logger.info(f"Starting global graph synchronization for {total_scans} scans.")
        
        for index, scan in enumerate(scans, 1):
            logger.info(f"[{index}/{total_scans}] Syncing scan: {scan.domain.name} (ID: {scan.id})")
            try:
                self.sync_scan_results(scan.id)
            except Exception as e:
                logger.error(f"Failed to sync scan {scan.id}: {e}")
        
        logger.info("Global graph synchronization completed successfully.")

    def get_cytoscape_json(self, scan_history_id):
        """Returns graph data in Cytoscape format for a specific scan."""
        query = """
            MATCH (sc:Scan {id: $scan_id})-[:FOUND]->(n)
            OPTIONAL MATCH (n)-[r]->(m)
            WHERE (sc)-[:FOUND]->(m)
            RETURN n, r, m
        """
        return self._fetch_graph_data(query, {"scan_id": int(scan_history_id)})

    def get_target_graph_data(self, target_name):
        """Returns graph data for all scans of a specific target (Domain)."""
        query = """
            MATCH (target:Domain {name: $target_name})<-[:TARGETS]-(sc:Scan)-[:FOUND]->(n)
            OPTIONAL MATCH (n)-[r]->(m)
            WHERE EXISTS {
               MATCH (sc2:Scan)-[:TARGETS]->(target)
               WHERE (sc2)-[:FOUND]->(m)
            }
            RETURN n, r, m, sc.id as scan_id
        """
        return self._fetch_graph_data(query, {"target_name": target_name})

    def _fetch_graph_data(self, query, params):
        if not self.driver:
            return {"nodes": [], "edges": []}

        nodes = []
        edges = []
        color_map = {
            'Domain': '#3b82f6',
            'Subdomain': '#10b981',
            'IPAddress': '#f59e0b',
            'Vulnerability': '#ef4444',
            'Endpoint': '#8b5cf6',
            'Parameter': '#ec4899'
        }

        with self.driver.session() as session:
            result = session.run(query, **params)
            
            seen_nodes = set()
            for record in result:
                scan_ids = record.get('scan_ids') or []
                if record.get('scan_id'):
                    scan_ids.append(record.get('scan_id'))

                for node_key in ['n', 'm']:
                    node = record[node_key]
                    if not node: continue
                    node_id = str(node.id)
                    if node_id not in seen_nodes:
                        label = node.get('name') or node.get('address') or node_id
                        node_type = list(node.labels)[0] if node.labels else 'Unknown'
                        nodes.append({
                            "data": {
                                "id": node_id,
                                "label": label,
                                "type": node_type,
                                "color": color_map.get(node_type, '#94a3b8'),
                                "scan_ids": scan_ids
                            }
                        })
                        seen_nodes.add(node_id)
                
                if record['r']:
                    edges.append({
                        "data": {
                            "source": str(record['n'].id),
                            "target": str(record['m'].id),
                            "label": record['r'].type,
                            "scan_ids": scan_ids
                        }
                    })
        
        return {"nodes": nodes, "edges": edges}
    def reset_database(self):
        """Deletes all nodes and relationships from the Neo4j database."""
        if not self.driver:
            return
        query = "MATCH (n) DETACH DELETE n"
        with self.driver.session() as session:
            session.run(query)
        print("[*] Neo4j database has been reset (all nodes deleted).")

    def sync_all_scans(self):
        """Utility to re-sync all historical scans from Django DB to Neo4j."""
        from startScan.models import ScanHistory
        scans = ScanHistory.objects.all().order_by('id')
        print(f"[*] Starting re-sync of {scans.count()} scans...")
        for scan in scans:
            try:
                print(f"[*] Syncing scan {scan.id} for {scan.domain.name}...")
                self.sync_scan_results(scan.id)
            except Exception as e:
                print(f"[!] Error syncing scan {scan.id}: {str(e)}")
        print("[*] Re-sync complete.")
