"""
APME Ingestion — Vulnerabilities

Converts reNgine Vulnerability models into APME graph nodes,
wiring them to their parent asset via EXPOSES edges.

ERL Integration:
- validated=True → confidence=1.0
- Unverified → confidence inferred from correlation_score or severity
"""

import logging
from typing import List, Tuple

from apme.models.node import Node
from apme.models.edge import Edge

logger = logging.getLogger(__name__)

# Maps keyword fragments in vulnerability name/type → APME taxonomy
TAXONOMY_MAP = {
    # Injection
    "sqli":               {"subtype": "sqli",              "cwe": "CWE-89",   "technique": "T1190"},
    "sql injection":      {"subtype": "sqli",              "cwe": "CWE-89",   "technique": "T1190"},
    "sql-injection":      {"subtype": "sqli",              "cwe": "CWE-89",   "technique": "T1190"},
    "command injection":  {"subtype": "command_injection", "cwe": "CWE-78",   "technique": "T1059"},
    "os command":         {"subtype": "command_injection", "cwe": "CWE-78",   "technique": "T1059"},
    "log4j":              {"subtype": "log_injection",     "cwe": "CWE-917",  "technique": "T1190"},
    "log4shell":          {"subtype": "log_injection",     "cwe": "CWE-917",  "technique": "T1190"},
    "jndi":               {"subtype": "log_injection",     "cwe": "CWE-917",  "technique": "T1190"},
    "rce":                {"subtype": "rce",               "cwe": "CWE-94",   "technique": "T1190"},
    "remote code exec":   {"subtype": "rce",               "cwe": "CWE-94",   "technique": "T1190"},
    "code injection":     {"subtype": "code_injection",    "cwe": "CWE-94",   "technique": "T1059"},
    "nosql":              {"subtype": "nosql_injection",   "cwe": "CWE-943",  "technique": "T1190"},
    "mongodb":            {"subtype": "nosql_injection",   "cwe": "CWE-943",  "technique": "T1190"},
    "xpath":              {"subtype": "xpath_injection",   "cwe": "CWE-643",  "technique": "T1083"},
    "ldap injection":     {"subtype": "ldap_injection",    "cwe": "CWE-90",   "technique": "T1548"},
    # Template
    "ssti":               {"subtype": "ssti",              "cwe": "CWE-94",   "technique": "T1190"},
    "template inject":    {"subtype": "ssti",              "cwe": "CWE-94",   "technique": "T1190"},
    # Server-side
    "ssrf":               {"subtype": "ssrf",              "cwe": "CWE-918",  "technique": "T1190"},
    "xxe":                {"subtype": "xxe",               "cwe": "CWE-611",  "technique": "T1190"},
    "xml external":       {"subtype": "xxe",               "cwe": "CWE-611",  "technique": "T1190"},
    # File operations
    "lfi":                {"subtype": "lfi",               "cwe": "CWE-22",   "technique": "T1083"},
    "local file inc":     {"subtype": "lfi",               "cwe": "CWE-22",   "technique": "T1083"},
    "path traversal":     {"subtype": "path_traversal",    "cwe": "CWE-22",   "technique": "T1083"},
    "directory trav":     {"subtype": "path_traversal",    "cwe": "CWE-22",   "technique": "T1083"},
    "file upload":        {"subtype": "file_upload",       "cwe": "CWE-434",  "technique": "T1190"},
    "unrestricted upload": {"subtype": "file_upload",      "cwe": "CWE-434",  "technique": "T1190"},
    # Deserialization
    "deserializ":         {"subtype": "deserialization",   "cwe": "CWE-502",  "technique": "T1059"},
    "insecure deserial":  {"subtype": "deserialization",   "cwe": "CWE-502",  "technique": "T1059"},
    # Client-side
    "xss":                {"subtype": "xss",               "cwe": "CWE-79",   "technique": "T1189"},
    "cross-site scripting": {"subtype": "xss",             "cwe": "CWE-79",   "technique": "T1189"},
    "open redirect":      {"subtype": "open_redirect",     "cwe": "CWE-601",  "technique": "T1204.001"},
    "clickjacking":       {"subtype": "clickjacking",      "cwe": "CWE-1021", "technique": "T1185"},
    "ui redress":         {"subtype": "clickjacking",      "cwe": "CWE-1021", "technique": "T1185"},
    "csrf":               {"subtype": "csrf",              "cwe": "CWE-352",  "technique": "T1185"},
    "cross-site request": {"subtype": "csrf",              "cwe": "CWE-352",  "technique": "T1185"},
    # Auth / Identity
    "jwt":                {"subtype": "jwt_abuse",         "cwe": "CWE-345",  "technique": "T1078.001"},
    "json web token":     {"subtype": "jwt_abuse",         "cwe": "CWE-345",  "technique": "T1078.001"},
    "oauth":              {"subtype": "oauth_misconfig",   "cwe": "CWE-287",  "technique": "T1078.004"},
    "idor":               {"subtype": "idor",              "cwe": "CWE-639",  "technique": "T1530"},
    "insecure direct":    {"subtype": "idor",              "cwe": "CWE-639",  "technique": "T1530"},
    "bola":               {"subtype": "idor",              "cwe": "CWE-639",  "technique": "T1530"},
    "crlf":               {"subtype": "crlf_injection",    "cwe": "CWE-113",  "technique": "T1563"},
    "header injection":   {"subtype": "crlf_injection",    "cwe": "CWE-113",  "technique": "T1563"},
    "host header":        {"subtype": "host_header",       "cwe": "CWE-644",  "technique": "T1586.002"},
    "bypass":             {"subtype": "misconfig",         "cwe": "CWE-288",  "technique": "T1548"},
    "unauthenticated":    {"subtype": "misconfig",         "cwe": "CWE-306",  "technique": "T1548"},
    "misconfig":          {"subtype": "misconfig",         "cwe": "CWE-16",   "technique": "T1562.001"},
    "misconfiguration":   {"subtype": "misconfig",         "cwe": "CWE-16",   "technique": "T1562.001"},
    "default":            {"subtype": "misconfig",         "cwe": "CWE-1392", "technique": "T1078"},
    "admin":              {"subtype": "misconfig",         "cwe": "CWE-287",  "technique": "T1078"},
    "login":              {"subtype": "misconfig",         "cwe": "CWE-287",  "technique": "T1078"},
    "ssh":                {"subtype": "misconfig",         "cwe": "CWE-287",  "technique": "T1021.004"},
    # Info disclosure
    "cors":               {"subtype": "cors",              "cwe": "CWE-942",  "technique": "T1557"},
    "graphql":            {"subtype": "graphql_injection", "cwe": "CWE-943",  "technique": "T1083"},
    "introspection":      {"subtype": "graphql_injection", "cwe": "CWE-943",  "technique": "T1083"},
    "prototype pollut":   {"subtype": "prototype_pollution", "cwe": "CWE-1321", "technique": "T1190"},
    # Cloud / DNS
    "s3 bucket":          {"subtype": "s3_misconfig",      "cwe": "CWE-732",  "technique": "T1530"},
    "open bucket":        {"subtype": "s3_misconfig",      "cwe": "CWE-732",  "technique": "T1530"},
    "public bucket":      {"subtype": "s3_misconfig",      "cwe": "CWE-732",  "technique": "T1530"},
    "subdomain takeov":   {"subtype": "subdomain_takeover", "cwe": "CWE-923", "technique": "T1584.001"},
    "unclaimed":          {"subtype": "subdomain_takeover", "cwe": "CWE-923", "technique": "T1584.001"},
    "dns rebind":         {"subtype": "dns_rebinding",     "cwe": "CWE-350",  "technique": "T1557"},
    "dependency conf":    {"subtype": "dependency_confusion", "cwe": "CWE-427", "technique": "T1195"},
    "supply chain":       {"subtype": "dependency_confusion", "cwe": "CWE-427", "technique": "T1195"},
    # SCA / Legacy
    "dependency":         {"subtype": "misconfig",         "cwe": "CWE-1395", "technique": "T1190"},
    "sca":                {"subtype": "misconfig",         "cwe": "CWE-1395", "technique": "T1190"},
    "outdated":           {"subtype": "misconfig",         "cwe": "CWE-1395", "technique": "T1190"},
}

