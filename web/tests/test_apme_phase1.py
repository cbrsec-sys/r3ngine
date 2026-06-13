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
