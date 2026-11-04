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
    def test_offline_request_export_excludes_session_key_and_never_sends(self):
        editor = self.shelf.edit_evidence()
        assistant = editor.open_ai()
        assistant.key.set("SYNTHETIC_SECRET_KEY")
        path = self.folder / "request.json"
        with patch("ai_window.filedialog.asksaveasfilename", return_value=str(path)), patch.object(assistant.task, "start") as sender:
            assistant.export_request()
            sender.assert_not_called()
        self.assertEqual(path.read_bytes(), assistant.payload)
        self.assertNotIn(b"SYNTHETIC_SECRET_KEY", path.read_bytes())
        assistant.close()
        editor.destroy()

    def test_filtered_fact_selection_keeps_identity_and_imported_draft_is_guarded(self):
        editor = self.shelf.open_profile()
        editor.fact_query.set("SQL")
        editor.refresh_facts()
        editor.facts.selection_set(0)
        editor.load_fact()
        self.assertIn("SQL", editor.claim.get("1.0", "end"))
        editor.clear_fact()
        editor.imported_draft = True
        with patch("profile_editor.messagebox.askyesno", return_value=False):
            editor.close()
        self.assertTrue(editor.winfo_exists())
        editor.destroy()

    def test_keyboard_new_uses_existing_unsaved_guard(self):
        self.shelf.posting.insert("end", " UNSAVED")
        with patch("desktop.messagebox.askyesno", return_value=False):
            self.assertEqual(self.shelf.shortcut(self.shelf.new_posting), "break")
        self.assertIn("UNSAVED", self.shelf.posting.get("1.0", "end"))
        self.assertEqual(self.shelf.current_id, self.job)
        self.assertTrue(self.root.bind("<Control-f>"))

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
