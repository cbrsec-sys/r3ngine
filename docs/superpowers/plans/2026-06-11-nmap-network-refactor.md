# Nmap Port Scan Correctness + Network Tasks Refactor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five cross-host data-integrity bugs in nmap scanning, move all network-oriented functions out of the monolithic `tasks.py` into `network_tasks.py`, and add IP-based deduplication so hosts sharing an IP are not nmap-scanned twice.

**Architecture:** The `port_scan` and `nmap` functions (and all `parse_nmap_*` helpers) currently live in `tasks.py` alongside ~5 000 lines of unrelated scan logic. They are extracted wholesale into `web/reNgine/network_tasks.py`, which already exists as the home for protocol-specific network enumeration. All callers — `temporal_activities.py` (3 sites) and `tests/test_nmap.py` — are updated to import from the new location. `tasks.py` keeps thin re-export shims so any unknown callers keep working without a search-and-replace pass.

**Tech Stack:** Python 3, Django ORM (`Subdomain`, `IpAddress`, `Port`), `xmltodict`, pytest inside Docker.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `web/reNgine/network_tasks.py` | Add `_get_host_ips`, `_lookup_host_subdomain`, all `parse_nmap_*` helpers, `nmap()`, `port_scan()` |
| Modify | `web/reNgine/tasks.py` | Remove moved functions; add one-line re-export shims for backward compat |
| Modify | `web/reNgine/temporal_activities.py` | Update 3 import sites (lines ~741, ~2278, ~2311) from `reNgine.tasks` → `reNgine.network_tasks` |
| Modify | `web/tests/test_nmap.py` | Update import from `reNgine.tasks` → `reNgine.network_tasks`; add regression tests |
| Read-only | `web/reNgine/common_func.py` | `sanitize_url` (line 550), `get_nmap_cmd` (line 1464), `save_vulnerability`, `get_subdomains`, `get_port_service_description`, `update_or_create_port`, `get_random_proxy` |
| Read-only | `web/reNgine/utils/task.py` | `save_ip_address`, `save_endpoint`, `run_command`, `stream_command` |

---

## Bug Reference (from audit)

| # | Severity | Location | Root Cause |
|---|----------|----------|------------|
| 1 | CRITICAL | `nmap()` line ~2675 | `save_vulnerability` uses `self.subdomain` (task-level) not the per-host subdomain |
| 2 | CRITICAL | `nmap()` line ~2729 | `save_auth_candidate` for discovered services uses `self.subdomain` |
| 3 | CRITICAL | `nmap()` line ~2624 | `output_file = self.output_path` is shared; every host overwrites the previous JSON |
| 4 | MEDIUM | `nmap()` line ~2622 | `self.filename = self.filename.replace('.txt', '.xml')` mutates shared instance state |
| 5 | CRITICAL | `nmap()` line ~2706 | `save_auth_candidate` for NSE auth-portal vulns uses `self.subdomain` |

---

## Task 1: Regression tests for all five bugs

**Files:**
- Modify: `web/tests/test_nmap.py`

These tests are written BEFORE any code changes. They must **fail** against the current codebase, then **pass** after Tasks 2–5.

- [ ] **Step 1: Add failing regression tests**

Append to `web/tests/test_nmap.py`:

```python
# ─────────────────────────────────────────────────────────────────────────────
# Regression tests for nmap() cross-host bugs
# ─────────────────────────────────────────────────────────────────────────────
from unittest.mock import patch, MagicMock, call
from django.test import TestCase
from startScan.models import Domain, ScanHistory, Subdomain
from scanEngine.models import EngineType


def _make_scan(domain_name='scan.example.com'):
    engine = EngineType.objects.create(
        engine_name='test-nmap',
        yaml_configuration='port_scan:\n  enable_nmap: true\n'
    )
    domain = Domain.objects.create(name=domain_name)
    scan = ScanHistory.objects.create(
        domain=domain, scan_type=engine, scan_status=0,
        start_scan_date='2026-01-01T00:00:00Z'
    )
    return domain, scan


def _make_subdomain(name, domain, scan):
    return Subdomain.objects.create(name=name, target_domain=domain, scan_history=scan)


def _proxy_for(scan, subdomain=None):
    """Build a minimal TemporalTaskProxy-like object."""
    from reNgine.temporal_activities import TemporalTaskProxy
    ctx = {
        'scan_history_id': scan.id,
        'domain_id': scan.domain.id,
    }
    proxy = TemporalTaskProxy.__new__(TemporalTaskProxy)
    proxy.scan = scan
    proxy.scan_id = scan.id
    proxy.domain = scan.domain
    proxy.subdomain = subdomain
    proxy.subscan = None
    proxy.results_dir = '/tmp'
    proxy.history_file = '/tmp/history.txt'
    proxy.filename = 'nmap_output.txt'
    proxy.output_path = '/tmp/nmap_output.json'
    proxy.activity_id = None
    proxy.yaml_configuration = {}
    return proxy


class TestNmapPerHostSubdomain(TestCase):
    """Bug #1/#2/#5: nmap() must use the scanned host's subdomain, not self.subdomain."""

    def setUp(self):
        self.domain, self.scan = _make_scan()
        self.sub_a = _make_subdomain('a.scan.example.com', self.domain, self.scan)
        self.sub_b = _make_subdomain('b.scan.example.com', self.domain, self.scan)

    @patch('reNgine.network_tasks.run_command')
    @patch('reNgine.network_tasks.parse_nmap_results')
    @patch('reNgine.network_tasks.get_random_proxy', return_value='')
    @patch('reNgine.network_tasks.OpSecManager')
    @patch('reNgine.network_tasks.save_vulnerability')
    def test_vulnerability_saved_with_correct_per_host_subdomain(
            self, mock_save_vuln, mock_opsec, mock_proxy, mock_parse, mock_run):
        """Vuln found on b.scan.example.com must be saved under sub_b, not sub_a."""
        mock_parse.return_value = {
            'vulns': [{'name': 'TestVuln', 'severity': 2, 'http_url': 'b.scan.example.com:22',
                        'type': 'info', 'source': 'nmap'}],
            'services': [],
        }
        from reNgine.network_tasks import nmap
        proxy = _proxy_for(self.scan, subdomain=self.sub_a)  # initialized to sub_a

        nmap(proxy, host='b.scan.example.com', ports=[22])

        called_subdomain = mock_save_vuln.call_args[1].get('subdomain') \
            or mock_save_vuln.call_args[0][0] if mock_save_vuln.called else None
        # Must be sub_b (b.scan.example.com), NOT sub_a
        if mock_save_vuln.called:
            kw = mock_save_vuln.call_args[1]
            self.assertEqual(kw.get('subdomain'), self.sub_b,
                             f"Expected sub_b but got {kw.get('subdomain')}")


class TestNmapPerHostOutputFile(TestCase):
    """Bug #3: nmap() must write to per-host JSON files, not a shared self.output_path."""

    def setUp(self):
        self.domain, self.scan = _make_scan('out.example.com')
        self.sub = _make_subdomain('out.example.com', self.domain, self.scan)

    @patch('reNgine.network_tasks.run_command')
    @patch('reNgine.network_tasks.parse_nmap_results')
    @patch('reNgine.network_tasks.get_random_proxy', return_value='')
    @patch('reNgine.network_tasks.OpSecManager')
    def test_output_file_is_per_host(self, mock_opsec, mock_proxy, mock_parse, mock_run):
        """parse_nmap_results must NOT be called with self.output_path."""
        mock_parse.return_value = {'vulns': [], 'services': []}
        from reNgine.network_tasks import nmap
        proxy = _proxy_for(self.scan, self.sub)

        nmap(proxy, host='out.example.com', ports=[80])

        output_file_arg = mock_parse.call_args[0][1]  # second positional arg
        self.assertNotEqual(output_file_arg, proxy.output_path,
                            "nmap() must use a per-host output file, not self.output_path")
        self.assertIn('out.example.com', output_file_arg)


class TestNmapFilenameNotMutated(TestCase):
    """Bug #4: nmap() must not mutate self.filename."""

    def setUp(self):
        self.domain, self.scan = _make_scan('fn.example.com')
        self.sub = _make_subdomain('fn.example.com', self.domain, self.scan)

    @patch('reNgine.network_tasks.run_command')
    @patch('reNgine.network_tasks.parse_nmap_results')
    @patch('reNgine.network_tasks.get_random_proxy', return_value='')
    @patch('reNgine.network_tasks.OpSecManager')
    def test_self_filename_unchanged_after_nmap(self, mock_opsec, mock_proxy, mock_parse, mock_run):
        mock_parse.return_value = {'vulns': [], 'services': []}
        from reNgine.network_tasks import nmap
        proxy = _proxy_for(self.scan, self.sub)
        original_filename = proxy.filename  # 'nmap_output.txt'

        nmap(proxy, host='fn.example.com', ports=[443])

        self.assertEqual(proxy.filename, original_filename,
                         "nmap() must not mutate self.filename")


class TestNmapIPDedup(TestCase):
    """IP deduplication: hosts sharing an already-scanned IP must be skipped."""

    def setUp(self):
        self.domain, self.scan = _make_scan('dedup.example.com')
        self.sub_a = _make_subdomain('a.dedup.example.com', self.domain, self.scan)
        self.sub_b = _make_subdomain('b.dedup.example.com', self.domain, self.scan)
        # Give both subdomains the same IP
        from startScan.models import IpAddress
        self.ip = IpAddress.objects.create(address='10.0.0.1')
        self.sub_a.ip_addresses.add(self.ip)
        self.sub_b.ip_addresses.add(self.ip)

    @patch('reNgine.network_tasks.nmap')
    @patch('reNgine.network_tasks.stream_command')
    def test_second_host_skipped_when_ip_already_scanned(self, mock_stream, mock_nmap):
        """When a.dedup and b.dedup share 10.0.0.1, nmap called only once."""
        # Simulate naabu finding port 22 on both hosts
        mock_stream.return_value = iter([
            {'ip': '10.0.0.1', 'port': 22, 'host': 'a.dedup.example.com'},
            {'ip': '10.0.0.1', 'port': 22, 'host': 'b.dedup.example.com'},
        ])
        from reNgine.network_tasks import port_scan
        proxy = _proxy_for(self.scan)
        proxy.yaml_configuration = {
            'port_scan': {'enable_nmap': True, 'ports': ['22']}
        }

        port_scan(proxy, ctx={'scan_history_id': self.scan.id, 'domain_id': self.domain.id})

        self.assertEqual(mock_nmap.call_count, 1,
                         f"Expected 1 nmap call (IP dedup), got {mock_nmap.call_count}")
```

