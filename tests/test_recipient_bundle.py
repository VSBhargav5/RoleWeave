from io import BytesIO
import unittest
import zipfile

from application_dossier import build_dossier
from recipient_bundle import recipient_bytes, export_recipient_bundle
import test_application_dossier as dossier_tests


class RecipientBundleTests(unittest.TestCase):
    def setUp(self):
        dossier_tests.ApplicationDossierTests.setUp(self)

    def dossier(self):
        return build_dossier(self.store.load(self.job), self.store.load_resume(self.resume), [])

    def test_only_chosen_public_documents_leave_private_dossier(self):
        with zipfile.ZipFile(BytesIO(recipient_bytes(self.dossier(), ["txt", "html"]))) as archive:
            self.assertEqual(set(archive.namelist()), {"resume.txt", "resume.html"})
            self.assertNotIn("Career profile", archive.read("resume.txt").decode())
            self.assertNotIn(b"resume-version.json", archive.read("resume.html"))
        self.assertEqual(self.store.application_history(self.job), [])

    def test_unavailable_invalid_unconfirmed_and_tampered_inputs_create_no_output(self):
        for formats in ([], ["pdf"], ["txt", "txt"], ["../review.json"]):
            with self.assertRaises(ValueError):
                recipient_bytes(self.dossier(), formats)
        with self.assertRaises(ValueError):
            export_recipient_bundle(self.dossier(), self.path, ["txt"])
        self.assertFalse(self.path.exists())
        with self.assertRaises(ValueError):
            recipient_bytes(b"corrupt", ["txt"])

    def test_matching_letter_can_be_exported_without_private_source_record(self):
        from cover_letter import make_letter
        item = self.store.load(self.job)
        letter = make_letter(self.store.load_profile(self.profile), ["project-python"], item,
                             "I value reliable systems.", "Thank you.", confirmed=True)
        dossier = build_dossier(item, self.store.load_resume(self.resume), [], letter=letter)
        with zipfile.ZipFile(BytesIO(recipient_bytes(dossier, ["txt", "letter"]))) as archive:
            self.assertEqual(set(archive.namelist()), {"resume.txt", "cover-letter.txt"})
            self.assertIn("reliable systems", archive.read("cover-letter.txt").decode())
            self.assertNotIn("source_snapshot", archive.read("cover-letter.txt").decode())
