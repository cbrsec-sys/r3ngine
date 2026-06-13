# APME Enhancement 2 — Design Spec
**Date**: 2026-06-13  
**Status**: Approved — ready for implementation planning  
**Scope**: Full attack surface — web app + infrastructure + AD/Kerberos + supply chain + email + network  
**Primary FP reduction strategy**: Tiered confidence system  
**Tech gating strategy**: Extend constraint flags (backwards-compatible)

---

## Overview

The Attack Path Modelling Engine (APME) currently has 76 rules across 13 YAML categories, 11 constraints, a 6-factor scorer, and a BFS+DFS+Dijkstra pathfinder. This design expands it to approximately 179 rules across 20 categories, 22 constraints, a 10-factor scorer, and a pathfinder with 6 targeted fixes — all without disrupting the existing architecture.

The primary goal is to reduce noise and false positives while achieving high-confidence, insightful, comprehensive attack path results across the full attack surface.

---

## Section 1: Schema & Ingestion Extensions

### 1.1 New Technology Subtypes (`schema.py`)

Add to `NODE_TYPES["Technology"]`:
```python
"dotnet", "ruby", "rails", "nodejs", "react", "angular", "vue",
"kubernetes", "docker", "terraform", "ansible",
"drupal", "joomla", "magento", "laravel",
"mssql", "oracle", "redis", "elasticsearch", "mongodb",
"exchange", "active_directory", "ldap"
```

### 1.2 New Vulnerability Subtypes (`schema.py`)

Add to `NODE_TYPES["Vulnerability"]`:
```python
# Network protocol
"http_request_smuggling", "tls_downgrade", "dns_cache_poisoning",
# Container / infrastructure
"docker_socket_exposed", "container_escape", "k8s_rbac_misconfig",
"privileged_container", "k8s_secret_exposure",
# Active Directory / Windows
"ntlm_relay", "pass_the_hash", "kerberoasting", "asrep_roasting",
"dcsync_privilege", "gpo_abuse", "pass_the_ticket",
# Modern API / web
"websocket_hijacking", "mass_assignment", "parameter_pollution",
"graphql_mutation_abuse", "api_versioning_bypass",
# Email security
"spf_dmarc_bypass", "email_header_injection",
# Business logic
"race_condition", "account_enumeration", "session_fixation",
"business_logic_bypass", "parameter_tampering",
# Supply chain / CI-CD
"typosquatting", "compromised_registry", "ci_artifact_poisoning",
"github_actions_injection",
# Blind injection variants
"blind_sqli", "blind_ssrf", "blind_xss", "blind_cmdi",
# Auth / SSO
"saml_signature_wrapping", "sso_bypass", "oauth_token_theft", "pkce_bypass",
# Web cache
"web_cache_deception", "cache_poisoning", "reflected_file_download",
# .NET
"aspnet_viewstate", "machinekey_exploitation",
# Misc
"http_method_tampering", "nginx_alias_traversal", "second_order_sqli",
"ognl_injection",
```

### 1.3 New Capability Subtypes (`schema.py`)

Add to `NODE_TYPES["Capability"]`:
```python
"domain_controller_compromise", "kerberos_ticket_forgery",
"container_escape_capability", "k8s_cluster_access",
"email_account_compromise", "email_spoofing",
"cache_poisoning_execution", "ci_pipeline_execution",
"registry_persistence", "scheduled_task_persistence",
"saml_assertion_forgery", "shadow_credentials", "webshell_persistence",
```

### 1.4 Ingestion Changes (`ingestion/vulnerabilities.py`)

**New TAXONOMY_MAP entries** (~50 new keyword mappings) covering all new vulnerability subtypes listed above, following the existing `keyword → {subtype, cwe, technique}` pattern.

**New node properties** added during ingestion:
- `is_poc` — from `vuln.is_poc` (already on model from Vulnx Phase 4-6)
- `exploit_url` — already extracted; ensure non-empty check
- `cve_published_date` — ISO date string from CVE enrichment pipeline
- `has_metasploit` — inferred from `template_id` prefix `msf/` or `metasploit`
- `cvss_vector` — store CVSS vector string for future attack complexity extraction

### 1.5 No Breaking Changes

All schema additions are additive. Existing `generic`, `generic_high`, `generic_critical` fallback subtypes remain. The TAXONOMY_MAP keyword-match-first approach means new keywords slot in without affecting existing matches.

