import os
import base64
import json
from urllib.parse import urlparse
from django.utils import timezone
from redis import Redis
from django.conf import settings
from celery.utils.log import get_task_logger

from reNgine.celery import app
from reNgine.celery_custom_task import RengineTask
from reNgine.definitions import (
	DIR_FILE_FUZZ,
	ENABLE_HTTP_CRAWL,
	RATE_LIMIT,
	EXTENSIONS,
	DEFAULT_DIR_FILE_FUZZ_EXTENSIONS,
	FOLLOW_REDIRECT,
	MAX_TIME,
	MATCH_HTTP_STATUS,
	FFUF_DEFAULT_MATCH_HTTP_STATUS,
	RECURSIVE_LEVEL,
	FFUF_DEFAULT_RECURSIVE_LEVEL,
	STOP_ON_ERROR,
	TIMEOUT,
	THREADS,
	WORDLIST,
	AUTO_CALIBRATION,
	DELAY,
	CUSTOM_HEADERS,
	CUSTOM_HEADER,
	FFUF_DEFAULT_WORDLIST_PATH
)
from reNgine.settings import (
	DEFAULT_ENABLE_HTTP_CRAWL,
	DEFAULT_RATE_LIMIT,
	DEFAULT_HTTP_TIMEOUT,
	DEFAULT_THREADS
)
from reNgine.opsec_utils import OpSecManager
from reNgine.common_func import get_http_urls, get_subdomain_from_url, extract_path_from_url, get_random_proxy
from reNgine.task_utils import (
	run_command,
	stream_command,
	save_endpoint,
	ensure_endpoints_crawled_and_execute,
	save_fuzzing_file,
	parse_custom_header_to_list
)
from startScan.models import DirectoryScan, DirectoryFile, Subdomain

logger = get_task_logger(__name__)


