"""
APME Output Serializer

Serializes AttackPath objects into the canonical JSON output format.
Phase 1: adds MITRE attribution fields to steps and nodes.
         adds speculative_paths envelope.
"""

import json
from typing import Any, Dict, List

from apme.models.path import AttackPath
from apme.utils.mitre import lookup as mitre_lookup


def serialize_path(path: AttackPath, node_index: Dict[str, Any] = None) -> Dict[str, Any]:
    """Serialize a single AttackPath to the canonical output format."""
    steps = []
    all_techniques: List[str] = []
    all_tactics: List[str] = []

    for step in path.steps:
        mitre_info = mitre_lookup(step.mitre_technique) if step.mitre_technique else {}

        step_dict: Dict[str, Any] = {
            "from":                 step.from_id,
            "to":                   step.to_id,
            "action":               step.action,
            "edge_type":            step.edge_type,
            "confidence":           round(step.confidence, 4),
            "validated":            step.validated,
            "status":               "validated" if step.validated else "inferred",
            "mitre_technique":      step.mitre_technique,
            "mitre_technique_name": mitre_info.get("technique_name", ""),
            "mitre_tactic":         step.mitre_tactic,
            "mitre_tactic_display": mitre_info.get("tactic_display", ""),
            "mitre_tactic_color":   mitre_info.get("tactic_color", ""),
        }

        if node_index:
            from_node = node_index.get(step.from_id)
            to_node = node_index.get(step.to_id)
            if from_node:
                step_dict["from_node"] = _serialize_node(from_node)
            if to_node:
                step_dict["to_node"] = _serialize_node(to_node)

        steps.append(step_dict)

        if step.mitre_technique:
            all_techniques.append(step.mitre_technique)
        if step.mitre_tactic:
            all_tactics.append(step.mitre_tactic)

    validated_count = sum(1 for s in path.steps if s.validated)
    inferred_count = len(path.steps) - validated_count

    return {
        "path_id":          path.id,
        "risk":             path.risk,
        "score":            round(path.score, 4),
        "start":            path.start,
        "end":              path.end,
        "entry_type":       path.entry_type,
        "step_count":       len(path.steps),
        "validated_steps":  validated_count,
        "inferred_steps":   inferred_count,
        "mitre_techniques": sorted(set(all_techniques)),
        "mitre_tactics":    sorted(set(all_tactics)),
        "steps":            steps,
    }


def _serialize_node(node: Any) -> Dict[str, Any]:
    return {
        "id":         node.id,
        "type":       node.type,
        "subtype":    node.subtype,
        "name":       node.properties.get("name", ""),
        "severity":   node.properties.get("severity"),
        "cvss_score": node.properties.get("cvss_score"),
        "vuln_id":    node.properties.get("vuln_id"),
        "cwe":        node.properties.get("cwe", ""),
        "technique":  node.properties.get("technique", ""),
    }


def serialize_paths(
    paths: List[AttackPath],
    node_index: Dict[str, Any] = None,
    top_n: int = 5,
) -> Dict[str, Any]:
    """Serialize top N paths into the canonical output envelope."""
    top = paths[:top_n]
    serialized = [serialize_path(p, node_index) for p in top]
    confirmed = [p for p in serialized if p["risk"] != "speculative"]
    speculative = [p for p in serialized if p["risk"] == "speculative"]
    return {
        "total_paths":       len(paths),
        "returned_paths":    len(top),
        "paths":             confirmed,
        "speculative_paths": speculative,
    }


def to_json(paths: List[AttackPath], top_n: int = 5, indent: int = 2) -> str:
    return json.dumps(serialize_paths(paths, top_n=top_n), indent=indent)
