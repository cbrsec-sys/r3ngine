import os
import django
from django.apps import apps
if not apps.ready:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reNgine.settings')
    django.setup()

import csv
import requests
import json
import pprint
import subprocess
import time
import validators
import xmltodict
import yaml
import tldextract
import concurrent.futures
import base64
import io
import shutil
from redis import Redis


from datetime import datetime
from urllib.parse import urlparse, parse_qs
from api.serializers import SubdomainSerializer
from celery import chain, chord, group
from celery.result import allow_join_result
from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models import Count
from dotted_dict import DottedDict
from django.utils import timezone
from django.shortcuts import get_object_or_404
from pycvesearch import CVESearch
from metafinder.extractor import extract_metadata_from_google_search

from django.core.cache import cache
from reNgine.celery import app
from reNgine.celery_custom_task import RengineTask
from reNgine.common_func import *
from reNgine.definitions import *
from reNgine.settings import *
from reNgine.llm import *
from reNgine.utilities import *
from reNgine.opsec_utils import OpSecManager, BruteForceOrchestrator, ProxychainsWrapper
from reNgine.waf_utils import OriginDiscoveryManager, WafBypassOrchestrator
from scanEngine.models import (EngineType, InstalledExternalTool, Notification, Proxy, OpSec)
from startScan.models import *
from startScan.models import EndPoint, Subdomain, Vulnerability, Parameter
from targetApp.models import Domain
from dashboard.models import AcunetixAPIKey
from reNgine.monitor_tasks import *
from reNgine.graph_utils import Neo4jManager
from reNgine.vulnerability_tasks import *
from reNgine.fuzzing_tasks import *
from reNgine.stress_testing_tasks import run_stress_testing
from reNgine.osint_tasks import *
from reNgine.task_utils import (
    run_command, stream_command, save_email, save_employee, save_subdomain, save_endpoint, save_parameter,
    sanitize_command_for_db, get_tool_color, ensure_endpoints_crawled_and_execute, save_fuzzing_file,
    parse_custom_header_to_list, save_subdomain_metadata
)
from reNgine.report_tasks import *
from reNgine.wpscan_tasks import wpscan_scan
from reNgine.parsers import SpiderFootBatchParser
from reNgine.tech_mapping import get_nuclei_tags_from_techs
try:
	from acunetix import Acunetix
except ImportError:
	Acunetix = None

from plugins.orchestrator import PluginOrchestrator

"""
Celery tasks.
"""

logger = get_task_logger(__name__)


SCAN_PIPELINE_DEFINITION = [
    {
        'tier': 1,
        'name': 'Discovery',
        'type': 'CONCURRENT',
        'tasks': ['amass_intel_discovery', 'subdomain_discovery', 'osint', 'spiderfoot_scan', 'firewall_vpn_scan']
    },
    {
        'tier': 2,
        'name': 'Enumeration',
        'type': 'CONCURRENT',
        'tasks': ['http_crawl', 'port_scan', 'screenshot']
    },
    {
        'tier': 3,
        'name': 'Fuzzing',
        'type': 'SEQUENTIAL',
        'tasks': ['dir_file_fuzz']
    },
    {
        'tier': 4,
        'name': 'URL Extraction',
        'type': 'SEQUENTIAL',
        'tasks': ['fetch_url']
    },
    {
        'tier': 5,
        'name': 'Analysis',
        'type': 'CONCURRENT',
        'tasks': ['web_api_discovery', 'waf_detection']
    },
    {
        'tier': 6,
        'name': 'Security Assessment',
        'type': 'CONCURRENT',
        'tasks': ['waf_bypass', 'vulnerability_scan', 'brute_force_scan']
    },
    {
        'tier': 7,
        'name': 'Finalization',
        'type': 'SEQUENTIAL',
        'tasks': [
            'correlate_vulnerabilities',
            'calculate_risk_scores',
            'generate_impact_assessment',
            'stress_test',
            'run_apme'
        ]
    }
]


#----------------------#
# Scan / Subscan tasks #
#----------------------#


@app.task(name='sync_all_scans_to_graph', queue='main_scan_queue', base=RengineTask, bind=True)
def sync_all_scans_to_graph(self):
	"""Sync all pre-existing scan results to Neo4j graph."""
	print(">>> [GRAPH SYNC] Starting global graph synchronization...")
	logger.info("Starting global graph synchronization...")
	nm = Neo4jManager()
	nm.sync_all_scans()
	nm.close()
	logger.info("Global graph synchronization completed.")
	print(">>> [GRAPH SYNC] Global graph synchronization completed.")

@app.task(name='finish_chord', queue='main_scan_queue')
def finish_chord(results, description="Task"):
    """Generic callback for Celery chords to mark a grouped operation as complete."""
    logger.info(f"Grouped task '{description}' completed.")
    return results

@app.task(name='finish_osint', queue='main_scan_queue')
def finish_osint(results, scan_history_id):
    """Callback for OSINT tasks, triggers Deep Pursuit pipeline."""
    from reNgine.tasks import osint_orchestrator
    logger.info(f"OSINT discovery completed for scan {scan_history_id}")
    logger.info('Starting Deep Pursuit OSINT Pipeline...')
    osint_orchestrator.delay(scan_history_id=scan_history_id)
    return results

@app.task(name='finish_vulnerability_scan', queue='main_scan_queue')
def finish_vulnerability_scan(results, scan_history_id):
    """Callback for vulnerability scan tasks."""
    logger.info(f"Vulnerability scan completed for scan {scan_history_id}")
    return results

@app.task(name='finish_nuclei_scan', queue='main_scan_queue')
def finish_nuclei_scan(results, scan_history_id):
    """Callback for Nuclei scan tasks."""
    logger.info(f"Nuclei scan completed for scan {scan_history_id}")
    return results

@app.task(name='finish_osint_discovery', queue='main_scan_queue')
def finish_osint_discovery(results, results_dir):
    """Callback for OSINT discovery tasks. Strips metadata from results."""
    from reNgine.opsec_utils import OpSecManager
    opsec = OpSecManager()
    opsec.strip_directory(results_dir)
    logger.info(f"OSINT discovery completed and cleaned up in {results_dir}")
    return results


def resolve_primary_vulnerability_tasks(config, urls=[], ctx={}):
    """Parses primary vulnerability subtasks configuration and returns signatures.

    Args:
        config (dict): The engine YAML configuration.
        urls (list): Optional URL targets.
        ctx (dict): The scan workflow context dictionary.
    """
    vuln_config = config.get(VULNERABILITY_SCAN) or {}
    should_run_nuclei = vuln_config.get(RUN_NUCLEI, True)
    should_run_crlfuzz = vuln_config.get(RUN_CRLFUZZ, False)
    should_run_dalfox = vuln_config.get(RUN_DALFOX, False)
    should_run_s3scanner = vuln_config.get(RUN_S3SCANNER, True)

    subtasks = []

    # Check and add nuclei scan task if enabled
    if should_run_nuclei:
        subtasks.append(nuclei_scan.si(urls=urls, ctx=ctx, description='Nuclei Scan'))

    # Check and add CRLFuzz scan task if enabled
    if should_run_crlfuzz:
        subtasks.append(crlfuzz_scan.si(urls=urls, ctx=ctx, description='CRLFuzz Scan'))

    # Check and add Dalfox XSS scan task if enabled
    if should_run_dalfox:
        subtasks.append(dalfox_xss_scan.si(urls=urls, ctx=ctx, description='Dalfox XSS Scan'))

    # Check and add S3Scanner task if enabled
    if should_run_s3scanner:
        subtasks.append(s3scanner.si(ctx=ctx, description='Misconfigured S3 Buckets Scanner'))

    return subtasks


def resolve_additional_vulnerability_tasks(config, urls=[], ctx={}):
    """Parses additional vulnerability subtasks configuration and returns signatures.

    Args:
        config (dict): The engine YAML configuration.
        urls (list): Optional URL targets.
        ctx (dict): The scan workflow context dictionary.
    """
    vuln_config = config.get(VULNERABILITY_SCAN) or {}
    should_run_acunetix = vuln_config.get(RUN_ACUNETIX, False)
    should_run_wpscan = vuln_config.get(RUN_WPSCAN, True)
    should_run_cpanel = vuln_config.get('cpanel_scanner', {}).get(RUN_CPANEL2SHELL, True)
    should_run_react2shell = vuln_config.get('react_scanner', {}).get(RUN_REACT2SHELL, True)

    subtasks = []

    # Check and add Acunetix scan task if enabled and valid credentials exist
    if should_run_acunetix:
        creds = AcunetixAPIKey.objects.first()
        if creds and creds.server_url and creds.api_key:
            subtasks.append(acunetix_scan.si(
                domain_id=ctx.get('domain_id'),
                scan_history_id=ctx.get('scan_history_id'),
                ctx=ctx
            ))

    # Check and add cPanel vulnerability scan task if enabled
    if should_run_cpanel:
        subtasks.append(cpanel_scan.si(ctx=ctx, description='cPanel Vulnerability Scan'))

    # Check and add WPScan task if enabled
    if should_run_wpscan:
        subtasks.append(wpscan_scan.si(urls=urls, ctx=ctx, description='WPScan'))

    # Check and add React2Shell vulnerability scan task if enabled
    if should_run_react2shell:
        subtasks.append(react2shell_scan.si(ctx=ctx, description='React Vulnerability Scan'))

    # Always append Semgrep Vulnerability Scan as default
    subtasks.append(semgrep_scan.si(ctx=ctx, mode='vulnerability', description='Semgrep Vulnerability Scan'))

    return subtasks


def resolve_vulnerability_tasks(config, urls=[], ctx={}):
    """Parses all vulnerability subtasks configuration and returns their signatures.

    Args:
        config (dict): The engine YAML configuration.
        urls (list): Optional URL targets.
        ctx (dict): The scan workflow context dictionary.
    """
    # Return both primary and additional resolved subtasks in order
    return resolve_primary_vulnerability_tasks(config, urls, ctx) + resolve_additional_vulnerability_tasks(config, urls, ctx)



@app.task(name='initiate_scan', bind=False, queue='initiate_scan_queue')
def initiate_scan(
		scan_history_id,
		domain_id,
		engine_id=None,
		scan_type=LIVE_SCAN,
		results_dir=RENGINE_RESULTS,
		imported_subdomains=[],
		out_of_scope_subdomains=[],
		initiated_by_id=None,
		starting_point_path='',
		excluded_paths=[],
		custom_dorks=None,
		enable_spiderfoot_scan=False,
	):
	"""Initiate a new scan.

	Args:
		scan_history_id (int): ScanHistory id.
		domain_id (int): Domain id.
		engine_id (int): Engine ID.
		scan_type (int): Scan type (periodic, live).
		results_dir (str): Results directory.
		imported_subdomains (list): Imported subdomains.
		out_of_scope_subdomains (list): Out-of-scope subdomains.
		starting_point_path (str): URL path. Default: '' Defined where to start the scan.
		initiated_by (int): User ID initiating the scan.
		excluded_paths (list): Excluded paths. Default: [], url paths to exclude from scan.
		custom_dorks (str): Custom dorks to run. Default: None.
	"""
	logger.info('Initiating scan on celery')
	scan = None
	try:
		# Get scan history
		if scan_history_id:
			scan = ScanHistory.objects.filter(pk=scan_history_id).first()

		# Get scan engine
		if not engine_id and scan:
			engine_id = scan.scan_type.id
		engine = EngineType.objects.get(pk=engine_id)

		# Get YAML config
		config = yaml.safe_load(engine.yaml_configuration)
		enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
		gf_patterns = config.get(GF_PATTERNS, [])
		# Get web_api_discovery config
		api_discovery_config = config.get(WEB_API_DISCOVERY, {})
		api_discovery_tools = api_discovery_config.get(USES_TOOLS, [])
		kr_wordlist = api_discovery_config.get(KITERUNNER_WORDLIST, 'routes-large.kite')

		# Get domain and set last_scan_date
		domain = Domain.objects.get(pk=domain_id)
		domain.last_scan_date = timezone.now()
		domain.save()

		# Get path filter
		starting_point_path = starting_point_path.rstrip('/')

		# for live scan scan history id is passed as scan_history_id 
		# and no need to create scan_history object
	
		if scan_type == SCHEDULED_SCAN: # scheduled
			# we need to create scan_history object for each scheduled scan 
			scan_history_id = create_scan_object(
				host_id=domain_id,
				engine_id=engine_id,
				initiated_by_id=initiated_by_id,
			)

		if not scan:
			scan = ScanHistory.objects.get(pk=scan_history_id)
		scan.scan_status = RUNNING_TASK
		scan.scan_type = engine
		scan.celery_ids = [initiate_scan.request.id]
		scan.domain = domain
		scan.start_scan_date = timezone.now()
		scan.tasks = engine.tasks
		scan.results_dir = f'{results_dir}/{domain.name}_{scan.id}'
		add_gf_patterns = gf_patterns and 'fetch_url' in engine.tasks
		# add configs to scan object, cfg_ prefix is used to avoid conflicts with other scan object fields
		scan.cfg_starting_point_path = starting_point_path
		scan.cfg_excluded_paths = excluded_paths
		scan.cfg_out_of_scope_subdomains = out_of_scope_subdomains
		scan.cfg_imported_subdomains = imported_subdomains

		if add_gf_patterns:
			scan.used_gf_patterns = ','.join(gf_patterns)
		
		if custom_dorks:
			scan.cfg_custom_dorks = custom_dorks

		scan.save()

		# Create scan results dir
		os.makedirs(scan.results_dir)

		# Save custom dorks to txt file if provided
		if custom_dorks:
			with open(f'{scan.results_dir}/custom_dorks.txt', 'w') as f:
				f.write(custom_dorks)

		# Build task context
		ctx = {
			'scan_history_id': scan_history_id,
			'engine_id': engine_id,
			'domain_id': domain.id,
			'results_dir': scan.results_dir,
			'starting_point_path': starting_point_path,
			'excluded_paths': excluded_paths,
			'yaml_configuration': config,
			'out_of_scope_subdomains': out_of_scope_subdomains,
			'custom_dorks': custom_dorks,
			'api_discovery_tools': api_discovery_tools,
			'kr_wordlist': kr_wordlist
		}
		ctx_str = json.dumps(ctx, indent=2)

		# Send start notif
		logger.warning(f'Starting scan {scan_history_id} with context:\n{ctx_str}')
		send_scan_notif.delay(
			scan_history_id,
			subscan_id=None,
			engine_id=engine_id,
			status=CELERY_TASK_STATUS_MAP[scan.scan_status])

		# Save imported subdomains in DB
		save_imported_subdomains(imported_subdomains, ctx=ctx)

		# Create initial subdomain in DB: make a copy of domain as a subdomain so
		# that other tasks using subdomains can use it.
		subdomain_name = domain.name
		subdomain, _ = save_subdomain(subdomain_name, ctx=ctx)

		# If enable_http_crawl is set, create an initial root HTTP endpoint so that
		# HTTP crawling can start somewhere
		http_url = f'{domain.name}{starting_point_path}' if starting_point_path else domain.name
		# Check if we should use a simplified alive check for stress tests
		stress_config = config.get('stress_test', {})
		is_stress_only = 'stress_test' in engine.tasks and len(engine.tasks) == 1
		
		should_crawl = enable_http_crawl
		endpoint = None
		
		if is_stress_only and not stress_config.get('crawl_targets', False):
			# The user wants ONLY the provided target and NO heavy discovery (like httpx)
			# but still wants an alive check.
			should_crawl = False
			# Perform a very basic alive check using requests
			try:
				import requests
				import urllib3
				urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
				
				check_url = http_url if '://' in http_url else f'http://{http_url}'
				logger.info(f"Performing simplified alive check for stress test on {check_url}")
				
				response = requests.get(
					check_url, 
					timeout=10, 
					verify=False, 
					allow_redirects=True,
					headers={'User-Agent': 'reNgine-Stress-Check'}
				)
				
				endpoint_data = {
					'http_status': response.status_code,
					'content_length': len(response.content),
					'response_time': response.elapsed.total_seconds(),
				}
				# Overwrite http_url with the final URL after redirects
				http_url = response.url
				endpoint, _ = save_endpoint(
					http_url,
					ctx=ctx,
					crawl=False,
					is_default=True,
					subdomain=subdomain,
					**endpoint_data
				)
			except Exception as e:
				logger.error(f"Simplified alive check failed: {e}")
				# Fallback to saving without check
				endpoint, _ = save_endpoint(
					http_url,
					ctx=ctx,
					crawl=False,
					is_default=True,
					subdomain=subdomain
				)
		else:
			endpoint, _ = save_endpoint(
				http_url,
				ctx=ctx,
				crawl=should_crawl,
				is_default=True,
				subdomain=subdomain
			)
		if endpoint and endpoint.is_alive:
			# TODO: add `root_endpoint` property to subdomain and simply do
			# subdomain.root_endpoint = endpoint instead
			logger.warning(f'Found subdomain root HTTP URL {endpoint.http_url}')
			subdomain.http_url = endpoint.http_url
			subdomain.http_status = endpoint.http_status
			subdomain.response_time = endpoint.response_time
			subdomain.page_title = endpoint.page_title
			subdomain.content_type = endpoint.content_type
			subdomain.content_length = endpoint.content_length
			for tech in endpoint.techs.all():
				subdomain.technologies.add(tech)
			subdomain.save()


		# Build Celery tasks, crafted according to the dependency graph below:
		# subdomain_discovery --> port_scan --> fetch_url --> dir_file_fuzz
		# osint								             	  vulnerability_scan
		# osint								             	  dalfox xss scan
		#						 	   		         	  	  screenshot
		tasks = engine.tasks
		logger.warning(f"Engine tasks for {engine.engine_name}: {tasks}")
		
		# WAF Logic: If WAF Bypass is enabled, WAF Detection MUST also be enabled
		if 'waf_bypass' in tasks and 'waf_detection' not in tasks:
			try:
				index = tasks.index('waf_bypass')
				tasks.insert(index, 'waf_detection')
			except ValueError:
				tasks.append('waf_detection')
			scan.tasks = tasks
			scan.save()

		if enable_spiderfoot_scan and 'spiderfoot_scan' not in tasks:
			tasks.append('spiderfoot_scan')
			scan.tasks = tasks
			scan.save()

		# Map YAML keys to their respective Celery tasks
		task_map = {
			'amass_intel_discovery': amass_intel_discovery.si(host=domain.name, ctx=ctx, description='Infrastructure Discovery'),
			'subdomain_discovery': subdomain_discovery.si(ctx=ctx, description='Subdomain discovery'),
			'osint': osint.si(ctx=ctx, description='OS Intelligence'),
			'spiderfoot_scan': spiderfoot_scan.si(ctx=ctx, description='Attack Surface Intelligence'),
			'http_crawl': http_crawl.si(ctx=ctx, description='HTTP Crawl'),
			'port_scan': port_scan.si(ctx=ctx, description='Port scan'),
			'fetch_url': fetch_url.si(ctx=ctx, description='Fetch URL'),
			'dir_file_fuzz': dir_file_fuzz.si(ctx=ctx, description='Directories & files fuzz'),
			'web_api_discovery': web_api_discovery.si(ctx=ctx, description='Web API Discovery'),
			'vulnerability_scan': vulnerability_scan.si(ctx=ctx, description='Vulnerability scan'),
			'screenshot': screenshot.si(ctx=ctx, description='Screenshot'),
			'waf_detection': waf_detection.si(ctx=ctx, description='WAF detection'),
			'waf_bypass': waf_bypass.si(ctx=ctx, description='WAF bypass'),
			'secret_scanning': secret_scanning.si(ctx=ctx, description='Secrets & Leaks Scan'),
			'firewall_vpn_scan': firewall_vpn_scan.si(ctx=ctx, description='Firewall & VPN scan'),
			'brute_force_scan': brute_force_scan.si(ctx=ctx, description='Brute force scan'),
			'correlate_vulnerabilities': correlate_vulnerabilities.si(scan_history_id=scan_history_id, ctx=ctx),
			'calculate_risk_scores': calculate_risk_scores.si(scan_history_id=scan_history_id, ctx=ctx),
			'generate_impact_assessment': generate_impact_assessment.si(scan_history_id=scan_history_id, ctx=ctx),
			'stress_test': run_stress_testing.si(
				scan_history_id=scan_history_id, 
				target_domain_name=domain.name, 
				yaml_config=config,
				ctx=ctx
			),
			'run_apme': run_apme.si(scan_history_id=scan_history_id, ctx=ctx)
		}

		def is_task_enabled(task_name):
			if task_name in ['subdomain_discovery', 'osint', 'spiderfoot_scan', 'http_crawl', 'port_scan', 'screenshot', 
							'dir_file_fuzz', 'fetch_url', 'web_api_discovery', 'waf_detection', 'waf_bypass', 
							'vulnerability_scan', 'brute_force_scan', 'firewall_vpn_scan', 'secret_scanning', 'stress_test']:
				return task_name in tasks
			
			if task_name in ['correlate_vulnerabilities', 'calculate_risk_scores']:
				vuln_producing_tasks = {'vulnerability_scan', 'dir_file_fuzz', 'web_api_discovery', 'brute_force_scan', 'osint'}
				return any(t in tasks for t in vuln_producing_tasks)
			
			if task_name == 'generate_impact_assessment':
				return config.get('enable_ai_impact_analysis', False)
			
			
			if task_name == 'run_apme':
				apme_config = config.get(ATTACK_PATH_MODELING, {})
				if apme_config.get('enabled', False): return True
				return config.get(VULNERABILITY_SCAN, {}).get('run_apme', False)
			
			return False

		workflow_steps = []
		
		# --- NEW REFACTORED PIPELINE WITH NON-BLOCKING BRANCHES ---
		
		# Helper to wrap task with plugins
		def get_wrapped(name):
			if not is_task_enabled(name): return None
			if name == 'vulnerability_scan':
				# Verify if any subtasks are configured/enabled before queueing the orchestrator
				subtasks = resolve_vulnerability_tasks(config, [], ctx)
				if not subtasks: return None
				base_flow = chain(
					vulnerability_scan.si(urls=[], ctx=ctx, description='Vulnerability scan'),
					finish_vulnerability_scan.s(scan_history_id=ctx.get('scan_history_id'))
				)
				return PluginOrchestrator.inject_tasks(name, base_flow, ctx)
			return PluginOrchestrator.inject_tasks(name, task_map[name], ctx)

		# Tier 7: Sequential terminal chain
		t7_tasks = []
		for t in ['correlate_vulnerabilities', 'calculate_risk_scores', 'generate_impact_assessment', 'stress_test', 'run_apme']:
			wrapped = get_wrapped(t)
			if wrapped: t7_tasks.append(wrapped)
		t7_chain = chain(*t7_tasks) if t7_tasks else None

		# Tier 6: Blockers for Tier 7
		t6_tasks = []
		for t in ['waf_bypass', 'vulnerability_scan', 'brute_force_scan']:
			wrapped = get_wrapped(t)
			if wrapped: t6_tasks.append(wrapped)
		t6_step = group(t6_tasks) if t6_tasks else None

		# Tier 5: Blockers for Tier 6
		t5_tasks = []
		for t in ['web_api_discovery', 'waf_detection', 'secret_scanning']:
			wrapped = get_wrapped(t)
			if wrapped: t5_tasks.append(wrapped)
		t5_step = group(t5_tasks) if t5_tasks else None

		# Build Assessment Chain (T5 -> T6 -> T7)
		assessment_steps = []
		if t5_step: assessment_steps.append(t5_step)
		if t6_step: assessment_steps.append(t6_step)
		if t7_chain: assessment_steps.append(t7_chain)
		assessment_chain = chain(*assessment_steps) if assessment_steps else None

		# Branch A: Independent URL Gathering & GF Pattern Matching flow (fetch_url)
		# Starts directly after Subdomain Enumeration, running in parallel.
		t4_task = get_wrapped('fetch_url')

		# Branch B: http_crawl -> dir_file_fuzz
		t3_task = get_wrapped('dir_file_fuzz')
		t2_blocker = get_wrapped('http_crawl')
		
		branch_b = None
		if t2_blocker and t3_task:
			branch_b = chain(t2_blocker, t3_task)
		elif t2_blocker:
			branch_b = t2_blocker
		elif t3_task:
			branch_b = t3_task

		# Define other Tier 2 background tasks running in parallel
		t2_background = []
		for t in ['port_scan', 'screenshot']:
			wrapped = get_wrapped(t)
			if wrapped: t2_background.append(wrapped)

		# Add Branch A and Branch B as parallel components in Tier 2 group
		parallel_branches = []
		if t4_task:
			parallel_branches.append(t4_task) # Branch A runs in parallel
		if branch_b:
			parallel_branches.append(branch_b) # Branch B runs in parallel
		
		t2_step = group(t2_background + parallel_branches) if (t2_background or parallel_branches) else None

		# Combine Tier 2 parallel group with the subsequent assessment chain (chords compile automatically)
		t2_main_branch = chain(t2_step, assessment_chain) if (t2_step and assessment_chain) else (t2_step or assessment_chain)

		# Tier 1: Branching logic
		t1_blockers = []
		for t in ['amass_intel_discovery', 'subdomain_discovery', 'firewall_vpn_scan']:
			wrapped = get_wrapped(t)
			if wrapped: t1_blockers.append(wrapped)
		
		t1_main_branch = chain(group(t1_blockers), t2_main_branch) if t1_blockers else t2_main_branch

		t1_background = []
		for t in ['osint']:
			wrapped = get_wrapped(t)
			if wrapped: t1_background.append(wrapped)

		# Trigger SpiderFoot asynchronously if enabled (Tier 1 Non-Blocking)
		if 'spiderfoot_scan' in engine.tasks or enable_spiderfoot_scan:
			logger.warning(f"[DEBUG] Reached SpiderFoot trigger for {domain.name}. enable_spiderfoot_scan={enable_spiderfoot_scan}, tasks={engine.tasks}")
			logger.warning(f"Triggering asynchronous SpiderFoot scan for {domain.name}")
			# Pass host=None for main scan to allow the task to fetch subdomains if needed
			spiderfoot_scan.apply_async(kwargs={'ctx': ctx, 'host': None})

		# Final Workflow construction
		workflow_steps = []
		# Global Start Plugin (Virtual)
		start_plugin = PluginOrchestrator.inject_tasks("Tier_1_Start", None, ctx)
		if start_plugin: workflow_steps.append(start_plugin)

		# Combine background and main branches
		if t1_background:
			workflow_steps.append(group(t1_background + ([t1_main_branch] if t1_main_branch else [])))
		elif t1_main_branch:
			workflow_steps.append(t1_main_branch)

		# Global End Plugin (Virtual)
		end_plugin = PluginOrchestrator.inject_tasks("Tier_7_End", None, ctx)
		if end_plugin: workflow_steps.append(end_plugin)

		# Filter out duplicates or None steps
		workflow_steps = [step for step in workflow_steps if step is not None]
		
		# Debug task list
		task_names = []
		for step in workflow_steps:
			if hasattr(step, 'task'):
				task_names.append(step.task)
			elif hasattr(step, 'tasks'):
				task_names.append([t.task if hasattr(t, 'task') else "complex_step" for t in step.tasks])
			else:
				task_names.append("complex_step")
		logger.warning(f"Scan {scan_history_id} Workflow: {task_names}")

		workflow = chain(*workflow_steps)

		# Build callback
		callback = report.si(ctx=ctx).set(link_error=[report.si(ctx=ctx)])

		# Run Celery chord
		logger.info(f'Running Celery workflow with {len(workflow.tasks) + 1} tasks')
		task = chain(workflow, callback).on_error(callback).delay()
		scan.celery_ids.append(task.id)
		scan.save()

		return {
			'success': True,
			'task_id': task.id
		}
	except Exception as e:
		logger.exception(e)
		if scan:
			scan.scan_status = FAILED_TASK
			scan.error_message = str(e)
			scan.save()
		return {
			'success': False,
			'error': str(e)
		}


def initiate_scan_temporal(
		scan_history_id,
		domain_id,
		engine_id=None,
		scan_type=LIVE_SCAN,
		results_dir=RENGINE_RESULTS,
		imported_subdomains=[],
		out_of_scope_subdomains=[],
		initiated_by_id=None,
		starting_point_path='',
		excluded_paths=[],
		custom_dorks=None,
		enable_spiderfoot_scan=False,
	):
	"""Initiate a new scan using Temporal durable workflow orchestration.

	This function performs the same scan setup as `initiate_scan` (creates the
	ScanHistory record, results directory, initial subdomain and endpoint objects)
	but delegates execution to a `MasterScanWorkflow` on the Temporal cluster
	instead of building a Celery chain.

	This is the production entrypoint for all new scans when Temporal is active.

	Args:
		scan_history_id (int): ScanHistory id.
		domain_id (int): Domain id.
		engine_id (int): Engine ID.
		scan_type (int): Scan type (periodic, live).
		results_dir (str): Results directory root.
		imported_subdomains (list): Pre-imported subdomains.
		out_of_scope_subdomains (list): Out-of-scope subdomains to skip.
		initiated_by_id (int): User ID initiating the scan.
		starting_point_path (str): URL path filter. Default: ''.
		excluded_paths (list): URL paths to exclude from scan.
		custom_dorks (str): Custom dorks to run. Default: None.
		enable_spiderfoot_scan (bool): Whether to enable SpiderFoot scan.

	Returns:
		dict: {'success': True, 'workflow_id': str} on success.
	"""
	import asyncio
	import uuid

	logger.info('Initiating scan via Temporal workflow orchestrator')
	scan = None
	try:
		# ---- Get scan objects ----
		if scan_history_id:
			scan = ScanHistory.objects.filter(pk=scan_history_id).first()

		if not engine_id and scan:
			engine_id = scan.scan_type.id
		engine = EngineType.objects.get(pk=engine_id)

		# ---- Parse engine YAML config ----
		config = yaml.safe_load(engine.yaml_configuration)
		enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
		gf_patterns = config.get(GF_PATTERNS, [])
		api_discovery_config = config.get(WEB_API_DISCOVERY, {})
		api_discovery_tools = api_discovery_config.get(USES_TOOLS, [])
		kr_wordlist = api_discovery_config.get(KITERUNNER_WORDLIST, 'routes-large.kite')

		# ---- Get domain ----
		domain = Domain.objects.get(pk=domain_id)
		domain.last_scan_date = timezone.now()
		domain.save()

		starting_point_path = starting_point_path.rstrip('/')

		if scan_type == SCHEDULED_SCAN:
			scan_history_id = create_scan_object(
				host_id=domain_id,
				engine_id=engine_id,
				initiated_by_id=initiated_by_id,
			)

		if not scan:
			scan = ScanHistory.objects.get(pk=scan_history_id)

		tasks = list(engine.tasks)

		# WAF Logic: If WAF Bypass is enabled, WAF Detection MUST also be enabled
		if 'waf_bypass' in tasks and 'waf_detection' not in tasks:
			tasks.insert(tasks.index('waf_bypass'), 'waf_detection')

		if enable_spiderfoot_scan and 'spiderfoot_scan' not in tasks:
			tasks.append('spiderfoot_scan')

		# ---- Update ScanHistory ----
		scan.scan_status = RUNNING_TASK
		scan.scan_type = engine
		scan.domain = domain
		scan.start_scan_date = timezone.now()
		scan.tasks = tasks
		scan.results_dir = f'{results_dir}/{domain.name}_{scan.id}'
		scan.cfg_starting_point_path = starting_point_path
		scan.cfg_excluded_paths = excluded_paths
		scan.cfg_out_of_scope_subdomains = out_of_scope_subdomains
		scan.cfg_imported_subdomains = imported_subdomains

		add_gf_patterns = gf_patterns and 'fetch_url' in tasks
		if add_gf_patterns:
			scan.used_gf_patterns = ','.join(gf_patterns)

		if custom_dorks:
			scan.cfg_custom_dorks = custom_dorks

		scan.save()

		# ---- Create scan results directory ----
		os.makedirs(scan.results_dir, exist_ok=True)

		if custom_dorks:
			with open(f'{scan.results_dir}/custom_dorks.txt', 'w') as f:
				f.write(custom_dorks)

		# ---- Save imported subdomains ----
		save_imported_subdomains(imported_subdomains, ctx={
			'scan_history_id': scan.id,
			'domain_id': domain.id,
			'results_dir': scan.results_dir
		})

		# ---- Create initial root subdomain & endpoint ----
		ctx_bootstrap = {
			'scan_history_id': scan.id,
			'engine_id': engine_id,
			'domain_id': domain.id,
			'results_dir': scan.results_dir,
			'starting_point_path': starting_point_path,
			'out_of_scope_subdomains': out_of_scope_subdomains,
		}
		subdomain, _ = save_subdomain(domain.name, ctx=ctx_bootstrap)
		http_url = f'{domain.name}{starting_point_path}' if starting_point_path else domain.name
		endpoint, _ = save_endpoint(
			http_url,
			ctx=ctx_bootstrap,
			crawl=enable_http_crawl,
			is_default=True,
			subdomain=subdomain
		)
		if endpoint and endpoint.is_alive:
			subdomain.http_url = endpoint.http_url
			subdomain.http_status = endpoint.http_status
			subdomain.response_time = endpoint.response_time
			subdomain.page_title = endpoint.page_title
			subdomain.content_type = endpoint.content_type
			subdomain.content_length = endpoint.content_length
			for tech in endpoint.techs.all():
				subdomain.technologies.add(tech)
			subdomain.save()

		# ---- Build Temporal workflow context (mirrors Celery ctx) ----
		temporal_ctx = {
			'scan_history_id': scan.id,
			'engine_id': engine_id,
			'domain_id': domain.id,
			'results_dir': scan.results_dir,
			'starting_point_path': starting_point_path,
			'excluded_paths': excluded_paths,
			'yaml_configuration': config,
			'out_of_scope_subdomains': out_of_scope_subdomains,
			'custom_dorks': custom_dorks,
			'api_discovery_tools': api_discovery_tools,
			'kr_wordlist': kr_wordlist,
			'tasks': tasks,
		}

		# ---- Start MasterScanWorkflow on Temporal ----
		from reNgine.temporal_client import TemporalClientProvider
		from datetime import timedelta
		from temporalio.exceptions import ServerError as TemporalServiceError

		workflow_id = f"scan-{scan.id}-{uuid.uuid4().hex[:8]}"
		max_retries = 3
		backoff_base = 2

		async def _start_workflow_with_retry():
			"""Async helper: connect to Temporal, start workflow, retry on transient errors."""
			for attempt in range(1, max_retries + 1):
				try:
					client = await TemporalClientProvider.get_client()
					logger.info(
						f'[initiate_scan_temporal] Starting MasterScanWorkflow '
						f'attempt {attempt}/{max_retries} workflow_id={workflow_id}'
					)
					handle = await client.start_workflow(
						"MasterScanWorkflow",
						temporal_ctx,
						id=workflow_id,
						task_queue="python-orchestrator-queue",
						execution_timeout=timedelta(days=30),
						run_timeout=timedelta(days=30),
						task_timeout=timedelta(hours=1),
					)
					return handle.id
				except TemporalServiceError as e:
					if attempt == max_retries:
						logger.error(
							f'[initiate_scan_temporal] Failed after {max_retries} retries: {e}'
						)
						raise
					wait_time = backoff_base ** (attempt - 1)
					logger.warning(
						f'[initiate_scan_temporal] Attempt {attempt} failed, retrying in {wait_time}s: {e}'
					)
					await asyncio.sleep(wait_time)

		TemporalClientProvider.reset()
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		try:
			started_workflow_id = loop.run_until_complete(_start_workflow_with_retry())
		finally:
			loop.close()

		logger.info(
			f'Started MasterScanWorkflow id={started_workflow_id} '
			f'for scan_history_id={scan.id}'
		)

		# Send start notification via Celery (non-blocking)
		send_scan_notif.delay(
			scan.id,
			subscan_id=None,
			engine_id=engine_id,
			status=CELERY_TASK_STATUS_MAP.get(scan.scan_status, 'RUNNING')
		)

		return {
			'success': True,
			'workflow_id': started_workflow_id,
		}

	except Exception as e:
		logger.exception(e)
		if scan:
			scan.scan_status = FAILED_TASK
			scan.error_message = str(e)
			scan.save()
		return {
			'success': False,
			'error': str(e)
		}