---

## Section 2: Constraint Engine Expansion (11 → 22)

### 2.1 New Constraint Flags in YAML DSL

Extend `_CONSTRAINT_FLAGS` in `rules_engine.py`:
```python
_CONSTRAINT_FLAGS = (
    # Existing 6
    "requires_victim", "requires_php", "requires_java",
    "requires_python", "requires_wordpress", "endpoint_requires_auth",
    # New 12
    "requires_dotnet", "requires_kubernetes", "requires_docker",
    "requires_ruby", "requires_nodejs", "requires_active_directory",
    "requires_mssql", "requires_oracle", "requires_redis",
    "requires_drupal", "requires_joomla", "requires_magento",
)
```

### 2.2 New `PathContext` Fields

```python
# Technology context — new
has_dotnet_tech: bool = False
has_kubernetes_tech: bool = False
has_docker_tech: bool = False
has_ruby_tech: bool = False
has_nodejs_tech: bool = False
has_active_directory_tech: bool = False
has_mssql_tech: bool = False
has_oracle_tech: bool = False
has_redis_tech: bool = False
has_drupal_tech: bool = False
has_joomla_tech: bool = False
has_magento_tech: bool = False
```

### 2.3 New Constraint Checks (added after existing 11, in `validate_step`)

| # | Name | Gate condition | Purpose |
|---|------|---------------|---------|
| 12 | .NET gate | `requires_dotnet` + `not context.has_dotnet_tech` | ASP.NET ViewState / MachineKey attacks only on .NET stacks |
| 13 | Kubernetes gate | `requires_kubernetes` + `not context.has_kubernetes_tech` | K8s RBAC / pod escape only if K8s detected |
| 14 | Docker gate | `requires_docker` + `not context.has_docker_tech` | docker.sock / container escape only in containerised environments |
| 15 | Ruby/Rails gate | `requires_ruby` + `not context.has_ruby_tech` | Rails-specific mass assignment / RCE only on Ruby stacks |
| 16 | Node.js gate | `requires_nodejs` + `not context.has_nodejs_tech` | Prototype pollution RCE, npm supply chain only on Node.js |
| 17 | Active Directory gate | `requires_active_directory` + `not context.has_active_directory_tech` | Pass-the-Hash / Kerberoasting only when AD is in scope |
| 18 | Redis gate | `requires_redis` + `not context.has_redis_tech` | Redis SSRF/RCE only when Redis detected |
| 19 | Drupal gate | `requires_drupal` + `not context.has_drupal_tech` | Drupal-specific RCEs |
| 20 | Joomla gate | `requires_joomla` + `not context.has_joomla_tech` | Joomla-specific vulns |
| 21 | Magento gate | `requires_magento` + `not context.has_magento_tech` | Magento SQLi / RCE |
| 22 | Unvalidated high-score cap | `validated_count == 0 AND not has_any_signal AND score >= 0.70` → classify as `medium` | Prevents unverified chains from reaching `high` or `critical` |

Note: Constraint 22 is enforced in the scorer's `_classify` method (see Section 4), not in `validate_step`, since it requires the full path score.

### 2.4 `update_context` Additions

Extend technology propagation in `update_context` to cover all new `to_subtype` values:
```python
elif to_subtype in ("dotnet", "csharp", "aspnet"): context.has_dotnet_tech = True
elif to_subtype in ("kubernetes", "k8s"):           context.has_kubernetes_tech = True
elif to_subtype in ("docker", "container"):         context.has_docker_tech = True
elif to_subtype in ("ruby", "rails"):               context.has_ruby_tech = True
elif to_subtype in ("nodejs", "node", "express"):   context.has_nodejs_tech = True
elif to_subtype in ("active_directory", "ldap", "exchange"): context.has_active_directory_tech = True
elif to_subtype == "redis":                         context.has_redis_tech = True
elif to_subtype == "drupal":                        context.has_drupal_tech = True
elif to_subtype == "joomla":                        context.has_joomla_tech = True
elif to_subtype == "magento":                       context.has_magento_tech = True
elif to_subtype in ("mssql", "sqlserver"):          context.has_mssql_tech = True
elif to_subtype in ("oracle", "orcl"):              context.has_oracle_tech = True
```

