import logging
import os
import json
import time

from reNgine.definitions import *
from reNgine.common_func import (
    get_random_proxy,
    save_vulnerability,
    record_exists,
    get_subdomain_from_url
)
from dashboard.models import WpScanAPIKey
from startScan.models import EndPoint, ScanHistory, Subdomain, Vulnerability

logger = logging.getLogger(__name__)

def parse_wpscan_results(task_instance, output_file, subdomain):
    """
    Parses WPScan JSON output and saves vulnerabilities to the database.
    """
    try:
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            return

        with open(output_file, 'r') as f:
            data = json.load(f)
            
            # WPScan JSON structure
            # 1. Interesting findings
            for finding in data.get('interesting_findings', []):
                save_finding(task_instance, finding, subdomain, "WPScan Finding")

            # 2. Version vulnerabilities
            version = data.get('version')
            if version and version.get('vulnerabilities'):
                for vuln in version.get('vulnerabilities'):
                    save_finding(task_instance, vuln, subdomain, f"WordPress Version {version.get('number', 'Unknown')}")

            # 3. Plugins vulnerabilities
            plugins = data.get('plugins', {})
            for plugin_name, plugin_info in plugins.items():
                if plugin_info.get('vulnerabilities'):
                    for vuln in plugin_info.get('vulnerabilities'):
                        save_finding(task_instance, vuln, subdomain, f"WordPress Plugin: {plugin_name}")

            # 4. Themes vulnerabilities
            themes = data.get('themes', {})
            for theme_name, theme_info in themes.items():
                if theme_info.get('vulnerabilities'):
                    for vuln in theme_info.get('vulnerabilities'):
                        save_finding(task_instance, vuln, subdomain, f"WordPress Theme: {theme_name}")

    except Exception as e:
        logger.error(f"Failed to parse WPScan results for {subdomain.name}: {str(e)}")

def save_finding(task_instance, finding, subdomain, default_title):
    """Saves a WPScan finding to the database.

    Args:
        task_instance: Temporal task proxy with scan context.
        finding (dict): Finding payload from WPScan JSON.
        subdomain (Subdomain): Associated Subdomain database object.
        default_title (str): Fallback title to use if finding has no title.
    """
    title = finding.get('title', default_title)
    description = finding.get('description', '')
    
    severity = 'info'
    if 'vulnerabilities' in str(finding).lower():
        severity = 'medium'
    
    references = finding.get('references', {})
    ref_urls = []
    cve_ids = []
    
    if isinstance(references, dict):
        for ref_type, ref_list in references.items():
            if ref_type == 'cve':
                cve_ids.extend(ref_list)
            elif isinstance(ref_list, list):
                ref_urls.extend(ref_list)
            else:
                ref_urls.append(str(ref_list))

    severity_num = NUCLEI_SEVERITY_MAP.get(severity, 2)
    vuln_data = {
        'name': title,
        'severity': severity_num,
        'description': description,
        'type': 'WordPress',
        'references': ref_urls,
        'cve_ids': cve_ids,
        'source': 'WPScan'
    }

    save_vulnerability(
        target_domain=task_instance.domain,
        http_url=f"http://{subdomain.name}",
        scan_history=task_instance.scan,
        subdomain=subdomain,
        **vuln_data
    )

