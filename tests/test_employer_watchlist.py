import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from employer_watchlist import filter_postings, read_watchlist, save_watchlist, validate_watchlist


def synthetic_watchlist():
    return {"format": "roleweave-watchlist-v1", "name": "Synthetic employer boards",
            "boards": [{"provider": "lever", "token": "synthetic", "company": "Synthetic Co", "market": "india_remote"},
                       {"provider": "ashby", "token": "synthetic", "company": "Synthetic AI Co", "market": "relocation"}],
            "filters": {"include": "", "exclude": "", "search_description": False}}


class EmployerWatchlistTests(unittest.TestCase):
    def test_portable_file_roundtrip_never_fetches_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder, patch("provider_boards.request_bytes") as network:
            path = Path(folder) / "boards.json"
            save_watchlist(synthetic_watchlist(), path)
            self.assertEqual(read_watchlist(path), synthetic_watchlist())
            with self.assertRaises(FileExistsError):
                save_watchlist(synthetic_watchlist(), path)
            network.assert_not_called()

    def test_unknown_duplicate_and_ambiguous_configuration_fails(self):
        for change in ({"market": "automatic"}, {"token": "https://evil.invalid"},
                       {"provider": "unknown"}, {"company": ""}, {"extra": True}):
            data = synthetic_watchlist()
            data["boards"][0].update(change)
            with self.assertRaises(ValueError):
                validate_watchlist(data)
        data = synthetic_watchlist()
        data["boards"].append(copy.deepcopy(data["boards"][0]))
        with self.assertRaises(ValueError):
            validate_watchlist(data)
        data = synthetic_watchlist()
        data["filters"]["search_description"] = 1
        with self.assertRaises(ValueError):
            validate_watchlist(data)

    def test_saved_filters_apply_literal_unicode_matching_locally(self):
        rows = [{"title": "Engineer", "location": "Remote", "posting": "Python and SQL"}]
        self.assertEqual(filter_postings(rows, {"include": "sql", "exclude": "", "search_description": False}), [])
        self.assertEqual(filter_postings(rows, {"include": "SQL", "exclude": "", "search_description": True}), rows)
        self.assertEqual(filter_postings(rows, {"include": "", "exclude": "PYTHON", "search_description": True}), [])
