import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest

from job_store import JobStore
from rehearsal_journal import make_rehearsal, rehearsal_snapshot, export_rehearsal, read_rehearsal


class RehearsalJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.item = self.store.load(self.job)
        self.answers = [{"requirement_id": "python", "answer": "My draft about a CSV project.", "reflection": "Explain error handling."},
                        {"requirement_id": "spark", "answer": "", "reflection": "Open review question."}]

    def make(self, **options):
        return make_rehearsal(self.item, options.get("answers", self.answers),
                              elapsed_seconds=options.get("seconds", 0), confirmed=options.get("confirmed", True))

    def test_private_version_keeps_exact_source_and_never_verifies_learning(self):
        record, _digest = rehearsal_snapshot(self.make(seconds=90))
        self.assertEqual(base64.b64decode(record["job_context"]["snapshot_base64"]), self.item["snapshot"])
        self.assertEqual(record["answers"], self.answers)
        self.assertFalse(record["learning_verified"])
        self.assertEqual(record["elapsed_seconds"], 90)
        changed = json.loads(self.item["snapshot"])
        changed["posting"] += " New provider text."
        other = self.store.save(json.dumps(changed).encode(), "Engineer", "Synthetic")
        self.assertNotEqual(record["job_context"]["input_sha256"], self.store.load(other)["input_sha256"])

    def test_unknown_duplicate_oversized_and_unconfirmed_drafts_fail(self):
        for options in ({"confirmed": False}, {"seconds": True}, {"seconds": -1}, {"seconds": 86401},
                        {"answers": []}, {"answers": self.answers * 2},
                        {"answers": [{"requirement_id": "missing", "answer": "", "reflection": ""}]},
                        {"answers": [{"requirement_id": "python", "answer": "x" * 6001, "reflection": ""}]}):
            with self.assertRaises(ValueError):
                self.make(**options)

    def test_changed_source_or_learning_claim_is_rejected(self):
        original = json.loads(self.make())
        for change in (lambda r: r.update(learning_verified=True),
                       lambda r: r["job_context"].update(input_sha256="0" * 64),
                       lambda r: r.update(recorded_at="2026-11-11"),
                       lambda r: r["answers"][0].update(score=100)):
            record = copy.deepcopy(original)
            change(record)
            with self.assertRaises(ValueError):
                rehearsal_snapshot(json.dumps(record).encode())

    def test_no_overwrite_roundtrip_requires_explicit_export(self):
        path = self.folder / "journal.json"
        snapshot = self.make()
        with self.assertRaises(ValueError):
            export_rehearsal(snapshot, path)
        self.assertFalse(path.exists())
        export_rehearsal(snapshot, path, confirmed=True)
        self.assertEqual(read_rehearsal(path)[0], snapshot)
        with self.assertRaises(FileExistsError):
            export_rehearsal(snapshot, path, confirmed=True)
