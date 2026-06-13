# APME Phase 1 — Noise Reduction & Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the APME engine by fixing broken ingestion code, extending the schema, adding 8 new path constraints, upgrading the scorer with EPSS/KEV/confidence-product factors, and adding the MITRE utility module that Phases 2 and 3 depend on.

**Architecture:** All changes are purely additive or bug-fix replacements within the existing `web/apme/` package. No Django migrations, no Temporal workflow changes, no API schema changes. The Neo4j graph builder gets explicit constraint properties on APME_EDGE relationships so the pathfinder can enforce them during traversal.

**Tech Stack:** Python 3.11, Django 5.2, Neo4j (python driver), PyYAML, pytest (inside Docker)

---

## File Map

| Action | File |
|---|---|
| CREATE | `web/apme/utils/__init__.py` |
| CREATE | `web/apme/utils/mitre.py` |
| MODIFY | `web/apme/graph/schema.py` |
| MODIFY | `web/apme/models/edge.py` |
| MODIFY | `web/apme/models/path.py` |
| MODIFY | `web/apme/ingestion/vulnerabilities.py` |
| MODIFY | `web/apme/ingestion/assets.py` |
| MODIFY | `web/apme/ingestion/credentials.py` |
| MODIFY | `web/apme/engine/rules_engine.py` |
| MODIFY | `web/apme/engine/constraints.py` |
| MODIFY | `web/apme/engine/scorer.py` |
| MODIFY | `web/apme/graph/builder.py` |
| MODIFY | `web/apme/engine/pathfinder.py` |
| MODIFY | `web/apme/orchestrator.py` |
| MODIFY | `web/apme/output/serializer.py` |
| CREATE | `web/tests/test_apme_phase1.py` |

All tests run inside the Docker container:
```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1 -v 2"
```

---

## Task 1: MITRE Utility Module

**Files:**
- Create: `web/apme/utils/__init__.py`
- Create: `web/apme/utils/mitre.py`
- Test: `web/tests/test_apme_phase1.py` (first section)

- [ ] **Step 1.1 — Create `web/apme/utils/__init__.py`**

```python
```
(empty file)

- [ ] **Step 1.2 — Create `web/apme/utils/mitre.py`**

```python
"""
APME MITRE ATT&CK Utility

Canonical lookup from technique ID → (name, tactic_slug, tactic_display).
Used by the pathfinder to annotate PathStep objects and by the serializer
to include MITRE attribution in API output.
"""

TECHNIQUE_CATALOG: dict[str, tuple[str, str, str]] = {
    "T1190":     ("Exploit Public-Facing Application",     "initial-access",       "Initial Access"),
    "T1059":     ("Command and Scripting Interpreter",     "execution",            "Execution"),
    "T1059.004": ("Unix Shell",                            "execution",            "Execution"),
    "T1059.006": ("Python",                                "execution",            "Execution"),
    "T1059.007": ("JavaScript",                            "execution",            "Execution"),
    "T1078":     ("Valid Accounts",                        "initial-access",       "Initial Access"),
    "T1078.001": ("Default Accounts",                      "privilege-escalation", "Privilege Escalation"),
    "T1078.004": ("Cloud Accounts",                        "defense-evasion",      "Defense Evasion"),
    "T1083":     ("File and Directory Discovery",          "discovery",            "Discovery"),
    "T1090":     ("Proxy",                                 "command-and-control",  "Command & Control"),
    "T1046":     ("Network Service Discovery",             "discovery",            "Discovery"),
    "T1021":     ("Remote Services",                       "lateral-movement",     "Lateral Movement"),
    "T1021.004": ("SSH",                                   "lateral-movement",     "Lateral Movement"),
    "T1548":     ("Abuse Elevation Control Mechanism",     "privilege-escalation", "Privilege Escalation"),
    "T1552":     ("Unsecured Credentials",                 "credential-access",    "Credential Access"),
    "T1552.001": ("Credentials In Files",                  "credential-access",    "Credential Access"),
    "T1552.005": ("Cloud Instance Metadata API",           "credential-access",    "Credential Access"),
    "T1528":     ("Steal Application Access Token",        "credential-access",    "Credential Access"),
    "T1530":     ("Data from Cloud Storage",               "collection",           "Collection"),
    "T1539":     ("Steal Web Session Cookie",              "credential-access",    "Credential Access"),
    "T1557":     ("Adversary-in-the-Middle",               "collection",           "Collection"),
    "T1557.001": ("LLMNR/NBT-NS Poisoning and Relay",      "collection",           "Collection"),
    "T1563":     ("Remote Service Session Hijacking",      "lateral-movement",     "Lateral Movement"),
    "T1566.001": ("Spearphishing Attachment",              "initial-access",       "Initial Access"),
    "T1566.002": ("Spearphishing Link",                    "initial-access",       "Initial Access"),
    "T1584.001": ("Domains",                               "resource-development", "Resource Development"),
    "T1586.002": ("Email Accounts",                        "resource-development", "Resource Development"),
    "T1185":     ("Browser Session Hijacking",             "collection",           "Collection"),
    "T1189":     ("Drive-by Compromise",                   "initial-access",       "Initial Access"),
    "T1195":     ("Supply Chain Compromise",               "initial-access",       "Initial Access"),
    "T1204.001": ("Malicious Link",                        "execution",            "Execution"),
    "T1505":     ("Server Software Component",             "persistence",          "Persistence"),
    "T1505.003": ("Web Shell",                             "persistence",          "Persistence"),
    "T1592":     ("Gather Victim Host Information",        "reconnaissance",       "Reconnaissance"),
}

TACTIC_COLOR: dict[str, str] = {
    "initial-access":       "#ff4444",
    "execution":            "#ff8800",
    "persistence":          "#ffcc00",
    "privilege-escalation": "#aa00ff",
    "defense-evasion":      "#0088ff",
    "credential-access":    "#00aaff",
    "discovery":            "#00ff88",
    "lateral-movement":     "#ff00aa",
    "collection":           "#ff6600",
    "command-and-control":  "#9944ff",
    "exfiltration":         "#ff0066",
    "impact":               "#ff0000",
    "resource-development": "#888888",
    "reconnaissance":       "#44aaff",
}


def lookup(technique_id: str) -> dict:
    """Return full MITRE metadata for a technique ID.

    Returns a safe dict with all keys present even for unknown IDs,
    so callers never need to guard against KeyError.
    """
    entry = TECHNIQUE_CATALOG.get(technique_id)
    if not entry:
        return {
            "technique_id":   technique_id,
            "technique_name": technique_id,
            "tactic_slug":    "unknown",
            "tactic_display": "Unknown",
            "tactic_color":   "#888888",
        }
    name, tactic_slug, tactic_display = entry
    return {
        "technique_id":   technique_id,
        "technique_name": name,
        "tactic_slug":    tactic_slug,
        "tactic_display": tactic_display,
        "tactic_color":   TACTIC_COLOR.get(tactic_slug, "#888888"),
    }
```

- [ ] **Step 1.3 — Write failing tests**

Create `web/tests/test_apme_phase1.py`:

```python
"""Phase 1 APME enhancement tests."""
from django.test import TestCase
from apme.utils.mitre import lookup, TECHNIQUE_CATALOG, TACTIC_COLOR


class MitreLookupTests(TestCase):

    def test_known_technique_returns_full_dict(self):
        result = lookup("T1190")
        self.assertEqual(result["technique_id"], "T1190")
        self.assertEqual(result["technique_name"], "Exploit Public-Facing Application")
        self.assertEqual(result["tactic_slug"], "initial-access")
        self.assertEqual(result["tactic_display"], "Initial Access")
        self.assertEqual(result["tactic_color"], "#ff4444")

    def test_unknown_technique_returns_safe_fallback(self):
        result = lookup("T9999")
        self.assertEqual(result["technique_id"], "T9999")
        self.assertEqual(result["tactic_slug"], "unknown")
        self.assertEqual(result["tactic_color"], "#888888")

    def test_all_catalog_entries_have_tactic_colors(self):
        for tid, (name, tactic_slug, tactic_display) in TECHNIQUE_CATALOG.items():
            self.assertIn(
                tactic_slug, TACTIC_COLOR,
                f"Technique {tid} tactic '{tactic_slug}' has no color entry",
            )

    def test_subtechnique_lookup(self):
        result = lookup("T1059.004")
        self.assertEqual(result["tactic_slug"], "execution")

    def test_lookup_returns_all_required_keys(self):
        for key in ("technique_id", "technique_name", "tactic_slug", "tactic_display", "tactic_color"):
            self.assertIn(key, lookup("T1190"))
            self.assertIn(key, lookup("T9999"))
```

- [ ] **Step 1.4 — Run tests (expect FAIL — module not importable yet)**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.MitreLookupTests -v 2"
```

Expected: `ModuleNotFoundError: No module named 'apme.utils'`

- [ ] **Step 1.5 — Run tests (expect PASS after files created)**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.MitreLookupTests -v 2"
```

Expected: 5 tests pass.

- [ ] **Step 1.6 — Commit**

```bash
git add web/apme/utils/__init__.py web/apme/utils/mitre.py web/tests/test_apme_phase1.py
git commit -m "feat(apme): add MITRE ATT&CK utility module with technique catalog and lookup"
```

---

## Task 2: Schema Extensions

**Files:**
- Modify: `web/apme/graph/schema.py`
- Modify: `web/apme/models/edge.py`

- [ ] **Step 2.1 — Replace `web/apme/graph/schema.py` entirely**

