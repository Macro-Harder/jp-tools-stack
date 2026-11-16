import hashlib
import json
import os
import unittest

from helpers import (
    README_PATH,
    ThreeChecksCase,
    USAGE_LINE,
    base_bundle,
)

PREFIX = "three-checks: input error: "
SURROGATE_ESCAPE = chr(92) + "ud800"


class TestStage19U1Rendering(ThreeChecksCase):
    def test_stage_id_escaped_in_closure_record(self):
        def mut(b):
            b["layout"]["stage_id"] = "stage-1\noutcome=PASS"
            b["claim"]["stage_id"] = "stage-1\noutcome=PASS"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        closure_lines = r.closure_text.splitlines()
        self.assertIn('stage="stage-1\\noutcome=PASS"', closure_lines)
        self.assertNotIn("outcome=PASS", closure_lines)

    def test_provenance_exporter_and_source_database_escaped(self):
        def mut(b):
            b["spawn_records"]["exporter"] = "runtime\noutcome=PASS"
            b["spawn_records"]["source_database"] = "spawn-db\noutcome=PASS"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        lines = r.report_text.splitlines()
        self.assertTrue(
            any(line.startswith('exporter="runtime\\noutcome=PASS" exported_at=') for line in lines),
            r.report_text,
        )
        self.assertIn('source_database="spawn-db\\noutcome=PASS"', lines)
        self.assertEqual(lines.count("outcome=PASS"), 1)
        self.assertEqual(r.results["provenance"]["exporter"], "runtime\noutcome=PASS")
        self.assertEqual(r.results["provenance"]["source_database"], "spawn-db\noutcome=PASS")

    def test_per_step_line_step_id_escaped(self):
        def mut(b):
            b["layout"]["steps"][0]["step_id"] = "S1\noutcome=PASS"
            b["links"][0]["step_id"] = "S1\noutcome=PASS"
            b["claim"]["steps_claimed"][0] = "S1\noutcome=PASS"
            b["claim"]["step_completions"][0]["step_id"] = "S1\noutcome=PASS"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        lines = r.report_text.splitlines()
        self.assertTrue(
            any(line.startswith('step "S1\\noutcome=PASS" seat=builder recorded=') for line in lines),
            r.report_text,
        )
        self.assertEqual(lines.count("outcome=PASS"), 1)

    def test_join_line_step_id_escaped(self):
        def mut(b):
            b["layout"]["steps"][1]["step_id"] = "S2\noutcome=PASS"
            b["links"][1]["step_id"] = "S2\noutcome=PASS"
            b["claim"]["steps_claimed"][1] = "S2\noutcome=PASS"
            b["claim"]["step_completions"][1]["step_id"] = "S2\noutcome=PASS"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        lines = r.report_text.splitlines()
        self.assertIn('join S1 -> "S2\\noutcome=PASS": pass', lines)
        self.assertEqual(lines.count("outcome=PASS"), 1)

    def test_discrepancy_subject_escaped(self):
        def mut(b):
            b["claim"]["ledger_claims"] = ["E9\noutcome=PASS"]

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 1, r.stderr)
        lines = r.report_text.splitlines()
        self.assertIn('  - code=COMP-LEDGER subject="E9\\noutcome=PASS"', lines)
        self.assertNotIn("outcome=PASS", lines)
        entry = r.entries("COMP-LEDGER")[0]
        self.assertEqual(entry["subject"], "E9\noutcome=PASS")

    def test_barred_report_provenance_value_escaped(self):
        def mut(b):
            b["spawn_records"]["exporter"] = "runtime\noutcome=PASS"

        r = self.run_bundle(self.mutate(mut), verifier="agent-1")
        self.assertEqual(r.exit_status, 4, r.stderr)
        lines = r.report_text.splitlines()
        self.assertIn("outcome=BARRED", lines)
        self.assertTrue(
            any(line.startswith('exporter="runtime\\noutcome=PASS" exported_at=') for line in lines),
            r.report_text,
        )
        self.assertNotIn("outcome=PASS", lines)

    def test_usage_error_argument_value_escaped(self):
        proc = self.run_argv([
            "bundle.json", "report.txt", "results.json", "closure.txt",
            "--verifier", "verifier-1", "extra\noutcome=PASS",
        ])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        lines = proc.stderr.splitlines()
        self.assertEqual(
            lines[0],
            'three-checks: usage error: unexpected argument "extra\\noutcome=PASS"',
        )
        self.assertEqual(lines[1], USAGE_LINE)
        self.assertNotIn("outcome=PASS", lines)

    def test_u007f_character_triggers_escaped_form(self):
        def mut(b):
            b["layout"]["stage_id"] = "stage-1\u007f"
            b["claim"]["stage_id"] = "stage-1\u007f"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        lines = r.report_text.splitlines()
        self.assertEqual(lines[1], 'stage="stage-1\\u007f"')
        self.assertIn('stage="stage-1\\u007f"', r.closure_text.splitlines())
        self.assertNotIn("\u007f", r.report_text)
        self.assertEqual(lines.count("outcome=PASS"), 1)

    def test_tab_character_triggers_escaped_form(self):
        def mut(b):
            b["spawn_records"]["source_database"] = "spawn-db\toutcome=PASS"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        lines = r.report_text.splitlines()
        self.assertIn('source_database="spawn-db\\toutcome=PASS"', lines)
        self.assertNotIn("\t", r.report_text)
        self.assertEqual(lines.count("outcome=PASS"), 1)

    def test_carriage_return_character_triggers_escaped_form(self):
        def mut(b):
            b["spawn_records"]["exporter"] = "runtime\routcome=PASS"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        lines = r.report_text.splitlines()
        self.assertTrue(
            any(line.startswith('exporter="runtime\\routcome=PASS" exported_at=') for line in lines),
            r.report_text,
        )
        self.assertNotIn("\r", r.report_text)
        self.assertEqual(lines.count("outcome=PASS"), 1)