- [ ] **Step 2: Run tests to confirm they fail (expected — functions not in network_tasks yet)**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test tests.test_nmap.TestNmapPerHostSubdomain tests.test_nmap.TestNmapPerHostOutputFile tests.test_nmap.TestNmapFilenameNotMutated tests.test_nmap.TestNmapIPDedup --verbosity=2 2>&1 | tail -30"
```

Expected: `ImportError` or `AttributeError` — functions not yet in `network_tasks`.

---

## Task 2: Add helpers and move parse_nmap_* to network_tasks.py

**Files:**
- Modify: `web/reNgine/network_tasks.py`

- [ ] **Step 1: Add imports and helpers at the top of network_tasks.py**

Open `web/reNgine/network_tasks.py`. After the existing imports, add:

```python
import json
import os
import re
import xmltodict

from reNgine.common_func import sanitize_url
from reNgine.definitions import NMAP
from startScan.models import Subdomain


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_host_ips(host: str, scan) -> set:
    """Return the set of IP address strings associated with *host* in *scan*.

    Used for nmap IP-deduplication: hosts sharing an IP that has already been
    nmap-scanned within this run can be safely skipped.
    """
    subdomain = Subdomain.objects.filter(name=host, scan_history=scan).first()
    if not subdomain:
        return set()
    return set(subdomain.ip_addresses.values_list('address', flat=True))


def _lookup_host_subdomain(host: str, self_task):
    """Return the Subdomain ORM object for *host* within the current scan.

    Falls back to self_task.subdomain when no match is found (e.g. IP-only
    targets where no Subdomain row exists yet).
    """
    if not host:
        return self_task.subdomain
    sub = Subdomain.objects.filter(
        name=host,
        target_domain=self_task.domain,
        scan_history=self_task.scan,
    ).first()
    return sub if sub is not None else self_task.subdomain
```

- [ ] **Step 2: Move all parse_nmap_* helpers from tasks.py into network_tasks.py**

Copy (do not delete yet) the following functions verbatim from `tasks.py` into `network_tasks.py`, in this order. Each function is self-contained. Replace any `logger.error(f'...')` / `logger.warning(f'...')` f-strings that embed external data with `%s` style per the logging standard.

Functions to copy (line numbers in `tasks.py` as of the audit):
- `parse_nmap_results` (line 4982) — fix the two f-string logger calls at ~4997 and ~5058
- `parse_nmap_https_redirect_output` (line 5140)
- `parse_nmap_http_server_header_output` (line 5149)
- `parse_nmap_fingerprint_strings_output` (line 5158)
- `parse_nmap_http_title_output` (line 5179)
- `parse_nmap_generic_vuln_output` (line 5190)
- `parse_nmap_http_csrf_output` (line 5226)
- `parse_nmap_vulscan_output` (line 5230)
- `parse_nmap_vulners_output` (line 5312)

Fixed logger calls inside `parse_nmap_results`:

```python
# Replace:
logger.error(f'Cannot parse {xml_file} to valid JSON. Skipping.')
# With:
logger.error('Cannot parse %s to valid JSON. Skipping.', xml_file)