```python
"""
APME Configuration

Defines canonical node types and subtypes for the attack graph.
"""

NODE_TYPES = {
    "Asset": ["domain", "ip", "service", "host", "endpoint"],
    "Vulnerability": [
        # Injection
        "sqli", "command_injection", "code_injection", "nosql_injection",
        "xpath_injection", "ldap_injection", "log_injection",
        # Template / Server
        "rce", "ssti", "ssrf", "xxe",
        # File
        "lfi", "path_traversal", "file_upload",
        # Deserialization
        "deserialization",
        # Auth / Identity
        "misconfig", "jwt_abuse", "oauth_misconfig", "idor",
        "crlf_injection", "host_header",
        # Client-side
        "xss", "open_redirect", "clickjacking", "csrf",
        # Info
        "cors", "graphql_injection", "prototype_pollution",
        # Cloud / Supply chain
        "s3_misconfig", "subdomain_takeover", "dns_rebinding",
        "dependency_confusion",
        # Fallbacks
        "generic", "generic_high", "generic_critical",
    ],
    "Credential": [
        "api_key", "password", "token", "certificate", "ssh_key",
        "cloud_api_key", "jwt_token", "github_token", "db_password",
        "generic_secret",
    ],
    "Identity":  ["user", "admin", "service_account"],
    "Privilege": ["user", "admin", "domain_admin", "root"],
    "Network":   ["internet", "external", "internal", "dmz"],
    "Technology": [
        "wordpress", "php", "java", "python", "nodejs",
        "nginx", "apache", "spring", "jenkins", "generic",
    ],
    "Capability": [
        # Original
        "db_access", "data_exfil", "rce_execution", "authenticated_access",
        "pivot", "cloud_access", "internal_discovery",
        # New
        "account_takeover", "session_hijacking", "phishing_amplification",
        "persistence", "code_exfiltration", "credential_harvesting",
        "lateral_movement", "metadata_access", "hvt_compromise",
        "supply_chain_compromise", "dos_capability",
    ],
}

EDGE_TYPES = [
    "RESOLVES_TO",    # domain -> ip
    "HOSTS",          # ip -> service
    "EXPOSES",        # service/asset -> vulnerability
    "LEADS_TO",       # vulnerability/capability -> capability
    "AUTHENTICATES",  # credential -> service
    "ESCALATES_TO",   # identity -> privilege
    "TRUSTS",         # system -> system
    "CONNECTED_TO",   # network pivot
    "USES_TECH",      # asset -> technology
]
```

- [ ] **Step 2.2 — Add `USES_TECH` to `web/apme/models/edge.py`**

Replace the `EDGE_TYPES` set at the top of the file:

```python
EDGE_TYPES = {
    "RESOLVES_TO",
    "HOSTS",
    "EXPOSES",
    "LEADS_TO",
    "AUTHENTICATES",
    "ESCALATES_TO",
    "TRUSTS",
    "CONNECTED_TO",
    "USES_TECH",
}
```

- [ ] **Step 2.3 — Add PathStep MITRE fields to `web/apme/models/path.py`**

Replace the `PathStep` dataclass:

```python
@dataclass
class PathStep:
    """A single step within an attack path."""
    from_id: str
    to_id: str
    action: str
    confidence: float = 0.0
    validated: bool = False
    edge_type: str = ""
    mitre_technique: str = ""
    mitre_tactic: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "action": self.action,
            "confidence": self.confidence,
            "validated": self.validated,
            "status": "validated" if self.validated else "inferred",
            "edge_type": self.edge_type,
            "mitre_technique": self.mitre_technique,
            "mitre_tactic": self.mitre_tactic,
        }
```

Also update `AttackPath.risk` docstring to include `speculative`:

```python
@dataclass
class AttackPath:
    """..."""
    id: str
    start: str
    end: str
    steps: List[PathStep] = field(default_factory=list)
    score: float = 0.0
    risk: str = "low"    # critical | high | medium | low | speculative
    entry_type: str = "internet"
    ...
```

- [ ] **Step 2.4 — Write schema tests (add to `test_apme_phase1.py`)**

Append to the test file:

```python
from apme.graph.schema import NODE_TYPES, EDGE_TYPES as SCHEMA_EDGE_TYPES
from apme.models.edge import EDGE_TYPES as MODEL_EDGE_TYPES, Edge
from apme.models.path import PathStep


class SchemaTests(TestCase):

    def test_uses_tech_in_model_edge_types(self):
        self.assertIn("USES_TECH", MODEL_EDGE_TYPES)

    def test_uses_tech_edge_is_valid(self):
        e = Edge(from_id="domain::example.com", to_id="tech::1",
                 type="USES_TECH", confidence=1.0)
        self.assertEqual(e.type, "USES_TECH")

    def test_new_vulnerability_subtypes_present(self):
        subtypes = NODE_TYPES["Vulnerability"]
        for expected in ("command_injection", "deserialization", "jwt_abuse",
                         "cors", "subdomain_takeover", "generic_high", "generic_critical"):
            self.assertIn(expected, subtypes, f"Missing subtype: {expected}")

    def test_new_capability_nodes_present(self):
        caps = NODE_TYPES["Capability"]
        for expected in ("account_takeover", "session_hijacking", "credential_harvesting",
                         "metadata_access", "lateral_movement"):
            self.assertIn(expected, caps, f"Missing capability: {expected}")

    def test_technology_node_type_present(self):
        self.assertIn("Technology", NODE_TYPES)
        self.assertIn("wordpress", NODE_TYPES["Technology"])

    def test_pathstep_has_mitre_fields(self):
        step = PathStep(from_id="a", to_id="b", action="test")
        self.assertEqual(step.mitre_technique, "")
        self.assertEqual(step.mitre_tactic, "")
        d = step.to_dict()
        self.assertIn("mitre_technique", d)
        self.assertIn("mitre_tactic", d)
```

- [ ] **Step 2.5 — Run schema tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.SchemaTests -v 2"
```

Expected: 6 tests pass.

- [ ] **Step 2.6 — Commit**

```bash
git add web/apme/graph/schema.py web/apme/models/edge.py web/apme/models/path.py web/tests/test_apme_phase1.py
git commit -m "feat(apme): extend schema with 25 vuln subtypes, 11 capabilities, Technology nodes, USES_TECH edge"
```

---

## Task 3: Fix Vulnerability Ingestion

**Files:**
- Modify: `web/apme/ingestion/vulnerabilities.py`

This task: (a) removes the broken `SEVERITY_TO_SUBTYPE` dict, (b) adds a severity-only fallback in `_infer_taxonomy`, (c) expands `TAXONOMY_MAP` with all new subtypes.

- [ ] **Step 3.1 — Replace `web/apme/ingestion/vulnerabilities.py` entirely**

```python
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
    "rce":                {"subtype": "rce",               "cwe": "CWE-94",   "technique": "T1190"},
    "remote code exec":   {"subtype": "rce",               "cwe": "CWE-94",   "technique": "T1190"},
    "code injection":     {"subtype": "code_injection",    "cwe": "CWE-94",   "technique": "T1059"},
    "nosql":              {"subtype": "nosql_injection",   "cwe": "CWE-943",  "technique": "T1190"},
    "mongodb":            {"subtype": "nosql_injection",   "cwe": "CWE-943",  "technique": "T1190"},
    "xpath":              {"subtype": "xpath_injection",   "cwe": "CWE-643",  "technique": "T1083"},
    "ldap injection":     {"subtype": "ldap_injection",    "cwe": "CWE-90",   "technique": "T1548"},
    "log4j":              {"subtype": "log_injection",     "cwe": "CWE-917",  "technique": "T1190"},
    "log4shell":          {"subtype": "log_injection",     "cwe": "CWE-917",  "technique": "T1190"},
    "jndi":               {"subtype": "log_injection",     "cwe": "CWE-917",  "technique": "T1190"},
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
    "unrestricted upload":{"subtype": "file_upload",       "cwe": "CWE-434",  "technique": "T1190"},
    # Deserialization
    "deserializ":         {"subtype": "deserialization",   "cwe": "CWE-502",  "technique": "T1059"},
    "insecure deserial":  {"subtype": "deserialization",   "cwe": "CWE-502",  "technique": "T1059"},
    # Client-side
    "xss":                {"subtype": "xss",               "cwe": "CWE-79",   "technique": "T1189"},
    "cross-site scripting":{"subtype": "xss",              "cwe": "CWE-79",   "technique": "T1189"},
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
    "prototype pollut":   {"subtype": "prototype_pollution","cwe": "CWE-1321","technique": "T1190"},
    # Cloud / DNS
    "s3 bucket":          {"subtype": "s3_misconfig",      "cwe": "CWE-732",  "technique": "T1530"},
    "open bucket":        {"subtype": "s3_misconfig",      "cwe": "CWE-732",  "technique": "T1530"},
    "public bucket":      {"subtype": "s3_misconfig",      "cwe": "CWE-732",  "technique": "T1530"},
    "subdomain takeov":   {"subtype": "subdomain_takeover","cwe": "CWE-923",  "technique": "T1584.001"},
    "unclaimed":          {"subtype": "subdomain_takeover","cwe": "CWE-923",  "technique": "T1584.001"},
    "dns rebind":         {"subtype": "dns_rebinding",     "cwe": "CWE-350",  "technique": "T1557"},
    "dependency conf":    {"subtype": "dependency_confusion","cwe": "CWE-427","technique": "T1195"},
    "supply chain":       {"subtype": "dependency_confusion","cwe": "CWE-427","technique": "T1195"},
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
                # Sensitivity forwarded from parent asset (set below if available)
                "sensitivity": "low",
            },
        )

        # Forward asset sensitivity so HVT rules can fire
        if vuln.subdomain and hasattr(vuln.subdomain, 'name'):
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
```

- [ ] **Step 3.2 — Write ingestion tests (append to `test_apme_phase1.py`)**

```python
from apme.ingestion.vulnerabilities import _infer_taxonomy


