# APME Phase 2 — Rules Expansion (14 → 72) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single `rules.yaml` with a `rules/` directory of 13 per-category YAML files totalling 72 rules. Verify every rule fires correctly against a mock graph.

**Prerequisite:** Phase 1 must be complete — the rules engine `_load_rules()` already supports directory loading as of Phase 1 Task 6.

**Architecture:** `web/apme/config/rules/` contains one file per kill-chain category, named with an alphabetical prefix (`a_injection.yaml`, `b_file_ops.yaml`, …) so they load in a predictable order. Each file is standalone — adding or auditing a category never touches another file. The `_RULES_FILE` constant in `rules_engine.py` already points to this directory after Phase 1.

**Tech Stack:** PyYAML, Django test framework (inside Docker)

---

## File Map

| Action | File |
|---|---|
| DELETE | `web/apme/config/rules.yaml` |
| CREATE | `web/apme/config/rules/a_injection.yaml` |
| CREATE | `web/apme/config/rules/b_file_ops.yaml` |
| CREATE | `web/apme/config/rules/c_server_side.yaml` |
| CREATE | `web/apme/config/rules/d_deserialization.yaml` |
| CREATE | `web/apme/config/rules/e_auth_identity.yaml` |
| CREATE | `web/apme/config/rules/f_client_side.yaml` |
| CREATE | `web/apme/config/rules/g_info_disclosure.yaml` |
| CREATE | `web/apme/config/rules/h_cloud.yaml` |
| CREATE | `web/apme/config/rules/i_tech_specific.yaml` |
| CREATE | `web/apme/config/rules/j_secrets.yaml` |
| CREATE | `web/apme/config/rules/k_dns_subdomain.yaml` |
| CREATE | `web/apme/config/rules/l_lateral_movement.yaml` |
| CREATE | `web/apme/config/rules/m_hvt.yaml` |
| CREATE | `web/tests/test_apme_phase2.py` |

All tests run inside Docker:
```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase2 -v 2"
```

---

## Task 1: Write Failing Tests First

- [ ] **Step 1.1 — Create `web/tests/test_apme_phase2.py`**

