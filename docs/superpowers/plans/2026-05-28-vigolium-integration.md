# Vigolium Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Vigolium v0.1.15-beta as a default background web vulnerability scanner across the r3ngine scan pipeline (Tier 2 endpoint seeding, Tier 5 dynamic analysis, and Tier 6 vulnerability assessment), feeding findings into the `Vulnerability` DB model and discovered endpoints into the `EndPoint` model via existing helpers.

**Architecture:** Vigolium runs as a subprocess tool (mirroring the wpscan/nuclei pattern) with `--stateless` mode so it uses a throwaway SQLite DB per scan. Output is JSONL format (`{"type": "finding"|"http_record"|"scan", "data": {...}}`). Three pipeline stages: endpoint seeding (`vigolium scan --only ingestion,discovery`) at Tier 2 parallel with http_crawl; dynamic analysis (`--only dynamic-assessment`) at Tier 5 parallel with web_api_discovery; and full vulnerability scan (`--only known-issue-scan,dynamic-assessment`) at Tier 6 inside NucleiPlannerWorkflow. All stages default-enabled.

**Tech Stack:** Python 3, Django ORM, Temporal SDK, vigolium v0.1.15-beta CLI, `stream_command()` subprocess helper, `save_vulnerability()` and `save_endpoint()` for DB persistence.

---

## Confirmed Build & Schema Facts

> These were verified by cloning, building, and running the tool against live scan data.

### Build
- **Repo**: `https://github.com/vigolium/vigolium`
- **Version**: v0.1.15-beta
- **Go requirement**: `go 1.26.0` minimum — requires `golang:1.26-bookworm` base image
- **Embedded binaries**: `vigolium-audit` and `jsscan` must be compiled via `bun` before `go build`
- **Build commands** (in order):
  ```bash
  curl -fsSL https://bun.sh/install | bash   # install bun
  make ensure-audit                           # builds vigolium-audit via bun (~98MB)
  make ensure-jsscan                          # builds jsscan via bun
  go build -ldflags="-s -w" -o bin/vigolium ./cmd/vigolium
  ```
- **Binary size**: ~341MB (embedded binaries inflate this)
- **Install target in container**: `/usr/local/bin/vigolium`

### CLI Execution Pattern (verified)
```bash
# Full vulnerability scan pipeline from endpoint list
vigolium scan \
  -T /path/to/endpoints.txt \
  -S \                          # stateless: temp DB, no persistent state
  --format jsonl \
  -o /path/to/output.jsonl \
  --only known-issue-scan,dynamic-assessment \
  -c 50 \                       # concurrency
  -r 100 \                      # rate limit req/sec
  --timeout 15s \
  --skip-dependency-check \
  --omit-response               # exclude raw response body from JSONL (smaller files)

# Discovery phase only (Tier 2 - endpoint seeding)
vigolium scan \
  -t https://target.example.com \
  -S \
  --format jsonl \
  -o /path/to/discovery.jsonl \
  --only ingestion,discovery \
  -c 20 \
  -r 50 \
  --timeout 10s \
  --skip-dependency-check

# Dynamic assessment only (Tier 5 - parallel with web_api_discovery)
vigolium scan \
  -t https://target.example.com \
  -S \
  --format jsonl \
  -o /path/to/analysis.jsonl \
  --only dynamic-assessment \
  -c 20 \
  -r 50 \
  --timeout 10s \
  --skip-dependency-check \
  --omit-response
```

### JSONL Output Schema (confirmed from live output)

The JSONL file mixes three record types, one JSON object per line:

**Finding record** (`type: "finding"`):
```json
{
  "type": "finding",
  "data": {
    "id": 10,
    "url": "https://www.defijn.io/",
    "hostname": "www.defijn.io",
    "module_id": "cacheable-https-detect",
    "module_name": "Cacheable HTTPS Response Detect",
    "module_type": "passive",
    "finding_source": "dynamic-assessment",
    "module_short": "Detects sensitive HTTPS responses without proper cache control",
    "description": "Sensitive HTTPS response without proper cache-control directives",
    "severity": "low",
    "confidence": "firm",
    "status": "triaged",
    "cvss_score": 0.0,
    "matched_at": ["https://www.defijn.io/"],
    "extracted_results": ["Response sets cookies", "Cache-Control: "],
    "tags": null,
    "request": "GET  HTTP/1.1\nHost: www.defijn.io\n\n",
    "response": "(omitted when --omit-response is used)",
    "finding_hash": "26204c3c3736454eb03ac587b830401c947fec6c",
    "found_at": "2026-05-28T07:36:53.199018Z",
    "created_at": "2026-05-28T07:36:53Z"
  }
}
```
- `severity` values: `"critical"` / `"high"` / `"medium"` / `"low"` / `"info"` / `"suspect"` (all lowercase strings)
- `tags` may be `null` or a list of strings
- `matched_at` is always a **list** (not a single string)
- `request` and `response` are raw strings (not base64)

**HTTP Record** (`type: "http_record"`) — discovered endpoints:
```json
{
  "type": "http_record",
  "data": {
    "url": "https://www.defijn.io/",
    "hostname": "www.defijn.io",
    "method": "GET",
    "path": "/",
    "status_code": 200,
    "ip": "198.202.211.1",
    "response_content_type": "text/html",
    "response_content_length": 12345,
    "response_time_ms": 234
  }
}
```

**Scan metadata** (`type: "scan"`) — one per file, ignore for integration.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `web/Dockerfile` | Modify | Add `vigolium-builder` stage (golang:1.26 + bun) before the runtime stage |
| `web/fixtures/external_tools.yaml` | Modify | Register vigolium as InstalledExternalTool (pk=46) |
| `web/reNgine/definitions.py` | Modify | Add vigolium constants |
| `web/reNgine/vigolium_tasks.py` | Create | Discovery, analysis, and vulnerability scan task functions + parsers |
| `web/reNgine/temporal_activities.py` | Modify | Add RunVigoliumScanActivity + RunVigoliumDiscoveryActivity + RunVigoliumAnalysisActivity |
| `web/reNgine/temporal_workflows.py` | Modify | Wire activities into Tier 2, Tier 5, and NucleiPlannerWorkflow |
| `web/fixtures/default_yaml_config.yaml` | Modify | Add vigolium config blocks |
| `web/fixtures/default_scan_engines.yaml` | Modify | Enable vigolium in all engine YAML configs |
| `web/tests/test_vigolium_tasks.py` | Create | Unit tests for parsers and scan function gate logic |

