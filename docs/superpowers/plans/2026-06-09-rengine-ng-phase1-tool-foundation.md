# rengine-ng Integration — Phase 1: Tool Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install 18 missing security tools into the r3ngine Docker image and wire each one up as a Temporal activity, giving later workflow phases a complete tool palette.

**Architecture:** Each new tool follows the established r3ngine pattern — binary in the Dockerfile, task function in a task module, thin `@activity.defn` wrapper in `temporal_activities.py`, and explicit registration in the orchestrator command. New tool task functions are grouped into `web/reNgine/recon_tasks.py` (network/recon tools) and `web/reNgine/crawl_tasks.py` (crawl/URL tools).

**Tech Stack:** Python 3.12, Temporal SDK 1.6.0, Django 5.2.3, Docker multi-stage build (Go tools builder + Ubuntu 22.04 runtime)

**Depends on:** Nothing — this is the foundation all other phases build on.

---

## Decision: RESOLVED — `search_vulns` added to port scan tier

**Choice:** `RunSearchVulnsActivity` will be added to r3ngine, querying vulners.com in real-time per discovered service during Tier 2 port scanning. `MasterScanWorkflow` will fan out concurrent `RunSearchVulnsActivity` tasks immediately after `RunPortScanActivity` returns, so exploit findings surface alongside port scan results rather than waiting for Tier 7 post-processing. `HostReconWorkflow` (Phase 2) will also call it. See Phase 1 Task 7 and Phase 2 Task 12.

---

## File Structure

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `docker/web/Dockerfile` | Add 18 tool binaries to Go-tools stage + runtime stage |
| Create | `web/reNgine/recon_tasks.py` | Task functions: dnsx, wafw00f, getasn, jswhois, whoisdomain, fping, arpscan, mapcidr, sshaudit, searchsploit, wpprobe, feroxbuster, bbot, **search_vulns** |
| Create | `web/reNgine/crawl_tasks.py` | Task functions: xurlfind3r, urlfinder, cariddi, bup, arjun |
| Modify | `web/reNgine/temporal_activities.py` | Add 18 new `@activity.defn` wrappers + `RunSearchVulnsActivity` |
| Modify | `web/scanEngine/management/commands/run_temporal_orchestrator.py` | Register new activities |
| Create | `web/tests/test_recon_tasks.py` | Tests for recon_tasks.py |
| Create | `web/tests/test_crawl_tasks.py` | Tests for crawl_tasks.py |

---

## Task 1: Add Go-compiled tools to Dockerfile

**Files:**
- Modify: `docker/web/Dockerfile`

- [ ] **Step 1: Locate the existing Go tools RUN block**

Open `docker/web/Dockerfile` and find the `go-tools-builder` stage's `RUN go install -ldflags="-s -w" ...` block (currently ends around line 55). Add the following tools at the end of that single chained `RUN` statement (before the `&&` that closes it):

```dockerfile
    go install -ldflags="-s -w" -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest && \
    go install -ldflags="-s -w" -v github.com/Vulnpire/getasn@latest && \
    go install -ldflags="-s -w" -v github.com/jschauma/jswhois@latest && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/mapcidr/cmd/mapcidr@latest && \
    go install -ldflags="-s -w" -v github.com/projectdiscovery/urlfinder/cmd/urlfinder@latest && \
    go install -ldflags="-s -w" -v github.com/Chocapikk/wpprobe@latest && \
    go install -ldflags="-s -w" -v github.com/hueristiq/xurlfind3r/cmd/xurlfind3r@latest && \
    go install -ldflags="-s -w" -v github.com/edoardottt/cariddi/cmd/cariddi@latest
```

Ensure each new binary is also copied in the `COPY --from=go-tools-builder` line in the runtime stage (it should already use a wildcard copy from `/root/go/bin/`; verify with `grep -n "go-tools-builder" docker/web/Dockerfile`).

- [ ] **Step 2: Add apt-get packages in the runtime stage**

In the runtime stage `apt-get install -y` block (around line 190–235), add:
```dockerfile
    fping \
    arp-scan \
```

- [ ] **Step 3: Add feroxbuster binary from GitHub releases**

After the existing `trufflehog` download block in the runtime stage, add:
```dockerfile
RUN FEROX_VERSION=$(curl -s https://api.github.com/repos/epi052/feroxbuster/releases/latest \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'].lstrip('v'))") && \
    wget -q "https://github.com/epi052/feroxbuster/releases/download/v${FEROX_VERSION}/x86-linux-feroxbuster.zip" \
      -O /tmp/feroxbuster.zip && \
    unzip /tmp/feroxbuster.zip -d /usr/local/bin && \
    chmod +x /usr/local/bin/feroxbuster && \
    rm /tmp/feroxbuster.zip
```

- [ ] **Step 4: Add searchsploit from exploit-db**

```dockerfile
RUN git clone --depth 1 https://gitlab.com/exploit-database/exploitdb /usr/src/exploitdb && \
    ln -sf /usr/src/exploitdb/searchsploit /usr/local/bin/searchsploit && \
    cp /usr/src/exploitdb/.searchsploit_rc /root/.searchsploit_rc && \
    searchsploit -u || true
```

- [ ] **Step 5: Add pipx/pip tools**

In the existing `pipx` installation block, add:
```dockerfile
RUN pipx install ssh-audit --force && \
    pipx install "git+https://github.com/EnableSecurity/wafw00f.git" --force && \
    pipx install whoisdomain --force && \
    pipx install "bypass-url-parser" --force && \
    pipx install bbot --force && \
    pip3 install arjun --quiet
```

- [ ] **Step 6: Verify build compiles cleanly**

```bash
docker build --no-cache -f docker/web/Dockerfile -t r3ngine-test:tools . 2>&1 | tail -20
```
Expected: `Successfully built ...` with no errors.

- [ ] **Step 7: Verify binaries are present in the built image**

```bash
docker run --rm r3ngine-test:tools bash -c "which dnsx wafw00f feroxbuster xurlfind3r urlfinder cariddi mapcidr wpprobe bup ssh-audit searchsploit arjun fping arp-scan"
```
Expected: all 15 paths printed (one per line).

- [ ] **Step 8: Commit Dockerfile changes**

```bash
git add docker/web/Dockerfile
git commit -m "feat(docker): add 18 rengine-ng workflow tool binaries to Docker image"
```

