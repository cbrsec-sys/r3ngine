"""
Integration tests for Phase 2 - Enhanced Stress Report Generation.
Tests report builder, chart generation, and full PDF report pipeline.
"""
import os
import json
from datetime import datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from startScan.models import (
    ScanHistory, Domain, StressTestResult, StressTelemetryPoint,
    StressToolConfiguration, EndPoint, ScanReport
)
from scanEngine.models import EngineType
from reNgine.stress.report_builder import StressReportBuilder
from reNgine.charts import (
    generate_stress_latency_distribution_chart,
    generate_stress_response_code_chart,
    generate_stress_error_breakdown_chart,
    generate_stress_endpoint_heatmap
)


class StressReportBuilderTestCase(TestCase):
    """Test the StressReportBuilder class."""

    def setUp(self):
        """Create test data."""
        self.user = User.objects.create_user(username='testuser', password='pass123')

        self.domain = Domain.objects.create(
            name='example.com',
            description='Test domain'
        )

        self.engine = EngineType.objects.create(engine_name='quick_scan')
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=datetime.now(),
            scan_status=2,
            initiated_by=self.user
        )

        self.stress_result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used='k6',
            concurrency_used=50,
            duration='30s',
            total_requests=10000,
            successful_requests=9800,
            failed_requests=200,
            avg_latency_ms=150.5,
            p50_latency_ms=100.0,
            p75_latency_ms=120.0,
            p90_latency_ms=180.0,
            p95_latency_ms=250.0,
            p99_latency_ms=500.0,
            p999_latency_ms=750.0,
            max_requests_per_second=500.0,
            peak_throughput_rps=450.0,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=30),
            endpoints_tested=['http://example.com/', 'http://example.com/api'],
            response_code_distribution={
                '200': 8000,
                '301': 500,
                '404': 1000,
                '500': 200,
            },
            error_breakdown={
                'timeout': 100,
                'connection_refused': 50,
                'tls_error': 30,
            },
            max_concurrent_connections=50,
            test_status='success',
            findings='Latency variance detected. P99 is 3.3x higher than average.',
            anomalies_detected=['high_p99_latency', 'elevated_error_rate'],
            recommendations='Implement caching. Optimize database queries. Scale application servers.',
            is_kill_switch_triggered=False
        )

        self.tool_config = StressToolConfiguration.objects.create(
            stress_result=self.stress_result,
            tool_configs={
                'vus': 50,
                'duration': '30s',
                'rps': None,
                'timeout': '30s'
            }
        )

        # Create telemetry points
        for i in range(10):
            StressTelemetryPoint.objects.create(
                stress_result=self.stress_result,
                tool='k6',
                timestamp=datetime.now() + timedelta(seconds=i*3),
                latency_ms=150.0 + (i * 10),
                throughput=450.0 - (i * 5),
                error_rate=0.02,
                request_count=1000 + (i * 100),
                error_count=20 + (i * 2),
                tool_specific_metrics={
                    'rps': 450.0 - (i * 5),
                    'error_count': 20 + (i * 2),
                }
            )

    def test_stress_report_builder_initialization(self):
        """Test that builder initializes with stress result."""
        builder = StressReportBuilder(self.stress_result)
        self.assertIsNotNone(builder)
        self.assertEqual(builder.stress_result, self.stress_result)

    def test_build_test_metadata(self):
        """Test building test metadata section."""
        builder = StressReportBuilder(self.stress_result)
        metadata = builder._build_test_metadata()

        self.assertEqual(metadata['tool_used'], 'k6')
        self.assertEqual(metadata['tool_display_name'], 'K6')
        self.assertEqual(metadata['concurrency_level'], 50)
        self.assertEqual(metadata['endpoints_tested_count'], 2)
        self.assertEqual(metadata['duration'], '30s')

    def test_build_performance_summary(self):
        """Test building performance summary KPI cards."""
        builder = StressReportBuilder(self.stress_result)
        summary = builder._build_performance_summary()

        self.assertEqual(summary['total_requests'], 10000)
        self.assertEqual(summary['successful_requests'], 9800)
        self.assertEqual(summary['failed_requests'], 200)
        self.assertAlmostEqual(summary['success_rate_percent'], 98.0)
        self.assertAlmostEqual(summary['error_rate_percent'], 2.0)
        self.assertEqual(summary['avg_latency_ms'], 150.5)

    def test_build_tool_specific_section(self):
        """Test building tool-specific section."""
        builder = StressReportBuilder(self.stress_result)
        tool_section = builder._build_tool_specific_section('k6', [])

        self.assertEqual(tool_section['tool'], 'k6')
        self.assertIn('k6_specific', tool_section)
        self.assertIn('status_code_distribution', tool_section['k6_specific'])
        self.assertIn('error_breakdown', tool_section['k6_specific'])

    def test_build_endpoint_analysis(self):
        """Test building endpoint analysis section."""
        builder = StressReportBuilder(self.stress_result)
        endpoint_analysis = builder._build_endpoint_analysis()

        self.assertEqual(endpoint_analysis['endpoint_count'], 2)
        self.assertEqual(len(endpoint_analysis['endpoints']), 2)

    def test_build_findings_and_recommendations(self):
        """Test building findings and recommendations section."""
        builder = StressReportBuilder(self.stress_result)
        findings = builder._build_findings_recommendations()

        self.assertIn('findings', findings)
        self.assertIn('anomalies', findings)
        self.assertIn('recommendations', findings)
        self.assertEqual(len(findings['findings_list']), 1)
        self.assertEqual(len(findings['anomalies']), 2)

    def test_build_timeline_data(self):
        """Test building timeline/time-series data."""
        builder = StressReportBuilder(self.stress_result)
        timeline = builder._build_timeline_data()

        self.assertIn('latency_over_time', timeline)
        self.assertIn('throughput_over_time', timeline)
        self.assertIn('error_rate_over_time', timeline)
        self.assertGreater(len(timeline['latency_over_time']), 0)

    def test_build_full_context(self):
        """Test building complete report context."""
        builder = StressReportBuilder(self.stress_result)
        context = builder.build()

        required_keys = [
            'test_metadata', 'performance_summary', 'tool_sections',
            'endpoint_analysis', 'findings_and_recommendations', 'timeline_data'
        ]
        for key in required_keys:
            self.assertIn(key, context)


