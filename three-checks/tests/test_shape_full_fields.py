import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from helpers import GOLDEN, PROGRAM, ART_TEXT, base_bundle

# Stage 14 shape tests for build steps 5 to 7. The stage 13 suite exercises
# the program only as a subprocess. These tests import the program module and
# assert the full field lists of plan parts 2.3 to 2.5 on the shapes the
# parts produce, as the carry forward condition in tests/README.md (F-21 and
# gap G-3) requires: the golden files under golden/ are subsets of those
# field lists, and each golden value is asserted against the shape here.

AUTHORISATION_RECORD_FIELDS = [
    "link_index", "step_id", "predicate_type", "performer_spawn_id", "builder",
    "ran_at", "binding_outcome", "binding_spawn_record", "spawn_created_at",
    "time_anchor_outcome", "roster_entries_considered", "authorising_entry",
    "authorisation_outcome", "recorded_at_for_report",
    "origin_of_authorising_entry", "seat_stands_in_advance_layout",
    "governing_republication", "republication_outcome",
    "all_unparseable_republication_marker", "first_failing_subtest",
    "authenticity_outcome", "part_assignment_input",
]
MATCHING_STEP_FIELDS = [
    "step", "presented_links", "per_step_authenticity",
    "reconstruction_outcomes", "matching_links", "per_step_matching",
    "multi_link", "predicate_mismatch_links",
]
MATCHING_STAGE_FIELDS = [
    "steps", "layout_steps_not_claimed",
    "claimed_steps_naming_no_layout_step", "orphan_links",
]
EXPORT_FACTS_FIELDS = [
    "duplicated_export_identities", "unbound_unparseable_creation_facts",
]
AUTHENTICITY_RESULT_FIELDS = [
    "check", "per_link_outcomes", "entries", "origin_outcomes",
    "full_pass_origin_facts",
]
CHAIN_RESULT_FIELDS = ["check", "join_outcomes", "boundary_outcome", "entries"]
JOIN_OUTCOME_FIELDS = ["earlier_step", "later_step", "result", "entries"]
BOUNDARY_OUTCOME_FIELDS = ["status", "entries"]
COMPLETENESS_RESULT_FIELDS = ["check", "links", "artifacts", "ledger"]
LINKS_SUBRESULT_FIELDS = ["value", "entries", "anomaly_entries"]
ARTIFACTS_SUBRESULT_FIELDS = ["value", "per_artifact", "entries"]
PER_ARTIFACT_FIELDS = [
    "artifact_id", "coverage_outcome", "standing_outcomes", "property_outcomes",
]
STANDING_OUTCOME_FIELDS = ["test", "outcome"]
LEDGER_SUBRESULT_FIELDS = ["value", "per_element", "entries"]
PER_ELEMENT_FIELDS = ["entry_id", "outcome"]


def load_program():
    spec = importlib.util.spec_from_file_location("three_checks", PROGRAM)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_golden(name):
    with open(os.path.join(GOLDEN, name), encoding="utf-8") as handle:
        return json.load(handle)


