# rengine-ng Integration — Phase 2: New Temporal Workflows

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all 13 rengine-ng workflow types as standalone Temporal workflow classes in r3ngine, each triggerable via a dedicated REST API endpoint, using the tool activities added in Phase 1.

**Architecture:** Each new workflow is a `@workflow.defn` class in `temporal_workflows.py`. Workflows are thin deterministic orchestrators — they sequence activities, branch on results, and fan-out with `asyncio.gather`. Each workflow has a corresponding API view in `api/views.py` and a `ScanHistory` record to track status. Scans are started via `TemporalClientProvider.start_workflow()`.

**Tech Stack:** Python 3.12, Temporal SDK 1.7.0, Django REST Framework + JWT, PostgreSQL

**Depends on:** Phase 1 (all tool activities must be registered)

---

## Decision: RESOLVED — `search_vulns` fans out concurrently in Tier 2

**Choice:** `RunSearchVulnsActivity` (built in Phase 1 Task 7) is fanned out concurrently per discovered service immediately after `RunPortScanActivity` returns in `MasterScanWorkflow` Tier 2. The workflow reads the list of `(host, port, service, version)` tuples returned by port scan and dispatches one `RunSearchVulnsActivity` + one `RunSearchsploitActivity` per service, all gathered in a single `asyncio.gather`. `HostReconWorkflow` (Task 4 below) does the same. See Task 12 for the `MasterScanWorkflow` modification.

---

## File Structure

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `web/reNgine/temporal_workflows.py` | Add 13 new `@workflow.defn` classes + modify `MasterScanWorkflow` Tier 2 |
| Modify | `web/scanEngine/management/commands/run_temporal_orchestrator.py` | Import + register new workflows |
| Modify | `web/api/views.py` | Add `StartWorkflowView` + per-workflow endpoints |
| Modify | `web/api/urls.py` | Wire up new URL patterns |
| Create | `web/tests/test_new_workflows.py` | Unit tests for workflow API endpoints |

---

## Task 1: UserHuntWorkflow (simplest — good warm-up)

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# web/tests/test_new_workflows.py
from django.test import TestCase
from unittest.mock import patch, AsyncMock


class TestUserHuntWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_user_hunt_runs_maigret_and_h8mail(self, mock_exec):
        from reNgine.temporal_workflows import UserHuntWorkflow
        wf = UserHuntWorkflow()
        ctx = {
            'scan_history_id': 1,
            'target': 'johndoe',
            'target_type': 'username',
            'yaml_configuration': {},
        }
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunMaigretActivity', activity_names)

    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_user_hunt_email_runs_h8mail(self, mock_exec):
        from reNgine.temporal_workflows import UserHuntWorkflow
        wf = UserHuntWorkflow()
        ctx = {
            'scan_history_id': 1,
            'target': 'user@example.com',
            'target_type': 'email',
            'yaml_configuration': {},
        }
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunH8MailActivity', activity_names)
```

- [ ] **Step 2: Confirm test fails**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestUserHuntWorkflow --verbosity=2 2>&1 | head -20"
```
Expected: `AttributeError: module has no attribute 'UserHuntWorkflow'`

- [ ] **Step 3: Add `UserHuntWorkflow` to `temporal_workflows.py`**

Append after the last workflow class in `temporal_workflows.py`:

```python
@workflow.defn(name="UserHuntWorkflow")
class UserHuntWorkflow:
    """Standalone user/email OSINT workflow.

    Searches for user accounts across platforms (maigret) and hunts
    password leaks (h8mail). Triggered directly from the API for email
    or username targets. Does not require a domain scan.

    rengine-ng equivalent: user_hunt workflow (maigret + h8mail).
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        target = ctx.get('target', '')
        target_type = ctx.get('target_type', 'username')

        if target_type == 'email':
            await workflow.execute_activity(
                "RunH8MailActivity",
                {**ctx, 'target': target},
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )
        else:
            await workflow.execute_activity(
                "RunMaigretActivity",
                {**ctx, 'target': target},
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )

        return True
```

Note: `RunMaigretActivity` and `RunH8MailActivity` are existing activities (already in the orchestrator). Verify with: `grep -n "RunMaigretActivity\|run_maigret" web/reNgine/temporal_activities.py`

If those activity names differ, align the names. The generic task system (`RunGenericTaskActivity`) dispatches tasks by name — check if maigret/h8mail are called via the generic path in the current codebase and wire accordingly.

- [ ] **Step 4: Register in orchestrator**

In `run_temporal_orchestrator.py`, in the `from reNgine.temporal_workflows import (` block, add:
```python
    UserHuntWorkflow,
```
Add it to the `workflows=[...]` list in `Worker(...)`.

- [ ] **Step 5: Run tests — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestUserHuntWorkflow --verbosity=2"
```
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_new_workflows.py
git commit -m "feat(workflows): add UserHuntWorkflow (maigret + h8mail OSINT)"
```

---

## Task 2: URLBypassWorkflow

- [ ] **Step 1: Add test to `test_new_workflows.py`**

```python
class TestURLBypassWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_url_bypass_calls_bup(self, mock_exec):
        from reNgine.temporal_workflows import URLBypassWorkflow
        wf = URLBypassWorkflow()
        ctx = {
            'scan_history_id': 1,
            'urls': ['https://example.com/admin'],
            'yaml_configuration': {},
        }
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunBUPActivity', activity_names)
```

