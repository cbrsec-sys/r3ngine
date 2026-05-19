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
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
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
            project_id = scan.domain.project.id if scan.domain and scan.domain.project else 0
            project_name = scan.domain.project.name if scan.domain and scan.domain.project else "Default Project"
            target_name = scan.domain.name if scan.domain else "Unknown Target"
            scan_date = (
                scan.start_scan_date.isoformat() if scan.start_scan_date else None
            )
        except Exception as e:
            logger.error(f"Failed to fetch scan details for sync: {e}")
            return

        with self.driver.session() as session:
            # Create Project and Scan nodes
            session.execute_write(
                self._initialize_scan_context,
                project_id,
                project_name,
                scan_history_id,
                target_name,
                scan_date,
            )

            # Sync Subdomains
            subdomains = Subdomain.objects.filter(scan_history_id=scan_history_id)
            for sub in subdomains:
                domain_name = sub.target_domain.name if sub.target_domain else target_name
                subdomain_name = sub.name or "unknown"
                ip_address = sub.ip_addresses if hasattr(sub, "ip_addresses") else None

                session.execute_write(
                    self._merge_assets,
                    domain_name,
                    subdomain_name,
                    ip_address,
                    scan_history_id,
                )

            # Sync Endpoints and Parameters
            endpoints = EndPoint.objects.filter(scan_history_id=scan_history_id)
            for endpoint in endpoints:
                subdomain_name = endpoint.subdomain.name if endpoint.subdomain else target_name
                session.execute_write(
                    self._merge_endpoints,
                    subdomain_name,
                    endpoint.http_url or "unknown",
                    scan_history_id,
                )

                # Sync Parameters
                parameters = endpoint.parameters.all()
                for param in parameters:
                    param_name = param.name or "unknown"
                    session.execute_write(
                        self._merge_parameters,
                        endpoint.http_url or "unknown",
                        param_name,
                        param.type,
                        scan_history_id,
                    )

            # Sync Technologies
            subdomains = Subdomain.objects.filter(scan_history_id=scan_history_id)
            for sub in subdomains:
                for tech in sub.technologies.all():
                    if tech and tech.name:
                        session.execute_write(
                            self._merge_technologies, sub.name or "unknown", tech.name, scan_history_id
                        )

            # Sync Vulnerabilities
            from startScan.models import Vulnerability

            vulns = Vulnerability.objects.filter(scan_history_id=scan_history_id)
            for vuln in vulns:
                asset_name = (
                    vuln.subdomain.name
                    if vuln.subdomain
                    else (vuln.endpoint.http_url if vuln.endpoint else None)
                )
                asset_type = (
                    "Subdomain"
                    if vuln.subdomain
                    else ("Endpoint" if vuln.endpoint else None)
                )
                if asset_name and asset_type:
                    session.execute_write(
                        self._merge_vulnerabilities,
                        asset_name,
                        asset_type,
                        vuln.name or "Unknown Vulnerability",
                        vuln.severity,
                        vuln.correlation_score,
                        scan_history_id,
                        vuln.id,
                    )
                    # Sync CVEs linked to this vulnerability
                    for cve in vuln.cve_ids.all():
                        if cve and cve.name:
                            session.execute_write(
                                self._merge_cves, vuln.name or "Unknown Vulnerability", cve.name, scan_history_id
                            )

    @staticmethod
    def _initialize_scan_context(
        tx, project_id, project_name, scan_id, target_name, scan_date
    ):
        # Create Project
        tx.run(
            "MERGE (p:Project {id: $id}) SET p.name = $name",
            id=project_id,
            name=project_name,
        )
        # Create Target (Domain)
        tx.run("MERGE (d:Domain {name: $name})", name=target_name)
        # Create Scan
        tx.run(
            "MERGE (s:Scan {id: $id}) SET s.date = $date", id=scan_id, date=scan_date
        )
        # Link Scan to Project and Target
        tx.run(
            """
            MATCH (p:Project {id: $project_id}), (s:Scan {id: $scan_id}), (d:Domain {name: $target_name})
            MERGE (s)-[:BELONGS_TO]->(p)
            MERGE (s)-[:TARGETS]->(d)
        """,
            project_id=project_id,
            scan_id=scan_id,
            target_name=target_name,
        )

    @staticmethod
    def _merge_assets(tx, domain_name, subdomain_name, ip_address, scan_id):
        # Create Domain
        tx.run("MERGE (d:Domain {name: $name})", name=domain_name)

        # Create Subdomain and link to Domain
        tx.run(
            """
            MERGE (s:Subdomain {name: $sub_name})
            WITH s
            MATCH (d:Domain {name: $dom_name}), (sc:Scan {id: $scan_id})
            MERGE (d)-[:HAS_SUBDOMAIN]->(s)
            MERGE (sc)-[:FOUND]->(s)
            MERGE (sc)-[:FOUND]->(d)
        """,
            sub_name=subdomain_name,
            dom_name=domain_name,
            scan_id=scan_id,
        )

        # If IP address exists, link it
        if ip_address:
            ips = [ip.strip() for ip in str(ip_address).split(",")]
            for ip in ips:
                tx.run(
                    """
                    MERGE (i:IPAddress {address: $ip})
                    WITH i
                    MATCH (s:Subdomain {name: $sub_name}), (sc:Scan {id: $scan_id})
                    MERGE (s)-[:RESOLVES_TO]->(i)
                    MERGE (sc)-[:FOUND]->(i)
                """,
                    ip=ip,
                    sub_name=subdomain_name,
                    scan_id=scan_id,
                )

    @staticmethod
    def _merge_endpoints(tx, subdomain_name, http_url, scan_id):
        tx.run(
            """
            MERGE (e:Endpoint {url: $url})
            WITH e
            MATCH (s:Subdomain {name: $sub_name}), (sc:Scan {id: $scan_id})
            MERGE (s)-[:HAS_ENDPOINT]->(e)
            MERGE (sc)-[:FOUND]->(e)
        """,
            url=http_url,
            sub_name=subdomain_name,
            scan_id=scan_id,
        )

    @staticmethod
    def _merge_parameters(tx, endpoint_url, param_name, param_type, scan_id):
        tx.run(
            """
            MERGE (p:Parameter {name: $name, type: $type})
            WITH p
            MATCH (e:Endpoint {url: $url}), (sc:Scan {id: $scan_id})
            MERGE (e)-[:HAS_PARAMETER]->(p)
            MERGE (sc)-[:FOUND]->(p)
        """,
            name=param_name,
            type=param_type,
            url=endpoint_url,
            scan_id=scan_id,
        )

    @staticmethod
    def _merge_technologies(tx, subdomain_name, tech_name, scan_id):
        tx.run(
            """
            MERGE (t:Technology {name: $tech_name})
            WITH t
            MATCH (s:Subdomain {name: $sub_name}), (sc:Scan {id: $scan_id})
            MERGE (s)-[:USES_TECH]->(t)
            MERGE (sc)-[:FOUND]->(t)
        """,
            tech_name=tech_name,
            sub_name=subdomain_name,
            scan_id=scan_id,
        )

    @staticmethod
    def _merge_vulnerabilities(
        tx,
        asset_name,
        asset_type,
        vuln_name,
        severity,
        correlation_score,
        scan_id,
        vuln_id,
    ):
        tx.run(
            f"""
            MERGE (v:Vulnerability {{id: $vuln_id}})
            SET v.name = $vuln_name, v.severity = $severity, v.correlation_score = $score
            WITH v
            MATCH (a:{asset_type} {{name: $asset_name}}), (sc:Scan {{id: $scan_id}})
            MERGE (a)-[:HAS_VULNERABILITY]->(v)
            MERGE (sc)-[:FOUND]->(v)
        """,
            vuln_id=vuln_id,
            vuln_name=vuln_name,
            severity=severity,
            score=correlation_score,
            asset_name=asset_name,
            scan_id=scan_id,
        )

    @staticmethod
    def _merge_cves(tx, vuln_name, cve_name, scan_id):
        tx.run(
            """
            MERGE (c:CVE {name: $cve_name})
            WITH c
            MATCH (v:Vulnerability {name: $vuln_name}), (sc:Scan {id: $scan_id})
            MERGE (v)-[:LINKED_TO_CVE]->(c)
            MERGE (sc)-[:FOUND]->(c)
        """,
            cve_name=cve_name,
            vuln_name=vuln_name,
            scan_id=scan_id,
        )

    def ingest_stress_telemetry(self, endpoint_url, scan_id, telemetry_data):
        """
        telemetry_data = {
            'tool': 'k6',
            'concurrent_users': 100,
            'avg_latency': 120.5,
            'p95_latency': 200.0,
            'error_rate': 0.05,
            'total_requests': 5000,
            'throughput_rps': 150.5
        }
        """
        if not self.driver:
            return

        with self.driver.session() as session:
            session.execute_write(
                self._merge_stress_telemetry, endpoint_url, scan_id, telemetry_data
            )

    @staticmethod
    def _merge_stress_telemetry(tx, endpoint_url, scan_id, data):
        tx.run(
            """
            MERGE (st:StressTest {scan_id: $scan_id, endpoint_url: $url, tool: $tool})
            SET st.concurrent_users = $concurrent_users,
                st.avg_latency = $avg_latency,
                st.p95_latency = $p95_latency,
                st.error_rate = $error_rate,
                st.total_requests = $total_requests,
                st.throughput_rps = $throughput_rps
            WITH st
            MATCH (e:Endpoint {url: $url}), (sc:Scan {id: $scan_id})
            MERGE (e)-[:STRESS_TESTED_BY]->(st)
            MERGE (sc)-[:FOUND]->(st)
        """,
            url=endpoint_url,
            scan_id=scan_id,
            tool=data.get("tool", "unknown"),
            concurrent_users=data.get("concurrent_users", 0),
            avg_latency=data.get("avg_latency", 0.0),
            p95_latency=data.get("p95_latency", 0.0),
            error_rate=data.get("error_rate", 0.0),
            total_requests=data.get("total_requests", 0),
            throughput_rps=data.get("throughput_rps", 0.0),
        )

    def get_stress_telemetry(self, scan_id):
        """Fetches stress test telemetry for a given scan."""
        if not self.driver:
            return []
        query = """
            MATCH (st:StressTest {scan_id: $scan_id})
            RETURN st
        """
        data = []
        try:
            with self.driver.session() as session:
                result = session.run(query, scan_id=scan_id)
                for record in result:
                    node = record["st"]
                    data.append(
                        {
                            "endpoint_url": node.get("endpoint_url"),
                            "tool": node.get("tool"),
                            "concurrent_users": node.get("concurrent_users"),
                            "avg_latency": node.get("avg_latency"),
                            "p95_latency": node.get("p95_latency"),
                            "error_rate": node.get("error_rate"),
                            "total_requests": node.get("total_requests"),
                            "throughput_rps": node.get("throughput_rps"),
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to fetch stress telemetry: {e}")
        return data

    def sync_all_scans(self):
        """Syncs all scan results from PostgreSQL to Neo4j."""
        from startScan.models import ScanHistory

        scans = ScanHistory.objects.all()
        total_scans = scans.count()
        logger.info(f"Starting global graph synchronization for {total_scans} scans.")

        for index, scan in enumerate(scans, 1):
            logger.info(
                f"[{index}/{total_scans}] Syncing scan: {scan.domain.name} (ID: {scan.id})"
            )
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

    def get_impact_path(self, vuln_id):
        """Returns a subgraph showing the attack path from the domain to a specific vulnerability."""
        query = """
            MATCH (v:Vulnerability {id: $vuln_id})
            MATCH p = (d:Domain)-[*..4]->(v)
            WITH p, v
            UNWIND nodes(p) as n
            UNWIND relationships(p) as r
            RETURN DISTINCT n, r, endNode(r) as m
        """
        return self._fetch_graph_data(query, {"vuln_id": int(vuln_id)})

    def _fetch_graph_data(self, query, params):
        if not self.driver:
            return {"nodes": [], "edges": []}

        nodes_dict = {}
        edges = []
        color_map = {
            "Domain": "#3b82f6",
            "Subdomain": "#10b981",
            "IPAddress": "#f59e0b",
            "Vulnerability": "#ef4444",
            "Endpoint": "#8b5cf6",
            "Parameter": "#ec4899",
            "Technology": "#facc15",
            "CVE": "#7c3aed",
            "StressTest": "#14b8a6",
        }

        with self.driver.session() as session:
            result = session.run(query, **params)

            for record in result:
                scan_ids = record.get("scan_ids") or []
                if record.get("scan_id"):
                    scan_ids.append(record.get("scan_id"))

                for node_key in ["n", "m"]:
                    node = record[node_key]
                    if not node:
                        continue
                    node_id = str(node.id)
                    if node_id not in nodes_dict:
                        label = node.get("name") or node.get("address") or node.get("url") or node_id
                        node_type = list(node.labels)[0] if node.labels else "Unknown"
                        nodes_dict[node_id] = {
                            "data": {
                                "id": node_id,
                                "label": label,
                                "type": node_type,
                                "color": color_map.get(node_type, "#94a3b8"),
                                "scan_ids": scan_ids,
                                "degree_centrality": 0,
                                "criticalVulnCount": 0,
                                "highVulnCount": 0,
                                "severity": node.get("severity", -1),
                            }
                        }

                if record["r"]:
                    src = str(record["n"].id)
                    tgt = str(record["m"].id)
                    r_type = record["r"].type
                    edges.append(
                        {
                            "data": {
                                "source": src,
                                "target": tgt,
                                "label": r_type,
                                "scan_ids": scan_ids,
                            }
                        }
                    )
                    
                    # Compute degree centrality
                    if src in nodes_dict:
                        nodes_dict[src]["data"]["degree_centrality"] += 1
                    if tgt in nodes_dict:
                        nodes_dict[tgt]["data"]["degree_centrality"] += 1
                        
                    # Compute vulnerability counts
                    if r_type == "HAS_VULNERABILITY":
                        vuln_node = nodes_dict.get(tgt)
                        if vuln_node and vuln_node["data"]["type"] == "Vulnerability":
                            severity = vuln_node["data"].get("severity", -1)
                            if severity == 4:
                                nodes_dict[src]["data"]["criticalVulnCount"] += 1
                            elif severity == 3:
                                nodes_dict[src]["data"]["highVulnCount"] += 1

        return {"nodes": list(nodes_dict.values()), "edges": edges}

    def get_blast_radius(self, node_id):
        """Calculates the blast radius of a compromised node using APOC."""
        query = """
            MATCH (startNode) WHERE startNode.id = $node_id OR toString(id(startNode)) = $node_id
            CALL apoc.path.subgraphAll(startNode, {maxLevel: 3}) YIELD relationships
            UNWIND relationships as r
            RETURN startNode(r) as n, r, endNode(r) as m
        """
        return self._fetch_graph_data(query, {"node_id": str(node_id)})

    def get_node_details(self, node_id):
        """Fetches detailed properties for a single node."""
        if not self.driver:
            return {}

        query = """
            MATCH (n) WHERE toString(id(n)) = $node_id OR n.id = $node_id
            RETURN n, labels(n) as labels
        """
        with self.driver.session() as session:
            result = session.run(query, node_id=str(node_id))
            record = result.single()
            if record:
                node = record["n"]
                labels = record["labels"]
                return {
                    "id": str(node.id),
                    "labels": labels,
                    "properties": dict(node)
                }
        return {}

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

        scans = ScanHistory.objects.all().order_by("id")
        print(f"[*] Starting re-sync of {scans.count()} scans...")
        for scan in scans:
            try:
                print(f"[*] Syncing scan {scan.id} for {scan.domain.name}...")
                self.sync_scan_results(scan.id)
            except Exception as e:
                print(f"[!] Error syncing scan {scan.id}: {str(e)}")
        print("[*] Re-sync complete.")
