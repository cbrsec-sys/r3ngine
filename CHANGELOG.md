# Changelog

## [v3.0.0-rc] - 2026-05-08
### Added
- **Multi-Service Brute-Force Orchestration**: Updated brute-force engine schema to support an array of services (SSH, FTP, HTTP, SMB, RDP, Telnet).
- **Brute-Force Candidate Filtering**: Refactored `BruteForceOrchestrator` to dynamically filter `AuthCandidate` records based on the engine's allowed services.
- **Fixture Standardization**: Aligned default scan engine fixtures with the new multi-service schema and resolved YAML deserialization issues.
- **Plugin Tooling System**: Introduced `tools.yaml` contract for automated background tool installation.
- **Engine Fixture Ingestion**: Plugins can now ship `*_engine.yaml` fixtures for automatic engine registration.
- **Exploit Readiness Layer (ERL) v2**: Refactored to use local subprocess execution instead of Docker-in-Docker.
- **Background Tool Installation**: Plugin tools are now installed/verified asynchronously via Celery on installation and system startup.
- **Subprocess Execution Model**: Standardized local execution for plugins to enhance performance and simplify container orchestration.
### Bug Fixes
- **Scan Summary API**: Resolved a 500 Internal Server Error in the scan summary dashboard caused by NULL status codes and missing scan start dates.
- **Trivy SCA Removal**: Safely excised the Trivy filesystem scanning engine and associated dependencies to refocus reNgine on remote reconnaissance workflows.

### Exploit Readiness Layer (ERL) Hardening (v3-beta)
- **Proxy Support**: Native integration with reNgine's proxy settings. Tools (`sqlmap`, `XSStrike`) now respect system-wide proxy rotation via proxychains or environmental injection.
- **OpSec Compliance**: ERL validations now inherit reNgine's OpSec policies, including random User-Agents and stealthy headers.
- **Subprocess Execution**: Migrated from Docker-in-Docker to high-performance local subprocess execution for tool validation.
- **Autonomous Tooling**: Standardized `tools.yaml` for automatic dependency management and installation of required binaries.

## v3.0.0
**Official Repo location:** https://github.com/whiterabb17/r3ngine
 
### New Features
- **Deep Pursuit OSINT Engine & Intelligence Hub**:
  - Replaced heavy Spiderfoot reliance with a modular, high-performance OSINT pipeline.
  - **Tool Orchestration**: Integrated `holehe` (email pivots), `maigret` (social profile mapping), and a custom **Playwright Social Intelligence Engine** into the core Celery task chain.
  - **Social Footprint Intelligence**: Added automated discovery of social media accounts associated with discovered emails, visualized in the enhanced "Emails & Credentials" section.
  - **Employee Dossiers**: Integrated username-to-profile mapping, allowing users to pivot from professional identities to social footprints with direct profile links.
  - **Metadata Persistence**: Added a schema-less `metadata` JSONField to `Email` and `Employee` models for storing rich, tool-specific intelligence findings.
  - **OpSec Proxy Rotation**: Fully integrated the `OpSecManager` into the OSINT pipeline, ensuring per-tool proxy rotation for all reconnaissance activities.
- **Internal Social Intelligence Engine (Playwright)**:
  - Developed a custom, high-performance LinkedIn reconnaissance engine powered by Playwright.
  - **Persistent Session Orchestration**: Implemented stateful context management in `scan_results/context/linkedin`, mimicking real-user sessions to drastically reduce account lockout risks.
  - **Evasion & Stealth**: Integrated a full evasion suite including `playwright-stealth`, randomized human-like behavioral modeling, and Gaussian interaction delays.
  - **Hybrid Personnel Discovery**: Sophisticated logic that pivots between Company Page scraping and global search filtering for maximum data extraction.
  - **Visual Verification**: Every discovery run generates a unique, timestamped screenshot (`linkedin_[company]_[timestamp].png`) for investigator audit.
- **Intelligence Credential Orchestration**:
  - Integrated secure management for LinkedIn and Hunter.io credentials directly within the reNgine API Vault.
  - Implemented intelligent skip logic to ensure OSINT tasks exit gracefully if credentials are not configured.
- **Responsive Header & Mobile Navigation Orchestration**:
  - Implemented a smart, responsive header using `useMediaQuery` to adapt to limited screen real estate.
  - **Premium Hamburger Menu**: Developed a dedicated mobile drawer for viewports where header items overflow (typically < 1200px).
  - **Antigravity Design Integration**: Applied advanced glassmorphism (`backdrop-filter: blur(25px)`), spatial depth layering, and weightless typography to the mobile navigation experience.
  - **Action Consolidation**: Seamlessly moved Projects, Quick Add, Theme Switching, Toolbox, and Notifications into a unified, high-fidelity sidebar for mobile users while maintaining Universal Search visibility.
- **Asynchronous Report Generation Pipeline**: Eliminated 502 Bad Gateway timeouts by offloading PDF generation to background workers.
  - **Status Tracking & Polling**: Implemented a new `ScanReport` model and status API endpoints to monitor generation progress.
  - **Dynamic UI Progress**: Added a polling mechanism to the `ScanReportModal` with real-time status updates and manual download fallback.
  - **Custom Aesthetics**: Fully integrated user-configured branding, including custom colors and company identity settings.
  - **Template Reliability**: Fixed 500 errors in Modern and Enterprise templates caused by parsing errors and invalid Django tags.
  - **Speed Optimization**: Refined LLM generation to focus on high-value sections, reducing generation time by 90%.
- **Integrated Subdomain Action Interface**: Fully wired and enabled interactive management for the Subdomains tab in the scan detail interface.
  - **Subscan Configuration Overlay**: Implemented a tactical overlay for initiating targeted subscans with multiple engine selection support.
  - **LLM-Powered Attack Surface Analysis**: Integrated on-demand attack surface generation for individual subdomains using configured LLMs.
  - **Tactical TODO Management**: Added functionality to quickly attach reconnaissance notes (TODOs) to specific subdomains.
  - **Status & Lifecycle Management**: Fully implemented deletion and importance toggling for subdomains with immediate UI feedback and query invalidation.
- **Intelligent Brute-Force Orchestration Engine**: Replaced legacy Nmap-based triggers with a centralized, discovery-driven queue.
  - **AuthCandidate Queue**: Implemented a new database model to track and deduplicate brute-force targets (SSH, RDP, SMB, FTP, Telnet, HTTP) across all discovery tools.
  - **Tiered HTTP Discovery**:
    - **Tier 1 (Tech Hints)**: Automatic detection of common services.
    - **Tier 2 (Nuclei)**: Integrated 500+ authentication-related Nuclei templates into the candidate queue.
    - **Tier 3 (Intelligent Extraction)**: Automated form extraction using httpx and regex to identify unknown login portals.
  - **Unified Hydra Orchestrator**: Refactored the brute-force engine to use Hydra for high-speed, multi-protocol batching with OpSec awareness (rate-limiting and delay controls).
  - **Stealth Integration**: Full support for rotating proxies via `proxychains` or native Hydra proxy flags.
- **Hydra Brute-Force Integration**: Migrated from Medusa to Hydra as the primary brute-force engine for enhanced reliability and better service support.
- **Adaptive Stress & Resilience Engine (ASRE)**: Implemented full-scale endpoint stress testing directly within the reNgine workflow.
  - **Tool Orchestration**: Seamlessly orchestrated backend stress tests via Celery, driving load testing tools such as `k6`, `wrk`, `hping3`, and `Locust`.
  - **Safety Guardrails**: Integrated a Redis-based kill-switch mechanisms for safe testing and instant termination to protect target infrastructure.
    - ✨ **Cyberpunk UI Evolution**: Tactical reorganization of Scan Detail headers for optimized workflow.
    - 📊 **Enhanced Telemetry**: Fixed HTTP status breakdown logic to capture and visualize all response codes across assets.
  - **Telemetry Ingestion**: Real-time aggregation of latency, throughput, and error rate metrics directly into Neo4j for topological node analysis.
  - **Visualization Dashboard**: Created a new React-based interactive UI utilizing Apache ECharts and Nivo to visually represent endpoint resilience, saturation points, and errors across the network.
- **Documentation Overhaul**: Comprehensive restructuring of the documentation to provide high-level visibility into v3 capabilities and surgical recon pipelines, including a new dedicated section for the **Adaptive Stress & Resilience Engine (ASRE)**.
- **Exploitation Readiness Layer (ERL)**: Implemented a safe, modular, and production-grade validation layer for vulnerabilities.
  - **Vulnerability Validation**: Automatically converts potential findings into "Verified" status using non-destructive, containerized validation tools (e.g., safe SQLmap profiles).
  - **Confidence Scoring**: Integrated a Bayesian confidence engine that aggregates tool results, asset metadata, and tool reliability into a unified confidence score.
  - **Containerized Sandboxing**: Orchestrated on-demand, ephemeral Docker sandboxes for validation execution to maintain strict isolation.
  - **Policy-Driven Safety**: Implemented a Policy Engine that enforces safety boundaries, preventing validation on sensitive assets (e.g., .gov, production) or during restricted hours.
  - **Normalizer & Adapters**: Standardized validation evidence (request/response dumps, payloads) into a unified schema for consistent UI rendering.
  - **Global Configuration**: Added a global toggle `RENGINE_ERL_ENABLED` and updated all default scan engines to include ERL by default.
  - **Interactive Evidence Viewer**: Added a new "Validation" column and expandable evidence section in the vulnerability dashboard to display cryptographic-grade proof of findings.
