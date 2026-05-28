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
from reNgine.utils.task import save_endpoint
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

    ctx = {
        'scan_history_id': task_instance.scan_id,
        'domain_id': getattr(task_instance, 'domain_id', None),
    }
    save_endpoint(
        http_url=url,
        ctx=ctx,
        crawl=False,
        is_default=False,
        http_status=record_data.get('status_code') or 0,
        method=record_data.get('method', 'GET'),
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
            if subdomain:
                parse_vigolium_finding(task_instance, data, subdomain)
                findings_saved += 1
            else:
                logger.warning(f"Vigolium {phase_label}: no subdomain found for '{hostname}', skipping finding.")

        elif record_type == 'http_record' and save_http_records:
            parse_vigolium_http_record(task_instance, data)
            endpoints_saved += 1

    logger.info(f"Vigolium {phase_label} complete — {findings_saved} findings, {endpoints_saved} endpoints saved")


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
    feed the endpoint DB before Tier 3-6 processing. Saves http_records as
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
