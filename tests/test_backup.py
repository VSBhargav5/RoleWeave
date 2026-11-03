import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "source.db")
        self.target = JobStore(self.folder / "target.db")
        self.source = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.identifier = self.store.save(self.source, "Engineer తెలుగు", "Synthetic Co", "https://example.invalid/job")
        data = json.loads(self.source)
        data["market"] = "relocation"
        self.store.save(json.dumps(data).encode(), "International", "Other Co")
        self.backup = self.folder / "shelf.json"
        self.store.backup(self.backup)

    def rewrite(self, data):
        self.backup.write_text(json.dumps(data), encoding="utf-8")

    def test_full_restore_preserves_bytes_metadata_ids_times_and_markets(self):
        self.assertEqual(self.target.restore(self.backup), (2, 0))
        self.assertEqual(self.target.list_jobs(), self.store.list_jobs())
        self.assertEqual(self.target.load(self.identifier), self.store.load(self.identifier))
        self.assertEqual(len(self.target.list_jobs("relocation")), 1)
        self.assertEqual(JobStore(self.folder / "target.db").load(self.identifier)["snapshot"], self.source)

    def test_repeat_restore_skips_duplicates_without_overwriting(self):
        self.target.restore(self.backup)
        before = self.target.list_jobs()
        self.assertEqual(self.target.restore(self.backup), (0, 2))
        self.assertEqual(before, self.target.list_jobs())

    def test_same_content_under_different_id_is_not_duplicated(self):
        self.target.save(self.source, "Engineer తెలుగు", "Synthetic Co", "https://example.invalid/job")
        self.assertEqual(self.target.restore(self.backup), (1, 1))
        self.assertEqual(len(self.target.list_jobs()), 2)

    def test_late_id_conflict_rolls_back_earlier_insert(self):
        data = json.loads(self.backup.read_bytes())
        conflict = data["jobs"][-1]
        self.target.restore(self.backup)
        # Keep only the conflicting ID in a fresh target, with changed metadata.
        self.target = JobStore(self.folder / "conflict.db")
        original = {"format": data["format"], "jobs": [conflict], "application_events": []}
        self.rewrite(original)
        self.target.restore(self.backup)
        data["jobs"][-1] = {**conflict, "company": "Conflicting company"}
        self.rewrite(data)
        before = self.target.list_jobs()
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.target.restore(self.backup)
        self.assertEqual(self.target.list_jobs(), before)

    def test_tamper_bad_time_encoding_market_or_fields_do_not_restore(self):
        original = json.loads(self.backup.read_bytes())
        changes = ({"input_sha256": "0" * 64}, {"snapshot_base64": "!!!"},
                   {"captured_at": "2026-11-03"}, {"market": "unknown"}, {"extra": "unsupported"},
                   {"snapshot_base64": base64.b64encode(b"{}").decode()})
        for change in changes:
            with self.subTest(change=change):
                data = json.loads(json.dumps(original))
                data["jobs"][-1].update(change)
                self.rewrite(data)
                with self.assertRaises(ValueError):
                    self.target.restore(self.backup)
                self.assertEqual(self.target.list_jobs(), [])

    def test_bad_json_duplicate_keys_duplicate_ids_and_versions_fail(self):
        original = json.loads(self.backup.read_bytes())
        duplicate = {**original, "jobs": [original["jobs"][0]] * 2}
        cases = (b"bad", b'{"format":"a","format":"b","jobs":[]}',
                 json.dumps(duplicate).encode(), b'{"format":"future-version","jobs":[]}', b"[]")
        for payload in cases:
            self.backup.write_bytes(payload)
            with self.assertRaises(ValueError):
                self.target.restore(self.backup)
            self.assertEqual(self.target.list_jobs(), [])

    def test_backup_refuses_overwrite_and_limits_before_creation(self):
        before = self.backup.read_bytes()
        with self.assertRaises(FileExistsError):
            self.store.backup(self.backup)
        self.assertEqual(self.backup.read_bytes(), before)
        destination = self.folder / "too-large.json"
        with patch("job_store.MAX_BACKUP_BYTES", 10):
            with self.assertRaises(ValueError):
                self.store.backup(destination)
            with self.assertRaises(ValueError):
                self.target.restore(self.backup)
        self.assertFalse(destination.exists())
        self.assertEqual(self.target.list_jobs(), [])

    def test_empty_shelf_round_trips(self):
        empty = self.folder / "empty.json"
        self.assertEqual(self.target.backup(empty), 0)
        self.assertEqual(self.target.restore(empty), (0, 0))

    def test_v2_round_trip_preserves_application_history_and_repeat_restore(self):
        event = self.store.record_application(self.identifier, "shortlisted", "Check remote scope", "2026-12-04")
        self.store.record_application(self.identifier, "applied", "Manual observation", "")
        self.backup.unlink()
        self.store.backup(self.backup)
        self.target.restore(self.backup)
        self.assertEqual(self.target.application_history(self.identifier), self.store.application_history(self.identifier))
        self.target.restore(self.backup)
        self.assertEqual(len(self.target.application_history(self.identifier)), 2)
        self.assertEqual(self.target.application_history(self.identifier)[0], event)

    def test_v1_backups_remain_readable_without_erasing_current_history(self):
        data = json.loads(self.backup.read_bytes())
        data["format"] = "roleweave-backup-v1"
        del data["application_events"]
        self.rewrite(data)
        self.target.restore(self.backup)
        event = self.target.record_application(self.identifier, "interview", "Recorded by user")
        self.target.restore(self.backup)
        self.assertEqual(self.target.application_history(self.identifier), [event])

    def test_conflicting_event_rolls_back_new_job_inserts(self):
        self.store.record_application(self.identifier, "shortlisted")
        self.backup.unlink()
        self.store.backup(self.backup)
        full = json.loads(self.backup.read_bytes())
        self.rewrite({**full, "jobs": [job for job in full["jobs"] if job["id"] == self.identifier]})
        self.target.restore(self.backup)
        before = self.target.list_jobs()
        full["application_events"][0]["note"] = "Conflicting edit to historical observation"
        self.rewrite(full)
        with self.assertRaisesRegex(ValueError, "event ID conflict"):
            self.target.restore(self.backup)
        self.assertEqual(self.target.list_jobs(), before)
        self.assertEqual(self.target.application_history(self.identifier)[0]["note"], "")

    def test_orphan_or_gapped_events_are_rejected_before_writes(self):
        event = self.store.record_application(self.identifier, "saved")
        original = json.loads(self.backup.read_bytes())
        for change in ({"job_id": "orphan"}, {"revision": 3}, {"stage": "auto_applied"}):
            self.rewrite({**original, "application_events": [{**event, **change}]})
            with self.assertRaises(ValueError):
                self.target.restore(self.backup)
            self.assertEqual(self.target.list_jobs(), [])

    def test_history_follows_identical_job_when_local_id_differs(self):
        local_id = self.target.save(self.source, "Engineer తెలుగు", "Synthetic Co", "https://example.invalid/job")
        self.store.record_application(self.identifier, "shortlisted", "Reviewed manually")
        self.backup.unlink()
        self.store.backup(self.backup)
        self.target.restore(self.backup)
        self.assertEqual(self.target.application_history(local_id)[0]["stage"], "shortlisted")
        self.target.restore(self.backup)
        self.assertEqual(len(self.target.application_history(local_id)), 1)

    def test_divergent_revision_does_not_merge_unrelated_observations(self):
        self.target.restore(self.backup)
        original = self.target.record_application(self.identifier, "applied", "Local observation")
        self.store.record_application(self.identifier, "shortlisted", "Different history")
        self.backup.unlink()
        self.store.backup(self.backup)
        with self.assertRaisesRegex(ValueError, "diverges"):
            self.target.restore(self.backup)
        self.assertEqual(self.target.application_history(self.identifier), [original])
