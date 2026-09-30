"""Tests for the %EXT% wordlist expansion used by ffuf and feroxbuster in dir_file_fuzz."""
import os
import tempfile
import unittest
from pathlib import Path

from django.test import TestCase

from reNgine.tasks.fuzzing import expand_ext_wordlist
from tests.test_ffuf_bugs import _prepare

DICC_LIKE = (
    'admin/\n'
    '/index.%EXT%\n'
    '\n'
    'config.%EXT%.bak\n'
    '/admin/\n'
    '.git/HEAD\n'
    'index.php\n'
)
PLAIN = 'admin\nlogin\nbackup\n'


class _TempDirMixin:
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.out_dir = self.tmp / 'results'

    def _wordlist(self, content: str, name: str = 'words.txt') -> str:
        path = self.tmp / name
        path.write_text(content, encoding='utf-8')
        return str(path)


class TestExpandExtWordlist(_TempDirMixin, unittest.TestCase):

    def _expand(self, content: str, extensions=('.php', '.bak')) -> tuple[str, bool]:
        return expand_ext_wordlist(self._wordlist(content), list(extensions), str(self.out_dir))

    def _lines(self, path: str) -> list[str]:
        return Path(path).read_text(encoding='utf-8').splitlines()

    def test_placeholder_expanded_once_per_extension_without_dot(self):
        path, expanded = self._expand('index.%EXT%\n')
        self.assertTrue(expanded)
        self.assertEqual(self._lines(path), ['index.php', 'index.bak'])

    def test_plain_words_kept_blank_lines_dropped_leading_slash_stripped_deduped(self):
        path, _ = self._expand(DICC_LIKE)
        self.assertEqual(self._lines(path), [
            'admin/',
            'index.php',
            'index.bak',
            'config.php.bak',
            'config.bak.bak',
            '.git/HEAD',
        ])

    def test_written_under_output_dir_without_leftover_part_file(self):
        path, _ = self._expand(DICC_LIKE)
        self.assertEqual(Path(path).parent, self.out_dir)
        self.assertEqual([p.name for p in self.out_dir.iterdir()], [Path(path).name])

    def test_existing_expansion_reused(self):
        wordlist = self._wordlist(DICC_LIKE)
        first, _ = expand_ext_wordlist(wordlist, ['.php'], str(self.out_dir))
        Path(first).write_text('sentinel\n', encoding='utf-8')
        second, expanded = expand_ext_wordlist(wordlist, ['.php'], str(self.out_dir))
        self.assertTrue(expanded)
        self.assertEqual(first, second)
        self.assertEqual(self._lines(second), ['sentinel'])

    def test_different_extensions_get_their_own_file(self):
        wordlist = self._wordlist(DICC_LIKE)
        php, _ = expand_ext_wordlist(wordlist, ['.php'], str(self.out_dir))
        asp, _ = expand_ext_wordlist(wordlist, ['.asp'], str(self.out_dir))
        self.assertNotEqual(php, asp)
        self.assertIn('index.asp', self._lines(asp))

    def test_wordlist_without_placeholder_passes_through(self):
        wordlist = self._wordlist(PLAIN)
        path, expanded = expand_ext_wordlist(wordlist, ['.php'], str(self.out_dir))
        self.assertFalse(expanded)
        self.assertEqual(path, wordlist)
        self.assertFalse(self.out_dir.exists())

    def test_missing_wordlist_passes_through(self):
        missing = str(self.tmp / 'missing.txt')
        self.assertEqual(expand_ext_wordlist(missing, ['.php'], str(self.out_dir)), (missing, False))


class TestDirFileFuzzWordlistCommands(_TempDirMixin, TestCase):

    CONFIG = {
        'dir_file_fuzz': {
            'extensions': ['php', 'bak'],
            'recursive_level': 0,
            'run_dirsearch': True,
            'run_feroxbuster': True,
        }
    }

    def _run(self, content: str, config=None) -> tuple[dict, str]:
        wordlist = self._wordlist(content)
        self.out_dir.mkdir()
        result = _prepare(config or self.CONFIG, wordlist_path=wordlist, results_dir=str(self.out_dir))
        return result, wordlist

    def test_dicc_like_list_ffuf_uses_expanded_list_without_e(self):
        result, wordlist = self._run(DICC_LIKE)
        cmd = result['ffuf_base_cmd']
        self.assertNotIn(f'-w {wordlist}', cmd)
        self.assertIn(f'-w {self.out_dir}{os.sep}ffuf_wordlist_', cmd)
        self.assertNotIn(' -e ', cmd)

    def test_dicc_like_list_dirsearch_keeps_original_list_and_e(self):
        result, wordlist = self._run(DICC_LIKE)
        cmd = result['dirsearch_base_cmd']
        self.assertIn(f'-w {wordlist}', cmd)
        self.assertIn(' -e php,bak', cmd)

    def test_dicc_like_list_feroxbuster_uses_expanded_list_without_extensions(self):
        result, _ = self._run(DICC_LIKE)
        cmd = result['ferox_base_cmd']
        self.assertIn(f'--wordlist {self.out_dir}{os.sep}ffuf_wordlist_', cmd)
        self.assertNotIn('--extensions', cmd)

    def test_plain_list_keeps_extension_flags(self):
        result, wordlist = self._run(PLAIN)
        self.assertIn(f'-w {wordlist} -e .php,.bak', result['ffuf_base_cmd'])
        self.assertIn('--extensions .php,.bak', result['ferox_base_cmd'])
        self.assertIn(f'-w {wordlist}', result['dirsearch_base_cmd'])

    def test_dirsearch_off_when_key_absent(self):
        config = {'dir_file_fuzz': {'extensions': ['php'], 'recursive_level': 0}}
        result, _ = self._run(PLAIN, config)
        self.assertIsNone(result['dirsearch_base_cmd'])
        self.assertTrue(result['ffuf_base_cmd'].startswith('ffuf '))
