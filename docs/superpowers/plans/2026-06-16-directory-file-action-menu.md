# Directory File Action Menu Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `MoreHorizontal` action menu to each `DirectoryFile` row in the Directories tab, dispatching security testing actions (auth extraction, vuln scan, deep fuzz, WAF bypass, secret scan, brute test) against that endpoint URL via a unified backend API.

**Architecture:** A new `DirectoryFileDispatchView` (`POST /api/action/directory-file/dispatch/`) routes an `action` string to the appropriate existing URL workflow (`URLVulnWorkflow`, `URLFuzzWorkflow`, `URLBypassWorkflow`, `URLDirSearchWorkflow`) or a new `URLAuthExtractWorkflow`. A second view (`POST /api/action/directory-file/delete/`) handles record deletion. The frontend `DirectoriesTab` adds a `MoreHorizontal` trigger on each file row, opening a MUI `Menu` with 9 items — following the exact `VulnerabilityTable` action menu pattern with theme tokens only.

**Tech Stack:** Django REST Framework, Temporal Python SDK (temporalio 1.6.0), React 18, MUI v5, lucide-react, TanStack Query, TypeScript

---

## File Map

**New:**
- `web/tests/test_directory_file_actions.py` — backend tests

**Modified:**
- `web/reNgine/temporal_activities.py` — add `ExtractAuthForURLActivity`
- `web/reNgine/temporal_workflows.py` — add `URLAuthExtractWorkflow`
- `web/scanEngine/management/commands/run_temporal_orchestrator.py` — register workflow + activity
- `web/api/views.py` — add `DirectoryFileDispatchView`, `DirectoryFileDeleteView`
- `web/api/urls.py` — register two URL patterns
- `frontend/src/features/subdomains/types/index.ts` — add `id: number` to `DirectoryFile`
- `frontend/src/features/scans/api/index.ts` — add `useDirectoryFileDispatch`, `useDirectoryFileDelete`
- `frontend/src/features/scans/components/DirectoriesTab.tsx` — add action menu

---

### Task 1: ExtractAuthForURLActivity

**Files:**
- Modify: `web/reNgine/temporal_activities.py`
- Test: `web/tests/test_directory_file_actions.py` (create)

- [ ] **Step 1: Verify AuthCandidate model fields**

  Open `web/startScan/models.py`, search for `class AuthCandidate`. Note the exact field names — the implementation in Step 4 uses `scan_history`, `target`, `protocol`, `port`, `user_field`, `pass_field`, `method`, `hidden_fields`. Adjust if any name differs.

- [ ] **Step 2: Write the failing tests**

  Create `web/tests/test_directory_file_actions.py`:

  ```python
  from django.test import TestCase
  from unittest.mock import patch, MagicMock
  from startScan.models import ScanHistory


  class TestExtractAuthForURLActivity(TestCase):

      def setUp(self):
          self.scan = ScanHistory.objects.create(scan_status=0)

      @patch('reNgine.temporal_activities._fetch_with_proxy_retry')
      @patch('reNgine.temporal_activities._extract_login_forms')
      @patch('reNgine.temporal_activities.get_proxy_list', return_value=[])
      @patch('reNgine.temporal_activities.get_random_proxy', return_value=None)
      def test_extract_auth_saves_candidates(
          self, mock_rand_proxy, mock_proxy_list, mock_extract_forms, mock_fetch
      ):
          mock_response = MagicMock()
          mock_response.text = '<html></html>'
          mock_fetch.return_value = (mock_response, None)
          mock_extract_forms.return_value = [{
              'action': 'http://example.com/login',
              'method': 'POST',
              'user_field': 'username',
              'pass_field': 'password',
              'hidden_fields': {},
              'all_fields': ['username', 'password'],
          }]

          from reNgine.temporal_activities import extract_auth_for_url_activity
          result = extract_auth_for_url_activity({
              'url': 'http://example.com/login',
              'scan_id': self.scan.id,
          })

          self.assertEqual(result['found'], 1)

      @patch('reNgine.temporal_activities._fetch_with_proxy_retry')
      @patch('reNgine.temporal_activities.get_proxy_list', return_value=[])
      @patch('reNgine.temporal_activities.get_random_proxy', return_value=None)
      def test_extract_auth_no_forms_returns_zero(
          self, mock_rand_proxy, mock_proxy_list, mock_fetch
      ):
          mock_response = MagicMock()
          mock_response.text = '<html><body>No forms here</body></html>'
          mock_fetch.return_value = (mock_response, None)

          from reNgine.temporal_activities import extract_auth_for_url_activity
          with patch('reNgine.temporal_activities._extract_login_forms', return_value=[]):
              result = extract_auth_for_url_activity({
                  'url': 'http://example.com/page',
                  'scan_id': self.scan.id,
              })

          self.assertEqual(result['found'], 0)

      @patch('reNgine.temporal_activities._fetch_with_proxy_retry',
             side_effect=Exception("connection refused"))
      @patch('reNgine.temporal_activities.get_proxy_list', return_value=[])
      @patch('reNgine.temporal_activities.get_random_proxy', return_value=None)
      def test_extract_auth_fetch_failure_raises(
          self, mock_rand_proxy, mock_proxy_list, mock_fetch
      ):
          from reNgine.temporal_activities import extract_auth_for_url_activity
          with self.assertRaises(Exception):
              extract_auth_for_url_activity({
                  'url': 'http://example.com/login',
                  'scan_id': self.scan.id,
              })
  ```

