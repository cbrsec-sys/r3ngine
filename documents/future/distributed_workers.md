# Implement Distributed Backend Workers

This plan outlines the architecture and implementation for supporting distributed Python Orchestrator workers in r3ngine. Workers will be configured via a new Settings page, report their heartbeat periodically, and can be dynamically selected by users when initiating scans from the frontend.

## Proposed Changes

### 1. Database Model
**`web/scanEngine/models.py`**
- [NEW] Create a new `ScanWorker` model.
```python
class ScanWorker(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    auth_token = models.CharField(max_length=255, unique=True) # Used to secure worker access
    task_queue = models.CharField(max_length=100)
    hostname = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.name
```
- A database migration will be generated and applied.

### 2. Backend Orchestrator Script
#### [MODIFY] [run_temporal_orchestrator.py](file:///d:/Repos/r3ngine/web/scanEngine/management/commands/run_temporal_orchestrator.py)
- Update the Django management command to accept `--worker-name` and `--worker-token` arguments.
- Read `worker_name` and `worker_token` from args or environment variables.
- **Security Check:** Upon startup, query the `ScanWorker` table to verify the provided `worker_name` and `worker_token` match a configured, active worker. If they do not match or the token is invalid, log a security error and exit immediately to prevent unauthorized access.
- Set `task_queue` dynamically: if `"default-worker"`, use `"python-orchestrator-queue"`, otherwise use `"python-orchestrator-queue-{worker_name}"`.
- Add an `asyncio` background task inside `handle()` that periodically (e.g., every 30 seconds) updates the worker's `last_heartbeat`, `hostname`, and `ip_address` in the `ScanWorker` table via the Django ORM. The heartbeat should also re-verify the token, shutting down the worker if the token is revoked or changed in the backend.

### 3. Backend API & Task Dispatch
#### [MODIFY] [views.py](file:///d:/Repos/r3ngine/web/api/views.py)
- Create `WorkersAPIView` that handles `GET` (list all workers), `POST` (create a new worker config), and `DELETE` (remove a worker).
- Update `InitiateScan` and `InitiateSubTask` views to accept an optional `task_queue` or `worker_name` from the request payload and pass it downstream.

#### [MODIFY] [urls.py](file:///d:/Repos/r3ngine/web/api/urls.py)
- Register the `/api/settings/workers/` endpoint for the `WorkersAPIView`.

#### [MODIFY] [tasks.py](file:///d:/Repos/r3ngine/web/reNgine/tasks.py)
- Update `initiate_scan_temporal` and `initiate_subscan_temporal` to accept a `task_queue` parameter.
- Use this `task_queue` parameter in the `client.start_workflow` calls instead of hardcoding `"python-orchestrator-queue"`. Fallback to `"python-orchestrator-queue"` if none is provided.

### 4. Frontend Settings & Worker Selection
#### [NEW] [RemoteWorkersPage.tsx](file:///d:/Repos/r3ngine/frontend/src/features/settings/components/RemoteWorkersPage.tsx)
- Create a new settings page for "Distributed Workers".
- The UI will allow users to ADD new workers (giving them a name and description), VIEW existing workers with their current status (Online / Offline based on `last_heartbeat`), and DELETE workers.
- When a worker is created, a secure `auth_token` is generated and displayed to the user (can be copied).
- The UI will provide the exact Docker / CLI command to run for each configured worker (e.g. `python manage.py run_temporal_orchestrator --worker-name <name> --worker-token <token>`).

#### [MODIFY] [Shell/index.tsx](file:///d:/Repos/r3ngine/frontend/src/components/Shell/index.tsx) & [router.tsx](file:///d:/Repos/r3ngine/frontend/src/router.tsx)
- Register `RemoteWorkersPage` in the React router and add it to the settings sidebar menu.

#### [NEW] [workersApi.ts](file:///d:/Repos/r3ngine/frontend/src/features/scans/api/workersApi.ts) (or add to existing settings API)
- Create `useWorkers` hooks for fetching, creating, and deleting workers.

#### [MODIFY] [StartScanModal.tsx](file:///d:/Repos/r3ngine/frontend/src/features/scans/components/StartScanModal.tsx)
- Integrate the `useWorkers` hook to fetch active workers.
- Add a new "Select Orchestrator Worker" dropdown field in the "Primary Configuration" section.
- The dropdown will show "Default Worker (Round Robin)" as the default option, and list any active registered workers.
- Add the selected worker's `task_queue` to the scan initiation payload.

## Open Questions

None at this time. The plan directly incorporates the feedback to provide a dedicated Settings UI for remote worker configuration.

## Verification Plan

### Automated Tests
- Run `flake8` / `mypy` locally (if available) on the changed python files.
- Run `npm run build` in the `frontend` directory to verify TypeScript compiles correctly.

### Manual Verification
1. Open the web UI, go to Settings -> Remote Workers.
2. Create a new worker named "remote-worker-1".
3. Open a terminal and run `python manage.py run_temporal_orchestrator --worker-name remote-worker-1`.
4. Verify the worker shows as "Online" in the UI.
5. Click "Initiate Scan" and verify that "remote-worker-1" appears in the worker dropdown.
6. Initiate a scan using "remote-worker-1" and verify that the workflow executes on that specific worker's task queue.
