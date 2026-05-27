"""
Comprehensive tests for Phase 1: Stress Testing Data Persistence Foundation
Tests cover: Models, Parsers, Aggregation Task
"""
import json
import time
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from startScan.models import (
    ScanHistory, StressTestResult, StressTelemetryPoint,
    StressToolConfiguration, Domain, EndPoint, Subdomain
)
from scanEngine.models import EngineType
from reNgine.parsers import K6Parser, WrkParser, Hping3Parser, LocustParser, TAStressorParser


class StressTestResultModelTest(TestCase):
    """Test enhanced StressTestResult model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.domain = Domain.objects.create(name='example.com')
        self.engine = EngineType.objects.create(engine_name='test_engine')
        self.scan = ScanHistory.objects.create(
            start_scan_date=timezone.now(),
            domain=self.domain,
            scan_type=self.engine,
            initiated_by=self.user
        )

    def test_stress_result_creation(self):
        """Test creating a StressTestResult with extended fields."""
        result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used='k6',
            concurrency_used=50,
            duration='30s',
            total_requests=1500,
            successful_requests=1485,
            failed_requests=15,
            avg_latency_ms=123.45,
            p95_latency_ms=250.5,
            p99_latency_ms=350.2,
            p50_latency_ms=100.0,
            p75_latency_ms=180.0,
            p90_latency_ms=220.0,
            p999_latency_ms=400.0,
            max_requests_per_second=50.5,
            test_status='success',
        )

        self.assertEqual(result.scan_history, self.scan)
        self.assertEqual(result.total_requests, 1500)
        self.assertEqual(result.p99_latency_ms, 350.2)
        self.assertEqual(result.test_status, 'success')

    def test_stress_result_default_values(self):
        """Test that default values are set correctly."""
        result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used='wrk',
        )

        self.assertEqual(result.total_requests, 0)
        self.assertEqual(result.p50_latency_ms, 0.0)
        self.assertEqual(result.endpoints_tested, [])
        self.assertEqual(result.response_code_distribution, {})
        self.assertEqual(result.error_breakdown, {})
        self.assertTrue(isinstance(result.start_time, datetime))

    def test_stress_result_status_choices(self):
        """Test that test_status accepts valid choices."""
        for status in ['success', 'aborted', 'failed', 'running']:
            result = StressTestResult.objects.create(
                scan_history=self.scan,
                tool_used='k6',
                test_status=status
            )
            self.assertEqual(result.test_status, status)


class StressTelemetryPointModelTest(TestCase):
    """Test StressTelemetryPoint model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.domain = Domain.objects.create(name='example.com')
        self.engine = EngineType.objects.create(engine_name='test_engine')
        self.scan = ScanHistory.objects.create(
            start_scan_date=timezone.now(),
            domain=self.domain,
            scan_type=self.engine,
            initiated_by=self.user
        )
        self.stress_result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used='k6',
        )
        self.subdomain = Subdomain.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            name='api.example.com'
        )
        self.endpoint = EndPoint.objects.create(
            scan_history=self.scan,
            subdomain=self.subdomain,
            http_url='https://api.example.com/users'
        )

    def test_telemetry_point_creation(self):
        """Test creating a telemetry point."""
        point = StressTelemetryPoint.objects.create(
            stress_result=self.stress_result,
            endpoint=self.endpoint,
            tool='k6',
            timestamp=timezone.now(),
            latency_ms=125.5,
            throughput=95.2,
            error_rate=0.01,
            tool_specific_metrics={
                'p95_latency': 250,
                'status_codes': {'200': 1000, '500': 5}
            }
        )

        self.assertEqual(point.tool, 'k6')
        self.assertEqual(point.latency_ms, 125.5)
        self.assertEqual(point.throughput, 95.2)
        self.assertIn('p95_latency', point.tool_specific_metrics)

    def test_telemetry_point_null_endpoint(self):
        """Test that endpoint can be null."""
        point = StressTelemetryPoint.objects.create(
            stress_result=self.stress_result,
            tool='wrk',
            timestamp=timezone.now(),
            latency_ms=100.0,
        )

        self.assertIsNone(point.endpoint)
        self.assertEqual(point.tool, 'wrk')


