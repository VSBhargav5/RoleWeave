import json
from pathlib import Path
import tempfile
import unittest

from job_store import JobStore


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        source = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
        self.india = self.store.save(source, "Data Engineer 100%", "Straße Labs", "https://example.invalid/india")
        data = json.loads(source)
        data["market"] = "relocation"
        self.abroad = self.store.save(json.dumps(data).encode(), "AI Engineer", "తెలుగు company")

    def test_unicode_casefold_and_literal_symbols_search_metadata(self):
        self.assertEqual(self.store.list_jobs(query="STRASSE")[0]["id"], self.india)
        self.assertEqual(self.store.list_jobs(query="తెలుగు")[0]["id"], self.abroad)
        self.assertEqual(len(self.store.list_jobs(query="%")), 1)
        self.assertEqual(self.store.list_jobs(query="_"), [])
        self.assertEqual(self.store.list_jobs(query="'; DROP TABLE jobs; --"), [])
        self.assertEqual(len(self.store.list_jobs()), 2)

    def test_market_stage_and_notes_filters_combine(self):
        self.store.record_application(self.india, "shortlisted", "Ask about timezone overlap")
        self.assertEqual(self.store.list_jobs(market="india_remote", stage="shortlisted", query="TIMEZONE")[0]["id"], self.india)
        self.assertEqual(self.store.list_jobs(market="relocation", stage="shortlisted"), [])
        self.assertEqual(self.store.list_jobs(stage="saved")[0]["id"], self.abroad)

    def test_due_dates_are_inclusive_ordered_and_exclude_closed(self):
        self.store.record_application(self.india, "applied", follow_up="2026-12-03")
        self.store.record_application(self.abroad, "interview", follow_up="2026-12-01")
        self.assertEqual([row["id"] for row in self.store.list_jobs(due_on="2026-12-03")], [self.abroad, self.india])
        self.assertEqual(self.store.list_jobs(due_on="2026-11-30"), [])
        self.store.record_application(self.abroad, "closed", follow_up="2026-12-01")
        self.assertEqual([row["id"] for row in self.store.list_jobs(due_on="2026-12-03")], [self.india])

    def test_clearing_follow_up_and_latest_stage_change_the_view(self):
        self.store.record_application(self.india, "applied", follow_up="2026-12-03")
        self.store.record_application(self.india, "shortlisted", "Correction", "")
        self.assertEqual(self.store.list_jobs(stage="applied"), [])
        self.assertEqual(self.store.list_jobs(due_on="2026-12-03"), [])
        self.assertEqual(len(self.store.application_history(self.india)), 2)

    def test_bad_filter_contracts_fail(self):
        for kwargs in ({"market": []}, {"stage": "auto-applied"}, {"query": "x" * 501},
                       {"due_on": ""}, {"due_on": "2026-02-30"}, {"query": None}):
            with self.assertRaises(ValueError):
                self.store.list_jobs(**kwargs)
