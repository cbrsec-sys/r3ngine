# netdetect + urlparser Wiring Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire two remaining tools from WORKFLOWS.md into r3ngine Temporal activities and workflows — no Dockerfile changes needed, both use libraries/binaries already present in the container.

**Tool identification (verified in container):**
- `netdetect` → implemented in pure Python via `psutil` (already installed). Enumerates non-loopback IPv4 interfaces and computes their CIDR ranges. Used in `CIDRReconWorkflow` when no explicit CIDR target is supplied.
- `urlparser` → implemented via `unfurl` binary at `/usr/local/bin/unfurl` (already installed). Extracts unique query-string key=value pairs from a list of URLs. Used in `URLParamsFuzzWorkflow` (passive param harvest before arjun) and `URLCrawlWorkflow` (param harvest after active crawl).

**Architecture:** Each tool follows the standard r3ngine pattern: task function in `*_tasks.py` → `@activity.defn` in `temporal_activities.py` → `await workflow.execute_activity(...)` in workflow → registration in `run_temporal_orchestrator.py`.

**Tech Stack:** Python 3.12, Django 5.2.3, Temporal 1.6.0; `psutil` for netdetect; `subprocess` calling `unfurl` for urlparser.

---

## File Map

| File | Change |
|------|--------|
| `web/reNgine/recon_tasks.py` | Append `netdetect_scan` |
| `web/reNgine/crawl_tasks.py` | Append `urlparser_scan` |
| `web/reNgine/temporal_activities.py` | Append `RunNetDetectActivity`, `RunURLParserActivity` |
| `web/reNgine/temporal_workflows.py` | Extend `CIDRReconWorkflow`, `URLParamsFuzzWorkflow`, `URLCrawlWorkflow` |
| `web/scanEngine/management/commands/run_temporal_orchestrator.py` | Import + register both |
| `web/tests/test_recon_tasks.py` | Append `TestNetDetectScan` |
| `web/tests/test_crawl_tasks.py` | Append `TestURLParserScan` |

---

## Task 6: Wire `netdetect` — CIDR auto-discovery

**What it does:** Enumerates local network interfaces via `psutil.net_if_addrs()`, filters to non-loopback IPv4 addresses, and computes each interface's CIDR range. Returns a list of CIDR strings (e.g. `['172.20.0.0/16']`). In `CIDRReconWorkflow`, this runs first when `ctx['cidr']` is empty so subsequent steps have a target.

**Verified command equivalent** (tested in container):
```python
import psutil, ipaddress
for iface, addrs in psutil.net_if_addrs().items():
    if iface == 'lo': continue
    for addr in addrs:
        if addr.family == 2:
            net = ipaddress.IPv4Network(addr.address + '/' + addr.netmask, strict=False)
            # → '172.20.0.0/16'
```

