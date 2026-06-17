# r3ngine — Full Stack Reference

Loaded on demand when detailed stack or module information is needed.

## Core Technologies

### Backend
- **Django** 3.2 (LTS): ORM, REST API (DRF 3.12.4), auth, permissions
- **Python** 3.12: backend logic, task functions, Temporal activities
- **temporalio** 1.6.0: workflow and activity SDK (replaced Celery entirely in v3.2.0)
- **channels** 3.0.5: WebSocket support via Redis channel layer
- **Playwright** 1.42.0: headless browser (screenshotting)

### Database
- **PostgreSQL**: primary persistent storage
- **Neo4j** 5.23.1: graph database for Attack Path Modeling Engine (APME) — Cypher queries via `Neo4jManager` in `web/reNgine/graph_utils.py`
- **Redis**: channel layer (WebSocket), task state, caching

### Frontend
- **React 18+**, TypeScript, Vite bundler
- State: Zustand stores (`frontend/src/store/`)
- API client layer: `frontend/src/api/`
- Components: `frontend/src/components/`
- Pages: `frontend/src/pages/`

### Deployment
- **Docker** / Docker Compose (development + production)
- Django dev server (development), Gunicorn/Daphne (production)
- All `manage.py` commands must run inside the container (`r3ngine-web-1`)
- Use `python3` (not `python`) inside the container

### Quality & Tooling
- **flake8**: lint; **black**: format
- Django test framework; tests under `web/tests/`

## Temporal Architecture

```
Django REST API
    ↓
temporal_client.py (start / cancel)
    ↓
Temporal Server
    ├─ Python orchestrator worker  →  temporal_workflows.py
    │                              →  temporal_activities.py (DB, Neo4j, HTTP)
    └─ Go executor worker          →  executor/main.go (subprocess tools)
```

- **Workflows** (`temporal_workflows.py`): deterministic orchestrators; no I/O
- **Activities** (`temporal_activities.py`): 30+ activities; DB, Neo4j, HTTP, LLM calls
- **Go executor** (`executor/main.go`): subprocess management for 30+ security tools
- **Temporal UI**: `http://localhost:8080`

## Key Modules

- **startScan** (core domain):
  - `startScan/models.py`: `ScanHistory`, `Subdomain`, `EndPoint`, `Vulnerability`, `Parameter`, `ScanActivity`, `TemporalWorkflowExecution`
  - `startScan/views.py`: scan management REST endpoints
- **scanEngine**:
  - `scanEngine/models.py`: `EngineType` (YAML scan config templates), `InstalledExternalTool`
- **reNgine app** (shared logic):
  - `reNgine/tasks.py`: task functions called by activities (no `@app.task` decorators)
  - `reNgine/temporal_workflows.py`: `MasterScanWorkflow`, `SubScanWorkflow`
  - `reNgine/temporal_activities.py`: 30+ `@activity.defn` functions
  - `reNgine/temporal_client.py`: `TemporalClientProvider` (sync/async bridge)
  - `reNgine/graph_utils.py`: `Neo4jManager` for APME Cypher queries
  - `reNgine/llm.py`, `reNgine/llm_utils.py`: LLM integration with PII anonymisation
  - `reNgine/common_func.py`: shared utilities
  - `reNgine/definitions.py`: enums, constants, task status values
  - `reNgine/utils/logger.py`: `get_module_logger`, `ModuleLogger`, `format_exception_for_log`
  - `reNgine/utils/opsec.py`: proxy rotation, OpSec controls
  - `reNgine/utils/task.py`: task utility helpers
- **api app**:
  - `api/views.py`: additional REST endpoints (subdomains, endpoints, vulnerabilities)
  - `api/urls.py`: URL routing for the API
- **plugins app**:
  - `plugins/views.py`: plugin management endpoints

## Database Model Key Entities

| Model | Purpose |
|-------|---------|
| `ScanHistory` | Top-level scan record with status, config, Temporal workflow ID |
| `Subdomain` | Discovered subdomains with scan context |
| `EndPoint` | HTTP endpoints (URL + method + parameters) |
| `Vulnerability` | Findings with severity, status, correlation state |
| `Parameter` | Extracted form/query parameters |
| `ScanActivity` | Granular activity log per scan step |
| `EngineType` | YAML-based scan configuration templates |
| `TemporalWorkflowExecution` | FK from ScanHistory to running workflow ID |

## Neo4j Graph Design (APME)

- **Nodes**: Domains, Subdomains, IPs, Vulnerabilities, Services
- **Edges**: Domain→Subdomain, Service→IP, Vulnerability→Service
- Used for Attack Path Modeling Engine traversal
- Query via `Neo4jManager` in `web/reNgine/graph_utils.py`
- Bolt protocol on `neo4j:7687` (configurable via env)

## LLM Integration

- Centralised AI hub in `reNgine/llm.py`
- PII anonymisation happens **before** any external API call (see `llm_utils.py`)
- Supports: OpenAI, Anthropic Claude, Google Gemini, Ollama (local)
- API keys stored in database via `Dashboard.ExternalAPIKey`

## REST API

- Base: `http://localhost:8000/api/`
- Authentication: JWT via `djangorestframework-simplejwt`
- Permissions: custom role-based via `django-role-permissions`

## WebSocket (Channels)

- Endpoint: `ws://localhost:8000/ws/scan/{scan_id}/`
- Real-time scan progress updates
- Backed by Redis channel layer

## Logging

```python
from reNgine.utils.logger import get_module_logger, format_exception_for_log

logger = get_module_logger(__name__)

# Section-style (preferred for scan pipeline steps)
logger.log_line("[SCAN]", "START", "target %s" % target_id)
logger.log_line("[ERROR]", "FAIL", format_exception_for_log(exc), level="error", exc_info=True)

# Plain logging — always %s style for user-controlled data
logger.info("Activity done for scan %s", scan_id)
```

## Best Practices (summary)

- Security: validation, sanitisation, ORM parameterisation, XSS/CSRF protection
- Performance: `select_related`/`prefetch_related`, Redis caching, connection pooling
- Scalability: Go executor for tool subprocesses, Temporal for distributed task fan-out
- Maintainability: modular layout, structured logging, typed code, test coverage