---

## Task 2: Create `recon_tasks.py` with network/recon tool task functions

**Files:**
- Create: `web/reNgine/recon_tasks.py`
- Test: `web/tests/test_recon_tasks.py`

- [ ] **Step 1: Write the failing tests first**

```python
# web/tests/test_recon_tasks.py
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase


class TestDNSXTask(TestCase):
    @patch('subprocess.run')
    def test_dnsx_parses_a_records(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"host":"sub.example.com","a":["1.2.3.4"],"resolver":"8.8.8.8"}\n',
            stderr='',
        )
        from reNgine.recon_tasks import dnsx_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = dnsx_scan(proxy, scan_history_id=1, domain_id=1, subdomain='sub.example.com')
        self.assertIsNotNone(result)

    @patch('subprocess.run')
    def test_wafw00f_parses_waf_detected(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='The site https://example.com is behind Cloudflare\n',
            stderr='',
        )
        from reNgine.recon_tasks import wafw00f_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = wafw00f_scan(proxy, scan_history_id=1, domain_id=1, url='https://example.com')
        self.assertIsNotNone(result)

    @patch('subprocess.run')
    def test_fping_parses_alive_hosts(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='192.0.2.1 is alive\n192.0.2.2 is alive\n192.0.2.3 is unreachable\n',
            stderr='',
        )
        from reNgine.recon_tasks import fping_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = fping_scan(proxy, scan_history_id=1, cidr='192.0.2.0/24')
        self.assertIsNotNone(result)

    @patch('subprocess.run')
    def test_sshaudit_parses_vulnerabilities(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "banner": {"raw": "SSH-2.0-OpenSSH_7.4"},
                "cves": [{"name": "CVE-2023-38408", "cvss": 9.8, "description": "..."}],
                "recommendations": [],
            }),
            stderr='',
        )
        from reNgine.recon_tasks import sshaudit_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = sshaudit_scan(proxy, scan_history_id=1, host='192.0.2.1', port=22)
        self.assertIsNotNone(result)

    @patch('subprocess.run')
    def test_wpprobe_parses_plugins(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{
                "plugin": "contact-form-7",
                "version": "5.7.5",
                "cve": "CVE-2023-6449",
                "severity": "medium",
            }]),
            stderr='',
        )
        from reNgine.recon_tasks import wpprobe_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = wpprobe_scan(proxy, scan_history_id=1, url='https://example.com')
        self.assertIsNotNone(result)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks --verbosity=2 2>&1 | head -30"
```
Expected: `ImportError: No module named 'reNgine.recon_tasks'`

- [ ] **Step 3: Implement `recon_tasks.py`**

