import logging
import os
import json
import shutil
from pathlib import Path

from reNgine.definitions import *
from reNgine.common_func import (
    save_vulnerability,
)
from startScan.models import EndPoint, Subdomain, Vulnerability
from reNgine.tasks import stream_command

logger = logging.getLogger(__name__)

def parse_wptaint_results(task_instance, output_file, subdomains, plugin_name):
    """
    Parses wp-taint-scan JSON output and saves vulnerabilities to the database.
    """
    try:
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            return

        with open(output_file, 'r') as f:
            data = json.load(f)

        for finding in data:
            title = finding.get('Title', f"WP Taint: {finding.get('SinkOp', 'Unknown')}")
            description = finding.get('Description', '')
            if finding.get('File'):
                description += f"\n\n**File**: `{finding.get('File')}`"
                if finding.get('Line'):
                    description += f" (Line {finding.get('Line')})"
            if finding.get('SourceCode'):
                description += f"\n\n**Source Code**:\n```php\n{finding.get('SourceCode')}\n```"

            vuln_data = {
                'name': f"WP Taint ({plugin_name}): {title}",
                'severity': 3,  # High severity for SAST findings
                'description': description,
                'type': 'WordPress',
                'references': [],
                'cve_ids': [],
                'source': 'WPTaintScan'
            }

            for subdomain in subdomains:
                save_vulnerability(
                    target_domain=task_instance.domain,
                    http_url=f"http://{subdomain.name}",
                    scan_history=task_instance.scan,
                    subdomain=subdomain,
                    **vuln_data
                )

    except Exception as e:
        logger.error(f"Failed to parse WP Taint Scan results for plugin {plugin_name}: {str(e)}")

def wptaint_scan(self, urls=[], ctx={}, description=None):
    """
    wp-taint-scan task for WordPress plugin static analysis.
    Runs against plugins discovered by other WordPress tasks.
    """
    logger.info("Starting WP Taint Vulnerability Scan")
    
    # Configuration from engine
    vulnerability_config = self.yaml_configuration.get(VULNERABILITY_SCAN, {})
    should_run = vulnerability_config.get(RUN_WPTAINT_SCAN, True)
    
    if not should_run:
        logger.info("WP Taint Scan is disabled in configuration. Skipping.")
        return

    # Gather plugins discovered by WPScan/Nuclei
    plugin_subdomains = {} # mapping of plugin_name -> set of Subdomain objects
    
    for vuln in Vulnerability.objects.filter(scan_history=self.scan, target_domain=self.domain, type='WordPress'):
        if vuln.name.startswith('WordPress Plugin:'):
            plugin_name = vuln.name.replace('WordPress Plugin:', '').strip()
            if plugin_name not in plugin_subdomains:
                plugin_subdomains[plugin_name] = set()
            plugin_subdomains[plugin_name].add(vuln.subdomain)

    if not plugin_subdomains:
        logger.info("No WordPress plugins discovered by previous tasks. Skipping WP Taint Scan.")
        return

    results_dir = f"{self.scan.results_dir}/vulnerability/wptaint"
    os.makedirs(results_dir, exist_ok=True)
    temp_download_dir = f"{self.scan.results_dir}/temp_wptaint"
    os.makedirs(temp_download_dir, exist_ok=True)

    for plugin_name, subdomains in plugin_subdomains.items():
        logger.info(f"WP Taint Scan target plugin: {plugin_name}")
        
        plugin_dir = os.path.join(temp_download_dir, plugin_name)
        plugin_zip = f"{plugin_dir}.zip"
        plugin_results_dir = os.path.join(results_dir, plugin_name)
        
        try:
            # 1. Download plugin source
            download_cmd = f"wget -q -O {plugin_zip} https://downloads.wordpress.org/plugin/{plugin_name}.zip"
            stdout, stderr, exit_code = stream_command(self, download_cmd, ctx)
            
            if exit_code != 0 or not os.path.exists(plugin_zip):
                logger.info(f"Could not download source for plugin {plugin_name}. It may be a premium or unavailable plugin.")
                continue
                
            # 2. Unzip
            os.makedirs(plugin_dir, exist_ok=True)
            unzip_cmd = f"unzip -q -o {plugin_zip} -d {plugin_dir}"
            stream_command(self, unzip_cmd, ctx)
            
            # 3. Run taint-scan
            os.makedirs(plugin_results_dir, exist_ok=True)
            taint_cmd = f"taint-scan -target {plugin_dir} -output-dir {plugin_results_dir}"
            logger.info(f"Running WP Taint Scan on {plugin_name}")
            stream_command(self, taint_cmd, ctx)
            
            # 4. Parse results
            results_file = os.path.join(plugin_results_dir, "taint-results.json")
            parse_wptaint_results(self, results_file, subdomains, plugin_name)
            
        except Exception as e:
            logger.error(f"Error executing WP Taint Scan on {plugin_name}: {e}")
        finally:
            # Cleanup source
            if os.path.exists(plugin_zip):
                os.remove(plugin_zip)
            if os.path.exists(plugin_dir):
                shutil.rmtree(plugin_dir)

    # Cleanup temp dir
    if os.path.exists(temp_download_dir):
        shutil.rmtree(temp_download_dir)