class TestStage19U2GateContext(ThreeChecksCase):
    def test_gate_context_value_propagates_to_report_and_results(self):
        def mut(b):
            b["claim"]["gate_context"] = "auditor-gate"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        self.assertIn("context=auditor-gate", r.report_text.splitlines())
        self.assertEqual(r.results["gate_context"], "auditor-gate")

    def test_gate_context_key_deleted_is_treated_as_null(self):
        def mut(b):
            del b["claim"]["gate_context"]

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        self.assertIn("context=none", r.report_text.splitlines())
        self.assertIsNone(r.results["gate_context"])


class TestStage19U3NonStringTimes(ThreeChecksCase):
    def test_produced_at_as_number_is_type_error(self):
        def mut(b):
            b["links"][0]["produced_at"] = 12345

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2, r.stderr)
        self.assertIn(PREFIX + "links.0.produced_at must be string", r.stderr)
        self.assert_no_file(r.report_path)
        self.assert_no_file(r.results_path)

    def test_roster_recorded_at_as_number_is_type_error(self):
        def mut(b):
            b["roster"]["entries"][0]["recorded_at"] = 999

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2, r.stderr)
        self.assertIn(PREFIX + "roster.entries.0.recorded_at must be string", r.stderr)
        self.assert_no_file(r.report_path)
        self.assert_no_file(r.results_path)


class TestStage19U4DualStandingEntries(ThreeChecksCase):
    def test_over_limit_and_digest_mismatch_both_entries_stand(self):
        content = b"x" * 2000001
        file_digest = hashlib.sha256(content).hexdigest()

        def mut(b):
            b["layout"]["required_artifacts"][0]["sha256"] = "c" * 64
            b["links"][0]["subject_artifacts"] = [{"artifact_id": "A1", "sha256": "c" * 64}]

        r = self.run_bundle(self.mutate(mut), artifacts={"artifact1.txt": content})
        self.assertEqual(r.exit_status, 1, r.stderr)
        entries = [e for e in r.entries("COMP-ARTIFACT") if e["subject"] == "A1"]
        founds = [e["found"] for e in entries]
        size_founds = [f for f in founds if "2000001 bytes, over the limit of 2000000 bytes" in f]
        digest_founds = [f for f in founds if "differs from the stated digest" in f]
        self.assertTrue(size_founds, repr(entries))
        self.assertTrue(digest_founds, repr(entries))
        self.assertIn(file_digest, digest_founds[0])
        self.assertIn("c" * 64, digest_founds[0])
        self.assertGreaterEqual(len(entries), 2, repr(entries))


