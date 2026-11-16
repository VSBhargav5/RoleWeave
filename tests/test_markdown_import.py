import base64
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from resume_import import extract_text, extract_in_worker, document_name
from web_service import WebService
from workspace_bundle import inspect_bundle, restore_bundle, recovered_database


class MarkdownImportTests(unittest.TestCase):
    def test_markdown_is_reviewed_literal_text_and_never_fetches_or_executes_markup(self):
        payload = b"# Synthetic Candidate\n- Built **Python** CSV exercise.\n![image](https://example.invalid/private)\n<script>neverExecute()</script>\n"
        for name in ("resume.md", "resume.MD", "resume.markdown"):
            with self.subTest(name=name), patch("network_io.request_bytes", side_effect=AssertionError("No external fetch")):
                result = extract_text(payload, document_name(name))
            self.assertEqual(result["text"], payload.decode().strip())
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertIn("**Python**", result["blocks"][1]["text"])
            self.assertIn("<script>", result["blocks"][-1]["text"])
        with self.assertRaises(UnicodeError): extract_text(b"bad \xff", "resume.md")
        with self.assertRaises(ValueError): extract_text(b"", "resume.md")

    def test_worker_and_original_markdown_bytes_join_managed_recovery(self):
        payload = b"# Synthetic candidate\nBuilt a Markdown import exercise."
        result = extract_in_worker(payload, "resume.md")
        self.assertEqual(result["text"], payload.decode())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); service = WebService(root / "jobs.db")
            preview = service.preview_resume_import({"name": "resume.md", "base64": base64.b64encode(payload).decode()})
            source = service.artifacts / "resume-imports" / (hashlib.sha256(payload).hexdigest() + ".md")
            self.assertFalse(source.exists())
            service.commit_resume_import({"id": preview["id"], "selected": [{"id": "2", "section": "Projects"}], "confirmed": True})
            self.assertIsNone(service.profile())
            self.assertEqual(source.read_bytes(), payload)
            bundle = service.workspace_bundle(); _, summary = inspect_bundle(bundle)
            self.assertEqual(summary["artifacts"]["resume-imports"], 1)
            restored = restore_bundle(bundle, root / "recovered")
            recovered = WebService(recovered_database(root / "recovered", restored["id"]))
            self.assertEqual((recovered.artifacts / "resume-imports" / source.name).read_bytes(), payload)
