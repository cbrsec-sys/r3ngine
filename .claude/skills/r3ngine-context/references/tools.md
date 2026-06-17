# r3ngine — Integrated Security Tools

Tools compiled into the Docker image and invoked via Temporal activities (Python orchestrator or Go executor).

---

## Reconnaissance

### DNS / Subdomains

| Tool | Description | Link |
|------|-------------|------|
| **subfinder** | Passive subdomain discovery from OSINT sources | [projectdiscovery/subfinder](https://github.com/projectdiscovery/subfinder) |
| **dnsx** | Fast multi-purpose DNS toolkit | [projectdiscovery/dnsx](https://github.com/projectdiscovery/dnsx) |
| **amass** | In-depth DNS enumeration and OSINT | [owasp-amass/amass](https://github.com/owasp-amass/amass) |

### Port Scanning

| Tool | Description | Link |
|------|-------------|------|
| **naabu** | Fast port discovery (Go) | [projectdiscovery/naabu](https://github.com/projectdiscovery/naabu) |
| **nmap** | Port / service / OS / vuln scanning with NSE | [nmap/nmap](https://github.com/nmap/nmap) |

---

## HTTP & Crawling

| Tool | Description | Link |
|------|-------------|------|
| **httpx** | Fast HTTP prober — status, title, tech stack | [projectdiscovery/httpx](https://github.com/projectdiscovery/httpx) |
| **katana** | Next-generation crawling and spidering | [projectdiscovery/katana](https://github.com/projectdiscovery/katana) |
| **gau** | Offline URL fetcher (Wayback, AlienVault, CommonCrawl) | [lc/gau](https://github.com/lc/gau) |
| **hakrawler** | Fast web crawler for endpoint discovery | [hakluke/hakrawler](https://github.com/hakluke/hakrawler) |
| **gospider** | Fast web spider (Go) | [jaeles-project/gospider](https://github.com/jaeles-project/gospider) |

---

## Fuzzing

| Tool | Description | Link |
|------|-------------|------|
| **ffuf** | Fast web fuzzer for directories, parameters, vhosts | [ffuf/ffuf](https://github.com/ffuf/ffuf) |
| **dirsearch** | Web path discovery (Python) | [maurosoria/dirsearch](https://github.com/maurosoria/dirsearch) |

---

## Screenshot

| Tool | Description | Link |
|------|-------------|------|
| **EyeWitness** | Web screenshot tool | [FortyNorthSecurity/EyeWitness](https://github.com/FortyNorthSecurity/EyeWitness) |

---

## OSINT

| Tool | Description | Link |
|------|-------------|------|
| **holehe** | OSINT – check email registration across sites | [megadose/holehe](https://github.com/megadose/holehe) |
| **maigret** | Hunt for user accounts across hundreds of websites | [soxoj/maigret](https://github.com/soxoj/maigret) |
| **h8mail** | Email OSINT and breach hunting | [khast3x/h8mail](https://github.com/khast3x/h8mail) |

---

## Vulnerability Scanning

| Tool | Description | Link |
|------|-------------|------|
| **nuclei** | Fast configurable vuln scanner (YAML DSL) | [projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei) |
| **dalfox** | XSS scanning and parameter analysis | [hahwul/dalfox](https://github.com/hahwul/dalfox) |
| **wpscan** | WordPress security scanner | [wpscanteam/wpscan](https://github.com/wpscanteam/wpscan) |
| **nikto** | Web server scanner | [sullo/nikto](https://github.com/sullo/nikto) |

---

## Credential / Auth Testing

| Tool | Description | Link |
|------|-------------|------|
| **hydra** | Multi-service auth brute force | [vanhauser-thc/thc-hydra](https://github.com/vanhauser-thc/thc-hydra) |

---

## Stress Testing

| Tool | Description | Link |
|------|-------------|------|
| **k6** | Load and stress testing (JavaScript scripts) | [grafana/k6](https://github.com/grafana/k6) |
| **wrk** | HTTP benchmarking | [wg/wrk](https://github.com/wg/wrk) |
| **hping3** | TCP/IP packet assembler / analyser | [antirez/hping](https://github.com/antirez/hping) |

---

*Tool list reflects the v3.4.0 Docker image build. Check `web/Dockerfile` stage 2 (Go Tools Builder) for the authoritative installed set.*