# Replace:
logger.info(f'Parsing nmap results for {hostname}:{port_number} ...')
# With:
logger.info('Parsing nmap results for %s:%s', hostname, port_number)

# Replace:
logger.debug(f'Ran nmap script "{script_id}" on {port_number}/{port_protocol}:\n{script_output}\n')
# With:
logger.debug('Ran nmap script "%s" on %s/%s', script_id, port_number, port_protocol)

# Replace:
logger.warning(f'Script output parsing for script "{script_id}" is not supported yet.')
# With:
logger.warning('Script output parsing for script "%s" is not supported yet.', script_id)
```

- [ ] **Step 3: Run the import test to confirm parse_nmap_results is importable from network_tasks**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 -c 'from reNgine.network_tasks import parse_nmap_results; print(\"OK\")'"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/network_tasks.py
git commit -m "refactor: move parse_nmap_* helpers to network_tasks"
```

---

## Task 3: Move nmap() to network_tasks.py with all bug fixes

**Files:**
- Modify: `web/reNgine/network_tasks.py`

The function is moved AND fixed in a single step to keep the diff coherent.

- [ ] **Step 1: Add nmap() to network_tasks.py**

Add the following new imports near the top of `network_tasks.py` (alongside existing ones):

```python
from reNgine.common_func import (
    get_nmap_cmd,
    get_random_proxy,
    save_vulnerability,
)
from reNgine.opsec_utils import OpSecManager
from reNgine.utils.task import run_command, save_endpoint
from reNgine.utilities import save_auth_candidate
from startScan.models import EndPoint
```

Then add the `nmap` function. This is the **corrected** version — diff from the original:

```python
def nmap(
        self,
        cmd=None,
        ports=[],
        host=None,
        input_file=None,
        script=None,
        script_args=None,
        max_rate=None,
        ctx={},
        description=None):
    """Run nmap against a single host.

    Each call writes to its own per-host XML and JSON output file so that
    running nmap in a loop over multiple hosts does not overwrite results.
    The subdomain DB object used for saving findings is looked up from the
    DB for the specific *host*, not from self.subdomain (which is
    task-level and does not change between loop iterations).
    """
    # Deduplicate ports
    ports = list(dict.fromkeys(ports))
    ports_str = ','.join(str(port) for port in ports)

    # Fix Bug #4: derive filenames locally — never mutate self.filename
    base_name = os.path.splitext(os.path.basename(self.filename))[0]
    output_file_xml = f'{self.results_dir}/{host}_{base_name}.xml'
    # Fix Bug #3: per-host JSON output so loop iterations don't overwrite each other
    output_file = f'{self.results_dir}/{host}_{base_name}.json'
    vulns_file = f'{self.results_dir}/{host}_{base_name}_vulns.json'

    # Build nmap command
    nmap_cmd = get_nmap_cmd(
        cmd=cmd,
        ports=ports_str,
        script=script,
        script_args=script_args,
        max_rate=max_rate,
        host=host,
        input_file=input_file,
        output_file=output_file_xml)

    if not nmap_cmd:
        logger.error('Could not build nmap command for host %s', host)
        return

    # Apply OpSec stealth
    proxy = get_random_proxy()
    opsec = OpSecManager()
    nmap_cmd = opsec.apply_stealth('nmap', nmap_cmd, proxy=proxy)

    # Run nmap
    run_command(
        nmap_cmd,
        shell=True,
        history_file=self.history_file,
        scan_id=self.scan_id,
        activity_id=self.activity_id)

    # Parse per-host XML results
    nmap_results = parse_nmap_results(output_file_xml, output_file)
    vulns = nmap_results['vulns']
    discovered_services = nmap_results['services']

    with open(vulns_file, 'w') as f:
        json.dump(vulns, f, indent=4)

    # Fix Bug #1: look up the subdomain for THIS host, not self.subdomain
    host_subdomain = _lookup_host_subdomain(host, self)

    # Save vulnerabilities found by nmap
    vulns_str = ''
    for vuln_data in vulns:
        url = vuln_data['http_url']
        endpoint = EndPoint.objects.filter(http_url__contains=url).first()
        if endpoint:
            vuln_data['http_url'] = endpoint.http_url
        vuln, created = save_vulnerability(
            target_domain=self.domain,
            subdomain=host_subdomain,           # Fix Bug #1
            scan_history=self.scan,
            subscan=self.subscan,
            endpoint=endpoint,
            dedup_fields=['name', 'subdomain', 'scan_history'],
            **vuln_data)
        vulns_str += f'• {str(vuln)}\n'
        if created:
            logger.warning('New nmap vulnerability: %s', vuln)

        # Register Auth Candidates from vulnerability tags
        if 'auth_portal' in (vuln_data.get('tags') or []):
            url_str = vuln_data.get('http_url') or ''
            parsed_port = 80
            if url_str:
                try:
                    from urllib.parse import urlparse as _urlparse
                    parsed_url = _urlparse(url_str)
                    if parsed_url.port:
                        parsed_port = parsed_url.port
                    else:
                        parsed_port = 443 if parsed_url.scheme == 'https' else 80
                except Exception:
                    try:
                        port_part = url_str.split(':')[-1]
                        if port_part.isdigit():
                            parsed_port = int(port_part)
                    except Exception:
                        pass
            save_auth_candidate(
                scan_history=self.scan,
                target=vuln_data['http_url'],
                protocol='http',
                port=parsed_port,
                source_tool='Nmap NSE',
                metadata={'tags': vuln_data.get('tags') or [],
                           'nse_script': vuln_data.get('name')},
                subdomain=host_subdomain,       # Fix Bug #5
                endpoint=endpoint,
            )

    # Register Auth Candidates from discovered services (SMB, RDP, SSH …)
    interesting_protocols = {
        'microsoft-ds': 'smb', 'smb': 'smb',
        'ms-wbt-server': 'rdp', 'rdp': 'rdp',
        'ssh': 'ssh', 'ftp': 'ftp', 'telnet': 'telnet',
    }
    for svc in discovered_services:
        proto = interesting_protocols.get(svc['service'])
        if proto:
            save_auth_candidate(
                scan_history=self.scan,
                target=svc['target'],
                protocol=proto,
                port=svc['port'],
                source_tool='Nmap Service Discovery',
                metadata={'banner': svc['banner']},
                subdomain=host_subdomain,       # Fix Bug #2
            )

    self.notify(
        severity=0,
        fields={'Vulnerabilities discovered': vulns_str},
        add_meta_info=False)

    return vulns
```

