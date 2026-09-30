"""Web app and API discovery (kiterunner, arjun, linkfinder, inql, grpcurl, ...) and its probe helpers.

Split out of the former reNgine/tasks/crawl.py; re-exported by
reNgine.tasks.crawl for backward compatibility.
"""
import os
import json
import hashlib
import re
import shlex
import requests
import urllib3
from pathlib import Path
from urllib.parse import urlparse

from reNgine.common_func import *  # noqa: F401,F403
from reNgine.definitions import *  # noqa: F401,F403
from startScan.models import *  # noqa: F401,F403
from reNgine.utils.logger import get_module_logger
from reNgine.utils.task import run_command, save_endpoint, save_parameter
from reNgine.utils.graph import Neo4jManager

logger = get_module_logger(__name__)

#: Ports where gRPC is plausibly served. Every probe costs a connect timeout, and
#: gRPC has no convention of living on arbitrary ports, so the rest of what the
#: port scan found is not worth the wait.
_GRPC_CANDIDATE_PORTS = frozenset({443, 8443, 9443, 8080, 8081, 9090, 9091, 50051, 50052})


#: Ports that speak TLS. grpcurl must not be told -plaintext for these.
_GRPC_TLS_PORTS = frozenset({443, 8443, 9443})


#: Service names that mark a port as worth probing, or as TLS, whatever its number.
_GRPC_SERVICE_HINTS = ('grpc', 'http2', 'h2')


_TLS_SERVICE_HINTS = ('https', 'ssl', 'tls')


#: Upper bound on probes per host, so a host with many open ports cannot stall
#: the task on connect timeouts alone.
_GRPC_MAX_PORTS_PER_HOST = 5


#: Seconds allowed for the connection itself.
_GRPC_CONNECT_TIMEOUT = 3


#: Seconds allowed for the whole call. Without it a host that completes the
#: handshake and then ignores the reflection request holds grpcurl open with no
#: deadline of any kind.
_GRPC_MAX_TIME = 10


#: Backstop at the subprocess level, in case grpcurl itself does not exit.
#: run_command's default is 43200 seconds, which is no bound at this scale.
_GRPC_COMMAND_TIMEOUT = 30


def gqlspection_schema_dumped(return_code, output):
	"""True when GQLSpection printed a schema.

	The tool does not report whether introspection is enabled; it dumps the
	schema *through* introspection, so a successful dump is itself the finding
	and a failure means there was nothing to dump. The previous check looked for
	the word "enabled" anywhere in the output, which appears only in the tool's
	own help text.
	"""
	if return_code != 0:
		return False
	text = (output or '').strip()
	if not text:
		return False
	return 'traceback' not in text.lower()


def grpc_probe_targets(open_ports, url_port, url_is_https):
	"""Decide which ports to try gRPC on for one host.

	Args:
		open_ports: (number, service_name) pairs the port scan found for the host.
		url_port: the port carried by the host's URL, used only when the port scan
			produced nothing — a scan without port_scan must not lose coverage.
		url_is_https: whether that URL was https, which decides TLS for the fallback.

	Returns:
		list[tuple[int, bool]]: (port, use_tls) pairs, ordered and capped.
	"""
	def _is_tls(port, service):
		lowered = (service or '').lower()
		return port in _GRPC_TLS_PORTS or any(hint in lowered for hint in _TLS_SERVICE_HINTS)

	candidates = {}
	for number, service in open_ports:
		lowered = (service or '').lower()
		named = any(hint in lowered for hint in _GRPC_SERVICE_HINTS)
		if number in _GRPC_CANDIDATE_PORTS or named:
			candidates[number] = _is_tls(number, service)

	if candidates:
		ordered = sorted(candidates.items())[:_GRPC_MAX_PORTS_PER_HOST]
		return ordered

	if open_ports:
		# The port scan ran and found nothing gRPC-shaped. Probing the web port
		# anyway is what made every run report "Failed to dial" on 443.
		return []

	return [(url_port, url_is_https)]


