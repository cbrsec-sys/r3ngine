# Open work

Known issues that need a decision or a real deployment to verify. Each entry
says what the problem is, what was decided, and what has been done.

## Deferred — needs a test stack

### Remote workers: Go executor shares the master's queue

Status: **deferred** (owner decision, 2026-09-29). Revisit once a two-host test
stack exists.

- `web/executor/main.go` always polls `go-executor-queue` and never reads the
  `--worker-name` flag that `docker/docker-compose.worker.yml` passes it.
- Python sends every routed tool run (nuclei, ffuf, nmap, httpx, …) to that
  same shared queue, so a remote executor would pick up the master's jobs and
  the master would pick up the worker's.
- Tool output lands in the `scan_results` volume of whichever host ran it; the
  Python side that parses it may be on the other host and silently find
  nothing.
- The worker compose points at
  `docker.pkg.github.com/whiterabb17/r3ngine/r3ngine-go-executor:latest`, an
  image that does not exist (upstream's retired registry; this fork builds no
  separate Go image), so a remote worker cannot start its executor today.

Options considered:

- **A (recommended):** per-worker queue `go-executor-queue-<WORKER_NAME>`; the
  Go executor reads `WORKER_NAME`, and Python on a worker routes to its own
  queue. Touches `main.go`, the six `task_queue="go-executor-queue"` call
  sites, the worker compose image, and tests.
- **B:** no Go executor on workers; run tools through `stream_command` with
  `route_to_executor=False` there. Smaller, but workers lose the executor's
  cancellation and timeouts.
- **C:** document remote workers as unsupported.

### `docker.sock` mounted into `web` and the worker

Status: **deferred** (owner decision, 2026-09-29). Needs compose changes and a
real Docker host to verify.

The socket is mounted in `docker/docker-compose.yml` (`web`),
`docker-compose.dev.yml` and `docker-compose.worker.yml`. Access to it is root
on the host, so any code execution inside `web` (a plugin, a dependency, a
deserialisation bug) becomes a host compromise.

What uses it today:

| Code | Use |
|---|---|
| `web/reNgine/tor_manager.py` | creates and starts the Tor container (`containers.run`) |
| `web/reNgine/ollama_manager.py` | creates and starts the Ollama container |
| `web/reNgine/tool_workers.py`, `tool_inventory.py` | `exec_run` into other containers to probe installed tools and versions |
| `web/plugins/views.py` | restarts `r3ngine-web-1` after a plugin install |

Options considered:

- **A:** docker-socket-proxy with an allowlist. Quick, but `containers.run`
  and `exec` are still needed and are enough to get root on the host.
- **B (recommended, in stages):** remove the socket. Tor and Ollama become
  compose services behind `profiles`; tool probing runs as a Temporal activity
  inside the target container; the plugin restart becomes a process signal or
  exit with `restart: always`.
- **C:** do the easy parts of B first (plugin restart, tool probing) and keep
  Tor/Ollama behind a minimal proxy.

## Decided

### Vulnerability list payload

Decision: **option B** (owner, 2026-09-29) — an opt-in compact format for the
list endpoint; the default response stays as it is for compatibility.

`VulnerabilitySerializer` uses `fields='__all__'` with `depth=2`, so every row
of `/api/listVulnerability/` embeds the whole subdomain, endpoint, target and
scan with their own relations. Phase 5 made the query count independent of
page size, but it is still 88 queries per page and a large payload, while the
UI reads only a few of those nested fields.

Options considered: A — change the list format for everyone (breaks the API
contract for other consumers such as MCP clients); B — opt-in compact format
the frontend switches to; C — leave it.

Done (2026-09-29):

- `GET /api/listVulnerability/?compact=1` (also `true`) returns
  `VulnerabilityCompactSerializer` rows: the vulnerability's own fields, plus
  `scan_history {id}`, `subdomain {id, name}`, `endpoint {id, http_url}`,
  `target_domain {id, name}`, `tags [{id, name}]`, `references [{id, url}]` and
  `cve_ids` with the CVE columns the table shows. Every kept key has the same
  name and value as in the default format, so a compact row is a subset of a
  default row. Dropped: `exposure`, `validation_results`, `cwe_ids`,
  `vuln_subscan_ids` — no list view reads them.
- The flag applies to the list action only; `/{id}/` and `/queue/` ignore it.
  Filtering, search, ordering and pagination are unchanged. Without the flag the
  response is byte-identical to before (checked against the previous
  serializer on the same data), so MCP clients, reports and the legacy page
  keep working.
- Cost per page: 88 → 7 queries; a populated row 12.6 KB → 1.4 KB.
- The frontend vulnerability table and the scan Exploits tab request
  `compact=1` (`fetchVulnerabilities` / `useVulnerabilities`), typed with
  `VulnerabilityCompact`. The detail modal still loads the full record from
  `/{id}/`.
- Tests: `web/tests/test_api_vulnerability_compact.py` (default format intact,
  compact ⊂ default, flag parsing, same ids/order/pagination with and without
  the flag across 15 filter cases), a compact query-count test in
  `test_list_endpoint_query_count.py`, and a vitest test for the api function.
- Not done: the generated `frontend/src/types/api.ts` is stale for this model
  (e.g. types `scan_history` as a string) and was not regenerated.

## Other known follow-ups

- MCP sessions still record the client IP from `X-Forwarded-For`.
- Some task functions still put `str(e)` into their internal result dicts
  (not returned to HTTP clients, but stored and shown in places).
- Compose images: `redis:alpine` is unpinned; `temporalio/auto-setup:1.22.4`
  is a development image; `neo4j:5.12.0` is old.
- Frontend: three chart libraries (ApexCharts, ECharts, Nivo) could be
  consolidated; the scan WHOIS and BUCKETS tabs read fields the summary API
  never sends (`domain_info.whois_data`, `buckets_count`).
- Tests: `tests.test_tool_execution` trufflehog case writes a directory named
  after a `MagicMock` into the current directory; tests that hit
  `tldextract` fetch the public suffix list over the network.