- [ ] **Step 3: Run test to confirm it fails**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_directory_file_actions.TestExtractAuthForURLActivity --verbosity=2"
  ```

  Expected: `ImportError: cannot import name 'extract_auth_for_url_activity'`

- [ ] **Step 4: Implement the activity**

  Open `web/reNgine/temporal_activities.py`. At the top of the file, add alongside the existing imports (do NOT remove any):

  ```python
  from reNgine.auth_discovery_tasks import (
      _fetch_with_proxy_retry,
      _extract_login_forms,
  )
  ```

  Then add this function near the other scan-related activities (search for existing `@activity.defn` blocks):

  ```python
  @activity.defn(name="ExtractAuthForURLActivity")
  def extract_auth_for_url_activity(ctx: dict) -> dict:
      """Extract authentication form candidates from a single URL.

      Fetches the URL (with proxy retry), parses login forms, and saves
      discovered forms as AuthCandidate records linked to the scan.

      Args:
          ctx: dict with 'url' (str) and 'scan_id' (int).

      Returns:
          dict: {'found': int} — count of new AuthCandidate records saved.
      """
      from startScan.models import ScanHistory, AuthCandidate
      from reNgine.common_func import get_proxy_list, get_random_proxy
      from urllib.parse import urlparse

      url = ctx.get('url')
      scan_id = ctx.get('scan_id')

      activity.heartbeat()
      logger.log_line("[AUTH_EXTRACT]", "START", "extracting auth from %s (scan %s)" % (url, scan_id))

      try:
          scan = ScanHistory.objects.get(id=scan_id)

          proxy_list = get_proxy_list()
          if not proxy_list:
              tor_or_single = get_random_proxy()
              if tor_or_single:
                  proxy_list = [tor_or_single]

          parsed_url = urlparse(url)
          if parsed_url.scheme not in ('http', 'https'):
              logger.log_line("[AUTH_EXTRACT]", "COMPLETE", "skipped non-HTTP URL %s" % url)
              return {'found': 0}

          response, _ = _fetch_with_proxy_retry(url, proxy_list)
          forms = _extract_login_forms(response.text, url)

          if not forms:
              logger.log_line("[AUTH_EXTRACT]", "COMPLETE", "no auth forms found at %s" % url)
              return {'found': 0}

          raw_scheme = parsed_url.scheme.lower()
          protocol = 'http' if raw_scheme in ('http', 'https') else raw_scheme
          port = parsed_url.port or (443 if raw_scheme == 'https' else 80)

          saved = 0
          for form in forms:
              _, created = AuthCandidate.objects.get_or_create(
                  scan_history=scan,
                  target=form.get('action', url),
                  defaults={
                      'protocol': protocol,
                      'port': port,
                      'user_field': form.get('user_field', ''),
                      'pass_field': form.get('pass_field', ''),
                      'method': form.get('method', 'POST'),
                      'hidden_fields': form.get('hidden_fields', {}),
                  },
              )
              if created:
                  saved += 1

          logger.log_line("[AUTH_EXTRACT]", "COMPLETE",
                          "found %d new auth candidates from %s" % (saved, url))
          return {'found': saved}

      except Exception as exc:
          logger.log_line("[AUTH_EXTRACT]", "ERROR", format_exception_for_log(exc),
                          level="error", exc_info=True)
          raise
  ```

  > **Check:** Confirm field names against `AuthCandidate` model (Step 1). If `get_proxy_list` / `get_random_proxy` live somewhere other than `reNgine.common_func`, search the codebase for their definition and update the import.

- [ ] **Step 5: Run test to confirm it passes**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_directory_file_actions.TestExtractAuthForURLActivity --verbosity=2"
  ```

  Expected: `OK (3 tests)`

- [ ] **Step 6: Commit**

  ```bash
  git add web/reNgine/temporal_activities.py web/tests/test_directory_file_actions.py
  git commit -m "feat(temporal): add ExtractAuthForURLActivity for single-URL auth extraction"
  ```

---

### Task 2: URLAuthExtractWorkflow + worker registration

**Files:**
- Modify: `web/reNgine/temporal_workflows.py`
- Modify: `web/scanEngine/management/commands/run_temporal_orchestrator.py`

