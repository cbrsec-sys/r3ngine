# Directory File Action Menu — Design Spec
**Date:** 2026-06-16  
**Version:** v3.6.0  
**Status:** Approved — ready for implementation planning

---

## Overview

Add a `MoreHorizontal` action menu to each `DirectoryFile` row in the **Directories** tab (Directory Fuzzing Results). The menu replaces the current rightmost element on each file row and allows users to dispatch security testing actions against that specific endpoint URL. Follows the `VulnerabilityTable` action menu pattern exactly; all colours use theme tokens (no hardcoded hex).

---

## Architecture

```
DirectoriesTab.tsx (frontend)
  └─ MoreHorizontal icon on each DirectoryFile row
       └─ MUI Menu → MenuItem (action selected)
            └─ useDirectoryFileDispatch() mutation
                 └─ POST /api/action/directory-file/dispatch/   (new)
                       ├─ scan_vuln    → starts url-vuln workflow (XSS/IDOR/LFI/SSRF via Dalfox + gf)
                       ├─ deep_fuzz   → starts url-fuzz workflow
                       ├─ bypass_waf  → starts url-bypass workflow
                       ├─ secret_scan → starts url-dirsearch workflow (hunt_secrets: true)
                       ├─ extract_auth → starts URLAuthExtractWorkflow (new)
                       └─ brute_test  → checks credential_intelligence plugin → plugin workflow

DirectoriesTab.tsx also calls:
  POST /api/action/directory-file/delete/   (new)
  usePlugins() hook (existing)              — gates brute_test item
```

Two new backend endpoints. Zero changes to existing workflows. The frontend never needs to know which internal workflow each action maps to.

---

## Backend

### New endpoints

#### `POST /api/action/directory-file/dispatch/`
```
Request  { url: str, action: str, scan_id: int }
Response { status: "dispatched", workflow_id: str }

Actions:
  scan_vuln    → url-vuln workflow
  deep_fuzz    → url-fuzz workflow
  bypass_waf   → url-bypass workflow
  secret_scan  → url-dirsearch workflow with yaml: {url_dirsearch: {hunt_secrets: true}}
  extract_auth → URLAuthExtractWorkflow (new Temporal workflow)
  brute_test   → credential_intelligence plugin workflow (403 if plugin disabled)

Auth: IsAuthenticated
CSRF: X-CSRFToken header required
Validation: 400 if url/action/scan_id missing or action unknown
```

#### `POST /api/action/directory-file/delete/`
```
Request  { directory_file_ids: [int] }
Response { deleted: int }

Auth: IsAuthenticated
CSRF: X-CSRFToken header required
```

Both views added to `web/api/views.py` and registered in `web/api/urls.py`:
```python
path('action/directory-file/dispatch/', DirectoryFileDispatchView.as_view()),
path('action/directory-file/delete/',   DirectoryFileDeleteView.as_view()),
```

### New Temporal pieces

**`ExtractAuthForURLActivity`** (`web/reNgine/temporal_activities.py`)
- Wraps the single-URL path of `extract_auth_candidates` from `auth_discovery_tasks.py`
- Accepts `ctx: dict` containing `url` and `scan_id`
- Logs START and COMPLETE/ERROR per project convention using `get_module_logger`
- Section prefix: `[AUTH_EXTRACT]`

**`URLAuthExtractWorkflow`** (`web/reNgine/temporal_workflows.py`)
- Thin orchestrator — calls `ExtractAuthForURLActivity` only
- `start_to_close_timeout=timedelta(minutes=10)`
- No DB calls in workflow body (determinism rule)

**Registration:** `ExtractAuthForURLActivity` added to `activities=[]` in `web/scanEngine/management/commands/run_temporal_orchestrator.py`

### Type update

`DirectoryFile` serializer already uses `fields = '__all__'` so `id` is returned by the API. Add `id: number` to the TypeScript `DirectoryFile` interface in `frontend/src/features/subdomains/types/index.ts`.

---

## Frontend

### Files changed
| File | Change |
|------|--------|
| `frontend/src/features/scans/components/DirectoriesTab.tsx` | Add action menu state, JSX, handlers |
| `frontend/src/features/scans/api/index.ts` | Add `useDirectoryFileDispatch`, `useDirectoryFileDelete` |
| `frontend/src/features/subdomains/types/index.ts` | Add `id: number` to `DirectoryFile` |

### Action menu items