@app.task(name='dir_file_fuzz', queue='main_scan_queue', base=RengineTask, bind=True)
def dir_file_fuzz(self, ctx=None, description=None):
	"""Perform directory and file fuzzing using FFUF and Dirsearch.

	This wrapper ensures that any endpoints are crawled first by delegating to
	ensure_endpoints_crawled_and_execute.

	Args:
		ctx (dict, optional): Task context containing scan information.
		description (str, optional): Task description shown in UI.

	Returns:
		list: List of URLs/lines discovered during fuzzing.
	"""
	if ctx is None:
		ctx = {}

	def _execute_dir_file_fuzz(ctx, description):
		"""Inner execution logic for FFUF and Dirsearch fuzzing.

		Args:
			ctx (dict): Task context containing scan information.
			description (str): Task description shown in UI.
		"""
		from scanEngine.models import Wordlist
		from reNgine.tasks import http_crawl

		# Config parsing from yaml configuration
		config = self.yaml_configuration.get(DIR_FILE_FUZZ) or {}
		enable_http_crawl = config.get(ENABLE_HTTP_CRAWL, DEFAULT_ENABLE_HTTP_CRAWL)
		rate_limit = config.get(RATE_LIMIT) or self.yaml_configuration.get(RATE_LIMIT, DEFAULT_RATE_LIMIT)
		extensions = config.get(EXTENSIONS, DEFAULT_DIR_FILE_FUZZ_EXTENSIONS)
		
		# prepend . on extensions if not already present
		extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]
		extensions_str = ','.join(map(str, extensions))
		follow_redirect = config.get(FOLLOW_REDIRECT, False)
		max_time = config.get(MAX_TIME, 0)
		match_http_status = config.get(MATCH_HTTP_STATUS, FFUF_DEFAULT_MATCH_HTTP_STATUS)
		mc = ','.join(str(status) for status in match_http_status) if match_http_status else ''
		recursive_level = config.get(RECURSIVE_LEVEL, FFUF_DEFAULT_RECURSIVE_LEVEL)
		stop_on_error = config.get(STOP_ON_ERROR, False)
		timeout = config.get(TIMEOUT) or self.yaml_configuration.get(TIMEOUT, DEFAULT_HTTP_TIMEOUT)
		threads = config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
		wordlist_name = config.get(WORDLIST, 'dicc')
		auto_calibration = config.get(AUTO_CALIBRATION, False)
		delay = rate_limit / (threads * 100) if threads else 0
		custom_headers = config.get(CUSTOM_HEADERS) or config.get(CUSTOM_HEADER) or []
		
		# Standardize headers into a list using helper
		custom_headers_list = parse_custom_header_to_list(custom_headers)

		# Resolve wordlist path
		wordlist_path = f'/usr/src/wordlist/{wordlist_name}.txt'
		if not os.path.exists(wordlist_path):
			db_wl = Wordlist.objects.filter(short_name=wordlist_name).first()
			if db_wl:
				wordlist_path = f'/usr/src/wordlist/{db_wl.short_name}.txt'
			else:
				wordlist_path = FFUF_DEFAULT_WORDLIST_PATH

		# Define input path for URLs to fuzz
		input_path = f'{self.results_dir}/input_endpoints_dir_file_fuzz.txt'

		# Build ffuf base command
		ffuf_base_cmd = 'ffuf'
		ffuf_base_cmd += f' -w {wordlist_path}'
		ffuf_base_cmd += f' -e {extensions_str}' if extensions else ''
		ffuf_base_cmd += f' -maxtime {max_time}' if max_time > 0 else ''
		ffuf_base_cmd += f' -p {delay}' if delay > 0 else ''
		ffuf_base_cmd += f' -recursion -recursion-depth {recursive_level} ' if recursive_level > 0 else ''
		ffuf_base_cmd += f' -t {threads}' if threads and threads > 0 else ''
		ffuf_base_cmd += f' -timeout {timeout}' if timeout and timeout > 0 else ''
		ffuf_base_cmd += ' -se' if stop_on_error else ''
		ffuf_base_cmd += ' -fr' if follow_redirect else ''
		ffuf_base_cmd += ' -ac' if auto_calibration else ''
		ffuf_base_cmd += f' -mc {mc}' if mc else ''

		# Check if User-Agent is already in custom headers
		has_ua = any('user-agent' in h.lower() for h in custom_headers_list)
		if not has_ua:
			ffuf_base_cmd += ' -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"'
		
		for header in custom_headers_list:
			ffuf_base_cmd += f' -H "{header}"'

		# Build dirsearch base command
		dirsearch_base_cmd = 'dirsearch'
		dirsearch_base_cmd += f' -w {wordlist_path}'
		dirsearch_base_cmd += f' -e {extensions_str.replace(".", "")}' if extensions else ''
		dirsearch_base_cmd += f' -t {threads}' if threads and threads > 0 else ''
		dirsearch_base_cmd += f' --timeout {timeout}' if timeout and timeout > 0 else ''
		dirsearch_base_cmd += f' -r' if recursive_level > 0 else ''
		dirsearch_base_cmd += f' --max-recursion-depth {recursive_level}' if recursive_level > 0 else ''
		dirsearch_base_cmd += f' -i {mc}' if mc else ''
		dirsearch_base_cmd += ' --follow-redirects' if follow_redirect else ''
		dirsearch_base_cmd += f' --max-time {max_time}' if max_time > 0 else ''
		dirsearch_base_cmd += f' --delay {delay}' if delay > 0 else ''
		dirsearch_base_cmd += ' --exit-on-error' if stop_on_error else ''
		
		if not has_ua:
			dirsearch_base_cmd += ' --random-agent'

		for header in custom_headers_list:
			dirsearch_base_cmd += f' -H "{header}"'

		# Grab URLs to fuzz
		urls = get_http_urls(
			is_alive=True,
			ignore_files=False,
			write_filepath=input_path,
			get_only_default_urls=True,
			ctx=ctx
		)
		if not urls:
			logger.error('No alive URLs found for directory fuzzing. Skipping.')
			return []

		logger.warning(f'Fuzzing URLs: {urls}')

		results = []
		redis_client = Redis.from_url(os.environ.get('CELERY_BROKER', 'redis://redis:6379/0'))
		opsec = OpSecManager()

		for url in urls:
			logger.warning(f'Fuzzing URL: {url}')
			url_parse = urlparse(url)
			base_url = url_parse.scheme + '://' + url_parse.netloc
			subdomain_name = get_subdomain_from_url(base_url)
			subdomain = Subdomain.objects.filter(name=subdomain_name, scan_history=self.scan).first()
			if not subdomain and ctx.get('subdomain_id', 0) > 0:
				subdomain = Subdomain.objects.filter(id=ctx['subdomain_id']).first()

			proxy = get_random_proxy()
			if proxy:
				if not any(proxy.startswith(s) for s in ['http://', 'https://', 'socks4://', 'socks5://']):
					proxy = 'http://' + proxy

			# Use a global lock to ensure sequential execution across all workers
			with redis_client.lock("fuzz_execution_lock", timeout=14400):
				logger.info(f'Running ffuf for {base_url}')
				# 1. Run FFUF
				fcmd = ffuf_base_cmd + f' -u {base_url}/FUZZ -json -s'
				fcmd += f' -x {proxy}' if proxy else ''
				fcmd = opsec.apply_stealth('ffuf', fcmd, proxy=proxy)
				
				# Initialize DirectoryScan object for FFUF
				dirscan = DirectoryScan.objects.create(
					scanned_date=timezone.now(),
					command_line=fcmd
				)
				if subdomain:
					subdomain.directories.add(dirscan)
					subdomain.save()

				logger.info(f'Running ffuf for {base_url}')
				logger.warning(f'ffuf command: {fcmd}')
				for line in stream_command(
						fcmd,
						shell=True,
						history_file=self.history_file,
						scan_id=self.scan_id,
						activity_id=self.activity_id):

					if not isinstance(line, dict):
						continue

					results.append(line)
					res_url = line.get('url')
					if not res_url:
						continue

					name = base64.b64encode(extract_path_from_url(res_url).encode()).decode()
					length = line.get('length', 0)
					status = line.get('status', 0)
					words = line.get('words', 0)
					lines = line.get('lines', 0)
					content_type = line.get('content-type', '')
					duration = line.get('duration', 0)

					if not name:
						continue

					endpoint, created = save_endpoint(res_url, ctx=ctx)
					if endpoint is None:
						continue

					logger.warning(f'Endpoint: {endpoint} Created: {created}')
					endpoint.http_status = status
					endpoint.content_length = length
					endpoint.response_time = duration / 1000000000
					endpoint.content_type = content_type
					endpoint.save()

					try:
						dfile, d_created = save_fuzzing_file(
							name=name,
							url=res_url,
							http_status=status,
							length=length,
							words=words,
							lines=lines,
							content_type=content_type
						)
						logger.info(f'Saved DirectoryFile for {res_url}')
						logger.warning(f'DirectoryFile: {dfile} Created: {d_created}')
					except Exception as e:
						logger.error(f'Failed to save DirectoryFile for {res_url}: {e}')
						continue

					dirscan.directory_files.add(dfile)
					if self.subscan:
						dirscan.dir_subscan_ids.add(self.subscan)

				dirscan.save()

				# 2. Run Dirsearch
				dirsearch_output = f'{self.results_dir}/dirsearch_{subdomain_name}.json'
				dcmd = f'{dirsearch_base_cmd} -u {base_url} --format=json -o {dirsearch_output} --no-color'
				if proxy:
					dcmd += f' --proxy={proxy}'
				
				dcmd = opsec.apply_stealth('dirsearch', dcmd, proxy=proxy)
				
				# Initialize DirectoryScan object for Dirsearch
				dirscan_ds = DirectoryScan.objects.create(
					scanned_date=timezone.now(),
					command_line=dcmd
				)
				if subdomain:
					subdomain.directories.add(dirscan_ds)
					subdomain.save()

				logger.info(f'Running dirsearch for {base_url}')
				logger.warning(f'dirsearch command: {dcmd}')
				run_command(
					dcmd,
					shell=True,
					history_file=self.history_file,
					scan_id=self.scan_id,
					activity_id=self.activity_id
				)
				
				# Parse dirsearch results from output file
				if os.path.exists(dirsearch_output):
					try:
						with open(dirsearch_output, 'r') as f:
							ds_data = json.load(f)
							for ds_res in ds_data.get('results', []):
								res_url = ds_res.get('url')
								status = ds_res.get('status', 0)
								length = ds_res.get('content-length', 0)
								content_type = ds_res.get('content-type', '')
								
								if not res_url:
									continue
								
								name = base64.b64encode(extract_path_from_url(res_url).encode()).decode()
								if not name:
									continue
								
								endpoint, created = save_endpoint(res_url, ctx=ctx)
								if endpoint is None:
									continue

								endpoint.http_status = status
								endpoint.content_length = length
								endpoint.content_type = content_type
								endpoint.save()

								try:
									dfile, d_created = save_fuzzing_file(
										name=name,
										url=res_url,
										http_status=status,
										length=length,
										content_type=content_type
									)
									logger.info(f'Saved DirectoryFile for {res_url}')
									logger.warning(f'DirectoryFile: {dfile} Created: {d_created}')
								except Exception as e:
									logger.error(f'Failed to save DirectoryFile for {res_url}: {e}')
									continue

								dirscan_ds.directory_files.add(dfile)
								if self.subscan:
									dirscan_ds.dir_subscan_ids.add(self.subscan)
					except Exception as e:
						logger.error(f'Error parsing dirsearch results for {base_url}: {e}')

				dirscan_ds.save()

		# Crawl discovered URLs if enabled
		if enable_http_crawl:
			ctx['track'] = True
			http_crawl(urls, ctx=ctx)

		return results

	return ensure_endpoints_crawled_and_execute(_execute_dir_file_fuzz, ctx, description)
