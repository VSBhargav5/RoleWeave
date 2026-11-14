import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from job_store import JobStore
from background_task import BackgroundTask


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows reviewed AI workflow")
class AIUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update_idletasks)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        source = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        identifier = self.store.save(source, "Synthetic Engineer", "Synthetic Co")
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.show_saved(identifier)
        self.editor = self.shelf.edit_evidence()
        self.editor.withdraw()
        self.window = self.editor.open_ai()
        self.window.withdraw()

    def test_no_automatic_send_session_key_and_reviewed_unlinked_draft(self):
        with patch.object(self.window.task, "start") as start:
            self.window.send()
            start.assert_not_called()
            self.window.consent.set(True)
            self.window.send()
            start.assert_not_called()
            self.window.key.set("synthetic-key-not-real")
            self.window.send()
            start.assert_called_once()
        self.assertFalse(self.window.consent.get())
        self.assertNotIn("synthetic-key", self.window.payload_view.get("1.0", "end"))
        before = len(self.editor.data["requirements"])
        self.window.received(["Spark operations required."])
        self.window.quotes.selection_set(0)
        self.window.accept()
        self.assertTrue(self.window.winfo_exists())
        self.window.reviewed.set(True)
        self.window.accept()
        self.assertEqual(self.window.key.get(), "")
        self.assertEqual(len(self.store.list_jobs()), 1)
        self.assertEqual(len(self.editor.data["requirements"]), before + 1)
        self.assertEqual(self.editor.data["requirements"][-1]["fact_ids"], [])

    def test_cancel_and_source_change_do_not_accept_proposals(self):
        self.window.received(["Python required."])
        self.window.quotes.selection_set(0)
        self.window.reviewed.set(True)
        before = json.dumps(self.editor.data)
        self.editor.data["posting"] += " Changed."
        self.window.accept()
        self.assertIn("Posting changed", self.window.status.get())
        self.window.cancel()
        self.assertFalse(self.window.consent.get())
        self.assertEqual(len(self.store.list_jobs()), 1)

    def test_background_cancel_discards_late_work_and_later_request_completes(self):
        task = BackgroundTask(self.root)
        release, started = threading.Event(), threading.Event()
        values, errors = [], []
        def work(event):
            started.set()
            release.wait(2)
            return "late private output"
        task.start(work, values.append, errors.append)
        self.assertTrue(started.wait(1))
        task.cancel()
        release.set()
        task.start(lambda event: "current result", values.append, errors.append)
        deadline = time.monotonic() + 2
        while task.active is not None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertEqual(values, ["current result"])
        self.assertEqual(errors, [])
