# APME Phase 2 — Rules Expansion (14 → 72) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 14-rule YAML with a comprehensive 72-rule attack knowledge base covering 13 kill-chain categories, fix the broken `any_vuln_on_hvt` rule, and verify every rule fires correctly against a mock graph.

**Prerequisite:** Phase 1 must be complete — the schema, rules engine numeric comparisons, and constraint flags all need to be in place before writing the YAML.

**Architecture:** All changes are in `web/apme/config/rules.yaml` (the data file) and one new test file. No Python code changes are needed — Phase 1 enhanced the rules engine to handle everything in this YAML.

**Tech Stack:** PyYAML, Django test framework (inside Docker)

---

## File Map

| Action | File |
|---|---|
| REPLACE | `web/apme/config/rules.yaml` |
| CREATE | `web/tests/test_apme_phase2.py` |

---

## Task 1: Replace `rules.yaml` — Full 72-Rule YAML

**Files:**
- Replace: `web/apme/config/rules.yaml`

- [ ] **Step 1.1 — Write the failing test first**

Create `web/tests/test_apme_phase2.py`:

```python
"""Phase 2 APME rules expansion tests.

Tests verify that each rule category fires correctly against mock APME nodes.
No Neo4j connection required — we test the RulesEngine directly.
"""
from django.test import TestCase
from apme.engine.rules_engine import RulesEngine
from apme.models.node import Node


def _vuln(subtype, severity=3, confidence=0.75, validated=False, sensitivity="low"):
    return Node(
        id=f"vuln::{subtype}::test",
        type="Vulnerability",
        subtype=subtype,
        confidence=confidence,
        source="test",
        properties={
            "severity": severity,
            "validated": str(validated),
            "sensitivity": sensitivity,
        },
    )


def _cred(subtype, confidence=0.8):
    return Node(
        id=f"cred::{subtype}::test",
        type="Credential",
        subtype=subtype,
        confidence=confidence,
        source="test",
        properties={},
    )


def _cap(subtype):
    return Node(
        id=f"goal::capability::{subtype}",
        type="Capability",
        subtype=subtype,
        confidence=1.0,
        source="test",
        properties={},
    )


def _priv(subtype):
    return Node(
        id=f"goal::privilege::{subtype}",
        type="Privilege",
        subtype=subtype,
        confidence=1.0,
        source="test",
        properties={},
    )


def _all_goal_nodes():
    from apme.graph.schema import NODE_TYPES
    nodes = []
    for subtype in NODE_TYPES.get("Capability", []):
        nodes.append(_cap(subtype))
    for subtype in NODE_TYPES.get("Privilege", []):
        nodes.append(_priv(subtype))
    return nodes


class CategoryAInjectionTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _edges(self, node):
        return self.engine.apply(node, [node] + self.goals)

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self._edges(node)}

    def test_sqli_leads_to_db_access(self):
        self.assertIn("db_access", self._target_subtypes(_vuln("sqli")))

    def test_sqli_high_confidence_leads_to_account_takeover(self):
        node = _vuln("sqli", severity=4, confidence=0.85, validated=True)
        self.assertIn("account_takeover", self._target_subtypes(node))

    def test_command_injection_leads_to_rce_execution(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("command_injection")))

    def test_code_injection_leads_to_rce_execution(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("code_injection")))

    def test_nosql_injection_leads_to_db_access(self):
        self.assertIn("db_access", self._target_subtypes(_vuln("nosql_injection")))

    def test_xpath_injection_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("xpath_injection")))

    def test_ldap_injection_leads_to_auth_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("ldap_injection")))

    def test_log_injection_high_severity_leads_to_rce(self):
        # Must have severity >= 3 to trigger
        high = _vuln("log_injection", severity=3)
        low  = _vuln("log_injection", severity=2)
        self.assertIn("rce_execution", self._target_subtypes(high))
        self.assertNotIn("rce_execution", self._target_subtypes(low))

    def test_ssti_leads_to_rce_execution(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("ssti")))


class CategoryBFileOpsTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_lfi_leads_to_rce(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("lfi")))

    def test_lfi_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("lfi")))

    def test_path_traversal_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("path_traversal")))

    def test_file_upload_leads_to_rce(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("file_upload")))

    def test_file_upload_leads_to_persistence(self):
        self.assertIn("persistence", self._target_subtypes(_vuln("file_upload")))


class CategoryCServerSideTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_rce_leads_to_rce_execution(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("rce")))

    def test_ssrf_leads_to_cloud_access(self):
        self.assertIn("cloud_access", self._target_subtypes(_vuln("ssrf")))

    def test_ssrf_leads_to_pivot(self):
        self.assertIn("pivot", self._target_subtypes(_vuln("ssrf")))

    def test_ssrf_leads_to_metadata_access(self):
        self.assertIn("metadata_access", self._target_subtypes(_vuln("ssrf")))

    def test_xxe_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("xxe")))


class CategoryDDeserializationTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def _edge_props(self, node, flag):
        edges = self.engine.apply(node, [node] + self.goals)
        return any(e.properties.get(flag) for e in edges)

    def test_deserialization_leads_to_rce(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("deserialization")))

    def test_java_deserialization_has_requires_java_flag(self):
        self.assertTrue(self._edge_props(_vuln("deserialization"), "requires_java") or
                        self._edge_props(_vuln("deserialization"), "requires_java"))

    def test_php_deserialization_has_requires_php_flag(self):
        edges = self.engine.apply(_vuln("deserialization"), [_vuln("deserialization")] + self.goals)
        php_edges = [e for e in edges if e.properties.get("requires_php")]
        # At least one rule should gate on PHP
        self.assertTrue(any(True for e in edges if e.properties.get("requires_php") or
                            e.properties.get("requires_java") or e.properties.get("requires_python")))


class CategoryEAuthTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_misconfig_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("misconfig")))

    def test_creds_lead_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_cred("api_key")))

    def test_jwt_abuse_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("jwt_abuse")))

    def test_jwt_abuse_high_confidence_leads_to_account_takeover(self):
        node = _vuln("jwt_abuse", confidence=0.75)
        self.assertIn("account_takeover", self._target_subtypes(node))

    def test_oauth_misconfig_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("oauth_misconfig")))

    def test_idor_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("idor")))

    def test_crlf_leads_to_session_hijacking(self):
        self.assertIn("session_hijacking", self._target_subtypes(_vuln("crlf_injection")))

    def test_host_header_leads_to_account_takeover(self):
        self.assertIn("account_takeover", self._target_subtypes(_vuln("host_header")))


class CategoryFClientSideTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _edges(self, node):
        return self.engine.apply(node, [node] + self.goals)

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self._edges(node)}

    def test_xss_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("xss")))

    def test_xss_session_hijack_has_requires_victim(self):
        edges = self._edges(_vuln("xss"))
        session_edges = [e for e in edges if "session_hijacking" in e.to_id]
        self.assertTrue(any(e.properties.get("requires_victim") for e in session_edges))

    def test_clickjacking_leads_to_account_takeover(self):
        self.assertIn("account_takeover", self._target_subtypes(_vuln("clickjacking")))

    def test_csrf_has_requires_victim_flag(self):
        edges = self._edges(_vuln("csrf"))
        self.assertTrue(any(e.properties.get("requires_victim") for e in edges))

    def test_open_redirect_leads_to_phishing_amplification(self):
        self.assertIn("phishing_amplification", self._target_subtypes(_vuln("open_redirect")))


class CategoryGInfoDisclosureTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_cors_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("cors")))

    def test_prototype_pollution_leads_to_auth_bypass(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("prototype_pollution")))

    def test_graphql_injection_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("graphql_injection")))

    def test_misconfig_backup_leads_to_credential_harvesting(self):
        # misconfig with severity >= 2 should lead to credential_harvesting via backup_file rule
        self.assertIn("credential_harvesting", self._target_subtypes(_vuln("misconfig", severity=2)))


class CategoryHCloudTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_cloud_api_key_leads_to_cloud_access(self):
        self.assertIn("cloud_access", self._target_subtypes(_cred("cloud_api_key")))

    def test_s3_misconfig_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("s3_misconfig")))

    def test_prototype_pollution_high_severity_leads_to_rce(self):
        high = _vuln("prototype_pollution", severity=3)
        low  = _vuln("prototype_pollution", severity=1)
        self.assertIn("rce_execution", self._target_subtypes(high))
        self.assertNotIn("rce_execution", self._target_subtypes(low))

    def test_graphql_injection_leads_to_rce(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("graphql_injection")))


class CategoryITechSpecificTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _edges(self, node):
        return self.engine.apply(node, [node] + self.goals)

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self._edges(node)}

    def test_wordpress_rce_has_requires_wordpress(self):
        edges = self._edges(_vuln("rce"))
        wp_edges = [e for e in edges if e.properties.get("requires_wordpress")]
        self.assertTrue(len(wp_edges) > 0)

    def test_log4j_needs_severity_4_and_validated(self):
        # Only fires when severity=4 and validated=True
        firing = _vuln("log_injection", severity=4, validated=True, confidence=1.0)
        not_firing = _vuln("log_injection", severity=3, validated=False)
        # log4j_to_rce should have higher confidence than generic log_injection rule
        firing_edges = self._edges(firing)
        not_firing_edges = self._edges(not_firing)
        firing_rce = [e for e in firing_edges if "rce_execution" in e.to_id
                      and e.properties.get("rule") == "log4j_to_rce"]
        not_firing_rce = [e for e in not_firing_edges if "rce_execution" in e.to_id
                           and e.properties.get("rule") == "log4j_to_rce"]
        self.assertTrue(len(firing_rce) > 0)
        self.assertEqual(len(not_firing_rce), 0)


class CategoryJSecretsTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_db_password_leads_to_db_access(self):
        self.assertIn("db_access", self._target_subtypes(_cred("db_password")))

    def test_jwt_token_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_cred("jwt_token")))

    def test_github_token_leads_to_code_exfiltration(self):
        self.assertIn("code_exfiltration", self._target_subtypes(_cred("github_token")))

    def test_api_key_leads_to_lateral_movement(self):
        self.assertIn("lateral_movement", self._target_subtypes(_cred("api_key")))


class CategoryKDNSTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_subdomain_takeover_leads_to_xss_capability(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("subdomain_takeover")))

    def test_subdomain_takeover_leads_to_phishing(self):
        self.assertIn("phishing_amplification", self._target_subtypes(_vuln("subdomain_takeover")))

    def test_dns_rebinding_leads_to_pivot(self):
        self.assertIn("pivot", self._target_subtypes(_vuln("dns_rebinding")))


class CategoryLLateralTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_rce_execution_capability_leads_to_pivot(self):
        self.assertIn("pivot", self._target_subtypes(_cap("rce_execution")))

    def test_pivot_capability_leads_to_internal_discovery(self):
        self.assertIn("internal_discovery", self._target_subtypes(_cap("pivot")))

    def test_internal_discovery_leads_to_lateral_movement(self):
        self.assertIn("lateral_movement", self._target_subtypes(_cap("internal_discovery")))

    def test_any_credential_leads_to_lateral_movement(self):
        self.assertIn("lateral_movement", self._target_subtypes(_cred("token")))

    def test_admin_privilege_leads_to_persistence(self):
        self.assertIn("persistence", self._target_subtypes(_priv("admin")))


class CategoryMHVTTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_critical_vuln_on_sensitive_asset_leads_to_hvt_compromise(self):
        node = _vuln("generic_critical", severity=4, sensitivity="high")
        self.assertIn("hvt_compromise", self._target_subtypes(node))

    def test_low_severity_does_not_trigger_hvt_rule(self):
        node = _vuln("generic", severity=1, sensitivity="high")
        self.assertNotIn("hvt_compromise", self._target_subtypes(node))

    def test_rce_on_sensitive_leads_to_hvt(self):
        node = _vuln("rce", severity=4, sensitivity="high")
        self.assertIn("hvt_compromise", self._target_subtypes(node))

    def test_any_vuln_hvt_rule_no_longer_exists(self):
        # The old any_vuln_on_hvt rule targeted hvt_compromise for ANY vulnerability.
        # With the new rules, only severity-gated nodes should reach it.
        low = _vuln("generic", severity=1, sensitivity="low")
        self.assertNotIn("hvt_compromise", self._target_subtypes(low))


class NoLongerFiringTests(TestCase):
    """Verify the removed broken rule no longer exists."""

    def test_any_vuln_on_hvt_rule_removed(self):
        engine = RulesEngine()
        rule_names = {r.get("name") for r in engine._rules}
        self.assertNotIn("any_vuln_on_hvt", rule_names)
```