- **Attack Path Modeling Engine (APME) Robustness & Rules Expansion**:
    - **Virtual Goal Injection**: Implemented automated injection of "Virtual Goal Nodes" (Objectives) into the attack graph, ensuring rules always have targets to wire to.
    - **Comprehensive Attack Rules**: Expanded `rules.yaml` with 20+ sophisticated rules covering XSS, XXE, SSRF, CORS, Prototype Pollution, and Open Redirects.
    - **SCA & Dependency Intelligence**: Integrated vulnerability mapping for supply chain and dependency findings, automatically deriving potential RCE and Data Exfil paths.
    - **Schema & Ingestion Hardening**: Expanded `vulnerabilities.py` to support deep subtype inference and updated `schema.py` for cloud-native capability modeling.
    - **Subscan Pipeline Integration**: Fixed a decoupling issue where APME and ERL validation would not trigger during targeted vulnerability subscans. Integrated correlation, risk scoring, and path modeling into the per-subdomain scan chain to ensure data consistency across targeted reconnaissance.
    - **Engine Decoupling**: Moved Attack Path Modeling configuration to its own independent engine block (`attack_path_modeling`), allowing it to be explicitly chained after other post-scan services like ERL validation.
- **WPScan Vulnerability Integration**:
  - Integrated **WPScan** as a first-class security tool for automated WordPress reconnaissance.
  - **Secure API Orchestration**: Added a dedicated persistence layer in the reNgine Vault for WPScan API tokens, enabling detailed vulnerability reporting.
  - **Automated Scanning & Detection**: Developed a multi-threaded Celery task that automatically detects WordPress instances, identifies vulnerable plugins/themes, and parses core version risks.
  - **Deduplication & Persistence**: Integrated results directly into the `Vulnerability` database with intelligent deduplication against existing findings.
  - **Tactical Configuration**: Added per-engine controls for WPScan enumeration modes and detection sensitivity via YAML configurations.
  - **Infrastructure Support**: Updated the core Docker environment to include Ruby and WPScan as a pre-installed dependency.

- **Advanced Web App & API Discovery Pipeline**: Introduced a dedicated reconnaissance engine for deep API discovery, featuring:
ring:
 - **Kiterunner**: High-performance API endpoint brute-forcing with custom `.kite` wordlists (`routes-large.kite` by default).
 - **Arjun**: Automated HTTP parameter discovery for identifying hidden API inputs.
 - **ParamSpider**: Advanced parameter extraction from web archives and live sources.
 - **InQL**: Comprehensive GraphQL introspection and vulnerability analysis.
 - **Aquatone**: Automated visual reconnaissance for discovered API endpoints.
 - **LinkFinder**: Deep extraction of endpoints from JavaScript files.
- **Spiderfoot OSINT Integration**: Fully integrated Spiderfoot as a standalone scan module, supporting:
 - Dynamic module configuration via YAML scan engines.
 - Automatic ingestion of discovered subdomains and URLs into the reNgine database.
- Full Neo4j graph synchronization for OSINT assets.
- **Multi-Tier Theme System (Hacker, Hybrid, Enterprise)**: Implemented a 3-tier, switchable aesthetic architecture for the React v3 frontend.
  - **Hacker Theme (Default)**: Optimized the signature cyberpunk look with custom scanline logic and Orbitron-driven typography.
    - **Aesthetic Refinement**: Applied signature neon pink branding (`rgb(255, 0, 241)`) and red glow effects to the brand logo and version badge across all Cyberpunk profiles (Hacker & Hybrid).
  - **Hybrid (Modern) Theme**: Introduced a "clean" dark mode that preserves brand-essential neon accents but removes high-intensity background effects.
  - **Enterprise (Professional) Theme**: Added a new, professional "Slate & Blue" interface using Inter typography and a flat, high-density layout for corporate use cases.
  - **Functional Token Architecture**: Centralized all theme logic in `tokens.ts`, enabling dynamic injection of CSS variables for fonts, colors, and motion.
  - **Persistent Selection**: Integrated a `HeaderThemeSwitcher` with `localStorage` persistence and automatic theme propagation via `ThemeContext`.
- **Cyberpunk V3 "Neon" Dashboard**: Reimagined the entire UI with a premium glassmorphic theme, featuring:
 - Unified dark/neon color palette for enhanced data visualization.
 - Improved sorting and filtering UI for large subdomain datasets.
 - Optimized sidebar and navigation for complex scan management.
- **Semgrep-Powered Static Analysis**: Integrated Semgrep to automatically analyze discovered JavaScript and API endpoints for common security flaws (replacing legacy JSParser).
- **Enhanced Proxy Orchestration**: Integrated rotating proxy support across all new discovery tools (Arjun, Kiterunner, etc.) to bypass rate-limiting and WAF blocks.
- **Result Ingestion V3**: Overhauled the result ingestion pipeline to handle massive datasets from API discovery, ensuring database performance and graph integrity.
- **Centralized AI Hub**: Introduced a unified AI management interface supporting multiple providers (OpenAI, Anthropic, Google Gemini, and Ollama).
- **Multi-Provider LLM Support**: Added production-ready integration for Claude 3 (Anthropic) and Gemini (Google) via REST APIs, alongside existing OpenAI and Ollama support.
- **Dynamic Model Fetching**: Implemented real-time model discovery for all supported providers, including hardware requirements and expertise insights for local models.
- **On-Demand Model Loading**: Optimized the AI Hub by fetching available models only when the dropdown is clicked, reducing initial page load overhead.
- **Legacy API Vault Sync**: Automatically migrates existing OpenAI keys from the legacy API Vault to the new AI Hub configuration.
- **Granular Proxychains Control**: Integrated a new `use_proxychains` toggle for precise control over proxy orchestration.
  - **Conditional Wrapping**: Users can now choose whether to wrap tools with `proxychains4` or prefer native tool proxy support.
  - **Automated Cleanup**: Implemented safe, multi-threaded configuration management that automatically cleans up temporary proxychains configs after execution.
  - **Tool Parity**: Updated core tasks (Hydra, Amass, Subfinder, Katana, etc.) to respect the new setting and utilize native flags where available.
  - **Integrated UI Switch**: Added a dedicated "USE PROXYCHAINS WRAPPER" switch in the Proxy Settings dashboard.
  - **On-the-fly Validation**: Automatically verify proxy connectivity before use to ensure high reliability during automated scans.
  - **Command UI Sanitization**: Improved timeline and results overlay by automatically stripping `export` and `proxychains` prefixes from the displayed command, ensuring the UI correctly identifies and displays the target tool name.
- **Enhanced Arjun Parameter Discovery**: 
  - Implemented configurable HTTP methods (default: GET, POST, JSON, XML, FETCH, PUT, DELETE, PATCH) via Scan Engine YAML.
  - Added support for `--stable` mode and dynamic thread orchestration.
  - Resolved `'list' object has no attribute 'items'` parsing error by supporting both list and dictionary output formats from Arjun.
- **Improved Tool Threading Consistency**: Standardized the use of the `threads` option from engine configurations across all discovery tools in `web_api_discovery` (Arjun, Kiterunner, etc.).
- **Arjun Stability Fix**: Resolved a crash in the `web_api_discovery` task where Arjun would fail during target stability probing with an `AttributeError`. Removed the `--stable` flag to ensure scan reliability across diverse targets.
- **UI/UX Standardization**: Standardized the `VulnerabilityTable` styling across the application by integrating it into the `TacticalPanel` component on the Scan Detail page and refining internal header aesthetics.
- **Arjun Version Management**: Updated Docker build to ensure `arjun`, `inql`, and `netlas` are always upgraded to their latest stable versions during installation.
- **Aquatone Pipeline Stability**: Resolved a `NameError` causing Aquatone task failures by standardizing the `EndPoint` model reference.
- **404 Page Enhancement**: Added an Interdimensional Rabbit Hole background image for the 404 page.
- **Production-Ready SSL Serial Retrieval**: Implemented a robust `_get_ssl_serial` function in `waf_utils.py` using the `cryptography` library for reliable origin discovery via Shodan.
  - **Standardized Notification System (Snackbar)**: 
    - Replaced legacy `alert()` dialogs with consistent, non-intrusive MUI `Snackbar` and `Alert` components across all settings modules.
    - Implemented state-driven feedback for critical actions in `SubdomainsTab`, `ApiVault`, `ProxySettings`, `ReportSettings`, `OpSecSettings`, `LlmToolkit`, `SystemSettings`, and `AdminSettings`.
    - Enhanced error handling with detailed feedback from backend mutation responses.
    - Unified notification visuals with the "Cyberpunk" design language (Orbitron font, filled severity backgrounds).
- **Modernized Censys Platform Integration**: 
  - Migrated from legacy Search v2 (Basic Auth) to the latest **Censys Platform API (2026 standards)** using Personal Access Tokens (Bearer authentication).
  - Updated the `CensysAPIKey` database model to support a single-key schema.
  - Refactored `OriginDiscoveryManager` to utilize the `censys-platform` SDK for more reliable host lookups and origin discovery.
  - Streamlined the API Vault and Onboarding UI for single-key configuration.
- **Scoped Attack Surface Visualization**: Refactored the Neo4j ingestion and retrieval pipeline to support scan-specific and target-specific scoping:
  - Introduced `Scan` nodes in Neo4j to anchor assets to specific execution contexts.
  - Implemented target-level graph aggregation with color-coded scan distinction in the UI.
  - Added backend API support for segmented graph data fetching (`/api/graph/target/<target_id>/data/`).
  - Added new "Attack Surface" and "Visualization" tabs to the Target Summary view.
  - Resolved "node bleeding" where global graph data would pollute individual scan maps.
  - Included a `sync_all_scans` migration utility to retroactively anchor historical data.
  - Added a `reset_graph` Django management command to clear and re-populate the Neo4j database in case of data corruption or schema changes.
  - **Attack Surface Map v4.0 UI Architecture**:
    - **Multi-Panel Layout**: Transitioned the visualization area to a multi-panel layout managed by Zustand state architecture (`useGraphStore`).
    - **Advanced Node Analytics**: Upgraded Cytoscape rendering to dynamically scale node sizes based on degree centrality and highlight critical vulnerabilities.
    - **Interactive Node Details**: Added a dedicated slide-out panel displaying live graph metrics (centrality, vulnerabilities) with actionable options.
    - **Blast Radius Computation**: Integrated real-time blast radius calculations using Neo4j APOC, displaying downstream compromised assets.
    - **AI-Driven Graph Search**: Replaced standard graph search with a mock AI natural language query interface for future conversational exploration.