**Files:**
- Modify: `web/reNgine/recon_tasks.py` — append after `getasn_scan`
- Modify: `web/reNgine/temporal_activities.py` — append after `run_getasn_activity`
- Modify: `web/reNgine/temporal_workflows.py` — `CIDRReconWorkflow.run()` preamble
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`
- Modify: `web/tests/test_recon_tasks.py` — append `TestNetDetectScan`

---

- [ ] **Step 6.1: Write failing tests**

Append to `web/tests/test_recon_tasks.py`:

```python
class TestNetDetectScan(TestCase):
    @patch('psutil.net_if_addrs')
    def test_netdetect_returns_cidr_for_non_loopback_interface(self, mock_addrs):
        import psutil as _psutil
        mock_addrs.return_value = {
            'lo': [
                _psutil._common.snicaddr(
                    family=2, address='127.0.0.1', netmask='255.0.0.0',
                    broadcast=None, ptp=None,
                ),
            ],
            'eth0': [
                _psutil._common.snicaddr(
                    family=2, address='10.0.0.5', netmask='255.255.0.0',
                    broadcast='10.0.255.255', ptp=None,
                ),
            ],
        }
        from reNgine.recon_tasks import netdetect_scan
        result = netdetect_scan(_make_proxy(), scan_history_id=1, domain_id=1)
        self.assertIsInstance(result, list)
        self.assertIn('10.0.0.0/16', result)
        self.assertNotIn('127.0.0.0/8', result)

    @patch('psutil.net_if_addrs')
    def test_netdetect_skips_loopback(self, mock_addrs):
        import psutil as _psutil
        mock_addrs.return_value = {
            'lo': [
                _psutil._common.snicaddr(
                    family=2, address='127.0.0.1', netmask='255.0.0.0',
                    broadcast=None, ptp=None,
                ),
            ],
        }
        from reNgine.recon_tasks import netdetect_scan
        result = netdetect_scan(_make_proxy(), scan_history_id=1, domain_id=1)
        self.assertEqual(result, [])

    @patch('psutil.net_if_addrs')
    def test_netdetect_handles_bad_netmask_gracefully(self, mock_addrs):
        import psutil as _psutil
        mock_addrs.return_value = {
            'eth0': [
                _psutil._common.snicaddr(
                    family=2, address='10.0.0.5', netmask=None,
                    broadcast=None, ptp=None,
                ),
            ],
        }
        from reNgine.recon_tasks import netdetect_scan
        result = netdetect_scan(_make_proxy(), scan_history_id=1, domain_id=1)
        self.assertEqual(result, [])
```

- [ ] **Step 6.2: Run — verify FAIL**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestNetDetectScan --keepdb --verbosity=2"
```
Expected: `ImportError: cannot import name 'netdetect_scan'`

- [ ] **Step 6.3: Add `netdetect_scan` to `web/reNgine/recon_tasks.py`**

Append after `getasn_scan`:

```python
def netdetect_scan(self, scan_history_id: int, domain_id: int) -> List[str]:
    """Detect local network CIDR ranges by enumerating network interfaces.

    Uses psutil to find non-loopback IPv4 interfaces and computes each
    interface's network CIDR. Returns a list of CIDR strings.
    Used in: CIDRReconWorkflow (auto-discover when no explicit target given).
    """
    import ipaddress
    import psutil

    cidrs: List[str] = []
    logger.log_line("[NETDETECT]", "START", "enumerating network interfaces")

    for iface, addrs in psutil.net_if_addrs().items():
        if iface == 'lo':
            continue
        for addr in addrs:
            if addr.family != 2:  # AF_INET only
                continue
            if not addr.netmask:
                continue
            try:
                net = ipaddress.IPv4Network(
                    '%s/%s' % (addr.address, addr.netmask), strict=False
                )
                if net.is_loopback:
                    continue
                cidr_str = str(net)
                cidrs.append(cidr_str)
                logger.log_line("[NETDETECT]", "FOUND", "iface=%s cidr=%s" % (iface, cidr_str))
            except ValueError:
                logger.log_line("[NETDETECT]", "WARN", "invalid addr on %s" % iface)

    logger.log_line("[NETDETECT]", "RESULT", "detected %d CIDR ranges" % len(cidrs))
    return cidrs
```

- [ ] **Step 6.4: Add `RunNetDetectActivity` to `temporal_activities.py`**

Append after `run_getasn_activity`:

```python
@activity.defn(name="RunNetDetectActivity")
def run_netdetect_activity(ctx: dict) -> list:
    from reNgine.recon_tasks import netdetect_scan
    activity.logger.info("[RunNetDetectActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(
        netdetect_scan, ctx, task_name='netdetect_scan',
        description='Network CIDR Detection (netdetect)',
    )
```

- [ ] **Step 6.5: Wire into `CIDRReconWorkflow`**

In `web/reNgine/temporal_workflows.py`, in `CIDRReconWorkflow.run()`, prepend CIDR auto-detection when no explicit cidr is provided. Replace the opening lines of `run()`:

