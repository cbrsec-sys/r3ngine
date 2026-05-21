import re
import json
import logging
from typing import Optional, List, Dict

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
        """Initialize the K6Parser state."""
        self.metrics = {
            "avg_latency": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0,
            "error_rate": 0.0,
            "throughput_rps": 0.0,
            "total_requests": 0,
        }

    def parse_line(self, line):
        """Parse a single line of k6 stdout.

        Args:
            line (str): The raw output line from k6 standard output.

        Returns:
            dict: The updated metrics dictionary.
        """
        # Example: http_req_duration..............: avg=12.34ms min=1.23ms med=10.11ms max=100.22ms p(90)=20.33ms p(95)=25.44ms p(99)=30.45ms
        avg_match = re.search(r"http_req_duration\.*:\s+avg=([0-9.]+)", line)
        if avg_match:
            self.metrics["avg_latency"] = float(avg_match.group(1))

        p95_match = re.search(r"p\(95\)=([0-9.]+)", line)
        if p95_match:
            self.metrics["p95_latency"] = float(p95_match.group(1))

        p99_match = re.search(r"p\(99\)=([0-9.]+)", line)
        if p99_match:
            self.metrics["p99_latency"] = float(p99_match.group(1))

        reqs_match = re.search(r"http_reqs\.*:\s+([0-9]+)\s+([0-9.]+)/s", line)
        if reqs_match:
            self.metrics["total_requests"] = int(reqs_match.group(1))
            self.metrics["throughput_rps"] = float(reqs_match.group(2))

        failed_match = re.search(r"http_req_failed\.*:\s+([0-9.]+)%", line)
        if failed_match:
            self.metrics["error_rate"] = float(failed_match.group(1)) / 100.0

        return self.metrics

    def get_final_metrics(self):
        """Calculate and return the final aggregated metrics for the k6 run.

        Returns:
            dict: Standardized dictionary containing total/success/failed requests, latencies, and max RPS.
        """
        total = self.metrics.get("total_requests", 0)
        error_rate = self.metrics.get("error_rate", 0.0)
        failed = int(total * error_rate)
        success = max(0, total - failed)
        return {
            "total_requests": total,
            "successful_requests": success,
            "failed_requests": failed,
            "avg_latency_ms": self.metrics.get("avg_latency", 0.0),
            "p95_latency_ms": self.metrics.get("p95_latency", 0.0),
            "p99_latency_ms": self.metrics.get("p99_latency", 0.0) or self.metrics.get("p95_latency", 0.0),
            "max_requests_per_second": self.metrics.get("throughput_rps", 0.0)
        }


