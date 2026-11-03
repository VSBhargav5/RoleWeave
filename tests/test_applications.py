from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from applications import current_application
from job_store import JobStore


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "jobs.db"
        self.store = JobStore(self.path)
        self.snapshot = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.job = self.store.save(self.snapshot, "Engineer", "Synthetic")

    def test_default_stage_and_append_only_history_survive_reopen(self):
        self.assertEqual(current_application(self.store.application_history(self.job))["stage"], "saved")
        first = self.store.record_application(self.job, "shortlisted", "Check authorization first", "2026-12-03")
        second = self.store.record_application(self.job, "applied", "Manually recorded; not proof of submission", "")
        reopened = JobStore(self.path)
        self.assertEqual(reopened.application_history(self.job), [first, second])
        self.assertEqual(current_application([first, second])["follow_up"], "")
        self.assertEqual(self.store.load(self.job)["snapshot"], self.snapshot)

    def test_bad_stage_date_note_or_unknown_job_do_not_write(self):
        for stage, note, follow_up in (("auto_applied", "", ""), ("saved", "x" * 4001, ""),
                                      ("saved", "", "2026-02-30"), ("saved", "", "20261203"),
                                      ("saved", "", None), ("saved", 1, "")):
            with self.assertRaises(ValueError):
                self.store.record_application(self.job, stage, note, follow_up)
        with self.assertRaises(ValueError):
            self.store.record_application("unknown", "applied")
        self.assertEqual(self.store.application_history(self.job), [])

    def test_new_review_does_not_inherit_applied_status(self):
        self.store.record_application(self.job, "applied")
        data = json.loads(self.snapshot)
        data["posting"] += " New role details."
        other = self.store.save(json.dumps(data).encode(), "Engineer", "Synthetic")
        self.assertEqual(current_application(self.store.application_history(other))["stage"], "saved")

    def test_correction_is_new_event_and_clock_does_not_order_history(self):
        first = self.store.record_application(self.job, "applied", "Incorrect entry")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE application_events SET recorded_at='2099-01-01T00:00:00+00:00' WHERE id=?", (first["id"],))
        self.store.record_application(self.job, "shortlisted", "Correcting previous entry")
        events = self.store.application_history(self.job)
        self.assertEqual(len(events), 2)
        self.assertEqual(current_application(events)["stage"], "shortlisted")

    def test_tampered_history_gap_fails_closed(self):
        event = self.store.record_application(self.job, "saved")
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE application_events SET revision=3 WHERE id=?", (event["id"],))
        with self.assertRaises(ValueError):
            self.store.application_history(self.job)
        with self.assertRaises(ValueError):
            self.store.record_application(self.job, "applied")
