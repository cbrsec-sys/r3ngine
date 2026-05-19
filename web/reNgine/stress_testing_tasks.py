from celery import shared_task
from django.conf import settings
import subprocess
import json
import os
import signal
import redis
import logging
import time
from startScan.models import ScanHistory, EndPoint, StressTestResult, Command
from targetApp.models import Domain
from reNgine.graph_utils import Neo4jManager
from django.utils import timezone
from reNgine.celery_custom_task import RengineTask
from reNgine.parsers import K6Parser, WrkParser, Hping3Parser, LocustParser, TAStressorParser
from reNgine.stress_telemetry import StressTelemetryPublisher
from reNgine.definitions import SUCCESS_TASK, FAILED_TASK, RUNNING_TASK, ABORTED_TASK

logger = logging.getLogger(__name__)

# Redis for kill switch
try:
    redis_client = redis.StrictRedis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0
    )
except:
    redis_client = None


class StressTestTask(RengineTask):
    """Dedicated task class for stress testing with specialized cleanup and telemetry."""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        super().on_failure(exc, task_id, args, kwargs, einfo)
        # Ensure any orphan sub-processes are killed
        scan_id = getattr(self, 'scan_id', None)
        if not scan_id and args:
            scan_id = args[0]
        
        if scan_id:
            self.terminate_processes(scan_id)

    def terminate_processes(self, scan_id):
        """Logic to kill all processes related to this scan."""
        if redis_client:
            redis_client.set(f"kill_switch_{scan_id}", "1", ex=3600)
        logger.warning(f"Termination requested for stress test on scan {scan_id}")


def is_kill_switch_active(scan_id):
    """Check if the kill switch for this scan has been flipped in Redis."""
    if redis_client:
        return redis_client.get(f"kill_switch_{scan_id}") == b"1"
    return False


