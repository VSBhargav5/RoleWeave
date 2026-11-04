import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from job_store import JobStore
from resume_versions import resume_snapshot
from test_profile import synthetic_profile


class ResumeVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.profile = synthetic_profile()
        self.profile_id = self.store.save_profile(json.dumps(self.profile).encode())
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")

    def create(self, **kwargs):
        return self.store.create_resume(self.profile_id, ["project-python"], "Synthetic application", self.job,
                                        include_pdf=kwargs.get("include_pdf", False), confirmed=kwargs.get("confirmed", True))

    def test_html_export_and_provenance_remain_frozen_after_profile_change(self):
        identifier = self.create()
        original = self.store.load_resume(identifier)
        context = original["resume"]["job_context"]
        self.assertEqual(context["id"], self.job)
        self.assertEqual(context["input_sha256"], self.store.load(self.job)["input_sha256"])
        self.profile["name"] = "Corrected Name"
        self.store.save_profile(json.dumps(self.profile).encode())
        output = self.folder / "resume.html"
        self.store.export_resume(identifier, output, "html")
        self.assertIn("Synthetic Candidate", output.read_text(encoding="utf-8"))
        self.assertNotIn("Corrected Name", output.read_text(encoding="utf-8"))
        self.assertEqual(self.store.load_resume(identifier)["snapshot"], original["snapshot"])

    def test_explicit_confirmation_and_valid_selection_are_required(self):
        with self.assertRaises(ValueError):
            self.create(confirmed=False)
        with self.assertRaises(ValueError):
            self.store.create_resume(self.profile_id, ["draft"], "Invalid", confirmed=True, include_pdf=False)
        self.assertEqual(self.store.list_resumes(), [])

    def test_exports_refuse_overwrite_and_missing_pdf_without_creating_output(self):
        identifier = self.create()
        path = self.folder / "keep.html"
        path.write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            self.store.export_resume(identifier, path, "html")
        self.assertEqual(path.read_bytes(), b"original")
        pdf = self.folder / "missing.pdf"
        with self.assertRaises(ValueError):
            self.store.export_resume(identifier, pdf, "pdf")
        self.assertFalse(pdf.exists())
        with self.assertRaises(ValueError):
            self.create()

    def test_changed_html_is_replayed_against_source_not_just_its_hash(self):
        record = self.store.load_resume(self.create())["resume"]
        fake = b"<html>Invented job experience</html>"
        record["html_base64"] = base64.b64encode(fake).decode()
        record["html_sha256"] = hashlib.sha256(fake).hexdigest()
        with self.assertRaisesRegex(ValueError, "source claims"):
            resume_snapshot(json.dumps(record).encode())