def initiate_subscan_temporal(
		scan_history_id,
		subdomain_id,
		engine_id=None,
		scan_type=None,
		results_dir=RENGINE_RESULTS,
		starting_point_path='',
		excluded_paths=[],
		custom_dorks=None,
	):
	"""Initiate a new subscan using Temporal durable workflow orchestration.

	This function performs the same subdomain scan setup as `initiate_subscan`
	(creates the SubScan record, results directory, initial subdomain and endpoint
	objects) but delegates execution to a `SubScanWorkflow` on the Temporal cluster
	instead of building a Celery chain.

	Args:
		scan_history_id (int): ScanHistory id.
		subdomain_id (int): Subdomain id.
		engine_id (int, optional): Engine ID.
		scan_type (str, optional): Scan type (e.g. 'osint', 'port_scan', etc.).
		results_dir (str, optional): Results directory root.
		starting_point_path (str, optional): URL path. Default: ''.
		excluded_paths (list, optional): Excluded paths. Default: [].
		custom_dorks (str, optional): Custom dorks. Default: None.

	Returns:
		dict: {'success': True, 'workflow_id': str} on success.
	"""
	import asyncio
	import uuid

	logger.info(f"Initiating subdomain subscan '{scan_type}' via Temporal workflow orchestrator")
	subscan = None
	try:
		# ---- Get Subdomain, Domain and ScanHistory ----
		subdomain = Subdomain.objects.get(pk=subdomain_id)
		scan = ScanHistory.objects.get(pk=subdomain.scan_history.id)
		domain = Domain.objects.get(pk=subdomain.target_domain.id)

		# ---- Get EngineType ----
		engine_id = engine_id or scan.scan_type.id
		engine = EngineType.objects.get(pk=engine_id)

		# ---- Get YAML config ----
		config = yaml.safe_load(engine.yaml_configuration)
		enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
		
		# ---- Get web_api_discovery config ----
		api_discovery_config = config.get(WEB_API_DISCOVERY, {})
		api_discovery_tools = api_discovery_config.get(USES_TOOLS, [])
		kr_wordlist = api_discovery_config.get(KITERUNNER_WORDLIST, 'routes-large.kite')

		# ---- Create scan activity of SubScan Model ----
		subscan = SubScan(
			start_scan_date=timezone.now(),
			celery_ids=[], # Will store temporal workflow ID
			scan_history=scan,
			subdomain=subdomain,
			type=scan_type,
			status=RUNNING_TASK,
			engine=engine
		)
		subscan.save()

		# ---- Create results directory ----
		subscan_results_dir = f'{scan.results_dir}/subscans/{subscan.id}'
		os.makedirs(subscan_results_dir, exist_ok=True)

		# ---- Update scan's tasks list ----
		if scan_type not in scan.tasks:
			scan.tasks.append(scan_type)
			scan.save()

		# ---- Send start notification via Celery (non-blocking) ----
		try:
			send_scan_notif.delay(
				scan.id,
				subscan_id=subscan.id,
				engine_id=engine_id,
				status='RUNNING'
			)
		except Exception as notif_err:
			logger.warning(f"Could not send subscan start notification: {notif_err}")

		# ---- Build Temporal workflow context (mirrors Celery ctx) ----
		temporal_ctx = {
			'scan_history_id': scan.id,
			'subscan_id': subscan.id,
			'engine_id': engine_id,
			'domain_id': domain.id,
			'subdomain_id': subdomain.id,
			'subdomain_name': subdomain.name,
			'subdomain_http_url': subdomain.http_url,
			'yaml_configuration': config,
			'results_dir': subscan_results_dir,
			'starting_point_path': starting_point_path,
			'excluded_paths': excluded_paths,
			'api_discovery_tools': api_discovery_tools,
			'kr_wordlist': kr_wordlist
		}

		# ---- Create initial endpoints in DB ----
		# Find domain HTTP endpoint so that HTTP crawling can start somewhere
		base_url = f'{subdomain.name}{starting_point_path}' if starting_point_path else subdomain.name
		endpoint, _ = save_endpoint(
			base_url,
			crawl=enable_http_crawl,
			ctx=temporal_ctx,
			subdomain=subdomain
		)
		if endpoint and endpoint.is_alive:
			logger.warning(f'Found subdomain root HTTP URL {endpoint.http_url}')
			subdomain.http_url = endpoint.http_url
			subdomain.http_status = endpoint.http_status
			subdomain.response_time = endpoint.response_time
			subdomain.page_title = endpoint.page_title
			subdomain.content_type = endpoint.content_type
			subdomain.content_length = endpoint.content_length
			for tech in endpoint.techs.all():
				subdomain.technologies.add(tech)
			subdomain.save()

			# Update context with new URL
			temporal_ctx['subdomain_http_url'] = subdomain.http_url

		# ---- Start SubScanWorkflow on Temporal ----
		from reNgine.temporal_client import TemporalClientProvider
		from datetime import timedelta
		from temporalio.exceptions import ServerError as TemporalServiceError

		workflow_id = f"subscan-{subscan.id}-{uuid.uuid4().hex[:8]}"
		max_retries = 3
		backoff_base = 2

		async def _start_subscan_workflow_with_retry():
			"""Async helper: connect to Temporal, start SubScanWorkflow, retry on transient errors."""
			for attempt in range(1, max_retries + 1):
				try:
					client = await TemporalClientProvider.get_client()
					logger.info(
						f'[initiate_subscan_temporal] Starting SubScanWorkflow '
						f'attempt {attempt}/{max_retries} workflow_id={workflow_id}'
					)
					handle = await client.start_workflow(
						"SubScanWorkflow",
						args=[temporal_ctx, scan_type],
						id=workflow_id,
						task_queue="python-orchestrator-queue",
						execution_timeout=timedelta(days=7),
						run_timeout=timedelta(days=7),
						task_timeout=timedelta(hours=1),
					)
					return handle.id
				except TemporalServiceError as e:
					if attempt == max_retries:
						logger.error(
							f'[initiate_subscan_temporal] Failed after {max_retries} retries: {e}'
						)
						raise
					wait_time = backoff_base ** (attempt - 1)
					logger.warning(
						f'[initiate_subscan_temporal] Attempt {attempt} failed, retrying in {wait_time}s: {e}'
					)
					await asyncio.sleep(wait_time)

		TemporalClientProvider.reset()
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		try:
			started_workflow_id = loop.run_until_complete(_start_subscan_workflow_with_retry())
		finally:
			loop.close()

		logger.info(
			f"Started SubScanWorkflow id={started_workflow_id} "
			f"for subscan_id={subscan.id} (type={scan_type})"
		)

		# Save workflow ID in subscan's celery_ids list for UI compatibility
		subscan.celery_ids = [started_workflow_id]
		subscan.save()

		return {
			'success': True,
			'workflow_id': started_workflow_id,
		}

	except Exception as e:
		logger.exception(e)
		if subscan:
			subscan.status = FAILED_TASK
			subscan.save()
		return {
			'success': False,
			'error': str(e)
		}


@app.task(name='initiate_subscan', bind=False, queue='subscan_queue')
def initiate_subscan(
		scan_history_id,
		subdomain_id,
		engine_id=None,
		scan_type=None,
		results_dir=RENGINE_RESULTS,
		starting_point_path='',
		excluded_paths=[],
		custom_dorks=None,
	):
	"""Initiate a new subscan.

	Args:
		scan_history_id (int): ScanHistory id.
		subdomain_id (int): Subdomain id.
		engine_id (int): Engine ID.
		scan_type (int): Scan type (periodic, live).
		results_dir (str): Results directory.
		starting_point_path (str): URL path. Default: ''
		excluded_paths (list): Excluded paths. Default: [], url paths to exclude from scan.
	"""

	# Get Subdomain, Domain and ScanHistory
	subdomain = Subdomain.objects.get(pk=subdomain_id)
	scan = ScanHistory.objects.get(pk=subdomain.scan_history.id)
	domain = Domain.objects.get(pk=subdomain.target_domain.id)

	# Get EngineType
	engine_id = engine_id or scan.scan_type.id
	engine = EngineType.objects.get(pk=engine_id)

	# Get YAML config
	config = yaml.safe_load(engine.yaml_configuration)
	enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
	
	# Get web_api_discovery config
	api_discovery_config = config.get(WEB_API_DISCOVERY, {})
	api_discovery_tools = api_discovery_config.get(USES_TOOLS, [])
	kr_wordlist = api_discovery_config.get(KITERUNNER_WORDLIST, 'routes-large.kite')

	# Create scan activity of SubScan Model
	subscan = SubScan(
		start_scan_date=timezone.now(),
		celery_ids=[initiate_subscan.request.id],
		scan_history=scan,
		subdomain=subdomain,
		type=scan_type,
		status=RUNNING_TASK,
		engine=engine)
	subscan.save()


	# Create results directory
	results_dir = f'{scan.results_dir}/subscans/{subscan.id}'
	os.makedirs(results_dir, exist_ok=True)

	# Run task
	method = globals().get(scan_type)
	if not method:
		logger.warning(f'Task {scan_type} is not supported by reNgine. Skipping')
		return
	scan.tasks.append(scan_type)
	scan.save()

	# Send start notif
	send_scan_notif.delay(
		scan.id,
		subscan_id=subscan.id,
		engine_id=engine_id,
		status='RUNNING')

	# Build context
	ctx = {
		'scan_history_id': scan.id,
		'subscan_id': subscan.id,
		'engine_id': engine_id,
		'domain_id': domain.id,
		'subdomain_id': subdomain.id,
		'yaml_configuration': config,
		'results_dir': results_dir,
		'starting_point_path': starting_point_path,
		'excluded_paths': excluded_paths,
		'api_discovery_tools': api_discovery_tools,
		'kr_wordlist': kr_wordlist
	}

	# Create initial endpoints in DB: find domain HTTP endpoint so that HTTP
	# crawling can start somewhere
	base_url = f'{subdomain.name}{starting_point_path}' if starting_point_path else subdomain.name
	endpoint, _ = save_endpoint(
		base_url,
		crawl=enable_http_crawl,
		ctx=ctx,
		subdomain=subdomain)
	if endpoint and endpoint.is_alive:
		# TODO: add `root_endpoint` property to subdomain and simply do
		# subdomain.root_endpoint = endpoint instead
		logger.warning(f'Found subdomain root HTTP URL {endpoint.http_url}')
		subdomain.http_url = endpoint.http_url
		subdomain.http_status = endpoint.http_status
		subdomain.response_time = endpoint.response_time
		subdomain.page_title = endpoint.page_title
		subdomain.content_type = endpoint.content_type
		subdomain.content_length = endpoint.content_length
		for tech in endpoint.techs.all():
			subdomain.technologies.add(tech)
		subdomain.save()

	# Build workflow steps based on task signature expectations
	target_url = subdomain.http_url or f"http://{subdomain.name}/"
	if scan_type == 'osint':
		workflow_steps = [method.si(ctx=ctx, host=subdomain.name)]
	elif scan_type == 'subdomain_discovery':
		workflow_steps = [method.si(ctx=ctx, host=subdomain.name)]
	elif scan_type == 'port_scan':
		workflow_steps = [method.si(ctx=ctx, hosts=[subdomain.name])]
	elif scan_type == 'fetch_url':
		workflow_steps = [method.si(ctx=ctx, urls=[target_url])]
	elif scan_type == 'vulnerability_scan':
		subtasks = resolve_vulnerability_tasks(config, [target_url], ctx)
		workflow_steps = [vulnerability_scan.si(urls=[target_url], ctx=ctx, description='Vulnerability scan')] if subtasks else []
	else:
		# dir_file_fuzz, screenshot, waf_detection and other plugin/unknown tasks
		# do not accept a 'host' or 'urls' parameter at the task level and read from ctx
		workflow_steps = [method.si(ctx=ctx)]

	# If this is a vulnerability scan, we need to run correlation
	if scan_type == 'vulnerability_scan':
		# Run ERL validation if plugin is installed
		workflow_steps.append(PluginOrchestrator.inject_tasks('ExploitReadinessLayer', None, ctx))

		# Run correlation
		workflow_steps.append(correlate_vulnerabilities.si(scan_history_id=scan.id, ctx=ctx))

		# Run risk score calculation
		workflow_steps.append(calculate_risk_scores.si(scan_history_id=scan.id, ctx=ctx))

	# Attack Path Modeling Engine (APME)
	apme_config = config.get(ATTACK_PATH_MODELING, {})
	# For backward compatibility, check both the new key and the old run_apme key in vulnerability_scan
	run_apme_enabled = apme_config.get('enabled', False)
	if not run_apme_enabled:
		vuln_scan_config = config.get(VULNERABILITY_SCAN, {})
		run_apme_enabled = vuln_scan_config.get('run_apme', False)

	if run_apme_enabled:
		workflow_steps.append(run_apme.si(scan_history_id=scan.id))

	# Filter out None steps (where plugins aren't present)
	workflow_steps = [step for step in workflow_steps if step is not None]

	# Build header + callback
	workflow = chain(*workflow_steps)
	callback = report.si(ctx=ctx).set(link_error=[report.si(ctx=ctx)])

	# Run Celery tasks
	task = chain(workflow, callback).on_error(callback).delay()
	subscan.celery_ids.append(task.id)
	subscan.save()


	return {
		'success': True,
		'task_id': task.id
	}


@app.task(name='report', bind=True, queue='report_queue')
def report(self, ctx={}, description=None):
	"""Report task running after all other tasks.
	Mark ScanHistory or SubScan object as completed and update with final
	status, log run details and send notification.

	Args:
		description (str, optional): Task description shown in UI.
	"""
	# Get objects
	subscan_id = ctx.get('subscan_id')
	scan_id = ctx.get('scan_history_id')

	# Check if there are other scanning tasks still running
	if scan_id:
		from startScan.models import ScanActivity
		from reNgine.definitions import RUNNING_TASK, INITIATED_TASK
		post_processing_names = ['correlate_vulnerabilities', 'calculate_risk_scores', 'generate_impact_assessment', 'run_apme', 'report']
		running_scans = ScanActivity.objects.filter(
			scan_of_id=scan_id,
			status__in=[RUNNING_TASK, INITIATED_TASK]
		).exclude(name__in=post_processing_names)
		if running_scans.exists():
			running_names = list(running_scans.values_list('name', flat=True))
			#logger.info(f"Scanning tasks are still running: {running_names}. Rescheduling report...")
			raise self.retry(countdown=10, max_retries=1000)

	engine_id = ctx.get('engine_id')
	scan = ScanHistory.objects.filter(pk=scan_id).first()
	subscan = SubScan.objects.filter(pk=subscan_id).first()

	# Get failed tasks
	tasks = ScanActivity.objects.filter(scan_of=scan).all()
	if subscan:
		tasks = tasks.filter(celery_id__in=subscan.celery_ids)
	failed_tasks = tasks.filter(status__in=[FAILED_TASK, ABORTED_TASK])

	# Get task status
	failed_count = failed_tasks.count()

	if subscan:
		status = SUCCESS_TASK if failed_count == 0 else FAILED_TASK
		status_h = 'SUCCESS' if failed_count == 0 else 'FAILED'
		subscan.stop_scan_date = timezone.now()
		subscan.status = status
		subscan.save()
	else:
		# Main scan completion
		if failed_count == 0:
			status = SUCCESS_TASK
			status_h = 'SUCCESS'
		else:
			# If any subscans failed, mark as Partially Complete
			has_failed_subscans = SubScan.objects.filter(scan_history=scan, status__in=[FAILED_TASK, ABORTED_TASK]).exists()

			if has_failed_subscans:
				status = PARTIALLY_COMPLETE_TASK
				status_h = 'PARTIALLY COMPLETE'
			else:
				status = FAILED_TASK
				status_h = 'FAILED'

		scan.scan_status = status

	scan.stop_scan_date = timezone.now()
	scan.save()

	# Send scan status notif
	send_scan_notif.delay(
		scan_history_id=scan_id,
		subscan_id=subscan_id,
		engine_id=engine_id,
		status=status_h)


#------------------------- #
# Tracked reNgine tasks    #
#--------------------------#

@app.task(name='amass_intel_discovery', queue='main_scan_queue', base=RengineTask, bind=True)
def amass_intel_discovery(self, host, ctx={}, description=None):
	"""Infrastructure discovery using Amass Intel.
	
	Args:
		host (str): Target domain to run intel on.
	"""
	config = self.yaml_configuration.get(SUBDOMAIN_DISCOVERY) or {}
	use_amass_config = config.get(USE_AMASS_CONFIG, False)
	
	output_path = f'{self.results_dir}/amass_intel.txt'
	
	cmd = f'amass intel -d {host} -whois -o {output_path}'
	cmd += ' -config /root/.config/amass.ini' if use_amass_config else ''
	
	#proxy = get_random_proxy()
	#if proxy:
	#	cmd = f"export HTTP_PROXY='{proxy}' HTTPS_PROXY='{proxy}' && {cmd}"
		
	#opsec = OpSecManager()
	#cmd = opsec.apply_stealth('amass', cmd, proxy=proxy)
	
	run_command(
		cmd,
		shell=True,
		history_file=self.history_file,
		scan_id=self.scan_id,
		activity_id=self.activity_id
	)
	
	# Process results: finding other root domains
	discovered_count = 0
	if os.path.exists(output_path):
		with open(output_path, 'r') as f:
			for line in f:
				domain_name = line.strip()
				if domain_name and domain_name != host:
					discovered_count += 1
					logger.info(f"Discovered associated domain: {domain_name}")
					
	if discovered_count > 0:
		self.notify(fields={'Infrastructure Discovery': f'Discovered {discovered_count} associated domains/assets via Amass Intel.'})
		
	return True


@app.task(name='subdomain_discovery', queue='main_scan_queue', base=RengineTask, bind=True)
def subdomain_discovery(
		self,
		host=None,
		ctx=None,
		description=None):
	"""Uses a set of tools (see SUBDOMAIN_SCAN_DEFAULT_TOOLS) to scan all
	subdomains associated with a domain.

	Args:
		host (str): Hostname to scan.

	Returns:
		subdomains (list): List of subdomain names.
	"""
	if not host:
		host = self.subdomain.name if self.subdomain else self.domain.name

	if self.starting_point_path:
		logger.warning(f'Ignoring subdomains scan as an URL path filter was passed ({self.starting_point_path}).')
		return

	# Config
	config = self.yaml_configuration.get(SUBDOMAIN_DISCOVERY) or {}
	enable_http_crawl = config.get(ENABLE_HTTP_CRAWL) or self.yaml_configuration.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
	threads = config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	timeout = config.get(TIMEOUT) or self.yaml_configuration.get(TIMEOUT, DEFAULT_HTTP_TIMEOUT)
	tools = config.get(USES_TOOLS, SUBDOMAIN_SCAN_DEFAULT_TOOLS)
	default_subdomain_tools = [tool.name.lower() for tool in InstalledExternalTool.objects.filter(is_default=True).filter(is_subdomain_gathering=True)]
	custom_subdomain_tools = [tool.name.lower() for tool in InstalledExternalTool.objects.filter(is_default=False).filter(is_subdomain_gathering=True)]
	send_subdomain_changes, send_interesting = False, False
	notif = Notification.objects.first()
	subdomain_scope_checker = SubdomainScopeChecker(self.out_of_scope_subdomains)
	if notif:
		send_subdomain_changes = notif.send_subdomain_changes_notif
		send_interesting = notif.send_interesting_notif

	# Gather tools to run for subdomain scan
	if ALL in tools:
		tools = SUBDOMAIN_SCAN_DEFAULT_TOOLS + custom_subdomain_tools
	tools = [t.lower() for t in tools]

	# Make exception for amass since tool name is amass, but command is amass-active/passive
	default_subdomain_tools.append('amass-passive')
	default_subdomain_tools.append('amass-active')

	# Run tools
	opsec = OpSecManager()
	existing_subs = set(Subdomain.objects.filter(scan_history=self.scan).values_list('name', flat=True))
	new_discoveries = []

	for tool in tools:
		cmd = None
		logger.info(f'Scanning subdomains for {host} with {tool}')
		proxy = get_random_proxy()
		if tool in default_subdomain_tools:
			if tool == 'amass-passive':
				use_amass_config = config.get(USE_AMASS_CONFIG, False)
				cmd = f'amass enum -passive -d {host} -o {self.results_dir}/subdomains_amass.txt'
				cmd += ' -config /root/.config/amass.ini' if use_amass_config else ''
				#if proxy:
				#	cmd = f"export HTTP_PROXY='{proxy}' HTTPS_PROXY='{proxy}' && {cmd}"

			elif tool == 'amass-active':
				use_amass_config = config.get(USE_AMASS_CONFIG, False)
				amass_wordlist_name = config.get(AMASS_WORDLIST, 'deepmagic.com-prefixes-top50000')
				wordlist_path = f'/usr/src/wordlist/{amass_wordlist_name}.txt'
				cmd = f'amass enum -active -d {host} -o {self.results_dir}/subdomains_amass_active.txt'
				cmd += ' -config /root/.config/amass.ini' if use_amass_config else ''
				cmd += f' -brute -w {wordlist_path}'
				#if proxy:
				#	cmd = f"export HTTP_PROXY='{proxy}' HTTPS_PROXY='{proxy}' && {cmd}"

			elif tool == 'sublist3r':
				cmd = f'python3 /usr/src/github/Sublist3r/sublist3r.py -d {host} -t {threads} -o {self.results_dir}/subdomains_sublister.txt'

			elif tool == 'subfinder':
				cmd = f'subfinder -d {host} -all -o {self.results_dir}/subdomains_subfinder.txt'
				use_subfinder_config = config.get(USE_SUBFINDER_CONFIG, False)
				cmd += ' -config /root/.config/subfinder/config.yaml' if use_subfinder_config else ''
				#cmd += f' -proxy {proxy}' if proxy else ''
				cmd += f' -timeout {timeout}' if timeout else ''
				cmd += f' -t {threads}' if threads else ''
				cmd += f' -silent'

			elif tool == 'oneforall':
				cmd = f'python3 /usr/src/github/OneForAll/oneforall.py --target {host} run'
				cmd_extract = f'cut -d\',\' -f6 /usr/src/github/OneForAll/results/{host}.csv | tail -n +2 > {self.results_dir}/subdomains_oneforall.txt'
				cmd_rm = f'rm -rf /usr/src/github/OneForAll/results/{host}.csv'
				cmd += f' && {cmd_extract} && {cmd_rm}'

			elif tool == 'ctfr':
				results_file = self.results_dir + '/subdomains_ctfr.txt'
				cmd = f'python3 /usr/src/github/ctfr/ctfr.py -d {host} -o {results_file}'
				cmd_extract = f"cat {results_file} | sed 's/\\*.//g' | tail -n +12 | uniq | sort > {results_file}_temp && mv {results_file}_temp {results_file}"
				cmd += f' && {cmd_extract}'

			elif tool == 'tlsx':
				results_file = self.results_dir + '/subdomains_tlsx.txt'
				cmd = f'tlsx -san -cn -silent -ro -host {host}'
				cmd += f" | sed -n '/^\([a-zA-Z0-9]\([-a-zA-Z0-9]*[a-zA-Z0-9]\)\?\.\)\+{host}$/p' | uniq | sort"
				cmd += f' > {results_file}'

			elif tool == 'netlas':
				results_file = self.results_dir + '/subdomains_netlas.txt'
				cmd = f'netlas search -d domain -i domain domain:"*.{host}" -f json'
				netlas_key = get_netlas_key()
				cmd += f' -a {netlas_key}' if netlas_key else ''
				cmd_extract = f"grep -oE '([a-zA-Z0-9]([-a-zA-Z0-9]*[a-zA-Z0-9])?\.)+{host}'"
				cmd += f' | {cmd_extract} > {results_file}'

			elif tool == 'chaos':
				# we need to find api key if not ignore
				chaos_key = get_chaos_key()
				if not chaos_key:
					logger.error('Chaos API key not found. Skipping.')
					continue
				results_file = self.results_dir + '/subdomains_chaos.txt'
				cmd = f'chaos -d {host} -silent -key {chaos_key} -o {results_file}'

			elif tool == 'baddns':
				results_file = self.results_dir + '/subdomains_baddns.txt'
				# baddns -d domain -o output
				cmd = f'baddns -d {host} -o {results_file}'


		elif tool in custom_subdomain_tools:
			tool_query = InstalledExternalTool.objects.filter(name__icontains=tool.lower())
			if not tool_query.exists():
				logger.error(f'{tool} configuration does not exists. Skipping.')
				continue
			custom_tool = tool_query.first()
			cmd = custom_tool.subdomain_gathering_command
			if '{TARGET}' not in cmd:
				logger.error(f'Missing {{TARGET}} placeholders in {tool} configuration. Skipping.')
				continue
			if '{OUTPUT}' not in cmd:
				logger.error(f'Missing {{OUTPUT}} placeholders in {tool} configuration. Skipping.')
				continue

			
			cmd = cmd.replace('{TARGET}', host)
			cmd = cmd.replace('{OUTPUT}', f'{self.results_dir}/subdomains_{tool}.txt')
			cmd = cmd.replace('{PATH}', custom_tool.github_clone_path) if '{PATH}' in cmd else cmd
		else:
			logger.warning(
				f'Subdomain discovery tool "{tool}" is not supported by reNgine. Skipping.')
			continue

		# Apply OpSec stealth
		cmd = opsec.apply_stealth(tool, cmd, proxy=proxy)

		# Run tool
		try:
			logger.warning(f'Running {tool} with command: {cmd}')
			run_command(
				cmd,
				shell=True,
				history_file=self.history_file,
				scan_id=self.scan_id,
				activity_id=self.activity_id,
				proxy=proxy if tool not in ['amass-passive', 'amass-active', 'subfinder'] else None)
			
		except Exception as e:
			logger.error(
				f'Subdomain discovery tool "{tool}" raised an exception')
			logger.exception(e)

	# Gather all the tools' results in one single file. Write subdomains into
	# separate files, and sort all subdomains.
	run_command(
		f'cat {self.results_dir}/subdomains_*.txt > {self.output_path}',
		shell=True,
		history_file=self.history_file,
		scan_id=self.scan_id,
		activity_id=self.activity_id)
	run_command(
		f'sort -u {self.output_path} -o {self.output_path}',
		shell=True,
		history_file=self.history_file,
		scan_id=self.scan_id,
		activity_id=self.activity_id)

	with open(self.output_path) as f:
		lines = f.readlines()

	# Parse the output_file file and store Subdomain and EndPoint objects found
	# in db.
	subdomain_count = 0
	subdomains = []
	urls = []
	for line in lines:
		subdomain_name = line.strip()
		valid_url = bool(validators.url(subdomain_name))
		valid_domain = (
			bool(validators.domain(subdomain_name)) or
			bool(validators.ipv4(subdomain_name)) or
			bool(validators.ipv6(subdomain_name)) or
			valid_url
		)
		if not valid_domain:
			logger.error(f'Subdomain {subdomain_name} is not a valid domain, IP or URL. Skipping.')
			continue

		if valid_url:
			subdomain_name = urlparse(subdomain_name).netloc

		if subdomain_scope_checker.is_out_of_scope(subdomain_name):
			logger.error(f'Subdomain {subdomain_name} is out of scope. Skipping.')
			continue

		# Add subdomain
		subdomain, created = save_subdomain(subdomain_name, ctx=ctx)
		if subdomain:
			subdomain_count += 1
			# Special handling for baddns findings (if it was a takeover)
			# We'll check the baddns report file specifically for this subdomain
			baddns_report = f'{self.results_dir}/subdomains_baddns.txt'
			if os.path.exists(baddns_report):
				with open(baddns_report, 'r') as f:
					for b_line in f:
						if subdomain_name in b_line and '[takeover]' in b_line.lower():
							subdomain.is_important = True
							subdomain.save()
							# Create Critical Vulnerability
							save_vulnerability(
								name=f"Subdomain Takeover on {subdomain_name}",
								description=f"baddns detected a potential subdomain takeover on {subdomain_name}. Line: {b_line.strip()}",
								severity='critical',
								type='Subdomain Takeover',
								subdomain=subdomain,
								scan_history=self.scan,
								target_domain=self.domain,
								validation_status='unverified'
							)
			subdomains.append(subdomain)
			urls.append(subdomain.name)

	# Bulk crawl subdomains - removed to avoid collisions; delegated to next stage in pipeline
	url_filter = ctx.get('url_filter')

	# Find root subdomain endpoints and save default endpoints
	for subdomain in subdomains:
		http_url = f'{subdomain.name}{url_filter}' if url_filter else subdomain.name
		endpoint, _ = save_endpoint(
			http_url,
			ctx=ctx,
			is_default=True,
			subdomain=subdomain
		)
		if endpoint:
			save_subdomain_metadata(subdomain, endpoint)

	# Send notifications
	subdomains_str = '\n'.join([f'• `{subdomain.name}`' for subdomain in subdomains])
	self.notify(fields={
		'Subdomain count': len(subdomains),
		'Subdomains': subdomains_str,
	})
	if send_subdomain_changes and self.scan_id and self.domain_id:
		added = get_new_added_subdomain(self.scan_id, self.domain_id)
		removed = get_removed_subdomain(self.scan_id, self.domain_id)

		if added:
			subdomains_str = '\n'.join([f'• `{subdomain}`' for subdomain in added])
			self.notify(fields={'Added subdomains': subdomains_str})

		if removed:
			subdomains_str = '\n'.join([f'• `{subdomain}`' for subdomain in removed])
			self.notify(fields={'Removed subdomains': subdomains_str})

	if send_interesting and self.scan_id and self.domain_id:
		interesting_subdomains = get_interesting_subdomains(self.scan_id, self.domain_id)
		if interesting_subdomains:
			subdomains_str = '\n'.join([f'• `{subdomain}`' for subdomain in interesting_subdomains])
			self.notify(fields={'Interesting subdomains': subdomains_str})

	return SubdomainSerializer(subdomains, many=True).data


@app.task(name='osint', queue='main_scan_queue', base=RengineTask, bind=True)
def osint(self, host=None, ctx={}, description=None):
	"""Run Open-Source Intelligence tools on selected domain.

	Args:
		host (str): Hostname to scan.

	Returns:
		dict: Results from osint discovery and dorking.
	"""
	config = self.yaml_configuration.get(OSINT) or OSINT_DEFAULT_CONFIG
	results = {}

	grouped_tasks = []

	if 'discover' in config:
		ctx['track'] = False
		# results = osint_discovery(host=host, ctx=ctx)
		_task = osint_discovery.si(
			config=config,
			host=self.scan.domain.name,
			scan_history_id=self.scan.id,
			activity_id=self.activity_id,
			results_dir=self.results_dir,
			ctx=ctx
		)
		grouped_tasks.append(_task)

	if OSINT_DORK in config or OSINT_CUSTOM_DORK in config or self.scan.cfg_custom_dorks:
		_task = dorking.si(
			config=config,
			host=self.scan.domain.name,
			scan_history_id=self.scan.id,
			activity_id=self.activity_id,
			results_dir=self.results_dir,
			raw_dorks=self.scan.cfg_custom_dorks
		)
		grouped_tasks.append(_task)

	if grouped_tasks:
		return self.replace(chord(grouped_tasks, finish_osint.s(scan_history_id=self.scan.id)))

	logger.info('Standard OSINT Tasks finished...')

	# Deep Pursuit OSINT Pipeline (holehe, maigret, LinkedInt)
	logger.info('Starting Deep Pursuit OSINT Pipeline...')
	osint_orchestrator.delay(scan_history_id=self.scan.id)

	logger.info('OSINT Tasks finished...')

	# with open(self.output_path, 'w') as f:
	# 	json.dump(results, f, indent=4)
	#
	# return results


@app.task(name='osint_discovery', queue='main_scan_queue', base=RengineTask, bind=True)
def osint_discovery(self, config, host, scan_history_id, activity_id, results_dir, ctx={}):
	"""Run OSINT discovery.

	Args:
		config (dict): yaml_configuration
		host (str): target name
		scan_history_id (startScan.ScanHistory): Scan History ID
		results_dir (str): Path to store scan results

	Returns:
		dict: osint metadat and theHarvester and h8mail results.
	"""
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	osint_lookup = config.get(OSINT_DISCOVER, [])
	osint_intensity = config.get(INTENSITY, 'normal')
	documents_limit = config.get(OSINT_DOCUMENTS_LIMIT, 50)
	results = {}
	meta_info = []
	emails = []
	creds = []

	# Get and save meta info
	if 'metainfo' in osint_lookup:
		if osint_intensity == 'normal':
			meta_dict = DottedDict({
				'osint_target': host,
				'domain': host,
				'scan_id': scan_history_id,
				'documents_limit': documents_limit
			})
			meta_info.append(save_metadata_info(meta_dict))

		# TODO: disabled for now
		# elif osint_intensity == 'deep':
		# 	subdomains = Subdomain.objects
		# 	if self.scan:
		# 		subdomains = subdomains.filter(scan_history=self.scan)
		# 	for subdomain in subdomains:
		# 		meta_dict = DottedDict({
		# 			'osint_target': subdomain.name,
		# 			'domain': self.domain,
		# 			'scan_id': self.scan_id,
		# 			'documents_limit': documents_limit
		# 		})
		# 		meta_info.append(save_metadata_info(meta_dict))

	grouped_tasks = []

	if 'emails' in osint_lookup:
		_task = h8mail.si(
			config=config,
			host=host,
			scan_history_id=scan_history_id,
			activity_id=activity_id,
			results_dir=results_dir,
			ctx=ctx
		)
		grouped_tasks.append(_task)

	if 'employees' in osint_lookup:
		ctx['track'] = False
		_task = theHarvester.si(
			config=config,
			host=host,
			scan_history_id=scan_history_id,
			activity_id=activity_id,
			results_dir=results_dir,
			ctx=ctx
		)
		grouped_tasks.append(_task)

	leaks_config = config.get(LEAKS_AND_SECRETS, {})
	if leaks_config:
		if leaks_config.get(LEAKLOOKUP):
			_task = leaklookup.si(
				host=host,
				scan_history_id=scan_history_id,
				activity_id=activity_id,
				results_dir=results_dir,
				ctx=ctx
			)
			grouped_tasks.append(_task)

		if leaks_config.get(GITLEAKS) or leaks_config.get(TRUFFLEHOG):
			_task = secret_scanning.si(
				config=leaks_config,
				host=host,
				scan_history_id=scan_history_id,
				activity_id=activity_id,
				results_dir=results_dir,
				ctx=ctx
			)
			grouped_tasks.append(_task)

	if grouped_tasks:
		return self.replace(chord(grouped_tasks, finish_osint_discovery.s(results_dir=results_dir)))

	# Strip metadata from OSINT results
	from reNgine.opsec_utils import OpSecManager
	opsec = OpSecManager()
	opsec.strip_directory(results_dir)

	return results


