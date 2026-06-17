from unittest import TestCase
from unittest.mock import patch
from reNgine.nuclei_batch_utils import count_templates_for_tag, build_tag_batches


class TestBuildTagBatches(TestCase):
    def test_empty_tags_returns_empty(self):
        result = build_tag_batches([], {})
        self.assertEqual(result, [])

    def test_all_tags_under_threshold_is_one_batch(self):
        tags = ['apache', 'nginx']
        counts = {'apache': 30, 'nginx': 40}
        result = build_tag_batches(tags, counts, max_per_batch=100)
        self.assertEqual(len(result), 1)
        self.assertIn('apache', result[0])
        self.assertIn('nginx', result[0])

    def test_tags_split_when_cumulative_count_exceeds_threshold(self):
        tags = ['apache', 'wordpress']
        counts = {'apache': 30, 'wordpress': 500}
        result = build_tag_batches(tags, counts, max_per_batch=100)
        self.assertGreater(len(result), 1)
        # Every tag must appear in exactly one batch
        flat = [t for batch in result for t in batch]
        self.assertEqual(sorted(flat), sorted(tags))

    def test_single_tag_exceeding_limit_gets_own_batch(self):
        # Tags that individually exceed the limit still get one batch (we don't split at file level)
        tags = ['wordpress']
        counts = {'wordpress': 2000}
        result = build_tag_batches(tags, counts, max_per_batch=100)
        self.assertEqual(result, [['wordpress']])

    def test_no_batch_exceeds_max_per_batch(self):
        tags = ['a', 'b', 'c', 'd', 'e', 'f']
        counts = {'a': 60, 'b': 50, 'c': 30, 'd': 25, 'e': 80, 'f': 10}
        result = build_tag_batches(tags, counts, max_per_batch=100)
        for batch in result:
            total = sum(counts[t] for t in batch)
            self.assertLessEqual(
                total, 100,
                msg=f"Batch {batch} total {total} exceeds max_per_batch=100",
            )

    def test_unknown_tags_default_to_zero_cost(self):
        tags = ['raretag']
        result = build_tag_batches(tags, {}, max_per_batch=100)
        self.assertEqual(result, [['raretag']])

    def test_all_tags_appear_across_batches(self):
        tags = ['a', 'b', 'c', 'd', 'e']
        counts = {t: 90 for t in tags}
        result = build_tag_batches(tags, counts, max_per_batch=100)
        flat = sorted(t for batch in result for t in batch)
        self.assertEqual(flat, sorted(tags))

    def test_two_small_tags_grouped_in_one_batch(self):
        tags = ['nginx', 'apache']
        counts = {'nginx': 20, 'apache': 20}
        result = build_tag_batches(tags, counts, max_per_batch=100)
        self.assertEqual(len(result), 1)


class TestCountTemplatesForTag(TestCase):
    @patch('reNgine.nuclei_batch_utils.subprocess.run')
    def test_counts_non_empty_lines(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            '/root/nuclei-templates/wordpress/wp-login.yaml\n'
            '/root/nuclei-templates/wordpress/wp-version.yaml\n'
            '\n'
        )
        count = count_templates_for_tag('wordpress', ['/root/nuclei-templates'])
        self.assertEqual(count, 2)

    @patch('reNgine.nuclei_batch_utils.subprocess.run')
    def test_returns_zero_on_empty_output(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ''
        count = count_templates_for_tag('sometag', ['/root/nuclei-templates'])
        self.assertEqual(count, 0)

    @patch('reNgine.nuclei_batch_utils.subprocess.run')
    def test_returns_zero_on_subprocess_exception(self, mock_run):
        mock_run.side_effect = Exception('nuclei not found')
        count = count_templates_for_tag('wordpress', ['/root/nuclei-templates'])
        self.assertEqual(count, 0)

    @patch('reNgine.nuclei_batch_utils.subprocess.run')
    def test_passes_correct_flags(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ''
        count_templates_for_tag('wordpress', ['/root/nuclei-templates'])
        cmd = mock_run.call_args[0][0]
        self.assertIn('nuclei', cmd)
        self.assertIn('-tl', cmd)
        self.assertIn('-tags', cmd)
        self.assertIn('wordpress', cmd)
        self.assertIn('-t', cmd)
        self.assertIn('/root/nuclei-templates', cmd)

    @patch('reNgine.nuclei_batch_utils.subprocess.run')
    def test_empty_tag_returns_zero_without_subprocess(self, mock_run):
        count = count_templates_for_tag('', ['/root/nuclei-templates'])
        self.assertEqual(count, 0)
        mock_run.assert_not_called()
