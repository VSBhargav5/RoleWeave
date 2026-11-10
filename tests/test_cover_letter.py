import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cover_letter import make_letter, letter_snapshot, export_letter
from job_store import JobStore
from test_profile import synthetic_profile


class CoverLetterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.job_id = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic Co")
        self.profile_id = self.store.save_profile(json.dumps(synthetic_profile()).encode())
        self.profile = self.store.load_profile(self.profile_id)
        self.job = self.store.load(self.job_id)

    def make(self, **options):
        return make_letter(self.profile, options.get("identifiers", ["project-python"]), self.job,
                           options.get("motivation", "I am interested in reliable data workflows."),
                           "Thank you for considering my application.", confirmed=options.get("confirmed", True))

    def test_selected_reviewed_claims_are_copied_exactly_without_sources_or_other_facts(self):
        record, _digest = letter_snapshot(self.make())
        selected = self.profile["profile"]["facts"][0]
        self.assertIn(selected["claim"], record["text"])
        self.assertNotIn(selected["source"], record["text"])
        self.assertIn("Engineer role at Synthetic Co", record["text"])
        self.assertEqual(record["job_context"]["id"], self.job_id)

    def test_review_selection_and_user_text_limits_fail_closed(self):
        for options in ({"confirmed": False}, {"identifiers": ["draft"]}, {"identifiers": []},
                        {"motivation": "x" * 6001}, {"motivation": chr(0xD800)}):
            with self.assertRaises(ValueError):
                self.make(**options)

    def test_recomputed_text_hash_cannot_hide_fabricated_claims(self):
        record = json.loads(self.make())
        record["text"] += "Invented experience"
        record["text_sha256"] = hashlib.sha256(record["text"].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "replay"):
            letter_snapshot(json.dumps(record).encode())

    def test_later_profile_versions_do_not_rewrite_export_and_existing_files_survive(self):
        snapshot = self.make()
        profile = copy.deepcopy(self.profile["profile"])
        profile["name"] = "Later name"
        self.store.save_profile(json.dumps(profile).encode())
        path = self.folder / "letter.txt"
        export_letter(snapshot, path, "txt", confirmed=True)
        self.assertIn("Synthetic Candidate", path.read_text())
        self.assertNotIn("Later name", path.read_text())
        with self.assertRaises(FileExistsError):
            export_letter(snapshot, path, "txt", confirmed=True)
        with self.assertRaises(ValueError):
            export_letter(snapshot, self.folder / "bad.json", "json")
