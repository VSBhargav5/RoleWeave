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

    def test_provider_switch_rejects_late_results_and_old_selections(self):
        self.window.received(self.feed)
        self.window.rows.selection_set("0")
        self.window.provider.set("lever")
        with self.assertRaisesRegex(ValueError, "provider changed"):
            self.window.selected()
        self.window.received(self.feed)
        self.assertIsNone(self.window.feed)
        self.assertEqual(self.window.rows.get_children(), ())
        self.window.provider.set("ashby")
        with patch("discovery_window.fetch_source", return_value={"jobs": []}) as fetch:
            with patch.object(self.window.task, "start") as start:
                self.window.fetch()
                start.call_args.args[0](None)
                fetch.assert_called_once_with("ashby", "synthetic", None)
        self.assertIn("api.ashbyhq.com", self.window.status.get())

    def test_archive_roundtrip_is_offline_and_clears_old_employer_label(self):
        from provider_boards import parse_source
        from test_provider_boards import lever_fixture
        self.window.provider.set("lever")
        self.window.received(parse_source(json.dumps(lever_fixture()).encode(), "lever", "synthetic"))
        path = str(Path(self.temp.name) / "board.json")
        original = self.window.feed
        with patch("discovery_window.filedialog.asksaveasfilename", return_value=path):
            self.window.export_observation()
        self.window.source_changed()
        with patch("discovery_window.filedialog.askopenfilename", return_value=path), patch("provider_boards.request_bytes") as network:
            self.window.open_observation()
            network.assert_not_called()
        self.assertEqual(self.window.feed, original)
        self.assertEqual(self.window.company.get(), "")
        self.assertIn("Offline", self.window.status.get())

    def test_description_and_exclusion_filters_are_local_and_clear_hidden_preview(self):
        self.window.received(self.feed)
        with patch("provider_boards.request_bytes") as network:
            self.window.query.set("SQL preferred")
            self.window.filter_rows()
            self.assertEqual(len(self.window.visible), 0)
            self.window.search_description.set(True)
            self.window.filter_rows()
            self.assertEqual(len(self.window.visible), 1)
            self.window.rows.selection_set("0")
            self.window.preview_selected()
            self.window.exclude.set("Python required")
            self.window.filter_rows()
            self.assertEqual(len(self.window.visible), 0)
            self.assertEqual(self.window.preview.get("1.0", "end").strip(), "")
            self.assertIn("0 of 1", self.window.filtered_count.get())
            network.assert_not_called()

    def test_board_url_resolves_locally_without_reusing_employer_label(self):
        with patch("discovery_window.simpledialog.askstring", return_value="https://jobs.ashbyhq.com/synthetic"), patch("provider_boards.request_bytes") as network:
            self.window.use_board_url()
            network.assert_not_called()
        self.assertEqual(self.window.provider.get(), "ashby")
        self.assertEqual(self.window.token.get(), "synthetic")
        self.assertEqual(self.window.company.get(), "")
        self.assertIsNone(self.window.feed)
