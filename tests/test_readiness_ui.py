import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from demo_data import seed_practice
from job_store import JobStore


@unittest.skipUnless(os.name == "nt", "Windows readiness interactions")
class ReadinessUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.job = seed_practice(self.store)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update_idletasks)
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.show_saved(self.job)

    def test_profile_transfer_preserves_export_but_requires_fresh_import_review(self):
        editor = self.shelf.open_profile()
        output = self.folder / "profile.json"
        original = self.store.active_profile()["snapshot"]
        with patch("profile_editor.filedialog.asksaveasfilename", return_value=str(output)):
            editor.export_profile()
        self.assertEqual(output.read_bytes(), original)
        with patch("profile_editor.filedialog.askopenfilename", return_value=str(output)):
            editor.import_profile()
        self.assertIsNone(editor.selected_version)
        self.assertTrue(all(not fact["reviewed"] for fact in editor.data["facts"]))
        self.assertEqual(self.store.active_profile()["snapshot"], original)
        editor.destroy()