@app.task(name='dorking', queue='main_scan_queue', base=RengineTask, bind=False)
def dorking(config, host, scan_history_id, results_dir, activity_id=None, raw_dorks=None):
	"""Run Google dorks.

	Args:
		config (dict): yaml_configuration
		host (str): target name
		scan_history_id (startScan.ScanHistory): Scan History ID
		results_dir (str): Path to store scan results
		raw_dorks (str): Raw custom dorks list (one per line)

	Returns:
		list: Dorking results for each dork ran.
	"""
	# Some dork sources: https://github.com/six2dez/degoogle_hunter/blob/master/degoogle_hunter.sh
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	dorks = config.get(OSINT_DORK, [])
	custom_dorks = config.get(OSINT_CUSTOM_DORK, [])
	results = []
	# custom dorking has higher priority
	try:
		for custom_dork in custom_dorks:
			if isinstance(custom_dork, str):
				# Handle simple string query from YAML
				query = custom_dork.replace('_target_', host)
				logger.info(f'Processing YAML custom dork: {query}')
				get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type='custom_dork_yaml',
					lookup_keywords=query,
					scan_history=scan_history,
					activity_id=activity_id
				)
			elif isinstance(custom_dork, dict):
				# Handle structured dict from YAML
				lookup_target = custom_dork.get('lookup_site')
				# replace with original host if _target_
				lookup_target = host if lookup_target == '_target_' else lookup_target
				if 'lookup_extensions' in custom_dork:
					results = get_and_save_dork_results(
						lookup_target=lookup_target,
						results_dir=results_dir,
						type='custom_dork',
						lookup_extensions=custom_dork.get('lookup_extensions'),
						scan_history=scan_history,
						activity_id=activity_id
					)
				elif 'lookup_keywords' in custom_dork:
					results = get_and_save_dork_results(
						lookup_target=lookup_target,
						results_dir=results_dir,
						type='custom_dork',
						lookup_keywords=custom_dork.get('lookup_keywords'),
						scan_history=scan_history,
						activity_id=activity_id
					)
	except Exception as e:
		logger.error(f'Error processing custom dorks from YAML: {str(e)}')
		logger.exception(e)

	# Process raw custom dorks from UI/ScanHistory
	if raw_dorks:
		logger.info('Processing raw custom dorks...')
		try:
			custom_dork_list = raw_dorks.split('\n')
			for dork_query in custom_dork_list:
				dork_query = dork_query.strip()
				if dork_query:
					# We use the raw query as keywords for GooFuzz
					# Note: If dork_query starts with site:{host}, we strip it.
					query_to_run = dork_query
					if dork_query.startswith(f'site:{host} '):
						query_to_run = dork_query.replace(f'site:{host} ', '', 1)
					elif dork_query.startswith(f'site:{host}'):
						query_to_run = dork_query.replace(f'site:{host}', '', 1)
					
					get_and_save_dork_results(
						lookup_target=host,
						results_dir=results_dir,
						type='custom_dork_ui',
						lookup_keywords=query_to_run,
						scan_history=scan_history,
						activity_id=activity_id
					)
		except Exception as e:
			logger.exception(e)

	# default dorking
	try:
		for dork in dorks:
			logger.info(f'Getting dork information for {dork}')
			if dork == 'stackoverflow':
				results = get_and_save_dork_results(
					lookup_target='stackoverflow.com',
					results_dir=results_dir,
					type=dork,
					lookup_keywords=host,
					scan_history=scan_history
				)

			elif dork == 'login_pages':
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_keywords='/login/,login.html',
					page_count=5,
					scan_history=scan_history
				)

			elif dork == 'admin_panels':
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_keywords='/admin/,admin.html',
					page_count=5,
					scan_history=scan_history
				)

			elif dork == 'dashboard_pages':
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_keywords='/dashboard/,dashboard.html',
					page_count=5,
					scan_history=scan_history
				)

			elif dork == 'social_media' :
				social_websites = [
					'tiktok.com',
					'facebook.com',
					'twitter.com',
					'youtube.com',
					'reddit.com'
				]
				for site in social_websites:
					results = get_and_save_dork_results(
						lookup_target=site,
						results_dir=results_dir,
						type=dork,
						lookup_keywords=host,
						scan_history=scan_history
					)

			elif dork == 'project_management' :
				project_websites = [
					'trello.com',
					'atlassian.net'
				]
				for site in project_websites:
					results = get_and_save_dork_results(
						lookup_target=site,
						results_dir=results_dir,
						type=dork,
						lookup_keywords=host,
						scan_history=scan_history
					)

			elif dork == 'code_sharing' :
				project_websites = [
					'github.com',
					'gitlab.com',
					'bitbucket.org'
				]
				for site in project_websites:
					results = get_and_save_dork_results(
						lookup_target=site,
						results_dir=results_dir,
						type=dork,
						lookup_keywords=host,
						scan_history=scan_history
					)

			elif dork == 'config_files' :
				config_file_exts = [
					'env',
					'xml',
					'conf',
					'toml',
					'yml',
					'yaml',
					'cnf',
					'inf',
					'rdp',
					'ora',
					'txt',
					'cfg',
					'ini'
				]
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_extensions=','.join(config_file_exts),
					page_count=4,
					scan_history=scan_history
				)

			elif dork == 'jenkins' :
				lookup_keyword = 'Jenkins'
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_keywords=lookup_keyword,
					page_count=1,
					scan_history=scan_history
				)

			elif dork == 'wordpress_files' :
				lookup_keywords = [
					'/wp-content/',
					'/wp-includes/'
				]
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_keywords=','.join(lookup_keywords),
					page_count=5,
					scan_history=scan_history
				)

			elif dork == 'php_error' :
				lookup_keywords = [
					'PHP Parse error',
					'PHP Warning',
					'PHP Error'
				]
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_keywords=','.join(lookup_keywords),
					page_count=5,
					scan_history=scan_history
				)

			elif dork == 'jenkins' :
				lookup_keywords = [
					'PHP Parse error',
					'PHP Warning',
					'PHP Error'
				]
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_keywords=','.join(lookup_keywords),
					page_count=5,
					scan_history=scan_history
				)

			elif dork == 'exposed_documents' :
				docs_file_ext = [
					'doc',
					'docx',
					'odt',
					'pdf',
					'rtf',
					'sxw',
					'psw',
					'ppt',
					'pptx',
					'pps',
					'csv'
				]
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_extensions=','.join(docs_file_ext),
					page_count=7,
					scan_history=scan_history
				)

			elif dork == 'db_files' :
				file_ext = [
					'sql',
					'db',
					'dbf',
					'mdb'
				]
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_extensions=','.join(file_ext),
					page_count=1,
					scan_history=scan_history
				)

			elif dork == 'git_exposed' :
				file_ext = [
					'git',
				]
				results = get_and_save_dork_results(
					lookup_target=host,
					results_dir=results_dir,
					type=dork,
					lookup_extensions=','.join(file_ext),
					page_count=1,
					scan_history=scan_history
				)

	except Exception as e:
		logger.exception(e)
	return results


@app.task(name='theHarvester', queue='main_scan_queue', base=RengineTask, bind=True)
def theHarvester(self, config, host, scan_history_id, activity_id, results_dir, ctx={}):
	"""Run theHarvester to get save emails, hosts, employees found in domain.

	Args:
		config (dict): yaml_configuration
		host (str): target name
		scan_history_id (startScan.ScanHistory): Scan History ID
		activity_id: ScanActivity ID
		results_dir (str): Path to store scan results
		ctx (dict): context of scan

	Returns:
		dict: Dict of emails, employees, hosts and ips found during crawling.
	"""
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
	output_path_json = f'{results_dir}/theHarvester.json'
	theHarvester_dir = '/usr/src/github/theHarvester'
	history_file = f'{results_dir}/commands.txt'

	# Update proxies.yaml
	proxy_query = Proxy.objects.all()
	if proxy_query.exists():
		proxy = proxy_query.first()
		if proxy.use_proxy:
			proxy_list = proxy.proxies.splitlines()
			yaml_data = {'http' : proxy_list}
			with open(f'{theHarvester_dir}/proxies.yaml', 'w') as file:
				yaml.dump(yaml_data, file)

	# Run cmd
	logger.info('theHarvester started')
	cmd = f'uv run theHarvester -d {host} -b all -f {output_path_json}'
	logger.warning(f'TheHarvester command: {cmd}')
	run_command(
		cmd,
		shell=True,
		cwd=theHarvester_dir,
		history_file=history_file,
		scan_id=scan_history_id,
		activity_id=activity_id)

	# Get file location
	if not os.path.isfile(output_path_json):
		logger.error(f'Could not open {output_path_json}')
		return {}

	# Load theHarvester results
	with open(output_path_json, 'r') as f:
		data = json.load(f)

	# Re-indent theHarvester JSON
	with open(output_path_json, 'w') as f:
		json.dump(data, f, indent=4)

	emails = data.get('emails', [])
	for email_address in emails:
		email, _ = save_email(email_address, scan_history=scan_history)
		if email:
			self.notify(fields={'Emails': f'• `{email.address}`'})

	linkedin_people = data.get('linkedin_people', [])
	for people in linkedin_people:
		employee, _ = save_employee(
			people,
			designation='linkedin',
			scan_history=scan_history)
		if employee:
			self.notify(fields={'LinkedIn people': f'• {employee.name}'})

	twitter_people = data.get('twitter_people', [])
	for people in twitter_people:
		employee, _ = save_employee(
			people,
			designation='twitter',
			scan_history=scan_history)
		if employee:
			self.notify(fields={'Twitter people': f'• {employee.name}'})

	hosts = data.get('hosts', [])
	urls = []
	for host in hosts:
		split = tuple(host.split(':'))
		http_url = split[0]
		subdomain_name = get_subdomain_from_url(http_url)
		subdomain, _ = save_subdomain(subdomain_name, ctx=ctx)
		endpoint, _ = save_endpoint(
			http_url,
			crawl=False,
			ctx=ctx,
			subdomain=subdomain)
		if endpoint:
			urls.append(endpoint.http_url)
			self.notify(fields={'Hosts': f'• {endpoint.http_url}'})

	# if enable_http_crawl:
	# 	ctx['track'] = False
	# 	http_crawl(urls, ctx=ctx)

	# TODO: Lots of ips unrelated with our domain are found, disabling
	# this for now.
	# ips = data.get('ips', [])
	# for ip_address in ips:
	# 	ip, created = save_ip_address(
	# 		ip_address,
	# 		subscan=subscan)
	# 	if ip:
	# 		send_task_notif.delay(
	# 			'osint',
	# 			scan_history_id=scan_history_id,
	# 			subscan_id=subscan_id,
	# 			severity='success',
	# 			update_fields={'IPs': f'{ip.address}'})
	return data


@app.task(name='h8mail', queue='main_scan_queue', base=RengineTask, bind=True)
def h8mail(self, config, host, scan_history_id, activity_id, results_dir, ctx={}):
	"""Run h8mail.

	Args:
		config (dict): yaml_configuration
		host (str): target name
		scan_history_id (startScan.ScanHistory): Scan History ID
		activity_id: ScanActivity ID
		results_dir (str): Path to store scan results
		ctx (dict): context of scan

	Returns:
		list[dict]: List of credentials info.
	"""
	logger.warning('Getting leaked credentials')
	scan_history = ScanHistory.objects.get(pk=scan_history_id)
	input_path = f'{results_dir}/emails.txt'
	output_file = f'{results_dir}/h8mail.json'

	cmd = f'h8mail -t {input_path} --json {output_file}'
	history_file = f'{results_dir}/commands.txt'

	run_command(
		cmd,
		history_file=history_file,
		scan_id=scan_history_id,
		activity_id=activity_id)

	if os.path.exists(output_file):
		try:
			with open(output_file) as f:
				data = json.load(f)
				creds = data.get('targets', [])
		except Exception as e:
			logger.error(f"Error reading h8mail output: {e}")
			creds = []
	else:
		logger.warning(f"h8mail output file {output_file} not found.")
		creds = []

	# TODO: go through h8mail output and save emails to DB
	for cred in creds:
		logger.warning(cred)
		email_address = cred['target']
		pwn_num = cred['pwn_num']
		pwn_data = cred.get('data', [])
		email, created = save_email(email_address, scan_history=scan_history)
		# if email:
		# 	self.notify(fields={'Emails': f'• `{email.address}`'})
	return creds


@app.task(name='leaklookup', queue='main_scan_queue', base=RengineTask, bind=True)
def leaklookup(self, host=None, ctx=None, **kwargs):
	"""Run LeakLookup and ProjectDiscovery query."""
	leaklookup_api_key = get_leaklookup_key()
	chaos_api_key = get_chaos_api_key()

	if not leaklookup_api_key and not chaos_api_key:
		return "LeakLookup and ProjectDiscovery API keys not found. Skipping."

	results_summary = []

	# LeakLookup
	if leaklookup_api_key:
		try:
			url = "https://leak-lookup.com/api/search"
			params = {
				'key': leaklookup_api_key,
				'type': 'domain',
				'query': host
			}
			response = requests.post(url, data=params, timeout=30)
			if response.status_code == 200:
				data = response.json()
				if data.get('error') == 'false':
					leaks = data.get('message') or {}
					leak_count = 0
					for db_name, contents in leaks.items():
						for match in contents:
							save_secret_leak(
								scan_history=self.scan,
								tool_name=LEAKLOOKUP,
								secret_type="Data Leak",
								source_url=db_name,
								match_content=match,
								status='unverified'
							)
							leak_count += 1
					results_summary.append(f"LeakLookup: Found {leak_count} leaks in {len(leaks)} databases")
				else:
					results_summary.append(f"LeakLookup error: {data.get('message')}")
			else:
				results_summary.append(f"LeakLookup HTTP error: {response.status_code}")
		except Exception as e:
			logger.error(f"Error in LeakLookup: {e}")
			results_summary.append(f"LeakLookup error: {e}")

	# ProjectDiscovery
	if chaos_api_key:
		try:
			pd_url = f"https://api.projectdiscovery.io/v1/leaks?type=all&time_range=all_time&domain={host}"
			headers = {"X-API-Key": chaos_api_key}
			response = requests.get(pd_url, headers=headers, timeout=30)
			if response.status_code == 200:
				data = response.json()
				leaks = data.get('data') or []
				leak_count = 0
				for match in leaks:
					source_url = match.get('url') or match.get('url_domain') or 'Unknown'
					match_content = ""
					if match.get('username'):
						match_content += f"Username: {match.get('username')} "
					if match.get('password'):
						match_content += f"Password: {match.get('password')} "
					if match.get('device_ip'):
						match_content += f"IP: {match.get('device_ip')} "
					
					save_secret_leak(
						scan_history=self.scan,
						tool_name=PROJECTDISCOVERY,
						secret_type="Data Leak",
						source_url=source_url,
						match_content=match_content.strip(),
						status='unverified'
					)
					leak_count += 1
				results_summary.append(f"ProjectDiscovery: Found {leak_count} leaks")
			else:
				results_summary.append(f"ProjectDiscovery HTTP error: {response.status_code}")
		except Exception as e:
			logger.error(f"Error in ProjectDiscovery: {e}")
			results_summary.append(f"ProjectDiscovery error: {e}")

	return " | ".join(results_summary)


@app.task(name='secret_scanning', queue='main_scan_queue', base=RengineTask, bind=True)
def secret_scanning(self, config=None, host=None, ctx=None, **kwargs):
	"""Scan for secrets in JS files and potentially other sources."""
	if not self.scan:
		return "No scan history found."

	endpoints = EndPoint.objects.filter(scan_history=self.scan)
	# Sensitive extensions to scan
	SENSITIVE_EXTENSIONS = ('.js', '.env', '.php', '.asp', '.aspx', '.jsp', '.jspx', '.txt', '.log', '.conf', '.config', '.bak', '.old', '.json', '.yaml', '.yml')
	target_endpoints = [e for e in endpoints if e.http_url.lower().endswith(SENSITIVE_EXTENSIONS)]

	if not target_endpoints:
		return "No sensitive files found to scan."

	temp_dir = f"{self.results_dir}/secrets_temp"
	os.makedirs(temp_dir, exist_ok=True)

	# Download sensitive files
	for js in target_endpoints:
		try:
			filename = "".join([c if c.isalnum() else "_" for c in js.http_url]) + ".js"
			filepath = os.path.join(temp_dir, filename)
			resp = requests.get(js.http_url, timeout=10, verify=False)
			if resp.status_code == 200:
				with open(filepath, 'w') as f:
					f.write(resp.text)
		except Exception as e:
			logger.error(f"Failed to download {js.http_url}: {e}")

	findings_count = 0

	# Run Gitleaks
	if config.get(GITLEAKS):
		report_path = f"{temp_dir}/gitleaks_report.json"
		# Gitleaks v8+ detect command
		cmd = f"gitleaks detect --source {temp_dir} --report-format json --report-path {report_path} --exit-code 0"
		subprocess.run(cmd, shell=True)
		
		if os.path.exists(report_path):
			try:
				with open(report_path, 'r') as f:
					findings = json.load(f)
					for finding in findings:
						# Map finding to SecretLeak
						save_secret_leak(
							scan_history=self.scan,
							tool_name=GITLEAKS,
							secret_type=finding.get('Description', 'Secret'),
							source_url=finding.get('File', 'Unknown'),
							match_content=finding.get('Secret', ''),
							status='unverified'
						)
						findings_count += 1
			except Exception as e:
				logger.error(f"Error parsing Gitleaks report: {e}")

	# Run Trufflehog
	if config.get(TRUFFLEHOG):
		# Trufflehog v3 filesystem command
		cmd = f"trufflehog filesystem {temp_dir} --json"
		process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()
		
		for line in stdout.decode().splitlines():
			if not line: continue
			try:
				finding = json.loads(line)
				# Trufflehog v3 output format varies, but usually has 'SourceMetadata' or 'DetectorName'
				save_secret_leak(
					scan_history=self.scan,
					tool_name=TRUFFLEHOG,
					secret_type=finding.get('DetectorName', 'Secret'),
					source_url=finding.get('SourceMetadata', {}).get('Data', {}).get('Filesystem', {}).get('file', 'Unknown'),
					match_content=finding.get('Raw', ''),
					status='unverified'
				)
				findings_count += 1
			except Exception as e:
				logger.error(f"Error parsing Trufflehog finding: {e}")

	# Run Betterleaks
	if config.get(BETTERLEAKS):
		# Betterleaks is typically run against files or a directory
		# It's good for finding secrets like API keys, passwords, etc.
		# Command: betterleaks -p {temp_dir}
		cmd = f"betterleaks -p {temp_dir}"
		# Since betterleaks output format might vary, we'll try to parse stdout
		logger.info(f"Running Betterleaks on {temp_dir}")
		process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		stdout, stderr = process.communicate()
		logger.info(f"Betterleaks output: {stdout}")
		for line in stdout.splitlines():
			if line.strip():
				# Assuming betterleaks outputs findings in a recognizable format
				# For now, let's just log it and save if it looks like a finding
				if any(keyword in line.lower() for keyword in ['key', 'password', 'secret', 'token', 'found']):
					save_secret_leak(
						scan_history=self.scan,
						tool_name=BETTERLEAKS,
						secret_type='Potential Secret',
						source_url='Discovered Files',
						match_content=line.strip(),
						status='unverified'
					)
					findings_count += 1

	# Run Semgrep Secret Scan (Default)
	try:
		logger.info('Running Semgrep Secret Scan...')
		semgrep_scan.apply(kwargs={'ctx': ctx, 'mode': 'secret', 'description': 'Semgrep Secret Scan'})
	except Exception as e:
		logger.error(f"Semgrep secret scan failed: {e}")

	# Cleanup
	shutil.rmtree(temp_dir, ignore_errors=True)

	return f"Secret scanning completed. Found {findings_count} findings."


@app.task(name='spiderfoot_scan', queue='spiderfoot_queue', base=RengineTask, bind=True)
def spiderfoot_scan(self, host=None, ctx={}, description=None):
	"""Run SpiderFoot scan on selected domain with real-time batch parsing.
	"""
	# host selection logic based on user rules
	if not host:
		if self.subscan_id and self.subdomain:
			host = self.subdomain.name
		else:
			host = self.domain.name
	
	logger.warning(f"[SPIDERFOOT] Starting scan for target: {host} (Scan ID: {self.scan_id}, Subscan ID: {self.subscan_id})")
	
	if not self.yaml_configuration:
		logger.error("[SPIDERFOOT] yaml_configuration is empty! Check engine config.")
	
	config = self.yaml_configuration.get(SPIDERFOOT_SCAN) or {}
	modules = config.get('modules', 'all')
	threads = config.get('threads') or self.yaml_configuration.get('threads', 5)
	intensity = config.get('intensity', 'normal') # normal, fast, deep

	# Spiderfoot CLI intensity mapping (profiles)
	profile_cmd = ""
	if intensity == 'fast':
		profile_cmd = "-u footprint"
	elif intensity == 'deep':
		profile_cmd = "-u all"
	
	if modules != 'all':
		profile_cmd = f"-m {modules}"
	elif not profile_cmd:
		profile_cmd = "-u investigate"
	
	# Use global SF config
	sf_config_path = "/usr/src/github/spiderfoot/spiderfoot.cfg"
	sf_exec_path = "/usr/src/github/spiderfoot/sf.py"
	
	if not os.path.exists(sf_exec_path):
		logger.error(f"[SPIDERFOOT] SpiderFoot executable not found at {sf_exec_path}!")
		return
		
	if not os.path.exists(sf_config_path):
		logger.error(f"[SPIDERFOOT] SpiderFoot config not found at {sf_config_path}. Task may fail or use defaults.")
	
	# Use CSV output for streaming. -r includes source data, -n strips newlines.
	cmd = f"python3 {sf_exec_path} -s {host} {profile_cmd} -max-threads {threads} -o csv -r -n"
	logger.warning(f"[SPIDERFOOT] Executing command: {cmd}")
	
	# Initialize stateful parser with Redis dedup
	redis_client = Redis(host="redis", port=6379, decode_responses=True)
	parser = SpiderFootBatchParser(dedup_backend=redis_client, scan_id=self.scan_id, target_domain=self.domain.name)
	
	batch = []
	batch_size = 100
	
	for line in stream_command(
		cmd,
		shell=True,
		scan_id=self.scan_id,
		activity_id=self.activity_id):
		
		event = parser.parse_line(line)
		if not event:
			continue
			
		batch.append(event)
		
		if len(batch) >= batch_size:
			_process_spiderfoot_batch(self, batch, ctx, host)
			batch = []
	
	# Process remaining
	if batch:
		_process_spiderfoot_batch(self, batch, ctx, host)
		
	# Sync to Neo4j
	graph = Neo4jManager()
	graph.sync_scan_results(self.scan_id)
	graph.close()


def persist_osint_item(scan_history, domain, osint_type, e_data, confidence, source_data=None, event_type=None, ctx=None, activity_id=None):
	"""
	Core logic to persist an OSINT item into primary tables.
	Separated from tasks to allow manual promotion from UI.
	"""
	if osint_type == 'Subdomain':
		sub_name = e_data.lower()
		save_subdomain(sub_name, ctx=ctx)
	elif osint_type == 'Email':
		save_email(e_data.lower(), scan_history=scan_history)
	elif osint_type == 'Employee':
		save_employee(e_data, scan_history=scan_history)
	elif osint_type == 'URL':
		if is_valid_url(e_data):
			save_endpoint(e_data, ctx=ctx)
	elif osint_type == 'IP':
		save_ip_address(e_data, scan_id=scan_history.id, activity_id=activity_id)
	elif osint_type == 'Port':
		if ':' in e_data:
			ip_part, port_part = e_data.split(':', 1)
			if port_part.isdigit():
				port_num = int(port_part)
				res = get_port_service_description(port_num)
				port_obj, _ = update_or_create_port(port_num, service_name=res.get('service_name'), description=res.get('description'))
				ip_obj, _ = save_ip_address(ip_part, scan_id=scan_history.id, activity_id=activity_id)
				if ip_obj:
					ip_obj.ports.add(port_obj)
		elif e_data.isdigit():
			port_num = int(e_data)
			update_or_create_port(port_num)
	elif osint_type == 'Tech':
		from django.core.exceptions import MultipleObjectsReturned
		try:
			tech_obj, _ = Technology.objects.get_or_create(name=e_data)
		except MultipleObjectsReturned:
			tech_obj = Technology.objects.filter(name=e_data).first()
		if source_data:
			subdomain = Subdomain.objects.filter(name=source_data, scan_history=scan_history).first()
			if subdomain:
				subdomain.technologies.add(tech_obj)
	elif osint_type == 'Leak':
		save_secret_leak(
			scan_history=scan_history,
			tool_name='SpiderFoot',
			secret_type=event_type or 'Sensitive Data',
			source_url=source_data or 'SpiderFoot Findings',
			match_content=e_data
		)

def _process_spiderfoot_batch(self, batch, ctx, host):
	"""Internal helper to process a batch of SpiderFoot findings with tiered validation."""
	try:
		with transaction.atomic():
			for event in batch:
				e_type = event.get('type')
				e_data = event.get('data')
				osint_type = event.get('osint_type')
				confidence = event.get('confidence', 0)
				
				if not osint_type or not e_data:
					continue

				# Automated Persistence (High Confidence)
				if confidence > 80:
					persist_osint_item(
						scan_history=self.scan,
						domain=self.domain,
						osint_type=osint_type,
						e_data=e_data,
						confidence=confidence,
						source_data=event.get('source_data'),
						event_type=e_type,
						ctx=ctx,
						activity_id=self.activity_id
					)
				
				# Staging Area (Moderate Confidence: 50% -> 80%)
				elif 50 <= confidence <= 80:
					OsintStaging.objects.update_or_create(
						scan_history=self.scan,
						target_domain=self.domain,
						content=e_data,
						osint_type=osint_type,
						defaults={
							'source': event.get('source', 'SpiderFoot'),
							'confidence': confidence,
							'metadata': {
								'sf_type': e_type,
								'source_data': event.get('source_data'),
								'iocs': event.get('iocs')
							},
							'status': 'pending'
						}
					)
				else:
					# Discard low confidence noise
					logger.debug(f"[SPIDERFOOT] Discarding low confidence finding: {osint_type} - {e_data} ({confidence}%)")

		logger.warning(f"Processed batch of {len(batch)} SpiderFoot findings with validation.")
	except Exception as e:
		logger.error(f"Error processing SpiderFoot batch: {str(e)}")


@app.task(name='screenshot', queue='main_scan_queue', base=RengineTask, bind=True)
def screenshot(self, ctx={}, description=None):
	"""Embedded Playwright Screenshot task.
	
	Args:
		description (str, optional): Task description shown in UI.
	"""
	from reNgine.screenshot.tasks import take_screenshot_and_save

	# Config
	config = self.yaml_configuration.get(SCREENSHOT) or {}
	enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
	intensity = config.get(INTENSITY) or self.yaml_configuration.get(INTENSITY, DEFAULT_SCAN_INTENSITY)
	
	# If intensity is normal, grab only the root endpoints of each subdomain
	strict = True if intensity == 'normal' else False

	# Get subdomains to process
	subdomains = Subdomain.objects.filter(scan_history=self.scan)
	
	# If strict/normal intensity, we only care about subdomains that are definitely alive
	if strict:
		subdomains = subdomains.filter(http_status__gt=0).exclude(http_url__isnull=True)
	
	logger.info(f"Starting Playwright screenshot capture for {subdomains.count()} subdomains...")
	
	success_count = 0
	for subdomain in subdomains:
		# The internal task handles browser lifecycle, metadata, and DB persistence
		if take_screenshot_and_save(subdomain.id, self.scan_id, self.results_dir, activity_id=self.activity_id):
			success_count += 1
			
	self.notify(fields={'Screenshots': f'Successfully captured {success_count} screenshots using Embedded Playwright.'})
	
	return True



@app.task(name='port_scan', queue='main_scan_queue', base=RengineTask, bind=True)
def port_scan(self, hosts=[], ctx={}, description=None):
	"""Run port scan.

	Args:
		hosts (list, optional): Hosts to run port scan on.
		description (str, optional): Task description shown in UI.

	Returns:
		list: List of open ports (dict).
	"""
	input_file = f'{self.results_dir}/input_subdomains_port_scan.txt'
	# projectdiscovery tools like naabu and httpx seem to fail when proxies are used
	# ensuring that proxies are never used for naabu
	proxy = ''

	# Config
	config = self.yaml_configuration.get(PORT_SCAN) or {}
	enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
	timeout = config.get(TIMEOUT) or self.yaml_configuration.get(TIMEOUT, DEFAULT_HTTP_TIMEOUT)
	exclude_ports = config.get(NAABU_EXCLUDE_PORTS, [])
	exclude_subdomains = config.get(NAABU_EXCLUDE_SUBDOMAINS, False)
	ports = config.get(PORTS, NAABU_DEFAULT_PORTS)
	ports = [str(port) for port in ports]
	rate_limit = config.get(NAABU_RATE) or self.yaml_configuration.get(RATE_LIMIT, DEFAULT_RATE_LIMIT)
	threads = config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	passive = config.get(NAABU_PASSIVE, False)
	use_naabu_config = config.get(USE_NAABU_CONFIG, False)
	exclude_ports_str = ','.join(return_iterable(exclude_ports))
	# nmap args
	nmap_enabled = config.get(ENABLE_NMAP, False)
	nmap_cmd = config.get(NMAP_COMMAND, '')
	nmap_script = config.get(NMAP_SCRIPT, '')
	nmap_script = ','.join(return_iterable(nmap_script))
	nmap_script_args = config.get(NMAP_SCRIPT_ARGS)

	if hosts:
		with open(input_file, 'w') as f:
			f.write('\n'.join(hosts))
	else:
		hosts = get_subdomains(
			write_filepath=input_file,
			exclude_subdomains=exclude_subdomains,
			ctx=ctx)

	# Build cmd
	cmd = 'naabu -json -exclude-cdn'
	cmd += f' -list {input_file}' if len(hosts) > 0 else f' -host {hosts[0]}'
	if 'full' in ports or 'all' in ports:
		ports_str = ' -p "-"'
	elif 'top-100' in ports:
		ports_str = ' -top-ports 100'
	elif 'top-1000' in ports:
		ports_str = ' -top-ports 1000'
	else:
		ports_str = ','.join(ports)
		ports_str = f' -p {ports_str}'
	cmd += ports_str
	cmd += ' -config /root/.config/naabu/config.yaml' if use_naabu_config else ''
	cmd += f' -proxy "{proxy}"' if proxy else ''
	cmd += f' -c {threads}' if threads else ''
	cmd += f' -rate {rate_limit}' if rate_limit > 0 else ''
	cmd += f' -timeout {timeout}s' if timeout > 0 else ''
	cmd += f' -passive' if passive else ''
	cmd += f' -exclude-ports {exclude_ports_str}' if exclude_ports else ''
	cmd += f' -silent'

	# Execute cmd and gather results
	results = []
	urls = []
	ports_data = {}
	for line in stream_command(
			cmd,
			shell=True,
			history_file=self.history_file,
			scan_id=self.scan_id,
			activity_id=self.activity_id):

		if not isinstance(line, dict):
			continue
		results.append(line)
		port_number = line['port']
		ip_address = line['ip']
		host = line.get('host') or ip_address
		if port_number == 0:
			continue

		# Grab subdomain
		subdomain = Subdomain.objects.filter(
			name=host,
			target_domain=self.domain,
			scan_history=self.scan
		).first()

		# Add IP DB
		ip, _ = save_ip_address(ip_address, subdomain, subscan=self.subscan, scan_id=self.scan_id, activity_id=self.activity_id)
		if self.subscan:
			ip.ip_subscan_ids.add(self.subscan)
			ip.save()

		# Add endpoint to DB
		# port 80 and 443 not needed as http crawl already does that.
		if port_number not in [80, 443]:
			http_url = f'{host}:{port_number}'
			endpoint, _ = save_endpoint(
				http_url,
				crawl=enable_http_crawl,
				ctx=ctx,
				subdomain=subdomain)
			if endpoint:
				http_url = endpoint.http_url
			urls.append(http_url)

		# Add Port in DB
		res = get_port_service_description(port_number)
		# get or create port
		port, created = update_or_create_port(
			port_number=port_number,
			service_name=res.get('service_name', ''),
			description=res.get('description', '')
		)

		if created:
			logger.warning(f'Added new port {port_number} to DB')

		# Centralized Brute-Force Candidate Registration for Naabu findings
		bf_protocols = {
			21: 'ftp',
			22: 'ssh',
			23: 'telnet',
			445: 'smb',
			3389: 'rdp'
		}
		if port_number in bf_protocols:
			from reNgine.utilities import save_auth_candidate
			try:
				save_auth_candidate(
					scan_history=self.scan,
					subdomain=subdomain,
					target=host,
					protocol=bf_protocols[port_number],
					port=port_number,
					source_tool='naabu',
					tech_hint=f"Open Port {port_number}"
				)
			except Exception as e:
				logger.error(f"Error registering AuthCandidate from Naabu port {port_number}: {e}")

		if port_number in UNCOMMON_WEB_PORTS:
			port.is_uncommon = True
			port.save()
		ip.ports.add(port)
		ip.save()
		if host in ports_data:
			ports_data[host].append(port_number)
		else:
			ports_data[host] = [port_number]

		# Send notification
		logger.warning(f'Found opened port {port_number} on {ip_address} ({host})')

	if len(ports_data) == 0:
		logger.info('Finished running naabu port scan - No open ports found.')
		if nmap_enabled:
			logger.info('Nmap scans skipped')
		return ports_data

	# Send notification
	fields_str = ''
	for host, ports in ports_data.items():
		ports_str = ', '.join([f'`{port}`' for port in ports])
		fields_str += f'• `{host}`: {ports_str}\n'
	self.notify(fields={'Ports discovered': fields_str})

	# Save output to file
	with open(self.output_path, 'w') as f:
		json.dump(results, f, indent=4)

	logger.info('Finished running naabu port scan.')

	# Process nmap results: 1 process per host
	if nmap_enabled:
		logger.warning(f'Starting nmap scans ...')
		logger.warning(ports_data)
		for host, port_list in ports_data.items():
			ports_str = '_'.join([str(p) for p in port_list])
			ctx_nmap = ctx.copy()
			ctx_nmap['description'] = get_task_title(f'nmap_{host}', self.scan_id, self.subscan_id)
			ctx_nmap['track'] = False
			ctx_nmap['activity_id'] = self.activity_id
			sig = nmap.si(
				cmd=nmap_cmd,
				ports=port_list,
				host=host,
				script=nmap_script,
				script_args=nmap_script_args,
				max_rate=rate_limit,
				ctx=ctx_nmap)
			logger.warning(f"APME: Running nmap task synchronously for {host} in port_scan to prevent Celery starvation/join deadlocks.")
			sig.apply()

	return ports_data


