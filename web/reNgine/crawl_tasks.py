"""
Crawl and URL-discovery task functions.

Adapts xurlfind3r, urlfinder, cariddi, bup, arjun, feroxbuster, and gf
to the TemporalTaskProxy interface expected by temporal_activities.py.

Severity mapping: critical=4, high=3, medium=2, low=1, info=0
"""
import json
import logging
import os
import subprocess
from typing import List, Optional

from reNgine.utils.logger import get_module_logger

logger = get_module_logger(__name__)


def xurlfind3r_scan(self, scan_history_id: int, domain: str = None,
                    domains: List[str] = None) -> bool:
    """Collect passive URLs from multiple sources using xurlfind3r.

    Persists discovered URLs as EndPoint records.
    Used in: URLCrawlWorkflow (passive), DomainReconWorkflow.
    """
    from startScan.models import EndPoint
    from django.db import transaction

    targets = domains or ([domain] if domain else [])
    if not targets:
        return True

    endpoints = []
    for target in targets:
        cmd = ['xurlfind3r', '-d', target, '-silent']
        logger.log_line("[XURLFIND3R]", "START", "passive crawl for %s" % target)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith('http'):
                    endpoints.append(EndPoint(
                        scan_history_id=scan_history_id,
                        http_url=line[:30000],
                        is_default=False,
                        source='xurlfind3r',
                    ))
        except subprocess.TimeoutExpired:
            logger.log_line("[XURLFIND3R]", "WARN", "timed out for %s" % target)

    if endpoints:
        with transaction.atomic():
            EndPoint.objects.bulk_create(endpoints, ignore_conflicts=True, batch_size=500)
        logger.log_line("[XURLFIND3R]", "RESULT", "saved %d URLs" % len(endpoints))
    return True


def urlfinder_scan(self, scan_history_id: int, domain: str = None) -> bool:
    """Collect passive URLs using urlfinder (projectdiscovery).

    Used in: URLCrawlWorkflow (passive).
    """
    from startScan.models import EndPoint
    from django.db import transaction

    if not domain:
        return True

    cmd = ['urlfinder', '-d', domain, '-silent']
    logger.log_line("[URLFINDER]", "START", "passive crawl for %s" % domain)
    endpoints = []
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith('http'):
                endpoints.append(EndPoint(
                    scan_history_id=scan_history_id,
                    http_url=line[:30000],
                    is_default=False,
                    source='urlfinder',
                ))
    except subprocess.TimeoutExpired:
        logger.log_line("[URLFINDER]", "WARN", "timed out for %s" % domain)

    if endpoints:
        with transaction.atomic():
            EndPoint.objects.bulk_create(endpoints, ignore_conflicts=True, batch_size=500)
        logger.log_line("[URLFINDER]", "RESULT", "saved %d URLs" % len(endpoints))
    return True


def cariddi_scan(self, scan_history_id: int, url: str = None,
                 urls: List[str] = None) -> bool:
    """Crawl endpoints and discover secrets using cariddi.

    Persists discovered endpoints as EndPoint records.
    Used in: URLCrawlWorkflow (active).
    """
    from startScan.models import EndPoint
    from django.db import transaction

    targets = urls or ([url] if url else [])
    if not targets:
        return True

    for target in targets:
        cmd = ['cariddi', '-i', target, '-info', '-secrets', '-e', '-s', '1']
        logger.log_line("[CARIDDI]", "START", "crawling %s" % target)
        endpoints = []
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            for line in result.stdout.splitlines():
                line = line.strip()
                # cariddi outputs "url\t[tag]..." format
                ep_url = line.split('\t')[0].strip() if '\t' in line else line
                if ep_url.startswith('http'):
                    endpoints.append(EndPoint(
                        scan_history_id=scan_history_id,
                        http_url=ep_url[:30000],
                        is_default=False,
                        source='cariddi',
                    ))
        except subprocess.TimeoutExpired:
            logger.log_line("[CARIDDI]", "WARN", "timed out for %s" % target)

        if endpoints:
            with transaction.atomic():
                EndPoint.objects.bulk_create(endpoints, ignore_conflicts=True, batch_size=500)
            logger.log_line(
                "[CARIDDI]", "RESULT",
                "saved %d endpoints for %s" % (len(endpoints), target),
            )

    return True


