import copy
import json
from pathlib import Path
import tempfile
import unittest
from roleweave import review, read_review, MAX_BYTES


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).parents[1] / "examples/synthetic.json").read_text())

    def test_evidence_and_gap_stay_distinct(self):
        result = review(self.data)
        self.assertEqual([r["state"] for r in result["requirements"]], ["evidence_selected", "needs_review"])
        self.assertEqual(result["requirements"][0]["evidence"][0]["claim"], self.data["facts"][0]["claim"])
        self.assertNotIn("score", result)

    def test_relocation_is_a_separate_market(self):
        self.data["market"] = "relocation"
        self.assertEqual(review(self.data)["market"], "relocation")

    def test_foreign_unknown_duplicate_or_unreviewed_facts_fail(self):
        for refs in (["invented"], ["project-1", "project-1"]):
            data = copy.deepcopy(self.data)
            data["requirements"][0]["fact_ids"] = refs
            with self.assertRaises(ValueError):
                review(data)
        self.data["facts"][0]["reviewed"] = False
        with self.assertRaises(ValueError):
            review(self.data)

    def test_posting_cannot_create_a_career_fact(self):
        self.data["requirements"][1]["fact_ids"] = ["Production Spark operations required."]
        with self.assertRaises(ValueError):
            review(self.data)

    def test_quote_must_exist_verbatim(self):
        self.data["requirements"][0]["quote"] = "Python expert required."
        with self.assertRaises(ValueError):
            review(self.data)

    def test_duplicate_ids_and_non_boolean_review_fail(self):
        for mutate in (lambda d: d["facts"].append(d["facts"][0]),
                       lambda d: d["requirements"].append(d["requirements"][0]),
                       lambda d: d["facts"][0].update(reviewed="true")):
            data = copy.deepcopy(self.data)
            mutate(data)
            with self.assertRaises(ValueError):
                review(data)

    def test_unknown_fields_and_bad_shapes_fail(self):
        for value in (None, [], {}, {**self.data, "score": 99}, {**self.data, "market": "global"},
                      {**self.data, "facts": "text"}):
            with self.assertRaises(ValueError):
                review(value)

    def test_input_snapshot_hash_and_posting_hash_detect_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            path.write_text(json.dumps(self.data))
            first = read_review(path)
            path.write_text(json.dumps(self.data, indent=2))
            second = read_review(path)
            self.assertNotEqual(first["input_sha256"], second["input_sha256"])
            self.assertEqual(first["posting_sha256"], second["posting_sha256"])

    def test_duplicate_keys_malformed_and_oversize_files_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            for content in (b'{"market":"india_remote","market":"relocation"}', b"bad", b"x" * (MAX_BYTES + 1)):
                path.write_bytes(content)
                with self.assertRaises(ValueError):
                    read_review(path)
