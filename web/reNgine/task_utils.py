import os
import re
import subprocess
import threading
import logging
import validators
import json
from django.utils import timezone

from urllib.parse import urlparse
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

logger = logging.getLogger(__name__)

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
    if isinstance(cmd, str):
        cmd = cmd.replace('\x00', '')
    # Strip export statements (matches both single and double quotes)
    cmd = re.sub(r'^export\s+.*?\s+&&\s+', '', cmd)
    # Strip proxychains4 wrapper with its config file
    cmd = re.sub(r'^(?:[/\w]*/)?proxychains4\s+-f\s+\S+\s+', '', cmd)
    return cmd

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
    popen = None
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
            output += "\nCommand timed out."
        else:
            return_code = popen.returncode
    except Exception as e:
        logger.error(f"Error executing command {cmd}: {str(e)}")
        output = f"Error executing command: {str(e)}"
        return_code = 127 # Command not found / error
    except BaseException as e:
        logger.error(f"BaseException raised during command execution: {str(e)}")
        if popen:
            try:
                popen.kill()
            except Exception:
                pass
        raise
    finally:
        if popen:
            try:
                if popen.stdout:
                    popen.stdout.close()
            except Exception:
                pass
            try:
                if popen.poll() is None:
                    popen.terminate()
                    try:
                        popen.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        popen.kill()
                else:
                    popen.wait()
            except Exception as ex:
                logger.error(f"Error reaping process in run_command: {ex}")
        if conf_path and os.path.exists(conf_path):
            os.remove(conf_path)

    if command_obj:
        logger.warning(f"Command {command_obj.id} finished with return code {return_code}")
        command_obj.output = output.replace('\x00', '')
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
        from reNgine.osint_tasks import enrich_identities_task
        threading.Thread(
            target=enrich_identities_task,
            kwargs={'identity': email_address, 'identity_type': 'email', 'scan_history_id': scan_history.id},
            daemon=True
        ).start()

    return email, created

