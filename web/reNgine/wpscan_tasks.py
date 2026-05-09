import os
import json
import time
from celery.utils.log import get_task_logger

from reNgine.celery import app
from reNgine.celery_custom_task import RengineTask
from reNgine.definitions import *
from reNgine.common_func import (
    get_random_proxy,
    save_vulnerability,
    record_exists,
    get_subdomain_from_url
)
from dashboard.models import WpScanAPIKey
from startScan.models import ScanHistory, Subdomain, Vulnerability

logger = get_task_logger(__name__)

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

    vuln_data = {
        'name': title,
        'severity': severity,
        'description': description,
        'type': 'WordPress',
        'references': ref_urls,
        'cve_ids': cve_ids
    }

    if record_exists(Vulnerability, data={'subdomain': subdomain, 'name': title, 'description': description}):
        return

    save_vulnerability(
        target_domain=task_instance.domain,
        http_url=f"http://{subdomain.name}",
        scan_history=task_instance.scan,
        subdomain=subdomain,
        **vuln_data
    )

@app.task(name='wpscan_scan', queue='main_scan_queue', base=RengineTask, bind=True)
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

    enumeration = vulnerability_config.get(WPSCAN_ENUMERATION, 'vp,vt,u')
    detection_mode = vulnerability_config.get(WPSCAN_DETECTION_MODE, 'mixed')
    
    # Get API Key
    api_key_obj = WpScanAPIKey.objects.first()
    api_key = api_key_obj.key if api_key_obj else None

    # Determine targets
    targets = []
    if urls:
        # Targeted scan on specific URLs
        for url in urls:
            subdomain_name = get_subdomain_from_url(url)
            subdomain = Subdomain.objects.filter(scan_history=self.scan, name=subdomain_name).first()
            if subdomain:
                targets.append((url, subdomain))
    else:
        # Full scan on all subdomains
        subdomains = Subdomain.objects.filter(scan_history=self.scan)
        for subdomain in subdomains:
            targets.append((f"http://{subdomain.name}", subdomain))

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
        cmd = f"wpscan --url {target_url} --format json --output {output_file} --enumerate {enumeration} --detection-mode {detection_mode} --no-banner"
        
        if api_key:
            cmd += f" --api-token {api_key}"
            
        # Execute tool
        stream_command(cmd, scan_id=self.scan_id, activity_id=self.activity_id)

        # Parse and save
        parse_wpscan_results(self, output_file, subdomain)

    return "WPScan completed"