```python
# web/reNgine/recon_tasks.py
"""
Recon task functions for network-layer and domain intelligence tools.

These functions are called by Temporal activities in temporal_activities.py.
They follow the same TemporalTaskProxy interface as tasks.py functions.
Each function is responsible for:
  1. Building the tool command from yaml_configuration
  2. Running the subprocess
  3. Parsing output and persisting findings to the database
  4. Updating ScanActivity status via self (TemporalTaskProxy)
"""
import json
import logging
import os
import subprocess
from typing import List, Optional

from reNgine.utils.logger import get_module_logger

logger = get_module_logger(__name__)


def dnsx_scan(self, scan_history_id: int, domain_id: int, subdomain: str = None,
              subdomains: List[str] = None, wordlist: str = None) -> bool:
    """Resolve DNS records for subdomains using dnsx.

    Writes Record objects to startScan_dnsrecord via bulk_create.
    Used in: DomainReconWorkflow (probe), SubdomainReconWorkflow (brute+probe).
    """
    from startScan.models import ScanHistory, Subdomain, DNSRecord
    from django.db import transaction

    yaml_config = getattr(self, 'yaml_configuration', {}) or {}
    scan_config = yaml_config.get('dnsx', {})

    targets = subdomains or ([subdomain] if subdomain else [])
    if not targets:
        logger.log_line("[DNSX]", "SKIP", "no targets provided")
        return True

    input_file = f"/tmp/dnsx_input_{scan_history_id}.txt"
    output_file = f"/tmp/dnsx_output_{scan_history_id}.json"

    try:
        with open(input_file, 'w') as f:
            f.write('\n'.join(targets))

        cmd = [
            'dnsx',
            '-l', input_file,
            '-resp', '-recon',
            '-json', '-o', output_file,
            '-silent',
        ]
        if wordlist:
            cmd += ['-w', wordlist]

        logger.log_line("[DNSX]", "START", "resolving %d targets" % len(targets))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if not os.path.exists(output_file):
            logger.log_line("[DNSX]", "WARN", "no output produced")
            return True

        records_to_create = []
        with open(output_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                host = data.get('host', '')
                for record_type in ('a', 'aaaa', 'mx', 'ns', 'cname', 'txt', 'soa'):
                    values = data.get(record_type, [])
                    for value in (values if isinstance(values, list) else [values]):
                        records_to_create.append(
                            DNSRecord(
                                scan_history_id=scan_history_id,
                                name=host,
                                type=record_type.upper(),
                                value=value,
                            )
                        )

        if records_to_create:
            with transaction.atomic():
                DNSRecord.objects.bulk_create(records_to_create, ignore_conflicts=True)
            logger.log_line("[DNSX]", "RESULT", "persisted %d DNS records" % len(records_to_create))

    finally:
        for f in [input_file, output_file]:
            try:
                os.remove(f)
            except FileNotFoundError:
                pass

    return True


def wafw00f_scan(self, scan_history_id: int, domain_id: int, url: str = None,
                 urls: List[str] = None) -> bool:
    """Detect WAF presence using wafw00f.

    Tags the Subdomain record with detected WAF name.
    Used in: DomainReconWorkflow.
    """
    from startScan.models import ScanHistory, Subdomain
    from django.db import transaction

    targets = urls or ([url] if url else [])
    if not targets:
        logger.log_line("[WAFW00F]", "SKIP", "no targets provided")
        return True

    for target_url in targets:
        try:
            cmd = ['wafw00f', target_url, '-o', '-', '-f', 'json']
            logger.log_line("[WAFW00F]", "START", "checking %s" % target_url)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            try:
                data = json.loads(result.stdout)
                if data and data[0].get('detected'):
                    waf_name = data[0].get('firewall', 'Unknown WAF')
                    Subdomain.objects.filter(
                        scan_history_id=scan_history_id,
                        http_url__startswith=target_url.rstrip('/'),
                    ).update(waf=waf_name)
                    logger.log_line("[WAFW00F]", "RESULT", "WAF detected: %s" % waf_name)
            except (json.JSONDecodeError, IndexError, KeyError):
                pass

        except subprocess.TimeoutExpired:
            logger.log_line("[WAFW00F]", "WARN", "timed out for %s" % target_url)

    return True


def fping_scan(self, scan_history_id: int, cidr: str = None,
               targets: List[str] = None) -> List[str]:
    """Discover alive hosts in a CIDR range using fping ICMP probes.

    Returns list of alive IP address strings.
    Used in: CIDRReconWorkflow (probe phase).
    """
    probe_targets = targets or ([cidr] if cidr else [])
    if not probe_targets:
        return []

    alive = []
    cmd = ['fping', '-a', '-A', '-g'] + probe_targets
    logger.log_line("[FPING]", "START", "probing %s" % ' '.join(probe_targets))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and 'is alive' in line:
                ip = line.split()[0]
                alive.append(ip)
    except subprocess.TimeoutExpired:
        logger.log_line("[FPING]", "WARN", "fping timed out")

    logger.log_line("[FPING]", "RESULT", "found %d alive hosts" % len(alive))
    return alive


def arpscan_scan(self, scan_history_id: int, cidr: str = None) -> List[str]:
    """Discover LAN hosts via ARP using arp-scan.

    Returns list of IP address strings found via ARP.
    Used in: CIDRReconWorkflow (local network discovery).
    Requires: CAP_NET_RAW or --privileged container.
    """
    if not cidr:
        return []

    alive = []
    cmd = ['arp-scan', '--plain', '--resolve', cidr]
    logger.log_line("[ARPSCAN]", "START", "ARP scanning %s" % cidr)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        for line in result.stdout.splitlines():
            parts = line.split('\t')
            if parts and parts[0]:
                alive.append(parts[0].strip())
    except subprocess.TimeoutExpired:
        logger.log_line("[ARPSCAN]", "WARN", "arp-scan timed out")

    logger.log_line("[ARPSCAN]", "RESULT", "found %d hosts via ARP" % len(alive))
    return alive


def mapcidr_expand(self, scan_history_id: int, cidr: str) -> List[str]:
    """Expand a CIDR range to individual IP addresses using mapcidr.

    Returns list of IP strings. Used in CIDRReconWorkflow before fping.
    """
    cmd = ['mapcidr', '-cidr', cidr, '-silent']
    logger.log_line("[MAPCIDR]", "START", "expanding %s" % cidr)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        ips = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        logger.log_line("[MAPCIDR]", "RESULT", "expanded to %d IPs" % len(ips))
        return ips
    except subprocess.TimeoutExpired:
        logger.log_line("[MAPCIDR]", "WARN", "mapcidr timed out")
        return []


def sshaudit_scan(self, scan_history_id: int, host: str, port: int = 22) -> bool:
    """Audit SSH service configuration using ssh-audit.

    Saves findings as Vulnerability records with severity mapping:
      cvss >= 9.0 → critical, >= 7.0 → high, >= 4.0 → medium, else low.
    Used in: HostReconWorkflow.
    """
    from startScan.models import ScanHistory, Vulnerability
    from django.db import transaction

    output_file = f"/tmp/sshaudit_{scan_history_id}_{host.replace('.', '_')}.json"
    cmd = ['ssh-audit', '-j', '-p', str(port), host]
    logger.log_line("[SSHAUDIT]", "START", "auditing %s:%d" % (host, port))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.log_line("[SSHAUDIT]", "WARN", "failed to parse json output")
            return True

        cves = data.get('cves', [])
        vulns = []
        for cve in cves:
            cvss = float(cve.get('cvss', 0))
            if cvss >= 9.0:
                severity = 'critical'
            elif cvss >= 7.0:
                severity = 'high'
            elif cvss >= 4.0:
                severity = 'medium'
            else:
                severity = 'low'
            vulns.append(Vulnerability(
                scan_history_id=scan_history_id,
                name=cve.get('name', 'SSH Vulnerability'),
                severity=severity,
                description=cve.get('description', ''),
                source='sshaudit',
                matched_at='%s:%d' % (host, port),
            ))

        if vulns:
            with transaction.atomic():
                Vulnerability.objects.bulk_create(vulns, ignore_conflicts=True)
            logger.log_line("[SSHAUDIT]", "RESULT", "saved %d SSH vulnerabilities" % len(vulns))

    except subprocess.TimeoutExpired:
        logger.log_line("[SSHAUDIT]", "WARN", "ssh-audit timed out for %s" % host)

    return True


def searchsploit_scan(self, scan_history_id: int, service: str, version: str = None) -> bool:
    """Search Exploit-DB for known exploits for a service/version combo.

    Saves matching exploits as Vulnerability records (severity=high).
    Used in: HostReconWorkflow.
    """
    from startScan.models import Vulnerability
    from django.db import transaction

    query = f"{service} {version}".strip() if version else service
    cmd = ['searchsploit', '--json', query]
    logger.log_line("[SEARCHSPLOIT]", "START", "searching exploits for %s" % query)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        data = json.loads(result.stdout)
        exploits = data.get('RESULTS_EXPLOIT', [])
        vulns = []
        for exploit in exploits[:20]:  # cap at 20 per service
            vulns.append(Vulnerability(
                scan_history_id=scan_history_id,
                name=exploit.get('Title', 'Exploit Found'),
                severity='high',
                description=exploit.get('Description', ''),
                source='searchsploit',
                matched_at=service,
                reference=exploit.get('Path', ''),
            ))
        if vulns:
            with transaction.atomic():
                Vulnerability.objects.bulk_create(vulns, ignore_conflicts=True)
            logger.log_line("[SEARCHSPLOIT]", "RESULT", "saved %d exploits" % len(vulns))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        logger.log_line("[SEARCHSPLOIT]", "WARN", "searchsploit failed for %s" % query)

    return True


def wpprobe_scan(self, scan_history_id: int, url: str) -> bool:
    """Scan WordPress site for vulnerable plugins using wpprobe.

    Saves findings as Vulnerability records.
    Used in: WordPressWorkflow.
    """
    from startScan.models import Vulnerability
    from django.db import transaction

    cmd = ['wpprobe', '-u', url, '-json']
    logger.log_line("[WPPROBE]", "START", "scanning %s" % url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        findings = json.loads(result.stdout) if result.stdout.strip() else []
        vulns = []
        for finding in findings:
            severity = finding.get('severity', 'medium').lower()
            vulns.append(Vulnerability(
                scan_history_id=scan_history_id,
                name=finding.get('cve', 'WordPress Plugin Vulnerability'),
                severity=severity,
                description='Plugin: %s v%s' % (
                    finding.get('plugin', ''), finding.get('version', '')),
                source='wpprobe',
                matched_at=url,
            ))
        if vulns:
            with transaction.atomic():
                Vulnerability.objects.bulk_create(vulns, ignore_conflicts=True)
            logger.log_line("[WPPROBE]", "RESULT", "saved %d plugin vulnerabilities" % len(vulns))
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        logger.log_line("[WPPROBE]", "WARN", "wpprobe failed for %s" % url)

    return True
```