def save_employee(name, designation='', scan_history=None):
    employee, created = Employee.objects.get_or_create(
        name=name,
        designation=designation)

    # Add employee to ScanHistory
    if scan_history:
        scan_history.employees.add(employee)
        scan_history.save()
        from reNgine.osint_tasks import enrich_identities_task
        threading.Thread(
            target=enrich_identities_task.apply,
            kwargs={'kwargs': {'identity': name, 'identity_type': 'employee', 'scan_history_id': scan_history.id}},
            daemon=True
        ).start()

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
        from reNgine.temporal_activities import TemporalTaskProxy
        ctx['track'] = False
        proxy = TemporalTaskProxy(ctx, 'http_crawl', 'HTTP Crawl')
        results = http_crawl(
            proxy,
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
			line = line.replace('\x00', '')
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
				command_obj.output = output.replace('\x00', '')
				command_obj.save()

				# Kill switch: abort the subprocess if the scan was stopped
				if scan_id:
					try:
						from startScan.models import ScanHistory
						from reNgine.definitions import ABORTED_TASK
						_scan = ScanHistory.objects.filter(pk=scan_id).only('scan_status').first()
						if _scan and _scan.scan_status == ABORTED_TASK:
							logger.warning(
								f"[stream_command] Scan {scan_id} aborted — killing subprocess."
							)
							process.kill()
							break
					except Exception:
						pass

		process.wait()
		command_obj.output = output.replace('\x00', '')
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


def ensure_endpoints_crawled_and_execute(task_proxy, task_function, ctx, description=None, max_wait_time=300):
	"""
	Ensure endpoints are crawled before executing a task that needs alive endpoints.
	
	Args:
		task_function: The task function to execute
		ctx: Task context
		description: Task description
		max_wait_time: Maximum time to wait for endpoints (seconds)
		
	Returns:
		Task result or None if no alive endpoints available
	"""
	from copy import deepcopy
	from reNgine.common_func import get_http_urls

	logger.info(f'Ensuring endpoints are crawled for {task_function.__name__}')

	if alive_endpoints := get_http_urls(is_alive=True, ctx=ctx):
		logger.info(f'Found {len(alive_endpoints)} alive endpoints, executing {task_function.__name__}')
		return task_function(ctx=ctx, description=description)

	# No alive endpoints found, check if we have uncrawled endpoints
	uncrawled_endpoints = get_http_urls(is_uncrawled=True, ctx=ctx)

	if not uncrawled_endpoints:
		logger.warning(f'No endpoints found for {task_function.__name__}, skipping task')
		return None

	logger.info(f'Found {len(uncrawled_endpoints)} uncrawled endpoints, launching HTTP crawl first')

	from reNgine.tasks import http_crawl
	custom_ctx = deepcopy(ctx)
	custom_ctx['track'] = False  # Don't track this internal crawl

	# Run synchronously — safe here because this function is called from Temporal activities
	http_crawl(task_proxy, urls=uncrawled_endpoints[:50], ctx=custom_ctx)

	if alive_endpoints := get_http_urls(is_alive=True, ctx=ctx):
		logger.info(f'Found {len(alive_endpoints)} alive endpoints after crawl, executing {task_function.__name__}')
		return task_function(ctx=ctx, description=description)
	else:
		logger.warning(f'No alive endpoints found after crawl, skipping {task_function.__name__}')
		return None


def save_fuzzing_file(name, url, http_status, length=0, words=0, lines=0, content_type=None):
	"""
	Save or retrieve DirectoryFile safely handling database concurrency/race conditions.
	"""
	from startScan.models import DirectoryFile
	from django.db import IntegrityError
	import time

	# Try/except block with retries to handle database concurrency/race conditions
	for attempt in range(3):
		try:
			dfile, created = DirectoryFile.objects.get_or_create(
				name=name,
				url=url,
				http_status=http_status,
				defaults={
					'length': length,
					'words': words,
					'lines': lines,
					'content_type': content_type or ''
				}
			)
			return dfile, created
		except IntegrityError:
			if attempt < 2:
				time.sleep(0.1 * (attempt + 1))
			continue

	# Final attempt
	return DirectoryFile.objects.get_or_create(
		name=name,
		url=url,
		http_status=http_status,
		defaults={
			'length': length,
			'words': words,
			'lines': lines,
			'content_type': content_type or ''
		}
	)


def parse_custom_header_to_list(custom_header):
	"""
	Convert dictionary, comma-separated string, or list of headers to flat list of header strings.
	"""
	if not custom_header:
		return []
	if isinstance(custom_header, list):
		return custom_header
	if isinstance(custom_header, dict):
		return [f"{k}: {v}" for k, v in custom_header.items()]
	if isinstance(custom_header, str):
		res = []
		for h in custom_header.split(','):
			h = h.strip()
			if h:
				res.append(h)
		return res
	return []


def is_iterable(variable):
	try:
		iter(variable)
		return not isinstance(variable, (str, bytes))
	except TypeError:
		return False


def save_subdomain_metadata(subdomain, endpoint, extra_datas=None):
	"""Save metadata from endpoint to subdomain.

	Args:
		subdomain: Subdomain object
		endpoint: EndPoint object
		extra_datas: Additional metadata to save
	"""
	if extra_datas is None:
		extra_datas = {}
	if endpoint and endpoint.is_alive:
		logger.info(f'Saving HTTP metadatas from {endpoint.http_url}')
		subdomain.http_url = endpoint.http_url
		subdomain.http_status = endpoint.http_status
		subdomain.response_time = endpoint.response_time
		subdomain.page_title = endpoint.page_title
		subdomain.content_type = endpoint.content_type
		subdomain.content_length = endpoint.content_length
		subdomain.webserver = endpoint.webserver

		cname = extra_datas.get('cname')
		if cname and is_iterable(cname):
			subdomain.cname = ','.join(cname)
		elif isinstance(cname, str):
			subdomain.cname = cname

		is_cdn = extra_datas.get('is_cdn', False)
		if isinstance(is_cdn, bool):
			subdomain.is_cdn = is_cdn
		else:
			cdn = extra_datas.get('cdn')
			if cdn:
				subdomain.is_cdn = True

		cdn_name = extra_datas.get('cdn_name')
		if cdn_name:
			subdomain.cdn_name = cdn_name

		for tech in endpoint.techs.all():
			subdomain.technologies.add(tech)
		subdomain.save()
	elif http_url := extra_datas.get('http_url'):
		subdomain.http_url = http_url
		subdomain.save()
	else:
		logger.error(f'No HTTP URL found for {subdomain.name}. Skipping.')


