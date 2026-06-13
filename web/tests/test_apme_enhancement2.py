"""APME Enhancement 2 — Phase 1 & Phase 2 tests."""
from django.test import TestCase

from apme.graph.schema import NODE_TYPES
from apme.ingestion.vulnerabilities import TAXONOMY_MAP, _infer_taxonomy
from apme.engine.constraints import ConstraintEngine, PathContext
from apme.engine.rules_engine import _CONSTRAINT_FLAGS


class SchemaExtensionTests(TestCase):
    """Verify new Technology, Vulnerability, and Capability subtypes."""

    # ── Technology ──────────────────────────────────────────────────────

    EXPECTED_TECH_SUBTYPES = [
        "dotnet", "ruby", "rails", "react", "angular", "vue",
        "kubernetes", "docker", "terraform", "ansible",
        "drupal", "joomla", "magento", "laravel",
        "mssql", "oracle", "redis", "elasticsearch", "mongodb",
        "exchange", "active_directory", "ldap",
    ]

    def test_new_technology_subtypes_present(self) -> None:
        subtypes = NODE_TYPES["Technology"]
        for expected in self.EXPECTED_TECH_SUBTYPES:
            self.assertIn(expected, subtypes, f"Missing Technology subtype: {expected}")

    # ── Vulnerability ───────────────────────────────────────────────────

    EXPECTED_VULN_SUBTYPES = [
        "http_request_smuggling", "tls_downgrade", "dns_cache_poisoning",
        "docker_socket_exposed", "container_escape", "k8s_rbac_misconfig",
        "privileged_container", "k8s_secret_exposure",
        "ntlm_relay", "pass_the_hash", "kerberoasting", "asrep_roasting",
        "dcsync_privilege", "gpo_abuse", "pass_the_ticket",
        "websocket_hijacking", "mass_assignment", "parameter_pollution",
        "graphql_mutation_abuse", "api_versioning_bypass",
        "spf_dmarc_bypass", "email_header_injection",
        "race_condition", "account_enumeration", "session_fixation",
        "business_logic_bypass", "parameter_tampering",
        "typosquatting", "compromised_registry", "ci_artifact_poisoning",
        "github_actions_injection",
        "blind_sqli", "blind_ssrf", "blind_xss", "blind_cmdi",
        "saml_signature_wrapping", "sso_bypass", "oauth_token_theft", "pkce_bypass",
        "web_cache_deception", "cache_poisoning", "reflected_file_download",
        "aspnet_viewstate", "machinekey_exploitation",
        "http_method_tampering", "nginx_alias_traversal",
        "second_order_sqli", "ognl_injection",
    ]

    def test_new_vulnerability_subtypes_present(self) -> None:
        subtypes = NODE_TYPES["Vulnerability"]
        for expected in self.EXPECTED_VULN_SUBTYPES:
            self.assertIn(expected, subtypes, f"Missing Vulnerability subtype: {expected}")

    # ── Capability ──────────────────────────────────────────────────────

    EXPECTED_CAPABILITY_SUBTYPES = [
        "domain_controller_compromise", "kerberos_ticket_forgery",
        "container_escape_capability", "k8s_cluster_access",
        "email_account_compromise", "email_spoofing",
        "cache_poisoning_execution", "ci_pipeline_execution",
        "registry_persistence", "scheduled_task_persistence",
        "saml_assertion_forgery", "shadow_credentials", "webshell_persistence",
    ]

    def test_new_capability_subtypes_present(self) -> None:
        subtypes = NODE_TYPES["Capability"]
        for expected in self.EXPECTED_CAPABILITY_SUBTYPES:
            self.assertIn(expected, subtypes, f"Missing Capability subtype: {expected}")

    # ── Regression ──────────────────────────────────────────────────────

    def test_existing_technology_subtypes_preserved(self) -> None:
        original = ["wordpress", "php", "java", "python", "nodejs",
                     "nginx", "apache", "spring", "jenkins", "generic"]
        subtypes = NODE_TYPES["Technology"]
        for expected in original:
            self.assertIn(expected, subtypes, f"Regression — missing: {expected}")

    def test_existing_vulnerability_subtypes_preserved(self) -> None:
        original = [
            "sqli", "command_injection", "code_injection", "rce", "ssti",
            "ssrf", "xxe", "lfi", "path_traversal", "file_upload",
            "deserialization", "misconfig", "jwt_abuse", "oauth_misconfig",
            "idor", "xss", "open_redirect", "clickjacking", "csrf",
            "cors", "graphql_injection", "prototype_pollution",
            "s3_misconfig", "subdomain_takeover", "dns_rebinding",
            "dependency_confusion", "generic", "generic_high", "generic_critical",
        ]
        subtypes = NODE_TYPES["Vulnerability"]
        for expected in original:
            self.assertIn(expected, subtypes, f"Regression — missing: {expected}")

    def test_existing_capability_subtypes_preserved(self) -> None:
        original = [
            "db_access", "data_exfil", "rce_execution", "authenticated_access",
            "pivot", "cloud_access", "internal_discovery",
            "account_takeover", "session_hijacking", "phishing_amplification",
            "persistence", "code_exfiltration", "credential_harvesting",
            "lateral_movement", "metadata_access", "hvt_compromise",
            "supply_chain_compromise", "dos_capability",
        ]
        subtypes = NODE_TYPES["Capability"]
        for expected in original:
            self.assertIn(expected, subtypes, f"Regression — missing: {expected}")


