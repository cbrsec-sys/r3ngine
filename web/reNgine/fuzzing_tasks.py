import logging
import os
import base64
import json
import threading
from urllib.parse import urlparse
from django.utils import timezone
from redis import Redis
from django.conf import settings

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
	FFUF_DEFAULT_WORDLIST_PATH,
	RUN_DIRSEARCH
)
from reNgine.settings import (
	DEFAULT_ENABLE_HTTP_CRAWL,
	DEFAULT_RATE_LIMIT,
	DEFAULT_HTTP_TIMEOUT,
	DEFAULT_THREADS
)
from reNgine.utils.opsec import OpSecManager
from reNgine.common_func import get_http_urls, get_subdomain_from_url, extract_path_from_url, get_random_proxy
from reNgine.utils.task import (
	run_command,
	stream_command,
	save_endpoint,
	ensure_endpoints_crawled_and_execute,
	save_fuzzing_file,
	parse_custom_header_to_list
)
from startScan.models import DirectoryScan, DirectoryFile, Subdomain

logger = logging.getLogger(__name__)


def dir_file_fuzz(self, ctx=None, description=None, prepare_only=False, parse_only=None):
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

	def _execute_dir_file_fuzz(ctx, description, prepare_only=False, parse_only=None):
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
		auto_calibration = config.get(AUTO_CALIBRATION, True)
		delay = rate_limit / (threads * 100) if threads else 0
		custom_headers = config.get(CUSTOM_HEADERS) or config.get(CUSTOM_HEADER) or []
		# Toggle for optional dirsearch tool (ffuf always runs)
		run_dirsearch = config.get(RUN_DIRSEARCH, True)
		
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

		# Override with API-specific wordlist when use_api_wordlist is enabled
		from reNgine.api_tasks import resolve_wordlist_path
		wordlist_path = resolve_wordlist_path(config, wordlist_path)

		# Define input path for URLs to fuzz
		input_path = f'{self.results_dir}/input_endpoints_dir_file_fuzz.txt'

		# Build ffuf base command
		ffuf_base_cmd = 'ffuf'
		ffuf_base_cmd += f' -w {wordlist_path}'
		ffuf_base_cmd += f' -e {extensions_str}' if extensions else ''
		ffuf_base_cmd += f' -maxtime {max_time}' if max_time > 0 else ''
		ffuf_base_cmd += f' -p {delay}' if delay > 0 else ''
		if recursive_level > 0:
			ffuf_base_cmd += f' -recursion -recursion-depth {recursive_level}'
		ffuf_base_cmd += f' -maxtime-job {max_time}' if max_time > 0 else ''
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
			if 'cookie' in header.lower() or 'authorization' in header.lower():
				logger.warning(f'Authenticated FFUF fuzzing enabled via header: {header}')

		# Build dirsearch base command (only when run_dirsearch is enabled)
		dirsearch_base_cmd = None
		if run_dirsearch:
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
				if 'cookie' in header.lower() or 'authorization' in header.lower():
					logger.warning(f'Authenticated Dirsearch fuzzing enabled via header: {header}')
		else:
			logger.info('Dirsearch disabled via run_dirsearch config key. Only ffuf will run.')

		if ctx.get("urls_override"):
			urls = ctx["urls_override"]
		else:
			# Grab URLs to fuzz
			raw_urls = get_http_urls(
				is_alive=True,
				ignore_files=False,
				write_filepath=input_path,
				get_only_default_urls=False,
				ctx=ctx
			)
			if not raw_urls:
				logger.error('No alive URLs found for directory fuzzing. Skipping.')
				return []
				
			# Group by base_url and extract unique directories up to depth 2
			base_url_map = {}
			for u in raw_urls:
				parsed = urlparse(u)
				base = f"{parsed.scheme}://{parsed.netloc}"
				if base not in base_url_map:
					base_url_map[base] = set()
					
				path = parsed.path
				if path and '.' in path.split('/')[-1]:
					path = '/'.join(path.split('/')[:-1])
				if not path.endswith('/'):
					path += '/'
					
				segments = [s for s in path.strip('/').split('/') if s]
				if len(segments) <= 2:
					base_url_map[base].add(path)
					
			urls = []
			for base, paths in base_url_map.items():
				for path in list(paths)[:10]:
					urls.append(f"{base}{path}")

		logger.warning(f'Fuzzing URLs: {urls}')

		if prepare_only:
			return {
				"urls": urls,
				"ffuf_base_cmd": ffuf_base_cmd,
				"dirsearch_base_cmd": dirsearch_base_cmd,
				"enable_http_crawl": enable_http_crawl,
			}

		results = []
		redis_client = Redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'))
		opsec = OpSecManager()

		for target_url in urls:
			logger.warning(f'Fuzzing URL: {target_url}')
			url_parse = urlparse(target_url)
			base_url = url_parse.scheme + '://' + url_parse.netloc
			subdomain_name = get_subdomain_from_url(base_url)
			subdomain = Subdomain.objects.filter(name=subdomain_name, scan_history=self.scan).first()
			if not subdomain and ctx.get('subdomain_id', 0) > 0:
				subdomain = Subdomain.objects.filter(id=ctx['subdomain_id']).first()

			proxy = get_random_proxy()
			if proxy:
				if not any(proxy.startswith(s) for s in ['http://', 'https://', 'socks4://', 'socks5://']):
					proxy = 'http://' + proxy

			# Per-scan lock: prevents concurrent ffuf/dirsearch for the same scan,
			# but allows different scans to fuzz in parallel. Timeout = 30 min per
			# URL window (generous for slow targets; auto-releases on crash).
			_fuzz_lock_name = f"fuzz_execution_lock_{self.scan_id}"
			with redis_client.lock(_fuzz_lock_name, timeout=1800):
				ffuf_results_local = []
				ffuf_exc = [None]
				ds_exc = [None]

				_FUZZ_BATCH_SIZE = 100

				def _flush_ffuf_batch(batch, dirscan):
					"""Persist a batch of ffuf result dicts and link files to dirscan."""
					from django.db import transaction
					if not batch:
						return
					dfiles = []
					with transaction.atomic():
						for line in batch:
							res_url = line.get('url')
							if not res_url:
								continue
							name = base64.b64encode(extract_path_from_url(res_url).encode()).decode()
							if not name:
								continue
							length = line.get('length', 0)
							status = line.get('status', 0)
							words = line.get('words', 0)
							lines_count = line.get('lines', 0)
							content_type = line.get('content-type', '')
							duration = line.get('duration', 0)
							endpoint, _ = save_endpoint(res_url, ctx=ctx)
							if endpoint is None:
								continue
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
									lines=lines_count,
									content_type=content_type
								)
								dfiles.append(dfile)
								logger.info(f'Saved ffuf DirectoryFile {res_url} (created={d_created})')
							except Exception as e:
								logger.error(f'Failed to save ffuf DirectoryFile for {res_url}: {e}')
					if dfiles:
						dirscan.directory_files.add(*dfiles)

				def _flush_ds_batch(batch, dirscan_ds):
					"""Persist a batch of dirsearch result dicts and link files to dirscan_ds."""
					from django.db import transaction
					if not batch:
						return
					dfiles = []
					with transaction.atomic():
						for ds_res in batch:
							res_url = ds_res.get('url')
							if not res_url:
								continue
							name = base64.b64encode(extract_path_from_url(res_url).encode()).decode()
							if not name:
								continue
							status = ds_res.get('status', 0)
							length = ds_res.get('content-length', 0)
							content_type = ds_res.get('content-type', '')
							endpoint, _ = save_endpoint(res_url, ctx=ctx)
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
								dfiles.append(dfile)
								logger.info(f'Saved ds DirectoryFile {res_url} (created={d_created})')
							except Exception as e:
								logger.error(f'Failed to save ds DirectoryFile for {res_url}: {e}')
					if dfiles:
						dirscan_ds.directory_files.add(*dfiles)

				def _run_ffuf():
					from django.db import connection
					try:
						fcmd = ffuf_base_cmd + f' -u {target_url}FUZZ -json' # -s
						fcmd += f' -x {proxy}' if proxy else ''
						fcmd = opsec.apply_stealth('ffuf', fcmd, proxy=proxy)

						dirscan = DirectoryScan.objects.create(
							scanned_date=timezone.now(),
							command_line=fcmd
						)
						if subdomain:
							subdomain.directories.add(dirscan)

						logger.info(f'Running ffuf for {base_url}')
						logger.warning(f'ffuf command: {fcmd}')

						batch = []
						if parse_only is not None and target_url in parse_only.get('ffuf', {}):
							ffuf_stdout = parse_only['ffuf'][target_url]
							for raw_line in ffuf_stdout.splitlines():
								raw_line = raw_line.strip()
								if not raw_line:
									continue
								try:
									parsed = json.loads(raw_line)
									batch.append(parsed)
									ffuf_results_local.append(parsed)
								except Exception:
									pass
								if len(batch) >= _FUZZ_BATCH_SIZE:
									_flush_ffuf_batch(batch, dirscan)
									batch = []
						else:
							for line in stream_command(
									fcmd,
									shell=True,
									history_file=self.history_file,
									scan_id=self.scan_id,
									activity_id=self.activity_id):
								if not isinstance(line, dict):
									continue
								batch.append(line)
								ffuf_results_local.append(line)
								if len(batch) >= _FUZZ_BATCH_SIZE:
									_flush_ffuf_batch(batch, dirscan)
									batch = []

						# Flush remaining results
						_flush_ffuf_batch(batch, dirscan)

						if self.subscan:
							from startScan.models import SubScan
							if SubScan.objects.filter(pk=self.subscan.pk).exists():
								dirscan.dir_subscan_ids.add(self.subscan)
						dirscan.save()
					except Exception as e:
						ffuf_exc[0] = e
					finally:
						connection.close()

				def _run_dirsearch():
					from django.db import connection
					try:
						if not run_dirsearch or not dirsearch_base_cmd:
							return
						dirsearch_output = f'{self.results_dir}/dirsearch_{subdomain_name}.json'
						target_url_stripped = target_url.rstrip('/')
						dcmd = f'{dirsearch_base_cmd} -u {target_url_stripped} --format=json -o {dirsearch_output} --no-color'
						# if proxy:
						#	dcmd += f' --proxy={proxy}'

						dcmd = opsec.apply_stealth('dirsearch', dcmd) # , proxy=proxy

						dirscan_ds = DirectoryScan.objects.create(
							scanned_date=timezone.now(),
							command_line=dcmd
						)
						if subdomain:
							subdomain.directories.add(dirscan_ds)

						logger.info(f'Running dirsearch for {target_url}')
						logger.warning(f'dirsearch command: {dcmd}')

						if parse_only is None:
							run_command(
								dcmd,
								shell=True,
								history_file=self.history_file,
								scan_id=self.scan_id,
								activity_id=self.activity_id
							)

						if os.path.exists(dirsearch_output):
							try:
								with open(dirsearch_output, 'r') as f:
									results_list = json.load(f).get('results', [])
								logger.info(f'dirsearch collected {len(results_list)} results for {target_url}')
								for i in range(0, len(results_list), _FUZZ_BATCH_SIZE):
									_flush_ds_batch(results_list[i:i + _FUZZ_BATCH_SIZE], dirscan_ds)
							except Exception as e:
								logger.error(f'Error parsing dirsearch output for {base_url}: {e}')

						if self.subscan:
							from startScan.models import SubScan
							if SubScan.objects.filter(pk=self.subscan.pk).exists():
								dirscan_ds.dir_subscan_ids.add(self.subscan)
						dirscan_ds.save()
					except Exception as e:
						ds_exc[0] = e
					finally:
						connection.close()

				t_ffuf = threading.Thread(target=_run_ffuf, name=f'ffuf-{target_url}')
				t_ffuf.start()
				if run_dirsearch and dirsearch_base_cmd:
					t_ds = threading.Thread(target=_run_dirsearch, name=f'dirsearch-{target_url}')
					t_ds.start()
					t_ds.join()
				t_ffuf.join()

				if ffuf_exc[0]:
					raise ffuf_exc[0]
				if ds_exc[0]:
					logger.error(f'dirsearch failed for {target_url}: {ds_exc[0]}')

				results.extend(ffuf_results_local)

		# Crawl discovered URLs if enabled
		if enable_http_crawl:
			ctx['track'] = True
			http_crawl(self, urls, ctx=ctx)

		return results

	return ensure_endpoints_crawled_and_execute(
		self, 
		lambda ctx, description: _execute_dir_file_fuzz(ctx, description, prepare_only=prepare_only, parse_only=parse_only), 
		ctx, 
		description
	)