class WrkParser(BaseParser):
    """Parses wrk output summary and accumulates performance statistics over multiple output lines.

    Keeps state between parsed lines to provide complete telemetry containing latency,
    throughput, total requests, socket errors, and calculated error rate.
    """
    def __init__(self):
        """Initialize the WrkParser state."""
        self.metrics = {
            "avg_latency": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0,
            "throughput_rps": 0.0,
            "error_rate": 0.0,
            "total_requests": 0,
            "socket_errors": 0
        }

    def parse_line(self, line):
        """Parse a single line of wrk command output.

        Args:
            line (str): The raw output line from wrk standard output.

        Returns:
            dict or None: The accumulated metrics dictionary if a metric was parsed, else None.
        """
        has_update = False
        
        # Parse Latency line (e.g., "Latency   318.27ms   35.96ms 781.98ms   93.08%")
        latency_match = re.search(r"Latency\s+([0-9.]+)([a-z]+)", line)
        if latency_match:
            val = float(latency_match.group(1))
            unit = latency_match.group(2).lower()
            if unit == "ms":
                self.metrics["avg_latency"] = val
            elif unit == "s":
                self.metrics["avg_latency"] = val * 1000
            has_update = True

        # Parse Latency distribution table lines, e.g. " 95% 150.34ms" or " 99% 250.12ms"
        p_match = re.search(r"^\s*(95%|99%)\s+([0-9.]+)([a-z]+)", line)
        if p_match:
            pct = p_match.group(1)
            val = float(p_match.group(2))
            unit = p_match.group(3).lower()
            if unit == "ms":
                ms_val = val
            elif unit == "s":
                ms_val = val * 1000.0
            else:
                ms_val = val
            if pct == "95%":
                self.metrics["p95_latency"] = ms_val
            elif pct == "99%":
                self.metrics["p99_latency"] = ms_val
            has_update = True
        
        # Parse Requests/sec line (e.g., "Requests/sec:    114.27")
        rps_match = re.search(r"Requests/sec:\s+([0-9.]+)", line)
        if rps_match:
            self.metrics["throughput_rps"] = float(rps_match.group(1))
            has_update = True

        # Parse Total Requests line (e.g., "6864 requests in 1.00m, 5.46MB read")
        reqs_match = re.search(r"([0-9]+)\s+requests\s+in", line)
        if reqs_match:
            self.metrics["total_requests"] = int(reqs_match.group(1))
            has_update = True
            # Recompute error rate if both metrics exist
            if self.metrics["total_requests"] > 0 and self.metrics["socket_errors"] > 0:
                self.metrics["error_rate"] = self.metrics["socket_errors"] / self.metrics["total_requests"]

        # Parse Socket Errors line (e.g., "Socket errors: connect 25, read 0, write 0, timeout 0")
        errors_match = re.search(r"Socket errors:\s+connect\s+([0-9]+),\s+read\s+([0-9]+),\s+write\s+([0-9]+),\s+timeout\s+([0-9]+)", line)
        if errors_match:
            connect_err = int(errors_match.group(1))
            read_err = int(errors_match.group(2))
            write_err = int(errors_match.group(3))
            timeout_err = int(errors_match.group(4))
            self.metrics["socket_errors"] = connect_err + read_err + write_err + timeout_err
            has_update = True
            # Recompute error rate if total requests is already known
            if self.metrics["total_requests"] > 0:
                self.metrics["error_rate"] = self.metrics["socket_errors"] / self.metrics["total_requests"]
            
        return self.metrics if has_update else None

    def get_final_metrics(self):
        """Calculate and return the final aggregated metrics for the wrk run.

        Returns:
            dict: Standardized dictionary containing total/success/failed requests, latencies, and max RPS.
        """
        total = self.metrics.get("total_requests", 0)
        failed = self.metrics.get("socket_errors", 0)
        success = max(0, total - failed)
        return {
            "total_requests": total,
            "successful_requests": success,
            "failed_requests": failed,
            "avg_latency_ms": self.metrics.get("avg_latency", 0.0),
            "p95_latency_ms": self.metrics.get("p95_latency", 0.0) or self.metrics.get("avg_latency", 0.0),
            "p99_latency_ms": self.metrics.get("p99_latency", 0.0) or self.metrics.get("avg_latency", 0.0),
            "max_requests_per_second": self.metrics.get("throughput_rps", 0.0)
        }


class Hping3Parser(BaseParser):
    """Parses hping3 output for L4 stats."""
    def __init__(self):
        """Initialize the Hping3Parser state."""
        self.latencies = []
        self.total_packets = 0
        self.failed_packets = 0
        self.packet_loss = 0.0
        
        self.start_time = None
        self.last_calc_time = None
        self.packets_in_window = 0
        self.current_rps = 0.0

    def parse_line(self, line):
        """Parse a single line of hping3 output.

        Args:
            line (str): The raw output line from hping3 standard output.

        Returns:
            dict: Parsed metrics for latency or packet loss.
        """
        metrics = {}
        now = time.time()
        
        if self.start_time is None:
            self.start_time = now
            self.last_calc_time = now
            
        # len=46 ip=1.2.3.4 ttl=64 id=1234 sport=80 flags=SA seq=0 win=512 rtt=12.3 ms
        rtt_match = re.search(r"rtt=([0-9.]+)\s+ms", line)
        if rtt_match:
            lat = float(rtt_match.group(1))
            self.latencies.append(lat)
            metrics["latency"] = lat
            self.packets_in_window += 1
        
        # 100 packets transmitted, 100 packets received, 0% packet loss
        loss_match = re.search(r"([0-9]+)\s+packets\s+transmitted,\s+([0-9]+)\s+packets\s+received,\s+([0-9.]+)%\s+packet\s+loss", line)
        if loss_match:
            self.total_packets = int(loss_match.group(1))
            received = int(loss_match.group(2))
            self.failed_packets = self.total_packets - received
            self.packet_loss = float(loss_match.group(3))
            metrics["packet_loss"] = self.packet_loss
            
        # Calculate live RPS every 1 second
        if now - self.last_calc_time >= 1.0:
            self.current_rps = self.packets_in_window / (now - self.last_calc_time)
            metrics["throughput_rps"] = self.current_rps
            self.packets_in_window = 0
            self.last_calc_time = now
        else:
            if self.current_rps > 0:
                metrics["throughput_rps"] = self.current_rps
            
        return metrics if metrics else None

    def get_final_metrics(self):
        """Calculate and return the final aggregated metrics for the hping3 run.

        Returns:
            dict: Standardized dictionary containing total/success/failed requests, latencies, and max RPS.
        """
        avg_lat = sum(self.latencies) / len(self.latencies) if self.latencies else 0.0
        sorted_lats = sorted(self.latencies)
        p95 = sorted_lats[int(len(sorted_lats) * 0.95)] if sorted_lats else 0.0
        p99 = sorted_lats[int(len(sorted_lats) * 0.99)] if sorted_lats else 0.0
        
        # If loss match was not encountered or packet stats not captured yet, estimate from RTT list
        total = self.total_packets
        if total == 0 and self.latencies:
            total = len(self.latencies)
            
        # RPS over the entire run
        total_time = time.time() - (self.start_time or time.time())
        max_rps = total / total_time if total_time > 0 else 0.0
            
        return {
            "total_requests": total,
            "successful_requests": total - self.failed_packets,
            "failed_requests": self.failed_packets,
            "avg_latency_ms": avg_lat,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "max_requests_per_second": max_rps
        }