- [ ] **Step 1: Add workflow to `temporal_workflows.py`**

  Open `web/reNgine/temporal_workflows.py`. Find the URL workflow classes (search for `class URLVulnWorkflow`). Add directly after the last URL workflow class:

  ```python
  @workflow.defn(name="URLAuthExtractWorkflow")
  class URLAuthExtractWorkflow:
      """Extract authentication form candidates from a single URL.

      Expects ctx: {'url': str, 'scan_id': int}.
      Delegates to ExtractAuthForURLActivity with a 10-minute timeout.
      """

      @workflow.run
      async def run(self, ctx: dict) -> dict:
          return await workflow.execute_activity(
              "ExtractAuthForURLActivity",
              ctx,
              start_to_close_timeout=timedelta(minutes=10),
              retry_policy=_RETRY_INTERNAL,
              task_queue="python-orchestrator-queue",
          )
  ```

  > **Check:** Search `temporal_workflows.py` for `_RETRY_INTERNAL` to confirm the name. If it differs, use the correct retry policy constant.

- [ ] **Step 2: Register in the orchestrator**

  Open `web/scanEngine/management/commands/run_temporal_orchestrator.py`.

  Find the import of workflow classes (e.g. `from reNgine.temporal_workflows import MasterScanWorkflow, ...`). Add `URLAuthExtractWorkflow` to that import line.

  Find the import of activity functions (e.g. `from reNgine.temporal_activities import ...`). Add `extract_auth_for_url_activity` to that import line.

  In the `Worker(...)` call, add to `workflows=[...]`:
  ```python
  URLAuthExtractWorkflow,
  ```

  And add to `activities=[...]`:
  ```python
  extract_auth_for_url_activity,
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add web/reNgine/temporal_workflows.py web/scanEngine/management/commands/run_temporal_orchestrator.py
  git commit -m "feat(temporal): add URLAuthExtractWorkflow and register with orchestrator"
  ```

---

### Task 3: DirectoryFileDispatchView

**Files:**
- Modify: `web/api/views.py`
- Modify: `web/api/urls.py`
- Test: `web/tests/test_directory_file_actions.py`

- [ ] **Step 1: Find the credential_intelligence plugin workflow name**

  Open `d:/Repos/r3ngine/r3ngine-plugins/credential_intelligence/`. Find the file containing `@workflow.defn(name="...")`. Note the exact string — you will replace `'CredentialBruteWorkflow'` in Step 4 with this value.

- [ ] **Step 2: Write the failing tests**

  Append to `web/tests/test_directory_file_actions.py`:

  ```python
  from django.contrib.auth.models import User
  from rest_framework.test import APIClient


  class TestDirectoryFileDispatchView(TestCase):

      def setUp(self):
          self.user = User.objects.create_user('dispatchuser', password='testpass')
          self.client = APIClient()
          self.client.force_authenticate(user=self.user)

      @patch('api.views.run_and_close')
      @patch('api.views.TemporalClientProvider')
      def test_dispatch_scan_vuln_returns_dispatched(self, mock_tc, mock_run):
          mock_run.return_value = 'wf-test-123'
          response = self.client.post('/api/action/directory-file/dispatch/', {
              'url': 'http://example.com/admin/',
              'action': 'scan_vuln',
              'scan_id': 1,
          }, format='json')
          self.assertEqual(response.status_code, 200)
          self.assertEqual(response.data['status'], 'dispatched')
          self.assertIn('workflow_id', response.data)

      @patch('api.views.run_and_close')
      @patch('api.views.TemporalClientProvider')
      def test_dispatch_extract_auth_returns_dispatched(self, mock_tc, mock_run):
          mock_run.return_value = 'wf-auth-123'
          response = self.client.post('/api/action/directory-file/dispatch/', {
              'url': 'http://example.com/login.php',
              'action': 'extract_auth',
              'scan_id': 1,
          }, format='json')
          self.assertEqual(response.status_code, 200)
          self.assertEqual(response.data['status'], 'dispatched')

      def test_dispatch_unknown_action_returns_400(self):
          response = self.client.post('/api/action/directory-file/dispatch/', {
              'url': 'http://example.com/',
              'action': 'do_something_invalid',
              'scan_id': 1,
          }, format='json')
          self.assertEqual(response.status_code, 400)
          self.assertIn('error', response.data)

      def test_dispatch_missing_fields_returns_400(self):
          response = self.client.post('/api/action/directory-file/dispatch/', {
              'url': 'http://example.com/',
          }, format='json')
          self.assertEqual(response.status_code, 400)

      def test_dispatch_brute_test_without_plugin_returns_403(self):
          response = self.client.post('/api/action/directory-file/dispatch/', {
              'url': 'http://example.com/login',
              'action': 'brute_test',
              'scan_id': 1,
          }, format='json')
          self.assertEqual(response.status_code, 403)

      @patch('api.views.run_and_close')
      @patch('api.views.TemporalClientProvider')
      def test_dispatch_brute_test_with_plugin_enabled(self, mock_tc, mock_run):
          from plugins.models import Plugin
          Plugin.objects.create(
              name='Credential Intelligence',
              slug='credential_intelligence',
              version='1.4.0',
              is_enabled=True,
              anchor_step='web_api_discovery',
          )
          mock_run.return_value = 'wf-brute-123'
          response = self.client.post('/api/action/directory-file/dispatch/', {
              'url': 'http://example.com/login',
              'action': 'brute_test',
              'scan_id': 1,
          }, format='json')
          self.assertEqual(response.status_code, 200)
          self.assertEqual(response.data['status'], 'dispatched')

      def test_dispatch_requires_authentication(self):
          unauthenticated = APIClient()
          response = unauthenticated.post('/api/action/directory-file/dispatch/', {
              'url': 'http://example.com/',
              'action': 'scan_vuln',
              'scan_id': 1,
          }, format='json')
          self.assertIn(response.status_code, [401, 403])
  ```