class TestShapeFullFields(unittest.TestCase):
    def setUp(self):
        self.module = load_program()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bundle_dir = Path(self.tmp.name)
        with open(self.bundle_dir / "artifact1.txt", "w", encoding="utf-8") as handle:
            handle.write(ART_TEXT)
        self.vb = self.module.build_validated(base_bundle(), "0" * 64, self.bundle_dir)
        self.records, self.details, self.seat_input = self.module.build_authorisation_records(self.vb)
        self.seat_parts = self.module.seat_part_map(self.vb, self.seat_input)
        self.matching = self.module.build_matching(self.vb, self.records)

    def test_authorisation_record_full_field_list(self):
        record = self.records[0]
        self.assertEqual(sorted(record.keys()), sorted(AUTHORISATION_RECORD_FIELDS))

    def test_authorisation_record_golden_subset_values(self):
        golden = load_golden("authorisation_record.json")
        record = self.records[0]
        for key, value in golden.items():
            if key == "ran_at":
                self.assertEqual(record["ran_at"]["raw"], value["raw"])
                self.assertEqual(record["ran_at"]["parses"], value["parses"])
            else:
                self.assertIn(key, record)
                self.assertEqual(record[key], value, key)
        self.assertIsNotNone(record["binding_spawn_record"])
        self.assertIsNotNone(record["spawn_created_at"])
        self.assertEqual(len(record["roster_entries_considered"]), 1)
        self.assertIsNotNone(record["authorising_entry"])
        self.assertIsNone(record["governing_republication"])
        self.assertIsNotNone(record["part_assignment_input"])

    def test_matching_full_field_list(self):
        self.assertEqual(sorted(self.matching.keys()), sorted(MATCHING_STAGE_FIELDS))
        for step_result in self.matching["steps"]:
            self.assertEqual(sorted(step_result.keys()), sorted(MATCHING_STEP_FIELDS))

    def test_matching_golden_subset_values(self):
        golden = load_golden("matching.json")
        first = self.matching["steps"][0]
        golden_first = golden["steps"][0]
        self.assertEqual(first["step"]["step_id"], golden_first["step_id"])
        self.assertEqual(first["per_step_authenticity"], golden_first["per_step_authenticity"])
        self.assertEqual(first["per_step_matching"], golden_first["per_step_matching"])
        self.assertEqual(first["multi_link"], golden_first["multi_link"])
        self.assertEqual(len(first["matching_links"]), golden_first["matching_link_count"])
        self.assertEqual(len(first["predicate_mismatch_links"]), golden_first["predicate_mismatch_count"])
        self.assertEqual(len(first["presented_links"]), 1)
        self.assertEqual(len(first["reconstruction_outcomes"]), 1)
        self.assertEqual(first["reconstruction_outcomes"][0]["outcome"], "pass")
        stage = golden["stage_level"]
        self.assertEqual(self.matching["layout_steps_not_claimed"], stage["layout_steps_not_claimed"])
        self.assertEqual(self.matching["claimed_steps_naming_no_layout_step"], stage["claimed_steps_naming_no_layout_step"])
        self.assertEqual(self.matching["orphan_links"], stage["orphan_links"])

    def test_export_facts_and_authenticity_full_field_list(self):
        export_facts = self.module.scan_export(self.vb)
        self.assertEqual(sorted(export_facts.keys()), sorted(EXPORT_FACTS_FIELDS))
        self.assertEqual(export_facts["duplicated_export_identities"], [])
        self.assertEqual(export_facts["unbound_unparseable_creation_facts"], [])
        result = self.module.run_authenticity(self.vb, self.records, self.details, export_facts, self.seat_parts)
        self.assertEqual(sorted(result.keys()), sorted(AUTHENTICITY_RESULT_FIELDS))
        self.assertEqual(result["check"], "pass")
        self.assertTrue(result["full_pass_origin_facts"]["roster_origin_pass"])
        self.assertIn("roster", result["origin_outcomes"])
        self.assertIn("push", result["origin_outcomes"])

    def test_chain_result_full_field_list(self):
        result = self.module.run_chain(self.vb, self.matching, self.seat_parts, False)
        self.assertEqual(sorted(result.keys()), sorted(CHAIN_RESULT_FIELDS))
        self.assertEqual(result["check"], "pass")
        self.assertEqual(len(result["join_outcomes"]), 1)
        self.assertEqual(sorted(result["join_outcomes"][0].keys()), sorted(JOIN_OUTCOME_FIELDS))
        self.assertEqual(sorted(result["boundary_outcome"].keys()), sorted(BOUNDARY_OUTCOME_FIELDS))
        self.assertEqual(result["boundary_outcome"]["status"], "not applicable")

    def test_completeness_result_full_field_list_and_golden(self):
        result = self.module.run_completeness(self.vb, self.matching, self.seat_parts, False)
        self.assertEqual(sorted(result.keys()), sorted(COMPLETENESS_RESULT_FIELDS))
        self.assertEqual(sorted(result["links"].keys()), sorted(LINKS_SUBRESULT_FIELDS))
        self.assertEqual(sorted(result["artifacts"].keys()), sorted(ARTIFACTS_SUBRESULT_FIELDS))
        self.assertEqual(sorted(result["ledger"].keys()), sorted(LEDGER_SUBRESULT_FIELDS))
        per_artifact = result["artifacts"]["per_artifact"][0]
        self.assertEqual(sorted(per_artifact.keys()), sorted(PER_ARTIFACT_FIELDS))
        for standing in per_artifact["standing_outcomes"]:
            self.assertEqual(sorted(standing.keys()), sorted(STANDING_OUTCOME_FIELDS))
        per_element = result["ledger"]["per_element"][0]
        self.assertEqual(sorted(per_element.keys()), sorted(PER_ELEMENT_FIELDS))
        golden = load_golden("completeness_result.json")
        self.assertEqual(result["check"], golden["check"])
        self.assertEqual(result["links"]["value"], golden["subresults"]["links"])
        self.assertEqual(result["artifacts"]["value"], golden["subresults"]["artifacts"])
        self.assertEqual(result["ledger"]["value"], golden["subresults"]["ledger"])
        golden_artifact = golden["artifacts"][0]
        self.assertEqual(per_artifact["artifact_id"], golden_artifact["artifact_id"])
        self.assertEqual(per_artifact["coverage_outcome"], golden_artifact["coverage"])
        self.assertEqual(per_artifact["standing_outcomes"], golden_artifact["standing"])
        self.assertEqual(per_artifact["property_outcomes"], golden_artifact["properties"])
        self.assertEqual(result["ledger"]["per_element"], golden["ledger"])


if __name__ == "__main__":
    unittest.main()