---

## Task 1: Add vigolium build stage to Dockerfile and register in fixtures

**Files:**
- Modify: `web/Dockerfile` (add new stage before the runtime stage, copy binary)
- Modify: `web/fixtures/external_tools.yaml` (append after pk=45)

- [ ] **Step 1: Read the end of the Dockerfile to find the runtime COPY block**

  Open `web/Dockerfile`. Find where binaries are copied from builder stages into the final runtime image (the `COPY --from=go-tools-builder` lines). This is where the vigolium binary COPY goes.

- [ ] **Step 2: Add vigolium-builder stage to Dockerfile**

  Add the following new stage **after** the `executor-builder` stage (after line ~78) and **before** the final runtime `FROM` line:

  ```dockerfile
  # ===========================================================================
  # Stage: Vigolium Builder
  #
  # Vigolium requires Go 1.26+ and bun (for embedded vigolium-audit and jsscan
  # binaries). Clone, build embedded deps, then compile the binary.
  # The ~341MB binary is copied directly to /usr/local/bin in the runtime image.
  # ===========================================================================
  FROM golang:1.26-bookworm AS vigolium-builder

  RUN apt-get update && \
      apt-get install -y --no-install-recommends curl git make unzip && \
      rm -rf /var/lib/apt/lists/*

  # Install bun (needed for vigolium-audit and jsscan embedded binary builds)
  RUN curl -fsSL https://bun.sh/install | bash
  ENV PATH="/root/.bun/bin:${PATH}"
  ENV GO111MODULE=on

  # Clone vigolium at the pinned release tag
  RUN git clone --depth 1 --branch v0.1.15-beta https://github.com/vigolium/vigolium /build/vigolium 2>/dev/null || \
      git clone --depth 1 https://github.com/vigolium/vigolium /build/vigolium

  WORKDIR /build/vigolium

  # Build embedded binaries (vigolium-audit via bun, jsscan via bun)
  RUN make ensure-audit && make ensure-jsscan

  # Compile vigolium binary
  RUN go build -ldflags="-s -w" -o /usr/local/bin/vigolium ./cmd/vigolium && \
      rm -rf /root/.cache/go-build /root/.bun /go/pkg /build/vigolium
  ```

- [ ] **Step 3: Add COPY line for vigolium in the runtime stage**

  In the same Dockerfile, find the block where Go tool binaries are copied into the final runtime image (the `COPY --from=go-tools-builder /go/bin/ /usr/local/bin/` line). After that block, add:

  ```dockerfile
  # Vigolium — web vulnerability scanner (built separately due to Go 1.26 + bun requirement)
  COPY --from=vigolium-builder /usr/local/bin/vigolium /usr/local/bin/vigolium
  ```

- [ ] **Step 4: Add vigolium to external_tools.yaml**

  Open `web/fixtures/external_tools.yaml`. Append after the pk=45 entry:

  ```yaml
  - model: scanEngine.installedexternaltool
    pk: 46
    fields:
      logo_url: https://www.vigolium.com/logo.png
      name: Vigolium
      description: "Vigolium is a high-fidelity web vulnerability scanner combining deterministic multi-phase native scanning with optional AI-driven agentic modes. Features 251 built-in modules covering injection, XSS, SSRF, IDOR, and more."
      github_url: https://github.com/vigolium/vigolium
      license_url: https://github.com/vigolium/vigolium/blob/main/LICENSE
      version_lookup_command: vigolium version
      update_command: "vigolium update"
      install_command: "git clone https://github.com/vigolium/vigolium && cd vigolium && make ensure-audit && make ensure-jsscan && go build -o /usr/local/bin/vigolium ./cmd/vigolium"
      version_match_regex: "v\\d+\\.\\d+\\.\\d+"
      is_default: true
      is_subdomain_gathering: false
      is_github_cloned: false
      github_clone_path: null
      subdomain_gathering_command: null
  ```

- [ ] **Step 5: Reload fixtures to verify the entry parses correctly**

  ```bash
  docker exec r3ngine-web-1 python manage.py loaddata fixtures/external_tools.yaml
  ```
  Expected: `Installed 46 object(s) from 1 fixture(s)`

- [ ] **Step 6: Commit**

  ```bash
  git add web/Dockerfile web/fixtures/external_tools.yaml
  git commit -m "feat(vigolium): add vigolium-builder Dockerfile stage and tool registry entry"
  ```

---

## Task 2: Add vigolium constants to definitions.py

**Files:**
- Modify: `web/reNgine/definitions.py` (append after the `RUN_WPSCAN` block at line ~183)
- Create: `web/tests/test_vigolium_tasks.py`

- [ ] **Step 1: Write the failing test**

  Create `web/tests/test_vigolium_tasks.py`:

  ```python
  # web/tests/test_vigolium_tasks.py
  from django.test import TestCase
  from unittest.mock import MagicMock, patch


  class VigoliumDefinitionsTest(TestCase):
      def test_vigolium_constants_defined(self):
          from reNgine.definitions import (
              RUN_VIGOLIUM,
              RUN_VIGOLIUM_DISCOVERY,
              RUN_VIGOLIUM_ANALYSIS,
              VIGOLIUM,
              VIGOLIUM_STRATEGY,
              VIGOLIUM_CONCURRENCY,
              VIGOLIUM_RATE_LIMIT,
              VIGOLIUM_TIMEOUT,
              VIGOLIUM_MODULES,
              VIGOLIUM_SEVERITY_FILTER,
              VIGOLIUM_DEFAULT_CONFIG,
          )
          self.assertEqual(RUN_VIGOLIUM, 'run_vigolium')
          self.assertEqual(RUN_VIGOLIUM_DISCOVERY, 'run_vigolium_discovery')
          self.assertEqual(RUN_VIGOLIUM_ANALYSIS, 'run_vigolium_analysis')
          self.assertEqual(VIGOLIUM, 'vigolium')
          self.assertIn('run_vigolium', VIGOLIUM_DEFAULT_CONFIG)
          self.assertTrue(VIGOLIUM_DEFAULT_CONFIG['run_vigolium'])
  ```

