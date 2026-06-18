# Design: web_api_discovery Tier Reorder + CPDE JS Collection Fix

**Date:** 2026-06-18
**Branch:** pr-57
**Status:** Approved

---

## Problem Statement

Two related bugs in the scan pipeline:

1. **Ordering bug**: `web_api_discovery` (kiterunner) runs at Tier 5, after CPDE has already
   executed at Tier 3b. CPDE's `url_param_collector.collect_from_kiterunner_files()` reads
   `kr_*.json` output from kiterunner — but those files don't exist yet when CPDE runs.
   paramspider, linkfinder, and arjun also have no API endpoints to work with because
   web_api_discovery hasn't populated the DB or results_dir yet.

2. **JS collection bug**: `js_collector.get_js_urls_from_katana_output()` reads only
   `urls_katana.txt`. JS files (e.g. `.js?ver=*`, `bundle.min.js`) discovered by gau,
   gospider, waybackurls, or hakrawler are written to `urls_gau.txt`, `urls_gospider.txt`,
   etc. — none of which js_collector reads. The AST analyzer therefore misses all JS
   URLs found by non-Katana tools.

---

## Current Tier Ordering (MasterScanWorkflow)

| Tier | Tasks |
|------|-------|
| T3   | `fetch_url` + `screenshot` (parallel) |
| T3a  | `http_crawl_bridge` |
| T3b  | `param_discovery` (CPDE) |
| T4   | `dir_file_fuzz` |
| T5   | `web_api_discovery` + `waf_detection` + `secret_scanning` + `vigolium_analysis` (parallel) |

---

## Proposed Tier Ordering

| Tier | Tasks |
|------|-------|
| T3   | `fetch_url` + `screenshot` (parallel, unchanged) |
| T3a  | `http_crawl_bridge` (unchanged) |
| T3b  | `web_api_discovery` ← moved from T5 |
| T3c  | `param_discovery` (CPDE) ← was T3b |
| T4   | `dir_file_fuzz` (unchanged) |
| T5   | `waf_detection` + `secret_scanning` + `vigolium_analysis` (`web_api_discovery` removed) |

`web_api_discovery` is now sequential and isolated at T3b so its `kr_*.json` output files
and DB-persisted endpoints are available before CPDE runs.

---

## Change 1: MasterScanWorkflow — web_api_discovery moves to T3b

**File:** `web/reNgine/temporal_workflows.py`

### Approach

Use `workflow.patched("web-api-to-tier-3b")` — the same guard pattern already used for
`http_crawl_bridge` — so that in-flight workflows replay their recorded history
(where `web_api_discovery` was a T5 parallel future) without hitting a nondeterminism error.

New workflows (patched=True) execute `RunWebAPIDiscoveryActivity` between T3a and CPDE.
Old workflows (patched=False, replaying) skip T3b and still run `RunWebAPIDiscoveryActivity`
in the T5 `analysis_futures` gather as before.

### Pseudocode diff

```python
# After T3a (http_crawl_bridge), before T3b (CPDE):
if "web_api_discovery" in tasks and workflow.patched("web-api-to-tier-3b"):
    await workflow.execute_activity(
        "RunWebAPIDiscoveryActivity",
        ctx,
        start_to_close_timeout=timedelta(hours=4),
        heartbeat_timeout=timedelta(minutes=10),
        retry_policy=_RETRY_NETWORK_SCAN,
        task_queue="python-orchestrator-queue",
    )

# T3b becomes T3c (CPDE, unchanged code, just renumbered in comments)

# T5 analysis_futures: remove web_api_discovery from the parallel gather,
# but keep it in the else-branch of the patch guard for replay compatibility.
analysis_futures = []
if "web_api_discovery" in tasks and not workflow.patched("web-api-to-tier-3b"):
    analysis_futures.append(workflow.execute_activity("RunWebAPIDiscoveryActivity", ...))
if "waf_detection" in tasks:
    analysis_futures.append(...)
# ... etc
```

---

## Change 2: SubScanWorkflow — tier list update

**File:** `web/reNgine/temporal_workflows.py` (SubScanWorkflow `tiers` list)

