# Screenshot Endpoint Collection Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix r3ngine's screenshot task so it discovers and screenshots all live default endpoints (one per subdomain), not just the single domain root that currently survives the Subdomain http_url/http_status filter.

**Architecture:** Mirror the rengine-ng approach — query `EndPoint.objects.filter(scan_history=..., is_default=True)` directly, passing the full `http_url` (with path) to the Playwright capture engine. Add a `url_override` parameter to `take_screenshot_and_save` so the outer loop controls the URL without re-querying endpoints.

**Tech Stack:** Python 3.x, Django ORM, Django TestCase, unittest.mock, `reNgine/tasks.py`, `reNgine/screenshot/tasks.py`

---

## Root Cause Analysis

The bug is in two places:

**Bug 1 — Wrong model queried in `screenshot()` (`tasks.py:2255-2288`)**

```python
# CURRENT CODE (broken)
subdomains = Subdomain.objects.filter(scan_history=self.scan)
if strict:                                               # intensity=normal is the DEFAULT
    subdomains = subdomains.filter(http_status__gt=0).exclude(http_url__isnull=True)
for subdomain in subdomains:
    take_screenshot_and_save(subdomain.id, ...)
```

- `intensity=normal` is `DEFAULT_SCAN_INTENSITY` (`definitions.py:269`)
- `Subdomain.http_url` is only populated when the default endpoint for that subdomain was probed by http_crawl
- The domain root (set in `initiate_scan_temporal`) always passes; discovered subdomains only pass if http_crawl already ran and found them alive
- In single-target or short scans, only the root subdomain passes → 1 screenshot

**Bug 2 — Paths stripped in `take_screenshot_and_save` (`screenshot/tasks.py:43-46`)**

```python
# CURRENT CODE (incomplete coverage)
base_url = f"{parsed.scheme}://{parsed.netloc}"   # strips all path
urls_to_capture.add(base_url)
```

Even when multiple endpoints exist (e.g. `https://app.example.com/api/v1`), they all collapse to `https://app.example.com` → 1 screenshot per subdomain regardless of how many endpoints were discovered.

**rengine-ng reference pattern** (`rengine-ng/web/reNgine/secator/services/target_builder_service.py`):
```python
EndPoint.objects.filter(domain_id__in=domain_ids, is_default=True).values_list("http_url", flat=True)
```
Queries EndPoints directly using `is_default=True` and passes the full URL.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `web/reNgine/tasks.py` lines 2255–2288 | `screenshot()` — replace Subdomain loop with EndPoint query |
| Modify | `web/reNgine/screenshot/tasks.py` | `take_screenshot_and_save()` — add `url_override` parameter |
| Create | `web/tests/test_screenshot_endpoint_collection.py` | Tests for both changes |

---

## Task 1: Add `url_override` parameter to `take_screenshot_and_save`

**Files:**
- Modify: `web/reNgine/screenshot/tasks.py` (function starts at line 15)
- Test: `web/tests/test_screenshot_endpoint_collection.py`

- [ ] **Step 1.1: Write the failing tests**

Create `web/tests/test_screenshot_endpoint_collection.py`:

```python
from django.test import TestCase
from unittest.mock import patch, MagicMock
from startScan.models import (
    ScanHistory, Subdomain, EndPoint, Domain, Screenshot
)
from reNgine.screenshot.tasks import take_screenshot_and_save


class TestTakeScreenshotAndSaveUrlOverride(TestCase):
    """Tests for url_override parameter in take_screenshot_and_save."""

    def setUp(self):
        self.domain = Domain.objects.create(name='example.com')
        self.scan = ScanHistory.objects.create(
            scan_status='running',
            domain=self.domain,
        )
        self.subdomain = Subdomain.objects.create(
            name='app.example.com',
            scan_history=self.scan,
            target_domain=self.domain,
            http_url='https://app.example.com/admin/panel',
            http_status=200,
        )

    @patch('reNgine.screenshot.tasks.run_capture')
    def test_url_override_uses_provided_url_not_base(self, mock_capture):
        """When url_override is provided, that exact URL is captured — no path stripping."""
        mock_capture.return_value = {
            'screenshot_path': '/results/screenshots/abc123.png',
            'html_path': '/results/html/abc123.html',
            'title': 'Admin Panel',
            'status_code': 200,
            'response_headers': {},
            'tags': [],
        }
        full_url = 'https://app.example.com/admin/panel'

        result = take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
            url_override=full_url,
        )

        self.assertTrue(result)
        mock_capture.assert_called_once()
        called_url = mock_capture.call_args[0][0]
        self.assertEqual(called_url, full_url)
        # Must NOT strip path to base URL
        self.assertNotEqual(called_url, 'https://app.example.com')

    @patch('reNgine.screenshot.tasks.run_capture')
    def test_url_override_does_not_query_endpoints(self, mock_capture):
        """url_override path skips querying EndPoint objects."""
        mock_capture.return_value = {
            'screenshot_path': '/results/screenshots/abc.png',
            'html_path': None,
            'title': 'Test',
            'status_code': 200,
            'response_headers': {},
            'tags': [],
        }
        # No endpoints created — if it tries to query them and fall back,
        # it would use http://app.example.com or https://app.example.com
        full_url = 'https://app.example.com/admin/panel'

        take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
            url_override=full_url,
        )

        called_url = mock_capture.call_args[0][0]
        # Confirms it used url_override, not a synthesised root URL
        self.assertEqual(called_url, 'https://app.example.com/admin/panel')

    @patch('reNgine.screenshot.tasks.run_capture')
    def test_screenshot_saved_with_override_url_in_db(self, mock_capture):
        """Screenshot model is created with the full url_override URL."""
        mock_capture.return_value = {
            'screenshot_path': '/results/screenshots/full_path.png',
            'html_path': None,
            'title': 'Panel',
            'status_code': 200,
            'response_headers': {},
            'tags': [],
        }
        full_url = 'https://app.example.com/admin/panel'

        take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
            url_override=full_url,
        )

        saved = Screenshot.objects.filter(subdomain=self.subdomain, scan_history=self.scan).first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.url, full_url)

    @patch('reNgine.screenshot.tasks.run_capture')
    def test_no_override_still_works_legacy_path(self, mock_capture):
        """Without url_override, existing endpoint-query behaviour is preserved."""
        mock_capture.return_value = {
            'screenshot_path': '/results/screenshots/legacy.png',
            'html_path': None,
            'title': 'Home',
            'status_code': 200,
            'response_headers': {},
            'tags': [],
        }
        # Create an endpoint so the legacy path has something to query
        EndPoint.objects.create(
            http_url='https://app.example.com',
            scan_history=self.scan,
            subdomain=self.subdomain,
            target_domain=self.domain,
        )

        result = take_screenshot_and_save(
            subdomain_id=self.subdomain.id,
            scan_id=self.scan.id,
        )

        self.assertTrue(result)
        # Legacy path strips to base URL
        called_url = mock_capture.call_args[0][0]
        self.assertEqual(called_url, 'https://app.example.com')
```