def wpscan_scan(self, urls=[], ctx={}, description=None):
    """
    WPScan task for WordPress vulnerability scanning.
    Runs against all discovered subdomains or specific URLs.
    """
    logger.info("Starting WPScan Vulnerability Scan")
    
    # Configuration from engine
    vulnerability_config = self.yaml_configuration.get(VULNERABILITY_SCAN, {})
    
    should_run = vulnerability_config.get(RUN_WPSCAN, True)
    if not should_run:
        logger.info("WPScan is disabled in configuration. Skipping.")
        return

    # Gate: only run when WordPress indicators are present, either from technology
    # fingerprinting or from wp-like paths found by fetch_url / dir_file_fuzz.
    # Mirrors the react2shell_scan gating pattern.
    from django.db.models import Q
    _WP_PATH_RE = r'(wp-login|wp-admin|wp-content|wp-json|xmlrpc\.php)'

    if self.subscan and self.subdomain:
        _sub_qs = Subdomain.objects.filter(pk=self.subdomain.id)
        _ep_qs = EndPoint.objects.filter(
            scan_history=self.scan,
            subdomain=self.subdomain,
            http_url__iregex=_WP_PATH_RE,
        )
    else:
        _sub_qs = Subdomain.objects.filter(scan_history=self.scan)
        _ep_qs = EndPoint.objects.filter(
            scan_history=self.scan,
            http_url__iregex=_WP_PATH_RE,
        )

    wp_via_tech = _sub_qs.filter(technologies__name__icontains='wordpress').exists()
    wp_via_paths = _ep_qs.exists()

    if not wp_via_tech and not wp_via_paths:
        logger.info("No WordPress indicators (technology or wp-like paths) found. Skipping WPScan.")
        return

    enumeration = vulnerability_config.get(WPSCAN_ENUMERATION, 'vp,vt,u')
    detection_mode = vulnerability_config.get(WPSCAN_DETECTION_MODE, 'mixed')

    # Get API Key
    api_key_obj = WpScanAPIKey.objects.first()
    api_key = api_key_obj.key if api_key_obj else None

    # Determine targets — narrow to only WordPress-positive subdomains.
    targets = []
    if self.subscan and self.subdomain:
        targets.append((f"https://{self.subdomain.name}/", self.subdomain))
    elif urls:
        # Targeted scan on specific URLs
        for url in urls:
            subdomain_name = get_subdomain_from_url(url)
            subdomain = Subdomain.objects.filter(scan_history=self.scan, name=subdomain_name).first()
            if subdomain:
                targets.append((url, subdomain))
    else:
        # Full scan — only subdomains with WP tech or WP-like endpoints.
        wp_subdomain_ids = set(
            _sub_qs.filter(technologies__name__icontains='wordpress')
            .values_list('id', flat=True)
        )
        ep_subdomain_ids = set(
            EndPoint.objects.filter(
                scan_history=self.scan,
                http_url__iregex=_WP_PATH_RE,
            ).values_list('subdomain_id', flat=True)
        )
        wp_ids = wp_subdomain_ids | ep_subdomain_ids
        for subdomain in Subdomain.objects.filter(scan_history=self.scan, id__in=wp_ids):
            targets.append((f"https://{subdomain.name}/", subdomain))

    if not targets:
        logger.info("No targets found for WPScan.")
        return

    results_dir = f"{self.scan.results_dir}/vulnerability/wpscan"
    os.makedirs(results_dir, exist_ok=True)

    from reNgine.tasks import stream_command

    for target_url, subdomain in targets:
        target_name = subdomain.name
        logger.info(f"WPScan target: {target_url}")
        
        output_file = f"{results_dir}/{target_name}_wpscan.json"
        
        # Command construction
        cmd = f"wpscan --url {target_url} --format json --random-user-agent --output {output_file} --enumerate {enumeration} --detection-mode {detection_mode} --no-banner --ignore-main-redirect"
        proxy = get_random_proxy()
        if proxy:
            cmd += f" --proxy {proxy}"
        if api_key:
            cmd += f" --api-token {api_key}"
        
        logger.info(f"Running WPScan for {target_url}")
        logger.warning(f"Full WPScan command: {cmd}")
        # Execute tool — stream_command is a generator; must be consumed to run the subprocess.
        for _ in stream_command(cmd, scan_id=self.scan_id, activity_id=self.activity_id):
            pass

        # Parse and save
        parse_wpscan_results(self, output_file, subdomain)

    return "WPScan completed"
