import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt", "Native Windows application tracker")
class TrackerTests(unittest.TestCase):
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
        source = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.job = self.store.save(source, "Synthetic Engineer", "Synthetic Co")
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.jobs.selection_set(0)
        self.shelf.open_selected()
        self.tracker = self.shelf.open_tracker()
        self.tracker.withdraw()

    def test_record_note_filter_stage_and_due_date_then_reopen(self):
        self.tracker.stage.set("applied")
        self.tracker.note.insert("1.0", "User-recorded example తెలుగు")
        self.tracker.follow_up.set("2000-01-01")
        self.tracker.record()
        self.assertIn("Observation saved", self.tracker.status.get())
        self.assertIn("తెలుగు", self.tracker.history.get("1.0", "end-1c"))
        self.shelf.stage_filter.set("applied")
        self.shelf.due_only.set(True)
        self.shelf.refresh()
        self.assertEqual(len(self.shelf.rows), 1)
        self.shelf.stage_filter.set("shortlisted")
        self.shelf.refresh()
        self.assertEqual(self.shelf.rows, [])
        self.tracker.destroy()
        self.shelf.stage_filter.set("All stages")
        self.shelf.refresh()
        self.shelf.jobs.selection_set(0)
        reopened = self.shelf.open_tracker()
        reopened.withdraw()
        self.assertEqual(reopened.stage.get(), "applied")
        self.assertEqual(reopened.follow_up.get(), "2000-01-01")

    def test_bad_date_and_no_op_do_not_add_events(self):
        self.tracker.record()
        self.assertIn("No change", self.tracker.status.get())
        self.tracker.stage.set("interview")
        self.tracker.follow_up.set("tomorrow")
        self.tracker.record()
        self.assertIn("YYYY-MM-DD", self.tracker.status.get())
        self.assertEqual(self.store.application_history(self.job), [])

    def test_refresh_error_does_not_report_successful_write_as_unsaved(self):
        def fail(_identifier):
            raise ValueError("Synthetic view error")
        self.tracker.on_change = fail
        self.tracker.stage.set("shortlisted")
        self.tracker.record()
        self.assertIn("Observation saved", self.tracker.status.get())
        self.assertEqual(len(self.store.application_history(self.job)), 1)
        self.tracker.record()
        self.assertIn("No change", self.tracker.status.get())
        self.assertEqual(len(self.store.application_history(self.job)), 1)

    def test_close_requires_discard_for_unrecorded_note(self):
        self.tracker.note.insert("1.0", "Unrecorded synthetic decision")
        with patch("application_tracker.messagebox.askyesno", return_value=False):
            self.tracker.close()
        self.assertTrue(self.tracker.winfo_exists())
        self.assertEqual(self.store.application_history(self.job), [])
