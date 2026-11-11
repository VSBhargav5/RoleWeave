from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from shelf_audit import audit_database, export_audit
from test_profile import synthetic_profile


class ShelfAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.path = self.folder / "jobs.db"
        self.store = JobStore(self.path)
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.profile = self.store.save_profile(json.dumps(synthetic_profile()).encode())
        self.resume = self.store.create_resume(self.profile, ["project-python"], "Synthetic selection", self.job, False, True)
        self.store.record_application(self.job, "shortlisted", "PRIVATE NOTE")

    def alter(self, sql, parameters=()):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(sql, parameters)

    def test_success_is_read_only_and_report_omits_source_claims_and_notes(self):
        before = self.path.read_bytes()
        report = audit_database(self.path)
        self.assertTrue(report["ok"])
        self.assertEqual(report["counts"]["resume_versions"], 1)
        self.assertEqual(before, self.path.read_bytes())
        self.assertNotIn("PRIVATE NOTE", json.dumps(report))
        self.assertNotIn("CSV reconciliation", json.dumps(report))
        output = self.folder / "audit.json"
        with self.assertRaises(ValueError):
            export_audit(report, output)
        export_audit(report, output, confirmed=True)
        with self.assertRaises(FileExistsError):
            export_audit(report, output, confirmed=True)

    def test_valid_sqlite_can_have_changed_review_bytes_and_broken_references(self):
        self.alter("UPDATE jobs SET snapshot=? WHERE id=?", (b"{}", self.job))
        self.alter("UPDATE app_settings SET value='missing' WHERE key='active_profile'")
        report = audit_database(self.path)
        codes = {row["code"] for row in report["issues"]}
        self.assertFalse(report["ok"])
        self.assertTrue({"invalid_source_or_metadata", "job_reference_mismatch", "job_reference_unavailable", "profile_reference_unavailable"} <= codes)

    def test_missing_profile_and_history_revision_gap_are_detected(self):
        self.alter("DELETE FROM career_profiles WHERE id=?", (self.profile,))
        self.alter("UPDATE application_events SET revision=2")
        codes = {row["code"] for row in audit_database(self.path)["issues"]}
        self.assertTrue({"profile_reference_mismatch", "invalid_events_or_revision_sequence"} <= codes)

    def test_self_consistent_resume_context_must_match_actual_saved_job_metadata(self):
        record = json.loads(self.store.load_resume(self.resume)["snapshot"])
        record["job_context"]["title"] = "Another frozen title"
        snapshot = json.dumps(record).encode()
        self.alter("UPDATE resume_versions SET snapshot=?,snapshot_sha256=? WHERE id=?", (snapshot, hashlib.sha256(snapshot).hexdigest(), self.resume))
        self.assertIn("job_reference_mismatch", {row["code"] for row in audit_database(self.path)["issues"]})

    def test_bounds_and_missing_or_corrupt_database_fail_without_writes(self):
        before = self.path.read_bytes()
        for name in ("MAX_AUDIT_ROWS", "MAX_AUDIT_BYTES"):
            with patch("shelf_audit." + name, 1):
                with self.assertRaises(ValueError):
                    audit_database(self.path)
        self.assertEqual(before, self.path.read_bytes())
        missing = self.folder / "missing.db"
        with self.assertRaises(ValueError):
            audit_database(missing)
        self.assertFalse(missing.exists())
        broken = self.folder / "broken.db"
        broken.write_bytes(b"not sqlite")
        with self.assertRaises(ValueError):
            audit_database(broken)
        self.assertEqual(broken.read_bytes(), b"not sqlite")
