"""
APME Ingestion — Vulnerabilities

Converts reNgine Vulnerability models into APME graph nodes,
wiring them to their parent asset via EXPOSES edges.

ERL Integration:
- If a vulnerability has validation_status='verified', the node
  gets confidence=1.0 and validated=True in properties.
- If unverified, confidence is inferred from the correlation_score.
"""

import logging
from typing import List, Tuple

from apme.models.node import Node
from apme.models.edge import Edge

logger = logging.getLogger(__name__)

# Map reNgine severity integers to APME subtype labels
SEVERITY_TO_SUBTYPE = {
    -1: "generic",
    0: "generic",
    1: "generic",
    2: "generic",
    3: "generic",
    4: "generic",
}

# Map Nuclei template tags / vulnerability names to APME subtypes
NAME_TO_SUBTYPE = {
    "sqli": "sqli",
    "sql injection": "sqli",
    "xss": "xss",
    "cross-site scripting": "xss",
    "rce": "rce",
    "remote code execution": "rce",
    "ssrf": "ssrf",
    "lfi": "lfi",
    "local file inclusion": "lfi",
    "ssti": "ssti",
    "open redirect": "open_redirect",
    "xxe": "xxe",
    "xml external entity": "xxe",
    "cors": "cors",
    "prototype pollution": "prototype_pollution",
    "dependency": "dependency",
    "sca": "dependency",
    "outdated": "dependency",
    "misconfig": "misconfig",
    "misconfiguration": "misconfig",
}


def _infer_subtype(vuln_name: str, vuln_type: str) -> str:
    name_lower = vuln_name.lower()
    for keyword, subtype in NAME_TO_SUBTYPE.items():
        if keyword in name_lower:
            return subtype
    if vuln_type:
        for keyword, subtype in NAME_TO_SUBTYPE.items():
            if keyword in vuln_type.lower():
                return subtype
    return "generic"


def _make_id(prefix: str, value: str) -> str:
    return f"{prefix}::{value}"


def ingest_vulnerabilities(scan_history_id: int) -> Tuple[List[Node], List[Edge]]:
    """
    Ingests Vulnerability records, creating APME nodes and EXPOSES edges
    to connect them to their parent asset nodes.
    """
    from startScan.models import Vulnerability

    nodes: List[Node] = []
    edges: List[Edge] = []

    vulns = Vulnerability.objects.filter(
        scan_history_id=scan_history_id,
        open_status=True,
        is_suppressed=False,
    ).select_related("subdomain", "endpoint")

    for vuln in vulns:
        validated = vuln.validation_status == "verified"

        # Confidence: use ERL result if available, else infer from correlation score
        if validated:
            confidence = 1.0
        elif vuln.correlation_score and vuln.correlation_score > 0:
            confidence = min(vuln.correlation_score / 100.0, 0.95)
        else:
            # Infer from severity: critical/high get moderate confidence
            confidence = {4: 0.75, 3: 0.60, 2: 0.45, 1: 0.30, 0: 0.20, -1: 0.10}.get(
                vuln.severity, 0.20
            )

        subtype = _infer_subtype(vuln.name, vuln.type or "")

        vuln_node_id = _make_id("vuln", str(vuln.id))
        vuln_node = Node(
            id=vuln_node_id,
            type="Vulnerability",
            subtype=subtype,
            confidence=confidence,
            source="reNgine:vulnerability_scan",
            properties={
                "name": vuln.name,
                "severity": vuln.severity,
                "cvss_score": vuln.cvss_score or 0.0,
                "validation_status": vuln.validation_status,
                "validated": validated,
                "http_url": vuln.http_url or "",
                "template_id": vuln.template_id or "",
                "exploit_url": vuln.exploit_url or "",
                "scan_history_id": scan_history_id,
                "vuln_id": vuln.id,
            },
        )
        nodes.append(vuln_node)

        # Determine parent asset node ID
        if vuln.subdomain:
            parent_id = _make_id("domain", vuln.subdomain.name)
            edge_confidence = confidence
        elif vuln.endpoint:
            parent_id = _make_id("endpoint", vuln.endpoint.http_url)
            edge_confidence = confidence
        else:
            logger.debug(f"APME Ingestion: Vuln {vuln.id} has no associated asset. Skipping EXPOSES edge.")
            continue

        try:
            edges.append(Edge(
                from_id=parent_id,
                to_id=vuln_node_id,
                type="EXPOSES",
                confidence=edge_confidence,
                properties={"validated": validated},
            ))
        except ValueError as exc:
            logger.warning(f"APME Ingestion: {exc}")

    logger.info(
        f"APME Ingestion [vulnerabilities]: {len(nodes)} nodes, {len(edges)} edges "
        f"(scan_history_id={scan_history_id})"
    )
    return nodes, edges
