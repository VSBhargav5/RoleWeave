import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from rehearsal_journal import make_rehearsal
from rehearsal_compare import compare_rehearsals, comparison_bytes, export_comparison


class RehearsalCompareTests(unittest.TestCase):
    def test_changed_selection_text_time_and_exact_source_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            store = JobStore(Path(folder) / "jobs.db")
            raw = (Path(__file__).parents[1] / "examples/synthetic.json").read_bytes()
            job = store.save(raw, "Engineer", "Synthetic")
            first = make_rehearsal(store.load(job), [{"requirement_id": "python", "answer": "First", "reflection": ""},
                                                    {"requirement_id": "spark", "answer": "", "reflection": "Open"}], confirmed=True)
            second = make_rehearsal(store.load(job), [{"requirement_id": "python", "answer": "Revised", "reflection": "Check limits"}], elapsed_seconds=42, confirmed=True)
            report = compare_rehearsals(first, second)
            self.assertEqual([row["state"] for row in report["questions"]], ["draft_changed", "not_selected"])
            self.assertEqual(report["elapsed_seconds_delta"], 42)
            self.assertFalse(report["learning_verified"])
            self.assertEqual(compare_rehearsals(first, first)["questions"][0]["state"], "unchanged")
            reversed_report = json.loads(first)
            reversed_report["recorded_at"] = "2099-01-01T00:00:00+00:00"
            with self.assertRaises(ValueError):
                compare_rehearsals(json.dumps(reversed_report).encode(), second)
            other = store.save(raw, "Another role", "Synthetic")
            different = make_rehearsal(store.load(other), [{"requirement_id": "python", "answer": "", "reflection": ""}], confirmed=True)
            with self.assertRaises(ValueError):
                compare_rehearsals(first, different)
            path = Path(folder) / "comparison.json"
            with self.assertRaises(ValueError):
                export_comparison(first, second, path)
            export_comparison(first, second, path, confirmed=True)
            self.assertEqual(json.loads(path.read_bytes()), report)
            with self.assertRaises(FileExistsError):
                export_comparison(first, second, path, confirmed=True)
            with patch("rehearsal_compare.MAX_COMPARISON_BYTES", 10):
                with self.assertRaises(ValueError):
                    comparison_bytes(first, second)
