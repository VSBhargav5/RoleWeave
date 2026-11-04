from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from calendar_export import follow_up_calendar
from job_store import JobStore


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        source = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.identifier = self.store.save(source, "Engineer తెలుగు " * 12 + "\nATTENDEE:fake", "Synthetic; Co, \\ team")

    def test_all_day_exclusive_end_stable_uid_no_invitation_or_private_notes(self):
        self.store.record_application(self.identifier, "applied", "PRIVATE_NOTE_NOT_EXPORTED", "2026-12-31")
        item, events = self.store.load(self.identifier), self.store.application_history(self.identifier)
        first = follow_up_calendar(item, events)
        self.assertEqual(first, follow_up_calendar(item, events))
        lines = first.decode().replace("\r\n ", "").split("\r\n")
        self.assertIn("DTSTART;VALUE=DATE:20261231", lines)
        self.assertIn("DTEND;VALUE=DATE:20270101", lines)
        self.assertIn("SEQUENCE:1", lines)
        self.assertFalse(any(line.startswith(("ATTENDEE:", "ORGANIZER:", "METHOD:")) for line in lines))
        self.assertNotIn("PRIVATE_NOTE_NOT_EXPORTED", first.decode())
        self.assertIn("\\nATTENDEE:fake", "".join(lines))
        self.assertIn("Synthetic\\; Co\\, \\\\ team", "".join(lines))
        for line in first.split(b"\r\n"):
            self.assertLessEqual(len(line), 75)
            line.decode("utf-8")
        uid = next(line for line in lines if line.startswith("UID:"))
        self.store.record_application(self.identifier, "interview", "", "2027-01-02")
        second = follow_up_calendar(item, self.store.application_history(self.identifier)).decode().replace("\r\n ", "")
        self.assertIn(uid, second)
        self.assertIn("SEQUENCE:2", second)

    def test_absent_terminal_or_out_of_range_dates_and_wrong_history_fail(self):
        with self.assertRaises(ValueError):
            self.store.export_follow_up(self.identifier, self.folder / "out.ics")
        self.store.record_application(self.identifier, "closed", "", "2026-12-03")
        with self.assertRaises(ValueError):
            self.store.export_follow_up(self.identifier, self.folder / "out.ics")
        self.store.record_application(self.identifier, "applied", "", "9999-12-31")
        with self.assertRaises(ValueError):
            self.store.export_follow_up(self.identifier, self.folder / "out.ics")
        self.assertFalse((self.folder / "out.ics").exists())

    def test_new_file_only_extension_and_changed_source_checks(self):
        self.store.record_application(self.identifier, "applied", "", "2026-12-03")
        path = self.folder / "out.ics"
        self.store.export_follow_up(self.identifier, path)
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.store.export_follow_up(self.identifier, path)
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(ValueError):
            self.store.export_follow_up(self.identifier, self.folder / "out.exe")
        item = self.store.load(self.identifier)
        item["input_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            follow_up_calendar(item, self.store.application_history(self.identifier))

    def test_early_year_keeps_four_digits_and_foreign_history_is_rejected(self):
        self.store.record_application(self.identifier, "saved", "", "0001-01-01")
        item = self.store.load(self.identifier)
        events = self.store.application_history(self.identifier)
        self.assertIn(b"DTSTART;VALUE=DATE:00010101", follow_up_calendar(item, events))
        with self.assertRaises(ValueError):
            follow_up_calendar(item, [{**events[0], "job_id": "other"}])

    @unittest.skipUnless(os.name == "nt", "Native Windows calendar export")
    def test_tracker_refuses_unsaved_date_then_exports_saved_observation(self):
        import tkinter as tk
        from application_tracker import ApplicationTracker
        root = tk.Tk()
        root.withdraw()
        try:
            tracker = ApplicationTracker(root, self.store, self.identifier, lambda _id: None)
            tracker.withdraw()
            tracker.follow_up.set("2026-12-03")
            path = self.folder / "ui.ics"
            with patch("application_tracker.filedialog.asksaveasfilename", return_value=str(path)) as dialog:
                tracker.export_calendar()
                dialog.assert_not_called()
                tracker.record()
                tracker.export_calendar()
            self.assertTrue(path.read_bytes().startswith(b"BEGIN:VCALENDAR\r\n"))
        finally:
            root.update_idletasks()
            root.destroy()