- [ ] **Step 2: Run to verify it fails**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks.VigoliumDefinitionsTest -v 2
  ```
  Expected: `ImportError: cannot import name 'RUN_VIGOLIUM'`

- [ ] **Step 3: Add constants to definitions.py**

  Open `web/reNgine/definitions.py`. After the `WPSCAN_SCAN_DEFAULT_CONFIG` block (after line ~188), add:

  ```python
  # ─── Vigolium ─────────────────────────────────────────────────────────────────
  RUN_VIGOLIUM = 'run_vigolium'
  RUN_VIGOLIUM_DISCOVERY = 'run_vigolium_discovery'
  RUN_VIGOLIUM_ANALYSIS = 'run_vigolium_analysis'
  VIGOLIUM = 'vigolium'
  VIGOLIUM_STRATEGY = 'strategy'
  VIGOLIUM_CONCURRENCY = 'concurrency'
  VIGOLIUM_RATE_LIMIT = 'rate_limit'
  VIGOLIUM_TIMEOUT = 'timeout'
  VIGOLIUM_MODULES = 'modules'
  VIGOLIUM_SEVERITY_FILTER = 'severity_filter'

  VIGOLIUM_DEFAULT_CONFIG = {
      'run_vigolium': True,
      'strategy': 'balanced',
      'concurrency': 50,
      'rate_limit': 100,
      'timeout': '15s',
  }

  VIGOLIUM_DEFAULT_DISCOVERY_CONFIG = {
      'run_vigolium_discovery': True,
      'strategy': 'balanced',
      'concurrency': 20,
      'rate_limit': 50,
      'timeout': '10s',
  }

  VIGOLIUM_DEFAULT_ANALYSIS_CONFIG = {
      'run_vigolium_analysis': True,
      'strategy': 'balanced',
      'concurrency': 20,
      'rate_limit': 50,
      'timeout': '10s',
  }
  ```

- [ ] **Step 4: Run to verify test passes**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks.VigoliumDefinitionsTest -v 2
  ```
  Expected: `OK (1 test)`

- [ ] **Step 5: Commit**

  ```bash
  git add web/reNgine/definitions.py web/tests/test_vigolium_tasks.py
  git commit -m "feat(vigolium): add vigolium constants to definitions.py"
  ```

---

## Task 3: Create vigolium_tasks.py — JSONL parser and helpers

**Files:**
- Create: `web/reNgine/vigolium_tasks.py`

The JSONL output schema is confirmed: each line is `{"type": "finding"|"http_record"|"scan", "data": {...}}`. Only `type: "finding"` and `type: "http_record"` records are processed.

- [ ] **Step 1: Write the failing parser tests**

  Add to `web/tests/test_vigolium_tasks.py`:

  ```python
  class VigoliumParserTest(TestCase):
      def _make_task(self):
          task = MagicMock()
          task.scan_id = 1
          task.activity_id = 1
          task.scan = MagicMock()
          task.scan.results_dir = '/tmp/test_scan'
          task.domain = MagicMock()
          task.domain.id = 1
          task.subscan = None
          task.subdomain = None
          task.yaml_configuration = {
              'vulnerability_scan': {
                  'run_vigolium': True,
                  'vigolium': {'strategy': 'balanced', 'concurrency': 50},
              },
              'vigolium_discovery': {'run_vigolium_discovery': True},
              'vigolium_analysis': {'run_vigolium_analysis': True},
          }
          return task

      def test_parse_finding_saves_vulnerability(self):
          """parse_vigolium_finding maps confirmed JSONL fields to save_vulnerability."""
          from reNgine.vigolium_tasks import parse_vigolium_finding

          # Real schema from live vigolium output
          finding_data = {
              'url': 'https://www.defijn.io/',
              'hostname': 'www.defijn.io',
              'module_id': 'xss-reflected',
              'module_name': 'Reflected XSS',
              'module_type': 'active',
              'finding_source': 'dynamic-assessment',
              'module_short': 'Detects reflected XSS via parameter injection',
              'description': 'User input is reflected unescaped in the response.',
              'severity': 'high',
              'confidence': 'firm',
              'status': 'triaged',
              'cvss_score': 6.1,
              'matched_at': ['https://www.defijn.io/search?q=test'],
              'extracted_results': ['<script>alert(1)</script>'],
              'tags': ['xss', 'injection'],
              'request': 'GET /search?q=test HTTP/1.1\nHost: www.defijn.io\n',
              'response': '',
              'finding_hash': 'abc123',
              'found_at': '2026-05-28T07:36:53Z',
          }
          task = self._make_task()
          subdomain = MagicMock()
          subdomain.name = 'www.defijn.io'

          with patch('reNgine.vigolium_tasks.save_vulnerability') as mock_save:
              parse_vigolium_finding(task, finding_data, subdomain)
              mock_save.assert_called_once()
              kwargs = mock_save.call_args[1]
              self.assertEqual(kwargs['name'], 'Reflected XSS')
              self.assertEqual(kwargs['severity'], 3)   # 'high' → 3
              self.assertEqual(kwargs['type'], 'Vigolium')
              self.assertEqual(kwargs['template_id'], 'xss-reflected')
              self.assertEqual(kwargs['http_url'], 'https://www.defijn.io/search?q=test')
              self.assertEqual(kwargs['description'], 'User input is reflected unescaped in the response.')

      def test_parse_finding_uses_url_when_matched_at_empty(self):
          """parse_vigolium_finding falls back to data.url when matched_at is empty."""
          from reNgine.vigolium_tasks import parse_vigolium_finding

          finding_data = {
              'url': 'https://www.defijn.io/',
              'hostname': 'www.defijn.io',
              'module_id': 'headers-missing',
              'module_name': 'Security Headers Missing',
              'severity': 'info',
              'description': 'Missing security headers.',
              'matched_at': [],
              'tags': None,
          }
          task = self._make_task()
          subdomain = MagicMock()
          with patch('reNgine.vigolium_tasks.save_vulnerability') as mock_save:
              parse_vigolium_finding(task, finding_data, subdomain)
              mock_save.assert_called_once()
              kwargs = mock_save.call_args[1]
              self.assertEqual(kwargs['http_url'], 'https://www.defijn.io/')
              self.assertEqual(kwargs['severity'], 0)  # 'info' → 0

      def test_parse_finding_skips_missing_name(self):
          """parse_vigolium_finding skips records with no module_name."""
          from reNgine.vigolium_tasks import parse_vigolium_finding

          task = self._make_task()
          subdomain = MagicMock()
          with patch('reNgine.vigolium_tasks.save_vulnerability') as mock_save:
              parse_vigolium_finding(task, {'severity': 'high'}, subdomain)
              mock_save.assert_not_called()

      def test_parse_http_record_saves_endpoint(self):
          """parse_vigolium_http_record saves a discovered URL as an EndPoint."""
          from reNgine.vigolium_tasks import parse_vigolium_http_record

          record_data = {
              'url': 'https://www.defijn.io/login',
              'hostname': 'www.defijn.io',
              'method': 'GET',
              'status_code': 200,
          }
          task = self._make_task()
          with patch('reNgine.vigolium_tasks.save_endpoint') as mock_save:
              parse_vigolium_http_record(task, record_data)
              mock_save.assert_called_once()
              kwargs = mock_save.call_args[1]
              self.assertEqual(kwargs['http_url'], 'https://www.defijn.io/login')

      def test_parse_http_record_skips_missing_url(self):
          """parse_vigolium_http_record skips records with no url field."""
          from reNgine.vigolium_tasks import parse_vigolium_http_record

          task = self._make_task()
          with patch('reNgine.vigolium_tasks.save_endpoint') as mock_save:
              parse_vigolium_http_record(task, {'method': 'GET'})
              mock_save.assert_not_called()
  ```

