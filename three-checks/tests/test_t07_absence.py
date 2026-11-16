import json
import os
import unittest
from helpers import ThreeChecksCase, TRANSCRIPTIONS

ABSENCE = json.load(open(os.path.join(TRANSCRIPTIONS, "absence_table.json")))
SECTIONS = ["layout", "roster", "links", "spawn_records", "identities", "claim"]


class TestT07Absence(ThreeChecksCase):
    def without(self, *sections):
        def mut(b):
            for section in sections:
                b.pop(section, None)
        return self.mutate(mut)


def expected_subresults(row, section):
    # Maps a transcription subresult effect to the value the base bundle run
    # produces: "computed normally" reads as the base bundle values, which are
    # pass for all three subresults. The links absent row is special: its
    # artifacts effect is computed normally with one COMP-ARTIFACT coverage
    # entry per required artifact, and that coverage failure fails the
    # artifacts subresult, while the ledger subresult is computed normally.
    expected = {}
    for name, effect in row["subresults"].items():
        if effect == "fail":
            expected[name] = "fail"
        elif effect == "computed normally":
            expected[name] = "pass"
        elif section == "links" and name == "artifacts":
            expected[name] = "fail"
        else:
            raise AssertionError("unmapped subresult effect: " + repr(effect))
    return expected


for section in SECTIONS:
    def make(section=section):
        def test(self):
            row = ABSENCE[section]
            r = self.run_bundle(self.without(section))
            self.assert_entry(r, "ABSENT-SECTION", subject=section, part="stage", check="stage", consequence="UNVERIFIABLE")
            self.assertEqual(r.exit_status, row["exit_status_on_otherwise_pass"], section)
            checks = r.results["checks"]
            for name, effect in row["triage"].items():
                if effect == "cannot run":
                    self.assertEqual(checks[name], "cannot_run", name)
                elif effect == "fail":
                    self.assertEqual(checks[name], "fail", name)
                elif effect == "run":
                    self.assertIn(checks[name], ("pass", "fail"), name)
                else:
                    raise AssertionError("unmapped triage effect: " + repr(effect))
            self.assertEqual(r.results["subresults"], expected_subresults(row, section), section)
            if section == "links":
                self.assert_entry(r, "COMP-ARTIFACT", subject="A1", part="stage", count=1)
            if row["header_stage"] is not None:
                self.assertIsNone(r.results["stage_id"])
                self.assertIn("stage=" + row["header_stage"], r.report_text)
            else:
                self.assertEqual(r.results["stage_id"], "stage-1")
            fallback = row["provenance_fallback"]
            if section == "spawn_records":
                self.assertIsNotNone(fallback)
                prov = r.results["provenance"]
                self.assertIsNone(prov["exporter"])
                self.assertIsNone(prov["exported_at"])
                self.assertIsNone(prov["scoping_method"])
                self.assertIsNone(prov["source_database"])
                for field in ("exporter", "exported_at", "scoping", "source_database"):
                    self.assertIn(field + "=" + fallback[field if field != "scoping" else "scoping"], r.report_text)
            elif section == "claim":
                self.assertIsNotNone(fallback)
                self.assertIn("boundary: " + fallback["boundary"], r.report_text)
                self.assertIn("context=" + fallback["context"], r.report_text)
                self.assertEqual(r.results["gate_context"], None)
            else:
                prov = r.results["provenance"]
                self.assertEqual(prov["exporter"], "runtime")
                self.assertIn("exporter=runtime", r.report_text)
            if row["outcome_cap"]:
                self.assertEqual(r.results["outcome"], "FAIL")
                self.assertEqual(r.results["consequence"], "UNVERIFIABLE")
            if section == "identities":
                self.assertEqual(checks, {"authenticity": "pass", "chain": "pass", "completeness": "pass"})
        return test
    setattr(TestT07Absence, "test_absent_" + section, make())


class TestT07Combinations(ThreeChecksCase):
    def without(self, *sections):
        def mut(b):
            for section in sections:
                b.pop(section, None)
        return self.mutate(mut)

    def combo(self, sections, count):
        r = self.run_bundle(self.without(*sections))
        self.assertEqual(len(r.entries("ABSENT-SECTION")), count)
        return r

    def test_layout_and_claim(self):
        self.combo(["layout", "claim"], 2)

    def test_roster_and_spawn_records(self):
        self.combo(["roster", "spawn_records"], 2)

    def test_links_and_identities(self):
        r = self.combo(["links", "identities"], 2)
        self.assertEqual(r.exit_status, 3)

    def test_identities_and_layout(self):
        r = self.combo(["identities", "layout"], 2)
        self.assertEqual(r.exit_status, 3)

    def test_identities_and_claim(self):
        self.combo(["identities", "claim"], 2)

    def test_spawn_records_and_claim(self):
        self.combo(["spawn_records", "claim"], 2)

    def test_three_absent_strongest_effect_no_per_object_entries(self):
        r = self.combo(["roster", "links", "spawn_records"], 3)
        self.assertEqual(r.results["checks"]["authenticity"], "cannot_run")
        codes = [e["code"] for e in r.results["discrepancies"]]
        self.assertNotIn("AUTH-NO-SPAWN", codes)
        self.assertNotIn("COMP-NO-LINK", codes)

    def test_completeness_cannot_run_subresults_fail(self):
        r = self.run_bundle(self.without("claim"))
        self.assertEqual(r.results["subresults"], {"links": "fail", "artifacts": "fail", "ledger": "fail"})
        self.assertIn("  links: fail", r.report_text)
        self.assertIn("  artifacts: fail", r.report_text)
        self.assertIn("  ledger: fail", r.report_text)

    def test_roster_absent_subresults_computed_normally(self):
        r = self.run_bundle(self.without("roster"))
        self.assertEqual(r.results["subresults"]["links"], "fail")
        self.assertEqual(r.results["subresults"]["artifacts"], "pass")
        self.assertEqual(r.results["subresults"]["ledger"], "pass")

    def test_spawn_absent_subresults_computed_normally(self):
        r = self.run_bundle(self.without("spawn_records"))
        self.assertEqual(r.results["subresults"]["links"], "fail")
        self.assertEqual(r.results["subresults"]["artifacts"], "pass")
        self.assertEqual(r.results["subresults"]["ledger"], "pass")

    def test_links_absent_coverage_per_artifact(self):
        r = self.run_bundle(self.without("links"))
        self.assertEqual(r.results["subresults"]["links"], "fail")
        self.assert_entry(r, "COMP-ARTIFACT", subject="A1", part="stage", count=1)
        self.assertEqual(r.results["subresults"]["ledger"], "pass")

    def test_boundary_runs_under_roster_absent(self):
        def mut(b):
            del b["roster"]
            b["claim"]["predecessor_inputs"] = [{"name": "m1", "sha256": "a" * 64}]
            b["previous_stage"] = {"stage_id": "prev", "outputs": [{"name": "m1", "sha256": "b" * 64}]}
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary", part="stage")
        self.assertIn("boundary: failed", r.report_text)

    def test_boundary_not_run_under_layout_absent(self):
        def mut(b):
            del b["layout"]
            b["claim"]["predecessor_inputs"] = [{"name": "m1", "sha256": "a" * 64}]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.entries("CHAIN-BOUNDARY"), [])
        self.assertIn("boundary: not applicable", r.report_text)


if __name__ == "__main__":
    unittest.main()
