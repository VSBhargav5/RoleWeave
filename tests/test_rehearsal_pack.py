from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from rehearsal_journal import make_rehearsal
from rehearsal_pack import render_pack, export_pack


class RehearsalPackTests(unittest.TestCase):
    def test_selected_evidence_is_private_and_answers_are_opt_in(self):
        with tempfile.TemporaryDirectory() as folder:
            store = JobStore(Path(folder) / "jobs.db")
            job = store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
            snapshot = make_rehearsal(store.load(job), [{"requirement_id": "python", "answer": "PRIVATE ANSWER", "reflection": "PRIVATE NOTE"}], confirmed=True)
            basic = render_pack(snapshot).decode()
            self.assertIn("Python", basic)
            self.assertNotIn("Spark", basic)
            self.assertNotIn("PRIVATE ANSWER", basic)
            self.assertNotIn("PRIVATE NOTE", basic)
            self.assertIn("PRIVATE ANSWER", render_pack(snapshot, include_answers=True).decode())
            self.assertIn("PRIVATE NOTE", render_pack(snapshot, include_answers=True).decode())
            path = Path(folder) / "practice.txt"
            with self.assertRaises(ValueError):
                export_pack(snapshot, path)
            self.assertFalse(path.exists())
            export_pack(snapshot, path, confirmed=True)
            self.assertEqual(path.read_bytes(), render_pack(snapshot))
            with self.assertRaises(FileExistsError):
                export_pack(snapshot, path, confirmed=True)
            with patch("rehearsal_pack.MAX_PACK_BYTES", 5):
                with self.assertRaises(ValueError):
                    render_pack(snapshot)
            with self.assertRaises(ValueError):
                render_pack(snapshot, include_answers=1)