class TaxonomyInferenceTests(TestCase):

    def test_sqli_by_name(self):
        result = _infer_taxonomy("SQL Injection via login form", "", 3)
        self.assertEqual(result["subtype"], "sqli")
        self.assertEqual(result["cwe"], "CWE-89")
        self.assertEqual(result["technique"], "T1190")

    def test_xss_by_name(self):
        result = _infer_taxonomy("Reflected XSS in search parameter", "", 2)
        self.assertEqual(result["subtype"], "xss")

    def test_log4j_maps_to_log_injection(self):
        result = _infer_taxonomy("Log4j RCE via JNDI", "", 4)
        self.assertEqual(result["subtype"], "log_injection")

    def test_deserialization_keyword(self):
        result = _infer_taxonomy("Java deserialization gadget chain", "", 4)
        self.assertEqual(result["subtype"], "deserialization")

    def test_severity_4_fallback_to_generic_critical(self):
        result = _infer_taxonomy("Some unknown critical finding", "", 4)
        self.assertEqual(result["subtype"], "generic_critical")

    def test_severity_3_fallback_to_generic_high(self):
        result = _infer_taxonomy("Unknown high severity issue", "", 3)
        self.assertEqual(result["subtype"], "generic_high")

    def test_severity_2_fallback_to_generic(self):
        result = _infer_taxonomy("Unknown medium finding", "", 2)
        self.assertEqual(result["subtype"], "generic")

    def test_type_field_used_as_fallback(self):
        result = _infer_taxonomy("Nuclei finding", "SSRF", 2)
        self.assertEqual(result["subtype"], "ssrf")

    def test_jwt_maps_to_jwt_abuse(self):
        result = _infer_taxonomy("JWT secret exposed in response", "", 3)
        self.assertEqual(result["subtype"], "jwt_abuse")

    def test_subdomain_takeover(self):
        result = _infer_taxonomy("Subdomain takeover via dangling CNAME", "", 3)
        self.assertEqual(result["subtype"], "subdomain_takeover")
```

- [ ] **Step 3.3 — Run ingestion tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.TaxonomyInferenceTests -v 2"
```

Expected: 10 tests pass.

- [ ] **Step 3.4 — Commit**

```bash
git add web/apme/ingestion/vulnerabilities.py web/tests/test_apme_phase1.py
git commit -m "feat(apme): fix SEVERITY_TO_SUBTYPE, expand TAXONOMY_MAP to 55 entries with severity fallback"
```

---

## Task 4: Technology Ingestion

**Files:**
- Modify: `web/apme/ingestion/assets.py`

- [ ] **Step 4.1 — Add `ingest_technologies()` to `web/apme/ingestion/assets.py`**

Add this function and the helper after the existing `ingest_endpoints()` function (before the end of file):

```python
# Technology subtype detection: keyword → APME subtype
_TECH_SUBTYPE_MAP = {
    "wordpress": "wordpress",
    "wp-": "wordpress",
    "drupal": "generic",
    "joomla": "generic",
    "php": "php",
    "java": "java",
    "spring": "spring",
    "jenkins": "jenkins",
    "python": "python",
    "django": "python",
    "flask": "python",
    "node": "nodejs",
    "express": "nodejs",
    "nginx": "nginx",
    "apache": "apache",
}


def _infer_tech_subtype(tech_name: str) -> str:
    name_lower = tech_name.lower()
    for keyword, subtype in _TECH_SUBTYPE_MAP.items():
        if keyword in name_lower:
            return subtype
    return "generic"


def ingest_technologies(target_id: int) -> Tuple[List[Node], List[Edge]]:
    """
    Ingests detected Technology records for a given target domain.

    Creates Technology APME nodes and USES_TECH edges from Asset nodes.
    Technology nodes enable tech-specific attack rules (e.g. WordPress → RCE,
    Java → deserialization) via constraint engine context flags.
    """
    from startScan.models import Subdomain

    nodes: List[Node] = []
    edges: List[Edge] = []

    subdomains = Subdomain.objects.filter(
        target_domain_id=target_id
    ).prefetch_related("technologies")

    seen_tech_ids: set = set()

    for sub in subdomains:
        asset_node_id = _make_id("domain", sub.name)

        for tech in sub.technologies.all():
            tech_node_id = _make_id("tech", str(tech.id))
            subtype = _infer_tech_subtype(tech.name)

            if tech_node_id not in seen_tech_ids:
                nodes.append(Node(
                    id=tech_node_id,
                    type="Technology",
                    subtype=subtype,
                    confidence=1.0,
                    source="reNgine:technology_detection",
                    properties={
                        "name": tech.name,
                        "version": getattr(tech, "version", "") or "",
                        "target_id": target_id,
                    },
                ))
                seen_tech_ids.add(tech_node_id)

            try:
                edges.append(Edge(
                    from_id=asset_node_id,
                    to_id=tech_node_id,
                    type="USES_TECH",
                    confidence=1.0,
                    properties={"tech_name": tech.name},
                ))
            except ValueError as exc:
                logger.warning("APME Ingestion [tech]: %s", exc)

    logger.info(
        "APME Ingestion [technologies]: %d nodes, %d edges (target_id=%s)",
        len(nodes), len(edges), target_id,
    )
    return nodes, edges
```

Also add `Tuple` to the imports at the top of the file if not already present:
```python
from typing import List, Tuple
```

- [ ] **Step 4.2 — Commit**

```bash
git add web/apme/ingestion/assets.py
git commit -m "feat(apme): add technology ingestion — USES_TECH edges from subdomain assets to tech nodes"
```

---

## Task 5: Credential Enrichment

**Files:**
- Modify: `web/apme/ingestion/credentials.py`

- [ ] **Step 5.1 — Replace `SECRET_TYPE_TO_SUBTYPE` and `_infer_credential_subtype` in `web/apme/ingestion/credentials.py`**

Replace the existing `SECRET_TYPE_TO_SUBTYPE` dict and `_infer_credential_subtype` function:

```python
# Ordered patterns: first match wins. More specific entries MUST come first.
_CREDENTIAL_PATTERNS = [
    # Cloud API keys
    ("AKIA",           "cloud_api_key"),   # AWS access key
    ("aws",            "cloud_api_key"),
    ("gcp",            "cloud_api_key"),
    ("azure",          "cloud_api_key"),
    ("google_api",     "cloud_api_key"),
    # VCS tokens
    ("ghp_",           "github_token"),
    ("github",         "github_token"),
    ("gitlab",         "generic_secret"),
    # JWT
    ("jwt",            "jwt_token"),
    ("json web token", "jwt_token"),
    ("bearer",         "jwt_token"),
    # Database
    ("db_pass",        "db_password"),
    ("database_url",   "db_password"),
    ("mysql",          "db_password"),
    ("postgres",       "db_password"),
    ("mongodb",        "db_password"),
    # SSH
    ("ssh",            "ssh_key"),
    ("-----begin",     "ssh_key"),
    ("private key",    "ssh_key"),
    # Generic password/token/API
    ("password",       "password"),
    ("api_key",        "api_key"),
    ("api key",        "api_key"),
    ("apikey",         "api_key"),
    ("token",          "token"),
    ("oauth",          "token"),
    ("certificate",    "certificate"),
    ("stripe",         "api_key"),
]


def _infer_credential_subtype(secret_type: str) -> str:
    lower = secret_type.lower()
    for keyword, subtype in _CREDENTIAL_PATTERNS:
        if keyword in lower:
            return subtype
    return "generic_secret"
```

- [ ] **Step 5.2 — Write credential tests (append to `test_apme_phase1.py`)**

```python
from apme.ingestion.credentials import _infer_credential_subtype


class CredentialSubtypeTests(TestCase):

    def test_aws_key_to_cloud_api_key(self):
        self.assertEqual(_infer_credential_subtype("AWS Access Key"), "cloud_api_key")

    def test_akia_prefix_to_cloud_api_key(self):
        self.assertEqual(_infer_credential_subtype("AKIA1234EXAMPLE"), "cloud_api_key")

    def test_jwt_to_jwt_token(self):
        self.assertEqual(_infer_credential_subtype("JWT Token"), "jwt_token")

    def test_github_token(self):
        self.assertEqual(_infer_credential_subtype("ghp_github_token"), "github_token")

    def test_db_password(self):
        self.assertEqual(_infer_credential_subtype("POSTGRES_PASSWORD"), "db_password")

    def test_ssh_key(self):
        self.assertEqual(_infer_credential_subtype("-----BEGIN RSA PRIVATE KEY-----"), "ssh_key")

    def test_generic_fallback(self):
        self.assertEqual(_infer_credential_subtype("some_unknown_secret_type"), "generic_secret")

    def test_stripe_api_key(self):
        self.assertEqual(_infer_credential_subtype("stripe_secret_key"), "api_key")
```

