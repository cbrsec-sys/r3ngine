import os
import requests
import json
import validators
import csv
import io
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from django.utils import timezone
from celery.utils.log import get_task_logger

from reNgine.celery import app
from reNgine.definitions import *
from reNgine.settings import *
from reNgine.common_func import *
from django.db import transaction
from reNgine.task_utils import save_subdomain, stream_command
from targetApp.models import Domain
from startScan.models import ScanHistory, Subdomain, EndPoint, MonitoringDiscovery
from scanEngine.models import EngineType

logger = get_task_logger(__name__)


def _process_monitor_spiderfoot_batch(batch, domain, scan_history, ctx, new_discoveries, existing_subs):
	"""Internal helper to process a batch of SpiderFoot findings for monitoring."""
	try:
		with transaction.atomic():
			for event in batch:
				e_type = event.get('Type')
				e_data = event.get('Data')
				
				if not e_type or not e_data:
					continue
				
				# SF types for hostnames/subdomains
				if e_type in ['DNS_NAME', 'INTERNET_NAME', 'AFFILIATE_INTERNET_NAME']:
					sub_name = e_data.lower()
					if sub_name and sub_name.endswith(domain.name) and sub_name not in existing_subs:
						sub_obj, created = save_subdomain(sub_name, ctx=ctx)
						if created:
							new_discoveries.append(f"Subdomain (SpiderFoot): {sub_name}")
							existing_subs.add(sub_name)
							MonitoringDiscovery.objects.create(
								domain=domain,
								discovery_type='subdomain',
								content={'name': sub_name, 'source': 'SpiderFoot'},
								scan_history=scan_history
							)
		logger.info(f"Processed monitoring batch of {len(batch)} SpiderFoot findings.")
	except Exception as e:
		logger.error(f"Error processing SpiderFoot monitoring batch: {str(e)}")


