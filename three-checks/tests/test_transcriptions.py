import json
import os
import unittest
from helpers import TRANSCRIPTIONS, GOLDEN, FIXTURES

CODES = ["ABSENT-SECTION", "AUTH-NO-SPAWN", "AUTH-NO-ROSTER", "AUTH-STEP-TIME", "AUTH-LATE-RECORD", "AUTH-NO-REPUB", "AUTH-NO-PUSH", "AUTH-ORIGIN", "LINK-NO-STEP", "CHAIN-JOIN", "CHAIN-BOUNDARY", "COMP-NO-LINK", "COMP-RECONSTRUCTED", "COMP-ARTIFACT", "COMP-PROPERTY", "COMP-UNSUPPORTED-PROPERTY", "COMP-LEDGER", "LINK-PREDICATE", "ANOM-MULTI-LINK"]


def load(name, base=TRANSCRIPTIONS):
    with open(os.path.join(base, name), encoding="utf-8") as handle:
        return json.load(handle)


class TestTranscriptions(unittest.TestCase):
    def test_absence_table_has_six_required_sections(self):
        table = load("absence_table.json")
        self.assertEqual(set(table.keys()), {"layout", "roster", "links", "spawn_records", "identities", "claim"})
        for row in table.values():
            self.assertIn("triage", row)
            self.assertIn("subresults", row)

    def test_consequence_table_covers_19_codes(self):
        data = load("consequence_table.json")
        self.assertEqual(data["codes"], CODES)
        self.assertEqual(set(data["table"].keys()), set(CODES))
        self.assertEqual(data["table"]["ABSENT-SECTION"], "UNVERIFIABLE")
        self.assertEqual(data["table"]["ANOM-MULTI-LINK"], "none")

    def test_part_assignment_table_covers_19_codes_with_subjects(self):
        table = load("part_assignment_table.json")
        self.assertEqual(set(table.keys()), set(CODES))
        for code, row in table.items():
            self.assertTrue(row["part"], code)
            self.assertTrue(row["subject"], code)

    def test_oracle_literals_are_64_lower_hex(self):
        data = load("oracle_literals.json")["sha256"]
        self.assertEqual(set(data.keys()), {"empty", "hello", "zero_bytes_32", "artifact_one"})
        for value in data.values():
            self.assertEqual(len(value), 64)
            self.assertEqual(value, value.lower())
            int(value, 16)

    def test_time_pairs_cover_rejection_shapes(self):
        pairs = load("time_pairs.json")
        self.assertEqual(len(pairs), 12)
        self.assertTrue(any(not pair["a_parses"] for pair in pairs))
        self.assertTrue(any(pair["relation"] == "equal" for pair in pairs))

    def test_golden_authorisation_record_shape(self):
        data = load("authorisation_record.json", GOLDEN)
        for key in ("link_index", "binding_outcome", "time_anchor_outcome", "authorisation_outcome", "first_failing_subtest", "authenticity_outcome", "all_unparseable_republication_marker"):
            self.assertIn(key, data)

    def test_golden_matching_shape(self):
        data = load("matching.json", GOLDEN)
        self.assertIn("steps", data)
        self.assertIn("stage_level", data)
        self.assertIn("orphan_links", data["stage_level"])

    def test_golden_completeness_shape(self):
        data = load("completeness_result.json", GOLDEN)
        self.assertEqual(set(data["subresults"].keys()), {"links", "artifacts", "ledger"})
        outcomes = [item["outcome"] for item in data["artifacts"][0]["standing"]]
        self.assertEqual(outcomes, ["pass", "pass", "pass"])

    def test_fixture_note_names_copied_sources(self):
        with open(os.path.join(FIXTURES, "FIXTURE_NOTE.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("copied_brief_excerpt.txt", text)
        self.assertIn("copied_plan_excerpt.txt", text)
        self.assertIn("uid 0", text)
        self.assertIn("frozen at creation", text)

    def test_hand_built_bundle_fixtures_exist(self):
        bundles = os.path.join(FIXTURES, "bundles")
        for name in ("passing_minimal.json", "missing_claim.json", "unknown_top_field.json", "empty_steps.json", "duplicate_key.json", "nan_token.json", "infinity_token.json", "top_level_list.json"):
            self.assertTrue(os.path.isfile(os.path.join(bundles, name)), name)

    def test_artifact_fixtures_exist(self):
        artifacts = os.path.join(FIXTURES, "artifacts")
        for name in ("artifact1.txt", "empty.txt", "no_trailing_newline.txt", "crlf.txt", "non_utf8.bin", "copied_brief_excerpt.txt", "copied_plan_excerpt.txt"):
            self.assertTrue(os.path.isfile(os.path.join(artifacts, name)), name)


if __name__ == "__main__":
    unittest.main()
