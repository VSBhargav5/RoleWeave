import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from job_store import JobStore
from test_profile import synthetic_profile


@unittest.skipUnless(os.name == "nt", "Native Windows dossier workflow")
class DossierUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        profile = self.store.save_profile(json.dumps(synthetic_profile()).encode())
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.resume = self.store.create_resume(profile, ["project-python"], "Exact", self.job, include_pdf=False, confirmed=True)
        self.store.create_resume(profile, ["project-python"], "General", include_pdf=False, confirmed=True)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update)
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.show_saved(self.job)
        self.window = self.shelf.open_dossier()
        self.window.withdraw()

    def test_only_exact_resume_and_explicit_preview_consent_export_cached_bytes(self):
        from application_dossier import verify_dossier
        self.assertEqual(len(self.window.versions), 1)
        self.window.choices.selection_set(0)
        self.window.export()
        self.assertIn("confirm", self.window.status.get())
        self.window.preview()
        expected = self.window.prepared[1]
        self.store.record_application(self.job, "shortlisted", "Later observation", "")
        path = self.folder / "dossier.zip"
        self.window.confirmed.set(True)
        with patch("dossier_window.filedialog.asksaveasfilename", return_value=str(path)):
            self.window.export()
        self.assertEqual(path.read_bytes(), expected)
        self.assertEqual(verify_dossier(path)["history_revision"], 0)
        self.window.invalidate()
        self.assertIsNone(self.window.prepared)
        self.assertFalse(self.window.confirmed.get())

    def test_unsaved_job_edits_block_dossier_context(self):
        self.window.destroy()
        self.shelf.posting.insert("end", "Unsaved edit")
        self.assertIsNone(self.shelf.open_dossier())
        self.assertIn("save/discard", self.shelf.status.get())

    def test_dossier_actions_and_reading_pane_fit_minimum_size(self):
        from tkinter import ttk
        self.root.deiconify()
        self.window.deiconify()
        self.window.geometry("850x650")
        self.window.update()
        self.assertGreaterEqual(self.window.manifest.winfo_height(), 80)
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        for button in (w for w in walk(self.window) if isinstance(w, ttk.Button)):
            self.assertTrue(button.winfo_ismapped())
            y = button.winfo_rooty() - self.window.winfo_rooty()
            self.assertGreaterEqual(button.winfo_height(), 28)
            self.assertLessEqual(y + button.winfo_height(), self.window.winfo_height())
