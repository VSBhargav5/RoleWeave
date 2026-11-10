from datetime import date
import unittest
from unittest.mock import patch

from application_dossier import build_dossier
from correspondence import record_correspondence
from job_store import JobStore
from submission_receipt import record_submission
from test_mail_observation import synthetic_mail
import test_application_dossier as dossier_tests


class HistoryConflictTests(unittest.TestCase):
    def setUp(self):
        dossier_tests.ApplicationDossierTests.setUp(self)

    def test_expected_revision_rejects_stale_or_invalid_values_without_writing(self):
        self.store.record_application(self.job, "interview", "Newer", "", expected_revision=0)
        for revision in (0, True, -1, "1"):
            with self.assertRaises(ValueError):
                self.store.record_application(self.job, "closed", "Stale", "", expected_revision=revision)
        self.assertEqual(len(self.store.application_history(self.job)), 1)
        self.store.record_application(self.job, "offer", "Reviewed", "", expected_revision=1)
        self.assertEqual(self.store.application_history(self.job)[-1]["stage"], "offer")

    def test_imported_observations_cannot_restore_stale_stage_or_followup(self):
        payload = build_dossier(self.store.load(self.job), self.store.load_resume(self.resume), [])
        original = self.store.application_history
        other = JobStore(self.store.path)
        def race(identifier):
            history = original(identifier)
            other.record_application(identifier, "interview", "Other window updated", "2026-12-03")
            return history
        operations = (
            lambda: record_correspondence(self.store, self.job, synthetic_mail(), "Please suggest a time", "", confirmed=True),
            lambda: record_submission(self.store, self.job, payload, date.today().isoformat(), "Email", "", "", confirmed=True))
        for operation in operations:
            with patch.object(self.store, "application_history", side_effect=race):
                with self.assertRaisesRegex(ValueError, "history changed"):
                    operation()
            current = original(self.job)[-1]
            self.assertEqual(current["stage"], "interview")
            self.assertEqual(current["follow_up"], "2026-12-03")