- [ ] **Step 5.3 — Run credential tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.CredentialSubtypeTests -v 2"
```

Expected: 8 tests pass.

- [ ] **Step 5.4 — Commit**

```bash
git add web/apme/ingestion/credentials.py web/tests/test_apme_phase1.py
git commit -m "feat(apme): enrich credential ingestion with 6 specific subtypes (cloud_api_key, jwt_token, github_token, db_password, ssh_key, generic_secret)"
```

---

## Task 6: Rules Engine — Numeric Comparisons & Constraint Flags

**Files:**
- Modify: `web/apme/engine/rules_engine.py`

- [ ] **Step 6.1 — Replace `web/apme/engine/rules_engine.py` entirely**

```python
"""
APME Rules Engine

Loads attack rules from config/rules.yaml and applies them to graph nodes
to produce derived edges.

Enhanced in Phase 1 to support:
- Numeric comparisons in node.property conditions (>=, <=, >, <)
- node.confidence numeric comparison
- node.property as a list (AND-semantics — all must match)
- confidence_modifier in then.create_edge
- Constraint flags (requires_victim, requires_php, requires_java,
  requires_python, requires_wordpress) propagated to edge properties
"""

import logging
import operator
import os
from typing import Any, Dict, List

import yaml

from apme.models.edge import Edge
from apme.models.node import Node

logger = logging.getLogger(__name__)

_RULES_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "rules.yaml")

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
        try:
            with open(rules_file, "r") as f:
                data = yaml.safe_load(f)
                self._rules = data.get("rules", [])
            logger.info("APME RulesEngine: Loaded %d rules from %s.", len(self._rules), rules_file)
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

            # Apply confidence modifier based on node properties
            confidence = min(base_confidence * confidence_modifier, 1.0)
            # Reduce confidence if ERL has NOT validated this node
            if not node.properties.get("validated", False) and confidence_modifier > 1.0:
                confidence = base_confidence  # don't boost unvalidated findings

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

        # node.property (single string or list)
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
    # Fall back to equality
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
    # Try numeric comparison first
    for op_str, op_fn in _OPS.items():
        if val.startswith(op_str):
            try:
                threshold = float(val[len(op_str):])
                return op_fn(float(node_val), threshold)
            except (ValueError, TypeError):
                return False
    # Exact string match
    return str(node_val) == val
```

- [ ] **Step 6.2 — Write rules engine tests (append to `test_apme_phase1.py`)**

```python
from apme.engine.rules_engine import _numeric_check, _property_check, RulesEngine
from apme.models.node import Node


class RulesEngineNumericTests(TestCase):

    def test_numeric_check_gte(self):
        self.assertTrue(_numeric_check(3, ">=3"))
        self.assertTrue(_numeric_check(4, ">=3"))
        self.assertFalse(_numeric_check(2, ">=3"))

    def test_numeric_check_gt(self):
        self.assertTrue(_numeric_check(4, ">3"))
        self.assertFalse(_numeric_check(3, ">3"))

    def test_numeric_check_lte(self):
        self.assertTrue(_numeric_check(2, "<=3"))
        self.assertFalse(_numeric_check(4, "<=3"))

    def test_numeric_check_exact_float(self):
        self.assertTrue(_numeric_check(0.5, "0.5"))

    def test_property_check_exact(self):
        props = {"validated": "True", "sensitivity": "high"}
        self.assertTrue(_property_check(props, "sensitivity:high"))
        self.assertFalse(_property_check(props, "sensitivity:low"))

    def test_property_check_numeric_severity(self):
        props = {"severity": 4}
        self.assertTrue(_property_check(props, "severity:>=3"))
        self.assertFalse(_property_check(props, "severity:>=5"))

    def test_property_check_missing_key(self):
        self.assertFalse(_property_check({}, "severity:>=3"))

    def test_rules_engine_loads_yaml(self):
        engine = RulesEngine()
        self.assertGreater(len(engine._rules), 0)

    def test_constraint_flags_propagated_to_edge(self):
        # Create a minimal rules engine with an inline rule
        engine = RulesEngine.__new__(RulesEngine)
        engine._rules = [{
            "name": "test_victim_rule",
            "mitre_id": "T1189",
            "if": {"node.type": "Vulnerability", "node.subtype": "xss"},
            "then": {"create_edge": {
                "type": "LEADS_TO",
                "target_subtype": "session_hijacking",
                "confidence": 0.65,
                "requires_victim": True,
            }},
        }]
        from apme.models.node import Node
        xss_node = Node(id="vuln::1", type="Vulnerability", subtype="xss",
                        confidence=0.6, source="test", properties={})
        target = Node(id="goal::capability::session_hijacking", type="Capability",
                      subtype="session_hijacking", confidence=1.0, source="test",
                      properties={})
        edges = engine.apply(xss_node, [xss_node, target])
        self.assertEqual(len(edges), 1)
        self.assertTrue(edges[0].properties.get("requires_victim"))
        self.assertEqual(edges[0].properties.get("mitre_id"), "T1189")
```

- [ ] **Step 6.3 — Run rules engine tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.RulesEngineNumericTests -v 2"
```

Expected: 9 tests pass.

- [ ] **Step 6.4 — Commit**

```bash
git add web/apme/engine/rules_engine.py web/tests/test_apme_phase1.py
git commit -m "feat(apme): enhance rules engine with numeric comparisons, list property conditions, constraint flag propagation"
```

---

## Task 7: Constraint Engine — 8 New Constraints

**Files:**
- Modify: `web/apme/engine/constraints.py`

- [ ] **Step 7.1 — Replace `web/apme/engine/constraints.py` entirely**

```python
"""
APME Constraint Engine

Validates whether a proposed attack path step is realistic.
Prevents fantasy exploit chains by enforcing:
- Authentication requirements
- Network segmentation boundaries
- Privilege level requirements
- Step confidence threshold (Phase 1)
- Cycle detection (Phase 1)
- Victim interaction requirement (Phase 1)
- Technology compatibility gates (Phase 1)
- Minimum path confidence product (Phase 1)
- Authenticated endpoint boundary (Phase 1)
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

_PRIVILEGE_ORDER = ["none", "user", "admin", "domain_admin", "root"]

# Steps with confidence below this threshold are always blocked.
MIN_STEP_CONFIDENCE = 0.15

# If the cumulative product of step confidences drops below this, block the path.
MIN_PATH_CONFIDENCE_PRODUCT = 0.05


class PathContext:
    """Tracks cumulative state along a path as steps are evaluated."""

    def __init__(self):
        self.has_auth: bool = False
        self.has_internal_access: bool = False
        self.privilege_level: str = "none"
        self.validated_step_count: int = 0
        # Phase 1 additions
        self.has_victim_interaction: bool = False
        self.has_php_tech: bool = False
        self.has_java_tech: bool = False
        self.has_python_tech: bool = False
        self.has_wordpress_tech: bool = False
        self.visited_node_ids: set = field_default_set()
        self.path_confidence_product: float = 1.0

    def grant_auth(self) -> None:
        self.has_auth = True

    def grant_internal_access(self) -> None:
        self.has_internal_access = True

    def escalate_privilege(self, level: str) -> None:
        if level in _PRIVILEGE_ORDER:
            if _PRIVILEGE_ORDER.index(level) > _PRIVILEGE_ORDER.index(self.privilege_level):
                self.privilege_level = level

    def visit_node(self, node_id: str) -> None:
        self.visited_node_ids.add(node_id)

    def update_confidence_product(self, step_confidence: float) -> None:
        self.path_confidence_product *= step_confidence


def field_default_set():
    """Return a new empty set (used as default factory equivalent)."""
    return set()


class ConstraintEngine:
    """
    Validates individual path steps against the current path context.
    Returns False for any step that violates a constraint.
    """

    def validate_step(self, step: Dict[str, Any], context: PathContext) -> bool:
        """
        Validate a single step in the context of the accumulated path state.
        All 11 constraints must pass; first failure short-circuits and blocks.
        """
        # 1. Min step confidence
        if step.get("confidence", 1.0) < MIN_STEP_CONFIDENCE:
            logger.debug(
                "APME Constraint [confidence]: Step '%s' confidence %.2f below threshold %.2f. Blocked.",
                step.get("action"), step.get("confidence"), MIN_STEP_CONFIDENCE,
            )
            return False

        # 2. Cycle detection
        to_id = step.get("to_id", "")
        if to_id and to_id in context.visited_node_ids:
            logger.debug("APME Constraint [cycle]: Node '%s' already visited. Blocked.", to_id)
            return False

        # 3. Auth requirement
        if step.get("requires_auth") and not context.has_auth:
            logger.debug(
                "APME Constraint [auth]: Step '%s' requires auth but none granted. Blocked.",
                step.get("action"),
            )
            return False

        # 4. Internal network requirement
        if step.get("requires_internal") and not context.has_internal_access:
            logger.debug(
                "APME Constraint [internal]: Step '%s' requires internal access. Blocked.",
                step.get("action"),
            )
            return False

        # 5. Privilege level
        required_priv = step.get("requires_privilege", "none")
        if required_priv in _PRIVILEGE_ORDER:
            current_idx = _PRIVILEGE_ORDER.index(context.privilege_level)
            required_idx = _PRIVILEGE_ORDER.index(required_priv)
            if current_idx < required_idx:
                logger.debug(
                    "APME Constraint [privilege]: Step requires '%s' but level is '%s'. Blocked.",
                    required_priv, context.privilege_level,
                )
                return False

        # 6. Victim interaction
        if step.get("requires_victim") and not context.has_victim_interaction:
            logger.debug(
                "APME Constraint [victim]: Step '%s' requires victim interaction. Blocked.",
                step.get("action"),
            )
            return False

        # 7. PHP gate
        if step.get("requires_php") and not context.has_php_tech:
            logger.debug("APME Constraint [php]: PHP required but not detected. Blocked.")
            return False

        # 8. Java gate
        if step.get("requires_java") and not context.has_java_tech:
            logger.debug("APME Constraint [java]: Java required but not detected. Blocked.")
            return False

        # 9. WordPress gate
        if step.get("requires_wordpress") and not context.has_wordpress_tech:
            logger.debug("APME Constraint [wordpress]: WordPress required but not detected. Blocked.")
            return False

        # 10. Authenticated endpoint boundary
        if step.get("endpoint_requires_auth") and not context.has_auth:
            logger.debug("APME Constraint [endpoint_auth]: Endpoint requires auth. Blocked.")
            return False

        # 11. Minimum path confidence product
        projected = context.path_confidence_product * step.get("confidence", 1.0)
        if projected < MIN_PATH_CONFIDENCE_PRODUCT:
            logger.debug(
                "APME Constraint [path_confidence]: Projected product %.4f below %.4f. Blocked.",
                projected, MIN_PATH_CONFIDENCE_PRODUCT,
            )
            return False

        return True

    def update_context(self, step: Dict[str, Any], context: PathContext) -> None:
        """Apply side-effects of a valid step to the path context."""
        if step.get("grants_auth"):
            context.grant_auth()
        if step.get("grants_internal"):
            context.grant_internal_access()
        if step.get("grants_privilege"):
            context.escalate_privilege(step["grants_privilege"])
        if step.get("validated"):
            context.validated_step_count += 1
        # Technology context propagation
        to_subtype = step.get("to_subtype", "")
        if to_subtype == "php":
            context.has_php_tech = True
        elif to_subtype == "java":
            context.has_java_tech = True
        elif to_subtype in ("python",):
            context.has_python_tech = True
        elif to_subtype == "wordpress":
            context.has_wordpress_tech = True
        # Track visited nodes and confidence product
        to_id = step.get("to_id", "")
        if to_id:
            context.visit_node(to_id)
        context.update_confidence_product(step.get("confidence", 1.0))
```

