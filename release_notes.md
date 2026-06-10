<p align="center">
<img src="https://raw.githubusercontent.com/whiterabb17/r3ngine/main/frontend/public/img/banner.png" height="400px" width="520px" alt=""/>
</p>

<h1 align="center">
  ⚡ r3ngine v3.5.0: The Phoenix Rebirth ⚡
</h1>

The Phoenix rises from the ashes even stronger. **r3ngine v3.5.0** is the production-stabilized, enterprise-grade evolution of the platform. This release delivers a complete **CVE Enrichment System** (NVD, EPSS, CISA KEV), a **Burp Suite Professional Integration Plugin**, and deep **Neo4j graph sync** with CVE metadata. The infrastructure has been overhauled with **Django 5.2.3 LTS**, **PostgreSQL 16**, **Python 3.12**, and **Gunicorn + Uvicorn ASGI** production serving. 

Building on the v3.2.0 Celery → Temporal migration — which replaced the legacy at-most-once task broker with a durable workflow engine providing crash-safe execution, full replay history, and pause/resume signaling — v3.5.0 focuses on intelligence enrichment, operational security, and production reliability at scale.

> [!IMPORTANT]
> **Existing installations must run the full upgrade script before starting services.**
>
> ```bash
> # Linux / macOS
> git pull && make fullupgrade
>
> # Windows
> git pull && make.bat fullupgrade
> ```
>
> The script stops all containers, rebuilds all images, performs a database backup, upgrades the database from pg12 to pg16, applies database migrations, and starts the updated stack. It will ask for explicit confirmation before making any changes. **All Docker volumes (scan data, nuclei templates, wordlists) are fully preserved.**

---

<h2 align="center">
  🚀 [v3.6.0] Unreleased 🚀
</h2>

## 🪟 Custom Parameter Discovery Engine (CPDE)

v3.6.0 introduces the Custom Parameter Discovery Engine (CPDE), allowing users to define custom regular expressions and keyword matchers to extract sensitive or high-value parameters across scan results.

* **Regex & String Matching**: Define specific parameter patterns using exact strings or complex regex statements.
* **Severity Levels**: Assign severity tiers to each custom parameter (e.g. Critical for `admin_token`, Info for `lang_id`).
* **Scan Integration**: Scans automatically extract matched parameters during the web enumeration and crawling phases. Results are aggregated in a dedicated "Parameters" tab on the Scan Detail page, displaying occurrence counts, severities, and the exact endpoint URLs.

---

## 🔍 WP Taint Scan SAST Integration

v3.6.0 integrates `wp-taint-scan` to perform automated Static Application Security Testing (SAST) on WordPress plugins during scans.

* **Automated Source Analysis**: Downloads the source code of discovered WordPress plugins and runs taint analysis to identify zero-day vulnerabilities or insecure code patterns.
* **Pipeline Orchestration**: Executes as the final tool in the WordPress discovery and vulnerability pipeline, maximizing plugin coverage.
* **Findings Correlation**: Results are automatically parsed and attributed as high-severity vulnerabilities to the specific subdomains running the plugins.

---

## 🧠 CVE Enrichment Expansion (SploitScan & AI Assessments)

v3.6.0 massively upgrades the CVE enrichment pipeline by integrating `sploitscan` and automated LLM-based risk assessments.

* **Real-World Exploit Tracking**: Runs `sploitscan` on newly discovered CVEs to pull ExploitDB, Metasploit, and GitHub Proof-of-Concept links directly into the database.
* **HackerOne Intelligence**: Captures HackerOne Hacktivity statistics and patching priority recommendations.
* **Automated AI Assessments**: Leverages the system's active LLM configuration (OpenAI, Anthropic, Gemini, or local Ollama) to automatically generate context-rich risk assessments and mitigation strategies based on the CVE's CVSS score and exploitability metrics.
* **Persistent Intelligence Cache**: All new intelligence points are permanently cached in the `CveId` database model, eliminating redundant API lookups and saving LLM tokens across future scans.

---

## 🔬 CVE Enrichment & Threat Intelligence

