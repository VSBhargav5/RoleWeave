import json
from pathlib import Path
import tempfile
import unittest
from discovery_archive import archive_bytes, export_archive, load_archive
from provider_boards import parse_source
from test_provider_boards import lever_fixture

class DiscoveryArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "board.json"
        self.feed = parse_source(json.dumps(lever_fixture()).encode(), "lever", "synthetic")

    def test_byte_exact_roundtrip_and_no_overwrite(self):
        export_archive(self.feed, self.path)
        self.assertEqual(load_archive(self.path), self.feed)
        with self.assertRaises(FileExistsError):
            export_archive(self.feed, self.path)

    def test_tampered_source_results_time_and_schema_fail(self):
        with self.assertRaises(ValueError):
            archive_bytes(dict(self.feed, jobs=[]))
        data = json.loads(archive_bytes(self.feed))
        for key, value in (("source_sha256", "0"*64), ("source_base64", "%%"),
                           ("observed_at", "2026-11-10"), ("extra", "unsupported")):
            broken = dict(data)
            broken[key] = value
            self.path.write_text(json.dumps(broken))
            with self.assertRaises(ValueError):
                load_archive(self.path)

    def test_missing_source_creates_no_misleading_file(self):
        with self.assertRaises(ValueError):
            export_archive({"jobs": []}, self.path)
        self.assertFalse(self.path.exists())

    def test_comparison_reports_observations_without_resolving_applications(self):
        from discovery_archive import compare_observations
        before = dict(self.feed, jobs=[
            {"id": "one", "title": "Before", "url": "https://example.invalid/one"},
            {"id": "gone", "title": "Absent later", "url": "https://example.invalid/gone"}])
        after = dict(self.feed, jobs=[
            {"id": "one", "title": "After", "url": "https://example.invalid/one"},
            {"id": "new", "title": "New", "url": "https://example.invalid/new"}])
        states = {row["id"]: row["state"] for row in compare_observations(before, after)}
        self.assertEqual(states, {"one": "changed", "gone": "not_observed", "new": "added"})
        self.assertTrue(all(row["state"] == "unchanged" for row in compare_observations(before, before)))
        with self.assertRaises(ValueError):
            compare_observations(before, dict(after, token="another"))
        with self.assertRaises(ValueError):
            compare_observations(before, dict(after, provider="ashby"))
