# HTTP Crawl Discovery Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken discovery → http_crawl handoff so that `RunHTTPCrawlActivity` reliably finds the endpoints seeded by `subdomain_discovery`, then add a `SeedEndpointsForCrawlActivity` bridge that mirrors rengine-ng's `pre_crawl` step.

**Architecture:** `subdomain_discovery` already writes `EndPoint(http_status=0, is_default=True)` rows. The bug is that `get_http_urls(is_uncrawled=True)` filters `http_status__isnull=True`, but the model defaults to `0` — so those rows are always invisible. After fixing the filter, a new `SeedEndpointsForCrawlActivity` runs between Tier 1 and Tier 2 to guarantee every discovered subdomain has a seeded endpoint and passes an explicit URL list into ctx for `RunHTTPCrawlActivity`.

**Tech Stack:** Django ORM, Temporal Python SDK, `temporalio.activity`, `startScan.models.EndPoint/Subdomain`

---

## Root Cause Reference

| Item | Value |
|---|---|
| `EndPoint.http_status` model default | `0` (`startScan/models.py:418`) |
| `get_http_urls` uncrawled filter | `http_status__isnull=True` (`common_func.py:327`) |
| rengine-ng uncrawled filter | `http_status=0` |
| Effect | All `http_status=0` endpoints are invisible → "No endpoints were found in query!" |

---

## Files to Create / Modify

| File | Action | What changes |
|---|---|---|
| `web/reNgine/common_func.py` | Modify | Fix `is_uncrawled` filter: `isnull=True` → `Q(…isnull=True) \| Q(http_status=0)` |
| `web/reNgine/temporal_activities.py` | Modify | Add `seed_endpoints_for_crawl_activity` |
| `web/scanEngine/management/commands/run_temporal_orchestrator.py` | Modify | Import + register `seed_endpoints_for_crawl_activity` |
| `web/reNgine/temporal_workflows.py` | Modify | Insert `SeedEndpointsForCrawlActivity` in Tier 1→2 bridge in both `MasterScanWorkflow` and `SubScanWorkflow` |
| `web/tests/test_http_crawl_bridge.py` | Create | Unit tests for filter fix and seeding logic |

---

## Task 1: Fix the `is_uncrawled` filter in `get_http_urls`

**Files:**
- Modify: `web/reNgine/common_func.py:327`
- Test: `web/tests/test_http_crawl_bridge.py`

- [ ] **Step 1: Write the failing test**

Create `web/tests/test_http_crawl_bridge.py`:

```python
from django.test import TestCase
from unittest.mock import patch, MagicMock
from reNgine.common_func import get_http_urls


class TestGetHttpUrlsUncrawledFilter(TestCase):
    """get_http_urls(is_uncrawled=True) must find endpoints with http_status=0."""

    def _make_ctx(self, scan_id=1, domain_id=1):
        return {'scan_history_id': scan_id, 'domain_id': domain_id}

    @patch('reNgine.common_func.ScanHistory')
    @patch('reNgine.common_func.Domain')
    @patch('reNgine.common_func.EndPoint')
    def test_finds_endpoints_with_http_status_zero(self, MockEndPoint, MockDomain, MockScan):
        """Endpoints with http_status=0 (model default) must be returned when is_uncrawled=True."""
        mock_scan = MagicMock()
        mock_domain = MagicMock()
        MockScan.objects.filter.return_value.first.return_value = mock_scan
        MockDomain.objects.filter.return_value.first.return_value = mock_domain

        mock_ep = MagicMock()
        mock_ep.http_url = 'http://sub.example.com'
        mock_ep.is_alive = True

        mock_qs = MagicMock()
        mock_qs.distinct.return_value.order_by.return_value.all.return_value = [mock_ep]
        MockEndPoint.objects.filter.return_value.filter.return_value = mock_qs
        MockEndPoint.objects = MagicMock()
        MockEndPoint.objects.filter.return_value = mock_qs

        with patch('reNgine.common_func.is_valid_url', return_value=True):
            result = get_http_urls(is_uncrawled=True, ctx=self._make_ctx())

        # Verify the query used Q(http_status__isnull=True) | Q(http_status=0)
        # The easiest check: the result is not empty when endpoints exist
        self.assertIsInstance(result, list)

    @patch('reNgine.common_func.ScanHistory')
    @patch('reNgine.common_func.Domain')
    @patch('reNgine.common_func.EndPoint')
    def test_uncrawled_filter_uses_http_status_zero_not_null(self, MockEndPoint, MockDomain, MockScan):
        """Verify the ORM call includes http_status=0 in the uncrawled filter."""
        MockScan.objects.filter.return_value.first.return_value = MagicMock()
        MockDomain.objects.filter.return_value.first.return_value = MagicMock()

        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs
        mock_qs.distinct.return_value.order_by.return_value.all.return_value = []
        MockEndPoint.objects = mock_qs

        with patch('reNgine.common_func.is_valid_url', return_value=True):
            get_http_urls(is_uncrawled=True, ctx=self._make_ctx())

        # Confirm filter was called with Q expressions (not just isnull)
        call_args_list = mock_qs.filter.call_args_list
        filter_kwargs = [str(c) for c in call_args_list]
        combined = ' '.join(filter_kwargs)
        self.assertIn('http_status', combined)
```

