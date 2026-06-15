"""
APME Graph Enricher

Applies the RulesEngine to the graph after initial ingestion.
Creates derived edges (e.g. LEADS_TO, ESCALATES_TO) based on configured attack rules.
This is where the attack reasoning logic lives.
"""

import logging
from typing import List, Tuple

from apme.engine.rules_engine import RulesEngine
from apme.graph.builder import GraphBuilder
from apme.models.edge import Edge
from apme.models.node import Node

logger = logging.getLogger(__name__)

MAX_EDGES_PER_NODE = 12


class GraphEnricher:
    """
    Enriches the APME graph by applying rules to produce new edges.
    Runs AFTER the initial ingestion phase.
    """

    def __init__(self, builder: GraphBuilder):
        self._builder = builder
        self._rules_engine = RulesEngine()

    def enrich(self, nodes: List[Node], scan_id: int) -> List[Edge]:
        """
        Apply rules to all nodes and return newly derived edges.
        Edges are also persisted to the graph.
        Per-node fan-out is capped at MAX_EDGES_PER_NODE to prevent graph explosion.
        """
        derived_edges: List[Edge] = []

        for node in nodes:
            node_edges = self._rules_engine.apply(node, existing_nodes=nodes)
            if len(node_edges) > MAX_EDGES_PER_NODE:
                node_edges = sorted(
                    node_edges, key=lambda e: e.confidence, reverse=True
                )[:MAX_EDGES_PER_NODE]
                logger.debug(
                    "APME Enricher: Node %s fan-out capped at %d edges.",
                    node.id, MAX_EDGES_PER_NODE,
                )
            derived_edges.extend(node_edges)

        if derived_edges:
            logger.info(
                "APME Enricher: Derived %d new edges from rules (fan-out cap: %d).",
                len(derived_edges), MAX_EDGES_PER_NODE,
            )
            self._builder.add_edges(derived_edges, scan_id)

        return derived_edges
