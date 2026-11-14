import os
from pathlib import Path
import unittest
from unittest.mock import patch

from test_mail_observation import synthetic_mail
import test_application_dossier as dossier_tests


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows correspondence workflow")
class CorrespondenceUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        dossier_tests.ApplicationDossierTests.setUp(self)
        self.email = self.folder / "synthetic.eml"
        self.email.write_bytes(synthetic_mail())
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update)
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.show_saved(self.job)
        self.window = self.shelf.open_correspondence()
        self.window.withdraw()

    def test_local_file_selection_exact_quote_and_review_required(self):
        with patch("correspondence_window.filedialog.askopenfilename", return_value=str(self.email)):
            self.window.load_mail()
        self.window.quote.insert("1.0", "Please suggest a time")
        self.window.record()
        self.assertEqual(self.store.application_history(self.job), [])
        self.window.confirmed.set(True)
        self.window.record()
        self.assertEqual(len(self.store.application_history(self.job)), 1)
        self.assertEqual(self.store.application_history(self.job)[0]["stage"], "saved")
        self.assertFalse(self.window.confirmed.get())

    def test_draft_close_and_main_unsaved_review_are_guarded(self):
        self.window.note.insert("1.0", "Unrecorded")
        with patch("correspondence_window.messagebox.askyesno", return_value=False):
            self.window.close()
        self.assertTrue(self.window.winfo_exists())
        self.window.destroy()
        self.shelf.posting.insert("end", "Unsaved")
        self.assertIsNone(self.shelf.open_correspondence())
