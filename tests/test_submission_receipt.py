from datetime import date, timedelta
import unittest

from application_dossier import build_dossier
from submission_receipt import record_submission
import test_application_dossier as dossier_tests


class SubmissionReceiptTests(unittest.TestCase):
    def setUp(self):
        dossier_tests.ApplicationDossierTests.setUp(self)
        self.payload = build_dossier(self.store.load(self.job), self.store.load_resume(self.resume), [])

    def record(self, **options):
        return record_submission(self.store, options.get("job", self.job), self.payload,
                options.get("submitted_on", date.today().isoformat()), options.get("channel", "Employer portal"),
                "My own reference", "I manually submitted the reviewed documents.",
                confirmed=options.get("confirmed", True))

    def test_record_appends_manual_observation_and_preserves_followup(self):
        self.store.record_application(self.job, "shortlisted", "Earlier note", "2026-12-03")
        self.record()
        history = self.store.application_history(self.job)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["stage"], "applied")
        self.assertEqual(history[-1]["follow_up"], "2026-12-03")
        self.assertIn("not independently verified", history[-1]["note"])
        self.assertIn("does not prove", history[-1]["note"])

    def test_unconfirmed_future_and_other_review_never_change_history(self):
        other = self.store.save(self.store.load(self.job)["snapshot"], "Another", "Synthetic")
        for options in ({"confirmed": False}, {"submitted_on": ""}, {"channel": "automatic"},
                        {"submitted_on": (date.today() + timedelta(days=1)).isoformat()}, {"job": other}):
            with self.assertRaises(ValueError):
                self.record(**options)
        self.assertEqual(self.store.application_history(self.job), [])
        self.assertEqual(self.store.application_history(other), [])