- [ ] **Step 2: Run to verify they fail**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks.VigoliumParserTest -v 2
  ```
  Expected: `ImportError: cannot import name 'parse_vigolium_finding'`

- [ ] **Step 3: Create vigolium_tasks.py with parser functions**

  Create `web/reNgine/vigolium_tasks.py`:

  ```python
  import json
  import logging
  import os

  from reNgine.definitions import (
      NUCLEI_SEVERITY_MAP,
      RUN_VIGOLIUM,
      RUN_VIGOLIUM_ANALYSIS,
      RUN_VIGOLIUM_DISCOVERY,
      VIGOLIUM,
      VIGOLIUM_CONCURRENCY,
      VIGOLIUM_MODULES,
      VIGOLIUM_RATE_LIMIT,
      VIGOLIUM_SEVERITY_FILTER,
      VIGOLIUM_STRATEGY,
      VIGOLIUM_TIMEOUT,
      VULNERABILITY_SCAN,
  )
  from reNgine.common_func import get_random_proxy, save_endpoint, save_vulnerability
  from startScan.models import Subdomain

  logger = logging.getLogger(__name__)


  def _iter_jsonl(output_file):
      """Yield parsed JSON objects from a vigolium JSONL output file."""
      if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
          return
      with open(output_file, 'r') as f:
          for line in f:
              line = line.strip()
              if not line:
                  continue
              try:
                  yield json.loads(line)
              except json.JSONDecodeError:
                  logger.warning(f"vigolium: skipping non-JSON line: {line[:80]}")


  def parse_vigolium_finding(task_instance, finding_data, subdomain):
      """Save a single vigolium finding record to the Vulnerability model.

      The JSONL finding schema (confirmed from live output):
        module_id   → template_id
        module_name → name
        severity    → string "critical"/"high"/"medium"/"low"/"info"
        matched_at  → list of URLs (use first; fall back to data.url)
        tags        → list or null
        request     → raw HTTP request string
      """
      name = finding_data.get('module_name')
      if not name:
          return

      severity_str = (finding_data.get('severity') or 'info').lower()
      severity_num = NUCLEI_SEVERITY_MAP.get(severity_str, 0)

      # matched_at is a list; use first entry, fall back to url field
      matched_at = finding_data.get('matched_at') or []
      http_url = matched_at[0] if matched_at else finding_data.get('url', f"https://{subdomain.name}")

      tags = finding_data.get('tags') or []
      if isinstance(tags, str):
          tags = [tags]

      save_vulnerability(
          target_domain=task_instance.domain,
          http_url=http_url,
          scan_history=task_instance.scan,
          subdomain=subdomain,
          name=name,
          severity=severity_num,
          description=finding_data.get('description', ''),
          type='Vigolium',
          template_id=finding_data.get('module_id', ''),
          curl_command='',
          request=finding_data.get('request', ''),
          response=finding_data.get('response', ''),
          tags=tags,
          cve_ids=[],
          references=[],
      )


  def parse_vigolium_http_record(task_instance, record_data):
      """Save a single vigolium http_record to the EndPoint model.

      Called for type='http_record' lines — vigolium discovered URLs
      that should populate the endpoint DB for downstream pipeline tiers.
      """
      url = record_data.get('url')
      if not url:
          return

      save_endpoint(
          http_url=url,
          scan_history=task_instance.scan,
          target_domain=task_instance.domain,
          method=record_data.get('method', 'GET'),
          http_status=record_data.get('status_code'),
      )


  def _run_vigolium_phase(task_instance, cmd, output_file, phase_label, save_http_records=False):
      """Execute a vigolium command, then parse and persist findings from the JSONL output.

      Args:
          task_instance: Temporal task proxy with scan context.
          cmd: Full vigolium command string.
          output_file: Path where vigolium writes its JSONL output.
          phase_label: Human-readable label for logging.
          save_http_records: If True, also save http_record entries as EndPoints.
      """
      from reNgine.tasks import stream_command

      logger.info(f"Running Vigolium {phase_label}")
      logger.warning(f"Command: {cmd}")

      for _ in stream_command(cmd, scan_id=task_instance.scan_id, activity_id=task_instance.activity_id):
          pass

      findings_saved = 0
      endpoints_saved = 0

      for record in _iter_jsonl(output_file):
          record_type = record.get('type')
          data = record.get('data', {})

          if record_type == 'finding':
              hostname = data.get('hostname', '')
              subdomain = Subdomain.objects.filter(
                  scan_history=task_instance.scan, name=hostname
              ).first()
              if not subdomain:
                  subdomain = Subdomain.objects.filter(scan_history=task_instance.scan).first()
              if subdomain:
                  parse_vigolium_finding(task_instance, data, subdomain)
                  findings_saved += 1
              else:
                  logger.warning(f"Vigolium {phase_label}: no subdomain found for {hostname}, skipping finding.")

          elif record_type == 'http_record' and save_http_records:
              parse_vigolium_http_record(task_instance, data)
              endpoints_saved += 1

      logger.info(f"Vigolium {phase_label} complete — {findings_saved} findings, {endpoints_saved} endpoints saved")
  ```

- [ ] **Step 4: Run parser tests**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks.VigoliumParserTest -v 2
  ```
  Expected: `OK (5 tests)`

