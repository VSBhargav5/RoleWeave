import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from google_calendar_sync import prepare_sync


@unittest.skipUnless(os.name == "nt", "Native Windows Calendar review")
class GoogleCalendarUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.store.record_application(self.job, "shortlisted", "PRIVATE NOTE", "2026-12-03")
        self.root = tk.Tk(); self.root.withdraw(); self.addCleanup(self.root.destroy)
        self.shelf = JobShelf(self.root, self.store); self.shelf.show_saved(self.job)
        self.window = self.shelf.open_google_calendar(); self.window.withdraw()

    def test_open_and_local_preview_never_connect_or_transmit_and_remote_requires_consent(self):
        before = self.store.path.read_bytes()
        with patch("google_calendar_window.connect_session") as connect, patch("google_calendar_window.read_remote") as read, patch.object(self.window.task, "start") as start:
            self.window.local_preview()
            self.window.connect()
            self.window.prepare()
            self.window.send()
            connect.assert_not_called(); read.assert_not_called(); start.assert_not_called()
        payload = self.window.preview.get("1.0", "end")
        self.assertIn("RoleWeave follow-up", payload)
        self.assertNotIn("PRIVATE NOTE", payload)
        self.assertEqual(self.store.path.read_bytes(), before)

    def test_input_changes_cancel_preview_and_send_is_one_shot(self):
        plan = prepare_sync(self.store.load(self.job), self.store.application_history(self.job), "synthetic@group.calendar.google.com")
        self.window.prepared((plan, None))
        self.window.write_consent.set(True)
        self.window.include_details.set(True)
        self.assertIsNone(self.window.plan)
        self.assertFalse(self.window.write_consent.get())
        self.window.prepared((plan, None)); self.window.write_consent.set(True)
        with patch.object(self.window.task, "start") as start:
            self.window.send()
            self.window.send()
        self.assertEqual(start.call_count, 1)
        self.assertIsNone(self.window.plan)
        self.window.client_secret.set("SYNTHETIC_SECRET")
        self.window.disconnect()
        self.assertIsNone(self.window.credentials)
        self.assertEqual(self.window.client_secret.get(), "")

    def test_minimum_size_keeps_footer_and_review_readable(self):
        from tkinter import ttk
        self.root.deiconify(); self.window.deiconify(); self.window.geometry("800x650")
        for index in (0, 1):
            self.window.tabs.select(index); self.window.update()
            if index == 1: self.assertGreaterEqual(self.window.preview.winfo_height(), 90)
            def walk(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from walk(child)
            for button in walk(self.window):
                if isinstance(button, ttk.Button) and button.winfo_ismapped():
                    self.assertGreaterEqual(button.winfo_height(), 28)
                    self.assertLessEqual(button.winfo_rooty() - self.window.winfo_rooty() + button.winfo_height(), self.window.winfo_height())
