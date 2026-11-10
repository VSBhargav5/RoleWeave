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

    def test_ashby_only_listed_posts_and_exact_plain_text_are_used(self):
        data = {"apiVersion": "1", "jobs": [
            {"isListed": True, "jobUrl": "https://jobs.ashbyhq.com/synthetic/one",
             "title": "AI Engineer", "descriptionPlain": "Python and SQL.",
             "publishedAt": "2026-11-10T00:00:00Z", "location": "Hybrid",
             "secondaryLocations": [{"location": "India"}], "isRemote": True},
            {"isListed": False}]}
        feed = self.parse(data, "ashby")
        self.assertEqual(len(feed["jobs"]), 1)
        self.assertEqual(feed["jobs"][0]["location"], "Hybrid | India")
        self.assertIn("Last published:", feed["jobs"][0]["updated_at"])
        self.assertNotIn("eligible", feed["jobs"][0]["posting"])
        self.assertEqual(source_endpoint("ashby", "synthetic")[0], "api.ashbyhq.com")
        for change in ({"isListed": None}, {"publishedAt": "2026-11-10"},
                       {"secondaryLocations": {}}, {"jobUrl": "https://user:secret@example.invalid"}):
            changed = json.loads(json.dumps(data))
            changed["jobs"][0].update(change)
            with self.assertRaises(ValueError):
                self.parse(changed, "ashby")
        data["jobs"] = data["jobs"][:1] * 2
        with self.assertRaises(ValueError):
            self.parse(data, "ashby")

    def test_ashby_unsupported_contract_and_nan_metadata_are_rejected(self):
        for data in ({}, {"apiVersion": "2", "jobs": []}, {"apiVersion": "1", "jobs": {}}):
            with self.assertRaises(ValueError):
                self.parse(data, "ashby")
        row = lever_fixture()
        row[0]["extra"] = float("nan")
        with self.assertRaises(ValueError):
            self.parse(row)

    def test_board_url_resolution_only_accepts_supported_exact_board_urls(self):
        from provider_boards import board_identity
        self.assertEqual(board_identity("https://jobs.eu.lever.co/synthetic/"), ("lever-eu", "synthetic"))
        self.assertEqual(board_identity("https://job-boards.greenhouse.io/synthetic"), ("greenhouse", "synthetic"))
        for value in ("https://evil.invalid/synthetic", "https://jobs.lever.co/synthetic/job-id",
                      "https://jobs.lever.co/synthetic?token=secret", "http://jobs.lever.co/synthetic",
                      "https://user:secret@jobs.lever.co/synthetic", "https://jobs.lever.co:443/synthetic",
                      "https://jobs.lever.co//synthetic", "https://jobs.lever.co/synthetic#private"):
            with self.assertRaises(ValueError):
                board_identity(value)