class StressToolConfigurationModelTest(TestCase):
    """Test StressToolConfiguration model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.domain = Domain.objects.create(name='example.com')
        self.engine = EngineType.objects.create(engine_name='test_engine')
        self.scan = ScanHistory.objects.create(
            start_scan_date=timezone.now(),
            domain=self.domain,
            scan_type=self.engine,
            initiated_by=self.user
        )
        self.stress_result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used='k6,wrk',
        )

    def test_tool_configuration_creation(self):
        """Test creating a tool configuration."""
        config = StressToolConfiguration.objects.create(
            stress_result=self.stress_result,
            tool_configs={
                'k6': {
                    'vus': 50,
                    'duration': '30s',
                    'attack_type': 'http_get'
                },
                'wrk': {
                    'threads': 2,
                    'connections': 50,
                    'duration': '30s'
                }
            }
        )

        self.assertEqual(config.stress_result, self.stress_result)
        self.assertEqual(config.tool_configs['k6']['vus'], 50)
        self.assertIn('wrk', config.tool_configs)


class K6ParserTest(TestCase):
    """Test K6Parser enhancements."""

    def setUp(self):
        """Set up parser."""
        self.parser = K6Parser()

    def test_k6_latency_parsing(self):
        """Test parsing k6 latency output."""
        line = "http_req_duration................: avg=123.45ms min=10.23ms med=100.11ms max=500.22ms p(90)=220.33ms p(95)=300.44ms p(99)=450.45ms"
        metrics = self.parser.parse_line(line)

        self.assertEqual(metrics['avg_latency'], 123.45)
        self.assertEqual(metrics['p95_latency'], 300.44)
        self.assertEqual(metrics['p99_latency'], 450.45)

    def test_k6_request_parsing(self):
        """Test parsing k6 request metrics."""
        line = "http_reqs..........................: 1500 125.50/s"
        metrics = self.parser.parse_line(line)

        self.assertEqual(metrics['total_requests'], 1500)
        self.assertEqual(metrics['throughput_rps'], 125.50)

    def test_k6_error_rate_parsing(self):
        """Test parsing k6 error rate."""
        line = "http_req_failed....................: 1.00%"
        metrics = self.parser.parse_line(line)

        self.assertEqual(metrics['error_rate'], 0.01)

    def test_k6_final_metrics(self):
        """Test get_final_metrics() returns standardized output."""
        self.parser.metrics['total_requests'] = 1500
        self.parser.metrics['error_rate'] = 0.01
        self.parser.metrics['avg_latency'] = 123.45

        final = self.parser.get_final_metrics()

        self.assertEqual(final['total_requests'], 1500)
        self.assertEqual(final['successful_requests'], 1485)
        self.assertEqual(final['failed_requests'], 15)
        self.assertEqual(final['avg_latency_ms'], 123.45)


class WrkParserTest(TestCase):
    """Test WrkParser enhancements."""

    def setUp(self):
        """Set up parser."""
        self.parser = WrkParser()

    def test_wrk_latency_parsing(self):
        """Test parsing wrk latency output."""
        line = "Latency   318.27ms   35.96ms 781.98ms   93.08%"
        metrics = self.parser.parse_line(line)

        self.assertEqual(metrics.get('avg_latency'), 318.27)

    def test_wrk_percentile_parsing(self):
        """Test parsing wrk percentiles."""
        line_95 = "     95%   150.34ms"
        line_99 = "     99%   250.12ms"

        self.parser.parse_line(line_95)
        self.parser.parse_line(line_99)

        self.assertEqual(self.parser.metrics['p95_latency'], 150.34)
        self.assertEqual(self.parser.metrics['p99_latency'], 250.12)

    def test_wrk_requests_parsing(self):
        """Test parsing wrk request metrics."""
        line = "6864 requests in 1.00m, 5.46MB read"
        metrics = self.parser.parse_line(line)

        self.assertEqual(metrics.get('total_requests'), 6864)

    def test_wrk_socket_errors(self):
        """Test parsing wrk socket errors."""
        line = "5 socket errors, 3 timeouts"
        self.parser.parse_line(line)

        self.assertEqual(self.parser.metrics['socket_errors'], 5)
        self.assertEqual(self.parser.metrics['timeout_errors'], 3)

    def test_wrk_final_metrics(self):
        """Test get_final_metrics() returns standardized output."""
        self.parser.metrics['total_requests'] = 6864
        self.parser.metrics['socket_errors'] = 5
        self.parser.metrics['timeout_errors'] = 3

        final = self.parser.get_final_metrics()

        self.assertEqual(final['total_requests'], 6864)
        self.assertEqual(final['failed_requests'], 8)
        self.assertEqual(final['successful_requests'], 6856)


class Hping3ParserTest(TestCase):
    """Test Hping3Parser enhancements."""

    def setUp(self):
        """Set up parser."""
        self.parser = Hping3Parser()

    def test_hping3_packet_summary(self):
        """Test parsing hping3 packet summary."""
        line = "100 packets transmitted, 95 packets received, 5.0% packet loss"
        self.parser.parse_line(line)

        self.assertEqual(self.parser.metrics['sent_packets'], 100)
        self.assertEqual(self.parser.metrics['received_packets'], 95)
        self.assertEqual(self.parser.metrics['packet_loss_rate'], 0.05)

    def test_hping3_rtt_parsing(self):
        """Test parsing hping3 RTT values."""
        self.parser.parse_line("len=46 ip=1.2.3.4 flags=SA seq=0 rtt=12.3ms")
        self.parser.parse_line("len=46 ip=1.2.3.4 flags=SA seq=1 rtt=14.5ms")

        self.assertGreater(self.parser.metrics['rtt_avg'], 0)

    def test_hping3_final_metrics(self):
        """Test get_final_metrics() returns standardized output."""
        self.parser.metrics['sent_packets'] = 100
        self.parser.metrics['received_packets'] = 95

        final = self.parser.get_final_metrics()

        self.assertEqual(final['total_requests'], 100)
        self.assertEqual(final['successful_requests'], 95)
        self.assertEqual(final['failed_requests'], 5)


class LocustParserTest(TestCase):
    """Test LocustParser enhancements."""

    def setUp(self):
        """Set up parser."""
        self.parser = LocustParser()

    def test_locust_aggregated_stats(self):
        """Test parsing locust aggregated statistics."""
        header = "Type Name # reqs # fails"
        line = "Aggregated    100    0(0.00%)  |      45      12     120     30   |    2.50    0.00"
        self.parser.parse_line(header)
        self.parser.parse_line(line)

        self.assertEqual(self.parser.metrics.get('total_requests'), 100)
        self.assertEqual(self.parser.metrics.get('error_rate'), 0.0)

    def test_locust_final_metrics(self):
        """Test get_final_metrics() returns standardized output."""
        self.parser.metrics = {
            'total_requests': 100,
            'failed_requests': 0,
            'error_rate': 0.0,
            'throughput_rps': 2.5,
            'avg_latency': 45.0
        }

        final = self.parser.get_final_metrics()

        self.assertEqual(final['total_requests'], 100)
        self.assertEqual(final['failed_requests'], 0)


class TAStressorParserTest(TestCase):
    """Test TAStressorParser enhancements."""

    def setUp(self):
        """Set up parser."""
        self.parser = TAStressorParser()

    def test_stressor_l4_mode(self):
        """Test parsing stressor L4 mode output."""
        line = "PPS: 50000 | BPS: 5000000 | Response Rate: 95%"
        self.parser.parse_line(line)

        self.assertEqual(self.parser.metrics['pps'], 50000.0)
        self.assertEqual(self.parser.metrics['bps'], 5000000.0)
        self.assertEqual(self.parser.metrics['response_rate'], 0.95)
        self.assertEqual(self.parser.metrics['mode'], 'L4')

    def test_stressor_l7_mode(self):
        """Test parsing stressor L7 mode output."""
        line = "RPS: 1000 | Response Rate: 98%"
        self.parser.parse_line(line)

        self.assertEqual(self.parser.metrics['rps'], 1000.0)
        self.assertEqual(self.parser.metrics['response_rate'], 0.98)
        self.assertEqual(self.parser.metrics['mode'], 'L7')

    def test_stressor_final_metrics(self):
        """Test get_final_metrics() returns standardized output."""
        self.parser.metrics['pps'] = 50000.0
        self.parser.metrics['response_rate'] = 0.95
        self.parser.metrics['mode'] = 'L4'

        final = self.parser.get_final_metrics()

        self.assertEqual(final['mode'], 'L4')
        self.assertEqual(final['response_rate'], 0.95)


class StressTestIntegrationTest(TestCase):
    """Integration tests for stress testing data persistence."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.domain = Domain.objects.create(name='example.com')
        self.engine = EngineType.objects.create(engine_name='test_engine')
        self.scan = ScanHistory.objects.create(
            start_scan_date=timezone.now(),
            domain=self.domain,
            scan_type=self.engine,
            initiated_by=self.user
        )
        self.stress_result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used='k6',
            concurrency_used=50,
            duration='30s'
        )

    def test_create_telemetry_points(self):
        """Test creating multiple telemetry points."""
        base_time = timezone.now()

        for i in range(10):
            StressTelemetryPoint.objects.create(
                stress_result=self.stress_result,
                tool='k6',
                timestamp=base_time + timedelta(seconds=i),
                latency_ms=100.0 + i * 5,
                throughput=50.0 + i,
                error_rate=0.01
            )

        points = StressTelemetryPoint.objects.filter(stress_result=self.stress_result)
        self.assertEqual(points.count(), 10)

    def test_percentile_calculation(self):
        """Test that percentiles can be calculated from telemetry points."""
        latencies = [50, 75, 100, 125, 150, 175, 200, 225, 250, 300]
        base_time = timezone.now()

        for i, latency in enumerate(latencies):
            StressTelemetryPoint.objects.create(
                stress_result=self.stress_result,
                tool='k6',
                timestamp=base_time + timedelta(seconds=i),
                latency_ms=latency,
            )

        points = list(
            StressTelemetryPoint.objects.filter(stress_result=self.stress_result)
            .values_list('latency_ms', flat=True)
            .order_by('latency_ms')
        )

        self.assertEqual(len(points), 10)
        self.assertEqual(points[0], 50)
        self.assertEqual(points[-1], 300)

    def test_stress_result_aggregates(self):
        """Test that stress result can store aggregate metrics."""
        self.stress_result.total_requests = 1500
        self.stress_result.successful_requests = 1485
        self.stress_result.failed_requests = 15
        self.stress_result.response_code_distribution = {
            '200': 1485,
            '500': 15
        }
        self.stress_result.error_breakdown = {
            'timeout': 10,
            'connection_reset': 5
        }
        self.stress_result.findings = "High latency detected"
        self.stress_result.recommendations = "Scale infrastructure"
        self.stress_result.save()

        fetched = StressTestResult.objects.get(id=self.stress_result.id)
        self.assertEqual(fetched.total_requests, 1500)
        self.assertIn('200', fetched.response_code_distribution)
        self.assertIn('timeout', fetched.error_breakdown)