- **Enhanced GeoMap Visualization**:
  - **Custom Tactical Markers**: Replaced broken default Leaflet markers with high-performance CSS-animated pulsing `divIcon` markers, maintaining the "Cyberpunk Hacker" aesthetic.
  - **Comprehensive Global Mapping**: Integrated an external `countryCentroids.ts` database covering all ISO-2 country codes for high-precision asset positioning.
  - **Improved Interaction Layer**: Replaced unsupported React-based marker children with native `react-leaflet` `Tooltip` components for reliable hover interactions and tactical styling.
  - **Visual Polish**: Added dedicated `.map-marker-pulse` and `.tactical-tooltip` global CSS styles for smooth animations and premium UI consistency.
  - **Vulnerability Impact Intelligence**: Integrated AI-driven impact assessment and graph-based attack path visualization:
    - **AI-Driven Impact Assessment**: Automated generation of potential impact narratives and remediation priorities using LLMs (OpenAI, Anthropic, Gemini, Ollama).
    - **Attack Path Visualization**: Interactive Cytoscape.js-powered graph showing the full exploit chain from root domain to vulnerability.
    - **Impact Explorer**: A tactical React component for real-time monitoring of impact generation tasks and interactive graph exploration.
    - **PII Gate**: Implemented a privacy-preserving "gate" that anonymizes sensitive reconnaissance data (IPs, emails, hostnames) before sending it to external LLMs and deanonymizes the returned results.
    - **Persistence & Polling**: Impact findings are persisted in PostgreSQL and synchronized with React Query using smart polling for asynchronous background tasks.
- **Real-Time Interactive Scan Timeline**: Overhauled the scan timeline to support live task monitoring and detailed command execution logs:
    - **Live Command Streaming**: Integrated real-time polling to capture and display command stdout/stderr as tools execute.
    - **Interactive Task Overlay**: Users can click on timeline events to open a terminal-style overlay showing all executed commands and their outputs.
    - **Enhanced Task Metadata**: Backend updated to track command-level lifecycle and log availability per scan activity.
    - **Smart Polling**: Implemented intelligent React Query polling that automatically adjusts based on scan status.
- **Advanced Vulnerability Correlation Engine**: 
  - Integrated **Trivy** for automated Software Composition Analysis (SCA) and **Gitleaks** for secret discovery.
  - Added **Retire.js** integration to identify vulnerable client-side JavaScript libraries.
  - Implemented a weighted correlation algorithm that unifies results from Nuclei (DAST), Semgrep (SAST), Trivy (SCA), Gitleaks, and Retire.js.
  - Introduced **Potential Attack Chain** generation to visualize sequential exploitation steps (Initial Access -> Lateral Movement -> Impact).
  - Added automated unit tests to ensure correlation logic accuracy across all security tools.
- **Seamless AI Impact Intelligence**: 
    - Modernized the AI-driven vulnerability assessment workflow with a state-aware Impact Explorer UI.
    - Replaced intrusive alerts with immediate loading overlays and persistent status monitoring.
    - Implemented auto-generation logic for first-time assessment views.
    - Synchronized AI findings directly to the `Vulnerability` model for consistent report persistence.
    - Fully updated the Exploit Readiness Layer (ERL) plugin to maintain cross-feature parity.
- **Acunetix & ReconX Orchestration**: 
    - **Acunetix (AWVS) Pipeline**: Integrated automated vulnerability scanning via Acunetix API. Supports secure storage of server URLs and API keys in the reNgine Vault, automated target provisioning, and native ingestion of scan findings into the core `Vulnerability` database.
    - **ReconX Auxiliary Discovery**: Integrated ReconX into the `monitor_tasks.py` pipeline to complement existing subdomain discovery and OSINT tools. ReconX findings are automatically parsed and mapped to `MonitoringDiscovery` nodes for consolidated asset tracking.
- **Build & Infrastructure**:
    - **ReconX Installation Fix**: Corrected the Go installation path for ReconX in `web/Dockerfile` (appended `/cmd/reconx`) to resolve module package errors.
    - **Proxy Orchestration Fix**: Resolved host resolution errors in the `proxy` container by aligning network aliases in `docker-compose.yml` with the Nginx configuration. Fixed deprecated `http2` directives in `rengine.conf`.
- **Frontend Security & Resilience**: 
    - **Centralized Auth Architecture**: Implemented a robust `AuthContext` and `AuthProvider` to manage user sessions and state globally.
    - **Protected Route Guards**: Integrated TanStack Router `beforeLoad` hooks to enforce authentication across all sensitive application routes.
    - **Robust CSRF Protection**: Centralized CSRF token retrieval and automated injection into all mutation requests via Axios interceptors.
    - **Automatic SQLi Prevention**: Implemented a client-side request interceptor that blocks outgoing requests containing suspicious SQL injection patterns in the payload.
    - **DOM Sanitization**: Integrated `DOMPurify` for secure rendering of potentially unsafe content, preventing XSS in future features.
    - **Dependency Hardening**: Remediated high-severity ReDoS vulnerabilities in the `d3` ecosystem via `package.json` overrides.
    - **Regex Security**: Optimized search highlighting logic with centralized regex escaping to prevent ReDoS attacks from user inputs.
- **Scan History Rescan Orchestration**: Finalized the integration and wiring of the "Rescan" feature across the entire scan management lifecycle:
  - **Scan History & Scan List Integration**: Wired the "RESCAN" menu item in both the Scan History page and the Dashboard Scan List, enabling immediate re-triggering of existing scans.
  - **Target List Menu**: Enhanced the Targets list with a tactical row menu featuring an "INITIATE SCAN" (Rescan) action for better workflow consistency.
  - **Scan Detail Header Action**: Added a primary "RESCAN" button to the Scan Detail header, allowing users to quickly restart discovery from the summary view.
  - **Scan Detail Header Reorganization**: Improved the aesthetic layout of the Scan Detail page by repositioning navigation breadcrumbs below action buttons and right-aligning the control group for better visual flow.
  - **UI/UX Stability**: Resolved critical state race conditions where menu actions would fail due to premature cleanup of active identifiers.
  - **Modular Scan Initiation**: Corrected all Rescan triggers to the `StartScanModal` and `useInitiateScan` orchestration layer, ensuring full parity with standard manual scan initiation.
- **Integrated Attack Surface Map Navigation**: 
  - Properly integrated the Attack Surface Map feature into the Scan History page.
  - Replaced the broken `window.open` placeholder with a dedicated, SPA-managed `AttackSurfacePage`.
  - Implemented a new route `/$projectSlug/attack_surface/$scanId` to host the cytoscape-based visualization.
  - Enhanced the UI with navigation breadcrumbs and scan-specific metadata for better context.
- **Security Hardening (v3)**:
    - **Path Traversal Fix**: Secured `serve_protected_media` in `reNgine/views.py` using the existing `is_safe_path` utility to prevent `../` directory traversal attacks (LFI).
    - **CSRF & API Method Hardening**: Migrated project creation from an unsafe `GET` request (vulnerable to CSRF via URL) to a secure `POST` request with proper CSRF token validation in both frontend (`projects/api.ts`) and backend (`CreateProjectApi`).
    - **Frontend XSS Prevention**: Hardened `monitoring/utils/formatters.ts` to use `DOMPurify` for all dynamic content sanitization, added prototype pollution protection in JSON parsing, and applied strict type-checking before accessing object properties.
    - **Django Security Headers**: Enabled `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_BROWSER_XSS_FILTER`, `X_FRAME_OPTIONS = DENY`, `SECURE_REFERRER_POLICY`, and secure `SESSION_COOKIE_HTTPONLY`. Configurable HTTPS/HSTS settings via `.env` (`RENGINE_HTTPS`, `SECURE_HSTS_SECONDS`).
    - **ALLOWED_HOSTS Hardening**: `ALLOWED_HOSTS` is now configurable via the `ALLOWED_HOSTS` environment variable (defaults to `*`; must be set to specific domains in production).
    - **DRF Rate Limiting**: Added global REST framework throttle classes (20/min anonymous, 200/min authenticated) to protect API endpoints from brute-force attacks.
    - **Role-Based Authorization Fix**: Corrected the `IsAuditor` DRF permission class which was incorrectly granting write access to all authenticated users. Auditors are now correctly restricted to read-only (`SAFE_METHODS`) access; `IsSysAdmin`, `IsPenetrationTester`, and `IsAuditor` role documentation updated to reflect the three-tier hierarchy.
    - **Command Injection Mitigation**: Replaced all `run_command.run(f'touch {path}', shell=True)` subprocess calls in `GetFileContents` with safe Python-native `pathlib.Path.touch()` calls. Fixed `delete_target` in `targetApp/views.py` to use `shutil.rmtree` on a validated path instead of `rm -rf {obj.name}*` with `shell=True`.
- **Restored Visual Evidence Pipeline (Screenshots)**: 
  - **Frontend Integration**: Implemented a dedicated `ScreenshotsTab` component in the `ScanDetailPage`, replacing the broken placeholder.
  - **Tactical Gallery UI**: Created a premium, responsive masonry-style gallery for screenshot thumbnails with hover effects and data labels.
  - **Secure Media Delivery**: Integrated authenticated image fetching via the `/media/` endpoint, protected by Django session-auth and Nginx `X-Accel-Redirect`.
  - **Interactive Lightbox**: Added a high-fidelity image overlay (lightbox) for full-size screenshot inspection with dismiss-on-click functionality.
  - **API Optimization**: Updated the `SubdomainsViewSet` to support an `only_screenshot` filter, significantly reducing payload size for the visual gallery.
  - **Backend Validation**: Verified and hardened the EyeWitness result ingestion pipeline (`Requests.csv` parsing) in `tasks.py` to ensure reliable DB synchronization.
- **Proxy & Vault Persistence Stability**:
  - Resolved missing `CircularProgress` import in `ProxySettingsPage.tsx` that caused frontend build failures.
  - Fixed Acunetix (AWVS) configuration persistence bug by correctly mapping `acunetix_url` and `acunetix_key` in the `useUpdateApiVault` mutation.
  - Synchronized frontend `FormData` keys with backend expectations (`key_acunetix_url`, `key_acunetix_key`).
  - Improved UI responsiveness for rescan actions and proxy fetching with immediate Snackbar feedback.
