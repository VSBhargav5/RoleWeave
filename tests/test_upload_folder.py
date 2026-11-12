from pathlib import Path
from unittest.mock import patch
import unittest
import hashlib
from io import BytesIO
import zipfile

from application_dossier import build_dossier
from recipient_bundle import recipient_bytes, export_upload_folder
import test_application_dossier as dossier_tests


class UploadFolderTests(unittest.TestCase):
    def setUp(self):
        dossier_tests.ApplicationDossierTests.setUp(self)
        self.payload = build_dossier(self.store.load(self.job), self.store.load_resume(self.resume), [])
        self.destination = self.path.parent / "upload"

    def test_exact_recipient_documents_and_completed_note_exclude_private_sources(self):
        export_upload_folder(self.payload, self.destination, ["txt", "html"], confirmed=True)
        self.assertEqual({p.name for p in self.destination.iterdir()}, {"resume.txt", "resume.html", "EXPORT-INFO.txt"})
        with zipfile.ZipFile(BytesIO(recipient_bytes(self.payload, ["txt", "html"]))) as source:
            for name in source.namelist():
                content = (self.destination / name).read_bytes()
                self.assertEqual(content, source.read(name))
                self.assertIn(hashlib.sha256(content).hexdigest(), (self.destination / "EXPORT-INFO.txt").read_text(encoding="utf-8"))
        self.assertEqual(self.store.application_history(self.job), [])

    def test_bad_inputs_and_unconfirmed_export_do_not_reserve_output(self):
        for options in ((self.payload, ["pdf"], True), (self.payload, ["txt"], False), (b"invalid", ["txt"], True)):
            with self.assertRaises(ValueError):
                export_upload_folder(options[0], self.destination, options[1], confirmed=options[2])
            self.assertFalse(self.destination.exists())

    def test_existing_empty_or_populated_folder_is_never_reused(self):
        self.destination.mkdir()
        with self.assertRaises(FileExistsError):
            export_upload_folder(self.payload, self.destination, ["txt"], confirmed=True)
        (self.destination / "keep.txt").write_bytes(b"user content")
        with self.assertRaises(FileExistsError):
            export_upload_folder(self.payload, self.destination, ["txt"], confirmed=True)
        self.assertEqual((self.destination / "keep.txt").read_bytes(), b"user content")

    def test_interrupted_write_leaves_no_completion_claim_and_retry_cannot_mix_files(self):
        from safe_export import publish_bytes
        def interrupted(path, payload):
            if Path(path).name == "resume.html":
                raise OSError("synthetic disk failure")
            publish_bytes(path, payload)
        with patch("recipient_bundle.publish_bytes", side_effect=interrupted):
            with self.assertRaises(OSError):
                export_upload_folder(self.payload, self.destination, ["txt", "html"], confirmed=True)
        self.assertTrue((self.destination / "resume.txt").is_file())
        self.assertFalse((self.destination / "EXPORT-INFO.txt").exists())
        with self.assertRaises(FileExistsError):
            export_upload_folder(self.payload, self.destination, ["txt"], confirmed=True)