class StressChartGenerationTestCase(TestCase):
    """Test chart generation functions."""

    def setUp(self):
        """Create test data."""
        self.domain = Domain.objects.create(name='example.com')
        self.engine = EngineType.objects.create(engine_name='quick_scan')
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=datetime.now()
        )

        self.stress_result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used='k6',
            concurrency_used=50,
            duration='30s',
            total_requests=10000,
            successful_requests=9800,
            failed_requests=200,
            avg_latency_ms=150.0,
            p50_latency_ms=100.0,
            p75_latency_ms=120.0,
            p90_latency_ms=180.0,
            p95_latency_ms=250.0,
            p99_latency_ms=500.0,
            p999_latency_ms=750.0,
            max_requests_per_second=500.0,
            peak_throughput_rps=450.0,
            endpoints_tested=['http://example.com/'],
            response_code_distribution={
                '200': 8000,
                '301': 500,
                '404': 1000,
                '500': 200,
            },
            error_breakdown={
                'timeout': 100,
                'connection_refused': 50,
            },
            test_status='success'
        )

    def test_latency_distribution_chart_generation(self):
        """Test that latency distribution chart generates base64 PNG."""
        chart_base64 = generate_stress_latency_distribution_chart(self.stress_result)
        self.assertIsNotNone(chart_base64)
        self.assertIsInstance(chart_base64, str)
        self.assertTrue(chart_base64.startswith('iVBOR'))  # PNG magic number in base64

    def test_response_code_chart_generation(self):
        """Test that response code chart generates base64 PNG."""
        chart_base64 = generate_stress_response_code_chart(self.stress_result.response_code_distribution)
        self.assertIsNotNone(chart_base64)
        self.assertIsInstance(chart_base64, str)
        self.assertTrue(chart_base64.startswith('iVBOR'))

    def test_error_breakdown_chart_generation(self):
        """Test that error breakdown chart generates base64 PNG."""
        chart_base64 = generate_stress_error_breakdown_chart(self.stress_result.error_breakdown)
        self.assertIsNotNone(chart_base64)
        self.assertIsInstance(chart_base64, str)
        self.assertTrue(chart_base64.startswith('iVBOR'))

    def test_endpoint_heatmap_generation(self):
        """Test that endpoint heatmap generates base64 PNG."""
        chart_base64 = generate_stress_endpoint_heatmap(
            self.stress_result.endpoints_tested,
            self.stress_result.response_code_distribution
        )
        self.assertIsNotNone(chart_base64)
        self.assertIsInstance(chart_base64, str)
        self.assertTrue(chart_base64.startswith('iVBOR'))

    def test_chart_with_empty_data(self):
        """Test chart generation with empty data returns None gracefully."""
        result = generate_stress_response_code_chart({})
        self.assertIsNone(result)

        result = generate_stress_error_breakdown_chart({})
        self.assertIsNone(result)

        result = generate_stress_endpoint_heatmap([], {})
        self.assertIsNone(result)