---

## Section 3: Rules Expansion (76 → ~220 Rules, 20 Categories)

### Confidence Tier System

All new rules follow this tiered confidence assignment to minimise false positives:

| Tier | Confidence | Conditions | Rationale |
|------|-----------|-----------|-----------|
| Speculative | 0.35–0.50 | No tech gate, no validation | Will classify as speculative; shown for completeness |
| Low-mid | 0.55–0.65 | Severity threshold OR victim interaction | Some signal present |
| Mid | 0.65–0.75 | Tech gate OR known pattern | Plausible, not confirmed |
| High | 0.80–0.90 | `validated:True` OR tech gate + severity | Strong signal |
| Confirmed | 0.90–0.95 | `validated:True` + tech gate + severity | Near-certain in context |

### 3.1 Additions to Existing Files

**a_injection.yaml** — +7 rules:
- `blind_sqli_to_db_access` (T1190, 0.55)
- `blind_sqli_verified_to_db_access` (T1190, 0.85, `validated:True`)
- `second_order_sqli_to_account_takeover` (T1190, 0.60, `severity:>=3`)
- `nosql_injection_to_auth_bypass` (T1190, 0.75)
- `ognl_injection_to_rce` (T1059, 0.90, `requires_java:true`)
- `blind_cmdi_to_rce` (T1059, 0.55)
- `blind_cmdi_verified_to_rce` (T1059, 0.90, `validated:True`)

**c_server_side.yaml** — +5 rules:
- `blind_ssrf_to_metadata_access` (T1552.005, 0.50)
- `blind_ssrf_verified_to_cloud_access` (T1552.005, 0.80, `validated:True`)
- `ssrf_to_redis_rce` (T1090, 0.75, `requires_redis:true`)
- `http_request_smuggling_to_auth_bypass` (T1557, 0.70)
- `http_request_smuggling_to_data_exfil` (T1557, 0.65)

**e_auth_identity.yaml** — +8 rules:
- `saml_signature_wrapping_to_auth_bypass` (T1606.002, 0.85)
- `saml_to_account_takeover` (T1606.002, 0.80, `validated:True`)
- `oauth_token_theft_to_account_takeover` (T1528, 0.80)
- `pkce_bypass_to_auth_access` (T1078.004, 0.75)
- `session_fixation_to_account_takeover` (T1563, 0.70, `requires_victim:true`)
- `account_enumeration_to_credential_harvesting` (T1589.001, 0.55)
- `broken_object_level_to_data_exfil` (T1530, 0.75, `validated:True`)
- `parameter_tampering_to_privilege_escalation` (T1548, 0.65, `validated:True`)

**f_client_side.yaml** — +5 rules:
- `blind_xss_to_credential_harvesting` (T1539, 0.50, `requires_victim:true`)
- `dom_xss_to_session_hijack` (T1539, 0.65, `requires_victim:true`)
- `websocket_hijacking_to_auth_access` (T1185, 0.70, `requires_victim:true`)
- `iframe_injection_to_phishing` (T1566.002, 0.55, `requires_victim:true`)
- `postmessage_origin_bypass_to_data_exfil` (T1185, 0.60, `requires_nodejs:true`, `requires_victim:true`)

**g_info_disclosure.yaml** — +4 rules:
- `nginx_alias_traversal_to_data_exfil` (T1083, 0.75)
- `http_method_tampering_to_data_exfil` (T1190, 0.60)
- `reflected_file_download_to_credential_harvesting` (T1566.002, 0.65, `requires_victim:true`)
- `web_cache_deception_to_data_exfil` (T1557, 0.70, `requires_victim:true`)

### 3.2 New Category Files

**n_network_protocol.yaml** — 8 rules:
- `tls_downgrade_to_data_exfil` (T1557.002, 0.60)
- `dns_cache_poisoning_to_phishing` (T1584.002, 0.70)
- `dns_cache_poisoning_to_pivot` (T1557, 0.65)
- `cache_poisoning_to_auth_bypass` (T1557, 0.75)
- `cache_poisoning_to_account_takeover` (T1557, 0.70, `validated:True`)
- `http_desync_to_cache_poisoning` (T1557, 0.80, `validated:True`)
- `tcp_sequence_prediction_to_pivot` (T1557.001, 0.35)
- `smtp_relay_to_email_spoofing` (T1566.001, 0.75)