@app.task(name='nmap', queue='main_scan_queue', base=RengineTask, bind=True)
def nmap(
		self,
		cmd=None,
		ports=[],
		host=None,
		input_file=None,
		script=None,
		script_args=None,
		max_rate=None,
		ctx={},
		description=None):
	"""Run nmap on a host.

	Args:
		cmd (str, optional): Existing nmap command to complete.
		ports (list, optional): List of ports to scan.
		host (str, optional): Host to scan.
		input_file (str, optional): Input hosts file.
		script (str, optional): NSE script to run.
		script_args (str, optional): NSE script args.
		max_rate (int): Max rate.
		description (str, optional): Task description shown in UI.
	"""
	notif = Notification.objects.first()
	# Deduplicate ports
	ports = list(dict.fromkeys(ports))
	ports_str = ','.join(str(port) for port in ports)
	self.filename = self.filename.replace('.txt', '.xml')
	filename_vulns = self.filename.replace('.xml', '_vulns.json')
	output_file = self.output_path
	output_file_xml = f'{self.results_dir}/{host}_{self.filename}'
	vulns_file = f'{self.results_dir}/{host}_{filename_vulns}'
	# Build cmd
	nmap_cmd = get_nmap_cmd(
		cmd=cmd,
		ports=ports_str,
		script=script,
		script_args=script_args,
		max_rate=max_rate,
		host=host,
		input_file=input_file,
		output_file=output_file_xml)
	
	if not nmap_cmd:
		logger.error('Could not build nmap command')
		return

	# Apply OpSec stealth
	proxy = get_random_proxy()
	opsec = OpSecManager()
	nmap_cmd = opsec.apply_stealth('nmap', nmap_cmd, proxy=proxy)

	# Run cmd
	run_command(
		nmap_cmd,
		shell=True,
		history_file=self.history_file,
		scan_id=self.scan_id,
		activity_id=self.activity_id)

	# Get nmap XML results and convert to JSON
	nmap_results = parse_nmap_results(output_file_xml, output_file)
	vulns = nmap_results['vulns']
	discovered_services = nmap_results['services']
	
	with open(vulns_file, 'w') as f:
		json.dump(vulns, f, indent=4)

	# Save vulnerabilities found by nmap
	vulns_str = ''
	for vuln_data in vulns:
		# URL is not necessarily an HTTP URL when running nmap (can be any
		# other vulnerable protocols). Look for existing endpoint and use its
		# URL as vulnerability.http_url if it exists.
		url = vuln_data['http_url']
		endpoint = EndPoint.objects.filter(http_url__contains=url).first()
		if endpoint:
			vuln_data['http_url'] = endpoint.http_url
		vuln, created = save_vulnerability(
			target_domain=self.domain,
			subdomain=self.subdomain,
			scan_history=self.scan,
			subscan=self.subscan,
			endpoint=endpoint,
			**vuln_data)
		vulns_str += f'• {str(vuln)}\n'
		if created:
			logger.warning(str(vuln))
		
		# Register Auth Candidates from vulnerability tags (like auth_portal)
		if 'auth_portal' in (vuln_data.get('tags') or []):
			from reNgine.utilities import save_auth_candidate
			# Parse port safely from http_url
			url_str = vuln_data.get('http_url') or ''
			parsed_port = 80
			if url_str:
				try:
					from urllib.parse import urlparse
					parsed_url = urlparse(url_str)
					if parsed_url.port:
						parsed_port = parsed_url.port
					else:
						parsed_port = 443 if parsed_url.scheme == 'https' else 80
				except Exception:
					try:
						port_part = url_str.split(':')[-1]
						if port_part.isdigit():
							parsed_port = int(port_part)
					except Exception:
						pass
			save_auth_candidate(
				scan_history=self.scan,
				target=vuln_data['http_url'],
				protocol='http',
				port=parsed_port,
				source_tool='Nmap NSE',
				metadata={'tags': vuln_data.get('tags') or [], 'nse_script': vuln_data.get('name')},
				subdomain=self.subdomain,
				endpoint=endpoint
			)

	# Register Auth Candidates from discovered services (SMB, RDP, etc.)
	interesting_protocols = {
		'microsoft-ds': 'smb',
		'smb': 'smb',
		'ms-wbt-server': 'rdp',
		'rdp': 'rdp',
		'ssh': 'ssh',
		'ftp': 'ftp',
		'telnet': 'telnet'
	}
	
	from reNgine.utilities import save_auth_candidate
	for svc in discovered_services:
		proto = interesting_protocols.get(svc['service'])
		if proto:
			save_auth_candidate(
				scan_history=self.scan,
				target=svc['target'],
				protocol=proto,
				port=svc['port'],
				source_tool='Nmap Service Discovery',
				metadata={'banner': svc['banner']},
				subdomain=self.subdomain
			)

	# Send only 1 notif for all vulns to reduce number of notifs
	#if len(vulns) > 0:
	self.notify(
		severity=0,
		fields={'Vulnerabilities discovered': vulns_str},
		add_meta_info=False)

	# Automatic Trigger for Brute Force Scan (Legacy Support for chaining)
	auth_targets = []
	for v in vulns:
		if 'auth_portal' in (v.get('tags') or []):
			auth_targets.append(v['http_url'])
	
	if auth_targets and self.scan.tasks and 'brute_force_scan' in self.scan.tasks:
		logger.warning(f'Detected Auth Portals on {host}. Triggering Brute Force Scan...')
		# We use delay to run it asynchronously
		from reNgine.tasks import brute_force_scan
		brute_force_scan.delay(targets=list(set(auth_targets)), ctx=ctx)

	return vulns


@app.task(name='waf_detection', queue='main_scan_queue', base=RengineTask, bind=True)
def waf_detection(self, ctx={}, description=None):
	"""
	Uses wafw00f to check for the presence of a WAF.

	Args:
		description (str, optional): Task description shown in UI.

	Returns:
		list: List of startScan.models.Waf objects.
	"""
	input_path = f'{self.results_dir}/input_endpoints_waf_detection.txt'
	config = self.yaml_configuration.get(WAF_DETECTION) or {}
	enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)

	# Get alive endpoints from DB
	get_http_urls(
		is_alive=enable_http_crawl,
		write_filepath=input_path,
		get_only_default_urls=True,
		ctx=ctx
	)

	cmd = f'wafw00f -i {input_path} -o {self.output_path}'
	logger.info(f'Running WAFW00F on {input_path}')
	run_command(
		cmd,
		history_file=self.history_file,
		scan_id=self.scan_id,
		activity_id=self.activity_id)
	if not os.path.isfile(self.output_path):
		logger.error(f'Could not find {self.output_path}')
		return

	with open(self.output_path) as file:
		wafs = file.readlines()

	for line in wafs:
		line = " ".join(line.split())
		splitted = line.split(' ', 1)
		waf_info = splitted[1].strip()
		waf_name = waf_info[:waf_info.find('(')].strip()
		waf_manufacturer = waf_info[waf_info.find('(')+1:waf_info.find(')')].strip().replace('.', '')
		http_url = sanitize_url(splitted[0].strip())
		if not waf_name or waf_name == 'None':
			continue

		# Add waf to db
		waf, _ = Waf.objects.get_or_create(
			name=waf_name,
			manufacturer=waf_manufacturer
		)

		# Add waf info to Subdomain in DB
		subdomain = get_subdomain_from_url(http_url)
		logger.info(f'Wafw00f Subdomain : {subdomain}')
		subdomain_query, _ = Subdomain.objects.get_or_create(scan_history=self.scan, name=subdomain)
		subdomain_query.waf.add(waf)
		subdomain_query.save()

		# Phase 2: Origin Discovery
		# If WAF is detected and Origin Discovery is enabled (implied by WAF detection in this context)
		# We check engine config for origin discovery specific settings
		waf_config = config or {}
		use_shodan = waf_config.get('use_shodan', True)
		use_censys = waf_config.get('use_censys', True)
		
		logger.info(f"Starting Origin Discovery for {subdomain}")
		origin_manager = OriginDiscoveryManager(subdomain_query)
		origin_ips = origin_manager.find_origin(
			use_shodan=use_shodan,
			use_censys=use_censys
		)
		
		if origin_ips:
			# Store the first one as primary origin_ip
			primary_origin = origin_ips[0]
			subdomain_query.origin_ip = primary_origin
			subdomain_query.save()
			
			# Ensure this IP is stored and geolocated
			save_ip_address(
				primary_origin,
				subdomain=subdomain_query,
				subscan=self.subscan,
				scan_id=self.scan_id,
				activity_id=self.activity_id
			)
			logger.info(f"Origin IP found for {subdomain}: {primary_origin}")

	return wafs


@app.task(name='waf_bypass', queue='main_scan_queue', base=RengineTask, bind=True)
def waf_bypass(self, ctx={}, description=None):
	"""
	Tests various WAF bypass techniques.
	"""
	if 'waf_bypass' not in self.scan.tasks:
		return

	config = self.yaml_configuration.get('waf_bypass') or {}
	use_nuclei = config.get('use_nuclei', True)
	use_benchmarking = config.get('use_benchmarking', True)

	# Get all subdomains with WAFs in this scan
	subdomains = Subdomain.objects.filter(scan_history=self.scan).exclude(waf=None)
	
	for subdomain in subdomains:
		logger.info(f"Starting WAF Bypass tests for {subdomain.name}")
		orchestrator = WafBypassOrchestrator(subdomain)
		findings = orchestrator.run_all_tests(
			use_nuclei=use_nuclei,
			use_benchmarking=use_benchmarking
		)
		
		if findings:
			logger.info(f"Found {len(findings)} potential WAF bypasses for {subdomain.name}")
	
	return True


# dir_file_fuzz has been refactored to fuzzing_tasks.py


@app.task(name='fetch_url', queue='main_scan_queue', base=RengineTask, bind=True)
def fetch_url(self, urls=[], ctx={}, description=None):
	"""Fetch URLs using different tools like gauplus, gau, gospider, waybackurls ...

	Args:
		urls (list): List of URLs to start from.
		description (str, optional): Task description shown in UI.
	"""
	input_path = f'{self.results_dir}/input_endpoints_fetch_url.txt'

	# Config
	config = self.yaml_configuration.get(FETCH_URL) or {}
	should_remove_duplicate_endpoints = config.get(REMOVE_DUPLICATE_ENDPOINTS, True)
	duplicate_removal_fields = config.get(DUPLICATE_REMOVAL_FIELDS, ENDPOINT_SCAN_DEFAULT_DUPLICATE_FIELDS)
	enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
	gf_patterns = config.get(GF_PATTERNS, DEFAULT_GF_PATTERNS)
	ignore_file_extension = config.get(IGNORE_FILE_EXTENSION, DEFAULT_IGNORE_FILE_EXTENSIONS)
	tools = config.get(USES_TOOLS, ENDPOINT_SCAN_DEFAULT_TOOLS)
	threads = config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	# domain_request_headers = self.domain.request_headers if self.domain else None
	custom_headers = self.yaml_configuration.get(CUSTOM_HEADERS, [])
	'''
	# TODO: Remove custom_header in next major release
		support for custom_header will be remove in next major release, 
		as of now it will be supported for backward compatibility
		only custom_headers will be supported
	'''
	custom_header = self.yaml_configuration.get(CUSTOM_HEADER)
	if custom_header:
		custom_headers.append(custom_header)
	exclude_subdomains = config.get(EXCLUDED_SUBDOMAINS, False)

	# Get URLs to scan and save to input file
	if urls:
		with open(input_path, 'w') as f:
			f.write('\n'.join(urls))
	else:
		urls = get_http_urls(
			is_alive=enable_http_crawl,
			write_filepath=input_path,
			exclude_subdomains=exclude_subdomains,
			get_only_default_urls=True,
			ctx=ctx
		)

	# Domain regex
	host = self.domain.name if self.domain else urlparse(urls[0]).netloc
	host_regex = f"\'https?://([a-zA-Z0-9_-]+[.])*{host}.*\'"

	# Tools cmds
	base_cmd_map = {
		'gau': f'gau',
		'hakrawler': 'hakrawler -subs -u',
		'waybackurls': 'waybackurls',
		'gospider': f'gospider -S {input_path} --js -d 2 --sitemap --robots -w -r',
		'katana': f'katana -list {input_path} -silent -jc -kf all -d 3 -fs rdn',
	}

	recon_run = False
	for tool in tools:
		if tool in base_cmd_map:
			p = get_random_proxy()
			tool_cmd = base_cmd_map[tool]
			
			# Apply proxy
			if p:
				if tool == 'katana': tool_cmd += f' -proxy "{p}"'
				#elif tool == 'gospider': tool_cmd += f' -p {p}'
				#elif tool == 'hakrawler': tool_cmd += f' -proxy {p}'
				#elif tool == 'katana': tool_cmd += f' -proxy {p}'
			
			# Apply threads
			if threads > 0:
				if tool == 'gau': tool_cmd += f' --threads {threads}'
				elif tool == 'gospider': tool_cmd += f' -t {threads}'
				elif tool == 'katana': tool_cmd += f' -c {threads}'

			# Apply custom headers
			if custom_headers:
				formatted_headers = ' '.join(f'-H "{header}"' for header in custom_headers)
				if tool == 'gospider': tool_cmd += formatted_headers
				elif tool == 'hakrawler': tool_cmd += ';;'.join(header for header in custom_headers)
				elif tool == 'katana': tool_cmd += formatted_headers

			full_cmd = f'cat {input_path} | {tool_cmd} | grep -Eo {host_regex} | tee {self.results_dir}/urls_{tool}.txt'
			logger.info(f'Running {tool}')
			logger.warning(f'{tool} command: {full_cmd}')
			run_command(
				full_cmd,
				shell=True,
				scan_id=self.scan_id,
				activity_id=self.activity_id
			)
			recon_run = True
	
	if not recon_run:
		logger.warning('No reconnaissance tools enabled for fetch_url. Skipping.')
		return

	# Cleanup task
	sort_output = [
		f'cat {self.results_dir}/urls_* > {self.output_path}',
		f'cat {input_path} >> {self.output_path}',
		f'sort -u {self.output_path} -o {self.output_path}',
	]
	if ignore_file_extension:
		ignore_exts = '|'.join(ignore_file_extension)
		grep_ext_filtered_output = [
			f'cat {self.output_path} | grep -Eiv "\\.({ignore_exts}).*" > {self.results_dir}/urls_filtered.txt',
			f'mv {self.results_dir}/urls_filtered.txt {self.output_path}'
		]
		sort_output.extend(grep_ext_filtered_output)

	for cmd in sort_output:
		run_command(
			cmd,
			shell=True,
			scan_id=self.scan_id,
			activity_id=self.activity_id
		)

	# Store all the endpoints and run httpx
	with open(self.output_path) as f:
		discovered_urls = f.readlines()
		self.notify(fields={'Discovered URLs': len(discovered_urls)})

	# Some tools can have an URL in the format <URL>] - <PATH> or <URL> - <PATH>, add them
	# to the final URL list
	all_urls = []
	for url in discovered_urls:
		url = url.strip()
		urlpath = None
		base_url = None
		if '] ' in url: # found JS scraped endpoint e.g from gospider
			split = tuple(url.split('] '))
			if not len(split) == 2:
				logger.warning(f'URL format not recognized for "{url}". Skipping.')
				continue
			base_url, urlpath = split
			urlpath = urlpath.lstrip('- ')
		elif ' - ' in url: # found JS scraped endpoint e.g from gospider
			base_url, urlpath = tuple(url.split(' - '))

		if base_url and urlpath:
			subdomain = urlparse(base_url)
			url = f'{subdomain.scheme}://{subdomain.netloc}{self.starting_point_path}'

		if not validators.url(url):
			logger.warning(f'Invalid URL "{url}". Skipping.')

		if url not in all_urls:
			all_urls.append(url)

	# Filter out URLs if a path filter was passed
	if self.starting_point_path:
		all_urls = [url for url in all_urls if self.starting_point_path in url]

	# if exclude_paths is found, then remove urls matching those paths
	if self.excluded_paths:
		all_urls = exclude_urls_by_patterns(self.excluded_paths, all_urls)

	# Write result to output path
	with open(self.output_path, 'w') as f:
		f.write('\n'.join(all_urls))
	logger.warning(f'Found {len(all_urls)} usable URLs')

	# Save discovered URLs immediately to database as skeleton endpoints.
	# Crawling is delegated to the next stage in the pipeline to avoid collisions.
	for url in all_urls:
		http_url = sanitize_url(url)
		subdomain_name = get_subdomain_from_url(http_url)
		subdomain, _ = save_subdomain(subdomain_name, ctx=ctx)
		if not isinstance(subdomain, Subdomain):
			continue
		save_endpoint(
			http_url,
			ctx=ctx,
			subdomain=subdomain
		)



	#-------------------#
	# GF PATTERNS MATCH #
	#-------------------#

	# Combine old gf patterns with new ones
	if gf_patterns:
		self.scan.used_gf_patterns = ','.join(gf_patterns)
		self.scan.save()

	# Run gf patterns on saved endpoints
	# TODO: refactor to Celery task
	for gf_pattern in gf_patterns:
		# TODO: js var is causing issues, removing for now
		if gf_pattern == 'jsvar':
			logger.info('Ignoring jsvar as it is causing issues.')
			continue

		# Run gf on current pattern
		logger.warning(f'Running gf on pattern "{gf_pattern}"')
		gf_output_file = f'{self.results_dir}/gf_patterns_{gf_pattern}.txt'
		cmd = f'cat {self.output_path} | gf {gf_pattern} | grep -Eo {host_regex} | tee -a {gf_output_file}'
		run_command(
			cmd,
			shell=True,
			history_file=self.history_file,
			scan_id=self.scan_id,
			activity_id=self.activity_id)

		# Check output file
		if not os.path.exists(gf_output_file):
			logger.error(f'Could not find GF output file {gf_output_file}. Skipping GF pattern "{gf_pattern}"')
			continue

		# Read output file line by line and
		with open(gf_output_file, 'r') as f:
			lines = f.readlines()

		# Add endpoints / subdomains to DB
		for url in lines:
			http_url = sanitize_url(url)
			subdomain_name = get_subdomain_from_url(http_url)
			subdomain, _ = save_subdomain(subdomain_name, ctx=ctx)
			if not subdomain:
				continue
			endpoint, created = save_endpoint(
				http_url,
				crawl=False,
				subdomain=subdomain,
				ctx=ctx)
			if not endpoint:
				continue
			earlier_pattern = None
			if not created:
				earlier_pattern = endpoint.matched_gf_patterns
			pattern = f'{earlier_pattern},{gf_pattern}' if earlier_pattern else gf_pattern
			endpoint.matched_gf_patterns = pattern
			endpoint.save()

	return all_urls


def parse_curl_output(response):
	# TODO: Enrich from other cURL fields.
	CURL_REGEX_HTTP_STATUS = f'HTTP\/(?:(?:\d\.?)+)\s(\d+)\s(?:\w+)'
	http_status = 0
	if response:
		failed = False
		regex = re.compile(CURL_REGEX_HTTP_STATUS, re.MULTILINE)
		try:
			http_status = int(regex.findall(response)[0])
		except (KeyError, TypeError, IndexError):
			pass
	return {
		'http_status': http_status,
	}



@app.task(name='web_api_discovery', queue='main_scan_queue', base=RengineTask, bind=True)
def web_api_discovery(self, urls=[], ctx={}, description=None):
	"""Advanced Web App & API Discovery using Kiterunner, Arjun, LinkFinder, etc."""
	logger.info('Running Web API Discovery Task')
	config = self.yaml_configuration.get(WEB_API_DISCOVERY) or {}
	uses_tools = ctx.get('api_discovery_tools') or config.get(USES_TOOLS, ['kiterunner', 'arjun', 'linkfinder', 'paramspider', 'aquatone', 'semgrep'])
	kr_wordlist = ctx.get('kr_wordlist') or config.get(KITERUNNER_WORDLIST, 'routes-large.kite')
	scan_only_active = config.get(SCAN_ONLY_ACTIVE, True)
	threads = config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	arjun_methods = config.get(ARJUN_METHODS, ARJUN_DEFAULT_METHODS)
	proxy = None

	# Get targets
	if not urls:
		urls = get_http_urls(
			is_alive=scan_only_active,
			write_filepath=None,
			ctx=ctx
		)

	if not urls:
		logger.warning('No targets found for Web API Discovery. Skipping.')
		return


	results_dir = f"{self.results_dir}/web_api_discovery"
	os.makedirs(results_dir, exist_ok=True)

	processed_paramspider_subdomains = set()
	processed_url_patterns = set()
	for url in urls:
		# URL Pattern Normalization to skip redundant endpoints (e.g. locale=ar vs locale=cs)
		parsed = urlparse(url)
		query_keys = sorted(parse_qs(parsed.query).keys())
		url_pattern = f"{parsed.netloc}{parsed.path}?{'&'.join(query_keys)}"
		
		if url_pattern in processed_url_patterns:
			continue
		processed_url_patterns.add(url_pattern)

		subdomain_name = get_subdomain_from_url(url)
		subdomain = Subdomain.objects.filter(name=subdomain_name, scan_history=self.scan).first()
		if not subdomain:
			continue

		# Arjun - Parameter discovery
		if 'arjun' in uses_tools:
			logger.info(f'Running Arjun on {url}')
			arjun_output = f"{results_dir}/arjun_{subdomain_name}.json"
			cmd = f"arjun -u {url} --passive -m {arjun_methods} -t {threads} -oJ {arjun_output}"
			#proxy = get_random_proxy()
			#if proxy:
			#	cmd = f"export HTTP_PROXY='{proxy}' HTTPS_PROXY='{proxy}' && {cmd}"
			run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id) #, proxy=proxy)
			if os.path.exists(arjun_output):
				try:
					with open(arjun_output, 'r') as f:
						data = json.load(f)
						for target_url, details in data.items():
							endpoint, _ = save_endpoint(target_url, ctx=ctx, subdomain=subdomain)
							if endpoint:
								params = details.get('params', {})
								if isinstance(params, dict):
									for method, param_list in params.items():
										for p in param_list:
											save_parameter(endpoint, p, param_type=method)
								elif isinstance(params, list):
									method = details.get('method', 'unknown')
									for p in params:
										save_parameter(endpoint, p, param_type=method)
				except Exception as e:
					logger.error(f"Error parsing Arjun output for {url}: {e}")

		# Kiterunner - API/Route discovery
		if 'kiterunner' in uses_tools:
			logger.info(f'Running Kiterunner on {url}')
			kr_output = f"{results_dir}/kr_{subdomain_name}.json"
			cmd = f"kr scan {url} -w /usr/src/wordlist/kr/{kr_wordlist} -j {threads} -o json | tee -a {kr_output}"
			#proxy = get_random_proxy()
			#if proxy:
			#	cmd = f"export HTTP_PROXY='{proxy}' HTTPS_PROXY='{proxy}' && {cmd}"
			logger.warning(f'Running Kiterunner command: {cmd}')
			run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id) #, proxy=proxy)
			if os.path.exists(kr_output):
				try:
					with open(kr_output, 'r') as f:
						for line in f:
							if not line.strip(): continue
							entry = json.loads(line)
							found_path = entry.get('path', '')
							if found_path:
								parsed = urlparse(url)
								full_url = f"{parsed.scheme}://{parsed.netloc}{found_path}"
								endpoint, _ = save_endpoint(full_url, ctx=ctx, subdomain=subdomain, http_status=entry.get('status'))
								# Extract parameters from Kiterunner path if any
								if '?' in full_url:
									params = extract_params_from_url(full_url)
									logger.warning(f'Found params: {params}')
									for p in params:
										save_parameter(endpoint, p['name'], param_type='Kiterunner', value=p['value'])
				except Exception as e:
					logger.error(f"Error parsing Kiterunner output for {url}: {e}")

		# ParamSpider
		if 'paramspider' in uses_tools and subdomain_name not in processed_paramspider_subdomains:
			logger.info(f'Running ParamSpider on {subdomain_name}')
			processed_paramspider_subdomains.add(subdomain_name)
			ps_output = f"{results_dir}/ps_{subdomain_name}.txt"
			cmd = f"paramspider --domain {subdomain_name} | tee {ps_output}"
			proxy = get_random_proxy()
			if proxy:
				cmd = f"paramspider --domain {subdomain_name} --proxy {proxy} | tee {ps_output}"
			logger.warning(f'Running ParamSpider command: {cmd}')
			run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id, proxy=proxy)
			if os.path.exists(ps_output):
				try:
					with open(ps_output, 'r') as f:
						for line in f:
							line = line.strip()
							if line and is_valid_url(line):
								endpoint, _ = save_endpoint(line, ctx=ctx, subdomain=subdomain)
								parsed = urlparse(line)
								if parsed.query:
									for q in parsed.query.split('&'):
										if '=' in q:
											p_name = q.split('=')[0]
											logger.warning(f'Found param: {p_name} in {line}')
											save_parameter(endpoint, p_name, param_type='URL Query')
				except Exception as e:
					logger.error(f"Error parsing ParamSpider output for {subdomain_name}: {e}")

		# LinkFinder
		if 'linkfinder' in uses_tools:
			logger.info(f'Running LinkFinder on {url}')
			lf_output = f"{results_dir}/lf_{subdomain_name}.txt"
			cmd = f"python3 /usr/src/github/LinkFinder/linkfinder.py -i {url} -o cli | tee {lf_output}"
			#proxy = get_random_proxy()
			#if proxy:
			#	cmd = f"export HTTP_PROXY='{proxy}' HTTPS_PROXY='{proxy}' && {cmd}"
			logger.warning(f'Running LinkFinder command: {cmd}')
			run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id) #, proxy=proxy)
			if os.path.exists(lf_output):
				try:
					with open(lf_output, 'r') as f:
						for line in f:
							line = line.strip()
							if line.startswith('/') or line.startswith('http'):
								if line.startswith('/'):
									parsed = urlparse(url)
									full_url = f"{parsed.scheme}://{parsed.netloc}{line}"
								else:
									full_url = line
								endpoint, _ = save_endpoint(full_url, ctx=ctx, subdomain=subdomain)
								# Extract parameters from LinkFinder findings
								if '?' in full_url:
									params = extract_params_from_url(full_url)
									for p in params:
										logger.warning(f'Found param: {p["name"]} in {full_url}')
										save_parameter(endpoint, p['name'], param_type='LinkFinder', value=p['value'])
				except Exception as e:
					logger.error(f"Error parsing LinkFinder output for {url}: {e}")

		# InQL - GraphQL Discovery
		if 'inql' in uses_tools:
			logger.info(f'Running InQL on {url}')
			inql_output = f"{results_dir}/inql_{subdomain_name}"
			cmd = f"inql -t {url} -o {inql_output}"
			proxy = get_random_proxy()
			if proxy:
				cmd += f" -p {proxy}"
			run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id, proxy=proxy)
			# Parse InQL results
			if os.path.exists(inql_output):
				try:
					inql_findings = parse_inql_results(inql_output)
					for finding in inql_findings:
						# InQL doesn't always give the full URL, but we know the base URL
						# We can register the discovery of GraphQL
						save_endpoint(url, ctx=ctx, subdomain=subdomain, source='InQL (GraphQL Found)')
				except Exception as e:
					logger.error(f"Error parsing InQL results for {url}: {e}")

	# Semgrep - Post-discovery pattern matching
	if 'semgrep' in uses_tools:
		logger.info(f'Running Semgrep on discovery results')
		semgrep_output = f"{results_dir}/semgrep_results.json"
		cmd = f"semgrep scan --config auto --json --output {semgrep_output} {results_dir}"
		logger.warning(f'Running Semgrep command: {cmd}')
		run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id)
		# Parse Semgrep results
		if os.path.exists(semgrep_output):
			with open(semgrep_output, 'r') as f:
				data = json.load(f)
				for match in data.get('results', []):
					vuln_data = parse_semgrep_result(match)
					logger.warning(f'Found potential vulnerability: {vuln_data}')
					save_vulnerability(vuln_data, self.scan, self.domain)

	# Retire.js - JS Library vulnerability scan
	if 'retire' in uses_tools:
		logger.info(f'Running Retire.js on discovery results')
		retire_output = f"{results_dir}/retire_results.json"
		cmd = f"npx -y retire --path {results_dir} --outputformat json --outputpath {retire_output}"
		logger.warning(f'Running Retire.js command: {cmd}')
		run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id)
		if os.path.exists(retire_output):
			with open(retire_output, 'r') as f:
				data = json.load(f)
				
				# Retire.js results can be either a list of file results or a dictionary wrapper
				results_list = []
				if isinstance(data, list):
					results_list = data
				elif isinstance(data, dict):
					# Check standard Retire.js dictionary output keys
					if 'data' in data and isinstance(data['data'], list):
						results_list = data['data']
					elif 'results' in data and isinstance(data['results'], list):
						results_list = data['results']
					else:
						results_list = [data]
						
				for result in results_list:
					if not isinstance(result, dict):
						continue
					for component in result.get('results', []):
						if not isinstance(component, dict):
							continue
						for vuln in component.get('vulnerabilities', []):
							if not isinstance(vuln, dict):
								continue
							vuln_data = parse_retire_result({
								'component': component.get('component'),
								'version': component.get('version'),
								'info': vuln.get('info'),
								'file': result.get('file')
							})
							logger.warning(f'Found potential vulnerability: {vuln_data}')
							save_vulnerability(vuln_data, self.scan, self.domain)

	# Aquatone - Visual discovery
	if 'aquatone' in uses_tools:
		logger.info('Running Aquatone on discovery results')
		aquatone_dir = f"{results_dir}/aquatone"
		os.makedirs(aquatone_dir, exist_ok=True)
		urls_file = f"{results_dir}/all_discovery_urls.txt"
		# Get all endpoints discovered so far for this scan
		all_endpoints = EndPoint.objects.filter(subdomain__scan_history=self.scan)
		with open(urls_file, 'w') as f:
			for ep in all_endpoints:
				f.write(f"{ep.http_url}\n")
		
		cmd = f"cat {urls_file} | aquatone -out {aquatone_dir} -chrome-path /usr/bin/chromium" # -silent"
		# Get a fresh random proxy specifically for Aquatone to avoid stale leaked loop variables
		aquatone_proxy = get_random_proxy()
		if aquatone_proxy:
			cmd += f" -proxy {aquatone_proxy}"
		logger.warning(f'Running Aquatone command: {cmd}')
		run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id)

		# Parse Aquatone results and link to database
		aquatone_session = f"{aquatone_dir}/aquatone_session.json"
		if os.path.exists(aquatone_session):
			try:
				from startScan.models import Screenshot
				with open(aquatone_session, 'r') as f:
					data = json.load(f)
					# Aquatone session data contains 'pages' key
					pages = data.get('pages', {})
					for page_id, page_data in pages.items():
						page_url = page_data.get('url')
						if not page_url: continue
						
						subdomain_name = get_subdomain_from_url(page_url)
						subdomain = Subdomain.objects.filter(name=subdomain_name, scan_history=self.scan).first()
						if not subdomain: continue
						
						# Save to Screenshot model
						screenshot_file = f"aquatone/screenshots/{page_id}.png"
						html_file = f"aquatone/html/{page_id}.html"
						logger.warning(f'Aquatone artifacts saved to {html_file}')
						Screenshot.objects.get_or_create(
							subdomain=subdomain,
							scan_history=self.scan,
							url=page_url,
							defaults={
								'title': page_data.get('title'),
								'status_code': page_data.get('status_code'),
								'screenshot_path': screenshot_file,
								'html_path': html_file,
								'technologies': page_data.get('tags', []), # Aquatone uses tags for tech
							}
						)
						# Also update the subdomain's screenshot_path if not set
						if not subdomain.screenshot_path:
							subdomain.screenshot_path = screenshot_file
							subdomain.save()
							
			except Exception as e:
				logger.error(f"Error parsing Aquatone session for {self.scan}: {e}")


	# Sync to Graph
	if Neo4jManager:
		nm = Neo4jManager()
		nm.sync_scan_results(self.scan_id)
		nm.close()

	# Trigger Intelligent Auth Candidate Extraction
	from reNgine.auth_discovery_tasks import extract_auth_candidates
	extract_auth_candidates.apply(kwargs={'ctx': ctx})