- **Bounty Hub Migration**: Completed the transition of the HackerOne Bounty Hub to the new React v3 architecture.
    - **Bulk Program Import**: Implemented a modern, persistent floating action bar for bulk importing programs into current projects.
    - **Asset Accordion Detail View**: Refactored the program details modal with grouped accordion views for organized asset browsing (Domain, IP, URL).
    - **Integrated Target Management**: Added "Add Target" functionality directly within the Bounty Hub asset list for immediate orchestration.
    - **HackerOne Metadata Enrichment**: Program cards now feature "Since" date, currency indicators, and "Open Scope"/"New" status badges.
    - **Standardized Tactical Feedback**: Integrated the global Snackbar system for all import and asset addition actions.
- **Dashboard & Scans:**
    - Improved Scan Detail header layout (breadcrumbs stacked under actions, right-aligned).
    - Fixed HTTP Status Breakdown chart to accurately display all status codes.
    - Synchronized Subdomain status attributes with probing results in the background engine.
    - Expanded Scan Summary data to include status codes from both subdomains and endpoints.
- **OSINT Intelligence Dashboard**: Implemented a comprehensive reconnaissance data visualization suite:
    - **Modular OSINT Tab**: Integrated a new, tactical dashboard into the Scan Detail view to aggregate and visualize discovery data.
    - **Email & Credential Exposure**: Displays discovered email addresses and associated leaked credentials in a secure, copy-able table.
    - **Employee Insights**: Visualizes discovered professional personnel and their designations in a responsive card grid.
    - **Search Engine Dorking Results**: Consolidated view of all search engine discovery URLs with direct links to findings.
    - **Document Metadata Analysis**: Detailed table of metadata (Author, OS, Creation Software) extracted from public documents via MetaFinder.
    - **Automated Dork Generation**: Introduced an "Autogenerate Dorks" feature in the scan initiation modal to programmatically build sensitive search queries for any target domain.
- **Plugin Orchestration System**: Introduced a powerful, modular system to extend reNgine with custom engines and UI.
  - **Dynamic Task Injection**: Implemented `PluginOrchestrator` to inject custom tasks into Celery scan chains at specific anchor points (e.g., after Vulnerability Scan).
  - **Pipeline Builder**: Created a drag-and-drop UI for reordering plugins relative to core engines.
  - **Atomic Installation**: Developed a secure installation system with automated database backups and rollback mechanisms for plugin management.
  - **Dynamic UI Modules**: Enabled runtime injection of custom React components into scan detail pages via ESM module loading.
  - **Plugin Registry**: Full CRUD support for plugin management, including enabling/disabling and metadata tracking.
- **Frontend Bundle Optimization**: Implemented granular manual chunking in Vite to split massive vendor libraries into smaller, more manageable bundles.
- **Route-Level Code Splitting**: Implemented lazy loading for all major tactical pages using TanStack Router's `lazyRouteComponent`, significantly reducing the initial application payload.
- **Plugin Management Pipeline Stability**: 
  - **404 Route Resolution**: Fixed a critical routing issue where refreshing the plugin management page would result in a 404 error by correctly registering the `/plugins/` route in the dashboard URL configuration.
  - **Hardened Atomic Installation**: Resolved 500 Internal Server Errors during plugin uploads by improving the `AtomicInstaller` database backup and rollback logic.
  - **Secure Authentication**: Implemented `PGPASSWORD` environment injection for secure, non-interactive database operations during plugin lifecycle events.
  - **Robust Environment Handling**: Migrated from fragile `os.environ.get` calls to centralized Django settings for database connection parameters.
  - **API Format Standardization**: Resolved frontend crashes and display issues by standardizing the plugin API to return non-paginated arrays and hardening React components with `Array.isArray` guards.

- **Hardened Plugin Asset Lifecycle**: Implemented automatic synchronization and cleanup for plugin UI assets.
  - **Asset Mirroring**: Updated `AtomicInstaller` to automatically mirror plugin UI components to `MEDIA_ROOT` during installation, ensuring they are accessible to the frontend via authenticated `/media/` paths.
  - **Automated Cleanup**: Integrated `post_delete` signals to automatically prune both internal data and public assets when a plugin is removed.
  - **Registry Robustness**: Enhanced `PluginComponent` to support both `overrides` and `components` manifest keys, ensuring compatibility with diverse plugin architectures (e.g., Exploit Readiness Layer).
  - **Full Lifecycle UI**: Wired up the "Delete Plugin" button in the frontend with confirmation dialogs and backend synchronization.
  - **Sync Management**: Added a `sync_plugin_ui` management command to retroactively repair UI asset placement for existing installations.

- **Automated Startup Synchronization**:
  - Implemented a robust, Redis-locked startup sequence in Celery to ensure essential datasets are synchronized when the system comes online.
  - **Graph Sync**: Automatically triggers a global Attack Surface graph synchronization (`sync_all_scans_to_graph`) upon system startup.
  - **CISA KEV Sync**: Automatically fetches and updates the Known Exploited Vulnerabilities (KEV) catalog (`sync_cisa_kev_catalog`) to ensure vulnerability intelligence is available immediately.
  - **Distributed Locking**: Uses Redis-based mutexes (`rengine:startup_graph_sync_lock` and `rengine:startup_kev_sync_lock`) to ensure tasks run exactly once across multi-worker deployments.

### Bug Fixes
- **Brute-Force Success Parsing**: Hardened the Medusa result parsing regex to require an explicit `[SUCCESS]` marker, eliminating false positives caused by misinterpreting `[FAILURE]` results.
- **Hydra Result Extraction**: Implemented robust parsing for Hydra output logs to correctly ingest discovered credentials into the vulnerability dashboard.
- **Scan Detail Page Stability**: Resolved runtime crashes (`TypeError: i?.forEach is not a function`) by implementing defensive `Array.isArray` checks and optional chaining across `ScanDetailPage`, `VulnerabilityTable`, and `AttackSurfaceTab`.
- **Scan Summary API Hardening**: Refactored `matched_gf_count` from a dictionary to a list of objects in the backend and API serializers to ensure type consistency and safe iteration on the frontend. Fixed a `500 Internal Server Error` in `ScanSummaryAPIView` caused by missing model imports.
- **SPA Navigation Hardening**: Replaced legacy `window.location.href` redirects in `LogoutPage.tsx` with TanStack Router's `navigate` to maintain application state and prevent unnecessary full-page reloads.
- **Automated Infrastructure Stability**: Integrated `custom_engines` directory creation into the Docker build and entrypoint processes to prevent runtime `FileNotFoundError` during engine initialization.
- **LLM Report Generation Dependency**: Fixed a `TypeError` in `create_report` where the `LLMReportGenerator` was missing its required `logger` dependency.
- **Version Badge Persistence**: Resolved a UI bug where the version badge would disappear shortly after page load by adding `rengine_version` to the dashboard API serializer and implementing defensive state updates.
- **Report Layout Refinements**: Fixed an issue in the Modern PDF report where the Table of Contents list would jump to a new page, leaving the title orphaned. Refactored TOC styles to use a more stable layout and added page-break avoidance rules.
- **Celery Task Resilience**: Resolved a `TypeError` in `RengineTask.write_results` caused by tasks returning boolean values. Implemented safe type checking and string casting for all task results.
- **Dockerfile Architecture Stability**: Fixed a bug in the Trivy installation logic where it hardcoded 32-bit binaries instead of using the detected system architecture.
- **Django System Check Cleanup**: Resolved the `(fields.W340)` warning by removing redundant `null=True` parameters from `ManyToManyField` definitions in `EndPoint` models.
- **Missing Nmap Timeline Commands**: Resolved an issue where Nmap commands were not appearing in the scan timeline overlay. Subtasks now correctly inherit and propagate their parent's activity ID, ensuring all executed commands are properly linked and visualized in the task overlay.
- **Refined Proxy Rotation Logic**: Optimized proxy rotation across all discovery and vulnerability modules. Each individual tool execution (Arjun, Kiterunner, ParamSpider, LinkFinder, Nuclei severities, etc.) now fetches a fresh random proxy, ensuring maximum traffic randomization and bypassing detection.
- **ParamSpider Optimization**: Optimized `web_api_discovery` to ensure `ParamSpider` only runs once per unique subdomain. Previously, it was being re-executed for every URL belonging to the same subdomain, leading to redundant work and log clutter.
- **Endpoint Deduplication**: Implemented URL pattern normalization in `web_api_discovery`. The engine now intelligently skips redundant endpoints that differ only by parameter values (e.g., locale variations), significantly reducing the number of tool calls while maintaining discovery coverage.
- **cPanel Scan Fix**: Resolved an `AttributeError` in the `cpanel_scan` task where the system attempted to access a non-existent `use_proxy` attribute on the `ScanHistory` model. The task now correctly utilizes the global proxy configuration system.
- **Arjun Results Parsing Fix**: Resolved `'list' object has no attribute 'items'` error during endpoint ingestion.
- **Proper Scan Termination**: Resolved critical failures in scan termination by aligning frontend and backend to a unified `StopScan` API.
    - **Deep Task Revocation**: Enhanced the backend to explicitly revoke all sub-tasks registered in `ScanActivity`, ensuring child processes (like port scans or nuclei) are killed immediately.
    - **Consistent Subscan Abort**: Fixed a loop logic error in the backend that prevented subscans from being stopped reliably.
    - **Unified API Hooks**: Refactored frontend hooks (`useStopScan`, `useBulkScanAction`, `useBulkStopSubScans`) to use the hardened `StopScan` endpoint with consistent payload structures.
- **Hydra Brute-Force Resilience & Service Mapping**:
    - Implemented `max_retries` in engine configuration to prevent infinite loops on tool failure.
    - Added automated service mapping to convert generic protocols (e.g., `http`, `https`) into valid Hydra modules (`http-get`, `https-get`).
    - Integrated automatic error tracking that terminates scan tasks after the configured retry threshold.



