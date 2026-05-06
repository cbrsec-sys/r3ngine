from celery import shared_task
from django.conf import settings
import subprocess
import json
import os
import re
import redis
import logging
from startScan.models import ScanHistory, EndPoint
from targetApp.models import Domain
from startScan.stress_result_models import StressTestResult
from reNgine.graph_utils import Neo4jManager
from django.utils import timezone
from .celery_custom_task import RengineTask
from reNgine.utilities import send_notification

logger = logging.getLogger(__name__)

# Redis for kill switch
try:
    redis_client = redis.StrictRedis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0
    )
except:
    redis_client = None


def is_kill_switch_active(scan_id):
    """Check if the kill switch for this scan has been flipped in Redis."""
    if redis_client:
        return redis_client.get(f"kill_switch_{scan_id}") == b"1"
    return False


def parse_k6_output(output_str):
    metrics = {
        "avg_latency": 0.0,
        "p95_latency": 0.0,
        "error_rate": 0.0,
        "throughput_rps": 0.0,
        "total_requests": 0,
    }
    avg_req_dur = re.search(r"http_req_duration\.*:\s+avg=([0-9.]+)", output_str)
    if avg_req_dur:
        metrics["avg_latency"] = float(avg_req_dur.group(1))

    p95_req_dur = re.search(r"http_req_duration\.*:\s+.*p\(95\)=([0-9.]+)", output_str)
    if p95_req_dur:
        metrics["p95_latency"] = float(p95_req_dur.group(1))

    reqs = re.search(r"http_reqs\.*:\s+([0-9]+)\s+([0-9.]+)/s", output_str)
    if reqs:
        metrics["total_requests"] = int(reqs.group(1))
        metrics["throughput_rps"] = float(reqs.group(2))

    failed = re.search(r"http_req_failed\.*:\s+([0-9.]+)%", output_str)
    if failed:
        metrics["error_rate"] = float(failed.group(1)) / 100.0

    return metrics


@shared_task(base=RengineTask, bind=True)
def run_stress_testing(self, scan_history_id, target_domain_name, yaml_config):
    # Extract config
    stress_config = yaml_config.get("stress_test", {})
    if not stress_config:
        return {"status": "success", "message": "No stress test config provided"}

    concurrency = stress_config.get("concurrency", 50)
    duration = stress_config.get("duration", "30s")
    tools = stress_config.get("uses_tools", ["k6"])

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
        tool_used=tools[0],
        concurrency_used=concurrency,
        duration=duration,
    )

    total_reqs = 0

    for endpoint in endpoints:
        if is_kill_switch_active(scan_history_id):
            logger.warning(
                f"Kill switch activated for scan {scan_history_id}. Aborting stress test."
            )
            overall_result.is_kill_switch_triggered = True
            overall_result.save()
            break

        # Traffic Engine Orchestration
        if "k6" in tools:
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

            cmd = [
                "k6",
                "run",
                "--vus",
                str(concurrency),
                "--duration",
                str(duration),
                script_path,
            ]
            logger.info(f"Running stress test command: {' '.join(cmd)}")

            try:
                process = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=120
                )
                output = process.stdout
            except Exception as e:
                output = ""
                logger.error(f"k6 execution failed: {e}")

            metrics = parse_k6_output(output)

            # Neo4j Telemetry Ingestion
            neo4j.ingest_stress_telemetry(
                endpoint.http_url,
                scan_history_id,
                {
                    "tool": "k6",
                    "concurrent_users": concurrency,
                    "avg_latency": metrics["avg_latency"],
                    "p95_latency": metrics["p95_latency"],
                    "error_rate": metrics["error_rate"],
                    "total_requests": metrics["total_requests"],
                    "throughput_rps": metrics["throughput_rps"],
                },
            )

            total_reqs += metrics["total_requests"]

            overall_result.total_requests += metrics["total_requests"]
            overall_result.avg_latency_ms = max(
                overall_result.avg_latency_ms, metrics["avg_latency"]
            )
            overall_result.p95_latency_ms = max(
                overall_result.p95_latency_ms, metrics["p95_latency"]
            )
            overall_result.save()

    neo4j.close()

    send_notification(
        f"Stress testing completed for {target_domain_name}. Total Requests: {total_reqs}",
        scan_history_id,
    )

    return {"status": "success"}