class StressReportGenerationAPITestCase(TestCase):
    """Test the stress report generation API endpoint."""

    def setUp(self):
        """Create test data and client."""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.domain = Domain.objects.create(name='example.com')
        self.engine = EngineType.objects.create(engine_name='quick_scan')
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=datetime.now(),
            initiated_by=self.user
        )

        self.stress_result = StressTestResult.objects.create(
            scan_history=self.scan,
            target_domain=self.domain,
            tool_used='k6',
            concurrency_used=50,
            duration='30s',
            total_requests=10000,
            successful_requests=9800,
            failed_requests=200,
            avg_latency_ms=150.0,
            p50_latency_ms=100.0,
            p75_latency_ms=120.0,
            p90_latency_ms=180.0,
            p95_latency_ms=250.0,
            p99_latency_ms=500.0,
            p999_latency_ms=750.0,
            max_requests_per_second=500.0,
            endpoints_tested=['http://example.com/'],
            response_code_distribution={'200': 8000, '404': 1000},
            error_breakdown={},
            test_status='success'
        )

    def test_stress_report_api_initiation(self):
        """Test that report generation API initiates correctly."""
        self.client.force_login(self.user)

        response = self.client.post(
            f'/api/stress/{self.scan.id}/report/',
            data={
                'report_template': 'stress_modern',
                'include_endpoints': True,
                'include_timeline': True
            },
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertTrue(data['status'])
        self.assertIn('report_id', data)

    def test_stress_report_api_status_check(self):
        """Test that report status can be checked."""
        self.client.force_login(self.user)

        # Create a report
        report = ScanReport.objects.create(
            scan_history=self.scan,
            report_type='stress_test',
            report_template='stress_modern',
            status=-1
        )

        # Check status
        response = self.client.get(
            f'/api/stress/{self.scan.id}/report/',
            {'report_id': report.id}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], -1)


class StressReportTemplateTestCase(TestCase):
    """Test that stress report templates render without errors."""

    def test_stress_modern_template_context(self):
        """Test that stress_modern template has required context."""
        from django.template import Template, Context

        domain = Domain.objects.create(name='example.com')
        engine = EngineType.objects.create(engine_name='quick_scan')
        scan = ScanHistory.objects.create(
            domain=domain,
            scan_type=engine,
            start_scan_date=datetime.now()
        )

        stress_result = StressTestResult.objects.create(
            scan_history=scan,
            target_domain=domain,
            tool_used='k6',
            concurrency_used=50,
            total_requests=10000,
            successful_requests=9800,
            failed_requests=200,
            avg_latency_ms=150.0,
            p95_latency_ms=250.0,
            p99_latency_ms=500.0,
            max_requests_per_second=500.0,
            test_status='success'
        )

        builder = StressReportBuilder(stress_result)
        context = builder.build()

        # Verify all required context keys for template
        self.assertIn('test_metadata', context)
        self.assertIn('performance_summary', context)
        self.assertIn('tool_sections', context)

    def test_stress_cyber_pro_template_context(self):
        """Test that stress_cyber_pro template has required context."""
        domain = Domain.objects.create(name='example.com')
        engine = EngineType.objects.create(engine_name='quick_scan')
        scan = ScanHistory.objects.create(
            domain=domain,
            scan_type=engine,
            start_scan_date=datetime.now()
        )

        stress_result = StressTestResult.objects.create(
            scan_history=scan,
            target_domain=domain,
            tool_used='wrk',
            concurrency_used=100,
            total_requests=50000,
            successful_requests=49000,
            failed_requests=1000,
            avg_latency_ms=200.0,
            p95_latency_ms=350.0,
            p99_latency_ms=600.0,
            max_requests_per_second=1000.0,
            test_status='success'
        )

        builder = StressReportBuilder(stress_result)
        context = builder.build()

        # Verify template context
        self.assertIn('test_metadata', context)
        self.assertIsInstance(context['performance_summary'], dict)
