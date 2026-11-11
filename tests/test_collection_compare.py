from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_compare import compare_collections, export_comparison
from provider_boards import parse_source
from test_employer_watchlist import synthetic_watchlist
from test_provider_boards import lever_fixture
from test_watchlist_fetch import fake_fetch
from watchlist_fetch import fetch_watchlist


class CollectionCompareTests(unittest.TestCase):
    def fetch(self, indices, callback=fake_fetch):
        with patch("watchlist_fetch.fetch_source", side_effect=callback):
            return fetch_watchlist(synthetic_watchlist(), indices)

    def test_changed_post_is_scoped_to_the_same_provider_board_identity(self):
        earlier = self.fetch([0, 1])
        def changed(provider, token, cancel=None):
            if provider == "lever":
                rows = lever_fixture()
                rows[0]["text"] = "Changed title"
                return parse_source(json.dumps(rows).encode(), provider, token)
            return fake_fetch(provider, token, cancel)
        later = self.fetch([0, 1], changed)
        report = compare_collections(earlier, later)
        lever = next(source for source in report["sources"] if source["provider"] == "lever")
        self.assertEqual(lever["state"], "compared")
        self.assertEqual(lever["posting_changes"][0]["state"], "changed")
        self.assertNotEqual(lever["earlier_sha256"], lever["later_sha256"])

    def test_failed_and_unselected_sources_do_not_produce_missing_job_findings(self):
        earlier = self.fetch([0, 1])
        def failed(provider, token, cancel=None):
            if provider == "ashby":
                raise ValueError("Synthetic unavailable")
            return fake_fetch(provider, token, cancel)
        later = self.fetch([0, 1], failed)
        ashby = next(source for source in compare_collections(earlier, later)["sources"] if source["provider"] == "ashby")
        self.assertEqual(ashby["state"], "not_comparable")
        self.assertEqual(ashby["posting_changes"], [])
        scopes = compare_collections(self.fetch([0]), self.fetch([1]))
        self.assertEqual(set(scopes["scope_counts"]), {"scope_added", "scope_not_selected"})
        self.assertTrue(all(not source["posting_changes"] for source in scopes["sources"]))

    def test_export_is_bounded_no_overwrite_and_reversed_time_is_rejected(self):
        earlier, later = self.fetch([0]), self.fetch([0])
        later["finished_at"] = (datetime.fromisoformat(later["finished_at"]) + timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError):
            compare_collections(later, earlier)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "comparison.json"
            export_comparison(earlier, later, path)
            self.assertEqual(json.loads(path.read_text())["format"], "roleweave-collection-comparison-v1")
            with self.assertRaises(FileExistsError):
                export_comparison(earlier, later, path)
