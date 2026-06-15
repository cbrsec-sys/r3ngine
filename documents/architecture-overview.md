# r3ngine — Architecture Overview

## System Overview

r3ngine is a modular, containerized reconnaissance and vulnerability assessment platform. The backend is a Django application with a Temporal-based durable workflow engine replacing the original Celery task queue.

---

## Container Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Docker Compose                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────────────┐  ┌───────────────┐  │
│  │   nginx      │  │   django (web)       │  │  postgres     │  │
│  │  :80/:443    │◄─┤  :8000               │  │  :5432        │  │
│  └──────────────┘  │  Django + DRF API    ├──►│  PostgreSQL   │  │
│                    │  Django Channels WS  │  └───────────────┘  │
│                    └──────────┬───────────┘                      │
│                               │                                  │
│  ┌─────────────────────────────▼──────────────────────────────┐  │
│  │                  Temporal Server :7233                      │  │
│  │  Workflow Engine — Namespace: default                       │  │
│  └──────────┬──────────────────────────┬──────────────────────┘  │
│             │                          │                          │
│  ┌──────────▼──────────┐  ┌───────────▼──────────────────────┐  │
│  │ temporal-orchestrator│  │  temporal-go-executor            │  │
│  │ (Python worker)      │  │  (Go worker)                     │  │
│  │ Queue:               │  │  Queue: go-executor-queue        │  │
│  │  python-orchestrator │  │  Runs heavy CLI tools:           │  │
│  │  -queue              │  │  nuclei, nmap, ffuf, httpx, etc. │  │
│  └─────────────────────┘  └──────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │   redis      │  │   neo4j      │  │  temporal-ui :8080     │ │
│  │  :6379       │  │  :7474/:7687 │  │  Temporal Web UI       │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Service Descriptions

### `django` (Web Container)

- **Framework:** Django 4.x + Django REST Framework
- **Real-time:** Django Channels (ASGI) with Redis channel layer
- **Responsibilities:**
  - Serves the REST API (`/api/`)
  - Serves the React frontend (static files)
  - Handles WebSocket connections for real-time scan updates
  - Acts as the Temporal client — starts workflows in response to API calls
  - Hosts the plugin management UI

### `temporal-orchestrator` (Python Worker)

- **Language:** Python
- **Task Queue:** `python-orchestrator-queue`
- **Responsibilities:**
  - Hosts all Temporal workflow definitions (`MasterScanWorkflow`, `SubScanWorkflow`, etc.)
  - Hosts Python-side Temporal activities (DB reads/writes, calling scan tool wrappers)
  - Dynamically loads plugin workflows and activities via `PluginTemporalRegistry`
  - Entry: `temporal-entrypoint.sh`

### `temporal-go-executor` (Go Worker)

- **Language:** Go
- **Task Queue:** `go-executor-queue`
- **Responsibilities:**
  - Executes heavy security tool subprocesses (Nuclei, Nmap, Ffuf, Httpx, Aquatone, etc.)
  - Reports stdout/stderr to the Python orchestrator via the shared PostgreSQL database
  - Entry: `executor/main.go`

### `temporal` (Temporal Server)

- **Version:** OSS Temporal Server
- **Storage:** PostgreSQL (shared with Django)
- **UI:** Available at `:8080` (Temporal Web UI)

### `redis`

Used for:
- Django Channels channel layer (WebSocket message routing)
- Redis Streams for real-time AD assessment progress events
- Celery broker (legacy — being phased out)

### `neo4j`

Graph database for:
- Attack Path Modeling Engine (APME) — nodes are scan findings, edges are attack paths
- Active Directory plugin — AD domain/trust/exposure graph

---

## Request Flow: Starting a Scan

```
Browser → POST /api/startScan/ (Django REST API)
    │
    ▼
startScan/views.py
    │
    ▼
reNgine.temporal_client.TemporalClientProvider.get_client()
    │
    ▼
Temporal Server (start MasterScanWorkflow)
    │
    ▼
temporal-orchestrator (Python Worker)
    │
    ├─ Tier 1–6 Activities → python-orchestrator-queue (Python) OR
    │                        → go-executor-queue (Go)
    │
    └─ Results written to PostgreSQL, events pushed via Redis/WebSocket
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend API | Django 4.x + Django REST Framework |
| Real-time | Django Channels (ASGI) + Redis |
| Workflow Engine | Temporal (OSS) |
| Python Worker | temporalio Python SDK |
| Go Worker | temporalio Go SDK |
| Database | PostgreSQL |
| Graph Database | Neo4j |
| Cache / Pub-Sub | Redis |
| Frontend | React (TypeScript) + MUI |
| Mobile | Expo React Native |
| Containerization | Docker Compose |