@app.task(name='monitor_target_task', queue='main_scan_queue')
def monitor_target_task(domain_id):
	try:
		domain = Domain.objects.get(pk=domain_id)
	except Domain.DoesNotExist:
		logger.error(f"Domain with ID {domain_id} does not exist.")
		return

	logger.info(f"Starting monitoring for {domain.name}")

	# 1. Setup Scan History
	engine = domain.monitor_engine
	if not engine:
		engine = EngineType.objects.filter(default_engine=True).first()

	scan_history = ScanHistory.objects.create(
		domain=domain,
		scan_type=engine,
		start_scan_date=timezone.now(),
		scan_status=RUNNING_TASK,
		tasks=['monitoring_discovery']
	)

	results_dir = f"{RENGINE_RESULTS}/{domain.name}_monitor_{scan_history.id}"
	os.makedirs(results_dir, exist_ok=True)
	scan_history.results_dir = results_dir
	scan_history.save()

	# Context for save_subdomain and save_endpoint
	ctx = {
		'scan_history_id': scan_history.id,
		'domain_id': domain.id,
		'results_dir': results_dir,
	}

	new_discoveries = []

	try:
		# 2. Subdomain Discovery (Subfinder)
		subdomain_file = f"{results_dir}/subdomains_monitor.txt"
		subfinder_cmd = f"subfinder -d {domain.name} -silent -o {subdomain_file}"
		os.system(subfinder_cmd)

		if os.path.exists(subdomain_file):
			with open(subdomain_file, 'r') as f:
				discovered_subs = [line.strip() for line in f if line.strip()]
			
			existing_subs = set(Subdomain.objects.filter(target_domain=domain).values_list('name', flat=True))
			
			# Check if subdomain discovery is enabled in tasks
			if 'subdomain_discovery' in scan_history.tasks:
				for sub_name in discovered_subs:
					if sub_name not in existing_subs:
						# Save new subdomain
						sub_obj, created = save_subdomain(sub_name, ctx=ctx)
					if created:
						new_discoveries.append(f"Subdomain: {sub_name}")
						MonitoringDiscovery.objects.create(
							domain=domain,
							discovery_type='subdomain',
							content={'name': sub_name},
							scan_history=scan_history
						)

		# 3. URL Discovery (GAU)
		url_file = f"{results_dir}/urls_monitor.txt"
		gau_cmd = f"gau {domain.name} --subs --silent -o {url_file}"
		os.system(gau_cmd)

		if os.path.exists(url_file):
			with open(url_file, 'r') as f:
				# Limit to 500 URLs to avoid overload in monitoring
				discovered_urls = [line.strip() for line in f if line.strip()][:500]
			
			existing_urls = set(EndPoint.objects.filter(target_domain=domain).values_list('http_url', flat=True))
			
			for url in discovered_urls:
				if url not in existing_urls:
					# Detect login and status
					status, title, is_login = detect_login_and_status(url)
					
					from reNgine.task_utils import save_endpoint
					endpoint_data = {
						'http_status': status,
						'page_title': title,
					}
					endpoint_obj, created = save_endpoint(url, ctx=ctx, **endpoint_data)
					
					if created:
						disc_type = 'login' if is_login else 'directory'
						new_discoveries.append(f"{disc_type.capitalize()}: {url}")
						MonitoringDiscovery.objects.create(
							domain=domain,
							discovery_type=disc_type,
							content={'url': url, 'status': status, 'title': title},
							scan_history=scan_history
						)

		# 4. ReconX Discovery
		reconx_results = f"{results_dir}/reconx_findings"
		os.makedirs(reconx_results, exist_ok=True)
		
		# Create a temporary targets file for reconx
		reconx_targets = f"{results_dir}/reconx_targets.txt"
		with open(reconx_targets, 'w') as f:
			f.write(domain.name)
		
		# Run reconx
		# reconx run uses targets from config, but we can override or use a specific config
		# For simplicity, we'll use a direct command if supported, or create a minimal config
		reconx_cmd = f"reconx run --targets {reconx_targets} --output {reconx_results}"
		os.system(reconx_cmd)
		
		# Parse reconx findings (JSONL format in findings directory)
		# Findings are usually in ~/.local/share/reconx/findings/ but we try to direct output if possible
		# If not, we'll check the default location
		reconx_default_findings = os.path.expanduser("~/.local/share/reconx/findings/")
		if os.path.exists(reconx_default_findings):
			for file in os.listdir(reconx_default_findings):
				if file.endswith(".jsonl"):
					try:
						with open(os.path.join(reconx_default_findings, file), 'r') as f:
							for line in f:
								finding = json.loads(line)
								# ReconX findings can be subdomains or vulnerabilities
								if finding.get('type') == 'subdomain':
									sub_name = finding.get('data', {}).get('subdomain')
									if sub_name and sub_name.endswith(domain.name) and sub_name not in existing_subs:
										from reNgine.tasks import save_subdomain
										sub_obj, created = save_subdomain(sub_name, ctx=ctx)
										if created:
											new_discoveries.append(f"Subdomain (ReconX): {sub_name}")
											existing_subs.add(sub_name)
											MonitoringDiscovery.objects.create(
												domain=domain,
												discovery_type='subdomain',
												content={'name': sub_name, 'source': 'ReconX'},
												scan_history=scan_history
											)
								elif finding.get('type') == 'vulnerability':
									# If reconx found a vulnerability, we can also log it
									vuln_info = finding.get('data', {})
									new_discoveries.append(f"Vulnerability (ReconX): {vuln_info.get('template-id')}")
					except Exception as e:
						logger.error(f"Error parsing ReconX findings: {str(e)}")

		# 5. Attack Surface Intelligence (SpiderFoot)
		if 'spiderfoot_scan' in scan_history.tasks:
			sf_output = f"{results_dir}/spiderfoot_monitor.json"
			# Use global SF config
			sf_config_path = "/usr/src/github/spiderfoot/spiderfoot.cfg"
			
			# Use a focused set of modules for monitoring efficiency
			# Discovery modules + OSINT
			sf_modules = "snovio,hunterio,emailrep,intelx,shodan,sublist3r,threatcrowd,crtsh"
			# Use CSV output for streaming. -r includes source data, -n strips newlines.
			sf_cmd = f"python3 /usr/src/github/spiderfoot/sf.py -s {domain.name} -m {sf_modules} -q -o csv -r -n -c {sf_config_path}"
			
			proxy = get_random_proxy()
			if proxy:
				sf_cmd = f"export HTTP_PROXY='{proxy}' HTTPS_PROXY='{proxy}' && {sf_cmd}"
			
			batch = []
			batch_size = 50
			header = None
			
			try:
				for line in stream_command(sf_cmd, shell=True):
					if not isinstance(line, str) or not line.strip():
						continue
					
					f = io.StringIO(line)
					reader = csv.reader(f)
					try:
						row = next(reader)
					except StopIteration:
						continue
					
					if not header:
						if "Data" in row and "Type" in row:
							header = row
							continue
						else:
							continue
					
					event = dict(zip(header, row))
					batch.append(event)
					
					if len(batch) >= batch_size:
						_process_monitor_spiderfoot_batch(batch, domain, scan_history, ctx, new_discoveries, existing_subs)
						batch = []
				
				if batch:
					_process_monitor_spiderfoot_batch(batch, domain, scan_history, ctx, new_discoveries, existing_subs)
					
			except Exception as e:
				logger.error(f"SpiderFoot monitoring failed: {e}")


		# 5. Notifications
		if new_discoveries:
			message = f"🔍 Monitoring discovery for {domain.name}:\n" + "\n".join(new_discoveries[:10])
			if len(new_discoveries) > 10:
				message += f"\n... and {len(new_discoveries) - 10} more."
			
			send_telegram_message(message)
			send_slack_message(message)
			send_discord_message(message, title=f"Monitoring: {domain.name}", severity='info')
			
			# Create In-App Notification (Toast)
			create_inappnotification(
				title=f"Monitoring Discovery: {domain.name}",
				description=f"Found {len(new_discoveries)} new items.",
				notification_type=PROJECT_LEVEL_NOTIFICATION,
				status='info'
			)

		# 6. Follow-up Scan
		if domain.monitor_scan_scope != 'none' and new_discoveries:
			from reNgine.tasks import initiate_scan
			if domain.monitor_scan_scope == 'targeted':
				# Targeted scan for new subdomains
				new_subs = [d.split(": ")[1] for d in new_discoveries if d.startswith("Subdomain")]
				if new_subs:
					initiate_scan.delay(
						scan_history_id=None,
						domain_id=domain.id,
						engine_id=engine.id,
						scan_type=SCHEDULED_SCAN,
						imported_subdomains=new_subs
					)
			elif domain.monitor_scan_scope == 'full':
				initiate_scan.delay(
					scan_history_id=None,
					domain_id=domain.id,
					engine_id=engine.id,
					scan_type=SCHEDULED_SCAN
				)

		scan_history.scan_status = SUCCESS_TASK
		scan_history.stop_scan_date = timezone.now()
		scan_history.save()
		
		# Update domain's last monitored date
		domain.last_monitored = timezone.now()
		domain.save()

	except Exception as e:
		logger.error(f"Error in monitoring task for {domain.name}: {str(e)}")
		scan_history.scan_status = FAILED_TASK
		scan_history.error_message = str(e)
		scan_history.save()

def detect_login_and_status(url):
	try:
		# Use a random User-Agent from OpSec if possible, or just a default
		headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
		response = requests.get(url, timeout=5, verify=False, headers=headers)
		status = response.status_code
		soup = BeautifulSoup(response.text, 'html.parser')
		title = soup.title.string.strip() if soup.title and soup.title.string else ""
		
		is_login = False
		if soup.find('input', {'type': 'password'}):
			is_login = True
		elif any(keyword in title.lower() for keyword in ['login', 'signin', 'auth', 'portal']):
			is_login = True
			
		return status, title, is_login
	except Exception as e:
		# logger.debug(f"Probing failed for {url}: {str(e)}")
		return 0, "", False