class TaxonomyMapTests(TestCase):
    """Verify new TAXONOMY_MAP entries and first-match ordering."""

    # ── First-match ordering ────────────────────────────────────────────

    def test_blind_sqli_matched_before_sqli(self) -> None:
        result = _infer_taxonomy("Blind SQL Injection in login", "", 3)
        self.assertEqual(result["subtype"], "blind_sqli")

    def test_second_order_sqli(self) -> None:
        result = _infer_taxonomy("Second Order SQL Injection", "", 3)
        self.assertEqual(result["subtype"], "second_order_sqli")

    def test_plain_sqli_still_works(self) -> None:
        result = _infer_taxonomy("SQL Injection in search param", "", 3)
        self.assertEqual(result["subtype"], "sqli")

    # ── Blind variants ──────────────────────────────────────────────────

    def test_blind_ssrf(self) -> None:
        result = _infer_taxonomy("Blind SSRF via webhook", "", 3)
        self.assertEqual(result["subtype"], "blind_ssrf")

    def test_blind_cmdi(self) -> None:
        result = _infer_taxonomy("Blind Command Injection", "", 3)
        self.assertEqual(result["subtype"], "blind_cmdi")

    # ── Network / protocol ──────────────────────────────────────────────

    def test_http_request_smuggling(self) -> None:
        result = _infer_taxonomy("HTTP Request Smuggling CL.TE", "", 3)
        self.assertEqual(result["subtype"], "http_request_smuggling")

    # ── Active Directory ────────────────────────────────────────────────

    def test_ntlm_relay(self) -> None:
        result = _infer_taxonomy("NTLM Relay via SMB", "", 4)
        self.assertEqual(result["subtype"], "ntlm_relay")

    def test_kerberoasting(self) -> None:
        result = _infer_taxonomy("Kerberoasting SPN extraction", "", 3)
        self.assertEqual(result["subtype"], "kerberoasting")

    # ── Container / infra ───────────────────────────────────────────────

    def test_docker_socket(self) -> None:
        result = _infer_taxonomy("Docker Socket Exposed", "", 4)
        self.assertEqual(result["subtype"], "docker_socket_exposed")

    # ── Supply chain ────────────────────────────────────────────────────

    def test_github_actions_injection(self) -> None:
        result = _infer_taxonomy("GitHub Actions Injection via PR", "", 3)
        self.assertEqual(result["subtype"], "github_actions_injection")

    # ── Auth / SSO ──────────────────────────────────────────────────────

    def test_saml_signature_wrapping(self) -> None:
        result = _infer_taxonomy("SAML Signature Wrapping attack", "", 4)
        self.assertEqual(result["subtype"], "saml_signature_wrapping")

    # ── .NET ────────────────────────────────────────────────────────────

    def test_aspnet_viewstate(self) -> None:
        result = _infer_taxonomy("ASP.NET ViewState Deserialization", "", 4)
        self.assertEqual(result["subtype"], "aspnet_viewstate")

    # ── Modern API / web ────────────────────────────────────────────────

    def test_race_condition(self) -> None:
        result = _infer_taxonomy("Race Condition in checkout flow", "", 2)
        self.assertEqual(result["subtype"], "race_condition")

    def test_mass_assignment(self) -> None:
        result = _infer_taxonomy("Mass Assignment in user profile", "", 3)
        self.assertEqual(result["subtype"], "mass_assignment")

    # ── Email ───────────────────────────────────────────────────────────

    def test_spf_dmarc_bypass(self) -> None:
        result = _infer_taxonomy("SPF DMARC Bypass allows spoofing", "", 2)
        self.assertEqual(result["subtype"], "spf_dmarc_bypass")

    # ── Misc ────────────────────────────────────────────────────────────

    def test_ognl_injection(self) -> None:
        result = _infer_taxonomy("OGNL injection in Struts", "", 4)
        self.assertEqual(result["subtype"], "ognl_injection")

    # ── Existing keywords still work ────────────────────────────────────

    def test_existing_xss_keyword(self) -> None:
        result = _infer_taxonomy("Reflected XSS in search", "", 2)
        self.assertEqual(result["subtype"], "xss")

    def test_existing_rce_keyword(self) -> None:
        result = _infer_taxonomy("Remote Code Execution via upload", "", 4)
        self.assertEqual(result["subtype"], "rce")

    def test_existing_ssrf_keyword(self) -> None:
        result = _infer_taxonomy("SSRF in image proxy", "", 3)
        self.assertEqual(result["subtype"], "ssrf")

    def test_existing_sqli_keyword(self) -> None:
        """Plain 'sqli' keyword must still resolve correctly."""
        result = _infer_taxonomy("sqli found in parameter", "", 2)
        self.assertEqual(result["subtype"], "sqli")