- [ ] **Step 3: Run tests to confirm they fail**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_directory_file_actions.TestDirectoryFileDispatchView --verbosity=2"
  ```

  Expected: `AssertionError: 404 != 200` (URL not registered yet)

- [ ] **Step 4: Implement `DirectoryFileDispatchView` in `web/api/views.py`**

  Find an existing action view (search for `class InitiateSubTask`). Add the new class nearby:

  ```python
  class DirectoryFileDispatchView(APIView):
      """Dispatch a security testing action against a specific directory file URL.

      POST /api/action/directory-file/dispatch/
      Body: { url: str, action: str, scan_id: int }
      Returns: { status: "dispatched", workflow_id: str }
      """
      permission_classes = [IsAuthenticated]

      _WORKFLOW_MAP = {
          'scan_vuln':   ('URLVulnWorkflow',     {}),
          'deep_fuzz':   ('URLFuzzWorkflow',      {}),
          'bypass_waf':  ('URLBypassWorkflow',    {}),
          'secret_scan': ('URLDirSearchWorkflow', {'url_dirsearch': {'hunt_secrets': True}}),
      }
      _AUTH_WORKFLOW = 'URLAuthExtractWorkflow'

      def post(self, request):
          import asyncio
          import uuid
          from datetime import timedelta
          from django.utils import timezone
          from reNgine import temporal_client as _tc

          url = request.data.get('url')
          action = request.data.get('action')
          scan_id = request.data.get('scan_id')

          if not url or not action or scan_id is None:
              return Response(
                  {'error': 'url, action, and scan_id are required'},
                  status=status.HTTP_400_BAD_REQUEST,
              )

          wf_id = f"dir-file-{action}-{scan_id}-{uuid.uuid4().hex[:8]}"

          if action in self._WORKFLOW_MAP:
              workflow_name, extra_yaml = self._WORKFLOW_MAP[action]
              ctx = {
                  'urls': [url],
                  'yaml_configuration': extra_yaml,
                  'scan_history_id': scan_id,
              }
          elif action == 'extract_auth':
              workflow_name = self._AUTH_WORKFLOW
              ctx = {'url': url, 'scan_id': scan_id}
          elif action == 'brute_test':
              from plugins.models import Plugin
              plugin = Plugin.objects.filter(
                  slug='credential_intelligence', is_enabled=True
              ).first()
              if not plugin:
                  return Response(
                      {'error': 'Credential Intelligence plugin not installed or disabled'},
                      status=status.HTTP_403_FORBIDDEN,
                  )
              # Replace 'CredentialBruteWorkflow' with the exact @workflow.defn name
              # found in r3ngine-plugins/credential_intelligence/
              workflow_name = 'CredentialBruteWorkflow'
              ctx = {'url': url, 'scan_id': scan_id}
          else:
              return Response(
                  {'error': f'Unknown action: {action}'},
                  status=status.HTTP_400_BAD_REQUEST,
              )

          try:
              async def _start():
                  client = await _tc.TemporalClientProvider.get_client()
                  handle = await client.start_workflow(
                      workflow_name,
                      ctx,
                      id=wf_id,
                      task_queue='python-orchestrator-queue',
                      execution_timeout=timedelta(hours=1),
                  )
                  return handle.id

              loop = asyncio.new_event_loop()
              started_id = _tc.run_and_close(loop, _start())
              return Response(
                  {'status': 'dispatched', 'workflow_id': started_id or wf_id},
                  status=status.HTTP_200_OK,
              )
          except Exception as exc:
              logger.error(
                  "[DirectoryFileDispatchView] failed to start %s: %s",
                  workflow_name, str(exc),
              )
              return Response(
                  {'error': 'Failed to dispatch action'},
                  status=status.HTTP_500_INTERNAL_SERVER_ERROR,
              )
  ```

  > **Check:** Verify `run_and_close` in `reNgine/temporal_client.py`. If the name differs from `run_and_close`, update the call.

  > **Check:** Verify the four workflow class names (`URLVulnWorkflow`, `URLFuzzWorkflow`, `URLBypassWorkflow`, `URLDirSearchWorkflow`) against `@workflow.defn(name="...")` decorators in `temporal_workflows.py`. Update `_WORKFLOW_MAP` if any differ.

- [ ] **Step 5: Register URL in `web/api/urls.py`**

  Find the block with other `action/` endpoints. Add:

  ```python
  path('action/directory-file/dispatch/', DirectoryFileDispatchView.as_view(), name='directory-file-dispatch'),
  ```

  Add `DirectoryFileDispatchView` to the import from `api.views` at the top of `urls.py`.

- [ ] **Step 6: Run tests to confirm they pass**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_directory_file_actions.TestDirectoryFileDispatchView --verbosity=2"
  ```

  Expected: `OK (7 tests)`