**o_container_infra.yaml** — 10 rules:
- `docker_socket_exposed_to_container_escape` (T1610, 0.90, `requires_docker:true`)
- `container_escape_to_pivot` (T1611, 0.85, `requires_docker:true`)
- `container_escape_to_rce_execution` (T1611, 0.90, `requires_docker:true`)
- `privileged_container_to_escape` (T1611, 0.85, `requires_docker:true`)
- `k8s_rbac_misconfig_to_cluster_access` (T1613, 0.80, `requires_kubernetes:true`)
- `k8s_secret_exposure_to_credential_harvesting` (T1552, 0.85, `requires_kubernetes:true`)
- `k8s_cluster_access_to_lateral_movement` (T1613, 0.80, `requires_kubernetes:true`)
- `k8s_cluster_access_to_persistence` (T1613, 0.75, `requires_kubernetes:true`)
- `k8s_cluster_access_to_supply_chain` (T1195, 0.70, `requires_kubernetes:true`)
- `docker_registry_exposure_to_code_exfil` (T1213, 0.75, `requires_docker:true`)

**p_active_directory.yaml** — 14 rules:
- `ntlm_relay_to_lateral_movement` (T1557.001, 0.85, `requires_active_directory:true`)
- `ntlm_relay_to_domain_admin` (T1557.001, 0.80, `requires_active_directory:true`, `validated:True`)
- `pass_the_hash_to_lateral_movement` (T1550.002, 0.85, `requires_active_directory:true`)
- `pass_the_ticket_to_lateral_movement` (T1550.003, 0.80, `requires_active_directory:true`)
- `kerberoasting_to_credential_harvesting` (T1558.003, 0.80, `requires_active_directory:true`)
- `kerberoasting_to_lateral_movement` (T1558.003, 0.75, `requires_active_directory:true`, `validated:True`)
- `asrep_roasting_to_credential_harvesting` (T1558.004, 0.75, `requires_active_directory:true`)
- `dcsync_to_credential_harvesting` (T1003.006, 0.90, `requires_active_directory:true`, `validated:True`)
- `dcsync_to_hvt_compromise` (T1003.006, 0.90, `requires_active_directory:true`, `validated:True`)
- `gpo_abuse_to_lateral_movement` (T1484.001, 0.80, `requires_active_directory:true`)
- `gpo_abuse_to_persistence` (T1484.001, 0.75, `requires_active_directory:true`)
- `shadow_credentials_to_account_takeover` (T1556, 0.85, `requires_active_directory:true`)
- `kerberos_ticket_forgery_to_hvt_compromise` (T1558.001, 0.90, `requires_active_directory:true`)
- `credential_harvesting_to_domain_controller` (T1003, 0.80, `requires_active_directory:true`, `validated:True`)

**q_api_web_modern.yaml** — 10 rules:
- `mass_assignment_to_privilege_escalation` (T1548, 0.70)
- `mass_assignment_verified_to_account_takeover` (T1548, 0.85, `validated:True`)
- `parameter_pollution_to_auth_bypass` (T1190, 0.65)
- `graphql_mutation_to_account_takeover` (T1059, 0.75, `validated:True`)
- `graphql_mutation_to_data_exfil` (T1059, 0.70)
- `api_versioning_bypass_to_auth_bypass` (T1190, 0.65)
- `api_versioning_bypass_to_data_exfil` (T1190, 0.60)
- `insecure_websocket_to_auth_bypass` (T1185, 0.65, `requires_victim:true`)
- `race_condition_to_privilege_escalation` (T1499, 0.60, `validated:True`)
- `race_condition_to_account_takeover` (T1499, 0.65, `validated:True`)

**r_email_security.yaml** — 8 rules:
- `spf_dmarc_bypass_to_email_spoofing` (T1566.001, 0.80)
- `spf_dmarc_bypass_to_phishing_amplification` (T1566.001, 0.75)
- `email_header_injection_to_phishing` (T1566.001, 0.70)
- `email_header_injection_to_account_takeover` (T1566.001, 0.65, `requires_victim:true`)
- `email_account_compromise_to_lateral_movement` (T1078.003, 0.85, `validated:True`)
- `email_account_compromise_to_credential_harvesting` (T1078.003, 0.80)
- `email_spoofing_to_hvt_compromise` (T1566.001, 0.70, `requires_victim:true`)
- `mx_misconfig_to_email_spoofing` (T1584.002, 0.65)

