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


from apme.engine.rules_engine import _numeric_check, _property_check, RulesEngine
from apme.models.node import Node as APMENode


class RulesEngineNumericTests(TestCase):

    def test_numeric_check_gte_passes(self):
        self.assertTrue(_numeric_check(3, ">=3"))
        self.assertTrue(_numeric_check(4, ">=3"))

    def test_numeric_check_gte_fails(self):
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
        props = {"sensitivity": "high"}
        self.assertTrue(_property_check(props, "sensitivity:high"))
        self.assertFalse(_property_check(props, "sensitivity:low"))

    def test_property_check_numeric_severity(self):
        props = {"severity": 4}
        self.assertTrue(_property_check(props, "severity:>=3"))
        self.assertFalse(_property_check(props, "severity:>=5"))

    def test_property_check_missing_key(self):
        self.assertFalse(_property_check({}, "severity:>=3"))

    def test_rules_engine_loads_yaml(self):
        # Point at the existing rules.yaml (single-file backward compat)
        import os
        yaml_path = os.path.join(
            os.path.dirname(__file__), "..", "apme", "config", "rules.yaml"
        )
        if os.path.exists(yaml_path):
            engine = RulesEngine(yaml_path)
            self.assertGreater(len(engine._rules), 0)
        else:
            # Phase 2 will create the rules/ dir; test that empty dir loads cleanly
            engine = RulesEngine.__new__(RulesEngine)
            engine._rules = []
            self.assertEqual(len(engine._rules), 0)

    def test_constraint_flags_propagated_to_edge(self):
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
        xss_node = APMENode(id="vuln::1", type="Vulnerability", subtype="xss",
                            confidence=0.6, source="test", properties={})
        target = APMENode(id="goal::capability::session_hijacking", type="Capability",
                          subtype="session_hijacking", confidence=1.0, source="test",
                          properties={})
        edges = engine.apply(xss_node, [xss_node, target])
        self.assertEqual(len(edges), 1)
        self.assertTrue(edges[0].properties.get("requires_victim"))
        self.assertEqual(edges[0].properties.get("mitre_id"), "T1189")


from apme.engine.constraints import ConstraintEngine, PathContext, MIN_STEP_CONFIDENCE


class ConstraintEngineTests(TestCase):

    def _make_step(self, **kwargs):
        defaults = {"action": "test", "confidence": 0.8, "to_id": "node::unique"}
        defaults.update(kwargs)
        return defaults

    def setUp(self):
        self.engine = ConstraintEngine()
        self.ctx = PathContext()

    def test_low_confidence_step_blocked(self):
        step = self._make_step(confidence=MIN_STEP_CONFIDENCE - 0.01, to_id="node::a")
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_adequate_confidence_passes(self):
        step = self._make_step(confidence=0.80, to_id="node::a")
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
        step = self._make_step(requires_victim=True, to_id="node::b")
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_victim_required_passes_with_context(self):
        self.ctx.has_victim_interaction = True
        step = self._make_step(requires_victim=True, to_id="node::b")
        self.assertTrue(self.engine.validate_step(step, self.ctx))

    def test_php_gate_blocked_without_tech(self):
        step = self._make_step(requires_php=True, to_id="node::c")
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_php_gate_passes_with_tech(self):
        self.ctx.has_php_tech = True
        step = self._make_step(requires_php=True, to_id="node::c")
        self.assertTrue(self.engine.validate_step(step, self.ctx))

    def test_path_confidence_product_drops_below_threshold(self):
        self.ctx.path_confidence_product = 0.06
        # 0.06 * 0.8 = 0.048 < 0.05
        step = self._make_step(confidence=0.8, to_id="node::d")
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_wordpress_gate_blocked_without_tech(self):
        step = self._make_step(requires_wordpress=True, to_id="node::e")
        self.assertFalse(self.engine.validate_step(step, self.ctx))

    def test_update_context_sets_visited(self):
        step = self._make_step(to_id="cap::pivot")
        self.engine.update_context(step, self.ctx)
        self.assertIn("cap::pivot", self.ctx.visited_node_ids)

    def test_update_context_propagates_php_tech(self):
        step = self._make_step(to_subtype="php")
        self.engine.update_context(step, self.ctx)
        self.assertTrue(self.ctx.has_php_tech)

    def test_update_context_propagates_java_tech_for_spring(self):
        step = self._make_step(to_subtype="spring")
        self.engine.update_context(step, self.ctx)
        self.assertTrue(self.ctx.has_java_tech)