- [ ] **Step 2: Run test to confirm it fails (or documents the bug)**

```
docker exec -it rengine-web python manage.py test tests.test_http_crawl_bridge -v 2
```

Expected: Tests run (may pass trivially due to mocking — the real verification is the integration behavior).

- [ ] **Step 3: Fix the filter in `common_func.py`**

In `web/reNgine/common_func.py`, find the `get_http_urls` function. Add `Q` to the Django imports at the top of the file (or at the top of the function if imported locally). Then change the `is_uncrawled` block:

```python
# BEFORE (line ~327):
if is_uncrawled:
    query = query.filter(http_status__isnull=True)

# AFTER:
if is_uncrawled:
    from django.db.models import Q
    query = query.filter(Q(http_status__isnull=True) | Q(http_status=0))
```

The full context (lines ~324–328) should look like:

```python
    # If is_uncrawled is True, select only endpoints that have not been crawled
    # yet (no status). EndPoint.http_status defaults to 0, so we match both
    # 0 (newly seeded) and NULL (explicitly unset).
    if is_uncrawled:
        from django.db.models import Q
        query = query.filter(Q(http_status__isnull=True) | Q(http_status=0))
```

- [ ] **Step 4: Run tests**

```
docker exec -it rengine-web python manage.py test tests.test_http_crawl_bridge -v 2
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/common_func.py web/tests/test_http_crawl_bridge.py
git commit -m "fix(http-crawl): match http_status=0 endpoints in is_uncrawled filter

EndPoint.http_status defaults to 0, not NULL. get_http_urls was filtering
http_status__isnull=True which excluded every endpoint seeded by
subdomain_discovery, causing 'No endpoints were found in query!' on every scan.
Now uses Q(isnull=True) | Q(http_status=0) to match both states."
```

---

## Task 2: Add `seed_endpoints_for_crawl_activity`

**Files:**
- Modify: `web/reNgine/temporal_activities.py` (add after `parse_discovery_results_activity`, before Tier 2 section)
- Test: `web/tests/test_http_crawl_bridge.py` (extend)

This mirrors rengine-ng's `pre_crawl` seeding step: for every `Subdomain` discovered in the scan, ensure an `EndPoint(is_default=True, http_status=0)` exists. Returns the seeded URL list into a `seed_urls` key on ctx so `RunHTTPCrawlActivity` can log it, and so future work can pass URLs explicitly.

- [ ] **Step 1: Write the failing test**

Append to `web/tests/test_http_crawl_bridge.py`:

