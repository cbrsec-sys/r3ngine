"""
APME Pathfinder

Implements graph traversal algorithms against Neo4j to discover
realistic attack paths from entry points to high-value targets.

Algorithms:
- BFS  → shortest paths (fewest hops)
- DFS  → deep chaining (discovers long paths)
- Dijkstra → weight-optimal paths (highest exploitability)

CRITICAL: All discovered paths are validated through the ConstraintEngine
before being returned. Constraint-failing paths are silently dropped.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase
from django.conf import settings

from apme.engine.constraints import ConstraintEngine, PathContext
from apme.models.path import AttackPath, PathStep

logger = logging.getLogger(__name__)

# Entry point node subtypes considered internet-facing
INTERNET_ENTRY_SUBTYPES = {"domain", "ip", "service", "endpoint"}

# Target node subtypes considered high-value
HIGH_VALUE_TARGET_SUBTYPES = {
    "domain_admin",
    "root",
    "admin",
    "db_access",
    "data_exfil",
    "rce_execution",
    "cloud_access",
    "authenticated_access",
    "pivot",
}


class Pathfinder:
    """
    Discovers attack paths in the Neo4j APME graph using BFS, DFS, and Dijkstra.
    """

    MAX_DEPTH = 8       # Maximum path depth to prevent runaway traversal
    MAX_PATHS = 20      # Maximum raw paths to retrieve before constraint filtering

    def __init__(self):
        self._driver = None
        self._constraint_engine = ConstraintEngine()
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        except Exception as exc:
            logger.error(f"APME Pathfinder: Neo4j connection failed: {exc}")
            raise

    def close(self):
        if self._driver:
            self._driver.close()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def find_paths_bfs(
        self,
        scan_id: int,
        start_node_id: str,
        target_subtypes: Optional[List[str]] = None,
        top_n: int = 5,
    ) -> List[AttackPath]:
        """
        BFS: finds shortest paths (minimum hops) from start to any high-value target.
        """
        targets = target_subtypes or list(HIGH_VALUE_TARGET_SUBTYPES)
        raw_paths = self._bfs_query(scan_id, start_node_id, targets)
        return self._validate_and_build(raw_paths, "bfs", top_n)

    def find_paths_dfs(
        self,
        scan_id: int,
        start_node_id: str,
        target_subtypes: Optional[List[str]] = None,
        top_n: int = 5,
    ) -> List[AttackPath]:
        """
        DFS: discovers deeper, more complex attack chains.
        """
        targets = target_subtypes or list(HIGH_VALUE_TARGET_SUBTYPES)
        raw_paths = self._dfs_query(scan_id, start_node_id, targets)
        return self._validate_and_build(raw_paths, "dfs", top_n)

    def find_paths_dijkstra(
        self,
        scan_id: int,
        start_node_id: str,
        target_subtypes: Optional[List[str]] = None,
        top_n: int = 5,
    ) -> List[AttackPath]:
        """
        Dijkstra: finds weight-optimal paths using (1 - confidence) as edge cost.
        Higher confidence edges are preferred.
        """
        targets = target_subtypes or list(HIGH_VALUE_TARGET_SUBTYPES)
        raw_paths = self._dijkstra_query(scan_id, start_node_id, targets)
        return self._validate_and_build(raw_paths, "dijkstra", top_n)

    def find_all_paths(
        self,
        scan_id: int,
        start_node_ids: Optional[List[str]] = None,
        target_subtypes: Optional[List[str]] = None,
        top_n: int = 5,
    ) -> List[AttackPath]:
        """
        Runs all three algorithms across all entry points and deduplicates results.
        Returns the top N paths by step count (shortest first).
        """
        entries = start_node_ids or self._get_internet_entry_points(scan_id)
        all_paths: List[AttackPath] = []

        for entry_id in entries:
            all_paths.extend(self.find_paths_bfs(scan_id, entry_id, target_subtypes, top_n))
            all_paths.extend(self.find_paths_dfs(scan_id, entry_id, target_subtypes, top_n))

        # Deduplicate by step fingerprint

        # Deduplicate by step fingerprint
        seen = set()
        unique = []
        for p in all_paths:
            key = "->".join(s.from_id + s.to_id for s in p.steps)
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return sorted(unique, key=lambda p: len(p.steps))[:top_n]

    # -------------------------------------------------------------------------
    # Neo4j Queries
    # -------------------------------------------------------------------------

    def _bfs_query(self, scan_id: int, start_id: str, target_subtypes: List[str]) -> List[List[Dict]]:
        query = """
            MATCH path = shortestPath(
                (start:APMENode {apme_id: $start_id, scan_id: $scan_id})-[:APME_EDGE*1..%d]->(target:APMENode)
            )
            WHERE target.subtype IN $target_subtypes AND target.scan_id = $scan_id
            RETURN [n in nodes(path) | {
                id: n.apme_id, type: n.type, subtype: n.subtype,
                confidence: n.confidence, properties: n.properties
            }] AS nodes,
            [r in relationships(path) | {
                type: r.edge_type, confidence: r.confidence
            }] AS rels
            LIMIT $limit
        """ % self.MAX_DEPTH

        return self._run_path_query(query, scan_id, start_id, target_subtypes)

    def _dfs_query(self, scan_id: int, start_id: str, target_subtypes: List[str]) -> List[List[Dict]]:
        query = """
            MATCH path = (start:APMENode {apme_id: $start_id, scan_id: $scan_id})-[:APME_EDGE*1..%d]->(target:APMENode)
            WHERE target.subtype IN $target_subtypes AND target.scan_id = $scan_id
            RETURN [n in nodes(path) | {
                id: n.apme_id, type: n.type, subtype: n.subtype,
                confidence: n.confidence, properties: n.properties
            }] AS nodes,
            [r in relationships(path) | {
                type: r.edge_type, confidence: r.confidence
            }] AS rels
            LIMIT $limit
        """ % self.MAX_DEPTH

        return self._run_path_query(query, scan_id, start_id, target_subtypes)

    def _dijkstra_query(self, scan_id: int, start_id: str, target_subtypes: List[str]) -> List[List[Dict]]:
        """
        Dijkstra using APOC's weighted shortest path.
        Edge cost = 1 - confidence (higher confidence = lower cost = preferred).
        Falls back to BFS if APOC is unavailable.
        """
        query = """
            MATCH (start:APMENode {apme_id: $start_id, scan_id: $scan_id}), (target:APMENode {scan_id: $scan_id})
            WHERE target.subtype IN $target_subtypes
            CALL apoc.algo.dijkstra(start, target, 'APME_EDGE', 'cost') YIELD path, weight
            RETURN [n in nodes(path) | {
                id: n.apme_id, type: n.type, subtype: n.subtype,
                confidence: n.confidence, properties: n.properties
            }] AS nodes,
            [r in relationships(path) | {
                type: r.edge_type, confidence: r.confidence
            }] AS rels
            LIMIT $limit
        """
        try:
            return self._run_path_query(query, scan_id, start_id, target_subtypes)
        except Exception:
            logger.warning("APME Pathfinder: APOC Dijkstra unavailable, falling back to BFS.")
            return self._bfs_query(scan_id, start_id, target_subtypes)

    def _run_path_query(
        self, query: str, scan_id: int, start_id: str, target_subtypes: List[str]
    ) -> List[List[Dict]]:
        results = []
        if not self._driver:
            return results
        try:
            with self._driver.session() as session:
                records = session.run(
                    query,
                    scan_id=scan_id,
                    start_id=start_id,
                    target_subtypes=target_subtypes,
                    limit=self.MAX_PATHS,
                )
                for record in records:
                    results.append({
                        "nodes": record["nodes"],
                        "rels": record["rels"],
                    })
        except Exception as exc:
            logger.error(f"APME Pathfinder: Query failed: {exc}")
        return results

    def _get_internet_entry_points(self, scan_id: int) -> List[str]:
        """Returns node IDs for all internet-exposed entry-point assets."""
        if not self._driver:
            return []
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (n:APMENode)
                WHERE n.subtype IN $subtypes AND n.scan_id = $scan_id
                RETURN n.apme_id AS id
                """,
                subtypes=list(INTERNET_ENTRY_SUBTYPES),
                scan_id=scan_id,
            )
            return [r["id"] for r in result]

    # -------------------------------------------------------------------------
    # Path Construction & Validation
    # -------------------------------------------------------------------------

    def _validate_and_build(
        self,
        raw_paths: List[Dict],
        algorithm: str,
        top_n: int,
    ) -> List[AttackPath]:
        """
        Convert raw Neo4j path records into validated AttackPath objects.
        Paths failing constraint checks are dropped.
        """
        validated: List[AttackPath] = []

        for raw in raw_paths:
            nodes = raw.get("nodes", [])
            rels = raw.get("rels", [])

            if len(nodes) < 2:
                continue

            steps: List[PathStep] = []
            context = PathContext()
            valid = True

            for i, rel in enumerate(rels):
                from_node = nodes[i]
                to_node = nodes[i + 1]
                edge_type = rel.get("type", "")
                confidence = float(rel.get("confidence", 0.5))

                step_dict = self._edge_to_step_dict(edge_type, from_node, to_node, confidence)

                if not self._constraint_engine.validate_step(step_dict, context):
                    valid = False
                    break

                self._constraint_engine.update_context(step_dict, context)

                steps.append(PathStep(
                    from_id=from_node.get("id", ""),
                    to_id=to_node.get("id", ""),
                    action=self._edge_to_action(edge_type, from_node, to_node),
                    confidence=confidence,
                    validated=step_dict.get("validated", False),
                    edge_type=edge_type,
                ))

            if valid and steps:
                path = AttackPath(
                    id=f"APT-{uuid.uuid4().hex[:6].upper()}",
                    start=nodes[0].get("id", ""),
                    end=nodes[-1].get("id", ""),
                    steps=steps,
                    entry_type="internet",
                )
                validated.append(path)

        return validated[:top_n]

    @staticmethod
    def _edge_to_step_dict(
        edge_type: str,
        from_node: Dict,
        to_node: Dict,
        confidence: float,
    ) -> Dict[str, Any]:
        """
        Map an edge type to a step dict with constraint flags.
        These flags feed into the ConstraintEngine.
        """
        step: Dict[str, Any] = {
            "action": edge_type,
            "confidence": confidence,
            "validated": False,
            "requires_auth": False,
            "requires_internal": False,
            "requires_privilege": "none",
            "grants_auth": False,
            "grants_internal": False,
            "grants_privilege": None,
        }

        if edge_type == "AUTHENTICATES":
            step["grants_auth"] = True
        elif edge_type == "CONNECTED_TO":
            step["grants_internal"] = True
        elif edge_type == "ESCALATES_TO":
            step["grants_privilege"] = to_node.get("subtype", "user")
        elif edge_type == "LEADS_TO":
            # Leading to internal capabilities requires internal access
            if to_node.get("subtype") in {"pivot", "data_exfil"}:
                step["requires_internal"] = True

        return step

    @staticmethod
    def _edge_to_action(edge_type: str, from_node: Dict, to_node: Dict) -> str:
        templates = {
            "RESOLVES_TO": "Resolve {src} to IP {dst}",
            "HOSTS": "{src} hosts service {dst}",
            "EXPOSES": "Service {src} exposes vulnerability {dst}",
            "LEADS_TO": "Exploit {src} to gain {dst}",
            "AUTHENTICATES": "Use credential {src} to authenticate to {dst}",
            "ESCALATES_TO": "Escalate from {src} to {dst}",
            "TRUSTS": "{src} trusts {dst} — lateral movement possible",
            "CONNECTED_TO": "Pivot via {src} to reach {dst}",
        }
        template = templates.get(edge_type, "{src} -> {dst}")
        return template.format(
            src=from_node.get("subtype", from_node.get("id", "?")),
            dst=to_node.get("subtype", to_node.get("id", "?")),
        )
