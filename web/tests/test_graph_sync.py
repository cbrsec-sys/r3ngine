"""Tests for Neo4j graph sync batching helpers."""
from django.test import SimpleTestCase

from reNgine.utils.graph import GRAPH_SYNC_BATCH_SIZE, _chunk_list


class GraphSyncBatchingTests(SimpleTestCase):
    def test_chunk_list_splits_evenly(self):
        items = list(range(10))
        chunks = list(_chunk_list(items, size=4))
        self.assertEqual(chunks, [
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [8, 9],
        ])

    def test_chunk_list_empty(self):
        self.assertEqual(list(_chunk_list([], size=GRAPH_SYNC_BATCH_SIZE)), [])

    def test_chunk_list_single_batch(self):
        items = [1, 2, 3]
        self.assertEqual(list(_chunk_list(items, size=10)), [[1, 2, 3]])
