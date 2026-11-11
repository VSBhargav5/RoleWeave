import json
from threading import Event
import unittest
from unittest.mock import patch

from network_io import Cancelled
from provider_boards import parse_source
from test_employer_watchlist import synthetic_watchlist
from test_provider_boards import lever_fixture
from watchlist_fetch import collection_rows, fetch_watchlist


def fake_fetch(provider, token, cancel=None):
    raw = json.dumps(lever_fixture()).encode()
    if provider == "ashby":
        raw = json.dumps({"apiVersion": "1", "jobs": [{"title": "AI Engineer", "jobUrl": "https://jobs.ashbyhq.com/synthetic/one",
            "isListed": True, "publishedAt": "2026-11-10T00:00:00Z", "location": "Hybrid", "descriptionPlain": "Python and SQL."}]}).encode()
    return parse_source(raw, provider, token)


class WatchlistFetchTests(unittest.TestCase):
    def test_selected_sources_keep_company_market_and_byte_provenance(self):
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch) as fetch:
            result = fetch_watchlist(synthetic_watchlist(), [1, 0])
        self.assertEqual(fetch.call_count, 2)
        rows = collection_rows(result)
        self.assertEqual(rows[0]["company"], "Synthetic AI Co")
        self.assertEqual(rows[0]["market"], "relocation")
        self.assertEqual(rows[1]["provider"], "lever")
        self.assertTrue(all(row["response_sha256"] for row in rows))
        self.assertEqual(result["selected_indices"], [1, 0])

    def test_source_failure_is_explicit_and_does_not_erase_other_successes(self):
        def fetch(provider, token, cancel=None):
            if provider == "ashby":
                raise ValueError("Synthetic source unavailable")
            return fake_fetch(provider, token, cancel)
        with patch("watchlist_fetch.fetch_source", side_effect=fetch):
            result = fetch_watchlist(synthetic_watchlist(), [0, 1])
        self.assertEqual(len(result["feeds"]), 1)
        self.assertEqual(result["failures"], [{"board_index": 1, "error": "Synthetic source unavailable"}])
        self.assertEqual(len(collection_rows(result)), 1)

    def test_invalid_selection_cancel_and_total_byte_budget_stop_dispatch(self):
        for indices in ([], [0, 0], [-1], [100], [True]):
            with patch("watchlist_fetch.fetch_source") as fetch:
                with self.assertRaises(ValueError):
                    fetch_watchlist(synthetic_watchlist(), indices)
                fetch.assert_not_called()
        event = Event()
        event.set()
        with patch("watchlist_fetch.fetch_source") as fetch:
            with self.assertRaises(Cancelled):
                fetch_watchlist(synthetic_watchlist(), [0], event)
            fetch.assert_not_called()
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch), patch("watchlist_fetch.MAX_COLLECTION_SOURCE_BYTES", 1):
            with self.assertRaisesRegex(ValueError, "16 MiB"):
                fetch_watchlist(synthetic_watchlist(), [0])

    def test_collection_contract_replays_source_identity_rows_and_outcomes(self):
        import copy
        from watchlist_fetch import validate_collection
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch):
            original = fetch_watchlist(synthetic_watchlist(), [0, 1])
        for mutate in (
            lambda c: c["feeds"].pop(),
            lambda c: c["feeds"][0]["feed"].update(provider="ashby"),
            lambda c: c["feeds"][0]["feed"].update(response_sha256="0" * 64),
            lambda c: c["feeds"][0]["feed"].update(jobs=[]),
            lambda c: c.update(finished_at="2000-01-01T00:00:00+00:00"),
            lambda c: c["feeds"][0]["feed"].update(fetched_at="2026-11-11"),
            lambda c: c["feeds"].append(c["feeds"][0])):
            changed = copy.deepcopy(original)
            mutate(changed)
            with self.assertRaises(ValueError):
                validate_collection(changed)
        self.assertEqual(validate_collection(original), original)

    def test_selected_source_failure_cannot_be_relabelled_as_another_board(self):
        import copy
        from watchlist_fetch import validate_collection
        with patch("watchlist_fetch.fetch_source", side_effect=ValueError("Synthetic unavailable")):
            original = fetch_watchlist(synthetic_watchlist(), [0, 1])
        changed = copy.deepcopy(original)
        changed["failures"][1]["board_index"] = 0
        with self.assertRaises(ValueError):
            validate_collection(changed)

    def test_failed_only_retry_keeps_successful_bytes_and_original_interval_start(self):
        import copy
        from watchlist_fetch import retry_failed_sources
        def initially_failed(provider, token, cancel=None):
            if provider == "ashby":
                raise ValueError("Synthetic unavailable")
            return fake_fetch(provider, token, cancel)
        with patch("watchlist_fetch.fetch_source", side_effect=initially_failed):
            original = fetch_watchlist(synthetic_watchlist(), [0, 1])
        before = copy.deepcopy(original)
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch) as request:
            result = retry_failed_sources(original)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[0], "ashby")
        self.assertEqual(result["feeds"][0], original["feeds"][0])
        self.assertEqual(result["started_at"], original["started_at"])
        self.assertEqual(result["failures"], [])
        self.assertEqual(original, before)
        with patch("watchlist_fetch.fetch_source") as request:
            with self.assertRaisesRegex(ValueError, "No failed"):
                retry_failed_sources(result)
            request.assert_not_called()

    def test_retry_cancellation_and_merged_byte_budget_keep_original_unchanged(self):
        import copy
        from watchlist_fetch import retry_failed_sources
        with patch("watchlist_fetch.fetch_source", side_effect=fake_fetch):
            original = fetch_watchlist(synthetic_watchlist(), [0, 1])
        original["feeds"].pop()
        original["failures"] = [{"board_index": 1, "error": "Synthetic failure"}]
        before = copy.deepcopy(original)
        event = Event()
        event.set()
        with self.assertRaises(Cancelled):
            retry_failed_sources(original, event)
        sizes = [len(original["feeds"][0]["feed"]["source_snapshot"]),
                 len(fake_fetch("ashby", "synthetic")["source_snapshot"])]
        with patch("watchlist_fetch.MAX_COLLECTION_SOURCE_BYTES", max(sizes) + 1), patch("watchlist_fetch.fetch_source", side_effect=fake_fetch):
            with self.assertRaises(ValueError):
                retry_failed_sources(original)
        self.assertEqual(original, before)

    def test_cancel_and_deadline_are_checked_after_failed_requests_too(self):
        event = Event()
        def cancelled(provider, token, cancel=None):
            event.set()
            raise ValueError("Synthetic transport failed after cancellation")
        with patch("watchlist_fetch.fetch_source", side_effect=cancelled):
            with self.assertRaises(Cancelled):
                fetch_watchlist(synthetic_watchlist(), [0], event)
        with patch("watchlist_fetch.fetch_source", side_effect=ValueError("Synthetic timeout")), patch("watchlist_fetch.time.monotonic", side_effect=[0, 0, 61]):
            with self.assertRaisesRegex(ValueError, "observation budget"):
                fetch_watchlist(synthetic_watchlist(), [0])