- [ ] **Step 5: Commit**

  ```bash
  git add web/reNgine/vigolium_tasks.py web/tests/test_vigolium_tasks.py
  git commit -m "feat(vigolium): add vigolium_tasks.py with JSONL parsers and execution helper"
  ```

---

## Task 4: Add scan task functions to vigolium_tasks.py

**Files:**
- Modify: `web/reNgine/vigolium_tasks.py` (append three task functions)

- [ ] **Step 1: Write failing tests**

  Add to `web/tests/test_vigolium_tasks.py`:

  ```python
  class VigoliumTaskGatingTest(TestCase):
      def _make_task(self, vuln_enabled=True, discovery_enabled=True, analysis_enabled=True):
          task = MagicMock()
          task.scan_id = 1
          task.activity_id = 1
          task.scan = MagicMock()
          task.scan.results_dir = '/tmp/test_scan'
          task.scan.domain = MagicMock()
          task.scan.domain.name = 'example.com'
          task.domain = MagicMock()
          task.subscan = None
          task.subdomain = None
          task.yaml_configuration = {
              'vulnerability_scan': {
                  'run_vigolium': vuln_enabled,
                  'vigolium': {'strategy': 'balanced', 'concurrency': 50, 'rate_limit': 100, 'timeout': '15s'},
              },
              'vigolium_discovery': {'run_vigolium_discovery': discovery_enabled},
              'vigolium_analysis': {'run_vigolium_analysis': analysis_enabled},
          }
          return task

      def test_vigolium_scan_skips_when_disabled(self):
          from reNgine.vigolium_tasks import vigolium_scan
          task = self._make_task(vuln_enabled=False)
          with patch('reNgine.vigolium_tasks._run_vigolium_phase') as mock_run:
              vigolium_scan(task)
              mock_run.assert_not_called()

      def test_vigolium_discovery_skips_when_disabled(self):
          from reNgine.vigolium_tasks import vigolium_discovery
          task = self._make_task(discovery_enabled=False)
          with patch('reNgine.vigolium_tasks._run_vigolium_phase') as mock_run:
              vigolium_discovery(task)
              mock_run.assert_not_called()

      def test_vigolium_analysis_skips_when_disabled(self):
          from reNgine.vigolium_tasks import vigolium_analysis
          task = self._make_task(analysis_enabled=False)
          with patch('reNgine.vigolium_tasks._run_vigolium_phase') as mock_run:
              vigolium_analysis(task)
              mock_run.assert_not_called()

      def test_vigolium_scan_calls_phase_runner(self):
          from reNgine.vigolium_tasks import vigolium_scan
          task = self._make_task(vuln_enabled=True)
          with patch('reNgine.vigolium_tasks._run_vigolium_phase') as mock_run, \
               patch('os.makedirs'), \
               patch('reNgine.vigolium_tasks.Subdomain'):
              vigolium_scan(task, urls=['https://example.com'])
              mock_run.assert_called_once()
              # Verify the command includes the correct phases
              call_args = mock_run.call_args
              cmd = call_args[0][1]
              self.assertIn('--only known-issue-scan,dynamic-assessment', cmd)
              self.assertIn('--stateless', cmd)
              self.assertIn('--skip-dependency-check', cmd)
              self.assertIn('--omit-response', cmd)
  ```

