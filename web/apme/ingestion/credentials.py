"""
APME Ingestion — Credentials

Converts reNgine SecretLeak records into APME Credential nodes,
with AUTHENTICATES edges pointing to the services they can access.
"""

import logging
from typing import List, Tuple

from apme.models.node import Node
from apme.models.edge import Edge

logger = logging.getLogger(__name__)

SECRET_TYPE_TO_SUBTYPE = {
    "api_key": "api_key",
    "api key": "api_key",
    "aws": "api_key",
    "stripe": "api_key",
    "password": "password",
    "token": "token",
    "jwt": "token",
    "oauth": "token",
    "ssh": "ssh_key",
    "certificate": "certificate",
}


def _infer_credential_subtype(secret_type: str) -> str:
    lower = secret_type.lower()
    for keyword, subtype in SECRET_TYPE_TO_SUBTYPE.items():
        if keyword in lower:
            return subtype
    return "token"


def _make_id(prefix: str, value: str) -> str:
    return f"{prefix}::{value}"


def ingest_credentials(target_id: int) -> Tuple[List[Node], List[Edge]]:
    """
    Ingests SecretLeak records for a given target.
    """
    from startScan.models import SecretLeak

    nodes: List[Node] = []
    edges: List[Edge] = []

    leaks = SecretLeak.objects.filter(
        subdomain__target_domain_id=target_id
    ).select_related("subdomain")

    for leak in leaks:
        validated = leak.status == "verified"
        confidence = 0.90 if validated else 0.60

        subtype = _infer_credential_subtype(leak.secret_type)
        cred_node_id = _make_id("credential", str(leak.id))

        cred_node = Node(
            id=cred_node_id,
            type="Credential",
            subtype=subtype,
            confidence=confidence,
            source="reNgine:secret_discovery",
            properties={
                "secret_type": leak.secret_type,
                "source_url": leak.source_url,
                "validated": validated,
                "tool_name": leak.tool_name,
                "target_id": target_id,
            },
        )
        nodes.append(cred_node)

        # Wire credential to source domain via AUTHENTICATES
        if leak.subdomain:
            target_id = _make_id("domain", leak.subdomain.name)
            try:
                edges.append(Edge(
                    from_id=cred_node_id,
                    to_id=target_id,
                    type="AUTHENTICATES",
                    confidence=confidence,
                    properties={"validated": validated},
                ))
            except ValueError as exc:
                logger.warning(f"APME Ingestion: {exc}")

    logger.info(
        f"APME Ingestion [credentials]: {len(nodes)} nodes, {len(edges)} edges "
        f"(target_id={target_id})"
    )
    return nodes, edges