- [ ] **Step 7: Commit**

  ```bash
  git add web/api/views.py web/api/urls.py web/tests/test_directory_file_actions.py
  git commit -m "feat(api): add DirectoryFileDispatchView for endpoint action dispatch"
  ```

---

### Task 4: DirectoryFileDeleteView

**Files:**
- Modify: `web/api/views.py`
- Modify: `web/api/urls.py`
- Test: `web/tests/test_directory_file_actions.py`

- [ ] **Step 1: Write the failing tests**

  Append to `web/tests/test_directory_file_actions.py`:

  ```python
  from django.utils import timezone
  from startScan.models import DirectoryFile


  class TestDirectoryFileDeleteView(TestCase):

      def setUp(self):
          self.user = User.objects.create_user('deluser', password='testpass')
          self.client = APIClient()
          self.client.force_authenticate(user=self.user)
          self.file1 = DirectoryFile.objects.create(
              name='L2FkbWlu',
              url='http://example.com/admin',
              http_status=200,
              length=1234,
          )
          self.file2 = DirectoryFile.objects.create(
              name='L2xvZ2lu',
              url='http://example.com/login',
              http_status=200,
              length=500,
          )

      def test_delete_records_by_ids(self):
          response = self.client.post('/api/action/directory-file/delete/', {
              'directory_file_ids': [self.file1.id, self.file2.id],
          }, format='json')
          self.assertEqual(response.status_code, 200)
          self.assertEqual(response.data['deleted'], 2)
          self.assertFalse(DirectoryFile.objects.filter(id=self.file1.id).exists())
          self.assertFalse(DirectoryFile.objects.filter(id=self.file2.id).exists())

      def test_delete_missing_ids_returns_400(self):
          response = self.client.post('/api/action/directory-file/delete/', {}, format='json')
          self.assertEqual(response.status_code, 400)

      def test_delete_empty_list_returns_400(self):
          response = self.client.post('/api/action/directory-file/delete/', {
              'directory_file_ids': [],
          }, format='json')
          self.assertEqual(response.status_code, 400)

      def test_delete_requires_authentication(self):
          unauthenticated = APIClient()
          response = unauthenticated.post('/api/action/directory-file/delete/', {
              'directory_file_ids': [self.file1.id],
          }, format='json')
          self.assertIn(response.status_code, [401, 403])
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_directory_file_actions.TestDirectoryFileDeleteView --verbosity=2"
  ```

  Expected: `AssertionError: 404 != 200`

- [ ] **Step 3: Implement `DirectoryFileDeleteView` in `web/api/views.py`**

  Add directly after `DirectoryFileDispatchView`:

  ```python
  class DirectoryFileDeleteView(APIView):
      """Delete DirectoryFile records by primary key.

      POST /api/action/directory-file/delete/
      Body: { directory_file_ids: [int] }
      Returns: { deleted: int }
      """
      permission_classes = [IsAuthenticated]

      def post(self, request):
          from startScan.models import DirectoryFile

          ids = request.data.get('directory_file_ids')
          if not ids:
              return Response(
                  {'error': 'directory_file_ids is required and must not be empty'},
                  status=status.HTTP_400_BAD_REQUEST,
              )

          deleted_count, _ = DirectoryFile.objects.filter(id__in=ids).delete()
          return Response({'deleted': deleted_count}, status=status.HTTP_200_OK)
  ```

- [ ] **Step 4: Register URL in `web/api/urls.py`**

  Add alongside the dispatch URL:

  ```python
  path('action/directory-file/delete/', DirectoryFileDeleteView.as_view(), name='directory-file-delete'),
  ```

  Add `DirectoryFileDeleteView` to the import from `api.views`.

- [ ] **Step 5: Run all backend tests**

  ```bash
  docker exec -it r3ngine-web-1 bash -c "cd /usr/src/app && python3 manage.py test tests.test_directory_file_actions --verbosity=2"
  ```

  Expected: `OK (14 tests)`

- [ ] **Step 6: Commit**

  ```bash
  git add web/api/views.py web/api/urls.py web/tests/test_directory_file_actions.py
  git commit -m "feat(api): add DirectoryFileDeleteView for endpoint record deletion"
  ```

---

### Task 5: Frontend types and API hooks

**Files:**
- Modify: `frontend/src/features/subdomains/types/index.ts`
- Modify: `frontend/src/features/scans/api/index.ts`

- [ ] **Step 1: Add `id` to `DirectoryFile` interface**

  Open `frontend/src/features/subdomains/types/index.ts`. Find `DirectoryFile` (around line 22). Add `id: number` as the first field:

  ```typescript
  export interface DirectoryFile {
    id: number;       // ← add this
    name: string;
    url: string;
    http_status: number;
    length: number;
    lines: number | null;
    words: number | null;
    content_type: string;
  }
  ```

