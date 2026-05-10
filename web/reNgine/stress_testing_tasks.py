from celery import shared_task
from django.conf import settings
import subprocess
import json
import os
import signal
import redis
import logging
import time
from startScan.models import ScanHistory, EndPoint, StressTestResult
from targetApp.models import Domain
from reNgine.graph_utils import Neo4jManager
from django.utils import timezone
from reNgine.celery_custom_task import RengineTask
from reNgine.parsers import K6Parser, WrkParser, Hping3Parser, LocustParser
from reNgine.stress_telemetry import StressTelemetryPublisher

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
def run_stress_testing(self, scan_history_id, target_domain_name, yaml_config):
    # Extract config
    stress_config = yaml_config.get("stress_test", {})
    if not stress_config:
        return {"status": "success", "message": "No stress test config provided"}

    concurrency = stress_config.get("concurrency", 50)
    duration = stress_config.get("duration", "30s")
    tools = stress_config.get("uses_tools", ["k6"])
    
    # Initialize Telemetry
    publisher = StressTelemetryPublisher(scan_history_id)

    # Target Profiling
    try:
        scan = ScanHistory.objects.get(id=scan_history_id)
        domain = Domain.objects.get(name=target_domain_name)
    except Exception as e:
        logger.error(f"Stress test error: {e}")
        return {"status": "failed"}

    endpoints = EndPoint.objects.filter(scan_history_id=scan_history_id)[:5]
    if not endpoints:
        logger.warning(f"No endpoints found for scan {scan_history_id} to stress test.")
        return {"status": "success", "message": "No endpoints to stress test"}

    neo4j = Neo4jManager()

    overall_result = StressTestResult.objects.create(
        scan_history=scan,
        target_domain=domain,
        tool_used=",".join(tools),
        concurrency_used=concurrency,
        duration=duration,
    )

    for endpoint in endpoints:
        if is_kill_switch_active(scan_history_id):
            logger.warning(f"Kill switch activated for scan {scan_history_id}. Aborting.")
            overall_result.is_kill_switch_triggered = True
            overall_result.save()
            break

        for tool in tools:
            parser = None
            cmd = []
            
            if tool == "k6":
                parser = K6Parser()
                script_path = f"/tmp/k6_script_{scan_history_id}.js"
                with open(script_path, "w") as f:
                    f.write(f"""
                    import http from 'k6/http';
                    import {{ sleep }} from 'k6';
                    export default function () {{
                        http.get('{endpoint.http_url}');
                        sleep(1);
                    }}
                    """)
                cmd = ["k6", "run", "--vus", str(concurrency), "--duration", str(duration), script_path]
            
            elif tool == "wrk":
                parser = WrkParser()
                cmd = ["wrk", "-t", "2", "-c", str(concurrency), "-d", duration, endpoint.http_url]
            
            elif tool == "hping3":
                parser = Hping3Parser()
                # hping3 needs careful handling of parameters
                cmd = ["hping3", "-S", "-p", "80", "-c", "10", target_domain_name]
            
            elif tool == "locust":
                parser = LocustParser()
                script_path = f"/tmp/locustfile_{scan_history_id}.py"
                with open(script_path, "w") as f:
                    f.write(f"""
from locust import HttpUser, task, between
import logging

# Disable locust logging to stdout to keep telemetry clean
logging.getLogger('locust').setLevel(logging.ERROR)

class StressUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task
    def test_target(self):
        self.client.get("/")
""")
                # Locust needs a host. If endpoint is a full URL, we use it as host and get("/")
                cmd = [
                    "locust",
                    "--headless",
                    "-u", str(concurrency),
                    "-r", str(max(1, int(concurrency) // 5)),
                    "--run-time", duration,
                    "--host", endpoint.http_url,
                    "--locustfile", script_path,
                    "--print-stats"
                ]

            if not cmd:
                continue

            logger.info(f"Executing {tool}: {' '.join(cmd)}")
            
            try:
                # Use start_new_session to ensure we can kill the whole process group
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True,
                    start_new_session=True
                )

                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    
                    if line:
                        line = line.strip()
                        # Parse metrics in real-time
                        metrics = parser.parse_line(line)
                        if metrics:
                            # Add context to metrics
                            metrics["tool"] = tool
                            metrics["endpoint"] = endpoint.http_url
                            metrics["timestamp"] = time.time()
                            
                            # Publish to Redis Stream
                            publisher.publish(metrics)

                    # Check kill switch during execution
                    if is_kill_switch_active(scan_history_id):
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        break

                process.wait()
                
                # Final aggregation for this tool/endpoint can be done here
                # For now, we rely on the summary stored at the end of the line loop
                
            except Exception as e:
                logger.error(f"Execution of {tool} failed: {e}")

    neo4j.close()

    # Final notification
    from reNgine.tasks import send_scan_notif
    send_scan_notif(
        scan_history_id=scan_history_id,
        status='COMPLETED'
    )

    return {"status": "success"}
