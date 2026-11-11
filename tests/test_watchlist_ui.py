import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from job_store import JobStore
from test_employer_watchlist import synthetic_watchlist


@unittest.skipUnless(os.name == "nt", "Native Windows watchlist workflow")
class WatchlistUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update)
        self.shelf = JobShelf(self.root, self.store)
        self.window = self.shelf.open_watchlist()
        self.window.withdraw()
        self.path = self.folder / "boards.json"
        self.path.write_text(json.dumps(synthetic_watchlist()))
        with patch("watchlist_window.filedialog.askopenfilename", return_value=str(self.path)):
            self.window.open_file()

    def test_open_board_reuses_explicit_labels_and_filters_without_fetch(self):
        self.window.rows.selection_set("0")
        self.window.load_selected()
        self.window.include.set("SQL")
        with patch("provider_boards.request_bytes") as network:
            child = self.window.open_board()
            network.assert_not_called()
        self.assertEqual(child.provider.get(), "lever")
        self.assertEqual(child.token.get(), "synthetic")
        self.assertEqual(child.market.get(), "India / remote from India")
        self.assertEqual(child.query.get(), "SQL")
        child.destroy()

    def test_unapplied_editor_changes_cannot_be_silently_omitted_from_save(self):
        self.window.rows.selection_set("0")
        self.window.load_selected()
        self.window.company.set("Changed label")
        with patch("watchlist_window.filedialog.asksaveasfilename") as save:
            self.window.save_file()
            save.assert_not_called()
        self.assertIn("Add/update", self.window.status.get())
        self.window.update_board()
        self.assertEqual(self.window.boards[0]["company"], "Changed label")
        output = self.folder / "new.json"
        with patch("watchlist_window.filedialog.asksaveasfilename", return_value=str(output)):
            self.window.save_file()
        self.assertEqual(json.loads(output.read_text())["boards"][0]["company"], "Changed label")

    def test_unsaved_close_and_job_form_guards_preserve_drafts(self):
        self.window.name.set("Unsaved choices")
        with patch("watchlist_window.messagebox.askyesno", return_value=False):
            self.window.close()
        self.assertTrue(self.window.winfo_exists())
        self.window.destroy()
        self.shelf.posting.insert("end", "Unsaved job")
        self.assertIsNone(self.shelf.open_watchlist())

    def test_watchlist_actions_fit_the_supported_minimum(self):
        from tkinter import ttk
        self.root.deiconify()
        self.window.deiconify()
        self.window.geometry("900x700")
        self.window.update()
        self.assertGreaterEqual(self.window.rows.winfo_height(), 48)
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        for widget in walk(self.window):
            if isinstance(widget, ttk.Button) and widget.winfo_ismapped():
                x = widget.winfo_rootx() - self.window.winfo_rootx()
                y = widget.winfo_rooty() - self.window.winfo_rooty()
                self.assertGreaterEqual(widget.winfo_height(), 28)
                self.assertLessEqual(x + widget.winfo_width(), self.window.winfo_width())
                self.assertLessEqual(y + widget.winfo_height(), self.window.winfo_height())

    def test_selected_boards_open_collection_without_automatic_fetch(self):
        self.window.rows.selection_set("0", "1")
        self.window.load_selected()
        with patch("provider_boards.request_bytes") as request:
            child = self.window.open_collection()
            request.assert_not_called()
        self.assertEqual(child.selected_indices, [0, 1])
        self.assertIsNone(child.collection)
        child.destroy()
