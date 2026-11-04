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
    def test_version_diff_reveals_source_change_without_inheriting_application_state(self):
        from review_history import review_difference
        self.store.record_application(self.job, "applied", "Original review only")
        data = json.loads(self.source)
        data["posting"] += " Additional source sentence."
        revised = self.store.save(json.dumps(data).encode(), "Synthetic Engineer", "Example Co")
        difference = review_difference(self.store.load(self.job), self.store.load(revised))
        self.assertIn("Additional source sentence", difference)
        self.assertEqual(self.store.application_history(revised), [])

    def test_bulk_calendar_has_one_container_and_only_active_dated_events(self):
        from workspace_exports import follow_up_list
        second = self.store.save(self.source, "Other", "Example")
        self.store.record_application(self.job, "applied", "private", "2026-12-03")
        self.store.record_application(second, "closed", "private", "2026-12-04")
        output = self.folder / "followups.ics"
        self.assertEqual(follow_up_list(self.store, self.store.list_jobs(), output), 1)
        content = output.read_bytes()
        self.assertEqual(content.count(b"BEGIN:VCALENDAR"), 1)
        self.assertEqual(content.count(b"BEGIN:VEVENT"), 1)
        self.assertNotIn(b"private", content)

    def test_filtered_csv_preserves_rows_escapes_formulas_and_omits_notes(self):
        import csv
        from workspace_exports import review_list_csv
        row = {**self.store.list_jobs()[0], "title": "  =HYPERLINK(\"bad\")", "decision_note": "PRIVATE"}
        path = self.folder / "list.csv"
        review_list_csv([row], path)
        rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
        self.assertEqual(rows[0]["title"], "'" + row["title"])
        self.assertNotIn("PRIVATE", path.read_text(encoding="utf-8-sig"))
        self.assertEqual(len(rows), 1)

    def test_backup_inspection_reports_counts_without_touching_live_shelf(self):
        self.store.record_application(self.job, "shortlisted", "Synthetic")
        path = self.folder / "backup.json"
        self.store.backup(path)
        before = self.store.path.read_bytes()
        counts = JobStore.inspect_backup(path)
        self.assertEqual(counts["saved_reviews"], 1)
        self.assertEqual(counts["history_entries"], 1)
        self.assertEqual(self.store.path.read_bytes(), before)

    def test_resume_job_filter_does_not_mix_general_or_other_review_versions(self):
        from test_profile import synthetic_profile
        profile = self.store.save_profile(json.dumps(synthetic_profile()).encode())
        specific = self.store.create_resume(profile, ["project-python"], "Role resume", self.job, False, True)
        self.store.create_resume(profile, ["project-python"], "General", include_pdf=False, confirmed=True)
        self.assertEqual([row["id"] for row in self.store.list_resumes(self.job)], [specific])
        self.assertEqual(len(self.store.list_resumes()), 2)

    def test_plain_resume_export_uses_frozen_selection_and_excludes_sources(self):
        from test_profile import synthetic_profile
        data = synthetic_profile()
        profile = self.store.save_profile(json.dumps(data).encode())
        resume = self.store.create_resume(profile, ["project-python"], "Synthetic", include_pdf=False, confirmed=True)
        path = self.folder / "resume.txt"
        self.store.export_resume(resume, path, "txt")
        contents = path.read_text(encoding="utf-8")
        self.assertIn(data["facts"][0]["claim"], contents)
        self.assertNotIn(data["facts"][0]["source"], contents)
        self.assertNotIn("Unreviewed draft", contents)

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
