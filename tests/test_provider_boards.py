import hashlib
import json
import unittest
from unittest.mock import patch

from provider_boards import parse_source, fetch_source, source_endpoint
from discovery import discovered_snapshot


def lever_fixture():
    return [{"id": "synthetic-id", "text": "Data Engineer",
             "hostedUrl": "https://jobs.lever.co/synthetic/synthetic-id",
             "categories": {"location": "Remote"}, "descriptionPlain": "Build Python pipelines.",
             "lists": [{"text": "Requirements", "content": "<li>SQL required.</li>"}],
             "additionalPlain": "Ask about country eligibility."}]


class ProviderBoardTests(unittest.TestCase):
    def parse(self, data, provider="lever"):
        return parse_source(json.dumps(data).encode(), provider, "synthetic")

    def test_lever_keeps_lists_identity_and_original_byte_hash(self):
        raw = json.dumps(lever_fixture()).encode()
        feed = parse_source(raw, "lever", "synthetic")
        self.assertEqual(feed["source_snapshot"], raw)
        self.assertEqual(feed["response_sha256"], hashlib.sha256(raw).hexdigest())
        row = feed["jobs"][0]
        self.assertIn("SQL required.", row["posting"])
        self.assertIn("country eligibility", row["posting"])
        self.assertIn("Not supplied", row["updated_at"])
        self.assertEqual(json.loads(discovered_snapshot(row, "relocation"))["requirements"], [])

    def test_global_and_eu_are_separate_fixed_endpoints(self):
        self.assertEqual(source_endpoint("lever-eu", "synthetic")[0], "api.eu.lever.co")
        with patch("provider_boards.request_bytes", return_value=b"[]") as request:
            self.assertEqual(fetch_source("lever", "synthetic")["jobs"], [])
            self.assertEqual(request.call_args.args[0], "api.lever.co")
            self.assertNotIn("key", request.call_args.kwargs)

    def test_invalid_duplicate_and_possible_truncated_boards_fail_closed(self):
        for change in ({"id": ""}, {"categories": []}, {"hostedUrl": "http://example.invalid"},
                       {"descriptionPlain": ""}, {"lists": {}}, {"text": chr(0xD800)}):
            data = lever_fixture()
            data[0].update(change)
            with self.assertRaises(ValueError):
                self.parse(data)
        with self.assertRaises(ValueError):
            self.parse(lever_fixture() * 2)
        with self.assertRaises(ValueError):
            self.parse(lever_fixture() * 1000)
        with self.assertRaises(ValueError):
            self.parse({})
        with self.assertRaises(ValueError):
            source_endpoint("lever", "../private")

    def test_public_provider_credentials_are_refused_before_connecting(self):
        from network_io import request_bytes
        for host in ("api.lever.co", "api.eu.lever.co"):
            with patch("network_io.http.client.HTTPSConnection") as connect:
                with self.assertRaises(ValueError):
                    request_bytes(host, "/v0/postings/synthetic", key="synthetic-key")
                connect.assert_not_called()