- [ ] **Step 2: Run targeted tests to confirm Bugs #1–#5 are fixed**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test \
   tests.test_nmap.TestNmapPerHostSubdomain \
   tests.test_nmap.TestNmapPerHostOutputFile \
   tests.test_nmap.TestNmapFilenameNotMutated \
   --verbosity=2 2>&1 | tail -20"
```

Expected: 3 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add web/reNgine/network_tasks.py
git commit -m "fix(nmap): per-host subdomain + JSON output + no self.filename mutation"
```

---

## Task 4: Move port_scan() to network_tasks.py with IP deduplication

**Files:**
- Modify: `web/reNgine/network_tasks.py`

- [ ] **Step 1: Add remaining imports needed by port_scan to network_tasks.py**

```python
from reNgine.common_func import (
    get_subdomains,
    get_port_service_description,
    update_or_create_port,
)
from reNgine.definitions import (
    DEFAULT_ENABLE_HTTP_CRAWL, DEFAULT_HTTP_TIMEOUT, DEFAULT_RATE_LIMIT,
    DEFAULT_THREADS, ENABLE_HTTP_CRAWL, ENABLE_NMAP, ENABLE_NETWORK_ENUM,
    NAABU_DEFAULT_PORTS, NAABU_EXCLUDE_PORTS, NAABU_EXCLUDE_SUBDOMAINS,
    NAABU_PASSIVE, NAABU_RATE, NMAP_COMMAND, NMAP_SCRIPT, NMAP_SCRIPT_ARGS,
    PORT_SCAN, PORTS, THREADS, TIMEOUT, UNCOMMON_WEB_PORTS, USE_NAABU_CONFIG,
)
from reNgine.utils.task import get_task_title, return_iterable, save_ip_address, save_endpoint, stream_command
```

(Verify each of these import paths exists before writing — `get_task_title` and `return_iterable` are likely in `utils/task.py` or `common_func.py`; check and adjust.)

- [ ] **Step 2: Add port_scan() with IP deduplication to network_tasks.py**

