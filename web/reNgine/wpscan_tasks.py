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

_FINDING_TYPE_MAP = {
    'xmlrpc':                     ('high',     'XML-RPC Enabled'),
    'upload_directory_listing':   ('medium',   'WordPress Upload Directory Listing Enabled'),
    'readme':                     ('info',     'WordPress Readme File Exposed'),
    'wp_cron':                    ('info',     'External WP-Cron Enabled'),
    'headers':                    ('info',     'WordPress HTTP Headers'),
    'backup_db':                  ('critical', 'WordPress Database Backup Exposed'),
    'debug_log':                  ('high',     'WordPress Debug Log Exposed'),
    'registration_enabled':       ('medium',   'WordPress User Registration Open'),
    'mu_plugins_listing':         ('medium',   'WordPress Must-Use Plugins Directory Listing'),
    'config_backup':              ('high',     'WordPress Configuration Backup Exposed'),
    'timthumb':                   ('high',     'TimThumb Script Detected'),
    'emergency_pwd_reset_script': ('critical', 'Emergency Password Reset Script Detected'),
    'full_path_disclosure':       ('medium',   'WordPress Full Path Disclosure'),
    'license':                    ('info',     'WordPress License File Exposed'),
}


def save_finding(task_instance, finding, subdomain, name, severity='info', extra_description=''):
    """Saves a WPScan finding to the database.

    Args:
        task_instance: Temporal task proxy with scan context.
        finding (dict): WPScan finding dict (may be empty {} for synthetic entries).
        subdomain (Subdomain): Associated Subdomain object.
        name (str): Vulnerability name/title to store.
        severity (str): One of 'info', 'low', 'medium', 'high', 'critical'.
        extra_description (str): Additional text prepended to the finding description.
    """
    description_parts = []
    if extra_description:
        description_parts.append(extra_description)
    base_desc = finding.get('description', '')
    if base_desc:
        description_parts.append(base_desc)
    description = '\n\n'.join(description_parts)

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

    severity_num = NUCLEI_SEVERITY_MAP.get(severity, 0)

    save_vulnerability(
        target_domain=task_instance.domain,
        http_url=f"http://{subdomain.name}",
        scan_history=task_instance.scan,
        subdomain=subdomain,
        name=name,
        severity=severity_num,
        description=description,
        type='WordPress',
        references=ref_urls,
        cve_ids=cve_ids,
        source='WPScan',
    )

def wpscan_scan(self, urls=[], ctx={}, description=None):
    """WPScan task for WordPress vulnerability scanning.
    Runs against all discovered subdomains or specific URLs.

    Args:
        self: The Temporal task proxy with scan context.
        urls (list, optional): List of specific target URLs to scan.
        ctx (dict, optional): Scan context data.
        description (str, optional): Descriptive text for this task.

    Returns:
        str: Status message on completion, or None if skipped.
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

    # Attempt to update WPScan database first before running scans on targets
    update_cmd = "wpscan --update --no-banner"
    proxy = get_random_proxy()
    if proxy:
        update_cmd += f" --proxy {proxy}"
    logger.info("Updating WPScan database...")
    try:
        for _ in stream_command(update_cmd, scan_id=self.scan_id, activity_id=self.activity_id):
            pass
    except Exception as e:
        logger.error(f"Failed to run wpscan database update: {e}")

    for target_url, subdomain in targets:
        target_name = subdomain.name
        
        # Ensure trailing slash is stripped from target URL
        target_url = target_url.rstrip('/')
        logger.info(f"WPScan target: {target_url}")
        
        output_file = f"{results_dir}/{target_name}_wpscan.json"
        
        max_attempts = 4  # 1 initial attempt + 3 retries
        for attempt in range(max_attempts):
            # Command construction
            cmd = f"wpscan --url {target_url} --format json --random-user-agent --output {output_file} --enumerate {enumeration} --detection-mode {detection_mode} --no-banner --ignore-main-redirect"
            
            # The final retry attempt must be executed without the proxy flag
            proxy = None
            if attempt < max_attempts - 1:
                proxy = get_random_proxy()
            
            if proxy:
                cmd += f" --proxy {proxy}"
            if api_key:
                cmd += f" --api-token {api_key}"
            
            logger.info(f"Running WPScan for {target_url} (Attempt {attempt + 1}/{max_attempts})")
            logger.warning(f"Full WPScan command: {cmd}")
            
            # Remove output file if it exists to ensure we don't read stale results
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except Exception:
                    pass

            # Execute tool — stream_command is a generator; must be consumed to run the subprocess.
            for _ in stream_command(cmd, scan_id=self.scan_id, activity_id=self.activity_id):
                pass

            # Check after the tool call at the output files for SSL peer certificate error
            failed_with_ssl_error = False
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                try:
                    with open(output_file, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            db_update_started = data.get('db_update_started')
                            scan_aborted = data.get('scan_aborted')
                            target_url_in_json = data.get('target_url')
                            
                            target_url_normalized = target_url.rstrip('/')
                            json_url_normalized = target_url_in_json.rstrip('/') if isinstance(target_url_in_json, str) else ''
                            
                            # Verify if update failed due to SSL peer certificate check
                            if (
                                db_update_started is True and
                                isinstance(scan_aborted, str) and
                                "SSL peer certificate or SSH remote key was not OK" in scan_aborted and
                                target_url_normalized == json_url_normalized
                            ):
                                failed_with_ssl_error = True
                except Exception as parse_err:
                    logger.error(f"Failed to parse WPScan output JSON: {parse_err}")

            if failed_with_ssl_error:
                if attempt < max_attempts - 1:
                    logger.warning(
                        f"WPScan aborted due to SSL peer certificate error on {target_url}. "
                        f"Retrying ({attempt + 1}/{max_attempts - 1})..."
                    )
                    time.sleep(2)
                    continue
                else:
                    logger.error(
                        f"WPScan failed on {target_url} with SSL certificate error after {max_attempts} attempts. "
                        f"Skipping target."
                    )
                    # Clean up aborted output file to prevent parsing junk
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                        except Exception:
                            pass
                    break
            else:
                # Execution succeeded or failed with different error
                break

        # Parse and save
        parse_wpscan_results(self, output_file, subdomain)

    return "WPScan completed"
