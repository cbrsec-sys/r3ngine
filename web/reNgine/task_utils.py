import os
import re
import subprocess
import validators
import json
from django.utils import timezone
from celery.utils.log import get_task_logger

from urllib.parse import urlparse
from reNgine.celery import app
from reNgine.opsec_utils import ProxychainsWrapper
import redis
from django.conf import settings
from startScan.models import ScanHistory, Email, Employee, Command, Subdomain, EndPoint, Parameter
from dashboard.models import SOCConfiguration
from targetApp.models import Domain
from reNgine.definitions import (
    COLOR_RESET, COLOR_WHITE, COLOR_RED, TOOL_COLORS
)
from reNgine.common_func import remove_ansi_escape_sequences, sanitize_url
from reNgine.utilities import SubdomainScopeChecker, replace_nulls
from reNgine.settings import RENGINE_RESULTS

logger = get_task_logger(__name__)

def get_tool_color(cmd):
    """Returns the ANSI color code for a given command based on the tool name."""
    sanitized = sanitize_command_for_db(cmd)
    if not sanitized:
        return COLOR_RED
    # Get the first part of the command (the binary)
    binary = sanitized.split()[0]
    # Strip path and extension
    tool = os.path.basename(binary).lower()
    if tool.endswith(('.py', '.sh', '.nse')):
        tool = tool.rsplit('.', 1)[0]
    return TOOL_COLORS.get(tool, COLOR_RED)

def sanitize_command_for_db(cmd):
    """
    Strips 'export HTTP_PROXY=... &&' and 'proxychains4 -f ...' from command
    to ensure the UI displays the actual tool name and clean command.
    """
    if not cmd:
        return cmd
    # Strip export statements (matches both single and double quotes)
    cmd = re.sub(r'^export\s+.*?\s+&&\s+', '', cmd)
    # Strip proxychains4 wrapper with its config file
    cmd = re.sub(r'^(?:[/\w]*/)?proxychains4\s+-f\s+\S+\s+', '', cmd)
    return cmd

@app.task(name='run_command', bind=False, queue='run_command_queue')
def run_command(
        cmd, 
        cwd=None, 
        shell=False, 
        history_file=None, 
        scan_id=None, 
        activity_id=None,
        remove_ansi_sequence=False,
        proxy=None
    ):
    """Run a given command using subprocess module.

    Args:
        cmd (str): Command to run.
        cwd (str): Current working directory.
        echo (bool): Log command.
        shell (bool): Run within separate shell if True.
        history_file (str): Write command + output to history file.
        remove_ansi_sequence (bool): Used to remove ANSI escape sequences from output such as color coding
        proxy (str): If provided, may be used for proxychains wrapping.
    Returns:
        tuple: Tuple with return_code, output.
    """
    color = get_tool_color(cmd)
    logger.debug(f"{color}{cmd}{COLOR_RESET}")

    conf_path = None
    if proxy:
        proxy_manager = ProxychainsWrapper()
        if proxy_manager.should_wrap():
            cmd, conf_path = proxy_manager.wrap_command(cmd, proxy=proxy)

    # Create a command record in the database
    from django.db import IntegrityError
    try:
        command_obj = Command.objects.create(
            command=sanitize_command_for_db(cmd),
            time=timezone.now(),
            scan_history_id=scan_id,
            activity_id=activity_id)
    except IntegrityError as e:
        logger.warning(f"Could not create Command object in DB (scan or activity may have been deleted/rolled back): {e}")
        command_obj = None

    # Run the command using subprocess
    try:
        popen = subprocess.Popen(
            cmd if shell else cmd.split(),
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            universal_newlines=True)
        output = ''
        for stdout_line in iter(popen.stdout.readline, ""):
            item = stdout_line.strip()
            output += '\n' + item
            logger.info(f"{COLOR_WHITE}{item}{COLOR_RESET}")
        popen.stdout.close()
        try:
            popen.wait(timeout=7200)
        except subprocess.TimeoutExpired:
            popen.kill()
            return_code = 124 # Timeout
            output += "\nCommand timed out after 30 seconds."
        else:
            return_code = popen.returncode
    except Exception as e:
        logger.error(f"Error executing command {cmd}: {str(e)}")
        output = f"Error executing command: {str(e)}"
        return_code = 127 # Command not found / error
    finally:
        if conf_path and os.path.exists(conf_path):
            os.remove(conf_path)

    if command_obj:
        logger.warning(f"Command {command_obj.id} finished with return code {return_code}")
        command_obj.output = output
        command_obj.return_code = return_code
        command_obj.save()
    else:
        logger.warning(f"Command finished with return code {return_code} (no database record saved)")

    if history_file:
        mode = 'a'
        if not os.path.exists(history_file):
            mode = 'w'
        with open(history_file, mode) as f:
            f.write(f'\n{cmd}\n{return_code}\n{output}\n------------------\n')
            
    if remove_ansi_sequence:
        output = remove_ansi_escape_sequences(output)
        
    return return_code, output