# ═══════════════════════════════════════════════════════════════════════
# Phase 2 tests: Constraint Engine Expansion
# ═══════════════════════════════════════════════════════════════════════


class ConstraintFlagTests(TestCase):
    """Verify all 18 flags are present in _CONSTRAINT_FLAGS."""

    EXPECTED_FLAGS = [
        "requires_victim",
        "requires_php",
        "requires_java",
        "requires_python",
        "requires_wordpress",
        "endpoint_requires_auth",
        "requires_dotnet",
        "requires_kubernetes",
        "requires_docker",
        "requires_ruby",
        "requires_nodejs",
        "requires_active_directory",
        "requires_mssql",
        "requires_oracle",
        "requires_redis",
        "requires_drupal",
        "requires_joomla",
        "requires_magento",
    ]

    def test_all_18_flags_present(self) -> None:
        for flag in self.EXPECTED_FLAGS:
            self.assertIn(flag, _CONSTRAINT_FLAGS, f"Missing flag: {flag}")

    def test_flag_count(self) -> None:
        self.assertEqual(len(_CONSTRAINT_FLAGS), 18)

    def test_original_six_flags_preserved(self) -> None:
        original = [
            "requires_victim", "requires_php", "requires_java",
            "requires_python", "requires_wordpress", "endpoint_requires_auth",
        ]
        for flag in original:
            self.assertIn(flag, _CONSTRAINT_FLAGS, f"Regression — missing: {flag}")