## v2.5.2

### Bug Fixes
- **SSLScan Parser**: Hardened the SSLScan XML parser against `NoneType` errors and missing elements in reports.
- **UI Rendering**: Fixed a bug where newlines in vulnerability descriptions, impacts, and remediations were being lost due to aggressive HTML encoding. Added `white-space: pre-wrap` to correctly render multi-line text in the dashboard.
- **Medusa Brute-Force Parser**: Fixed success identification logic for Medusa v2.2 by updating the result parsing regex to handle variations in output format, including optional Host fields and bracket styles.
- **Selective Brute-Force Triggering**: Restricted automatic brute-force scan triggering to only occur if `brute_force_scan` is explicitly selected for the current scan or subscan, preventing unintended executions.


## v2.5.1

### Bug Fixes
- **Monitoring Frequency**: Fixed a bug where monitoring frequency was stored as an integer, causing mismatch with the expected choice values in task scheduling.
- **Nmap Parser**: Added validation logic to filter out common false positive alerts from Nmap script results (e.g., timeouts, failed executions, and "not vulnerable" messages).


### New Features
- **Continuous Monitoring Engine**: Automated periodic discovery of new subdomains, directories, and login pages with real-time alerting and automated scan triggers.
- **Monitoring Dashboards**: Dedicated global monitoring dashboard and target-specific monitoring tabs to track asset growth over time.
- **Auth Brute-Force Engine**: Integrated Medusa for high-performance authentication testing across multiple services (HTTP, SSH, etc.).
- **Stealth Brute-Force Orchestrator**: Advanced orchestrator with dynamic proxy rotation via Proxychains4, batched attempts (1-10 per proxy), and random delays to bypass account lockout and IP blacklisting.
- **Deep Fingerprint Parsing**: Enhanced Nmap parsing to extract page titles even from 404, 401, and 403 responses by analyzing raw service fingerprint strings.
- **Automated Auth Triggering**: New logic to automatically trigger brute-force scans when an authentication portal or VPN gateway is detected, provided the brute-force module is enabled in the selected scan engine.
- **Curated Auth Wordlists**: Added specially curated "top/default" and "most common" wordlists for authentication testing, persisted in the `/usr/src/wordlist/auth/` volume.
- **Nmap Vuln Script Support**: Added comprehensive parsing for Nmap `vuln` script outputs, integrating them directly into the vulnerability dashboard.
- **Repository Migration**: Formally transitioned the project to `whiterabb17/rengine` as an unofficial fork.
- **Enhanced Update Check**: Implemented a fallback mechanism that checks both GitHub Releases and the raw `.version` file in the master branch. If a newer version is detected in the repository root, the system directs users to the main repo instead of the releases page.

## v2.4.0

### New Features
- **OpSec Settings**: Advanced stealth configuration including User-Agent rotation, custom rate limiting, WAF bypass headers, and custom DNS resolvers.
- **Stealth Presets**: Quick configuration for "Quiet", "Balanced", and "Aggressive" scan modes.
- **Metadata Stripping**: Automatically remove sensitive EXIF data and metadata from captured screenshots and downloaded OSINT documents.
- **New Scan Engine (Firewall & VPN)**: Dedicated Sophos Firewall and VPN scan engine with IKE and SSL scan capabilities.
- **New Tool Integrations**: Integrated Chaos, TLSX, CTFR, Netlas, and Katana for broader and more efficient reconnaissance.
- **Automatic Proxy Fetching and Validation**: Automatically sources and tests live proxies from multiple providers to ensure scan stability and stealth.
- **Improved NMap Vulners Script Parsing**: Enhanced parsing of NMap vulnerability scan results for more accurate service and version identification.
- **LLM-Powered Report Summaries and Conclusions**: Automatically generates Assessment Overviews, Executive Briefs, and Final Conclusions in PDF reports using OpenAI or local LLMs (Ollama).

### Bug Fixes
- **theHarvester Integration**: Fixed Docker installation and runtime issues for theHarvester OSINT tool.

## v2.2.0

## What's Changed

### Summary
- Introducing Bounty Hub: Central platform for managing and importing bug bounty programs
- New Built-in notification system for important events and updates
- Enhanced subdomain discovery using Chaos project dataset
- Bug Bounty Mode as user preference to enable or disable features related to bug bounty
- Path exclusion feature for scans
- New visually appealing PDF report template
- Regex support for out-of-scope subdomains
- Stop All Scans killswitch to halt multiple running scans at once
- Smart rescans that automatically import and apply previous scan configurations
- Improved Start Scan UI for consistent configuration across multiple scans
- Support for bulk uploads of nuclei and gf patterns
- API key protection (masking in settings view)

* feat: Allow uploading of multiple gf patterns #1318 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1319
* feat: Introduce stop multiple scans #1270 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1321
* feat: Mask API keys Fixes #1213 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1331
* feat: Allow uploading multiple nuclei patterns #461 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1320
* feat: Introduce github action for auto updating version and changelog on every release by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1348
* chores: Removes external IP from reNgine ui by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1350
* feat: Implement URL Path Exclusion Feature with Regex Support Fixes #1264 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1354
* feat: Consistent start scan ui across schedule scan, multiple scans. Now supports import, out of scope subdomains, starting path, excluded path for all types of scan #1357 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1361
* Update of template.html with conditional statement by @DamianHusted in https://github.com/yogeshojha/rengine/pull/1378
* feat: feat ability to delete multiple scheduled scan #1360 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1382
* feat: Enhanced Out of Scope Subdomain Checking, Support for regex in out of scope scan parameter #1358  by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1380
* feat: Store and showcase scan related configuration such as imported subdomains, out of scope subdomains, starting point url and excluded paths fixes #1356 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1383
* Update celery-entrypoint.sh by @SJ029626 in https://github.com/yogeshojha/rengine/pull/1390
* feat:  Prefll the scan parameters during rescan with the scan configuration values that were being used in earlier scan #1381  by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1386
* feat: Added additional templates for PDF reports #1387 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1391
* Replace CVE-2024-41661 with CVE-2023-50094 by @shelbyc in https://github.com/yogeshojha/rengine/pull/1393
* hotfix: Workflow autocomment issues by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1396
* Fix comment workflow on fork PRs by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1400
* Hotfix/workflow cmt1 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1401
* fix author name by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1403
* Update of the uninstall.sh script by @DamianHusted in https://github.com/yogeshojha/rengine/pull/1385
* feat: Builtin notification system in reNgine #1392  by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1394
* feat: Show what's new popup when update happens and new features are released #1395  by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1405
* feat: Add Chaos for subdomain enumeration #173 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1406
* Version 2.1.3 contains a patch for CVE-2024-43381 by @shelbyc in https://github.com/yogeshojha/rengine/pull/1412
* feat: Introducing Bounty Hub, a central hub to import and manage your hackerone programs to reNgine by @null-ref-0000 in https://github.com/yogeshojha/rengine/pull/1410
* feat: Add ability to delete multiple organizations by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1417
* feat: Enable bug bounty mode as User Preference to separate bug bounty related features #1411 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1418
* bug: remove watchmedo usage in production #1419 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1424
* feat: Create organization when quick adding targets #492 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1425
* reNgine 2.2.0 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1349

## New Contributors
* @DamianHusted made their first contribution in https://github.com/yogeshojha/rengine/pull/1378
* @SJ029626 made their first contribution in https://github.com/yogeshojha/rengine/pull/1390
* @shelbyc made their first contribution in https://github.com/yogeshojha/rengine/pull/1393

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.1.3...v2.2.0

## 2.1.3

**Release Date: Aug 18, 2024**

## What's Changed

### Security Update

* (Security) CVE-2024-43381 Stored Cross-Site Scripting (XSS) via DNS Record Poisoning reported by @touhidshaikh Advisory https://github.com/yogeshojha/rengine/security/advisories/GHSA-96q4-fj2m-jqf7

### Bug Fixes

* remove redundant docker environment variables by @jxdv in https://github.com/yogeshojha/rengine/pull/1353
* fix: reNgine installation issue due to orjson and langchain #1362 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1363
* #1364 Fix whois lookup and improve performance by executing various modules of whois lookup to run concurrently by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1368
* chores: Add error handling for the curl command by @gitworkflows in https://github.com/yogeshojha/rengine/pull/1367
* Update Github Actions Workflows by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1369
* chores: Fix docker build on master by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1373

#### New Contributors
* @gitworkflows made their first contribution in https://github.com/yogeshojha/rengine/pull/1367

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.1.2...v2.1.3

## 2.1.2

**Release Date: July 30, 2024**

## What's Changed

### Security update
* (Security) CVE-2023-50094 Fix Authenticated command injection in WAF detection tool reported by @n-thumann Advisory https://github.com/yogeshojha/rengine/security/advisories/GHSA-fx7f-f735-vgh4

### Bug Fixes

* Fix issue while initiating periodic and clocked scan #1322 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1328
* Fix 500 error on "Test Hackerone api Key" by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1332
* UI Typos and bug Fixes #1333 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1334
* Fix error during tool update Fixes #1152 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1335
* Upgrade setuptools to 72.1.0 to resolve installation error by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1338
* (chores) Fix github pages build by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1339
* Fix subdomain import for subdomains with suffixes more than 4 chars Fixes #1128 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1340

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.1.1...v2.1.2


## 2.1.1

**Release Date: July 20, 2024**