- [ ] **Step 2: Run to verify they fail**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks.VigoliumTaskGatingTest -v 2
  ```
  Expected: `ImportError: cannot import name 'vigolium_scan'`

- [ ] **Step 3: Append three task functions to vigolium_tasks.py**

  Append to the end of `web/reNgine/vigolium_tasks.py`:

  ```python

  def vigolium_scan(self, urls=[], ctx={}, description=None):
      """Run vigolium known-issue + dynamic-assessment scan against discovered endpoints.

      Runs inside NucleiPlannerWorkflow at Tier 6 alongside nuclei. Reads from
      the passed URL list or falls back to get_http_urls() from the endpoint DB.
      """
      logger.info("Starting Vigolium Vulnerability Scan")

      vuln_config = self.yaml_configuration.get(VULNERABILITY_SCAN, {})
      if not vuln_config.get(RUN_VIGOLIUM, True):
          logger.info("Vigolium scan disabled in configuration. Skipping.")
          return

      vig_config = vuln_config.get(VIGOLIUM, {})
      strategy = vig_config.get(VIGOLIUM_STRATEGY, 'balanced')
      concurrency = vig_config.get(VIGOLIUM_CONCURRENCY, 50)
      rate_limit = vig_config.get(VIGOLIUM_RATE_LIMIT, 100)
      timeout = vig_config.get(VIGOLIUM_TIMEOUT, '15s')
      modules = vig_config.get(VIGOLIUM_MODULES, [])
      severity_filter = vig_config.get(VIGOLIUM_SEVERITY_FILTER, [])

      if urls:
          target_urls = urls
      else:
          from reNgine.common_func import get_http_urls
          target_urls = get_http_urls(self.scan_id)

      if not target_urls:
          if self.scan and self.scan.domain:
              target_urls = [f"https://{self.scan.domain.name}"]
          else:
              logger.warning("Vigolium scan: no targets found. Skipping.")
              return

      results_dir = f"{self.scan.results_dir}/vigolium/vuln"
      os.makedirs(results_dir, exist_ok=True)

      targets_file = f"{results_dir}/targets.txt"
      with open(targets_file, 'w') as f:
          for url in target_urls:
              f.write(f"{url}\n")

      output_file = f"{results_dir}/findings.jsonl"

      cmd = (
          f"vigolium scan"
          f" -T {targets_file}"
          f" --stateless"
          f" --format jsonl"
          f" -o {output_file}"
          f" --only known-issue-scan,dynamic-assessment"
          f" -c {concurrency}"
          f" -r {rate_limit}"
          f" --timeout {timeout}"
          f" --strategy {strategy}"
          f" --skip-dependency-check"
          f" --omit-response"
      )

      if modules:
          cmd += f" -m {','.join(modules)}"
      if severity_filter:
          cmd += f" --known-issue-scan-severities {','.join(severity_filter)}"

      proxy = get_random_proxy()
      if proxy:
          cmd += f" --proxy {proxy}"

      _run_vigolium_phase(self, cmd, output_file, "Vulnerability Scan", save_http_records=False)
      return "Vigolium scan completed"


  def vigolium_discovery(self, ctx={}, description=None):
      """Run vigolium endpoint discovery for each subdomain at Tier 2.

      Runs the ingestion + discovery phases to find paths and endpoints that
      feed the endpoint DB before Tier 3–6 processing. Saves http_records as
      EndPoint entries for downstream pipeline stages to consume.
      """
      logger.info("Starting Vigolium Discovery")

      discovery_config = self.yaml_configuration.get('vigolium_discovery', {})
      if not discovery_config.get(RUN_VIGOLIUM_DISCOVERY, True):
          logger.info("Vigolium discovery disabled in configuration. Skipping.")
          return

      strategy = discovery_config.get(VIGOLIUM_STRATEGY, 'balanced')
      concurrency = discovery_config.get(VIGOLIUM_CONCURRENCY, 20)
      rate_limit = discovery_config.get(VIGOLIUM_RATE_LIMIT, 50)
      timeout = discovery_config.get(VIGOLIUM_TIMEOUT, '10s')

      if self.subscan and self.subdomain:
          subdomains = Subdomain.objects.filter(pk=self.subdomain.id)
      else:
          subdomains = Subdomain.objects.filter(scan_history=self.scan)

      if not subdomains.exists():
          logger.info("No subdomains found for Vigolium discovery.")
          return

      results_dir = f"{self.scan.results_dir}/vigolium/discovery"
      os.makedirs(results_dir, exist_ok=True)

      for subdomain in subdomains:
          target = f"https://{subdomain.name}"
          output_file = f"{results_dir}/{subdomain.name}_discovery.jsonl"

          cmd = (
              f"vigolium scan"
              f" -t {target}"
              f" --stateless"
              f" --format jsonl"
              f" -o {output_file}"
              f" --only ingestion,discovery"
              f" -c {concurrency}"
              f" -r {rate_limit}"
              f" --timeout {timeout}"
              f" --strategy {strategy}"
              f" --skip-dependency-check"
          )

          proxy = get_random_proxy()
          if proxy:
              cmd += f" --proxy {proxy}"

          _run_vigolium_phase(self, cmd, output_file, f"Discovery ({subdomain.name})", save_http_records=True)

      return "Vigolium discovery completed"


  def vigolium_analysis(self, ctx={}, description=None):
      """Run vigolium dynamic assessment for each subdomain at Tier 5.

      Runs the dynamic-assessment phase (passive + active module scanning)
      in parallel with web_api_discovery to find security weaknesses.
      Saves findings as Vulnerability records and discovered URLs as EndPoints.
      """
      logger.info("Starting Vigolium Dynamic Analysis")

      analysis_config = self.yaml_configuration.get('vigolium_analysis', {})
      if not analysis_config.get(RUN_VIGOLIUM_ANALYSIS, True):
          logger.info("Vigolium analysis disabled in configuration. Skipping.")
          return

      strategy = analysis_config.get(VIGOLIUM_STRATEGY, 'balanced')
      concurrency = analysis_config.get(VIGOLIUM_CONCURRENCY, 20)
      rate_limit = analysis_config.get(VIGOLIUM_RATE_LIMIT, 50)
      timeout = analysis_config.get(VIGOLIUM_TIMEOUT, '10s')

      if self.subscan and self.subdomain:
          subdomains = Subdomain.objects.filter(pk=self.subdomain.id)
      else:
          subdomains = Subdomain.objects.filter(scan_history=self.scan)

      if not subdomains.exists():
          logger.info("No subdomains found for Vigolium analysis.")
          return

      results_dir = f"{self.scan.results_dir}/vigolium/analysis"
      os.makedirs(results_dir, exist_ok=True)

      for subdomain in subdomains:
          target = f"https://{subdomain.name}"
          output_file = f"{results_dir}/{subdomain.name}_analysis.jsonl"

          cmd = (
              f"vigolium scan"
              f" -t {target}"
              f" --stateless"
              f" --format jsonl"
              f" -o {output_file}"
              f" --only dynamic-assessment"
              f" -c {concurrency}"
              f" -r {rate_limit}"
              f" --timeout {timeout}"
              f" --strategy {strategy}"
              f" --skip-dependency-check"
              f" --omit-response"
          )

          proxy = get_random_proxy()
          if proxy:
              cmd += f" --proxy {proxy}"

          _run_vigolium_phase(self, cmd, output_file, f"Analysis ({subdomain.name})", save_http_records=True)

      return "Vigolium analysis completed"
  ```

- [ ] **Step 4: Run tests**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks.VigoliumTaskGatingTest -v 2
  ```
  Expected: `OK (4 tests)`

- [ ] **Step 5: Run all vigolium tests**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks -v 2
  ```
  Expected: `OK (10 tests)`

- [ ] **Step 6: Commit**

  ```bash
  git add web/reNgine/vigolium_tasks.py web/tests/test_vigolium_tasks.py
  git commit -m "feat(vigolium): add vigolium scan, discovery, and analysis task functions"
  ```

---

## Task 5: Add three Temporal activities

**Files:**
- Modify: `web/reNgine/temporal_activities.py` (append after `RunSemgrepActivity`, around line 874)

- [ ] **Step 1: Write failing tests**

  Add to `web/tests/test_vigolium_tasks.py`:

  ```python
  class VigoliumActivitiesTest(TestCase):
      def test_activities_are_importable(self):
          from reNgine.temporal_activities import (
              run_vigolium_scan_activity,
              run_vigolium_discovery_activity,
              run_vigolium_analysis_activity,
          )
          self.assertTrue(callable(run_vigolium_scan_activity))
          self.assertTrue(callable(run_vigolium_discovery_activity))
          self.assertTrue(callable(run_vigolium_analysis_activity))
  ```

- [ ] **Step 2: Run to verify failure**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks.VigoliumActivitiesTest -v 2
  ```
  Expected: `ImportError: cannot import name 'run_vigolium_scan_activity'`

