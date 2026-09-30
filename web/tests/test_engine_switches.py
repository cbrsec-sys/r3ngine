"""Engine YAML switches the editor writes, and the backend steps they gate."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from reNgine.task_plan import build_scan_task_plan
from reNgine.tasks.osint.pipeline import post_crawl_osint
from scanEngine.models import EngineType


def _planned(tasks: list, yaml_configuration: dict) -> set:
    return {entry['name'] for entry in build_scan_task_plan(tasks, yaml_configuration)}


class CredSpyTaskTests(unittest.TestCase):

    def test_credspy_under_osint_schedules_the_post_crawl_step(self) -> None:
        engine = EngineType(engine_name='t', yaml_configuration='osint:\n  credspy: true\n')
        self.assertIn('post_crawl_osint', engine.tasks)

    def test_without_credspy_nothing_is_added(self) -> None:
        engine = EngineType(engine_name='t', yaml_configuration='osint:\n  credspy: false\n')
        self.assertNotIn('post_crawl_osint', engine.tasks)

    @patch('reNgine.tasks.osint.pipeline.get_opsec_manager')
    @patch('reNgine.osint.credspy.run_credspy')
    def test_post_crawl_step_runs_credspy_without_its_own_section(self, mock_credspy, _opsec) -> None:
        task = SimpleNamespace(
            yaml_configuration={'osint': {'credspy': True}},
            domain=SimpleNamespace(name='example.test'),
            scan=MagicMock(),
            scan_id=1,
            results_dir='/tmp/unused',
        )
        post_crawl_osint(task)
        mock_credspy.assert_called_once()

    @patch('reNgine.tasks.osint.pipeline.get_opsec_manager')
    @patch('reNgine.osint.credspy.run_credspy')
    def test_post_crawl_step_skips_when_nothing_is_on(self, mock_credspy, mock_opsec) -> None:
        task = SimpleNamespace(yaml_configuration={}, domain=None, scan=None, scan_id=1, results_dir='/tmp/unused')
        self.assertTrue(post_crawl_osint(task))
        mock_credspy.assert_not_called()
        mock_opsec.assert_not_called()


class AttackPathPlanTests(unittest.TestCase):

    def test_apme_is_planned_by_default(self) -> None:
        self.assertIn('run_apme', _planned(['subdomain_discovery'], {}))

    def test_apme_is_not_planned_when_switched_off(self) -> None:
        conf = {'attack_path_modeling': {'enabled': False}}
        self.assertNotIn('run_apme', _planned(['subdomain_discovery', 'attack_path_modeling'], conf))
