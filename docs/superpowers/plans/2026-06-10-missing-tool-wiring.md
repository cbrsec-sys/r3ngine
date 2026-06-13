# Missing Tool Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire 6 security tools into r3ngine Temporal activities and appropriate workflows to reach rengine-ng v3 tool parity — 4 tools are already installed in the Dockerfile but have no task function or activity; 2 tools need Dockerfile installs before wiring. Three tools (netdetect, urlparser, msfconsole) are deferred at the end of this document with justification.

**Architecture:** Every tool follows the established r3ngine pattern:
1. Task function in `reNgine/*_tasks.py` — subprocess execution + DB persistence via `TemporalTaskProxy` interface (`self` argument)
2. `@activity.defn` in `temporal_activities.py` — thin wrapper calling `_run_task()`
3. `await workflow.execute_activity(...)` in the target workflow
4. Import + registration in `run_temporal_orchestrator.py` `all_activities` list

**Tech Stack:** Python 3.12, Django 5.2.3, Temporal 1.6.0, PostgreSQL; `subprocess.run` for tool calls; `save_vulnerability()` from `common_func` for CVE findings.

---

## File Map

| File | Action |
|------|--------|
| `web/startScan/models.py` | Add `asn`, `asn_org`, `asn_cidr` to `IpAddress` |
| `web/targetApp/models.py` | Add `whois_raw` JSONField to `DomainInfo` |
| `web/reNgine/recon_tasks.py` | Add `getasn_scan`, `jswhois_scan`, `whoisdomain_scan`, `bbot_scan` |
| `web/reNgine/vulnerability_tasks.py` | Add `grype_scan`, `trivy_scan` |
| `web/reNgine/temporal_activities.py` | Add 7 new `@activity.defn` wrappers |
| `web/reNgine/temporal_workflows.py` | Extend `DomainReconWorkflow`, `HostReconWorkflow`, `SubdomainReconWorkflow`, `CodeScanWorkflow` |
| `web/scanEngine/management/commands/run_temporal_orchestrator.py` | Import + register 7 new activities |
| `docker/web/Dockerfile` | Install `grype` and `trivy` binaries |
| `web/tests/test_recon_tasks.py` | Append `TestGetASNScan`, `TestJsWhoisScan`, `TestWhoisDomainScan`, `TestBBotScan` |
| `web/tests/test_vulnerability_tasks.py` | **New file** — `TestGrypeScan`, `TestTrivyScan` |

---

## Task 1: Wire `getasn` — ASN enrichment for discovered IPs

**What it does:** `getasn` maps IP addresses to their ASN number, CIDR range, and owning organization. In rengine-ng it runs post-port-scan to enrich host intelligence. r3ngine wires it into `DomainReconWorkflow` (runs after initial discovery) and `HostReconWorkflow` (runs after port scan).

**Tool CLI:** `getasn -ip 172.217.14.196`
**Expected output** (one line, space-delimited):
```
172.217.14.196 AS15169 172.217.0.0/16 GOOGLE - Google LLC US
```
Fields: `<IP> <ASN> <CIDR> <Org...> <Country>`

**Files:**
- Modify: `web/startScan/models.py` — `IpAddress` class (~line 804)
- Modify: `web/reNgine/recon_tasks.py` — append after `arpscan_scan`
- Modify: `web/reNgine/temporal_activities.py` — append at end of Phase 1 section (~line 2620)
- Modify: `web/reNgine/temporal_workflows.py` — `DomainReconWorkflow` (~line 2252), `HostReconWorkflow` (~line 2110)
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py` — imports (~line 173) + `all_activities` (~line 461)
- Modify: `web/tests/test_recon_tasks.py` — append class

---

- [ ] **Step 1.1: Write failing tests**

Append to `web/tests/test_recon_tasks.py`:

```python
from django.utils import timezone


class TestGetASNScan(TestCase):
    @patch('subprocess.run')
    def test_getasn_updates_ip_address_asn_fields(self, mock_run):
        from startScan.models import IpAddress, ScanHistory
        from targetApp.models import Domain as TargetDomain, Project
        from reNgine.recon_tasks import getasn_scan

        project = Project.objects.create(name='test-asn-proj', insert_date=timezone.now())
        domain = TargetDomain.objects.create(
            name='asn-test.example.com', project=project, insert_date=timezone.now(),
        )
        scan = ScanHistory.objects.create(
            scan_status=0, start_scan_date=timezone.now(), domain=domain,
        )
        ip = IpAddress.objects.create(address='172.217.14.196')

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='172.217.14.196 AS15169 172.217.0.0/16 GOOGLE - Google LLC US\n',
            stderr='',
        )
        result = getasn_scan(_make_proxy(), scan_history_id=scan.id, domain_id=domain.id,
                             ips=['172.217.14.196'])
        self.assertTrue(result)
        ip.refresh_from_db()
        self.assertEqual(ip.asn, 'AS15169')
        self.assertEqual(ip.asn_cidr, '172.217.0.0/16')
        self.assertIn('GOOGLE', ip.asn_org)

    @patch('subprocess.run')
    def test_getasn_returns_true_with_no_ips(self, mock_run):
        from reNgine.recon_tasks import getasn_scan
        result = getasn_scan(_make_proxy(), scan_history_id=1, domain_id=1, ips=[])
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_getasn_handles_malformed_output(self, mock_run):
        from reNgine.recon_tasks import getasn_scan
        mock_run.return_value = MagicMock(returncode=0, stdout='bad output\n', stderr='')
        result = getasn_scan(_make_proxy(), scan_history_id=1, domain_id=1, ips=['1.2.3.4'])
        self.assertTrue(result)
```

- [ ] **Step 1.2: Run — verify FAIL**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestGetASNScan --verbosity=2"
```
Expected: `AttributeError: type object 'IpAddress' has no attribute 'asn'`

