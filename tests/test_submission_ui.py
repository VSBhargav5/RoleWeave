import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from application_dossier import build_dossier
from job_store import JobStore
import test_application_dossier as dossier_tests


@unittest.skipUnless(os.name == "nt", "Native Windows submission workflow")
class SubmissionUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        dossier_tests.ApplicationDossierTests.setUp(self)
        self.path.write_bytes(build_dossier(self.store.load(self.job), self.store.load_resume(self.resume), []))
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update)
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.show_saved(self.job)
        self.window = self.shelf.open_submission()
        self.window.withdraw()

    def test_verified_packet_and_explicit_observation_are_required(self):
        self.window.channel.set("Employer portal")
        self.window.record()
        self.assertEqual(self.store.application_history(self.job), [])
        with patch("submission_window.filedialog.askopenfilename", return_value=str(self.path)):
            self.window.load_dossier()
        self.window.record()
        self.assertEqual(self.store.application_history(self.job), [])
        self.window.confirmed.set(True)
        self.window.record()
        self.assertEqual(self.store.application_history(self.job)[-1]["stage"], "applied")
        self.assertFalse(self.window.confirmed.get())
        self.window.confirmed.set(True)
        self.window.record()
        self.assertEqual(len(self.store.application_history(self.job)), 1)
        self.assertIn("already recorded", self.window.status.get())

    def test_close_keeps_unrecorded_inputs_and_main_job_drafts_block_open(self):
        self.window.note.insert("1.0", "Not recorded")
        with patch("submission_window.messagebox.askyesno", return_value=False):
            self.window.close()
        self.assertTrue(self.window.winfo_exists())
        self.window.destroy()
        self.shelf.posting.insert("end", "Unsaved review")
        self.assertIsNone(self.shelf.open_submission())

    def test_basic_submission_records_details_and_followup_without_dossier(self):
        self.window.channel.set("Employer portal")
        self.window.reference.set("SYNTHETIC-REF")
        self.window.follow_up.set("2026-12-01")
        self.window.confirmed.set(True)
        self.window.record()
        event = self.store.application_history(self.job)[-1]
        self.assertEqual(event["stage"], "applied")
        self.assertEqual(event["follow_up"], "2026-12-01")
        self.assertIn("SYNTHETIC-REF", event["note"])
        self.assertIn("documents: not linked", event["note"])

    def test_stale_form_retains_draft_and_explicit_reload_preserves_submission_fields(self):
        self.window.channel.set("Email")
        self.window.reference.set("MY-DRAFT")
        self.store.record_application(self.job, "interview", "Newer observation", "2026-12-03")
        self.window.confirmed.set(True)
        self.window.record()
        self.assertIn("history changed", self.window.status.get())
        self.assertEqual(len(self.store.application_history(self.job)), 1)
        self.assertEqual(self.window.reference.get(), "MY-DRAFT")
        with patch("submission_window.messagebox.askyesno", return_value=True):
            self.window.reload_tracking()
        self.assertEqual(self.window.follow_up.get(), "2026-12-03")
        self.assertFalse(self.window.confirmed.get())
        self.window.confirmed.set(True)
        self.window.record()
        self.assertEqual(self.store.application_history(self.job)[-1]["stage"], "interview")
        self.assertEqual(self.store.application_history(self.job)[-1]["follow_up"], "2026-12-03")

    def test_refresh_failure_reports_saved_observation_without_duplicate_retry(self):
        self.window.on_change = lambda _id: (_ for _ in ()).throw(ValueError("synthetic refresh failure"))
        self.window.channel.set("Employer portal")
        self.window.confirmed.set(True)
        self.window.record()
        self.assertIn("saved, but view refresh failed", self.window.status.get())
        self.window.confirmed.set(True)
        self.window.record()
        self.assertEqual(len(self.store.application_history(self.job)), 1)

    def test_submission_minimum_keeps_note_and_controls_usable(self):
        from tkinter import ttk
        self.root.deiconify()
        self.window.deiconify()
        self.window.geometry("850x650")
        self.window.update()
        self.assertGreaterEqual(self.window.note.winfo_height(), 40)
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        for button in walk(self.window):
            if isinstance(button, ttk.Button):
                self.assertTrue(button.winfo_ismapped())
                self.assertGreaterEqual(button.winfo_height(), 28)
                self.assertLessEqual(button.winfo_rooty() - self.window.winfo_rooty() + button.winfo_height(), self.window.winfo_height())
