"""LinkFinder output handling in web_api_discovery: scope and parsing."""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from reNgine.tasks.crawl.api_discovery import _linkfinder_url, _save_linkfinder_results

BASE = 'https://app.example.test/'
SCOPE = 'example.test'


class LinkFinderUrlTests(unittest.TestCase):

    def test_absolute_path_resolves_against_the_page(self) -> None:
        self.assertEqual(_linkfinder_url('/api/users?id=1', BASE, SCOPE), 'https://app.example.test/api/users?id=1')

    def test_protocol_relative_url_takes_the_page_scheme(self) -> None:
        self.assertEqual(_linkfinder_url('//cdn.example.test/x.json', BASE, SCOPE), 'https://cdn.example.test/x.json')

    def test_relative_api_path_is_kept(self) -> None:
        self.assertEqual(_linkfinder_url('api/v2/orders', BASE, SCOPE), 'https://app.example.test/api/v2/orders')
        self.assertEqual(_linkfinder_url('./login.php', BASE, SCOPE), 'https://app.example.test/login.php')

    def test_noise_is_dropped(self) -> None:
        for line in ('application/json', 'text/html', 'dd/mm/yyyy', 'and/or', 'Usage: linkfinder.py', ''):
            with self.subTest(line=line):
                self.assertIsNone(_linkfinder_url(line, BASE, SCOPE))

    def test_other_domains_are_dropped(self) -> None:
        for line in ('https://cdn.vendor.test/lib.js', 'https://example.test.attacker.test/x', 'https://notexample.test/'):
            with self.subTest(line=line):
                self.assertIsNone(_linkfinder_url(line, BASE, SCOPE))

    def test_scope_is_the_scanned_domain_not_its_parent(self) -> None:
        # Scanning the apex must not put every host under its TLD in scope.
        self.assertIsNone(_linkfinder_url('https://other.test/', 'https://example.test/', SCOPE))
        self.assertEqual(_linkfinder_url('https://example.test/a', 'https://example.test/', SCOPE), 'https://example.test/a')

    def test_nothing_is_in_scope_without_a_domain(self) -> None:
        self.assertIsNone(_linkfinder_url('/api', BASE, ''))


@patch('reNgine.tasks.crawl.api_discovery.save_parameter')
@patch('reNgine.tasks.crawl.api_discovery.save_endpoint')
@patch('reNgine.tasks.crawl.api_discovery.save_subdomain')
class SaveLinkFinderResultsTests(unittest.TestCase):

    def _run(self, lines: list[str], subdomain) -> tuple[int, int, int]:
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'lf_app.example.test.txt')
            with open(path, 'w') as fh:
                fh.write('\n'.join(lines) + '\n')
            return _save_linkfinder_results(path, BASE, SCOPE, subdomain, ctx={'scan_history_id': 1})

    def test_new_in_scope_host_is_added_and_owns_its_endpoint(self, mock_sub, mock_ep, mock_param) -> None:
        page_sub = MagicMock()
        page_sub.name = 'app.example.test'
        new_sub = MagicMock()
        mock_sub.return_value = (new_sub, True)
        mock_ep.return_value = (MagicMock(), True)

        counts = self._run(['https://jenkins.example.test/job', '/api?id=1'], page_sub)

        mock_sub.assert_called_once_with('jenkins.example.test', ctx={'scan_history_id': 1})
        self.assertIs(mock_ep.call_args_list[0].kwargs['subdomain'], new_sub)
        self.assertIs(mock_ep.call_args_list[1].kwargs['subdomain'], page_sub)
        self.assertEqual(counts, (2, 1, 1))

    def test_out_of_scope_host_rejected_by_save_subdomain_saves_nothing(self, mock_sub, mock_ep, mock_param) -> None:
        mock_sub.return_value = (None, False)

        counts = self._run(['https://blocked.example.test/a', 'https://blocked.example.test/b'], None)

        mock_sub.assert_called_once()
        mock_ep.assert_not_called()
        self.assertEqual(counts, (0, 0, 0))

    def test_duplicates_and_foreign_hosts_are_skipped(self, mock_sub, mock_ep, mock_param) -> None:
        page_sub = MagicMock()
        page_sub.name = 'app.example.test'
        mock_ep.return_value = (None, False)

        self._run(['/a?x=1', '/a?x=1', 'https://s3.amazonaws.test/bucket'], page_sub)

        mock_sub.assert_not_called()
        mock_ep.assert_called_once()
        mock_param.assert_not_called()