- [ ] **Step 3: Append activities to temporal_activities.py**

  Open `web/reNgine/temporal_activities.py`. After the `RunSemgrepActivity` block (around line 873) and **before** `MarkVulnerabilityScanCompleteActivity`, insert:

  ```python
  @activity.defn(name="RunVigoliumScanActivity")
  def run_vigolium_scan_activity(ctx: dict) -> bool:
      """Run Vigolium known-issue + dynamic-assessment scan against live endpoints.

      Runs inside NucleiPlannerWorkflow at Tier 6 alongside Nuclei. Default-enabled
      via vulnerability_scan.run_vigolium: true in the engine YAML config.
      """
      from reNgine.vigolium_tasks import vigolium_scan
      activity.logger.info(f"[RunVigoliumScanActivity] scan_id={ctx.get('scan_history_id')}")
      return _run_task(vigolium_scan, ctx, task_name='vigolium_scan', description='Vigolium Vulnerability Scan')


  @activity.defn(name="RunVigoliumDiscoveryActivity")
  def run_vigolium_discovery_activity(ctx: dict) -> bool:
      """Run Vigolium discovery phase to seed the endpoint DB.

      Runs at Tier 2 in parallel with http_crawl. Populates EndPoint records
      with URLs discovered by vigolium's ingestion + discovery phases.
      Controlled by vigolium_discovery.run_vigolium_discovery in engine YAML.
      """
      from reNgine.vigolium_tasks import vigolium_discovery
      activity.logger.info(f"[RunVigoliumDiscoveryActivity] scan_id={ctx.get('scan_history_id')}")
      return _run_task(vigolium_discovery, ctx, task_name='vigolium_discovery', description='Vigolium Endpoint Discovery')


  @activity.defn(name="RunVigoliumAnalysisActivity")
  def run_vigolium_analysis_activity(ctx: dict) -> bool:
      """Run Vigolium dynamic-assessment phase at Tier 5.

      Runs in parallel with web_api_discovery. Executes vigolium's 251-module
      passive + active scanning suite and saves findings as Vulnerability records.
      Controlled by vigolium_analysis.run_vigolium_analysis in engine YAML.
      """
      from reNgine.vigolium_tasks import vigolium_analysis
      activity.logger.info(f"[RunVigoliumAnalysisActivity] scan_id={ctx.get('scan_history_id')}")
      return _run_task(vigolium_analysis, ctx, task_name='vigolium_analysis', description='Vigolium Dynamic Analysis')
  ```

- [ ] **Step 4: Run to verify test passes**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks.VigoliumActivitiesTest -v 2
  ```
  Expected: `OK (1 test)`

- [ ] **Step 5: Commit**

  ```bash
  git add web/reNgine/temporal_activities.py web/tests/test_vigolium_tasks.py
  git commit -m "feat(vigolium): add RunVigoliumScanActivity, RunVigoliumDiscoveryActivity, RunVigoliumAnalysisActivity"
  ```

---

## Task 6: Wire vigolium into NucleiPlannerWorkflow (Tier 6)

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`

Vigolium runs **in parallel with Nuclei** — it adds zero wall-clock overhead because NucleiPlannerWorkflow already runs as a child workflow with its own history. Add it as the last scanner, after `RunSemgrepActivity`.

- [ ] **Step 1: Locate insertion point**

  Open `web/reNgine/temporal_workflows.py`. Find `NucleiPlannerWorkflow.run()`. The `RunSemgrepActivity` block ends around line 656. The `MarkVulnerabilityScanCompleteActivity` call follows at ~line 661.

- [ ] **Step 2: Insert vigolium block**

  After the `RunSemgrepActivity` block and **before** `MarkVulnerabilityScanCompleteActivity`, insert:

  ```python
          if vuln_config.get('run_vigolium', True):
              await workflow.execute_activity(
                  "RunVigoliumScanActivity",
                  ctx,
                  start_to_close_timeout=timedelta(hours=4),
                  heartbeat_timeout=timedelta(minutes=5),
                  retry_policy=_RETRY_LONG_SCAN,
                  task_queue="python-orchestrator-queue"
              )
  ```

- [ ] **Step 3: Verify import**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python -c "from reNgine.temporal_workflows import NucleiPlannerWorkflow; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 4: Commit**

  ```bash
  git add web/reNgine/temporal_workflows.py
  git commit -m "feat(vigolium): wire RunVigoliumScanActivity into NucleiPlannerWorkflow (Tier 6)"
  ```

---

## Task 7: Wire vigolium discovery into Tier 2 (parallel with http_crawl)

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`

Vigolium discovery runs in the `tier2_futures` list so it runs **concurrently** with `http_crawl` and `port_scan`. The `await asyncio.gather(*tier2_futures)` at line ~288 ensures Tier 3 waits for all of them.

- [ ] **Step 1: Locate tier2_futures**

  In `MasterScanWorkflow.run()`, find `tier2_futures = [_http_crawl_branch()]` (around line 274). The `port_scan` block follows. Insert vigolium discovery **after the `port_scan` block** and before `await asyncio.gather(*tier2_futures)`.

- [ ] **Step 2: Insert vigolium discovery block**

  ```python
          vigolium_discovery_config = yaml_config.get('vigolium_discovery', {})
          if vigolium_discovery_config.get('run_vigolium_discovery', True):
              tier2_futures.append(
                  workflow.execute_activity(
                      "RunVigoliumDiscoveryActivity",
                      ctx,
                      start_to_close_timeout=timedelta(hours=3),
                      heartbeat_timeout=timedelta(minutes=5),
                      retry_policy=_RETRY_LONG_SCAN,
                      task_queue="python-orchestrator-queue"
                  )
              )
  ```

- [ ] **Step 3: Verify import**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python -c "from reNgine.temporal_workflows import MasterScanWorkflow; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 4: Commit**

  ```bash
  git add web/reNgine/temporal_workflows.py
  git commit -m "feat(vigolium): wire RunVigoliumDiscoveryActivity into Tier 2 parallel group"
  ```

---

## Task 8: Wire vigolium analysis into Tier 5 (parallel with web_api_discovery)

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`

