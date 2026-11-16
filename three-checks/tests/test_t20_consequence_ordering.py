import json
import os
import unittest
from helpers import ThreeChecksCase, TRANSCRIPTIONS, ART_DIGEST

CONSEQUENCE = json.load(open(os.path.join(TRANSCRIPTIONS, "consequence_table.json")))["table"]
PART_TABLE = json.load(open(os.path.join(TRANSCRIPTIONS, "part_assignment_table.json")))

CURES = {
    "ABSENT-SECTION": "supply the roster section in the bundle.",
    "AUTH-NO-SPAWN": "supply exactly one spawn record for the performer identity in the export.",
    "AUTH-NO-ROSTER": "supply a roster entry authorising the seat for the performer with a parseable recorded_at at or before the step run time.",
    "AUTH-STEP-TIME": "supply a spawn record whose created_at parses and is at or before the step run time, and, for the ran_at variant, supply a link whose ran_at parses.",
    "AUTH-LATE-RECORD": "supply a roster entry for the seat and performer recorded at or before the step run time.",
    "AUTH-NO-REPUB": "supply a republication for the seat with a parseable republished_at at or before the step run time.",
    "AUTH-NO-PUSH": "supply the push_record section for the push link in play.",
    "AUTH-ORIGIN": "supply the record kind from its required origin, runtime-spawn-records for roster or api-verification for push, or correct the differing push field.",
    "LINK-NO-STEP": "supply the step in the layout, or withdraw the link.",
    "CHAIN-JOIN": "supply matching links whose outputs and inputs agree on every name, or correct the differing material entry.",
    "CHAIN-BOUNDARY": "supply previous stage outputs matching the predecessor inputs on every name, or withdraw the predecessor inputs claim.",
    "COMP-NO-LINK": "supply a genuine link for the step, or withdraw the step from the layout.",
    "COMP-RECONSTRUCTED": "supply a genuine link produced within the step run and completion times, with its completion time recorded.",
    "COMP-ARTIFACT": "supply the artifact file at its path with the stated digest, or correct the stated digest and the link naming it.",
    "COMP-PROPERTY": "supply an artifact file for which the stated property holds, or correct the stated property.",
    "COMP-UNSUPPORTED-PROPERTY": "state the property in one of the seven evaluated kinds, or withdraw the property.",
    "COMP-LEDGER": "supply the path ledger entry for the claimed element, or withdraw the claim for that element.",
    "LINK-PREDICATE": "supply a link whose predicate_type equals the layout step predicate_type.",
    "ANOM-MULTI-LINK": "no cure is required; the anomaly is reported and the run is not failed by it.",
}


def producer(code):
    def absent(b):
        del b["roster"]
    def no_spawn(b):
        b["links"][0]["performer_spawn_id"] = "agent-unknown"
        b["roster"]["entries"][0]["agent_id"] = "agent-unknown"
    def no_roster(b):
        b["roster"]["entries"] = [e for e in b["roster"]["entries"] if e["seat"] != "builder"]
    def step_time(b):
        b["spawn_records"]["records"][0]["created_at"] = "2026-01-01T12:00:01Z"
    def late_record(b):
        b["roster"]["entries"][0]["recorded_at"] = "2026-01-01T12:00:01Z"
    def no_repub(b):
        b["roster"]["entries"][0]["origin"] = "addition"
    def no_push(b):
        del b["push_record"]
    def origin(b):
        for e in b["layout"]["record_sources"]:
            if e["record_kind"] == "roster":
                e["source"] = "self-reported-file"
    def no_step(b):
        link = dict(b["links"][0])
        link["step_id"] = "S9"
        b["links"].append(link)
    def join(b):
        b["links"][1]["inputs"][0]["sha256"] = "b" * 64
    def boundary(b):
        b["claim"]["predecessor_inputs"] = [{"name": "m1", "sha256": "a" * 64}]
    def no_link(b):
        b["links"] = [link for link in b["links"] if link["step_id"] != "S2"]
    def reconstructed(b):
        del b["links"][0]["produced_at"]
    def artifact(b):
        b["links"][0]["subject_artifacts"] = []
    def prop(b):
        b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "contains_line", "line": "nope"}]
    def unsupported(b):
        b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "bogus-kind"}]
    def ledger(b):
        b["claim"]["ledger_claims"] = ["E9"]
    def predicate(b):
        b["links"][0]["predicate_type"] = "other"
    def multi(b):
        b["links"].insert(1, dict(b["links"][0]))
    return {
        "ABSENT-SECTION": absent, "AUTH-NO-SPAWN": no_spawn, "AUTH-NO-ROSTER": no_roster,
        "AUTH-STEP-TIME": step_time, "AUTH-LATE-RECORD": late_record, "AUTH-NO-REPUB": no_repub,
        "AUTH-NO-PUSH": no_push, "AUTH-ORIGIN": origin, "LINK-NO-STEP": no_step,
        "CHAIN-JOIN": join, "CHAIN-BOUNDARY": boundary, "COMP-NO-LINK": no_link,
        "COMP-RECONSTRUCTED": reconstructed, "COMP-ARTIFACT": artifact, "COMP-PROPERTY": prop,
        "COMP-UNSUPPORTED-PROPERTY": unsupported, "COMP-LEDGER": ledger, "LINK-PREDICATE": predicate,
        "ANOM-MULTI-LINK": multi,
    }[code]