v3.5.0 introduces the **CVE Enrichment Service**, a centralized threat intelligence layer that transforms raw scanner findings into prioritized, contextual vulnerability profiles.

* **NVD API v2.0 Integration**: Fetches real-time CVSS v3.1 metrics directly from the National Vulnerability Database.
* **EPSS Exploitation Probability**: Pulls Exploit Prediction Scoring System (EPSS) probability scores and percentiles from FIRST to measure the likelihood of a vulnerability being exploited in the wild.
* **CISA KEV Sync**: Automatically cross-references findings with the CISA Known Exploited Vulnerabilities (KEV) catalog.
* **Local Caching**: Minimizes API request overhead by caching CVE metadata locally (7-day TTL for CVEs, 1-hour for KEV) with graceful degradation during NVD/FIRST API unavailability.
* **Automated & Manual Sync**: Synchronization runs automatically 5 minutes after every orchestrator startup, or can be run manually via:
  ```bash
  python manage.py sync_cve_data --all
  ```

---

## 🧠 CVE Correlation, Deduplication & Graph Sync

The scan finalization tier has been rebuilt to synthesize raw tool outputs, assess composite risk, and update the graph database safely.

* **Multi-Criteria Scoring**: Replaced basic CVSS severity lookups with a composite risk scoring algorithm (`correlation.py`) that incorporates tool weights, asset criticality, exploitability (KEV/EPSS), and temporal modifiers.
* **In-Scan Deduplication**: Suppresses duplicate findings in-memory and groups them under a unique `group_key` before writing, preventing database bloat.
* **Vulnerability History Tracking**: The `VulnerabilityHistory` model traces findings across historical scans to automatically classify vulnerabilities as **new**, **persistent**, or **remediated**.
* **Durable DB Transactions**: Operations are wrapped in atomic transaction blocks to prevent race conditions and duplicate database inserts.
* **Neo4j ID-Based Linkage**: Refactored the Neo4j sync engine (`graph.py`) to link vulnerability nodes to CVE nodes using precise ID matches rather than string names, embedding CVSS base scores and EPSS scores directly as node properties.

---

## 🔌 Burp Suite Professional Integration Plugin

A dedicated, self-contained integration plugin (`burpsuite_integration`) enables bidirectional synchronization between r3ngine and Burp Suite.

* **Bidirectional Temporal Workflows**: Structured into a two-phase architecture: Phase 1 imports raw findings from the Burp REST API; Phase 2 maps findings to existing subdomain/endpoint targets, generating linked core `Vulnerability` records.
* **Tactical Control Panel**: A React + MUI dashboard built around dynamic Module Federation, displaying HSL glowing KPI cards, a filterable issues grid with drawer details, and a live config tester.
* **Health and Scope Sync**: A pulsing `HealthDot` status indicator displays live API connectivity. Scope pushing enables sending r3ngine targets back to Burp scope directly from the UI.
* **Signed Plugin Support**: Leverages the `.r3n` plugin format, verifying package integrity and signatures with Ed25519 cryptography.

---

## ⚡ Infrastructure Modernization & Performance

The core system runtime, frameworks, and database engines have been upgraded to the latest LTS releases.

* **Python 3.12 Runtime**: Upgraded the container execution runtime from Python 3.10 to Python 3.12, gaining ~25% execution speedup. Configured the deadsnakes PPA, ensurepip bootstrap, and alternatives to route all global commands safely.
* **Django 5.2.3 LTS**: Upgraded from the expired Django 3.2 LTS to 5.2.3 LTS (supported until April 2028). Deprecated APIs have been fully migrated (`url()` -> `re_path()`, `USE_L10N` removed, and `unique_together` migrated to `UniqueConstraint`).
* **PostgreSQL 16**: Upgraded the database engine from PostgreSQL 12.3 to PostgreSQL 16-alpine (supported until November 2028).
* **Gunicorn + Uvicorn ASGI**: Replaced the development server in production with Gunicorn 22 + `UvicornWorker` for full ASGI support, improving performance and enabling robust WebSocket log streaming.
* **Connection Pooling & SSL**: Added `CONN_MAX_AGE=60` and `CONN_HEALTH_CHECKS=True` to reuse database connections, and configured secure client SSL configurations.