@app.task(name='vulnerability_scan', queue='main_scan_queue', bind=True, base=RengineTask)
def vulnerability_scan(self, urls=[], ctx={}, description=None):
	"""This task serves as the entrypoint for vulnerability scans, spawning all enabled scanners.

	Args:
		urls (list): Target URLs to scan.
		ctx (dict): Scan context.
		description (str): Task description.
	"""
	logger.info('Running Vulnerability Scan Queue')
	config = self.yaml_configuration
	
	from celery.result import allow_join_result
	from celery import group

	# Stage 1: Primary vulnerability scans (rengine-ng compatible: Nuclei, CRLFuzz, Dalfox, S3Scanner)
	primary_tasks = resolve_primary_vulnerability_tasks(config, urls, ctx)
	if primary_tasks:
		logger.info(f"Starting {len(primary_tasks)} primary vulnerability scan tasks (Stage 1)")
		primary_group = group(primary_tasks)
		primary_job = primary_group.apply_async()
		
		# Block synchronous worker execution until Stage 1 completes to prevent premature flow progression
		with allow_join_result():
			primary_job.get()
		logger.info("Primary vulnerability scan tasks (Stage 1) completed.")
	else:
		logger.info("No primary vulnerability scan tasks to run for Stage 1.")

	# Stage 2: Additional vulnerability scans (r3ngine-specific: Acunetix, cPanel, WPScan, React2Shell, Semgrep)
	additional_tasks = resolve_additional_vulnerability_tasks(config, urls, ctx)
	if additional_tasks:
		logger.info(f"Starting {len(additional_tasks)} additional vulnerability scan tasks (Stage 2)")
		additional_group = group(additional_tasks)
		additional_job = additional_group.apply_async()
		
		# Block synchronous worker execution until Stage 2 completes to prevent premature flow progression
		with allow_join_result():
			additional_job.get()
		logger.info("Additional vulnerability scan tasks (Stage 2) completed.")
	else:
		logger.info("No additional vulnerability scan tasks to run for Stage 2.")

	logger.info('Vulnerability scan completed...')
	return None

@app.task(name='nuclei_individual_severity_module', queue='main_scan_queue', base=RengineTask, bind=True)
def nuclei_individual_severity_module(self, cmd, severity, enable_http_crawl, should_fetch_gpt_report, ctx={}, description=None):
	'''
		This celery task will run vulnerability scan for a specific severity.
		All severities run sequentially to optimize resource utilization and prevent worker crashes.
	'''
	results = []
	logger.info(f'Running vulnerability scan with severity: {severity}')
	cmd += f' -severity {severity}'
	proxy = get_random_proxy()
	if proxy:
		if not any(proxy.startswith(s) for s in ['http://', 'https://', 'socks4://', 'socks5://']):
			proxy = 'http://' + proxy
		cmd += f' -proxy {proxy}'
	# Send start notification
	notif = Notification.objects.first()
	send_status = notif.send_scan_status_notif if notif else False

	for line in stream_command(
			cmd,
			history_file=self.history_file,
			scan_id=self.scan_id,
			activity_id=self.activity_id):

		if not isinstance(line, dict):
			continue

		results.append(line)

		# Gather nuclei results
		vuln_data = parse_nuclei_result(line)

		# Get corresponding subdomain
		http_url = sanitize_url(line.get('matched-at'))
		subdomain_name = get_subdomain_from_url(http_url)

		# TODO: this should be get only
		subdomain, _ = Subdomain.objects.get_or_create(
			name=subdomain_name,
			scan_history=self.scan,
			target_domain=self.domain
		)

		# Look for duplicate vulnerabilities by excluding records that might change but are irrelevant.
		object_comparison_exclude = ['response', 'curl_command', 'tags', 'references', 'cve_ids', 'cwe_ids']

		# Add subdomain and target domain to the duplicate check
		vuln_data_copy = vuln_data.copy()
		vuln_data_copy['subdomain'] = subdomain
		vuln_data_copy['target_domain'] = self.domain

		# Check if record exists, if exists do not save it
		if record_exists(Vulnerability, data=vuln_data_copy, exclude_keys=object_comparison_exclude):
			logger.warning(f'Nuclei vulnerability of severity {severity} : {vuln_data_copy["name"]} for {subdomain_name} already exists')
			continue

		# Get or create EndPoint object
		response = line.get('response')
		httpx_crawl = False if response else enable_http_crawl # avoid yet another httpx crawl
		endpoint, _ = save_endpoint(
			http_url,
			crawl=httpx_crawl,
			subdomain=subdomain,
			ctx=ctx)
		if endpoint:
			http_url = endpoint.http_url
			if not httpx_crawl:
				output = parse_curl_output(response)
				endpoint.http_status = output['http_status']
				endpoint.save()

		# Register Auth Candidate if Nuclei flagged it as login or auth
		tags = line.get('info', {}).get('tags', []) or []
		if any(tag in tags for tag in ['login', 'auth', 'admin', 'default-login', 'bruteforce', 'panel']):
			from reNgine.utilities import save_auth_candidate
			save_auth_candidate(
				scan_history=self.scan,
				target=http_url,
				protocol='http',
				port=int(urlparse(http_url).port or (443 if 'https' in http_url else 80)),
				source_tool='Nuclei',
				metadata={'tags': tags, 'template_id': line.get('template-id')},
				subdomain=subdomain,
				endpoint=endpoint
			)

		# Get or create Vulnerability object
		vuln, _ = save_vulnerability(
			target_domain=self.domain,
			http_url=http_url,
			scan_history=self.scan,
			subscan=self.subscan,
			subdomain=subdomain,
			**vuln_data)
		if not vuln:
			continue

		# Print vuln
		severity = line['info'].get('severity', 'unknown')
		logger.warning(str(vuln))


		# Send notification for all vulnerabilities except info
		url = vuln.http_url or vuln.subdomain
		send_vuln = (
			notif and
			notif.send_vuln_notif and
			vuln and
			severity in ['low', 'medium', 'high', 'critical'])
		if send_vuln:
			fields = {
				'Severity': f'**{severity.upper()}**',
				'URL': http_url,
				'Subdomain': subdomain_name,
				'Name': vuln.name,
				'Type': vuln.type,
				'Description': vuln.description,
				'Template': vuln.template_url,
				'Tags': vuln.get_tags_str() or "N/A",
				'CVEs': vuln.get_cve_str(),
				'CWEs': vuln.get_cwe_str(),
				'References': vuln.get_refs_str()
			}
			severity_map = {
				'low': 'info',
				'medium': 'warning',
				'high': 'error',
				'critical': 'error'
			}
			self.notify(
				f'vulnerability_scan_#{vuln.id}',
				severity_map[severity],
				fields,
				add_meta_info=False)

		"""
			Send report to hackerone when
			1. send_report is True from Hackerone model in ScanEngine
			2. username and key is set in HackerOneAPIKey in Dashboard
			3. severity is not info or low
		"""
		hackerone_query = Hackerone.objects.filter(send_report=True)
		api_key_check_query = HackerOneAPIKey.objects.filter(
			Q(username__isnull=False) & Q(key__isnull=False)
		)

		send_report = (
			hackerone_query.exists() and
			api_key_check_query.exists() and
			severity not in ('info', 'low') and
			vuln.target_domain.h1_team_handle
		)

		if send_report:
			hackerone = hackerone_query.first()
			if hackerone.send_critical and severity == 'critical':
				send_hackerone_report.delay(vuln.id)
			elif hackerone.send_high and severity == 'high':
				send_hackerone_report.delay(vuln.id)
			elif hackerone.send_medium and severity == 'medium':
				send_hackerone_report.delay(vuln.id)

	# Write results to JSON file
	with open(self.output_path, 'w') as f:
		json.dump(results, f, indent=4)

	# Send finish notif
	if send_status:
		vulns = Vulnerability.objects.filter(scan_history__id=self.scan_id)
		info_count = vulns.filter(severity=0).count()
		low_count = vulns.filter(severity=1).count()
		medium_count = vulns.filter(severity=2).count()
		high_count = vulns.filter(severity=3).count()
		critical_count = vulns.filter(severity=4).count()
		unknown_count = vulns.filter(severity=-1).count()
		vulnerability_count = info_count + low_count + medium_count + high_count + critical_count + unknown_count
		fields = {
			'Total': vulnerability_count,
			'Critical': critical_count,
			'High': high_count,
			'Medium': medium_count,
			'Low': low_count,
			'Info': info_count,
			'Unknown': unknown_count
		}
		self.notify(fields=fields)

	# after vulnerability scan is done, we need to run gpt if
	# should_fetch_gpt_report and openapi key exists

	if should_fetch_gpt_report and OpenAiAPIKey.objects.all().first():
		logger.info('Getting Vulnerability GPT Report')
		vulns = Vulnerability.objects.filter(
			scan_history__id=self.scan_id
		).filter(
			source=NUCLEI
		).exclude(
			severity=0
		)
		# find all unique vulnerabilities based on path and title
		# all unique vulnerability will go thru gpt function and get report
		# once report is got, it will be matched with other vulnerabilities and saved
		unique_vulns = set()
		for vuln in vulns:
			unique_vulns.add((vuln.name, vuln.get_path()))

		unique_vulns = list(unique_vulns)

		with concurrent.futures.ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
			future_to_gpt = {executor.submit(get_vulnerability_gpt_report, vuln): vuln for vuln in unique_vulns}

			# Wait for all tasks to complete
			for future in concurrent.futures.as_completed(future_to_gpt):
				gpt = future_to_gpt[future]
				try:
					future.result()
				except Exception as e:
					logger.error(f"Exception for Vulnerability {gpt}: {e}")

		return None


def get_vulnerability_gpt_report(vuln, vulnerability_id=None):
	title = vuln[0]
	path = vuln[1]
	if not path:
		path = '/'
	logger.info(f'Getting GPT Report for {title}, PATH: {path}')

	# 1. Check if the specific vulnerability already has GPT info
	if vulnerability_id:
		try:
			lookup_vulnerability = Vulnerability.objects.get(id=vulnerability_id)
			if lookup_vulnerability.is_gpt_used and lookup_vulnerability.description and lookup_vulnerability.impact and lookup_vulnerability.remediation:
				logger.info(f'Returning existing GPT report from Vulnerability ID {vulnerability_id}')
				return {
					'status': True,
					'description': lookup_vulnerability.description,
					'impact': lookup_vulnerability.impact,
					'remediation': lookup_vulnerability.remediation,
					'references': [url.url for url in lookup_vulnerability.references.all()]
				}
		except Vulnerability.DoesNotExist:
			pass

	# 2. Check if in global cache (GPTVulnerabilityReport) already exists
	stored = GPTVulnerabilityReport.objects.filter(
		url_path=path,
		title=title
	).first()

	if stored and stored.description and stored.impact and stored.remediation:
		logger.info(f'Found GPT Report in global cache for {title}')
		response = {
			'status': True,
			'description': stored.description,
			'impact': stored.impact,
			'remediation': stored.remediation,
			'references': [url.url for url in stored.references.all()]
		}
	else:
		# 3. Call LLM
		report = LLMVulnerabilityReportGenerator(logger=logger)
		vulnerability_description = get_gpt_vuln_input_description(
			title,
			path
		)
		response = report.get_vulnerability_description(vulnerability_description)
		if response.get('status'):
			add_gpt_description_db(
				title,
				path,
				response.get('description'),
				response.get('impact'),
				response.get('remediation'),
				response.get('references', [])
			)

	# 4. Update all matching vulnerabilities that don't have GPT info yet, or at least the specific one
	if response.get('status'):
		# Update matching vulnerabilities
		for v in Vulnerability.objects.filter(name=title, http_url__icontains=path):
			v.description = response.get('description', v.description)
			v.impact = response.get('impact', v.impact)
			v.remediation = response.get('remediation', v.remediation)
			v.is_gpt_used = True
			v.save()

			for url in response.get('references', []):
				ref, created = VulnerabilityReference.objects.get_or_create(url=url)
				v.references.add(ref)
			v.save()
	
	return response


def add_gpt_description_db(title, path, description, impact, remediation, references):
	logger.info(f'Adding GPT Report to DB for {title}, PATH: {path}')
	if not path:
		path = '/'
	
	gpt_report, created = GPTVulnerabilityReport.objects.update_or_create(
		url_path=path,
		title=title,
		defaults={
			'description': description,
			'impact': impact,
			'remediation': remediation
		}
	)

	if references:
		for url in references:
			ref, created = VulnerabilityReference.objects.get_or_create(url=url)
			gpt_report.references.add(ref)
		gpt_report.save()

@app.task(name='nuclei_scan', queue='main_scan_queue', base=RengineTask, bind=True)
def nuclei_scan(self, urls=[], ctx={}, description=None):
	"""HTTP vulnerability scan using Nuclei

	Args:
		urls (list, optional): If passed, filter on those URLs.
		description (str, optional): Task description shown in UI.

	Notes:
	Unfurl the urls to keep only domain and path, will be sent to vuln scan and
	ignore certain file extensions. Thanks: https://github.com/six2dez/reconftw
	"""
	from startScan.models import Subdomain
	# Config
	config = self.yaml_configuration.get(VULNERABILITY_SCAN) or {}
	input_path = f'{self.results_dir}/input_endpoints_vulnerability_scan.txt'
	enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
	concurrency = config.get(NUCLEI_CONCURRENCY) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	intensity = config.get(INTENSITY) or self.yaml_configuration.get(INTENSITY, DEFAULT_SCAN_INTENSITY)
	rate_limit = config.get(RATE_LIMIT) or self.yaml_configuration.get(RATE_LIMIT, DEFAULT_RATE_LIMIT)
	retries = config.get(RETRIES) or self.yaml_configuration.get(RETRIES, DEFAULT_RETRIES)
	timeout = config.get(TIMEOUT) or self.yaml_configuration.get(TIMEOUT, DEFAULT_HTTP_TIMEOUT)
	custom_headers = self.yaml_configuration.get(CUSTOM_HEADERS, [])
	'''
	# TODO: Remove custom_header in next major release
		support for custom_header will be remove in next major release, 
		as of now it will be supported for backward compatibility
		only custom_headers will be supported
	'''
	custom_header = self.yaml_configuration.get(CUSTOM_HEADER)
	if custom_header:
		custom_headers.append(custom_header)
	should_fetch_gpt_report = config.get(FETCH_GPT_REPORT, DEFAULT_GET_GPT_REPORT)
	nuclei_specific_config = config.get('nuclei', {})
	use_nuclei_conf = nuclei_specific_config.get(USE_NUCLEI_CONFIG, False)
	severities = nuclei_specific_config.get(NUCLEI_SEVERITY, NUCLEI_DEFAULT_SEVERITIES)
	tags = nuclei_specific_config.get(NUCLEI_TAGS, [])
	
	# Intelligence-Driven Scanning: Inject tags based on detected technologies
	tech_tags = []
	if self.scan:
		# Get all technologies discovered for this scan
		subdomains = Subdomain.objects.filter(scan_history=self.scan)
		all_techs = set()
		for sub in subdomains:
			# assuming technologies is a many-to-many field with 'name' attribute
			all_techs.update(sub.technologies.values_list('name', flat=True))
		
		# Temporarily disabled to check if this is causing nuclei scans to hang
		if all_techs:
			tech_tags = get_nuclei_tags_from_techs(list(all_techs))
			logger.info(f'Detected technologies: {list(all_techs)}. Adding targeted Nuclei tags: {tech_tags}')

	if tech_tags:
		# Combine user tags with tech tags
		user_tags = set(tags if isinstance(tags, list) else tags.split(',') if tags else [])
		user_tags.update(tech_tags)
		tags = ','.join(user_tags)
	else:
		tags = ','.join(tags) if isinstance(tags, list) else tags

	nuclei_templates = nuclei_specific_config.get(NUCLEI_TEMPLATE)
	custom_nuclei_templates = nuclei_specific_config.get(NUCLEI_CUSTOM_TEMPLATE)
	severities_str = ','.join(severities)

	# Get alive endpoints
	if urls:
		with open(input_path, 'w') as f:
			f.write('\n'.join(urls))
	else:
		get_http_urls(
			is_alive=enable_http_crawl,
			ignore_files=True,
			write_filepath=input_path,
			ctx=ctx
		)

	if intensity == 'normal': # reduce number of endpoints to scan
		unfurl_filter = f'{self.results_dir}/urls_unfurled.txt'
		run_command(
			f"cat {input_path} | unfurl -u format %s://%d%p |uro > {unfurl_filter}",
			shell=True,
			history_file=self.history_file,
			scan_id=self.scan_id,
			activity_id=self.activity_id)
		run_command(
			f'sort -u {unfurl_filter} -o  {unfurl_filter}',
			shell=True,
			history_file=self.history_file,
			scan_id=self.scan_id,
			activity_id=self.activity_id)
		input_path = unfurl_filter

	# Build templates
	logger.info('Updating Nuclei templates ...')
	# Wordfence Templates integration
	is_wordpress_detected = False # Temporarily disabled topscoder wordpress nuclei templates
	wordfence_exists = False
	if is_wordpress_detected:
		logger.info("WordPress detected. Preparing Wordfence Nuclei Templates...")
		os.environ['GITHUB_TEMPLATE_REPO'] = 'topscoder/nuclei-wordfence-cve'
		
		wordfence_dir = '/usr/src/github/topscoder/nuclei-wordfence-cve'
		if not os.path.exists(wordfence_dir) or not os.listdir(wordfence_dir):
			os.makedirs(os.path.dirname(wordfence_dir), exist_ok=True)
			logger.info("Cloning topscoder/nuclei-wordfence-cve templates from GitHub...")
			try:
				import subprocess
				subprocess.run(
					["git", "clone", "--depth", "1", "https://github.com/topscoder/nuclei-wordfence-cve.git", wordfence_dir],
					timeout=20,
					check=True,
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE
				)
				logger.info("Successfully cloned Wordfence templates.")
				wordfence_exists = True
			except Exception as e:
				logger.warning(f"Could not clone Wordfence templates: {str(e)}")
		else:
			wordfence_exists = True

	run_command(
		'nuclei -update-templates',
		shell=True,
		history_file=self.history_file,
		scan_id=self.scan_id,
		activity_id=self.activity_id)
	templates = []
	if not (nuclei_templates or custom_nuclei_templates):
		templates.append(NUCLEI_DEFAULT_TEMPLATES_PATH)

	if nuclei_templates:
		if ALL in nuclei_templates:
			template = NUCLEI_DEFAULT_TEMPLATES_PATH
			templates.append(template)
		else:
			templates.extend(nuclei_templates)

	if custom_nuclei_templates:
		custom_nuclei_template_paths = []
		for elem in custom_nuclei_templates:
			if str(elem).endswith(('.yaml', '.yml')) or str(elem).endswith('/'):
				custom_nuclei_template_paths.append(str(elem))
			else:
				custom_nuclei_template_paths.append(f'{str(elem)}.yaml')
		templates.extend(custom_nuclei_template_paths)

	# Build CMD
	cmd = 'nuclei -j'
	cmd += ' -config /root/.config/nuclei/config.yaml' if use_nuclei_conf else ''
	cmd += f' -irr'

	# Apply OpSec stealth
	proxy = get_random_proxy()
	opsec = OpSecManager()
	cmd = opsec.apply_stealth('nuclei', cmd, proxy=proxy)
	formatted_headers = ' '.join(f'-H "{header}"' for header in custom_headers)
	if formatted_headers:
		cmd += formatted_headers
	cmd += f' -l {input_path}'
	cmd += f' -c {str(concurrency)}' if concurrency > 0 else ''

	cmd += f' -retries {retries}' if retries > 0 else ''
	cmd += f' -rl {rate_limit}' if rate_limit > 0 else ''
	# cmd += f' -severity {severities_str}'
	cmd += f' -timeout {str(timeout)}' if timeout and timeout > 0 else ''
	cmd += f' -tags {tags}' if tags else ''
	cmd += f' -silent'
	for tpl in templates:
		cmd += f' -t {tpl}'
	
	if is_wordpress_detected and wordfence_exists:
		# Add Wordfence template path
		logger.warning(f'wordfence_detected: {is_wordpress_detected}, wordfence_exists: {wordfence_exists}')
		cmd += " -t /usr/src/github/topscoder/nuclei-wordfence-cve"
		# Default to production, optional candidate
		use_candidate = config.get('nuclei_config', {}).get(USE_WORDFENCE_CANDIDATE, False)
		if use_candidate:
			cmd += " -tags candidate"
		else:
			cmd += " -tags production"


	# Run each severity sequentially inside the same nuclei_scan task
	for severity in severities:
		logger.info(f"Running Nuclei severity: {severity}")
		if hasattr(self, 'activity') and self.activity:
			self.activity.title = f"Nuclei Scan - Severity: {severity}"
			self.activity.save()
		
		# Invoke the nuclei_individual_severity_module synchronously via Celery apply
		logger.warning(f'cmd: {cmd}')
		nuclei_individual_severity_module.apply(
			kwargs={
				'cmd': cmd,
				'severity': severity,
				'enable_http_crawl': enable_http_crawl,
				'should_fetch_gpt_report': should_fetch_gpt_report,
				'ctx': ctx,
				'description': f'Nuclei Scan with severity {severity}'
			}
		)

	logger.info('Vulnerability scan with all severities completed...')
	return None

@app.task(name='dalfox_xss_scan', queue='main_scan_queue', base=RengineTask, bind=True)
def dalfox_xss_scan(self, urls=[], ctx={}, description=None):
	"""XSS Scan using dalfox

	Args:
		urls (list, optional): If passed, filter on those URLs.
		description (str, optional): Task description shown in UI.
	"""
	vuln_config = self.yaml_configuration.get(VULNERABILITY_SCAN) or {}
	should_fetch_gpt_report = vuln_config.get(FETCH_GPT_REPORT, DEFAULT_GET_GPT_REPORT)
	dalfox_config = vuln_config.get(DALFOX) or {}
	custom_headers = self.yaml_configuration.get(CUSTOM_HEADERS, [])
	'''
	# TODO: Remove custom_header in next major release
		support for custom_header will be remove in next major release, 
		as of now it will be supported for backward compatibility
		only custom_headers will be supported
	'''
	custom_header = self.yaml_configuration.get(CUSTOM_HEADER)
	if custom_header:
		custom_headers.append(custom_header)
	is_waf_evasion = dalfox_config.get(WAF_EVASION, False)
	blind_xss_server = dalfox_config.get(BLIND_XSS_SERVER)
	user_agent = dalfox_config.get(USER_AGENT) or self.yaml_configuration.get(USER_AGENT)
	timeout = dalfox_config.get(TIMEOUT)
	delay = dalfox_config.get(DELAY)
	threads = dalfox_config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	input_path = f'{self.results_dir}/input_endpoints_dalfox_xss.txt'

	if urls:
		with open(input_path, 'w') as f:
			f.write('\n'.join(urls))
	else:
		get_http_urls(
			is_alive=False,
			ignore_files=False,
			write_filepath=input_path,
			ctx=ctx
		)

	notif = Notification.objects.first()
	send_status = notif.send_scan_status_notif if notif else False

	# command builder
	proxy = get_random_proxy()
	opsec = OpSecManager()
	cmd = 'dalfox --silence --no-color --no-spinner'
	cmd += f' --only-poc r '
	cmd += f' --ignore-return 302,404,403'
	
	cmd = opsec.apply_stealth('dalfox', cmd, proxy=proxy)
	cmd += f' --skip-bav'
	cmd += f' file {input_path}'
	cmd += f' --proxy {proxy}' if proxy else ''
	cmd += f' --waf-evasion' if is_waf_evasion else ''
	cmd += f' -b {blind_xss_server}' if blind_xss_server else ''
	cmd += f' --delay {delay}' if delay else ''
	cmd += f' --timeout {timeout}' if timeout else ''
	formatted_headers = ' '.join(f'-H "{header}"' for header in custom_headers)
	if formatted_headers:
		cmd += formatted_headers
	cmd += f' --user-agent {user_agent}' if user_agent else ''
	cmd += f' --worker {threads}' if threads else ''
	cmd += f' --format json'

	results = []
	for line in stream_command(
			cmd,
			history_file=self.history_file,
			scan_id=self.scan_id,
			activity_id=self.activity_id,
			trunc_char=','
		):
		if not isinstance(line, dict):
			continue

		results.append(line)

		vuln_data = parse_dalfox_result(line)

		http_url = sanitize_url(line.get('data'))
		subdomain_name = get_subdomain_from_url(http_url)

		# TODO: this should be get only
		subdomain, _ = Subdomain.objects.get_or_create(
			name=subdomain_name,
			scan_history=self.scan,
			target_domain=self.domain
		)
		endpoint, _ = save_endpoint(
			http_url,
			crawl=False,
			subdomain=subdomain,
			ctx=ctx
		)
		if endpoint:
			http_url = endpoint.http_url
			endpoint.save()

		vuln, _ = save_vulnerability(
			target_domain=self.domain,
			http_url=http_url,
			scan_history=self.scan,
			subscan=self.subscan,
			**vuln_data
		)

		if not vuln:
			continue

	# after vulnerability scan is done, we need to run gpt if
	# should_fetch_gpt_report and openapi key exists

	if should_fetch_gpt_report and OpenAiAPIKey.objects.all().first():
		logger.info('Getting Dalfox Vulnerability GPT Report')
		vulns = Vulnerability.objects.filter(
			scan_history__id=self.scan_id
		).filter(
			source=DALFOX
		).exclude(
			severity=0
		)

		_vulns = []
		for vuln in vulns:
			_vulns.append((vuln.name, vuln.http_url))

		with concurrent.futures.ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
			future_to_gpt = {executor.submit(get_vulnerability_gpt_report, vuln): vuln for vuln in _vulns}

			# Wait for all tasks to complete
			for future in concurrent.futures.as_completed(future_to_gpt):
				gpt = future_to_gpt[future]
				try:
					future.result()
				except Exception as e:
					logger.error(f"Exception for Vulnerability {gpt}: {e}")
	return results


@app.task(name='crlfuzz_scan', queue='main_scan_queue', base=RengineTask, bind=True)
def crlfuzz_scan(self, urls=[], ctx={}, description=None):
	"""CRLF Fuzzing with CRLFuzz

	Args:
		urls (list, optional): If passed, filter on those URLs.
		description (str, optional): Task description shown in UI.
	"""
	vuln_config = self.yaml_configuration.get(VULNERABILITY_SCAN) or {}
	should_fetch_gpt_report = vuln_config.get(FETCH_GPT_REPORT, DEFAULT_GET_GPT_REPORT)
	custom_headers = self.yaml_configuration.get(CUSTOM_HEADERS, [])
	'''
	# TODO: Remove custom_header in next major release
		support for custom_header will be remove in next major release, 
		as of now it will be supported for backward compatibility
		only custom_headers will be supported
	'''
	custom_header = self.yaml_configuration.get(CUSTOM_HEADER)
	if custom_header:
		custom_headers.append(custom_header)
	user_agent = vuln_config.get(USER_AGENT) or self.yaml_configuration.get(USER_AGENT)
	threads = vuln_config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	input_path = f'{self.results_dir}/input_endpoints_crlf.txt'
	output_path = f'{self.results_dir}/{self.filename}'

	if urls:
		with open(input_path, 'w') as f:
			f.write('\n'.join(urls))
	else:
		get_http_urls(
			is_alive=False,
			ignore_files=True,
			write_filepath=input_path,
			ctx=ctx
		)

	notif = Notification.objects.first()
	send_status = notif.send_scan_status_notif if notif else False

	# command builder
	proxy = get_random_proxy()
	cmd = 'crlfuzz -s'
	cmd += f' -l {input_path}'
	cmd += f' -x {proxy}' if proxy else ''
	formatted_headers = ' '.join(f'-H "{header}"' for header in custom_headers)
	if formatted_headers:
		cmd += formatted_headers
	cmd += f' -o {output_path}'

	run_command(
		cmd,
		shell=True,
		history_file=self.history_file,
		scan_id=self.scan_id,
		activity_id=self.activity_id
	)

	if not os.path.isfile(output_path):
		logger.info('No Results from CRLFuzz')
		return

	crlfs = []
	results = []
	with open(output_path, 'r') as file:
		crlfs = file.readlines()

	for crlf in crlfs:
		url = crlf.strip()

		vuln_data = parse_crlfuzz_result(url)

		http_url = sanitize_url(url)
		subdomain_name = get_subdomain_from_url(http_url)

		subdomain, _ = Subdomain.objects.get_or_create(
			name=subdomain_name,
			scan_history=self.scan,
			target_domain=self.domain
		)

		endpoint, _ = save_endpoint(
			http_url,
			crawl=False,
			subdomain=subdomain,
			ctx=ctx
		)
		if endpoint:
			http_url = endpoint.http_url
			endpoint.save()

		vuln, _ = save_vulnerability(
			target_domain=self.domain,
			http_url=http_url,
			scan_history=self.scan,
			subscan=self.subscan,
			**vuln_data
		)

		if not vuln:
			continue

	# after vulnerability scan is done, we need to run gpt if
	# should_fetch_gpt_report and openapi key exists

	if should_fetch_gpt_report and OpenAiAPIKey.objects.all().first():
		logger.info('Getting CRLFuzz Vulnerability GPT Report')
		vulns = Vulnerability.objects.filter(
			scan_history__id=self.scan_id
		).filter(
			source=CRLFUZZ
		).exclude(
			severity=0
		)

		_vulns = []
		for vuln in vulns:
			_vulns.append((vuln.name, vuln.http_url))

		with concurrent.futures.ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
			future_to_gpt = {executor.submit(get_vulnerability_gpt_report, vuln): vuln for vuln in _vulns}

			# Wait for all tasks to complete
			for future in concurrent.futures.as_completed(future_to_gpt):
				gpt = future_to_gpt[future]
				try:
					future.result()
				except Exception as e:
					logger.error(f"Exception for Vulnerability {gpt}: {e}")

	return results


@app.task(name='s3scanner', queue='main_scan_queue', base=RengineTask, bind=True)
def s3scanner(self, ctx={}, description=None):
	"""Bucket Scanner

	Args:
		ctx (dict): Context
		description (str, optional): Task description shown in UI.
	"""
	input_path = f'{self.results_dir}/#{self.scan_id}_subdomain_discovery.txt'
	vuln_config = self.yaml_configuration.get(VULNERABILITY_SCAN) or {}
	s3_config = vuln_config.get(S3SCANNER) or {}
	threads = s3_config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	providers = s3_config.get(PROVIDERS, S3SCANNER_DEFAULT_PROVIDERS)
	scan_history = ScanHistory.objects.filter(pk=self.scan_id).first()
	for provider in providers:
		cmd = f's3scanner -bucket-file {input_path} -enumerate -provider {provider} -threads {threads} -json'
		for line in stream_command(
				cmd,
				history_file=self.history_file,
				scan_id=self.scan_id,
				activity_id=self.activity_id):

			if not isinstance(line, dict):
				continue

			if line.get('bucket', {}).get('exists', 0) == 1:
				result = parse_s3scanner_result(line)
				s3bucket, created = S3Bucket.objects.get_or_create(**result)
				scan_history.buckets.add(s3bucket)
				logger.info(f"s3 bucket added {result['provider']}-{result['name']}-{result['region']}")


@app.task(name='http_crawl', queue='main_scan_queue', base=RengineTask, bind=True)
def http_crawl(
		self,
		urls=[],
		method=None,
		recrawl=False,
		ctx={},
		track=True,
		description=None,
		is_ran_from_subdomain_scan=False,
		should_remove_duplicate_endpoints=True,
		duplicate_removal_fields=[]):
	"""Use httpx to query HTTP URLs for important info like page titles, http
	status, etc...

	Args:
		urls (list, optional): A set of URLs to check. Overrides default
			behavior which queries all endpoints related to this scan.
		method (str): HTTP method to use (GET, HEAD, POST, PUT, DELETE).
		recrawl (bool, optional): If False, filter out URLs that have already
			been crawled.
		should_remove_duplicate_endpoints (bool): Whether to remove duplicate endpoints
		duplicate_removal_fields (list): List of Endpoint model fields to check for duplicates

	Returns:
		list: httpx results.
	"""
	logger.info('Initiating HTTP Crawl')
	if is_ran_from_subdomain_scan:
		logger.info('Running From Subdomain Scan...')
	cmd = '/usr/local/bin/httpx'
	cfg = self.yaml_configuration.get(HTTP_CRAWL) or {}
	custom_headers = self.yaml_configuration.get(CUSTOM_HEADERS, [])
	'''
	# TODO: Remove custom_header in next major release
		support for custom_header will be remove in next major release, 
		as of now it will be supported for backward compatibility
		only custom_headers will be supported
	'''
	custom_header = self.yaml_configuration.get(CUSTOM_HEADER)
	if custom_header:
		custom_headers.append(custom_header)
	threads = cfg.get(THREADS, DEFAULT_THREADS)
	follow_redirect = cfg.get(FOLLOW_REDIRECT, True)
	self.output_path = None
	input_path = f'{self.results_dir}/httpx_input.txt'
	history_file = f'{self.results_dir}/commands.txt'
	if urls: # direct passing URLs to check
		if self.starting_point_path:
			urls = [u for u in urls if self.starting_point_path in u]

		with open(input_path, 'w') as f:
			f.write('\n'.join(urls))
	else:
		urls = get_http_urls(
			is_uncrawled=not recrawl,
			write_filepath=input_path,
			ctx=ctx
		)
		# logger.debug(urls)

	# exclude urls by pattern
	if self.excluded_paths:
		urls = exclude_urls_by_patterns(self.excluded_paths, urls)

	# If no URLs found, skip it
	if not urls:
		return

	# Re-adjust thread number if few URLs to avoid spinning up a monster to
	# kill a fly.
	if len(urls) < threads:
		threads = len(urls)

	# projectdiscovery tools like naabu and httpx seem to fail when proxies are used
	# ensuring that proxies are never used for httpx
	proxy = ''

	# Run command
	cmd += f' -cl -ct -rt -location -td -websocket -cname -asn -cdn -probe -random-agent'
	cmd += f' -t {threads}' if threads > 0 else ''
	cmd += f' --http-proxy {proxy}' if proxy else ''
	formatted_headers = ' '.join(f'-H "{header}"' for header in custom_headers)
	if formatted_headers:
		cmd += formatted_headers
	cmd += f' -json'
	cmd += f' -u {urls[0]}' if len(urls) == 1 else f' -l {input_path}'
	cmd += f' -x {method}' if method else ''
	if follow_redirect:
		cmd += ' --follow-redirects'
	
	# Apply OpSec stealth
	opsec = OpSecManager()
	cmd = opsec.apply_stealth('httpx', cmd, proxy=proxy)

	results = []
	endpoint_ids = []
	for line in stream_command(
			cmd,
			history_file=history_file,
			scan_id=self.scan_id,
			activity_id=self.activity_id):

		if not line or not isinstance(line, dict):
			continue

		logger.debug(line)

		# No response from endpoint
		if line.get('failed', False):
			continue

		httpx_result = process_httpx_response(line, ctx=ctx, is_ran_from_subdomain_scan=is_ran_from_subdomain_scan)
		if not httpx_result:
			continue

		endpoint, created = httpx_result

		if not endpoint:
			continue

		endpoint_str = f'{endpoint.http_url} [{endpoint.http_status}] `{endpoint.content_length}B` `{endpoint.webserver}` `{line.get("time")}`'
		logger.warning(endpoint_str)
		if endpoint.is_alive and endpoint.http_status != 403:
			self.notify(
				fields={'Alive endpoint': f'• {endpoint_str}'},
				add_meta_info=False)

		# Add endpoint to results for UI tabs
		line['_cmd'] = cmd
		line['final_url'] = endpoint.http_url
		line['endpoint_id'] = endpoint.id
		line['endpoint_created'] = created
		line['is_redirect'] = endpoint.is_redirect
		line['status_code'] = endpoint.http_status
		line['title'] = endpoint.page_title
		line['content_length'] = endpoint.content_length
		line['webserver'] = endpoint.webserver
		line['content_type'] = endpoint.content_type
		line['response_time'] = endpoint.response_time
		
		results.append(line)

		techs = line.get('tech', [])
		subdomain = endpoint.subdomain

		# Add technology objects to DB
		for technology in techs:
			from django.core.exceptions import MultipleObjectsReturned
			try:
				tech, _ = Technology.objects.get_or_create(name=technology)
			except MultipleObjectsReturned:
				tech = Technology.objects.filter(name=technology).first()
			endpoint.techs.add(tech)
			if is_ran_from_subdomain_scan:
				subdomain.technologies.add(tech)
				subdomain.save()
			endpoint.save()
		techs_str = ', '.join([f'`{tech}`' for tech in techs])
		self.notify(
			fields={'Technologies': techs_str},
			add_meta_info=False)

		# Add IP objects for 'a' records to DB
		a_records = line.get('a', [])
		cdn = line.get('cdn', False)
		for ip_address in a_records:
			ip, _ = save_ip_address(
				ip_address,
				subdomain,
				subscan=self.subscan,
				scan_id=self.scan_id,
				activity_id=self.activity_id,
				cdn=cdn)
		
		if a_records:
			ips_str = '• ' + '\n• '.join([f'`{ip}`' for ip in a_records])
			self.notify(
				fields={'IPs': ips_str},
				add_meta_info=False)

		# Update subdomain status attributes if this is the default endpoint
		if is_ran_from_subdomain_scan and endpoint.is_default:
			subdomain.http_url = endpoint.http_url
			subdomain.http_status = endpoint.http_status
			subdomain.page_title = endpoint.page_title
			subdomain.content_length = endpoint.content_length
			subdomain.webserver = endpoint.webserver
			subdomain.response_time = endpoint.response_time
			subdomain.content_type = endpoint.content_type
			
			cnames = line.get('cnames', [])
			if cnames:
				subdomain.cname = ','.join(cnames)
			
			subdomain.is_cdn = cdn
			if cdn:
				subdomain.cdn_name = line.get('cdn_name')
			subdomain.save()
		endpoint.save()
		endpoint_ids.append(endpoint.id)

	if should_remove_duplicate_endpoints:
		# Remove 'fake' alive endpoints that are just redirects to the same page
		remove_duplicate_endpoints(
			self.scan_id,
			self.domain_id,
			self.subdomain_id,
			filter_ids=endpoint_ids
		)

	# Remove input file
	run_command(
		f'rm {input_path}',
		shell=True,
		history_file=self.history_file,
		scan_id=self.scan_id,
		activity_id=self.activity_id)

	return results


