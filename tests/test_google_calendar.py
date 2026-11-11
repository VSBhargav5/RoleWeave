import copy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

from job_store import JobStore
from google_calendar_sync import SCOPE, desired_event, prepare_sync, apply_sync, api_request, read_remote, calendar_path
from google_calendar_auth import connect_session, create_calendar


class GoogleCalendarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.store.record_application(self.job, "shortlisted", "PRIVATE DECISION NOTE", "2026-12-03")
        self.item = self.store.load(self.job)
        self.events = self.store.application_history(self.job)
        self.credentials = SimpleNamespace(valid=True, token="SYNTHETIC_TOKEN")

    def plan(self, existing=None, details=False):
        return prepare_sync(self.item, self.events, "synthetic@group.calendar.google.com", existing, include_details=details)

    def test_minimal_payload_exact_dates_and_deterministic_identity(self):
        plan = self.plan()
        event = plan["event"]
        self.assertEqual(event["summary"], "RoleWeave follow-up")
        self.assertRegex(event["id"], r"^[0-9a-v]{66}$")
        self.assertNotIn("PRIVATE", json.dumps(event))
        self.assertNotIn("CSV", json.dumps(event))
        self.assertNotIn("attendees", event)
        self.assertEqual(event["end"], {"date": "2026-12-04"})
        self.assertEqual(self.plan(details=True)["event"]["summary"], "Follow up: Synthetic - Engineer")
        self.assertEqual(event["id"], self.plan(details=True)["event"]["id"])
        for identifier in ("primary", "bad\nheader", ""):
            with self.assertRaises(ValueError): calendar_path(identifier)

    def test_owned_updates_have_etag_and_preserve_foreign_fields(self):
        existing = {**self.plan()["event"], "etag": '"version1"', "location": "Remote-only field"}
        self.assertEqual(self.plan(existing)["operation"], "unchanged")
        existing["start"] = {"date": "2026-12-02"}
        plan = self.plan(existing)
        self.assertEqual(plan["operation"], "update")
        with patch("google_calendar_sync.api_request", return_value={"id": plan["event"]["id"]}) as send:
            apply_sync(self.store, plan, self.credentials, confirmed=True)
        self.assertEqual(send.call_args.args[1], "PATCH")
        self.assertEqual(send.call_args.kwargs["etag"], '"version1"')
        self.assertNotIn("location", send.call_args.kwargs["body"])
        for change in ({"attendees": [{"email": "other@example.invalid"}]}, {"recurrence": ["RRULE:FREQ=DAILY"]},
                       {"etag": "bad\r\nheader"}, {"status": "cancelled"}, {"extendedProperties": None}):
            with self.assertRaises(ValueError): self.plan({**existing, **change})
        owned = copy.deepcopy(existing)
        owned["extendedProperties"]["private"]["rwSource"] = "0" * 64
        with self.assertRaises(ValueError): self.plan(owned)

    def test_confirmation_stale_revision_and_tampered_body_prevent_writes(self):
        plan = self.plan()
        with patch("google_calendar_sync.api_request") as send:
            with self.assertRaises(ValueError): apply_sync(self.store, plan, self.credentials)
            tampered = copy.deepcopy(plan)
            tampered["event"]["attendees"] = [{"email": "other@example.invalid"}]
            with self.assertRaises(ValueError): apply_sync(self.store, tampered, self.credentials, confirmed=True)
            self.store.record_application(self.job, "shortlisted", "A new observation", "2026-12-03")
            with self.assertRaises(ValueError): apply_sync(self.store, plan, self.credentials, confirmed=True)
            send.assert_not_called()
        self.store.record_application(self.job, "closed", "Closed", "")
        with self.assertRaises(ValueError): desired_event(self.item, self.store.application_history(self.job))

    def test_transport_bounds_redirect_conflict_and_cancel_do_not_retry(self):
        response = MagicMock(status=200)
        response.getheader.return_value = "application/json"
        response.read1.side_effect = [b'{"id":"example"}', b'']
        connection = MagicMock()
        connection.getresponse.return_value = response
        with patch("google_calendar_sync.http.client.HTTPSConnection", return_value=connection) as create:
            result = api_request(self.credentials, "GET", "/calendar/v3/calendars/example/events/example")
            self.assertEqual(result["id"], "example")
            self.assertEqual(create.call_args.args, ("www.googleapis.com",))
            self.assertEqual(connection.request.call_count, 1)
            self.assertEqual(connection.request.call_args.kwargs["headers"]["Authorization"], "Bearer SYNTHETIC_TOKEN")
            for status in (302, 409, 412, 500):
                response.status = status
                with self.assertRaises(ValueError): api_request(self.credentials, "PATCH", "/calendar/v3/calendars/example/events/example")
            response.status = 200
            response.read1.side_effect = [b'x' * 20]
            with patch("google_calendar_sync.MAX_RESPONSE_BYTES", 10):
                with self.assertRaises(ValueError): api_request(self.credentials, "GET", "/calendar/v3/calendars/example/events/example")
        event = threading.Event(); event.set()
        with patch("google_calendar_sync.http.client.HTTPSConnection") as create:
            with self.assertRaises(ValueError): api_request(self.credentials, "GET", "/calendar/v3/calendars/example/events/example", cancel=event)
            create.return_value.request.assert_not_called()
        with self.assertRaises(ValueError): api_request(self.credentials, "DELETE", "/calendar/v3/calendars/example")

    def test_explicit_browser_consent_has_narrow_scope_pkce_and_no_refresh_token_retained(self):
        flow = MagicMock()
        credentials = SimpleNamespace(valid=True, token="TOKEN", scopes=[SCOPE], granted_scopes=[SCOPE], expiry=None)
        flow.run_local_server.return_value = credentials
        with patch("google_calendar_auth.InstalledAppFlow.from_client_config", return_value=flow) as start:
            with self.assertRaises(ValueError): connect_session("synthetic-client.apps.googleusercontent.com", "CLIENT_SECRET")
            start.assert_not_called()
            session = connect_session("synthetic-client.apps.googleusercontent.com", "CLIENT_SECRET", confirmed=True)
            self.assertEqual(start.call_args.args[1], [SCOPE])
            self.assertTrue(start.call_args.kwargs["autogenerate_code_verifier"])
            self.assertFalse(flow.oauth2session.trust_env)
            self.assertEqual(flow.run_local_server.call_args.kwargs["host"], "127.0.0.1")
            self.assertEqual(flow.run_local_server.call_args.kwargs["access_type"], "online")
            self.assertIsNone(session.refresh_token)
            credentials.granted_scopes = [SCOPE, "other-scope"]
            with self.assertRaises(ValueError): connect_session("synthetic-client.apps.googleusercontent.com", "CLIENT_SECRET", confirmed=True)
        with patch("google_calendar_auth.api_request", return_value={"id": "synthetic@group.calendar.google.com"}) as send:
            with self.assertRaises(ValueError): create_calendar(self.credentials)
            send.assert_not_called()
            self.assertIn("@", create_calendar(self.credentials, confirmed=True))
