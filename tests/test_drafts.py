import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows unsaved draft guards")
class DraftTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        from job_store import JobStore
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        self.source = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.first = self.store.save(self.source, "First role", "Synthetic Co")
        self.second = self.store.save(self.source, "Second role", "Other Co")
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.select_job(self.first)
        self.shelf.open_selected()

    def test_switching_saved_jobs_requires_discard_and_restores_previous_selection(self):
        self.shelf.posting.insert("end", " UNSAVED")
        self.shelf.select_job(self.second)
        with patch("desktop.messagebox.askyesno", return_value=False):
            self.shelf.open_selected()
        self.assertEqual(self.shelf.current_id, self.first)
        self.assertIn("UNSAVED", self.shelf.posting.get("1.0", "end-1c"))
        self.assertEqual(self.shelf.jobs.selection()[0], self.first)
        self.shelf.select_job(self.second)
        with patch("desktop.messagebox.askyesno", return_value=True):
            self.shelf.open_selected()
        self.assertEqual(self.shelf.current_id, self.second)
        self.assertFalse(self.shelf.has_draft_changes())
        self.assertEqual(len(self.store.list_jobs()), 2)

    def test_new_reload_close_and_saved_pack_guards_preserve_draft(self):
        self.shelf.fields["Job title"].insert("end", " draft")
        self.assertIsNone(self.shelf.open_tracker())
        with patch("desktop.filedialog.asksaveasfilename") as dialog:
            self.shelf.export_pack()
            dialog.assert_not_called()
        with patch("desktop.messagebox.askyesno", return_value=False):
            self.shelf.new_posting()
            self.shelf.reload_saved()
            self.shelf.close()
        self.assertTrue(self.root.winfo_exists())
        self.assertTrue(self.shelf.has_draft_changes())
        with patch("desktop.messagebox.askyesno", return_value=True):
            self.shelf.reload_saved()
        self.assertEqual(self.shelf.fields["Job title"].get(), "First role")
        self.assertFalse(self.shelf.has_draft_changes())

    def test_save_marks_baseline_and_filtering_does_not_discard_later_edits(self):
        self.shelf.posting.insert("end", " Saved revision.")
        with patch("desktop.messagebox.showerror") as error:
            self.shelf.save()
            error.assert_not_called()
        saved_posting = self.shelf.posting.get("1.0", "end-1c")
        self.assertFalse(self.shelf.has_draft_changes())
        self.shelf.posting.insert("end", " UNSAVED")
        self.shelf.search.set("No matching company")
        self.shelf.refresh()
        self.assertEqual(self.shelf.rows, [])
        self.assertTrue(self.shelf.has_draft_changes())
        with patch("desktop.messagebox.askyesno", return_value=True):
            self.shelf.reload_saved()
        self.assertEqual(self.shelf.posting.get("1.0", "end-1c"), saved_posting)
        self.assertEqual(len(self.store.list_jobs()), 3)