#---------------------#
# Notifications tasks #
#---------------------#
@app.task(name='send_notif', bind=False, queue='send_notif_queue')
def send_notif(
		message,
		scan_history_id=None,
		subscan_id=None,
		**options):
	if not 'title' in options:
		message = enrich_notification(message, scan_history_id, subscan_id)
	send_discord_message(message, **options)
	send_slack_message(message)
	send_lark_message(message)
	send_telegram_message(message)


@app.task(name='send_scan_notif', bind=False, queue='send_scan_notif_queue')
def send_scan_notif(
		scan_history_id,
		subscan_id=None,
		engine_id=None,
		status='RUNNING'):
	"""Send scan status notification. Works for scan or a subscan if subscan_id
	is passed.

	Args:
		scan_history_id (int, optional): ScanHistory id.
		subscan_id (int, optional): SuScan id.
		engine_id (int, optional): EngineType id.
	"""
	# Get domain, engine, scan_history objects
	scan = ScanHistory.objects.filter(pk=scan_history_id).first()
	if not engine_id and scan:
		engine = scan.scan_type
	else:
		engine = EngineType.objects.filter(pk=engine_id).first()
	
	subscan = SubScan.objects.filter(pk=subscan_id).first()
	tasks = ScanActivity.objects.filter(scan_of=scan) if scan else 0

	# Build notif options
	url = get_scan_url(scan_history_id, subscan_id)
	title = get_scan_title(scan_history_id, subscan_id)
	fields = get_scan_fields(engine, scan, subscan, status, tasks)

	severity = None
	msg = f'{title} {status}\n'
	msg += '\n🡆 '.join(f'**{k}:** {v}' for k, v in fields.items())
	if status:
		severity = STATUS_TO_SEVERITIES.get(status)
	opts = {
		'title': title,
		'url': url,
		'fields': fields,
		'severity': severity
	}
	logger.warning(f'Sending notification "{title}" [{severity}]')

	# inapp notification has to be sent eitherways
	generate_inapp_notification(scan, subscan, status, engine, fields)

	notif = Notification.objects.first()

	if notif and notif.send_scan_status_notif:
		# Send notification
		send_notif(
			msg,
			scan_history_id,
			subscan_id,
			**opts)
	
def generate_inapp_notification(scan, subscan, status, engine, fields):
	if status == 'COMPLETED':
		status = 'SUCCESS'

	scan_type = "Subscan" if subscan else "Scan"
	domain = subscan.domain.name if subscan else scan.domain.name
	duration_msg = None
	redirect_link = None
	title = f"Scan Status Update"
	description = f"Scan status update for {domain}"
	icon = "mdi-information-outline"
	notif_status = 'info'
	
	if status == 'RUNNING':
		title = f"{scan_type} Started"
		description = f"{scan_type} has been initiated for {domain}"
		icon = "mdi-play-circle-outline"
		notif_status = 'info'
	elif status == 'SUCCESS':
		title = f"{scan_type} Completed"
		description = f"{scan_type} was successful for {domain}"
		icon = "mdi-check-circle-outline"
		notif_status = 'success'
		duration_msg = f'Completed in {fields.get("Duration")}'
	elif status == 'ABORTED':
		title = f"{scan_type} Aborted"
		description = f"{scan_type} was aborted for {domain}"
		icon = "mdi-alert-circle-outline"
		notif_status = 'warning'
		duration_msg = f'Aborted in {fields.get("Duration")}'
	elif status == 'FAILED':
		title = f"{scan_type} Failed"
		description = f"{scan_type} has failed for {domain}"
		icon = "mdi-close-circle-outline"
		notif_status = 'error'
		duration_msg = f'Failed in {fields.get("Duration")}'
	elif status == 'PARTIALLY COMPLETE':
		title = f"{scan_type} Partially Completed"
		description = f"{scan_type} has completed with some failures for {domain}"
		icon = "mdi-alert-circle-outline"
		notif_status = 'warning'
		duration_msg = f'Partially completed in {fields.get("Duration")}'

	description += f"<br>Engine: {engine.engine_name if engine else 'N/A'}"
	slug = scan.domain.project.slug if scan else subscan.history.domain.project.slug
	if duration_msg:
		description += f"<br>{duration_msg}"

	if status != 'RUNNING':
		redirect_link = f"/scan/{slug}/detail/{scan.id}" if scan else None

	create_inappnotification(
		title=title,
		description=description,
		notification_type='project',
		project_slug=slug,
		icon=icon,
		is_read=False,
		status=notif_status,
		redirect_link=redirect_link,
		open_in_new_tab=False
	)


@app.task(name='send_task_notif', bind=False, queue='send_task_notif_queue')
def send_task_notif(
		task_name,
		status=None,
		result=None,
		output_path=None,
		traceback=None,
		scan_history_id=None,
		engine_id=None,
		subscan_id=None,
		severity=None,
		add_meta_info=True,
		update_fields={}):
	"""Send task status notification.

	Args:
		task_name (str): Task name.
		status (str, optional): Task status.
		result (str, optional): Task result.
		output_path (str, optional): Task output path.
		traceback (str, optional): Task traceback.
		scan_history_id (int, optional): ScanHistory id.
		subscan_id (int, optional): SuScan id.
		engine_id (int, optional): EngineType id.
		severity (str, optional): Severity (will be mapped to notif colors)
		add_meta_info (bool, optional): Wheter to add scan / subscan info to notif.
		update_fields (dict, optional): Fields key / value to update.
	"""

	# Skip send if notification settings are not configured
	notif = Notification.objects.first()
	if not (notif and notif.send_scan_status_notif):
		return

	# Build fields
	url = None
	fields = {}
	if add_meta_info:
		engine = EngineType.objects.filter(pk=engine_id).first()
		scan = ScanHistory.objects.filter(pk=scan_history_id).first()
		subscan = SubScan.objects.filter(pk=subscan_id).first()
		url = get_scan_url(scan_history_id)
		if status:
			fields['Status'] = f'**{status}**'
		if engine:
			fields['Engine'] = engine.engine_name
		if scan:
			fields['Scan ID'] = f'[#{scan.id}]({url})'
		if subscan:
			url = get_scan_url(scan_history_id, subscan_id)
			fields['Subscan ID'] = f'[#{subscan.id}]({url})'
	title = get_task_title(task_name, scan_history_id, subscan_id)
	if status:
		severity = STATUS_TO_SEVERITIES.get(status)

	msg = f'{title} {status}\n'
	msg += '\n🡆 '.join(f'**{k}:** {v}' for k, v in fields.items())

	# Add fields to update
	for k, v in update_fields.items():
		fields[k] = v

	# Add traceback to notif
	if traceback and notif.send_scan_tracebacks:
		fields['Traceback'] = f'```\n{traceback}\n```'

	# Add files to notif
	files = []
	attach_file = (
		notif.send_scan_output_file and
		output_path and
		result and
		not traceback
	)
	if attach_file:
		output_title = output_path.split('/')[-1]
		files = [(output_path, output_title)]

	# Send notif
	opts = {
		'title': title,
		'url': url,
		'files': files,
		'severity': severity,
		'fields': fields,
		'fields_append': update_fields.keys()
	}
	send_notif(
		msg,
		scan_history_id=scan_history_id,
		subscan_id=subscan_id,
		**opts)


@app.task(name='send_file_to_discord', bind=False, queue='send_file_to_discord_queue')
def send_file_to_discord(file_path, title=None):
	notif = Notification.objects.first()
	do_send = notif and notif.send_to_discord and notif.discord_hook_url
	if not do_send:
		return False

	webhook = DiscordWebhook(
		url=notif.discord_hook_url,
		rate_limit_retry=True,
		username=title or "reNgine Discord Plugin"
	)
	with open(file_path, "rb") as f:
		head, tail = os.path.split(file_path)
		webhook.add_file(file=f.read(), filename=tail)
	webhook.execute()


@app.task(name='send_hackerone_report', bind=False, queue='send_hackerone_report_queue')
def send_hackerone_report(vulnerability_id):
	"""Send HackerOne vulnerability report.

	Args:
		vulnerability_id (int): Vulnerability id.

	Returns:
		int: HTTP response status code.
	"""
	vulnerability = Vulnerability.objects.get(id=vulnerability_id)
	severities = {v: k for k,v in NUCLEI_SEVERITY_MAP.items()}

	# can only send vulnerability report if team_handle exists and send_report is True and api_key exists
	hackerone = Hackerone.objects.filter(send_report=True).first()
	api_key = HackerOneAPIKey.objects.filter(username__isnull=False, key__isnull=False).first()

	if not (vulnerability.target_domain.h1_team_handle and hackerone and api_key):
		logger.error('Missing required data: team handle, Hackerone config, or API key.')
		return {"status_code": 400, "message": "Missing required data"}

	severity_value = severities[vulnerability.severity]
	tpl = hackerone.report_template or ""

	tpl_vars = {
		'{vulnerability_name}': vulnerability.name,
		'{vulnerable_url}': vulnerability.http_url,
		'{vulnerability_severity}': severity_value,
		'{vulnerability_description}': vulnerability.description or '',
		'{vulnerability_extracted_results}': vulnerability.extracted_results or '',
		'{vulnerability_reference}': vulnerability.reference or '',
	}

	# Replace syntax of report template with actual content
	for key, value in tpl_vars.items():
		tpl = tpl.replace(key, value)

	data = {
		"data": {
			"type": "report",
			"attributes": {
				"team_handle": vulnerability.target_domain.h1_team_handle,
				"title": f'{vulnerability.name} found in {vulnerability.http_url}',
				"vulnerability_information": tpl,
				"severity_rating": severity_value,
				"impact": "More information about the impact and vulnerability can be found here: \n" + vulnerability.reference if vulnerability.reference else "NA",
			}
		}
	}

	headers = {
		'Content-Type': 'application/json',
		'Accept': 'application/json'
	}

	r = requests.post(
		'https://api.hackerone.com/v1/hackers/reports',
		auth=(api_key.username, api_key.key),
		json=data,
		headers=headers
	)
	response = r.json()
	status_code = r.status_code
	if status_code == 201:
		vulnerability.hackerone_report_id = response['data']["id"]
		vulnerability.open_status = False
		vulnerability.save()
		return {"status_code": r.status_code, "message": "Report sent successfully"}
	logger.error(f"Error sending report to HackerOne")
	return {"status_code": r.status_code, "message": response}


#-------------#
# Utils tasks #
#-------------#

@app.task(name='parse_nmap_results', bind=False, queue='parse_nmap_results_queue')
def parse_nmap_results(xml_file, output_file=None):
	"""Parse results from nmap output file.

	Args:
		xml_file (str): nmap XML report file path.

	Returns:
		list: List of vulnerabilities found from nmap results.
	"""
	with open(xml_file, encoding='utf8') as f:
		content = f.read()
		try:
			nmap_results = xmltodict.parse(content) # parse XML to dict
		except Exception as e:
			logger.exception(e)
			logger.error(f'Cannot parse {xml_file} to valid JSON. Skipping.')
			return []

	# Write JSON to output file
	if output_file:
		with open(output_file, 'w') as f:
			json.dump(nmap_results, f, indent=4)
	logger.warning(json.dumps(nmap_results, indent=4))
	hosts = (
		nmap_results
		.get('nmaprun', {})
		.get('host', {})
	)
	all_vulns = []
	services = []
	if isinstance(hosts, dict):
		hosts = [hosts]

	for host in hosts:
		# Grab hostname / IP from output
		hostnames_dict = host.get('hostnames', {})
		if hostnames_dict:
			# Ensure that hostnames['hostname'] is a list for consistency
			hostnames_list = hostnames_dict['hostname'] if isinstance(hostnames_dict['hostname'], list) else [hostnames_dict['hostname']]

			# Extract all the @name values from the list of dictionaries
			hostnames = [entry.get('@name') for entry in hostnames_list]
		else:
			hostnames = [host.get('address')['@addr']]

		# Iterate over each hostname for each port
		for hostname in hostnames:

			# Grab ports from output
			ports = host.get('ports', {}).get('port', [])
			if isinstance(ports, dict):
				ports = [ports]

			for port in ports:
				# Skip closed ports
				state = port.get('state', {}).get('@state', 'unknown')
				if state != 'open':
					continue

				url_vulns = []
				port_number = port['@portid']
				url = sanitize_url(f'{hostname}:{port_number}')
				logger.info(f'Parsing nmap results for {hostname}:{port_number} ...')
				if not port_number or not port_number.isdigit():
					continue
				
				port_protocol = port['@protocol']
				service = port.get('service', {})
				service_name = service.get('@name', '').lower()
				
				# Register discovered service for brute-force candidates
				services.append({
					'target': hostname,
					'port': int(port_number),
					'service': service_name,
					'banner': service.get('@product', '')
				})
				port_protocol = port['@protocol']
				scripts = port.get('script', [])
				if isinstance(scripts, dict):
					scripts = [scripts]

				for script in scripts:
					script_id = script['@id']
					script_output = script['@output']
					script_output_table = script.get('table', [])
					service = port.get('service', {})
					service_product = service.get('@product', '')
					service_version = service.get('@version', '')
					service_title = f"{service_product} {service_version}".strip()
					logger.debug(f'Ran nmap script "{script_id}" on {port_number}/{port_protocol}:\n{script_output}\n')
					if script_id == 'vulscan':
						vulns = parse_nmap_vulscan_output(script_output)
						url_vulns.extend(vulns)
					elif script_id == 'vulners':
						vulns = parse_nmap_vulners_output(script_output, service_title=service_title)
						url_vulns.extend(vulns)
					elif script_id == 'http-server-header':
						vulns = parse_nmap_http_server_header_output(script_output)
						url_vulns.extend(vulns)
					elif script_id == 'fingerprint-strings':
						vulns = parse_nmap_fingerprint_strings_output(script_output)
						url_vulns.extend(vulns)
					elif script_id == 'https-redirect':
						vulns = parse_nmap_https_redirect_output(script_output)
						url_vulns.extend(vulns)
					elif script_id == 'http-title':
						vulns = parse_nmap_http_title_output(script_output)
						url_vulns.extend(vulns)
					elif script_id == 'http-vuln-*' or script_id.startswith('http-vuln'):
						vulns = parse_nmap_generic_vuln_output(script_id, script_output)
						url_vulns.extend(vulns)
					else:
						# Generic vuln script handling if script_id contains 'vuln'
						if 'vuln' in script_id:
							vulns = parse_nmap_generic_vuln_output(script_id, script_output)
							url_vulns.extend(vulns)
						else:
							# Robust catch-all for any script output indicating a vulnerability
							lower_output = script_output.lower()
							if "vulnerable" in lower_output or "vulnerability" in lower_output or "account found" in lower_output:
								vulns = parse_nmap_generic_vuln_output(script_id, script_output)
								url_vulns.extend(vulns)
							else:
								# Support for specific non-'vuln' scripts that can still find issues
								if any(s in script_id for s in ['csrf', 'xss', 'exec', 'exploit', 'injection', 'drown']):
									vulns = parse_nmap_generic_vuln_output(script_id, script_output)
									url_vulns.extend(vulns)
								else:
									logger.warning(f'Script output parsing for script "{script_id}" is not supported yet.')

				# Add URL & source to vuln
				for vuln in url_vulns:
					if 'source' not in vuln:
						vuln['source'] = NMAP
					# TODO: This should extend to any URL, not just HTTP
					vuln['http_url'] = url
					if 'http_path' in vuln:
						vuln['http_url'] += vuln['http_path']
					all_vulns.append(vuln)

	return {'vulns': all_vulns, 'services': services}


def parse_nmap_https_redirect_output(script_output):
	return [{
		'name': 'HTTPS Redirect Detected',
		'severity': 0,
		'description': f'Service redirects to HTTPS:\n{script_output}',
		'type': 'info'
	}]


def parse_nmap_http_server_header_output(script_output):
	return [{
		'name': 'HTTP Server Header',
		'severity': 0,
		'description': f'HTTP Server Header detected: {script_output}',
		'type': 'info'
	}]


def parse_nmap_fingerprint_strings_output(script_output):
	vulns = [{
		'name': 'Service Fingerprint',
		'severity': 0,
		'description': f'Nmap discovered service fingerprint strings:\n{script_output}',
		'type': 'info'
	}]
	# Deep inspection for titles
	title_match = re.search(r'<title>(.*?)</title>', script_output, re.IGNORECASE | re.DOTALL)
	if title_match:
		title = title_match.group(1).strip()
		vulns.append({
			'name': f'{title} (Service Fingerprint)',
			'severity': 0,
			'description': f'Extracted title "{title}" from service fingerprint.',
			'type': 'info',
			'tags': ['auth_portal'] if any(x in title.lower() for x in ['vpn', 'portal', 'login', 'auth', 'admin']) else []
		})
	return vulns


def parse_nmap_http_title_output(script_output):
	title = script_output.strip()
	return [{
		'name': f'HTTP Title: {title}',
		'severity': 0,
		'description': f'Detected HTTP page title: {title}',
		'type': 'info',
		'tags': ['auth_portal'] if any(x in title.lower() for x in ['vpn', 'portal', 'login', 'auth', 'admin']) else []
	}]


def parse_nmap_generic_vuln_output(script_id, script_output):
	if not script_output or not script_output.strip():
		return []

	lower_output = script_output.lower()

	# List of common "negative" indicators in nmap script output
	false_positive_indicators = [
		"couldn't find",
		"could not find",
		"error: script execution failed",
		"no reply from server",
		"timeout",
		"did not work",
		"might not be vulnerable",
		"not vulnerable",
		"no findings",
		"0 vulnerabilities found",
		"no vulnerabilities found",
		"vulnerabilities: 0",
		"vulnerable: no",
	]

	if any(indicator in lower_output for indicator in false_positive_indicators):
		return []

	return [{
		'name': f'Nmap Vuln Script: {script_id}',
		'severity': 2, # Medium by default for vuln scripts
		'description': f'Nmap script {script_id} flagged a potential issue:\n{script_output}',
		'type': 'Vulnerability',
		'tags': ['auth_portal'] if any(x in script_output.lower() for x in ['login', 'auth', 'brute', 'password']) else []
	}]



def parse_nmap_http_csrf_output(script_output):
	pass


def parse_nmap_vulscan_output(script_output):
	"""Parse nmap vulscan script output.

	Args:
		script_output (str): Vulscan script output.

	Returns:
		list: List of Vulnerability dicts.
	"""
	data = {}
	vulns = []
	provider_name = ''

	# Sort all vulns found by provider so that we can match each provider with
	# a function that pulls from its API to get more info about the
	# vulnerability.
	for line in script_output.splitlines():
		if not line:
			continue
		if not line.startswith('['): # provider line
			if "No findings" in line:
				logger.info(f"No findings: {line}")
				continue
			elif ' - ' in line:
				provider_name, provider_url = tuple(line.split(' - '))
				data[provider_name] = {'url': provider_url.rstrip(':'), 'entries': []}
				continue
			else:
				# Log a warning
				logger.warning(f"Unexpected line format: {line}")
				continue
		reg = r'\[(.*)\] (.*)'
		matches = re.match(reg, line)
		id, title = matches.groups()
		entry = {'id': id, 'title': title}
		data[provider_name]['entries'].append(entry)

	logger.warning('Vulscan parsed output:')
	logger.warning(pprint.pformat(data))

	for provider_name in data:
		if provider_name == 'Exploit-DB':
			logger.error(f'Provider {provider_name} is not supported YET.')
			pass
		elif provider_name == 'IBM X-Force':
			logger.error(f'Provider {provider_name} is not supported YET.')
			pass
		elif provider_name == 'MITRE CVE':
			logger.error(f'Provider {provider_name} is not supported YET.')
			for entry in data[provider_name]['entries']:
				cve_id = entry['id']
				vuln = cve_to_vuln(cve_id)
				vulns.append(vuln)
		elif provider_name == 'OSVDB':
			logger.error(f'Provider {provider_name} is not supported YET.')
			pass
		elif provider_name == 'OpenVAS (Nessus)':
			logger.error(f'Provider {provider_name} is not supported YET.')
			pass
		elif provider_name == 'SecurityFocus':
			logger.error(f'Provider {provider_name} is not supported YET.')
			pass
		elif provider_name == 'VulDB':
			logger.error(f'Provider {provider_name} is not supported YET.')
			pass
		else:
			logger.error(f'Provider {provider_name} is not supported.')
	return vulns


def get_severity_from_cvss(cvss_score):
	"""Get severity integer from CVSS score."""
	if cvss_score < 4:
		return NUCLEI_SEVERITY_MAP['low']
	elif cvss_score < 7:
		return NUCLEI_SEVERITY_MAP['medium']
	elif cvss_score < 9:
		return NUCLEI_SEVERITY_MAP['high']
	else:
		return NUCLEI_SEVERITY_MAP['critical']


def parse_nmap_vulners_output(script_output, url='', service_title=''):
	"""Parse nmap vulners script output.

	Args:
		script_output (str): Script output.

	Returns:
		list: List of found vulnerabilities.
	"""
	if not script_output or not isinstance(script_output, str):
		return []
	vulns = []
	lines = script_output.split('\n')
	for line in lines:
		line = line.strip()
		# Typical line: ID   SCORE   URL   [*EXPLOIT*]
		# Example: PACKETSTORM:173661      9.8     https://vulners.com/packetstorm/PACKETSTORM:173661      *EXPLOIT*
		parts = re.split(r'\s+', line)
		if len(parts) >= 3:
			vuln_id = parts[0]
			try:
				vuln_cvss = float(parts[1])
			except (ValueError, TypeError):
				continue # Not a vuln line

			vuln_url = parts[2]
			is_exploit = '*EXPLOIT*' in line

			# Determine a better vulnerability name
			vuln_name = vuln_id
			if service_title:
				vuln_name = f"{service_title} ({vuln_id})"

			# Extract tags
			tags = []
			if is_exploit:
				tags.append('is exploit')
			
			source_tag = ''
			vuln_url_lower = vuln_url.lower()
			if 'packetstorm' in vuln_url_lower:
				source_tag = 'packetstorm'
			elif 'githubexploit' in vuln_url_lower:
				source_tag = 'githubexploit'
			elif 'seebug' in vuln_url_lower or 'ssv:' in vuln_id.lower():
				source_tag = 'seebug'
			elif 'zdt' in vuln_url_lower or '1337day' in vuln_url_lower or '1337day' in vuln_id.lower():
				source_tag = '1337day'
			elif 'exploit-db' in vuln_url_lower or 'edb' in vuln_id.lower():
				source_tag = 'exploit-db'
			
			if source_tag:
				tags.append(source_tag)

			# Create a base vulnerability object
			vuln = {
				'name': vuln_name,
				'type': 'nmap-vulners-nse',
				'severity': get_severity_from_cvss(vuln_cvss),
				'description': f"Vulnerability found by nmap vulners script: {vuln_id}. Product: {service_title}",
				'cvss_score': vuln_cvss,
				'references': [vuln_url],
				'cve_ids': [],
				'cwe_ids': [],
				'tags': tags
			}

			# If it's a CVE, try to enrich it with cve_to_vuln
			if vuln_id.startswith('CVE-'):
				enriched_vuln = cve_to_vuln(vuln_id, vuln_type='nmap-vulners-nse')
				if enriched_vuln:
					# Use enriched data but keep some nmap specifics if needed
					old_tags = vuln.get('tags', [])
					vuln.update(enriched_vuln)
					
					# Merge tags
					if 'tags' not in vuln:
						vuln['tags'] = []
					vuln['tags'].extend(old_tags)
					vuln['tags'] = list(set(vuln['tags']))
					
					# Improve name if service_title is present
					if service_title:
						# If enriched name is just the CVE, use service title
						if enriched_vuln.get('name') == vuln_id:
							vuln['name'] = f"{service_title} ({vuln_id})"
						else:
							# Combine them if they are different
							if service_title.lower() not in enriched_vuln.get('name', '').lower():
								vuln['name'] = f"{service_title}: {enriched_vuln.get('name')}"
					
					# Ensure the CVSS score from nmap is used if API has -1 or something
					if vuln.get('cvss_score', -1) == -1:
						vuln['cvss_score'] = vuln_cvss
						vuln['severity'] = get_severity_from_cvss(vuln_cvss)

			if vuln:
				vuln['source'] = 'VULNERS'
				if is_exploit:
					vuln['exploit_url'] = vuln_url
				vulns.append(vuln)

	# If no structured findings found, fallback to the old regex
	if not vulns:
		# Check for CVE in script output
		CVE_REGEX = re.compile(r'.*(CVE-\d\d\d\d-\d+).*')
		matches = CVE_REGEX.findall(script_output)
		matches = list(dict.fromkeys(matches))
		for cve_id in matches: # get CVE info
			vuln = cve_to_vuln(cve_id, vuln_type='nmap-vulners-nse')
			if vuln:
				vuln['source'] = 'VULNERS'
				vulns.append(vuln)
	return vulns


def cve_to_vuln(cve_id, vuln_type=''):
	"""Search for a CVE using CVESearch and return Vulnerability data.

	Args:
		cve_id (str): CVE ID in the form CVE-*

	Returns:
		dict: Vulnerability dict.
	"""
	cve_info = CVESearch('https://cve.circl.lu').id(cve_id)
	if not cve_info:
		logger.error(f'Could not fetch CVE info for cve {cve_id}. Skipping.')
		return None
	vuln_cve_id = cve_info.get('id', cve_info.get('CVE', cve_id))
	vuln_name = vuln_cve_id
	vuln_description = cve_info.get('summary', 'none').replace(vuln_cve_id, '').strip()
	try:
		vuln_cvss = float(cve_info.get('cvss', -1))
	except (ValueError, TypeError):
		vuln_cvss = -1
	vuln_cwe_id = cve_info.get('cwe', '')
	exploit_ids = cve_info.get('refmap', {}).get('exploit-db', [])
	osvdb_ids = cve_info.get('refmap', {}).get('osvdb', [])
	references = cve_info.get('references', [])
	capec_objects = cve_info.get('capec', [])

	# Parse ovals for a better vuln name / type
	ovals = cve_info.get('oval', [])
	if ovals and isinstance(ovals, list) and len(ovals) > 0:
		vuln_name = ovals[0].get('title', vuln_name)
		vuln_type = ovals[0].get('family', vuln_type)

	# Set vulnerability severity based on CVSS score
	vuln_severity = 'info'
	if vuln_cvss < 4:
		vuln_severity = 'low'
	elif vuln_cvss < 7:
		vuln_severity = 'medium'
	elif vuln_cvss < 9:
		vuln_severity = 'high'
	else:
		vuln_severity = 'critical'

	# Build console warning message
	msg = f'{vuln_name} | {vuln_severity.upper()} | {vuln_cve_id} | {vuln_cwe_id} | {vuln_cvss}'
	for id in osvdb_ids:
		msg += f'\n\tOSVDB: {id}'
	for exploit_id in exploit_ids:
		msg += f'\n\tEXPLOITDB: {exploit_id}'
	logger.warning(msg)
	vuln = {
		'name': vuln_name,
		'type': vuln_type,
		'severity': NUCLEI_SEVERITY_MAP[vuln_severity],
		'description': vuln_description,
		'cvss_score': vuln_cvss,
		'references': references,
		'cve_ids': [vuln_cve_id],
		'cwe_ids': [vuln_cwe_id]
	}
	return vuln


def parse_s3scanner_result(line):
	'''
		Parses and returns s3Scanner Data
	'''
	bucket = line['bucket']
	return {
		'name': bucket['name'],
		'region': bucket['region'],
		'provider': bucket['provider'],
		'owner_display_name': bucket['owner_display_name'],
		'owner_id': bucket['owner_id'],
		'perm_auth_users_read': bucket['perm_auth_users_read'],
		'perm_auth_users_write': bucket['perm_auth_users_write'],
		'perm_auth_users_read_acl': bucket['perm_auth_users_read_acl'],
		'perm_auth_users_write_acl': bucket['perm_auth_users_write_acl'],
		'perm_auth_users_full_control': bucket['perm_auth_users_full_control'],
		'perm_all_users_read': bucket['perm_all_users_read'],
		'perm_all_users_write': bucket['perm_all_users_write'],
		'perm_all_users_read_acl': bucket['perm_all_users_read_acl'],
		'perm_all_users_write_acl': bucket['perm_all_users_write_acl'],
		'perm_all_users_full_control': bucket['perm_all_users_full_control'],
		'num_objects': bucket['num_objects'],
		'size': bucket['bucket_size']
	}


def parse_nuclei_result(line):
	"""Parse results from nuclei JSON output.

	Args:
		line (dict): Nuclei JSON line output.

	Returns:
		dict: Vulnerability data.
	"""
	return {
		'name': line['info'].get('name', ''),
		'type': line['type'],
		'severity': NUCLEI_SEVERITY_MAP[line['info'].get('severity', 'unknown')],
		'template': line['template'],
		'template_url': line.get('template-url', []),
		'template_id': line['template-id'],
		'description': line['info'].get('description', ''),
		'matcher_name': line.get('matcher-name', ''),
		'curl_command': line.get('curl-command'),
		'request': line.get('request'),
		'response': line.get('response'),
		'extracted_results': line.get('extracted-results', []),
		'cvss_metrics': line['info'].get('classification', {}).get('cvss-metrics', ''),
		'cvss_score': line['info'].get('classification', {}).get('cvss-score'),
		'cve_ids': line['info'].get('classification', {}).get('cve_id', []) or [],
		'cwe_ids': line['info'].get('classification', {}).get('cwe_id', []) or [],
		'references': line['info'].get('reference', []) or [],
		'tags': line['info'].get('tags', []) or [],
		'source': NUCLEI,
	}


def parse_dalfox_result(line):
	"""Parse results from nuclei JSON output.

	Args:
		line (dict): Nuclei JSON line output.

	Returns:
		dict: Vulnerability data.
	"""

	description = ''
	description += f" Evidence: {line.get('evidence')} <br>" if line.get('evidence') else ''
	description += f" Message: {line.get('message')} <br>" if line.get('message') else ''
	description += f" Payload: {line.get('message_str')} <br>" if line.get('message_str') else ''
	description += f" Vulnerable Parameter: {line.get('param')} <br>" if line.get('param') else ''

	return {
		'name': 'XSS (Cross Site Scripting)',
		'type': 'XSS',
		'severity': DALFOX_SEVERITY_MAP[line.get('severity', 'unknown')],
		'description': description,
		'source': DALFOX,
		'cwe_ids': [line.get('cwe')]
	}


def parse_crlfuzz_result(url):
	"""Parse CRLF results

	Args:
		url (str): CRLF Vulnerable URL

	Returns:
		dict: Vulnerability data.
	"""

	return {
		'name': 'CRLF (HTTP Response Splitting)',
		'type': 'CRLF',
		'severity': 2,
		'description': 'A CRLF (HTTP Response Splitting) vulnerability has been discovered.',
		'source': CRLFUZZ,
	}



@app.task(name='geo_localize', bind=False, queue='geo_localize_queue')
def geo_localize(host, ip_id=None, scan_id=None, activity_id=None):
	"""Uses geoiplookup to find location associated with host.

	Args:
		host (str): Hostname.
		ip_id (int): IpAddress object id.
		scan_id (int): ScanHistory object id.
		activity_id (int): ScanActivity object id.

	Returns:
		startScan.models.CountryISO: CountryISO object from DB or None.
	"""
	import ipaddress
	import re
	
	geo_object = None
	country_iso = "Unknown"
	country_name = "Unknown Location"

	# Check if IP is private
	try:
		ip_obj = ipaddress.ip_address(host)
		if ip_obj.is_private:
			country_iso = "PV"
			country_name = "Private Network"
		elif ip_obj.version == 6:
			# geoiplookup often doesn't support IPv6 in the default DB
			# We'll mark it as Unknown (IPv6) for now
			country_iso = "IPv6"
			country_name = "IPv6 Address"
	except ValueError:
		# Not a valid IP (could be a hostname)
		pass

	if country_iso == "Unknown":
		cmd = f'geoiplookup {host}'
		_, out = run_command(cmd, scan_id=scan_id, activity_id=activity_id)
		if 'IP Address not found' not in out and "can't resolve hostname" not in out and ':' in out:
			try:
				# Use regex for more robust parsing of geoiplookup output
				# Typical format: "GeoIP Country Edition: US, United States"
				# We look for the line containing "Country Edition" for precision
				match = re.search(r"Country Edition:\s*([A-Z0-9]{2,}),\s*(.*)", out)
				if match:
					country_iso = match.group(1).strip()
					country_name = match.group(2).strip()
				else:
					# Fallback to general colon-based split if specific line not found
					parts = out.split(':')[1].strip().split(',')
					country_iso = parts[0].strip()
					country_name = parts[1].strip() if len(parts) > 1 else country_iso
			except Exception as e:
				logger.error(f"Error parsing geoiplookup output for {host}: {e}")
		else:
			logger.info(f'Geo IP lookup failed for host "{host}"')

	geo_object, _ = CountryISO.objects.get_or_create(
		iso=country_iso,
		defaults={'name': country_name}
	)

	if ip_id:
		IpAddress.objects.filter(id=ip_id).update(geo_iso=geo_object)

	return geo_object


