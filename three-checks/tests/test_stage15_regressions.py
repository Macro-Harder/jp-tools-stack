import json
import os
import unittest

from helpers import EXAMPLES_DIR, ThreeChecksCase, load_json


class TestStage15M1(ThreeChecksCase):
    def test_unclaimed_step_with_no_matching_link_carries_both_no_link_entries(self):
        bundle = load_json(os.path.join(EXAMPLES_DIR, "example_bundle.json"))
        bundle["claim"]["steps_claimed"] = ["S1"]
        for link in bundle["links"]:
            if link["step_id"] == "S2":
                del link["produced_at"]
        r = self.run_bundle(bundle)
        entries = r.entries_for("COMP-NO-LINK", "S2")
        self.assertEqual(len(entries), 2, repr(entries))
        stage_entries = [entry for entry in entries if entry["part"] == "stage"]
        self.assertEqual(len(stage_entries), 1, repr(entries))
        self.assertEqual(stage_entries[0]["subject"], "S2")
        self.assertEqual(stage_entries[0]["found"], "the step is not claimed")
        self.assertEqual(stage_entries[0]["check"], "completeness")
        self.assertEqual(stage_entries[0]["expected"], "at least one matching link")
        per_step_entries = [entry for entry in entries if entry["part"] != "stage"]
        self.assertEqual(len(per_step_entries), 1, repr(entries))
        self.assertEqual(per_step_entries[0]["part"], "part1")
        self.assertEqual(per_step_entries[0]["subject"], "S2")
        self.assertEqual(per_step_entries[0]["found"], "no matching link")
        self.assertEqual(per_step_entries[0]["check"], "completeness")
        self.assertEqual(per_step_entries[0]["expected"], "at least one matching link")


if __name__ == "__main__":
    unittest.main()
