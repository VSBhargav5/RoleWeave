import base64
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from job_store import JobStore
from test_profile import synthetic_profile


class ProfileRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "source.db")
        self.target = JobStore(self.folder / "target.db")
        data = synthetic_profile()
        self.first = self.store.save_profile(json.dumps(data).encode())
        self.resume = self.store.create_resume(self.first, ["project-python"], "Synthetic version", include_pdf=False, confirmed=True)
        data["headline"] = "Corrected headline"
        self.active = self.store.save_profile(json.dumps(data).encode())
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Role", "Synthetic Co")
        self.backup = self.folder / "all.json"
        self.store.backup(self.backup)

    def test_full_v3_restore_preserves_profiles_active_choice_and_resume_bytes(self):
        self.target.restore(self.backup)
        self.assertEqual(self.target.active_profile()["id"], self.active)
        self.assertEqual(self.target.load_profile(self.first), self.store.load_profile(self.first))
        self.assertEqual(self.target.load_resume(self.resume), self.store.load_resume(self.resume))
        self.target.restore(self.backup)
        self.assertEqual(len(self.target.list_profiles()), 2)
        self.assertEqual(len(self.target.list_resumes()), 1)

    def test_restore_does_not_silently_switch_an_existing_active_profile(self):
        data = synthetic_profile()
        data["name"] = "Existing Candidate"
        current = self.target.save_profile(json.dumps(data).encode())
        self.target.restore(self.backup)
        self.assertEqual(self.target.active_profile()["id"], current)
        self.target.activate_profile(self.active)
        self.assertEqual(self.target.active_profile()["id"], self.active)

    def test_late_profile_conflict_rolls_back_job_inserts(self):
        self.target.restore(self.backup)
        data = synthetic_profile()
        data["name"] = "Different existing content"
        snapshot = json.dumps(data).encode()
        with closing(sqlite3.connect(self.target.path)) as db, db:
            db.execute("DELETE FROM jobs")
            db.execute("UPDATE career_profiles SET snapshot=?, snapshot_sha256=? WHERE id=?",
                       (snapshot, hashlib.sha256(snapshot).hexdigest(), self.first))
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.target.restore(self.backup)
        self.assertEqual(self.target.list_jobs(), [])

    def test_missing_resume_profile_or_bad_active_reference_is_rejected(self):
        original = json.loads(self.backup.read_bytes())
        for change in ({"career_profiles": []}, {"active_profile_id": "unknown"}):
            self.backup.write_text(json.dumps({**original, **change}), encoding="utf-8")
            with self.assertRaises(ValueError):
                self.target.restore(self.backup)
            self.assertEqual(self.target.list_jobs(), [])
            self.assertEqual(self.target.list_profiles(), [])

    def test_v2_restore_keeps_existing_profile_and_resume(self):
        self.target.restore(self.backup)
        original = json.loads(self.backup.read_bytes())
        legacy = {key: original[key] for key in ("jobs", "application_events")}
        legacy["format"] = "roleweave-backup-v2"
        self.backup.write_text(json.dumps(legacy), encoding="utf-8")
        self.target.restore(self.backup)
        self.assertEqual(self.target.active_profile()["id"], self.active)
        self.assertEqual(len(self.target.list_resumes()), 1)