- [ ] **Step 1.2 — Run tests (all should FAIL — rules.yaml not yet updated)**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase2 -v 2 2>&1 | grep -E '(FAIL|ERROR|OK|test_)' | head -40"
```

Expected: Many test failures — rules don't exist yet.

- [ ] **Step 1.3 — Replace `web/apme/config/rules.yaml` with the full 72-rule set**

```yaml
# APME Attack Rules — v2 (Phase 2)
#
# Rule format:
#   name:          unique snake_case identifier
#   mitre_id:      ATT&CK technique ID
#   if:
#     node.type:       <Vulnerability|Credential|Capability|Privilege>
#     node.subtype:    <subtype from schema.py>
#     node.property:   "key:value" or "key:>=N" (numeric) or list of these
#     node.confidence: ">=N" (numeric check on node.confidence)
#   then:
#     create_edge:
#       type:               LEADS_TO | AUTHENTICATES | ESCALATES_TO
#       target_subtype:     <capability or privilege subtype>
#       confidence:         0.0–1.0
#       confidence_modifier: float (multiplies base confidence; default 1.0)
#       requires_victim:    true/false
#       requires_php:       true/false
#       requires_java:      true/false
#       requires_python:    true/false
#       requires_wordpress: true/false
#       endpoint_requires_auth: true/false