## What's Changed and Fixed
* Update contribution guidelines reference by @emmanuel-ferdman in https://github.com/yogeshojha/rengine/pull/1286
* fix xss on page title fix #1185 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1296
* fix context key error #1263 #1209 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1294
* fix xss on vulnerability description payloads #1262 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1298
* (bug) fix screenshot csv parser #1299 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1300
* (Security) Fixes #1202 bug risk of leaking the scan result files by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1301
* Fix #1291 Refactor Makefiles for windows/linux to accomodate both v1 and v2 of docker compose by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1302
* Fix custom_header to accept multiple headers using custom_headers by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1303
* Handle hash in url, added navigation for Tabs, Fixes #1155 bug href link with html id does not link to the expected url by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1306
* Optimize uninstall scripts to perform operations only related to reNgine Fixes # 1187 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1307
* Added validators to validate URL fixes #1176 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1308
* Fix LLM/langchain issue for fetching vulnerability report using local LLM model Fixed #1292  local model dont use fetch gpt vulnerability details by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1311
* Fixes for Clocked and Periodic Scans Fix #1287 Fixes #1015 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1313
* Fix Not able to add todo from All Subdomains Section Fixes #1310 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1314
* Fix #1315 Fix for todo URLs not compatible with slugs by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1316
* Fixes #1122 But in port service lookup that caused multiple entries of Port with same port number but different service name/description by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1317

#### New Contributors
* @emmanuel-ferdman made their first contribution in https://github.com/yogeshojha/rengine/pull/1286

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.1.0...v2.1.1

## 2.1.0

**Release Date: June 22, 2024**

## What's Changed
* ARM support
* Add LLM Toolkit by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1259
* use django-env by @fopina in https://github.com/yogeshojha/rengine/pull/1230
* Add Lark to notifications. by @iuime in https://github.com/yogeshojha/rengine/pull/1137
* Added restart: always to redis container by @null-ref-0000 in https://github.com/yogeshojha/rengine/pull/1275
* Dockerfile cleanup: reduce image size 3x by @sa7mon in https://github.com/yogeshojha/rengine/pull/1212
* Support for ARM-based platforms and remove obsolete composer version by @metehan-arslan in https://github.com/yogeshojha/rengine/pull/1242
* Fix importing CIDR blocks by @pbehnke in https://github.com/yogeshojha/rengine/pull/1205
* Added SAN extension to the generated certs by @michschl in https://github.com/yogeshojha/rengine/pull/1282
* Release/2.1.0 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1147
* Dockerfile Build Multiple Platforms by @vncloudsco in https://github.com/yogeshojha/rengine/pull/1210

#### New Contributors
* @fopina made their first contribution in https://github.com/yogeshojha/rengine/pull/1230
* @iuime made their first contribution in https://github.com/yogeshojha/rengine/pull/1137
* @null-ref-0000 made their first contribution in https://github.com/yogeshojha/rengine/pull/1275
* @sa7mon made their first contribution in https://github.com/yogeshojha/rengine/pull/1212
* @metehan-arslan made their first contribution in https://github.com/yogeshojha/rengine/pull/1242
* @pbehnke made their first contribution in https://github.com/yogeshojha/rengine/pull/1205
* @michschl made their first contribution in https://github.com/yogeshojha/rengine/pull/1282
* @vncloudsco made their first contribution in https://github.com/yogeshojha/rengine/pull/1210

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.0.6...v2.1.0

## 2.0.6

**Release Date: May 11, 2024**

## What's Changed
* Fix installation error and celery workers having issues with httpcore
* remove duplicate gospider references by @Talanor in https://github.com/yogeshojha/rengine/pull/1245
* Fix "subdomain" s3 bucket by @Talanor in https://github.com/yogeshojha/rengine/pull/1244
* Fix Txt File Var Declaration by @specters312 in https://github.com/yogeshojha/rengine/pull/1239
* Bug Correction: When dumping and loading customscanengines by @TH3xACE in https://github.com/yogeshojha/rengine/pull/1224
* Fix/infoga removal by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1249
* Fix #1241 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1251

#### New Contributors
* @Talanor made their first contribution in https://github.com/yogeshojha/rengine/pull/1245
* @specters312 made their first contribution in https://github.com/yogeshojha/rengine/pull/1239
* @TH3xACE made their first contribution in https://github.com/yogeshojha/rengine/pull/1224

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.0.5...v2.0.6

## 2.0.5

**Release Date: April 20, 2024**

* Fix #1234 reNgine unable to load celery tasks due to mismatched celery and redis versions

## 2.0.4

**Release Date: April 18, 2024**

## What's Changed
* chore: update version number to 2.0.3 by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/1180
* Fix various ffuf bugs by @yarysp in https://github.com/yogeshojha/rengine/pull/1199
* Set and update default YAML config with all latest vars by @yarysp in https://github.com/yogeshojha/rengine/pull/1200
* Add checks for placeholder in custom tool task by @yarysp in https://github.com/yogeshojha/rengine/pull/1201
* Whatportis - Replace purge by truncate to prevent port import error by @yarysp in https://github.com/yogeshojha/rengine/pull/1203
* ops(installation): fix nano not being installed when absent by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/1143
* Complete dev environment to debug/code easily by @yarysp in https://github.com/yogeshojha/rengine/pull/1196
* Revert "Complete dev environment to debug/code easily" by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1225
* Update README.md | Fixed 1 broken link to the regine.wiki by @jostasik in https://github.com/yogeshojha/rengine/pull/1226
* Fix uninitialised variable cmd in custom_subdomain_tools by @cpandya2909 in https://github.com/yogeshojha/rengine/pull/1207
* [FIX] security: OS Command Injection vulnerability (x2) #1219 by @0xtejas in https://github.com/yogeshojha/rengine/pull/1227

### New Contributors :rocket: 
* @yarysp made their first contribution in https://github.com/yogeshojha/rengine/pull/1199
* @jostasik made their first contribution in https://github.com/yogeshojha/rengine/pull/1226
* @cpandya2909 made their first contribution in https://github.com/yogeshojha/rengine/pull/1207
* @0xtejas made their first contribution in https://github.com/yogeshojha/rengine/pull/1227

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.0.3...v2.0.4


## 2.0.3

**Release Date: January 25, 2024**

## What's Changed
* CI: update GitHub action versions by @jxdv in https://github.com/yogeshojha/rengine/pull/1136
* Fixed (subdomain_discovery | ERROR | local variable 'use_amass_config' referenced before assignment) by @Deathpoolxrs in https://github.com/yogeshojha/rengine/pull/1149
* chore: update LICENSE by @jxdv in https://github.com/yogeshojha/rengine/pull/1153
* Fix subdomains list empty in Target by @psyray in https://github.com/yogeshojha/rengine/pull/1166
* Fix top menu text overflow in low resolution by @psyray in https://github.com/yogeshojha/rengine/pull/1167
* Update auto comment workflow due to deprecation warnings by @ErdemOzgen in https://github.com/yogeshojha/rengine/pull/1126
* Change Redirect URL after login to prevent 500 error by @psyray in https://github.com/yogeshojha/rengine/pull/1124
* fix-1030: Add missing slug on target summary link by @psyray in https://github.com/yogeshojha/rengine/pull/1123

### New Contributors
* @Deathpoolxrs made their first contribution in https://github.com/yogeshojha/rengine/pull/1149
* @ErdemOzgen made their first contribution in https://github.com/yogeshojha/rengine/pull/1126

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.0.2...v2.0.3


## 2.0.2

**Release Date: December 8, 2023**


## What's Changed
* Added tooltip text to dashboard total vulnerabilities tooltip by @luizmlo in https://github.com/yogeshojha/rengine/pull/1029
* ops(`uninstall.sh`): add missing volumes and echo messages by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/977
* Fix no results in target subdomain list by @psyray in https://github.com/yogeshojha/rengine/pull/1036
* Fix Tool Settings Broken Link by @aqhmal in https://github.com/yogeshojha/rengine/pull/1021
* Fix subdomains list empty in Target by @psyray in https://github.com/yogeshojha/rengine/pull/1053
* Raise page limit to 500 for popup list by @psyray in https://github.com/yogeshojha/rengine/pull/1051
* Add directories count on Directories list by @psyray in https://github.com/yogeshojha/rengine/pull/1050
* ops(docker-compose): upgrade to 2.23.0 by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/1023
* Fix endpoints list and count by @psyray in https://github.com/yogeshojha/rengine/pull/1041
* Fix failing visualization when dorks are present by @psyray in https://github.com/yogeshojha/rengine/pull/1045
* Fix note not saving by @psyray in https://github.com/yogeshojha/rengine/pull/1047
* Count only not done todos in subdomains list by @psyray in https://github.com/yogeshojha/rengine/pull/1048
* Fix user agent definition keyword by @psyray in https://github.com/yogeshojha/rengine/pull/1054
* Upgrade project discovery tool at CT build by @psyray in https://github.com/yogeshojha/rengine/pull/1055
* Add a check to not load datatables twice by @psyray in https://github.com/yogeshojha/rengine/pull/1039
* Nmap port scan fails when Naabu return no port by @psyray in https://github.com/yogeshojha/rengine/pull/1067
* chore(issue-templates): incorrect label name by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/1066
* Endpoints list popup empty by @psyray in https://github.com/yogeshojha/rengine/pull/1070
* Add missing domain id value in subscan by @psyray in https://github.com/yogeshojha/rengine/pull/1069
* Fixes for #1033, #1026, #1027 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1071
* Temporary fix to prevent celery beat crash by @psyray in https://github.com/yogeshojha/rengine/pull/1072
* fix: ffuf ANSI code processing preventing task to finish by @ocervell in https://github.com/yogeshojha/rengine/pull/1058
* Update views.py by @Vijayragha1 in https://github.com/yogeshojha/rengine/pull/1074
* Fix crash on saving endpoint (FFUF related only) by @psyray in https://github.com/yogeshojha/rengine/pull/1063
* chore(issue-templates): fix incorrect description by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/1078
* IOError -> OSError by @jxdv in https://github.com/yogeshojha/rengine/pull/1081
* Add directories count on Directories list by @psyray in https://github.com/yogeshojha/rengine/pull/1090
* chore(issue-template): don't allow blank issues by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/1089
* Fix bad nuclei config name by @psyray in https://github.com/yogeshojha/rengine/pull/1098
* disallow empty password by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1105
* fix attribute error on scan history #1103 by @yogeshojha in https://github.com/yogeshojha/rengine/pull/1104
* issue-633: added already-in-org filter to target dropdown in org form by @SeanOverton in https://github.com/yogeshojha/rengine/pull/1106
* Update Dockerfile to fix silicon incompatability by @SubGlitch1 in https://github.com/yogeshojha/rengine/pull/1107
* Add source for nmap scan by @psyray in https://github.com/yogeshojha/rengine/pull/1108
* Spelling mistake in hackerone.html by @Linuxinet in https://github.com/yogeshojha/rengine/pull/1112
* fix(version): incorrect number in art by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/1111
* Fix report generation when `Ignore Informational Vulnerabilities` checked by @psyray in https://github.com/yogeshojha/rengine/pull/1100
* fix(tool_arsenal): incorrect regex version numbers by @AnonymousWP in https://github.com/yogeshojha/rengine/pull/1086