class LocustParser(BaseParser):
    """Parses Locust --print-stats output."""
    def __init__(self):
        """Initialize the LocustParser state."""
        self.metrics = {
            "avg_latency": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0,
            "throughput_rps": 0.0,
            "total_requests": 0,
            "failed_requests": 0,
            "error_rate": 0.0,
            "main_table": [],
            "percentile_table": []
        }
        self.in_main = False
        self.in_perc = False

    def parse_line(self, line):
        """Parse a single line of Locust --print-stats output.

        Args:
            line (str): The raw output line.

        Returns:
            dict: The updated metrics dictionary.
        """
        has_update = False
        line_stripped = line.strip("\r")
        if "Type" in line_stripped and "# reqs" in line_stripped and "# fails" in line_stripped:
            self.in_main = True
            self.in_perc = False
            self.metrics["main_table"] = []
            return None
        if "Type" in line_stripped and "50%" in line_stripped and "66%" in line_stripped:
            self.in_perc = True
            self.in_main = False
            self.metrics["percentile_table"] = []
            return None
            
        if line_stripped.startswith("--------"):
            return None

        if self.in_main and line_stripped.strip() != "":
            cleaned = line_stripped.replace("|", " ").replace("(", " ").replace(")", " ").replace("%", " ")
            parts = re.split(r'\s+', cleaned.strip())
            if len(parts) >= 10:
                has_update = True
                try:
                    if parts[0] == "Aggregated":
                        self.metrics["main_table"].append({
                            "method": "", "name": "Aggregated", "reqs": int(parts[1]), "fails": int(parts[2]),
                            "error_rate": float(parts[3]), "avg": float(parts[4]), "min": float(parts[5]),
                            "max": float(parts[6]), "med": float(parts[7]), "req_s": float(parts[8]), "fail_s": float(parts[9])
                        })
                        # Also update top-level metrics
                        self.metrics["total_requests"] = int(parts[1])
                        self.metrics["failed_requests"] = int(parts[2])
                        self.metrics["error_rate"] = float(parts[3]) / 100.0
                        self.metrics["avg_latency"] = float(parts[4])
                        self.metrics["throughput_rps"] = float(parts[8])
                        self.in_main = False # End of table
                    else:
                        self.metrics["main_table"].append({
                            "method": parts[0], "name": parts[1], "reqs": int(parts[2]), "fails": int(parts[3]),
                            "error_rate": float(parts[4]), "avg": float(parts[5]), "min": float(parts[6]),
                            "max": float(parts[7]), "med": float(parts[8]), "req_s": float(parts[9]), "fail_s": float(parts[10])
                        })
                except (ValueError, IndexError):
                    pass

        if self.in_perc and line_stripped.strip() != "":
            cleaned = line_stripped.replace("|", " ")
            parts = re.split(r'\s+', cleaned.strip())
            if len(parts) >= 12:
                has_update = True
                try:
                    if parts[0] == "Aggregated":
                        self.metrics["percentile_table"].append({
                            "method": "", "name": "Aggregated",
                            "p50": float(parts[1]), "p66": float(parts[2]), "p75": float(parts[3]), "p80": float(parts[4]),
                            "p90": float(parts[5]), "p95": float(parts[6]), "p98": float(parts[7]), "p99": float(parts[8]),
                            "p999": float(parts[9]), "p9999": float(parts[10]), "p100": float(parts[11]), "reqs": int(parts[12])
                        })
                        self.in_perc = False # End of table
                    else:
                        self.metrics["percentile_table"].append({
                            "method": parts[0], "name": parts[1],
                            "p50": float(parts[2]), "p66": float(parts[3]), "p75": float(parts[4]), "p80": float(parts[5]),
                            "p90": float(parts[6]), "p95": float(parts[7]), "p98": float(parts[8]), "p99": float(parts[9]),
                            "p999": float(parts[10]), "p9999": float(parts[11]), "p100": float(parts[12]), "reqs": int(parts[13])
                        })
                except (ValueError, IndexError):
                    pass
        
        return self.metrics if has_update else None

    def get_final_metrics(self):
        """Calculate and return the final aggregated metrics for the Locust run.

        Returns:
            dict: Standardized dictionary containing total/success/failed requests, latencies, and max RPS.
        """
        total = self.metrics.get("total_requests", 0)
        failed = self.metrics.get("failed_requests", 0)
        success = max(0, total - failed)
        return {
            "total_requests": total,
            "successful_requests": success,
            "failed_requests": failed,
            "avg_latency_ms": self.metrics.get("avg_latency", 0.0),
            "p95_latency_ms": self.metrics.get("avg_latency", 0.0),
            "p99_latency_ms": self.metrics.get("avg_latency", 0.0),
            "max_requests_per_second": self.metrics.get("throughput_rps", 0.0)
        }