```python
    @workflow.run
    async def run(self, ctx: dict) -> bool:
        cidr = ctx.get('cidr', '')
        yaml_config = ctx.get('yaml_configuration') or {}
        cidr_config = yaml_config.get('cidr_recon', {})
        use_arp = cidr_config.get('use_arp', False)

        # Auto-detect CIDR from local network interfaces when no target is given
        if not cidr:
            detected = await workflow.execute_activity(
                "RunNetDetectActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
            if not detected:
                return True
            cidr = detected[0]
            ctx = {**ctx, 'cidr': cidr}

        if use_arp:
            # ... rest of existing workflow unchanged
```

The remainder of the workflow body (the `if use_arp:` block through `return True`) stays exactly as it is.

- [ ] **Step 6.6: Register in `run_temporal_orchestrator.py`**

Add to Phase 1 imports:
```python
    run_netdetect_activity,
```
Add to `all_activities`:
```python
                run_netdetect_activity,
```

- [ ] **Step 6.7: Run tests — verify PASS**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_recon_tasks.TestNetDetectScan --keepdb --verbosity=2"
```
Expected: 3 tests PASS.

- [ ] **Step 6.8: Commit**

```bash
git add web/reNgine/recon_tasks.py web/reNgine/temporal_activities.py web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_recon_tasks.py
git commit -m "feat(tools): wire netdetect CIDR auto-discovery into CIDRReconWorkflow"
```

---

## Task 7: Wire `urlparser` — URL parameter extraction via `unfurl`

**What it does:** Takes a list of crawled URLs, writes them to a temp file, pipes through `unfurl -u keypairs` to extract unique `key=value` query-string pairs, then stores each as a `Parameter` record linked to the matching `EndPoint`. When no URL list is provided, loads from the scan's discovered endpoints.

**Verified command** (tested in container):
```bash
# Input: list of URLs, one per line, piped to unfurl
cat /tmp/urls.txt | unfurl -u keypairs
# Output: unique key=value pairs, one per line
# e.g.  foo=1
#       bar=2
```

**Parameter model:** `Parameter(endpoint=ep, name=str, value=str, type='GET')` — FK to `EndPoint` required.

**Files:**
- Modify: `web/reNgine/crawl_tasks.py` — append `urlparser_scan`
- Modify: `web/reNgine/temporal_activities.py` — append `RunURLParserActivity`
- Modify: `web/reNgine/temporal_workflows.py` — `URLParamsFuzzWorkflow`, `URLCrawlWorkflow`
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`
- Modify: `web/tests/test_crawl_tasks.py` — append `TestURLParserScan`

---

- [ ] **Step 7.1: Write failing tests**

Append to `web/tests/test_crawl_tasks.py` (check if file exists first; create the class at the end):

