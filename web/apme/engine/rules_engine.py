"""
APME Rules Engine

Loads attack rules from config/rules.yaml and applies them to graph nodes
to produce derived edges. Rules define how vulnerabilities and access translate
into capabilities.

RULES MUST:
- Be configurable (defined in rules.yaml, not hardcoded)
- NOT create edges unless the relationship is logically sound
- Support chaining: the output of one rule can feed into another
"""

import logging
import os
from typing import Any, Dict, List

import yaml

from apme.models.edge import Edge
from apme.models.node import Node

logger = logging.getLogger(__name__)

_RULES_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "rules.yaml")


class RulesEngine:
    """
    Configuration-driven attack logic engine.
    Applies rules from rules.yaml to produce derived graph edges.
    """

    def __init__(self, rules_file: str = _RULES_FILE):
        self._rules: List[Dict[str, Any]] = []
        self._load_rules(rules_file)

    def _load_rules(self, rules_file: str) -> None:
        try:
            with open(rules_file, "r") as f:
                data = yaml.safe_load(f)
                self._rules = data.get("rules", [])
            logger.info(f"APME RulesEngine: Loaded {len(self._rules)} rules from {rules_file}.")
        except Exception as exc:
            logger.error(f"APME RulesEngine: Failed to load rules from {rules_file}: {exc}")

    def apply(self, node: Node, existing_nodes: List[Node]) -> List[Edge]:
        """
        Apply all matching rules to the given node.
        Returns a list of new edges to be added to the graph.

        FAIL SAFE: Rules that don't match the node are silently skipped.
        Rules that reference non-existent targets are dropped.
        """
        derived_edges: List[Edge] = []
        node_index = {n.id: n for n in existing_nodes}

        for rule in self._rules:
            if not self._matches(node, rule.get("if", {})):
                continue

            then = rule.get("then", {})
            create_edge = then.get("create_edge")
            if not create_edge:
                continue

            edge_type = create_edge.get("type")
            target_subtype = create_edge.get("target_subtype")
            confidence = float(create_edge.get("confidence", 0.7))

            if not edge_type:
                logger.debug(f"APME Rule '{rule.get('name')}': No edge type defined. Skipping.")
                continue

            # Find target nodes matching the specified subtype
            target_nodes = [
                n for n in existing_nodes
                if n.subtype == target_subtype and n.id != node.id
            ]

            if not target_nodes:
                # FAIL SAFE: if we can't find a target, do not create a fantasized edge
                logger.debug(
                    f"APME Rule '{rule.get('name')}': No target nodes with "
                    f"subtype='{target_subtype}' found. Edge skipped."
                )
                continue

            for target_node in target_nodes:
                try:
                    edge = Edge(
                        from_id=node.id,
                        to_id=target_node.id,
                        type=edge_type,
                        confidence=confidence,
                        properties={"rule": rule.get("name", "unknown")},
                    )
                    derived_edges.append(edge)
                    logger.debug(
                        f"APME Rule '{rule.get('name')}': Created {edge_type} "
                        f"{node.id} -> {target_node.id} (confidence={confidence})"
                    )
                except ValueError as exc:
                    logger.warning(f"APME Rule '{rule.get('name')}': Invalid edge type: {exc}")

        return derived_edges

    @staticmethod
    def _matches(node: Node, condition: Dict[str, Any]) -> bool:
        """
        Check if a node satisfies the rule's 'if' conditions.
        All conditions must match (AND logic).
        """
        if not condition:
            return False

        node_type = condition.get("node.type")
        node_subtype = condition.get("node.subtype")
        node_role = condition.get("node.role")

        if node_type and node.type != node_type:
            return False
        if node_subtype and node.subtype != node_subtype:
            return False
        if node_role and node.properties.get("role") != node_role:
            return False

        return True
