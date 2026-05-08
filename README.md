<p align="center">
<a href="https://rengine.wiki"><img src="frontend/public/img/banner.png" height="400px" width="520px" alt=""/></a>
</p>

<p align="center">
  <h4 align="center"><strong>Phoenix: Fire from the Ashes even Stronger</strong></h4> 
  <h3 align="center">Official v3 Rebirth: The Ultimate Web Reconnaissance & Vulnerability Scanner 🚀</h3>
</p>

<p align="center"><a href="https://github.com/whiterabb17/r3ngine/releases" target="_blank"><img src="https://img.shields.io/badge/version-v3.0.0-informational?&logo=none" alt="r3ngine Latest Version" /></a>&nbsp;<a href="https://www.gnu.org/licenses/gpl-3.0" target="_blank"><img src="https://img.shields.io/badge/License-GPLv3-red.svg?&logo=none" alt="License" /></a>&nbsp;<a href="#" target="_blank"><img src="https://img.shields.io/badge/first--timers--only-friendly-blue.svg?&logo=none" alt="" /></a></p>

<p align="center">
  <a href="https://www.youtube.com/watch?v=Xk_YH83IQgg" target="_blank"><img src="https://img.shields.io/badge/BlackHat--Arsenal--Asia-2023-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://www.youtube.com/watch?v=Xk_YH83IQgg" target="_blank"><img src="https://img.shields.io/badge/BlackHat--Arsenal--USA-2022-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://www.youtube.com/watch?v=Xk_YH83IQgg" target="_blank"><img src="https://img.shields.io/badge/Open--Source--Summit-2022-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://cyberweek.ae/2021/hitb-armory/" target="_blank"><img src="https://img.shields.io/badge/HITB--Armory-2021-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://www.youtube.com/watch?v=7uvP6MaQOX0" target="_blank"><img src="https://img.shields.io/badge/BlackHat--Arsenal--USA-2021-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://drive.google.com/file/d/1Bh8lbf-Dztt5ViHJVACyrXMiglyICPQ2/view?usp=sharing" target="_blank"><img src="https://img.shields.io/badge/Defcon--Demolabs--29-2021-blue.svg?logo=none" alt="" /></a>&nbsp;
  <a href="https://www.youtube.com/watch?v=A1oNOIc0h5A" target="_blank"><img src="https://img.shields.io/badge/BlackHat--Arsenal--Europe-2020-blue.svg?&logo=none" alt="" /></a>&nbsp;
</p>

<p align="center">
<a href="https://github.com/whiterabb17/r3ngine/actions/workflows/codeql-analysis.yml" target="_blank"><img src="https://github.com/whiterabb17/r3ngine/actions/workflows/codeql-analysis.yml/badge.svg" alt="" /></a>&nbsp;<a href="https://github.com/whiterabb17/r3ngine/actions/workflows/build.yml" target="_blank"><img src="https://github.com/whiterabb17/r3ngine/actions/workflows/build.yml/badge.svg" alt="" /></a>&nbsp;
</p>

<p align="center">
<a href="https://opensourcesecurityindex.io/" target="_blank" rel="noopener">
<img style="width: 282px; height: 56px" src="https://opensourcesecurityindex.io/badge.svg" alt="Open Source Security Index - Fastest Growing Open Source Security Projects" width="282" height="56" /> </a>
</p>
<h4>r3ngine 3.0.0: The Phoenix Rebirth</h4>
<p>
  r3ngine 3.0.0 marks the official rebirth and production stabilization of the project. This version features the new <b>Cyberpunk Phoenix</b> identity, <b>Interactive KPI Reports</b> with internal navigation, and <b>Scoped Attack Surface Visualization</b>. Built on the massive v3.0 core, it represents a complete architectural overhaul designed for the modern threat landscape.
</p>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## 🚀 The v3 Evolution: Comprehensive Enhancements (Since v2.2)

Version 3.0 and the preceding v2.5/2.4 cycles represent a paradigm shift in r3ngine's capabilities. Below are the core pillars of the recent evolution, detailed for security professionals who require surgical precision.

