"""Activities that run a per-host tool over batches of hosts.

The workflow side (`_run_chunked` in temporal/workflows/_common.py) plans the
batches with PlanChunkedTaskActivity, runs RunChunkedTaskBatchActivity for each
of them a few at a time, and closes the step with FinalizeChunkedTaskActivity.

All batches write to the step's one planned timeline row: they run untracked
with that row's activity_id, so their commands and the per-batch progress lines
appear in its detail overlay, and Retry/recovery keep working by task name.
The host lists stay in a plan file next to the scan results and never enter the
workflow history.
"""
import json
import os
from dataclasses import dataclass
from typing import Callable

from django.utils import timezone
from temporalio import activity

from reNgine.chunking import batching_config, plan_batches, target_host
from reNgine.temporal.activities.core import TemporalTaskProxy, _run_task
from reNgine.temporal.heartbeat import keep_alive
from reNgine.utils.logger import get_module_logger

logger = get_module_logger(__name__)

#: Error text stored on the step's row; ScanActivity.error_message holds 300 characters.
_MESSAGE_LIMIT = 300


@dataclass(frozen=True)
class ChunkedTask:
    """What the batching machinery needs to know about one tool."""

    title: str
    config_key: str
    select_targets: Callable  # (proxy, ctx) -> list[str]
    run_batch: Callable  # (ctx, targets) -> None
    is_done: Callable  # (results_dir, target) -> bool
    finalize: Callable  # (proxy, ctx, targets) -> None


def _fuzz_targets(proxy, ctx: dict) -> list:
    from reNgine.tasks.fuzzing import dir_file_fuzz
    prepared = dir_file_fuzz(proxy, ctx=ctx, prepare_only=True) or {}
    return list(prepared.get('urls') or []) if isinstance(prepared, dict) else []


def _fuzz_batch(ctx: dict, targets: list) -> None:
    from reNgine.tasks.fuzzing import dir_file_fuzz
    _run_task(
        dir_file_fuzz,
        {**ctx, 'urls_override': targets, 'skip_post_crawl': True},
        task_name='dir_file_fuzz',
        description='Directory & File Fuzz',
    )


def _fuzz_done(results_dir: str, target: str) -> bool:
    from reNgine.tasks.fuzzing import _fuzz_target_marker
    return os.path.exists(_fuzz_target_marker(results_dir, target))


def _fuzz_finalize(proxy, ctx: dict, targets: list) -> None:
    """The batches skip the fuzzer's trailing crawl of its targets; run it once here."""
    from reNgine.definitions import DIR_FILE_FUZZ, ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL
    from reNgine.tasks import http_crawl
    config = proxy.yaml_configuration.get(DIR_FILE_FUZZ) or {}
    if targets and config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL):
        http_crawl(proxy, targets, ctx={**ctx, 'track': True})


CHUNKED_TASKS = {
    'dir_file_fuzz': ChunkedTask(
        title='Directory & File Fuzz',
        config_key='dir_file_fuzz',
        select_targets=_fuzz_targets,
        run_batch=_fuzz_batch,
        is_done=_fuzz_done,
        finalize=_fuzz_finalize,
    ),
}


def _chunked_task(task: str) -> ChunkedTask:
    try:
        return CHUNKED_TASKS[task]
    except KeyError:
        raise ValueError(f"{task} cannot run in batches") from None


def _plan_path(results_dir: str, task: str) -> str:
    # `task` is a CHUNKED_TASKS key, never user input.
    return os.path.join(results_dir, 'batches', task, 'plan.json')


def _load_plan(results_dir: str, task: str) -> dict | None:
    try:
        with open(_plan_path(results_dir, task), encoding='utf-8') as handle:
            plan = json.load(handle)
    except (OSError, ValueError):
        return None
    return plan if isinstance(plan.get('batches'), list) else None


def _save_plan(results_dir: str, task: str, plan: dict) -> None:
    path = _plan_path(results_dir, task)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f'{path}.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(plan, handle)
    os.replace(tmp, path)


def _record(scan_id, activity_id, command: str, output: str, return_code: int = 0) -> None:
    """One progress line in the step's detail overlay."""
    from startScan.models import Command
    try:
        Command.objects.create(
            command=command, output=output, return_code=return_code, time=timezone.now(),
            scan_history_id=scan_id, activity_id=activity_id,
        )
    except Exception as exc:
        logger.warning("Could not record batch progress for activity %s: %s", activity_id, exc)


def _hosts(targets: list) -> list:
    return sorted({target_host(target) for target in targets})


@activity.defn(name="PlanChunkedTaskActivity")
@keep_alive
def plan_chunked_task_activity(ctx: dict, task: str) -> dict:
    """Claim the step's timeline row and split its targets into batches.

    A plan already on disk is reused, so a retry or a resumed scan gets the same
    batches; finished targets are skipped by the tool's own done markers.

    Returns:
        dict: activity_id, batches, targets, hosts and the batching settings the
        workflow schedules with (it may not read the engine YAML itself).
    """
    spec = _chunked_task(task)
    scan_id = ctx.get('scan_history_id')
    logger.log_line("[TEMPORAL]", "START", "task=plan_chunked step=%s scan_id=%s" % (task, scan_id))

    proxy = TemporalTaskProxy(ctx, task, spec.title)
    config = batching_config(proxy.yaml_configuration.get(spec.config_key))
    results_dir = proxy.results_dir

    plan = _load_plan(results_dir, task)
    reused = plan is not None
    if not reused:
        targets = spec.select_targets(proxy, ctx)
        plan = {'batches': plan_batches(targets, config.batch_size, config.max_batches)}
        _save_plan(results_dir, task, plan)

    batches = plan['batches']
    targets = [target for batch in batches for target in batch]
    hosts = _hosts(targets)
    _record(
        scan_id, proxy.activity_id, f"{task} plan",
        "%s %d targets on %d hosts in %d batches of up to %d hosts, %d at a time%s" % (
            "Reusing the plan:" if reused else "Planned",
            len(targets), len(hosts), len(batches), max(config.batch_size, 1), config.max_parallel,
            "" if batches else " — nothing to do",
        ),
    )
    logger.log_line(
        "[TEMPORAL]", "COMPLETE",
        "task=plan_chunked step=%s scan_id=%s batches=%d targets=%d" % (task, scan_id, len(batches), len(targets)),
    )
    return {
        'activity_id': proxy.activity_id,
        'batches': len(batches),
        'targets': len(targets),
        'hosts': len(hosts),
        **config.as_dict(),
    }