SubScanWorkflow uses a plain Python list of tier sets — no `workflow.patched()` needed
(subscans are short-lived and the list is reevaluated on every execution).

### Diff

```python
# Before (tier 3b and tier 5):
[t for t in active_tasks if t == "param_discovery"],          # T3b
...
[t for t in active_tasks if t in {                            # T5
    "web_api_discovery", "waf_detection", "secret_scanning", "vigolium_analysis"
}],

# After:
[t for t in active_tasks if t == "web_api_discovery"],        # T3b (new)
[t for t in active_tasks if t == "param_discovery"],          # T3c (was T3b)
...
[t for t in active_tasks if t in {                            # T5
    "waf_detection", "secret_scanning", "vigolium_analysis"   # web_api_discovery removed
}],
```

Also update the fallback "not in" set at the bottom to include `"web_api_discovery"`.

---

## Change 3: js_collector — read all fetch_url tool outputs

**File:** `web/reNgine/cpde/js_collector.py`

### Root cause

`KATANA_OUTPUT_FILENAME = 'urls_katana.txt'` is hardcoded. Tools like gau, gospider,
waybackurls, and hakrawler write to `urls_gau.txt`, `urls_gospider.txt`, etc. All of
these files are present in `results_dir` after fetch_url completes.
`url_param_collector.collect_from_url_files()` already globs `urls_*.txt` correctly.

### Fix

Rename `get_js_urls_from_katana_output(results_dir)` to `get_js_urls_from_results_dir(results_dir)`.
Replace the single-file open with a glob over all `urls_*.txt` files. The existing
`seen` set already deduplicates URLs; `download_js_files` deduplicates by SHA-256 hash.

```python
def get_js_urls_from_results_dir(results_dir: str) -> list[str]:
    """Read all urls_*.txt files and return discovered JS file URLs."""
    import glob as _glob
    pattern = os.path.join(results_dir, 'urls_*.txt')
    file_paths = _glob.glob(pattern)

    js_urls = []
    seen = set()
    for filepath in file_paths:
        try:
            with open(filepath, encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    url = line.strip()
                    if url and url not in seen and _JS_URL_RE.match(url):
                        seen.add(url)
                        js_urls.append(url)
        except OSError as exc:
            logger.error('[CPDE:js_collector] Failed to read %s: %s', filepath, exc)

    logger.info('[CPDE:js_collector] Found %d unique JS URLs across %d url files',
                len(js_urls), len(file_paths))
    return js_urls
```

Update the call site in `cpde_tasks.py`:
```python
# Before:
js_urls = js_collector.get_js_urls_from_katana_output(results_dir)
# After:
js_urls = js_collector.get_js_urls_from_results_dir(results_dir)
```

---

## Files Changed

| File | Change |
|------|--------|
| `web/reNgine/temporal_workflows.py` | MasterScanWorkflow: add T3b web_api_discovery block with patched guard; update T5 to skip web_api_discovery when patched |
| `web/reNgine/temporal_workflows.py` | SubScanWorkflow: insert web_api_discovery tier between http_crawl_bridge and param_discovery; remove from T5 set |
| `web/reNgine/cpde/js_collector.py` | Rename function, glob all `urls_*.txt` instead of only `urls_katana.txt` |
| `web/reNgine/cpde_tasks.py` | Update call site to use new function name |

---

## Tests Required

- `web/tests/test_cpde_js_collector.py` — new/updated tests covering multi-file glob, `.js?ver=` URLs, and `bundle.min.js` discovered from non-Katana tool files
- `web/tests/test_temporal_workflows.py` or equivalent — verify patched/unpatched branches both compile; mock activity execution to confirm web_api_discovery runs at T3b in new workflows
- `web/tests/test_url_param_collector.py` — confirm kiterunner files present after web_api_discovery are picked up by CPDE (integration-style test with mocked results_dir)

---

## Non-Goals

- No change to the web_api_discovery activity implementation itself
- No change to when waf_detection, secret_scanning, or vigolium_analysis run
- No change to the CPDE correlation engine or parameter persistence logic