### 🧠 The Intelligence & AI Hub
r3ngine is now an AI-native reconnaissance suite, moving beyond simple tool automation to intelligent analysis.
*   **Centralized AI Hub**: A unified management interface supporting **OpenAI, Anthropic (Claude 3), Google Gemini, and local Ollama models**.
*   **Vulnerability Impact Intelligence**: Automated generation of detailed impact narratives and remediation priorities using LLMs, visualized through interactive **Cytoscape.js attack paths**. Features a seamless, state-aware **Impact Explorer** with real-time assessment monitoring and persistent synchronization to reporting models.
*   **PII Gate Security**: Advanced privacy layer that anonymizes sensitive reconnaissance data (IPs, emails, hostnames) before sending it to external LLMs, ensuring enterprise-grade data protection.
*   **Dynamic Model Discovery**: Real-time fetching of available models with hardware requirement insights for local deployments.

### 🛠️ Advanced Engine Overhaul
The core scanning engines have been upgraded to provide "Verification-First" reconnaissance.
*   **Attack Path Modeling Engine (APME)**: A production-grade, graph-based modeling system utilizing **Neo4j**. It discovers feasible attack routes (e.g., SQLi → DB Access → Pivot) based on a dynamic rules engine. **v3 Update**: Expanded rule set with 20+ sophisticated security patterns and automated "Goal Injection" for robust path discovery.
*   **Exploitation Readiness Layer (ERL)**: A safe, modular validation layer that converts potential findings into **"Verified" status** using containerized, non-destructive validation tools.
*   **Adaptive Stress & Resilience Engine (ASRE)**: Full-scale endpoint stress testing directly within the workflow, orchestrating `k6`, `wrk`, `hping3`, and `Locust` with real-time telemetry ingestion.
*   **Vulnerability Correlation Engine**: Unifies findings from **Nuclei, Semgrep, Trivy, Gitleaks, Acunetix, and Retire.js** into a prioritized threat landscape.
*   **Centralized Brute-Force Orchestration**: A multi-tiered authentication attack pipeline that supports **multi-service targeting (SSH, FTP, HTTP, SMB, RDP, Telnet)**. Centralizes targets from Nmap, Nuclei, and intelligent form extraction into a unified `AuthCandidate` queue, orchestrated via **Hydra** with full OpSec controls.
*   **Autonomous Plugin Management**: A powerful, modular system to extend reNgine with custom engines and dynamic UI components. Features **Atomic Installation** with background tool installation (`tools.yaml`), automated engine registration via fixtures, and persistent startup verification.

### 🕵️ Surgical Recon & API Discovery
The reconnaissance pipeline has been deepened to handle modern, API-centric web architectures.
*   **Deep Pursuit OSINT Engine**: A modernized, high-performance intelligence pipeline that replaces heavy Spiderfoot scans with surgical discovery. Featuring **holehe** for email pivots, **maigret** for cross-platform social profile mapping, and a custom **Internal Social Intelligence Engine** for advanced LinkedIn discovery.
*   **OSINT Intelligence Dashboard**: Aggregated view of emails, leaks, employees, dorks, and document metadata.

### 🥷 Stealth, OpSec & Infrastructure
Operational security is no longer an afterthought; it is baked into every execution.
*   **Enhanced Proxy Orchestration**: Per-tool rotating proxy support across all discovery modules to bypass rate-limiting and WAF blocks.
*   **Proper Scan Termination**: Resolved critical failures in scan termination by aligning frontend and backend to a unified `StopScan` API, ensuring all sub-tasks and child processes are killed immediately.
*   **Hydra & Medusa Integration**: High-performance authentication brute-forcing with automated service mapping and stealthy, batched execution via **Proxychains4**.
*   **WAF Bypass & OpSec Presets**: Advanced stealth configuration including User-Agent rotation, custom DNS resolvers, and WAF bypass headers.
*   **Automated Startup Sync**: A Redis-locked sequence ensures Attack Surface graphs and CISA KEV (Known Exploited Vulnerabilities) catalogs are synchronized immediately upon boot.