def save_email(email_address, scan_history=None):
    if not validators.email(email_address):
        logger.info(f'Email {email_address} is invalid. Skipping.')
        return None, False
    email, created = Email.objects.get_or_create(address=email_address)

    # Add email to ScanHistory
    if scan_history:
        scan_history.emails.add(email)
        scan_history.save()
        # Trigger identity enrichment
        from reNgine.osint_tasks import enrich_identities_task
        enrich_identities_task.delay(email_address, 'email', scan_history.id)

    return email, created

def save_employee(name, designation='', scan_history=None):
    employee, created = Employee.objects.get_or_create(
        name=name,
        designation=designation)

    # Add employee to ScanHistory
    if scan_history:
        scan_history.employees.add(employee)
        scan_history.save()
        # Trigger identity enrichment
        from reNgine.osint_tasks import enrich_identities_task
        enrich_identities_task.delay(name, 'employee', scan_history.id)

    return employee, created

def save_subdomain(subdomain_name, ctx={}):
    """Get or create Subdomain object."""
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
        logger.error(f'{subdomain_name} is not a valid domain. Skipping.')
        return None, False

    if subdomain_checker.is_out_of_scope(subdomain_name):
        logger.error(f'{subdomain_name} is out-of-scope. Skipping.')
        return None, False

    if ctx.get('domain_id'):
        domain = Domain.objects.filter(id=ctx.get('domain_id')).first()
        if domain and domain.name not in subdomain_name:
            logger.error(f"{subdomain_name} is not a subdomain of domain {domain.name}. Skipping.")
            return None, False

    scan = ScanHistory.objects.filter(pk=scan_id).first()
    domain = scan.domain if scan else Domain.objects.filter(id=ctx.get('domain_id')).first()
    
    subdomain, created = Subdomain.objects.get_or_create(
        scan_history=scan,
        target_domain=domain,
        name=subdomain_name)
    
    if created:
        subdomain.discovered_date = timezone.now()
        if subscan_id:
            subdomain.subdomain_subscan_ids.add(subscan_id)
        subdomain.save()
    return subdomain, created

def save_endpoint(
        http_url,
        ctx={},
        crawl=False,
        is_default=False,
        **endpoint_data):
    """Get or create EndPoint object."""
    endpoint_data = replace_nulls(endpoint_data)
    scheme = urlparse(http_url).scheme
    endpoint = None
    created = False
    
    if ctx.get('domain_id'):
        domain = Domain.objects.filter(id=ctx.get('domain_id')).first()
        if domain and domain.name not in http_url:
            logger.error(f"{http_url} is not a URL of domain {domain.name}. Skipping.")
            return None, False
            
    if crawl:
        # Avoid circular import by importing here
        from reNgine.tasks import http_crawl
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
    else:
        scan = ScanHistory.objects.filter(pk=ctx.get('scan_history_id')).first()
        domain = Domain.objects.filter(pk=ctx.get('domain_id')).first()
        if not validators.url(http_url):
            return None, False
        http_url = sanitize_url(http_url)

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
        subscan_id = ctx.get('subscan_id')
        if subscan_id:
            endpoint.endpoint_subscan_ids.add(subscan_id)
            endpoint.save()

    return endpoint, created

def save_parameter(endpoint, name, param_type='unknown', impact='none', value=None):
    """Save a discovered parameter to the database."""
    param, created = Parameter.objects.get_or_create(
        endpoint=endpoint,
        name=name,
        defaults={'type': param_type, 'impact': impact, 'value': value}
    )
    if not created:
        if param_type != 'unknown':
            param.type = param_type
        if value:
            param.value = value
        param.save()
    return param, created

