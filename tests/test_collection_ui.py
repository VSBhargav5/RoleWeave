import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from test_employer_watchlist import synthetic_watchlist
from test_watchlist_fetch import fake_fetch
from watchlist_fetch import fetch_watchlist


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows collection workflow")
class CollectionUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf, MARKET_LABELS
        from collection_window import CollectionWindow
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update)
        self.shelf = JobShelf(self.root, self.store)
        self.data = synthetic_watchlist()
        self.window = CollectionWindow(self.root, self.store, self.data, [0, 1], MARKET_LABELS, self.shelf.show_saved)
        self.window.withdraw()
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch):
            self.collection = fetch_watchlist(self.data, [0, 1])

    def test_preview_scope_market_and_deliberate_single_import(self):
        self.window.received(self.collection)
        self.window.rows.selection_set("1")
        self.window.preview_selected()
        self.assertIn("ashby", self.window.preview.get("1.0", "end"))
        self.assertEqual(self.window.market.get(), "International relocation")
        self.window.market.set("")
        self.window.import_selected()
        self.assertEqual(self.store.list_jobs(), [])
        self.window.market.set("India / remote from India")
        self.window.import_selected()
        self.assertEqual(len(self.store.list_jobs("india_remote")), 1)
        self.assertEqual(self.store.load(self.shelf.current_id)["review"]["requirements"], [])
        self.window.import_selected()
        self.assertEqual(len(self.store.list_jobs()), 1)

    def test_partial_failures_remain_visible_and_new_fetch_clears_stale_results(self):
        partial = copy.deepcopy(self.collection)
        partial["feeds"].pop()
        partial["failures"] = [{"board_index": 1, "error": "Synthetic unavailable"}]
        self.window.received(partial)
        self.assertIn("FAILED", self.window.sources.get("1.0", "end"))
        self.assertEqual(len(self.window.visible), 1)
        with patch.object(self.window.task, "start") as start:
            self.window.fetch()
            start.assert_called_once()
        self.window.failed("Synthetic failure")
        self.assertIsNone(self.window.collection)
        self.assertEqual(self.window.rows.get_children(), ())
        self.assertEqual(self.store.list_jobs(), [])

    def test_changed_source_labels_and_mutated_caller_results_cannot_be_imported(self):
        self.window.received(self.collection)
        self.collection["feeds"][0]["feed"]["jobs"][0]["title"] = "Changed after receipt"
        self.assertNotEqual(self.window.visible[0]["title"], "Changed after receipt")
        changed = copy.deepcopy(self.window.collection)
        changed["watchlist"]["boards"][0]["company"] = "Different label"
        self.window.received(changed)
        self.assertIsNone(self.window.collection)
        self.assertIn("scope changed", self.window.status.get())

    def test_minimum_layout_reserves_preview_and_actions(self):
        from tkinter import ttk
        self.root.deiconify()
        self.window.deiconify()
        self.window.geometry("900x700")
        self.window.update()
        self.assertGreaterEqual(self.window.preview.winfo_height(), 80)
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        for button in (widget for widget in walk(self.window) if isinstance(widget, (ttk.Button, ttk.Menubutton)) and widget.winfo_ismapped()):
            x = button.winfo_rootx() - self.window.winfo_rootx()
            y = button.winfo_rooty() - self.window.winfo_rooty()
            self.assertGreaterEqual(button.winfo_height(), 28)
            self.assertLessEqual(x + button.winfo_width(), self.window.winfo_width())
            self.assertLessEqual(y + button.winfo_height(), self.window.winfo_height())

    def test_private_archive_keeps_filters_and_reopens_without_network(self):
        from collection_archive import read_collection_archive
        path = Path(self.temp.name) / "observation.json"
        self.window.received(self.collection)
        self.window.include.set("SQL")
        self.window.search_description.set(True)
        with patch("collection_window.filedialog.asksaveasfilename", return_value=str(path)):
            self.window.save_archive()
        self.assertEqual(read_collection_archive(path)["watchlist"]["filters"]["include"], "SQL")
        self.window.clear_observation()
        with patch("collection_window.filedialog.askopenfilename", return_value=str(path)), patch("provider_boards.request_bytes") as request:
            self.window.open_archive()
            request.assert_not_called()
        self.assertEqual(self.window.include.get(), "SQL")
        self.assertEqual(len(self.window.visible), 2)
        self.assertIn("Offline replay", self.window.status.get())
        with patch("desktop.filedialog.askopenfilename", return_value=str(path)), patch("provider_boards.request_bytes") as request:
            child = self.shelf.open_collection_file()
            request.assert_not_called()
        self.assertIsNotNone(child.collection)
        child.destroy()

    def test_comparison_and_filtered_shortlist_do_not_change_jobs(self):
        from collection_archive import archive_collection
        earlier = Path(self.temp.name) / "earlier.json"
        archive_collection(self.collection, earlier)
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch):
            later = fetch_watchlist(self.data, [0, 1])
        self.window.received(later)
        with patch("collection_window.filedialog.askopenfilename", return_value=str(earlier)):
            comparison = self.window.compare_archive()
        self.assertTrue(comparison.winfo_exists())
        comparison.destroy()
        self.window.include.set("AI Engineer")
        self.window.filter_rows()
        output = Path(self.temp.name) / "shortlist.csv"
        with patch("collection_window.filedialog.asksaveasfilename", return_value=str(output)):
            self.window.export_shortlist()
        self.assertIn("Synthetic AI Co", output.read_text(encoding="utf-8-sig"))
        self.assertNotIn("Synthetic Co,", output.read_text(encoding="utf-8-sig"))
        self.assertEqual(self.store.list_jobs(), [])

    def test_failed_retry_keeps_prior_observations_and_does_not_dispatch_successful_sources(self):
        partial = copy.deepcopy(self.collection)
        partial["feeds"].pop()
        partial["failures"] = [{"board_index": 1, "error": "Synthetic failure"}]
        self.window.received(partial)
        with patch.object(self.window.task, "start") as start, patch("watchlist_fetch.fetch_source", side_effect=fake_fetch) as request:
            self.window.retry_failed()
            result = start.call_args.args[0](None)
            start.call_args.args[1](result)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[0], "ashby")
        self.assertEqual(len(self.window.visible), 2)
        previous = copy.deepcopy(self.window.collection)
        self.window.retry_failed_error("Synthetic timeout")
        self.assertEqual(self.window.collection, previous)
        self.assertEqual(self.store.list_jobs(), [])