### New Contributors
* @luizmlo made their first contribution in https://github.com/yogeshojha/rengine/pull/1029 :partying_face: 
* @aqhmal made their first contribution in https://github.com/yogeshojha/rengine/pull/1021 :partying_face: 
* @C0wnuts made their first contribution in https://github.com/yogeshojha/rengine/pull/973 :partying_face: 
* @ocervell made their first contribution in https://github.com/yogeshojha/rengine/pull/1058 :partying_face: 
* @Vijayragha1 made their first contribution in https://github.com/yogeshojha/rengine/pull/1074 :partying_face: 
* @jxdv made their first contribution in https://github.com/yogeshojha/rengine/pull/1081 :partying_face: 
* @SeanOverton made their first contribution in https://github.com/yogeshojha/rengine/pull/1106 :partying_face: 
* @SubGlitch1 made their first contribution in https://github.com/yogeshojha/rengine/pull/1107 :partying_face: 
* @Linuxinet made their first contribution in https://github.com/yogeshojha/rengine/pull/1112 :partying_face: 

**Full Changelog**: https://github.com/yogeshojha/rengine/compare/v2.0.1...v2.0.2

Once again excellent work on reNgine v2.0.2 by @AnonymousWP, @psyray, @ocervell and everybody else! :rocket: 

## 2.0.1

**Release Date: October 24, 2023**


2.0.1 fixes a ton of issues in reNgine 2.0.

Fixes: 
1. Prevent duplicating Nuclei vulns for subdomain #1012 @psyray
2. Fixes for empty subdomain returned during nuclei scan #1011 @psyray
3. Add all the missing slug in scanEngine view & other places #1005 @psyray
4. Foxes for missing vulscan script #1004 @psyray
5. Fixes for missing slug in report settings saving #1003
6. Fixes for Nmap Parsing Error #1001 #1002 @psyray
7. Fix nmap script ports iterable args #1000 @psyray
8. Iterate over hostnames when multiple #1002 @psyray
8. Gau install #998, change gauplus to gau @psyray
9. Add missing slug parameter in schedule scan #996 @psyray
10. Add missing slug parameter in schedule scan #996, fixes #940, #937, #897, #764 @psyray
11. Add stack trace into make logs if DEBUG True #994 @psyray
12. Fix dirfuzz base64 name display #993 #992 @psyray
13. Fix target subdomains list not loading #991 @psyray
14. Change WORDLIST constant value #987, fixes #986@psyray 
15. fix(notification_settings): submitting results in error 502 #981 fixes #970 @psyray
16. Fixes with documentation and installation/update/uninstall scripts @anonymousWP
17. Fix file directory popup not showing in detailed scan #912 @psyray


@AnonymousWP and @psyray have been phenomenal in fixing these bugs. Thanks to both of you! :heart: :rocket: 


## 2.0.0

**Release Date: October 7, 2023**

