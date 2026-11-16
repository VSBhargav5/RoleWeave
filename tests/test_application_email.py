import copy
from email import policy
from email.parser import BytesParser
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4
import zipfile

from application_email import address, email_snapshot, replay_email
from cover_letter import make_letter
from web_service import WebService, seed_web_demo
from workspace_bundle import restore_bundle, recovered_database


class ApplicationEmailTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.path = self.root / "jobs.db"
        seed_web_demo(self.path); self.service = WebService(self.path, demo=True)
        self.resume = self.service.store.list_resumes()[0]
        record = self.service.store.load_resume(self.resume["id"])["resume"]
        self.job = record["job_context"]["id"]
        self.values = {"job_id": self.job, "resume_id": self.resume["id"], "letter_id": "",
                       "sender": "candidate@example.invalid", "recipient": "hiring@example.invalid",
                       "subject": "Application — synthetic role", "body": "Hello,\nPlease see the selected PDFs.\nSynthetic candidate"}

    def save(self, values=None):
        values = copy.deepcopy(values or self.values)
        preview = self.service.email(values)
        return self.service.email({**values, "confirmed": True, "preview_sha256": preview["preview_sha256"]}, freeze=True)["id"]

    def letter(self, job=None):
        resume = self.service.store.load_resume(self.resume["id"])["resume"]
        profile = self.service.store.load_profile(resume["profile_id"])
        payload = make_letter(profile, resume["selected_fact_ids"], self.service.store.load(job or self.job), "My synthetic project background.", "Thank you.", confirmed=True, include_pdf=True)
        identifier = uuid4().hex; self.service._artifact("letters", identifier).write_bytes(payload)
        return identifier

    def test_preview_is_local_stateless_and_eml_has_only_selected_pdf_and_plain_body(self):
        before = self.service.store.application_history(self.job)
        preview = self.service.email(self.values)
        self.assertFalse((self.service.artifacts / "emails").exists())
        self.assertFalse(preview["sent"])
        identifier = self.save(); payload, content_type, name = self.service.download("email", identifier)
        message = BytesParser(policy=policy.default).parsebytes(payload)
        self.assertEqual((content_type, name), ("message/rfc822", "application-draft.eml"))
        self.assertEqual(str(message["To"]), self.values["recipient"])
        self.assertEqual(str(message["Subject"]), self.values["subject"])
        self.assertEqual(message["X-Unsent"], "1")
        self.assertIsNone(message["Bcc"])
        self.assertEqual(message.get_body(preferencelist=("plain",)).get_content().replace("\r\n", "\n").strip(), self.values["body"])
        attachments = list(message.iter_attachments())
        self.assertEqual([a.get_filename() for a in attachments], ["resume.pdf"])
        self.assertEqual(attachments[0].get_payload(decode=True), self.service.download("resume", self.resume["id"])[0])
        self.assertEqual(hashlib.sha256(payload).hexdigest(), preview["eml_sha256"])
        self.assertEqual(self.service.store.application_history(self.job), before)

    def test_preview_confirmation_and_source_binding_reject_stale_edits_without_write(self):
        preview = self.service.email(self.values)
        for changes in ({"confirmed": False}, {"body": "Changed message"}, {"recipient": "other@example.invalid"}, {"subject": "Changed subject"}, {"preview_sha256": "bad"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.service.email({**self.values, "confirmed": True, "preview_sha256": preview["preview_sha256"], **changes}, freeze=True)
        self.assertFalse((self.service.artifacts / "emails").exists())
        other = self.service.store.save(self.service.store.load(self.job)["snapshot"], "Other role", "Other employer")
        with self.assertRaises(ValueError): self.service.email({**self.values, "job_id": other})

    def test_multiple_addresses_header_injection_and_invalid_inputs_are_rejected(self):
        for value in ("a@example.invalid\r\nBcc: hidden@example.invalid", "a@example.invalid,b@example.invalid", "Name <a@example.invalid>", "a@localhost", "a@bad[.invalid", "é@example.invalid", ""):
            with self.subTest(value=value), self.assertRaises(ValueError): address(value)
        for changes in ({"subject": "Hello\nBcc: hidden@example.invalid"}, {"subject": "x" * 201}, {"body": "x" * 10001}, {"bcc": "hidden@example.invalid"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.service.email({**self.values, **changes})

    def test_optional_letter_is_exact_pdf_and_wrong_review_letter_is_refused(self):
        identifier = self.letter(); values = {**self.values, "letter_id": identifier}
        saved = self.save(values); payload = self.service.download("email", saved)[0]
        message = BytesParser(policy=policy.default).parsebytes(payload)
        files = {part.get_filename(): part.get_payload(decode=True) for part in message.iter_attachments()}
        self.assertEqual(set(files), {"resume.pdf", "cover-letter.pdf"})
        self.assertEqual(files["cover-letter.pdf"], self.service.download("letter", identifier)[0])
        other = self.service.store.save(self.service.store.load(self.job)["snapshot"], "Other role", "Other employer")
        with self.assertRaises(ValueError): self.service.email({**self.values, "letter_id": self.letter(other)})

    def test_restart_reopen_original_download_and_recovery_preserve_bytes(self):
        identifier = self.save({**self.values, "letter_id": self.letter()})
        original = self.service.download("email", identifier)[0]
        service = WebService(self.path)
        self.assertEqual(service.job(self.job)["email_drafts"][0]["id"], identifier)
        self.assertEqual(service.get_email(identifier, self.job)["values"], {**self.values, "letter_id": service.get_email(identifier)["values"]["letter_id"]})
        self.assertEqual(service.download("email", identifier)[0], original)
        restored = restore_bundle(service.workspace_bundle(), self.root / "recovered")
        recovered = WebService(recovered_database(self.root / "recovered", restored["id"]))
        self.assertEqual(recovered.download("email", identifier)[0], original)
        self.assertFalse(recovered.get_email(identifier)["sent"])
        with self.assertRaises(ValueError): service.get_email(identifier, "other-review")
        with self.assertRaises(ValueError): service.get_email("../private")

    def test_modified_message_fingerprint_is_refused_by_download_and_backup(self):
        identifier = self.save(); path = self.service._artifact("emails", identifier)
        record = email_snapshot(path.read_bytes()); record["values"]["body"] = "Tampered body"
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(ValueError): self.service.download("email", identifier)
        with self.assertRaises(ValueError): self.service.workspace_bundle()

    def test_even_rehashed_wrong_resume_binding_rejects_restore_before_output(self):
        identifier = self.save(); bundle = self.service.workspace_bundle()
        with zipfile.ZipFile(BytesIO(bundle)) as archive: parts = {n: archive.read(n) for n in archive.namelist()}
        name = "web-artifacts/emails/" + identifier + ".json"
        record = json.loads(parts[name]); record["resume_sha256"] = "0" * 64
        parts[name] = json.dumps(record).encode(); manifest = json.loads(parts["manifest.json"])
        manifest["files"][name] = {"bytes": len(parts[name]), "sha256": hashlib.sha256(parts[name]).hexdigest()}
        parts["manifest.json"] = json.dumps(manifest).encode(); out = BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            for name, content in parts.items(): archive.writestr(name, content)
        with self.assertRaises(ValueError): restore_bundle(out.getvalue(), self.root / "refused")
        self.assertFalse((self.root / "refused").exists())

    def test_text_only_or_other_profile_letter_is_not_an_application_attachment(self):
        resume = self.service.store.load_resume(self.resume["id"])["resume"]
        profile = self.service.store.load_profile(resume["profile_id"])
        payload = make_letter(profile, resume["selected_fact_ids"], self.service.store.load(self.job), "Synthetic introduction.", "Thank you.", confirmed=True, include_pdf=False)
        identifier = uuid4().hex; self.service._artifact("letters", identifier).write_bytes(payload)
        with self.assertRaises(ValueError): self.service.email({**self.values, "letter_id": identifier})
        changed = copy.deepcopy(profile["profile"]); changed["name"] = "Different synthetic candidate"
        other_id = self.service.store.save_profile(json.dumps(changed).encode())
        other = self.service.store.load_profile(other_id)
        payload = make_letter(other, resume["selected_fact_ids"], self.service.store.load(self.job), "Synthetic introduction.", "Thank you.", confirmed=True, include_pdf=True)
        self.service._artifact("letters", identifier).write_bytes(payload)
        with self.assertRaises(ValueError): self.service.email({**self.values, "letter_id": identifier})
