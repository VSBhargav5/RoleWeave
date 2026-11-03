from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from job_store import JobStore
from roleweave import MAX_BYTES


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "jobs.db"
        self.store = JobStore(self.path)
        self.snapshot = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()

    def save(self, snapshot=None):
        return self.store.save(self.snapshot if snapshot is None else snapshot, "Data Engineer", "Synthetic Ltd")

    def test_reopen_preserves_exact_original_bytes_and_evidence(self):
        identifier = self.save()
        item = JobStore(self.path).load(identifier)
        self.assertEqual(item["snapshot"], self.snapshot)
        self.assertEqual(item["review"]["requirements"][1]["state"], "needs_review")
        self.assertEqual(item["title"], "Data Engineer")

    def test_markets_stay_separate_and_unknown_filter_fails(self):
        self.save()
        data = json.loads(self.snapshot)
        data["market"] = "relocation"
        self.save(json.dumps(data).encode())
        self.assertEqual(len(self.store.list_jobs()), 2)
        for market in ("india_remote", "relocation"):
            self.assertEqual(len(self.store.list_jobs(market)), 1)
            self.assertEqual(self.store.list_jobs(market)[0]["market"], market)
        with self.assertRaises(ValueError):
            self.store.list_jobs("global")

    def test_invalid_review_leaves_store_unchanged(self):
        for invalid in (b"bad", b"x" * (MAX_BYTES + 1), self.snapshot.replace(b"Python required.", b"Invented quote.", 1)):
            with self.assertRaises(ValueError):
                self.save(invalid)
        self.assertEqual(self.store.list_jobs(), [])

    def test_duplicate_rejected_and_missing_job_fails(self):
        self.save()
        with self.assertRaisesRegex(ValueError, "already saved"):
            self.save()
        self.assertEqual(len(self.store.list_jobs()), 1)
        with self.assertRaises(ValueError):
            self.store.load("unknown")

    def test_parameterized_metadata_round_trips(self):
        title = "Robert'); DROP TABLE jobs;--"
        identifier = self.store.save(self.snapshot, title, "తెలుగు company", "https://example.invalid/job")
        self.assertEqual(self.store.load(identifier)["title"], title)
        self.assertEqual(len(self.store.list_jobs()), 1)

    def test_export_is_exact_refuses_overwrite_and_can_reimport(self):
        identifier = self.save()
        destination = Path(self.temp.name) / "export.json"
        self.store.export(identifier, destination)
        self.assertEqual(destination.read_bytes(), self.snapshot)
        with self.assertRaises(FileExistsError):
            self.store.export(identifier, destination)
        other = JobStore(Path(self.temp.name) / "restored.db")
        restored = other.save(destination.read_bytes(), "Restored", "Synthetic")
        self.assertEqual(other.load(restored)["review"], self.store.load(identifier)["review"])

    def test_tampered_source_or_market_fails_closed(self):
        identifier = self.save()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE jobs SET market='relocation' WHERE id=?", (identifier,))
        with self.assertRaisesRegex(ValueError, "market"):
            self.store.load(identifier)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("UPDATE jobs SET snapshot=? WHERE id=?", (b"{}", identifier))
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.store.load(identifier)

    def test_metadata_validation(self):
        for title, company, url in (("", "company", ""), ("title", "", ""), ("title", "company", 123)):
            with self.assertRaises(ValueError):
                self.store.save(self.snapshot, title, company, url)
        self.assertEqual(self.store.list_jobs(), [])


if __name__ == "__main__":
    unittest.main()
