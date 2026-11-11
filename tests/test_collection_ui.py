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


@unittest.skipUnless(os.name == "nt", "Native Windows collection workflow")
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
        for button in (widget for widget in walk(self.window) if isinstance(widget, ttk.Button) and widget.winfo_ismapped()):
            x = button.winfo_rootx() - self.window.winfo_rootx()
            y = button.winfo_rooty() - self.window.winfo_rooty()
            self.assertGreaterEqual(button.winfo_height(), 28)
            self.assertLessEqual(x + button.winfo_width(), self.window.winfo_width())
            self.assertLessEqual(y + button.winfo_height(), self.window.winfo_height())
