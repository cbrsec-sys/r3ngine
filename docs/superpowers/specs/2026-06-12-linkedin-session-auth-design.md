# LinkedIn Intelligence — Session-Based Authentication Design

**Date:** 2026-06-12  
**Branch:** apme-enhancement  
**Status:** Approved — ready for implementation planning

---

## Problem

The existing `LinkedInScraper` uses `launch_persistent_context()` (Chromium user data directory) and authenticates with a stored username and password. This approach fails with a `Timeout 30000ms exceeded` error because LinkedIn detects automated login and may challenge with MFA/2FA, which a headless browser cannot complete. The scan halts or errors on the LinkedIn OSINT tier.

---

## Goals

1. Replace credential-based login with session-state authentication.
2. Support two authentication paths that share a common session model.
3. Never store a LinkedIn password in the system.
4. If LinkedIn authentication fails at scan time, log a note and continue — do not fail or stop the scan.

---

## Authentication Priority (at scan time)

1. **`storage_state.json` file** — load the saved Playwright session state from the Docker volume and validate the session by navigating to `/feed/`.
2. **Cookie injection from vault** — if the state file is missing or invalid, inject the `cookies_json` stored in the database into a fresh browser context and validate.
3. **Graceful skip** — if both paths fail, write a structured note to the scan activity log and return an empty employee list. The scan continues.

---

## Section 1 — Data Model

### `LinkedInCredentials` (updated)

| Field | Type | Notes |
|---|---|---|
| `username` | CharField(500) | Display only — not used for login |
| `cookies_json` | TextField | Serialised LinkedIn session cookies — Playwright format: JSON array of `{name, value, domain, path, httpOnly, secure, sameSite}` dicts |
| `state_file_path` | CharField(500) | Absolute path to `storage_state.json` on the results volume |
| `last_validated_at` | DateTimeField (nullable) | Set after each successful session check |
| `is_valid` | BooleanField | Set False when both auth paths fail |

**Migration required:** Remove the `password` field. Add `cookies_json`, `state_file_path`, `last_validated_at`, `is_valid`.

### Session storage location

`storage_state.json` is written to `{RENGINE_RESULTS}/context/linkedin/storage_state.json` on the shared Docker volume, consistent with the existing `context_path` convention.

---

## Section 2 — `LinkedInScraper` Architecture

File: `web/reNgine/osint/linkedin_intelligence.py`

### Constructor

```python
LinkedInScraper(session: LinkedInCredentials, hunter_key: str)
```

Accepts a `LinkedInCredentials` instance instead of username/password strings. Accumulates warnings in `self.notes: list[str]`.

### Authentication flow

```
authenticate() -> bool
  1. _try_storage_state()
       - load state_file_path via browser.new_context(storage_state=...)
       - call _validate_session()
       - if valid: update session.is_valid=True, last_validated_at=now(); return True
  2. _try_cookie_injection()
       - parse session.cookies_json (Playwright cookie dict list: name/value/domain/path)
       - context.add_cookies([...])
       - call _validate_session()
       - if valid: _save_state(); session.is_valid=True; return True
  3. session.is_valid = False; session.save()
     self.notes.append("[OSINT][LinkedIn] Session invalid ...")
     return False
```

### Session validation

```
_validate_session() -> bool
  - page.goto("https://www.linkedin.com/feed/", wait_until="networkidle")
  - return False if "login" in page.url or sign-in button present
  - return True otherwise
  - catches all exceptions → return False
```

### State persistence

```
_save_state()
  - context.storage_state(path=session.state_file_path)
  - session.last_validated_at = timezone.now()
  - session.save(update_fields=["state_file_path", "last_validated_at", "is_valid"])
```

### `discover_employees()` contract

```python
def discover_employees(company_name, domain, scan_history) -> list[dict]:
```

- Calls `authenticate()` first.
- If auth returns `False`: appends note, returns `[]`.
- All scraping exceptions are caught internally — method never raises.
- Returns a list of `{name, designation, email}` dicts (same shape as today).

### Return from `run_linkedint()`

`run_linkedint()` in `osint_tasks.py` receives the employee list. Notes from `scraper.notes` are written to the `ScanActivity` log entry for the OSINT tier. The function always returns the list (empty on failure) and never raises.

### Scan-level note format

```
[OSINT][LinkedIn] Session invalid and cookie injection failed —
LinkedIn intelligence skipped. Re-authenticate via Settings → API Keys.
```

---

## Section 3 — Session Management API & Frontend

### New API endpoints

All endpoints under `/api/v1/linkedin/`, JWT-authenticated (`IsAuthenticated`).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/linkedin/session/upload/` | Upload `storage_state.json` (multipart) **or** submit `cookies_json` payload |
| `GET` | `/api/v1/linkedin/session/status/` | Returns `{is_valid, last_validated_at, username, has_state_file, has_cookies}` |
| `DELETE` | `/api/v1/linkedin/session/` | Deletes `storage_state.json` from disk, clears `cookies_json` and `state_file_path` in DB, sets `is_valid=False` |

Upload endpoint saves the state file to `{RENGINE_RESULTS}/context/linkedin/storage_state.json` and updates `state_file_path` on the `LinkedInCredentials` singleton.

### Downloadable helper script

`GET /api/v1/linkedin/session/helper-script/` — serves a static `linkedin_capture.py` file. This standalone Python script:

1. Launches headed Chromium via `sync_playwright`.
2. Navigates to `https://www.linkedin.com/login`.
3. Waits for the user to complete login (including MFA) — `page.wait_for_url("**/feed/**", timeout=0)`.
4. Calls `context.storage_state(path="storage_state.json")`.
5. Exits. User uploads the resulting file via the UI.

### Frontend — LinkedIn card (existing API Keys settings page)

```
┌─ LinkedIn Intelligence ─────────────────────────────────────────┐
│  Status:  ● Active  (last validated 2h ago)                     │
│  Account: scott@example.com                                     │
│                                                                 │
│  [ Upload session state ]   [ Revoke session ]                  │
│                                                                 │
│  Instructions: Run the helper script on your local machine,     │
│  log in to LinkedIn in the browser that opens, then upload      │
│  the exported storage_state.json here.                          │
│                                                                 │
│  [ Download helper script ]                                     │
└─────────────────────────────────────────────────────────────────┘
```

Status dot: green (valid), amber (unknown/not validated recently), red (invalid/missing).

---

## Out of Scope

- In-container VNC/CDP guided login (can be added as a future enhancement).
- Session auto-renewal (requires stored credentials — excluded by design).
- LinkedIn API usage (violates ToS differently; out of scope).

---

## Files Affected

| File | Change |
|---|---|
| `web/dashboard/models.py` | Remove `password`, add `cookies_json`, `state_file_path`, `last_validated_at`, `is_valid` |
| `web/dashboard/migrations/` | New migration for model change |
| `web/reNgine/osint/linkedin_intelligence.py` | Rewrite `LinkedInScraper` — session-based auth |
| `web/reNgine/osint_tasks.py` | Update `run_linkedint()` — use session object, write notes |
| `web/api/views.py` | Add `LinkedInSessionUploadView`, `LinkedInSessionStatusView`, `LinkedInSessionDeleteView`, helper script endpoint |
| `web/api/urls.py` | Register new routes |
| `web/reNgine/static/linkedin_capture.py` | New helper script (static file served by Django) |
| `frontend/src/components/` | New `LinkedInSessionCard` component |
| `frontend/src/api/` | New `linkedin.ts` API client functions |
| `web/scanEngine/views.py` | Remove password field from LinkedIn credential save logic |
| `web/tests/test_linkedin_session.py` | New test file |