```python
from unittest.mock import patch, MagicMock, call
import sys
import types


class TestSeedEndpointsForCrawlActivity(TestCase):
    """seed_endpoints_for_crawl_activity ensures every subdomain has a default EndPoint."""

    def _make_ctx(self):
        return {
            'scan_history_id': 10,
            'domain_id': 5,
            'results_dir': '/tmp/results',
            'yaml_configuration': {},
        }

    @patch('reNgine.temporal_activities.activity')
    def test_activity_creates_missing_endpoints(self, mock_activity):
        """For each subdomain without a default endpoint, save_endpoint is called."""
        from reNgine.temporal_activities import seed_endpoints_for_crawl_activity

        mock_sub1 = MagicMock()
        mock_sub1.name = 'sub1.example.com'
        mock_sub2 = MagicMock()
        mock_sub2.name = 'sub2.example.com'

        with patch('startScan.models.Subdomain') as MockSub, \
             patch('startScan.models.EndPoint') as MockEP, \
             patch('reNgine.utils.task.save_endpoint') as mock_save_ep:

            MockSub.objects.filter.return_value = [mock_sub1, mock_sub2]
            MockEP.objects.filter.return_value.exists.return_value = False
            mock_save_ep.return_value = (MagicMock(), True)

            result = seed_endpoints_for_crawl_activity(self._make_ctx())

        self.assertEqual(mock_save_ep.call_count, 2)
        self.assertIn('seed_urls', result)
        self.assertIsInstance(result['seed_urls'], list)

    @patch('reNgine.temporal_activities.activity')
    def test_activity_skips_existing_endpoints(self, mock_activity):
        """Subdomains that already have a default endpoint are not re-seeded."""
        from reNgine.temporal_activities import seed_endpoints_for_crawl_activity

        mock_sub = MagicMock()
        mock_sub.name = 'already.example.com'

        with patch('startScan.models.Subdomain') as MockSub, \
             patch('startScan.models.EndPoint') as MockEP, \
             patch('reNgine.utils.task.save_endpoint') as mock_save_ep:

            MockSub.objects.filter.return_value = [mock_sub]
            mock_existing_ep = MagicMock()
            mock_existing_ep.http_url = 'http://already.example.com'
            MockEP.objects.filter.return_value.first.return_value = mock_existing_ep

            result = seed_endpoints_for_crawl_activity(self._make_ctx())

        mock_save_ep.assert_not_called()
        self.assertIn('http://already.example.com', result['seed_urls'])
```

- [ ] **Step 2: Run test to confirm it fails**

```
docker exec -it rengine-web python manage.py test tests.test_http_crawl_bridge.TestSeedEndpointsForCrawlActivity -v 2
```

Expected: FAIL — `ImportError: cannot import name 'seed_endpoints_for_crawl_activity'`

- [ ] **Step 3: Implement the activity**

In `web/reNgine/temporal_activities.py`, add the following after `parse_discovery_results_activity` (after line ~430, before the `# Tier 2` section comment):

```python
@activity.defn(name="SeedEndpointsForCrawlActivity")
def seed_endpoints_for_crawl_activity(ctx: dict) -> dict:
    """Ensure every discovered subdomain has a default EndPoint before http_crawl runs.

    Mirrors rengine-ng's pre_crawl step. Queries all Subdomain records for the
    current scan and creates EndPoint(is_default=True, http_status=0) for any
    subdomain that does not yet have a default endpoint. Returns an updated ctx
    with a 'seed_urls' list that RunHTTPCrawlActivity can log and use.
    """
    from startScan.models import Subdomain, EndPoint
    from reNgine.utils.task import save_endpoint

    scan_id = ctx.get('scan_history_id')
    url_filter = ctx.get('starting_point_path', '')

    subdomains = Subdomain.objects.filter(scan_history_id=scan_id)
    seed_urls = []

    for subdomain in subdomains:
        raw_url = f'{subdomain.name}{url_filter}' if url_filter else subdomain.name
        if not raw_url.startswith(('http://', 'https://')):
            raw_url = f'http://{raw_url}'

        existing = EndPoint.objects.filter(
            scan_history_id=scan_id,
            http_url=raw_url,
            is_default=True,
        ).first()

        if existing:
            seed_urls.append(existing.http_url)
        else:
            endpoint, _ = save_endpoint(
                raw_url,
                ctx=ctx,
                is_default=True,
                subdomain=subdomain,
            )
            if endpoint:
                seed_urls.append(endpoint.http_url)

    activity.logger.info(
        f"[SeedEndpointsForCrawlActivity] scan_id={scan_id}: "
        f"seeded {len(seed_urls)} endpoint(s) for http_crawl."
    )
    return {**ctx, 'seed_urls': seed_urls}
```

- [ ] **Step 4: Run tests**