def web_api_discovery(self, urls=[], ctx={}, description=None):
	"""Advanced Web App & API Discovery using Kiterunner, Arjun, LinkFinder, etc."""
	scan_id = ctx.get('scan_history_id')
	config = self.yaml_configuration.get(WEB_API_DISCOVERY) or {}
	uses_tools = ctx.get('api_discovery_tools') or resolve_api_discovery_tools(
		config, default=['kiterunner', 'arjun', 'linkfinder', 'paramspider', 'semgrep'])
	kr_wordlist = ctx.get('kr_wordlist') or config.get(KITERUNNER_WORDLIST, 'routes-small.kite')
	scan_only_active = config.get(SCAN_ONLY_ACTIVE, True)
	threads = config.get(THREADS) or self.yaml_configuration.get(THREADS, DEFAULT_THREADS)
	timeout = config.get(TIMEOUT) or self.yaml_configuration.get(TIMEOUT, DEFAULT_HTTP_TIMEOUT)
	arjun_methods = config.get(ARJUN_METHODS, ARJUN_DEFAULT_METHODS)
	proxy = None
	kr_proxy = 'socks5://tor:9050' if ctx.get('use_tor') else None

	logger.warning("[WEB_API] Starting Web API Discovery | scan_id=%s | tools=%s", scan_id, uses_tools)

	# Get targets
	if not urls:
		urls = get_http_urls(
			is_alive=scan_only_active,
			write_filepath=None,
			ctx=ctx
		)

	if not urls:
		logger.warning('[WEB_API] No targets found for Web API Discovery — aborting.')
		return

	logger.warning('[WEB_API] Target URL count: %d | scan_only_active=%s', len(urls), scan_only_active)

	results_dir = f"{self.results_dir}/web_api_discovery"
	os.makedirs(results_dir, exist_ok=True)

	# ── Phase 1: Map URLs to subdomains ─────────────────────────────────────
	# Build subdomain_targets {name: (Subdomain, base_url)} for Kiterunner and
	# an ordered url_subdomain_map for per-URL tools (Arjun, LinkFinder, InQL).
	# URL pattern deduplication removes param-value variants that add no value
	# (e.g. locale=ar vs locale=cs share the same path+key signature).
	subdomain_targets = {}
	url_subdomain_map = []
	processed_url_patterns = set()
	skipped_no_subdomain = 0

	for url in urls:
		parsed = urlparse(url)
		query_keys = sorted(parse_qs(parsed.query).keys())
		url_pattern = f"{parsed.netloc}{parsed.path}?{'&'.join(query_keys)}"
		if url_pattern in processed_url_patterns:
			continue
		processed_url_patterns.add(url_pattern)

		subdomain_name = get_subdomain_from_url(url)
		subdomain = Subdomain.objects.filter(name=subdomain_name, scan_history=self.scan).first()
		if not subdomain:
			skipped_no_subdomain += 1
			continue

		if subdomain_name not in subdomain_targets:
			base_url = f"{parsed.scheme}://{parsed.netloc}/"
			subdomain_targets[subdomain_name] = (subdomain, base_url)

		url_subdomain_map.append((url, subdomain_name, subdomain))

	logger.warning(
		'[WEB_API] URL mapping complete: %d unique subdomains, %d deduplicated URLs queued, %d skipped (no subdomain record)',
		len(subdomain_targets), len(url_subdomain_map), skipped_no_subdomain,
	)

	# ── Kiterunner: batched scan across subdomains ───────────────────────────
	# Subdomains are batched in groups of `threads` and written to a hosts file
	# so that -j (max-parallel-hosts) is actually utilised rather than wasted
	# on a single host per call.
	# Per-subdomain .json files act as the idempotency guard for Temporal retries:
	# any subdomain with a non-empty file is skipped; the rest form the next batch.
	if 'kiterunner' in uses_tools:
		# Task 6: Validate wordlist path to prevent traversal (Rule 1.1/1.2)
		_kr_base_dir = Path('/usr/src/wordlist/kr').resolve()
		_kr_wordlist_path = (_kr_base_dir / kr_wordlist).resolve()
		if not str(_kr_wordlist_path).startswith(str(_kr_base_dir)):
			logger.error('[WEB_API] Kiterunner: wordlist path %s escapes base dir — skipping', kr_wordlist)
		elif not _kr_wordlist_path.exists():
			logger.error('[WEB_API] Kiterunner: wordlist file %s not found — skipping (download may have failed at container start)', kr_wordlist)
		else:
			logger.warning('[WEB_API] Kiterunner: scanning %d subdomains | wordlist=%s | batch_size=%d', len(subdomain_targets), kr_wordlist, threads)

			# Separate cached subdomains from those that still need scanning
			to_scan = {
				name: (sub, base_url)
				for name, (sub, base_url) in subdomain_targets.items()
				if not (os.path.exists(f"{results_dir}/kr_{name}.json") and os.path.getsize(f"{results_dir}/kr_{name}.json") > 0)
			}
			cached_count = len(subdomain_targets) - len(to_scan)
			if cached_count:
				logger.warning('[WEB_API] Kiterunner: %d subdomains cached, scanning %d new', cached_count, len(to_scan))

			# Scan phase: batch uncached subdomains so -j is utilised
			scan_items = list(to_scan.items())
			for batch_start in range(0, len(scan_items), threads):
				batch = dict(scan_items[batch_start:batch_start + threads])
				batch_idx = batch_start // threads

				hosts_file = f"{results_dir}/kr_hosts_batch_{batch_idx}.txt"
				with open(hosts_file, 'w') as hf:
					for _name, (_sub, _base_url) in batch.items():
						hf.write(_base_url + '\n')

				combined_output = f"{results_dir}/kr_batch_{batch_idx}.json"
				cmd = (
					f"kr scan {hosts_file}"
					f" -w {_kr_wordlist_path}"
					f" -j {threads}"
					f" --timeout {timeout}s"
					f" --fail-status-codes 404"
					f" -o json -q"
					f" | tee {combined_output}"
				)
				logger.warning('[WEB_API] Kiterunner: batch %d — %d hosts | cmd: %s', batch_idx, len(batch), cmd)
				run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id, proxy=kr_proxy)
				logger.warning('[WEB_API] Kiterunner: batch %d finished', batch_idx)

				# Split combined JSON output into per-subdomain files for caching
				if os.path.exists(combined_output):
					subdomain_lines: dict = {name: [] for name in batch}
					with open(combined_output, 'r') as f:
						for line in f:
							line = line.strip()
							if not line:
								continue
							try:
								entry = json.loads(line)
								target_host = urlparse(entry.get('target', '')).hostname or ''
								if target_host in subdomain_lines:
									subdomain_lines[target_host].append(line)
							except (ValueError, AttributeError, TypeError):
								continue  # not a JSON object with a string target
					for _name, lines in subdomain_lines.items():
						if lines:
							_kr_out = f"{results_dir}/kr_{_name}.json"
							with open(_kr_out, 'w') as f:
								f.write('\n'.join(lines) + '\n')
				else:
					logger.warning('[WEB_API] Kiterunner: combined output missing for batch %d', batch_idx)

			# Parse pass: read all per-subdomain files (cached + newly written)
			for subdomain_name, (subdomain, base_url) in subdomain_targets.items():
				kr_output = f"{results_dir}/kr_{subdomain_name}.json"
				if not os.path.exists(kr_output):
					logger.warning('[WEB_API] Kiterunner: output file missing for %s', subdomain_name)
					continue
				try:
					kr_parsed = urlparse(base_url)
					kr_endpoints = 0
					kr_params = 0
					with open(kr_output, 'r') as f:
						for line in f:
							if not line.strip():
								continue
							entry = json.loads(line)
							found_path = entry.get('path', '')
							if not found_path:
								continue
							# Use correct status field from responses array
							responses = entry.get('responses', [])
							http_status = responses[0].get('sc') if responses else None
							# Skip 404s as defence-in-depth (--fail-status-codes 404 handles most)
							if http_status == 404:
								continue
							full_url = f"{kr_parsed.scheme}://{kr_parsed.netloc}{found_path}"
							endpoint, _ = save_endpoint(full_url, ctx=ctx, subdomain=subdomain, http_status=http_status)
							kr_endpoints += 1
							if endpoint and '?' in full_url:
								params = extract_params_from_url(full_url)
								for p in params:
									save_parameter(endpoint, p['name'], param_type='Kiterunner', value=p['value'])
									kr_params += 1
					logger.warning('[WEB_API] Kiterunner: %s → %d endpoints, %d params saved', subdomain_name, kr_endpoints, kr_params)
				except Exception as e:
					logger.error('[WEB_API] Kiterunner: error parsing output for %s: %s', subdomain_name, e)
	else:
		logger.warning('[WEB_API] Kiterunner: skipped (not in uses_tools)')

	# ── Per-URL tools (Arjun, ParamSpider, LinkFinder, InQL) ─────────────────
	# Each tool uses a file-existence check so that Temporal retries skip work
	# that already completed in a previous attempt.
	processed_paramspider_subdomains = set()
	processed_arjun_subdomains = set()
	processed_linkfinder_subdomains = set()
	processed_inql_subdomains = set()
	processed_jwt_subdomains = set()
	processed_graphql_cop_subdomains = set()
	# Gate-check caches: has_graphql_endpoint probes up to 6 network paths with a
	# 5s timeout each, and has_jwt_tokens issues 2 DB queries — both return the
	# same result for every URL sharing a subdomain.  Evaluate each gate once per
	# subdomain and reuse the cached bool for subsequent URLs.
	_graphql_gate_cache: dict = {}  # subdomain_name -> bool
	_jwt_gate_cache: dict = {}      # subdomain_name -> bool
	logger.warning('[WEB_API] Starting per-URL tool phase for %d URLs', len(url_subdomain_map))

	for url, subdomain_name, subdomain in url_subdomain_map:

		# Arjun - Parameter discovery (once per subdomain; output is subdomain-scoped)
		# Cache sentinel: arjun_{subdomain}.json exists (even empty) means already ran.
		# When arjun confirms params it writes the JSON file; when it can't (e.g.
		# connection error during logicforcing) it exits without writing anything.
		# In that case we fall back to parsing the extracted-params line from stdout
		# so parameters found in the response are still persisted.
		if 'arjun' in uses_tools and subdomain_name not in processed_arjun_subdomains:
			processed_arjun_subdomains.add(subdomain_name)
			arjun_output = f"{results_dir}/arjun_{subdomain_name}.json"
			arjun_stdout = ''
			if os.path.exists(arjun_output):
				logger.warning('[WEB_API] Arjun: cache hit for %s — loading existing results', subdomain_name)
			else:
				cmd = f"arjun -u {shlex.quote(url)} --passive -m {arjun_methods} -t {threads} -oJ {shlex.quote(arjun_output)}"
				logger.warning('[WEB_API] Arjun: running on %s | cmd: %s', subdomain_name, cmd)
				_, arjun_stdout = run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id)
				# Write empty sentinel so Temporal retries don't re-run the tool
				if not os.path.exists(arjun_output):
					open(arjun_output, 'w').close()
				logger.warning('[WEB_API] Arjun: finished on %s', subdomain_name)
			arjun_params = 0
			if os.path.exists(arjun_output) and os.path.getsize(arjun_output) > 0:
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
											arjun_params += 1
								elif isinstance(params, list):
									method = details.get('method', 'unknown')
									for p in params:
										save_parameter(endpoint, p, param_type=method)
										arjun_params += 1
				except Exception as e:
					logger.error('[WEB_API] Arjun: error parsing output for %s: %s', subdomain_name, e)
			if arjun_params == 0 and arjun_stdout:
				# Arjun printed "Extracted N parameters from response for testing: p1, p2, ..."
				# but couldn't confirm them (e.g. connection error). Save them anyway.
				_match = re.search(r'Extracted\s+\d+\s+parameters?\s+from\s+response\s+for\s+testing:\s+(.+)', arjun_stdout)
				if _match:
					endpoint, _ = save_endpoint(url, ctx=ctx, subdomain=subdomain)
					if endpoint:
						for p_name in [p.strip() for p in _match.group(1).split(',') if p.strip()]:
							save_parameter(endpoint, p_name, param_type='Arjun')
							arjun_params += 1
			logger.warning('[WEB_API] Arjun: %s → %d params saved', subdomain_name, arjun_params)

		# ParamSpider - once per subdomain
		# ParamSpider writes results to results/{domain}.txt (not stdout).
		# The sentinel file ps_{domain}.txt is written after a run so Temporal
		# retries skip re-running the tool; actual URLs are read from results/.
		if 'paramspider' in uses_tools and subdomain_name not in processed_paramspider_subdomains:
			processed_paramspider_subdomains.add(subdomain_name)
			ps_sentinel = f"{results_dir}/ps_{subdomain_name}.txt"
			ps_results_file = f"{results_dir}/results/{subdomain_name}.txt"
			if os.path.exists(ps_sentinel):
				logger.warning('[WEB_API] ParamSpider: cache hit for %s — loading existing results', subdomain_name)
			else:
				cmd = f"paramspider --domain {shlex.quote(subdomain_name)}"
				proxy = get_random_proxy()
				if proxy:
					cmd = f"paramspider --domain {shlex.quote(subdomain_name)} --proxy {shlex.quote(proxy)}"
				logger.warning('[WEB_API] ParamSpider: running on %s | cmd: %s', subdomain_name, cmd)
				run_command(cmd, shell=True, cwd=results_dir, scan_id=self.scan_id, activity_id=self.activity_id)
				# Write sentinel so retries skip re-running
				open(ps_sentinel, 'w').close()
				logger.warning('[WEB_API] ParamSpider: finished on %s', subdomain_name)
			if os.path.exists(ps_results_file):
				try:
					ps_params = 0
					with open(ps_results_file, 'r') as f:
						for line in f:
							line = line.strip()
							if line and is_valid_url(line):
								endpoint, _ = save_endpoint(line, ctx=ctx, subdomain=subdomain)
								if endpoint:
									parsed = urlparse(line)
									if parsed.query:
										for q in parsed.query.split('&'):
											if '=' in q:
												p_name = q.split('=')[0]
												save_parameter(endpoint, p_name, param_type='URL Query')
												ps_params += 1
					logger.warning('[WEB_API] ParamSpider: %s → %d params saved', subdomain_name, ps_params)
				except Exception as e:
					logger.error('[WEB_API] ParamSpider: error parsing output for %s: %s', subdomain_name, e)
			else:
				logger.warning('[WEB_API] ParamSpider: no results file for %s (tool may have found nothing)', subdomain_name)

		# LinkFinder - once per subdomain (JS endpoint and parameter extraction).
		# Two passes:
		#  1. Crawl the root URL with -d so linkfinder discovers inline <script> tags.
		#  2. Run linkfinder against each JS file already recorded in the DB for this
		#     subdomain (downloaded by the HTTP crawler), bypassing 403s on the HTML page.
		# processed_linkfinder_subdomains is the primary dedup guard.
		# os.path.exists(lf_output) is the Temporal retry guard.
		if 'linkfinder' in uses_tools and subdomain_name not in processed_linkfinder_subdomains:
			processed_linkfinder_subdomains.add(subdomain_name)
			lf_output = f"{results_dir}/lf_{subdomain_name}.txt"
			if os.path.exists(lf_output):
				logger.warning('[WEB_API] LinkFinder: cache hit for %s — loading existing results', subdomain_name)
			else:
				# Pass 1: root URL with -d
				cmd = f"python3 /usr/src/github/LinkFinder/linkfinder.py -d -i {shlex.quote(url)} -o cli 2>/dev/null | tee {shlex.quote(lf_output)}"
				logger.warning('[WEB_API] LinkFinder: running on %s | cmd: %s', subdomain_name, cmd)
				run_command(cmd, shell=True, cwd=results_dir, scan_id=self.scan_id, activity_id=self.activity_id)
				# Pass 2: run on JS endpoints already in the DB for this subdomain
				try:
					js_endpoints = EndPoint.objects.filter(
						scan_history__id=self.scan_id,
						subdomain=subdomain,
					).filter(
						Q(http_url__iendswith='.js') |
						Q(http_url__icontains='.js?') |
						Q(content_type__icontains='javascript')
					).values_list('http_url', flat=True)[:50]
					for js_url in js_endpoints:
						if not js_url:
							continue
						js_hash = hashlib.md5(js_url.encode()).hexdigest()[:8]  # noqa: S324 (non-crypto)
						js_local = f"{results_dir}/js_{subdomain_name}_{js_hash}.js"
						if not os.path.exists(js_local):
							try:
								resp = requests.get(js_url, timeout=10, verify=False, allow_redirects=True)  # noqa: S501
								if resp.status_code == 200:
									with open(js_local, 'wb') as jf:
										jf.write(resp.content[:512 * 1024])  # cap at 512 KiB
							except Exception:
								continue
						if os.path.exists(js_local) and os.path.getsize(js_local) > 0:
							lf_js_cmd = f"python3 /usr/src/github/LinkFinder/linkfinder.py -i {shlex.quote(js_local)} -o cli 2>/dev/null >> {shlex.quote(lf_output)}"
							run_command(lf_js_cmd, shell=True, cwd=results_dir, scan_id=self.scan_id, activity_id=self.activity_id)
				except Exception as exc:
					logger.error('[WEB_API] LinkFinder: JS-file pass failed for %s: %s', subdomain_name, exc)
				logger.warning('[WEB_API] LinkFinder: finished on %s', subdomain_name)
			# Parse output with improved host classification
			if os.path.exists(lf_output):
				try:
					lf_endpoints = 0
					lf_params = 0
					lf_new_subs = 0
					base_parsed = urlparse(url)
					base_host = base_parsed.hostname or ''
					scan_domain = base_host.split('.', 1)[-1] if '.' in base_host else base_host
					with open(lf_output, 'r') as f:
						for line in f:
							line = line.strip()
							if not line or line.startswith('#') or line.startswith('Error'):
								continue
							# Normalise protocol-relative URLs
							if line.startswith('//'):
								line = base_parsed.scheme + ':' + line
							# Resolve absolute paths against the base URL
							if line.startswith('/'):
								full_url = f"{base_parsed.scheme}://{base_parsed.netloc}{line}"
							elif line.startswith('http'):
								full_url = line
							else:
								# Relative path or noise (MIME type strings, etc.) — skip
								continue
							parsed_out = urlparse(full_url)
							out_host = parsed_out.hostname or ''
							# In-scope: same subdomain or any subdomain of the scan domain
							if out_host == base_host or (scan_domain and out_host.endswith('.' + scan_domain)):
								if out_host != base_host:
									# Discovered a new subdomain via JS analysis
									new_sub_qs = Subdomain.objects.filter(
										scan_history__id=self.scan_id,
										name=out_host,
									)
									if not new_sub_qs.exists():
										try:
											Subdomain.objects.get_or_create(
												name=out_host,
												scan_history_id=self.scan_id,
												defaults={'target_domain': subdomain.target_domain},
											)
											lf_new_subs += 1
											logger.warning('[WEB_API] LinkFinder: discovered new subdomain %s via JS analysis', out_host)
										except Exception:
											pass
								endpoint, _ = save_endpoint(full_url, ctx=ctx, subdomain=subdomain)
								lf_endpoints += 1
								if endpoint is not None and '?' in full_url:
									params = extract_params_from_url(full_url)
									for p in params:
										save_parameter(endpoint, p['name'], param_type='LinkFinder', value=p['value'])
										lf_params += 1
							# External hosts are silently dropped
					logger.warning('[WEB_API] LinkFinder: %s → %d endpoints, %d params, %d new subdomains', subdomain_name, lf_endpoints, lf_params, lf_new_subs)
				except Exception as e:
					logger.error('[WEB_API] LinkFinder: error parsing output for %s: %s', subdomain_name, e)
			else:
				logger.warning('[WEB_API] LinkFinder: output file missing for %s', subdomain_name)

		# InQL - GraphQL Discovery (only when a GraphQL endpoint is detected).
		# processed_inql_subdomains is the primary dedup guard so the tool runs at
		# most once per subdomain regardless of how many URLs that subdomain has.
		# _graphql_gate_cache[subdomain_name] is populated on first visit so that
		# has_graphql_endpoint (which issues a DB iregex query + up to 6 network
		# probes × 5 s each) is called at most once per subdomain, not per URL.
		if 'inql' in uses_tools and subdomain_name not in processed_inql_subdomains:
			processed_inql_subdomains.add(subdomain_name)
			if subdomain_name not in _graphql_gate_cache:
				logger.warning('[WEB_API] InQL: checking GraphQL gate for %s (first visit)', subdomain_name)
				_graphql_gate_cache[subdomain_name] = has_graphql_endpoint(self.scan_id, url)
			if not _graphql_gate_cache[subdomain_name]:
				logger.warning('[WEB_API] InQL: no GraphQL endpoint detected, skipping %s', subdomain_name)
			else:
				inql_output = f"{results_dir}/inql_{subdomain_name}"
				cmd = f"inql -t {shlex.quote(url)} -o {shlex.quote(inql_output)}"
				proxy = get_random_proxy()
				if proxy:
					cmd += f" -p {shlex.quote(proxy)}"
				logger.warning('[WEB_API] InQL: running on %s | cmd: %s', subdomain_name, cmd)
				run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id)
				if os.path.exists(inql_output):
					try:
						inql_findings = parse_inql_results(inql_output)
						for finding in inql_findings:
							save_endpoint(url, ctx=ctx, subdomain=subdomain, source='InQL (GraphQL Found)')
						from reNgine.cpde.graphql_enricher import enrich_graphql_params
						enrich_graphql_params(inql_output, url, subdomain, ctx)
						logger.warning('[WEB_API] InQL: %s → %d GraphQL findings saved', subdomain_name, len(inql_findings))
					except Exception as e:
						logger.error('[WEB_API] InQL: error parsing results for %s: %s', subdomain_name, e)
				else:
					logger.warning('[WEB_API] InQL: no output directory found for %s', subdomain_name)

		# jwt_tool - JWT security testing (only when JWT tokens have been found).
		# processed_jwt_subdomains is the primary dedup guard so the tool runs at
		# most once per subdomain regardless of how many URLs that subdomain has.
		# _jwt_gate_cache[subdomain_name] is populated on first visit so that
		# has_jwt_tokens (2 DB queries per call) runs at most once per subdomain.
		if JWT_TOOL in uses_tools and subdomain_name not in processed_jwt_subdomains:
			processed_jwt_subdomains.add(subdomain_name)
			if subdomain_name not in _jwt_gate_cache:
				logger.warning('[WEB_API] jwt_tool: checking JWT gate for %s (first visit)', subdomain_name)
				_jwt_gate_cache[subdomain_name] = has_jwt_tokens(self.scan_id, subdomain=subdomain)
			if _jwt_gate_cache[subdomain_name]:
				logger.warning('[WEB_API] jwt_tool: JWT tokens found, running on %s', subdomain_name)
				from reNgine.tasks.api import run_jwt_scan
				run_jwt_scan(self, ctx, url, subdomain, results_dir)
				logger.warning('[WEB_API] jwt_tool: finished on %s', subdomain_name)
			else:
				logger.warning('[WEB_API] jwt_tool: no JWT tokens detected, skipping %s', subdomain_name)

		# graphql-cop - GraphQL security audit (only when a GraphQL endpoint is detected).
		# processed_graphql_cop_subdomains is the primary dedup guard so the tool runs
		# at most once per subdomain regardless of how many URLs that subdomain has.
		# Shares _graphql_gate_cache with InQL — no second round of probes needed.
		if GRAPHQL_COP in uses_tools and subdomain_name not in processed_graphql_cop_subdomains:
			processed_graphql_cop_subdomains.add(subdomain_name)
			if subdomain_name not in _graphql_gate_cache:
				logger.warning('[WEB_API] graphql-cop: checking GraphQL gate for %s (first visit)', subdomain_name)
				_graphql_gate_cache[subdomain_name] = has_graphql_endpoint(self.scan_id, url)
			if not _graphql_gate_cache[subdomain_name]:
				logger.warning('[WEB_API] graphql-cop: no GraphQL endpoint detected, skipping %s', subdomain_name)
			else:
				logger.warning('[WEB_API] graphql-cop: running on %s', subdomain_name)
				from reNgine.tasks.api import run_graphql_cop
				run_graphql_cop(self, ctx, url, subdomain)
				logger.warning('[WEB_API] graphql-cop: finished on %s', subdomain_name)

	# Semgrep - Post-discovery pattern matching
	if 'semgrep' in uses_tools:
		semgrep_output = f"{results_dir}/semgrep_results.json"
		cmd = f"semgrep scan --config auto --json --output {semgrep_output} {results_dir}"
		logger.warning('[WEB_API] Semgrep: running post-discovery scan | cmd: %s', cmd)
		run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id)
		if os.path.exists(semgrep_output):
			try:
				with open(semgrep_output, 'r') as f:
					data = json.load(f)
					matches = data.get('results', [])
					for match in matches:
						vuln_data = parse_semgrep_result(match)
						save_vulnerability(vuln_data, self.scan, self.domain)
				logger.warning('[WEB_API] Semgrep: %d vulnerabilities saved', len(matches))
			except Exception as e:
				logger.error('[WEB_API] Semgrep: error parsing output: %s', e)
		else:
			logger.warning('[WEB_API] Semgrep: output file not found — may have failed silently')
	else:
		logger.warning('[WEB_API] Semgrep: skipped (not in uses_tools)')

	# Retire.js - JS Library vulnerability scan
	if 'retire' in uses_tools:
		retire_output = f"{results_dir}/retire_results.json"
		cmd = f"npx -y retire --path {results_dir} --outputformat json --outputpath {retire_output}"
		logger.warning('[WEB_API] Retire.js: running | cmd: %s', cmd)
		run_command(cmd, shell=True, scan_id=self.scan_id, activity_id=self.activity_id)
		if os.path.exists(retire_output):
			try:
				retire_vulns = 0
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
							save_vulnerability(vuln_data, self.scan, self.domain)
							retire_vulns += 1
				logger.warning('[WEB_API] Retire.js: %d vulnerabilities saved', retire_vulns)
			except Exception as e:
				logger.error('[WEB_API] Retire.js: error parsing output: %s', e)
		else:
			logger.warning('[WEB_API] Retire.js: output file not found — may have failed silently')
	else:
		logger.warning('[WEB_API] Retire.js: skipped (not in uses_tools)')

	# Favirecon
	if 'favirecon' in uses_tools and urls:
		from reNgine.tasks.parsers import parse_favirecon_result
		favirecon_out = f"{results_dir}/favirecon_out.json"
		targets_file = f"{results_dir}/targets.txt"
		with open(targets_file, 'w') as _f:
			_f.write('\n'.join(urls))
		cmd = f"favirecon -j -l {targets_file} -o {favirecon_out}"
		logger.warning('[WEB_API] Favirecon: running on %d URLs | cmd: %s', len(urls), cmd)
		run_command(cmd, shell=True, cwd=results_dir, scan_id=self.scan_id, activity_id=self.activity_id)
		if os.path.exists(favirecon_out):
			try:
				with open(favirecon_out, 'r') as f:
					for line in f:
						if not line.strip(): continue
						try:
							finding = json.loads(line)
							if 'hash' in finding:
								vuln_data = parse_favirecon_result(finding)
								vuln_data['http_url'] = finding.get('url', '')
								save_vulnerability(vuln_data, self.scan, self.domain)
						except json.JSONDecodeError:
							pass
			except Exception as e:
				logger.error("Favirecon parse error: %s", e)
		logger.warning('[WEB_API] Favirecon: finished')

	# Sourcemapper
	if 'sourcemapper' in uses_tools and urls:
		from reNgine.tasks.parsers import parse_sourcemapper_result
		logger.warning('[WEB_API] Sourcemapper: evaluating %d candidate URLs', len(urls))
		sourcemap_base_dir = f"{results_dir}/sourcemapper_out"
		os.makedirs(sourcemap_base_dir, exist_ok=True)

		valid_sourcemap_targets = set()
		for url in urls:
			parsed = urlparse(url)
			path_lower = parsed.path.lower()
			if path_lower.endswith('.map'):
				valid_sourcemap_targets.add(url)
			elif path_lower.endswith('.js') or '.js' in path_lower:
				base_path = url.split('?')[0]
				map_candidate = f"{base_path}.map"
				if map_candidate not in valid_sourcemap_targets:
					try:
						res = requests.get(map_candidate, timeout=3, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
						if res.status_code == 200:
							peek = res.raw.read(512, decode_content=True).decode('utf-8', errors='ignore').strip()
							if peek.startswith('{') and ('"version"' in peek or '"sources"' in peek or '"mappings"' in peek):
								valid_sourcemap_targets.add(map_candidate)
					except (requests.RequestException, urllib3.exceptions.HTTPError):
						pass  # no reachable sourcemap next to this script

		logger.warning('[WEB_API] Sourcemapper: identified %d valid sourcemap target(s)', len(valid_sourcemap_targets))
		for sm_url in valid_sourcemap_targets:
			url_hash = hashlib.md5(sm_url.encode('utf-8'), usedforsecurity=False).hexdigest()[:10]
			url_out_dir = f"{sourcemap_base_dir}/{url_hash}"
			os.makedirs(url_out_dir, exist_ok=True)
			cmd = f"sourcemapper -output {shlex.quote(url_out_dir)} -url {shlex.quote(sm_url)}"
			run_command(cmd, shell=True, cwd=results_dir, scan_id=self.scan_id, activity_id=self.activity_id)
			if os.path.exists(url_out_dir) and os.listdir(url_out_dir):
				vuln_data = parse_sourcemapper_result(sm_url, url_out_dir)
				save_vulnerability(vuln_data, self.scan, self.domain)
		logger.warning('[WEB_API] Sourcemapper: finished')

	# GQLSpection — dumps a GraphQL schema through introspection. A successful
	# dump is the finding; the tool has no "is introspection on?" mode.
	if 'gqlspection' in uses_tools and urls:
		from reNgine.tasks.parsers import parse_gqlspection_result
		targets = [url for url in urls if is_graphql_endpoint_url(url)]
		logger.warning(
			'[WEB_API] GQLSpection: %d of %d URLs address a GraphQL endpoint',
			len(targets), len(urls),
		)
		seen_hosts = set()
		for url in targets:
			hostname = urlparse(url).hostname
			if not hostname or hostname in seen_hosts:
				continue
			seen_hosts.add(hostname)
			cmd = f"gqlspection -u {shlex.quote(url)} -l all"
			return_code, output = run_command(cmd, shell=True, cwd=results_dir, scan_id=self.scan_id, activity_id=self.activity_id)
			if gqlspection_schema_dumped(return_code, output):
				vuln_data = parse_gqlspection_result(url, output)
				save_vulnerability(vuln_data, self.scan, self.domain)
		logger.warning('[WEB_API] GQLSpection: finished')

	# grpcurl
	if 'grpcurl' in uses_tools and urls:
		from reNgine.tasks.parsers import parse_grpcurl_result
		logger.warning('[WEB_API] grpcurl: evaluating %d URLs', len(urls))

		host_urls = {}
		for url in urls:
			parsed = urlparse(url)
			if not parsed.hostname:
				continue
			if parsed.hostname not in host_urls:
				host_urls[parsed.hostname] = (
					url,
					parsed.port or (443 if parsed.scheme == 'https' else 80),
					parsed.scheme == 'https',
				)

		# Ports the port scan actually found open, per host. Probing the web port
		# the URL happens to carry is a guess; probing it with -plaintext when it
		# is 443 is a guess that cannot come true whatever is listening there.
		open_ports = {}
		for name, number, service in Subdomain.objects.filter(
			scan_history=self.scan, name__in=list(host_urls),
		).values_list(
			'name', 'ip_addresses__ports__number', 'ip_addresses__ports__service_name',
		).distinct():
			if number:
				open_ports.setdefault(name, []).append((number, service))

		for hostname, (representative_url, url_port, url_is_https) in host_urls.items():
			targets = grpc_probe_targets(
				open_ports.get(hostname, []), url_port, url_is_https
			)
			if not targets:
				logger.warning(
					'[WEB_API] grpcurl: no plausible gRPC port for %s — skipping', hostname
				)
				continue

			for port, use_tls in targets:
				transport = '-insecure' if use_tls else '-plaintext'
				# -connect-timeout bounds the handshake only. A host that accepts
				# the connection and then never answers the reflection request
				# leaves grpcurl waiting forever — two such hosts spent four hours
				# of a scan's Tier 3 budget, three times over. -max-time bounds the
				# whole call, and run_command's own timeout backs it up in case the
				# process ignores it.
				cmd = (
					f"grpcurl -connect-timeout {_GRPC_CONNECT_TIMEOUT} "
					f"-max-time {_GRPC_MAX_TIME} {transport} {shlex.quote(f'{hostname}:{port}')} list"
				)
				return_code, output = run_command(
					cmd, shell=True, cwd=results_dir,
					scan_id=self.scan_id, activity_id=self.activity_id,
					timeout=_GRPC_COMMAND_TIMEOUT,
				)

				if return_code == 0 and output.strip() and "Failed to dial" not in output:
					vuln_data = parse_grpcurl_result(representative_url, output)
					save_vulnerability(vuln_data, self.scan, self.domain)
					break

				if 'no such host' in output.lower():
					logger.warning(
						'[WEB_API] grpcurl: %s does not resolve — skipping its remaining ports',
						hostname,
					)
					break

		logger.warning('[WEB_API] grpcurl: finished')

	# Julius (LLM scanner)
	# julius probe -f <file> -o jsonl is broken upstream — combining -f with the
	# global -o flag causes julius to ignore the file and show its help menu.
	# Workaround: feed targets via stdin using `julius probe -`.
	if 'julius' in uses_tools and urls:
		from reNgine.tasks.parsers import parse_julius_result
		logger.warning('[WEB_API] Julius: running on %d URLs', len(urls))
		targets_file = f"{results_dir}/targets.txt"
		julius_out = f"{results_dir}/julius.jsonl"
		with open(targets_file, 'w') as _f:
			_f.write('\n'.join(urls))
		_julius_cmd = f"cat {targets_file} | julius probe - -o jsonl --no-banner | tee {julius_out}"
		_, _julius_output = run_command(_julius_cmd, shell=True, cwd=results_dir, scan_id=self.scan_id, activity_id=self.activity_id)
		_tls_error_sigs = ('x509: certificate', 'tls: failed to verify certificate', 'certificate verify failed')
		if any(sig in _julius_output for sig in _tls_error_sigs):
			logger.warning('[WEB_API] Julius: TLS certificate error detected, retrying with --insecure')
			if os.path.exists(julius_out):
				os.remove(julius_out)
			_julius_cmd = f"cat {targets_file} | julius probe - --insecure -o jsonl --no-banner | tee {julius_out}"
			run_command(_julius_cmd, shell=True, cwd=results_dir, scan_id=self.scan_id, activity_id=self.activity_id)
		if os.path.exists(julius_out):
			try:
				with open(julius_out, 'r') as f:
					for line in f:
						if not line.strip(): continue
						try:
							finding = json.loads(line)
							vuln_data = parse_julius_result(finding)
							save_vulnerability(vuln_data, self.scan, self.domain)
						except json.JSONDecodeError:
							pass
			except Exception as e:
				logger.error("Julius parse error: %s", e)
		logger.warning('[WEB_API] Julius: finished')

	# Aquatone - visual inspection of discovered URLs
	if 'aquatone' in uses_tools and urls:
		aquatone_out = f"{results_dir}/aquatone"
		os.makedirs(aquatone_out, exist_ok=True)
		targets_file = f"{aquatone_out}/targets.txt"
		with open(targets_file, 'w') as _f:
			_f.write('\n'.join(urls))
		cmd = f"cat {targets_file} | aquatone -out {aquatone_out} -threads {threads} -silent"
		logger.warning('[WEB_API] Aquatone: running on %d URLs | cmd: %s', len(urls), cmd)
		run_command(cmd, shell=True, cwd=aquatone_out, scan_id=self.scan_id, activity_id=self.activity_id)
		logger.warning('[WEB_API] Aquatone: finished')
	elif 'aquatone' in uses_tools:
		logger.warning('[WEB_API] Aquatone: skipped (no URLs)')

	# Sync to Graph
	if Neo4jManager:
		logger.warning('[WEB_API] Syncing results to Neo4j graph...')
		nm = Neo4jManager()
		nm.sync_scan_results(self.scan_id)
		nm.close()
		logger.warning('[WEB_API] Neo4j sync complete')

	# Trigger Intelligent Auth Candidate Extraction
	logger.warning('[WEB_API] Running auth candidate extraction...')
	from reNgine.tasks.auth_discovery import extract_auth_candidates
	extract_auth_candidates(self, ctx=ctx)
	logger.warning('[WEB_API] Web API Discovery complete | scan_id=%s', scan_id)
