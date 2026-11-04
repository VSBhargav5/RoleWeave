import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt", "Native Windows resume review workflow")
class ResumeUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        from job_store import JobStore
        from test_profile import synthetic_profile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        data = synthetic_profile()
        data["facts"].append({"id": "sql", "claim": "Practised SQL with synthetic examples", "source": "Synthetic exercise", "reviewed": True, "section": "Skills"})
        self.store.save_profile(json.dumps(data).encode())
        self.shelf = JobShelf(self.root, self.store)
        self.builder = self.shelf.open_resume()
        self.builder.withdraw()
        self.builder.include_pdf.set(False)

    def test_review_save_export_and_modified_file_open_guard(self):
        self.builder.facts.selection_set(0)
        self.builder.preview()
        self.builder.save()
        self.assertEqual(self.store.list_resumes(), [])
        self.builder.confirmed.set(True)
        self.builder.save()
        self.assertEqual(len(self.store.list_resumes()), 1)
        destination = Path(self.temp.name) / "resume.html"
        with patch("resume_builder.filedialog.asksaveasfilename", return_value=str(destination)):
            self.builder.export("html")
        self.assertIn("Synthetic Candidate", destination.read_text(encoding="utf-8"))
        self.assertNotIn("Unreviewed draft claim", destination.read_text(encoding="utf-8"))
        destination.write_bytes(b"changed")
        with patch("resume_builder.os.startfile") as opener:
            self.builder.open_exported()
            opener.assert_not_called()
        self.assertIn("changed", self.builder.status.get())

    def test_selection_changed_after_preview_requires_review_again(self):
        self.builder.facts.selection_set(0)
        self.builder.preview()
        self.builder.confirmed.set(True)
        self.builder.facts.selection_set(1)
        self.builder.save()
        self.assertEqual(self.store.list_resumes(), [])
        self.assertIn("current selection", self.builder.status.get())

    def test_shelf_blocks_resume_from_unsaved_job_edits(self):
        self.builder.destroy()
        self.shelf.fields["Job title"].insert(0, "Unsaved role")
        self.assertIsNone(self.shelf.open_resume())
        self.assertIn("Save or discard", self.shelf.status.get())