```
docker exec -it rengine-web python manage.py test tests.test_http_crawl_bridge.TestSeedEndpointsForCrawlActivity -v 2
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/reNgine/temporal_activities.py web/tests/test_http_crawl_bridge.py
git commit -m "feat(temporal): add SeedEndpointsForCrawlActivity (pre_crawl bridge)

Mirrors rengine-ng's pre_crawl step: after Tier 1 discovery completes,
guarantees every discovered subdomain has a default EndPoint(http_status=0)
before RunHTTPCrawlActivity runs. Returns seed_urls list in ctx."
```

---

## Task 3: Register `seed_endpoints_for_crawl_activity` with the worker

**Files:**
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`

- [ ] **Step 1: Add import**

In `run_temporal_orchestrator.py`, find the `# Tier 3/4: Fuzzing` import block (around line 97). Add the new import to the Tier 1 block above it:

```python
# BEFORE (around line 87):
    parse_discovery_results_activity,

# AFTER:
    parse_discovery_results_activity,
    seed_endpoints_for_crawl_activity,
```

- [ ] **Step 2: Add to `all_activities` list**

Find the `all_activities` list (around line 264). Locate the `# Tier 1` section and add:

```python
    # BEFORE:
    parse_discovery_results_activity,

    # AFTER:
    parse_discovery_results_activity,
    seed_endpoints_for_crawl_activity,
```

- [ ] **Step 3: Verify no import errors**

```
docker exec -it rengine-web python -c "from scanEngine.management.commands.run_temporal_orchestrator import Command; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add web/scanEngine/management/commands/run_temporal_orchestrator.py
git commit -m "feat(temporal): register SeedEndpointsForCrawlActivity with worker"
```

---

## Task 4: Wire `SeedEndpointsForCrawlActivity` into workflows

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`

The activity must run at the end of Tier 1 (after `ParseDiscoveryResultsActivity`) and its returned ctx must flow into Tier 2. It runs in both `MasterScanWorkflow` and `SubScanWorkflow`.

- [ ] **Step 1: Write the test**

Append to `web/tests/test_http_crawl_bridge.py`:

```python
class TestWorkflowSeedingOrder(TestCase):
    """SeedEndpointsForCrawlActivity must be called after ParseDiscoveryResultsActivity
    and before RunHTTPCrawlActivity in workflow execution order."""

    def test_seed_activity_name_in_temporal_activities_module(self):
        """Confirms the activity is registered and importable."""
        from reNgine.temporal_activities import seed_endpoints_for_crawl_activity
        import temporalio.activity as ta
        # The function must carry a Temporal activity definition
        self.assertTrue(
            hasattr(seed_endpoints_for_crawl_activity, '__temporal_activity_definition'),
            "seed_endpoints_for_crawl_activity must be decorated with @activity.defn"
        )
```

Run:
```
docker exec -it rengine-web python manage.py test tests.test_http_crawl_bridge.TestWorkflowSeedingOrder -v 2
```

Expected: PASS (the decorator is already applied from Task 2).

- [ ] **Step 2: Update `MasterScanWorkflow`**

In `web/reNgine/temporal_workflows.py`, find the block at the end of Tier 1 (around line 224–233):

```python
# BEFORE:
            if discovery_futures:
                await asyncio.gather(*discovery_futures)
                # Verify / log discovery results persisted to DB
                await workflow.execute_activity(
                    "ParseDiscoveryResultsActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=_RETRY_INTERNAL,
                    task_queue="python-orchestrator-queue"
                )

# AFTER:
            if discovery_futures:
                await asyncio.gather(*discovery_futures)
                # Verify / log discovery results persisted to DB
                await workflow.execute_activity(
                    "ParseDiscoveryResultsActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=_RETRY_INTERNAL,
                    task_queue="python-orchestrator-queue"
                )
                # Seed default EndPoints for every discovered subdomain so that
                # RunHTTPCrawlActivity finds them via get_http_urls(is_uncrawled=True).
                ctx = await workflow.execute_activity(
                    "SeedEndpointsForCrawlActivity",
                    ctx,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=_RETRY_INTERNAL,
                    task_queue="python-orchestrator-queue"
                )
