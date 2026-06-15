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


class TestFfufDefaultMatchStatus(TestCase):
    """Bug #4: default match status must include discovery-relevant codes."""

    REQUIRED_CODES = [200, 204, 301, 302, 307, 401, 403, 405]

    def test_default_match_status_includes_discovery_codes(self):
        from reNgine.definitions import FFUF_DEFAULT_MATCH_HTTP_STATUS
        for code in self.REQUIRED_CODES:
            self.assertIn(code, FFUF_DEFAULT_MATCH_HTTP_STATUS,
                          f"HTTP {code} must be in FFUF_DEFAULT_MATCH_HTTP_STATUS")

    def test_no_duplicate_status_codes(self):
        from reNgine.definitions import FFUF_DEFAULT_MATCH_HTTP_STATUS
        self.assertEqual(
            len(FFUF_DEFAULT_MATCH_HTTP_STATUS),
            len(set(FFUF_DEFAULT_MATCH_HTTP_STATUS)),
            "FFUF_DEFAULT_MATCH_HTTP_STATUS must not contain duplicates"
        )


class TestFfufUrlAndHeaderConstruction(TestCase):
    """Bug #5: FUZZ must always follow a /. Bug #6: header values must be single-quoted."""

    BASE_CONFIG = {
        'dir_file_fuzz': {
            'auto_calibration': False,
            'rate_limit': 0,
            'threads': 10,
            'wordlist_name': 'dicc',
            'extensions': [],
            'match_http_status': [200],
            'recursive_level': 0,
            'max_time': 0,
            'stop_on_error': False,
            'follow_redirect': False,
            'timeout': 10,
            'custom_header': [],
        }
    }

    # --- Bug #5: URL path separator ---

    def test_fuzz_keyword_has_leading_slash_when_url_has_no_trailing_slash(self):
        """URLs without trailing slash must get / inserted before FUZZ."""
        captured_cmds = []

        def fake_stream(cmd, **kwargs):
            captured_cmds.append(cmd)
            return iter([])

        config = {'dir_file_fuzz': {**self.BASE_CONFIG['dir_file_fuzz']}}
        proxy = _make_proxy(config)
        ctx = {"urls_override": ["http://example.com/api"]}  # no trailing slash

        def _fake_ensure(task_proxy, func, ctx, description=None):
            return func(ctx=ctx, description=description)

        with patch('reNgine.fuzzing_tasks.ensure_endpoints_crawled_and_execute',
                   side_effect=_fake_ensure), \
             patch('os.path.exists', return_value=False), \
             patch('reNgine.api_tasks.resolve_wordlist_path',
                   side_effect=lambda cfg, path: path), \
             patch('reNgine.fuzzing_tasks.stream_command', side_effect=fake_stream), \
             patch('reNgine.fuzzing_tasks.run_command', return_value=None), \
             patch('reNgine.fuzzing_tasks.DirectoryScan') as mock_ds, \
             patch('reNgine.fuzzing_tasks.Subdomain'), \
             patch('reNgine.fuzzing_tasks.ScanHistory'), \
             patch('reNgine.fuzzing_tasks.Redis'), \
             patch('reNgine.fuzzing_tasks.OpSecManager') as mock_opsec, \
             patch('reNgine.fuzzing_tasks.get_random_proxy', return_value=None), \
             patch('reNgine.fuzzing_tasks._fuzz_target_marker', return_value='/tmp/no_marker'), \
             patch('reNgine.tasks.http_crawl', return_value=None), \
             patch('builtins.open', MagicMock()):
            mock_ds.objects.create.return_value = MagicMock()
            mock_opsec.return_value.apply_stealth = MagicMock(side_effect=lambda t, c, proxy=None: c)
            dir_file_fuzz(proxy, ctx=ctx)

        self.assertTrue(len(captured_cmds) > 0, "stream_command should have been called")
        for cmd in captured_cmds:
            self.assertIn('/FUZZ', cmd,
                          f"FUZZ must be preceded by /. Got: {cmd}")
            self.assertNotIn('apiFUZZ', cmd,
                             f"FUZZ must not be appended directly to path segment. Got: {cmd}")

    # --- Bug #6: Custom header quoting ---

    def test_custom_header_uses_single_quotes(self):
        """Custom headers must be wrapped in single quotes to avoid shell breakage."""
        config = {
            'dir_file_fuzz': {
                **self.BASE_CONFIG['dir_file_fuzz'],
                'custom_header': ['Authorization: Bearer mytoken'],
            }
        }
        result = _prepare(config)
        self.assertIsNotNone(result, "_prepare() must return a dict, not None")
        self.assertIn('ffuf_base_cmd', result, "prepare_only=True must return ffuf_base_cmd key")
        cmd = result['ffuf_base_cmd']
        self.assertIn("-H 'Authorization: Bearer mytoken'", cmd,
                      f"Header must use single quotes. Got: {cmd}")

    def test_custom_header_double_quote_in_value_is_safe(self):
        """A header value containing a double-quote must be safely wrapped in single quotes."""
        config = {
            'dir_file_fuzz': {
                **self.BASE_CONFIG['dir_file_fuzz'],
                'custom_header': ['X-Test: val"ue'],
            }
        }
        result = _prepare(config)
        self.assertIsNotNone(result, "_prepare() must return a dict, not None")
        self.assertIn('ffuf_base_cmd', result, "prepare_only=True must return ffuf_base_cmd key")
        cmd = result['ffuf_base_cmd']
        self.assertIn("-H 'X-Test: val\"ue'", cmd,
                      f"Double-quote inside value must remain inside single quotes. Got: {cmd}")