class SpiderFootBatchParser(BaseParser):
    """
    Robust stateful SpiderFoot CSV parser.
    Supports streaming, batching, and Redis-backed deduplication.
    """
    
    REQUIRED_COLUMNS = ["Source", "Type", "Source Data", "Data"]
    
    IOC_REGEX = {
        "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "domain": re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b"),
        "email": re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
        "url": re.compile(r"https?://[^\s]+"),
        "hash": re.compile(r"\b[a-fA-F0-9]{32,64}\b"),
    }

    # Maps SF Type strings (from CSV) to internal OSINT types and confidence weights
    SF_TYPE_MAPPING = {
        'EMAIL_ADDRESS': {'osint_type': 'Email', 'weight': 90},
        'EMAILADDR': {'osint_type': 'Email', 'weight': 90},
        'HUMAN_NAME': {'osint_type': 'Employee', 'weight': 70},
        'USERNAME': {'osint_type': 'Employee', 'weight': 80},
        'LINKEDIN_NAME': {'osint_type': 'Employee', 'weight': 85},
        'PHONE_NUMBER': {'osint_type': 'Phone', 'weight': 85},
        'INTERNET_NAME': {'osint_type': 'Subdomain', 'weight': 100},
        'DOMAIN_NAME': {'osint_type': 'Subdomain', 'weight': 100},
        'AFFILIATE_DOMAIN_NAME': {'osint_type': 'Subdomain', 'weight': 60},
        'IP_ADDRESS': {'osint_type': 'IP', 'weight': 100},
        'IPV4_ADDRESS': {'osint_type': 'IP', 'weight': 100},
        'TCP_PORT_OPEN': {'osint_type': 'Port', 'weight': 100},
        'UDP_PORT_OPEN': {'osint_type': 'Port', 'weight': 100},
        'SOCIAL_MEDIA': {'osint_type': 'Social', 'weight': 80},
        'ACCOUNT_EXTERNAL': {'osint_type': 'Social', 'weight': 75},
        'BITCOIN_ADDRESS': {'osint_type': 'Crypto', 'weight': 90},
        'WEB_RESOURCE': {'osint_type': 'URL', 'weight': 100},
        'URL_ALL': {'osint_type': 'URL', 'weight': 100},
        'LEAKSITE_CONTENT': {'osint_type': 'Leak', 'weight': 85},
        'ACCOUNT_EXTERNAL_OWNED_PARTIAL': {'osint_type': 'Social', 'weight': 60},
        # Infrastructure & Tech
        'WEB_SERVER': {'osint_type': 'Tech', 'weight': 90},
        'SOFTWARE_USED': {'osint_type': 'Tech', 'weight': 85},
        'OPERATING_SYSTEM': {'osint_type': 'OS', 'weight': 85},
        # DNS & Infrastructure (Staging)
        'DNS_TXT_RECORD': {'osint_type': 'DNS', 'weight': 60},
        'DNS_MX_RECORD': {'osint_type': 'DNS', 'weight': 60},
        'DNS_NS_RECORD': {'osint_type': 'DNS', 'weight': 60},
        'NAME_SERVER_(DNS_NS_RECORDS)': {'osint_type': 'DNS', 'weight': 60},
        'EMAIL_GATEWAY_(DNS_MX_RECORDS)': {'osint_type': 'DNS', 'weight': 60},
        'RAW_DNS_RECORDS': {'osint_type': 'DNS', 'weight': 50},
        'PROVIDER_DNS': {'osint_type': 'DNS', 'weight': 50},
        'SSL_CERTIFICATE_ISSUED_TO': {'osint_type': 'SSL', 'weight': 70},
        'SSL_CERTIFICATE_RAW': {'osint_type': 'SSL', 'weight': 50},
        'CO-HOSTED_SITE': {'osint_type': 'Hosting', 'weight': 60},
    }

    def __init__(self, dedup_backend=None, scan_id=None, target_domain=None):
        self.dedup_backend = dedup_backend or set()
        self.scan_id = scan_id
        self.target_domain = target_domain
        self.stats = {
            "processed": 0,
            "duplicates": 0,
            "valid": 0,
            "invalid": 0,
        }
        self.header = None

    def parse_line(self, line: str) -> Optional[dict]:
        """Parses a single line of SpiderFoot CSV output."""
        if not line or not line.strip():
            return None
            
        self.stats["processed"] += 1
        
        # Strip null bytes to prevent _csv.Error
        line = line.replace('\0', '')
        
        import io
        import csv
        
        f = io.StringIO(line)
        reader = csv.reader(f)
        try:
            row = next(reader)
        except (StopIteration, csv.Error):
            self.stats["invalid"] += 1
            return None

        if not self.header:
            if "Data" in row and "Type" in row:
                self.header = row
                return None
            else:
                self.stats["invalid"] += 1
                return None

        # Map row to dict
        event = dict(zip(self.header, row))
        
        parsed = self._normalize_event(event)
        if not parsed:
            self.stats["invalid"] += 1
            return None
            
        # Deduplication
        fingerprint = self._fingerprint(parsed)
        if self._is_duplicate(fingerprint):
            self.stats["duplicates"] += 1
            return None
            
        self._store_fingerprint(fingerprint)
        self.stats["valid"] += 1
        
        # Confidence & Relevance Calculation
        mapping = self.SF_TYPE_MAPPING.get(parsed["type"], {'osint_type': 'Other', 'weight': 50})
        parsed["osint_type"] = mapping['osint_type']
        parsed["confidence"] = self._calculate_confidence(parsed, mapping['weight'])
        
        # Add IOCs
        parsed["iocs"] = self._extract_iocs(parsed["data"])
        
        return parsed

    def _normalize_event(self, event: dict) -> Optional[dict]:
        e_type = event.get("Type", "").strip().upper().replace(" ", "_")
        e_data = event.get("Data", "").strip()
        
        if not e_type or not e_data:
            return None
            
        return {
            "source": event.get("Source", "").strip(),
            "type": e_type,
            "source_data": event.get("Source Data", "").strip(),
            "data": e_data,
        }

    def _calculate_confidence(self, event: dict, base_weight: int) -> int:
        """
        Calculates confidence score (0-100) based on relevance to target_domain.
        """
        score = base_weight
        data = event["data"].lower()
        
        if not self.target_domain:
            return score

        target = self.target_domain.lower()
        
        # Relevance adjustments
        if event["osint_type"] == "Email":
            if data.endswith(f"@{target}"):
                score = min(100, score + 10)
            elif any(domain in data for domain in ["gmail.com", "outlook.com", "yahoo.com"]):
                score = max(0, score - 20) # Personal emails are lower confidence for company
        
        elif event["osint_type"] == "Subdomain":
            if data.endswith(f".{target}") or data == target:
                score = 100
            else:
                score = max(0, score - 30) # Unrelated domain
                
        elif event["osint_type"] == "IP":
            # Hard to judge without WHOIS/ASN check here, keep base weight
            pass
            
        elif event["osint_type"] == "Employee":
            # If source data contains the target domain, boost it
            if target in event["source_data"].lower():
                score = min(100, score + 15)

        return score

    def _fingerprint(self, event: dict) -> str:
        import hashlib
        raw = "|".join([
            event.get("source", ""),
            event.get("type", ""),
            event.get("source_data", ""),
            event.get("data", ""),
        ])
        return hashlib.sha256(raw.encode()).hexdigest()

    def _is_duplicate(self, fingerprint: str) -> bool:
        if hasattr(self.dedup_backend, "sismember"):
            key = f"spiderfoot:dedup:{self.scan_id}" if self.scan_id else "spiderfoot:dedup"
            return self.dedup_backend.sismember(key, fingerprint)
        return fingerprint in self.dedup_backend

    def _store_fingerprint(self, fingerprint: str):
        if hasattr(self.dedup_backend, "sadd"):
            key = f"spiderfoot:dedup:{self.scan_id}" if self.scan_id else "spiderfoot:dedup"
            self.dedup_backend.sadd(key, fingerprint)
            return
        self.dedup_backend.add(fingerprint)

    def _extract_iocs(self, text: str) -> dict:
        results = {}
        for name, regex in self.IOC_REGEX.items():
            matches = regex.findall(text)
            if matches:
                results[name] = list(sorted(set(matches)))
        return results