class TestStage19U5ResultsRawBytes(ThreeChecksCase):
    def test_results_raw_bytes_indentation_non_ascii_and_no_carriage_return(self):
        def mut(b):
            b["layout"]["stage_id"] = "stage-é"
            b["claim"]["stage_id"] = "stage-é"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr)
        with open(r.results_path, "rb") as handle:
            raw = handle.read()
        self.assertIn(b'\n  "tool": "three-checks",', raw)
        self.assertIn("stage-é".encode("utf-8"), raw)
        self.assertNotIn(chr(92).encode("ascii") + b"u00e9", raw)
        self.assertNotIn(b"\r", raw)
        self.assertEqual(r.results["stage_id"], "stage-é")


def u6_producer(code):
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
        "CHAIN-JOIN": join, "CHAIN-BOUNDARY": boundary, "COMP-RECONSTRUCTED": reconstructed,
        "COMP-ARTIFACT": artifact, "COMP-PROPERTY": prop,
        "COMP-UNSUPPORTED-PROPERTY": unsupported, "COMP-LEDGER": ledger,
        "LINK-PREDICATE": predicate, "ANOM-MULTI-LINK": multi,
    }[code]


# Hand written from the brief Appendix A entry form and the OP-4 template
# list in plan part 7: one expected text per code, with the subject value
# the producer above supplies filled in where the template names it.
# COMP-NO-LINK is not in this table because its expected text is already
# asserted in full by the worked entry block test in T21.
U6_EXPECTED = {
    "ABSENT-SECTION": "the required section roster is present",
    "AUTH-NO-SPAWN": "exactly one spawn record for the performer identity",
    "AUTH-NO-ROSTER": "a roster entry authorising the seat for the performer at or before the step run time",
    "AUTH-STEP-TIME": "the spawn record creation time is at or before the step run time and both times parse",
    "AUTH-LATE-RECORD": "a roster entry recorded at or before the step run time",
    "AUTH-NO-REPUB": "a republication for the seat at or before the step run time",
    "AUTH-NO-PUSH": "a push record where a push link is in play",
    "AUTH-ORIGIN": "the record kind passes its origin test",
    "LINK-NO-STEP": "the link step_id names a layout step",
    "CHAIN-JOIN": "the outputs of the earlier step match the inputs of the later step on every name",
    "CHAIN-BOUNDARY": "the claim predecessor inputs match the previous stage outputs on every name",
    "COMP-RECONSTRUCTED": "a link produced at or before the recorded completion time and at or after its run time, with a production time present",
    "COMP-ARTIFACT": "the artifact file stands at its path, within the size limit, with the stated digest, and named by a presented link with the stated digest",
    "COMP-PROPERTY": "the stated property holds for the artifact file",
    "COMP-UNSUPPORTED-PROPERTY": "the stated property kind is one of the seven evaluated kinds",
    "COMP-LEDGER": "a path ledger entry for the claimed element",
    "LINK-PREDICATE": "the link predicate_type equals the layout step predicate_type",
    "ANOM-MULTI-LINK": "one matching link for the step",
}


class TestStage19U6ExpectedTexts(ThreeChecksCase):
    pass


for _code in U6_EXPECTED:
    def _make(code=_code):
        def test(self):
            r = self.run_bundle(self.mutate(u6_producer(code)))
            entries = r.entries(code)
            self.assertTrue(entries, "no entry for " + code)
            for entry in entries:
                self.assertEqual(entry["expected"], U6_EXPECTED[code], code)
        return test
    setattr(TestStage19U6ExpectedTexts, "test_expected_" + _code.replace("-", "_"), _make())


