"""Phase 2 APME rules expansion tests."""
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
        properties={"severity": severity, "validated": str(validated), "sensitivity": sensitivity},
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
    return Node(id=f"goal::capability::{subtype}", type="Capability", subtype=subtype,
                confidence=1.0, source="test", properties={})

def _priv(subtype):
    return Node(id=f"goal::privilege::{subtype}", type="Privilege", subtype=subtype,
                confidence=1.0, source="test", properties={})

def _all_goal_nodes():
    from apme.graph.schema import NODE_TYPES
    nodes = []
    for subtype in NODE_TYPES.get("Capability", []):
        nodes.append(_cap(subtype))
    for subtype in NODE_TYPES.get("Privilege", []):
        nodes.append(_priv(subtype))
    return nodes


class RulesDirectoryLoadingTests(TestCase):
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

    def test_rule_names_are_unique(self):
        engine = RulesEngine()
        names = [r.get("name") for r in engine._rules]
        self.assertEqual(len(names), len(set(names)), "Duplicate rule names found")


class CategoryAInjectionTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _targets(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_sqli_leads_to_db_access(self):
        self.assertIn("db_access", self._targets(_vuln("sqli")))

    def test_sqli_high_confidence_leads_to_account_takeover(self):
        self.assertIn("account_takeover", self._targets(_vuln("sqli", severity=4, confidence=0.85, validated=True)))

    def test_sqli_low_confidence_no_account_takeover(self):
        self.assertNotIn("account_takeover", self._targets(_vuln("sqli", severity=2, confidence=0.40)))

    def test_command_injection_leads_to_rce(self):
        self.assertIn("rce_execution", self._targets(_vuln("command_injection")))

    def test_log_injection_severity3_leads_to_rce(self):
        self.assertIn("rce_execution", self._targets(_vuln("log_injection", severity=3)))

    def test_log_injection_severity2_no_rce(self):
        self.assertNotIn("rce_execution", self._targets(_vuln("log_injection", severity=2)))

    def test_ssti_leads_to_rce(self):
        self.assertIn("rce_execution", self._targets(_vuln("ssti")))


class CategoryBFileOpsTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _targets(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_lfi_leads_to_rce(self):
        self.assertIn("rce_execution", self._targets(_vuln("lfi")))

    def test_path_traversal_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._targets(_vuln("path_traversal")))

    def test_file_upload_leads_to_rce(self):
        self.assertIn("rce_execution", self._targets(_vuln("file_upload")))

    def test_file_upload_leads_to_persistence(self):
        self.assertIn("persistence", self._targets(_vuln("file_upload")))


class CategoryCServerSideTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _targets(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_ssrf_leads_to_cloud_access(self):
        self.assertIn("cloud_access", self._targets(_vuln("ssrf")))

    def test_ssrf_leads_to_metadata_access(self):
        self.assertIn("metadata_access", self._targets(_vuln("ssrf")))

    def test_xxe_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._targets(_vuln("xxe")))


class CategoryDDeserializationTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def test_deserialization_leads_to_rce(self):
        targets = {e.to_id.split("::")[-1] for e in self.engine.apply(_vuln("deserialization"), [_vuln("deserialization")] + self.goals)}
        self.assertIn("rce_execution", targets)

    def test_deserialization_has_java_flag(self):
        edges = self.engine.apply(_vuln("deserialization"), [_vuln("deserialization")] + self.goals)
        self.assertTrue(any(e.properties.get("requires_java") for e in edges))

    def test_deserialization_has_php_flag(self):
        edges = self.engine.apply(_vuln("deserialization"), [_vuln("deserialization")] + self.goals)
        self.assertTrue(any(e.properties.get("requires_php") for e in edges))


class CategoryEAuthTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _targets(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_creds_lead_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._targets(_cred("api_key")))

    def test_jwt_abuse_leads_to_authenticated_access(self):
        self.assertIn("authenticated_access", self._targets(_vuln("jwt_abuse")))

    def test_jwt_abuse_high_confidence_leads_to_account_takeover(self):
        self.assertIn("account_takeover", self._targets(_vuln("jwt_abuse", confidence=0.75)))

    def test_crlf_leads_to_session_hijacking(self):
        self.assertIn("session_hijacking", self._targets(_vuln("crlf_injection")))

    def test_idor_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._targets(_vuln("idor")))


class CategoryFClientSideTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def test_xss_session_hijack_has_requires_victim(self):
        edges = self.engine.apply(_vuln("xss"), [_vuln("xss")] + self.goals)
        session_edges = [e for e in edges if "session_hijacking" in e.to_id]
        self.assertTrue(any(e.properties.get("requires_victim") for e in session_edges))

    def test_open_redirect_leads_to_phishing(self):
        targets = {e.to_id.split("::")[-1] for e in self.engine.apply(_vuln("open_redirect"), [_vuln("open_redirect")] + self.goals)}
        self.assertIn("phishing_amplification", targets)

    def test_csrf_has_requires_victim(self):
        edges = self.engine.apply(_vuln("csrf"), [_vuln("csrf")] + self.goals)
        self.assertTrue(any(e.properties.get("requires_victim") for e in edges))


class CategoryGHIJKTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _targets(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_cors_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._targets(_vuln("cors")))

    def test_cloud_api_key_leads_to_cloud_access(self):
        self.assertIn("cloud_access", self._targets(_cred("cloud_api_key")))

    def test_s3_misconfig_leads_to_data_exfil(self):
        self.assertIn("data_exfil", self._targets(_vuln("s3_misconfig")))

    def test_metadata_access_cap_leads_to_credential_harvesting(self):
        self.assertIn("credential_harvesting", self._targets(_cap("metadata_access")))

    def test_prototype_pollution_severity3_leads_to_rce(self):
        self.assertIn("rce_execution", self._targets(_vuln("prototype_pollution", severity=3)))

    def test_db_password_leads_to_db_access(self):
        self.assertIn("db_access", self._targets(_cred("db_password")))

    def test_github_token_leads_to_code_exfiltration(self):
        self.assertIn("code_exfiltration", self._targets(_cred("github_token")))

    def test_subdomain_takeover_leads_to_phishing(self):
        self.assertIn("phishing_amplification", self._targets(_vuln("subdomain_takeover")))

    def test_dependency_confusion_leads_to_supply_chain(self):
        self.assertIn("supply_chain_compromise", self._targets(_vuln("dependency_confusion")))


class CategoryLMTests(TestCase):
    def setUp(self):
        self.engine = RulesEngine()
        self.goals = _all_goal_nodes()

    def _targets(self, node):
        return {e.to_id.split("::")[-1] for e in self.engine.apply(node, [node] + self.goals)}

    def test_rce_execution_cap_leads_to_pivot(self):
        self.assertIn("pivot", self._targets(_cap("rce_execution")))

    def test_internal_discovery_leads_to_lateral_movement(self):
        self.assertIn("lateral_movement", self._targets(_cap("internal_discovery")))

    def test_admin_privilege_leads_to_persistence(self):
        self.assertIn("persistence", self._targets(_priv("admin")))

    def test_critical_vuln_on_sensitive_asset_leads_to_hvt(self):
        self.assertIn("hvt_compromise", self._targets(_vuln("generic_critical", severity=4, sensitivity="high")))

    def test_low_severity_does_not_trigger_hvt(self):
        self.assertNotIn("hvt_compromise", self._targets(_vuln("generic", severity=1)))

    def test_log4j_rule_fires_only_with_severity4_and_validated(self):
        firing = _vuln("log_injection", severity=4, validated=True, confidence=1.0)
        not_firing = _vuln("log_injection", severity=3, validated=False)
        firing_edges = [e for e in self.engine.apply(firing, [firing] + self.goals) if e.properties.get("rule") == "log4j_to_rce"]
        not_firing_edges = [e for e in self.engine.apply(not_firing, [not_firing] + self.goals) if e.properties.get("rule") == "log4j_to_rce"]
        self.assertTrue(len(firing_edges) > 0, "log4j_to_rce did not fire")
        self.assertEqual(len(not_firing_edges), 0, "log4j_to_rce fired when it should not")

    def test_any_vuln_on_hvt_rule_removed(self):
        engine = RulesEngine()
        self.assertNotIn("any_vuln_on_hvt", {r.get("name") for r in engine._rules})