Vigolium analysis runs in `analysis_futures` alongside `web_api_discovery`, `waf_detection`, and `secret_scanning`.

- [ ] **Step 1: Locate analysis_futures**

  In `MasterScanWorkflow.run()`, find the Tier 5 block: `analysis_futures = []` (around line 339). The `secret_scanning` block ends around line 372. Insert vigolium analysis **after the `secret_scanning` block** and before `if analysis_futures:`.

- [ ] **Step 2: Insert vigolium analysis block**

  ```python
          vigolium_analysis_config = yaml_config.get('vigolium_analysis', {})
          if vigolium_analysis_config.get('run_vigolium_analysis', True):
              analysis_futures.append(
                  workflow.execute_activity(
                      "RunVigoliumAnalysisActivity",
                      ctx,
                      start_to_close_timeout=timedelta(hours=2),
                      heartbeat_timeout=timedelta(minutes=5),
                      retry_policy=_RETRY_LONG_SCAN,
                      task_queue="python-orchestrator-queue"
                  )
              )
  ```

- [ ] **Step 3: Verify all workflow imports**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python -c "
  from reNgine.temporal_workflows import MasterScanWorkflow, NucleiPlannerWorkflow
  from reNgine.temporal_activities import run_vigolium_scan_activity, run_vigolium_discovery_activity, run_vigolium_analysis_activity
  print('ALL OK')
  "
  ```
  Expected: `ALL OK`

- [ ] **Step 4: Commit**

  ```bash
  git add web/reNgine/temporal_workflows.py
  git commit -m "feat(vigolium): wire RunVigoliumAnalysisActivity into Tier 5 parallel group"
  ```

---

## Task 9: Update default YAML config fixtures

**Files:**
- Modify: `web/fixtures/default_yaml_config.yaml`
- Modify: `web/fixtures/default_scan_engines.yaml`

- [ ] **Step 1: Add vigolium to vulnerability_scan block in default_yaml_config.yaml**

  Open `web/fixtures/default_yaml_config.yaml`. In the `vulnerability_scan` block (lines 89–117), after `'run_wpscan': true,` add:

  ```yaml
    'run_vigolium': true,
    'vigolium': {
      'strategy': 'balanced',
      'concurrency': 50,
      'rate_limit': 100,
      'timeout': '15s'
    },
  ```

- [ ] **Step 2: Add vigolium_discovery and vigolium_analysis top-level blocks**

  After the closing `}` of the `vulnerability_scan` block (after line 117), add:

  ```yaml
  vigolium_discovery: {
    'run_vigolium_discovery': true,
    'strategy': 'balanced',
    'concurrency': 20,
    'rate_limit': 50,
    'timeout': '10s'
  }
  vigolium_analysis: {
    'run_vigolium_analysis': true,
    'strategy': 'balanced',
    'concurrency': 20,
    'rate_limit': 50,
    'timeout': '10s'
  }
  ```

- [ ] **Step 3: Update default_scan_engines.yaml**

  For each engine's embedded YAML config string that contains `'run_nuclei': true`, add `'run_vigolium': true` on the next line. Also add the `vigolium_discovery` and `vigolium_analysis` top-level blocks to each engine config.

- [ ] **Step 4: Reload fixtures**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py loaddata fixtures/default_yaml_config.yaml
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py loaddata fixtures/default_scan_engines.yaml
  ```
  Expected: no errors

- [ ] **Step 5: Verify vigolium appears in a loaded engine**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py shell -c "
  import yaml
  from scanEngine.models import EngineType
  e = EngineType.objects.filter(default_engine=True).first()
  cfg = yaml.safe_load(e.yaml_configuration)
  print('run_vigolium:', cfg.get('vulnerability_scan', {}).get('run_vigolium'))
  print('vigolium_discovery:', cfg.get('vigolium_discovery'))
  print('vigolium_analysis:', cfg.get('vigolium_analysis'))
  "
  ```
  Expected:
  ```
  run_vigolium: True
  vigolium_discovery: {'run_vigolium_discovery': True, 'strategy': 'balanced', 'concurrency': 20, 'rate_limit': 50, 'timeout': '10s'}
  vigolium_analysis: {'run_vigolium_analysis': True, 'strategy': 'balanced', 'concurrency': 20, 'rate_limit': 50, 'timeout': '10s'}
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add web/fixtures/default_yaml_config.yaml web/fixtures/default_scan_engines.yaml
  git commit -m "feat(vigolium): enable vigolium by default in all scan engine YAML configs"
  ```

---

## Task 10: Full test suite and verification

- [ ] **Step 1: Run all vigolium tests**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test tests.test_vigolium_tasks -v 2
  ```
  Expected: `OK (11 tests)` — all pass

- [ ] **Step 2: Run full test suite**

  ```bash
  docker exec r3ngine-temporal-python-orchestrator-1 python manage.py test -v 1
  ```
  Expected: same pass count as before this feature (no regressions)

- [ ] **Step 3: Verify activity registration after worker restart**

  ```bash
  docker compose restart temporal-python-orchestrator
  docker compose logs temporal-python-orchestrator | grep -i "vigolium"
  ```
  Expected: log lines confirming `RunVigoliumScanActivity`, `RunVigoliumDiscoveryActivity`, `RunVigoliumAnalysisActivity` registered.

- [ ] **Step 4: Final commit**

  ```bash
  git add .
  git commit -m "feat(vigolium): complete Vigolium integration — Tier 2/5/6 default background scanner"
  ```

---

## Post-Implementation Verification

- [ ] `vigolium version` works in the rebuilt container
- [ ] A new scan started from the UI shows vigolium discovery, analysis, and vuln scan activities in the Temporal workflow history
- [ ] Vulnerability findings from vigolium appear in scan results with `type='Vigolium'`
- [ ] Discovered endpoints from vigolium discovery appear in the Endpoints tab
- [ ] Vigolium phases are independently disableable via `run_vigolium: false`, `run_vigolium_discovery: false`, `run_vigolium_analysis: false` in the engine YAML
- [ ] The Temporal worker healthcheck passes after rebuild