```python
class TestURLParserScan(TestCase):
    @patch('subprocess.run')
    def test_urlparser_saves_keypairs_as_parameters(self, mock_run):
        from startScan.models import ScanHistory, EndPoint, Parameter
        from targetApp.models import Domain as TargetDomain, Project
        from scanEngine.models import EngineType
        from reNgine.crawl_tasks import urlparser_scan

        project = Project.objects.create(name='up-proj', insert_date=timezone.now())
        domain = TargetDomain.objects.create(
            name='up-test.example.com', project=project, insert_date=timezone.now(),
        )
        engine = EngineType.objects.create(engine_name='up-engine', yaml_configuration='{}')
        scan = ScanHistory.objects.create(
            scan_status=0, start_scan_date=timezone.now(), domain=domain, scan_type=engine,
        )
        ep = EndPoint.objects.create(
            scan_history=scan,
            http_url='https://up-test.example.com/page?foo=1&bar=2',
        )

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='foo=1\nbar=2\n',
            stderr='',
        )
        result = urlparser_scan(
            _make_proxy(), scan_history_id=scan.id, domain_id=domain.id,
            urls=['https://up-test.example.com/page?foo=1&bar=2'],
        )
        self.assertTrue(result)
        params = Parameter.objects.filter(endpoint=ep)
        names = list(params.values_list('name', flat=True))
        self.assertIn('foo', names)
        self.assertIn('bar', names)

    @patch('subprocess.run')
    def test_urlparser_returns_true_with_no_urls(self, mock_run):
        from reNgine.crawl_tasks import urlparser_scan
        result = urlparser_scan(_make_proxy(), scan_history_id=1, domain_id=1, urls=[])
        self.assertTrue(result)
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_urlparser_handles_no_query_params(self, mock_run):
        from reNgine.crawl_tasks import urlparser_scan
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        result = urlparser_scan(
            _make_proxy(), scan_history_id=1, domain_id=1,
            urls=['https://example.com/page'],
        )
        self.assertTrue(result)

    @patch('subprocess.run')
    def test_urlparser_handles_timeout(self, mock_run):
        from reNgine.crawl_tasks import urlparser_scan
        mock_run.side_effect = __import__('subprocess').TimeoutExpired(cmd='unfurl', timeout=120)
        result = urlparser_scan(
            _make_proxy(), scan_history_id=1, domain_id=1,
            urls=['https://example.com/page?x=1'],
        )
        self.assertTrue(result)
```

**Note:** `test_crawl_tasks.py` already exists — check if it imports `timezone`, `MagicMock`, `patch`, and has a `_make_proxy()` helper. Add only what's missing; do not duplicate.

- [ ] **Step 7.2: Run — verify FAIL**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_crawl_tasks.TestURLParserScan --keepdb --verbosity=2"
```
Expected: `ImportError: cannot import name 'urlparser_scan'`

- [ ] **Step 7.3: Add `urlparser_scan` to `web/reNgine/crawl_tasks.py`**

First check the imports at the top of `crawl_tasks.py` — add `from typing import List, Optional` if not present.

Append at end of file:

```python
def urlparser_scan(self, scan_history_id: int, domain_id: int,
                   urls: Optional[List[str]] = None) -> bool:
    """Extract unique query-string parameters from URLs using unfurl.

    Pipes URLs through `unfurl -u keypairs` to get unique key=value pairs.
    Stores each pair as a Parameter record on the matching EndPoint.
    When urls is None/empty, loads discovered endpoints for the scan.
    Used in: URLParamsFuzzWorkflow, URLCrawlWorkflow.
    """
    import os
    from startScan.models import EndPoint, Parameter
    from django.db import transaction

    targets = urls or []
    if not targets and scan_history_id:
        targets = list(
            EndPoint.objects.filter(
                scan_history_id=scan_history_id
            ).values_list('http_url', flat=True)[:2000]
        )

    if not targets:
        logger.log_line("[URLPARSER]", "SKIP", "no URLs to parse")
        return True

    input_file = '/tmp/urlparser_input_%s.txt' % scan_history_id
    try:
        with open(input_file, 'w') as f:
            f.write('\n'.join(t for t in targets if t))

        with open(input_file, 'rb') as stdin_f:
            result = subprocess.run(
                ['unfurl', '-u', 'keypairs'],
                stdin=stdin_f,
                capture_output=True, text=True, timeout=120,
            )

        logger.log_line("[URLPARSER]", "START", "parsing %d URLs" % len(targets))

        # Build a lookup of base_url → EndPoint for fast matching
        ep_map = {
            ep.http_url: ep
            for ep in EndPoint.objects.filter(
                scan_history_id=scan_history_id,
                http_url__in=targets,
            )
        }

        params_to_create: List[Parameter] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            # Associate with any endpoint that has this param in its URL
            for url, ep in ep_map.items():
                if ('?' + key + '=') in url or ('&' + key + '=') in url:
                    if not Parameter.objects.filter(
                        endpoint=ep, name=key
                    ).exists():
                        params_to_create.append(
                            Parameter(
                                endpoint=ep,
                                name=key,
                                value=value,
                                type='GET',
                            )
                        )

        if params_to_create:
            with transaction.atomic():
                Parameter.objects.bulk_create(params_to_create, ignore_conflicts=True)
            logger.log_line("[URLPARSER]", "RESULT",
                            "saved %d parameters" % len(params_to_create))
        else:
            logger.log_line("[URLPARSER]", "RESULT", "no new parameters found")

    except subprocess.TimeoutExpired:
        logger.log_line("[URLPARSER]", "WARN", "unfurl timed out")
    finally:
        if os.path.exists(input_file):
            os.remove(input_file)

    return True