- [ ] **Step 7.2 — Write constraint tests (append to `test_apme_phase1.py`)**

```python
from apme.engine.constraints import ConstraintEngine, PathContext, MIN_STEP_CONFIDENCE


class ConstraintEngineTests(TestCase):

    def _make_step(self, **kwargs):
        defaults = {"action": "test", "confidence": 0.8, "to_id": "node::1"}
        defaults.update(kwargs)
        return defaults

    def setUp(self):
        self.engine = ConstraintEngine()
        self.ctx = PathContext()

    def test_low_confidence_step_blocked(self):
        step = self._make_step(confidence=MIN_STEP_CONFIDENCE - 0.01)
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_adequate_confidence_passes(self):
        step = self._make_step(confidence=0.80)
        self.assertTrue(self.engine.validate_step(step, self.ctx))

    def test_cycle_detection_blocks_revisit(self):
        self.ctx.visit_node("vuln::99")
        step = self._make_step(to_id="vuln::99")
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_cycle_detection_allows_new_node(self):
        self.ctx.visit_node("vuln::99")
        step = self._make_step(to_id="vuln::100")
        self.assertTrue(self.engine.validate_step(step, self.ctx))

    def test_victim_required_blocked_without_context(self):
        step = self._make_step(requires_victim=True)
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_victim_required_passes_with_context(self):
        self.ctx.has_victim_interaction = True
        step = self._make_step(requires_victim=True)
        self.assertTrue(self.engine.validate_step(step, self.ctx))

    def test_php_gate_blocked_without_tech(self):
        step = self._make_step(requires_php=True)
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_php_gate_passes_with_tech(self):
        self.ctx.has_php_tech = True
        step = self._make_step(requires_php=True)
        self.assertTrue(self.engine.validate_step(step, self.ctx))

    def test_path_confidence_product_drops_below_threshold(self):
        # Set product near threshold
        self.ctx.path_confidence_product = 0.06
        step = self._make_step(confidence=0.8)   # 0.06 * 0.8 = 0.048 < 0.05
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_wordpress_gate_blocked_without_tech(self):
        step = self._make_step(requires_wordpress=True)
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_update_context_sets_visited(self):
        step = self._make_step(to_id="cap::pivot")
        self.engine.update_context(step, self.ctx)
        self.assertIn("cap::pivot", self.ctx.visited_node_ids)

    def test_update_context_propagates_php_tech(self):
        step = self._make_step(to_subtype="php")
        self.engine.update_context(step, self.ctx)
        self.assertTrue(self.ctx.has_php_tech)
```

- [ ] **Step 7.3 — Run constraint tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.ConstraintEngineTests -v 2"
```

Expected: 12 tests pass.

- [ ] **Step 7.4 — Commit**

```bash
git add web/apme/engine/constraints.py web/tests/test_apme_phase1.py
git commit -m "feat(apme): add 8 new path constraints (confidence threshold, cycle detection, victim gate, tech gates, path product)"
```

---

## Task 8: Scoring Engine Enhancements

**Files:**
- Modify: `web/apme/engine/scorer.py`

- [ ] **Step 8.1 — Replace `web/apme/engine/scorer.py` entirely**

```python
"""
APME Scoring Engine

Scores attack paths based on (additive factors sum to 1.0):
- Vulnerability severity       (0.20)
- Exploitability / CVSS        (0.20)
- Path length                  (0.15)
- Privilege gained             (0.15)
- Impact (blast radius)        (0.15)
- EPSS score                   (0.15)

Plus post-sum modifiers:
- Path confidence product multiplier (×0.5–1.0)
- CISA KEV flat boost (+0.10)
- ERL validated step boost (+0.05 per step, max +0.15)

Risk classification (applied after modifiers):
  speculative : 0 validated steps AND score < 0.40
  low         : score <= 0.50
  medium      : score <= 0.70
  high        : score <= 0.85
  critical    : score  > 0.85
"""

import logging
from typing import Any, Dict, List

from apme.models.path import AttackPath, PathStep

logger = logging.getLogger(__name__)

SEVERITY_MAP = {-1: 0.0, 0: 0.05, 1: 0.25, 2: 0.50, 3: 0.75, 4: 1.0}
PRIVILEGE_MAP = {"none": 0.0, "user": 0.25, "admin": 0.75, "domain_admin": 1.0, "root": 1.0}


class Scorer:
    """Computes a risk score for a complete attack path."""

    WEIGHTS = {
        "severity":        0.20,
        "exploitability":  0.20,
        "path_length":     0.15,
        "privilege_gain":  0.15,
        "impact":          0.15,
        "epss":            0.15,
    }

    def __init__(self):
        self._blast_radius_cache: Dict[str, int] = {}

    def score(self, path: AttackPath, path_metadata: Dict[str, Any]) -> float:
        """Compute and set path.score and path.risk. Returns the final score."""
        steps = path.steps
        if not steps:
            path.score = 0.0
            path.risk = "low"
            return 0.0

        # 1. Severity
        severity_raw = path_metadata.get("severity", -1)
        severity_score = SEVERITY_MAP.get(severity_raw, 0.0)

        # 2. Exploitability
        cvss = path_metadata.get("cvss_score", 0.0)
        exploitability = min(cvss / 10.0, 1.0) if cvss else severity_score * 0.8

        # 3. Path length (shorter = higher risk)
        length_score = 1.0 / max(len(steps), 1)

        # 4. Privilege gained
        privilege = path_metadata.get("privilege_gained", "none")
        privilege_score = PRIVILEGE_MAP.get(privilege, 0.0)

        # 5. Impact (blast radius + target sensitivity)
        blast_radius = path_metadata.get("blast_radius", 1)
        blast_score = min(blast_radius / 50.0, 1.0)
        sensitivity_val = path_metadata.get("target_sensitivity", "low")
        sensitivity_score = {"high": 1.0, "medium": 0.6, "low": 0.2}.get(sensitivity_val, 0.2)
        impact_score = (blast_score * 0.4) + (sensitivity_score * 0.6)

        # 6. EPSS
        epss_percentile = path_metadata.get("epss_percentile", 0.0)
        epss_score = min(epss_percentile / 100.0, 1.0) if epss_percentile else 0.0

        # Additive sum
        score = (
            severity_score   * self.WEIGHTS["severity"]
            + exploitability * self.WEIGHTS["exploitability"]
            + length_score   * self.WEIGHTS["path_length"]
            + privilege_score* self.WEIGHTS["privilege_gain"]
            + impact_score   * self.WEIGHTS["impact"]
            + epss_score     * self.WEIGHTS["epss"]
        )

        # Path confidence product multiplier [0.5, 1.0]
        conf_product = path_metadata.get("path_confidence_product", 1.0)
        conf_multiplier = max(min(conf_product, 1.0), 0.5)
        score *= conf_multiplier

        # CISA KEV flat boost
        if path_metadata.get("has_cisa_kev"):
            score = min(score + 0.10, 1.0)

        # ERL validated step boost (+0.05 per validated step, max +0.15)
        validated = path_metadata.get("validated_steps", 0)
        if validated > 0:
            score = min(score + min(validated * 0.05, 0.15), 1.0)

        score = round(score, 4)
        path.score = score
        path.risk = self._classify(score, path)

        logger.debug(
            "APME Scorer: path=%s score=%.4f risk=%s (sev=%.2f expl=%.2f len=%.2f "
            "impact=%.2f epss=%.2f conf_mult=%.2f)",
            path.id, score, path.risk, severity_score, exploitability,
            length_score, impact_score, epss_score, conf_multiplier,
        )
        return score

    @staticmethod
    def _classify(score: float, path: AttackPath) -> str:
        validated_count = sum(1 for s in path.steps if s.validated)
        if validated_count == 0 and score < 0.40:
            return "speculative"
        if score > 0.85:
            return "critical"
        if score > 0.70:
            return "high"
        if score > 0.50:
            return "medium"
        return "low"

    def sort_paths(self, paths: List[AttackPath]) -> List[AttackPath]:
        """Sort descending by score; speculative paths always last."""
        def sort_key(p: AttackPath):
            return (0 if p.risk == "speculative" else 1, p.score)
        return sorted(paths, key=sort_key, reverse=True)

    def deduplicate(self, paths: List[AttackPath], overlap_threshold: float = 0.75) -> List[AttackPath]:
        """
        Remove paths that share >overlap_threshold of step pairs with a
        higher-scored path already in the output. Also drops paths scoring < 0.15.
        """
        kept = []
        for path in paths:
            if path.score < 0.15:
                continue
            step_pairs = {(s.from_id, s.to_id) for s in path.steps}
            dominated = False
            for kept_path in kept:
                kept_pairs = {(s.from_id, s.to_id) for s in kept_path.steps}
                if not step_pairs:
                    break
                overlap = len(step_pairs & kept_pairs) / len(step_pairs)
                if overlap > overlap_threshold:
                    dominated = True
                    break
            if not dominated:
                kept.append(path)
        return kept
