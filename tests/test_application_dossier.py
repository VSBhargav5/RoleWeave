import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from application_dossier import build_dossier, export_dossier
from job_store import JobStore
from test_profile import synthetic_profile


class ApplicationDossierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.profile = self.store.save_profile(json.dumps(synthetic_profile()).encode())
        self.resume = self.store.create_resume(self.profile, ["project-python"], "For exact review", self.job,
                                               include_pdf=False, confirmed=True)
        self.path = self.folder / "dossier.zip"

    def test_exact_private_dossier_is_deterministic_and_never_marks_submission(self):
        item, resume = self.store.load(self.job), self.store.load_resume(self.resume)
        first = build_dossier(item, resume, [])
        self.assertEqual(first, build_dossier(item, resume, []))
        with zipfile.ZipFile(BytesIO(first)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            self.assertTrue(manifest["contains_private_evidence"])
            self.assertFalse(manifest["submission_verified"])
            self.assertEqual(archive.read("review.json"), item["snapshot"])
            self.assertEqual(archive.read("resume-version.json"), resume["snapshot"])
            for name, value in manifest["files"].items():
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), value["sha256"])
        self.assertEqual(self.store.application_history(self.job), [])

    def test_confirmation_no_overwrite_and_exact_context_are_enforced(self):
        with self.assertRaises(ValueError):
            export_dossier(self.store, self.job, self.resume, self.path)
        self.assertFalse(self.path.exists())
        digest = export_dossier(self.store, self.job, self.resume, self.path, confirmed=True)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), digest)
        with self.assertRaises(FileExistsError):
            export_dossier(self.store, self.job, self.resume, self.path, confirmed=True)
        other = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Another", "Synthetic")
        with self.assertRaisesRegex(ValueError, "exact saved review"):
            build_dossier(self.store.load(other), self.store.load_resume(self.resume), [])

    def test_other_history_and_general_resumes_cannot_be_misattributed(self):
        general = self.store.create_resume(self.profile, ["project-python"], "General", include_pdf=False, confirmed=True)
        with self.assertRaises(ValueError):
            build_dossier(self.store.load(self.job), self.store.load_resume(general), [])
        self.store.record_application(self.job, "shortlisted", "Synthetic note", "")
        events = self.store.application_history(self.job)
        events[0]["job_id"] = "different"
        with self.assertRaises(ValueError):
            build_dossier(self.store.load(self.job), self.store.load_resume(self.resume), events)