```python
"""Phase 2 APME rules expansion tests.

Tests verify that each rule category fires correctly against mock APME nodes.
No Neo4j connection required — the RulesEngine is tested directly.
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


class RulesDirectoryLoadingTests(TestCase):
    """Verify the rules/ directory loads correctly."""

    def test_rules_loaded_from_directory(self):
        engine = RulesEngine()
        self.assertGreaterEqual(len(engine._rules), 72)

    def test_any_vuln_on_hvt_rule_removed(self):
        engine = RulesEngine()
        rule_names = {r.get("name") for r in engine._rules}
        self.assertNotIn("any_vuln_on_hvt", rule_names)

    def test_all_rules_have_mitre_id(self):
        engine = RulesEngine()
        missing = [r.get("name") for r in engine._rules if not r.get("mitre_id")]
        self.assertEqual(missing, [], f"Rules missing mitre_id: {missing}")

    def test_all_rules_have_name(self):
        engine = RulesEngine()
        unnamed = [i for i, r in enumerate(engine._rules) if not r.get("name")]
        self.assertEqual(unnamed, [], f"Unnamed rules at indices: {unnamed}")

    def test_rule_names_are_unique(self):
        engine = RulesEngine()
        names = [r.get("name") for r in engine._rules]
        self.assertEqual(len(names), len(set(names)), "Duplicate rule names found")


class CategoryAInjectionTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_sqli_leads_to_db_access(self):
        self.assertIn("db_access", self._target_subtypes(_vuln("sqli")))

    def test_sqli_high_confidence_leads_to_account_takeover(self):
        node = _vuln("sqli", severity=4, confidence=0.85, validated=True)
        self.assertIn("account_takeover", self._target_subtypes(node))

    def test_sqli_low_confidence_no_account_takeover(self):
        node = _vuln("sqli", severity=2, confidence=0.40, validated=False)
        self.assertNotIn("account_takeover", self._target_subtypes(node))

    def test_command_injection_leads_to_rce_execution(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("command_injection")))

    def test_code_injection_leads_to_rce_execution(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("code_injection")))

    def test_nosql_injection_leads_to_db_access(self):
        self.assertIn("db_access", self._target_subtypes(_vuln("nosql_injection")))

    def test_xpath_injection_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("xpath_injection")))

    def test_ldap_injection_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("ldap_injection")))

    def test_log_injection_severity3_leads_to_rce(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("log_injection", severity=3)))

    def test_log_injection_severity2_no_rce(self):
        self.assertNotIn("rce_execution", self._target_subtypes(_vuln("log_injection", severity=2)))

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

    def test_ssrf_leads_to_internal_discovery(self):
        self.assertIn("internal_discovery", self._target_subtypes(_vuln("ssrf")))

    def test_xxe_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("xxe")))

    def test_xxe_leads_to_pivot(self):
        self.assertIn("pivot", self._target_subtypes(_vuln("xxe")))


class CategoryDDeserializationTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _edges(self, node):
        return self.engine.apply(node, [node] + self.goals)

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self._edges(node)}

    def test_deserialization_leads_to_rce(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("deserialization")))

    def test_deserialization_edges_include_java_flag(self):
        edges = self._edges(_vuln("deserialization"))
        java_edges = [e for e in edges if e.properties.get("requires_java")]
        self.assertTrue(len(java_edges) > 0, "No edges have requires_java=True")

    def test_deserialization_edges_include_php_flag(self):
        edges = self._edges(_vuln("deserialization"))
        php_edges = [e for e in edges if e.properties.get("requires_php")]
        self.assertTrue(len(php_edges) > 0, "No edges have requires_php=True")

    def test_deserialization_edges_include_python_flag(self):
        edges = self._edges(_vuln("deserialization"))
        python_edges = [e for e in edges if e.properties.get("requires_python")]
        self.assertTrue(len(python_edges) > 0, "No edges have requires_python=True")


class CategoryEAuthTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_misconfig_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("misconfig")))

    def test_any_credential_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_cred("api_key")))

    def test_jwt_abuse_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("jwt_abuse")))

    def test_jwt_abuse_high_confidence_leads_to_account_takeover(self):
        self.assertIn("account_takeover", self._target_subtypes(_vuln("jwt_abuse", confidence=0.75)))

    def test_jwt_abuse_low_confidence_no_account_takeover(self):
        self.assertNotIn("account_takeover", self._target_subtypes(_vuln("jwt_abuse", confidence=0.50)))

    def test_oauth_misconfig_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("oauth_misconfig")))

    def test_idor_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("idor")))

    def test_crlf_leads_to_session_hijacking(self):
        self.assertIn("session_hijacking", self._target_subtypes(_vuln("crlf_injection")))

    def test_host_header_leads_to_account_takeover(self):
        self.assertIn("account_takeover", self._target_subtypes(_vuln("host_header")))

    def test_validated_misconfig_leads_to_account_takeover(self):
        self.assertIn("account_takeover", self._target_subtypes(_vuln("misconfig", validated=True)))


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

    def test_xss_session_hijack_edge_has_requires_victim(self):
        edges = self._edges(_vuln("xss"))
        session_edges = [e for e in edges if "session_hijacking" in e.to_id]
        self.assertTrue(any(e.properties.get("requires_victim") for e in session_edges),
                        "xss→session_hijacking edge missing requires_victim flag")

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

    def test_cors_has_requires_victim(self):
        edges = self.engine.apply(_vuln("cors"), [_vuln("cors")] + self.goals)
        self.assertTrue(any(e.properties.get("requires_victim") for e in edges))

    def test_prototype_pollution_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._target_subtypes(_vuln("prototype_pollution")))

    def test_graphql_injection_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("graphql_injection")))

    def test_misconfig_severity2_leads_to_credential_harvesting(self):
        self.assertIn("credential_harvesting",
                      self._target_subtypes(_vuln("misconfig", severity=2)))

    def test_misconfig_severity2_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_vuln("misconfig", severity=2)))


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

    def test_metadata_access_capability_leads_to_credential_harvesting(self):
        self.assertIn("credential_harvesting", self._target_subtypes(_cap("metadata_access")))

    def test_cloud_access_capability_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._target_subtypes(_cap("cloud_access")))

    def test_prototype_pollution_severity3_leads_to_rce(self):
        self.assertIn("rce_execution",
                      self._target_subtypes(_vuln("prototype_pollution", severity=3)))

    def test_prototype_pollution_severity1_no_rce(self):
        self.assertNotIn("rce_execution",
                         self._target_subtypes(_vuln("prototype_pollution", severity=1)))

    def test_graphql_injection_leads_to_rce(self):
        self.assertIn("rce_execution", self._target_subtypes(_vuln("graphql_injection")))


class CategoryITechSpecificTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _edges(self, node):
        return self.engine.apply(node, [node] + self.goals)

    def test_rce_has_wordpress_gated_edge(self):
        edges = self._edges(_vuln("rce"))
        wp_edges = [e for e in edges if e.properties.get("requires_wordpress")]
        self.assertTrue(len(wp_edges) > 0, "No wordpress-gated RCE rule found")

    def test_misconfig_has_java_gated_edge_to_data_exfil(self):
        edges = self._edges(_vuln("misconfig"))
        java_edges = [e for e in edges
                      if e.properties.get("requires_java") and "data_exfil" in e.to_id]
        self.assertTrue(len(java_edges) > 0)

    def test_log4j_rule_fires_only_with_severity4_and_validated(self):
        firing = _vuln("log_injection", severity=4, validated=True, confidence=1.0)
        not_firing = _vuln("log_injection", severity=3, validated=False)
        firing_edges = [
            e for e in self._edges(firing)
            if e.properties.get("rule") == "log4j_to_rce"
        ]
        not_firing_edges = [
            e for e in self._edges(not_firing)
            if e.properties.get("rule") == "log4j_to_rce"
        ]
        self.assertTrue(len(firing_edges) > 0, "log4j_to_rce did not fire")
        self.assertEqual(len(not_firing_edges), 0, "log4j_to_rce fired when it should not")


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

    def test_misconfig_severity2_leads_to_credential_harvesting(self):
        self.assertIn("credential_harvesting",
                      self._target_subtypes(_vuln("misconfig", severity=2)))


class CategoryKDNSTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _target_subtypes(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_subdomain_takeover_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access",
                      self._target_subtypes(_vuln("subdomain_takeover")))

    def test_subdomain_takeover_leads_to_phishing(self):
        self.assertIn("phishing_amplification",
                      self._target_subtypes(_vuln("subdomain_takeover")))

    def test_dns_rebinding_leads_to_pivot(self):
        self.assertIn("pivot", self._target_subtypes(_vuln("dns_rebinding")))

    def test_dependency_confusion_leads_to_supply_chain_compromise(self):
        self.assertIn("supply_chain_compromise",
                      self._target_subtypes(_vuln("dependency_confusion")))


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

    def test_critical_vuln_on_sensitive_asset_leads_to_hvt(self):
        node = _vuln("generic_critical", severity=4, sensitivity="high")
        self.assertIn("hvt_compromise", self._target_subtypes(node))

    def test_low_severity_does_not_trigger_hvt(self):
        node = _vuln("generic", severity=1, sensitivity="high")
        self.assertNotIn("hvt_compromise", self._target_subtypes(node))

    def test_rce_on_sensitive_leads_to_hvt(self):
        node = _vuln("rce", severity=4, sensitivity="high")
        self.assertIn("hvt_compromise", self._target_subtypes(node))

    def test_low_sensitivity_critical_vuln_no_hvt_from_category_m(self):
        # HVT rules require sensitivity=high; a critical vuln on low-sensitivity asset
        # should NOT reach hvt_compromise via category M rules
        node = _vuln("generic_critical", severity=4, sensitivity="low")
        self.assertNotIn("hvt_compromise", self._target_subtypes(node))
```