class TestT20CureAndConsequence(ThreeChecksCase):
    pass


# Hand stated expected part and subject for the entry each producer above
# makes, derived from the part assignment transcription in
# part_assignment_table.json (plan part 2.6, including its subject column).
# A seat part value names the part of the seat of the step the entry belongs
# to: seat builder and seat reviewer both stand in part1 on the base bundle,
# except where the producer changes the authorising origin to addition,
# which places seat builder in part2.
EXPECTED_PART_SUBJECT = {
    "ABSENT-SECTION": ("stage", "roster"),
    "AUTH-NO-SPAWN": ("part1", "S1"),
    "AUTH-NO-ROSTER": ("part1", "S1"),
    "AUTH-STEP-TIME": ("part1", "S1"),
    "AUTH-LATE-RECORD": ("part1", "S1"),
    "AUTH-NO-REPUB": ("part2", "S1"),
    "AUTH-NO-PUSH": ("stage", "push"),
    "AUTH-ORIGIN": ("stage", "roster"),
    "LINK-NO-STEP": ("stage", "S9"),
    "CHAIN-JOIN": ("part1", "S1 -> S2"),
    "CHAIN-BOUNDARY": ("stage", "boundary"),
    "COMP-NO-LINK": ("part1", "S2"),
    "COMP-RECONSTRUCTED": ("part1", "S1"),
    "COMP-ARTIFACT": ("stage", "A1"),
    "COMP-PROPERTY": ("stage", "A1"),
    "COMP-UNSUPPORTED-PROPERTY": ("stage", "A1"),
    "COMP-LEDGER": ("stage", "E9"),
    "LINK-PREDICATE": ("part1", "S1"),
    "ANOM-MULTI-LINK": ("part1", "S1"),
}


for code in CURES:
    def make(code=code):
        def test(self):
            r = self.run_bundle(self.mutate(producer(code)))
            entries = r.entries(code)
            self.assertTrue(entries, "no entry for " + code)
            self.assertEqual(entries[0]["cure"], CURES[code], code)
            expected_consequence = CONSEQUENCE[code]
            if code in ("AUTH-NO-SPAWN", "AUTH-NO-ROSTER"):
                expected_consequence = "PARTIAL"
            self.assertEqual(entries[0]["consequence"], expected_consequence, code)
            self.assertIn(code, PART_TABLE)
            expected_part, expected_subject = EXPECTED_PART_SUBJECT[code]
            self.assertEqual(entries[0]["part"], expected_part, code)
            self.assertEqual(entries[0]["subject"], expected_subject, code)
        return test
    setattr(TestT20CureAndConsequence, "test_code_" + code.replace("-", "_"), make())


