"""
APME Graph Builder

Constructs the attack graph using Neo4j (always available in reNgine).
Ingests normalized Node and Edge objects from the ingestion layer and persists
them to the graph database, wiring up relationships between assets,
vulnerabilities, credentials, and capabilities.

CRITICAL RULES:
- DO NOT create an edge if the relationship is unclear.
- ALL nodes must have a valid type from graph/schema.py.
- Confidence scores MUST be propagated to edges.
"""

import logging
from typing import List

from neo4j import GraphDatabase
from django.conf import settings

from apme.models.node import Node
from apme.models.edge import Edge

logger = logging.getLogger(__name__)


class GraphBuilder:
    """
    Manages the APME attack graph in Neo4j.
    Uses MERGE semantics to be idempotent — safe to run multiple times per scan.
    """

    def __init__(self):
        self._driver = None
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            logger.info("APME GraphBuilder connected to Neo4j.")
        except Exception as exc:
            logger.error(f"APME GraphBuilder failed to connect to Neo4j: {exc}")
            raise

    def close(self):
        if self._driver:
            self._driver.close()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def add_nodes(self, nodes: List[Node], scan_id: int) -> None:
        """Persist a batch of nodes to Neo4j."""
        with self._driver.session() as session:
            for node in nodes:
                try:
                    session.execute_write(self._merge_node, node, scan_id)
                except Exception as exc:
                    logger.warning(f"APME: Failed to merge node {node.id}: {exc}")

    def add_edges(self, edges: List[Edge], scan_id: int) -> None:
        """
        Persist a batch of directed edges.
        FAIL SAFE: if either endpoint node does not exist, the edge is skipped.
        """
        with self._driver.session() as session:
            for edge in edges:
                try:
                    created = session.execute_write(self._merge_edge, edge, scan_id)
                    if not created:
                        logger.debug(
                            f"APME: Skipped edge {edge.from_id} -[{edge.type}]-> {edge.to_id} "
                            "(one or both endpoint nodes not found)."
                        )
                except Exception as exc:
                    logger.warning(
                        f"APME: Failed to merge edge {edge.from_id} -> {edge.to_id}: {exc}"
                    )

    def clear_scan(self, scan_id: int) -> None:
        """Remove all APME-labelled nodes/edges for a given scan."""
        with self._driver.session() as session:
            session.run(
                "MATCH (n:APMENode {scan_id: $scan_id}) DETACH DELETE n",
                scan_id=scan_id,
            )

    # -------------------------------------------------------------------------
    # Neo4j transaction helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _merge_node(tx, node: Node, scan_id: int) -> None:
        tx.run(
            """
            MERGE (n:APMENode {apme_id: $id, scan_id: $scan_id})
            SET n.type       = $type,
                n.subtype    = $subtype,
                n.confidence = $confidence,
                n.source     = $source,
                n.properties = $properties
            """,
            id=node.id,
            scan_id=scan_id,
            type=node.type,
            subtype=node.subtype,
            confidence=node.confidence,
            source=node.source,
            properties=str(node.properties),
        )

    @staticmethod
    def _merge_edge(tx, edge: Edge, scan_id: int) -> bool:
        """
        Create a directed edge between two APMENodes, automatically generating
        skeleton endpoints if one or both nodes are missing from the ingestion layer.
        """
        def infer_node_type(apme_id: str) -> tuple:
            if apme_id.startswith("domain::"):
                return "Asset", "domain"
            elif apme_id.startswith("ip::"):
                return "Asset", "ip"
            elif apme_id.startswith("service::"):
                return "Asset", "service"
            elif apme_id.startswith("endpoint::"):
                return "Asset", "endpoint"
            elif apme_id.startswith("vuln::"):
                return "Vulnerability", "generic"
            elif apme_id.startswith("goal::capability::"):
                return "Capability", apme_id.split("::")[-1]
            elif apme_id.startswith("goal::privilege::"):
                return "Privilege", apme_id.split("::")[-1]
            return "Asset", "generic"

        from_type, from_subtype = infer_node_type(edge.from_id)
        to_type, to_subtype = infer_node_type(edge.to_id)

        result = tx.run(
            """
            MERGE (a:APMENode {apme_id: $from_id, scan_id: $scan_id})
            ON CREATE SET a.type = $from_type, 
                          a.subtype = $from_subtype, 
                          a.confidence = 0.5, 
                          a.source = "APME:skeleton",
                          a.properties = '{}'
            
            MERGE (b:APMENode {apme_id: $to_id, scan_id: $scan_id})
            ON CREATE SET b.type = $to_type, 
                          b.subtype = $to_subtype, 
                          b.confidence = 0.5, 
                          b.source = "APME:skeleton",
                          b.properties = '{}'
            
            MERGE (a)-[r:APME_EDGE {edge_type: $type}]->(b)
            SET r.confidence  = $confidence,
                r.properties  = $properties
            RETURN r
            """,
            from_id=edge.from_id,
            to_id=edge.to_id,
            scan_id=scan_id,
            type=edge.type,
            confidence=edge.confidence,
            properties=str(edge.properties),
            from_type=from_type,
            from_subtype=from_subtype,
            to_type=to_type,
            to_subtype=to_subtype,
        )
        return result.single() is not None
