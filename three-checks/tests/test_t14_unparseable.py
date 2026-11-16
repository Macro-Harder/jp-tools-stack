import json
import os
import unittest
from helpers import ThreeChecksCase, TRANSCRIPTIONS, T_EARLY

TIME_PAIRS = json.load(open(os.path.join(TRANSCRIPTIONS, "time_pairs.json")))
BAD = "not-a-time"


class TestT14UnparseableTimes(ThreeChecksCase):
    def test_created_at_unparseable_bound_record(self):
        def mut(b):
            b["spawn_records"]["records"][0]["created_at"] = BAD
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-STEP-TIME", subject="S1")

    def test_created_at_unparseable_unbound_record(self):
        def mut(b):
            rec = dict(b["spawn_records"]["records"][0])
            rec["agent_id"] = "agent-u"
            rec["session_id"] = "sess-u"
            rec["created_at"] = BAD
            b["spawn_records"]["records"].append(rec)
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-STEP-TIME", subject="agent-u", part="stage")
        self.assertIn("sess-u", entry["found"])

    def test_ran_at_unparseable(self):
        def mut(b):
            b["links"][0]["ran_at"] = BAD
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-STEP-TIME", subject="S1")
        self.assertIn(BAD, entry["found"])
        self.assertIn("ran_at", entry["cure"])

    def test_recorded_at_unparseable_parseable_entry_stands(self):
        def mut(b):
            b["roster"]["entries"].insert(0, {"seat": "builder", "agent_id": "agent-1", "recorded_at": BAD, "origin": "layout"})
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["checks"]["authenticity"], "pass", repr(r.results))

    def test_recorded_at_unparseable_no_parseable_entry(self):
        def mut(b):
            b["roster"]["entries"][0]["recorded_at"] = BAD
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-NO-ROSTER", subject="S1")
        self.assertIn(BAD, entry["found"])

    def test_recorded_at_unparseable_with_parseable_late_entry(self):
        def mut(b):
            b["roster"]["entries"][0]["recorded_at"] = BAD
            b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-1", "recorded_at": "2026-01-02T00:00:00Z", "origin": "layout"})
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-LATE-RECORD", subject="S1")
        self.assertEqual([e for e in r.entries("AUTH-NO-ROSTER") if e["subject"] == "S1"], [])

    def test_republished_at_unparseable(self):
        def mut(b):
            b["roster"]["entries"][0]["origin"] = "addition"
            b["roster"]["republications"] = [{"seat": "builder", "republished_at": BAD}]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-NO-REPUB", subject="S1")
        self.assertIn(BAD, entry["found"])

    def test_republication_mixed_parseable_governs(self):
        def mut(b):
            b["roster"]["entries"][0]["origin"] = "addition"
            b["roster"]["republications"] = [{"seat": "builder", "republished_at": BAD}, {"seat": "builder", "republished_at": "2026-01-01T11:00:00Z"}]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["checks"]["authenticity"], "pass", repr(r.results))
        self.assertEqual(r.entries("AUTH-NO-REPUB"), [])

    def test_republication_all_unparseable_first_value_named(self):
        def mut(b):
            b["roster"]["entries"][0]["origin"] = "addition"
            b["roster"]["republications"] = [{"seat": "builder", "republished_at": "bad-one"}, {"seat": "builder", "republished_at": "bad-two"}]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-NO-REPUB", subject="S1")
        self.assertIn("bad-one", entry["found"])

    def test_produced_at_unparseable(self):
        def mut(b):
            b["links"][0]["produced_at"] = BAD
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-RECONSTRUCTED", subject="S1")
        self.assertIn(BAD, entry["found"])

    def test_completed_at_unparseable(self):
        def mut(b):
            b["claim"]["step_completions"][0]["completed_at"] = BAD
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-RECONSTRUCTED", subject="S1")
        self.assertIn("does not parse", entry["found"])

    def test_push_verified_at_unparseable_in_play(self):
        def mut(b):
            b["push_record"]["verified_at"] = BAD
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-ORIGIN", subject="push", part="stage")

    def test_exported_at_unparseable_no_effect(self):
        def mut(b):
            b["spawn_records"]["exported_at"] = BAD
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))
        self.assertIn("exported_at=" + BAD, r.report_text)


class TestT14TimeForms(ThreeChecksCase):
    pass


# The form and relation cases are driven by the recorded time pair table in
# transcriptions/time_pairs.json, under the oracle rule: each row states the
# pair, the expected relation, and the expected parse success, recorded
# outside the tool. In each generated case the first value of the pair is the
# spawn record created_at and the second value is the link ran_at, so the
# time anchor outcome states the relation directly: a parseable created_at
# equal to or before ran_at passes, a parseable created_at after ran_at
# fails under AUTH-STEP-TIME, and a created_at that does not parse fails
# under AUTH-STEP-TIME as a time that cannot be anchored.
for index, pair in enumerate(TIME_PAIRS):
    def make(pair=pair, index=index):
        def test(self):
            def mut(b):
                b["spawn_records"]["records"][0]["created_at"] = pair["a"]
                b["links"][0]["ran_at"] = pair["b"]
            r = self.run_bundle(self.mutate(mut))
            self.assertNotEqual(r.exit_status, 2, r.stderr)
            if not pair["a_parses"]:
                self.assert_entry(r, "AUTH-STEP-TIME", subject="S1")
            elif pair["relation"] in ("equal", "before"):
                self.assertEqual(r.results["checks"]["authenticity"], "pass", repr(r.results))
            elif pair["relation"] == "after":
                self.assert_entry(r, "AUTH-STEP-TIME", subject="S1")
            else:
                raise AssertionError("unmapped time pair relation: " + repr(pair))
        return test
    label = pair["relation"].replace(" ", "_").replace("-", "_")
    setattr(TestT14TimeForms, "test_pair_" + str(index) + "_" + label, make())


class TestT14Digests(ThreeChecksCase):
    def test_chain_material_out_of_form(self):
        def mut(b):
            b["links"][1]["inputs"][0]["sha256"] = "XYZ"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-JOIN")

    def test_subject_artifact_digest_out_of_form(self):
        def mut(b):
            b["links"][0]["subject_artifacts"][0]["sha256"] = "XYZ"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "COMP-ARTIFACT", subject="A1")

    def test_stated_artifact_digest_out_of_form(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["sha256"] = "XYZ"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "COMP-ARTIFACT", subject="A1")

    def test_push_hash_out_of_form_claimed_vs_record(self):
        def mut(b):
            b["claim"]["push_link"] = {"repo": "repo-1", "head_sha": "XYZ", "tree_sha": "t1"}
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-ORIGIN", subject="push")

    def test_uppercase_hex_out_of_form(self):
        def mut(b):
            b["links"][1]["inputs"][0]["sha256"] = "A" * 64
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-JOIN")

    def test_digest_63_chars_out_of_form(self):
        def mut(b):
            b["links"][1]["inputs"][0]["sha256"] = "a" * 63
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-JOIN")

    def test_digest_65_chars_out_of_form(self):
        def mut(b):
            b["links"][1]["inputs"][0]["sha256"] = "a" * 65
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-JOIN")

    def test_non_string_digest_is_type_error(self):
        def mut(b):
            b["links"][0]["outputs"][0]["sha256"] = 7
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn("must be string", r.stderr)

    def test_time_pairs_table_shape(self):
        self.assertEqual(len(TIME_PAIRS), 12)
        for pair in TIME_PAIRS:
            self.assertIn("relation", pair)


if __name__ == "__main__":
    unittest.main()