@activity.defn(name="RunChunkedTaskBatchActivity")
def run_chunked_task_batch_activity(ctx: dict, task: str, index: int, activity_id: int) -> dict:
    """Run the tool over one batch; finished targets are skipped by the tool itself.

    Heartbeats and the stop before the attempt's time limit come from _run_task.
    A failure raises so Temporal retries the batch, which resumes where it stopped.

    Returns:
        dict: index, status ("done", or "partial" when the run was stopped before
        every target finished), targets and finished counts.
    """
    spec = _chunked_task(task)
    scan_id = ctx.get('scan_history_id')
    results_dir = ctx.get('results_dir') or ''
    plan = _load_plan(results_dir, task)
    if plan is None or not 0 <= index < len(plan['batches']):
        raise ValueError(f"No batch {index} in the {task} plan of scan {scan_id}")
    targets = plan['batches'][index]
    total = len(plan['batches'])
    label = f"{task} batch {index + 1}/{total}"
    logger.log_line("[TEMPORAL]", "START", "task=%s scan_id=%s targets=%d" % (label, scan_id, len(targets)))

    pending = [target for target in targets if not spec.is_done(results_dir, target)]
    if pending:
        _record(scan_id, activity_id, label, "START — %d of %d targets left on %s" % (
            len(pending), len(targets), ', '.join(_hosts(pending))[:2000]))
        try:
            spec.run_batch({**ctx, 'track': False, 'activity_id': activity_id}, pending)
        except Exception as exc:
            _record(scan_id, activity_id, label, "FAILED — %s" % type(exc).__name__, return_code=1)
            raise

    finished = sum(1 for target in targets if spec.is_done(results_dir, target))
    status = 'done' if finished == len(targets) else 'partial'
    if pending:
        _record(scan_id, activity_id, label, (
            "DONE" if status == 'done'
            else "STOPPED — %d of %d targets finished; a retry continues with the rest" % (finished, len(targets))
        ))
    logger.log_line("[TEMPORAL]", "COMPLETE", "task=%s scan_id=%s status=%s" % (label, scan_id, status))
    return {'index': index, 'status': status, 'targets': len(targets), 'finished': finished}


def summarize_batches(results: list, total: int) -> tuple[bool, str | None]:
    """(succeeded, note) for the step's row from every batch's outcome.

    Failed batches fail the step, so Retry and auto-recovery pick it up. Batches
    cut short by a time limit or the overall budget do not: like a single run
    stopped at its time limit, the step keeps what it found and says so.
    """
    failed = sorted(r['index'] + 1 for r in results if r.get('status') == 'failed')
    unfinished = sorted(r['index'] + 1 for r in results if r.get('status') in ('partial', 'skipped'))

    def _list(numbers: list) -> str:
        shown = ', '.join(map(str, numbers[:20]))
        return shown + (', …' if len(numbers) > 20 else '')

    if failed:
        note = "%d/%d batches failed (%s); Retry re-runs only the targets not finished yet" % (
            len(failed), total, _list(failed))
        return False, note[:_MESSAGE_LIMIT]
    if unfinished:
        note = "Stopped at the time budget with %d/%d batches unfinished (%s); Retry continues with them" % (
            len(unfinished), total, _list(unfinished))
        return True, note[:_MESSAGE_LIMIT]
    return True, None


@activity.defn(name="FinalizeChunkedTaskActivity")
@keep_alive
def finalize_chunked_task_activity(ctx: dict, task: str, activity_id: int, results: list) -> bool:
    """Run the tool's once-per-step work and close the step's row from the batch outcomes."""
    from reNgine.definitions import FAILED_TASK, SUCCESS_TASK
    from startScan.models import ScanActivity

    spec = _chunked_task(task)
    scan_id = ctx.get('scan_history_id')
    logger.log_line("[TEMPORAL]", "START", "task=finalize_chunked step=%s scan_id=%s" % (task, scan_id))

    plan = _load_plan(ctx.get('results_dir') or '', task) or {'batches': []}
    targets = [target for batch in plan['batches'] for target in batch]
    proxy = TemporalTaskProxy({**ctx, 'track': False, 'activity_id': activity_id}, task, spec.title)
    try:
        spec.finalize(proxy, ctx, targets)
    except Exception as exc:
        # The findings are saved by the batches already; a failed follow-up crawl
        # must not turn them into a failed step.
        logger.log_line("[TEMPORAL]", "ERROR", "task=finalize_chunked step=%s follow-up failed: %s" % (task, type(exc).__name__), level="error")

    succeeded, note = summarize_batches(results, len(plan['batches']))
    now = timezone.now()
    ScanActivity.objects.filter(pk=activity_id).update(
        status=SUCCESS_TASK if succeeded else FAILED_TASK,
        time=now, time_ended=now, error_message=note,
    )
    logger.log_line(
        "[TEMPORAL]", "COMPLETE",
        "task=finalize_chunked step=%s scan_id=%s succeeded=%s" % (task, scan_id, succeeded),
    )
    return succeeded
