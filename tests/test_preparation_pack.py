import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from preparation_pack import build_pack


class PreparationPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        data = json.loads((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes())
        data["facts"].append({"id": "private-unselected", "claim": "UNSELECTED_PRIVATE_NOTE",
                              "source": "Unreviewed source", "reviewed": False})
        self.job = self.store.save(json.dumps(data).encode(), "Engineer తెలుగు", "Synthetic Co")
        self.output = self.folder / "pack.txt"

    def test_only_selected_claims_are_copied_and_open_requirements_remain_questions(self):
        self.store.export_preparation_pack(self.job, self.output)
        contents = self.output.read_text(encoding="utf-8")
        self.assertIn("Engineer తెలుగు", contents)
        self.assertIn("Built a Python CSV reconciliation exercise", contents)
        self.assertIn("Production Spark operations required.", contents)
        self.assertIn("needs_review", contents)
        self.assertNotIn("UNSELECTED_PRIVATE_NOTE", contents)
        self.assertIn(self.store.load(self.job)["input_sha256"], contents)
        self.assertIn("Not a submitted application", contents)

    def test_same_source_and_history_give_identical_bytes_and_stage_is_manual(self):
        self.store.record_application(self.job, "applied", "Human-recorded observation", "2026-12-03")
        item = self.store.load(self.job)
        events = self.store.application_history(self.job)
        self.assertEqual(build_pack(item, events), build_pack(item, events))
        output = build_pack(item, events).decode()
        self.assertIn("History revision included\n  1", output)
        self.assertIn("Manual stage\n  applied", output)
        self.assertIn("Human-recorded observation", output)

    def test_overwrite_is_refused_and_tampered_source_is_not_exported(self):
        self.output.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            self.store.export_preparation_pack(self.job, self.output)
        self.assertEqual(self.output.read_bytes(), b"keep")
        item = self.store.load(self.job)
        item["input_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            build_pack(item, [])

    def test_foreign_tracking_history_is_rejected(self):
        event = self.store.record_application(self.job, "saved", "Manual note")
        event["job_id"] = "another-job"
        with self.assertRaises(ValueError):
            build_pack(self.store.load(self.job), [event])

    def test_size_limit_fails_before_file_creation(self):
        with patch("preparation_pack.MAX_PACK_BYTES", 10):
            with self.assertRaises(ValueError):
                self.store.export_preparation_pack(self.job, self.output)
        self.assertFalse(self.output.exists())
