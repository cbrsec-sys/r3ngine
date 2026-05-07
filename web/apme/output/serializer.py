"""
APME Output Serializer

Serializes AttackPath objects into the canonical JSON output format.
Clearly distinguishes validated vs inferred steps per spec.
"""

import json
from typing import Any, Dict, List

from apme.models.path import AttackPath


def serialize_path(path: AttackPath) -> Dict[str, Any]:
    """
    Serialize a single AttackPath to the canonical output format.

    Output includes:
    - path_id, risk, score
    - steps with action, target, validated flag, confidence
    - validated vs inferred step counts
    """
    steps = []
    for step in path.steps:
        steps.append({
            "from": step.from_id,
            "to": step.to_id,
            "action": step.action,
            "edge_type": step.edge_type,
            "confidence": round(step.confidence, 4),
            # Clearly distinguish validated (ERL-confirmed) vs inferred steps
            "validated": step.validated,
            "status": "validated" if step.validated else "inferred",
        })

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


def serialize_paths(paths: List[AttackPath], top_n: int = 5) -> Dict[str, Any]:
    """
    Serialize the top N attack paths into the canonical output envelope.
    """
    top = paths[:top_n]
    return {
        "total_paths": len(paths),
        "returned_paths": len(top),
        "paths": [serialize_path(p) for p in top],
    }


def to_json(paths: List[AttackPath], top_n: int = 5, indent: int = 2) -> str:
    return json.dumps(serialize_paths(paths, top_n), indent=indent)