```python
def port_scan(self, hosts=[], ctx={}, description=None, prepare_only=False, parse_only=None):
    """Run port scan (naabu + optional nmap) against *hosts*.

    IP deduplication: before invoking nmap for a host, the host's resolved
    IP addresses are checked against a set of already-nmap-scanned IPs in
    this run. If the IP has been scanned already, nmap is skipped for that
    host — the port data is already attributed to the shared IP object.
    """
    input_file = f'{self.results_dir}/input_subdomains_port_scan.txt'
    proxy = ''  # naabu/httpx fail with proxies

    config = self.yaml_configuration.get(PORT_SCAN) or {}
    enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
    timeout = config.get(TIMEOUT) or self.yaml_configuration.get(TIMEOUT, DEFAULT_HTTP_TIMEOUT)
    exclude_ports = config.get(NAABU_EXCLUDE_PORTS, [])
    exclude_subdomains = config.get(NAABU_EXCLUDE_SUBDOMAINS, False)
    ports = config.get(PORTS, NAABU_DEFAULT_PORTS)
    ports = [str(port) for port in ports]
    rate_limit = config.get(NAABU_RATE) or self.yaml_configuration.get(RATE_LIMIT, DEFAULT_RATE_LIMIT)
    threads = config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
    passive = config.get(NAABU_PASSIVE, False)
    use_naabu_config = config.get(USE_NAABU_CONFIG, False)
    exclude_ports_str = ','.join(return_iterable(exclude_ports))
    nmap_enabled = config.get(ENABLE_NMAP, False)
    nmap_cmd = config.get(NMAP_COMMAND, '')
    nmap_script = config.get(NMAP_SCRIPT, '')
    nmap_script = ','.join(return_iterable(nmap_script))
    nmap_script_args = config.get(NMAP_SCRIPT_ARGS)

    if hosts:
        with open(input_file, 'w') as f:
            f.write('\n'.join(hosts))
    else:
        hosts = get_subdomains(
            write_filepath=input_file,
            exclude_subdomains=exclude_subdomains,
            ctx=ctx)

    if not hosts:
        logger.warning('port_scan: no hosts to scan, skipping.')
        return []

    # Build naabu command
    cmd = 'naabu -json -exclude-cdn'
    cmd += f' -list {input_file}' if len(hosts) > 1 else f' -host {hosts[0]}'
    if 'full' in ports or 'all' in ports:
        ports_str = ' -p "-"'
    elif 'top-100' in ports:
        ports_str = ' -top-ports 100'
    elif 'top-1000' in ports:
        ports_str = ' -top-ports 1000'
    else:
        ports_str = ','.join(ports)
        ports_str = f' -p {ports_str}'
    cmd += ports_str
    cmd += ' -config /root/.config/naabu/config.yaml' if use_naabu_config else ''
    cmd += f' -proxy "{proxy}"' if proxy else ''
    cmd += f' -c {threads}' if threads else ''
    cmd += f' -rate {rate_limit}' if rate_limit > 0 else ''
    cmd += f' -timeout {timeout}s' if timeout > 0 else ''
    cmd += ' -passive' if passive else ''
    cmd += f' -exclude-ports {exclude_ports_str}' if exclude_ports else ''
    cmd += ' -silent'

    if prepare_only:
        return {
            "cmd": cmd,
            "input_file": input_file,
            "hosts": hosts,
            "nmap_enabled": nmap_enabled,
            "nmap_cmd": nmap_cmd,
            "nmap_script": nmap_script,
            "nmap_script_args": nmap_script_args,
            "rate_limit": rate_limit,
        }

    results = []
    urls = []
    ports_data = {}

    if parse_only is not None:
        line_source = []
        for raw_line in parse_only.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                line_source.append(json.loads(raw_line))
            except Exception:
                line_source.append(raw_line)
    else:
        line_source = stream_command(
            cmd,
            shell=True,
            history_file=self.history_file,
            scan_id=self.scan_id,
            activity_id=self.activity_id)

    for line in line_source:
        if not isinstance(line, dict):
            continue
        results.append(line)
        port_number = line['port']
        ip_address = line['ip']
        host = line.get('host') or ip_address
        if port_number == 0:
            continue

        subdomain = Subdomain.objects.filter(
            name=host,
            target_domain=self.domain,
            scan_history=self.scan,
        ).first()

        ip, _ = save_ip_address(
            ip_address, subdomain, subscan=self.subscan,
            scan_id=self.scan_id, activity_id=self.activity_id)
        if self.subscan:
            from startScan.models import SubScan
            if SubScan.objects.filter(pk=self.subscan.pk).exists():
                ip.ip_subscan_ids.add(self.subscan)
            ip.save()

        if port_number not in [80, 443]:
            http_url = f'{host}:{port_number}'
            endpoint, _ = save_endpoint(http_url, crawl=False, ctx=ctx, subdomain=subdomain)
            if endpoint:
                http_url = endpoint.http_url
            urls.append(http_url)

        res = get_port_service_description(port_number)
        port, created = update_or_create_port(
            port_number=port_number,
            service_name=res.get('service_name', ''),
            description=res.get('description', ''),
        )
        if created:
            logger.warning('Added new port %d to DB', port_number)

        bf_protocols = {21: 'ftp', 22: 'ssh', 23: 'telnet', 445: 'smb', 3389: 'rdp'}
        if port_number in bf_protocols:
            try:
                save_auth_candidate(
                    scan_history=self.scan,
                    subdomain=subdomain,
                    target=host,
                    protocol=bf_protocols[port_number],
                    port=port_number,
                    source_tool='naabu',
                    tech_hint=f"Open Port {port_number}",
                )
            except Exception as e:
                logger.error('Error registering AuthCandidate from Naabu port %d: %s', port_number, e)

        if port_number in UNCOMMON_WEB_PORTS:
            port.is_uncommon = True
            port.save()
        ip.ports.add(port)
        ip.save()
        ports_data.setdefault(host, [])
        if port_number not in ports_data[host]:
            ports_data[host].append(port_number)

        logger.warning('Found opened port %d on %s (%s)', port_number, ip_address, host)

    if len(ports_data) == 0:
        logger.info('Finished naabu port scan — no open ports found.')
        if nmap_enabled:
            logger.warning('naabu found no open ports; running nmap independently.')
            nmap_fallback_ports = [int(p) for p in ports if p.isdigit()]
            # IP deduplication for fallback path
            nmap_scanned_ips: set = set()
            for host in hosts:
                host_ips = _get_host_ips(host, self.scan)
                if host_ips & nmap_scanned_ips:
                    logger.info('Skipping nmap for %s — IP already scanned this run', host)
                    continue
                nmap_scanned_ips |= host_ips
                ctx_nmap = ctx.copy()
                ctx_nmap['description'] = get_task_title(f'nmap_{host}', self.scan_id, self.subscan_id)
                ctx_nmap['track'] = False
                ctx_nmap['activity_id'] = self.activity_id
                nmap(self, cmd=nmap_cmd, ports=nmap_fallback_ports, host=host,
                     script=nmap_script, script_args=nmap_script_args,
                     max_rate=rate_limit, ctx=ctx_nmap)
        return ports_data

    # Notify
    fields_str = ''
    for host, host_ports in ports_data.items():
        ports_str_notif = ', '.join([f'`{p}`' for p in host_ports])
        fields_str += f'• `{host}`: {ports_str_notif}\n'
    self.notify(fields={'Ports discovered': fields_str})

    with open(self.output_path, 'w') as f:
        json.dump(results, f, indent=4)

    logger.info('Finished naabu port scan.')

    # nmap — one process per host, with IP deduplication
    if nmap_enabled:
        logger.warning('Starting nmap scans for %d hosts …', len(ports_data))
        nmap_scanned_ips: set = set()
        for host, port_list in ports_data.items():
            host_ips = _get_host_ips(host, self.scan)
            if host_ips & nmap_scanned_ips:
                logger.info('Skipping nmap for %s — IP %s already scanned this run',
                            host, host_ips & nmap_scanned_ips)
                continue
            nmap_scanned_ips |= host_ips
            ctx_nmap = ctx.copy()
            ctx_nmap['description'] = get_task_title(f'nmap_{host}', self.scan_id, self.subscan_id)
            ctx_nmap['track'] = False
            ctx_nmap['activity_id'] = self.activity_id
            logger.info('Running nmap for %s', host)
            nmap(self, cmd=nmap_cmd, ports=port_list, host=host,
                 script=nmap_script, script_args=nmap_script_args,
                 max_rate=rate_limit, ctx=ctx_nmap)

    # Protocol-specific network enumeration
    if config.get(ENABLE_NETWORK_ENUM, False) and ports_data:
        run_network_enum(self, ctx, ports_data)

    return ports_data
```

