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
# Map Nuclei template tags / vulnerability names to APME subtypes and taxonomy
TAXONOMY_MAP = {
    "sqli": {"subtype": "sqli", "cwe": "CWE-89", "technique": "T1190"},
    "sql injection": {"subtype": "sqli", "cwe": "CWE-89", "technique": "T1190"},
    "xss": {"subtype": "xss", "cwe": "CWE-79", "technique": "T1189"},
    "cross-site scripting": {"subtype": "xss", "cwe": "CWE-79", "technique": "T1189"},
    "rce": {"subtype": "rce", "cwe": "CWE-94", "technique": "T1190"},
    "remote code execution": {"subtype": "rce", "cwe": "CWE-94", "technique": "T1190"},
    "ssrf": {"subtype": "ssrf", "cwe": "CWE-918", "technique": "T1190"},
    "lfi": {"subtype": "lfi", "cwe": "CWE-22", "technique": "T1083"},
    "local file inclusion": {"subtype": "lfi", "cwe": "CWE-22", "technique": "T1083"},
    "ssti": {"subtype": "ssti", "cwe": "CWE-94", "technique": "T1190"},
    "open redirect": {"subtype": "open_redirect", "cwe": "CWE-601", "technique": "T1204.001"},
    "xxe": {"subtype": "xxe", "cwe": "CWE-611", "technique": "T1190"},
    "xml external entity": {"subtype": "xxe", "cwe": "CWE-611", "technique": "T1190"},
    "cors": {"subtype": "cors", "cwe": "CWE-942", "technique": "T1557"},
    "prototype pollution": {"subtype": "prototype_pollution", "cwe": "CWE-1321", "technique": "T1190"},
    "dependency": {"subtype": "dependency", "cwe": "CWE-1395", "technique": "T1190"},
    "sca": {"subtype": "dependency", "cwe": "CWE-1395", "technique": "T1190"},
    "outdated": {"subtype": "dependency", "cwe": "CWE-1395", "technique": "T1190"},
    "misconfig": {"subtype": "misconfig", "cwe": "CWE-16", "technique": "T1562.001"},
    "misconfiguration": {"subtype": "misconfig", "cwe": "CWE-16", "technique": "T1562.001"},
    "bypass": {"subtype": "misconfig", "cwe": "CWE-288", "technique": "T1548"},
    "unauthenticated": {"subtype": "misconfig", "cwe": "CWE-306", "technique": "T1548"},
    "ssh": {"subtype": "rce", "cwe": "CWE-287", "technique": "T1021.004"},
    "login": {"subtype": "misconfig", "cwe": "CWE-287", "technique": "T1078"},
    "admin": {"subtype": "misconfig", "cwe": "CWE-287", "technique": "T1078"},
    "default": {"subtype": "misconfig", "cwe": "CWE-1392", "technique": "T1078"},
}


def _infer_taxonomy(vuln_name: str, vuln_type: str) -> dict:
    name_lower = vuln_name.lower()
    for keyword, info in TAXONOMY_MAP.items():
        if keyword in name_lower:
            return info
    if vuln_type:
        type_lower = vuln_type.lower()
        for keyword, info in TAXONOMY_MAP.items():
            if keyword in type_lower:
                return info
    return {"subtype": "generic", "cwe": "CWE-200", "technique": "T1592"}


def _make_id(prefix: str, value: str) -> str:
    return f"{prefix}::{value}"


def ingest_vulnerabilities(target_id: int) -> Tuple[List[Node], List[Edge]]:
    """
    Ingests Vulnerability records for a given target.
    """
    from startScan.models import Vulnerability

    nodes: List[Node] = []
    edges: List[Edge] = []

    vulns = Vulnerability.objects.filter(
        target_domain_id=target_id,
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

        taxonomy = _infer_taxonomy(vuln.name, vuln.type or "")
        subtype = taxonomy["subtype"]

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
                "cwe": taxonomy["cwe"],
                "technique": taxonomy["technique"],
                "validation_status": vuln.validation_status,
                "validated": validated,
                "http_url": vuln.http_url or "",
                "template_id": vuln.template_id or "",
                "exploit_url": vuln.exploit_url or "",
                "target_id": target_id,
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
        f"(target_id={target_id})"
    )
    return nodes, edges
