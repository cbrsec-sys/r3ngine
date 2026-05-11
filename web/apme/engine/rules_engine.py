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
            mitre_id = rule.get("mitre_id")

            if not edge_type:
                logger.debug(f"APME Rule '{rule.get('name')}': No edge type defined. Skipping.")
                continue

            # Find target nodes matching the specified subtype
            target_nodes = [
                n for n in existing_nodes
                if n.subtype == target_subtype and n.id != node.id
            ]

            if not target_nodes:
                continue

            for target_node in target_nodes:
                try:
                    edge = Edge(
                        from_id=node.id,
                        to_id=target_node.id,
                        type=edge_type,
                        confidence=confidence,
                        properties={
                            "rule": rule.get("name", "unknown"),
                            "mitre_id": mitre_id or "unknown"
                        },
                    )
                    derived_edges.append(edge)
                except ValueError as exc:
                    logger.warning(f"APME Rule '{rule.get('name')}': Invalid edge type: {exc}")

        return derived_edges

    @staticmethod
    def _matches(node: Node, condition: Dict[str, Any]) -> bool:
        """
        Check if a node satisfies the rule's 'if' conditions.
        Supports node.type, node.subtype, and property matching.
        """
        if not condition:
            return False

        # Node basic attributes
        if "node.type" in condition and node.type != condition["node.type"]:
            return False
        if "node.subtype" in condition and node.subtype != condition["node.subtype"]:
            return False

        # Property matching (e.g. node.property: "sensitivity:high")
        if "node.property" in condition:
            prop_cond = condition["node.property"]
            if isinstance(prop_cond, str) and ":" in prop_cond:
                key, val = prop_cond.split(":", 1)
                if node.properties.get(key) != val:
                    return False

        return True
