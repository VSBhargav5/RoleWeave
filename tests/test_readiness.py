import copy
import json
from pathlib import Path
import tempfile
import unittest

from job_store import JobStore
from roleweave import review_snapshot


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.source = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.job = self.store.save(self.source, "Synthetic Engineer", "Example Co")

    def test_invalid_unicode_and_controls_fail_before_storage(self):
        for value in ("bad\ud800", "bad\x00"):
            data = json.loads(self.source)
            data["facts"][0]["claim"] = value
            with self.assertRaises(ValueError):
                self.store.save(json.dumps(data).encode(), "Role", "Co")
            with self.assertRaises(ValueError):
                self.store.record_application(self.job, "saved", value)
        self.assertEqual(len(self.store.list_jobs()), 1)
        self.assertEqual(self.store.application_history(self.job), [])
