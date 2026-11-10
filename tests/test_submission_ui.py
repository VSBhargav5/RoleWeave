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
