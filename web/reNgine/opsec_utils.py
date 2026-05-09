import os
import random
import logging
import re
import tempfile
import subprocess
from scanEngine.models import OpSec, Proxy
from reNgine.definitions import MEDUSA_EXEC_PATH, HYDRA_EXEC_PATH, PROXYCHAINS_EXEC_PATH

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

    def get_random_ua(self):
        return random.choice(self.USER_AGENTS)

    def get_waf_headers(self):
        return self.WAF_BYPASS_HEADERS

    def apply_stealth(self, tool_name, command):
        """
        Applies stealth flags to a given command string for a specific tool.
        """
        if not self.is_enabled():
            return command

        if tool_name == "nuclei":
            return self._apply_nuclei(command)
        elif tool_name == "nmap":
            return self._apply_nmap(command)
        elif tool_name == "subfinder":
            return self._apply_subfinder(command)
        elif tool_name == "amass":
            return self._apply_amass(command)
        elif tool_name == "ffuf":
            return self._apply_ffuf(command)
        elif tool_name == "httpx":
            return self._apply_httpx(command)
        elif tool_name == "hydra":
            return self._apply_hydra(command)
        
        return command

    def _apply_hydra(self, cmd):
        flags = []
        if self.settings.enable_delay:
            # hydra -c (delay in seconds)
            flags.insert(0, f"-c {self.settings.delay_ms / 1000.0}")
        
        if self.settings.enable_rate_limit:
            # hydra -t (tasks)
            flags.insert(0, f"-t {self.settings.max_rps}")
            
        return f"hydra {' '.join(flags)} {cmd.replace('hydra ', '')}"

    def _apply_nuclei(self, cmd):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua()}'")
        
        if self.settings.enable_waf_bypass:
            for header in self.get_waf_headers():
                flags.append(f"-H '{header}'")
        
        if self.settings.enable_rate_limit:
            flags.append(f"-rl {self.settings.max_rps}")
        
        if self.settings.http_protocol == "http2":
            flags.append("-h2")
        
        if self.settings.custom_dns_servers:
            dns = ",".join(self.settings.custom_dns_servers.splitlines())
            flags.append(f"-resolvers {dns}")

        return f"{cmd} {' '.join(flags)}"

    def _apply_nmap(self, cmd):
        flags = []
        if self.settings.enable_delay:
            flags.append(f"--scan-delay {self.settings.delay_ms}ms")
        
        if self.settings.enable_random_ua:
            flags.append(f"--script-args http.useragent='{self.get_random_ua()}'")
        
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

    def _apply_ffuf(self, cmd):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua()}'")
        if self.settings.enable_rate_limit:
            flags.append(f"-p {1.0 / self.settings.max_rps}")
        return f"{cmd} {' '.join(flags)}"

    def _apply_httpx(self, cmd):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua()}'")
        if self.settings.http_protocol == "http2":
            flags.append("-http2")
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
        return random.choice(self.proxies) if self.proxies else None

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
    Orchestrates Hydra/Medusa brute-force attacks with proxy rotation, 
    multi-protocol support, and centralized target management.
    """
    def __init__(self, scan_history):
        self.scan = scan_history
        self.proxy_manager = ProxychainsWrapper()
        self.opsec = OpSecManager()
        self.logger = logging.getLogger(__name__)
        self.results_dir = f"{settings.SCAN_HISTORY_PATH}/{self.scan.id}/brute_force"
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
        
        # Build command (Hydra)
        # Hydra uses -M for targets file
        cmd = f"{HYDRA_EXEC_PATH} -L {user_list} -P {pass_list} -M {target_file} {protocol}"
        
        # Apply OpSec & Proxy
        cmd = self.opsec.apply_stealth('hydra', cmd)
        wrapped_cmd, conf_path = self.proxy_manager.wrap_command(cmd)
        
        results = []
        try:
            self.logger.info(f"Executing batch: {wrapped_cmd}")
            output_file = f"{self.results_dir}/{protocol}_results.log"
            proc = subprocess.run(f"{wrapped_cmd} -o {output_file}", shell=True, timeout=1200)
            
            if os.path.exists(output_file):
                results = self._parse_hydra_output(output_file, protocol)
                # Update candidate status
                for c in candidates:
                    c.status = 'completed'
                    c.save()
        except Exception as e:
            self.logger.error(f"Error in {protocol} batch: {e}")
        finally:
            if conf_path and os.path.exists(conf_path): os.remove(conf_path)
            
        return results

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
        
        cmd = f"{HYDRA_EXEC_PATH} -L {user_list} -P {pass_list} {host} http-post-form \"{form_params}\""
        
        # Apply OpSec & Proxy
        cmd = self.opsec.apply_stealth('hydra', cmd)
        wrapped_cmd, conf_path = self.proxy_manager.wrap_command(cmd)
        
        results = []
        try:
            output_file = f"{self.results_dir}/http_{host.replace(':','_')}_results.log"
            subprocess.run(f"{wrapped_cmd} -o {output_file}", shell=True, timeout=600)
            if os.path.exists(output_file):
                results = self._parse_hydra_output(output_file, 'http')
                candidate.status = 'completed'
                candidate.save()
        except Exception as e:
            self.logger.error(f"Error in HTTP brute for {candidate.target}: {e}")
        finally:
            if conf_path and os.path.exists(conf_path): os.remove(conf_path)
            
        return results

    def _parse_hydra_output(self, log_file, protocol):
        results = []
        if not os.path.exists(log_file):
            return results
            
        with open(log_file, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip(): continue
                # Hydra output format: host protocol port user pass
                parts = line.split()
                if len(parts) >= 5:
                    results.append({
                        'target': parts[0],
                        'protocol': parts[1],
                        'port': parts[2],
                        'user': parts[3],
                        'password': parts[4],
                        'service': protocol
                    })
        return results