| # | Label | Icon | Token | Condition |
|---|-------|------|-------|-----------|
| 1 | Extract Auth | `KeyRound` | `warning.main` | Always |
| 2 | Scan Vulnerabilities | `ShieldAlert` | `error.main` | Always |
| 3 | Deep Fuzz | `Crosshair` | `info.main` | Always |
| 4 | Secret Scan | `ScanSearch` | `success.main` | Always |
| 5 | WAF Bypass | `Zap` | `secondary.main` | Always |
| — | *(divider)* | | | |
| 6 | Send to Brute Test | `UserX` | `warning.main` | Shown always; disabled + Tooltip if `credential_intelligence` not enabled |
| — | *(divider)* | | | |
| 7 | Copy URL | `Copy` | `text.secondary` | Always (client-side clipboard) |
| 8 | Open in Browser | `ExternalLink` | `text.secondary` | Always (window.open) |
| — | *(divider)* | | | |
| 9 | Delete | `Trash2` | `error.main` | Always, with ConfirmDialog |

### State added to `DirectoriesTab`
```typescript
const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
const [selectedFile, setSelectedFile] = useState<DirectoryFile | null>(null);
const [confirmOpen, setConfirmOpen] = useState(false);
const [confirmConfig, setConfirmConfig] = useState<ConfirmConfig>({ title: '', message: '', onConfirm: () => {} });
const [snackbar, setSnackbar] = useState<SnackbarState>({ open: false, message: '', severity: 'success' });

const { data: plugins } = usePlugins();
const credPluginEnabled = plugins?.some(p => p.slug === 'credential_intelligence' && p.is_enabled);

const dispatchMutation = useDirectoryFileDispatch();
const deleteMutation = useDirectoryFileDelete();
```

### API mutation hooks (`scans/api/index.ts`)
```typescript
useDirectoryFileDispatch()
  POST /api/action/directory-file/dispatch/
  body: { url: string; action: string; scan_id: number }
  returns: { status: string; workflow_id: string }

useDirectoryFileDelete()
  POST /api/action/directory-file/delete/
  body: { directory_file_ids: number[] }
  invalidates: ['directories'] query on success
```

### Trigger button placement
`MoreHorizontal` icon button added at the end of each `DirectoryFile` row, placed after the existing external link icon. Styling matches `VulnerabilityTable`:
- Rest state: `theme.palette.text.secondary`
- Hover state: `isLight ? theme.palette.primary.main : theme.palette.primary.light`
- No hardcoded hex anywhere

### Loading / feedback
- **`Backdrop` + `CircularProgress`** while any mutation is pending; label updates per active action (e.g. `DISPATCHING VULNERABILITY SCAN...`)
- **`Snackbar`** on success and error
- **`ConfirmDialog`** (`type: 'danger'`) before delete executes

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Dispatch succeeds | Snackbar: action-specific label e.g. `"VULNERABILITY SCAN DISPATCHED"` |
| Dispatch fails | Snackbar error: `"Failed to dispatch — check Temporal logs"` |
| Delete succeeds | Snackbar success + directories query invalidated |
| Delete fails | Snackbar error |
| `credential_intelligence` not enabled | Menu item disabled + Tooltip: `"Credential Intelligence plugin not installed"` |
| Auth extract dispatched | Snackbar: `"AUTH EXTRACTION QUEUED"` — result appears in Auth Candidates table |
| Unknown action | Backend 400 `{"error": "Unknown action"}` |
| Missing fields | Backend 400 with field-level validation errors |

---

## Tests

### Backend (`web/tests/test_directory_file_actions.py`)
- Each action in dispatch view routes to the correct workflow slug
- `extract_auth` starts `URLAuthExtractWorkflow`
- `brute_test` with plugin disabled returns 403
- `brute_test` with plugin enabled dispatches to plugin workflow
- Delete endpoint deletes records and returns correct count
- Missing / invalid fields return 400

### Temporal unit tests
- `ExtractAuthForURLActivity` calls `extract_auth_candidates` for the provided URL
- START and COMPLETE log lines emitted
- Activity registered in `run_temporal_orchestrator.py`

---

## Constraints

- All frontend colours via theme tokens — no hardcoded hex
- `DirectoriesTab` receives `scanId` as a direct prop — pass it through to dispatch calls
- `URLAuthExtractWorkflow` must not import Django directly; use `workflow.unsafe.imports_passed_through()` for any constant imports
- All activities must be idempotent (Temporal may retry)
- `brute_test` requires `credential_intelligence` plugin to be both installed and `is_enabled: true`
