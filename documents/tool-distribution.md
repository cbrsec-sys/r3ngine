# r3ngine — Tool Distribution (Go Executor)

## Overview

r3ngine uses a two-worker architecture for running security tools. Heavy CLI tool execution (Nuclei, Nmap, Ffuf, Httpx, Aquatone, etc.) is delegated to a dedicated **Go Executor** service that runs on the `go-executor-queue` Temporal task queue.

This separation allows:
- **Performance**: Go's goroutine-based concurrency handles many concurrent subprocess calls efficiently.
- **Isolation**: Tool crashes don't affect the Python orchestrator.
- **Scalability**: The Go executor can be independently scaled.

---

## Architecture

```
MasterScanWorkflow (Python)
        │
        ▼  task_queue="go-executor-queue"
GoExecutorTaskWorkflow
        │
        ▼
RunToolSubprocessActivity (Go Worker)
        │
        ▼
subprocess: nuclei / nmap / ffuf / httpx / ...
        │
        ▼
stdout/stderr → PostgreSQL CommandResult table
```

---

## `GoExecutorTaskWorkflow`

**File:** `web/reNgine/temporal_workflows.py`

```python
@workflow.defn(name="GoExecutorTaskWorkflow")
class GoExecutorTaskWorkflow:
    @workflow.run
    async def run(self, input_data: dict) -> dict:
        return await workflow.execute_activity(
            "RunToolSubprocessActivity",
            input_data,
            start_to_close_timeout=timedelta(hours=2),
            heartbeat_timeout=timedelta(minutes=5),
            task_queue="go-executor-queue"
        )
```

### Input Payload

```python
{
    "command": ["nuclei", "-u", "https://target.example.com", "-t", "cves/"],
    "scan_id": 42,
    "command_id": 17
}
```

| Key | Type | Description |
|---|---|---|
| `command` | `list[str]` | The binary and its arguments |
| `scan_id` | `int` | ScanHistory ID for logging |
| `command_id` | `int` | `Command` DB record ID to log stdout/stderr to |

### Output

```python
{
    "stdout": "...",
    "stderr": "...",
    "exit_code": 0
}
```

---

## Go Executor Service

**Source:** `web/executor/main.go`  
**Container:** `temporal-go-executor`  
**Task Queue:** `go-executor-queue`

### Responsibilities

1. Registers `RunToolSubprocessActivity` with Temporal.
2. When an activity is dispatched, executes the command as a subprocess.
3. Streams stdout/stderr to the `Command` DB record (PostgreSQL) for real-time log viewing.
4. Sends periodic heartbeats to Temporal to prevent activity timeouts during long-running tools.
5. Returns the subprocess result dict.

### Heartbeating

The Go worker sends heartbeats every 30 seconds during subprocess execution. If the subprocess takes longer than `heartbeat_timeout` without a heartbeat, Temporal reschedules the activity.

---

## Which Tools Run on Which Queue?

### `go-executor-queue` (Go Worker)

| Tool | Description |
|---|---|
| Nuclei | Template-based vulnerability scanner |
| Nmap | Network port scanner |
| Ffuf | Directory/path fuzzing |
| Httpx | HTTP probing and crawling |
| Aquatone | Web screenshot and asset discovery |
| Amass | Subdomain enumeration |
| Subfinder | Passive subdomain discovery |
| Assetfinder | Subdomain discovery |
| Hakrawler | Web spider/crawl |
| GAU | URL archive fetching |
| Gospider | Web spider |
| Katana | JavaScript-aware web spider |
| WaybackURLs | Wayback Machine URL fetcher |
| Dirsearch | Directory fuzzing |
| SQLMap | SQL injection exploitation |
| Dalfox | XSS scanner |
| CRLFuzz | CRLF injection fuzzer |
| WPScan | WordPress scanner |
| S3Scanner | S3 bucket misconfiguration scanner |
| BadDNS | DNS takeover checker |
| SpiderFoot | Attack surface intelligence |

### `python-orchestrator-queue` (Python Worker)

| Task | Description |
|---|---|
| Django DB reads/writes | All ORM operations |
| Tool output parsing | Parsing raw tool output into structured DB records |
| Correlation engine | Vulnerability correlation logic |
| Risk scoring | Risk score computation |
| LLM calls | AI impact assessment and APME |
| Neo4j sync | Graph database synchronization |
| WebSocket events | Real-time progress push to frontend |

---

## `RunToolSubprocessActivity` (Go)

The single activity registered on the Go worker. Executes any command as a subprocess and streams the output.

### Implementation Details

- Uses `os/exec` to spawn the subprocess.
- Reads stdout line-by-line and writes to the `Command` DB record.
- Sends Temporal heartbeats every 30 seconds.
- On heartbeat timeout, the activity is cancelled and the subprocess is killed with `SIGTERM`.
- Buffers large tool outputs to prevent DB row size issues.

---

## Executor Entrypoint (`executor-entrypoint.sh`)

The Go executor container:

1. Waits for the Temporal server and PostgreSQL to be ready.
2. Builds the Go executor binary if not already built.
3. Runs database tool installer scripts to ensure all security tools are present.
4. Starts the Temporal Go worker.

---

## Tool Installation

Tools are installed in the Go executor container via Dockerfile (`web/Dockerfile`):

```dockerfile
# Example tool installations
RUN go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
RUN go install github.com/projectdiscovery/httpx/cmd/httpx@latest
RUN go install github.com/projectdiscovery/amass/v4/...@latest
RUN pip install sqlmap xsstrike
```

Tools that require Python are installed via pip; Go-based tools via `go install`.
