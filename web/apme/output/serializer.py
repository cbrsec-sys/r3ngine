"""
APME Output Serializer

Serializes AttackPath objects into the canonical JSON output format.
Clearly distinguishes validated vs inferred steps per spec.
"""

import json
from typing import Any, Dict, List

from apme.models.path import AttackPath


def serialize_path(path: AttackPath, node_index: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Serialize a single AttackPath to the canonical output format.

    Output includes:
    - path_id, risk, score
    - steps with action, target, validated flag, confidence
    - validated vs inferred step counts
    """
    steps = []
    for step in path.steps:
        step_dict = {
            "from": step.from_id,
            "to": step.to_id,
            "action": step.action,
            "edge_type": step.edge_type,
            "confidence": round(step.confidence, 4),
            # Clearly distinguish validated (ERL-confirmed) vs inferred steps
            "validated": step.validated,
            "status": "validated" if step.validated else "inferred",
        }
        if node_index:
            from_node = node_index.get(step.from_id)
            to_node = node_index.get(step.to_id)
            if from_node:
                step_dict["from_node"] = {
                    "id": from_node.id,
                    "type": from_node.type,
                    "subtype": from_node.subtype,
                    "name": from_node.properties.get("name", ""),
                    "severity": from_node.properties.get("severity"),
                    "cvss_score": from_node.properties.get("cvss_score"),
                    "vuln_id": from_node.properties.get("vuln_id"),
                }
            if to_node:
                step_dict["to_node"] = {
                    "id": to_node.id,
                    "type": to_node.type,
                    "subtype": to_node.subtype,
                    "name": to_node.properties.get("name", ""),
                    "severity": to_node.properties.get("severity"),
                    "cvss_score": to_node.properties.get("cvss_score"),
                    "vuln_id": to_node.properties.get("vuln_id"),
                }
        steps.append(step_dict)

    validated_count = sum(1 for s in path.steps if s.validated)
    inferred_count = len(path.steps) - validated_count

    return {
        "path_id": path.id,
        "risk": path.risk,
        "score": round(path.score, 4),
        "start": path.start,
        "end": path.end,
        "entry_type": path.entry_type,
        "step_count": len(path.steps),
        "validated_steps": validated_count,
        "inferred_steps": inferred_count,
        "steps": steps,
    }


def serialize_paths(paths: List[AttackPath], node_index: Dict[str, Any] = None, top_n: int = 5) -> Dict[str, Any]:
    """
    Serialize the top N attack paths into the canonical output envelope.
    """
    top = paths[:top_n]
    return {
        "total_paths": len(paths),
        "returned_paths": len(top),
        "paths": [serialize_path(p, node_index) for p in top],
    }


def to_json(paths: List[AttackPath], top_n: int = 5, indent: int = 2) -> str:
    return json.dumps(serialize_paths(paths, top_n), indent=indent)