- [ ] **Step 2: Add mutation hooks to `frontend/src/features/scans/api/index.ts`**

  Open the file. Check how existing mutations import CSRF token (search for `getCsrfToken` or `csrftoken`). Use that same pattern below.

  Add these two hooks after the existing `useDirectories` hook:

  ```typescript
  export const useDirectoryFileDispatch = () => {
    return useMutation({
      mutationFn: async (params: {
        url: string;
        action: string;
        scan_id: number;
      }): Promise<{ status: string; workflow_id: string }> => {
        const response = await axios.post(
          '/api/action/directory-file/dispatch/',
          params,
          {
            headers: {
              'X-CSRFToken': document.cookie
                .split('; ')
                .find((row) => row.startsWith('csrftoken='))
                ?.split('=')[1] ?? '',
            },
          }
        );
        return response.data;
      },
    });
  };

  export const useDirectoryFileDelete = () => {
    const queryClient = useQueryClient();
    return useMutation({
      mutationFn: async (params: {
        directory_file_ids: number[];
      }): Promise<{ deleted: number }> => {
        const response = await axios.post(
          '/api/action/directory-file/delete/',
          params,
          {
            headers: {
              'X-CSRFToken': document.cookie
                .split('; ')
                .find((row) => row.startsWith('csrftoken='))
                ?.split('=')[1] ?? '',
            },
          }
        );
        return response.data;
      },
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ['directories'] });
      },
    });
  };
  ```

  > **Check:** If the file already has a `getCsrfToken()` helper imported, use it instead of the inline cookie parse above — keep it DRY.

- [ ] **Step 3: Commit**

  ```bash
  git add frontend/src/features/subdomains/types/index.ts frontend/src/features/scans/api/index.ts
  git commit -m "feat(frontend): add DirectoryFile id field and dispatch/delete API hooks"
  ```

---

### Task 6: DirectoriesTab action menu

**Files:**
- Modify: `frontend/src/features/scans/components/DirectoriesTab.tsx`

Before starting, read `frontend/src/features/vulnerabilities/components/VulnerabilityTable.tsx` lines 898–1758. The state variables, handler pattern, Menu JSX, Backdrop, ConfirmDialog, and Snackbar there are the exact template to follow.

- [ ] **Step 1: Add imports**

  Open `DirectoriesTab.tsx`. Add any of the following that are not already imported:

  ```typescript
  import {
    Menu,
    MenuItem,
    ListItemIcon,
    ListItemText,
    Divider,
    Backdrop,
    CircularProgress,
    Snackbar,
    Alert,
    Tooltip,
    Stack,
    Typography,
  } from '@mui/material';
  import { useTheme } from '@mui/material/styles';
  import {
    MoreHorizontal,
    KeyRound,
    ShieldAlert,
    Crosshair,
    ScanSearch,
    Zap,
    UserX,
    Copy,
    ExternalLink,
    Trash2,
  } from 'lucide-react';
  ```

  Then search the codebase for `usePlugins` and `ConfirmDialog` to find their exact import paths, and add:

  ```typescript
  import { usePlugins } from '<exact-path-from-codebase>';
  import { ConfirmDialog } from '<exact-path-from-codebase>';
  import { useDirectoryFileDispatch, useDirectoryFileDelete } from '../api';
  ```

- [ ] **Step 2: Add state and mutations inside `DirectoriesTab`**

  Find the `DirectoriesTab` function body (line 48). After the existing state declarations, add:

  ```typescript
  const theme = useTheme();
  const isLight = theme.palette.mode === 'light';

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedFile, setSelectedFile] = useState<DirectoryFile | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmConfig, setConfirmConfig] = useState<{
    title: string;
    message: string;
    onConfirm: () => void;
    type?: 'danger' | 'info' | 'warning';
  }>({ title: '', message: '', onConfirm: () => {} });
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({ open: false, message: '', severity: 'success' });

  const { data: plugins } = usePlugins();
  const credPluginEnabled = plugins?.some(
    (p: { slug: string; is_enabled: boolean }) =>
      p.slug === 'credential_intelligence' && p.is_enabled
  );

  const dispatchMutation = useDirectoryFileDispatch();
  const deleteMutation = useDirectoryFileDelete();

  const showNotification = (
    message: string,
    severity: 'success' | 'error' | 'info' | 'warning' = 'success'
  ) => setSnackbar({ open: true, message, severity });
  ```