- [ ] **Step 1.2: Run tests to confirm they fail**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test tests.test_screenshot_endpoint_collection --verbosity=2 2>&1 | tail -30"
```

Expected: `TypeError` or `FAIL` — `url_override` parameter does not exist yet.

- [ ] **Step 1.3: Add `url_override` to `take_screenshot_and_save`**

Replace the entire `take_screenshot_and_save` function in `web/reNgine/screenshot/tasks.py`:

```python
def take_screenshot_and_save(subdomain_id, scan_id, results_dir=None, activity_id=None, url_override=None):
    """
    Orchestrates the capture and database persistence of screenshots for a subdomain.

    When url_override is provided (recommended), that exact URL is captured without
    any path stripping — mirrors the rengine-ng pattern of passing full endpoint URLs.

    When url_override is None, falls back to the legacy behaviour: queries all
    endpoints for the subdomain, collapses them to base URLs (scheme://netloc),
    and caps at MAX_SCREENSHOTS_PER_SUBDOMAIN.

    Args:
        subdomain_id (int): ID of the Subdomain object.
        scan_id (int): ID of the ScanHistory object.
        results_dir (str, optional): Directory for results. Defaults to settings.RENGINE_RESULTS.
        activity_id (int, optional): ID of the ScanActivity executing this task.
        url_override (str, optional): Full URL to capture. Skips endpoint querying when set.

    Returns:
        bool: True if at least one screenshot was successfully captured and saved.
    """
    if not results_dir:
        results_dir = settings.RENGINE_RESULTS
    try:
        subdomain = Subdomain.objects.get(id=subdomain_id)
        scan = ScanHistory.objects.get(id=scan_id)

        if url_override:
            # Use the caller-provided URL directly — no path stripping.
            target_urls = [url_override]
        else:
            # Legacy: gather all endpoints for this subdomain and collapse to base URLs.
            endpoints = EndPoint.objects.filter(subdomain=subdomain, scan_history=scan)

            urls_to_capture = set()
            for ep in endpoints:
                if ep.http_url:
                    try:
                        parsed = urlparse(ep.http_url)
                        if parsed.scheme and parsed.netloc:
                            base_url = f"{parsed.scheme}://{parsed.netloc}"
                            urls_to_capture.add(base_url)
                    except Exception as parse_err:
                        logger.debug(f"Failed to parse endpoint URL {ep.http_url}: {parse_err}")

            if subdomain.http_url:
                try:
                    parsed = urlparse(subdomain.http_url)
                    if parsed.scheme and parsed.netloc:
                        urls_to_capture.add(f"{parsed.scheme}://{parsed.netloc}")
                    else:
                        urls_to_capture.add(subdomain.http_url)
                except Exception:
                    urls_to_capture.add(subdomain.http_url)

            if not urls_to_capture:
                urls_to_capture.add(f"http://{subdomain.name}")
                urls_to_capture.add(f"https://{subdomain.name}")

            max_screenshots = int(os.getenv("MAX_SCREENSHOTS_PER_SUBDOMAIN", 10))
            target_urls = sorted(list(urls_to_capture))[:max_screenshots]

        logger.info(
            f"Processing {len(target_urls)} screenshot(s) for subdomain "
            f"{subdomain.name} (ID: {subdomain_id})"
        )

        success_count = 0
        first_successful_path = None

        for url in target_urls:
            try:
                logger.info(f"Capturing screenshot for {url} (Subdomain ID: {subdomain_id})")
                Command.objects.create(
                    command=f"Playwright: screenshot {url}",
                    time=timezone.now(),
                    scan_history_id=scan_id,
                    activity_id=activity_id
                )

                capture_result = run_capture(url, scan_id, results_dir)

                if capture_result["screenshot_path"]:
                    Screenshot.objects.create(
                        subdomain=subdomain,
                        scan_history=scan,
                        url=url,
                        title=capture_result["title"],
                        status_code=capture_result["status_code"],
                        screenshot_path=capture_result["screenshot_path"],
                        html_path=capture_result["html_path"],
                        response_headers=capture_result.get("response_headers", {}),
                        tags=capture_result.get("tags", [])
                    )
                    success_count += 1
                    if not first_successful_path:
                        first_successful_path = capture_result["screenshot_path"]
                    logger.info(f"Successfully saved screenshot for {url}")
                else:
                    logger.warning(f"No screenshot captured for {url}")
            except Exception as capture_err:
                logger.error(f"Error capturing screenshot for {url}: {str(capture_err)}")

        if first_successful_path:
            subdomain.screenshot_path = first_successful_path
            subdomain.save(update_fields=['screenshot_path'])
            return True

    except Subdomain.DoesNotExist:
        logger.error(f"Subdomain with ID {subdomain_id} does not exist.")
    except ScanHistory.DoesNotExist:
        logger.error(f"ScanHistory with ID {scan_id} does not exist.")
    except Exception as e:
        logger.error(f"Error in take_screenshot_and_save: {str(e)}")

    return False
```

- [ ] **Step 1.4: Run tests to confirm they pass**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test tests.test_screenshot_endpoint_collection --verbosity=2 2>&1 | tail -20"
```

Expected: All 4 tests PASS.

- [ ] **Step 1.5: Commit**

```bash
git add web/reNgine/screenshot/tasks.py web/tests/test_screenshot_endpoint_collection.py
git commit -m "fix(screenshot): add url_override to take_screenshot_and_save, preserves full URL path"
```

---

## Task 2: Fix `screenshot()` to query EndPoints directly

**Files:**
- Modify: `web/reNgine/tasks.py` lines 2255–2288
- Test: `web/tests/test_screenshot_endpoint_collection.py` (extend with new class)

- [ ] **Step 2.1: Write the failing tests**

Append to `web/tests/test_screenshot_endpoint_collection.py`:

```python
from unittest.mock import patch, call, MagicMock
from django.test import TestCase
from startScan.models import ScanHistory, Subdomain, EndPoint, Domain


class TestScreenshotEndpointQuery(TestCase):
    """Tests for the screenshot() task — endpoint collection logic."""

    def _make_mock_proxy(self, scan, yaml_config=None):
        """Build a minimal TemporalTaskProxy-shaped mock."""
        proxy = MagicMock()
        proxy.scan = scan
        proxy.scan_id = scan.id
        proxy.results_dir = '/tmp/test_results'
        proxy.activity_id = None
        proxy.yaml_configuration = yaml_config or {}
        proxy.notify = MagicMock()
        return proxy

    def setUp(self):
        self.domain = Domain.objects.create(name='target.com')
        self.scan = ScanHistory.objects.create(
            scan_status='running',
            domain=self.domain,
        )

    def _make_subdomain(self, name, http_status=200):
        return Subdomain.objects.create(
            name=name,
            scan_history=self.scan,
            target_domain=self.domain,
            http_url=f'https://{name}',
            http_status=http_status,
        )

    def _make_default_endpoint(self, subdomain, http_url=None, http_status=200):
        url = http_url or f'https://{subdomain.name}'
        return EndPoint.objects.create(
            http_url=url,
            http_status=http_status,
            scan_history=self.scan,
            target_domain=self.domain,
            subdomain=subdomain,
            is_default=True,
        )

    @patch('reNgine.tasks.take_screenshot_and_save')
    def test_screenshots_all_default_endpoints_normal_intensity(self, mock_save):
        """Normal intensity: all is_default=True endpoints with http_status > 0 are screenshotted."""
        mock_save.return_value = True

        sub1 = self._make_subdomain('a.target.com', http_status=200)
        sub2 = self._make_subdomain('b.target.com', http_status=403)
        sub3 = self._make_subdomain('c.target.com', http_status=200)
        ep1 = self._make_default_endpoint(sub1, 'https://a.target.com', http_status=200)
        ep2 = self._make_default_endpoint(sub2, 'https://b.target.com', http_status=403)
        ep3 = self._make_default_endpoint(sub3, 'https://c.target.com', http_status=200)

        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        # ep1 and ep3 have http_status > 0; ep2 does too (403 > 0), so all 3 pass
        self.assertEqual(mock_save.call_count, 3)
        called_urls = {c.kwargs['url_override'] for c in mock_save.call_args_list}
        self.assertIn('https://a.target.com', called_urls)
        self.assertIn('https://b.target.com', called_urls)
        self.assertIn('https://c.target.com', called_urls)

    @patch('reNgine.tasks.take_screenshot_and_save')
    def test_normal_intensity_excludes_zero_status_endpoints(self, mock_save):
        """Normal intensity excludes default endpoints where http_status == 0 (unreachable)."""
        mock_save.return_value = True

        alive_sub = self._make_subdomain('alive.target.com', http_status=200)
        dead_sub = self._make_subdomain('dead.target.com', http_status=0)
        self._make_default_endpoint(alive_sub, 'https://alive.target.com', http_status=200)
        self._make_default_endpoint(dead_sub, 'https://dead.target.com', http_status=0)

        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        self.assertEqual(mock_save.call_count, 1)
        called_url = mock_save.call_args.kwargs['url_override']
        self.assertEqual(called_url, 'https://alive.target.com')

    @patch('reNgine.tasks.take_screenshot_and_save')
    def test_non_default_endpoints_are_skipped(self, mock_save):
        """Endpoints with is_default=False are never passed to screenshot capture."""
        mock_save.return_value = True

        sub = self._make_subdomain('sub.target.com', http_status=200)
        self._make_default_endpoint(sub, 'https://sub.target.com/root', http_status=200)
        # Non-default endpoint — should be ignored
        EndPoint.objects.create(
            http_url='https://sub.target.com/api/v1',
            http_status=200,
            scan_history=self.scan,
            target_domain=self.domain,
            subdomain=sub,
            is_default=False,
        )

        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        self.assertEqual(mock_save.call_count, 1)
        called_url = mock_save.call_args.kwargs['url_override']
        self.assertEqual(called_url, 'https://sub.target.com/root')

    @patch('reNgine.tasks.take_screenshot_and_save')
    def test_full_url_with_path_is_passed(self, mock_save):
        """The full http_url including path is passed as url_override — not stripped to scheme://netloc."""
        mock_save.return_value = True

        sub = self._make_subdomain('panel.target.com', http_status=200)
        self._make_default_endpoint(sub, 'https://panel.target.com/admin/login', http_status=200)

        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        called_url = mock_save.call_args.kwargs['url_override']
        self.assertEqual(called_url, 'https://panel.target.com/admin/login')
        self.assertNotEqual(called_url, 'https://panel.target.com')

    @patch('reNgine.tasks.take_screenshot_and_save')
    def test_no_endpoints_no_screenshots(self, mock_save):
        """With no default endpoints, screenshot() completes without calling capture."""
        proxy = self._make_mock_proxy(self.scan, {'intensity': 'normal'})

        from reNgine.tasks import screenshot
        screenshot(proxy)

        mock_save.assert_not_called()
```