### 🎨 Premium Visual Experience
Aesthetic excellence is a core requirement of the v3 vision.
*   **Cyberpunk V3 "Neon" Dashboard**: A premium glassmorphic theme with a unified dark/neon palette optimized for complex data visualization.
    *   **Interactive Subdomain Management**: Fully wired tactical interface for on-demand **LLM Attack Surface Analysis**, targeted **Subscans**, and reconnaissance **TODO/Note management** directly from the inventory.
    *   **Scan Detail Header Reorganization**: Improved the aesthetic layout of the Scan Detail page by repositioning navigation breadcrumbs below action buttons and right-aligned the control group.
    *   📊 **Enhanced Telemetry**: Fixed HTTP status breakdown logic to capture and visualize all response codes across assets. Resolved critical Scan Summary API stability issues related to NULL data handling.
*   **Responsive Header & Mobile Menu**: Dynamic adaptation of header actions into a high-fidelity hamburger drawer for small viewports, preserving the glassmorphic aesthetic.
*   **Multi-Tier Theme System**: Toggle between **Hacker (Cyberpunk)**, **Hybrid (Modern Dark)**, and **Enterprise (Professional Slate)** interfaces instantly.
*   **Attack Surface Map v4.0**: Advanced node analytics scaling by degree centrality, blast radius computation, and AI-driven graph search.
*   **Tactical GeoMap Visualization**: Custom high-performance CSS-animated markers and tooltip interactions for global asset positioning.

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)


## Table of Contents

