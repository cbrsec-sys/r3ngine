---
name: r3ngine-context
description: Provides the r3ngine project technology stack, architecture, and conventions. Use when contributing to r3ngine, implementing features, debugging scans, or when the user asks about the stack, Django, Temporal, Neo4j, React, PostgreSQL, security tools, or the codebase structure.
---

# r3ngine Context

Project context and technology stack for the r3ngine v3 web reconnaissance and vulnerability scanning platform.

## When to Use

- Contributing code, fixing bugs, or adding features in this repository
- User asks about the stack, frameworks, or how the app is built
- Implementing or modifying scans, targets, API, or UI
- Need to know which versions are in use (Django 3.2, Python 3.12, Temporal 1.6.0, React 18+)
- Debugging Temporal workflow failures or scan pipeline issues

## Stack Summary

| Layer        | Technology |
|-------------|------------|
| Backend     | Django 3.2, Python 3.12 |
| DB (primary)| PostgreSQL |
| DB (graph)  | Neo4j (attack path modeling) |
| Cache/Broker| Redis (Channels, task state, caching) |
| Orchestration | Temporal (Python SDK 1.6.0 + Go executor) |
| Frontend    | React 18+, TypeScript, Vite |
| Async comms | Django Channels + WebSockets |
| Containers  | Docker multi-stage + Docker Compose |
| Quality     | flake8, black, type hints, tests in `web/tests/` |

- **Paths**: App code under `web/`; frontend under `frontend/`.
- **API**: Django REST Framework + JWT auth; `ws://localhost:8000/ws/scan/{scan_id}/` for WebSocket.
- **Temporal UI**: `http://localhost:8080` — workflow history, signals, replay, cancellation.
- **Logging**: `get_module_logger(__name__)` from `reNgine.utils.logger`; use `log_line(prefix, action, msg)` for structured output; `format_exception_for_log(exc)` for safe exception text; `%`-style formatting for user-controlled data in plain log calls.
- **Container name**: `r3ngine-web-1` (use `python3` not `python` inside the container).

## Scan Pipeline (7-Tier Architecture)

| Tier | Purpose |
|------|---------|
| 0 | Target profiling & context enrichment |
| 1 | Subdomain discovery, intel gathering, firewall detection |
| 2 | HTTP crawl, port scanning, screenshotting, URL fetching |
| 3–4 | Directory/file fuzzing (ffuf, dirsearch, katana) |
| 5 | Web API discovery, WAF detection, secret scanning |
| 6 | Vulnerability scanning (Nuclei), WAF bypass, credential brute force |
| 7 | Vulnerability correlation, risk scoring, Neo4j sync, reporting |

Scan entry point: `initiate_scan_temporal()` in `tasks.py` → starts `MasterScanWorkflow`.

## Key Conventions (from project rules)

- Code and comments in English; SOLID, KISS, DRY.
- Type hints on all new Python code; TypeScript types on all new frontend code.
- Tests for every change; `django.test.TestCase`; anonymise test data.
- Private methods at the bottom of the file.
- No path constructed from user input without validation (resolve + bounds-check).
- No raw exception messages returned to the client.
- `temporal_workflows.py` must stay deterministic — no DB calls, no I/O, no `datetime.now()`.
- All scanning logic belongs in `temporal_activities.py` or the Go executor.
- Run tests inside Docker: `docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test"`

## Temporal Quick Reference

- Workflows (deterministic): `web/reNgine/temporal_workflows.py`
- Activities (side-effecting): `web/reNgine/temporal_activities.py`
- Client (start/cancel from Django): `web/reNgine/temporal_client.py`
- Go executor (subprocess tools): `web/executor/main.go` on `go-executor-queue`

## Additional Reference

- Full stack and modules: [reference.md](reference.md)
- Security tools (recon, fuzzers, vuln scanners): [references/tools.md](references/tools.md)