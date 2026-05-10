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
        """
        derived_edges: List[Edge] = []

        for node in nodes:
            new_edges = self._rules_engine.apply(node, existing_nodes=nodes)
            derived_edges.extend(new_edges)

        if derived_edges:
            logger.info(f"APME Enricher: Derived {len(derived_edges)} new edges from rules.")
            self._builder.add_edges(derived_edges, scan_id)

        return derived_edges
