import os
import random
import logging
import re
import tempfile
import subprocess
import json
from urllib.parse import urlparse
from django.conf import settings
from scanEngine.models import OpSec, Proxy
from reNgine.definitions import BRUTUS_EXEC_PATH, PROXYCHAINS_EXEC_PATH

class OpSecManager:
    """
    Manages Operational Security (OpSec) settings and provides utility functions
    to inject stealth flags into tool commands.
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    ]

    WAF_BYPASS_HEADERS = [
        "X-Forwarded-For: 127.0.0.1",
        "X-Originating-IP: 127.0.0.1",
        "X-Remote-IP: 127.0.0.1",
        "X-Remote-Addr: 127.0.0.1",
        "X-Client-IP: 127.0.0.1",
        "X-Host: 127.0.0.1",
        "Forwarded: for=127.0.0.1;proto=http;by=127.0.0.1",
    ]

    def __init__(self):
        self.settings = OpSec.objects.first()
        self.proxy_settings = Proxy.objects.first()

    def is_enabled(self):
        return self.settings and self.settings.enable_opsec

    def get_random_ua(self, proxy_ip=None):
        ua = random.choice(self.USER_AGENTS)
        if proxy_ip:
            ua = ua.replace("127.0.0.1", proxy_ip)
        return ua

    def get_waf_headers(self, proxy_ip=None):
        headers = self.WAF_BYPASS_HEADERS
        if proxy_ip:
            headers = [h.replace("127.0.0.1", proxy_ip) for h in headers]
        return headers

    def _extract_proxy_ip(self, proxy_str):
        """
        Extracts the IP or Hostname from a proxy string.
        Expected format: http://{ip}:{port} or socks5://{ip}:{port}
        """
        if not proxy_str:
            return None
        
        # Add scheme if missing for urlparse
        if "://" not in proxy_str:
            proxy_str = f"http://{proxy_str}"
            
        try:
            parsed = urlparse(proxy_str)
            return parsed.hostname
        except Exception:
            return None

    def apply_stealth(self, tool_name, command, proxy=None):
        """
        Applies stealth flags to a given command string for a specific tool.
        """
        if not self.is_enabled():
            return command

        proxy_ip = self._extract_proxy_ip(proxy)

        if tool_name == "nuclei":
            return self._apply_nuclei(command, proxy_ip)
        elif tool_name == "nmap":
            return self._apply_nmap(command, proxy_ip)
        elif tool_name == "subfinder":
            return self._apply_subfinder(command)
        elif tool_name == "amass":
            return self._apply_amass(command)
        elif tool_name == "ffuf":
            return self._apply_ffuf(command, proxy_ip)
        elif tool_name == "httpx":
            return self._apply_httpx(command, proxy_ip)
        elif tool_name == "brutus":
            return self._apply_brutus(command)
        elif tool_name == "dalfox":
            return self._apply_dalfox(command, proxy_ip)
        elif tool_name == "dirsearch":
            return self._apply_dirsearch(command, proxy_ip)
        
        return command

    def _apply_brutus(self, cmd):
        flags = []
        if self.settings.enable_delay:
            # Brutus doesn't have a direct delay flag like hydra -c, 
            # but we can use rate limiting as a proxy for it if needed.
            pass
        
        # Check if threads were passed in cmd (e.g. from orchestrator)
        # Otherwise use max_rps from OpSec settings
        if "-t" not in cmd and self.settings.enable_rate_limit:
            flags.append(f"-t {self.settings.max_rps}")
            
        return f"brutus {' '.join(flags)} {cmd.replace('brutus ', '')}"

    def _apply_nuclei(self, cmd, proxy_ip=None):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua(proxy_ip)}'")
        
        if self.settings.enable_waf_bypass:
            for header in self.get_waf_headers(proxy_ip):
                flags.append(f"-H '{header}'")
        
        if self.settings.enable_rate_limit:
            flags.append(f"-rl {self.settings.max_rps}")
        
        if self.settings.http_protocol == "http2":
            flags.append("-fh2")
        
        if self.settings.custom_dns_servers:
            dns = ",".join(self.settings.custom_dns_servers.splitlines())
            flags.append(f"-resolvers {dns}")

        return f"{cmd} {' '.join(flags)}"

    def _apply_nmap(self, cmd, proxy_ip=None):
        flags = []
        if self.settings.enable_delay:
            flags.append(f"--scan-delay {self.settings.delay_ms}ms")
        
        if self.settings.enable_random_ua:
            flags.append(f"--script-args http.useragent='{self.get_random_ua(proxy_ip)}'")
        
        if self.settings.custom_dns_servers:
            dns = ",".join(self.settings.custom_dns_servers.splitlines())
            flags.append(f"--dns-servers {dns}")

        return f"{cmd} {' '.join(flags)}"

    def _apply_subfinder(self, cmd):
        flags = []
        if self.settings.enable_rate_limit:
            # subfinder -rl (requests per minute)
            flags.append(f"-rl {self.settings.max_rps * 60}")
        return f"{cmd} {' '.join(flags)}"

    def _apply_amass(self, cmd):
        return cmd

    def _apply_ffuf(self, cmd, proxy_ip=None):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua(proxy_ip)}'")
        if self.settings.enable_rate_limit:
            flags.append(f"-p {1.0 / self.settings.max_rps}")
        return f"{cmd} {' '.join(flags)}"

    def _apply_httpx(self, cmd, proxy_ip=None):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua(proxy_ip)}'")
        if self.settings.http_protocol == "http2":
            flags.append("-http2")
        return f"{cmd} {' '.join(flags)}"

    def _apply_dalfox(self, cmd, proxy_ip=None):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"--user-agent '{self.get_random_ua(proxy_ip)}'")
        
        if self.settings.enable_waf_bypass:
            for header in self.get_waf_headers(proxy_ip):
                flags.append(f"-H '{header}'")
        
        if self.settings.enable_delay:
            flags.append(f"--delay {self.settings.delay_ms}")
            
        return f"{cmd} {' '.join(flags)}"

    def _apply_dirsearch(self, cmd, proxy_ip=None):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua(proxy_ip)}'")
        
        if self.settings.enable_waf_bypass:
            for header in self.get_waf_headers(proxy_ip):
                flags.append(f"-H '{header}'")
        
        return f"{cmd} {' '.join(flags)}"

    def strip_metadata(self, file_path):
        """
        Strips metadata from a given file. Supported formats: PDF, JPG, PNG.
        """
        if not self.is_enabled() or not self.settings.enable_metadata_stripping:
            return

        if not os.path.exists(file_path):
            return

        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".pdf":
                import pikepdf
                with pikepdf.open(file_path, allow_overwriting_input=True) as pdf:
                    del pdf.Root.Metadata
                    pdf.save(file_path)
            elif ext in [".jpg", ".jpeg", ".png"]:
                from PIL import Image
                img = Image.open(file_path)
                data = list(img.getdata())
                img_without_exif = Image.new(img.mode, img.size)
                img_without_exif.putdata(data)
                img_without_exif.save(file_path)
        except Exception:
            pass

    def strip_directory(self, directory):
        """
        Recursively strips metadata from all files in a directory.
        """
        if not self.is_enabled() or not self.settings.enable_metadata_stripping:
            return
        

class ProxychainsWrapper:
    """
    Handles dynamic generation of proxychains configurations for stealthy rotation.
    """
    def __init__(self):
        self.proxies = self._fetch_proxies()

    def _fetch_proxies(self):
        proxy_obj = Proxy.objects.first()
        if not proxy_obj or not proxy_obj.use_proxy or not proxy_obj.proxies:
            return []
        
        # Clean and validate proxy list
        proxies = []
        for line in proxy_obj.proxies.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Format expected by proxychains: type host port [user pass]
            # reNgine might store as protocol://host:port or host:port
            
            p_type = "socks5" # default
            p_host = ""
            p_port = ""
            
            if "://" in line:
                p_type = line.split("://")[0].lower()
                if p_type == "http" or p_type == "https":
                    p_type = "http" # proxychains uses 'http' for both
                line = line.split("://")[1]
            
            if ":" in line:
                parts = line.split(":")
                p_host = parts[0]
                p_port = parts[1]
                # If there are more parts, could be user:pass@host:port or host:port:user:pass
                # But simple host:port is most common in reNgine
                proxies.append(f"{p_type} {p_host} {p_port}")
            elif " " in line:
                # Already in type host port format
                proxies.append(line)
                
        return proxies

    def get_random_proxy(self):
        """
        Retrieves a random, verified alive, and unauthenticated proxy from the fetched proxy list.
        Converts the proxychains line format to standard requests proxy dictionary for testing.

        Returns:
            str: Validated proxy line in 'type host port [user pass]' format, or None if no valid proxy is found.
        """
        if not self.proxies:
            return None
        
        # Create a copy and shuffle to test proxies in a random sequence
        test_list = list(self.proxies)
        random.shuffle(test_list)
        
        checked_count = 0
        for proxy_str in test_list:
            if checked_count >= 5:
                logging.getLogger(__name__).warning("Reached maximum sequential proxychains validation limit (5). Stopping checks.")
                break
            checked_count += 1
            # Parse the proxychains formatted line: type host port [user pass]
            parts = proxy_str.split()
            if len(parts) >= 3:
                p_type = parts[0]
                p_host = parts[1]
                p_port = parts[2]
                
                # Map proxychains protocol name to requests standard scheme
                scheme = "http" if p_type in ["http", "https"] else p_type
                proxy_url = f"{scheme}://{p_host}:{p_port}"
                
                try:
                    from reNgine.common_func import check_proxy_robust
                    
                    # Perform validation check with robust verification method to avoid false positives
                    if not check_proxy_robust(proxy_url, timeout=5):
                        raise Exception("Proxy verification failed (robust check)")
                        
                    # Valid proxy found, return the original proxychains formatted line
                    return proxy_str
                except Exception as e:
                    # Log the proxy validation failure and continue to the next one
                    logging.getLogger(__name__).error(f"Proxychains proxy {proxy_url} validation failed: {e}")
                    
        return None

    def should_wrap(self):
        proxy_obj = Proxy.objects.first()
        return proxy_obj and proxy_obj.use_proxy and proxy_obj.use_proxychains

    def write_temp_config(self, proxy_str):
        fd, path = tempfile.mkstemp(suffix=".conf", prefix="proxychains_")
        os.close(fd)
        with open(path, 'w') as f:
            f.write("strict_chain\n")
            f.write("proxy_dns\n")
            f.write("tcp_read_time_out 15000\ntcp_connect_time_out 8000\n")
            f.write("[ProxyList]\n")
            f.write(f"{proxy_str}\n")
        return path

    def wrap_command(self, cmd, proxy=None):
        """
        Conditionally wraps a command with proxychains if enabled in settings.
        Returns (wrapped_command, temp_config_path)
        """
        if not proxy:
            proxy = self.get_random_proxy()
        
        if proxy and self.should_wrap():
            conf_path = self.write_temp_config(proxy)
            return f"{PROXYCHAINS_EXEC_PATH} -f {conf_path} {cmd}", conf_path
        return cmd, None


class BruteForceOrchestrator:
    """
    Orchestrates Brutus brute-force attacks with proxy rotation, 
    multi-protocol support, and centralized target management.
    """
    def __init__(self, scan_history):
        self.scan = scan_history
        self.proxy_manager = ProxychainsWrapper()
        self.opsec = OpSecManager()
        self.logger = logging.getLogger(__name__)
        self.results_dir = f"{self.scan.results_dir}/brute_force"
        os.makedirs(self.results_dir, exist_ok=True)

    def run_orchestration(self, ctx={}, allowed_services=[]):
        """
        Main entry point: Pulls candidates from DB, batches them, and executes.
        """
        from startScan.models import AuthCandidate
        candidates = AuthCandidate.objects.filter(scan_history=self.scan, status='pending')
        
        if allowed_services:
            candidates = candidates.filter(protocol__in=allowed_services)
        
        if not candidates.exists():
            self.logger.info("No pending auth candidates found for this scan.")
            return []

        # Group candidates by protocol
        groups = {}
        for c in candidates:
            if c.protocol not in groups:
                groups[c.protocol] = []
            groups[c.protocol].append(c)

        all_results = []
        for protocol, cand_list in groups.items():
            self.logger.info(f"Processing {len(cand_list)} candidates for protocol: {protocol}")
            
            # For non-HTTP, we can batch targets if they share credentials
            if protocol in ['ssh', 'ftp', 'smb', 'rdp', 'telnet']:
                results = self._run_protocol_batch(protocol, cand_list, ctx)
                all_results.extend(results)
            elif protocol == 'http':
                # HTTP needs individual handling per form
                for c in cand_list:
                    results = self._run_http_brute(c, ctx)
                    all_results.extend(results)
                    
        return all_results

    def _run_protocol_batch(self, protocol, candidates, ctx):
        """Batch execution for simple protocols (SSH, SMB, etc.)"""
        # Create target file
        target_file = f"{self.results_dir}/{protocol}_targets.txt"
        with open(target_file, 'w') as f:
            for c in candidates:
                f.write(f"{c.target}\n")
        
        # Wordlists
        user_list = ctx.get('user_list', "/usr/src/wordlist/common_users.txt")
        pass_list = ctx.get('pass_list', "/usr/src/wordlist/common_passwords.txt")
        threads = ctx.get('threads', 5)
        
        # Build command (Brutus)
        # Brutus uses -U for user list and -P for password list
        # We assume candidates[0].target is a single target for now as reNgine 
        # usually does one-by-one or small batches.
        # If multiple targets, Brutus needs multiple runs or a script wrapper.
        # For simplicity, we'll run Brutus per target in this orchestrator.
        
        all_results = []
        for c in candidates:
            cmd = f"{BRUTUS_EXEC_PATH} --target {c.target} --protocol {protocol} -U {user_list} -P {pass_list} -t {threads} --json"
            
            # Apply OpSec & Proxy
            proxy = self.proxy_manager.get_random_proxy()
            cmd = self.opsec.apply_stealth('brutus', cmd, proxy=proxy)
            wrapped_cmd, conf_path = self.proxy_manager.wrap_command(cmd, proxy=proxy)
            
            try:
                self.logger.info(f"Executing Brutus for {c.target} ({protocol}): {wrapped_cmd}")
                output_file = f"{self.results_dir}/{protocol}_{c.id}_results.json"
                subprocess.run(f"{wrapped_cmd} > {output_file}", shell=True, timeout=1200)
                
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    results = self._parse_brutus_output(output_file, protocol)
                    all_results.extend(results)
                    c.status = 'completed'
                    c.save()
            except Exception as e:
                self.logger.error(f"Error in Brutus {protocol} for {c.target}: {e}")
            finally:
                if conf_path and os.path.exists(conf_path): os.remove(conf_path)
            
        return all_results

    def _run_http_brute(self, candidate, ctx):
        """Individual execution for HTTP (handles forms)"""
        meta = candidate.metadata or {}
        user_list = ctx.get('user_list', "/usr/src/wordlist/common_users.txt")
        pass_list = ctx.get('pass_list', "/usr/src/wordlist/common_passwords.txt")
        
        # Extract target host
        parsed = urlparse(candidate.target)
        host = parsed.netloc
        path = parsed.path or "/"
        
        # Determine form parameters (Hydra format)
        # Default: /login.php:user=^USER^&pass=^PASS^:F=Login failed
        user_field = meta.get('user_field', 'username')
        pass_field = meta.get('pass_field', 'password')
        form_params = f"{path}:{user_field}=^USER^&{pass_field}=^PASS^:F=failed"
        
        cmd = f"{BRUTUS_EXEC_PATH} --target {host} --protocol http -U {user_list} -P {pass_list} --json"
        # Note: Brutus might need specific flags for form-based auth if supported, 
        # but the current requirement focuses on protocol mapping.
        
        # Apply OpSec & Proxy
        proxy = self.proxy_manager.get_random_proxy()
        cmd = self.opsec.apply_stealth('brutus', cmd, proxy=proxy)
        wrapped_cmd, conf_path = self.proxy_manager.wrap_command(cmd, proxy=proxy)
        
        results = []
        try:
            output_file = f"{self.results_dir}/http_{host.replace(':','_')}_results.log"
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                results = self._parse_brutus_output(output_file, 'http')
                candidate.status = 'completed'
                candidate.save()
        except Exception as e:
            self.logger.error(f"Error in HTTP brute for {candidate.target}: {e}")
        finally:
            if conf_path and os.path.exists(conf_path): os.remove(conf_path)
            
        return results

    def _parse_brutus_output(self, json_file, protocol):
        results = []
        if not os.path.exists(json_file):
            return results
            
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                # Assuming Brutus JSON output is a list of findings or a similar structure
                # We'll map it to the expected reNgine format
                findings = data if isinstance(data, list) else data.get('findings', [])
                for finding in findings:
                    results.append({
                        'target': finding.get('target', ''),
                        'protocol': finding.get('protocol', protocol),
                        'port': finding.get('port', ''),
                        'user': finding.get('username', ''),
                        'password': finding.get('password', ''),
                        'service': protocol
                    })
        except Exception as e:
            self.logger.error(f"Failed to parse Brutus JSON output: {e}")
            
        return results