- [ ] **Step 3: Add handler functions**

  Add inside `DirectoriesTab`, after the state declarations:

  ```typescript
  const handleActionClick = (
    event: React.MouseEvent<HTMLButtonElement>,
    file: DirectoryFile
  ) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
    setSelectedFile(file);
  };

  const handleActionClose = () => setAnchorEl(null);

  const handleDispatchAction = async (action: string, label: string) => {
    if (!selectedFile || !scanId) return;
    handleActionClose();
    try {
      await dispatchMutation.mutateAsync({ url: selectedFile.url, action, scan_id: scanId });
      showNotification(`${label} DISPATCHED`);
    } catch {
      showNotification(`Failed to dispatch ${label.toLowerCase()} — check Temporal logs`, 'error');
    }
  };

  const handleCopyUrl = () => {
    if (selectedFile) {
      navigator.clipboard.writeText(selectedFile.url);
      showNotification('URL COPIED TO CLIPBOARD', 'info');
    }
    handleActionClose();
  };

  const handleOpenInBrowser = () => {
    if (selectedFile) window.open(selectedFile.url, '_blank', 'noopener,noreferrer');
    handleActionClose();
  };

  const handleDelete = () => {
    if (!selectedFile) return;
    handleActionClose();
    setConfirmConfig({
      title: 'DELETE ENDPOINT RECORD',
      message: `Delete the record for ${selectedFile.url}? This cannot be undone.`,
      type: 'danger',
      onConfirm: async () => {
        try {
          await deleteMutation.mutateAsync({ directory_file_ids: [selectedFile.id] });
          showNotification('ENDPOINT RECORD DELETED');
        } catch {
          showNotification('Failed to delete endpoint record', 'error');
        }
      },
    });
    setConfirmOpen(true);
  };
  ```

- [ ] **Step 4: Add the trigger button to each file row**

  Find the `DirectoryFile` row renderer inside `DirectoriesTab` (search for `scan.directory_files.map` around line 442). The row callback variable may be named `file`, `dirFile`, or `f` — use whatever name is already there.

  At the end of each row's JSX, after the existing external link icon button, add:

  ```tsx
  <IconButton
    size="small"
    onClick={(e) => handleActionClick(e, file)}
    sx={{
      color: theme.palette.text.secondary,
      p: 0.5,
      '&:hover': {
        color: isLight ? theme.palette.primary.main : theme.palette.primary.light,
      },
    }}
  >
    <MoreHorizontal size={14} />
  </IconButton>
  ```