- [ ] **Step 3: Run the IP dedup regression test**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test tests.test_nmap.TestNmapIPDedup --verbosity=2 2>&1 | tail -20"
```

Expected: 1 test PASS.

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/network_tasks.py
git commit -m "feat(port_scan): IP dedup + move port_scan to network_tasks"
```

---

## Task 5: Update tasks.py — remove functions, add re-export shims

**Files:**
- Modify: `web/reNgine/tasks.py`

- [ ] **Step 1: Add re-export shims at the top of tasks.py (after existing imports)**

This preserves backward compatibility for any caller not updated yet:

```python
# Re-exports — these functions have moved to network_tasks. Import them here
# so existing callers that do `from reNgine.tasks import port_scan` keep working.
from reNgine.network_tasks import (  # noqa: F401 (re-export)
    nmap,
    parse_nmap_results,
    parse_nmap_vulners_output,
    parse_nmap_vulscan_output,
    parse_nmap_generic_vuln_output,
    parse_nmap_https_redirect_output,
    parse_nmap_http_server_header_output,
    parse_nmap_fingerprint_strings_output,
    parse_nmap_http_title_output,
    parse_nmap_http_csrf_output,
    port_scan,
)
```

- [ ] **Step 2: Delete the original function bodies from tasks.py**

Remove (do NOT leave stubs — the re-export above covers it):
- `def port_scan(...)` and its entire body (lines ~2338–2592)
- `def nmap(...)` and its entire body (lines ~2595–2749)
- `def parse_nmap_results(...)` and all `parse_nmap_*` helpers (lines ~4982–5360+)

