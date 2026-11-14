import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows Tk evidence editor")
class EditorTests(unittest.TestCase):
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
        self.fixture = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.original = self.store.save(self.fixture, "Synthetic role", "Synthetic company")
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.jobs.selection_set(self.shelf.rows[0]["id"])
        self.shelf.open_selected()
        self.editor = self.shelf.edit_evidence()
        self.editor.withdraw()

    def quote(self, value):
        self.editor.quote.delete("1.0", "end")
        self.editor.quote.insert("1.0", value)

    def test_window_close_preserves_unsaved_evidence_when_discard_is_declined(self):
        self.quote("Pending synthetic quote")
        with patch("evidence_editor.messagebox.askyesno", return_value=False):
            self.editor.request_close()
        self.assertTrue(self.editor.winfo_exists())
        self.assertEqual(len(self.store.list_jobs()), 1)

    def test_fact_correction_resets_review_unlinks_and_saves_new_snapshot(self):
        self.editor.facts.selection_set(0)
        self.editor.load_fact()
        self.assertFalse(self.editor.reviewed.get())
        self.editor.claim.delete("1.0", "end")
        self.editor.claim.insert("1.0", "Corrected: only a synthetic Python exercise")
        self.editor.reviewed.set(True)
        self.editor.update_fact()
        self.assertIn("removed 1", self.editor.status.get())
        self.assertEqual(self.editor.data["requirements"][0]["fact_ids"], [])
        self.editor.save()
        newest = self.store.load(self.store.list_jobs()[0]["id"])
        self.assertEqual(newest["review"]["requirements"][0]["state"], "needs_review")
        self.assertEqual(self.store.load(self.original)["snapshot"], self.fixture)

    def test_fact_removal_rejects_links_and_pending_forms(self):
        self.editor.facts.selection_set(0)
        self.editor.delete_fact()
        self.assertIn("Unlink", self.editor.status.get())
        self.editor.load_fact()
        self.editor.delete_fact()
        self.assertIn("pending", self.editor.status.get())
        self.editor.update_fact()  # unchecked review revokes links
        self.editor.facts.selection_set(0)
        self.editor.delete_fact()
        self.assertEqual(self.editor.data["facts"], [])
        self.editor.save()
        self.assertEqual(len(self.store.list_jobs()), 2)
        self.assertEqual(self.store.load(self.original)["snapshot"], self.fixture)

    def test_link_exact_requirement_save_reopen_and_preserve_original(self):
        self.editor.claim.insert("1.0", "Operated a synthetic Spark exercise; not production employment")
        self.editor.source.insert(0, "Synthetic learning project")
        self.editor.reviewed.set(True)
        self.editor.add_fact()
        self.assertFalse(self.editor.reviewed.get())
        self.editor.requirements.selection_set(1)
        self.editor.load_requirement()
        self.editor.facts.selection_set(1)
        self.editor.update_requirement()
        self.editor.save()
        self.assertEqual(len(self.store.list_jobs()), 2)
        newest = self.store.load(self.store.list_jobs()[0]["id"])
        self.assertEqual(newest["review"]["requirements"][1]["state"], "evidence_selected")
        self.assertEqual(self.store.load(self.original)["snapshot"], self.fixture)
        self.assertEqual(self.store.load(self.original)["review"]["requirements"][1]["state"], "needs_review")
        self.assertIn("Operated a synthetic Spark", self.shelf.evidence.plain_text)

    def test_invented_quote_and_unreviewed_link_fail_without_changing_store(self):
        self.quote("Invented qualification")
        self.editor.add_requirement()
        self.assertIn("exact substring", self.editor.status.get())
        self.assertEqual(len(self.editor.data["requirements"]), 2)
        self.editor.claim.insert("1.0", "Unreviewed synthetic fact")
        self.editor.source.insert(0, "Unverified note")
        self.editor.add_fact()
        self.quote("Production Spark operations required.")
        self.editor.facts.selection_set(1)
        self.editor.add_requirement()
        self.assertIn("Unreviewed", self.editor.status.get())
        self.assertEqual(len(self.store.list_jobs()), 1)
        self.editor.destroy()
        self.assertEqual(self.store.load(self.original)["snapshot"], self.fixture)

    def test_pending_form_edits_do_not_silently_disappear_on_save(self):
        self.quote("Python required.")
        self.editor.save()
        self.assertIn("pending requirement", self.editor.status.get())
        self.assertEqual(len(self.store.list_jobs()), 1)
        self.quote("")
        self.editor.claim.insert("1.0", "Still typing")
        self.editor.save()
        self.assertIn("pending fact", self.editor.status.get())
        self.assertEqual(len(self.store.list_jobs()), 1)

    def test_remove_requirement_in_new_snapshot_and_cancel_does_not_persist(self):
        self.editor.requirements.selection_set(1)
        self.editor.remove_requirement()
        self.assertEqual(len(self.editor.data["requirements"]), 1)
        self.editor.destroy()
        self.assertEqual(len(self.store.list_jobs()), 1)
        self.assertEqual(len(json.loads(self.store.load(self.original)["snapshot"])["requirements"]), 2)