- [ ] **Step 5: Add Menu, ConfirmDialog, Backdrop, and Snackbar JSX**

  In the return statement of `DirectoriesTab`, before the final closing tag, add:

  ```tsx
  {/* Directory File Action Menu */}
  <Menu
    anchorEl={anchorEl}
    open={Boolean(anchorEl)}
    onClose={handleActionClose}
    slotProps={{
      paper: {
        sx: {
          bgcolor: isLight ? 'background.paper' : 'background.default',
          border: isLight
            ? `1px solid ${theme.palette.divider}`
            : `1px solid ${theme.palette.primary.main}33`,
          color: 'text.primary',
          minWidth: 220,
          '& .MuiMenuItem-root': {
            fontSize: '0.8rem',
            fontWeight: 600,
            fontFamily: 'Inter, sans-serif',
            py: 1,
            gap: 1.5,
            '&:hover': {
              bgcolor: isLight ? 'action.hover' : `${theme.palette.primary.main}15`,
            },
          },
        },
      },
    }}
  >
    <MenuItem onClick={() => handleDispatchAction('extract_auth', 'AUTH EXTRACTION')}>
      <ListItemIcon><KeyRound size={15} color={theme.palette.warning.main} /></ListItemIcon>
      <ListItemText primary="EXTRACT AUTH" />
    </MenuItem>
    <MenuItem onClick={() => handleDispatchAction('scan_vuln', 'VULNERABILITY SCAN')}>
      <ListItemIcon><ShieldAlert size={15} color={theme.palette.error.main} /></ListItemIcon>
      <ListItemText primary="SCAN VULNERABILITIES" />
    </MenuItem>
    <MenuItem onClick={() => handleDispatchAction('deep_fuzz', 'DEEP FUZZ')}>
      <ListItemIcon><Crosshair size={15} color={theme.palette.info.main} /></ListItemIcon>
      <ListItemText primary="DEEP FUZZ" />
    </MenuItem>
    <MenuItem onClick={() => handleDispatchAction('secret_scan', 'SECRET SCAN')}>
      <ListItemIcon><ScanSearch size={15} color={theme.palette.success.main} /></ListItemIcon>
      <ListItemText primary="SCAN FOR SECRETS" />
    </MenuItem>
    <MenuItem onClick={() => handleDispatchAction('bypass_waf', 'WAF BYPASS')}>
      <ListItemIcon><Zap size={15} color={theme.palette.secondary.main} /></ListItemIcon>
      <ListItemText primary="BYPASS WAF" />
    </MenuItem>
    <Divider sx={{ my: 0.5, borderColor: theme.palette.divider }} />
    <Tooltip
      title={credPluginEnabled ? '' : 'Credential Intelligence plugin not installed'}
      placement="left"
    >
      <span>
        <MenuItem
          disabled={!credPluginEnabled}
          onClick={() => handleDispatchAction('brute_test', 'BRUTE TEST')}
        >
          <ListItemIcon>
            <UserX
              size={15}
              color={credPluginEnabled ? theme.palette.warning.main : theme.palette.text.disabled}
            />
          </ListItemIcon>
          <ListItemText primary="SEND TO BRUTE TEST" />
        </MenuItem>
      </span>
    </Tooltip>
    <Divider sx={{ my: 0.5, borderColor: theme.palette.divider }} />
    <MenuItem onClick={handleCopyUrl}>
      <ListItemIcon><Copy size={15} color={theme.palette.text.secondary} /></ListItemIcon>
      <ListItemText primary="COPY URL" />
    </MenuItem>
    <MenuItem onClick={handleOpenInBrowser}>
      <ListItemIcon><ExternalLink size={15} color={theme.palette.text.secondary} /></ListItemIcon>
      <ListItemText primary="OPEN IN BROWSER" />
    </MenuItem>
    <Divider sx={{ my: 0.5, borderColor: theme.palette.divider }} />
    <MenuItem onClick={handleDelete} sx={{ color: theme.palette.error.main }}>
      <ListItemIcon><Trash2 size={15} color={theme.palette.error.main} /></ListItemIcon>
      <ListItemText primary="DELETE RECORD" />
    </MenuItem>
  </Menu>

  {/* Confirm Dialog */}
  <ConfirmDialog
    open={confirmOpen}
    onClose={() => { setConfirmOpen(false); setSelectedFile(null); }}
    onConfirm={() => { confirmConfig.onConfirm(); setConfirmOpen(false); }}
    title={confirmConfig.title}
    message={confirmConfig.message}
    type={confirmConfig.type}
  />

  {/* Loading Backdrop */}
  <Backdrop
    sx={{
      color: theme.palette.primary.main,
      zIndex: (t) => t.zIndex.drawer + 1,
      bgcolor: 'rgba(0,0,0,0.8)',
    }}
    open={dispatchMutation.isPending || deleteMutation.isPending}
  >
    <Stack spacing={2} alignItems="center">
      <CircularProgress color="inherit" size={60} thickness={2} />
      <Typography sx={{ fontFamily: 'Orbitron, sans-serif', letterSpacing: 2, fontSize: '0.9rem' }}>
        {deleteMutation.isPending ? 'DELETING RECORD...' : 'DISPATCHING ACTION...'}
      </Typography>
    </Stack>
  </Backdrop>

  {/* Snackbar */}
  <Snackbar
    open={snackbar.open}
    autoHideDuration={4000}
    onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
    anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
  >
    <Alert
      onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
      severity={snackbar.severity}
      variant="filled"
    >
      {snackbar.message}
    </Alert>
  </Snackbar>
  ```

  > **Check:** Verify `ConfirmDialog` prop names against its actual component definition. If prop names differ (e.g., `body` instead of `message`), use the correct names.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/src/features/scans/components/DirectoriesTab.tsx
  git commit -m "feat(frontend): add action menu to DirectoriesTab file endpoint rows"
  ```

---

### Task 7: Frontend build verification

- [ ] **Step 1: Run the build locally**

  ```bash
  cd d:/Repos/r3ngine/frontend && npm run build
  ```

  Expected: Build completes with no TypeScript errors.

- [ ] **Step 2: Fix any TypeScript errors**

  Common issues:
  - `ConfirmDialog` prop type mismatch — check the component definition and adjust prop names
  - `usePlugins()` return type — update the `credPluginEnabled` filter cast if the Plugin type has a different shape
  - `DirectoryFile.id` — adding a field is non-breaking; no existing code should fail

- [ ] **Step 3: Commit if any fixes applied**

  ```bash
  git add frontend/src/features/scans/components/DirectoriesTab.tsx
  git commit -m "fix(frontend): resolve TypeScript errors in DirectoriesTab action menu"
  ```

---

## Self-Review

**Spec coverage:**
- ✅ `ExtractAuthForURLActivity` — Task 1
- ✅ `URLAuthExtractWorkflow` — Task 2
- ✅ Activity + workflow registered in orchestrator — Task 2
- ✅ `DirectoryFileDispatchView` (all 6 actions) — Task 3
- ✅ `DirectoryFileDeleteView` — Task 4
- ✅ URL patterns — Tasks 3 & 4
- ✅ Backend tests (14 total) — Tasks 1, 3, 4
- ✅ `DirectoryFile.id` TypeScript field — Task 5
- ✅ `useDirectoryFileDispatch` / `useDirectoryFileDelete` — Task 5
- ✅ 9-item action menu — Task 6
- ✅ `MoreHorizontal` trigger alongside existing external link icon — Task 6
- ✅ Theme tokens only (no hardcoded hex) — Task 6
- ✅ `credential_intelligence` conditional (disabled + Tooltip) — Task 6
- ✅ `ConfirmDialog` for delete — Task 6
- ✅ `Backdrop` + loading label — Task 6
- ✅ `Snackbar` notifications — Task 6
- ✅ Frontend build verification — Task 7

**Open item:** The `brute_test` branch in Task 3 uses `'CredentialBruteWorkflow'` as a placeholder. The implementer must read the credential_intelligence plugin source (Step 1 of Task 3) to find the actual `@workflow.defn(name="...")` value and replace it before that branch is exercised.