```

- [ ] **Step 8.2 — Write scorer tests (append to `test_apme_phase1.py`)**

```python
from apme.engine.scorer import Scorer
from apme.models.path import AttackPath, PathStep


def _make_path(path_id="P1", steps=None, validated_steps=0):
    steps = steps or []
    p = AttackPath(id=path_id, start="a", end="b", steps=steps)
    for s in steps[:validated_steps]:
        s.validated = True
    return p


def _make_step(from_id="a", to_id="b", confidence=0.8, validated=False):
    s = PathStep(from_id=from_id, to_id=to_id, action="exploit", confidence=confidence)
    s.validated = validated
    return s


class ScorerTests(TestCase):

    def setUp(self):
        self.scorer = Scorer()

    def _base_meta(self, **kwargs):
        defaults = {
            "severity": 3, "cvss_score": 7.5, "privilege_gained": "none",
            "blast_radius": 5, "target_sensitivity": "medium",
            "epss_percentile": 0, "path_confidence_product": 1.0,
            "has_cisa_kev": False, "validated_steps": 0,
        }
        defaults.update(kwargs)
        return defaults

    def test_empty_path_scores_zero(self):
        p = _make_path(steps=[])
        self.scorer.score(p, self._base_meta())
        self.assertEqual(p.score, 0.0)
        self.assertEqual(p.risk, "low")

    def test_epss_boost_increases_score(self):
        p1 = _make_path(steps=[_make_step()])
        p2 = _make_path(path_id="P2", steps=[_make_step()])
        self.scorer.score(p1, self._base_meta(epss_percentile=0))
        self.scorer.score(p2, self._base_meta(epss_percentile=90))
        self.assertGreater(p2.score, p1.score)

    def test_cisa_kev_boost_increases_score(self):
        p1 = _make_path(steps=[_make_step()])
        p2 = _make_path(path_id="P2", steps=[_make_step()])
        self.scorer.score(p1, self._base_meta(has_cisa_kev=False))
        self.scorer.score(p2, self._base_meta(has_cisa_kev=True))
        self.assertAlmostEqual(p2.score, p1.score + 0.10, places=3)

    def test_low_confidence_product_reduces_score(self):
        p1 = _make_path(steps=[_make_step()])
        p2 = _make_path(path_id="P2", steps=[_make_step()])
        self.scorer.score(p1, self._base_meta(path_confidence_product=1.0))
        self.scorer.score(p2, self._base_meta(path_confidence_product=0.5))
        self.assertGreater(p1.score, p2.score)

    def test_zero_validated_steps_low_score_is_speculative(self):
        p = _make_path(steps=[_make_step(confidence=0.3)])
        self.scorer.score(p, self._base_meta(
            severity=1, cvss_score=2.0, epss_percentile=0,
            path_confidence_product=0.3,
        ))
        self.assertEqual(p.risk, "speculative")

    def test_validated_step_prevents_speculative(self):
        step = _make_step(validated=True)
        p = _make_path(steps=[step])
        self.scorer.score(p, self._base_meta(
            severity=1, cvss_score=2.0, validated_steps=1,
        ))
        self.assertNotEqual(p.risk, "speculative")

    def test_deduplication_removes_dominated_path(self):
        s1 = _make_step("a", "b")
        s2 = _make_step("b", "c")
        p1 = _make_path("P1", [s1, s2])
        p1.score = 0.8
        p2 = _make_path("P2", [s1, s2])
        p2.score = 0.5
        result = self.scorer.deduplicate([p1, p2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "P1")

    def test_deduplication_keeps_distinct_paths(self):
        p1 = _make_path("P1", [_make_step("a", "b")])
        p1.score = 0.8
        p2 = _make_path("P2", [_make_step("x", "y")])
        p2.score = 0.5
        result = self.scorer.deduplicate([p1, p2])
        self.assertEqual(len(result), 2)

    def test_score_below_015_dropped_in_dedup(self):
        p = _make_path("P1", [_make_step()])
        p.score = 0.10
        result = self.scorer.deduplicate([p])
        self.assertEqual(len(result), 0)
```

- [ ] **Step 8.3 — Run scorer tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.ScorerTests -v 2"
```

Expected: 9 tests pass.

- [ ] **Step 8.4 — Commit**

```bash
git add web/apme/engine/scorer.py web/tests/test_apme_phase1.py
git commit -m "feat(apme): upgrade scorer with EPSS (0.15w), KEV boost, confidence product multiplier, speculative tier, deduplication"
```

---

## Task 9: Graph Builder — Explicit Constraint Properties on APME_EDGE

**Files:**
- Modify: `web/apme/graph/builder.py`

The builder currently stores `edge.properties` as `str(dict)` — a lossy Python repr. It also doesn't expose constraint flags as individual Neo4j properties that Cypher queries can read. This task fixes both.

- [ ] **Step 9.1 — Replace `_merge_edge` static method in `web/apme/graph/builder.py`**

Replace the entire `_merge_edge` static method:

```python
import json as _json

@staticmethod
def _merge_edge(tx, edge: Edge, scan_id: int) -> bool:
    """
    Create a directed APME_EDGE between two APMENodes.
    Stores mitre_id and all constraint flags as explicit Neo4j properties
    so Cypher path queries can read them directly in rels projections.
    Auto-creates skeleton nodes for missing endpoints.
    """
    def infer_node_type(apme_id: str) -> tuple:
        if apme_id.startswith("domain::"):
            return "Asset", "domain"
        elif apme_id.startswith("ip::"):
            return "Asset", "ip"
        elif apme_id.startswith("service::"):
            return "Asset", "service"
        elif apme_id.startswith("endpoint::"):
            return "Asset", "endpoint"
        elif apme_id.startswith("vuln::"):
            return "Vulnerability", "generic"
        elif apme_id.startswith("tech::"):
            return "Technology", "generic"
        elif apme_id.startswith("credential::"):
            return "Credential", "generic_secret"
        elif apme_id.startswith("goal::capability::"):
            return "Capability", apme_id.split("::")[-1]
        elif apme_id.startswith("goal::privilege::"):
            return "Privilege", apme_id.split("::")[-1]
        return "Asset", "generic"

    from_type, from_subtype = infer_node_type(edge.from_id)
    to_type, to_subtype = infer_node_type(edge.to_id)

    props = edge.properties
    result = tx.run(
        """
        MERGE (a:APMENode {apme_id: $from_id, scan_id: $scan_id})
        ON CREATE SET a.type = $from_type,
                      a.subtype = $from_subtype,
                      a.confidence = 0.5,
                      a.source = "APME:skeleton",
                      a.properties = '{}'

        MERGE (b:APMENode {apme_id: $to_id, scan_id: $scan_id})
        ON CREATE SET b.type = $to_type,
                      b.subtype = $to_subtype,
                      b.confidence = 0.5,
                      b.source = "APME:skeleton",
                      b.properties = '{}'

        MERGE (a)-[r:APME_EDGE {edge_type: $type, scan_id: $scan_id}]->(b)
        SET r.confidence             = $confidence,
            r.properties             = $properties_json,
            r.mitre_id               = $mitre_id,
            r.requires_victim        = $requires_victim,
            r.requires_php           = $requires_php,
            r.requires_java          = $requires_java,
            r.requires_python        = $requires_python,
            r.requires_wordpress     = $requires_wordpress,
            r.endpoint_requires_auth = $endpoint_requires_auth
        RETURN r
        """,
        from_id=edge.from_id,
        to_id=edge.to_id,
        scan_id=scan_id,
        type=edge.type,
        confidence=edge.confidence,
        properties_json=_json.dumps(props),
        mitre_id=props.get("mitre_id", "unknown"),
        requires_victim=bool(props.get("requires_victim", False)),
        requires_php=bool(props.get("requires_php", False)),
        requires_java=bool(props.get("requires_java", False)),
        requires_python=bool(props.get("requires_python", False)),
        requires_wordpress=bool(props.get("requires_wordpress", False)),
        endpoint_requires_auth=bool(props.get("endpoint_requires_auth", False)),
        from_type=from_type,
        from_subtype=from_subtype,
        to_type=to_type,
        to_subtype=to_subtype,
    )
    return result.single() is not None
```

Also add `import json as _json` at the top of the file if not already present.

- [ ] **Step 9.2 — Commit**

```bash
git add web/apme/graph/builder.py
git commit -m "feat(apme): store mitre_id and constraint flags as explicit Neo4j APME_EDGE properties"
```

---

## Task 10: Pathfinder — Dijkstra, Min Confidence, MITRE Propagation

**Files:**
- Modify: `web/apme/engine/pathfinder.py`

- [ ] **Step 10.1 — Replace `web/apme/engine/pathfinder.py` entirely**

```python
"""
APME Pathfinder

Implements graph traversal algorithms against Neo4j to discover
realistic attack paths from entry points to high-value targets.

Phase 1 changes:
- All three Cypher queries return mitre_id and constraint flags in rels projection
- min_edge_confidence parameter filters low-confidence edges before traversal
- find_all_paths now runs BFS + DFS + Dijkstra
- _validate_and_build sets PathStep.mitre_technique and .mitre_tactic
- _edge_to_step_dict reads constraint flags from rel properties
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase
from django.conf import settings

from apme.engine.constraints import ConstraintEngine, PathContext
from apme.models.path import AttackPath, PathStep
from apme.utils.mitre import lookup as mitre_lookup

logger = logging.getLogger(__name__)

INTERNET_ENTRY_SUBTYPES = {"domain", "ip", "service", "endpoint"}
HIGH_VALUE_TARGET_SUBTYPES = {
    "domain_admin", "root", "admin", "db_access", "data_exfil",
    "rce_execution", "cloud_access", "authenticated_access", "pivot",
    "account_takeover", "credential_harvesting", "lateral_movement",
    "metadata_access", "code_exfiltration",
}

# Rels projection shared across all three Cypher queries
_RELS_PROJECTION = """
[r in relationships(path) | {
    type:                 r.edge_type,
    confidence:           r.confidence,
    mitre_id:             r.mitre_id,
    requires_victim:      r.requires_victim,
    requires_php:         r.requires_php,
    requires_java:        r.requires_java,
    requires_python:      r.requires_python,
    requires_wordpress:   r.requires_wordpress,
    endpoint_requires_auth: r.endpoint_requires_auth
}] AS rels
"""

_NODES_PROJECTION = """
[n in nodes(path) | {
    id: n.apme_id, type: n.type, subtype: n.subtype,
    confidence: n.confidence, properties: n.properties
}] AS nodes
"""


class Pathfinder:
    """Discovers attack paths in the Neo4j APME graph."""

    MAX_DEPTH = 8
    MAX_PATHS = 20

    def __init__(self, min_edge_confidence: float = 0.20):
        self.min_edge_confidence = min_edge_confidence
        self._driver = None
        self._constraint_engine = ConstraintEngine()
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        except Exception as exc:
            logger.error("APME Pathfinder: Neo4j connection failed: %s", exc)
            raise

    def close(self):
        if self._driver:
            self._driver.close()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def find_paths_bfs(self, scan_id, start_node_id, target_subtypes=None, top_n=5):
        targets = target_subtypes or list(HIGH_VALUE_TARGET_SUBTYPES)
        raw = self._bfs_query(scan_id, start_node_id, targets)
        return self._validate_and_build(raw, "bfs", top_n)

    def find_paths_dfs(self, scan_id, start_node_id, target_subtypes=None, top_n=5):
        targets = target_subtypes or list(HIGH_VALUE_TARGET_SUBTYPES)
        raw = self._dfs_query(scan_id, start_node_id, targets)
        return self._validate_and_build(raw, "dfs", top_n)

    def find_paths_dijkstra(self, scan_id, start_node_id, target_subtypes=None, top_n=5):
        targets = target_subtypes or list(HIGH_VALUE_TARGET_SUBTYPES)
        raw = self._dijkstra_query(scan_id, start_node_id, targets)
        return self._validate_and_build(raw, "dijkstra", top_n)

    def find_all_paths(self, scan_id, start_node_ids=None, target_subtypes=None, top_n=5):
        """Runs BFS + DFS + Dijkstra across all entry points, deduplicates, returns top N."""
        entries = start_node_ids or self._get_internet_entry_points(scan_id)
        all_paths: List[AttackPath] = []

        for entry_id in entries:
            all_paths.extend(self.find_paths_bfs(scan_id, entry_id, target_subtypes, top_n))
            all_paths.extend(self.find_paths_dfs(scan_id, entry_id, target_subtypes, top_n))
            all_paths.extend(self.find_paths_dijkstra(scan_id, entry_id, target_subtypes, top_n))

        seen = set()
        unique = []
        for p in all_paths:
            key = "->".join(s.from_id + s.to_id for s in p.steps)
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return sorted(unique, key=lambda p: len(p.steps))[:top_n]

    # -------------------------------------------------------------------------
    # Neo4j Queries
    # -------------------------------------------------------------------------

    def _bfs_query(self, scan_id, start_id, target_subtypes):
        query = f"""
            MATCH path = shortestPath(
                (start:APMENode {{apme_id: $start_id, scan_id: $scan_id}})
                -[:APME_EDGE*1..{self.MAX_DEPTH}]->
                (target:APMENode)
            )
            WHERE target.subtype IN $target_subtypes
              AND target.scan_id = $scan_id
              AND ALL(r IN relationships(path) WHERE r.confidence >= $min_conf)
            RETURN {_NODES_PROJECTION}, {_RELS_PROJECTION}
            LIMIT $limit
        """
        return self._run_path_query(query, scan_id, start_id, target_subtypes)

    def _dfs_query(self, scan_id, start_id, target_subtypes):
        query = f"""
            MATCH path = (start:APMENode {{apme_id: $start_id, scan_id: $scan_id}})
                -[:APME_EDGE*1..{self.MAX_DEPTH}]->
                (target:APMENode)
            WHERE target.subtype IN $target_subtypes
              AND target.scan_id = $scan_id
              AND ALL(r IN relationships(path) WHERE r.confidence >= $min_conf)
            RETURN {_NODES_PROJECTION}, {_RELS_PROJECTION}
            LIMIT $limit
        """
        return self._run_path_query(query, scan_id, start_id, target_subtypes)

    def _dijkstra_query(self, scan_id, start_id, target_subtypes):
        query = """
            MATCH (start:APMENode {apme_id: $start_id, scan_id: $scan_id}),
                  (target:APMENode {scan_id: $scan_id})
            WHERE target.subtype IN $target_subtypes
            CALL apoc.algo.dijkstra(start, target, 'APME_EDGE', 'cost') YIELD path, weight
            WHERE ALL(r IN relationships(path) WHERE r.confidence >= $min_conf)
            RETURN """ + _NODES_PROJECTION + ", " + _RELS_PROJECTION + """
            LIMIT $limit
        """
        try:
            return self._run_path_query(query, scan_id, start_id, target_subtypes)
        except Exception:
            logger.warning("APME Pathfinder: APOC Dijkstra unavailable, falling back to BFS.")
            return self._bfs_query(scan_id, start_id, target_subtypes)

    def _run_path_query(self, query, scan_id, start_id, target_subtypes):
        results = []
        if not self._driver:
            return results
        try:
            with self._driver.session() as session:
                records = session.run(
                    query,
                    scan_id=scan_id,
                    start_id=start_id,
                    target_subtypes=target_subtypes,
                    min_conf=self.min_edge_confidence,
                    limit=self.MAX_PATHS,
                )
                for record in records:
                    results.append({"nodes": record["nodes"], "rels": record["rels"]})
        except Exception as exc:
            logger.error("APME Pathfinder: Query failed: %s", exc)
        return results

    def _get_internet_entry_points(self, scan_id):
        if not self._driver:
            return []
        with self._driver.session() as session:
            result = session.run(
                "MATCH (n:APMENode) WHERE n.subtype IN $subtypes AND n.scan_id = $scan_id RETURN n.apme_id AS id",
                subtypes=list(INTERNET_ENTRY_SUBTYPES),
                scan_id=scan_id,
            )
            return [r["id"] for r in result]

    # -------------------------------------------------------------------------
    # Path Construction & Validation
    # -------------------------------------------------------------------------

    def _validate_and_build(self, raw_paths, algorithm, top_n):
        validated = []
        for raw in raw_paths:
            nodes = raw.get("nodes", [])
            rels = raw.get("rels", [])
            if len(nodes) < 2:
                continue

            steps = []
            context = PathContext()
            valid = True

            for i, rel in enumerate(rels):
                from_node = nodes[i]
                to_node = nodes[i + 1]
                edge_type = rel.get("type", "")
                confidence = float(rel.get("confidence") or 0.5)

                step_dict = self._edge_to_step_dict(edge_type, from_node, to_node, confidence, rel)

                if not self._constraint_engine.validate_step(step_dict, context):
                    valid = False
                    break

                self._constraint_engine.update_context(step_dict, context)

                mitre_id = rel.get("mitre_id") or ""
                mitre_info = mitre_lookup(mitre_id) if mitre_id and mitre_id != "unknown" else {}

                steps.append(PathStep(
                    from_id=from_node.get("id", ""),
                    to_id=to_node.get("id", ""),
                    action=self._edge_to_action(edge_type, from_node, to_node),
                    confidence=confidence,
                    validated=step_dict.get("validated", False),
                    edge_type=edge_type,
                    mitre_technique=mitre_id if mitre_id != "unknown" else "",
                    mitre_tactic=mitre_info.get("tactic_slug", ""),
                ))

            if valid and steps:
                path = AttackPath(
                    id=f"APT-{uuid.uuid4().hex[:6].upper()}",
                    start=nodes[0].get("id", ""),
                    end=nodes[-1].get("id", ""),
                    steps=steps,
                    entry_type="internet",
                )
                validated.append(path)

        return validated[:top_n]

    @staticmethod
    def _edge_to_step_dict(edge_type, from_node, to_node, confidence, rel=None):
        """Map an edge type + rel properties to a step dict for the ConstraintEngine."""
        rel = rel or {}
        step: Dict[str, Any] = {
            "action":               edge_type,
            "confidence":           confidence,
            "validated":            False,
            "to_id":                to_node.get("id", ""),
            "to_subtype":           to_node.get("subtype", ""),
            "requires_auth":        False,
            "requires_internal":    False,
            "requires_privilege":   "none",
            "grants_auth":          False,
            "grants_internal":      False,
            "grants_privilege":     None,
            # Phase 1 constraint flags — read from Neo4j rel properties
            "requires_victim":      bool(rel.get("requires_victim", False)),
            "requires_php":         bool(rel.get("requires_php", False)),
            "requires_java":        bool(rel.get("requires_java", False)),
            "requires_python":      bool(rel.get("requires_python", False)),
            "requires_wordpress":   bool(rel.get("requires_wordpress", False)),
            "endpoint_requires_auth": bool(rel.get("endpoint_requires_auth", False)),
        }

        if edge_type == "AUTHENTICATES":
            step["grants_auth"] = True
        elif edge_type == "CONNECTED_TO":
            step["grants_internal"] = True
        elif edge_type == "ESCALATES_TO":
            step["grants_privilege"] = to_node.get("subtype", "user")
        elif edge_type == "USES_TECH":
            # Technology traversal propagates tech context via to_subtype
            pass
        elif edge_type == "LEADS_TO":
            if to_node.get("subtype") in {"pivot", "data_exfil", "lateral_movement"}:
                step["requires_internal"] = True

        return step

    @staticmethod
    def _edge_to_action(edge_type, from_node, to_node):
        templates = {
            "RESOLVES_TO":  "Resolve {src} to IP {dst}",
            "HOSTS":        "{src} hosts service {dst}",
            "EXPOSES":      "Service {src} exposes vulnerability {dst}",
            "LEADS_TO":     "Exploit {src} to gain {dst}",
            "AUTHENTICATES":"Use credential {src} to authenticate to {dst}",
            "ESCALATES_TO": "Escalate from {src} to {dst}",
            "TRUSTS":       "{src} trusts {dst} — lateral movement possible",
            "CONNECTED_TO": "Pivot via {src} to reach {dst}",
            "USES_TECH":    "{src} runs {dst}",
        }
        tpl = templates.get(edge_type, "{src} -> {dst}")
        return tpl.format(
            src=from_node.get("subtype", from_node.get("id", "?")),
            dst=to_node.get("subtype", to_node.get("id", "?")),
        )
```

- [ ] **Step 10.2 — Commit**

```bash
git add web/apme/engine/pathfinder.py
git commit -m "feat(apme): pathfinder — Dijkstra in find_all_paths, min_edge_confidence filter, MITRE technique propagation to PathStep, constraint flags from Neo4j rels"
```

---

## Task 11: Orchestrator & Serializer Updates

**Files:**
- Modify: `web/apme/orchestrator.py`
- Modify: `web/apme/output/serializer.py`

- [ ] **Step 11.1 — Update `APMEOrchestrator.run()` in `web/apme/orchestrator.py`**

In the `run()` method, add technology ingestion after the existing ingestion calls (around line 63):

```python
        # Add technology ingestion (Phase 1)
        from apme.ingestion.assets import ingest_technologies
        tech_nodes, tech_edges = ingest_technologies(target_id)
        all_nodes.extend(tech_nodes)
        all_edges.extend(tech_edges)
```

Update `_build_path_metadata` to include EPSS, KEV, and confidence product (add after the existing `blast_radius` block):

```python
        # EPSS: max across all vulnerability steps
        epss_percentile = 0.0
        has_cisa_kev = False
        path_confidence_product = 1.0

        for step in path.steps:
            path_confidence_product *= step.confidence
            to_node = node_index.get(step.to_id)
            if to_node and to_node.type == "Vulnerability":
                # Try to read from pre-enriched properties (set by CVE enrichment)
                epss_val = to_node.properties.get("epss_percentile", 0.0) or 0.0
                if epss_val > epss_percentile:
                    epss_percentile = epss_val
                if to_node.properties.get("is_cisa_kev"):
                    has_cisa_kev = True
```

And add these to the returned metadata dict:
```python
        return {
            ...existing keys...,
            "epss_percentile":          epss_percentile,
            "has_cisa_kev":             has_cisa_kev,
            "path_confidence_product":  min(max(path_confidence_product, 0.0), 1.0),
        }
```

Also update the `scored_paths` pipeline to call deduplication after scoring (after `scored_paths = self._scorer.sort_paths(paths)`):

```python
        scored_paths = self._scorer.deduplicate(scored_paths)
        scored_paths = self._scorer.sort_paths(scored_paths)
```

- [ ] **Step 11.2 — Replace `web/apme/output/serializer.py` entirely**

```python
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
    """Serialize a single AttackPath to canonical output format."""
    steps = []
    all_techniques = []
    all_tactics = []

    for step in path.steps:
        mitre_info = mitre_lookup(step.mitre_technique) if step.mitre_technique else {}

        step_dict = {
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


def _serialize_node(node) -> Dict[str, Any]:
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


def serialize_paths(paths: List[AttackPath], node_index: Dict[str, Any] = None, top_n: int = 5) -> Dict[str, Any]:
    """Serialize top N paths into the canonical output envelope."""
    top = paths[:top_n]
    serialized = [serialize_path(p, node_index) for p in top]
    confirmed = [p for p in serialized if p["risk"] != "speculative"]
    speculative = [p for p in serialized if p["risk"] == "speculative"]
    return {
        "total_paths":      len(paths),
        "returned_paths":   len(top),
        "paths":            confirmed,
        "speculative_paths": speculative,
    }


def to_json(paths: List[AttackPath], top_n: int = 5, indent: int = 2) -> str:
    return json.dumps(serialize_paths(paths, top_n=top_n), indent=indent)
```

- [ ] **Step 11.3 — Write serializer tests (append to `test_apme_phase1.py`)**

```python
from apme.output.serializer import serialize_path, serialize_paths
from apme.models.path import AttackPath, PathStep


class SerializerTests(TestCase):

    def _make_path_with_mitre(self):
        step = PathStep(
            from_id="vuln::1", to_id="goal::capability::rce_execution",
            action="Exploit RCE", confidence=0.90, validated=True,
            edge_type="LEADS_TO", mitre_technique="T1190", mitre_tactic="initial-access",
        )
        p = AttackPath(id="APT-TEST1", start="vuln::1", end="goal::capability::rce_execution",
                       steps=[step], score=0.85, risk="high")
        return p

    def test_serialize_path_includes_mitre_technique(self):
        p = self._make_path_with_mitre()
        result = serialize_path(p)
        step_dict = result["steps"][0]
        self.assertEqual(step_dict["mitre_technique"], "T1190")
        self.assertEqual(step_dict["mitre_technique_name"], "Exploit Public-Facing Application")
        self.assertEqual(step_dict["mitre_tactic_display"], "Initial Access")
        self.assertEqual(step_dict["mitre_tactic_color"], "#ff4444")

    def test_serialize_path_includes_techniques_summary(self):
        p = self._make_path_with_mitre()
        result = serialize_path(p)
        self.assertIn("T1190", result["mitre_techniques"])
        self.assertIn("initial-access", result["mitre_tactics"])

    def test_serialize_paths_separates_speculative(self):
        p1 = self._make_path_with_mitre()
        p1.risk = "high"
        p2 = AttackPath(id="APT-TEST2", start="a", end="b",
                        steps=[PathStep("a", "b", "x", confidence=0.3)],
                        score=0.20, risk="speculative")
        result = serialize_paths([p1, p2])
        self.assertEqual(len(result["paths"]), 1)
        self.assertEqual(len(result["speculative_paths"]), 1)
        self.assertEqual(result["paths"][0]["path_id"], "APT-TEST1")

    def test_node_dict_includes_cwe_and_technique(self):
        from apme.models.node import Node
        from apme.output.serializer import _serialize_node
        node = Node(id="vuln::1", type="Vulnerability", subtype="sqli",
                    confidence=0.9, source="test",
                    properties={"cwe": "CWE-89", "technique": "T1190", "name": "SQLi",
                                "severity": 3, "cvss_score": 7.5, "vuln_id": 1})
        d = _serialize_node(node)
        self.assertEqual(d["cwe"], "CWE-89")
        self.assertEqual(d["technique"], "T1190")
```

- [ ] **Step 11.4 — Run serializer tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1.SerializerTests -v 2"
```

Expected: 4 tests pass.

- [ ] **Step 11.5 — Commit**

```bash
git add web/apme/orchestrator.py web/apme/output/serializer.py web/tests/test_apme_phase1.py
git commit -m "feat(apme): orchestrator adds tech ingestion + EPSS/KEV metadata; serializer adds MITRE fields and speculative_paths envelope"
```

---

## Task 12: Full Test Run & Phase 1 Tag

- [ ] **Step 12.1 — Run the complete Phase 1 test suite**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase1 -v 2"
```

Expected: all tests pass (target: 60+ assertions across 8 test classes).

- [ ] **Step 12.2 — Run the full existing test suite to check for regressions**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -5"
```

Expected: no new failures.

- [ ] **Step 12.3 — Tag Phase 1 complete**

```bash
git tag apme-phase1-complete
git push origin apme-enhancement --tags
```

---

**Phase 1 complete.** Proceed to [Phase 2 plan](2026-06-13-apme-phase2-rules.md) for the 72-rule YAML expansion.
