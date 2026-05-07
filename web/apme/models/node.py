from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Node:
    """
    Represents a node in the attack graph.

    Types: Asset | Vulnerability | Credential | Identity | Privilege | Network
    """
    id: str
    type: str
    subtype: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = "reNgine"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "subtype": self.subtype,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
        }
