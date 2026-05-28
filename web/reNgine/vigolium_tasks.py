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
from reNgine.common_func import get_random_proxy, save_vulnerability
from reNgine.tasks import save_endpoint
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
