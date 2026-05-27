"""
Temporary cleanup script — cancel all RUNNING Temporal workflows and
mark any DB-orphaned scans/subscans as ABORTED_TASK.

Run inside the web container:
    python3 scripts/flush_workflows.py
"""
import asyncio
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reNgine.settings")
django.setup()

from temporalio.client import Client
from startScan.models import ScanHistory, SubScan, TemporalWorkflowExecution
from reNgine.definitions import RUNNING_TASK, ABORTED_TASK
from django.utils import timezone


async def list_running_workflows(client):
    running = []
    async for wf in client.list_workflows('ExecutionStatus="Running"'):
        running.append(wf.id)
    return running


SYSTEM_WORKFLOW_PREFIX = "temporal-sys-scheduler:"


async def terminate_workflow(client, workflow_id):
    try:
        handle = client.get_workflow_handle(workflow_id)
        await handle.terminate(reason="Manual flush: no scans should be running")
        return True
    except Exception as e:
        print(f"  WARN: could not terminate {workflow_id}: {e}")
        return False


async def main():
    host = os.environ.get("TEMPORAL_HOST", "temporal:7233")
    ns = os.environ.get("TEMPORAL_NAMESPACE", "default")
    print(f"Connecting to Temporal at {host} namespace={ns}")
    client = await Client.connect(host, namespace=ns)

    # --- Step 1: list all running workflows ---
    print("\n=== Step 1: Listing all running Temporal workflows ===")
    running_ids = await list_running_workflows(client)
    system_ids = [w for w in running_ids if w.startswith(SYSTEM_WORKFLOW_PREFIX)]
    scan_ids = [w for w in running_ids if not w.startswith(SYSTEM_WORKFLOW_PREFIX)]

    if not running_ids:
        print("No running workflows found in Temporal.")
    else:
        print(f"Found {len(running_ids)} running workflow(s):")
        for wid in system_ids:
            print(f"  [SYSTEM - skip] {wid}")
        for wid in scan_ids:
            print(f"  [SCAN/SUBSCAN]  {wid}")

    # --- Step 2: terminate scan/subscan workflows (use terminate, not cancel) ---
    if scan_ids:
        print(f"\n=== Step 2: Terminating {len(scan_ids)} scan/subscan workflow(s) ===")
        terminated = 0
        for wid in scan_ids:
            ok = await terminate_workflow(client, wid)
            if ok:
                terminated += 1
                print(f"  TERMINATED: {wid}")
        print(f"Terminated {terminated}/{len(scan_ids)} workflows.")
    else:
        terminated = 0
        print("\n=== Step 2: No scan/subscan workflows to terminate ===")

    print("\n=== Done (Temporal) ===")
    print(f"Temporal workflows terminated: {terminated}")
    return terminated


cancelled_count = asyncio.run(main())

# --- Step 3: DB cleanup (sync, outside asyncio context) ---
print("\n=== Step 3: Cleaning up Django DB ===")

running_scans = ScanHistory.objects.filter(scan_status=RUNNING_TASK)
scan_count = running_scans.count()
print(f"RUNNING scans in DB: {scan_count}")
for scan in running_scans:
    scan.scan_status = ABORTED_TASK
    scan.stop_scan_date = timezone.now()
    scan.save()
    print(f"  Marked scan {scan.id} ABORTED")

running_subs = SubScan.objects.filter(status=RUNNING_TASK)
sub_count = running_subs.count()
print(f"RUNNING subscans in DB: {sub_count}")
for sub in running_subs:
    sub.status = ABORTED_TASK
    sub.stop_scan_date = timezone.now()
    sub.save()
    print(f"  Marked subscan {sub.id} ABORTED")

te_qs = TemporalWorkflowExecution.objects.filter(status="RUNNING")
te_count = te_qs.count()
print(f"RUNNING TemporalWorkflowExecution records in DB: {te_count}")
te_qs.update(status="CANCELLED", ended_at=timezone.now())
print(f"  Updated {te_count} record(s) to CANCELLED")

print("\n=== All Done ===")
print(f"Temporal workflows terminated: {cancelled_count}")
print(f"DB scans marked ABORTED      : {scan_count}")
print(f"DB subscans marked ABORTED   : {sub_count}")
print(f"TemporalExec records CANCELLED: {te_count}")
