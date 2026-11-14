import json
import os
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows career profile workflow")
class ProfileUITests(unittest.TestCase):
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
        self.shelf = JobShelf(self.root, self.store)

    def test_create_profile_then_copy_reviewed_fact_into_job_without_auto_link(self):
        profile = self.shelf.open_profile()
        profile.withdraw()
        profile.fields["name"].insert(0, "Synthetic UI Candidate")
        profile.claim.insert("1.0", "Built a synthetic Python practice project.")
        profile.source.insert(0, "Synthetic project notes, not employment")
        profile.section.set("Projects")
        profile.reviewed.set(True)
        profile.add_fact()
        profile.save()
        self.assertEqual(self.store.active_profile()["profile"]["name"], "Synthetic UI Candidate")
        job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.shelf.show_saved(job)
        editor = self.shelf.edit_evidence()
        editor.withdraw()
        picker = editor.open_career_facts()
        picker.withdraw()
        picker.list.selection_set(0)
        picker.copy()
        self.assertEqual(len(editor.data["facts"]), 2)
        self.assertIn("Career profile", editor.data["facts"][-1]["source"])
        self.assertEqual(editor.data["requirements"][1]["fact_ids"], [])
        editor.save()
        newest = self.store.load(self.store.list_jobs()[0]["id"])
        self.assertEqual(len(json.loads(newest["snapshot"])["facts"]), 2)

    def test_profile_changes_preserve_original_and_pending_fact_blocks_save(self):
        from test_profile import synthetic_profile
        first = self.store.save_profile(json.dumps(synthetic_profile()).encode())
        original = self.store.load_profile(first)["snapshot"]
        editor = self.shelf.open_profile()
        editor.withdraw()
        editor.facts.selection_set(0)
        editor.load_fact()
        self.assertFalse(editor.reviewed.get())
        editor.save()
        self.assertIn("pending fact", editor.status.get())
        editor.claim.delete("1.0", "end")
        editor.claim.insert("1.0", "Corrected synthetic claim")
        editor.reviewed.set(True)
        editor.update_fact()
        editor.save()
        self.assertNotEqual(self.store.active_profile()["id"], first)
        self.assertEqual(self.store.load_profile(first)["snapshot"], original)