- [ ] **Step 1.3: Add ASN fields to `IpAddress` model**

In `web/startScan/models.py`, in the `IpAddress` class, after the `reverse_pointer` field (~line 813):

```python
    asn = models.CharField(max_length=20, blank=True, null=True)
    asn_cidr = models.CharField(max_length=50, blank=True, null=True)
    asn_org = models.CharField(max_length=200, blank=True, null=True)
```

- [ ] **Step 1.4: Generate and apply migration**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py makemigrations startScan --name ipaddress_asn_fields && python3 manage.py migrate"
```

- [ ] **Step 1.5: Add `getasn_scan` to `web/reNgine/recon_tasks.py`**

Append after the `arpscan_scan` function:

```python
def getasn_scan(self, scan_history_id: int, domain_id: int, ips: List[str] = None) -> bool:
    """Enrich discovered IPs with ASN number, CIDR, and organization using getasn.

    Calls `getasn -ip <addr>` per IP and stores the result on IpAddress records.
    Used in: DomainReconWorkflow, HostReconWorkflow.
    """
    from startScan.models import IpAddress

    targets = ips or []
    if not targets:
        logger.log_line("[GETASN]", "SKIP", "no IPs to enrich")
        return True

    logger.log_line("[GETASN]", "START", "enriching %d IPs" % len(targets))
    enriched = 0

    for ip_addr in targets:
        try:
            result = subprocess.run(
                ['getasn', '-ip', ip_addr],
                capture_output=True, text=True, timeout=30,
            )
            line = result.stdout.strip()
            if not line:
                continue
            parts = line.split()
            # Expected: <IP> <ASN> <CIDR> <Org...> <Country>
            if len(parts) >= 3:
                asn = parts[1]
                asn_cidr = parts[2]
                asn_org = ' '.join(parts[3:]) if len(parts) > 3 else ''
                updated = IpAddress.objects.filter(address=ip_addr).update(
                    asn=asn[:20],
                    asn_cidr=asn_cidr[:50],
                    asn_org=asn_org[:200],
                )
                if updated:
                    enriched += 1
        except subprocess.TimeoutExpired:
            logger.log_line("[GETASN]", "WARN", "timeout for %s" % ip_addr)
        except Exception as exc:
            logger.log_line("[GETASN]", "ERROR", "failed for %s: %s" % (ip_addr, exc))

    logger.log_line("[GETASN]", "RESULT", "enriched %d/%d IPs" % (enriched, len(targets)))
    return True
```

- [ ] **Step 1.6: Add `GetDiscoveredIPsActivity` and `RunGetASNActivity` to `temporal_activities.py`**

Append after `run_bup_activity` (~line 2620):

```python
@activity.defn(name="GetDiscoveredIPsActivity")
def get_discovered_ips_activity(ctx: dict) -> list:
    """Return distinct IP address strings discovered for this scan."""
    from startScan.models import IpAddress
    scan_id = ctx.get('scan_history_id')
    if not scan_id:
        return []
    ips = (
        IpAddress.objects
        .filter(ip_addresses__scan_history_id=scan_id)
        .values_list('address', flat=True)
        .distinct()
    )
    return list(ips)


@activity.defn(name="RunGetASNActivity")
def run_getasn_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import getasn_scan
    activity.logger.info("[RunGetASNActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(
        getasn_scan, ctx, task_name='getasn_scan',
        description='ASN Enrichment (getasn)', ips=ctx.get('ips', []),
    )
```

- [ ] **Step 1.7: Wire into `DomainReconWorkflow`**

In `web/reNgine/temporal_workflows.py`, in `DomainReconWorkflow.run()`, replace `return True` with:

```python
        # Enrich discovered IPs with ASN data after initial discovery
        discovered_ips = await workflow.execute_activity(
            "GetDiscoveredIPsActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue",
        )
        if discovered_ips:
            await workflow.execute_activity(
                "RunGetASNActivity",
                {**ctx, 'ips': discovered_ips},
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )
        return True
```

- [ ] **Step 1.8: Wire into `HostReconWorkflow`**

In `HostReconWorkflow.run()`, after the `asyncio.gather(RunHTTPCrawlActivity, RunSSHAuditActivity)` block and before `if run_nuclei:`:

```python
        # Enrich host IP with ASN data
        host_ip = ctx.get('host') or ctx.get('domain_name') or ctx.get('domain')
        if host_ip:
            await workflow.execute_activity(
                "RunGetASNActivity",
                {**ctx, 'ips': [host_ip]},
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )
```

- [ ] **Step 1.9: Register in `run_temporal_orchestrator.py`**

In the Phase 1 imports block (~line 173), add:
```python
    get_discovered_ips_activity,
    run_getasn_activity,
```

In `all_activities` list (~line 461), add:
```python
                get_discovered_ips_activity,
                run_getasn_activity,
```

- [ ] **Step 1.10: Run tests — verify PASS**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestGetASNScan --verbosity=2"
```
Expected: 3 tests PASS.

- [ ] **Step 1.11: Commit**

```bash
git add web/startScan/models.py web/startScan/migrations/ web/reNgine/recon_tasks.py web/reNgine/temporal_activities.py web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_recon_tasks.py
git commit -m "feat(tools): wire getasn ASN enrichment into DomainRecon + HostRecon workflows"
```

---

## Task 2: Wire `jswhois` + `whoisdomain` — supplemental WHOIS enrichment

**What they do:**
- `jswhois` (Go binary): outputs standard WHOIS response as JSON for a domain. Supplements the existing internal `query_whois()` with a direct binary call that requires no external API key.
- `whoisdomain` (Python/pipx): WHOIS library CLI outputting structured JSON. Captures registrar, dates, name-servers that may differ from the Netlas-backed `query_whois`.