class ConstraintGateTests(TestCase):
    """Verify each new gate blocks without tech and passes with tech."""

    def setUp(self) -> None:
        self.engine = ConstraintEngine()

    def _base_step(self, **overrides) -> dict:
        step = {"action": "test_action", "confidence": 0.8}
        step.update(overrides)
        return step

    # ── Active Directory ───────────────────────────────────────────────

    def test_active_directory_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_active_directory=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_active_directory_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_active_directory_tech = True
        step = self._base_step(requires_active_directory=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Kubernetes ─────────────────────────────────────────────────────

    def test_kubernetes_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_kubernetes=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_kubernetes_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_kubernetes_tech = True
        step = self._base_step(requires_kubernetes=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Docker ─────────────────────────────────────────────────────────

    def test_docker_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_docker=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_docker_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_docker_tech = True
        step = self._base_step(requires_docker=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Redis ──────────────────────────────────────────────────────────

    def test_redis_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_redis=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_redis_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_redis_tech = True
        step = self._base_step(requires_redis=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Drupal ─────────────────────────────────────────────────────────

    def test_drupal_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_drupal=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_drupal_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_drupal_tech = True
        step = self._base_step(requires_drupal=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Joomla ─────────────────────────────────────────────────────────

    def test_joomla_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_joomla=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_joomla_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_joomla_tech = True
        step = self._base_step(requires_joomla=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Magento ────────────────────────────────────────────────────────

    def test_magento_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_magento=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_magento_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_magento_tech = True
        step = self._base_step(requires_magento=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Ruby ───────────────────────────────────────────────────────────

    def test_ruby_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_ruby=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_ruby_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_ruby_tech = True
        step = self._base_step(requires_ruby=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Node.js ────────────────────────────────────────────────────────

    def test_nodejs_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_nodejs=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_nodejs_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_nodejs_tech = True
        step = self._base_step(requires_nodejs=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── .NET ───────────────────────────────────────────────────────────

    def test_dotnet_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_dotnet=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_dotnet_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_dotnet_tech = True
        step = self._base_step(requires_dotnet=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── MSSQL ──────────────────────────────────────────────────────────

    def test_mssql_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_mssql=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_mssql_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_mssql_tech = True
        step = self._base_step(requires_mssql=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Oracle ─────────────────────────────────────────────────────────

    def test_oracle_gate_blocks(self) -> None:
        ctx = PathContext()
        step = self._base_step(requires_oracle=True)
        self.assertFalse(self.engine.validate_step(step, ctx))

    def test_oracle_gate_passes(self) -> None:
        ctx = PathContext()
        ctx.has_oracle_tech = True
        step = self._base_step(requires_oracle=True)
        self.assertTrue(self.engine.validate_step(step, ctx))

    # ── Unrestricted pass ──────────────────────────────────────────────

    def test_no_flag_set_passes_unrestricted(self) -> None:
        ctx = PathContext()
        step = self._base_step()
        self.assertTrue(self.engine.validate_step(step, ctx))


class ConstraintContextUpdateTests(TestCase):
    """Verify update_context tech propagation for new technologies."""

    def setUp(self) -> None:
        self.engine = ConstraintEngine()

    def _step_with_subtype(self, subtype: str) -> dict:
        return {"action": "test", "confidence": 0.8, "to_subtype": subtype, "to_id": f"node-{subtype}"}

    # ── .NET / ASP.NET ─────────────────────────────────────────────────

    def test_dotnet_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("dotnet"), ctx)
        self.assertTrue(ctx.has_dotnet_tech)

    def test_aspnet_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("aspnet"), ctx)
        self.assertTrue(ctx.has_dotnet_tech)

    def test_csharp_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("csharp"), ctx)
        self.assertTrue(ctx.has_dotnet_tech)

    # ── Kubernetes ─────────────────────────────────────────────────────

    def test_kubernetes_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("kubernetes"), ctx)
        self.assertTrue(ctx.has_kubernetes_tech)

    def test_k8s_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("k8s"), ctx)
        self.assertTrue(ctx.has_kubernetes_tech)

    # ── Docker ─────────────────────────────────────────────────────────

    def test_docker_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("docker"), ctx)
        self.assertTrue(ctx.has_docker_tech)

    def test_container_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("container"), ctx)
        self.assertTrue(ctx.has_docker_tech)

    # ── Ruby ───────────────────────────────────────────────────────────

    def test_ruby_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("ruby"), ctx)
        self.assertTrue(ctx.has_ruby_tech)

    def test_rails_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("rails"), ctx)
        self.assertTrue(ctx.has_ruby_tech)

    # ── Node.js ────────────────────────────────────────────────────────

    def test_nodejs_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("nodejs"), ctx)
        self.assertTrue(ctx.has_nodejs_tech)

    def test_node_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("node"), ctx)
        self.assertTrue(ctx.has_nodejs_tech)

    def test_express_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("express"), ctx)
        self.assertTrue(ctx.has_nodejs_tech)

    # ── Active Directory ───────────────────────────────────────────────

    def test_active_directory_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("active_directory"), ctx)
        self.assertTrue(ctx.has_active_directory_tech)

    def test_ldap_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("ldap"), ctx)
        self.assertTrue(ctx.has_active_directory_tech)

    def test_exchange_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("exchange"), ctx)
        self.assertTrue(ctx.has_active_directory_tech)

    # ── Redis ──────────────────────────────────────────────────────────

    def test_redis_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("redis"), ctx)
        self.assertTrue(ctx.has_redis_tech)

    # ── Drupal ─────────────────────────────────────────────────────────

    def test_drupal_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("drupal"), ctx)
        self.assertTrue(ctx.has_drupal_tech)

    # ── Joomla ─────────────────────────────────────────────────────────

    def test_joomla_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("joomla"), ctx)
        self.assertTrue(ctx.has_joomla_tech)

    # ── Magento ────────────────────────────────────────────────────────

    def test_magento_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("magento"), ctx)
        self.assertTrue(ctx.has_magento_tech)

    # ── MSSQL ──────────────────────────────────────────────────────────

    def test_mssql_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("mssql"), ctx)
        self.assertTrue(ctx.has_mssql_tech)

    def test_sqlserver_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("sqlserver"), ctx)
        self.assertTrue(ctx.has_mssql_tech)

    # ── Oracle ─────────────────────────────────────────────────────────

    def test_oracle_propagation(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("oracle"), ctx)
        self.assertTrue(ctx.has_oracle_tech)

    # ── Existing propagation regression ────────────────────────────────

    def test_php_propagation_still_works(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("php"), ctx)
        self.assertTrue(ctx.has_php_tech)

    def test_java_propagation_still_works(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("java"), ctx)
        self.assertTrue(ctx.has_java_tech)

    def test_wordpress_propagation_still_works(self) -> None:
        ctx = PathContext()
        self.engine.update_context(self._step_with_subtype("wordpress"), ctx)
        self.assertTrue(ctx.has_wordpress_tech)


