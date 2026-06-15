"""
Tests for ffuf rate-limiting bugs:
  Bug #1 — fuzzing_tasks.py used -p (per-thread delay) instead of -rate N
  Bug #2 — opsec.py _apply_ffuf appended a second -p flag
"""
import types
from unittest.mock import MagicMock, patch

from django.test import TestCase

from reNgine.fuzzing_tasks import dir_file_fuzz


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_proxy(yaml_config=None):
    """Minimal scan proxy for prepare_only=True tests."""
    proxy = types.SimpleNamespace(
        yaml_configuration=yaml_config or {},
        results_dir='/tmp/test_ffuf',
        scan=MagicMock(),
        scan_id=1,
        activity_id=1,
        history_file='/tmp/test_ffuf_history.txt',
        subscan=None,
    )
    return proxy


def _prepare(yaml_config, ctx_override=None):
    """Call dir_file_fuzz with prepare_only=True, returning the built command dict."""
    proxy = _make_proxy(yaml_config)
    ctx = {"urls_override": ctx_override or ["http://example.com/"]}

    def _fake_ensure(task_proxy, func, ctx, description=None):
        return func(ctx=ctx, description=description)

    with patch('reNgine.fuzzing_tasks.ensure_endpoints_crawled_and_execute',
               side_effect=_fake_ensure), \
         patch('os.path.exists', return_value=True), \
         patch('reNgine.api_tasks.resolve_wordlist_path',
               side_effect=lambda cfg, path: path):
        return dir_file_fuzz(proxy, ctx=ctx, prepare_only=True)


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestFfufRateLimiting(TestCase):
    """Bug #1 + #2: rate limiting uses -p (wrong) instead of -rate (correct)."""

    BASE_CONFIG = {
        'dir_file_fuzz': {
            'auto_calibration': False,
            'rate_limit': 150,
            'threads': 30,
            'wordlist_name': 'dicc',
            'extensions': [],
            'match_http_status': [200],
            'recursive_level': 0,
            'max_time': 0,
            'stop_on_error': False,
            'follow_redirect': False,
            'timeout': 10,
        }
    }

    def test_ffuf_base_cmd_uses_rate_flag(self):
        result = _prepare(self.BASE_CONFIG)
        self.assertIsNotNone(result, "_prepare() must return a dict, not None")
        self.assertIn('ffuf_base_cmd', result, "prepare_only=True must return ffuf_base_cmd key")
        cmd = result['ffuf_base_cmd']
        self.assertIn('-rate 150', cmd,
                      "ffuf base command must use -rate, not -p")

    def test_ffuf_base_cmd_no_p_flag(self):
        result = _prepare(self.BASE_CONFIG)
        self.assertIsNotNone(result, "_prepare() must return a dict, not None")
        self.assertIn('ffuf_base_cmd', result, "prepare_only=True must return ffuf_base_cmd key")
        cmd = result['ffuf_base_cmd']
        self.assertNotIn(' -p ', cmd,
                         f"ffuf command must not contain -p flag, got: {cmd}")
        self.assertFalse(cmd.endswith(' -p'),
                         f"ffuf command must not end with -p flag, got: {cmd}")

    def test_opsec_apply_ffuf_uses_rate_not_p(self):
        from reNgine.utils.opsec import OpSecManager
        opsec = OpSecManager.__new__(OpSecManager)
        opsec.settings = MagicMock()
        opsec.settings.enable_random_ua = False
        opsec.settings.enable_rate_limit = True
        opsec.settings.max_rps = 150
        opsec.get_random_ua = MagicMock(return_value='UA')

        cmd = 'ffuf -w /usr/src/wordlist/dicc.txt -u http://example.com/FUZZ -json'
        result = opsec._apply_ffuf(cmd)
        self.assertIn('-rate 150', result)
        self.assertNotIn(' -p ', result)

    def test_opsec_apply_ffuf_no_duplicate_rate(self):
        """If -rate already exists in cmd, opsec must not add a second one."""
        from reNgine.utils.opsec import OpSecManager
        opsec = OpSecManager.__new__(OpSecManager)
        opsec.settings = MagicMock()
        opsec.settings.enable_random_ua = False
        opsec.settings.enable_rate_limit = True
        opsec.settings.max_rps = 150
        opsec.get_random_ua = MagicMock(return_value='UA')

        cmd = 'ffuf -w /usr/src/wordlist/dicc.txt -rate 150 -u http://example.com/FUZZ -json'
        result = opsec._apply_ffuf(cmd)
        self.assertEqual(result.count('-rate'), 1,
                         "opsec must not add a second -rate flag")


class TestFfufAcMcConflict(TestCase):
    """Bug #3: -ac and -mc must not both appear in the same command."""

    def _config(self, auto_calibration, match_statuses=None):
        return {
            'dir_file_fuzz': {
                'auto_calibration': auto_calibration,
                'rate_limit': 0,
                'threads': 10,
                'wordlist_name': 'dicc',
                'extensions': [],
                'match_http_status': match_statuses if match_statuses is not None else [200, 204],
                'recursive_level': 0,
                'max_time': 0,
                'stop_on_error': False,
                'follow_redirect': False,
                'timeout': 10,
            }
        }

    def test_auto_calibration_true_omits_mc(self):
        result = _prepare(self._config(auto_calibration=True))
        self.assertIsNotNone(result, "_prepare() must return a dict, not None")
        self.assertIn('ffuf_base_cmd', result, "prepare_only=True must return ffuf_base_cmd key")
        cmd = result['ffuf_base_cmd']
        self.assertIn('-ac', cmd)
        self.assertNotIn('-mc', cmd,
                         "When auto_calibration=True, -mc must be omitted")

    def test_auto_calibration_false_adds_mc(self):
        result = _prepare(self._config(auto_calibration=False))
        self.assertIsNotNone(result, "_prepare() must return a dict, not None")
        self.assertIn('ffuf_base_cmd', result, "prepare_only=True must return ffuf_base_cmd key")
        cmd = result['ffuf_base_cmd']
        self.assertNotIn('-ac', cmd)
        self.assertIn('-mc 200,204', cmd,
                      "When auto_calibration=False, -mc must be present")

    def test_auto_calibration_true_never_has_both(self):
        result = _prepare(self._config(auto_calibration=True, match_statuses=[200, 301, 403]))
        self.assertIsNotNone(result, "_prepare() must return a dict, not None")
        self.assertIn('ffuf_base_cmd', result, "prepare_only=True must return ffuf_base_cmd key")
        cmd = result['ffuf_base_cmd']
        self.assertFalse('-ac' in cmd and '-mc' in cmd,
                         "Command must never contain both -ac and -mc")
