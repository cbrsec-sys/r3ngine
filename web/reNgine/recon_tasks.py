"""
Recon task functions for network-layer and domain intelligence tools.

These functions follow the TemporalTaskProxy interface used by temporal_activities.py.
Each function:
  1. Builds a tool command from yaml_configuration
  2. Runs the subprocess
  3. Parses output and persists findings to the database
  4. Returns True on success (or graceful non-fatal failure)

Severity mapping (matches Vulnerability.severity IntegerField):
  critical=4, high=3, medium=2, low=1, info=0
"""
import json
import logging
import os
import subprocess
from typing import List, Optional

from reNgine.utils.logger import get_module_logger

logger = get_module_logger(__name__)

# Severity string -> integer map matching NUCLEI_SEVERITY_MAP in definitions.py
_SEVERITY = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'info': 0, 'unknown': -1}


def dnsx_scan(self, scan_history_id: int, domain_id: int,
              subdomain: str = None, subdomains: List[str] = None,
              wordlist: str = None) -> bool:
    """Resolve DNS records for subdomains/hosts using dnsx.

    Discovered hostnames are upserted as Subdomain records (scan-history-linked).
    Used in: DomainReconWorkflow, SubdomainReconWorkflow.
    """
    from startScan.models import ScanHistory, Subdomain
    from targetApp.models import Domain
    from django.db import transaction

    targets = subdomains or ([subdomain] if subdomain else [])
    if not targets:
        logger.log_line("[DNSX]", "SKIP", "no targets provided")
        return True

    input_file = f"/tmp/dnsx_input_{scan_history_id}.txt"
    output_file = f"/tmp/dnsx_output_{scan_history_id}.json"

    try:
        with open(input_file, 'w') as f:
            f.write('\n'.join(targets))

        cmd = ['dnsx', '-l', input_file, '-resp', '-recon', '-json', '-o', output_file, '-silent']
        if wordlist:
            cmd += ['-w', wordlist]

        logger.log_line("[DNSX]", "START", "resolving %d targets" % len(targets))
        subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if not os.path.exists(output_file):
            logger.log_line("[DNSX]", "WARN", "no output produced")
            return True

        records_to_upsert = []
        try:
            domain_obj = Domain.objects.get(pk=domain_id)
        except Domain.DoesNotExist:
            domain_obj = None

        with open(output_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                host = data.get('host', '').strip()
                if host:
                    records_to_upsert.append(host)

        if records_to_upsert:
            subdomains_to_create = []
            for host in records_to_upsert:
                if not Subdomain.objects.filter(
                    scan_history_id=scan_history_id, name=host
                ).exists():
                    subdomains_to_create.append(Subdomain(
                        scan_history_id=scan_history_id,
                        target_domain=domain_obj,
                        name=host,
                    ))
            if subdomains_to_create:
                with transaction.atomic():
                    Subdomain.objects.bulk_create(subdomains_to_create, ignore_conflicts=True)
                logger.log_line(
                    "[DNSX]", "RESULT", "upserted %d subdomains" % len(subdomains_to_create),
                )

    finally:
        for fpath in [input_file, output_file]:
            try:
                os.remove(fpath)
            except FileNotFoundError:
                pass

    return True


def wafw00f_scan(self, scan_history_id: int, domain_id: int,
                 url: str = None, urls: List[str] = None) -> bool:
    """Detect WAF presence using wafw00f.

    Tags matching Subdomain records with the detected WAF via M2M.
    Used in: DomainReconWorkflow.
    """
    from startScan.models import Subdomain, Waf
    from urllib.parse import urlparse
    from django.db import transaction

    targets = urls or ([url] if url else [])
    if not targets:
        logger.log_line("[WAFW00F]", "SKIP", "no targets provided")
        return True

    for target_url in targets:
        try:
            cmd = ['wafw00f', target_url, '-o', '-', '-f', 'json']
            logger.log_line("[WAFW00F]", "START", "checking %s" % target_url)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            try:
                data = json.loads(result.stdout)
                if data and data[0].get('detected'):
                    waf_name = data[0].get('firewall', 'Unknown WAF')
                    manufacturer = data[0].get('manufacturer', '')
                    waf_obj, _ = Waf.objects.get_or_create(
                        name=waf_name,
                        defaults={'manufacturer': manufacturer},
                    )
                    parsed = urlparse(target_url)
                    hostname = parsed.hostname or ''
                    with transaction.atomic():
                        for sub in Subdomain.objects.filter(
                            scan_history_id=scan_history_id,
                            name=hostname,
                        ):
                            sub.waf.add(waf_obj)
                    logger.log_line("[WAFW00F]", "RESULT", "WAF detected: %s" % waf_name)
            except (json.JSONDecodeError, IndexError, KeyError):
                pass
        except subprocess.TimeoutExpired:
            logger.log_line("[WAFW00F]", "WARN", "timed out for %s" % target_url)

    return True


def fping_scan(self, scan_history_id: int, cidr: str = None,
               targets: List[str] = None) -> List[str]:
    """Discover alive hosts in a CIDR range using fping ICMP probes.

    Returns list of alive IP address strings.
    Used in: CIDRReconWorkflow (probe phase).
    """
    probe_targets = targets or ([cidr] if cidr else [])
    if not probe_targets:
        return []

    alive: List[str] = []
    cmd = ['fping', '-a', '-A', '-g'] + probe_targets
    logger.log_line("[FPING]", "START", "probing %s" % ' '.join(probe_targets))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        for line in result.stdout.splitlines():
            line = line.strip()
            if line and 'is alive' in line:
                alive.append(line.split()[0])
    except subprocess.TimeoutExpired:
        logger.log_line("[FPING]", "WARN", "fping timed out")

    logger.log_line("[FPING]", "RESULT", "found %d alive hosts" % len(alive))
    return alive


def arpscan_scan(self, scan_history_id: int, cidr: str = None) -> List[str]:
    """Discover LAN hosts via ARP using arp-scan.

    Returns list of IP address strings found via ARP.
    Used in: CIDRReconWorkflow (local network discovery).
    Requires: NET_RAW capability or --privileged container.
    """
    if not cidr:
        return []

    alive: List[str] = []
    cmd = ['arp-scan', '--plain', '--resolve', cidr]
    logger.log_line("[ARPSCAN]", "START", "ARP scanning %s" % cidr)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        for line in result.stdout.splitlines():
            parts = line.split('\t')
            if parts and parts[0].strip():
                alive.append(parts[0].strip())
    except subprocess.TimeoutExpired:
        logger.log_line("[ARPSCAN]", "WARN", "arp-scan timed out")

    logger.log_line("[ARPSCAN]", "RESULT", "found %d hosts via ARP" % len(alive))
    return alive


def mapcidr_expand(self, scan_history_id: int, cidr: str) -> List[str]:
    """Expand a CIDR range to individual IP addresses using mapcidr.

    Returns list of IP strings.
    Used in: CIDRReconWorkflow before fping.
    """
    cmd = ['mapcidr', '-cidr', cidr, '-silent']
    logger.log_line("[MAPCIDR]", "START", "expanding %s" % cidr)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        ips = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        logger.log_line("[MAPCIDR]", "RESULT", "expanded to %d IPs" % len(ips))
        return ips
    except subprocess.TimeoutExpired:
        logger.log_line("[MAPCIDR]", "WARN", "mapcidr timed out")
        return []


def sshaudit_scan(self, scan_history_id: int, host: str, port: int = 22) -> bool:
    """Audit SSH service configuration using ssh-audit.

    Saves CVE findings as Vulnerability records.
    Severity: cvss >= 9.0 → critical(4), >= 7.0 → high(3), >= 4.0 → medium(2), else low(1).
    Used in: HostReconWorkflow.
    """
    from startScan.models import Vulnerability
    from django.db import transaction

    cmd = ['ssh-audit', '-j', '-p', str(port), host]
    logger.log_line("[SSHAUDIT]", "START", "auditing %s:%d" % (host, port))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.log_line("[SSHAUDIT]", "WARN", "failed to parse json output for %s" % host)
            return True

        cves = data.get('cves', [])
        vulns = []
        for cve in cves:
            cvss = float(cve.get('cvss', 0))
            if cvss >= 9.0:
                sev = 4  # critical
            elif cvss >= 7.0:
                sev = 3  # high
            elif cvss >= 4.0:
                sev = 2  # medium
            else:
                sev = 1  # low

            vulns.append(Vulnerability(
                scan_history_id=scan_history_id,
                name=cve.get('name', 'SSH Vulnerability'),
                severity=sev,
                description=cve.get('description', ''),
                source='sshaudit',
                http_url='%s:%d' % (host, port),
            ))

        if vulns:
            with transaction.atomic():
                Vulnerability.objects.bulk_create(vulns, ignore_conflicts=True)
            logger.log_line("[SSHAUDIT]", "RESULT", "saved %d SSH vulnerabilities" % len(vulns))

    except subprocess.TimeoutExpired:
        logger.log_line("[SSHAUDIT]", "WARN", "ssh-audit timed out for %s" % host)

    return True


def searchsploit_scan(self, scan_history_id: int, service: str,
                      version: Optional[str] = None) -> bool:
    """Search Exploit-DB for known exploits for a service/version combo.

    Saves matching exploits as Vulnerability records (severity=high/3).
    Used in: HostReconWorkflow, _fan_out_search_vulns in MasterScanWorkflow.
    """
    from startScan.models import Vulnerability
    from django.db import transaction

    if not service:
        return True

    query = ('%s %s' % (service, version)).strip() if version else service.strip()
    cmd = ['searchsploit', '--json', query]
    logger.log_line("[SEARCHSPLOIT]", "START", "searching exploits for %s" % query)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        data = json.loads(result.stdout)
        exploits = data.get('RESULTS_EXPLOIT', [])
        vulns = []
        for exploit in exploits[:20]:
            vulns.append(Vulnerability(
                scan_history_id=scan_history_id,
                name=exploit.get('Title', 'Exploit Found'),
                severity=3,  # high
                description=exploit.get('Description', ''),
                source='searchsploit',
                exploit_url=exploit.get('Path', ''),
            ))
        if vulns:
            with transaction.atomic():
                Vulnerability.objects.bulk_create(vulns, ignore_conflicts=True)
            logger.log_line("[SEARCHSPLOIT]", "RESULT", "saved %d exploits" % len(vulns))
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        logger.log_line("[SEARCHSPLOIT]", "WARN", "searchsploit failed for %s" % query)

    return True


def wpprobe_scan(self, scan_history_id: int, url: str) -> bool:
    """Scan WordPress site for vulnerable plugins using wpprobe.

    Saves findings as Vulnerability records.
    Used in: WordPressWorkflow.
    """
    from startScan.models import Vulnerability
    from django.db import transaction

    cmd = ['wpprobe', '-u', url, '-json']
    logger.log_line("[WPPROBE]", "START", "scanning %s" % url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        findings = json.loads(result.stdout) if result.stdout.strip().startswith('[') else []
        vulns = []
        for finding in findings:
            sev_str = finding.get('severity', 'medium').lower()
            sev = _SEVERITY.get(sev_str, 2)
            vulns.append(Vulnerability(
                scan_history_id=scan_history_id,
                name=finding.get('cve', 'WordPress Plugin Vulnerability'),
                severity=sev,
                description='Plugin: %s v%s' % (
                    finding.get('plugin', ''), finding.get('version', '')),
                source='wpprobe',
                http_url=url,
            ))
        if vulns:
            with transaction.atomic():
                Vulnerability.objects.bulk_create(vulns, ignore_conflicts=True)
            logger.log_line("[WPPROBE]", "RESULT", "saved %d plugin vulnerabilities" % len(vulns))
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        logger.log_line("[WPPROBE]", "WARN", "wpprobe failed for %s" % url)

    return True


def search_vulns_scan(self, scan_history_id: int, service: str,
                      version: Optional[str], host: str, port: int) -> bool:
    """Query vulners.com for CVEs/exploits for a discovered service+version.

    Called concurrently per service immediately after port scan completes.
    Saves findings as Vulnerability records. Skips when service is empty.

    VULNERS_API_KEY env var enables higher rate limits (optional).
    """
    import requests
    from startScan.models import Vulnerability
    from django.db import transaction

    if not service or not service.strip():
        return True

    query = ('%s %s' % (service, version)).strip() if version else service.strip()
    api_key = os.environ.get('VULNERS_API_KEY', '')
    url = 'https://vulners.com/api/v3/search/lucene/'
    params: dict = {
        'query': query,
        'fields': ['id', 'title', 'cvss', 'description', 'published'],
        'size': 10,
    }
    if api_key:
        params['apiKey'] = api_key

    logger.log_line("[SEARCH_VULNS]", "START", "querying vulners for %s" % query)

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get('data', {}).get('search', [])
    except Exception as exc:
        logger.log_line("[SEARCH_VULNS]", "WARN", "vulners query failed: %s" % str(exc))
        return True

    if not results:
        logger.log_line("[SEARCH_VULNS]", "RESULT", "no results for %s" % query)
        return True

    vulns = []
    for item in results:
        cvss_data = item.get('cvss') or {}
        if isinstance(cvss_data, dict):
            cvss_score = float(cvss_data.get('score', 0))
        elif isinstance(cvss_data, (int, float)):
            cvss_score = float(cvss_data)
        else:
            cvss_score = 0.0

        if cvss_score >= 9.0:
            sev = 4  # critical
        elif cvss_score >= 7.0:
            sev = 3  # high
        elif cvss_score >= 4.0:
            sev = 2  # medium
        else:
            sev = 1  # low

        vulns.append(Vulnerability(
            scan_history_id=scan_history_id,
            name=item.get('id', 'Service Vulnerability'),
            severity=sev,
            description='%s\n\nService: %s %s\nHost: %s:%d\nCVSS: %.1f\n\n%s' % (
                item.get('title', ''),
                service, version or '',
                host, port,
                cvss_score,
                item.get('description', ''),
            ),
            source='search_vulns',
            http_url='%s:%d' % (host, port),
        ))

    if vulns:
        with transaction.atomic():
            Vulnerability.objects.bulk_create(vulns, ignore_conflicts=True)
        logger.log_line(
            "[SEARCH_VULNS]", "RESULT",
            "saved %d vulns for %s on %s:%d" % (len(vulns), query, host, port),
        )

    return True