def bup_scan(self, scan_history_id: int, url: str = None,
             urls: List[str] = None) -> bool:
    """Attempt 4xx bypass techniques using bypass-url-parser (bup).

    Saves successful bypasses as Vulnerability records (severity=medium/2).
    Used in: URLBypassWorkflow.
    """
    from startScan.models import Vulnerability
    from django.db import transaction

    targets = urls or ([url] if url else [])
    if not targets:
        return True

    for target in targets:
        cmd = ['bup', '-u', target, '-d']
        logger.log_line("[BUP]", "START", "bypass attempt on %s" % target)
        bypasses = []
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            for line in result.stdout.splitlines():
                if '[BYPASS]' in line or ('200' in line and 'bypass' in line.lower()):
                    bypasses.append(Vulnerability(
                        scan_history_id=scan_history_id,
                        name='4xx Bypass Found',
                        severity=2,  # medium
                        description=line.strip(),
                        source='bup',
                        http_url=target,
                    ))
        except subprocess.TimeoutExpired:
            logger.log_line("[BUP]", "WARN", "timed out for %s" % target)

        if bypasses:
            with transaction.atomic():
                Vulnerability.objects.bulk_create(bypasses, ignore_conflicts=True)
            logger.log_line(
                "[BUP]", "RESULT", "found %d bypasses for %s" % (len(bypasses), target),
            )

    return True


def arjun_scan(self, scan_history_id: int, urls: List[str] = None,
               url: str = None) -> bool:
    """Discover hidden HTTP parameters using arjun.

    Saves discovered parameters to the Parameter model via EndPoint FK.
    Creates EndPoint records for any URLs that don't already have one.
    Used in: URLParamsFuzzWorkflow.
    """
    from startScan.models import Parameter, EndPoint
    from django.db import transaction

    targets = urls or ([url] if url else [])
    if not targets:
        return True

    output_file = f"/tmp/arjun_output_{scan_history_id}.json"
    cmd = ['arjun', '-i', '/dev/stdin', '-oJ', output_file, '-q']
    logger.log_line("[ARJUN]", "START", "parameter discovery for %d URLs" % len(targets))

    try:
        result = subprocess.run(
            cmd,
            input='\n'.join(targets),
            capture_output=True, text=True, timeout=600,
        )
        if os.path.exists(output_file):
            with open(output_file) as f:
                data = json.load(f)
            params = []
            for ep_url, param_list in data.items():
                # Get or create an EndPoint for this URL
                endpoint, _ = EndPoint.objects.get_or_create(
                    scan_history_id=scan_history_id,
                    http_url=ep_url[:30000],
                    defaults={'source': 'arjun', 'is_default': False},
                )
                for param_name in param_list:
                    params.append(Parameter(
                        endpoint=endpoint,
                        name=param_name,
                        type='query',
                    ))
            if params:
                with transaction.atomic():
                    Parameter.objects.bulk_create(params, ignore_conflicts=True)
                logger.log_line("[ARJUN]", "RESULT", "saved %d parameters" % len(params))
    except subprocess.TimeoutExpired:
        logger.log_line("[ARJUN]", "WARN", "arjun timed out")
    except (json.JSONDecodeError, Exception) as exc:
        logger.log_line("[ARJUN]", "WARN", "arjun parse error: %s" % str(exc))
    finally:
        try:
            os.remove(output_file)
        except FileNotFoundError:
            pass

    return True


def feroxbuster_scan(self, scan_history_id: int, url: str = None,
                     urls: List[str] = None) -> bool:
    """Recursively fuzz web content using feroxbuster.

    Persists discovered paths as EndPoint records.
    Used in: URLFuzzWorkflow.
    """
    from startScan.models import EndPoint
    from django.db import transaction

    yaml_config = getattr(self, 'yaml_configuration', {}) or {}
    scan_config = yaml_config.get('feroxbuster', {})
    wordlist = scan_config.get(
        'wordlist',
        '/usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt',
    )

    targets = urls or ([url] if url else [])
    if not targets:
        return True

    for target in targets:
        output_file = f"/tmp/feroxbuster_{scan_history_id}.txt"
        cmd = [
            'feroxbuster', '--url', target,
            '--no-state', '--output', output_file,
            '--auto-calibration', '--follow-redirects', '--silent',
        ]
        if os.path.exists(wordlist):
            cmd += ['--wordlist', wordlist]

        logger.log_line("[FEROXBUSTER]", "START", "fuzzing %s" % target)
        endpoints = []
        try:
            subprocess.run(cmd, capture_output=True, timeout=1800)
            if os.path.exists(output_file):
                with open(output_file) as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 4 and parts[0].isdigit():
                            ep_url = parts[-1].strip()
                            if ep_url.startswith('http'):
                                endpoints.append(EndPoint(
                                    scan_history_id=scan_history_id,
                                    http_url=ep_url[:30000],
                                    http_status=int(parts[0]),
                                    is_default=False,
                                    source='feroxbuster',
                                ))
        except subprocess.TimeoutExpired:
            logger.log_line("[FEROXBUSTER]", "WARN", "timed out for %s" % target)
        finally:
            try:
                os.remove(output_file)
            except FileNotFoundError:
                pass

        if endpoints:
            with transaction.atomic():
                EndPoint.objects.bulk_create(endpoints, ignore_conflicts=True, batch_size=500)
            logger.log_line("[FEROXBUSTER]", "RESULT", "saved %d endpoints" % len(endpoints))

    return True


