import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_export import export_collection_csv
from test_employer_watchlist import synthetic_watchlist
from test_watchlist_fetch import fake_fetch
from watchlist_fetch import fetch_watchlist


class CollectionExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "shortlist.csv"
        data = synthetic_watchlist()
        data["boards"][0]["company"] = "  =HYPERLINK(untrusted)"
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch):
            self.collection = fetch_watchlist(data, [0, 1])

    def test_filtered_metadata_preserves_evidence_and_escapes_formula_prefixes(self):
        count = export_collection_csv(self.collection, self.path)
        self.assertEqual(count, 2)
        with self.path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(rows[0]["your_employer_label"].startswith("'"))
        self.assertEqual(rows[0]["selected_source_count"], "2")
        self.assertTrue(rows[0]["response_sha256"])
        self.assertNotIn("posting", rows[0])
        self.assertNotIn("Build Python pipelines", self.path.read_text())
        with self.assertRaises(FileExistsError):
            export_collection_csv(self.collection, self.path)

    def test_zero_matches_or_size_failure_never_create_a_misleading_file(self):
        self.collection["watchlist"]["filters"]["include"] = "No matching synthetic phrase"
        with self.assertRaises(ValueError):
            export_collection_csv(self.collection, self.path)
        self.assertFalse(self.path.exists())
        self.collection["watchlist"]["filters"]["include"] = ""
        with patch("collection_export.MAX_CSV_BYTES", 10):
            with self.assertRaises(ValueError):
                export_collection_csv(self.collection, self.path)
        self.assertFalse(self.path.exists())