- [ ] **Step 1.2 — Run tests (expect FAIL — rules directory doesn't exist yet)**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase2.RulesDirectoryLoadingTests -v 2 2>&1 | tail -10"
```

Expected: `FileNotFoundError` or test failures — the `rules/` directory doesn't exist yet.

- [ ] **Step 1.3 — Commit the test file**

```bash
git add web/tests/test_apme_phase2.py
git commit -m "test(apme): add Phase 2 rules expansion test suite (written before rules)"
```

---

## Task 2: Create `rules/` Directory and Category Files

Each file follows this structure:
```yaml
# Category X — Description (N rules)
rules:
  - name: rule_name
    ...
```

The old `rules.yaml` is deleted after all files are created.

- [ ] **Step 2.1 — Create `web/apme/config/rules/a_injection.yaml`**

```yaml
# Category A — Injection (9 rules)
rules:

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
```

- [ ] **Step 2.2 — Create `web/apme/config/rules/b_file_ops.yaml`**

```yaml
# Category B — File Operations (5 rules)
rules:

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
```

- [ ] **Step 2.3 — Create `web/apme/config/rules/c_server_side.yaml`**

```yaml
# Category C — Server-Side Exploitation (7 rules)
rules:

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
```

- [ ] **Step 2.4 — Create `web/apme/config/rules/d_deserialization.yaml`**

```yaml
# Category D — Deserialization (4 rules)
# All fire on node.subtype: deserialization.
# Tech-gated variants add requires_java/php/python so the constraint
# engine blocks them unless the technology is detected on the target.
rules:

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
```

- [ ] **Step 2.5 — Create `web/apme/config/rules/e_auth_identity.yaml`**

```yaml
# Category E — Authentication & Identity (9 rules)
rules:

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
```

- [ ] **Step 2.6 — Create `web/apme/config/rules/f_client_side.yaml`**

```yaml
# Category F — Client-Side (7 rules)
# Victim-interaction rules set requires_victim: true so the constraint engine
# blocks them unless a victim-interaction context flag is set.
rules:

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
```

- [ ] **Step 2.7 — Create `web/apme/config/rules/g_info_disclosure.yaml`**

```yaml
# Category G — Information Disclosure (6 rules)
rules:

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
```

- [ ] **Step 2.8 — Create `web/apme/config/rules/h_cloud.yaml`**

```yaml
# Category H — Cloud & Infrastructure (6 rules)
# Includes Capability→Capability chaining rules so discovered metadata access
# can cascade to credential harvesting and data exfiltration.
rules:

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
```

- [ ] **Step 2.9 — Create `web/apme/config/rules/i_tech_specific.yaml`**

```yaml
# Category I — Web Technology–Specific (5 rules)
# These rules fire on common vulnerability subtypes but gate on technology
# context flags. The constraint engine blocks them unless the corresponding
# technology is detected on the target asset.
rules:

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
```

- [ ] **Step 2.10 — Create `web/apme/config/rules/j_secrets.yaml`**

```yaml
# Category J — Secrets & Credentials (5 rules)
# Fire on specific Credential subtypes produced by Phase 1 credential enrichment,
# and on misconfig vulnerabilities that commonly expose secrets.
rules:

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
```

- [ ] **Step 2.11 — Create `web/apme/config/rules/k_dns_subdomain.yaml`**

```yaml
# Category K — DNS & Subdomain (4 rules)
rules:

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
```

- [ ] **Step 2.12 — Create `web/apme/config/rules/l_lateral_movement.yaml`**

```yaml
# Category L — Lateral Movement & Post-Exploitation (5 rules)
# These fire on Capability and Privilege nodes, enabling multi-hop chaining:
# e.g. SSRF → metadata_access → credential_harvesting → lateral_movement
rules:

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
```

- [ ] **Step 2.13 — Create `web/apme/config/rules/m_hvt.yaml`**

```yaml
# Category M — Severity-Gated High Value Target Rules (4 rules)
#
# Replaces the removed broken `any_vuln_on_hvt` rule (which targeted a
# non-existent capability and fired for every vulnerability indiscriminately).
#
# These rules only fire when both severity AND asset sensitivity meet a
# threshold, ensuring hvt_compromise is a high-signal output not triggered
# by routine low-severity findings.
rules:

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

---

## Task 3: Delete Old `rules.yaml` and Verify

- [ ] **Step 3.1 — Delete the old single-file rules.yaml**

```bash
rm web/apme/config/rules.yaml
```

- [ ] **Step 3.2 — Verify rule loading from the new directory**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 -c \"
from apme.engine.rules_engine import RulesEngine
e = RulesEngine()
print(f'Total rules: {len(e._rules)}')
names = [r[\\\"name\\\"] for r in e._rules]
print(f'any_vuln_on_hvt removed: {\\\"any_vuln_on_hvt\\\" not in names}')
print(f'log4j_to_rce present: {\\\"log4j_to_rce\\\" in names}')
print(f'github_token_to_code_exfil present: {\\\"github_token_to_code_exfil\\\" in names}')
\""
```

Expected output:
```
Total rules: 72
any_vuln_on_hvt removed: True
log4j_to_rce present: True
github_token_to_code_exfil present: True
```

- [ ] **Step 3.3 — Run full Phase 2 test suite**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_apme_phase2 -v 2"
```

Expected: All tests pass. If any fail, check the error — the most common cause is a missing capability/subtype in `schema.py NODE_TYPES` (should have been added in Phase 1 Task 2).

- [ ] **Step 3.4 — Run full test suite for regressions**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -5"
```

Expected: No new failures.

- [ ] **Step 3.5 — Commit everything**

```bash
git add web/apme/config/rules/ web/tests/test_apme_phase2.py
git rm web/apme/config/rules.yaml
git commit -m "feat(apme): expand to 72 rules in dedicated rules/ directory (13 categories); remove broken any_vuln_on_hvt rule"
```

- [ ] **Step 3.6 — Tag Phase 2 complete**

```bash
git tag apme-phase2-complete
git push origin apme-enhancement --tags
```

---

**Phase 2 complete.** The rules directory structure:
```
web/apme/config/rules/
├── a_injection.yaml        (9 rules)
├── b_file_ops.yaml         (5 rules)
├── c_server_side.yaml      (7 rules)
├── d_deserialization.yaml  (4 rules)
├── e_auth_identity.yaml    (9 rules)
├── f_client_side.yaml      (7 rules)
├── g_info_disclosure.yaml  (6 rules)
├── h_cloud.yaml            (6 rules)
├── i_tech_specific.yaml    (5 rules)
├── j_secrets.yaml          (5 rules)
├── k_dns_subdomain.yaml    (4 rules)
├── l_lateral_movement.yaml (5 rules)
└── m_hvt.yaml              (4 rules)
                             ───────
                             72 total
```

Adding a new category in future = create one new file. No other files touched.

Proceed to [Phase 3 plan](2026-06-13-apme-phase3-mitre-ui.md) for MITRE ATT&CK UI attribution.