Use your editor or `Edit` tool to remove each block. Confirm the re-exports at the top resolve correctly before deleting.

- [ ] **Step 3: Verify tasks.py still imports cleanly**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 -c 'import reNgine.tasks; print(\"OK\")'"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/tasks.py
git commit -m "refactor: remove nmap/port_scan from tasks.py (moved to network_tasks)"
```

---

## Task 6: Update temporal_activities.py imports

**Files:**
- Modify: `web/reNgine/temporal_activities.py`

There are three import sites. Each does a local `from reNgine.tasks import port_scan` inside an activity function. Update each to import from `network_tasks`:

- [ ] **Step 1: Find all three import sites**

```bash
grep -n "from reNgine.tasks import port_scan" web/reNgine/temporal_activities.py
```

Expected output (3 lines near ~741, ~2278, ~2311):
```
741:    from reNgine.tasks import port_scan
2278:    from reNgine.tasks import port_scan
2311:    from reNgine.tasks import port_scan
```

- [ ] **Step 2: Replace all three occurrences**

```bash
sed -i 's/from reNgine\.tasks import port_scan/from reNgine.network_tasks import port_scan/g' \
  web/reNgine/temporal_activities.py
```

Verify:
```bash
grep -n "port_scan" web/reNgine/temporal_activities.py | head -10
```

Expected: `from reNgine.network_tasks import port_scan` at all three sites.

- [ ] **Step 3: Commit**

```bash
git add web/reNgine/temporal_activities.py
git commit -m "refactor: update temporal_activities imports to use network_tasks"
```

---

## Task 7: Update test_nmap.py imports

**Files:**
- Modify: `web/tests/test_nmap.py`

- [ ] **Step 1: Update the two import lines at the top of test_nmap.py**

```python
# Replace:
from reNgine.tasks import parse_nmap_results
# With:
from reNgine.network_tasks import parse_nmap_results

# Replace (line ~84, inside a test method):
from reNgine import tasks
# That test inspects task source — update to use network_tasks:
from reNgine import network_tasks as tasks
```

The `test_vulners_dedup_uses_subdomain_not_http_url` test uses `inspect.getsource(tasks)` to check the source of the module. After moving, the dedup pattern lives in `network_tasks`, so this reference must point there.

- [ ] **Step 2: Run full nmap test suite**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test tests.test_nmap --verbosity=2 2>&1 | tail -30"
```

Expected: All tests PASS (including the 4 regression tests from Task 1).

- [ ] **Step 3: Commit**

```bash
git add web/tests/test_nmap.py
git commit -m "test(nmap): update imports to network_tasks + regression tests pass"
```

---

## Task 8: Full test suite smoke check

- [ ] **Step 1: Run the full test suite inside Docker**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -20"
```

Expected: All previously-passing tests still pass. Zero new failures.

- [ ] **Step 2: If failures exist, triage**

Any `ImportError` in tests → check that the re-export shim in `tasks.py` covers the symbol.
Any `AttributeError` on proxy/self → check that `_proxy_for` helper in the regression tests builds a complete-enough proxy object.

---

## Verification Checklist

After all tasks complete, verify these properties end-to-end:

1. **No cross-host vuln contamination**: Start a scan with 2+ subdomains, enable nmap. Confirm each `Vulnerability.subdomain` matches the host nmap found it on (query Django shell or DB).

2. **Per-host JSON files**: In `results_dir/`, confirm one `{host}_nmap.json` per scanned host, not a single shared file.

3. **self.filename unchanged**: Add a `logger.info('filename after nmap: %s', self.filename)` temporarily after the nmap loop in `port_scan`; confirm it still ends in `.txt` (or whatever it was before).

4. **IP dedup fires**: With two subdomains sharing an IP, confirm the Docker logs show `Skipping nmap for … — IP already scanned this run` for the second host.

5. **All tests pass**: `python3 manage.py test` inside the container returns 0 failures.
