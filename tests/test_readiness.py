import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from safe_export import publish_bytes

from job_store import JobStore
from roleweave import review_snapshot


class ReadinessTests(unittest.TestCase):
    def test_job_order_is_explicit_stable_and_keeps_undated_followups_last(self):
        second = self.store.save(self.source, "Analyst", "Zulu Co")
        self.store.record_application(second, "saved", "", "2026-12-03")
        self.assertEqual(self.store.list_jobs(sort="title")[0]["id"], second)
        self.assertEqual(self.store.list_jobs(sort="company")[0]["id"], self.job)
        self.assertEqual(self.store.list_jobs(sort="follow_up")[0]["id"], second)
        with self.assertRaises(ValueError):
            self.store.list_jobs(sort="sql injection")

    def test_source_links_never_launch_files_credentials_or_custom_schemes(self):
        from source_links import source_link
        self.assertEqual(source_link("https://example.invalid/jobs/123"), "https://example.invalid/jobs/123")
        for value in ("file:///C:/x.exe", "javascript:alert(1)", "https://user:secret@example.invalid", "https://example.invalid\n", "https://example.invalid:bad", ""):
            with self.assertRaises(ValueError):
                source_link(value)

    def test_posting_search_is_explicit_and_checks_exact_saved_source(self):
        self.assertEqual(self.store.list_jobs(query="Spark"), [])
        self.assertEqual(self.store.list_jobs(query="SPARK", search_posting=True)[0]["id"], self.job)
        with self.assertRaises(ValueError):
            self.store.list_jobs(search_posting="yes")

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

    def test_exports_publish_only_complete_bytes_and_never_clobber(self):
        output = self.folder / "review.json"
        with patch("safe_export.os.fsync", side_effect=OSError("synthetic disk error")):
            with self.assertRaises(OSError):
                self.store.export(self.job, output)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.folder.glob(".roleweave-*")), [])
        self.store.export(self.job, output)
        self.assertEqual(output.read_bytes(), self.source)
        with self.assertRaises(FileExistsError):
            publish_bytes(output, b"replacement")
        self.assertEqual(output.read_bytes(), self.source)

    def test_failed_package_promotion_restores_previous_complete_app(self):
        import os
        from build_windows import promote_package
        live, staged = self.folder / "live", self.folder / "new"
        live.mkdir()
        staged.mkdir()
        (live / "app").write_text("old")
        (staged / "app").write_text("new")
        replace = os.replace
        def fail_new(source, destination):
            if Path(source) == staged:
                raise PermissionError("Synthetic locked app")
            return replace(source, destination)
        with patch("build_windows.os.replace", side_effect=fail_new):
            with self.assertRaises(PermissionError):
                promote_package(staged, live)
        self.assertEqual((live / "app").read_text(), "old")
        self.assertEqual((staged / "app").read_text(), "new")