def urlparser_scan(self, scan_history_id: int, domain_id: int,
                   urls: Optional[List[str]] = None) -> bool:
    """Extract unique query-string parameters from URLs using unfurl.

    Pipes URLs through `unfurl -u keypairs`, parses key=value output,
    and stores each pair as a Parameter record on the matching EndPoint.
    Falls back to loading EndPoint URLs from the scan when urls is not given.
    Used in: URLParamsFuzzWorkflow, URLCrawlWorkflow.
    """
    from startScan.models import EndPoint, Parameter
    from django.db import transaction

    targets = urls or []
    if not targets and scan_history_id:
        targets = list(
            EndPoint.objects.filter(
                scan_history_id=scan_history_id
            ).values_list('http_url', flat=True)[:2000]
        )

    if not targets:
        logger.log_line("[URLPARSER]", "SKIP", "no URLs to parse")
        return True

    input_file = '/tmp/urlparser_input_%s.txt' % scan_history_id
    try:
        with open(input_file, 'w') as f:
            f.write('\n'.join(t for t in targets if t))

        logger.log_line("[URLPARSER]", "START", "parsing %d URLs" % len(targets))
        with open(input_file, 'rb') as stdin_f:
            result = subprocess.run(
                ['unfurl', '-u', 'keypairs'],
                stdin=stdin_f,
                capture_output=True, text=True, timeout=120,
            )

        # Build lookup: http_url → EndPoint for fast matching
        ep_map = {
            ep.http_url: ep
            for ep in EndPoint.objects.filter(
                scan_history_id=scan_history_id,
                http_url__in=targets,
            )
        }

        params_to_create: List[Parameter] = []
        seen: set = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key = key.strip()
            value = value.strip()
            for url, ep in ep_map.items():
                if ('?%s=' % key) in url or ('&%s=' % key) in url:
                    dedup_key = (ep.id, key)
                    if dedup_key in seen:
                        continue
                    params_to_create.append(
                        Parameter(endpoint=ep, name=key, value=value, type='GET')
                    )
                    seen.add(dedup_key)

        if params_to_create:
            with transaction.atomic():
                Parameter.objects.bulk_create(params_to_create, ignore_conflicts=True)
            logger.log_line("[URLPARSER]", "RESULT",
                            "saved %d parameters" % len(params_to_create))
        else:
            logger.log_line("[URLPARSER]", "RESULT", "no new parameters found")

    except subprocess.TimeoutExpired:
        logger.log_line("[URLPARSER]", "WARN", "unfurl timed out")
    finally:
        if os.path.exists(input_file):
            os.remove(input_file)

    return True


def gf_scan(self, scan_history_id: int, pattern: str,
            urls: List[str] = None) -> List[str]:
    """Filter URLs by vulnerability pattern using gf (grep for URLs).

    Returns list of matched URL strings.
    Patterns: xss, lfi, ssrf, rce, idor, debug_logic, interestingparams.
    Used in: URLVulnWorkflow.
    """
    if not urls:
        return []

    cmd = ['gf', pattern]
    logger.log_line("[GF]", "START", "pattern=%s targets=%d" % (pattern, len(urls)))

    try:
        result = subprocess.run(
            cmd,
            input='\n'.join(urls),
            capture_output=True, text=True, timeout=60,
        )
        matched = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        logger.log_line("[GF]", "RESULT", "pattern=%s matched=%d" % (pattern, len(matched)))
        return matched
    except subprocess.TimeoutExpired:
        logger.log_line("[GF]", "WARN", "gf timed out for pattern %s" % pattern)
        return []