Both write to a new `whois_raw` JSONField on `DomainInfo`, letting the UI show all WHOIS sources side-by-side without altering the existing `query_whois` path.

**Tool CLIs:**
- `jswhois -j example.com` → JSON object (WHOIS fields as keys)
- `whoisdomain -d example.com -o /tmp/out.json` → JSON file

**Files:**
- Modify: `web/targetApp/models.py` — `DomainInfo` class (~line 79)
- Modify: `web/reNgine/recon_tasks.py` — append `jswhois_scan`, `whoisdomain_scan`
- Modify: `web/reNgine/temporal_activities.py` — append `RunJsWhoisActivity`, `RunWhoisDomainActivity`
- Modify: `web/reNgine/temporal_workflows.py` — `DomainReconWorkflow` first `asyncio.gather`
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`
- Modify: `web/tests/test_recon_tasks.py` — append `TestJsWhoisScan`, `TestWhoisDomainScan`

---

- [ ] **Step 2.1: Write failing tests**

Append to `web/tests/test_recon_tasks.py`:

```python
class TestJsWhoisScan(TestCase):
    @patch('subprocess.run')
    def test_jswhois_stores_raw_json_in_domain_info(self, mock_run):
        from targetApp.models import Domain as TargetDomain, DomainInfo, Project
        from startScan.models import ScanHistory
        from reNgine.recon_tasks import jswhois_scan

        project = Project.objects.create(name='test-jswhois-proj', insert_date=timezone.now())
        domain_info = DomainInfo.objects.create()
        domain = TargetDomain.objects.create(
            name='jswhois-test.example.com', project=project,
            insert_date=timezone.now(), domain_info=domain_info,
        )
        scan = ScanHistory.objects.create(
            scan_status=0, start_scan_date=timezone.now(), domain=domain,
        )
        whois_json = '{"registrar": "ACME Registrar", "creation_date": "2000-01-01"}'
        mock_run.return_value = MagicMock(returncode=0, stdout=whois_json, stderr='')

        result = jswhois_scan(_make_proxy(), scan_history_id=scan.id, domain_id=domain.id,
                              domain='jswhois-test.example.com')
        self.assertTrue(result)
        domain_info.refresh_from_db()
        self.assertIsNotNone(domain_info.whois_raw)
        self.assertIn('registrar', domain_info.whois_raw)

    @patch('subprocess.run')
    def test_jswhois_returns_true_with_no_domain(self, mock_run):
        from reNgine.recon_tasks import jswhois_scan
        result = jswhois_scan(_make_proxy(), scan_history_id=1, domain_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()


class TestWhoisDomainScan(TestCase):
    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', create=True)
    def test_whoisdomain_stores_raw_json(self, mock_open, mock_exists, mock_run):
        from targetApp.models import Domain as TargetDomain, DomainInfo, Project
        from startScan.models import ScanHistory
        from reNgine.recon_tasks import whoisdomain_scan
        import json as _json

        project = Project.objects.create(name='test-wd-proj', insert_date=timezone.now())
        domain_info = DomainInfo.objects.create()
        domain = TargetDomain.objects.create(
            name='wd-test.example.com', project=project,
            insert_date=timezone.now(), domain_info=domain_info,
        )
        scan = ScanHistory.objects.create(
            scan_status=0, start_scan_date=timezone.now(), domain=domain,
        )
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        mock_open.return_value.__enter__.return_value.read.return_value = _json.dumps(
            {'registrar': 'Test Registrar', 'expiration_date': '2030-01-01'}
        )

        result = whoisdomain_scan(_make_proxy(), scan_history_id=scan.id, domain_id=domain.id,
                                  domain='wd-test.example.com')
        self.assertTrue(result)
        domain_info.refresh_from_db()
        self.assertIsNotNone(domain_info.whois_raw)

    @patch('subprocess.run')
    def test_whoisdomain_returns_true_with_no_domain(self, mock_run):
        from reNgine.recon_tasks import whoisdomain_scan
        result = whoisdomain_scan(_make_proxy(), scan_history_id=1, domain_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()
```

- [ ] **Step 2.2: Run — verify FAIL**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestJsWhoisScan tests.test_recon_tasks.TestWhoisDomainScan --verbosity=2"
```
Expected: `AttributeError: type object 'DomainInfo' has no attribute 'whois_raw'`

- [ ] **Step 2.3: Add `whois_raw` JSONField to `DomainInfo`**

In `web/targetApp/models.py`, in the `DomainInfo` class, after the `whois_server` field (~line 120):

```python
    whois_raw = models.JSONField(null=True, blank=True)
```

- [ ] **Step 2.4: Generate and apply migration**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py makemigrations targetApp --name domaininfo_whois_raw && python3 manage.py migrate"
```

- [ ] **Step 2.5: Add `jswhois_scan` and `whoisdomain_scan` to `web/reNgine/recon_tasks.py`**

Append after `getasn_scan`:

```python
def jswhois_scan(self, scan_history_id: int, domain_id: int, domain: str = None) -> bool:
    """Fetch WHOIS data as JSON using the jswhois Go binary.

    Stores raw JSON in DomainInfo.whois_raw for the target domain.
    Does not overwrite existing query_whois results.
    Used in: DomainReconWorkflow.
    """
    from targetApp.models import Domain

    target = domain or ''
    if not target:
        logger.log_line("[JSWHOIS]", "SKIP", "no domain provided")
        return True

    cmd = ['jswhois', '-j', target]
    logger.log_line("[JSWHOIS]", "START", "querying %s" % target)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        raw = result.stdout.strip()
        if not raw:
            return True
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.log_line("[JSWHOIS]", "WARN", "non-JSON output for %s" % target)
            return True

        domain_obj = Domain.objects.filter(pk=domain_id).first()
        if domain_obj and domain_obj.domain_info:
            domain_obj.domain_info.whois_raw = data
            domain_obj.domain_info.save(update_fields=['whois_raw'])
            logger.log_line("[JSWHOIS]", "RESULT", "stored whois_raw for %s" % target)
    except subprocess.TimeoutExpired:
        logger.log_line("[JSWHOIS]", "WARN", "timeout for %s" % target)

    return True


def whoisdomain_scan(self, scan_history_id: int, domain_id: int, domain: str = None) -> bool:
    """Fetch WHOIS data using the whoisdomain Python CLI.

    Writes JSON output to a temp file, reads it, and stores in DomainInfo.whois_raw.
    Used in: DomainReconWorkflow.
    """
    import os
    from targetApp.models import Domain

    target = domain or ''
    if not target:
        logger.log_line("[WHOISDOMAIN]", "SKIP", "no domain provided")
        return True

    output_file = f'/tmp/whoisdomain_{scan_history_id}.json'
    cmd = ['whoisdomain', '-d', target, '-o', output_file]
    logger.log_line("[WHOISDOMAIN]", "START", "querying %s" % target)

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if not os.path.exists(output_file):
            return True
        with open(output_file) as f:
            raw = f.read().strip()
        if not raw:
            return True
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return True

        domain_obj = Domain.objects.filter(pk=domain_id).first()
        if domain_obj and domain_obj.domain_info:
            domain_obj.domain_info.whois_raw = data
            domain_obj.domain_info.save(update_fields=['whois_raw'])
            logger.log_line("[WHOISDOMAIN]", "RESULT", "stored whois_raw for %s" % target)
    except subprocess.TimeoutExpired:
        logger.log_line("[WHOISDOMAIN]", "WARN", "timeout for %s" % target)
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)

    return True
```

- [ ] **Step 2.6: Add activities to `temporal_activities.py`**

Append after `run_getasn_activity`:

```python
@activity.defn(name="RunJsWhoisActivity")
def run_jswhois_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import jswhois_scan
    activity.logger.info("[RunJsWhoisActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(
        jswhois_scan, ctx, task_name='jswhois_scan',
        description='WHOIS Lookup (jswhois)', domain=ctx.get('domain'),
    )


@activity.defn(name="RunWhoisDomainActivity")
def run_whoisdomain_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import whoisdomain_scan
    activity.logger.info("[RunWhoisDomainActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(
        whoisdomain_scan, ctx, task_name='whoisdomain_scan',
        description='WHOIS Lookup (whoisdomain)', domain=ctx.get('domain'),
    )
```

- [ ] **Step 2.7: Wire into `DomainReconWorkflow`**

In `temporal_workflows.py`, in `DomainReconWorkflow.run()`, extend the first `asyncio.gather(...)` to include both WHOIS activities alongside the existing `whois` generic task:

```python
        await asyncio.gather(
            workflow.execute_activity(
                "RunGenericTaskActivity",
                {**ctx, 'task_name': 'whois'},
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunJsWhoisActivity",
                {**ctx, 'domain': ctx.get('domain')},
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunWhoisDomainActivity",
                {**ctx, 'domain': ctx.get('domain')},
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunDNSXActivity",
                {**ctx, 'subdomain': ctx.get('domain')},
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunXURLFind3rActivity",
                {**ctx, 'domain': ctx.get('domain')},
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            ),
        )
```

- [ ] **Step 2.8: Register in `run_temporal_orchestrator.py`**

Add to Phase 1 imports:
```python
    run_jswhois_activity,
    run_whoisdomain_activity,
```

Add to `all_activities`:
```python
                run_jswhois_activity,
                run_whoisdomain_activity,
```

- [ ] **Step 2.9: Run tests — verify PASS**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestJsWhoisScan tests.test_recon_tasks.TestWhoisDomainScan --verbosity=2"
```
Expected: 4 tests PASS.

- [ ] **Step 2.10: Commit**

```bash
git add web/targetApp/models.py web/targetApp/migrations/ web/reNgine/recon_tasks.py web/reNgine/temporal_activities.py web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_recon_tasks.py
git commit -m "feat(tools): wire jswhois + whoisdomain WHOIS enrichment into DomainReconWorkflow"
```

---

## Task 3: Wire `bbot` — OSINT subdomain + email discovery

**What it does:** BBOT (Bit Bounce OSINT Tool) is a modular passive OSINT framework. In rengine-ng, it augments subdomain discovery via passive DNS, web archives, and certificate transparency. r3ngine wires it into `SubdomainReconWorkflow` as an additional discovery source alongside `subfinder`.

**Output format:** NDJSON events (`--output-type ndjson`). Only `DNS_NAME` type events are relevant — their `data` field contains discovered hostnames.

**Tool CLI:**
```
bbot -t example.com -p subdomain-enum --silent --no-deps \
     -o /tmp/bbot_out -om ndjson
```
Output file: `/tmp/bbot_out/output.ndjson`

Each line: `{"type": "DNS_NAME", "data": "sub.example.com", ...}`

**Files:**
- Modify: `web/reNgine/recon_tasks.py` — append `bbot_scan`
- Modify: `web/reNgine/temporal_activities.py` — append `RunBBotActivity`
- Modify: `web/reNgine/temporal_workflows.py` — `SubdomainReconWorkflow` discovery tasks
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`
- Modify: `web/tests/test_recon_tasks.py` — append `TestBBotScan`

---

- [ ] **Step 3.1: Write failing tests**

Append to `web/tests/test_recon_tasks.py`:

```python
class TestBBotScan(TestCase):
    @patch('subprocess.run')
    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', create=True)
    def test_bbot_saves_dns_name_events_as_subdomains(self, mock_open, mock_exists, mock_run):
        import json as _json
        from startScan.models import ScanHistory, Subdomain
        from targetApp.models import Domain as TargetDomain, Project
        from reNgine.recon_tasks import bbot_scan

        project = Project.objects.create(name='test-bbot-proj', insert_date=timezone.now())
        domain = TargetDomain.objects.create(
            name='bbot-test.example.com', project=project, insert_date=timezone.now(),
        )
        scan = ScanHistory.objects.create(
            scan_status=0, start_scan_date=timezone.now(), domain=domain,
        )
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        events = [
            _json.dumps({'type': 'DNS_NAME', 'data': 'api.bbot-test.example.com'}),
            _json.dumps({'type': 'DNS_NAME', 'data': 'mail.bbot-test.example.com'}),
            _json.dumps({'type': 'OPEN_TCP_PORT', 'data': '1.2.3.4:80'}),  # should be ignored
        ]
        mock_open.return_value.__enter__.return_value.__iter__ = lambda s: iter(events)

        result = bbot_scan(_make_proxy(), scan_history_id=scan.id, domain_id=domain.id,
                           domain='bbot-test.example.com')
        self.assertTrue(result)
        names = list(Subdomain.objects.filter(
            scan_history_id=scan.id
        ).values_list('name', flat=True))
        self.assertIn('api.bbot-test.example.com', names)
        self.assertIn('mail.bbot-test.example.com', names)

    @patch('subprocess.run')
    def test_bbot_returns_true_with_no_domain(self, mock_run):
        from reNgine.recon_tasks import bbot_scan
        result = bbot_scan(_make_proxy(), scan_history_id=1, domain_id=1)
        self.assertTrue(result)
        mock_run.assert_not_called()
```

- [ ] **Step 3.2: Run — verify FAIL**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestBBotScan --verbosity=2"
```
Expected: `ImportError: cannot import name 'bbot_scan'`

- [ ] **Step 3.3: Add `bbot_scan` to `web/reNgine/recon_tasks.py`**

Append after `whoisdomain_scan`:

```python
def bbot_scan(self, scan_history_id: int, domain_id: int, domain: str = None) -> bool:
    """Discover subdomains and hostnames using BBOT passive OSINT modules.

    Runs the bbot subdomain-enum preset and parses DNS_NAME events from NDJSON
    output. Discovered names are upserted as Subdomain records.
    Used in: SubdomainReconWorkflow.
    """
    import os
    import shutil
    from startScan.models import Subdomain
    from targetApp.models import Domain
    from django.db import transaction

    target = domain or ''
    if not target:
        logger.log_line("[BBOT]", "SKIP", "no domain provided")
        return True

    output_dir = f'/tmp/bbot_{scan_history_id}'
    output_file = f'{output_dir}/output.ndjson'

    try:
        cmd = [
            'bbot', '-t', target,
            '-p', 'subdomain-enum',
            '--silent', '--no-deps',
            '-o', output_dir,
            '-om', 'ndjson',
        ]
        logger.log_line("[BBOT]", "START", "scanning %s" % target)
        subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if not os.path.exists(output_file):
            logger.log_line("[BBOT]", "WARN", "no output produced for %s" % target)
            return True

        try:
            domain_obj = Domain.objects.get(pk=domain_id)
        except Domain.DoesNotExist:
            domain_obj = None

        new_names: List[str] = []
        with open(output_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get('type') == 'DNS_NAME':
                    name = event.get('data', '').strip()
                    if name and not Subdomain.objects.filter(
                        scan_history_id=scan_history_id, name=name
                    ).exists():
                        new_names.append(name)

        if new_names:
            with transaction.atomic():
                Subdomain.objects.bulk_create(
                    [Subdomain(scan_history_id=scan_history_id,
                               target_domain=domain_obj, name=n)
                     for n in new_names],
                    ignore_conflicts=True,
                )
            logger.log_line("[BBOT]", "RESULT", "saved %d new subdomains" % len(new_names))

    except subprocess.TimeoutExpired:
        logger.log_line("[BBOT]", "WARN", "bbot timed out for %s" % target)
    finally:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)

    return True
```

- [ ] **Step 3.4: Add `RunBBotActivity` to `temporal_activities.py`**

Append after `run_whoisdomain_activity`:

```python
@activity.defn(name="RunBBotActivity")
def run_bbot_activity(ctx: dict) -> bool:
    from reNgine.recon_tasks import bbot_scan
    activity.logger.info("[RunBBotActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(
        bbot_scan, ctx, task_name='bbot_scan',
        description='OSINT Discovery (bbot)', domain=ctx.get('domain'),
    )
```

- [ ] **Step 3.5: Wire into `SubdomainReconWorkflow`**

In `temporal_workflows.py`, in `SubdomainReconWorkflow.run()`, add bbot to the `discovery_tasks` list (it runs in parallel with subfinder, gated by YAML config):

Replace the `discovery_tasks = [...]` block with:

```python
        yaml_config = ctx.get('yaml_configuration') or {}
        subdomain_config = yaml_config.get('subdomain_recon', {})
        passive_only = subdomain_config.get('passive', False)
        brute_dns = subdomain_config.get('brute_dns', False)
        run_bbot = subdomain_config.get('bbot', False)

        discovery_tasks = [
            workflow.execute_activity(
                "RunSubdomainDiscoveryActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunFetchURLActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            ),
        ]
        if brute_dns and not passive_only:
            discovery_tasks.append(
                workflow.execute_activity(
                    "RunDNSXActivity",
                    {**ctx, 'wordlist': 'combined_subdomains'},
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue",
                )
            )
        if run_bbot:
            discovery_tasks.append(
                workflow.execute_activity(
                    "RunBBotActivity",
                    {**ctx, 'domain': ctx.get('domain')},
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue",
                )
            )
        await asyncio.gather(*discovery_tasks)
```

**Note:** The existing `passive_only` and `brute_dns` variable declarations at the top of the original `run` method must be removed when applying this replacement to avoid duplicate declarations.

- [ ] **Step 3.6: Register in `run_temporal_orchestrator.py`**

Add to Phase 1 imports:
```python
    run_bbot_activity,
```

Add to `all_activities`:
```python
                run_bbot_activity,
```

- [ ] **Step 3.7: Run tests — verify PASS**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestBBotScan --verbosity=2"
```
Expected: 2 tests PASS.

- [ ] **Step 3.8: Commit**

```bash
git add web/reNgine/recon_tasks.py web/reNgine/temporal_activities.py web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_recon_tasks.py
git commit -m "feat(tools): wire bbot OSINT discovery into SubdomainReconWorkflow"
```

---

## Task 4: Install + wire `grype` + `trivy` — code vulnerability scanning

**What they do:**
- `grype`: Anchore's vulnerability scanner. Scans a filesystem directory for known CVEs in installed packages. Outputs JSON with `matches[]` each containing a `vulnerability.id`, `vulnerability.severity`, and `artifact.name`.
- `trivy`: Aqua Security's scanner. Scans filesystem, containers, and IaC. Outputs JSON with `Results[]` → `Vulnerabilities[]` containing `VulnerabilityID`, `Severity`, `Title`, `Description`.

Both run in `CodeScanWorkflow` against the `starting_point_path` (a local code directory target).

**Dockerfile install locations:** Append to the pipx section (~line 484) in `docker/web/Dockerfile`:
```dockerfile
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin
RUN curl -sSfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin latest
```

**Tool CLIs:**
- `grype dir:/path/to/code -o json --quiet`
- `trivy fs /path/to/code --format json --quiet`

**Files:**
- Modify: `docker/web/Dockerfile` — add 2 install `RUN` lines
- Modify: `web/reNgine/vulnerability_tasks.py` — append `grype_scan`, `trivy_scan`
- Modify: `web/reNgine/temporal_activities.py` — append `RunGrypeScanActivity`, `RunTrivyScanActivity`
- Modify: `web/reNgine/temporal_workflows.py` — `CodeScanWorkflow` gather
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`
- Create: `web/tests/test_vulnerability_tasks.py`

---

- [ ] **Step 4.1: Write failing tests**

Create `web/tests/test_vulnerability_tasks.py`:

```python
"""Tests for web/reNgine/vulnerability_tasks.py — grype and trivy."""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.utils import timezone


def _make_proxy(yaml_config=None, starting_point_path='/tmp/test-code'):
    proxy = MagicMock()
    proxy.yaml_configuration = yaml_config or {}
    proxy.starting_point_path = starting_point_path
    proxy.scan = None
    proxy.domain = None
    return proxy


class TestGrypeScan(TestCase):
    @patch('subprocess.run')
    def test_grype_saves_matches_as_vulnerabilities(self, mock_run):
        from startScan.models import ScanHistory, Vulnerability
        from targetApp.models import Domain as TargetDomain, Project
        from reNgine.vulnerability_tasks import grype_scan

        project = Project.objects.create(name='test-grype-proj', insert_date=timezone.now())
        domain = TargetDomain.objects.create(
            name='grype-test.example.com', project=project, insert_date=timezone.now(),
        )
        scan = ScanHistory.objects.create(
            scan_status=0, start_scan_date=timezone.now(), domain=domain,
        )
        grype_output = json.dumps({
            'matches': [
                {
                    'vulnerability': {
                        'id': 'CVE-2021-44228',
                        'severity': 'Critical',
                        'description': 'Log4Shell RCE',
                        'fix': {'versions': ['2.17.0']},
                    },
                    'artifact': {'name': 'log4j-core', 'version': '2.14.1'},
                }
            ]
        })
        mock_run.return_value = MagicMock(returncode=0, stdout=grype_output, stderr='')
        proxy = _make_proxy(starting_point_path='/tmp/test-code')
        proxy.scan = scan
        proxy.domain = domain

        result = grype_scan(proxy, scan_history_id=scan.id, domain_id=domain.id,
                            code_path='/tmp/test-code')
        self.assertTrue(result)
        self.assertTrue(
            Vulnerability.objects.filter(
                scan_history=scan, name__icontains='CVE-2021-44228'
            ).exists()
        )

    @patch('subprocess.run')
    def test_grype_returns_true_with_empty_matches(self, mock_run):
        from reNgine.vulnerability_tasks import grype_scan
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({'matches': []}), stderr=''
        )
        result = grype_scan(_make_proxy(), scan_history_id=1, domain_id=1, code_path='/tmp')
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_grype_handles_non_json_output(self, mock_run):
        from reNgine.vulnerability_tasks import grype_scan
        mock_run.return_value = MagicMock(returncode=1, stdout='error text', stderr='')
        result = grype_scan(_make_proxy(), scan_history_id=1, domain_id=1, code_path='/tmp')
        self.assertTrue(result)


class TestTrivyScan(TestCase):
    @patch('subprocess.run')
    def test_trivy_saves_vulnerabilities(self, mock_run):
        from startScan.models import ScanHistory, Vulnerability
        from targetApp.models import Domain as TargetDomain, Project
        from reNgine.vulnerability_tasks import trivy_scan

        project = Project.objects.create(name='test-trivy-proj', insert_date=timezone.now())
        domain = TargetDomain.objects.create(
            name='trivy-test.example.com', project=project, insert_date=timezone.now(),
        )
        scan = ScanHistory.objects.create(
            scan_status=0, start_scan_date=timezone.now(), domain=domain,
        )
        trivy_output = json.dumps({
            'Results': [
                {
                    'Target': 'requirements.txt',
                    'Vulnerabilities': [
                        {
                            'VulnerabilityID': 'CVE-2022-42969',
                            'Severity': 'HIGH',
                            'Title': 'Sensitive data exposure in py lib',
                            'Description': 'py before 1.11.0 allows ...',
                            'InstalledVersion': '1.10.0',
                            'FixedVersion': '1.11.0',
                        }
                    ],
                }
            ]
        })
        mock_run.return_value = MagicMock(returncode=0, stdout=trivy_output, stderr='')
        proxy = _make_proxy(starting_point_path='/tmp/test-code')
        proxy.scan = scan
        proxy.domain = domain

        result = trivy_scan(proxy, scan_history_id=scan.id, domain_id=domain.id,
                            code_path='/tmp/test-code')
        self.assertTrue(result)
        self.assertTrue(
            Vulnerability.objects.filter(
                scan_history=scan, name__icontains='CVE-2022-42969'
            ).exists()
        )

    @patch('subprocess.run')
    def test_trivy_returns_true_with_no_results(self, mock_run):
        from reNgine.vulnerability_tasks import trivy_scan
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({'Results': []}), stderr=''
        )
        result = trivy_scan(_make_proxy(), scan_history_id=1, domain_id=1, code_path='/tmp')
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_trivy_handles_non_json_output(self, mock_run):
        from reNgine.vulnerability_tasks import trivy_scan
        mock_run.return_value = MagicMock(returncode=1, stdout='trivy error', stderr='')
        result = trivy_scan(_make_proxy(), scan_history_id=1, domain_id=1, code_path='/tmp')
        self.assertTrue(result)
```

- [ ] **Step 4.2: Run — verify FAIL**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_vulnerability_tasks --verbosity=2"
```
Expected: `ImportError: cannot import name 'grype_scan' from 'reNgine.vulnerability_tasks'`

- [ ] **Step 4.3: Add `grype_scan` and `trivy_scan` to `web/reNgine/vulnerability_tasks.py`**

Append at end of file:

```python
_SEVERITY_MAP = {
    'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'negligible': 0, 'unknown': 0,
}


def grype_scan(self, scan_history_id: int, domain_id: int, code_path: str = None) -> bool:
    """Scan a code directory for known CVEs using Anchore Grype.

    Runs `grype dir:<path> -o json --quiet` and saves each match as a Vulnerability
    record. Severity is mapped from grype's string labels (Critical/High/Medium/Low).
    Used in: CodeScanWorkflow.
    """
    import subprocess
    from reNgine.common_func import save_vulnerability

    path = code_path or getattr(self, 'starting_point_path', None) or '/tmp/code'
    logger.info("[grype] scanning %s", path)

    try:
        result = subprocess.run(
            ['grype', f'dir:{path}', '-o', 'json', '--quiet'],
            capture_output=True, text=True, timeout=600,
        )
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
        logger.warning("[grype] failed: %s", exc)
        return True

    matches = data.get('matches', [])
    scan_obj = getattr(self, 'scan', None)
    domain_obj = getattr(self, 'domain', None)

    for match in matches:
        vuln = match.get('vulnerability', {})
        artifact = match.get('artifact', {})
        cve_id = vuln.get('id', 'Unknown')
        sev_str = vuln.get('severity', 'unknown').lower()
        sev = _SEVERITY_MAP.get(sev_str, 0)
        description = vuln.get('description', '')
        fix_versions = vuln.get('fix', {}).get('versions', [])
        remediation = ('Upgrade to: ' + ', '.join(fix_versions)) if fix_versions else ''
        pkg_name = artifact.get('name', '')
        pkg_version = artifact.get('version', '')

        save_vulnerability(
            name=cve_id,
            severity=sev,
            description='%s — %s %s\n%s' % (cve_id, pkg_name, pkg_version, description),
            remediation=remediation,
            source='grype',
            scan_history=scan_obj,
            target_domain=domain_obj,
        )

    logger.info("[grype] saved %d findings", len(matches))
    return True


def trivy_scan(self, scan_history_id: int, domain_id: int, code_path: str = None) -> bool:
    """Scan a code directory for known CVEs using Aqua Trivy.

    Runs `trivy fs <path> --format json --quiet` and saves each Vulnerability
    record. Severity is mapped from Trivy's string labels (CRITICAL/HIGH/MEDIUM/LOW).
    Used in: CodeScanWorkflow.
    """
    import subprocess
    from reNgine.common_func import save_vulnerability

    path = code_path or getattr(self, 'starting_point_path', None) or '/tmp/code'
    logger.info("[trivy] scanning %s", path)

    try:
        result = subprocess.run(
            ['trivy', 'fs', path, '--format', 'json', '--quiet'],
            capture_output=True, text=True, timeout=600,
        )
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
        logger.warning("[trivy] failed: %s", exc)
        return True

    scan_obj = getattr(self, 'scan', None)
    domain_obj = getattr(self, 'domain', None)
    count = 0

    for result_group in data.get('Results', []):
        for vuln in result_group.get('Vulnerabilities') or []:
            cve_id = vuln.get('VulnerabilityID', 'Unknown')
            sev_str = vuln.get('Severity', 'UNKNOWN').lower()
            sev = _SEVERITY_MAP.get(sev_str, 0)
            title = vuln.get('Title', cve_id)
            desc = vuln.get('Description', '')
            fixed = vuln.get('FixedVersion', '')
            installed = vuln.get('InstalledVersion', '')
            remediation = ('Upgrade to %s' % fixed) if fixed else ''

            save_vulnerability(
                name=cve_id,
                severity=sev,
                description='%s (%s → %s)\n%s\n%s' % (title, installed, fixed, cve_id, desc),
                remediation=remediation,
                source='trivy',
                scan_history=scan_obj,
                target_domain=domain_obj,
            )
            count += 1

    logger.info("[trivy] saved %d findings", count)
    return True
```

- [ ] **Step 4.4: Add activities to `temporal_activities.py`**

Append after `run_bbot_activity`:

```python
@activity.defn(name="RunGrypeScanActivity")
def run_grype_scan_activity(ctx: dict) -> bool:
    from reNgine.vulnerability_tasks import grype_scan
    activity.logger.info("[RunGrypeScanActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(
        grype_scan, ctx, task_name='grype_scan',
        description='CVE Scan (grype)', code_path=ctx.get('starting_point_path'),
    )


@activity.defn(name="RunTrivyScanActivity")
def run_trivy_scan_activity(ctx: dict) -> bool:
    from reNgine.vulnerability_tasks import trivy_scan
    activity.logger.info("[RunTrivyScanActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(
        trivy_scan, ctx, task_name='trivy_scan',
        description='Security Scan (trivy)', code_path=ctx.get('starting_point_path'),
    )
```

- [ ] **Step 4.5: Extend `CodeScanWorkflow` in `temporal_workflows.py`**

Replace the existing `CodeScanWorkflow.run()` gather with:

```python
    @workflow.run
    async def run(self, ctx: dict) -> bool:
        await asyncio.gather(
            workflow.execute_activity(
                "RunGenericTaskActivity",
                {**ctx, 'task_name': 'gitleaks_scan'},
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunSecretScanningActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunSemgrepActivity",
                {**ctx, 'mode': 'vulnerability'},
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunGrypeScanActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunTrivyScanActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            ),
        )
        return True
```

- [ ] **Step 4.6: Register in `run_temporal_orchestrator.py`**

Add to Phase 1 imports:
```python
    run_grype_scan_activity,
    run_trivy_scan_activity,
```

Add to `all_activities`:
```python
                run_grype_scan_activity,
                run_trivy_scan_activity,
```

- [ ] **Step 4.7: Add Dockerfile installs for grype + trivy**

In `docker/web/Dockerfile`, append two `RUN` lines after the pipx block (~line 470):

```dockerfile
# grype — Anchore filesystem CVE scanner
RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# trivy — Aqua Security filesystem + container scanner
RUN curl -sSfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin latest
```

- [ ] **Step 4.8: Run tests — verify PASS**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_vulnerability_tasks --verbosity=2"
```
Expected: 6 tests PASS.

- [ ] **Step 4.9: Commit**

```bash
git add docker/web/Dockerfile web/reNgine/vulnerability_tasks.py web/reNgine/temporal_activities.py web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_vulnerability_tasks.py
git commit -m "feat(tools): install + wire grype and trivy CVE scanning into CodeScanWorkflow"
```

---

## Task 5: Full regression run

After all four coding tasks are committed, run the full test suite to confirm no regressions.

- [ ] **Step 5.1: Run full suite**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=2 2>&1 | tail -20"
```
Expected: All existing tests pass plus the ~13 new tests added in Tasks 1–4.

- [ ] **Step 5.2: Rebuild Docker image and smoke-test tool binaries**

```bash
docker compose build web
docker exec -it r3ngine-web-1 bash -c "getasn -h && jswhois --help && whoisdomain --help && bbot --help && grype version && trivy --version"
```
Expected: All 6 tools print help/version without errors.

---

## Deferred Items

### `netdetect` — tool identity unclear

**Status:** Not in Dockerfile. Before implementation can proceed, the exact tool must be confirmed.

The name "netdetect" does not map to a widely-known single binary. Candidates include:
- `NetDetect` by Vulnpire (github.com/Vulnpire/NetDetect) — network service OS fingerprinting
- Some other internal tool

**Action required before implementing:**
1. Confirm the exact GitHub repo and install command.
2. Run `netdetect --help` to understand CLI and output format.
3. Determine where output is stored (service_name on `Port`? new field on `IpAddress`?).

Once confirmed, the pattern mirrors `getasn_scan`: add to Dockerfile, write task in `recon_tasks.py`, add `RunNetDetectActivity`, wire into `CIDRReconWorkflow` and `HostReconWorkflow`.

---

### `urlparser` — utility, not a standalone workflow step

**Status:** Not in Dockerfile. Role in r3ngine context is unclear from the tool list alone.

`urlparser` is likely used to normalize and extract components (scheme, host, path, params) from discovered URLs. In rengine-ng it may be called inline within crawl tasks, not as a standalone Temporal activity.

**Action required before implementing:**
1. Confirm whether rengine-ng runs urlparser as a standalone step or as a library import within other tasks.
2. If standalone: install binary, add task + activity, wire into `URLCrawlWorkflow` after discovery.
3. If library: integrate into existing crawl task functions in `crawl_tasks.py` without a new activity.

---

### `msfconsole` — requires architectural decision

**Status:** Not in Dockerfile. This is Metasploit Framework and warrants a separate conversation before any implementation.

Key concerns:
- Docker image size: metasploit-framework adds ~600 MB+ to the build.
- Database dependency: MSF requires a PostgreSQL database; it must not conflict with r3ngine's app database.
- Security boundary: Exploitation tooling running inside the same container as the web app is a critical isolation risk.
- Operational scope: MSF is not a scanner — it is an exploitation framework. Wiring it as a Temporal activity requires very careful scoping (which modules run, against which targets, with what safeguards).

**Recommendation:** Implement msfconsole as a dedicated sidecar container (`msf-worker`) that exposes an RPC interface (`msfrpc`), with r3ngine calling it via a Go executor activity over a local socket. This isolates blast radius, avoids image bloat, and lets MSF maintain its own DB connection. Discuss architecture before building.