# ═══════════════════════════════════════════════════════════════════════
# Phase 3 — Existing Rules Addition Tests
# ═══════════════════════════════════════════════════════════════════════


class ExistingRulesAdditionTests(TestCase):
    """Verify the 29 new rules added to existing YAML rule files."""

    def setUp(self) -> None:
        from apme.engine.rules_engine import RulesEngine
        self.engine = RulesEngine()
        self.rule_names = {r["name"] for r in self.engine._rules}

    # ── Aggregate count ───────────────────────────────────────────────

    def test_total_rule_count_at_least_105(self) -> None:
        self.assertGreaterEqual(
            len(self.engine._rules), 105,
            f"Expected >= 105 rules (76 existing + 29 new), got {len(self.engine._rules)}",
        )

    # ── a_injection rules (7) ─────────────────────────────────────────

    def test_blind_sqli_to_db_access(self) -> None:
        self.assertIn("blind_sqli_to_db_access", self.rule_names)

    def test_blind_sqli_verified_to_db_access(self) -> None:
        self.assertIn("blind_sqli_verified_to_db_access", self.rule_names)

    def test_second_order_sqli_to_account_takeover(self) -> None:
        self.assertIn("second_order_sqli_to_account_takeover", self.rule_names)

    def test_nosql_injection_to_auth_bypass(self) -> None:
        self.assertIn("nosql_injection_to_auth_bypass", self.rule_names)

    def test_ognl_injection_to_rce(self) -> None:
        self.assertIn("ognl_injection_to_rce", self.rule_names)

    def test_blind_cmdi_to_rce(self) -> None:
        self.assertIn("blind_cmdi_to_rce", self.rule_names)

    def test_blind_cmdi_verified_to_rce(self) -> None:
        self.assertIn("blind_cmdi_verified_to_rce", self.rule_names)

    # ── c_server_side rules (5) ───────────────────────────────────────

    def test_blind_ssrf_to_metadata_access(self) -> None:
        self.assertIn("blind_ssrf_to_metadata_access", self.rule_names)

    def test_blind_ssrf_verified_to_cloud_access(self) -> None:
        self.assertIn("blind_ssrf_verified_to_cloud_access", self.rule_names)

    def test_ssrf_to_redis_rce(self) -> None:
        self.assertIn("ssrf_to_redis_rce", self.rule_names)

    def test_http_request_smuggling_to_auth_bypass(self) -> None:
        self.assertIn("http_request_smuggling_to_auth_bypass", self.rule_names)

    def test_http_request_smuggling_to_data_exfil(self) -> None:
        self.assertIn("http_request_smuggling_to_data_exfil", self.rule_names)

    # ── e_auth_identity rules (8) ─────────────────────────────────────

    def test_saml_signature_wrapping_to_auth_bypass(self) -> None:
        self.assertIn("saml_signature_wrapping_to_auth_bypass", self.rule_names)

    def test_saml_to_account_takeover(self) -> None:
        self.assertIn("saml_to_account_takeover", self.rule_names)

    def test_oauth_token_theft_to_account_takeover(self) -> None:
        self.assertIn("oauth_token_theft_to_account_takeover", self.rule_names)

    def test_pkce_bypass_to_auth_access(self) -> None:
        self.assertIn("pkce_bypass_to_auth_access", self.rule_names)

    def test_session_fixation_to_account_takeover(self) -> None:
        self.assertIn("session_fixation_to_account_takeover", self.rule_names)

    def test_account_enumeration_to_credential_harvesting(self) -> None:
        self.assertIn("account_enumeration_to_credential_harvesting", self.rule_names)

    def test_broken_object_level_to_data_exfil(self) -> None:
        self.assertIn("broken_object_level_to_data_exfil", self.rule_names)

    def test_parameter_tampering_to_privilege_escalation(self) -> None:
        self.assertIn("parameter_tampering_to_privilege_escalation", self.rule_names)

    # ── f_client_side rules (5) ───────────────────────────────────────

    def test_blind_xss_to_credential_harvesting(self) -> None:
        self.assertIn("blind_xss_to_credential_harvesting", self.rule_names)

    def test_dom_xss_to_account_takeover(self) -> None:
        self.assertIn("dom_xss_to_account_takeover", self.rule_names)

    def test_websocket_hijacking_to_auth_access(self) -> None:
        self.assertIn("websocket_hijacking_to_auth_access", self.rule_names)

    def test_iframe_injection_to_phishing(self) -> None:
        self.assertIn("iframe_injection_to_phishing", self.rule_names)

    def test_postmessage_origin_bypass_to_data_exfil(self) -> None:
        self.assertIn("postmessage_origin_bypass_to_data_exfil", self.rule_names)

    # ── g_info_disclosure rules (4) ───────────────────────────────────

    def test_nginx_alias_traversal_to_data_exfil(self) -> None:
        self.assertIn("nginx_alias_traversal_to_data_exfil", self.rule_names)

    def test_http_method_tampering_to_data_exfil(self) -> None:
        self.assertIn("http_method_tampering_to_data_exfil", self.rule_names)

    def test_reflected_file_download_to_credential_harvesting(self) -> None:
        self.assertIn("reflected_file_download_to_credential_harvesting", self.rule_names)

    def test_web_cache_deception_to_data_exfil(self) -> None:
        self.assertIn("web_cache_deception_to_data_exfil", self.rule_names)

    # ── Constraint flag spot-checks ───────────────────────────────────

    def test_ognl_rule_has_requires_java(self) -> None:
        rule = next(r for r in self.engine._rules if r["name"] == "ognl_injection_to_rce")
        self.assertTrue(rule["then"]["create_edge"].get("requires_java"))

    def test_ssrf_redis_rule_has_requires_redis(self) -> None:
        rule = next(r for r in self.engine._rules if r["name"] == "ssrf_to_redis_rce")
        self.assertTrue(rule["then"]["create_edge"].get("requires_redis"))


