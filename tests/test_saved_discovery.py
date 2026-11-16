from contextlib import closing
import copy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from discovery_store import DiscoveryStore, candidate_key, parse_snapshot, snapshot_bytes
from job_search import parse_search
from job_store import JobStore
from web_service import WebService
from workspace_bundle import export_bundle, restore_bundle, recovered_database


class SavedDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.service = WebService(self.root / "jobs.db")
        self.configure = {"name": "Data India", "query": "data engineer", "location": "India", "country": "IN", "remote": True, "market": "india_remote", "archived": False}
        self.configure_search(); self.set_result()

    def configure_search(self, **changes):
        state = self.service.discovery.read()
        self.state = self.service.save_discovery_search({**self.configure, **changes, "expected_revision": state["revision"]})
        self.search = self.state["searches"][-1]
        return self.search

    def set_result(self, posting="Python required.", rows=None):
        data = rows if rows is not None else [{"public_slug": "synthetic-engineer", "title": "Data Engineer", "company": "Synthetic employer", "description": posting, "url": "https://example.invalid/apply", "location": "India", "work_mode": "remote"}]
        self.raw = json.dumps({"data": data, "meta": {"offset": 0, "limit": 20, "total": len(data)}}).encode()
        self.result = parse_search(self.raw)
        self.service.searcher.search = Mock(return_value=self.result)
        self.service.searcher.snapshots[self.result["source_sha256"]] = self.raw

    def run_search(self):
        return self.service.run_discovery({"id": self.search["id"], "expected_revision": self.service.discovery.read()["revision"], "confirmed": True})

    def action(self, candidate, action):
        return self.service.discovery_decision({"id": candidate, "action": action, "expected_revision": self.service.discovery.read()["revision"], "confirmed": True})

    def test_saved_filters_run_explicitly_and_queue_survives_restart_without_request(self):
        self.service.searcher.search.assert_not_called()
        state = self.run_search(); entry = state["candidates"][0]
        self.service.searcher.search.assert_called_once_with("data engineer", "India", "IN", True, 0)
        self.assertEqual((entry["status"], entry["market"]), ("pending", "india_remote"))
        self.assertEqual(entry["first_search"]["query"], "data engineer")
        self.assertEqual(self.service.store.list_jobs(), [])
        service = WebService(self.root / "jobs.db")
        with patch.object(service.searcher, "search", side_effect=AssertionError("No automatic request")):
            self.assertEqual(service.discovery.read(), state)
        self.assertEqual((service.artifacts / "sources" / (self.result["source_sha256"] + ".json")).read_bytes(), self.raw)

    def test_duplicate_and_cross_search_attribution_preserve_dismissal(self):
        state = self.run_search(); identifier = state["candidates"][0]["id"]
        self.action(identifier, "dismiss")
        self.configure_search(name="Another named search", query="python engineer")
        state = self.run_search()
        self.assertEqual(len(state["candidates"]), 1)
        self.assertEqual(state["candidates"][0]["status"], "dismissed")
        self.assertEqual(len(state["candidates"][0]["search_ids"]), 2)
        self.assertEqual(state["runs"][-1]["repeated"], 1)

    def test_changed_posting_and_other_market_are_separate_observations(self):
        original = self.run_search()["candidates"][0]["id"]; self.action(original, "dismiss")
        self.set_result("Python and SQL required."); state = self.run_search()
        self.assertEqual(len(state["candidates"]), 2)
        self.configure_search(name="Relocation", market="relocation", location="London", country="GB")
        state = self.run_search()
        self.assertEqual(len(state["candidates"]), 3)
        self.assertEqual(state["candidates"][0]["status"], "dismissed")
        self.assertEqual(state["candidates"][-1]["market"], "relocation")

    def test_failure_preserves_queue_counts_attempts_and_never_means_closed(self):
        before = self.run_search()["candidates"]
        self.service.searcher.search = Mock(side_effect=ValueError("Provider returned HTTP 429; no retry"))
        for _ in range(2):
            with self.assertRaises(ValueError): self.run_search()
        state = self.service.discovery.read()
        self.assertEqual(state["candidates"], before)
        self.assertEqual(state["runs"][-1]["status"], "failed")
        with self.assertRaisesRegex(ValueError, "three run attempts"): self.run_search()
        self.assertEqual(self.service.searcher.search.call_count, 2)
        self.assertEqual(len(self.service.discovery.read()["runs"]), 3)

    def test_stale_revision_and_missing_consent_make_no_provider_request(self):
        for changes in ({"expected_revision": 0}, {"confirmed": False}):
            with self.assertRaises(ValueError):
                self.service.run_discovery({"id": self.search["id"], "expected_revision": self.service.discovery.read()["revision"], "confirmed": True, **changes})
        self.service.searcher.search.assert_not_called()
        self.assertEqual(self.service.discovery.read()["runs"], [])

    def test_interrupted_run_blocks_late_results_and_explicit_restart_is_possible(self):
        run = self.service.discovery.begin_run(self.search["id"], self.service.discovery.read()["revision"])
        with self.assertRaises(ValueError): self.run_search()
        self.service.searcher.search.assert_not_called()
        self.action(run["id"], "interrupt")
        with self.assertRaisesRegex(ValueError, "not queued"): self.service.discovery.finish_run(run["id"], self.result)
        self.assertEqual(self.service.discovery.read()["candidates"], [])
        self.assertEqual(self.run_search()["runs"][-1]["status"], "succeeded")

    def test_keep_dismiss_reopen_and_exact_application_save_are_explicit(self):
        identifier = self.run_search()["candidates"][0]["id"]
        for action, status in (("keep", "kept"), ("dismiss", "dismissed"), ("reopen", "pending")):
            self.assertEqual(self.action(identifier, action)["candidates"][0]["status"], status)
        saved = self.action(identifier, "save")["candidates"][0]
        item = self.service.store.load(saved["saved_job_id"])
        self.assertEqual((item["title"], item["market"]), ("Data Engineer", "india_remote"))
        self.assertEqual(json.loads(item["snapshot"])["posting"], "Python required.")
        self.assertEqual(self.service.store.application_history(item["id"]), [])
        self.action(identifier, "save")
        self.assertEqual(len(self.service.store.list_jobs()), 1)

    def test_save_retry_recognizes_application_if_companion_commit_failed(self):
        identifier = self.run_search()["candidates"][0]["id"]
        original = snapshot_bytes
        def refuse_saved(state):
            if any(c["status"] == "saved" for c in state["candidates"]): raise ValueError("Synthetic companion commit failure")
            return original(state)
        with patch("discovery_store.snapshot_bytes", side_effect=refuse_saved), self.assertRaises(ValueError): self.action(identifier, "save")
        self.assertEqual(len(self.service.store.list_jobs()), 1)
        self.assertEqual(self.service.discovery.read()["candidates"][0]["status"], "pending")
        self.action(identifier, "save")
        self.assertEqual(len(self.service.store.list_jobs()), 1)

    def test_archiving_keeps_sources_and_limits_active_searches(self):
        self.configure_search(name="Second"); self.configure_search(name="Third")
        before = self.service.discovery.snapshot()
        with self.assertRaises(ValueError): self.configure_search(name="Fourth")
        self.assertEqual(self.service.discovery.snapshot(), before)
        first = self.service.discovery.read()["searches"][0]
        self.configure_search(**{**{k: v for k, v in first.items() if k != "revision"}, "archived": True})
        self.configure_search(name="Fourth")
        self.assertEqual(sum(not c["archived"] for c in self.service.discovery.read()["searches"]), 3)

    def test_forgetting_resolved_cache_never_deletes_saved_application(self):
        identifier = self.run_search()["candidates"][0]["id"]
        with self.assertRaises(ValueError): self.action(identifier, "forget")
        self.action(identifier, "save"); self.action(identifier, "forget")
        self.assertEqual(len(self.service.store.list_jobs()), 1)
        state = self.run_search()
        self.assertEqual(state["candidates"][0]["status"], "pending")
        self.action(state["candidates"][0]["id"], "save")
        self.assertEqual(len(self.service.store.list_jobs()), 1)

    def test_recovery_preserves_config_queue_decisions_run_budget_and_source_bytes(self):
        identifier = self.run_search()["candidates"][0]["id"]; self.action(identifier, "save")
        original = self.service.discovery.snapshot()
        restored = restore_bundle(self.service.workspace_bundle(), self.root / "recovered")
        service = WebService(recovered_database(self.root / "recovered", restored["id"]))
        self.assertEqual(service.discovery.snapshot(), original)
        self.assertEqual(service.discovery.read()["candidates"][0]["status"], "saved")
        self.assertEqual((service.artifacts / "sources" / (self.result["source_sha256"] + ".json")).read_bytes(), self.raw)

    def test_rehashed_tampered_posting_fails_restore_before_output(self):
        self.run_search(); bundle = self.service.workspace_bundle()
        with zipfile.ZipFile(BytesIO(bundle)) as archive: parts = {n: archive.read(n) for n in archive.namelist()}
        state = parse_snapshot(parts["discovery.json"])
        item = state["candidates"][0]; item["row"]["posting"] = "Tampered posting"
        item["id"] = candidate_key(item["row"], item["market"])
        parts["discovery.json"] = snapshot_bytes(state)
        manifest = json.loads(parts["manifest.json"]); data = parts["discovery.json"]
        manifest["files"]["discovery.json"] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        parts["manifest.json"] = json.dumps(manifest).encode(); stream = BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for n, data in parts.items(): archive.writestr(n, data)
        with self.assertRaises(ValueError): restore_bundle(stream.getvalue(), self.root / "refused")
        self.assertFalse((self.root / "refused").exists())

    def test_old_shelf_bundle_without_discovery_and_foreign_database_remain_safe(self):
        other = self.root / "old"; other.mkdir(); store = JobStore(other / "jobs.db")
        restored = restore_bundle(export_bundle(store, other / "web-artifacts"), self.root / "recovered-old")
        service = WebService(recovered_database(self.root / "recovered-old", restored["id"]))
        self.assertEqual(service.discovery.read()["revision"], 0)
        foreign = self.root / "foreign.db"
        with closing(sqlite3.connect(foreign)) as db, db: db.execute("CREATE TABLE user_data (value TEXT)")
        original = foreign.read_bytes()
        with self.assertRaises(ValueError): DiscoveryStore(foreign)
        self.assertEqual(foreign.read_bytes(), original)

    def test_provider_ignored_values_fail_closed_and_lower_bound_count_keeps_next_page(self):
        raw = json.loads(self.raw)
        raw["meta"]["ignored_values"] = {"countries": ["ZZ"]}
        with self.assertRaises(ValueError): parse_search(json.dumps(raw).encode())
        item = raw["data"][0]
        raw = {"data": [{**item, "public_slug": "synthetic-" + str(i)} for i in range(20)],
               "meta": {"limit": 20, "offset": 0, "total": 20, "total_is_lower_bound": True}}
        self.assertTrue(parse_search(json.dumps(raw).encode())["page"]["has_next"])
        raw["meta"]["total_is_lower_bound"] = False
        self.assertFalse(parse_search(json.dumps(raw).encode())["page"]["has_next"])
        raw["meta"]["total_is_lower_bound"] = 1
        with self.assertRaises(ValueError): parse_search(json.dumps(raw).encode())

    def test_empty_success_does_not_close_or_remove_prior_candidates(self):
        before = self.run_search()["candidates"]
        self.set_result(rows=[]); state = self.run_search()
        self.assertEqual(state["candidates"], before)
        self.assertEqual((state["runs"][-1]["status"], state["runs"][-1]["found"]), ("succeeded", 0))

    def test_full_queue_rolls_back_whole_run_and_preserves_existing_decisions(self):
        self.service.demo = True
        base = self.run_search()["candidates"][0]
        with self.service.discovery.edit() as state:
            state["candidates"] = []
            for i in range(200):
                item = copy.deepcopy(base); item["row"]["id"] = "capacity-" + str(i)
                item["row"]["url"] = "https://example.invalid/capacity/" + str(i)
                item["id"] = candidate_key(item["row"], item["market"])
                state["candidates"].append(item)
        before = self.service.discovery.read()["candidates"]
        with self.assertRaisesRegex(ValueError, "capacity"): self.run_search()
        state = self.service.discovery.read()
        self.assertEqual(state["candidates"], before)
        self.assertEqual(state["runs"][-1]["status"], "failed")

    def test_changed_location_is_a_new_pending_observation_even_for_saved_description(self):
        first = self.run_search()["candidates"][0]
        self.action(first["id"], "save")
        source = json.loads(self.raw)["data"][0]
        self.set_result(rows=[{**source, "location": "London", "work_mode": "on-site"}])
        state = self.run_search()
        self.assertEqual(len(state["candidates"]), 2)
        self.assertEqual(state["candidates"][-1]["status"], "pending")
        self.assertNotEqual(state["candidates"][-1]["id"], first["id"])
        self.action(state["candidates"][-1]["id"], "save")
        self.assertEqual(len(self.service.store.list_jobs()), 1)