**s_supply_chain.yaml** — 8 rules:
- `github_actions_injection_to_ci_execution` (T1195.002, 0.85, `validated:True`)
- `ci_artifact_poisoning_to_supply_chain` (T1195.002, 0.80)
- `typosquatting_to_supply_chain` (T1195.001, 0.70)
- `compromised_registry_to_rce_execution` (T1195.001, 0.85, `validated:True`)
- `ci_execution_to_credential_harvesting` (T1552, 0.85)
- `ci_execution_to_code_exfil` (T1213, 0.80)
- `github_token_to_ci_execution` (T1528, 0.85)
- `supply_chain_compromise_to_hvt_compromise` (T1195, 0.80, `validated:True`)

**t_dotnet_cms.yaml** — 8 rules:
- `aspnet_viewstate_to_rce` (T1059.005, 0.85, `requires_dotnet:true`)
- `machinekey_to_rce` (T1059.005, 0.90, `requires_dotnet:true`, `validated:True`)
- `drupal_rce_to_execution` (T1505.003, 0.85, `requires_drupal:true`)
- `drupal_sqli_to_db_access` (T1190, 0.85, `requires_drupal:true`)
- `joomla_rce_to_execution` (T1505.003, 0.80, `requires_joomla:true`)
- `magento_sqli_to_db_access` (T1190, 0.85, `requires_magento:true`)
- `rails_mass_assign_to_privilege_escalation` (T1548, 0.80, `requires_ruby:true`)
- `nodejs_prototype_pollution_to_rce` (T1059, 0.85, `requires_nodejs:true`, `severity:>=3`)

**u_persistence_chains.yaml** — 8 rules:
- `rce_execution_to_webshell_persistence` (T1505.003, 0.85)
- `rce_execution_to_scheduled_task` (T1053.005, 0.75)
- `rce_execution_to_registry_persistence` (T1547.001, 0.70, `requires_dotnet:true`)
- `file_upload_to_webshell` (T1505.003, 0.90)
- `admin_access_to_cron_persistence` (T1053.003, 0.75)
- `persistence_to_lateral_movement` (T1021, 0.80)
- `persistence_to_credential_harvesting` (T1003, 0.75)
- `webshell_to_data_exfil` (T1041, 0.85)

### 3.3 Rule Count Summary

| Category | File | Existing | Added | Total |
|----------|------|----------|-------|-------|
| Injection | a_ | 9 | +7 | 16 |
| File Ops | b_ | 5 | 0 | 5 |
| Server-side | c_ | 7 | +5 | 12 |
| Deserialization | d_ | 4 | 0 | 4 |
| Auth/Identity | e_ | 9 | +8 | 17 |
| Client-side | f_ | 7 | +5 | 12 |
| Info Disclosure | g_ | 6 | +4 | 10 |
| Cloud | h_ | 6 | 0 | 6 |
| Tech-specific | i_ | 5 | 0 | 5 |
| Secrets | j_ | 5 | 0 | 5 |
| DNS/Subdomain | k_ | 4 | 0 | 4 |
| Lateral Movement | l_ | 5 | 0 | 5 |
| HVT | m_ | 4 | 0 | 4 |
| Network Protocol | n_ | — | 8 | 8 |
| Container/Infra | o_ | — | 10 | 10 |
| Active Directory | p_ | — | 14 | 14 |
| API/Web Modern | q_ | — | 10 | 10 |
| Email Security | r_ | — | 8 | 8 |
| Supply Chain | s_ | — | 8 | 8 |
| .NET / CMS | t_ | — | 8 | 8 |
| Persistence Chains | u_ | — | 8 | 8 |
| **Total** | | **76** | **+103** | **~179** |

---

## Section 4: Scoring Overhaul (6 → 10 Factors)

### 4.1 Revised Weight Table

| Factor | Old weight | New weight |
|--------|-----------|-----------|
| Severity | 0.20 | 0.15 |
| Exploitability (CVSS) | 0.20 | 0.15 |
| Path length | 0.15 | 0.10 |
| Privilege gained | 0.15 | 0.15 |
| Impact (blast radius + sensitivity) | 0.15 | 0.12 |
| EPSS | 0.15 | 0.13 |
| **PoC / exploit availability** | — | **0.08** |
| **CVE recency factor** | — | **0.04** |
| **Asset connectivity degree** | — | **0.05** |
| **Path stealthiness** | — | **0.03** |
| **Total** | **1.00** | **1.00** |