@app.task(name='query_whois', bind=False, queue='query_whois_queue')
def query_whois(target, force_reload_whois=False, scan_id=None, activity_id=None):
	"""Query WHOIS information for an IP or a domain name.

	Args:
		target (str): IP address or domain name.
		save_domain (bool): Whether to save domain or not, default False
	Returns:
		dict: WHOIS information.
	"""
	try:
		# TODO: Implement cache whois only for 48 hours otherwise get from whois server
		# TODO: in 3.0
		if not force_reload_whois:
			logger.info(f'Querying WHOIS information for {target} from db...')
			domain_info = get_domain_info_from_db(target)
			if domain_info:
				return format_whois_response(domain_info)
			
		# Query WHOIS information as not found in db
		logger.info(f'Whois info not found in db')
		logger.info(f'Querying WHOIS information for {target} from WHOIS server...')

		domain_info = DottedDict()
		domain_info.target = target

		whois_data = None
		related_domains = []

		with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
			futures_func = {
				executor.submit(get_domain_historical_ip_address, target): 'historical_ips',
				executor.submit(fetch_related_tlds_and_domains, target, scan_id=scan_id, activity_id=activity_id): 'related_tlds_and_domains',
				executor.submit(reverse_whois, target): 'reverse_whois',
				executor.submit(fetch_whois_data_using_netlas, target, scan_id=scan_id, activity_id=activity_id): 'whois_data',
			}

			for future in concurrent.futures.as_completed(futures_func):
				func_name = futures_func[future]
				try:
					result = future.result()
					if func_name == 'historical_ips':
						domain_info.historical_ips = result
					elif func_name == 'related_tlds_and_domains':
						domain_info.related_tlds, tlsx_related_domain = result
					elif func_name == 'reverse_whois':
						related_domains = result
					elif func_name == 'whois_data':
						whois_data = result

					logger.debug('*'*100)
					logger.info(f'Task {func_name} finished for target {target}')
					logger.debug(result)
					logger.debug('*'*100)

				except Exception as e:
					logger.error(f'An error occurred while fetching {func_name} for {target}: {str(e)}')
					continue

		logger.info(f'All concurrent whosi lookup tasks finished for target {target}')

		if 'tlsx_related_domain' in locals():
			related_domains += tlsx_related_domain
		
		whois_data = whois_data.get('data', {})

		# related domains can also be fetched from whois_data
		whois_related_domains = whois_data.get('related_domains', [])
		related_domains += whois_related_domains

		# remove duplicate ones
		related_domains = list(set(related_domains))
		domain_info.related_domains = related_domains


		parse_whois_data(domain_info, whois_data)
		saved_domain_info = save_domain_info_to_db(target, domain_info)
		return format_whois_response(domain_info)
	except Exception as e:
		logger.error(f'An error occurred while querying WHOIS information for {target}: {str(e)}')
		return {
			'status': False, 
			'target': target, 
			'result': f'An error occurred while querying WHOIS information for {target}: {str(e)}'
		}


def fetch_related_tlds_and_domains(domain, scan_id=None, activity_id=None):
	"""
	Fetch related TLDs and domains using TLSx.
	related domains are those that are not part of related TLDs.
	
	Args:
		domain (str): The domain to find related TLDs and domains for.
	
	Returns:
		tuple: A tuple containing two lists (related_tlds, related_domains).
	"""
	logger.info(f"Fetching related TLDs and domains for {domain}")
	related_tlds = set()
	related_domains = set()
	
	# Extract the base domain
	extracted = tldextract.extract(domain)
	base_domain = f"{extracted.domain}.{extracted.suffix}"
	
	cmd = f'tlsx -san -cn -silent -ro -host {domain}'
	_, result = run_command(cmd, shell=True, scan_id=scan_id, activity_id=activity_id)

	for line in result.splitlines():
		try:
				line = line.strip()
				if line == "":
					continue
				extracted_result = tldextract.extract(line)
				full_domain = f"{extracted_result.domain}.{extracted_result.suffix}"
				
				if extracted_result.domain == extracted.domain:
					if full_domain != base_domain:
						related_tlds.add(full_domain)
				elif extracted_result.domain != extracted.domain or extracted_result.subdomain:
					related_domains.add(line)
		except Exception as e:
			logger.error(f"An error occurred while fetching related TLDs and domains for {domain}: {str(e)}")
			continue
	
	logger.info(f"Found {len(related_tlds)} related TLDs and {len(related_domains)} related domains for {domain}")
	return list(related_tlds), list(related_domains)


def fetch_whois_data_using_netlas(target, scan_id=None, activity_id=None):
	"""
		Fetch WHOIS data using netlas.
		Args:
			target (str): IP address or domain name.
		Returns:
			dict: WHOIS information.
	"""
	logger.info(f'Fetching WHOIS data for {target} using Netlas...')
	command = f'netlas host {target} -f json'
	netlas_key = get_netlas_key()
	if netlas_key:
		command += f' -a {netlas_key}'

	try:
		_, result = run_command(command, remove_ansi_sequence=True, scan_id=scan_id, activity_id=activity_id)
		
		# catch errors
		if 'Failed to parse response data' in result:
			return {
				'status': False, 
				'message': 'Netlas limit exceeded.'
			}
		
		if 'api key doesn\'t exist' in result:
			return {
				'status': False, 
				'message': 'Invalid Netlas API Key!'
			}
		
		if 'Request limit' in result:
			return {
				'status': False, 
				'message': 'Netlas request limit exceeded.'
			}
		
		data = json.loads(result)

		if not data:
			return {
				'status': False, 
				'message': 'No data available for the given domain or IP.'
			}
		# if 'whois' not in data:
		# 	return {
		# 		'status': False, 
		# 		'message': 'Invalid domain or no WHOIS data available.'
		# 	}

		return {
			'status': True, 
			'data': data
		}

	except json.JSONDecodeError:
		return {
			'status': False, 
			'message': 'Failed to parse JSON response from Netlas.'
		}
	except Exception as e:
		return {
			'status': False, 
			'message': f'An error occurred while fetching WHOIS data: {str(e)}'
		}
	

@app.task(name='remove_duplicate_endpoints', bind=False, queue='remove_duplicate_endpoints_queue')
def remove_duplicate_endpoints(
		scan_history_id,
		domain_id,
		subdomain_id=None,
		filter_ids=[],
		filter_status=[200, 301, 404],
		duplicate_removal_fields=ENDPOINT_SCAN_DEFAULT_DUPLICATE_FIELDS
	):
	"""Remove duplicate endpoints.

	Check for implicit redirections by comparing endpoints:
	- [x] `content_length` similarities indicating redirections
	- [x] `page_title` (check for same page title)
	- [ ] Sign-in / login page (check for endpoints with the same words)

	Args:
		scan_history_id: ScanHistory id.
		domain_id (int): Domain id.
		subdomain_id (int, optional): Subdomain id.
		filter_ids (list): List of endpoint ids to filter on.
		filter_status (list): List of HTTP status codes to filter on.
		duplicate_removal_fields (list): List of Endpoint model fields to check for duplicates
	"""
	logger.info(f'Removing duplicate endpoints based on {duplicate_removal_fields}')
	endpoints = (
		EndPoint.objects
		.filter(scan_history__id=scan_history_id)
		.filter(target_domain__id=domain_id)
	)
	if filter_status:
		endpoints = endpoints.filter(http_status__in=filter_status)

	if subdomain_id:
		endpoints = endpoints.filter(subdomain__id=subdomain_id)

	if filter_ids:
		endpoints = endpoints.filter(id__in=filter_ids)

	for field_name in duplicate_removal_fields:
		cl_query = (
			endpoints
			.values_list(field_name)
			.annotate(mc=Count(field_name))
			.order_by('-mc')
		)
		for (field_value, count) in cl_query:
			if count > DELETE_DUPLICATES_THRESHOLD:
				eps_to_delete = (
					endpoints
					.filter(**{field_name: field_value})
					.order_by('discovered_date')
					.all()[1:]
				)
				msg = f'Deleting {len(eps_to_delete)} endpoints [reason: same {field_name} {field_value}]'
				for ep in eps_to_delete:
					url = urlparse(ep.http_url)
					if url.path in ['', '/', '/login']: # try do not delete the original page that other pages redirect to
						continue
					msg += f'\n\t {ep.http_url} [{ep.http_status}] [{field_name}={field_value}]'
					ep.delete()
				logger.warning(msg)

# run_command, sanitize_command_for_db and stream_command moved to task_utils.py


#-------------#
# Other utils #
#-------------#


def process_httpx_response(line, ctx={}, is_ran_from_subdomain_scan=False):
	"""Process a single line of httpx output and save to database."""
	if not line or not isinstance(line, dict):
		return None, False

	# No response from endpoint
	if line.get('failed', False):
		return None, False

	# Parse httpx output
	http_status = line.get('status_code')
	http_url, is_redirect = extract_httpx_url(line)
	content_length = line.get('content_length', 0)
	page_title = line.get('title')
	webserver = line.get('webserver')
	rt = line.get('time')
	content_type = line.get('content_type', '')
	
	response_time = -1
	if rt:
		response_time = float(''.join(ch for ch in rt if not ch.isalpha()))
		if rt[-2:] == 'ms':
			response_time = response_time / 1000

	# Create Subdomain object in DB
	subdomain_name = get_subdomain_from_url(http_url)
	subdomain, _ = save_subdomain(subdomain_name, ctx=ctx)

	if not subdomain:
		return None, False

	# Save default HTTP URL to endpoint object in DB
	endpoint, created = save_endpoint(
		http_url,
		crawl=False,
		ctx=ctx,
		subdomain=subdomain,
		is_default=is_ran_from_subdomain_scan
	)
	if not endpoint:
		return None, False
	
	endpoint.http_status = http_status
	endpoint.page_title = page_title
	endpoint.content_length = content_length
	endpoint.webserver = webserver
	endpoint.response_time = response_time
	endpoint.content_type = content_type
	endpoint.is_redirect = is_redirect
	endpoint.save()

	# Sync Subdomain status attributes if this is the default endpoint
	if is_ran_from_subdomain_scan:
		subdomain.http_status = http_status
		subdomain.page_title = page_title
		subdomain.content_length = content_length
		subdomain.webserver = webserver
		subdomain.response_time = response_time
		subdomain.content_type = content_type
		subdomain.http_url = http_url
		subdomain.save()
	
	return endpoint, created


def extract_httpx_url(line):
	"""Extract final URL from httpx results. Always follow redirects to find
	the last URL.

	Args:
		line (dict): URL data output by httpx.

	Returns:
		tuple: (final_url, redirect_bool) tuple.
	"""
	status_code = line.get('status_code', 0)
	final_url = line.get('final_url')
	location = line.get('location')
	chain_status_codes = line.get('chain_status_codes', [])

	# Final URL is already looking nice, if it exists return it
	if final_url:
		return final_url, False
	http_url = line['url'] # fallback to url field

	# Handle redirects manually
	REDIRECT_STATUS_CODES = [301, 302]
	is_redirect = (
		status_code in REDIRECT_STATUS_CODES
		or
		any(x in REDIRECT_STATUS_CODES for x in chain_status_codes)
	)
	if is_redirect and location:
		if location.startswith(('http', 'https')):
			http_url = location
		else:
			http_url = f'{http_url}/{location.lstrip("/")}'

	# Sanitize URL
	http_url = sanitize_url(http_url)

	return http_url, is_redirect


#-------------#
# OSInt utils #
#-------------#
def get_and_save_dork_results(lookup_target, results_dir, type, lookup_keywords=None, lookup_extensions=None, delay=3, page_count=2, scan_history=None, activity_id=None):
	"""
		Uses gofuzz to dork and store information

		Args:
			lookup_target (str): target to look into such as stackoverflow or even the target itself
			results_dir (str): Results directory
			type (str): Dork Type Title
			lookup_keywords (str): comma separated keywords or paths to look for
			lookup_extensions (str): comma separated extensions to look for
			delay (int): delay between each requests
			page_count (int): pages in google to extract information
			scan_history (startScan.ScanHistory): Scan History Object
	"""
	results = []
	# Use quotes around arguments to handle spaces and special characters safely in the shell
	gofuzz_command = f'{GOFUZZ_EXEC_PATH} -t "{lookup_target}" -d {delay} -p {page_count}'
	proxy = get_random_proxy()

	if lookup_extensions:
		gofuzz_command += f' -e "{lookup_extensions}"'
	elif lookup_keywords:
		# Double quote keywords to preserve complex dork queries, escaping any inner quotes
		escaped_keywords = lookup_keywords.replace('"', '\\"')
		gofuzz_command += f' -w "{escaped_keywords}"'

	if proxy:
		gofuzz_command += f' -r "{proxy}"'

	output_file = f'{results_dir}/gofuzz.txt'
	gofuzz_command += f' -o "{output_file}"'
	history_file = f'{results_dir}/commands.txt'

	try:
		run_command(
			gofuzz_command,
			shell=True, # Use shell=True to handle quoted arguments correctly
			history_file=history_file,
			scan_id=scan_history.id if scan_history else None,
			activity_id=activity_id,
			proxy=proxy
		)

		if not os.path.isfile(output_file):
			return

		with open(output_file) as f:
			for line in f.readlines():
				url = line.strip()
				if url:
					results.append(url)
					dork, created = Dork.objects.get_or_create(
						type=type,
						url=url
					)
					if scan_history:
						scan_history.dorks.add(dork)

		# remove output file
		os.remove(output_file)

	except Exception as e:
		logger.exception(e)

	return results

def save_metadata_info(meta_dict):
	"""Extract metadata from Google Search.

	Args:
		meta_dict (dict): Info dict.

	Returns:
		list: List of startScan.MetaFinderDocument objects.
	"""
	logger.warning(f'Getting metadata for {meta_dict.osint_target}')

	scan_history = ScanHistory.objects.get(id=meta_dict.scan_id)

	# Proxy settings
	proxy = get_random_proxy()

	# Get metadata
	try:
		result = extract_metadata_from_google_search(meta_dict.osint_target, meta_dict.documents_limit)
	except Exception as e:
		logger.error(f'Error extracting metadata from Google Search for {meta_dict.osint_target}: {str(e)}')
		return []

	if not result:
		logger.error(f'No metadata result from Google Search for {meta_dict.osint_target}.')
		return []

	# Add metadata info to DB
	results = []
	for metadata_name, data in result.get_metadata().items():
		subdomain = Subdomain.objects.get(
			scan_history=meta_dict.scan_id,
			name=meta_dict.osint_target)
		metadata = DottedDict({k: v for k, v in data.items()})
		meta_finder_document = MetaFinderDocument(
			subdomain=subdomain,
			target_domain=meta_dict.domain,
			scan_history=scan_history,
			url=metadata.url,
			doc_name=metadata_name,
			http_status=metadata.status_code,
			producer=metadata.metadata.get('Producer'),
			creator=metadata.metadata.get('Creator'),
			creation_date=metadata.metadata.get('CreationDate'),
			modified_date=metadata.metadata.get('ModDate'),
			author=metadata.metadata.get('Author'),
			title=metadata.metadata.get('Title'),
			os=metadata.metadata.get('OSInfo'))
		meta_finder_document.save()
		results.append(data)
	return results


#-----------------#
# Utils functions #
#-----------------#
def create_scan_activity(scan_history_id, message, status):
	scan_activity = ScanActivity()
	scan_activity.scan_of = ScanHistory.objects.get(pk=scan_history_id)
	scan_activity.title = message
	scan_activity.time = timezone.now()
	scan_activity.status = status
	scan_activity.save()
	return scan_activity.id


#--------------------#
# Database functions #
#--------------------#
def save_endpoint(
		http_url,
		ctx={},
		crawl=False,
		is_default=False,
		**endpoint_data):
	"""Get or create EndPoint object. If crawl is True, also crawl the endpoint
	HTTP URL with httpx.

	Args:
		http_url (str): Input HTTP URL.
		is_default (bool): If the url is a default url for SubDomains.
		scan_history (startScan.models.ScanHistory): ScanHistory object.
		domain (startScan.models.Domain): Domain object.
		subdomain (starScan.models.Subdomain): Subdomain object.
		results_dir (str, optional): Results directory.
		crawl (bool, optional): Run httpx on endpoint if True. Default: False.
		force (bool, optional): Force crawl even if ENABLE_HTTP_CRAWL mode is on.
		subscan (startScan.models.SubScan, optional): SubScan object.

	Returns:
		tuple: (startScan.models.EndPoint, created) where `created` is a boolean
			indicating if the object is new or already existed.
	"""
	# remove nulls
	endpoint_data = replace_nulls(endpoint_data)

	scheme = urlparse(http_url).scheme
	endpoint = None
	created = False
	if ctx.get('domain_id'):
		domain = Domain.objects.get(id=ctx.get('domain_id'))
		if domain.name not in http_url:
			logger.error(f"{http_url} is not a URL of domain {domain.name}. Skipping.")
			return None, False
	if crawl:
		ctx['track'] = False
		results = http_crawl(
			urls=[http_url],
			method='HEAD',
			ctx=ctx)
		if results and isinstance(results, list) and isinstance(results[0], dict):
			endpoint_data = results[0]
			if 'endpoint_id' in endpoint_data:
				endpoint_id = endpoint_data['endpoint_id']
				created = endpoint_data.get('endpoint_created', False)
				endpoint = EndPoint.objects.get(pk=endpoint_id)
	elif not scheme:
		return None, False
	else: # add dumb endpoint without probing it
		scan = ScanHistory.objects.filter(pk=ctx.get('scan_history_id')).first()
		domain = Domain.objects.filter(pk=ctx.get('domain_id')).first()
		if not validators.url(http_url):
			return None, False
		http_url = sanitize_url(http_url)

		# Try to get the first matching record (prevent duplicate error)
		endpoints = EndPoint.objects.filter(
			scan_history=scan,
			target_domain=domain,
			http_url=http_url,
			**endpoint_data
		)

		if endpoints.exists():
			endpoint = endpoints.first()
			created = False
		else:
			# No existing record, create a new one
			endpoint = EndPoint.objects.create(
				scan_history=scan,
				target_domain=domain,
				http_url=http_url,
				**endpoint_data
			)
			created = True

	if created:
		endpoint.is_default = is_default
		endpoint.discovered_date = timezone.now()
		endpoint.save()

		# Centralized Brute-Force Candidate Registration
		auth_keywords = ['login', 'admin', 'auth', 'portal', 'controlpanel', 'signin', 'manage']
		if any(k in http_url.lower() for k in auth_keywords):
			from reNgine.utilities import save_auth_candidate
			try:
				parsed = urlparse(http_url)
				port = parsed.port or (443 if parsed.scheme == 'https' else 80)
				save_auth_candidate(
					scan_history=endpoint.scan_history,
					subdomain=endpoint.subdomain,
					endpoint=endpoint,
					target=parsed.hostname,
					protocol='http',
					port=port,
					source_tool=endpoint_data.get('source_tool', 'discovery_engine'),
					tech_hint=f"Discovered URL: {http_url}"
				)
			except Exception as e:
				logger.error(f"Error registering AuthCandidate from endpoint {http_url}: {e}")
		subscan_id = ctx.get('subscan_id')
		if subscan_id:
			endpoint.endpoint_subscan_ids.add(subscan_id)
			endpoint.save()

	return endpoint, created


def save_subdomain(subdomain_name, ctx={}):
	"""Get or create Subdomain object.

	Args:
		subdomain_name (str): Subdomain name.
		scan_history (startScan.models.ScanHistory): ScanHistory object.

	Returns:
		tuple: (startScan.models.Subdomain, created) where `created` is a
			boolean indicating if the object has been created in DB.
	"""
	scan_id = ctx.get('scan_history_id')
	subscan_id = ctx.get('subscan_id')
	out_of_scope_subdomains = ctx.get('out_of_scope_subdomains', [])
	subdomain_checker = SubdomainScopeChecker(out_of_scope_subdomains)
	valid_domain = (
		validators.domain(subdomain_name) or
		validators.ipv4(subdomain_name) or
		validators.ipv6(subdomain_name)
	)
	if not valid_domain:
		logger.error(f'{subdomain_name} is not an invalid domain. Skipping.')
		return None, False

	if subdomain_checker.is_out_of_scope(subdomain_name):
		logger.error(f'{subdomain_name} is out-of-scope. Skipping.')
		return None, False

	if ctx.get('domain_id'):
		domain = Domain.objects.get(id=ctx.get('domain_id'))
		if domain.name not in subdomain_name:
			logger.error(f"{subdomain_name} is not a subdomain of domain {domain.name}. Skipping.")
			return None, False

	scan = ScanHistory.objects.filter(pk=scan_id).first()
	domain = scan.domain if scan else None
	subdomain, created = Subdomain.objects.get_or_create(
		scan_history=scan,
		target_domain=domain,
		name=subdomain_name)
	if created:
		# logger.warning(f'Found new subdomain {subdomain_name}')
		subdomain.discovered_date = timezone.now()
		if subscan_id:
			subdomain.subdomain_subscan_ids.add(subscan_id)
		subdomain.save()
	return subdomain, created


# save_email and save_employee moved to task_utils.py
def save_ip_address(ip_address, subdomain=None, subscan=None, scan_id=None, activity_id=None, **kwargs):
	if not (validators.ipv4(ip_address) or validators.ipv6(ip_address)):
		logger.info(f'IP {ip_address} is not a valid IP. Skipping.')
		return None, False
	ip, created = IpAddress.objects.get_or_create(address=ip_address)
	if created:
		ip.discovered_date = timezone.now()

	# Trigger geo localization if newly created OR if geo_iso is null
	if created or ip.geo_iso is None:
		geo_localize.delay(ip_address, ip_id=ip.id, scan_id=scan_id, activity_id=activity_id)

	# Set extra attributes
	for key, value in kwargs.items():
		setattr(ip, key, value)
	ip.save()

	# Add IP to subdomain
	if subdomain:
		subdomain.ip_addresses.add(ip)
		subdomain.save()

	# Add subscan to IP
	if subscan:
		ip.ip_subscan_ids.add(subscan)

	# Geo-localize IP asynchronously
	if created:
		geo_localize.delay(ip_address, ip.id)

	return ip, created


def save_secret_leak(scan_history, tool_name, secret_type, source_url, match_content, subdomain=None, status='unverified'):
	leak, created = SecretLeak.objects.get_or_create(
		scan_history=scan_history,
		tool_name=tool_name,
		secret_type=secret_type,
		source_url=source_url,
		match_content=match_content,
		subdomain=subdomain,
	)
	if created:
		leak.status = status
		leak.save()
	return leak, created


def save_imported_subdomains(subdomains, ctx={}):
	"""Take a list of subdomains imported and write them to from_imported.txt.

	Args:
		subdomains (list): List of subdomain names.
		scan_history (startScan.models.ScanHistory): ScanHistory instance.
		domain (startScan.models.Domain): Domain instance.
		results_dir (str): Results directory.
	"""
	domain_id = ctx['domain_id']
	domain = Domain.objects.get(pk=domain_id)
	results_dir = ctx.get('results_dir', RENGINE_RESULTS)

	# Validate each subdomain and de-duplicate entries
	subdomains = list(set([
		subdomain for subdomain in subdomains
		if validators.domain(subdomain) and domain.name == get_domain_from_subdomain(subdomain)
	]))
	if not subdomains:
		return

	logger.warning(f'Found {len(subdomains)} imported subdomains.')
	with open(f'{results_dir}/from_imported.txt', 'w+') as output_file:
		for name in subdomains:
			subdomain_name = name.strip()
			subdomain, _ = save_subdomain(subdomain_name, ctx=ctx)
			subdomain.is_imported_subdomain = True
			subdomain.save()
			output_file.write(f'{subdomain}\n')


@app.task(name='query_reverse_whois', bind=False, queue='query_reverse_whois_queue')
def query_reverse_whois(lookup_keyword):
	"""Queries Reverse WHOIS information for an organization or email address.

	Args:
		lookup_keyword (str): Registrar Name or email
	Returns:
		dict: Reverse WHOIS information.
	"""

	return reverse_whois(lookup_keyword)


@app.task(name='query_ip_history', bind=False, queue='query_ip_history_queue')
def query_ip_history(domain):
	"""Queries the IP history for a domain

	Args:
		domain (str): domain_name
	Returns:
		list: list of historical ip addresses
	"""

	return get_domain_historical_ip_address(domain)


@app.task(name='llm_vulnerability_description', bind=False, queue='llm_queue')
def llm_vulnerability_description(vulnerability_id):
	"""Generate and store Vulnerability Description using GPT.

	Args:
		vulnerability_id (Vulnerability Model ID): Vulnerability ID to fetch Description.
	"""
	logger.info('Getting GPT Vulnerability Description')
	try:
		lookup_vulnerability = Vulnerability.objects.get(id=vulnerability_id)
		return get_vulnerability_gpt_report((lookup_vulnerability.name, lookup_vulnerability.get_path()), vulnerability_id=vulnerability_id)
	except Exception as e:
		return {
			'status': False,
			'error': str(e)
		}


@app.task(name='fetch_proxies_task', bind=True, queue='main_scan_queue')
def fetch_proxies_task(self, limit=1000):
    """Scrape proxies concurrently from a large list of public sources,
    verify their validity against robust target APIs, and return the live ones.

    Args:
        self: The task instance bind.
        limit (int, optional): Maximum number of raw proxies to scrape and check. Defaults to 1000.

    Returns:
        str: Newline-separated list of validated live proxies.
    """
    from reNgine.common_func import check_proxy_robust
    import re

    logger.info(f"Starting automated proxy fetch and verification task (limit={limit}).")
    self.update_state(state='PROGRESS', meta={'message': 'Downloading new proxies', 'progress': 10})
    
    proxy_urls = [
        'https://api.proxyscrape.com/v2/?request=displayproxies',
        'https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/http/http.txt',
        'https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt',
        'https://raw.githubusercontent.com/yuceltoluyag/GoodProxy/main/raw.txt',
        'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
        'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt',
        'https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt',
        'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
        'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies.txt',
        'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt',
        'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
        'https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt',
        'https://raw.githubusercontent.com/opsxcq/proxy-list/master/list.txt',
        'https://proxyspace.pro/http.txt',
        'https://api.proxyscrape.com/?request=displayproxies&proxytype=http',
        'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
        'http://worm.rip/http.txt',
        'http://alexa.lr2b.com/proxylist.txt',
        'https://api.openproxylist.xyz/http.txt',
        'http://rootjazz.com/proxies/proxies.txt',
        'https://multiproxy.org/txt_all/proxy.txt',
        'https://proxy-spider.com/api/proxies.example.txt',
        'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all',
        'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=anonymous',
        'https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt',
        'https://raw.githubusercontent.com/Firdoxx/proxy-list/main/https',
        'https://raw.githubusercontent.com/Firdoxx/proxy-list/main/http',
        'https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt',
        'https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/https.txt',
        'https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt',
        'https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt',
        'https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt',
        'https://raw.githubusercontent.com/ALIILAPRO/Proxy/main/http.txt',
        'https://raw.githubusercontent.com/casals-ar/proxy-list/main/http',
        'https://raw.githubusercontent.com/casals-ar/proxy-list/main/https',
        'https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt',
        'https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt',
        'https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/https.txt',
        'https://raw.githubusercontent.com/Jakee8718/Free-Proxies/main/proxy/-http%20and%20https.txt',
        'https://raw.githubusercontent.com/Tsprnay/Proxy-lists/master/proxies/http.txt',
        'https://raw.githubusercontent.com/Tsprnay/Proxy-lists/master/proxies/https.txt',
        'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt',
        'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt',
        'https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all',
        'https://www.proxy-list.download/api/v1/get?type=socks5',
        'https://raw.githubusercontent.com/manuGMG/proxy-365/main/SOCKS5.txt',
        'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt',
        'https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt',
        'https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt',
        'https://raw.githubusercontent.com/a2u/free-proxy-list/master/free-proxy-list.txt',
        'https://raw.githubusercontent.com/mishakorzik/Free-Proxy/main/proxy.txt',
        'https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt',
        'https://raw.githubusercontent.com/UptimerBot/proxy-list/master/proxies/http.txt',
        'https://github.com/hookzof/socks5_list/blob/master/proxy.txt',
        'https://github.com/jetkai/proxy-list/blob/main/online-proxies/txt/proxies-http.txt',
        'https://github.com/jetkai/proxy-list/blob/main/online-proxies/txt/proxies-https.txt',
        'https://github.com/jetkai/proxy-list/blob/main/online-proxies/txt/proxies-socks4.txt',
        'https://github.com/jetkai/proxy-list/blob/main/online-proxies/txt/proxies-socks5.txt',
        'https://github.com/jetkai/proxy-list/blob/main/online-proxies/txt/proxies.txt',
        'https://github.com/clarketm/proxy-list/blob/master/proxy-list-raw.txt'
    ]

    all_proxies = set()
    for url in proxy_urls:
        if len(all_proxies) >= limit:
            break
            
        if 'github.com' in url and '/blob/' in url:
            url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
            
        logger.info(f"Downloading proxy list from: {url}")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Process lines to extract IP:PORT
                lines = response.text.splitlines()
                added_this_url = 0
                for line in lines:
                    if len(all_proxies) >= limit:
                        break
                        
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('//') or line.startswith('<'):
                        continue
                        
                    # Split by space, comma or semicolon and take the first valid part containing colon
                    parts = re.split(r'[\s,;]+', line)
                    token = parts[0].strip()
                    if ':' in token:
                        if token not in all_proxies:
                            all_proxies.add(token)
                            added_this_url += 1
                            
                logger.info(f"Successfully added {added_this_url} raw proxies from {url}")
            else:
                logger.warning(f"Failed to download proxy list from {url}. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching proxies from {url}: {str(e)}")

    unique_proxies = list(all_proxies)[:limit]
    total = len(unique_proxies)
    logger.info(f"Total unique raw proxies fetched: {total} (capped at {limit})")
    
    self.update_state(state='PROGRESS', meta={'message': f'Verifying {total} proxies', 'progress': 30})

    import threading

    live_proxies = []
    lock = threading.Lock()
    completed_count = [0]
    # Capture task_id here — self.request.id is thread-local and will be None inside spawned threads
    task_id = self.request.id

    N_THREADS = 4
    WORKERS_PER_CHUNK = 13  # 4 * 13 ≈ 52 concurrent IO checks, matching original throughput
    chunk_size = max(1, (total + N_THREADS - 1) // N_THREADS)
    chunks = [unique_proxies[i:i + chunk_size] for i in range(0, total, chunk_size)]

    def check_chunk(chunk):
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS_PER_CHUNK) as pool:
            future_map = {pool.submit(check_proxy_robust, p): p for p in chunk}
            for future in concurrent.futures.as_completed(future_map):
                proxy_str = future_map[future]
                try:
                    alive = future.result()
                except Exception:
                    alive = False
                if alive:
                    logger.info(f"Proxy LIVE: {proxy_str}")
                    print(f"[PROXY LIVE] {proxy_str}", flush=True)
                    with lock:
                        live_proxies.append(proxy_str)
                with lock:
                    completed_count[0] += 1
                    done = completed_count[0]
                if done % 50 == 0 or done == total:
                    logger.info(f"Verification progress: {done}/{total} - Found {len(live_proxies)} live proxies so far.")
                    progress = 30 + int((done / total) * 65)
                    app.backend.store_result(
                        task_id,
                        {'message': f'Checking proxies: {done}/{total} ({len(live_proxies)} live)', 'progress': progress},
                        'PROGRESS'
                    )

    threads = [threading.Thread(target=check_chunk, args=(chunk,), daemon=True) for chunk in chunks]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    logger.info(f"Proxy verification complete. Found {len(live_proxies)} live proxies out of {total} tested.")
    self.update_state(state='PROGRESS', meta={'message': 'Formatting live proxies', 'progress': 95})

    # Prefix with http:// if missing scheme, as requested
    final_list = [f"http://{p}" if not p.startswith('http') and not p.startswith('socks') else p for p in live_proxies]
    
    self.update_state(state='PROGRESS', meta={'message': 'Proxy list updated', 'progress': 100})
    logger.info("Automated proxy fetch task finished successfully.")
    return "\n".join(final_list)