```

- [ ] **Step 7.4: Add `RunURLParserActivity` to `temporal_activities.py`**

Append after `run_netdetect_activity`:

```python
@activity.defn(name="RunURLParserActivity")
def run_urlparser_activity(ctx: dict) -> bool:
    from reNgine.crawl_tasks import urlparser_scan
    activity.logger.info("[RunURLParserActivity] scan_id=%s", ctx.get('scan_history_id'))
    return _run_task(
        urlparser_scan, ctx, task_name='urlparser_scan',
        description='URL Parameter Extraction (urlparser/unfurl)',
        urls=ctx.get('urls'),
    )
```

- [ ] **Step 7.5: Wire into `URLParamsFuzzWorkflow`**

In `temporal_workflows.py`, in `URLParamsFuzzWorkflow.run()`, add urlparser **before** the `RunArjunActivity` call (passive param harvest before active arjun probing):

```python
        # Passive parameter harvest from already-crawled URLs before active arjun probing
        await workflow.execute_activity(
            "RunURLParserActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=_RETRY_INTERNAL,
            task_queue="python-orchestrator-queue",
        )

        await workflow.execute_activity(
            "RunArjunActivity",
            # ... existing arjun call unchanged
```

- [ ] **Step 7.6: Wire into `URLCrawlWorkflow`**

In `URLCrawlWorkflow.run()`, add urlparser in the `hunt_secrets` block alongside the existing secret scan — after active crawl when `not passive_only`:

```python
            if hunt_secrets:
                await asyncio.gather(
                    workflow.execute_activity(
                        "RunSecretScanningActivity",
                        ctx,
                        start_to_close_timeout=timedelta(hours=1),
                        retry_policy=_RETRY_LONG_SCAN,
                        task_queue="python-orchestrator-queue",
                    ),
                    workflow.execute_activity(
                        "RunGenericTaskActivity",
                        {**ctx, 'task_name': 'maigret'},
                        start_to_close_timeout=timedelta(minutes=30),
                        retry_policy=_RETRY_NETWORK_SCAN,
                        task_queue="python-orchestrator-queue",
                    ),
                )

            # Extract URL parameters from all crawled endpoints
            await workflow.execute_activity(
                "RunURLParserActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
```

This runs unconditionally after active crawl, regardless of `hunt_secrets`.

- [ ] **Step 7.7: Register in `run_temporal_orchestrator.py`**

Add to Phase 1 imports:
```python
    run_urlparser_activity,
```
Add to `all_activities`:
```python
                run_urlparser_activity,
```

- [ ] **Step 7.8: Run tests — verify PASS**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_crawl_tasks.TestURLParserScan --keepdb --verbosity=2"
```
Expected: 4 tests PASS.

- [ ] **Step 7.9: Commit**

```bash
git add web/reNgine/crawl_tasks.py web/reNgine/temporal_activities.py web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_crawl_tasks.py
git commit -m "feat(tools): wire urlparser (unfurl) parameter extraction into URLParamsFuzz + URLCrawl workflows"
```

---

## Task 8: Final regression run

- [ ] **Step 8.1: Run full test suite**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --keepdb 2>&1 | tail -5"
```
Expected: all tests pass, no regressions.