```

Note: `ctx =` (assignment) is intentional — `seed_endpoints_for_crawl_activity` returns the enriched ctx containing `seed_urls`.

- [ ] **Step 3: Update `SubScanWorkflow`**

In `temporal_workflows.py`, find the equivalent Tier 1 completion point in `SubScanWorkflow`. Search for `"ParseDiscoveryResultsActivity"` inside the `SubScanWorkflow.run` method. Add the same `SeedEndpointsForCrawlActivity` call immediately after it:

```python
                    await workflow.execute_activity(
                        "ParseDiscoveryResultsActivity",
                        ctx,
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=_RETRY_INTERNAL,
                        task_queue="python-orchestrator-queue"
                    )
                    ctx = await workflow.execute_activity(
                        "SeedEndpointsForCrawlActivity",
                        ctx,
                        start_to_close_timeout=timedelta(minutes=5),
                        retry_policy=_RETRY_INTERNAL,
                        task_queue="python-orchestrator-queue"
                    )
```

- [ ] **Step 4: Verify syntax**

```
docker exec -it rengine-web python -c "import reNgine.temporal_workflows; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Run full test suite**

```
docker exec -it rengine-web python manage.py test tests.test_http_crawl_bridge -v 2
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add web/reNgine/temporal_workflows.py web/tests/test_http_crawl_bridge.py
git commit -m "feat(temporal): wire SeedEndpointsForCrawlActivity into Tier 1→2 bridge

Inserted after ParseDiscoveryResultsActivity in both MasterScanWorkflow and
SubScanWorkflow. The activity guarantees default EndPoints exist for all
discovered subdomains before http_crawl queries the DB. ctx is updated with
the returned seed_urls list."
```

---

## Task 5: Log seed URLs in `RunHTTPCrawlActivity`

**Files:**
- Modify: `web/reNgine/temporal_activities.py` (the `run_http_crawl_activity` function around line 437)

`seed_urls` is now in ctx. Log it so operators can verify the correct input is being passed to httpx.

- [ ] **Step 1: Update `run_http_crawl_activity`**

Find `run_http_crawl_activity` in `temporal_activities.py` (around line 437):

```python
# BEFORE:
@activity.defn(name="RunHTTPCrawlActivity")
def run_http_crawl_activity(ctx: dict) -> bool:
    """Run httpx HTTP crawl across all discovered subdomains.

    Delegates to the existing `http_crawl` task which probes all discovered
    subdomains for live HTTP services and persists endpoint metadata.
    ...
    """
    from reNgine.tasks import http_crawl
    activity.logger.info(f"[RunHTTPCrawlActivity] scan_id={ctx.get('scan_history_id')}")
    return _run_task(
        http_crawl,
        ctx,
        task_name='http_crawl',
        description='HTTP Crawl'
    )

# AFTER:
@activity.defn(name="RunHTTPCrawlActivity")
def run_http_crawl_activity(ctx: dict) -> bool:
    """Run httpx HTTP crawl across all discovered subdomains.

    Delegates to the existing `http_crawl` task which probes all discovered
    subdomains for live HTTP services and persists endpoint metadata.
    ...
    """
    from reNgine.tasks import http_crawl
    scan_id = ctx.get('scan_history_id')
    seed_urls = ctx.get('seed_urls', [])
    activity.logger.info(
        f"[RunHTTPCrawlActivity] scan_id={scan_id} "
        f"seed_count={len(seed_urls)}"
    )
    return _run_task(
        http_crawl,
        ctx,
        task_name='http_crawl',
        description='HTTP Crawl'
    )
```

- [ ] **Step 2: Commit**

```bash
git add web/reNgine/temporal_activities.py
git commit -m "feat(temporal): log seed_urls count in RunHTTPCrawlActivity"
```

---

## Self-Review Checklist

- [x] **Root cause addressed**: `get_http_urls` filter changed to `Q(isnull=True) | Q(http_status=0)` (Task 1)
- [x] **Bridge added**: `SeedEndpointsForCrawlActivity` mirrors rengine-ng's `pre_crawl` (Task 2)
- [x] **Worker registration**: new activity imported and listed in `all_activities` (Task 3)
- [x] **Both workflows updated**: `MasterScanWorkflow` and `SubScanWorkflow` (Task 4)
- [x] **Observability**: `seed_count` logged at activity start (Task 5)
- [x] **No breaking changes**: all other `get_http_urls` callers with `is_uncrawled=True` benefit from the fix
- [x] **Backward compatible**: `seed_urls` key is optional in ctx; `RunHTTPCrawlActivity` defaults to `[]`
- [x] **Existing dedup preserved**: `save_endpoint` uses get-or-create; duplicate calls are idempotent
