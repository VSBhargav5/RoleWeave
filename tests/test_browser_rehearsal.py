import copy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from web_service import WebService
from workspace_bundle import inspect_bundle, restore_bundle, recovered_database


class BrowserRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = WebService(self.root / "jobs.db")
        self.source = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.job = self.service.store.save(self.source, "Engineer", "Synthetic")
        self.answers = [{"requirement_id": "python", "answer": "CSV exercise, not employment.", "reflection": "Check the error case."}]

    def save(self, **changes):
        return self.service.save_rehearsal({"job_id": self.job, "answers": copy.deepcopy(self.answers), "confirmed": True, **changes})["id"]

    def test_saved_versions_reopen_after_restart_and_download_exact_private_bytes(self):
        first = self.save(); second = self.save()
        self.assertNotEqual(first, second)
        service = WebService(self.root / "jobs.db")
        self.assertEqual(len(service.job(self.job)["rehearsals"]), 2)
        record = service.rehearsal(first, self.job)["record"]
        self.assertEqual(record["answers"], self.answers)
        self.assertFalse(record["learning_verified"])
        self.assertEqual(record["elapsed_seconds"], 0)
        payload, kind, name = service.download("rehearsal", first)
        self.assertEqual(json.loads(payload), record)
        self.assertEqual(payload, service._artifact("rehearsals", first).read_bytes())
        self.assertEqual((kind, name), ("application/json", "private-rehearsal.json"))
        cards = service.job(self.job)["practice_cards"]
        self.assertIn("not employment", cards[0]["evidence"])
        self.assertIn("No evidence linked", cards[1]["evidence"])

    def test_confirmation_ids_limits_and_unknown_fields_fail_without_artifacts(self):
        for changes in ({"confirmed": False}, {"answers": []}, {"answers": self.answers * 2},
                        {"answers": [{**self.answers[0], "requirement_id": "invented"}]},
                        {"answers": [{**self.answers[0], "answer": "a" * 6001}]},
                        {"answers": [{**self.answers[0], "reflection": "a" * 2001}]}, {"elapsed_seconds": 90}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.save(**changes)
        self.assertFalse((self.service.artifacts / "rehearsals").exists())

    def test_other_exact_review_and_path_traversal_are_refused(self):
        identifier = self.save()
        other = self.service.store.save(self.source, "Other engineer", "Synthetic")
        with self.assertRaises(ValueError): self.service.rehearsal(identifier, other)
        self.assertEqual(self.service.job(other)["rehearsals"], [])
        with self.assertRaises(ValueError): self.service.rehearsal("../jobs")

    def test_changed_embedded_context_is_refused_by_read_download_and_backup(self):
        identifier = self.save(); path = self.service._artifact("rehearsals", identifier)
        record = json.loads(path.read_bytes()); record["job_context"]["title"] = "Altered title"
        path.write_text(json.dumps(record), encoding="utf-8")
        for action in (lambda: self.service.rehearsal(identifier), lambda: self.service.download("rehearsal", identifier), self.service.workspace_bundle):
            with self.assertRaises(ValueError): action()

    def test_bundle_restores_exact_journals_and_keeps_original_workspace(self):
        identifier = self.save(); original = self.service.download("rehearsal", identifier)[0]
        bundle = self.service.workspace_bundle(); _, summary = inspect_bundle(bundle)
        self.assertEqual(summary["artifacts"]["rehearsals"], 1)
        restored = restore_bundle(bundle, self.root / "recovered")
        service = WebService(recovered_database(self.root / "recovered", restored["id"]))
        self.assertEqual(service.download("rehearsal", identifier)[0], original)
        self.assertEqual(service.rehearsal(identifier, self.job)["record"]["answers"], self.answers)
        self.assertEqual(self.service.download("rehearsal", identifier)[0], original)

    def test_even_rehashed_wrong_review_journal_is_rejected_on_restore(self):
        identifier = self.save(); bundle = self.service.workspace_bundle()
        with zipfile.ZipFile(BytesIO(bundle)) as archive: parts = {name: archive.read(name) for name in archive.namelist()}
        name = "web-artifacts/rehearsals/" + identifier + ".json"
        record = json.loads(parts[name]); record["job_context"]["company"] = "Wrong company"
        parts[name] = json.dumps(record).encode(); manifest = json.loads(parts["manifest.json"])
        manifest["files"][name] = {"bytes": len(parts[name]), "sha256": hashlib.sha256(parts[name]).hexdigest()}
        parts["manifest.json"] = json.dumps(manifest).encode(); out = BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            for key, value in parts.items(): archive.writestr(key, value)
        with self.assertRaises(ValueError): restore_bundle(out.getvalue(), self.root / "rejected")
        self.assertFalse((self.root / "rejected").exists())

    def test_old_bundle_without_journals_still_restores(self):
        bundle = self.service.workspace_bundle()
        restored = restore_bundle(bundle, self.root / "old")
        service = WebService(recovered_database(self.root / "old", restored["id"]))
        self.assertEqual(service.job(self.job)["rehearsals"], [])

    def test_full_collection_refuses_next_save_without_hiding_existing_versions(self):
        identifier = self.save(); directory = self.service.artifacts / "rehearsals"
        payload = (directory / (identifier + ".json")).read_bytes()
        for index in range(999):
            (directory / (format(index, "032x") + ".json")).write_bytes(payload)
        with self.assertRaises(ValueError): self.save()
        self.assertEqual(len(list(directory.iterdir())), 1000)
        self.assertEqual(len(self.service.rehearsals(self.job)), 1000)
