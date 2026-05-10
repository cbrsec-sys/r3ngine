import re
import json
import logging

logger = logging.getLogger(__name__)

class BaseParser:
    """Base class for all tool output parsers."""
    def parse_line(self, line):
        raise NotImplementedError("Subclasses must implement parse_line")

class K6Parser(BaseParser):
    """
    Parses k6 output. 
    Note: For real-time telemetry, k6 is best run with '--out json' 
    or we can parse the standard output summary if needed.
    """
    def __init__(self):
        self.metrics = {
            "avg_latency": 0.0,
            "p95_latency": 0.0,
            "error_rate": 0.0,
            "throughput_rps": 0.0,
            "total_requests": 0,
        }

    def parse_line(self, line):
        # Example: http_req_duration..............: avg=12.34ms min=1.23ms med=10.11ms max=100.22ms p(90)=20.33ms p(95)=25.44ms
        avg_match = re.search(r"http_req_duration\.*:\s+avg=([0-9.]+)", line)
        if avg_match:
            self.metrics["avg_latency"] = float(avg_match.group(1))

        p95_match = re.search(r"p\(95\)=([0-9.]+)", line)
        if p95_match:
            self.metrics["p95_latency"] = float(p95_match.group(1))

        reqs_match = re.search(r"http_reqs\.*:\s+([0-9]+)\s+([0-9.]+)/s", line)
        if reqs_match:
            self.metrics["total_requests"] = int(reqs_match.group(1))
            self.metrics["throughput_rps"] = float(reqs_match.group(2))

        failed_match = re.search(r"http_req_failed\.*:\s+([0-9.]+)%", line)
        if failed_match:
            self.metrics["error_rate"] = float(failed_match.group(1)) / 100.0

        return self.metrics

class WrkParser(BaseParser):
    """Parses wrk output summary."""
    def parse_line(self, line):
        # wrk output is mostly a summary at the end, 
        # but we can parse the intermediate stats if using a custom script.
        metrics = {}
        latency_match = re.search(r"Latency\s+([0-9.]+)([a-z]+)", line)
        if latency_match:
            val = float(latency_match.group(1))
            unit = latency_match.group(2)
            if unit == "ms":
                metrics["avg_latency"] = val
            elif unit == "s":
                metrics["avg_latency"] = val * 1000
        
        rps_match = re.search(r"Requests/sec:\s+([0-9.]+)", line)
        if rps_match:
            metrics["throughput_rps"] = float(rps_match.group(1))
            
        return metrics

class Hping3Parser(BaseParser):
    """Parses hping3 output for L4 stats."""
    def parse_line(self, line):
        # len=46 ip=1.2.3.4 ttl=64 id=1234 sport=80 flags=SA seq=0 win=512 rtt=12.3 ms
        metrics = {}
        rtt_match = re.search(r"rtt=([0-9.]+)\s+ms", line)
        if rtt_match:
            metrics["latency"] = float(rtt_match.group(1))
        
        # 100 packets transmitted, 100 packets received, 0% packet loss
        loss_match = re.search(r"([0-9.]+)%\s+packet\s+loss", line)
        if loss_match:
            metrics["packet_loss"] = float(loss_match.group(1))
            
        return metrics

class LocustParser(BaseParser):
    """Parses Locust --print-stats output."""
    def parse_line(self, line):
        # Example: Aggregated    100    0(0.00%)  |      45      12     120     30   |    2.50    0.00
        metrics = {}
        if "Aggregated" in line:
            parts = re.split(r'\s+', line.strip())
            # parts: ['Aggregated', '100', '0(0.00%)', '|', '45', '12', '120', '30', '|', '2.50', '0.00']
            if len(parts) >= 11:
                try:
                    metrics["total_requests"] = int(parts[1])
                    metrics["avg_latency"] = float(parts[4])
                    metrics["throughput_rps"] = float(parts[9])
                    # Parse failure rate from 0(0.00%)
                    fail_match = re.search(r'\(([0-9.]+)%\)', parts[2])
                    if fail_match:
                        metrics["error_rate"] = float(fail_match.group(1)) / 100.0
                except (ValueError, IndexError):
                    pass
        return metrics
