import copy
import json
from datetime import datetime, timedelta
import os
import unittest
from helpers import ThreeChecksCase, EXAMPLES_DIR


class TestNamedMutations(ThreeChecksCase):
    def load_example(self):
        bundle_path = os.path.join(EXAMPLES_DIR, "example_bundle.json")
        if not os.path.isfile(bundle_path):
            self.fail("missing shipped companion: examples pair bundle " + bundle_path + " (lands at build step 10, so the named mutations cannot run at stage 13)")
        with open(bundle_path, encoding="utf-8") as handle:
            return json.load(handle)

    def run_example(self, bundle):
        artifacts = {}
        for name in os.listdir(EXAMPLES_DIR):
            if name.startswith("expected") or name.endswith(".json"):
                continue
            with open(os.path.join(EXAMPLES_DIR, name), "rb") as handle:
                artifacts[name] = handle.read()
        return self.run_bundle(bundle, artifacts=artifacts if artifacts else None)

    def check_mutation(self, mutator, code, expected_codes=None):
        bundle = self.load_example()
        mutator(bundle)
        r = self.run_example(bundle)
        self.assertEqual(r.exit_status, 1, repr(r.results))
        codes = [e["code"] for e in r.results["discrepancies"]]
        self.assertIn(code, codes)
        expected = set(expected_codes) if expected_codes is not None else {code}
        self.assertEqual(set(codes), expected, "mutation must produce exactly its expected code set: " + repr(codes))

    def test_mutation_01_digest_char_in_link_output(self):
        def mut(b):
            digest = b["links"][0]["outputs"][0]["sha256"]
            b["links"][0]["outputs"][0]["sha256"] = ("b" if digest[0] != "b" else "c") + digest[1:]
        self.check_mutation(mut, "CHAIN-JOIN")

    def test_mutation_02_digest_char_in_subject_artifact(self):
        def mut(b):
            digest = b["links"][0]["subject_artifacts"][0]["sha256"]
            b["links"][0]["subject_artifacts"][0]["sha256"] = ("b" if digest[0] != "b" else "c") + digest[1:]
        self.check_mutation(mut, "COMP-ARTIFACT")

    def test_mutation_03_roster_recorded_one_second_late(self):
        def mut(b):
            for entry in b["roster"]["entries"]:
                for link in b["links"]:
                    if entry["seat"] and entry["agent_id"] == link["performer_spawn_id"]:
                        entry["recorded_at"] = "2026-01-01T12:00:01Z"
                        return
        self.check_mutation(mut, "AUTH-LATE-RECORD", expected_codes={"AUTH-LATE-RECORD", "COMP-NO-LINK", "CHAIN-JOIN"})

    def test_mutation_04_produced_at_removed(self):
        def mut(b):
            del b["links"][0]["produced_at"]
        self.check_mutation(mut, "COMP-RECONSTRUCTED", expected_codes={"COMP-RECONSTRUCTED", "COMP-NO-LINK", "CHAIN-JOIN"})

    def test_mutation_05_produced_at_past_completion(self):
        def mut(b):
            done = b["claim"]["step_completions"][0]["completed_at"]
            parsed = datetime.strptime(done, "%Y-%m-%dT%H:%M:%SZ") + timedelta(seconds=1)
            b["links"][0]["produced_at"] = parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
        self.check_mutation(mut, "COMP-RECONSTRUCTED", expected_codes={"COMP-RECONSTRUCTED", "COMP-NO-LINK", "CHAIN-JOIN"})

    def test_mutation_06_ledger_claim_renamed(self):
        def mut(b):
            b["claim"]["ledger_claims"][0] = b["claim"]["ledger_claims"][0] + "-renamed"
        self.check_mutation(mut, "COMP-LEDGER")

    def test_mutation_07_record_source_self_reported(self):
        def mut(b):
            b["layout"]["record_sources"][0]["source"] = "self-reported-file"
        self.check_mutation(mut, "AUTH-ORIGIN")

    def test_mutation_08_step_claimed_not_in_layout(self):
        def mut(b):
            b["claim"]["steps_claimed"].append("S-NOT-IN-LAYOUT")
        bundle = self.load_example()
        mut(bundle)
        r = self.run_example(bundle)
        self.assertEqual(r.exit_status, 1, repr(r.results))
        codes = [e["code"] for e in r.results["discrepancies"]]
        self.assertEqual(set(codes), {"COMP-NO-LINK"}, repr(codes))
        entry = r.entries("COMP-NO-LINK")[0]
        self.assertEqual(entry["part"], "stage")
        self.assertEqual(entry["subject"], "S-NOT-IN-LAYOUT")

    def test_mutation_09_material_name_duplicated_agreeing(self):
        def mut(b):
            b["links"][0]["outputs"].append(copy.deepcopy(b["links"][0]["outputs"][0]))
        self.check_mutation(mut, "CHAIN-JOIN")

    def test_mutation_10_republication_removed(self):
        def mut(b):
            b["roster"]["republications"] = [e for e in b["roster"].get("republications", []) if False]
            b["roster"]["republications"] = []
        self.check_mutation(mut, "AUTH-NO-REPUB", expected_codes={"AUTH-NO-REPUB", "COMP-NO-LINK", "CHAIN-JOIN"})


if __name__ == "__main__":
    unittest.main()
