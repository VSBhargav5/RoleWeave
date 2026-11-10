import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from test_profile import synthetic_profile


@unittest.skipUnless(os.name == "nt", "Native Windows letter workflow")
class LetterUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.profile = self.store.save_profile(json.dumps(synthetic_profile()).encode())
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update)
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.show_saved(self.job)
        self.window = self.shelf.open_letter()
        self.window.withdraw()

    def prepare(self):
        self.window.choices.selection_set(0)
        self.window.motivation.insert("1.0", "I am interested in reliable systems.")
        self.window.preview()
        self.window.confirmed.set(True)

    def test_changed_input_blocks_stale_export_and_frozen_version_reopens(self):
        from cover_letter import read_letter
        from letter_window import FrozenLetterWindow
        self.prepare()
        self.window.motivation.insert("end", " Changed.")
        with patch("letter_window.filedialog.asksaveasfilename") as save:
            self.window.export("json")
            save.assert_not_called()
        self.window.preview()
        self.window.confirmed.set(True)
        path = self.folder / "letter.json"
        with patch("letter_window.filedialog.asksaveasfilename", return_value=str(path)):
            self.window.export("json")
        snapshot, record = read_letter(path)
        viewer = FrozenLetterWindow(self.root, snapshot)
        self.assertIn("Changed.", record["text"])
        viewer.destroy()

    def test_unsaved_close_and_job_draft_guards_preserve_inputs(self):
        self.window.motivation.insert("1.0", "Unsaved")
        with patch("letter_window.messagebox.askyesno", return_value=False):
            self.window.close()
        self.assertTrue(self.window.winfo_exists())
        self.window.destroy()
        self.shelf.posting.insert("end", "Unsaved job edit")
        self.assertIsNone(self.shelf.open_letter())