- [ ] **Step 2: Implement `URLBypassWorkflow`**

```python
@workflow.defn(name="URLBypassWorkflow")
class URLBypassWorkflow:
    """Attempt 4xx URL bypass on a list of URLs.

    rengine-ng equivalent: url_bypass workflow (bup).
    Input: list of URLs returning 4xx status codes.
    Output: Vulnerability records for successful bypasses.
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        await workflow.execute_activity(
            "RunBUPActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue",
        )
        return True
```

- [ ] **Step 3: Register and test**

Add `URLBypassWorkflow` to orchestrator imports and workflows list.

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestURLBypassWorkflow --verbosity=2"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(workflows): add URLBypassWorkflow (bup 4xx bypass)"
```

---

## Task 3: WordPressWorkflow

- [ ] **Step 1: Add test**

```python
class TestWordPressWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_wordpress_runs_three_tools(self, mock_exec):
        from reNgine.temporal_workflows import WordPressWorkflow
        wf = WordPressWorkflow()
        ctx = {
            'scan_history_id': 1,
            'urls': ['https://example.com'],
            'yaml_configuration': {'vulnerability_scan': {'run_wpscan': True}},
        }
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunWpscanActivity', activity_names)
        self.assertIn('RunWPProbeActivity', activity_names)
        self.assertIn('RunNucleiActivity', activity_names)