---

## 📁 URL Deduplication & Grouped NSE Findings

Scan load and UI noise are heavily reduced through intelligent filtering and grouping.

* **Two-Pass URL Deduplication**:
  1. *Pass 1 (Pre-Save)*: Collapses parametric variants of the same path (e.g. `/page?id=1` and `/page?id=100` are collapsed to `/page?id`) to reduce scan payload for Tier 4–6 tools.
  2. *Pass 2 (Post-Save)*: Groups crawled endpoints by subdomain, content length, and page title, discarding duplicate HTTP responses.
* **Nmap Vulners Version Grouping**: Vulners NSE script results are grouped by product version (e.g. "Exim smtpd 4.99.2") and displayed as a single card with collapsible CVE sub-tables in both the UI and PDF/HTML report templates (`cyber_pro`, `enterprise`, `modern`, `default`).
* **Nuclei Sequential Severity Execution**: The `NucleiPlannerWorkflow` executes severity levels sequentially to prevent Out-Of-Memory (OOM) crashes on large target sets.



---

## 🛠️ Hardened Upgrade & Operational Tooling

Upgrades and scan operations are protected by automation and strict validation.

* **Automated `make fullupgrade`**: An 8-step idempotent upgrade process. Includes a dedicated pre-upgrade database backup script (`scripts/db_backup.sh`) and an automated PostgreSQL major-version dump/restore script (`scripts/pg_upgrade.sh`).
* **Pipx Isolation**: Migrated `dirsearch`, `maigret`, and `semgrep` into isolated `pipx` virtual environments to eliminate build-time dependency conflicts with Django.
* **Semgrep Normalization**: Implemented a centralized `clean_semgrep_check_id` helper to strip system/path-based prefixes and deduplicate repeating suffixes in Semgrep check IDs. Capped individual file downloads at 5MB and total files per domain at 500 to prevent stalling.
* **gRPC Connection Cancellation Fix**: Refactored `stream_command` inside `tasks.py` to run `handle.result()` inside a single `asyncio.Task` wrapper to resolve `temporalio.service.RPCError: operation was canceled` errors caused by connection leaks.

---

## 📱 Mobile App & Dashboard Integration

The mobile companion client receives interface and API compatibility updates to align with the core v3.5.0 system.

* **Active Scan Pulse**: Added an animated, pulsing/scaling `Activity` radar badge in the mobile header next to the notification bell, flashing subtly whenever a scan is running.
* **System-Wide Log Viewer**: Integrated an observability panel in the mobile client for viewing System, Database, Temporal, and Scan logs. Features include live search, auto-refresh toggles, auto-scroll, and color-coded level badges.
* **Hardware Profile Selection**: Choose specific hardware resource profiles (CPU/RAM limits, worker queues) when starting a scan directly from the mobile app.
* **JWT WebSocket Auth**: Appended authentication tokens to WebSocket URLs for real-time Log Streaming and Stress Telemetry screens, resolving system log connection failures.
* **Redirection Protection**: Nginx redirects are updated to `308 Permanent Redirect` to preserve HTTP POST methods, preventing mobile login failures on HTTPS redirection.

---

### 🛠️ Technical Highlights
* **Temporal Schedules**: All OSINT and sync cron schedules migrated to native Temporal Schedules.
* **Cleaned Remnants**: Completely removed all Celery-related files, log handlers, and dependencies (`celery`, `django-celery-beat`).
* **Settings Cleanup**: All `CELERY_*` configuration blocks replaced with clean `REDIS_URL` settings.
* **Explicit DRF router basenames**: Added unique basenames to viewsets sharing the same model to resolve strict duplicate basename exceptions in DRF 3.15+.

**Your scans are durable. Your threat intelligence is enriched. Welcome to the Phoenix Rebirth.**

---
*Stay Tactical. Stay Rebellious.*  
🚀 [whiterabb17/r3ngine](https://github.com/whiterabb17/r3ngine)