###  Added
 - Projects: Projects allow you to efficiently organize their web application reconnaissance efforts. With this feature, you can create distinct project spaces, each tailored to a specific purpose, such as personal bug bounty hunting, client engagements, or any other specialized recon task.
 - Roles and Permissions: assign distinct roles to your team members: Sys Admin, Penetration Tester, and Auditor—each with precisely defined permissions to tailor their access and actions within the reNgine ecosystem.
 - GPT-powered Report Generation: With the power of OpenAI's GPT, reNgine now provides you with detailed vulnerability descriptions, remediation strategies, and impact assessments.
 - API Vault: This feature allows you to organize your API keys such as OpenAI or Netlas API keys.
 - GPT-powered Attack Surface Generation
 - URL gathering now is much more efficient, removing duplicate endpoints based on similar HTTP Responses, having the same content_lenth, or page_title. Custom duplicate fields can also be set from the scan engine configuration.
 - URL Path filtering while initiating scan: For instance, if we want to scan only endpoints starting with https://example.com/start/, we can pass the /start as a path filter while starting the scan. [@ocervell](https://github.com/ocervell)
 - Expanding Target Concept: reNgine 2.0 now accepts IPs, URLS, etc as targets. (#678, #658) Excellent work by [@ocervell](https://github.com/ocervell)
 - A ton of refactoring on reNgine's core to improve scan efficiency. Massive kudos to [@ocervell](https://github.com/ocervell)
 - Created a custom celery workflow to be able to run several tasks in parallel that are not dependent on each other, such OSINT task and subdomain discovery will run in parallel, and directory and file fuzzing, vulnerability scan, screenshot gathering etc. will run in parallel after port scan or url fetching is completed. This will increase the efficiency of scans and instead of having one long flow of tasks, they can run independently on their own. [@ocervell](https://github.com/ocervell)
 - Refactored all tasks to run asynchronously [@ocervell](https://github.com/ocervell)
 - Added a stream_command that allows to read the output of a command live: this means the UI is updated with results while the command runs and does not have to wait until the task completes. Excellent work by [@ocervell](https://github.com/ocervell)
 - Pwndb is now replaced by h8mail. [@ocervell](https://github.com/ocervell)
 - Group Scan Results: reNgine 2.0 allows to group of subdomains based on similar page titles and HTTP status, and also vulnerability grouping based on the same vulnerability title and severity.
 - Added Support for Nmap: reNgine 2.0 allows to run Nmap scripts and vuln scans on ports found by Naabu. [@ocervell](https://github.com/ocervell)
 - Added support for Shared Scan Variables in Scan Engine Configuration:
    - `enable_http_crawl`: (true/false) You can disable it to be more stealthy or focus on something different than HTTP
    - `timeout`: set timeout for all tasks
    - `rate_limit`: set rate limit for all tasks
    - `retries`: set retries for all tasks
    - `custom_header`: set the custom header for all tasks
 - Added Dalfox for XSS Vulnerability Scan
 - Added CRLFuzz for CRLF Vulnerability Scan
 - Added S3Scanner for scanning misconfigured S3 buckets
 - Improve OSINT Dork results, now detects admin panels, login pages and dashboards
 - Added Custom Dorks
 - Improved UI for vulnerability results, clicking on each vulnerability will open up a sidebar with vulnerability details.
 - Added HTTP Request and Response in vulnerability Results
 - Under Admin Settings, added an option to allow add/remove/deactivate additional users
 - Added Option to Preview Scan Report instead of forcing to download
 - Added Katana for crawling and spidering URLs
 - Added Netlas for Whois and subdomain gathering
 - Added TLSX for subdomain gathering
 - Added CTFR for subdomain gathering
 - Added historical IP in whois section
 - Added Pagination on Large datatables such as subdomains, endpoints, vulnerabilities etc #949 [@psyray](https://github.com/psyray)


### Fixes
 - GF patterns do not run on 404 endpoints (#574 closed)
 - Fixes for retrieving whois data (#693 closed)
 - Related/Associated Domains in Whois section is now fixed
 - Fixed missing lightbox css & js on target screenshot page #947 #948 [@psyray](https://github.com/psyray)
 - Issue in Port-scan: int object is not subscriptable Fixed #939, #938 [@AnonymousWP](https://github.com/AnonymousWP)


### Removed
 - Removed pwndb and tor related to it.
 - Removed tor for pwndb


## 1.3.6
**Release Date: March 2, 2023**

- Fixed installation errors. Fixed #824, #823, #816, #809, #803, #801, #798, #797, #794, #791 .


## 1.3.5
**Release Date: December 29, 2022**

- Fixed #769, #768, #766, #761, Thanks to, @bin-maker, @carsonchan12345, @paweloque, @opabravo


## 1.3.4
**Release Date: November 16, 2022**

### Fixes
- Fixed #748 , #743 , #738, #739


## 1.3.3
**Release Date: October 9, 2022**

### Fixes
- #723, Upgraded Go to 1.18.2


## 1.3.2
**Release Date: August 20, 2022**

### Fixes
- #683 For Filtering GF tags
- #669 Where Directory UI had to be collapsed


## 1.3.1
**Release Date: August 12, 2022**

### Fixes
- Fix for #643 Downloading issue for Subdomain and Endpoints
- Fix for #627 Too many Targets causes issues while loading datatable
- Fix version Numbering issue


## 1.3.0
**Release Date: July 11, 2022**

### Added

- Geographic Distribution of Assets Map
- Added WAF Detector as an optional tool in Scan Engine

### Fixes

- WHOIS Provider Changed
- Fixed Dark UI Issues
- Fix HTTPX Issue with custom Header

## 1.2.0
**Release Date: May 27, 2022**

### Added

- Naabu Exclude CDN Port Scanning
- Added WAF Detection

### Fixes

- Fix #630 Character Name too Long Issue
- [Security] Fixed several instances of Command Injections, CVE-2022-28995, CVE-2022-1813
- Hakrawler Fixed - #623
- Fixed XSS on Hackerone report via Markdown
- Fixed XSS on Import Target using malicious filename
- Stop Scan Fixed #561
- Fix installation issue due to missing curl
- Updated docker-compose version

## 🏷️ 1.1.0
**Release Date: Apr 24, 2022**

- Redeigned UI
- Added Subscan Feature

    Subscan allows further scanning any subdomains. Assume from a normal recon process you identified a subdomain that you wish to do port scan. Earlier, you had to add that subdomain as a target. Now you can just select the subdomain and initiate subscan.

- Ability to Download reconnaissance or vulnerability report
- Added option to customize report, customization includes the look and feel of report, executive summary etc.

- Add IP Address from IP
- WHOIS Addition on Detail Scan and fetch whois automatically on Adding Single Targets
- Universal Search Box
- Addition of Quick Add menus
- Added ToolBox Feature

    ToolBox will feature most commonly used recon tools. One can use these tools to identify whois, CMSDetection etc without adding targets. Currently, Whois, CMSDetector and CVE ID lookup is supported. More tools to follow up.

- Notify New Releases on reNgine if available
- Tools Arsenal Section to feature preinstalled and custom tools
- Ability to Update preinstalled tools from Tools Arsenal Section
- Ability to download/add custom tools
- Added option for Custom Header on Scan Engine
- Added CVE_ID, CWE_ID, CVSS Score, CVSS Metrics on Vulnerability Section, this also includes lookup using cve_id, cwe_id, cvss_score etc
- Added curl command and references on Vulnerability Section
- Added Columns Filtering Option on Subdomain, Vulnerability and Endpoints Tables
- Added Error Handling for Failed Scans, reason for failure scan will be displayed
- Added Related Domains using WHOIS
- Added Related TLDs
- Added HTTP Status Breakdown Widget
- Added CMS Detector
- Updated Visualization
- Option to Download Selected Subdomains
- Added additional Nuclei Templates from https://github.com/geeknik/the-nuclei-templates
- Added SSRF check from Nagli Nuclei Template
- Added option to fetch CVE_ID details
- Added option to Delete Multiple Scans
- Added ffuf as Directory and Files fuzzer
- Added widgets such as Most vulnerable Targets, Most Common Vulnerabilities, Most Common CVE IDs, Most Common CWE IDs, Most Common Vulnerability Tags

And more...

## 🏷️ 1.0.1

**Release Date: Aug 29, 2021**

**Changelog**

- Fixed [#482](https://github.com/yogeshojha/rengine/issues/482) Endpoints and Vulnerability Datatable were showing results of other targets due to the scan_id parameter
- Fixed [#479](https://github.com/yogeshojha/rengine/issues/479) where the scan was failing due to recent httpx release, change was in the JSON output
- Fixed [#476](https://github.com/yogeshojha/rengine/issues/476) where users were unable to click on Clocked Scan (Reported only on Firefox)
- Fixed [#442](https://github.com/yogeshojha/rengine/issues/442) where an extra slash was added in Directory URLs
- Fixed [#337](https://github.com/yogeshojha/rengine/issues/337) where users were unable to link custom wordlist
- Fixed [#436](https://github.com/yogeshojha/rengine/issues/436) Checkbox in Notification Settings were not working due to same name attribute, now fixed
- Fixed [#439](https://github.com/yogeshojha/rengine/issues/439) Hakrawler crashed if the deep mode was activated due to -plain flag
- Fixed [#437](https://github.com/yogeshojha/rengine/issues/437) If Out of Scope subdomains were supplied, the scan was failing due to None value
- Fixed [#424](https://github.com/yogeshojha/rengine/issues/424) Multiple Targets couldn't be scanned

**Improvements**

- Enhanced install script, check for if docker is running service or not #468

**Security**

- Fixed Cross Site Scripting
    - [#460](https://github.com/yogeshojha/rengine/issues/460)
    - [#457](https://github.com/yogeshojha/rengine/issues/457)
    - [#454](https://github.com/yogeshojha/rengine/issues/454)
    - [#453](https://github.com/yogeshojha/rengine/issues/453)
    - [#459](https://github.com/yogeshojha/rengine/issues/459)
    - [#460](https://github.com/yogeshojha/rengine/issues/460)
- Fixed Cross Site Scripting reported on Huntr [#478](https://github.com/yogeshojha/rengine/issues/478)
    [https://www.huntr.dev/bounties/ac07ae2a-1335-4dca-8d55-64adf720bafb/](https://www.huntr.dev/bounties/ac07ae2a-1335-4dca-8d55-64adf720bafb/)

### Verion 1.0 Major release

### Additions
- Dark Mode
- Recon Data visualization
- Improved correlation among recon data
- Ability to identify Interesting Subdomains
- Ability to Automatically report Vulnerabilities to Hackerone with customizable vulnerability report
- Added option to download URLs and Endpoints along with matched GF patterns
- Dorking support for stackoverflow, 3rdparty, social_media, project_management, code_sharing, config_files, jenkins, wordpress_files, cloud_buckets, php_error, exposed_documents, struts_rce, db_files, traefik, git_exposed
- Emails, metainfo, employees, leaked password discovery
- Optin to Add bulk targets
- Proxy Support
- Target Summary
- Recon Todo
- Unusual Port Identification
- GF patterns support #110, #88
- Screenshot Gallery with Filters
- Powerful recon data filtering with auto suggestions
- Added whatportis, this allows ports to be displayed as Service Name and Description
- Recon Data changes, finds new/removed subdomains/endpoints
- Tagging of targets into Organization
- Added option to delete all scan results or delete all screenshots inside Settings and reNgine settings
- Support for custom GF patterns and Nuclei Templates
- Support for editing tool related configuration files (Nuclei, Subfinder, Naabu, amass)
- Option to Mark Subdomains as important
- Separate tab for Directory scan results
- Option to Import Subdomains
- Clean your scan results and screenshots
- Enhanced and Customizable Scan alert with support for sending recon data directly to Discord
- Improvement in Vulnerability Scanning, If endpoint scan is performed, those endpoints will be an input to Nuclei.
- Ignore file extensions in URLs
- Added response time in endpoints and subdomains
- Added badge to identify CDN and non CDN IPs
- Added gospider, gauplus and waybackurls for url discovery
- Added activity log in Scan activity
- For better UX shifted nav bar from vertical position to horizontal position on top. This allows better navigation on recon data.
- Separate table for Directory scan results #244
- Scan results UI now in tabs
- Added badge on Subdomain Result table to directly query Vulnerability and Endpoints
- Webserver and content_type badge has been addeed in Subdomain Result table
- Inside Targets list, Recent Scan button has been added to quickly go to the last scan results
- In target summary, timelin of scan has been added
- Randomized user agent in HTTPX
- reNgine will no longer store any recon data apart from that in Database, this includes sorted_subdomains list.txt or any json file
- aquatone has been replaced with Eyewitness
- Out of Scope subdomains are no longer part of scan engine, they can be imported before initiating the scan
- Added script to uninstall reNgine
- Added option to filter targets and scans using organization, scan status, etc
- Added random user agent in directory scan
- Added concurrency, rate limit, timeout, retries in Scan Engine YAML
- Added Rescan option
- Other tiny fixes.....

### V0.5.3 Feb25 2021
- Build error for Naabu v2 Fixed
- Added rate support for Naabu

### V0.5.2 Feb 23 2021
- Fixed XSS https://github.com/yogeshojha/rengine/issues/347

### V0.5.1 Feb 19 2021

### Features
- Added Discord Support for Notification Web hooks

### V0.5 29 Nov 2020

### Features
- Nuclei Integration: v0.5 is primarily focused on vulnerability scanner using Nuclei. This was a long pending due and we've finally integrated it.

- Powerful search queries across endpoints, subdomains and vulnerability scan results: reNgine reconnaissance data can now be queried using operators like <,>,&,| and !, namely greater than, less than, and, or, and not. This is extremely useful in querying the recon data. More details can be found at Instructions to perform Queries on Recon data

- Out of scope options: Many of you have been asking for out of scope option. Thanks to Valerio Brussani for his pull request which made it possible for out of scope options. Please check the documentation on how to define out of scope options.

- Official Documentation(WIP): We often get asked on how to use reNgine. For long, we had no official documentation. Finally, I've worked on it and we have the official documentation at rengine.wiki

- The documentation is divided into two parts, for Developers and for Penetration Testers. For developers, it's a work in progress. I will keep you all updated throughout the process.

- Redefined Dashboard: We've also made some changes in the Dashboard. The additions include vulnerability scan results, most vulnerable targets, most common vulnerabilities.

- Global Search: This feature has been one of the most requested features for reNgine. Now you can search all the subdomains, endpoints, and vulnerabilities.

- OneForAll Support: reNgine now supports OneForAll for subdomain discovery, it is currently in beta. I am working on how to integrate OneForAll APIKeys and Configuration files.

- Configuration Support for subfinder: You will now have ability to add configurations for subfinder as well.

- Timeout option for aquatone: We added timeout options in yaml configuration as a lot of screenshots were missing. You can now define timeout for http, scan and screenshots for timeout in milliseconds.

- Design Changes A lot of design changes has happened in reNgine. Some of which are:

- Endpoints Results and Vulnerability Scan Results are now displayed as a separate page, this is to separate the results and decrease the page load time.
Checkbox next to Subdomains and Vulnerability report list to change the status, this allows you to mark all subdomains and vulnerabilities that you've already completed working on.
- Sometimes due to timeout, aquatone was skipping the screenshots and due to that, navigations between screenshots was little annoying. We have fixed it as well.
Ability to delete multiple targets and initiate multiple scans.

### Abandoned
- Subdomain Takeover: As we decided to use Nuclei for Vulnerability Scanner, and also, since Subjack wasn't giving enough results, I decided to remove Subjack. The subdomain Takeover will now be part of Nuclei Vulnerability Scanner.

### V0.4 Release 2020-10-08

### Features
- Background tasks migrated to Celery and redis
- Periodic and clocked scan added
- Ability to Stop and delete the scan
- CNAME and IP address added on detail scan
- Content type added on Endpoints section
- Ability to initiate multiple scans at a time

### V0.3 Release 2020-07-21

### Features
- YAML based Customization Engine
- Ability to add wordlists
- Login Feature

### V0.2 Release 2020-07-11

### Features
- Directory Search Enabled
- Fetch URLS using hakrawler
- Subdomain takeover using Subjack
- Add Bulk urls
- Delete Scan functionality

### Fix
- Windows Installation issue fixed
- Scrollbar Issue on small screens fixed

### V0.1 Release 2020-07-08
- reNgine is released