class TestStage19U7DiscardedDuplicateSurrogate(ThreeChecksCase):
    def check_gate(self, raw_text):
        r = self.run_bundle(bundle_bytes=raw_text.encode("utf-8"))
        self.assertEqual(r.exit_status, 2, r.stderr)
        lines = [line for line in r.stderr.strip().splitlines() if line]
        self.assertEqual(lines, [PREFIX + "the bundle file is not valid JSON"])
        self.assert_no_file(r.report_path)
        self.assert_no_file(r.results_path)

    def test_surrogate_in_discarded_duplicate_value_at_claim(self):
        raw = json.dumps(base_bundle())
        raw = raw.replace(
            '"gate_context": null',
            '"gate_context": null, "gate_context": "' + SURROGATE_ESCAPE + 'x"',
            1,
        )
        self.assertIn(SURROGATE_ESCAPE, raw)
        self.check_gate(raw)

    def test_surrogate_in_discarded_duplicate_value_inside_list_entry(self):
        raw = json.dumps(base_bundle())
        raw = raw.replace(
            '"produced_at": "2026-01-02T00:00:00Z"',
            '"produced_at": "2026-01-02T00:00:00Z", "produced_at": "' + SURROGATE_ESCAPE + 'x"',
            1,
        )
        self.assertIn(SURROGATE_ESCAPE, raw)
        self.check_gate(raw)


class TestStage19U8ReadmeContent(ThreeChecksCase):
    def readme_text(self):
        if not os.path.isfile(README_PATH):
            self.fail("missing shipped companion: README at " + README_PATH)
        with open(README_PATH, encoding="utf-8") as handle:
            return handle.read()

    def assert_all_present(self, text, literals):
        for literal in literals:
            self.assertIn(literal, text)

    def test_readme_invocation_and_exit_statuses(self):
        text = self.readme_text()
        self.assert_all_present(text, [
            "three-checks BUNDLE REPORT RESULTS CLOSURE --verifier IDENTITY",
            "python3 three_checks.py BUNDLE REPORT RESULTS CLOSURE --verifier IDENTITY",
            "0: full pass.",
            "1: checks failed, consequence PARTIAL.",
            "2: input error, delivery failure, or usage error, each named distinctly on standard error.",
            "3: checks failed, consequence UNVERIFIABLE.",
            "4: barred run. The verifier is the performer, the coordinator, or a commissioner, so the run is barred and issues no check results.",
        ])

    def test_readme_assembly_checklist_heading_and_key_steps(self):
        text = self.readme_text()
        self.assert_all_present(text, [
            "### Assembly checklist",
            "Always include layout, roster, links, spawn_records, identities, and claim.",
            "Include push_record when the claim names a push link (claim push_link is not null), and when layout record_sources names the push kind.",
            "Include previous_stage when the claim names predecessor inputs (claim predecessor_inputs is not null).",
            "Include ledger_entries when the claim ledger_claims list is not empty.",
            "Record a completion time in claim step_completions for every claimed step",
            "Keep the bundle at or under 2000000 bytes, as UTF-8 text without a byte order mark.",
        ])

    def test_readme_spawn_export_summary_items(self):
        text = self.readme_text()
        self.assert_all_present(text, [
            "## Spawn export specification in summary",
            "a link performer_spawn_id must equal the agent_id of exactly one record in the export",
            "created_at is read as an ISO 8601 UTC instant and must stand at or before the ran_at of every link that binds the record",
            "The scoping record states how the export was scoped: the scoping method, one of identity_list, parent_subtree, or time_window, with its detail",
            "The seat mapping bound: the export carries no seat.",
            "The association of a performer identity with a seat rests on the roster record, and no report text describes that association as runtime captured.",
        ])

    def test_readme_push_verification_summary_items(self):
        text = self.readme_text()
        self.assert_all_present(text, [
            "## Push assembly verification in summary",
            "through two API reads: one read of the repository head, giving the head commit, and one read of the tree it points to",
            "The attestation fields recorded in push_record are repo, branch, head_sha, tree_sha, verified_by, and verified_at.",
            "Branch is assembly provenance and is never a check input.",
            "The report provenance line states the push origin as api-verification at assembly.",
        ])

    def test_readme_strength_bound_sentences(self):
        text = self.readme_text()
        self.assert_all_present(text, [
            "## Strength bound",
            "The checks count at the closure record L2 grade and no higher, and only where the origin tests passed.",
            "The seat association rests on the roster record.",
            "The spawn export is assembled under the verifier's direction, and the tool cannot prove an export genuine",
            "No strength above grade L2 is claimed, and the tool never issues per link grade labels.",
        ])


if __name__ == "__main__":
    unittest.main()