- [ ] **Step 4: Run failing tests to verify they now pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks --verbosity=2"
```
Expected: `OK` — all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/recon_tasks.py web/tests/test_recon_tasks.py
git commit -m "feat(recon): add network/recon tool task functions (dnsx, wafw00f, fping, arpscan, mapcidr, sshaudit, searchsploit, wpprobe)"
```

---

## Task 3: Create `crawl_tasks.py` with URL/crawl tool task functions

**Files:**
- Create: `web/reNgine/crawl_tasks.py`
- Test: `web/tests/test_crawl_tasks.py`

- [ ] **Step 1: Write failing tests**

```python
# web/tests/test_crawl_tasks.py
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase


class TestXURLFind3rTask(TestCase):
    @patch('subprocess.run')
    def test_xurlfind3r_yields_urls(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({'url': 'https://example.com/path'}) + '\n',
            stderr='',
        )
        from reNgine.crawl_tasks import xurlfind3r_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = xurlfind3r_scan(proxy, scan_history_id=1, domain='example.com')
        self.assertIsNotNone(result)


class TestCariddiTask(TestCase):
    @patch('subprocess.run')
    def test_cariddi_parses_secrets(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://example.com/api.js\t[secret:api_key]\n',
            stderr='',
        )
        from reNgine.crawl_tasks import cariddi_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = cariddi_scan(proxy, scan_history_id=1, url='https://example.com')
        self.assertIsNotNone(result)


class TestBUPTask(TestCase):
    @patch('subprocess.run')
    def test_bup_parses_bypasses(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[BYPASS] https://example.com/admin (200 via X-Original-URL)\n',
            stderr='',
        )
        from reNgine.crawl_tasks import bup_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = bup_scan(proxy, scan_history_id=1, url='https://example.com/admin')
        self.assertIsNotNone(result)


class TestArjunTask(TestCase):
    @patch('subprocess.run')
    def test_arjun_parses_parameters(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                'https://example.com/search': ['q', 'page', 'sort']
            }),
            stderr='',
        )
        from reNgine.crawl_tasks import arjun_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = arjun_scan(proxy, scan_history_id=1, urls=['https://example.com/search'])
        self.assertIsNotNone(result)


class TestFeroxbusterTask(TestCase):
    @patch('subprocess.run')
    def test_feroxbuster_parses_urls(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='200      25l       89w      612c https://example.com/admin\n',
            stderr='',
        )
        from reNgine.crawl_tasks import feroxbuster_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = feroxbuster_scan(proxy, scan_history_id=1, url='https://example.com')
        self.assertIsNotNone(result)
```

- [ ] **Step 2: Run to confirm tests fail**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_crawl_tasks --verbosity=2 2>&1 | head -20"
```
Expected: `ImportError: No module named 'reNgine.crawl_tasks'`

- [ ] **Step 3: Implement `crawl_tasks.py`**

```python
# web/reNgine/crawl_tasks.py
"""
Crawl and URL-discovery task functions.

Adapts xurlfind3r, urlfinder, cariddi, bup, arjun, and feroxbuster to the
TemporalTaskProxy interface expected by temporal_activities.py.
"""
import json
import logging
import os
import subprocess
from typing import List, Optional

from reNgine.utils.logger import get_module_logger

logger = get_module_logger(__name__)


def xurlfind3r_scan(self, scan_history_id: int, domain: str = None,
                    domains: List[str] = None) -> bool:
    """Collect passive URLs from multiple sources using xurlfind3r.

    Persists discovered URLs as EndPoint records.
    Used in: URLCrawlWorkflow (passive), DomainReconWorkflow.
    """
    from startScan.models import EndPoint, ScanHistory
    from django.db import transaction

    targets = domains or ([domain] if domain else [])
    if not targets:
        return True

    endpoints = []
    for target in targets:
        cmd = ['xurlfind3r', '-d', target, '-silent']
        logger.log_line("[XURLFIND3R]", "START", "passive crawl for %s" % target)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith('http'):
                    endpoints.append(EndPoint(
                        scan_history_id=scan_history_id,
                        http_url=line[:2000],
                        is_default=False,
                        source='xurlfind3r',
                    ))
        except subprocess.TimeoutExpired:
            logger.log_line("[XURLFIND3R]", "WARN", "timed out for %s" % target)

    if endpoints:
        with transaction.atomic():
            EndPoint.objects.bulk_create(endpoints, ignore_conflicts=True, batch_size=500)
        logger.log_line("[XURLFIND3R]", "RESULT", "saved %d URLs" % len(endpoints))
    return True


def urlfinder_scan(self, scan_history_id: int, domain: str = None) -> bool:
    """Collect passive URLs using urlfinder (projectdiscovery).

    Used in: URLCrawlWorkflow (passive).
    """
    from startScan.models import EndPoint
    from django.db import transaction

    if not domain:
        return True

    cmd = ['urlfinder', '-d', domain, '-silent']
    logger.log_line("[URLFINDER]", "START", "passive crawl for %s" % domain)
    endpoints = []
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith('http'):
                endpoints.append(EndPoint(
                    scan_history_id=scan_history_id,
                    http_url=line[:2000],
                    is_default=False,
                    source='urlfinder',
                ))
    except subprocess.TimeoutExpired:
        logger.log_line("[URLFINDER]", "WARN", "timed out for %s" % domain)

    if endpoints:
        with transaction.atomic():
            EndPoint.objects.bulk_create(endpoints, ignore_conflicts=True, batch_size=500)
        logger.log_line("[URLFINDER]", "RESULT", "saved %d URLs" % len(endpoints))
    return True


