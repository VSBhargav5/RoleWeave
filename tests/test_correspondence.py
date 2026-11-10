import unittest
from correspondence import record_correspondence
from test_mail_observation import synthetic_mail
import test_application_dossier as dossier_tests


class CorrespondenceTests(unittest.TestCase):
    def setUp(self):
        dossier_tests.ApplicationDossierTests.setUp(self)

    def test_exact_excerpt_preserves_stage_followup_and_rejects_duplicates(self):
        self.store.record_application(self.job, "interview", "Earlier manual stage", "2026-12-03")
        raw = synthetic_mail()
        record_correspondence(self.store, self.job, raw, "Please suggest a time", "My observation", confirmed=True)
        event = self.store.application_history(self.job)[-1]
        self.assertEqual(event["stage"], "interview")
        self.assertEqual(event["follow_up"], "2026-12-03")
        self.assertIn("not authenticated", event["note"])
        self.assertNotIn("untrusted attachment", event["note"])
        with self.assertRaisesRegex(ValueError, "already recorded"):
            record_correspondence(self.store, self.job, raw, "Please suggest a time", "My observation", confirmed=True)

    def test_fabricated_excerpt_and_unconfirmed_mail_leave_history_untouched(self):
        for quote, confirmed in (("You are hired", True), ("Please suggest", False)):
            with self.assertRaises(ValueError):
                record_correspondence(self.store, self.job, synthetic_mail(), quote, "", confirmed=confirmed)
        self.assertEqual(self.store.application_history(self.job), [])
