from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from job_store import JobStore, SCHEMA, SCHEMA_APPLICATION_ID, SCHEMA_VERSION


class SchemaCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "shelf.db"

    def execute(self, statements):
        with closing(sqlite3.connect(self.path)) as db, db:
            for statement in statements:
                db.execute(statement)

    def refused_unchanged(self):
        before = self.path.read_bytes()
        with self.assertRaises((ValueError, sqlite3.DatabaseError)):
            JobStore(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_known_legacy_jobs_only_upgrade_preserves_original_rows(self):
        self.execute([SCHEMA[0]])
        original = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        # Populate the real original jobs schema without invoking the new initializer.
        from roleweave import review_snapshot
        digest = review_snapshot(original)["input_sha256"]
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       ("legacy", "Data Engineer", "Synthetic", "", "india_remote", "2026-11-12T00:00:00+00:00", digest, original))
        store = JobStore(self.path)
        self.assertEqual(store.load("legacy")["snapshot"], original)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("PRAGMA application_id").fetchone()[0], SCHEMA_APPLICATION_ID)
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], SCHEMA_VERSION)
        before = self.path.read_bytes()
        self.assertEqual(JobStore(self.path).load("legacy")["snapshot"], original)
        self.assertEqual(self.path.read_bytes(), before)

    def test_new_shelf_and_full_unversioned_legacy_are_supported(self):
        for statements in ([], list(SCHEMA)):
            with self.subTest(statements=len(statements)):
                self.path.unlink(missing_ok=True)
                self.execute(statements)
                self.assertEqual(JobStore(self.path).list_jobs(), [])

    def test_future_schema_and_foreign_file_identity_are_not_changed(self):
        for marker in ("PRAGMA user_version=2", "PRAGMA application_id=12345"):
            with self.subTest(marker=marker):
                self.path.unlink(missing_ok=True)
                self.execute([SCHEMA[0], marker])
                self.refused_unchanged()

    def test_foreign_database_and_extra_schema_objects_are_not_adopted(self):
        for extra in ("CREATE TABLE other (id TEXT)",
                      "CREATE VIEW all_jobs AS SELECT * FROM jobs",
                      "CREATE TRIGGER extra AFTER INSERT ON jobs BEGIN DELETE FROM jobs; END",
                      "CREATE INDEX extra ON jobs(title)"):
            with self.subTest(extra=extra):
                self.path.unlink(missing_ok=True)
                self.execute([SCHEMA[0], extra])
                self.refused_unchanged()
        self.path.unlink()
        self.execute(["CREATE TABLE other (id TEXT)"])
        self.refused_unchanged()

    def test_altered_constraints_and_partial_tagged_schema_are_refused(self):
        self.execute([SCHEMA[0].replace("UNIQUE(title, company, source_url, input_sha256)", "UNIQUE(title)")])
        self.refused_unchanged()
        self.path.unlink()
        self.execute([SCHEMA[0], f"PRAGMA application_id={SCHEMA_APPLICATION_ID}", f"PRAGMA user_version={SCHEMA_VERSION}"])
        self.refused_unchanged()

    def test_corrupt_database_is_preserved_without_reinitialization(self):
        self.path.write_bytes(b"not a SQLite database; preserve this evidence")
        self.refused_unchanged()

    def test_failed_adoption_rolls_back_schema_and_header(self):
        self.execute([SCHEMA[0]])
        before = self.path.read_bytes()
        from unittest.mock import patch
        original_connect = sqlite3.connect
        class FailingConnection(sqlite3.Connection):
            def execute(self, statement, *args):
                if statement == SCHEMA[2]:
                    raise sqlite3.OperationalError("synthetic interruption after earlier DDL")
                return super().execute(statement, *args)
        def connect(path, *args, **kwargs):
            if str(path) != ":memory:":
                kwargs["factory"] = FailingConnection
            return original_connect(path, *args, **kwargs)
        with patch("job_store.sqlite3.connect", side_effect=connect):
            with self.assertRaisesRegex(sqlite3.Error, "synthetic interruption"):
                JobStore(self.path)
        self.assertEqual(self.path.read_bytes(), before)
