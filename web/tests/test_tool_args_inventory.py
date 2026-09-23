"""Tests for tool inventory sync, arg schema cache, and validation."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rolepermissions.roles import assign_role
from unittest.mock import patch

from dashboard.models import Project
from reNgine.definitions import SUCCESS_TASK
from reNgine.tool_args import (
    ToolArgsError,
    parse_help_text,
    validate_tool_args,
    get_or_refresh_schema,
)
from scanEngine.models import EngineType, InstalledExternalTool, ToolArgSchemaCache
from startScan.models import ScanHistory, Subdomain
from targetApp.models import Domain

User = get_user_model()


class ToolArgsParseTests(TestCase):
    def test_parse_help_and_denylist(self):
        help_text = """
Usage:
  nuclei [flags]

Flags:
  -c, --concurrency int         number of templates (default 25)
  -rl, --rate-limit int         max requests per second
  -u, --url string              target URL (denied)
  -update                       update nuclei templates (denied)
  -s, --severity string[]     severities
"""
        schema = parse_help_text(help_text)
        names = {e['name'] for e in schema}
        self.assertIn('concurrency', names)
        self.assertIn('rate-limit', names)
        self.assertIn('severity', names)
        self.assertNotIn('url', names)
        self.assertNotIn('update', names)

    def test_validate_rejects_unknown_and_target(self):
        with self.assertRaises(ToolArgsError):
            validate_tool_args('port_scan', {'not-a-real-flag': 1}, schema_payload={
                'schema': [
                    {'name': 'threads', 'long_flag': '--threads', 'type': 'int', 'takes_value': True},
                ],
            })
        with self.assertRaises(ToolArgsError):
            validate_tool_args('port_scan', {'url': 'https://evil.example'}, schema_payload={
                'schema': [
                    {'name': 'url', 'long_flag': '-u', 'type': 'string', 'takes_value': True},
                ],
            })
        with self.assertRaises(ToolArgsError):
            validate_tool_args('port_scan', {'ports': '80 -host evil.internal'}, schema_payload={
                'schema': [
                    {'name': 'ports', 'long_flag': '-p', 'type': 'string', 'takes_value': True},
                ],
            })

    def test_singular_activity_name_helpers(self):
        from reNgine.task_plan import (
            is_singular_activity_name,
            pipeline_task_name,
            singular_activity_name,
            get_task_tier,
        )
        self.assertEqual(singular_activity_name('port_scan'), 'single_tool_port_scan')
        self.assertEqual(singular_activity_name('single_tool_port_scan'), 'single_tool_port_scan')
        self.assertEqual(pipeline_task_name('single_tool_port_scan'), 'port_scan')
        self.assertEqual(pipeline_task_name('port_scan'), 'port_scan')
        self.assertTrue(is_singular_activity_name('single_tool_waf_detection'))
        self.assertFalse(is_singular_activity_name('waf_detection'))
        self.assertEqual(get_task_tier('single_tool_port_scan'), get_task_tier('port_scan'))

    def test_validate_accepts_known(self):
        result = validate_tool_args('port_scan', {'threads': 10}, schema_payload={
            'schema': [
                {'name': 'threads', 'long_flag': '--threads', 'type': 'int', 'takes_value': True},
            ],
        })
        self.assertEqual(result['sanitized']['threads'], 10)
        self.assertIn('--threads', result['extra_cli_args'])
        self.assertEqual(result['yaml_overlay'].get('threads'), 10)

    def test_ports_string_becomes_list_and_rate_maps_for_naabu(self):
        from reNgine.tool_args import merge_yaml_overlay

        result = validate_tool_args('port_scan', {'ports': '8080,443', 'rate': 150}, schema_payload={
            'schema': [
                {'name': 'ports', 'long_flag': '-p', 'type': 'string', 'takes_value': True},
                {'name': 'rate', 'long_flag': '-rate', 'type': 'int', 'takes_value': True},
            ],
        })
        self.assertEqual(result['yaml_overlay']['ports'], ['8080', '443'])
        self.assertEqual(result['yaml_overlay']['rate'], 150)
        merged = merge_yaml_overlay({}, 'port_scan', {'ports': '80,443', 'rate_limit': 200})
        self.assertEqual(merged['port_scan']['ports'], ['80', '443'])
        self.assertEqual(merged['port_scan']['rate'], 200)

    def test_nuclei_severity_and_dalfox_section_merge(self):
        from reNgine.tool_args import merge_yaml_overlay

        result = validate_tool_args('nuclei_scan', {'severity': 'critical,high'}, schema_payload={
            'schema': [
                {'name': 'severity', 'long_flag': '-s', 'type': 'string', 'takes_value': True},
            ],
        })
        self.assertEqual(result['yaml_overlay']['severities'], ['critical', 'high'])
        merged_n = merge_yaml_overlay({}, 'nuclei_scan', result['yaml_overlay'])
        self.assertEqual(
            merged_n['vulnerability_scan']['nuclei']['severities'],
            ['critical', 'high'],
        )
        merged_d = merge_yaml_overlay({}, 'dalfox_xss_scan', {'threads': 8, 'delay': 100})
        self.assertEqual(merged_d['vulnerability_scan']['dalfox']['threads'], 8)
        self.assertEqual(merged_d['vulnerability_scan']['dalfox']['delay'], 100)
        self.assertNotIn('dalfox_xss_scan', merged_d)

    def test_http_crawl_threads_and_waf_yaml_only(self):
        from reNgine.tool_args import merge_yaml_overlay

        result = validate_tool_args('http_crawl', {'threads': 25}, schema_payload={
            'schema': [
                {'name': 'threads', 'long_flag': '-t', 'type': 'int', 'takes_value': True},
            ],
        })
        self.assertEqual(result['yaml_overlay']['threads'], 25)
        self.assertEqual(result['extra_cli_args'][:2], ['-t', '25'])
        merged = merge_yaml_overlay({}, 'http_crawl', result['yaml_overlay'])
        self.assertEqual(merged['http_crawl']['threads'], 25)

        waf = validate_tool_args('waf_detection', {'enable_http_crawl': True}, schema_payload={
            'schema': [
                {'name': 'enable_http_crawl', 'long_flag': '', 'type': 'bool', 'takes_value': False},
            ],
        })
        self.assertEqual(waf['extra_cli_args'], [])
        self.assertTrue(waf['yaml_overlay']['enable_http_crawl'])
        merged_w = merge_yaml_overlay({}, 'waf_detection', waf['yaml_overlay'])
        self.assertTrue(merged_w['waf_detection']['enable_http_crawl'])


class ToolInventorySyncTests(TestCase):
    def test_sync_marks_missing_and_present(self):
        from reNgine.tool_inventory import sync_installed_tools

        tool = InstalledExternalTool.objects.create(
            name='__missing_tool_xyz__',
            description='x',
            github_url='https://example.com',
            install_command='echo x',
            is_default=True,
        )
        with patch('reNgine.tool_inventory.resolve_binary_path', return_value=None):
            result = sync_installed_tools(probe_versions=False)
        tool.refresh_from_db()
        self.assertFalse(tool.is_present)
        self.assertGreaterEqual(result['missing'], 1)

        with patch('reNgine.tool_inventory.resolve_binary_path', return_value='/usr/local/bin/naabu'):
            with patch('reNgine.tool_inventory.os.path.isfile', return_value=True):
                with patch('reNgine.tool_inventory.probe_version', return_value=('1.2.3', None)):
                    InstalledExternalTool.objects.filter(pk=tool.pk).update(name='naabu')
                    sync_installed_tools(probe_versions=True)
        tool.refresh_from_db()
        self.assertTrue(tool.is_present)
        self.assertEqual(tool.resolved_path, '/usr/local/bin/naabu')
        self.assertEqual(tool.detected_version, '1.2.3')


class ToolArgsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tool-args', password='x')
        assign_role(self.user, 'penetration_tester')
        self.client = APIClient()
        self.client.force_login(self.user)
        self.project = Project.objects.create(
            name='TA', slug='ta-project', insert_date=timezone.now(),
        )
        self.engine = EngineType.objects.create(engine_name='E', yaml_configuration='port_scan: {}\n')
        self.domain = Domain.objects.create(
            name='ta.example.com', project=self.project, insert_date=timezone.now(),
        )
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_type=self.engine,
            scan_status=SUCCESS_TASK,
            start_scan_date=timezone.now(),
            tasks=['port_scan'],
        )
        self.sub = Subdomain.objects.create(
            name='ta.example.com',
            target_domain=self.domain,
            scan_history=self.scan,
        )

    def test_get_args_seed_fallback(self):
        res = self.client.get('/api/action/tool/port_scan/args/')
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body['pipeline_tool'], 'port_scan')
        self.assertTrue(isinstance(body['schema'], list))
        self.assertTrue(len(body['schema']) >= 1)

    @patch('api.tool_run.TemporalClientProvider.get_client')
    @patch('api.tool_run.run_and_close', return_value=None)
    def test_run_with_tool_args(self, _run, _client):
        args_res = self.client.get('/api/action/tool/port_scan/args/')
        self.assertEqual(args_res.status_code, 200, args_res.content)
        schema = args_res.json().get('schema') or []
        int_field = next((f for f in schema if f.get('type') == 'int'), None)
        tool_args = {int_field['name']: 5} if int_field else {}
        res = self.client.post('/api/action/tool/run/', {
            'tool': 'port_scan',
            'asset_type': 'subdomain',
            'asset_id': self.sub.id,
            'scan_history_id': self.scan.id,
            'tool_args': tool_args or None,
        }, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertTrue(body.get('status'))
        if int_field:
            self.assertEqual(body.get('tool_args', {}).get(int_field['name']), 5)

    def test_cache_hit_skips_help_when_version_matches(self):
        ToolArgSchemaCache.objects.create(
            pipeline_tool='port_scan',
            binary_name='naabu',
            version_fingerprint='9.9.9',
            schema=[{'name': 'threads', 'long_flag': '--threads', 'type': 'int', 'takes_value': True}],
            source='help',
            fetched_at=timezone.now(),
        )
        InstalledExternalTool.objects.create(
            name='naabu',
            description='naabu',
            github_url='https://example.com',
            install_command='go install naabu',
            is_default=True,
            is_present=True,
            resolved_path='/usr/local/bin/naabu',
            detected_version='9.9.9',
        )
        with patch('reNgine.tool_args._run_help') as help_mock:
            payload = get_or_refresh_schema('port_scan', force=False)
            help_mock.assert_not_called()
        self.assertEqual(payload['version'], '9.9.9')
        self.assertEqual(payload['schema'][0]['name'], 'threads')
