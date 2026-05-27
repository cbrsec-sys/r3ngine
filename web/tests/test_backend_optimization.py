import os
import unittest
import json
import base64
from unittest.mock import patch, MagicMock
from django.test import TransactionTestCase
from django.utils import timezone

# Import tasks and their underlying functions
from reNgine.tasks import nuclei_scan, amass_intel_discovery, dir_file_fuzz
from reNgine.tech_mapping import get_nuclei_tags_from_techs
from startScan.models import ScanHistory, Subdomain, Technology, DirectoryFile, EndPoint, DirectoryScan
from targetApp.models import Domain
from scanEngine.models import EngineType, OpSec, Proxy

class BackendOptimizationTest(TransactionTestCase):
    def setUp(self):
        self.domain_name = "test-optimization.io"
        self.domain = Domain.objects.create(name=self.domain_name)
        self.engine = EngineType.objects.create(engine_name="Optimization Test Engine")
        
        # Ensure OpSec and Proxy exist
        OpSec.objects.get_or_create(id=1)
        Proxy.objects.get_or_create(id=1)
        
        self.scan = ScanHistory.objects.create(
            domain=self.domain,
            scan_status=1,
            start_scan_date=timezone.now(),
            scan_type=self.engine
        )
        self.results_dir = f"/tmp/rengine_results/{self.scan.id}"
        os.makedirs(self.results_dir, exist_ok=True)
        self.scan.results_dir = self.results_dir
        self.scan.save()
        
        self.subdomain = Subdomain.objects.create(
            name=self.domain_name,
            scan_history=self.scan,
            target_domain=self.domain
        )
        
        self.ctx = {
            'scan_history_id': self.scan.id,
            'domain_id': self.domain.id,
            'results_dir': self.results_dir,
            'yaml_configuration': {
                'vulnerability_scan': {
                    'nuclei': {
                        'severities': ['critical'],
                        'tags': ['cve']
                    }
                }
            }
        }

    def test_tech_mapping_logic(self):
        """Test that technology mapping returns correct Nuclei tags."""
        techs = ['WordPress', 'Nginx', 'PHP']
        tags = get_nuclei_tags_from_techs(techs)
        self.assertIn('wordpress', tags)
        self.assertIn('nginx', tags)
        self.assertIn('php', tags)

    @patch('reNgine.tasks.get_http_urls')
    @patch('reNgine.tasks.Subdomain.objects.filter')
    @patch('reNgine.tasks.chord')
    @patch('reNgine.tasks.nuclei_individual_severity_module')
    @patch('reNgine.tasks.run_command')
    def test_nuclei_tag_injection(self, mock_run_cmd, mock_nuclei_module, mock_chord, mock_subdomain_filter, mock_get_urls):
        """Test that nuclei_scan correctly injects tags based on discovered technologies."""
        mock_sub = MagicMock()
        mock_sub.name = self.domain_name
        mock_sub.technologies.values_list.return_value = ['WordPress', 'Nginx']
        mock_subdomain_filter.return_value = [mock_sub]
        
        def get_urls_side_effect(write_filepath=None, **kwargs):
            if write_filepath:
                os.makedirs(os.path.dirname(write_filepath), exist_ok=True)
                with open(write_filepath, 'w') as f:
                    f.write(f"http://{self.domain_name}\n")
            return [f"http://{self.domain_name}"]
        mock_get_urls.side_effect = get_urls_side_effect
        
        task_instance = MagicMock()
        task_instance.scan = self.scan
        task_instance.scan_id = self.scan.id
        task_instance.results_dir = self.results_dir
        task_instance.yaml_configuration = self.ctx['yaml_configuration']
        
        actual_func = getattr(nuclei_scan.run, '__func__', getattr(nuclei_scan, '__wrapped__', nuclei_scan))
        # Signature: (self, urls=[], ctx={}, description=None)
        actual_func(task_instance, [f"http://{self.domain_name}"], self.ctx)
        
        self.assertTrue(mock_nuclei_module.apply.called)
        kwargs = mock_nuclei_module.apply.call_args[1]['kwargs']
        cmd = kwargs['cmd']
        self.assertIn('-tags', cmd)
        self.assertIn('wordpress', cmd)

    @patch('reNgine.fuzzing_tasks.Redis')
    @patch('reNgine.fuzzing_tasks.get_http_urls')
    @patch('reNgine.common_func.get_http_urls')
    @patch('reNgine.fuzzing_tasks.stream_command')
    @patch('reNgine.fuzzing_tasks.run_command')
    def test_dir_file_fuzz_deduplication(self, mock_run, mock_stream, mock_get_urls_common, mock_get_urls_fuzz, mock_redis_cls):
        """Test that dir_file_fuzz correctly merges and deduplicates results from ffuf and dirsearch."""
        mock_redis = MagicMock()
        mock_redis_cls.from_url.return_value = mock_redis
        mock_redis.lock.return_value.__enter__.return_value = True
        
        mock_get_urls_fuzz.return_value = [f"http://{self.domain_name}"]
        mock_get_urls_common.return_value = [f"http://{self.domain_name}"]
        
        ffuf_output = [
            {"url": f"http://{self.domain_name}/admin", "status": 200, "length": 1234},
            {"url": f"http://{self.domain_name}/login", "status": 200, "length": 567}
        ]
        
        dirsearch_results = {
            "results": [
                {"url": f"http://{self.domain_name}/admin", "status": 200, "content-length": 1234},
                {"url": f"http://{self.domain_name}/new-page", "status": 200, "content-length": 888}
            ]
        }
        
        def stream_side_effect(cmd, *args, **kwargs):
            if 'ffuf' in cmd:
                for item in ffuf_output:
                    yield item
            else:
                yield "Done"
        
        def run_side_effect(cmd, *args, **kwargs):
            if 'dirsearch' in cmd:
                import re
                match = re.search(r'-o\s+([^\s]+)', cmd)
                if match:
                    output_file = match.group(1)
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, 'w') as f:
                        json.dump(dirsearch_results, f)
        
        mock_stream.side_effect = stream_side_effect
        mock_run.side_effect = run_side_effect
        
        actual_func = getattr(dir_file_fuzz.run, '__func__', getattr(dir_file_fuzz, '__wrapped__', dir_file_fuzz))
        
        task_instance = MagicMock()
        task_instance.scan = self.scan
        task_instance.scan_id = self.scan.id
        task_instance.results_dir = self.results_dir
        task_instance.history_file = "/tmp/history.txt"
        task_instance.subscan = None
        task_instance.yaml_configuration = {
            'fuzzing': {
                'ffuf': True,
                'dirsearch': True
            }
        }
        
        # Signature: (self, ctx={}, description=None)
        actual_func(task_instance, self.ctx)
        
        df_count = DirectoryFile.objects.all().count()
        self.assertEqual(df_count, 3)

    @patch('reNgine.tasks.run_command')
    def test_amass_intel_discovery(self, mock_run):
        """Test that amass_intel_discovery runs and attempts to save results."""
        output_file = f"{self.results_dir}/amass_intel.txt"
        
        def run_side_effect(cmd, *args, **kwargs):
            if 'amass intel' in cmd:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w') as f:
                    f.write("associated-domain.com\n")
        
        mock_run.side_effect = run_side_effect
        
        actual_func = getattr(amass_intel_discovery.run, '__func__', getattr(amass_intel_discovery, '__wrapped__', amass_intel_discovery))
        
        task_instance = MagicMock()
        task_instance.scan = self.scan
        task_instance.scan_id = self.scan.id
        task_instance.domain = self.domain
        task_instance.results_dir = self.results_dir
        task_instance.yaml_configuration = {}
        
        # Signature: (self, host, ctx={}, description=None)
        actual_func(task_instance, self.domain_name, self.ctx)
        
        self.assertTrue(mock_run.called)