def stream_command(
		cmd, 
		cwd=None, 
		shell=False, 
		history_file=None, 
		encoding='utf-8', 
		scan_id=None, 
		activity_id=None, 
		trunc_char=None,
		proxy=None,
		timeout=3600
	):
	"""Run a command and yield output line by line.

	Args:
		cmd (str): Command to run.
		cwd (str): Current working directory.
		shell (bool): Run within separate shell if True.
		history_file (str): Write command + output to history file.
		encoding (str): Output encoding.
		scan_id (int): Scan ID.
		activity_id (int): Activity ID.
		trunc_char (str): Character used to truncate the output line.
		proxy (str): If provided, may be used for proxychains wrapping.
		timeout (int): Overall execution timeout in seconds.
	Yields:
		str/dict: Output line.
	"""
	color = get_tool_color(cmd)
	logger.debug(f"{color}{cmd}{COLOR_RESET}")

	conf_path = None
	if proxy:
		proxy_manager = ProxychainsWrapper()
		if proxy_manager.should_wrap():
			cmd, conf_path = proxy_manager.wrap_command(cmd, proxy=proxy)

	# Create a command record in the database
	command_obj = Command.objects.create(
		command=sanitize_command_for_db(cmd),
		time=timezone.now(),
		scan_history_id=scan_id,
		activity_id=activity_id)

	# Sanitize the cmd
	command = cmd if shell else cmd.split()

	# Run the command using subprocess
	process = subprocess.Popen(
		command,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		universal_newlines=True,
		shell=shell)

	# Start a watchdog thread to terminate the command if it runs too long
	import threading
	import time

	def watchdog(proc, limit_sec):
		time.sleep(limit_sec)
		if proc.poll() is None:
			logger.error(f"Watchdog: Command timed out after {limit_sec} seconds. Killing process: {cmd}")
			try:
				proc.kill()
			except Exception as ex:
				logger.error(f"Watchdog: Failed to kill process: {ex}")

	watchdog_thread = threading.Thread(
		target=watchdog,
		args=(process, timeout),
		daemon=True
	)
	watchdog_thread.start()

	# Log the output in real-time to the database
	output = ""

	# Process the output
	line_count = 0
	try:
		for line in iter(lambda: process.stdout.readline(), ''):
			if not line:
				break
			line = line.strip()
			ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
			line = ansi_escape.sub('', line)
			line = line.replace('\\x0d\\x0a', '\n')
			if trunc_char and line.endswith(trunc_char):
				line = line[:-1]
			item = line

			# Try to parse the line as JSON
			try:
				item = json.loads(line)
			except json.JSONDecodeError:
				pass

			# Log to console for visibility
			if isinstance(item, str):
				logger.debug(f"{COLOR_WHITE}{item}{COLOR_RESET}")
			else:
				logger.debug(f"{COLOR_WHITE}{json.dumps(item)}{COLOR_RESET}")

			# Yield the line
			yield item
			
			# Real-time log streaming to Redis if enabled
			try:
				soc_config = SOCConfiguration.objects.get_or_create(id=1)[0]
				if soc_config.enable_live_log_streaming and scan_id:
					r = redis.StrictRedis(
						host=settings.REDIS_HOST, 
						port=settings.REDIS_PORT, 
						db=0
					)
					stream_key = f"scan:logs:{scan_id}"
					log_payload = {
						"data": json.dumps({
							"line": line,
							"timestamp": str(timezone.now()),
							"command_id": command_obj.id
						})
					}
					r.xadd(stream_key, log_payload)
					# Limit stream length
					r.xtrim(stream_key, maxlen=soc_config.log_retention_count, approximate=True)
			except Exception as e:
				# Log but don't fail the command if streaming fails
				logger.error(f"Failed to publish log to Redis: {e}")

			# Update output
			output += '\n' + line
			line_count += 1
			if line_count % 10 == 0:
				command_obj.output = output
				command_obj.save()

		process.wait()
		command_obj.output = output
		command_obj.return_code = process.returncode
		command_obj.save()

	except BaseException as e:
		if not isinstance(e, GeneratorExit):
			logger.error(f"Error in stream_command: {str(e)}")
		if process:
			try:
				process.kill()
			except Exception:
				pass
		raise
	finally:
		if process:
			if process.stdout:
				try:
					process.stdout.close()
				except Exception:
					pass
			try:
				if process.poll() is None:
					process.terminate()
					try:
						process.wait(timeout=5)
					except subprocess.TimeoutExpired:
						process.kill()
				else:
					process.wait()
			except Exception as ex:
				logger.error(f"Error reaping process in stream_command: {ex}")
		if conf_path and os.path.exists(conf_path):
			os.remove(conf_path)