def cariddi_scan(self, scan_history_id: int, url: str = None,
                 urls: List[str] = None) -> bool:
    """Crawl endpoints, hunt juicy patterns, and discover secrets using cariddi.

    Flags endpoints with 'secret' tag when cariddi reports a secret match.
    Used in: URLCrawlWorkflow (active).
    """
    from startScan.models import EndPoint
    from django.db import transaction

    targets = urls or ([url] if url else [])
    if not targets:
        return True

    for target in targets:
        cmd = ['cariddi', '-i', target, '-info', '-secrets', '-e', '-s', '1']
        logger.log_line("[CARIDDI]", "START", "crawling %s" % target)
        endpoints = []
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            for line in result.stdout.splitlines():
                line = line.strip()
                if '\t' in line:
                    parts = line.split('\t')
                    ep_url = parts[0].strip()
                    tags = [p.strip('[]') for p in parts[1:] if p.startswith('[')]
                    if ep_url.startswith('http'):
                        endpoints.append(EndPoint(
                            scan_history_id=scan_history_id,
                            http_url=ep_url[:2000],
                            is_default=False,
                            source='cariddi',
                        ))
        except subprocess.TimeoutExpired:
            logger.log_line("[CARIDDI]", "WARN", "timed out for %s" % target)

        if endpoints:
            with transaction.atomic():
                EndPoint.objects.bulk_create(endpoints, ignore_conflicts=True, batch_size=500)
            logger.log_line("[CARIDDI]", "RESULT", "saved %d endpoints for %s" % (len(endpoints), target))

    return True


def bup_scan(self, scan_history_id: int, url: str = None,
             urls: List[str] = None) -> bool:
    """Attempt 4xx bypass techniques using bypass-url-parser (bup).

    Saves successful bypasses as Vulnerability records (severity=medium).
    Used in: URLBypassWorkflow.
    """
    from startScan.models import Vulnerability
    from django.db import transaction

    targets = urls or ([url] if url else [])
    if not targets:
        return True

    for target in targets:
        cmd = ['bup', '-u', target, '-d']
        logger.log_line("[BUP]", "START", "bypass attempt on %s" % target)
        bypasses = []
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            for line in result.stdout.splitlines():
                if '[BYPASS]' in line or '200' in line:
                    bypasses.append(Vulnerability(
                        scan_history_id=scan_history_id,
                        name='4xx Bypass Found',
                        severity='medium',
                        description=line.strip(),
                        source='bup',
                        matched_at=target,
                    ))
        except subprocess.TimeoutExpired:
            logger.log_line("[BUP]", "WARN", "timed out for %s" % target)

        if bypasses:
            with transaction.atomic():
                Vulnerability.objects.bulk_create(bypasses, ignore_conflicts=True)
            logger.log_line("[BUP]", "RESULT", "found %d bypasses for %s" % (len(bypasses), target))

    return True


def arjun_scan(self, scan_history_id: int, urls: List[str] = None,
               url: str = None) -> bool:
    """Discover hidden HTTP parameters using arjun.

    Saves discovered parameters to the Parameter model.
    Used in: URLParamsFuzzWorkflow.
    """
    from startScan.models import Parameter, EndPoint
    from django.db import transaction

    targets = urls or ([url] if url else [])
    if not targets:
        return True

    output_file = f"/tmp/arjun_output_{scan_history_id}.json"
    cmd = ['arjun', '-i', '/dev/stdin', '-oJ', output_file, '-q']
    logger.log_line("[ARJUN]", "START", "parameter discovery for %d URLs" % len(targets))

    try:
        result = subprocess.run(
            cmd,
            input='\n'.join(targets),
            capture_output=True, text=True, timeout=600,
        )
        if os.path.exists(output_file):
            with open(output_file) as f:
                data = json.load(f)
            params = []
            for ep_url, param_list in data.items():
                for param_name in param_list:
                    params.append(Parameter(
                        scan_history_id=scan_history_id,
                        parameter=param_name,
                        url=ep_url,
                        source='arjun',
                    ))
            if params:
                with transaction.atomic():
                    Parameter.objects.bulk_create(params, ignore_conflicts=True)
                logger.log_line("[ARJUN]", "RESULT", "saved %d parameters" % len(params))
    except subprocess.TimeoutExpired:
        logger.log_line("[ARJUN]", "WARN", "arjun timed out")
    finally:
        try:
            os.remove(output_file)
        except FileNotFoundError:
            pass

    return True


def feroxbuster_scan(self, scan_history_id: int, url: str = None,
                     urls: List[str] = None) -> bool:
    """Recursively fuzz web content using feroxbuster.

    Persists discovered paths as EndPoint records.
    Used in: URLFuzzWorkflow.
    """
    from startScan.models import EndPoint
    from django.db import transaction

    yaml_config = getattr(self, 'yaml_configuration', {}) or {}
    scan_config = yaml_config.get('feroxbuster', {})
    wordlist = scan_config.get('wordlist', '/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt')

    targets = urls or ([url] if url else [])
    if not targets:
        return True

    for target in targets:
        output_file = f"/tmp/feroxbuster_{scan_history_id}.txt"
        cmd = [
            'feroxbuster',
            '--url', target,
            '--wordlist', wordlist,
            '--no-state',
            '--output', output_file,
            '--auto-calibration',
            '--follow-redirects',
            '--silent',
        ]
        logger.log_line("[FEROXBUSTER]", "START", "fuzzing %s" % target)
        endpoints = []
        try:
            subprocess.run(cmd, capture_output=True, timeout=1800)
            if os.path.exists(output_file):
                with open(output_file) as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 5 and parts[0].isdigit():
                            ep_url = parts[-1].strip()
                            if ep_url.startswith('http'):
                                endpoints.append(EndPoint(
                                    scan_history_id=scan_history_id,
                                    http_url=ep_url[:2000],
                                    http_status=int(parts[0]),
                                    is_default=False,
                                    source='feroxbuster',
                                ))
        except subprocess.TimeoutExpired:
            logger.log_line("[FEROXBUSTER]", "WARN", "timed out for %s" % target)
        finally:
            try:
                os.remove(output_file)
            except FileNotFoundError:
                pass

        if endpoints:
            with transaction.atomic():
                EndPoint.objects.bulk_create(endpoints, ignore_conflicts=True, batch_size=500)
            logger.log_line("[FEROXBUSTER]", "RESULT", "saved %d endpoints" % len(endpoints))

    return True