class TAStressorParser(BaseParser):
    """Parses TA_Stresser.py debug output for PPS/throughput."""
    def __init__(self):
        """Initialize the TAStressorParser state."""
        self.metrics = {
            "avg_latency": 0.0,
            "throughput_rps": 0.0,
            "throughput_bps": 0.0,
            "error_rate": 0.0,
            "total_requests": 0,
            "failed_requests": 0,
            "total_bytes": 0,
        }

    def parse_line(self, line):
        """Parse a single line of TAStressor debug output.

        Args:
            line (str): The raw output line.

        Returns:
            dict: The updated metrics dictionary.
        """
        has_update = False
        
        # Strip ANSI escape codes
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        
        # Regex to capture the PPS (Packets/Requests per second) and optional unit suffix
        pps_match = re.search(r"PPS:\s*([0-9.]+)([kmgtp]?)", clean_line, re.IGNORECASE)
        if pps_match:
            val = float(pps_match.group(1))
            unit = pps_match.group(2).lower()
            if unit == 'k':
                val *= 1_000
            elif unit == 'm':
                val *= 1_000_000
            elif unit == 'g':
                val *= 1_000_000_000
            elif unit == 't':
                val *= 1_000_000_000_000
            
            self.metrics["throughput_rps"] = val
            # Accumulate requests dynamically (since logs output rate every 1 second)
            self.metrics["total_requests"] += int(val)
            has_update = True
            
        # Regex to capture BPS (Bytes per second)
        bps_match = re.search(r"BPS:\s*([0-9.]+)\s*([kmgtp]?b)", clean_line, re.IGNORECASE)
        if bps_match:
            val = float(bps_match.group(1))
            unit = bps_match.group(2).lower()
            if unit == 'kb':
                val *= 1_000
            elif unit == 'mb':
                val *= 1_000_000
            elif unit == 'gb':
                val *= 1_000_000_000
            elif unit == 'tb':
                val *= 1_000_000_000_000
                
            self.metrics["throughput_bps"] = val
            self.metrics["total_bytes"] += int(val)
            has_update = True
            
        # Parse failed count if present (for future-proofing)
        failed_match = re.search(r"PPS_failed:\s*([0-9.]+)([kmgtp]?)", clean_line, re.IGNORECASE)
        if failed_match:
            f_val = float(failed_match.group(1))
            f_unit = failed_match.group(2).lower()
            if f_unit == 'k': f_val *= 1_000
            elif f_unit == 'm': f_val *= 1_000_000
            elif f_unit == 'g': f_val *= 1_000_000_000
                
            self.metrics["failed_requests"] += int(f_val)
            has_update = True
            
        return self.metrics if has_update else None

    def get_final_metrics(self):
        """Calculate and return the final aggregated metrics for the TAStressor run.

        Returns:
            dict: Standardized dictionary containing total/success/failed requests, latencies, and max RPS.
        """
        total = self.metrics.get("total_requests", 0)
        failed = self.metrics.get("failed_requests", 0)
        
        # fallback to error_rate if failed is 0 and error_rate exists
        if failed == 0 and total > 0:
            error_rate = self.metrics.get("error_rate", 0.0)
            failed = int(total * error_rate)
            
        success = max(0, total - failed)
        return {
            "total_requests": total,
            "successful_requests": success,
            "failed_requests": failed,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "max_requests_per_second": self.metrics.get("throughput_rps", 0.0)
        }