@shared_task(name='stress_testing', queue='main_scan_queue', bind=True, base=StressTestTask)
def run_stress_testing(self, scan_history_id, target_domain_name, yaml_config, **kwargs):
    # Extract config
    stress_config = yaml_config.get("stress_test", {})
    if not stress_config:
        return {"status": "success", "message": "No stress test config provided"}

    concurrency = stress_config.get("concurrency", 50)
    duration = stress_config.get("duration", "30s")
    tools = stress_config.get("uses_tools", ["k6"])
    
    # Initialize Telemetry
    publisher = StressTelemetryPublisher(scan_history_id)
    
    # Publish initial running status
    publisher.publish({
        "type": "scan_status",
        "status": "running",
        "timestamp": time.time()
    })

    try:
        # Target Profiling
        try:
            scan = ScanHistory.objects.get(id=scan_history_id)
            domain = Domain.objects.get(name=target_domain_name)
            scan.scan_status = RUNNING_TASK
            scan.save()
        except Exception as e:
            logger.error(f"Stress test error: {e}")
            return {"status": "failed"}

        selected_endpoints = stress_config.get('selected_endpoints', [])
        
        if selected_endpoints:
            # Filter specifically on selected endpoints matching the list of URLs
            endpoints = EndPoint.objects.filter(
                scan_history_id=scan_history_id,
                http_url__in=selected_endpoints
            )
        else:
            crawl_targets = yaml_config.get('crawl_targets', False)
            if not crawl_targets:
                # Only take the root target.
                endpoints = EndPoint.objects.filter(
                    scan_history_id=scan_history_id, 
                    subdomain__name=target_domain_name
                ).order_by('id')[:1]
            else:
                # Take up to 5 endpoints on the target domain
                endpoints = EndPoint.objects.filter(
                    scan_history_id=scan_history_id, 
                    subdomain__name=target_domain_name
                )[:5]
        if not endpoints:
            logger.warning(f"No endpoints found for scan {scan_history_id} to stress test.")
            try:
                scan.scan_status = SUCCESS_TASK
                scan.stop_scan_date = timezone.now()
                scan.save()
            except Exception as e:
                logger.error(f"Failed to update scan status: {e}")
            return {"status": "success", "message": "No endpoints to stress test"}

        neo4j = Neo4jManager()

        overall_result = StressTestResult.objects.create(
            scan_history=scan,
            target_domain=domain,
            tool_used=",".join(tools),
            concurrency_used=concurrency,
            duration=duration,
        )

        from reNgine.opsec_utils import ProxychainsWrapper
        from reNgine.common_func import get_random_proxy
        
        proxy_wrapper = ProxychainsWrapper()
        single_proxy = get_random_proxy()

        for endpoint in endpoints:
            if is_kill_switch_active(scan_history_id):
                logger.warning(f"Kill switch activated for scan {scan_history_id}. Aborting.")
                overall_result.is_kill_switch_triggered = True
                overall_result.save()
                break

            for tool in tools:
                parser = None
                cmd = []
                temp_conf_path = None
                temp_proxy_path = None
                
                tool_config = stress_config.get(f"{tool}_config", {})
                
                # Dynamic sanitisation to avoid shell injection
                def sanitize(val, allowed_chars=None, default=""):
                    if val is None:
                        return default
                    val_str = str(val).strip()
                    if not allowed_chars:
                        allowed_chars = r"^[a-zA-Z0-9.\-_/:=%]+$"
                    import re
                    if not re.match(allowed_chars, val_str):
                        logger.warning(f"Sanitization blocked input: {val_str}")
                        return default
                    return val_str

                if tool == "k6":
                    parser = K6Parser()
                    k6_vus = sanitize(tool_config.get("vus"), default=str(concurrency))
                    k6_duration = sanitize(tool_config.get("duration"), default=str(duration))
                    k6_attack_type = sanitize(tool_config.get("attack_type", "http_get"), default="http_get")
                    k6_rps = sanitize(tool_config.get("rps"), default="")
                    k6_insecure = tool_config.get("insecure_skip_tls", False)
                    k6_no_reuse = tool_config.get("no_connection_reuse", False)
                    k6_http_debug = sanitize(tool_config.get("http_debug"), default="")

                    script_path = f"/tmp/k6_script_{scan_history_id}.js"
                    with open(script_path, "w") as f:
                        if k6_attack_type == "slowloris":
                            f.write(f"""
                            import http from 'k6/http';
                            import {{ sleep }} from 'k6';
                            export const options = {{
                                vus: {k6_vus},
                                duration: '{k6_duration}',
                            }};
                            export default function () {{
                                const params = {{
                                    headers: {{
                                        'User-Agent': 'k6-slowloris-agent',
                                        'X-Keep-Alive': 'true',
                                    }},
                                    timeout: '30s',
                                }};
                                try {{
                                    const res = http.get('{endpoint.http_url}', params);
                                    sleep(10);
                                }} catch (e) {{
                                    sleep(1);
                                }}
                            }}
                            """)
                        else:
                            f.write(f"""
                            import http from 'k6/http';
                            import {{ sleep }} from 'k6';
                            export default function () {{
                                http.get('{endpoint.http_url}');
                                sleep(0.5);
                            }}
                            """)
                    
                    cmd = ["k6", "run", "--vus", k6_vus, "--duration", k6_duration]
                    if k6_rps:
                        cmd += ["--rps", k6_rps]
                    if k6_insecure:
                        cmd += ["--insecure-skip-tls-verify"]
                    if k6_no_reuse:
                        cmd += ["--no-connection-reuse"]
                    if k6_http_debug:
                        cmd += [f"--http-debug={k6_http_debug}"]
                    cmd += [script_path]
                
                elif tool == "wrk":
                    parser = WrkParser()
                    wrk_threads = sanitize(tool_config.get("threads"), default="2")
                    wrk_connections = sanitize(tool_config.get("connections"), default=str(concurrency))
                    wrk_duration = sanitize(tool_config.get("duration"), default=str(duration))
                    wrk_latency = tool_config.get("latency", True)
                    wrk_timeout = sanitize(tool_config.get("timeout"), default="")
                    wrk_headers = tool_config.get("headers", [])

                    cmd = ["wrk", "-t", wrk_threads, "-c", wrk_connections, "-d", wrk_duration]
                    if wrk_latency:
                        cmd += ["--latency"]
                    if wrk_timeout:
                        cmd += ["--timeout", wrk_timeout]
                    for header in wrk_headers:
                        san_hdr = sanitize(header, allowed_chars=r"^[a-zA-Z0-9.\-_/:=%\s]+$")
                        if san_hdr:
                            cmd += ["-H", san_hdr]
                    cmd += [endpoint.http_url]
                
                elif tool == "hping3":
                    parser = Hping3Parser()
                    hping_mode = sanitize(tool_config.get("attack_mode"), default="syn")
                    hping_port = sanitize(tool_config.get("port"), default="80")
                    hping_rate = sanitize(tool_config.get("rate"), default="fast")
                    hping_data = sanitize(tool_config.get("data_size"), default="")
                    
                    cmd = ["hping3"]
                    if hping_mode == "udp":
                        cmd += ["--udp"]
                    elif hping_mode == "icmp":
                        cmd += ["--icmp"]
                    else:
                        cmd += ["--syn"]

                    cmd += ["-p", hping_port]

                    if hping_rate == "flood":
                        cmd += ["--flood"]
                    elif hping_rate == "faster":
                        cmd += ["--faster"]
                    else:
                        cmd += ["--fast"]

                    if hping_data:
                        cmd += ["-d", hping_data]
                    
                    cmd += ["-c", "100", target_domain_name]
                
                elif tool == "locust":
                    parser = LocustParser()
                    locust_users = sanitize(tool_config.get("users"), default=str(concurrency))
                    locust_spawn = sanitize(tool_config.get("spawn_rate"), default=str(max(1, int(concurrency) // 5)))
                    locust_runtime = sanitize(tool_config.get("run_time"), default=str(duration))
                    locust_loglevel = sanitize(tool_config.get("loglevel"), default="ERROR")

                    script_path = f"/tmp/locustfile_{scan_history_id}.py"
                    with open(script_path, "w") as f:
                        f.write(f"""
from locust import HttpUser, task, between
import logging

logging.getLogger('locust').setLevel(logging.{locust_loglevel})

class StressUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def test_target(self):
        self.client.get("/")
""")
                    cmd = [
                        "locust",
                        "--headless",
                        "-u", locust_users,
                        "-r", locust_spawn,
                        "--run-time", locust_runtime,
                        "--host", endpoint.http_url,
                        "--locustfile", script_path,
                        "--print-stats"
                    ]

                elif tool == "stressor":
                    parser = TAStresserParser()
                    stresser_method = sanitize(tool_config.get("method"), default="GET")
                    stresser_threads = sanitize(tool_config.get("threads"), default=str(concurrency))
                    stresser_duration = sanitize(tool_config.get("duration"), default=str(duration))
                    stresser_rpc = sanitize(tool_config.get("rpc"), default="1")
                    stresser_proxy_type = sanitize(tool_config.get("proxy_type"), default="0")
                    stresser_proxy_file = sanitize(tool_config.get("proxy_file"), default="")

                    # Fetch proxies from global reNgine settings and write formatted proxies to temp file
                    from scanEngine.models import Proxy
                    import tempfile
                    
                    temp_proxy_lines = []
                    if Proxy.objects.all().exists():
                        proxy_config = Proxy.objects.first()
                        if proxy_config.use_proxy and proxy_config.proxies:
                            for line in proxy_config.proxies.splitlines():
                                line = line.strip()
                                if not line:
                                    continue
                                # Strip scheme: http://, https://, socks4://, socks5://, etc.
                                for scheme in ['http://', 'https://', 'socks4://', 'socks5://', 'socks5h://', 'socks4a://']:
                                    if line.lower().startswith(scheme):
                                        line = line[len(scheme):]
                                        break
                                if line:
                                    temp_proxy_lines.append(line)
                    
                    if temp_proxy_lines:
                        try:
                            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', prefix='proxies_stressor_')
                            temp_file.write('\n'.join(temp_proxy_lines) + '\n')
                            temp_file.close()
                            temp_proxy_path = temp_file.name
                            stresser_proxy_file = temp_proxy_path
                            logger.info(f"Saved {len(temp_proxy_lines)} proxies to temp file: {temp_proxy_path}")
                        except Exception as temp_err:
                            logger.error(f"Failed to create temp proxy file: {temp_err}")

                    # TA_Stresser expects absolute script path. We can place it at /usr/src/app/TA_Stresser.py in Docker.
                    # Fix: script path to lowercase "stressor.py" to match file name and ensure Linux compatibility.
                    script_path = "./stressor/stressor.py"

                    # Construct command depending on whether it is Layer 4 or Layer 7
                    is_l7 = stresser_method in ["CFB", "BYPASS", "GET", "POST", "OVH", "STRESS", "SLOW", "HEAD", "COOKIE", "TOR"]
                    
                    if is_l7:
                        # Format: [method] [url] [proxy_type] [threads] [proxy_file] [rpc] [duration] [debug_flag]
                        cmd = [
                            "python3", script_path,
                            stresser_method,
                            endpoint.http_url,
                            stresser_proxy_type,
                            stresser_threads,
                            stresser_proxy_file if stresser_proxy_file else "none",
                            stresser_rpc,
                            stresser_duration,
                            "debug"  # 9th argument enables debug logger (printing PPS/BPS output)
                        ]
                    else:
                        # Format: [method] [target_host:port] [threads] [duration]
                        target_host_port = f"{target_domain_name}:{tool_config.get('port', '80')}"
                        if stresser_proxy_file:
                            cmd = [
                                "python3", script_path,
                                stresser_method,
                                target_host_port,
                                stresser_threads,
                                stresser_duration,
                                stresser_proxy_type,
                                stresser_proxy_file
                            ]
                        else:
                            cmd = [
                                "python3", script_path,
                                stresser_method,
                                target_host_port,
                                stresser_threads,
                                stresser_duration,
                            ]

                if not cmd:
                    continue

                cmd_str = ' '.join(cmd)

                if proxy_wrapper.should_wrap():
                    cmd_str, temp_conf_path = proxy_wrapper.wrap_command(cmd_str)
                    logger.info(f"Wrapping execution via proxychains: {cmd_str}")
                #elif single_proxy:
                #    cmd_str = f"export HTTP_PROXY='{single_proxy}' HTTPS_PROXY='{single_proxy}' && {cmd_str}"
                #    logger.info(f"Prepending single proxy environment: {cmd_str}")
                else:
                    logger.info(f"Executing {tool}: {cmd_str}")
                
                command_obj = Command.objects.create(
                    command=cmd_str,
                    time=timezone.now(),
                    scan_history_id=scan_history_id
                )

                publisher.publish({
                    "type": "command",
                    "tool": tool,
                    "endpoint": endpoint.http_url,
                    "command": cmd_str,
                    "timestamp": time.time()
                })

                accumulated_lines = []
                
                try:
                    process = subprocess.Popen(
                        cmd_str, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT, 
                        text=True,
                        shell=True,
                        start_new_session=True
                    )

                    while True:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                        
                        if line:
                            line = line.strip()
                            accumulated_lines.append(line)

                            publisher.publish({
                                "type": "log",
                                "tool": tool,
                                "endpoint": endpoint.http_url,
                                "line": line,
                                "timestamp": time.time()
                            })

                            metrics = parser.parse_line(line)
                            if metrics:
                                metrics["type"] = "metric"
                                metrics["tool"] = tool
                                metrics["endpoint"] = endpoint.http_url
                                metrics["timestamp"] = time.time()
                                publisher.publish(metrics)

                        if is_kill_switch_active(scan_history_id):
                            import signal
                            try:
                                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                            except Exception as kill_err:
                                logger.error(f"Failed to kill process group: {kill_err}")
                            break

                    process.wait()
                    
                    command_obj.output = "\n".join(accumulated_lines)
                    command_obj.return_code = process.returncode
                    command_obj.save()
                    
                except Exception as e:
                    logger.error(f"Execution of {tool} failed: {e}")
                finally:
                    if temp_conf_path and os.path.exists(temp_conf_path):
                        try:
                            os.remove(temp_conf_path)
                        except Exception as rm_err:
                            logger.error(f"Failed to remove temp config file: {rm_err}")
                    if temp_proxy_path and os.path.exists(temp_proxy_path):
                        try:
                            os.remove(temp_proxy_path)
                        except Exception as rm_err:
                            logger.error(f"Failed to remove temp proxy file: {rm_err}")

        neo4j.close()

        # Update ScanHistory status
        is_aborted = is_kill_switch_active(scan_history_id) or overall_result.is_kill_switch_triggered
        if is_aborted:
            scan.scan_status = ABORTED_TASK
            status_notif = 'ABORTED'
        else:
            scan.scan_status = SUCCESS_TASK
            status_notif = 'SUCCESS'
            
        scan.stop_scan_date = timezone.now()
        scan.save()

        # Final notification
        from reNgine.tasks import send_scan_notif
        send_scan_notif(
            scan_history_id=scan_history_id,
            status=status_notif
        )

        return {"status": "success"}

    except Exception as exc:
        logger.error(f"Stress test failed: {exc}")
        try:
            scan = ScanHistory.objects.get(id=scan_history_id)
            scan.scan_status = FAILED_TASK
            scan.stop_scan_date = timezone.now()
            scan.save()
            from reNgine.tasks import send_scan_notif
            send_scan_notif(
                scan_history_id=scan_history_id,
                status='FAILED'
            )
        except Exception as db_err:
            logger.error(f"Failed to update scan status: {db_err}")
        raise exc

    finally:
        # Publish final completed status to telemetry
        publisher.publish({
            "type": "scan_status",
            "status": "completed",
            "timestamp": time.time()
        })
