import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from discovery import parse_board
from test_discovery import fixture
from job_store import JobStore


@unittest.skipUnless(os.name == "nt", "Native Windows discovery workflow")
class DiscoveryUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update_idletasks)
        self.shelf = JobShelf(self.root, self.store)
        self.window = self.shelf.open_discovery()
        self.window.withdraw()
        self.window.token.insert(0, "synthetic")
        self.window.company.insert(0, "Synthetic Co")
        self.feed = parse_board(json.dumps(fixture()).encode(), "synthetic")

    def test_preview_explicit_market_import_repeat_and_changed_version(self):
        self.window.received(self.feed)
        self.window.rows.selection_set("0")
        self.window.preview_selected()
        self.assertIn("Python required", self.window.preview.get("1.0", "end"))
        self.window.import_selected()
        self.assertEqual(self.store.list_jobs(), [])  # no inferred market
        self.window.market.set("International relocation")
        self.window.import_selected()
        self.assertEqual(len(self.store.list_jobs("relocation")), 1)
        item = self.store.load(self.shelf.current_id)
        self.assertEqual(item["review"]["requirements"], [])
        self.window.import_selected()
        self.assertEqual(len(self.store.list_jobs()), 1)
        self.assertIn("already saved", self.window.status.get())
        data = fixture()
        data["jobs"][0]["content"] = "<p>Changed source description.</p>"
        self.window.received(parse_board(json.dumps(data).encode(), "synthetic"))
        self.window.rows.selection_set("0")
        self.window.import_selected()
        self.assertEqual(len(self.store.list_jobs()), 2)
        self.assertEqual(self.store.load(item["id"])["snapshot"], item["snapshot"])

    def test_fetch_failure_and_changed_token_cannot_import_stale_results(self):
        self.window.received(self.feed)
        self.window.rows.selection_set("0")
        self.window.token.delete(0, "end")
        self.window.token.insert(0, "other")
        self.window.import_selected()
        self.assertIn("token changed", self.window.status.get().lower())
        with patch.object(self.window.task, "start") as start:
            self.window.fetch()
            start.assert_called_once()
        self.window.failed("Synthetic network error")
        self.assertEqual(self.window.rows.get_children(), ())
        self.assertEqual(self.store.list_jobs(), [])

    def test_shelf_unsaved_posting_is_preserved(self):
        self.window.destroy()
        self.shelf.posting.insert("end", "Unsaved posting")
        self.assertIsNone(self.shelf.open_discovery())
        self.assertIn("Unsaved posting", self.shelf.posting.get("1.0", "end"))
