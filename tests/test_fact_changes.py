import copy
import json
from pathlib import Path
import unittest

from roleweave import revise_fact, remove_fact, review


class FactChangeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes())
        self.original = copy.deepcopy(self.data)

    def test_changed_claim_unlinks_every_requirement_preserving_original(self):
        self.data["requirements"][1]["fact_ids"] = ["project-1"]
        before = copy.deepcopy(self.data)
        revised, count = revise_fact(self.data, "project-1", "Corrected project scope", "Reviewed source", True)
        self.assertEqual(count, 2)
        self.assertEqual([item["state"] for item in review(revised)["requirements"]], ["needs_review"] * 2)
        self.assertEqual(revised["facts"][0]["id"], "project-1")
        self.assertEqual(self.data, before)

    def test_source_correction_unlinks_even_with_unchanged_claim(self):
        revised, count = revise_fact(self.data, "project-1", self.data["facts"][0]["claim"], "Corrected provenance", True)
        self.assertEqual(count, 1)
        self.assertEqual(revised["requirements"][0]["fact_ids"], [])

    def test_revoking_review_unlinks_but_unchanged_reviewed_fact_keeps_links(self):
        fact = self.data["facts"][0]
        revised, count = revise_fact(self.data, fact["id"], fact["claim"], fact["source"], False)
        self.assertEqual(count, 1)
        self.assertFalse(revised["facts"][0]["reviewed"])
        same, count = revise_fact(self.data, fact["id"], fact["claim"], fact["source"], True)
        self.assertEqual(count, 0)
        self.assertEqual(same, self.original)

    def test_invalid_changes_do_not_mutate_input(self):
        for identifier, claim, source, reviewed in (("unknown", "a", "b", True),
                ("project-1", "", "b", True), ("project-1", "a", "", True),
                ("project-1", "a", "b", "true")):
            with self.assertRaises(ValueError):
                revise_fact(self.data, identifier, claim, source, reviewed)
            self.assertEqual(self.data, self.original)

    def test_remove_only_unlinked_fact_without_mutating_original(self):
        with self.assertRaisesRegex(ValueError, "Unlink"):
            remove_fact(self.data, "project-1")
        unlinked, _ = revise_fact(self.data, "project-1", "Corrected claim", "Reviewed source", True)
        removed = remove_fact(unlinked, "project-1")
        self.assertEqual(removed["facts"], [])
        self.assertEqual(len(unlinked["facts"]), 1)
        self.assertEqual(self.data, self.original)
        review(removed)
        with self.assertRaises(ValueError):
            remove_fact(self.data, "unknown")