### 4.2 New Factor Logic

**PoC / exploit availability (0.08)**:
```python
poc_score = 0.0
if path_metadata.get("has_poc"):         poc_score = 0.60
if path_metadata.get("has_exploit_url"): poc_score = max(poc_score, 0.80)
if path_metadata.get("has_metasploit"):  poc_score = 1.0
```

**CVE recency factor (0.04)**:
```python
days_since = (today - cve_published_date).days
if days_since < 30:    recency_score = 1.0    # actively exploited window
elif days_since < 180: recency_score = 0.70
elif days_since < 730: recency_score = 0.40
elif has_cisa_kev:     recency_score = 0.80   # old but KEV = still exploited
else:                  recency_score = 0.15
```
Source: `cve_published_date` from vulnerability node properties.

**Asset connectivity degree (0.05)**:
```python
degree = path_metadata.get("target_node_degree", 1)
connectivity_score = min(degree / 20.0, 1.0)
```
One lightweight Neo4j query per path in `_build_path_metadata`:
`MATCH (n:APMENode {apme_id: $end_id}) RETURN size((n)--()) AS degree`

**Path stealthiness (0.03)**:
```python
boundary_crossings = sum(1 for s in steps if s.edge_type in {"CONNECTED_TO", "TRUSTS"})
victim_steps = sum(1 for s in steps if getattr(s, "requires_victim", False))
stealthiness_score = max(0.0, 1.0 - (boundary_crossings * 0.2) - (victim_steps * 0.3))
```
Purely structural — no new data required. Requires `PathStep.requires_victim` field (see Section 5 note).

### 4.3 Strengthened Post-Sum Modifiers

**KEV boost** (tiered, replaces flat +0.10):
```python
if has_cisa_kev and (has_poc or has_exploit_url):
    score = min(score + 0.15, 1.0)
elif has_cisa_kev:
    score = min(score + 0.10, 1.0)
```

**ERL validated boost** — existing +0.05/step max +0.15, now only applies when path has ≥ 2 steps total (prevents single validated findings from unfairly jumping risk bands).

### 4.4 Recalibrated Risk Classification

The `_classify` signature gains a `metadata` parameter:

```python
@staticmethod
def _classify(score: float, path: AttackPath, metadata: dict) -> str:
    validated_count = sum(1 for s in path.steps if s.validated)
    has_any_signal = (
        metadata.get("has_poc") or
        metadata.get("has_exploit_url") or
        metadata.get("has_cisa_kev")
    )
    if validated_count == 0 and score < 0.40:
        return "speculative"
    if validated_count == 0 and not has_any_signal and score >= 0.70:
        return "medium"    # cap: unverified high-score paths cannot reach high/critical
    if score > 0.85:
        return "critical"
    if score > 0.70:
        return "high"
    if score > 0.50:
        return "medium"
    return "low"
```

All call sites of `_classify` and `Scorer.score` must pass `metadata`.

### 4.5 `_build_path_metadata` Additions in `orchestrator.py`

New fields extracted from vulnerability nodes during metadata build:
- `has_poc` — `any(n.properties.get("is_poc") for vuln nodes in path)`
- `has_exploit_url` — `any(bool(n.properties.get("exploit_url")) for vuln nodes in path)`
- `has_metasploit` — `any(n.properties.get("has_metasploit") for vuln nodes in path)`
- `cve_published_date` — earliest date from vuln nodes (as `datetime.date`)
- `target_node_degree` — queried from Neo4j for `path.end` node

---

## Section 5: Pathfinder Improvements

### 5.1 Semantic Fingerprint Deduplication

Replace raw node-ID fingerprint with edge-type + subtype fingerprint in `find_all_paths`:
```python
key = "->".join(
    f"{s.edge_type}:{s.from_id.split('::')[0]}:{s.to_id.split('::')[0]}"
    for s in p.steps
)
```
Deduplicates semantically equivalent paths (same attack chain, different target instances) while preserving genuinely distinct chains.