class TestT20EmptyAndOrdering(ThreeChecksCase):
    def test_empty_records_unverifiable_exit3(self):
        def mut(b):
            b["spawn_records"]["records"] = []
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 3)
        for entry in r.entries("AUTH-NO-SPAWN"):
            self.assertEqual(entry["consequence"], "UNVERIFIABLE")

    def test_empty_roster_entries_unverifiable_exit3(self):
        def mut(b):
            b["roster"]["entries"] = []
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 3)
        for entry in r.entries("AUTH-NO-ROSTER"):
            self.assertEqual(entry["consequence"], "UNVERIFIABLE")

    def test_empty_links_partial_exit1(self):
        def mut(b):
            b["links"] = []
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 1)
        self.assertEqual(r.results["checks"]["authenticity"], "pass")
        self.assertEqual(r.results["checks"]["completeness"], "fail")
        self.assertEqual(r.results["consequence"], "PARTIAL")

    def test_partial_only_exit1(self):
        r = self.run_bundle(self.mutate(producer("COMP-LEDGER")))
        self.assertEqual(r.exit_status, 1)
        self.assertEqual(r.results["consequence"], "PARTIAL")

    def test_mixed_consequence_unverifiable_exit3(self):
        def mut(b):
            del b["roster"]
            b["claim"]["ledger_claims"] = ["E9"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 3)
        self.assertEqual(r.results["consequence"], "UNVERIFIABLE")

    def test_anomaly_only_consequence_none_pass(self):
        r = self.run_bundle(self.mutate(producer("ANOM-MULTI-LINK")))
        self.assertEqual(r.exit_status, 0)
        self.assertIsNone(r.results["consequence"])
        self.assertIn("consequence=none", r.report_text)

    def test_all_exit_statuses_reachable_in_suite(self):
        statuses = set()
        statuses.add(self.run_bundle().exit_status)
        statuses.add(self.run_bundle(self.mutate(producer("COMP-LEDGER"))).exit_status)
        statuses.add(self.run_bundle(bundle_bytes=b"not json").exit_status)
        statuses.add(self.run_bundle(self.mutate(lambda b: b["spawn_records"].update({"records": []}))).exit_status)
        statuses.add(self.run_bundle(verifier="agent-1").exit_status)
        self.assertEqual(statuses, {0, 1, 2, 3, 4})

    def test_report_ordering_groups_and_keys(self):
        def mut(b):
            del b["identities"]
            b["claim"]["ledger_claims"] = ["E9"]
            b["links"][1]["inputs"][0]["sha256"] = "b" * 64
        r = self.run_bundle(self.mutate(mut))
        entries = r.results["discrepancies"]
        group_rank = {"stage": 0, "part1": 1, "part2": 2}
        ranks = [group_rank[e["part"]] for e in entries]
        self.assertEqual(ranks, sorted(ranks), repr(entries))

    def test_report_ordering_within_stage_group_full_keys(self):
        # Entries inside one group (stage) that differ by blocking effect, by
        # code, and by subject, asserting the full order: UNVERIFIABLE
        # carrying entries first, then chain, then authenticity, then
        # completeness; inside one blocking effect, code alphabetically, then
        # subject alphabetically.
        def mut(b):
            del b["identities"]
            b["claim"]["predecessor_inputs"] = [{"name": "m1", "sha256": "a" * 64}]
            b["previous_stage"] = {"stage_id": "prev", "outputs": [{"name": "m1", "sha256": "b" * 64}]}
            for entry in b["layout"]["record_sources"]:
                if entry["record_kind"] == "roster":
                    entry["source"] = "self-reported-file"
            b["links"][0]["subject_artifacts"] = []
            b["claim"]["ledger_claims"] = ["E9", "E8"]
        r = self.run_bundle(self.mutate(mut))
        stage_entries = [(e["code"], e["subject"]) for e in r.results["discrepancies"] if e["part"] == "stage"]
        self.assertEqual(stage_entries, [
            ("ABSENT-SECTION", "identities"),
            ("CHAIN-BOUNDARY", "boundary"),
            ("AUTH-ORIGIN", "roster"),
            ("COMP-ARTIFACT", "A1"),
            ("COMP-LEDGER", "E8"),
            ("COMP-LEDGER", "E9"),
        ], repr(r.results["discrepancies"]))

    def test_chain_join_part_is_earlier_step_part(self):
        r = self.run_bundle(self.mutate(producer("CHAIN-JOIN")))
        entry = r.entries("CHAIN-JOIN")[0]
        self.assertEqual(entry["part"], "part1")
        self.assertEqual(entry["subject"], "S1 -> S2")

    def test_chain_boundary_stage_level(self):
        r = self.run_bundle(self.mutate(producer("CHAIN-BOUNDARY")))
        self.assertEqual(r.entries("CHAIN-BOUNDARY")[0]["part"], "stage")

    def test_rejection_scope_sound_evidence_stands(self):
        r = self.run_bundle(self.mutate(producer("COMP-ARTIFACT")))
        self.assertEqual(r.results["checks"]["authenticity"], "pass")
        self.assertIn("step S1", r.report_text)


if __name__ == "__main__":
    unittest.main()