def parse_sslscan_results(xml_file):
	"""Parse results from sslscan XML output file.

	Args:
		xml_file (str): sslscan XML report file path.

	Returns:
		str: Formatted description of SSL/TLS findings.
	"""
	if not os.path.isfile(xml_file):
		return "SSLScan XML report not found."

	try:
		with open(xml_file, 'r', encoding='utf8') as f:
			content = f.read()
		
		data = xmltodict.parse(content) or {}
		document = data.get('document') or {}
		ssltest = document.get('ssltest') or {}
		
		if not ssltest:
			return "No SSLScan results found in the report."
		
		host = ssltest.get('@host', '')
		port = ssltest.get('@port', '')
		
		description = f"SSLScan Results for {host}:{port}\n\n"
		
		# Protocols
		protocols = ssltest.get('protocol', [])
		if protocols is None: protocols = []
		if isinstance(protocols, dict):
			protocols = [protocols]
		
		description += "Protocols:\n"
		for proto in protocols:
			if not proto: continue
			status = "Enabled" if proto.get('@enabled') == '1' else "Disabled"
			description += f"- {proto.get('@type', 'UNKNOWN').upper()} {proto.get('@version', '')}: {status}\n"
		description += "\n"
		
		# Renegotiation
		reneg = ssltest.get('renegotiation') or {}
		if reneg:
			supp = "Supported" if reneg.get('@supported') == '1' else "Not supported"
			sec = "Secure" if reneg.get('@secure') == '1' else "Insecure"
			description += f"Renegotiation: {supp} ({sec})\n\n"
			
		# Heartbleed
		heartbleed = ssltest.get('heartbleed', [])
		if heartbleed is None: heartbleed = []
		if isinstance(heartbleed, dict):
			heartbleed = [heartbleed]
		
		vulnerable_to_heartbleed = False
		for hb in heartbleed:
			if hb and hb.get('@vulnerable') == '1':
				vulnerable_to_heartbleed = True
				break
		
		description += f"Heartbleed: {'Vulnerable' if vulnerable_to_heartbleed else 'Not vulnerable'}\n\n"
		
		# Ciphers
		ciphers = ssltest.get('cipher', [])
		if ciphers is None: ciphers = []
		if isinstance(ciphers, dict):
			ciphers = [ciphers]
		
		preferred_ciphers = [c for c in ciphers if c and c.get('@status') == 'preferred']
		if preferred_ciphers:
			description += "Preferred Ciphers:\n"
			for c in preferred_ciphers:
				description += f"- {c.get('@sslversion', '')}: {c.get('@cipher', '')} ({c.get('@bits', '')} bits, {c.get('@strength', '')} strength)\n"
			description += "\n"
			
		# Certificates
		certificates_sec = ssltest.get('certificates') or {}
		certs = certificates_sec.get('certificate', [])
		if certs is None: certs = []
		if isinstance(certs, dict):
			certs = [certs]
		
		if certs:
			description += "Certificate Information:\n"
			for cert in certs:
				if not cert: continue
				description += f"- Subject: {cert.get('subject', 'N/A')}\n"
				description += f"- Issuer: {cert.get('issuer', 'N/A')}\n"
				description += f"- Signature Algorithm: {cert.get('signature-algorithm', 'N/A')}\n"
				pk = cert.get('pk') or {}
				description += f"- Key: {pk.get('@type', 'N/A')} {pk.get('@bits', 'N/A')} bits\n"
				description += f"- Not Valid After: {cert.get('not-valid-after', 'N/A')}\n"
				if cert.get('expired') == 'true':
					description += "- Status: EXPIRED\n"
				description += "\n"
			description += "\n"
			
		return description

	except Exception as e:
		logger.exception(e)
		return f"Error parsing SSLScan XML: {str(e)}"


@app.task(name='firewall_vpn_scan', queue='main_scan_queue', base=RengineTask, bind=True)
def firewall_vpn_scan(self, ctx={}, description=None):
	"""
	Specialized scan for Firewalls and VPNs (Sophos focus).
	Runs ike-scan and sslscan.
	"""
	config = self.yaml_configuration.get(FIREWALL_VPN_SCAN) or {}
	run_ike_scan = config.get('run_ike_scan', True)
	run_sslscan = config.get('run_sslscan', True)
	ssl_ports = config.get('ports', [443, 4444, 8443])

	target = self.domain.name

	# 1. IKE-scan
	if run_ike_scan:
		logger.warning(f'Running IKE-scan on {target}')
		ike_output_file = f'{self.results_dir}/ike_scan_{target}.txt'
		# ike-scan does not natively support HTTP/SOCKS proxies
		cmd = f'ike-scan --multiline {target} > {ike_output_file}'
		#proxy = get_random_proxy()
		run_command(
			cmd,
			shell=True,
			history_file=self.history_file,
			scan_id=self.scan_id,
			activity_id=self.activity_id)

		if os.path.isfile(ike_output_file):
			with open(ike_output_file, 'r') as f:
				content = f.read()
			if "Main Mode" in content or "Aggressive Mode" in content:
				vuln_data = {
					'name': 'IPSec VPN Detected',
					'severity': 0,
					'description': f'IKE-scan detected an IPSec VPN service.\n\nResults:\n{content}',
					'http_url': target,
					'type': 'Infrastructure'
				}
				save_vulnerability(target_domain=self.domain, scan_history=self.scan, **vuln_data)

	# 2. SSLScan
	if run_sslscan:
		for port in ssl_ports:
			logger.warning(f'Running SSLScan on {target}:{port}')
			ssl_output_file = f'{self.results_dir}/sslscan_{target}_{port}.xml'
			# sslscan does not natively support proxies
			cmd = f'sslscan --xml={ssl_output_file} {target}:{port}'
			#proxy = get_random_proxy()
			run_command(
				cmd,
				shell=True,
				history_file=self.history_file,
				scan_id=self.scan_id,
				activity_id=self.activity_id)

			if os.path.isfile(ssl_output_file):
				vuln_data = {
					'name': f'SSL/TLS Configuration Audit (Port {port})',
					'severity': 0,
					'description': parse_sslscan_results(ssl_output_file),
					'http_url': f'https://{target}:{port}',
					'type': 'SSL/TLS'
				}
				save_vulnerability(target_domain=self.domain, scan_history=self.scan, **vuln_data)
	
	# Automatic Trigger for Brute Force Scan on Sophos Portals
	if run_sslscan and self.scan.tasks and 'brute_force_scan' in self.scan.tasks:
		auth_targets = [f'https://{target}:{port}' for port in ssl_ports]
		logger.warning(f'Triggering Brute Force Scan for potential Sophos Portals on {target}')
		from reNgine.tasks import brute_force_scan
		brute_force_scan.delay(targets=auth_targets, ctx=ctx)

	return True


@app.task(name='brute_force_scan', queue='main_scan_queue', base=RengineTask, bind=True)
def brute_force_scan(self, targets=[], ctx={}, description=None):
	"""
	Perform centralized brute-force orchestration.
	1. Pull all pending candidates from AuthCandidate table
	2. Execute via BruteForceOrchestrator with OpSec settings
	"""
	logger.info(f"Starting Centralized Brute Force Orchestration for Scan {self.scan_id}")
	
	# Prerequisite: Run Intelligent Form Extraction (Tier 3)
	from reNgine.auth_discovery_tasks import extract_auth_candidates
	extract_auth_candidates.apply(kwargs={'ctx': ctx})
	
	# Initialize Orchestrator
	from reNgine.opsec_utils import BruteForceOrchestrator
	orchestrator = BruteForceOrchestrator(self.scan)
	
	# Extract allowed services from config
	config = self.yaml_configuration.get(BRUTE_FORCE_SCAN) or {}
	allowed_services = config.get(SERVICES, [])
	
	# Extract threads and pass to ctx
	ctx['threads'] = config.get(THREADS, 5)
	
	# Execute orchestration
	results = orchestrator.run_orchestration(ctx=ctx, allowed_services=allowed_services)
	
	total_found = 0
	for res in results:
		total_found += 1
		# Determine URL for reporting
		if res['service'] == 'http':
			report_url = res['target']
		else:
			report_url = f"{res['service']}://{res['target']}:{res['port']}"

		vuln_data = {
			'name': f'Successful Brute-Force: {res["service"].upper()}',
			'severity': 4, # Critical
			'description': f'Successfully identified valid credentials on {res["target"]} via Brutus.\n\n'
						 f'User: {res["user"]}\n'
						 f'Password: {res["password"]}\n'
						 f'Service: {res["service"]}\n'
						 f'Port: {res["port"]}',
			'http_url': report_url,
			'type': 'Broken Authentication'
		}
		save_vulnerability(target_domain=self.domain, scan_history=self.scan, **vuln_data)
		
	logger.info(f"Brute Force Orchestration completed. Credentials Found: {total_found}")
	return True

@app.task(name='pull_ollama_model', queue='main_scan_queue')
def pull_ollama_model(model_name):
    """
    Pulls a model from Ollama and stores progress in cache for live terminal.
    """
    cache_key = f"ollama_pull_log_{model_name}"
    cache.set(cache_key, f"[*] Starting download of {model_name}...\n", 3600)
    
    try:
        url = f"{OLLAMA_INSTANCE}/api/pull"
        payload = {"name": model_name, "stream": True}
        
        response = requests.post(url, json=payload, stream=True, timeout=None)
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                status = data.get('status', '')
                digest = data.get('digest', '')
                total = data.get('total', 0)
                completed = data.get('completed', 0)
                
                if total > 0:
                    percent = round((completed / total) * 100, 2)
                    progress_msg = f"[*] {status} {digest[:12]}... {percent}%\n"
                else:
                    progress_msg = f"[*] {status}\n"
                
                # Append to cache
                current_log = cache.get(cache_key, "")
                # Keep only last 50 lines to prevent cache bloat
                log_lines = current_log.split('\n')[-50:]
                log_lines.append(progress_msg.strip())
                cache.set(cache_key, '\n'.join(log_lines) + '\n', 3600)
                
                if status == 'success':
                    cache.set(f"ollama_pull_status_{model_name}", "success", 3600)
                    return True
                    
    except Exception as e:
        error_msg = f"[!] Error pulling model: {str(e)}\n"
        current_log = cache.get(cache_key, "")
        cache.set(cache_key, current_log + error_msg, 3600)
        cache.set(f"ollama_pull_status_{model_name}", "failed", 3600)
        return False
    
    return True


def map_acunetix_severity(severity):
	# Acunetix: 3 (High), 2 (Medium), 1 (Low), 0 (Informational)
	# reNgine: 4 (Critical), 3 (High), 2 (Medium), 1 (Low), 0 (Info)
	mapping = {
		3: 3,
		2: 2,
		1: 1,
		0: 0
	}
	if isinstance(severity, str):
		sev_map = {'high': 3, 'medium': 2, 'low': 1, 'info': 0}
		return sev_map.get(severity.lower(), 0)
	return mapping.get(severity, 0)


@app.task(name='acunetix_scan', queue='main_scan_queue', base=RengineTask, bind=True)
def acunetix_scan(self, domain_id, scan_history_id=None, ctx={}, description=None):
	"""
	Run Acunetix (AWVS) scan for the given domain.
	"""
	if not Acunetix:
		logger.error("Acunetix library not found. Skipping Acunetix scan.")
		return False
	logger.info(f"Starting Acunetix scan for domain ID: {domain_id}")
	scan_history = ScanHistory.objects.get(pk=scan_history_id) if scan_history_id else None
	domain = Domain.objects.get(pk=domain_id)
	
	# Get credentials from vault
	creds = AcunetixAPIKey.objects.first()
	if not (creds and creds.server_url and creds.api_key):
		logger.error("Acunetix API keys not fully configured in vault. Skipping.")
		return False
	logger.info(f"Acunetix API keys found: {creds.server_url}, {creds.api_key}")
	try:
		acunetix = Acunetix(host=creds.server_url, api=creds.api_key)
		logger.info(f"Acunetix instance created: {acunetix}")
		
		target_url = f"https://{domain.name}"
		logger.info(f"Starting Acunetix scan for {target_url}")
		
		# Use the library's start_scan which typically adds target and starts scan
		# Based on the user provided example
		scan_info = acunetix.start_scan(domain.name)
		target_id = scan_info.get('target_id')
		
		# Now we need to poll for status and fetch findings.
		headers = {
			'X-Auth': creds.api_key,
			'Content-Type': 'application/json'
		}
		base_url = f"{creds.server_url}"
		
		# If target_id wasn't in scan_info, try to find it
		if not target_id:
			targets_data = acunetix.targets()
			target = next((t for t in targets_data.get('targets', []) if domain.name in t['address']), None)
			if target:
				target_id = target['target_id']

		if not target_id:
			logger.error(f"Target {domain.name} not found in Acunetix after start_scan.")
			return False
			
		# Wait for scan to complete
		# We'll poll /api/v1/scans
		scan_id = None
		max_retries = 360 # 1 hour
		retries = 0
		while retries < max_retries:
			scans_resp = requests.get(f"{base_url}/api/v1/scans?q=target_id:{target_id}", headers=headers, verify=False)
			if scans_resp.status_code == 200:
				scans_data = scans_resp.json()
				scans_list = scans_data.get('scans', [])
				if scans_list:
					latest_scan = scans_list[0]
					current_status = latest_scan.get('current_session', {}).get('status')
					
					if current_status == 'completed':
						logger.info(f"Acunetix scan for {domain.name} completed.")
						scan_id = latest_scan.get('scan_id')
						break
					elif current_status in ['failed', 'aborted']:
						logger.error(f"Acunetix scan for {domain.name} {current_status}.")
						return False
			
			time.sleep(10)
			retries += 1
			
		# Fetch Vulnerabilities for the specific scan
		if not scan_id:
			# Fallback to target_id if scan_id not found
			vulns_url = f"{base_url}/api/v1/vulnerabilities?q=target_id:{target_id}"
		else:
			# Fetch vulnerabilities for the specific scan
			# Note: The API for scan vulnerabilities might be different, 
			# but q=scan_id:ID or the sub-resource works in many versions.
			vulns_url = f"{base_url}/api/v1/scans/{scan_id}/vulnerabilities"

		vulns_resp = requests.get(vulns_url, headers=headers, verify=False)
		if vulns_resp.status_code == 200:
			vulns_data = vulns_resp.json()
			for vuln in vulns_data.get('vulnerabilities', []):
				# Get full details for each vuln
				vuln_detail_resp = requests.get(f"{base_url}/api/v1/vulnerabilities/{vuln['vuln_id']}", headers=headers, verify=False)
				if vuln_detail_resp.status_code == 200:
					v_detail = vuln_detail_resp.json()
					
					save_v_data = {
						'scan_history': scan_history,
						'target_domain': domain,
						'source': 'Acunetix',
						'name': v_detail.get('vt_name'),
						'severity': map_acunetix_severity(v_detail.get('severity')),
						'description': v_detail.get('description'),
						'impact': v_detail.get('impact'),
						'remediation': v_detail.get('recommendation'),
						'http_url': v_detail.get('affects_url'),
						'request': v_detail.get('request'),
						'response': v_detail.get('response'),
						'template_id': v_detail.get('vt_id'),
					}
					
					# Handle references, CVEs, CWEs
					refs = []
					for r in v_detail.get('references', []):
						if isinstance(r, dict):
							refs.append(r.get('href'))
						else:
							refs.append(str(r))
					save_v_data['references'] = refs

					# Extract CVEs
					cves = []
					for ref in v_detail.get('references', []):
						if isinstance(ref, dict) and 'CVE-' in ref.get('rel', ''):
							cves.append(ref.get('rel'))
					save_v_data['cve_ids'] = cves

					# Extract CWEs
					cwes = []
					if v_detail.get('cwe_id'):
						cwes.append(f"CWE-{v_detail['cwe_id']}")
					save_v_data['cwe_ids'] = cwes
					
					save_vulnerability(**save_v_data)
					
		return True
		
	except Exception as e:
		logger.error(f"Error in Acunetix scan: {str(e)}")
		return False


@app.task(name='correlate_vulnerabilities', queue='main_scan_queue', base=RengineTask, bind=True)
def correlate_vulnerabilities(self, scan_history_id, ctx={}, description=None):
	"""Correlate discovered technologies with known CVEs and update the graph database.

	Args:
		scan_history_id (int): Scan history ID.
		ctx (dict): Scan context.
	"""
	# Check if there are other scanning tasks still running
	from startScan.models import ScanActivity
	from reNgine.definitions import RUNNING_TASK, INITIATED_TASK
	post_processing_names = ['correlate_vulnerabilities', 'calculate_risk_scores', 'generate_impact_assessment', 'run_apme', 'report']
	
	if self.subscan:
		running_scans = ScanActivity.objects.filter(
			celery_id__in=self.subscan.celery_ids,
			status__in=[RUNNING_TASK, INITIATED_TASK]
		).exclude(name__in=post_processing_names)
	else:
		running_scans = ScanActivity.objects.filter(
			scan_of_id=scan_history_id,
			status__in=[RUNNING_TASK, INITIATED_TASK]
		).exclude(name__in=post_processing_names)

	if running_scans.exists() and not getattr(self, '_is_temporal_proxy', False):
		running_names = list(running_scans.values_list('name', flat=True))
		#logger.info(f"Scanning tasks are still running: {running_names}. Rescheduling correlate_vulnerabilities...")
		raise self.retry(countdown=10, max_retries=1000)

	nm = Neo4jManager()
	try:
		# In a real scenario, this would query a CVE DB. 
		# For now, we sync the graph which now includes Tech and CVE links from Vulnerability models.
		nm.sync_scan_results(scan_history_id)
	except Exception as e:
		logger.error(f"Error in correlate_vulnerabilities: {str(e)}")
	finally:
		nm.close()


@app.task(name='calculate_risk_scores', queue='main_scan_queue', base=RengineTask, bind=True)
def calculate_risk_scores(self, scan_history_id, ctx={}, description=None):
	"""Calculate a weighted risk score for discovered vulnerabilities.

	Args:
		scan_history_id (int): Scan history ID.
		ctx (dict): Scan context.
	"""
	# Check if there are other scanning tasks still running
	from startScan.models import ScanActivity
	from reNgine.definitions import RUNNING_TASK, INITIATED_TASK
	post_processing_names = ['correlate_vulnerabilities', 'calculate_risk_scores', 'generate_impact_assessment', 'run_apme', 'report']
	
	if self.subscan:
		running_scans = ScanActivity.objects.filter(
			celery_id__in=self.subscan.celery_ids,
			status__in=[RUNNING_TASK, INITIATED_TASK]
		).exclude(name__in=post_processing_names)
	else:
		running_scans = ScanActivity.objects.filter(
			scan_of_id=scan_history_id,
			status__in=[RUNNING_TASK, INITIATED_TASK]
		).exclude(name__in=post_processing_names)

	if running_scans.exists() and not getattr(self, '_is_temporal_proxy', False):
		running_names = list(running_scans.values_list('name', flat=True))
		#logger.info(f"Scanning tasks are still running: {running_names}. Rescheduling calculate_risk_scores...")
		raise self.retry(countdown=10, max_retries=1000)

	from reNgine.correlation import VulnerabilityCorrelationEngine
	scan_history = ScanHistory.objects.get(id=scan_history_id)
	correlator = VulnerabilityCorrelationEngine(scan_history=scan_history)
	correlator.correlate_findings()


@app.task(name='generate_impact_assessment', queue='main_scan_queue', base=RengineTask, bind=True)
def generate_impact_assessment(self, scan_history_id=None, vulnerability_id=None, ctx={}, description=None):
	"""Generate an AI-powered impact assessment for vulnerabilities.

	Args:
		scan_history_id (int): Scan history ID.
		vulnerability_id (int): Specific vulnerability ID.
		ctx (dict): Scan context.
	"""
	from reNgine.llm import LLMImpactGenerator
	from reNgine.privacy import PIIGate

	if vulnerability_id:
		vulns = Vulnerability.objects.filter(id=vulnerability_id)
		if not scan_history_id and vulns.exists():
			scan_history_id = vulns.first().scan_history_id
	elif scan_history_id:
		vulns = Vulnerability.objects.filter(scan_history_id=scan_history_id)
	else:
		logger.error("Neither scan_history_id nor vulnerability_id provided for impact assessment.")
		return False

	# Check if there are other scanning tasks still running
	if scan_history_id:
		from startScan.models import ScanActivity
		from reNgine.definitions import RUNNING_TASK, INITIATED_TASK
		post_processing_names = ['correlate_vulnerabilities', 'calculate_risk_scores', 'generate_impact_assessment', 'run_apme', 'report']
		
		if self.subscan:
			running_scans = ScanActivity.objects.filter(
				celery_id__in=self.subscan.celery_ids,
				status__in=[RUNNING_TASK, INITIATED_TASK]
			).exclude(name__in=post_processing_names)
		else:
			running_scans = ScanActivity.objects.filter(
				scan_of_id=scan_history_id,
				status__in=[RUNNING_TASK, INITIATED_TASK]
			).exclude(name__in=post_processing_names)

		if running_scans.exists() and not getattr(self, '_is_temporal_proxy', False):
			running_names = list(running_scans.values_list('name', flat=True))
			logger.info(f"Scanning tasks are still running: {running_names}. Rescheduling generate_impact_assessment...")
			raise self.retry(countdown=10, max_retries=1000)

	generator = LLMImpactGenerator(logger)

	# Run Correlation Engine to unify results and calculate scores
	from reNgine.correlation import VulnerabilityCorrelationEngine
	correlator = VulnerabilityCorrelationEngine(scan_history=ScanHistory.objects.get(id=scan_history_id))
	correlator.correlate_findings()

	for vuln in vulns:
		if vuln.is_suppressed:
			continue

		context = f"Vulnerability: {vuln.name}\n"
		context += f"Description: {vuln.description}\n"
		context += f"Asset: {vuln.subdomain.name if vuln.subdomain else (vuln.endpoint.http_url if vuln.endpoint else 'Unknown')}\n"
		if vuln.subdomain:
			context += f"Technologies: {', '.join([t.name for t in vuln.subdomain.technologies.all()])}\n"

		# Call LLM (PII protection is handled inside generator)
		final_impact = generator.generate_impact_assessment(context)

		# Persist to ImpactAssessment model
		ImpactAssessment.objects.update_or_create(
			vulnerability=vuln,
			defaults={
				'scan_history_id': scan_history_id,
				'subdomain': vuln.subdomain,
				'potential_impact': final_impact,
				'is_ai_generated': True
			}
		)

		# Also sync to Vulnerability model for reports
		vuln.impact = final_impact
		vuln.save()


@app.task(name='sync_cisa_kev_catalog', queue='main_scan_queue', bind=False)
def sync_cisa_kev_catalog():
	"""
	Syncs CISA KEV catalog and updates CVE records.
	"""
	import requests
	from startScan.models import CveId
	url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
	try:
		response = requests.get(url, timeout=30)
		if response.status_code == 200:
			data = response.json()
			cve_list = [v.get("cveID") for v in data.get("vulnerabilities", [])]
			if cve_list:
				CveId.objects.filter(name__in=cve_list).update(is_cisa_kev=True)
				logger.info(f"Successfully synced CISA KEV catalog. Updated {len(cve_list)} records.")
	except Exception as e:
		logger.error(f"Error syncing CISA KEV catalog: {e}")


@app.task(name='sync_semgrep_rules', queue='main_scan_queue', bind=False)
def sync_semgrep_rules():
	"""
	Synchronizes Semgrep rules from the public registry to the local filesystem.
	Runs at system startup and can be triggered manually.
	"""
	rules_dir = "/usr/src/github/semgrep_rules"
	if not os.path.exists(rules_dir):
		os.makedirs(rules_dir, exist_ok=True)
	
	# Rule sets to sync
	rule_sets = {
		"p/secrets": "secrets.yaml",
		"p/owasp-top-ten": "owasp-top-10.yaml",
		"p/ci": "ci.yaml",
		"p/javascript": "javascript.yaml",
		"p/python": "python.yaml"
	}
	
	for config, filename in rule_sets.items():
		target_path = os.path.join(rules_dir, filename)
		url = f"https://semgrep.dev/c/{config}"
		try:
			logger.info(f"Syncing Semgrep rule set: {config} -> {filename}")
			response = requests.get(url, timeout=60)
			if response.status_code == 200:
				with open(target_path, 'wb') as f:
					f.write(response.content)
				logger.info(f"Successfully synced Semgrep rule set: {config}")
			else:
				logger.error(f"Failed to download Semgrep rule set {config}: HTTP {response.status_code}")
		except Exception as e:
			logger.error(f"Failed to sync Semgrep rule set {config}: {e}")


@app.task(name='semgrep_scan', queue='main_scan_queue', bind=True, base=RengineTask)
def semgrep_scan(self, ctx={}, mode='vulnerability', description=None):
	"""
	Runs Semgrep static analysis on fetched files.
	mode: 'secret' or 'vulnerability'
	"""
	scan_id = ctx.get('scan_history_id')
	results_dir = ctx.get('results_dir')
	
	if not results_dir:
		logger.error("Results directory not provided. Semgrep scan aborted.")
		return
	
	# Create a directory for Semgrep to scan
	semgrep_dir = os.path.join(results_dir, f'semgrep_{mode}_temp')
	os.makedirs(semgrep_dir, exist_ok=True)

	# But to be robust, we'll download files ourselves if the directory is empty
	SENSITIVE_EXTENSIONS = ('.js', '.env', '.php', '.asp', '.aspx', '.jsp', '.jspx', '.txt', '.log', '.conf', '.config', '.bak', '.old', '.json', '.yaml', '.yml', '.html', '.htm')
	
	# Load URLs from fetch_url output files and tool-specific files
	urls_from_files = set()
	if os.path.exists(results_dir):
		for f in os.listdir(results_dir):
			if f.endswith('_fetch_url.txt') or (f.startswith('urls_') and f.endswith('.txt')):
				fpath = os.path.join(results_dir, f)
				try:
					with open(fpath, 'r', encoding='utf-8', errors='ignore') as f_in:
						for line in f_in:
							url_str = line.strip()
							if url_str:
								urls_from_files.add(url_str)
					logger.info(f"Loaded URLs from fetch_url output file: {fpath}")
				except Exception as e:
					logger.error(f"Failed to read file {fpath}: {e}")

	endpoints = EndPoint.objects.filter(scan_history_id=scan_id)
	all_urls = set(e.http_url for e in endpoints)
	all_urls.update(urls_from_files)
	
	# Filter sensitive URLs robustly by parsing their path component
	target_urls = []
	for url in all_urls:
		try:
			path = urlparse(url).path.lower()
			if path.endswith(SENSITIVE_EXTENSIONS):
				target_urls.append(url)
		except Exception:
			if url.lower().endswith(SENSITIVE_EXTENSIONS):
				target_urls.append(url)
	
	if not target_urls:
		logger.info(f"No target files found for Semgrep {mode} scan.")
		return

	# Retrieve proxies configuration from database
	downloaded_count = 0
	available_proxies = []
	use_proxy = False
	current_proxy_index = 0
	
	try:
		if Proxy.objects.all().exists():
			proxy_config = Proxy.objects.first()
			if proxy_config.use_proxy:
				use_proxy = True
				available_proxies = [p.strip() for p in proxy_config.proxies.splitlines() if p.strip()]
				# Shuffle the proxies to distribute traffic randomly
				random.shuffle(available_proxies)
	except Exception as e:
		logger.error(f"Failed to load proxies configuration: {e}")

	# Convert custom headers list to dictionary
	headers_dict = {}
	custom_headers = self.yaml_configuration.get(CUSTOM_HEADERS, [])
	custom_header = self.yaml_configuration.get(CUSTOM_HEADER)
	if custom_header:
		custom_headers.append(custom_header)
	for h in custom_headers:
		if ':' in h:
			k, v = h.split(':', 1)
			headers_dict[k.strip()] = v.strip()
	if 'User-Agent' not in headers_dict:
		headers_dict['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

	for url in target_urls:
		try:
			# Normalize URL if relative or missing scheme
			base_domain = self.domain.name if self.domain else None
			full_url = url.strip()
			if not full_url:
				continue
			
			parsed_url = urlparse(full_url)
			if not parsed_url.scheme:
				if base_domain:
					if full_url.startswith('//'):
						full_url = f"https:{full_url}"
					else:
						full_url = f"https://{base_domain}/{full_url.lstrip('/')}"
				else:
					full_url = f"https://{full_url.lstrip('/')}"
			
			# Create a safe filename from URL
			safe_name = "".join([c if c.isalnum() else "_" for c in url])
			# Preserve extension if possible
			ext = os.path.splitext(urlparse(full_url).path)[1]
			if not ext:
				ext = ".js"
			filename = f"{safe_name}{ext}"
			filepath = os.path.join(semgrep_dir, filename)
			
			if os.path.exists(filepath):
				continue # Skip if already exists
			
			# Try downloading the URL, with proxy cycling on failure (capped at max 5 to prevent stalls)
			max_retries = min(5, len(available_proxies)) if use_proxy and available_proxies else 1
			if max_retries < 1:
				max_retries = 1
			attempt = 0
			download_success = False

			while attempt < max_retries:
				proxies = None
				current_proxy_name = None
				if use_proxy and available_proxies:
					current_proxy_name = available_proxies[current_proxy_index % len(available_proxies)]
					proxies = {
						'http': current_proxy_name,
						'https': current_proxy_name
					}

				try:
					resp = requests.get(full_url, headers=headers_dict, proxies=proxies, timeout=10, verify=False)
					if resp.status_code == 200:
						with open(filepath, 'w', encoding='utf-8') as f:
							f.write(resp.text)
						downloaded_count += 1
						download_success = True
						break  # Successfully downloaded
					elif resp.status_code in [407, 502, 503, 504]:
						# Proxy connection or authentication error code, cycle and retry
						raise requests.exceptions.ProxyError(f"Proxy returned status code {resp.status_code}")
					else:
						logger.debug(f"Semgrep downloader got status {resp.status_code} for {full_url}")
						# Other response codes (e.g. 404/403) are verified responses from the target host itself
						break
				except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
					attempt += 1
					if use_proxy and available_proxies:
						old_proxy = current_proxy_name
						current_proxy_index += 1
						new_proxy = available_proxies[current_proxy_index % len(available_proxies)]
						logger.warning(
							f"Proxy failure using {old_proxy} for {full_url}. "
							f"Cycling to next proxy: {new_proxy} (Attempt {attempt}/{max_retries}). Error: {e}"
						)
					else:
						logger.debug(f"Semgrep downloader network failure for {full_url}: {e}")
						break
				except Exception as e:
					logger.debug(f"Semgrep downloader got non-network error for {url} (full: {full_url}): {e}")
					break

		except Exception as e:
			logger.debug(f"Semgrep downloader loop error for {url}: {e}")

	if downloaded_count == 0:
		logger.warning("No files could be downloaded for Semgrep scan.")
		shutil.rmtree(semgrep_dir, ignore_errors=True)
		return

	rules_dir = "/usr/src/github/semgrep_rules"
	config_file = "owasp-top-10.yaml" if mode == 'vulnerability' else "secrets.yaml"
	rules_path = os.path.join(rules_dir, config_file)
	
	# Fallback if local sync failed
	if not os.path.exists(rules_path):
		rules_path = "p/owasp-top-10" if mode == 'vulnerability' else "p/secrets"

	output_json = os.path.join(results_dir, f'semgrep_{mode}_{int(time.time())}.json')
	
	# Run Semgrep
	cmd = f"semgrep scan --config {rules_path} {semgrep_dir} --json --output {output_json} --timeout 600"
	return_code, output = run_command(cmd, scan_id=scan_id)
	
	if os.path.exists(output_json):
		try:
			with open(output_json, 'r') as f:
				data = json.load(f)
				results = data.get('results', [])
				
				for result in results:
					if mode == 'secret':
						save_semgrep_secret_finding(result, ctx, semgrep_dir)
					else:
						save_semgrep_vulnerability_finding(result, ctx, semgrep_dir)
						
			logger.info(f"Semgrep {mode} scan completed. Found {len(results)} matches.")
		except Exception as e:
			logger.error(f"Error parsing Semgrep output: {e}")
	
	# Cleanup
	shutil.rmtree(semgrep_dir, ignore_errors=True)
	
	return return_code


def save_semgrep_vulnerability_finding(result, ctx, base_dir):
	"""Saves a Semgrep finding as a Vulnerability."""
	extra = result.get('extra', {})
	path = result.get('path', '')
	
	try:
		scan = ScanHistory.objects.get(id=ctx.get('scan_history_id'))
		domain = Domain.objects.get(id=ctx.get('domain_id'))
		
		vuln_data = {
			'name': f"Semgrep: {result.get('check_id')}",
			'description': extra.get('message', ''),
			'severity': SEMGREP_SEVERITY_MAP.get(extra.get('severity', 'INFO'), 0),
			'http_url': path.replace(base_dir, '').lstrip('/'),
			'type': 'SAST',
			'request': f"File: {path}\nLine: {result.get('start', {}).get('line')}",
			'response': extra.get('lines', ''),
		}
		save_vulnerability(vuln_data, scan_history=scan, target_domain=domain)
	except Exception as e:
		logger.error(f"Error saving Semgrep vulnerability: {e}")


def save_semgrep_secret_finding(result, ctx, base_dir):
	"""Saves a Semgrep finding as a SecretLeak."""
	extra = result.get('extra', {})
	path = result.get('path', '')
	
	try:
		scan = ScanHistory.objects.get(id=ctx.get('scan_history_id'))
		
		leak_data = {
			'scan_history': scan,
			'tool_name': 'Semgrep',
			'secret_type': result.get('check_id', 'Secret'),
			'source_url': path.replace(base_dir, '').lstrip('/'),
			'match_content': extra.get('lines', '').strip(),
			'status': 'unverified'
		}
		save_secret_leak(**leak_data)
	except Exception as e:
		logger.error(f"Error saving Semgrep secret: {e}")


@app.task(name='run_apme', queue='main_scan_queue', base=RengineTask, bind=True)
def run_apme(self, scan_history_id, ctx={}, description=None):
	"""Run the Attack Path Modeling Engine (APME).

	Args:
		scan_history_id (int): Scan history ID.
		ctx (dict): Scan context.
	"""
	if not RENGINE_APME_ENABLED:
		logger.info("APME is disabled in settings (RENGINE_APME_ENABLED=False). Skipping.")
		return

	# Check if there are other scanning tasks still running
	from startScan.models import ScanActivity
	from reNgine.definitions import RUNNING_TASK, INITIATED_TASK
	post_processing_names = ['correlate_vulnerabilities', 'calculate_risk_scores', 'generate_impact_assessment', 'run_apme', 'report']
	
	if self.subscan:
		running_scans = ScanActivity.objects.filter(
			celery_id__in=self.subscan.celery_ids,
			status__in=[RUNNING_TASK, INITIATED_TASK]
		).exclude(name__in=post_processing_names)
	else:
		running_scans = ScanActivity.objects.filter(
			scan_of_id=scan_history_id,
			status__in=[RUNNING_TASK, INITIATED_TASK]
		).exclude(name__in=post_processing_names)

	if running_scans.exists() and not getattr(self, '_is_temporal_proxy', False):
		running_names = list(running_scans.values_list('name', flat=True))
		#logger.info(f"Scanning tasks are still running: {running_names}. Rescheduling run_apme...")
		raise self.retry(countdown=10, max_retries=1000)

	logger.info(f"APME: Initiating attack path modeling for scan_history_id={scan_history_id}")
	try:
		from apme.orchestrator import APMEOrchestrator
		from startScan.models import ScanHistory
		
		# Fetch configuration from engine
		scan = ScanHistory.objects.get(id=scan_history_id)
		config = yaml.safe_load(scan.scan_type.yaml_configuration) or {}
		apme_config = config.get(ATTACK_PATH_MODELING, {})
		top_n = apme_config.get('top_n', 5)

		orchestrator = APMEOrchestrator(top_n=top_n)
		result = orchestrator.run(scan_history_id)
		logger.info(
			f"APME: Completed. Found {result.get('total_paths', 0)} paths, "
			f"returned top {result.get('returned_paths', 0)}."
		)
		return result
	except Exception as exc:
		logger.error(f"APME: Task failed for scan {scan_history_id}: {exc}", exc_info=True)
		return {"error": str(exc), "total_paths": 0, "returned_paths": 0, "paths": []}