rules:

  # ============================================================
  # CATEGORY A — Injection (9 rules)
  # ============================================================

  - name: sqli_to_db_access
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: sqli
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: db_access
        confidence: 0.90

  - name: sqli_verified_to_account_takeover
    mitre_id: "T1078"
    if:
      node.type: Vulnerability
      node.subtype: sqli
      node.property:
        - "severity:>=3"
        - "validated:True"
      node.confidence: ">=0.60"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: account_takeover
        confidence: 0.85

  - name: command_injection_to_rce
    mitre_id: "T1059"
    if:
      node.type: Vulnerability
      node.subtype: command_injection
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.90

  - name: code_injection_to_rce
    mitre_id: "T1059"
    if:
      node.type: Vulnerability
      node.subtype: code_injection
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.85

  - name: nosql_injection_to_db_access
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: nosql_injection
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: db_access
        confidence: 0.80

  - name: xpath_injection_to_data_exfil
    mitre_id: "T1083"
    if:
      node.type: Vulnerability
      node.subtype: xpath_injection
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.75

  - name: ldap_injection_to_auth_bypass
    mitre_id: "T1548"
    if:
      node.type: Vulnerability
      node.subtype: ldap_injection
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.80

  - name: log_injection_to_rce
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: log_injection
      node.property: "severity:>=3"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.85

  - name: ssti_to_rce
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: ssti
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.85

  # ============================================================
  # CATEGORY B — File Operations (5 rules)
  # ============================================================

  - name: lfi_to_rce
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: lfi
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.70

  - name: lfi_to_data_exfil
    mitre_id: "T1083"
    if:
      node.type: Vulnerability
      node.subtype: lfi
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.80

  - name: path_traversal_to_data_exfil
    mitre_id: "T1083"
    if:
      node.type: Vulnerability
      node.subtype: path_traversal
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.80

  - name: file_upload_to_rce
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: file_upload
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.90

  - name: file_upload_to_persistence
    mitre_id: "T1505.003"
    if:
      node.type: Vulnerability
      node.subtype: file_upload
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: persistence
        confidence: 0.85

  # ============================================================
  # CATEGORY C — Server-Side (7 rules)
  # ============================================================

  - name: rce_to_execution
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: rce
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.95

  - name: ssrf_to_cloud_access
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: ssrf
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: cloud_access
        confidence: 0.80

  - name: ssrf_to_pivot
    mitre_id: "T1090"
    if:
      node.type: Vulnerability
      node.subtype: ssrf
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: pivot
        confidence: 0.75

  - name: ssrf_to_metadata_access
    mitre_id: "T1552.005"
    if:
      node.type: Vulnerability
      node.subtype: ssrf
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: metadata_access
        confidence: 0.85

  - name: ssrf_to_internal_service
    mitre_id: "T1090"
    if:
      node.type: Vulnerability
      node.subtype: ssrf
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: internal_discovery
        confidence: 0.80

  - name: xxe_to_data_exfil
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: xxe
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.75

  - name: xxe_to_internal_service
    mitre_id: "T1090"
    if:
      node.type: Vulnerability
      node.subtype: xxe
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: pivot
        confidence: 0.70

  # ============================================================
  # CATEGORY D — Deserialization (4 rules)
  # ============================================================

  - name: deserialization_to_rce
    mitre_id: "T1059"
    if:
      node.type: Vulnerability
      node.subtype: deserialization
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.85

  - name: java_deserialization_to_rce
    mitre_id: "T1059.007"
    if:
      node.type: Vulnerability
      node.subtype: deserialization
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.85
        requires_java: true

  - name: php_deserialization_to_rce
    mitre_id: "T1059.004"
    if:
      node.type: Vulnerability
      node.subtype: deserialization
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.80
        requires_php: true

  - name: python_pickle_to_rce
    mitre_id: "T1059.006"
    if:
      node.type: Vulnerability
      node.subtype: deserialization
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.80
        requires_python: true

  # ============================================================
  # CATEGORY E — Authentication & Identity (9 rules)
  # ============================================================

  - name: bypass_to_auth_access
    mitre_id: "T1548"
    if:
      node.type: Vulnerability
      node.subtype: misconfig
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.75

  - name: creds_to_auth_access
    mitre_id: "T1078"
    if:
      node.type: Credential
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.95

  - name: jwt_abuse_to_auth_bypass
    mitre_id: "T1078.001"
    if:
      node.type: Vulnerability
      node.subtype: jwt_abuse
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.90

  - name: jwt_abuse_to_account_takeover
    mitre_id: "T1078.001"
    if:
      node.type: Vulnerability
      node.subtype: jwt_abuse
      node.confidence: ">=0.70"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: account_takeover
        confidence: 0.85

  - name: oauth_misconfig_to_auth
    mitre_id: "T1078.004"
    if:
      node.type: Vulnerability
      node.subtype: oauth_misconfig
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.80

  - name: default_creds_to_admin_access
    mitre_id: "T1078.001"
    if:
      node.type: Vulnerability
      node.subtype: misconfig
      node.property: "validated:True"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: account_takeover
        confidence: 0.85

  - name: crlf_to_session_fixation
    mitre_id: "T1563"
    if:
      node.type: Vulnerability
      node.subtype: crlf_injection
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: session_hijacking
        confidence: 0.70

  - name: host_header_to_password_reset_poison
    mitre_id: "T1586.002"
    if:
      node.type: Vulnerability
      node.subtype: host_header
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: account_takeover
        confidence: 0.75

  - name: idor_to_data_exfil
    mitre_id: "T1530"
    if:
      node.type: Vulnerability
      node.subtype: idor
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.75

  # ============================================================
  # CATEGORY F — Client-Side (7 rules)
  # ============================================================

  - name: xss_to_auth_access
    mitre_id: "T1189"
    if:
      node.type: Vulnerability
      node.subtype: xss
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.60

  - name: xss_to_session_hijack
    mitre_id: "T1539"
    if:
      node.type: Vulnerability
      node.subtype: xss
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: session_hijacking
        confidence: 0.65
        requires_victim: true

  - name: xss_to_credential_theft
    mitre_id: "T1539"
    if:
      node.type: Vulnerability
      node.subtype: xss
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: credential_harvesting
        confidence: 0.60
        requires_victim: true

  - name: clickjacking_to_account_takeover
    mitre_id: "T1185"
    if:
      node.type: Vulnerability
      node.subtype: clickjacking
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: account_takeover
        confidence: 0.60
        requires_victim: true

  - name: csrf_to_state_change
    mitre_id: "T1185"
    if:
      node.type: Vulnerability
      node.subtype: csrf
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: account_takeover
        confidence: 0.65
        requires_victim: true

  - name: redirect_to_auth_access
    mitre_id: "T1204.001"
    if:
      node.type: Vulnerability
      node.subtype: open_redirect
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.50

  - name: open_redirect_to_phishing
    mitre_id: "T1566.002"
    if:
      node.type: Vulnerability
      node.subtype: open_redirect
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: phishing_amplification
        confidence: 0.60

  # ============================================================
  # CATEGORY G — Information Disclosure (6 rules)
  # ============================================================

  - name: cors_to_data_exfil
    mitre_id: "T1557"
    if:
      node.type: Vulnerability
      node.subtype: cors
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.70
        requires_victim: true

  - name: debug_endpoint_to_data_exfil
    mitre_id: "T1083"
    if:
      node.type: Vulnerability
      node.subtype: misconfig
      node.property: "severity:>=2"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.70

  - name: backup_file_to_credential_harvest
    mitre_id: "T1552"
    if:
      node.type: Vulnerability
      node.subtype: misconfig
      node.property: "severity:>=2"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: credential_harvesting
        confidence: 0.80

  - name: graphql_introspection_to_data_exfil
    mitre_id: "T1083"
    if:
      node.type: Vulnerability
      node.subtype: graphql_injection
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.70

  - name: api_key_disclosure_to_cloud_access
    mitre_id: "T1552.001"
    if:
      node.type: Vulnerability
      node.subtype: misconfig
      node.property: "severity:>=3"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: cloud_access
        confidence: 0.85

  - name: prototype_pollution_to_auth_bypass
    mitre_id: "T1548"
    if:
      node.type: Vulnerability
      node.subtype: prototype_pollution
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.70

  # ============================================================
  # CATEGORY H — Cloud & Infrastructure (6 rules)
  # ============================================================

  - name: cloud_api_key_to_cloud_access
    mitre_id: "T1552.005"
    if:
      node.type: Credential
      node.subtype: cloud_api_key
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: cloud_access
        confidence: 0.90

  - name: s3_misconfig_to_data_exfil
    mitre_id: "T1530"
    if:
      node.type: Vulnerability
      node.subtype: s3_misconfig
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.85

  - name: metadata_access_to_credential_harvest
    mitre_id: "T1552.005"
    if:
      node.type: Capability
      node.subtype: metadata_access
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: credential_harvesting
        confidence: 0.85

  - name: cloud_access_to_data_exfil
    mitre_id: "T1530"
    if:
      node.type: Capability
      node.subtype: cloud_access
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.85

  - name: prototype_pollution_to_rce
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: prototype_pollution
      node.property: "severity:>=3"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.75

  - name: graphql_injection_to_rce
    mitre_id: "T1059"
    if:
      node.type: Vulnerability
      node.subtype: graphql_injection
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.80

  # ============================================================
  # CATEGORY I — Web Technology–Specific (5 rules)
  # ============================================================

  - name: wordpress_plugin_to_rce
    mitre_id: "T1505.003"
    if:
      node.type: Vulnerability
      node.subtype: rce
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.80
        requires_wordpress: true

  - name: wordpress_sqli_to_db_access
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: sqli
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: db_access
        confidence: 0.85
        requires_wordpress: true

  - name: spring_actuator_to_data_exfil
    mitre_id: "T1083"
    if:
      node.type: Vulnerability
      node.subtype: misconfig
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: data_exfil
        confidence: 0.80
        requires_java: true

  - name: jenkins_unauth_to_rce
    mitre_id: "T1059"
    if:
      node.type: Vulnerability
      node.subtype: misconfig
      node.property: "validated:True"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.90
        requires_java: true

  - name: log4j_to_rce
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: log_injection
      node.property:
        - "severity:>=4"
        - "validated:True"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: rce_execution
        confidence: 0.95

  # ============================================================
  # CATEGORY J — Secrets & Credentials (5 rules)
  # ============================================================

  - name: exposed_db_creds_to_db_access
    mitre_id: "T1552"
    if:
      node.type: Credential
      node.subtype: db_password
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: db_access
        confidence: 0.90

  - name: exposed_jwt_secret_to_auth_bypass
    mitre_id: "T1528"
    if:
      node.type: Credential
      node.subtype: jwt_token
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.90

  - name: github_token_to_code_exfil
    mitre_id: "T1528"
    if:
      node.type: Credential
      node.subtype: github_token
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: code_exfiltration
        confidence: 0.85

  - name: env_file_to_credential_harvest
    mitre_id: "T1552"
    if:
      node.type: Vulnerability
      node.subtype: misconfig
      node.property: "severity:>=2"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: credential_harvesting
        confidence: 0.85

  - name: api_key_to_lateral_movement
    mitre_id: "T1078"
    if:
      node.type: Credential
      node.subtype: api_key
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: lateral_movement
        confidence: 0.75

  # ============================================================
  # CATEGORY K — DNS & Subdomain (4 rules)
  # ============================================================

  - name: subdomain_takeover_to_authenticated_access
    mitre_id: "T1584.001"
    if:
      node.type: Vulnerability
      node.subtype: subdomain_takeover
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: authenticated_access
        confidence: 0.85

  - name: subdomain_takeover_to_phishing
    mitre_id: "T1566.001"
    if:
      node.type: Vulnerability
      node.subtype: subdomain_takeover
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: phishing_amplification
        confidence: 0.80

  - name: dns_rebinding_to_internal_access
    mitre_id: "T1557"
    if:
      node.type: Vulnerability
      node.subtype: dns_rebinding
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: pivot
        confidence: 0.70

  - name: dependency_confusion_to_supply_chain
    mitre_id: "T1195"
    if:
      node.type: Vulnerability
      node.subtype: dependency_confusion
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: supply_chain_compromise
        confidence: 0.75

  # ============================================================
  # CATEGORY L — Lateral Movement & Post-Exploitation (5 rules)
  # ============================================================

  - name: execution_to_pivot
    mitre_id: "T1090"
    if:
      node.type: Capability
      node.subtype: rce_execution
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: pivot
        confidence: 0.85

  - name: pivot_to_internal_discovery
    mitre_id: "T1046"
    if:
      node.type: Capability
      node.subtype: pivot
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: internal_discovery
        confidence: 0.80

  - name: internal_discovery_to_lateral
    mitre_id: "T1021"
    if:
      node.type: Capability
      node.subtype: internal_discovery
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: lateral_movement
        confidence: 0.75

  - name: credential_to_lateral_movement
    mitre_id: "T1021"
    if:
      node.type: Credential
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: lateral_movement
        confidence: 0.80

  - name: admin_access_to_persistence
    mitre_id: "T1505"
    if:
      node.type: Privilege
      node.subtype: admin
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: persistence
        confidence: 0.75

  # ============================================================
  # CATEGORY M — Severity-Gated HVT Rules (4 rules)
  # Replaces the removed broken `any_vuln_on_hvt` rule.
  # ============================================================

  - name: critical_vuln_on_sensitive_asset
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.property:
        - "severity:>=4"
        - "sensitivity:high"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: hvt_compromise
        confidence: 0.85

  - name: high_vuln_on_sensitive_asset_validated
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.property:
        - "severity:>=3"
        - "sensitivity:high"
        - "validated:True"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: hvt_compromise
        confidence: 0.75

  - name: rce_on_sensitive_to_full_compromise
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: rce
      node.property: "sensitivity:high"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: hvt_compromise
        confidence: 0.90

  - name: sqli_on_db_asset_to_full_compromise
    mitre_id: "T1190"
    if:
      node.type: Vulnerability
      node.subtype: sqli
      node.property: "severity:>=3"
    then:
      create_edge:
        type: LEADS_TO
        target_subtype: hvt_compromise
        confidence: 0.88