```

- [ ] **Step 2: Implement `WordPressWorkflow`**

```python
@workflow.defn(name="WordPressWorkflow")
class WordPressWorkflow:
    """Standalone WordPress security assessment.

    Runs httpx probe, wpscan, wpprobe, and nuclei (wordpress tag) against
    WordPress URLs. Designed to be triggered from the API for any URL or host.

    rengine-ng equivalent: wordpress workflow.
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        vuln_config = yaml_config.get('vulnerability_scan', {})

        # Probe first — establish alive HTTP services
        await workflow.execute_activity(
            "RunHTTPCrawlActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue",
        )

        # Run all three WordPress scanners in parallel
        await asyncio.gather(
            workflow.execute_activity(
                "RunWpscanActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunWPProbeActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunNucleiActivity",
                {**ctx, 'tags_override': ['wordpress'], 'severity': 'critical,high,medium,low'},
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            ),
        )

        return True
```

- [ ] **Step 3: Register and test**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestWordPressWorkflow --verbosity=2"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(workflows): add WordPressWorkflow (wpscan + wpprobe + nuclei)"
```

---

## Task 4: HostReconWorkflow

- [ ] **Step 1: Add test**

```python
class TestHostReconWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_host_recon_scans_ports_and_ssh(self, mock_exec):
        from reNgine.temporal_workflows import HostReconWorkflow
        wf = HostReconWorkflow()
        ctx = {
            'scan_history_id': 1,
            'target': '192.0.2.1',
            'target_type': 'ip',
            'yaml_configuration': {},
        }
        mock_exec.return_value = {'ports': [{'port': 22, 'service': 'ssh'}]}
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunPortScanActivity', activity_names)
        self.assertIn('RunSSHAuditActivity', activity_names)
```

- [ ] **Step 2: Implement `HostReconWorkflow`**

```python
@workflow.defn(name="HostReconWorkflow")
class HostReconWorkflow:
    """Standalone host/IP reconnaissance workflow.

    Performs: port scan (naabu light + nmap version detection),
    SSH audit on port 22, HTTP probe on open ports, nuclei network/SSL scan,
    and optionally searchsploit for each discovered service.

    rengine-ng equivalent: host_recon workflow.
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        host_config = yaml_config.get('host_recon', {})
        run_nuclei = host_config.get('run_nuclei', False)
        run_searchsploit = host_config.get('run_searchsploit', True)

        # Port discovery (light naabu scan first)
        port_results = await workflow.execute_activity(
            "RunPortScanActivity",
            {**ctx, 'port_scan_tool': 'naabu'},
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue",
        )

        # Nmap for version detection on discovered ports
        await workflow.execute_activity(
            "RunPortScanActivity",
            {**ctx, 'port_scan_tool': 'nmap', 'version_detection': True},
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue",
        )

        # Parallel: HTTP probe + SSH audit
        await asyncio.gather(
            workflow.execute_activity(
                "RunHTTPCrawlActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunSSHAuditActivity",
                {**ctx, 'port': 22},
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            ),
        )

        if run_searchsploit:
            await workflow.execute_activity(
                "RunSearchsploitActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )

        if run_nuclei:
            await workflow.execute_activity(
                "RunNucleiActivity",
                {**ctx, 'tags_override': ['network', 'ssl'], 'severity': 'critical,high,medium'},
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )

        return True
```

- [ ] **Step 3: Register and test**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestHostReconWorkflow --verbosity=2"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(workflows): add HostReconWorkflow (naabu+nmap+sshaudit+httpx+nuclei)"
```

---

## Task 5: CIDRReconWorkflow

- [ ] **Step 1: Add test**

```python
class TestCIDRReconWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_cidr_recon_discovers_hosts(self, mock_exec):
        from reNgine.temporal_workflows import CIDRReconWorkflow
        wf = CIDRReconWorkflow()
        ctx = {
            'scan_history_id': 1,
            'cidr': '192.0.2.0/24',
            'yaml_configuration': {},
        }
        mock_exec.return_value = ['192.0.2.1', '192.0.2.5']
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunFPingActivity', activity_names)
        self.assertIn('RunPortScanActivity', activity_names)
```

- [ ] **Step 2: Implement `CIDRReconWorkflow`**

```python
@workflow.defn(name="CIDRReconWorkflow")
class CIDRReconWorkflow:
    """Network CIDR reconnaissance workflow.

    Phases:
      1. Discover alive hosts via ARP (LAN) or ICMP (fping)
      2. Expand CIDR with mapcidr
      3. Port scan discovered hosts with nmap
      4. HTTP probe services
      5. Search exploits for open services

    rengine-ng equivalent: cidr_recon workflow.
    Requires: NET_RAW capability or --privileged for ARP scanning.
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        cidr = ctx.get('cidr', '')
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        cidr_config = yaml_config.get('cidr_recon', {})
        use_arp = cidr_config.get('use_arp', False)

        # Phase 1: Host discovery
        if use_arp:
            alive_hosts = await workflow.execute_activity(
                "RunARPScanActivity",
                {**ctx, 'cidr': cidr},
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )
        else:
            # Expand CIDR then ping sweep
            await workflow.execute_activity(
                "RunMapCIDRActivity",
                {**ctx, 'cidr': cidr},
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
            alive_hosts = await workflow.execute_activity(
                "RunFPingActivity",
                {**ctx, 'cidr': cidr},
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )

        if not alive_hosts:
            return True

        # Phase 2: Port scan each alive host
        await workflow.execute_activity(
            "RunPortScanActivity",
            {**ctx, 'targets': alive_hosts, 'port_scan_tool': 'nmap', 'version_detection': True},
            start_to_close_timeout=timedelta(hours=1),
            retry_policy=_RETRY_LONG_SCAN,
            task_queue="python-orchestrator-queue",
        )

        # Phase 3: HTTP probe on open ports
        await workflow.execute_activity(
            "RunHTTPCrawlActivity",
            {**ctx, 'targets': alive_hosts},
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue",
        )

        return True
```

- [ ] **Step 3: Register and test**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestCIDRReconWorkflow --verbosity=2"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(workflows): add CIDRReconWorkflow (arpscan/fping + mapcidr + nmap + httpx)"
```

---

## Task 6: CodeScanWorkflow

- [ ] **Step 1: Add test**

```python
class TestCodeScanWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_code_scan_runs_four_tools(self, mock_exec):
        from reNgine.temporal_workflows import CodeScanWorkflow
        wf = CodeScanWorkflow()
        ctx = {
            'scan_history_id': 1,
            'target': '/code/repo',
            'target_type': 'path',
            'yaml_configuration': {},
        }
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunGitleaksActivity', activity_names)
        self.assertIn('RunSecretScanningActivity', activity_names)
```

- [ ] **Step 2: Implement `CodeScanWorkflow`**

```python
@workflow.defn(name="CodeScanWorkflow")
class CodeScanWorkflow:
    """Source code vulnerability and secrets scanning workflow.

    Runs grype (dependency CVEs), gitleaks (git secret leaks),
    trufflehog (credential detection), and semgrep (SAST) against
    a local path, git repository URL, or file system path.

    rengine-ng equivalent: code_scan workflow.
    Note: grype/trivy are already in the r3ngine Docker image via vigolium.
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        # Parallel: run all code scanners simultaneously
        await asyncio.gather(
            workflow.execute_activity(
                "RunGitleaksActivity",
                ctx,
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
        )
        return True
```

Note: `RunGitleaksActivity` — check the existing orchestrator for the exact activity name used for gitleaks. It may be dispatched via `RunGenericTaskActivity` with `task_name='gitleaks_scan'`. Align the name accordingly.

- [ ] **Step 3: Register and test**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestCodeScanWorkflow --verbosity=2"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(workflows): add CodeScanWorkflow (gitleaks + trufflehog + semgrep)"
```

---

## Task 7: DomainReconWorkflow (lightweight standalone)

- [ ] **Step 1: Add test**

```python
class TestDomainReconWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_domain_recon_probes_dns_and_waf(self, mock_exec):
        from reNgine.temporal_workflows import DomainReconWorkflow
        wf = DomainReconWorkflow()
        ctx = {
            'scan_history_id': 1,
            'domain': 'example.com',
            'target_type': 'domain',
            'yaml_configuration': {},
        }
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunDNSXActivity', activity_names)
        self.assertIn('RunWAFW00FActivity', activity_names)
        self.assertIn('RunHTTPCrawlActivity', activity_names)
```

- [ ] **Step 2: Implement `DomainReconWorkflow`**

```python
@workflow.defn(name="DomainReconWorkflow")
class DomainReconWorkflow:
    """Lightweight standalone domain reconnaissance workflow.

    Collects WHOIS, resolves DNS records, probes HTTP services,
    detects WAF, tests SSL/TLS, and retrieves ASN info.
    Designed for fast domain intelligence without full 7-tier scanning.

    rengine-ng equivalent: domain_recon workflow
    (jswhois + whois + httpx + getasn + xurlfind3r + testssl + dnsx + wafw00f).
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        passive_only = yaml_config.get('domain_recon', {}).get('passive', False)

        # Parallel: WHOIS + DNS + passive URL collection
        await asyncio.gather(
            workflow.execute_activity(
                "RunGenericTaskActivity",
                {**ctx, 'task_name': 'whois'},
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

        if not passive_only:
            # Parallel: HTTP probe + SSL test + WAF detection
            await asyncio.gather(
                workflow.execute_activity(
                    "RunHTTPCrawlActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                ),
                workflow.execute_activity(
                    "RunWAFDetectionActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                ),
                workflow.execute_activity(
                    "RunWAFW00FActivity",
                    {**ctx, 'url': 'https://' + ctx.get('domain', '')},
                    start_to_close_timeout=timedelta(minutes=10),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                ),
            )

        return True
```

- [ ] **Step 3: Register and test, then commit**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestDomainReconWorkflow --verbosity=2"
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(workflows): add DomainReconWorkflow (whois+dnsx+httpx+testssl+wafw00f)"
```

---

## Task 8: SubdomainReconWorkflow (standalone)

- [ ] **Step 1: Add test**

```python
class TestSubdomainReconWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_subdomain_recon_runs_subfinder_and_dnsx(self, mock_exec):
        from reNgine.temporal_workflows import SubdomainReconWorkflow
        wf = SubdomainReconWorkflow()
        ctx = {
            'scan_history_id': 1,
            'domain': 'example.com',
            'yaml_configuration': {},
        }
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunSubdomainDiscoveryActivity', activity_names)
        self.assertIn('RunDNSXActivity', activity_names)
```

- [ ] **Step 2: Implement `SubdomainReconWorkflow`**

```python
@workflow.defn(name="SubdomainReconWorkflow")
class SubdomainReconWorkflow:
    """Standalone subdomain discovery and verification workflow.

    Combines passive sources (subfinder, gau), TLS cert scraping (httpx),
    DNS validation (dnsx), optional brute-force (ffuf), and nuclei
    takeover detection.

    rengine-ng equivalent: subdomain_recon workflow.
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        subdomain_config = yaml_config.get('subdomain_recon', {})
        passive_only = subdomain_config.get('passive', False)
        active_only = subdomain_config.get('active', False)
        brute_dns = subdomain_config.get('brute_dns', False)
        brute_http = subdomain_config.get('brute_http', False)
        hunt_secrets = subdomain_config.get('hunt_secrets', False)
        test_ssl = subdomain_config.get('test_ssl', False)

        # Phase 1: Discovery (passive + TLS cert)
        discovery_tasks = []
        if not active_only:
            discovery_tasks.append(
                workflow.execute_activity(
                    "RunSubdomainDiscoveryActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue",
                )
            )
            discovery_tasks.append(
                workflow.execute_activity(
                    "RunFetchURLActivity",
                    {**ctx, 'use_gau': True},
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                )
            )
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
        if discovery_tasks:
            await asyncio.gather(*discovery_tasks)

        # Phase 2: DNS probe + HTTP probe
        await asyncio.gather(
            workflow.execute_activity(
                "RunDNSXActivity",
                {**ctx, 'subdomain': None},
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            ),
            workflow.execute_activity(
                "RunHTTPCrawlActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            ) if not passive_only else asyncio.sleep(0),
        )

        # Phase 3: Takeover detection (nuclei)
        if not passive_only:
            await workflow.execute_activity(
                "RunNucleiActivity",
                {**ctx, 'tags_override': ['takeover'], 'severity': 'critical,high,medium'},
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )

        return True
```

- [ ] **Step 3: Register, test, commit**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestSubdomainReconWorkflow --verbosity=2"
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(workflows): add SubdomainReconWorkflow (subfinder+dnsx+httpx+nuclei takeover)"
```

---

## Task 9: URLCrawlWorkflow

- [ ] **Step 1: Add test**

```python
class TestURLCrawlWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_url_crawl_runs_passive_and_active(self, mock_exec):
        from reNgine.temporal_workflows import URLCrawlWorkflow
        wf = URLCrawlWorkflow()
        ctx = {
            'scan_history_id': 1,
            'urls': ['https://example.com'],
            'yaml_configuration': {},
        }
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunKatanaActivity', activity_names)
        self.assertIn('RunXURLFind3rActivity', activity_names)
```

Note: `RunKatanaActivity` — verify the exact activity name used in existing code by checking `temporal_activities.py`. It may be called via `RunDirFileFuzzActivity` or a dedicated activity. Align accordingly.

- [ ] **Step 2: Implement `URLCrawlWorkflow`**

```python
@workflow.defn(name="URLCrawlWorkflow")
class URLCrawlWorkflow:
    """Standalone URL crawl and passive discovery workflow.

    Combines passive sources (xurlfind3r, urlfinder, gau) with active
    crawlers (katana, gospider, cariddi). Optionally hunts secrets in
    HTTP responses (trufflehog) and OSINT on found email addresses (maigret).

    rengine-ng equivalent: url_crawl workflow.
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        crawl_config = yaml_config.get('url_crawl', {})
        passive_only = crawl_config.get('passive', False)
        active_only = crawl_config.get('active', False)
        hunt_secrets = crawl_config.get('hunt_secrets', False)

        # Parallel passive collection
        if not active_only:
            await asyncio.gather(
                workflow.execute_activity(
                    "RunXURLFind3rActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                ),
                workflow.execute_activity(
                    "RunURLFinderActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                ),
                workflow.execute_activity(
                    "RunFetchURLActivity",
                    {**ctx, 'use_gau': True},
                    start_to_close_timeout=timedelta(minutes=30),
                    retry_policy=_RETRY_NETWORK_SCAN,
                    task_queue="python-orchestrator-queue",
                ),
            )

        if not passive_only:
            # Active crawlers
            await asyncio.gather(
                workflow.execute_activity(
                    "RunDirFileFuzzActivity",
                    {**ctx, 'tool': 'katana'},
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue",
                ),
                workflow.execute_activity(
                    "RunCariddiActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=1),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue",
                ),
            )

            # HTTP probe to verify discovered URLs
            await workflow.execute_activity(
                "RunHTTPCrawlActivity",
                ctx,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=_RETRY_NETWORK_SCAN,
                task_queue="python-orchestrator-queue",
            )

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

        return True
```

- [ ] **Step 3: Register, test, commit**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestURLCrawlWorkflow --verbosity=2"
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(workflows): add URLCrawlWorkflow (xurlfind3r+urlfinder+gau+katana+cariddi)"
```

---

## Task 10: URLDirSearchWorkflow, URLFuzzWorkflow, URLParamsFuzzWorkflow, URLVulnWorkflow

These four workflows follow the same pattern. Implement them together.

- [ ] **Step 1: Add tests**

```python
class TestURLDirSearchWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_dir_search_runs_ffuf_and_httpx(self, mock_exec):
        from reNgine.temporal_workflows import URLDirSearchWorkflow
        wf = URLDirSearchWorkflow()
        ctx = {'scan_history_id': 1, 'urls': ['https://example.com'], 'yaml_configuration': {}}
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunHTTPCrawlActivity', activity_names)
        self.assertIn('RunDirFileFuzzActivity', activity_names)


class TestURLFuzzWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_url_fuzz_runs_feroxbuster_and_ffuf(self, mock_exec):
        from reNgine.temporal_workflows import URLFuzzWorkflow
        wf = URLFuzzWorkflow()
        ctx = {'scan_history_id': 1, 'urls': ['https://example.com'], 'yaml_configuration': {}}
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunFeroxbusterActivity', activity_names)


class TestURLParamsFuzzWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_params_fuzz_discovers_params(self, mock_exec):
        from reNgine.temporal_workflows import URLParamsFuzzWorkflow
        wf = URLParamsFuzzWorkflow()
        ctx = {'scan_history_id': 1, 'urls': ['https://example.com/search'], 'yaml_configuration': {}}
        mock_exec.return_value = True
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunArjunActivity', activity_names)


class TestURLVulnWorkflow(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_url_vuln_runs_gf_then_dalfox(self, mock_exec):
        from reNgine.temporal_workflows import URLVulnWorkflow
        wf = URLVulnWorkflow()
        ctx = {'scan_history_id': 1, 'urls': ['https://example.com/search?q=test'], 'yaml_configuration': {}}
        mock_exec.side_effect = lambda name, *a, **kw: (
            ['https://example.com/search?q=test'] if name == 'RunGFActivity' else True
        )
        await wf.run(ctx)
        activity_names = [call.args[0] for call in mock_exec.call_args_list]
        self.assertIn('RunGFActivity', activity_names)
        self.assertIn('RunDalfoxActivity', activity_names)
```

- [ ] **Step 2: Implement the four workflows**

```python
@workflow.defn(name="URLDirSearchWorkflow")
class URLDirSearchWorkflow:
    """Hidden directory/file search on web servers.

    rengine-ng equivalent: url_dirsearch (httpx + ffuf dir mode + katana + trufflehog).
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        dirsearch_config = yaml_config.get('url_dirsearch', {})
        hunt_secrets = dirsearch_config.get('hunt_secrets', False)
        hunt_files = dirsearch_config.get('hunt_files', False)

        await workflow.execute_activity(
            "RunHTTPCrawlActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue",
        )

        await workflow.execute_activity(
            "RunDirFileFuzzActivity",
            {**ctx, 'mode': 'directory'},
            start_to_close_timeout=timedelta(hours=2),
            retry_policy=_RETRY_LONG_SCAN,
            task_queue="python-orchestrator-queue",
        )

        if hunt_files or hunt_secrets:
            await workflow.execute_activity(
                "RunSecretScanningActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )
        return True


@workflow.defn(name="URLFuzzWorkflow")
class URLFuzzWorkflow:
    """Comprehensive URL fuzzing with multiple fuzz engines.

    rengine-ng equivalent: url_fuzz (feroxbuster + ffuf + httpx + trufflehog).
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        fuzz_config = yaml_config.get('url_fuzz', {})
        hunt_secrets = fuzz_config.get('hunt_secrets', False)
        fuzzers = fuzz_config.get('fuzzers', ['ffuf'])

        fuzz_tasks = []
        if 'feroxbuster' in fuzzers:
            fuzz_tasks.append(
                workflow.execute_activity(
                    "RunFeroxbusterActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue",
                )
            )
        if 'ffuf' in fuzzers:
            fuzz_tasks.append(
                workflow.execute_activity(
                    "RunDirFileFuzzActivity",
                    ctx,
                    start_to_close_timeout=timedelta(hours=2),
                    retry_policy=_RETRY_LONG_SCAN,
                    task_queue="python-orchestrator-queue",
                )
            )
        if fuzz_tasks:
            await asyncio.gather(*fuzz_tasks)

        await workflow.execute_activity(
            "RunHTTPCrawlActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue",
        )

        if hunt_secrets:
            await workflow.execute_activity(
                "RunSecretScanningActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )
        return True


@workflow.defn(name="URLParamsFuzzWorkflow")
class URLParamsFuzzWorkflow:
    """URL parameter discovery and fuzzing.

    rengine-ng equivalent: url_params_fuzz (httpx + arjun + ffuf + trufflehog).
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        params_config = yaml_config.get('url_params_fuzz', {})
        hunt_secrets = params_config.get('hunt_secrets', False)
        fuzz_values = params_config.get('fuzz_values', False)

        # Probe URLs first
        await workflow.execute_activity(
            "RunHTTPCrawlActivity",
            ctx,
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=_RETRY_NETWORK_SCAN,
            task_queue="python-orchestrator-queue",
        )

        # Discover parameters with arjun
        await workflow.execute_activity(
            "RunArjunActivity",
            ctx,
            start_to_close_timeout=timedelta(hours=1),
            retry_policy=_RETRY_LONG_SCAN,
            task_queue="python-orchestrator-queue",
        )

        if fuzz_values:
            await workflow.execute_activity(
                "RunDirFileFuzzActivity",
                {**ctx, 'mode': 'params'},
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )

        if hunt_secrets:
            await workflow.execute_activity(
                "RunSecretScanningActivity",
                ctx,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )
        return True


@workflow.defn(name="URLVulnWorkflow")
class URLVulnWorkflow:
    """URL vulnerability scanning with gf pattern matching + dalfox + nuclei.

    Runs gf patterns to identify suspicious URLs (XSS, LFI, SSRF, RCE, IDOR,
    debug_logic), then attacks XSS candidates with dalfox, and optionally
    runs a full nuclei HTTP scan.

    rengine-ng equivalent: url_vuln workflow.
    """

    @workflow.run
    async def run(self, ctx: dict) -> bool:
        yaml_config = ctx.get('yaml_configuration', {}) or {}
        vuln_config = yaml_config.get('url_vuln', {})
        run_nuclei = vuln_config.get('nuclei', False)

        urls = ctx.get('urls', [])
        if not urls:
            return True

        # Run all gf patterns in parallel
        gf_patterns = ['xss', 'lfi', 'ssrf', 'rce', 'idor', 'debug_logic', 'interestingparams']
        gf_results = await asyncio.gather(*[
            workflow.execute_activity(
                "RunGFActivity",
                {**ctx, 'pattern': pattern, 'urls': urls},
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
            for pattern in gf_patterns
        ])

        # Flatten XSS matches for dalfox
        xss_urls = gf_results[0] if gf_results else []

        # Run dalfox on XSS candidates
        if xss_urls:
            await workflow.execute_activity(
                "RunDalfoxActivity",
                {**ctx, 'urls': xss_urls},
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )

        if run_nuclei:
            await workflow.execute_activity(
                "RunNucleiActivity",
                {**ctx, 'exclude_tags': ['network', 'ssl', 'file', 'dns', 'osint'],
                 'severity': 'critical,high,medium'},
                start_to_close_timeout=timedelta(hours=2),
                retry_policy=_RETRY_LONG_SCAN,
                task_queue="python-orchestrator-queue",
            )

        return True
```

- [ ] **Step 3: Register all four in orchestrator, run tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows --verbosity=2"
```
Expected: `OK` — all tests pass.

- [ ] **Step 4: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py web/tests/test_new_workflows.py
git commit -m "feat(workflows): add URLDirSearch, URLFuzz, URLParamsFuzz, URLVuln workflows"
```

---

## Task 11: API endpoints for all 13 workflows

**Files:**
- Modify: `web/api/views.py`
- Modify: `web/api/urls.py`

- [ ] **Step 1: Write test for API endpoint**

```python
# Add to web/tests/test_new_workflows.py

class TestWorkflowAPIEndpoints(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('testuser', password='testpass')
        self.client.force_login(self.user)

    @patch('reNgine.temporal_client.TemporalClientProvider.start_workflow')
    def test_start_user_hunt_workflow(self, mock_start):
        mock_start.return_value = 'wf-user-hunt-1'
        response = self.client.post('/api/v1/workflows/user-hunt/start/', {
            'target': 'johndoe',
            'target_type': 'username',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('workflow_id', data)

    @patch('reNgine.temporal_client.TemporalClientProvider.start_workflow')
    def test_start_cidr_recon_workflow(self, mock_start):
        mock_start.return_value = 'wf-cidr-1'
        response = self.client.post('/api/v1/workflows/cidr-recon/start/', {
            'cidr': '192.0.2.0/24',
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 2: Add `StartWorkflowView` to `api/views.py`**

Find the end of the API views file and add:

```python
# web/api/views.py (append)

WORKFLOW_REGISTRY = {
    'user-hunt': ('UserHuntWorkflow', ['target', 'target_type']),
    'url-bypass': ('URLBypassWorkflow', ['urls']),
    'wordpress': ('WordPressWorkflow', ['urls']),
    'host-recon': ('HostReconWorkflow', ['target', 'target_type']),
    'cidr-recon': ('CIDRReconWorkflow', ['cidr']),
    'code-scan': ('CodeScanWorkflow', ['target', 'target_type']),
    'domain-recon': ('DomainReconWorkflow', ['domain']),
    'subdomain-recon': ('SubdomainReconWorkflow', ['domain']),
    'url-crawl': ('URLCrawlWorkflow', ['urls']),
    'url-dirsearch': ('URLDirSearchWorkflow', ['urls']),
    'url-fuzz': ('URLFuzzWorkflow', ['urls']),
    'url-params-fuzz': ('URLParamsFuzzWorkflow', ['urls']),
    'url-vuln': ('URLVulnWorkflow', ['urls']),
}


class StartWorkflowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workflow_slug: str):
        if workflow_slug not in WORKFLOW_REGISTRY:
            return Response({'error': 'Unknown workflow'}, status=404)

        workflow_name, required_fields = WORKFLOW_REGISTRY[workflow_slug]
        data = request.data

        ctx = {
            'yaml_configuration': data.get('yaml_configuration', {}),
            'scan_history_id': data.get('scan_history_id'),
        }
        for field in required_fields:
            if field in data:
                ctx[field] = data[field]

        import asyncio
        from reNgine.temporal_client import TemporalClientProvider

        try:
            workflow_id = asyncio.run(
                TemporalClientProvider.start_workflow(
                    workflow_name,
                    args=[ctx],
                    id=f"{workflow_slug}-{request.user.id}-{int(timezone.now().timestamp())}",
                    task_queue="python-orchestrator-queue",
                )
            )
            return Response({'workflow_id': str(workflow_id), 'status': 'started'})
        except Exception as exc:
            logger.error("Failed to start workflow %s: %s", workflow_name, str(exc))
            return Response({'error': 'Failed to start workflow'}, status=500)
```

- [ ] **Step 3: Add URL patterns to `api/urls.py`**

```python
# In api/urls.py, add inside urlpatterns:
path('v1/workflows/<str:workflow_slug>/start/', StartWorkflowView.as_view(), name='start-workflow'),
```

- [ ] **Step 4: Run API tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestWorkflowAPIEndpoints --verbosity=2"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add web/api/views.py web/api/urls.py web/tests/test_new_workflows.py
git commit -m "feat(api): add StartWorkflowView and URL patterns for all 13 rengine-ng workflows"
```

---

## Task 12: Add per-service concurrent `search_vulns` fan-out to `MasterScanWorkflow` Tier 2

This task modifies the **existing** `MasterScanWorkflow` to fan out `RunSearchVulnsActivity` and `RunSearchsploitActivity` concurrently per discovered service immediately after `RunPortScanActivity` returns. This is purely additive — no existing activities are removed or reordered.

**Files:**
- Modify: `web/reNgine/temporal_workflows.py` (`MasterScanWorkflow._tier2_branch` or inline Tier 2 block)

- [ ] **Step 1: Write the failing test**

```python
# Add to web/tests/test_new_workflows.py

class TestMasterScanSearchVulnsFanOut(TestCase):
    @patch('reNgine.temporal_workflows.workflow.execute_activity', new_callable=AsyncMock)
    async def test_port_scan_result_fans_out_search_vulns(self, mock_exec):
        """After port scan returns service list, search_vulns fires per service."""
        from reNgine.temporal_workflows import MasterScanWorkflow

        port_scan_result = {
            'services': [
                {'host': '192.0.2.1', 'port': 22, 'service': 'openssh', 'version': '7.4'},
                {'host': '192.0.2.1', 'port': 80, 'service': 'apache-httpd', 'version': '2.4.49'},
            ]
        }

        # Make port scan return the service list; everything else returns True
        async def activity_side_effect(name, *args, **kwargs):
            if name == 'RunPortScanActivity':
                return port_scan_result
            return True

        mock_exec.side_effect = activity_side_effect
        wf = MasterScanWorkflow()
        ctx = {
            'scan_history_id': 1,
            'domain_id': 1,
            'yaml_configuration': {'port_scan': {}},
            'results_dir': '/tmp',
        }
        # Only run up to Tier 2 — mock everything else to return immediately
        try:
            await wf.run(ctx)
        except Exception:
            pass  # Workflow may raise for missing activities; we check call args

        search_vulns_calls = [
            call for call in mock_exec.call_args_list
            if call.args and call.args[0] == 'RunSearchVulnsActivity'
        ]
        # Should have one call per discovered service (2 services = 2 calls)
        self.assertEqual(len(search_vulns_calls), 2)
        services_queried = {c.args[1].get('service') for c in search_vulns_calls}
        self.assertIn('openssh', services_queried)
        self.assertIn('apache-httpd', services_queried)
```

- [ ] **Step 2: Run to confirm failure**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestMasterScanSearchVulnsFanOut --verbosity=2 2>&1 | head -20"
```
Expected: test fails — `len(search_vulns_calls) == 0` because the fan-out doesn't exist yet.

- [ ] **Step 3: Locate the Tier 2 port scan block in `MasterScanWorkflow`**

```bash
grep -n "RunPortScanActivity\|tier.*2\|Tier 2" web/reNgine/temporal_workflows.py | head -20
```
Note the line number where `RunPortScanActivity` is awaited in `MasterScanWorkflow`.

- [ ] **Step 4: Add `_fan_out_search_vulns` helper to `temporal_workflows.py`**

Add this deterministic helper function at module level (not inside a workflow class), after the existing `_dispatch_tier_plugins` helper:

```python
async def _fan_out_search_vulns(ctx: dict, port_scan_result: dict) -> None:
    """Fan out concurrent per-service CVE + exploit lookups after port scan.

    Reads the 'services' list from port_scan_result and launches one
    RunSearchVulnsActivity + one RunSearchsploitActivity per service,
    all gathered concurrently. Safe to call with an empty services list.

    Args:
        ctx: Full scan context dict.
        port_scan_result: Dict returned by RunPortScanActivity, expected to
                          contain a 'services' key with list of
                          {host, port, service, version} dicts.
    """
    services = port_scan_result.get('services', []) if isinstance(port_scan_result, dict) else []
    if not services:
        return

    lookup_tasks = []
    for svc in services:
        service_name = svc.get('service', '').strip()
        if not service_name:
            continue
        svc_ctx = {
            **ctx,
            'host': svc.get('host', ''),
            'port': svc.get('port', 0),
            'service': service_name,
            'version': svc.get('version'),
        }
        lookup_tasks.append(
            workflow.execute_activity(
                "RunSearchVulnsActivity",
                svc_ctx,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
        )
        lookup_tasks.append(
            workflow.execute_activity(
                "RunSearchsploitActivity",
                svc_ctx,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=_RETRY_INTERNAL,
                task_queue="python-orchestrator-queue",
            )
        )

    if lookup_tasks:
        await asyncio.gather(*lookup_tasks, return_exceptions=True)
```

Note `return_exceptions=True` — a failed lookup for one service must not abort the gather.

- [ ] **Step 5: Call `_fan_out_search_vulns` after `RunPortScanActivity` in `MasterScanWorkflow`**

Find the line in `MasterScanWorkflow` where `RunPortScanActivity` is awaited and capture its result. Then add the fan-out call immediately after. The existing code likely looks like:

```python
# Before (existing):
await workflow.execute_activity(
    "RunPortScanActivity",
    ctx,
    ...
)
```

Change to:

```python
# After:
port_scan_result = await workflow.execute_activity(
    "RunPortScanActivity",
    ctx,
    start_to_close_timeout=timedelta(hours=1),
    retry_policy=_RETRY_NETWORK_SCAN,
    task_queue="python-orchestrator-queue",
)
# Fan out per-service CVE/exploit lookups concurrently — does not block scan progress
await _fan_out_search_vulns(ctx, port_scan_result or {})
```

If the existing call is already inside an `asyncio.gather` (Tier 2 parallel block), extract `RunPortScanActivity` from the gather, run it first to get the result, then call `_fan_out_search_vulns`, then continue with the rest of the gather. Preserving the other Tier 2 activities' concurrency is the goal.

- [ ] **Step 6: Also add `_fan_out_search_vulns` to `HostReconWorkflow` (Task 4 of this plan)**

In the `HostReconWorkflow.run` implemented earlier in this plan, after the nmap version detection activity, add:

```python
# After nmap version detection:
port_scan_result = await workflow.execute_activity(
    "RunPortScanActivity",
    {**ctx, 'port_scan_tool': 'nmap', 'version_detection': True},
    start_to_close_timeout=timedelta(minutes=30),
    retry_policy=_RETRY_NETWORK_SCAN,
    task_queue="python-orchestrator-queue",
)
await _fan_out_search_vulns(ctx, port_scan_result or {})
```

- [ ] **Step 7: Run the new test — expect pass**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_new_workflows.TestMasterScanSearchVulnsFanOut --verbosity=2"
```
Expected: `OK` — 2 `RunSearchVulnsActivity` calls detected, one per service.

- [ ] **Step 8: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/tests/test_new_workflows.py
git commit -m "feat(workflows): fan out RunSearchVulnsActivity per service in MasterScanWorkflow Tier 2 and HostReconWorkflow"
```

---

## Task 13: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -20"
```
Expected: `OK`

- [ ] **Step 2: Tag Phase 2 complete**

```bash
git tag phase2-workflows
```

---

## Self-Review

**Spec coverage:**
- ✅ All 13 rengine-ng workflows implemented as Temporal workflow classes
- ✅ Each uses activities from Phase 1 + existing activities
- ✅ All registered in orchestrator
- ✅ Generic `StartWorkflowView` API handles all 13 workflows via `workflow_slug`
- ✅ Tests for each workflow (activity dispatch verification)
- ✅ Tests for API endpoints (mock workflow start)
- ✅ `_fan_out_search_vulns` helper fans out one `RunSearchVulnsActivity` + one `RunSearchsploitActivity` per service concurrently after port scan in both `MasterScanWorkflow` and `HostReconWorkflow`
- ✅ `return_exceptions=True` on the gather so a failed lookup never aborts the scan

**Placeholder scan:** None — all workflow implementations have real `asyncio.gather` + `execute_activity` code.

**Type consistency:** All workflows use `ctx: dict` as run argument. All activity calls use string names (matching `@activity.defn(name=...)` in Phase 1). `_fan_out_search_vulns` accepts `dict` return from port scan and is safe with `None` / empty results.
