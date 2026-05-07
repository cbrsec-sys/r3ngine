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

    def add_nodes(self, nodes: List[Node]) -> None:
        """Persist a batch of nodes to Neo4j."""
        with self._driver.session() as session:
            for node in nodes:
                try:
                    session.execute_write(self._merge_node, node)
                except Exception as exc:
                    logger.warning(f"APME: Failed to merge node {node.id}: {exc}")

    def add_edges(self, edges: List[Edge]) -> None:
        """
        Persist a batch of directed edges.
        FAIL SAFE: if either endpoint node does not exist, the edge is skipped.
        """
        with self._driver.session() as session:
            for edge in edges:
                try:
                    created = session.execute_write(self._merge_edge, edge)
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
    def _merge_node(tx, node: Node) -> None:
        tx.run(
            """
            MERGE (n:APMENode {apme_id: $id})
            SET n.type       = $type,
                n.subtype    = $subtype,
                n.confidence = $confidence,
                n.source     = $source,
                n.properties = $properties
            """,
            id=node.id,
            type=node.type,
            subtype=node.subtype,
            confidence=node.confidence,
            source=node.source,
            properties=str(node.properties),
        )

    @staticmethod
    def _merge_edge(tx, edge: Edge) -> bool:
        """
        Create a directed edge between two existing APMENodes.
        Returns True if successfully created, False if endpoints not found.
        """
        result = tx.run(
            """
            MATCH (a:APMENode {apme_id: $from_id})
            MATCH (b:APMENode {apme_id: $to_id})
            MERGE (a)-[r:APME_EDGE {edge_type: $type}]->(b)
            SET r.confidence  = $confidence,
                r.properties  = $properties
            RETURN r
            """,
            from_id=edge.from_id,
            to_id=edge.to_id,
            type=edge.type,
            confidence=edge.confidence,
            properties=str(edge.properties),
        )
        return result.single() is not None