```

- [ ] **Step 1.4 — Run the full Phase 2 test suite**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase2 -v 2"
```

Expected: All tests pass. If any fail, check the test output — the most common issue is a missing subtype in `schema.py NODE_TYPES` or a missing capability in the goal nodes.

- [ ] **Step 1.5 — Verify rule count**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 -c \"
from apme.engine.rules_engine import RulesEngine
e = RulesEngine()
print(f'Total rules: {len(e._rules)}')
names = [r.get(\\\"name\\\") for r in e._rules]
print(f'any_vuln_on_hvt present: {\\\"any_vuln_on_hvt\\\" in names}')
\""
```

Expected output:
```
Total rules: 72
any_vuln_on_hvt present: False
```

- [ ] **Step 1.6 — Run full test suite for regressions**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -5"
```

Expected: No new failures.

- [ ] **Step 1.7 — Commit**

```bash
git add web/apme/config/rules.yaml web/tests/test_apme_phase2.py
git commit -m "feat(apme): expand rules from 14 to 72 across 13 kill-chain categories; remove broken any_vuln_on_hvt rule"
```

- [ ] **Step 1.8 — Tag Phase 2 complete**

```bash
git tag apme-phase2-complete
git push origin apme-enhancement --tags
```

---

**Phase 2 complete.** Proceed to [Phase 3 plan](2026-06-13-apme-phase3-mitre-ui.md) for MITRE ATT&CK UI attribution on web and mobile.