### 5.2 Orchestrator Deduplication Order Validation

`find_all_paths` returns unscored paths, so any sort by `path.score` inside it is meaningless (score is 0.0 until `Scorer.score` runs). The risk-weighted sort is already correctly handled in the orchestrator:

```python
# Orchestrator — current order (correct, no change needed):
scored_paths = self._scorer.sort_paths(paths)       # sort by score desc
scored_paths = self._scorer.deduplicate(scored_paths) # keep best of overlapping
scored_paths = self._scorer.sort_paths(scored_paths)  # re-sort after dedup
```

The only change: `find_all_paths` internal sort changes from step-count to a **pre-dedup candidate sort** that prefers longer, richer paths (more steps = more signal) over trivial single-step candidates — inverting the current `len(p.steps)` ascending sort:

```python
# find_all_paths — change ascending step sort to descending (richer candidates first)
return sorted(unique, key=lambda p: len(p.steps), reverse=True)[:top_n]
```

This ensures the scorer and orchestrator dedup see the most informative chains first, not the shortest ones.

### 5.3 DFS Depth Guard

- Reduce `DFS_MAX_DEPTH` from 8 to 6
- Change DFS minimum hop from 1 to 2: `[:APME_EDGE*2..{DFS_MAX_DEPTH}]`
- Eliminates trivial 1-step paths at the Cypher level, reducing traversal cost

### 5.4 Per-Node Edge Fan-Out Cap in `GraphEnricher`

```python
MAX_EDGES_PER_NODE = 12

# After collecting per-node edges in enrich():
if len(node_edges) > MAX_EDGES_PER_NODE:
    node_edges = sorted(node_edges, key=lambda e: e.confidence, reverse=True)[:MAX_EDGES_PER_NODE]
    logger.debug("APME Enricher: Node %s fan-out capped at %d.", node.id, MAX_EDGES_PER_NODE)
```
Prevents combinatorial explosion from over-matched generic nodes (e.g. `misconfig` matching 6+ rules).

### 5.5 Minimum 2-Step Path Filter in `_validate_and_build`

```python
if len(rels) < 2:
    continue  # single-step findings reported as individual vulns, not attack chains
```

### 5.6 Dijkstra APOC Fallback

When APOC is unavailable, use higher-confidence DFS instead of BFS to avoid duplicate BFS results:
```python
except Exception:
    logger.warning("APME Pathfinder: APOC unavailable, using high-confidence DFS fallback.")
    saved_conf = self.min_edge_confidence
    self.min_edge_confidence = min(saved_conf + 0.10, 0.80)
    result = self._dfs_query(scan_id, start_id, target_subtypes)
    self.min_edge_confidence = saved_conf
    return result
```

### 5.7 Model Change: `PathStep.requires_victim`

`PathStep` needs a `requires_victim: bool = False` field to support stealthiness scoring. This field is set in `_validate_and_build` from `rel.get("requires_victim", False)`.

---

## Implementation Phasing

| Phase | Scope | Key Files | New Rules |
|-------|-------|-----------|-----------|
| 1 | Schema + ingestion extensions | `schema.py`, `vulnerabilities.py` | — |
| 2 | Constraint engine expansion | `constraints.py`, `rules_engine.py` | — |
| 3 | Rules — additions to existing files | `a_`, `c_`, `e_`, `f_`, `g_` YAML | +29 |
| 4 | Rules — new category files | `n_` through `u_` YAML (8 new files) | +74 |
| 5 | Scoring overhaul | `scorer.py`, `orchestrator.py` | — |
| 6 | Pathfinder improvements | `pathfinder.py`, `enricher.py`, `path.py` | — |
| 7 | Tests | `web/tests/test_apme_*.py` | — |

Phases 3 and 4 can run in parallel once Phase 2 is complete. Each phase is independently releasable.

---

## Constraints & Non-Goals

- No Neo4j GDS plugin dependency introduced
- No APOC dependency added (Dijkstra fallback remains, not new APOC calls)
- No changes to `temporal_workflows.py` or `temporal_activities.py`
- No new Python package dependencies
- All YAML additions are backwards-compatible with `RulesEngine._load_rules`
- AD rules produce zero edges on purely web-app scans (gated by `requires_active_directory`)
- Container rules produce zero edges unless Docker/K8s technology nodes are detected