# Severity-only fallback when name/type keyword matching returns generic
_SEVERITY_FALLBACK = {
    4: "generic_critical",
    3: "generic_high",
}


def _infer_taxonomy(vuln_name: str, vuln_type: str, severity: int = 0) -> dict:
    """Return APME subtype, CWE, and MITRE technique for a vulnerability."""
    name_lower = vuln_name.lower()
    for keyword, info in TAXONOMY_MAP.items():
        if keyword in name_lower:
            return info

    if vuln_type:
        type_lower = vuln_type.lower()
        for keyword, info in TAXONOMY_MAP.items():
            if keyword in type_lower:
                return info

    # Severity-only fallback — distinguishes high/critical generics from noise
    fallback_subtype = _SEVERITY_FALLBACK.get(severity, "generic")
    return {"subtype": fallback_subtype, "cwe": "CWE-200", "technique": "T1592"}


def _make_id(prefix: str, value: str) -> str:
    return f"{prefix}::{value}"


def ingest_vulnerabilities(target_id: int) -> Tuple[List[Node], List[Edge]]:
    """Ingests Vulnerability records for a given target."""
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

        if validated:
            confidence = 1.0
        elif vuln.correlation_score and vuln.correlation_score > 0:
            confidence = min(vuln.correlation_score / 100.0, 0.95)
        else:
            confidence = {4: 0.75, 3: 0.60, 2: 0.45, 1: 0.30, 0: 0.20, -1: 0.10}.get(
                vuln.severity, 0.20
            )

        taxonomy = _infer_taxonomy(vuln.name, vuln.type or "", vuln.severity or 0)
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
                "sensitivity": "low",
            },
        )

        # Forward asset sensitivity so HVT rules can fire on high-value assets
        if vuln.subdomain and hasattr(vuln.subdomain, "name"):
            from apme.ingestion.assets import _infer_sensitivity
            vuln_node.properties["sensitivity"] = _infer_sensitivity(vuln.subdomain.name)

        nodes.append(vuln_node)

        if vuln.subdomain:
            parent_id = _make_id("domain", vuln.subdomain.name)
            edge_confidence = confidence
        elif vuln.endpoint:
            parent_id = _make_id("endpoint", vuln.endpoint.http_url)
            edge_confidence = confidence
        else:
            logger.debug("APME Ingestion: Vuln %s has no associated asset. Skipping.", vuln.id)
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
            logger.warning("APME Ingestion: %s", exc)

    logger.info(
        "APME Ingestion [vulnerabilities]: %d nodes, %d edges (target_id=%s)",
        len(nodes), len(edges), target_id,
    )
    return nodes, edges
