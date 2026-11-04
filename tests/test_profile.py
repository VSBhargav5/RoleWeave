import copy
import json
from pathlib import Path
import tempfile
import unittest

from career_profile import PROFILE_FIELDS, imported_career_facts, profile_snapshot
from job_store import JobStore


def synthetic_profile():
    return {**{key: "" for key in PROFILE_FIELDS}, "name": "Synthetic Candidate", "headline": "Data Engineering",
            "email": "candidate@example.invalid", "facts": [
                {"id": "project-python", "claim": "Built a synthetic Python CSV reconciliation project.",
                 "source": "Synthetic project exercise, not employment", "reviewed": True, "section": "Projects"},
                {"id": "draft", "claim": "Unreviewed draft claim", "source": "Unverified note",
                 "reviewed": False, "section": "Additional"}]}


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        self.data = synthetic_profile()

    def test_profile_versions_are_immutable_and_active_choice_is_explicit(self):
        original = json.dumps(self.data).encode()
        first = self.store.save_profile(original)
        self.data["headline"] = "Corrected headline"
        second = self.store.save_profile(json.dumps(self.data).encode())
        self.assertEqual(self.store.active_profile()["id"], second)
        self.assertEqual(self.store.load_profile(first)["snapshot"], original)
        self.store.activate_profile(first)
        self.assertEqual(self.store.active_profile()["id"], first)
        with self.assertRaises(ValueError):
            self.store.save_profile(original)
        self.assertEqual(len(self.store.list_profiles()), 2)

    def test_reused_facts_keep_frozen_provenance_and_exclude_unreviewed_claims(self):
        first = self.store.save_profile(json.dumps(self.data).encode())
        copied = imported_career_facts(self.store.load_profile(first), ["project-python"])
        self.assertIn(first, copied[0]["source"])
        self.assertEqual(copied[0]["claim"], self.data["facts"][0]["claim"])
        with self.assertRaises(ValueError):
            imported_career_facts(self.store.load_profile(first), ["draft"])
        self.data["facts"][0]["claim"] = "Corrected claim"
        second = self.store.save_profile(json.dumps(self.data).encode())
        updated = imported_career_facts(self.store.load_profile(second), ["project-python"])
        self.assertNotEqual(copied[0]["id"], updated[0]["id"])
        self.assertNotEqual(copied[0]["claim"], updated[0]["claim"])

    def test_profile_contract_rejects_bad_shapes_and_unreviewed_types(self):
        for change in ({"name": ""}, {"facts": "text"}, {"extra": "field"}):
            data = {**self.data, **change}
            with self.assertRaises(ValueError):
                profile_snapshot(json.dumps(data).encode())
        for field, value in (("reviewed", "true"), ("section", "Invented")):
            data = copy.deepcopy(self.data)
            data["facts"][0][field] = value
            with self.assertRaises(ValueError):
                profile_snapshot(json.dumps(data).encode())
        with self.assertRaises(ValueError):
            profile_snapshot(b'{"name":"one","name":"two"}')