- [ ] **Step 2.2: Run tests to confirm they fail**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test tests.test_screenshot_endpoint_collection.TestScreenshotEndpointQuery --verbosity=2 2>&1 | tail -30"
```

Expected: Tests FAIL — `screenshot()` still uses the Subdomain loop and doesn't pass `url_override`.

- [ ] **Step 2.3: Replace the `screenshot()` function in `tasks.py`**

Find the function at line 2255 and replace it. The old function signature starts at `def screenshot(self, ctx={}, description=None):` and ends at `return True` (line 2288). Replace the function body only:

```python
def screenshot(self, ctx={}, description=None):
    """Embedded Playwright Screenshot task.

    Queries is_default=True endpoints directly — one per subdomain root — and
    passes the full http_url (including path) to the capture engine.
    This mirrors the rengine-ng approach and fixes the single-screenshot bug
    caused by the Subdomain http_url/http_status strict filter.

    Args:
        description (str, optional): Task description shown in UI.
    """
    from reNgine.screenshot.tasks import take_screenshot_and_save

    config = self.yaml_configuration.get(SCREENSHOT) or {}
    intensity = config.get(INTENSITY) or self.yaml_configuration.get(INTENSITY, DEFAULT_SCAN_INTENSITY)
    strict = intensity == 'normal'

    # Query default endpoints directly — one per subdomain root, same approach as rengine-ng.
    # Avoids the Subdomain http_url/http_status gap that caused only 1 screenshot per scan.
    endpoints = (
        EndPoint.objects
        .filter(scan_history=self.scan, is_default=True)
        .exclude(http_url__isnull=True)
        .exclude(http_url='')
        .select_related('subdomain')
    )

    if strict:
        endpoints = endpoints.filter(http_status__gt=0)

    logger.info(f"Starting Playwright screenshot capture for {endpoints.count()} default endpoints...")

    success_count = 0
    for endpoint in endpoints:
        if take_screenshot_and_save(
            subdomain_id=endpoint.subdomain_id,
            scan_id=self.scan_id,
            results_dir=self.results_dir,
            activity_id=self.activity_id,
            url_override=endpoint.http_url,
        ):
            success_count += 1

    self.notify(fields={'Screenshots': f'Successfully captured {success_count} screenshots using Embedded Playwright.'})
    return True
```

- [ ] **Step 2.4: Run all screenshot tests**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test tests.test_screenshot_endpoint_collection --verbosity=2 2>&1 | tail -30"
```

Expected: All 9 tests PASS.

- [ ] **Step 2.5: Run the full test suite to catch regressions**

```bash
docker exec -it r3ngine-web-1 bash -c \
  "cd /usr/src/app && python3 manage.py test --verbosity=1 2>&1 | tail -20"
```

Expected: Same or better pass count vs baseline — no new failures.

- [ ] **Step 2.6: Commit**

```bash
git add web/reNgine/tasks.py web/tests/test_screenshot_endpoint_collection.py
git commit -m "fix(screenshot): query is_default endpoints directly, pass full URL — fixes single-screenshot bug"
```

---

## Self-Review Checklist

### Spec coverage
- [x] Bug 1 (Subdomain filter causes single screenshot): fixed in Task 2 — `screenshot()` queries EndPoints directly
- [x] Bug 2 (path stripping): fixed in Task 1 — `url_override` bypasses the base-URL collapse
- [x] rengine-ng approach mirrored: `is_default=True` + `http_status__gt=0` filter (strict mode)
- [x] Backward compatibility: `take_screenshot_and_save` without `url_override` still works (legacy path unchanged)
- [x] Tests cover: multi-endpoint scan, dead-subdomain exclusion, non-default endpoint exclusion, full URL preservation, no-endpoint scenario

### Placeholder scan
- No TBD/TODO in plan
- All code blocks complete
- Test classes and function names consistent across both tasks

### Type consistency
- `url_override` parameter name consistent in Task 1 (definition) and Task 2 (call site)
- `subdomain_id=endpoint.subdomain_id` — correct FK accessor (not `endpoint.subdomain.id` which would require the join)
- `mock_save.call_args.kwargs` — valid for Python 3.8+; if running 3.7, use `mock_save.call_args[1]`
