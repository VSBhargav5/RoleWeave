import copy
import json
import unittest
from unittest.mock import patch, MagicMock
from threading import Event

from discovery import board_path, parse_board, plain_posting, discovered_snapshot
from network_io import request_bytes, Cancelled


def fixture():
    return {"jobs": [{"id": 123, "internal_job_id": 456, "title": "Synthetic Data Engineer",
                      "absolute_url": "https://example.invalid/jobs/123", "updated_at": "2026-11-04T00:00:00Z",
                      "location": {"name": "Remote"}, "content": "&lt;p&gt;Python required. SQL preferred.&lt;/p&gt;"}],
            "meta": {"total": 1}}


class DiscoveryTests(unittest.TestCase):
    def parse(self, data):
        return parse_board(json.dumps(data).encode(), "synthetic")

    def test_contract_preserves_identity_plain_content_and_separate_market(self):
        row = self.parse(fixture())["jobs"][0]
        self.assertIn("Python required. SQL preferred.", row["posting"])
        self.assertIn("not publication date", row["posting"])
        self.assertNotIn("&lt;p", row["posting"])
        self.assertEqual(json.loads(discovered_snapshot(row, "relocation"))["market"], "relocation")
        with self.assertRaises(ValueError):
            discovered_snapshot(row, "automatic")

    def test_plain_text_never_executes_and_keeps_technical_escaped_text(self):
        self.assertEqual(plain_posting("<p>Use &lt;T&gt; &amp; SQL.</p><script>secret()</script>"), "Use <T> & SQL.")

    def test_unchanged_posting_has_stable_snapshot_despite_fetch_time(self):
        first = self.parse(fixture())["jobs"][0]
        second = self.parse(fixture())["jobs"][0]
        self.assertEqual(discovered_snapshot(first, "india_remote"), discovered_snapshot(second, "india_remote"))

    def test_bad_board_tokens_never_form_arbitrary_urls(self):
        for token in ("../test", "https://evil.invalid", "x?key=a", "", None):
            with self.assertRaises(ValueError):
                board_path(token)

    def test_prospects_are_excluded_and_malformed_or_partial_feeds_fail(self):
        data = fixture()
        data["jobs"][0]["internal_job_id"] = None
        self.assertEqual(self.parse(data)["jobs"], [])
        for change in ({"id": True}, {"content": ""}, {"absolute_url": "http://example.invalid"},
                       {"updated_at": "2026-11-04"}, {"location": None}):
            data = fixture()
            data["jobs"][0].update(change)
            with self.assertRaises(ValueError):
                self.parse(data)
        data = fixture()
        data["meta"]["total"] = 2
        with self.assertRaises(ValueError):
            self.parse(data)
        with self.assertRaises(ValueError):
            parse_board(b'{"jobs":[],"jobs":[],"meta":{"total":0}}', "synthetic")


class NetworkTests(unittest.TestCase):
    def test_no_redirect_retry_or_provider_body_error_leak(self):
        with patch("network_io.http.client.HTTPSConnection") as factory:
            response = factory.return_value.getresponse.return_value
            response.status = 302
            with self.assertRaisesRegex(ValueError, "HTTP 302"):
                request_bytes("api.openai.com", "/v1/responses", body=b"{}", key="synthetic-key")
            self.assertEqual(factory.return_value.request.call_count, 1)
            response.read1.assert_not_called()
            factory.return_value.close.assert_called_once()

    def test_bounded_response_and_cancel_before_dispatch(self):
        with patch("network_io.http.client.HTTPSConnection") as factory:
            response = factory.return_value.getresponse.return_value
            response.status = 200
            response.getheader.return_value = "application/json; charset=utf-8"
            response.read1.return_value = b"12345"
            with self.assertRaisesRegex(ValueError, "size"):
                request_bytes("boards-api.greenhouse.io", "/v1/test", limit=4)
        event = Event()
        event.set()
        with patch("network_io.http.client.HTTPSConnection") as factory:
            with self.assertRaises(Cancelled):
                request_bytes("api.openai.com", "/v1/responses", cancel=event)
            factory.assert_not_called()

    def test_errors_do_not_echo_key_and_header_injection_is_rejected(self):
        with patch("network_io.http.client.HTTPSConnection") as factory:
            factory.return_value.request.side_effect = OSError("SENSITIVE KEY")
            with self.assertRaises(ValueError) as caught:
                request_bytes("api.openai.com", "/v1/responses")
            self.assertNotIn("SENSITIVE", str(caught.exception))
        with self.assertRaises(ValueError):
            request_bytes("api.openai.com", "/v1/responses", key="bad\r\nheader")