# ═══════════════════════════════════════════════════════════════════════
# Phase 4 — New Rule Category Files (74 rules across 8 files)
# ═══════════════════════════════════════════════════════════════════════


class NewRuleCategoryTests(TestCase):
    """Verify 74 new rules from 8 new YAML rule category files (n_ through u_)."""

    def setUp(self) -> None:
        from apme.engine.rules_engine import RulesEngine
        self.engine = RulesEngine()
        self.rule_names = {r["name"] for r in self.engine._rules}

    def _assert_rules(self, *names: str) -> None:
        for name in names:
            self.assertIn(name, self.rule_names, f"Missing rule: {name}")

    def _rule(self, name: str) -> dict:
        return next(r for r in self.engine._rules if r["name"] == name)

    # ── Aggregate count ──────────────────────────────────────────────────

    def test_total_rule_count_approximately_179(self) -> None:
        count = len(self.engine._rules)
        self.assertGreaterEqual(count, 174, f"Expected >= 174 rules, got {count}")
        self.assertLessEqual(count, 184, f"Expected <= 184 rules, got {count}")

    # ── n_network_protocol.yaml (8 rules) ────────────────────────────────

    def test_network_protocol_rules_loaded(self) -> None:
        self._assert_rules(
            "tls_downgrade_to_data_exfil",
            "dns_cache_poisoning_to_phishing",
            "dns_cache_poisoning_to_pivot",
            "cache_poisoning_to_auth_bypass",
            "cache_poisoning_to_account_takeover",
            "http_desync_to_cache_poisoning",
            "tcp_sequence_prediction_to_pivot",
            "smtp_relay_to_email_spoofing",
        )

    # ── o_container_infra.yaml (10 rules) ────────────────────────────────

    def test_container_infra_rules_loaded(self) -> None:
        self._assert_rules(
            "docker_socket_exposed_to_container_escape",
            "container_escape_to_pivot",
            "container_escape_to_rce_execution",
            "privileged_container_to_escape",
            "k8s_rbac_misconfig_to_cluster_access",
            "k8s_secret_exposure_to_credential_harvesting",
            "k8s_cluster_access_to_lateral_movement",
            "k8s_cluster_access_to_persistence",
            "k8s_cluster_access_to_supply_chain",
            "docker_registry_exposure_to_code_exfil",
        )

    def test_docker_rules_have_requires_docker(self) -> None:
        docker_rules = [
            "docker_socket_exposed_to_container_escape",
            "container_escape_to_pivot",
            "container_escape_to_rce_execution",
            "privileged_container_to_escape",
            "docker_registry_exposure_to_code_exfil",
        ]
        for name in docker_rules:
            rule = self._rule(name)
            self.assertTrue(
                rule["then"]["create_edge"].get("requires_docker"),
                f"Rule {name} missing requires_docker",
            )

    def test_k8s_rules_have_requires_kubernetes(self) -> None:
        k8s_rules = [
            "k8s_rbac_misconfig_to_cluster_access",
            "k8s_secret_exposure_to_credential_harvesting",
            "k8s_cluster_access_to_lateral_movement",
            "k8s_cluster_access_to_persistence",
            "k8s_cluster_access_to_supply_chain",
        ]
        for name in k8s_rules:
            rule = self._rule(name)
            self.assertTrue(
                rule["then"]["create_edge"].get("requires_kubernetes"),
                f"Rule {name} missing requires_kubernetes",
            )

    # ── p_active_directory.yaml (14 rules) ───────────────────────────────

    def test_active_directory_rules_loaded(self) -> None:
        self._assert_rules(
            "ntlm_relay_to_lateral_movement",
            "ntlm_relay_to_domain_admin",
            "pass_the_hash_to_lateral_movement",
            "pass_the_ticket_to_lateral_movement",
            "kerberoasting_to_credential_harvesting",
            "kerberoasting_to_lateral_movement",
            "asrep_roasting_to_credential_harvesting",
            "dcsync_to_credential_harvesting",
            "dcsync_to_hvt_compromise",
            "gpo_abuse_to_lateral_movement",
            "gpo_abuse_to_persistence",
            "shadow_credentials_to_account_takeover",
            "kerberos_ticket_forgery_to_hvt_compromise",
            "credential_harvesting_to_domain_controller",
        )

    def test_all_ad_rules_have_requires_active_directory(self) -> None:
        ad_rules = [
            "ntlm_relay_to_lateral_movement",
            "ntlm_relay_to_domain_admin",
            "pass_the_hash_to_lateral_movement",
            "pass_the_ticket_to_lateral_movement",
            "kerberoasting_to_credential_harvesting",
            "kerberoasting_to_lateral_movement",
            "asrep_roasting_to_credential_harvesting",
            "dcsync_to_credential_harvesting",
            "dcsync_to_hvt_compromise",
            "gpo_abuse_to_lateral_movement",
            "gpo_abuse_to_persistence",
            "shadow_credentials_to_account_takeover",
            "kerberos_ticket_forgery_to_hvt_compromise",
            "credential_harvesting_to_domain_controller",
        ]
        for name in ad_rules:
            rule = self._rule(name)
            self.assertTrue(
                rule["then"]["create_edge"].get("requires_active_directory"),
                f"Rule {name} missing requires_active_directory",
            )

    # ── q_api_web_modern.yaml (10 rules) ─────────────────────────────────

    def test_api_web_modern_rules_loaded(self) -> None:
        self._assert_rules(
            "mass_assignment_to_privilege_escalation",
            "mass_assignment_verified_to_account_takeover",
            "parameter_pollution_to_auth_bypass",
            "graphql_mutation_to_account_takeover",
            "graphql_mutation_to_data_exfil",
            "api_versioning_bypass_to_auth_bypass",
            "api_versioning_bypass_to_data_exfil",
            "insecure_websocket_to_auth_bypass",
            "race_condition_to_privilege_escalation",
            "race_condition_to_account_takeover",
        )

    # ── r_email_security.yaml (8 rules) ──────────────────────────────────

    def test_email_security_rules_loaded(self) -> None:
        self._assert_rules(
            "spf_dmarc_bypass_to_email_spoofing",
            "spf_dmarc_bypass_to_phishing_amplification",
            "email_header_injection_to_phishing",
            "email_header_injection_to_account_takeover",
            "email_account_compromise_to_lateral_movement",
            "email_account_compromise_to_credential_harvesting",
            "email_spoofing_to_hvt_compromise",
            "mx_misconfig_to_email_spoofing",
        )

    # ── s_supply_chain.yaml (8 rules) ────────────────────────────────────

    def test_supply_chain_rules_loaded(self) -> None:
        self._assert_rules(
            "github_actions_injection_to_ci_execution",
            "ci_artifact_poisoning_to_supply_chain",
            "typosquatting_to_supply_chain",
            "compromised_registry_to_rce_execution",
            "ci_execution_to_credential_harvesting",
            "ci_execution_to_code_exfil",
            "github_token_to_ci_execution",
            "supply_chain_compromise_to_hvt_compromise",
        )

    # ── t_dotnet_cms.yaml (8 rules) ──────────────────────────────────────

    def test_dotnet_cms_rules_loaded(self) -> None:
        self._assert_rules(
            "aspnet_viewstate_to_rce",
            "machinekey_to_rce",
            "drupal_rce_to_execution",
            "drupal_sqli_to_db_access",
            "joomla_rce_to_execution",
            "magento_sqli_to_db_access",
            "rails_mass_assign_to_privilege_escalation",
            "nodejs_prototype_pollution_to_rce",
        )

    def test_dotnet_rules_have_requires_dotnet(self) -> None:
        dotnet_rules = ["aspnet_viewstate_to_rce", "machinekey_to_rce"]
        for name in dotnet_rules:
            rule = self._rule(name)
            self.assertTrue(
                rule["then"]["create_edge"].get("requires_dotnet"),
                f"Rule {name} missing requires_dotnet",
            )

    def test_drupal_rules_have_requires_drupal(self) -> None:
        drupal_rules = ["drupal_rce_to_execution", "drupal_sqli_to_db_access"]
        for name in drupal_rules:
            rule = self._rule(name)
            self.assertTrue(
                rule["then"]["create_edge"].get("requires_drupal"),
                f"Rule {name} missing requires_drupal",
            )

    def test_nodejs_rule_has_requires_nodejs(self) -> None:
        rule = self._rule("nodejs_prototype_pollution_to_rce")
        self.assertTrue(rule["then"]["create_edge"].get("requires_nodejs"))

    def test_joomla_rule_has_requires_joomla(self) -> None:
        rule = self._rule("joomla_rce_to_execution")
        self.assertTrue(rule["then"]["create_edge"].get("requires_joomla"))

    def test_magento_rule_has_requires_magento(self) -> None:
        rule = self._rule("magento_sqli_to_db_access")
        self.assertTrue(rule["then"]["create_edge"].get("requires_magento"))

    def test_rails_rule_has_requires_ruby(self) -> None:
        rule = self._rule("rails_mass_assign_to_privilege_escalation")
        self.assertTrue(rule["then"]["create_edge"].get("requires_ruby"))

    # ── u_persistence_chains.yaml (8 rules) ──────────────────────────────

    def test_persistence_chains_rules_loaded(self) -> None:
        self._assert_rules(
            "rce_execution_to_webshell_persistence",
            "rce_execution_to_scheduled_task",
            "rce_execution_to_registry_persistence",
            "file_upload_to_webshell",
            "admin_access_to_cron_persistence",
            "persistence_to_lateral_movement",
            "persistence_to_credential_harvesting",
            "webshell_to_data_exfil",
        )

    def test_registry_persistence_requires_dotnet(self) -> None:
        rule = self._rule("rce_execution_to_registry_persistence")
        self.assertTrue(rule["then"]["create_edge"].get("requires_dotnet"))

    # ── Cross-file constraint spot-checks ────────────────────────────────

    def test_insecure_websocket_requires_victim(self) -> None:
        rule = self._rule("insecure_websocket_to_auth_bypass")
        self.assertTrue(rule["then"]["create_edge"].get("requires_victim"))

    def test_email_spoofing_to_hvt_requires_victim(self) -> None:
        rule = self._rule("email_spoofing_to_hvt_compromise")
        self.assertTrue(rule["then"]["create_edge"].get("requires_victim"))

    def test_email_header_injection_to_account_takeover_requires_victim(self) -> None:
        rule = self._rule("email_header_injection_to_account_takeover")
        self.assertTrue(rule["then"]["create_edge"].get("requires_victim"))