* [About r3ngine](#about-r3ngine)
* [Workflow](#workflow)
* [Features](#features)
* [Enterprise Support](#enterprise-support)
* [Quick Installation](#quick-installation)
* [Installation Video](#installation-video-tutorial)
* [Community-Curated Videos](#community-curated-videos)
* [Screenshots](#screenshots)
* [What's new in reNgine](https://github.com/whiterabb17/rengine/releases)
* [Contributing](#contributing)
* [r3ngine Support](#r3ngine-support)
* [Support and Sponsoring](#support-and-sponsoring)
* [Reporting Security Vulnerabilities](#reporting-security-vulnerabilities)
* [License](#license)

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## About reNgine

reNgine is not an ordinary reconnaissance suite; it's a game-changer! We've turbocharged the traditional workflow with groundbreaking features that ease your reconnaissance game. reNgine redefines the art of reconnaissance with highly configurable scan engines, recon data correlation, continuous monitoring, GPT powered Vulnerability Report, Project Management and role based access control etc.


🦾&nbsp;&nbsp; reNgine has advanced reconnaissance capabilities, harnessing a range of open-source tools to deliver a comprehensive web application reconnaissance experience. With its intuitive User Interface, it excels in subdomain discovery, pinpointing IP addresses and open ports, collecting endpoints, conducting directory and file fuzzing, capturing screenshots, and performing vulnerability scans. To summarize, it does end-to-end reconnaissance. With WHOIS identification and WAF detection, it offers deep insights into target domains. Additionally, reNgine also identifies misconfigured S3 buckets and find interesting subdomains and URLS, based on specific keywords to helps you identify your next target, making it a go-to tool for efficient reconnaissance.

🗃️&nbsp; &nbsp; Say goodbye to recon data chaos! reNgine seamlessly integrates with a database, providing you with unmatched data correlation and organization. Forgot the hassle of grepping through json, txt or csv files. Plus, our custom query language lets you filter reconnaissance data effortlessly using natural language like operators such as filtering all alive subdomains with `http_status=200` and also filter all subdomains that are alive and has admin in name `http_status=200&name=admin`

🔧&nbsp;&nbsp; reNgine offers unparalleled flexibility through its highly configurable scan engines, based on a YAML-based configuration. It offers the freedom to create and customize recon scan engines based on any kind of requirement, users can tailor them to their specific objectives and preferences, from thread management to timeout settings and rate-limit configurations, everything is customizable. Additionally, reNgine offers a range of pre-configured scan engines right out of the box, including Full Scan, Passive Scan, Screenshot Gathering, and the OSINT Scan Engine. These ready-to-use engines eliminate the need for extensive manual setup, aligning perfectly with reNgine's core mission of simplifying the reconnaissance process and enabling users to effortlessly access the right reconnaissance data with minimal effort.

💎&nbsp;&nbsp;Subscans: Subscan is a game-changing feature in reNgine, setting it apart as the only open-source tool of its kind to offer this capability. With Subscan, waiting for the entire pipeline to complete is a thing of the past. Now, users can swiftly respond to newfound discoveries during reconnaissance. Whether you've stumbled upon an intriguing subdomain and wish to conduct a focused port scan or want to delve deeper with a vulnerability assessment, reNgine has you covered.

📃&nbsp;&nbsp; PDF Reports: In addition to its robust reconnaissance capabilities, reNgine goes the extra mile by simplifying the report generation process, recognizing the crucial role that PDF reports play in the realm of end-to-end reconnaissance. Users can effortlessly generate and customize PDF reports to suit their exact needs. Whether it's a Full Scan Report, Vulnerability Report, or a concise reconnaissance report, reNgine provides the flexibility to choose the report type that best communicates your findings. Moreover, the level of customization is unparalleled, allowing users to select report colors, fine-tune executive summaries, and even add personalized touches like company names and footers. With GPT and LLM integration, your reports aren't just a report; with Assessment Overviews, Executive Briefs, Final Conclusions, remediation steps, and impacts, you get a 360-degree view of the vulnerabilities you've uncovered.

🔖&nbsp; &nbsp; Say Hello to Projects! reNgine 2.0 introduces a powerful addition that enables you to efficiently organize your web application reconnaissance efforts. With this feature, you can create distinct project spaces, each tailored to a specific purpose, such as personal bug bounty hunting, client engagements, or any other specialized recon task. Each projects will have separate dashboard and all the scan results will be separated from each project, while scan engines and configuration will be shared across all the projects.

⚙&nbsp; &nbsp; Roles and Permissions! In reNgine 2.0, we've taken your web application reconnaissance to a whole new level of control and security. Now, you can assign distinct roles to your team members—Sys Admin, Penetration Tester, and Auditor—each with precisely defined permissions to tailor their access and actions within the reNgine ecosystem.

  - 🔐 Sys Admin: Sys Admin is a superuser that has permission to modify system and scan related configurations, scan engines, create new users, add new tools etc. Superuser can initiate scans and subscans effortlessly.
  - 🔍 Penetration Tester: Penetration Tester will be allowed to modify and initiate scans and subscans, add or update targets, etc. A penetration tester will not be allowed to modify system configurations.
  - 📊 Auditor: Auditor can only view and download the report. An auditor can not change any system or scan related configurations nor can initiate any scans or subscans.

🧭&nbsp;&nbsp;**Continuous Monitoring**: r3ngine's automated monitoring engine ensures your targets are under constant scrutiny. Schedule scans at regular intervals and receive real-time alerts via Discord, Slack, and Telegram for new subdomains, vulnerabilities, or asset changes.

⚡&nbsp;&nbsp;**Adaptive Stress & Resilience Engine (ASRE)**: r3ngine v3 introduces the **Adaptive Stress & Resilience Engine (ASRE)**, a production-grade endpoint testing suite designed to evaluate the stability and resilience of target infrastructure. Unlike traditional scanners, ASRE orchestrates high-performance tools like `k6`, `wrk`, `hping3`, and `Locust` directly within your reconnaissance workflow. It provides real-time telemetry ingestion into the Attack Surface Graph (Neo4j), allowing you to visualize how endpoints behave under load and identify potential bottlenecks or denial-of-service vulnerabilities before they become critical failures.

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## Workflow

<img src="https://github.com/whiterabb17/rengine/assets/17223002/10c475b8-b4a8-440d-9126-77fe2038a386">

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## Features

### 🧠 Intelligence & AI Hub
*   **Centralized AI Management**: Unified interface for OpenAI, Anthropic, Gemini, and local Ollama models.
*   **Vulnerability Impact Intelligence**: AI-generated impact narratives, remediation strategies, and tactical reports.
*   **GPT Attack Surface Generator**: Automated generation of target profiles and high-value asset identification.
*   **PII Gate Security**: Native anonymization of sensitive reconnaissance data before LLM processing.
*   **Natural Language Querying**: Perform complex database lookups using intuitive, human-like operators.

### 🛠️ Advanced Scan Engines
*   **Attack Path Modeling Engine (APME)**: Graph-based visualization and discovery of multi-stage attack routes via Neo4j.
*   **Exploitation Readiness Layer (ERL)**: Modular, non-destructive vulnerability validation with containerized sandboxing and confidence scoring.
*   **Adaptive Stress & Resilience Engine (ASRE)**: Built-in endpoint stress testing using `k6`, `wrk`, `hping3`, and `Locust`.
*   **Vulnerability Correlation Engine**: Multi-tool unification mapping findings from Nuclei, Semgrep, Trivy, Gitleaks, Acunetix, and more.
*   **Autonomous Tooling & Plugin System**: Background tool management ensures all plugin dependencies (e.g., sqlmap, XSStrike) are installed and verified automatically at runtime. **v3-Hardening**: Integrated native **proxy rotation** and **OpSec compliance** (User-Agent randomization, custom headers) directly into the ERL adapter layer, ensuring stealthy validation of all discovered vulnerabilities.
*   **Continuous Monitoring**: Periodic discovery of new subdomains, endpoints, and data changes with automated diffing.

### 🕵️ Surgical Reconnaissance
*   **Advanced Web API Discovery**: Dedicated pipeline featuring Kiterunner, Arjun, ParamSpider, LinkFinder, and InQL.
*   **Deep OSINT 2.0**: A modular, internal intelligence pipeline featuring automated email pivoting, social profile mapping, and a **Custom Playwright-driven Social Intelligence Engine** that mimics human behavior to discover corporate personnel while maintaining high OpSec.
*   **ReconX Auxiliary Discovery**: Integrated third-party asset discovery and monitoring.
*   **Vulnerability Scanning**:
    *   **Nuclei**: Specialized templates and rate-limited execution.
    *   **Semgrep**: Automated static analysis for JS and GraphQL.
    *   **WPScan**: Automated WordPress reconnaissance and vulnerability identification.
    *   **Dalfox**: Advanced XSS discovery.
    *   **CRLFuzzer, S3Scanner, Gitleaks, Retire.js**.
*   **WHOIS, WAF Detection, and IP Geolocation**.

### 🥷 Stealth & Operational Security
*   **Enhanced Proxy Orchestration**: Automated fetching, validation, and per-tool rotation of high-quality proxies.
*   **Brute-Force Engines**: High-performance Hydra and Medusa integration with Proxychains4, **multi-service orchestration (SSH, FTP, HTTP, SMB, RDP, Telnet)**, automated service mapping (e.g., http → http-get), and configurable `max_retries` to ensure scan resilience.
*   **OpSec Presets**: User-Agent rotation, stealth timing, and WAF bypass headers.
*   **Metadata Stripping**: Automated removal of sensitive information from discovered assets.

### 🎨 Visual & Administrative
*   **Cyberpunk V3 UI**: Premium glassmorphic dashboard with Hacker, Hybrid, and Enterprise themes.
*   **Attack Surface Map v4.0**: Interactive, high-fidelity infrastructure visualization with node analytics.
*   **Interactive Subdomain Action Interface**: Real-time management for subdomains, subscans, and TODOs.
*   **Bounty Hub**: Centralized platform for managing HackerOne programs and assets.
*   **Automated Startup Sync**: Immediate synchronization of Attack Surface graphs and CISA KEV intelligence.
*   **Customizable Alerts**: Notifications via Slack, Discord, Telegram, and Lark.
*   **HackerOne Integration**: Direct reporting of vulnerabilities to bug bounty platforms.
*   **Screenshot Gallery**: Automated visual captures with advanced filtering and tagging.
*   **Export/Import**: Interoperable with other tools via JSON, CSV, and TXT.
-optimizer
* integrated tools: Chaos, TLSX, CTFR, Netlas, Katana, Medusa.

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

<p align="center">
  <h3>Enterprise Support</h3>
</p>

<p align="center">
  <a href="https://hailbytes.com/hardened-ubuntu-rengine/" target="_blank">
    <img src="https://hailbytes.com/wp-content/uploads/2020/04/HailBytes-Logo-2023-350-%C3%97-100-px.png" alt="HailBytes - Enterprise reNgine Support" height="60"/>
  </a>
</p>

<p align="center">
  Official enterprise-grade support, deployment, and maintenance services for reNgine are available through <a href="https://hailbytes.com">HailBytes</a>.
</p>

<p align="center">
You can also find the deep dive video on how to use and install reNgine from here <a href="https://www.youtube.com/watch?v=C6BFBxLmZIA">reNgine Deep Dive by HailBytes</a>
</p>

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## Quick Installation

### Quick Setup for Ubuntu/VPS

1. Clone the repository

    ```bash
    git clone https://github.com/whiterabb17/r3ngine && cd r3ngine
    ```

1. Configure the environment

    ```bash
    nano .env
    ```

    **Ensure you change the `POSTGRES_PASSWORD` for security.**

1. (Optional) For non-interactive install, set admin credentials in `.env`

    ```bash
    DJANGO_SUPERUSER_USERNAME=yourUsername
    DJANGO_SUPERUSER_EMAIL=YourMail@example.com
    DJANGO_SUPERUSER_PASSWORD=yourStrongPassword
    ```
    If you need to carry out a non-interactive installation, you can setup the login, email and password of the web interface admin directly from the .env file (instead of manually setting them from prompts during the installation process). This option can be interesting for automated installation (via ansible, vagrant, etc.).

    * `DJANGO_SUPERUSER_USERNAME`: web interface admin username (used to login to the web interface).

    * `DJANGO_SUPERUSER_EMAIL`: web interface admin email.

    * `DJANGO_SUPERUSER_PASSWORD`: web interface admin password (used to login to the web interface).

1. Adjust Celery worker scaling in `.env`

    ```bash
    MAX_CONCURRENCY=80
    MIN_CONCURRENCY=10
    ```

    `MAX_CONCURRENCY`: This parameter specifies the maximum number of reNgine's concurrent Celery worker processes that can be spawned. In this case, it's set to 80, meaning that the application can utilize up to 80 concurrent worker processes to execute tasks concurrently. This is useful for handling a high volume of scans or when you want to scale up processing power during periods of high demand. If you have more CPU cores, you will need to increase this for maximised performance.

    `MIN_CONCURRENCY`: On the other hand, MIN_CONCURRENCY specifies the minimum number of concurrent worker processes that should be maintained, even during periods of lower demand. In this example, it's set to 10, which means that even when there are fewer tasks to process, at least 10 worker processes will be kept running. This helps ensure that the application can respond promptly to incoming tasks without the overhead of repeatedly starting and stopping worker processes.

    These settings allow for dynamic scaling of Celery workers, ensuring that the application efficiently manages its workload by adjusting the number of concurrent workers based on the workload's size and complexity.

    Here is the ideal value for `MIN_CONCURRENCY` and `MAX_CONCURRENCY` depending on the number of RAM your machine has:

    * 4GB: `MAX_CONCURRENCY=10`
    * 8GB: `MAX_CONCURRENCY=30`
    * 16GB: `MAX_CONCURRENCY=50`

    This is just an ideal value which developers have tested and tried out and works! But feel free to play around with the values.
    Maximum number of scans is determined by various factors, your network bandwidth, RAM, number of CPUs available. etc

1. Run the installation script:

    ```bash
    sudo ./install.sh
    ```

    For non-interactive install: `sudo ./install.sh -n`

    *Note: If needed, run `chmod +x install.sh` to grant execution permissions.*

**reNgine can now be accessed from <https://127.0.0.1> or if you're on the VPS <https://your_vps_ip_address>**

**Unless you are on development branch, please do not access reNgine via any ports**

### Installation on Other Platforms

For Mac, Windows, or other systems, refer to our detailed installation guide [https://reNgine.wiki/install/detailed/](https://reNgine.wiki/install/detailed/)

### Installation Video Tutorial

If you encounter any issues during installation or prefer a visual guide, one of our community members has created an excellent installation video for Kali Linux installation. You can find it here: [https://www.youtube.com/watch?v=7OFfrU6VrWw](https://www.youtube.com/watch?v=7OFfrU6VrWw)

Please note: This is community-curated content and is not owned by reNgine. The installation process may change, so please refer to the official documentation for the most up-to-date instructions.

## Updating

1. To update reNgine, run:

    ```bash
    cd r3ngine &&  sudo ./update.sh
    ```

    If `update.sh` lacks execution permissions, use:

    ```bash
    sudo chmod +x update.sh
    ```

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## Community-Curated Videos

reNgine has a vibrant community that often creates helpful content about installation, features, and usage. Below is a collection of community-curated videos that you might find useful. Please note that these videos are not official reNgine content, and the information they contain may become outdated as reNgine evolves.

Always refer to the official documentation for the most up-to-date and accurate information. If you've created a video about reNgine and would like it featured here, please send a pull request updating this table.

| Video Title | Language | Publisher | Date | Link |
|-------------|----------|----------|------|------|
| reNgine Installation on Kali Linux | English | Secure the Cyber World | 2024-02-29 | [Watch](https://www.youtube.com/watch?v=7OFfrU6VrWw) |
| Resultados do ReNgine - Automação para Recon | Portuguese | Guia Anônima | 2023-04-18 | [Watch](https://www.youtube.com/watch?v=6aNvDy1FzIM) |
| reNgine Introduction | Moroccan Arabic | Th3 Hacker News Bdarija | 2021-07-27 | [Watch](https://www.youtube.com/watch?v=9FuRrcmWgWU) |
| Automated recon? ReNgine - Hacker Tools | English | Intigriti | 2021-08-24 | [Watch](https://www.youtube.com/watch?v=vP7tBopQSEc) |

We appreciate the community's contributions in creating these resources.

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)


## Screenshots

### Scan Results

![](.github/screenshots/scan_results.gif)

### General Usage

<img src="https://user-images.githubusercontent.com/17223002/164993781-b6012995-522b-480a-a8bf-911193d35894.gif">

### Initiating Subscan

<img src="https://user-images.githubusercontent.com/17223002/164993749-1ad343d6-8ce7-43d6-aee7-b3add0321da7.gif">

### Recon Data filtering

<img src="https://user-images.githubusercontent.com/17223002/164993687-b63f3de8-e033-4ac0-808e-a2aa377d3cf8.gif">

### Report Generation

<img src="https://user-images.githubusercontent.com/17223002/164993689-c796c6cd-eb61-43f4-800d-08aba9740088.gif">

### Toolbox

<img src="https://user-images.githubusercontent.com/17223002/164993751-d687e88a-eb79-440f-9dc0-0ad006901620.gif">

### Adding Custom tool in Tools Arsenal

<img src="https://user-images.githubusercontent.com/17223002/164993670-466f6459-9499-498b-a9bd-526476d735a7.gif">

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## Contributing

We welcome contributions of all sizes! The open-source community thrives on collaboration, and your input is invaluable. Whether you're fixing a typo, improving UI, or adding new features, every contribution matters.

How you can contribute:
  * Code improvements
  * Documentation updates
  * Bug reports and fixes
  * New feature suggestions and implementations
  * UI/UX enhancements

To get started:

  1. Check our [Contributing Guide](.github/CONTRIBUTING.md)
  2. Pick an [open issue](https://github.com/whiterabb17/rengine/issues) or propose a new one
  3. Fork the repository and create your branch
  4. Make your changes and submit a pull request

Remember, no contribution is too small. Your efforts help make reNgine better for everyone!

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## Submitting issues

When submitting issues, provide as much valuable information as possible to help developers resolve the problem quickly. Follow these steps to gather detailed debug information:

1. Enable Debug Mode:
   - Edit `web/entrypoint.sh` in the project root
   - Add `export DEBUG=1` at the top of the file:
     ```bash
     #!/bin/bash

     export DEBUG=1

     python3 manage.py migrate
     python3 manage.py runserver 0.0.0.0:8000

     exec "$@"
     ```
   - Restart the web container: `docker-compose restart web`

2. View Debug Output:
   - Run `make logs` to see the full stack trace
   - Check the browser's developer console for XHR requests with 500 errors

3. Example Debug Output:
    ```
    web_1          |   File "/usr/local/lib/python3.10/dist-packages/celery/app/task.py", line 411, in __call__
    web_1          |     return self.run(*args, **kwargs)
    web_1          | TypeError: run_command() got an unexpected keyword argument 'echo'
    ```

4. Submit Your Issue:
    - Include the full stack trace in your GitHub issue
    - Describe the steps to reproduce the problem
    - Mention any relevant system information

5. Disable Debug Mode:
    - Set `DEBUG=0` in `web/entrypoint.sh`
    - Restart the web container

By providing this detailed information, you significantly help developers identify and fix issues more efficiently.

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## First-time Open Source contributors

reNgine is an open-source project that welcomes contributors of all experience levels, including beginners. If you've never contributed to open source before, we encourage you to start here!

* We're proud to support your first Pull Request (PR)
* Check our [open issues](https://github.com/whiterabb17/rengine/issues) for starter-friendly tasks
* Don't hesitate to ask questions in our community channels

Your contribution, no matter how small, is valuable to us.

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## reNgine Support

Before seeking support:

* Please carefully read the README and documentation at [rengine.wiki](https://rengine.wiki).
* Most common questions and issues are addressed there.

If you still need assistance:

* Do not use GitHub issues for support requests.
* Join our [community-maintained Discord channel](https://discord.gg/azv6fzhNCE).

Please note:
* The Discord channel is maintained by the community.
* While we strive to help, there's no guarantee of support or response time.
* For confirmed bugs or feature requests, consider opening a GitHub issue.


![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## Support and Sponsoring

reNgine is a passion project developed in my free time, alongside my day job. Your support helps keep this project alive and growing. Here's how you can contribute:

* Add a [GitHub Star](https://github.com/whiterabb17/rengine) to the project.
* Share about reNgine on social media or in blog posts
* Nominate me for [GitHub Stars?](https://stars.github.com/nominate/)
* Use my [DigitalOcean referral link](https://m.do.co/c/e353502d19fc) to get $100 credit (I receive $25)

Your support, whether through donations or simply giving a star, tells me that reNgine is valuable to you. It motivates me to continue improving and adding features to make reNgine the go-to tool for reconnaissance.

Thank you for your support!

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## Reporting Security Vulnerabilities

We appreciate your efforts to responsibly disclose your findings and will make every effort to acknowledge your contributions.

To report a security vulnerability, please follow these steps:

1. **Do Not** disclose the vulnerability publicly on GitHub issues or any other public forum.

2. Go to the [Security tab](https://github.com/whiterabb17/rengine/security) of the reNgine repository.

3. Click on "Report a vulnerability" to open GitHub's private vulnerability reporting form.

4. Provide a detailed description of the vulnerability, including:
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes or mitigations (if you have them)

5. I will review your report and respond as quickly as possible, usually within 48-72 hours.

6. Please allow some time to investigate and address the vulnerability before disclosing it to others.

We are committed to working with security researchers to verify and address any potential vulnerabilities reported to us. After fixing the issue, we will publicly acknowledge your responsible disclosure, unless you prefer to remain anonymous.

Thank you for helping to keep reNgine and its users safe!

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

## License

Distributed under the GNU GPL v3 License. See [LICENSE](LICENSE) for more information.

![-----------------------------------------------------](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/aqua.png)

<p align="right"><i>Note: Parts of this README were written or refined using AI language models.</i></p>
