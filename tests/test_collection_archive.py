import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_archive import archive_collection, collection_archive_bytes, read_collection_archive, replay_collection_archive
from test_employer_watchlist import synthetic_watchlist
from test_watchlist_fetch import fake_fetch
from watchlist_fetch import fetch_watchlist


class CollectionArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "collection.json"
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch):
            self.collection = fetch_watchlist(synthetic_watchlist(), [0, 1])

    def test_exact_roundtrip_keeps_original_bytes_time_scope_and_filters_offline(self):
        with patch("provider_boards.request_bytes") as network:
            archive_collection(self.collection, self.path)
            self.assertEqual(read_collection_archive(self.path), self.collection)
            network.assert_not_called()
        with self.assertRaises(FileExistsError):
            archive_collection(self.collection, self.path)

    def test_changed_bytes_identity_time_and_outcome_coverage_are_rejected(self):
        original = json.loads(collection_archive_bytes(self.collection))
        for mutate in (
            lambda c: c["sources"][0].update(response_sha256="0" * 64),
            lambda c: c["sources"][0].update(source_base64="%%"),
            lambda c: c["sources"][0].update(provider="ashby"),
            lambda c: c["sources"][0].update(fetched_at="2000-01-01T00:00:00+00:00"),
            lambda c: c["sources"].pop(),
            lambda c: c.update(extra="unsupported")):
            data = copy.deepcopy(original)
            mutate(data)
            with self.assertRaises(ValueError):
                replay_collection_archive(json.dumps(data).encode())

    def test_partial_failures_and_empty_successful_boards_remain_distinct(self):
        original = copy.deepcopy(self.collection)
        original["feeds"].pop()
        original["failures"] = [{"board_index": 1, "error": "Synthetic source failed"}]
        replay = replay_collection_archive(collection_archive_bytes(original))
        self.assertEqual(replay["failures"], original["failures"])
        self.assertEqual(len(replay["feeds"]), 1)
        snapshot = collection_archive_bytes(original)
        with patch("collection_archive.MAX_ARCHIVE_BYTES", 10):
            with self.assertRaises(ValueError):
                replay_collection_archive(snapshot)
            with self.assertRaises(ValueError):
                collection_archive_bytes(original)
