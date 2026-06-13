"""
APME Rules Engine

Loads attack rules from a directory of YAML files (or single file for backward
compatibility) and applies them to graph nodes to produce derived edges.

Phase 1 enhancements:
- Directory loading: loads all *.yaml files from config/rules/ alphabetically
- Numeric comparisons in node.property conditions (>=, <=, >, <)
- node.confidence numeric comparison
- node.property as a list (AND-semantics — all conditions must match)
- confidence_modifier in then.create_edge (scales edge confidence)
- Constraint flags (requires_victim, requires_php, requires_java,
  requires_python, requires_wordpress, endpoint_requires_auth)
  propagated from rule YAML to edge.properties
"""

import logging
import operator
import os
from typing import Any, Dict, List

import yaml

from apme.models.edge import Edge
from apme.models.node import Node

logger = logging.getLogger(__name__)

_RULES_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "rules")

_OPS = {
    ">=": operator.ge,
    "<=": operator.le,
    ">":  operator.gt,
    "<":  operator.lt,
}

_CONSTRAINT_FLAGS = (
    "requires_victim",
    "requires_php",
    "requires_java",
    "requires_python",
    "requires_wordpress",
    "endpoint_requires_auth",
)


class RulesEngine:
    """Configuration-driven attack logic engine."""

    def __init__(self, rules_file: str = _RULES_FILE):
        self._rules: List[Dict[str, Any]] = []
        self._load_rules(rules_file)

    def _load_rules(self, rules_file: str) -> None:
        """Load rules from a directory of YAML files or a single YAML file.

        Directory mode: loads all *.yaml files sorted alphabetically (category
        prefix a_, b_, … ensures consistent load order) and merges their
        `rules` lists. Single-file mode is kept for backward-compatibility and
        tests that pass an explicit path.
        """
        all_rules: List[Dict[str, Any]] = []
        try:
            if os.path.isdir(rules_file):
                yaml_files = sorted(
                    f for f in os.listdir(rules_file)
                    if f.endswith(".yaml") or f.endswith(".yml")
                )
                for fname in yaml_files:
                    fpath = os.path.join(rules_file, fname)
                    try:
                        with open(fpath, "r") as f:
                            data = yaml.safe_load(f)
                            file_rules = (data.get("rules", []) if data else [])
                            all_rules.extend(file_rules)
                            logger.info(
                                "APME RulesEngine: Loaded %d rules from %s.",
                                len(file_rules), fname,
                            )
                    except Exception as exc:
                        logger.error("APME RulesEngine: Failed to load %s: %s", fpath, exc)
            else:
                with open(rules_file, "r") as f:
                    data = yaml.safe_load(f)
                    all_rules = data.get("rules", []) if data else []
                logger.info(
                    "APME RulesEngine: Loaded %d rules from %s.", len(all_rules), rules_file
                )

            self._rules = all_rules
            logger.info("APME RulesEngine: Total rules loaded: %d.", len(self._rules))
        except Exception as exc:
            logger.error("APME RulesEngine: Failed to load rules from %s: %s", rules_file, exc)

    def apply(self, node: Node, existing_nodes: List[Node]) -> List[Edge]:
        """
        Apply all matching rules to the given node.
        Returns a list of new edges to be added to the graph.
        """
        derived_edges: List[Edge] = []

        for rule in self._rules:
            if not self._matches(node, rule.get("if", {})):
                continue

            then = rule.get("then", {})
            create_edge = then.get("create_edge")
            if not create_edge:
                continue

            edge_type = create_edge.get("type")
            target_subtype = create_edge.get("target_subtype")
            base_confidence = float(create_edge.get("confidence", 0.7))
            confidence_modifier = float(create_edge.get("confidence_modifier", 1.0))
            mitre_id = rule.get("mitre_id", "unknown")

            if not edge_type:
                logger.debug("APME Rule '%s': No edge type defined. Skipping.", rule.get("name"))
                continue

            # Apply confidence modifier; never boost unvalidated findings
            if confidence_modifier > 1.0 and not node.properties.get("validated", False):
                confidence = base_confidence
            else:
                confidence = min(base_confidence * confidence_modifier, 1.0)

            target_nodes = [
                n for n in existing_nodes
                if n.subtype == target_subtype and n.id != node.id
            ]

            if not target_nodes:
                continue

            # Build constraint properties from rule definition
            constraint_props = {
                flag: bool(create_edge.get(flag, False))
                for flag in _CONSTRAINT_FLAGS
            }

            for target_node in target_nodes:
                try:
                    edge = Edge(
                        from_id=node.id,
                        to_id=target_node.id,
                        type=edge_type,
                        confidence=confidence,
                        properties={
                            "rule": rule.get("name", "unknown"),
                            "mitre_id": mitre_id,
                            **constraint_props,
                        },
                    )
                    derived_edges.append(edge)
                except ValueError as exc:
                    logger.warning("APME Rule '%s': %s", rule.get("name"), exc)

        return derived_edges

    @staticmethod
    def _matches(node: Node, condition: Any) -> bool:
        """
        Check if a node satisfies the rule's 'if' conditions.

        Supports:
        - node.type, node.subtype (exact match)
        - node.property: "key:value" (exact) or "key:>=N" (numeric comparison)
        - node.property: ["key:>=N", "key2:value"] (AND — all must match)
        - node.confidence: ">=0.5" (numeric comparison on node.confidence)
        """
        if not condition:
            return False

        if node.type != condition.get("node.type", node.type):
            return False
        if node.subtype != condition.get("node.subtype", node.subtype):
            return False

        # node.confidence comparison
        if "node.confidence" in condition:
            if not _numeric_check(node.confidence, condition["node.confidence"]):
                return False

        # node.property (single string or list — AND semantics)
        prop_cond = condition.get("node.property")
        if prop_cond is not None:
            conditions = prop_cond if isinstance(prop_cond, list) else [prop_cond]
            for cond_str in conditions:
                if not _property_check(node.properties, cond_str):
                    return False

        return True


def _numeric_check(value: Any, condition_str: str) -> bool:
    """Check a numeric value against an operator condition string like '>=0.5'."""
    condition_str = str(condition_str).strip()
    for op_str, op_fn in _OPS.items():
        if condition_str.startswith(op_str):
            try:
                threshold = float(condition_str[len(op_str):])
                return op_fn(float(value), threshold)
            except (ValueError, TypeError):
                return False
    # Equality fallback
    try:
        return float(value) == float(condition_str)
    except (ValueError, TypeError):
        return str(value) == condition_str


def _property_check(properties: dict, cond_str: str) -> bool:
    """Check node.properties against a 'key:value_or_op' string."""
    if ":" not in cond_str:
        return False
    key, val = cond_str.split(":", 1)
    node_val = properties.get(key)
    if node_val is None:
        return False
    # Try numeric operator first
    for op_str, op_fn in _OPS.items():
        if val.startswith(op_str):
            try:
                threshold = float(val[len(op_str):])
                return op_fn(float(node_val), threshold)
            except (ValueError, TypeError):
                return False
    # Exact string match
    return str(node_val) == val