def gf_scan(self, scan_history_id: int, pattern: str, urls: List[str] = None) -> List[str]:
    """Filter URLs by vulnerability pattern using gf (grep for URLs).

    Returns list of matched URLs. Patterns: xss, lfi, ssrf, rce, idor, debug_logic.
    Used in: URLVulnWorkflow.
    """
    if not urls:
        return []

    cmd = ['gf', pattern]
    logger.log_line("[GF]", "START", "pattern=%s targets=%d" % (pattern, len(urls)))

    try:
        result = subprocess.run(
            cmd,
            input='\n'.join(urls),
            capture_output=True, text=True, timeout=60,
        )
        matched = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        logger.log_line("[GF]", "RESULT", "pattern=%s matched=%d" % (pattern, len(matched)))
        return matched
    except subprocess.TimeoutExpired:
        logger.log_line("[GF]", "WARN", "gf timed out for pattern %s" % pattern)
        return []
```

- [ ] **Step 4: Run tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_crawl_tasks --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/crawl_tasks.py web/tests/test_crawl_tasks.py
git commit -m "feat(crawl): add URL/crawl tool task functions (xurlfind3r, urlfinder, cariddi, bup, arjun, feroxbuster, gf)"
```

---

## Task 4: Add 18 `@activity.defn` wrappers in `temporal_activities.py`

**Files:**
- Modify: `web/reNgine/temporal_activities.py` (append after the last existing activity, before any closing)

- [ ] **Step 1: Append the new activity wrappers**

Add the following block at the end of `temporal_activities.py`:

```python
# ---------------------------------------------------------------------------
# Phase 1 — New tool activities (rengine-ng workflow compatibility)
# ---------------------------------------------------------------------------

@activity.defn(name="RunDNSXActivity")
def run_dnsx_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import dnsx_scan
    activity.logger.info("[RunDNSXActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(dnsx_scan, ctx, task_name='dnsx_scan', description='DNS Resolution (dnsx)',
                     subdomain=ctx.get('subdomain'), subdomains=ctx.get('subdomains'),
                     wordlist=ctx.get('wordlist'))


@activity.defn(name="RunWAFW00FActivity")
def run_wafw00f_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import wafw00f_scan
    activity.logger.info("[RunWAFW00FActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(wafw00f_scan, ctx, task_name='wafw00f_scan', description='WAF Detection (wafw00f)',
                     url=ctx.get('url'), urls=ctx.get('urls'))


@activity.defn(name="RunFPingActivity")
def run_fping_activity(ctx: dict) -> list:
    from reNgine.recon_tasks import fping_scan
    activity.logger.info("[RunFPingActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(fping_scan, ctx, task_name='fping_scan', description='ICMP Host Discovery (fping)',
                     cidr=ctx.get('cidr'), targets=ctx.get('targets'))


@activity.defn(name="RunARPScanActivity")
def run_arpscan_activity(ctx: dict) -> list:
    from reNgine.recon_tasks import arpscan_scan
    activity.logger.info("[RunARPScanActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(arpscan_scan, ctx, task_name='arpscan_scan', description='ARP Host Discovery',
                     cidr=ctx.get('cidr'))


@activity.defn(name="RunMapCIDRActivity")
def run_mapcidr_activity(ctx: dict) -> list:
    from reNgine.recon_tasks import mapcidr_expand
    activity.logger.info("[RunMapCIDRActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(mapcidr_expand, ctx, task_name='mapcidr_expand', description='CIDR Expansion (mapcidr)',
                     cidr=ctx.get('cidr'))


@activity.defn(name="RunSSHAuditActivity")
def run_sshaudit_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import sshaudit_scan
    activity.logger.info("[RunSSHAuditActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(sshaudit_scan, ctx, task_name='sshaudit_scan', description='SSH Audit (ssh-audit)',
                     host=ctx.get('host'), port=ctx.get('port', 22))


@activity.defn(name="RunSearchsploitActivity")
def run_searchsploit_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import searchsploit_scan
    activity.logger.info("[RunSearchsploitActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(searchsploit_scan, ctx, task_name='searchsploit_scan', description='Exploit Search (searchsploit)',
                     service=ctx.get('service', ''), version=ctx.get('version'))


@activity.defn(name="RunWPProbeActivity")
def run_wpprobe_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import wpprobe_scan
    activity.logger.info("[RunWPProbeActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(wpprobe_scan, ctx, task_name='wpprobe_scan', description='WordPress Plugin Scan (wpprobe)',
                     url=ctx.get('url'))


@activity.defn(name="RunXURLFind3rActivity")
def run_xurlfind3r_activity(ctx: dict) -> bool:
    from reNgine.crawl_tasks import xurlfind3r_scan
    activity.logger.info("[RunXURLFind3rActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(xurlfind3r_scan, ctx, task_name='xurlfind3r_scan', description='Passive URL Discovery (xurlfind3r)',
                     domain=ctx.get('domain'), domains=ctx.get('domains'))


@activity.defn(name="RunURLFinderActivity")
def run_urlfinder_activity(ctx: dict) -> bool:
    from reNgine.crawl_tasks import urlfinder_scan
    activity.logger.info("[RunURLFinderActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(urlfinder_scan, ctx, task_name='urlfinder_scan', description='Passive URL Discovery (urlfinder)',
                     domain=ctx.get('domain'))


@activity.defn(name="RunCariddiActivity")
def run_cariddi_activity(ctx: dict) -> bool:
    from reNgine.crawl_tasks import cariddi_scan
    activity.logger.info("[RunCariddiActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(cariddi_scan, ctx, task_name='cariddi_scan', description='Endpoint Crawl & Secret Hunt (cariddi)',
                     url=ctx.get('url'), urls=ctx.get('urls'))


@activity.defn(name="RunBUPActivity")
def run_bup_activity(ctx: dict) -> bool:
    from reNgine.crawl_tasks import bup_scan
    activity.logger.info("[RunBUPActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(bup_scan, ctx, task_name='bup_scan', description='4xx URL Bypass (bup)',
                     url=ctx.get('url'), urls=ctx.get('urls'))


@activity.defn(name="RunArjunActivity")
def run_arjun_activity(ctx: dict) -> bool:
    from reNgine.crawl_tasks import arjun_scan
    activity.logger.info("[RunArjunActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(arjun_scan, ctx, task_name='arjun_scan', description='Parameter Discovery (arjun)',
                     url=ctx.get('url'), urls=ctx.get('urls'))


@activity.defn(name="RunFeroxbusterActivity")
def run_feroxbuster_activity(ctx: dict) -> bool:
    from reNgine.crawl_tasks import feroxbuster_scan
    activity.logger.info("[RunFeroxbusterActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(feroxbuster_scan, ctx, task_name='feroxbuster_scan', description='Recursive Fuzzing (feroxbuster)',
                     url=ctx.get('url'), urls=ctx.get('urls'))


@activity.defn(name="RunGFActivity")
def run_gf_activity(ctx: dict) -> list:
    """Run gf URL pattern matching. Returns matched URL list (not bool)."""
    from reNgine.crawl_tasks import gf_scan
    activity.logger.info("[RunGFActivity] pattern=%s scan_id=%s", ctx.get('pattern'), ctx.get('scan_history_id'))
    proxy = TemporalTaskProxy(ctx, task_name='gf_scan', description='URL Pattern Match (gf)')
    return gf_scan(proxy, scan_history_id=ctx.get('scan_history_id'),
                   pattern=ctx.get('pattern', 'xss'), urls=ctx.get('urls', []))
```

