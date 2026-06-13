"""APME Enhancement 2 — Phase 1 tests: Schema & Ingestion Extensions."""
from django.test import TestCase

from apme.graph.schema import NODE_TYPES
from apme.ingestion.vulnerabilities import TAXONOMY_MAP, _infer_taxonomy


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
