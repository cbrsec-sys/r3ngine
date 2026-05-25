"""
StressReportBuilder - Organizes stress test data for report generation.
Extracts and structures data from StressTestResult + StressTelemetryPoint for templating.
"""
from django.utils import timezone
from startScan.models import StressTestResult, StressTelemetryPoint


class StressReportBuilder:
    """Builds comprehensive report context from a StressTestResult."""

    TOOL_CHOICES = ['k6', 'wrk', 'hping3', 'locust', 'stressor']

    def __init__(self, stress_result):
        """Initialize with a StressTestResult instance."""
        self.stress_result = stress_result
        self.telemetry_points = None
        self.tool_config = None

    def build(self):
        """Build complete report context."""
        context = {
            'test_metadata': self._build_test_metadata(),
            'performance_summary': self._build_performance_summary(),
            'tool_sections': self._build_tool_sections(),
            'endpoint_analysis': self._build_endpoint_analysis(),
            'findings_and_recommendations': self._build_findings_recommendations(),
            'timeline_data': self._build_timeline_data(),
        }
        return context

    def _fetch_telemetry(self):
        """Fetch telemetry points once if not cached."""
        if self.telemetry_points is None:
            self.telemetry_points = list(
                self.stress_result.telemetry_points.all().order_by('timestamp')
            )
        return self.telemetry_points

    def _fetch_tool_config(self):
        """Fetch tool configuration once if not cached."""
        if self.tool_config is None:
            try:
                self.tool_config = self.stress_result.tool_config
            except:
                self.tool_config = None
        return self.tool_config

    def _build_test_metadata(self):
        """Extract test metadata (duration, target, tool, concurrency, etc.)."""
        duration = self.stress_result.duration or 'Unknown'

        return {
            'tool_used': self.stress_result.tool_used,
            'tool_display_name': self._get_tool_display_name(self.stress_result.tool_used),
            'target_domain': str(self.stress_result.target_domain) if self.stress_result.target_domain else 'Unknown',
            'start_time': self.stress_result.start_time,
            'end_time': self.stress_result.end_time,
            'duration': duration,
            'concurrency_level': self.stress_result.concurrency_used,
            'max_concurrent_connections': self.stress_result.max_concurrent_connections,
            'test_status': self.stress_result.get_test_status_display() if hasattr(self.stress_result, 'get_test_status_display') else self.stress_result.test_status,
            'endpoints_tested_count': len(self.stress_result.endpoints_tested) if self.stress_result.endpoints_tested else 0,
            'endpoints_tested': self.stress_result.endpoints_tested or [],
        }

    def _build_performance_summary(self):
        """Build KPI cards with key metrics."""
        success_rate = 0
        if self.stress_result.total_requests > 0:
            success_rate = (self.stress_result.successful_requests / self.stress_result.total_requests) * 100

        error_rate = 0
        if self.stress_result.total_requests > 0:
            error_rate = (self.stress_result.failed_requests / self.stress_result.total_requests) * 100

        return {
            'total_requests': self.stress_result.total_requests,
            'successful_requests': self.stress_result.successful_requests,
            'failed_requests': self.stress_result.failed_requests,
            'success_rate_percent': round(success_rate, 2),
            'error_rate_percent': round(error_rate, 2),
            'avg_latency_ms': round(self.stress_result.avg_latency_ms, 2),
            'p50_latency_ms': round(self.stress_result.p50_latency_ms, 2),
            'p75_latency_ms': round(self.stress_result.p75_latency_ms, 2),
            'p90_latency_ms': round(self.stress_result.p90_latency_ms, 2),
            'p95_latency_ms': round(self.stress_result.p95_latency_ms, 2),
            'p99_latency_ms': round(self.stress_result.p99_latency_ms, 2),
            'p999_latency_ms': round(self.stress_result.p999_latency_ms, 2),
            'peak_throughput_rps': round(self.stress_result.peak_throughput_rps, 2),
            'max_requests_per_second': round(self.stress_result.max_requests_per_second, 2),
            'kill_switch_triggered': self.stress_result.is_kill_switch_triggered,
        }

    def _build_tool_sections(self):
        """Build per-tool sections with tool-specific visualizations."""
        tool_sections = {}
        tool = self.stress_result.tool_used

        telemetry = self._fetch_telemetry()

        tool_sections[tool] = self._build_tool_specific_section(tool, telemetry)

        return tool_sections

    def _build_tool_specific_section(self, tool, telemetry):
        """Build tool-specific metrics and visualizations."""
        section = {
            'tool': tool,
            'tool_display_name': self._get_tool_display_name(tool),
            'configuration': self._extract_tool_config(),
            'common_metrics': self._build_common_metrics(),
        }

        if tool == 'k6':
            section.update(self._build_k6_section(telemetry))
        elif tool == 'wrk':
            section.update(self._build_wrk_section(telemetry))
        elif tool == 'hping3':
            section.update(self._build_hping3_section(telemetry))
        elif tool == 'locust':
            section.update(self._build_locust_section(telemetry))
        elif tool == 'stressor':
            section.update(self._build_stressor_section(telemetry))

        return section

    def _build_common_metrics(self):
        """Build metrics common to all tools."""
        return {
            'total_requests': self.stress_result.total_requests,
            'successful_requests': self.stress_result.successful_requests,
            'failed_requests': self.stress_result.failed_requests,
            'avg_latency_ms': round(self.stress_result.avg_latency_ms, 2),
            'p95_latency_ms': round(self.stress_result.p95_latency_ms, 2),
            'p99_latency_ms': round(self.stress_result.p99_latency_ms, 2),
            'peak_throughput_rps': round(self.stress_result.peak_throughput_rps, 2),
        }

    def _build_k6_section(self, telemetry):
        """Build K6-specific metrics and visualizations."""
        return {
            'k6_specific': {
                'status_code_distribution': self.stress_result.response_code_distribution or {},
                'error_breakdown': self.stress_result.error_breakdown or {},
                'latency_percentiles': self._extract_percentiles(),
                'checks_results': self._extract_k6_checks(),
            }
        }

    def _build_wrk_section(self, telemetry):
        """Build WRK-specific metrics and visualizations."""
        tool_metrics = self._extract_tool_specific_metrics(telemetry)

        return {
            'wrk_specific': {
                'requests_completed': self.stress_result.total_requests,
                'bytes_transferred': tool_metrics.get('bytes_transferred', 'N/A'),
                'socket_errors': tool_metrics.get('socket_errors', 0),
                'timeouts': tool_metrics.get('timeout_errors', 0),
                'latency_stats': {
                    'avg': round(self.stress_result.avg_latency_ms, 2),
                    'min': tool_metrics.get('min_latency', 0),
                    'max': tool_metrics.get('max_latency', 0),
                    'stdev': tool_metrics.get('latency_stdev', 0),
                },
                'throughput_rps': round(self.stress_result.peak_throughput_rps, 2),
            }
        }

    def _build_hping3_section(self, telemetry):
        """Build Hping3-specific metrics and visualizations."""
        tool_metrics = self._extract_tool_specific_metrics(telemetry)

        # Calculate packet loss percentage
        packets_sent = tool_metrics.get('packets_sent', 0)
        packets_received = tool_metrics.get('packets_received', 0)
        packet_loss_percent = 0
        if packets_sent > 0:
            packet_loss_percent = ((packets_sent - packets_received) / packets_sent) * 100

        return {
            'hping3_specific': {
                'packets_sent': packets_sent,
                'packets_received': packets_received,
                'packet_loss_percent': round(packet_loss_percent, 2),
                'packet_loss_color': self._get_packet_loss_color(packet_loss_percent),
                'rtt_stats': {
                    'min': tool_metrics.get('rtt_min', 0),
                    'avg': tool_metrics.get('rtt_avg', 0),
                    'max': tool_metrics.get('rtt_max', 0),
                },
                'protocol': tool_metrics.get('protocol', 'ICMP'),
            }
        }

    def _build_locust_section(self, telemetry):
        """Build Locust-specific metrics and visualizations."""
        tool_metrics = self._extract_tool_specific_metrics(telemetry)

        return {
            'locust_specific': {
                'total_users': tool_metrics.get('total_users', self.stress_result.concurrency_used),
                'request_count': self.stress_result.total_requests,
                'failure_count': self.stress_result.failed_requests,
                'avg_response_time': round(self.stress_result.avg_latency_ms, 2),
                'per_endpoint_stats': tool_metrics.get('per_endpoint_stats', []),
                'user_ramp_up': tool_metrics.get('user_ramp_up_data', []),
                'response_time_percentiles': self._extract_percentiles(),
            }
        }

    def _build_stressor_section(self, telemetry):
        """Build TAStressor-specific metrics and visualizations."""
        tool_metrics = self._extract_tool_specific_metrics(telemetry)

        layer = tool_metrics.get('attack_mode', 'Unknown')
        is_layer4 = 'layer4' in str(layer).lower()

        return {
            'stressor_specific': {
                'attack_mode': layer,
                'is_layer4': is_layer4,
                'is_layer7': not is_layer4,
                'pps': tool_metrics.get('pps', 0) if is_layer4 else None,
                'bps': tool_metrics.get('bps', 0) if is_layer4 else None,
                'rps': tool_metrics.get('rps', self.stress_result.peak_throughput_rps) if not is_layer4 else None,
                'response_rates': tool_metrics.get('response_rates', {}),
                'protocol_breakdown': tool_metrics.get('protocol_breakdown', {}),
                'status_code_distribution': self.stress_result.response_code_distribution or {},
            }
        }

    def _build_endpoint_analysis(self):
        """Build per-endpoint performance analysis."""
        endpoints = self.stress_result.endpoints_tested or []

        endpoint_stats = []
        for endpoint in endpoints:
            endpoint_stats.append({
                'url': endpoint.get('url', endpoint) if isinstance(endpoint, dict) else endpoint,
                'method': endpoint.get('method', 'GET') if isinstance(endpoint, dict) else 'GET',
                'requests': endpoint.get('requests', 0) if isinstance(endpoint, dict) else 0,
                'failures': endpoint.get('failures', 0) if isinstance(endpoint, dict) else 0,
            })

        return {
            'endpoints': endpoint_stats,
            'endpoint_count': len(endpoint_stats),
        }

    def _build_findings_recommendations(self):
        """Build findings and recommendations sections."""
        return {
            'findings': self.stress_result.findings or '',
            'findings_list': self._parse_findings(self.stress_result.findings),
            'anomalies': self.stress_result.anomalies_detected or [],
            'recommendations': self.stress_result.recommendations or '',
            'recommendations_list': self._parse_recommendations(self.stress_result.recommendations),
        }

    def _build_timeline_data(self):
        """Build timeline/time-series data for charts."""
        telemetry = self._fetch_telemetry()

        timeline = {
            'latency_over_time': [],
            'throughput_over_time': [],
            'error_rate_over_time': [],
            'request_count_over_time': [],
        }

        for point in telemetry:
            timestamp = point.timestamp.isoformat()

            if point.latency_ms is not None:
                timeline['latency_over_time'].append({
                    'timestamp': timestamp,
                    'value': round(point.latency_ms, 2)
                })

            if point.throughput is not None:
                timeline['throughput_over_time'].append({
                    'timestamp': timestamp,
                    'value': round(point.throughput, 2)
                })

            if point.error_rate is not None:
                timeline['error_rate_over_time'].append({
                    'timestamp': timestamp,
                    'value': round(point.error_rate * 100, 2)
                })

            if point.request_count is not None:
                timeline['request_count_over_time'].append({
                    'timestamp': timestamp,
                    'value': point.request_count
                })

        return timeline

    def _extract_tool_config(self):
        """Extract tool configuration from StressToolConfiguration."""
        config = self._fetch_tool_config()
        if config and config.tool_configs:
            return config.tool_configs
        return {}

    def _extract_tool_specific_metrics(self, telemetry):
        """Extract tool-specific metrics from telemetry points."""
        if not telemetry:
            return {}

        aggregated = {}
        for point in telemetry:
            if point.tool_specific_metrics:
                for key, value in point.tool_specific_metrics.items():
                    if key not in aggregated:
                        aggregated[key] = value
                    elif isinstance(value, (int, float)):
                        aggregated[key] = max(aggregated[key], value) if isinstance(aggregated[key], (int, float)) else value

        return aggregated

    def _extract_percentiles(self):
        """Extract all percentile data."""
        percentiles = self.stress_result.percentile_latencies or {}
        if not percentiles:
            percentiles = {
                'p50': self.stress_result.p50_latency_ms,
                'p75': self.stress_result.p75_latency_ms,
                'p90': self.stress_result.p90_latency_ms,
                'p95': self.stress_result.p95_latency_ms,
                'p99': self.stress_result.p99_latency_ms,
                'p999': self.stress_result.p999_latency_ms,
            }

        return {k: round(v, 2) if isinstance(v, float) else v for k, v in percentiles.items()}

    def _extract_k6_checks(self):
        """Extract K6 check results if available."""
        telemetry = self._fetch_telemetry()
        checks = {}

        for point in telemetry:
            if point.tool_specific_metrics and 'checks' in point.tool_specific_metrics:
                checks.update(point.tool_specific_metrics['checks'])

        return checks

    def _parse_findings(self, findings_text):
        """Parse findings text into a list."""
        if not findings_text:
            return []
        return [line.strip() for line in findings_text.split('\n') if line.strip()]

    def _parse_recommendations(self, recommendations_text):
        """Parse recommendations text into a list."""
        if not recommendations_text:
            return []
        return [line.strip() for line in recommendations_text.split('\n') if line.strip()]

    def _get_tool_display_name(self, tool):
        """Get human-readable tool name."""
        names = {
            'k6': 'K6',
            'wrk': 'WRK',
            'hping3': 'Hping3',
            'locust': 'Locust',
            'stressor': 'TAStressor',
        }
        return names.get(tool, tool)

    def _get_packet_loss_color(self, packet_loss_percent):
        """Get color code for packet loss indicator."""
        if packet_loss_percent < 1:
            return 'green'
        elif packet_loss_percent < 5:
            return 'yellow'
        else:
            return 'red'