- [ ] **Step 2: Verify no import errors**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 -c 'from reNgine.temporal_activities import run_dnsx_activity, run_wafw00f_activity, run_fping_activity, run_gf_activity; print(\"OK\")'"
```
Expected: `OK`

- [ ] **Step 3: Commit activities**

```bash
git add web/reNgine/temporal_activities.py
git commit -m "feat(activities): register 14 new Temporal activities for rengine-ng tool palette"
```

---

## Task 5: Register all new activities in the orchestrator

**Files:**
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`

- [ ] **Step 1: Add imports to the orchestrator**

In the `from reNgine.temporal_activities import (` block, add the following entries under the `# Tier 6` section:

```python
    # Phase 1 — rengine-ng tool activities
    run_dnsx_activity,
    run_wafw00f_activity,
    run_fping_activity,
    run_arpscan_activity,
    run_mapcidr_activity,
    run_sshaudit_activity,
    run_searchsploit_activity,
    run_wpprobe_activity,
    run_xurlfind3r_activity,
    run_urlfinder_activity,
    run_cariddi_activity,
    run_bup_activity,
    run_arjun_activity,
    run_feroxbuster_activity,
    run_gf_activity,
```

- [ ] **Step 2: Add to the `activities=[...]` list in `Worker(...)` constructor**

Find the `activities=[...]` list inside the `Worker` constructor and add each new function at the end.

- [ ] **Step 3: Verify orchestrator starts without error**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && timeout 5 python3 manage.py run_temporal_orchestrator 2>&1 | grep -E '(ERROR|registered|Started)' | head -20"
```
Expected: Lines showing activity registrations, no `ERROR` or `ImportError`.

- [ ] **Step 4: Commit**

```bash
git add web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(orchestrator): register 14 new Phase 1 tool activities with Temporal worker"
```

---

## Task 6: Run full test suite to confirm no regressions

- [ ] **Step 1: Run all tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -20"
```
Expected: `OK` — existing tests still pass.

- [ ] **Step 2: Commit checkpoint**

```bash
git add .
git commit -m "chore(phase1): tool foundation checkpoint — all activities registered"
```

---

## Task 7: `search_vulns` — per-service real-time exploit lookup activity

This task implements the decided behaviour: a `RunSearchVulnsActivity` that queries vulners.com in real-time for each discovered service version. It is separate from `RunSearchsploitActivity` (offline exploit-db) — both will be fanned out concurrently per service in `MasterScanWorkflow` Tier 2 (see Phase 2 Task 12).

**Files:**
- Modify: `web/reNgine/recon_tasks.py` (add `search_vulns_scan`)
- Modify: `web/reNgine/temporal_activities.py` (add `RunSearchVulnsActivity`)
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py` (register)
- Modify: `web/tests/test_recon_tasks.py` (add test)

- [ ] **Step 1: Add test for `search_vulns_scan`**

```python
# Add to web/tests/test_recon_tasks.py

class TestSearchVulnsTask(TestCase):
    @patch('requests.get')
    def test_search_vulns_parses_vulners_response(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'data': {
                    'search': [
                        {
                            'id': 'CVE-2021-44228',
                            'title': 'Log4Shell',
                            'cvss': {'score': 10.0},
                            'description': 'Remote code execution in Log4j',
                            'published': '2021-12-10',
                        }
                    ]
                }
            }
        )
        from reNgine.recon_tasks import search_vulns_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = search_vulns_scan(
            proxy,
            scan_history_id=1,
            service='apache-httpd',
            version='2.4.49',
            host='192.0.2.1',
            port=80,
        )
        self.assertTrue(result)

    @patch('requests.get')
    def test_search_vulns_handles_empty_results(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {'data': {'search': []}}
        )
        from reNgine.recon_tasks import search_vulns_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = search_vulns_scan(
            proxy, scan_history_id=1, service='custom-app', version='1.0',
            host='192.0.2.1', port=9090,
        )
        self.assertTrue(result)

    @patch('requests.get')
    def test_search_vulns_skips_unknown_service(self, mock_get):
        from reNgine.recon_tasks import search_vulns_scan
        proxy = MagicMock()
        proxy.yaml_configuration = {}
        result = search_vulns_scan(
            proxy, scan_history_id=1, service='', version=None,
            host='192.0.2.1', port=12345,
        )
        self.assertTrue(result)
        mock_get.assert_not_called()
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestSearchVulnsTask --verbosity=2 2>&1 | head -15"
```
Expected: `ImportError: cannot import name 'search_vulns_scan'`

- [ ] **Step 3: Add `search_vulns_scan` to `recon_tasks.py`**

Append to `web/reNgine/recon_tasks.py`:

```python
def search_vulns_scan(
    self,
    scan_history_id: int,
    service: str,
    version: Optional[str],
    host: str,
    port: int,
) -> bool:
    """Query vulners.com for known CVEs/exploits for a discovered service+version.

    Called concurrently per service immediately after port scan completes in
    MasterScanWorkflow Tier 2. Saves findings as Vulnerability records.
    Skips lookup when service name is empty or the service is unrecognised
    (too many false positives from non-standard service strings).

    Uses vulners.com free text search API. No API key required for low
    volume usage; key configurable via VULNERS_API_KEY env var for higher
    rate limits.
    """
    import requests
    from startScan.models import Vulnerability
    from django.db import transaction

    if not service or not service.strip():
        return True

    # Normalise: "apache-httpd 2.4.49" → "apache-httpd/2.4.49" style query
    query = f"{service} {version}".strip() if version else service.strip()
    api_key = os.environ.get('VULNERS_API_KEY', '')
    url = 'https://vulners.com/api/v3/search/lucene/'

    params: dict = {
        'query': query,
        'fields': ['id', 'title', 'cvss', 'description', 'published'],
        'size': 10,
    }
    if api_key:
        params['apiKey'] = api_key

    logger.log_line("[SEARCH_VULNS]", "START", "querying vulners for %s" % query)

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get('data', {}).get('search', [])
    except Exception as exc:
        logger.log_line("[SEARCH_VULNS]", "WARN", "vulners query failed: %s" % str(exc))
        return True

    if not results:
        logger.log_line("[SEARCH_VULNS]", "RESULT", "no results for %s" % query)
        return True

    vulns = []
    for item in results:
        cvss_score = 0.0
        cvss_data = item.get('cvss') or {}
        if isinstance(cvss_data, dict):
            cvss_score = float(cvss_data.get('score', 0))
        elif isinstance(cvss_data, (int, float)):
            cvss_score = float(cvss_data)

        if cvss_score >= 9.0:
            severity = 'critical'
        elif cvss_score >= 7.0:
            severity = 'high'
        elif cvss_score >= 4.0:
            severity = 'medium'
        else:
            severity = 'low'

        vulns.append(Vulnerability(
            scan_history_id=scan_history_id,
            name=item.get('id', 'Service Vulnerability'),
            severity=severity,
            description='%s\n\nService: %s %s\nHost: %s:%d\nCVSS: %.1f\n\n%s' % (
                item.get('title', ''),
                service, version or '',
                host, port,
                cvss_score,
                item.get('description', ''),
            ),
            source='search_vulns',
            matched_at='%s:%d' % (host, port),
        ))

    if vulns:
        with transaction.atomic():
            Vulnerability.objects.bulk_create(vulns, ignore_conflicts=True)
        logger.log_line(
            "[SEARCH_VULNS]", "RESULT",
            "saved %d vulns for %s on %s:%d" % (len(vulns), query, host, port),
        )

    return True
```

- [ ] **Step 4: Add `RunSearchVulnsActivity` to `temporal_activities.py`**

Append at the end of the Phase 1 activity block added in Task 4:

```python
@activity.defn(name="RunSearchVulnsActivity")
def run_search_vulns_activity(ctx: dict) -> bool:
    """Query vulners.com for CVEs/exploits for a single service+version.

    Designed to be fanned out concurrently — one activity instance per
    discovered service from RunPortScanActivity. Called from
    MasterScanWorkflow Tier 2 after port scan returns.
    """
    from reNgine.recon_tasks import search_vulns_scan
    activity.logger.info(
        "[RunSearchVulnsActivity] service=%s host=%s scan_id=%s",
        ctx.get('service'), ctx.get('host'), ctx.get('scan_history_id'),
    )
    proxy = TemporalTaskProxy(ctx, task_name='search_vulns_scan',
                              description='Per-service CVE Lookup (vulners.com)')
    return search_vulns_scan(
        proxy,
        scan_history_id=ctx.get('scan_history_id'),
        service=ctx.get('service', ''),
        version=ctx.get('version'),
        host=ctx.get('host', ''),
        port=ctx.get('port', 0),
    )
```

- [ ] **Step 5: Register in orchestrator**

Add `run_search_vulns_activity` to the import block and `activities=[]` list in `run_temporal_orchestrator.py`.

- [ ] **Step 6: Run tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestSearchVulnsTask --verbosity=2"
```
Expected: `OK` — all 3 tests pass.

- [ ] **Step 7: Commit**

```bash
git add web/reNgine/recon_tasks.py web/reNgine/temporal_activities.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_recon_tasks.py
git commit -m "feat(activities): add RunSearchVulnsActivity — per-service real-time CVE lookup via vulners.com"
```

---

## Task 8: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -20"
```
Expected: `OK` — existing tests still pass.

- [ ] **Step 2: Tag Phase 1 complete**

```bash
git tag phase1-tool-foundation
```

---

## Self-Review

**Spec coverage:**
- ✅ All 18 tools installed in Dockerfile (Go, apt, pipx, pip, GitHub releases)
- ✅ Task functions created for all 18 tools + `search_vulns_scan`
- ✅ `@activity.defn` wrappers for all tools + `RunSearchVulnsActivity`
- ✅ All activities registered in orchestrator
- ✅ Tests for each task module
- ✅ `search_vulns_scan` queries vulners.com per service, saves Vulnerability records with CVSS-mapped severity

**Skipped (by design):**
- `msfconsole` — too heavy (100MB+ Metasploit framework); excluded by design
- `prompt` — secator interactive CLI utility, has no place in Temporal activities
- `netdetect` — Python-only network interface detection; not a subprocess tool; will be inlined in CIDRReconWorkflow (Phase 2)
- `urlparser` — Python string parsing utility; inlined in URLParamsFuzzWorkflow (Phase 2)
- `bbot` — installed in Dockerfile but activity deferred to Phase 2 (used in extended OSINT)

**Placeholder scan:** None — all steps have exact commands and code.

**Type consistency:** `_run_task` pattern used consistently; `ctx: dict` parameter on all activities matches existing pattern. `RunSearchVulnsActivity` uses direct proxy construction (not `_run_task`) because it passes individual kwargs, not a bulk ctx passthrough.
