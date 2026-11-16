import hashlib
import json
import os
import tempfile
import unittest
from helpers import ThreeChecksCase, EXAMPLES_DIR, README_PATH, STRENGTH_LINE, FIXTURES, VERIFIER

CODES = ["ABSENT-SECTION", "AUTH-NO-SPAWN", "AUTH-NO-ROSTER", "AUTH-STEP-TIME", "AUTH-LATE-RECORD", "AUTH-NO-REPUB", "AUTH-NO-PUSH", "AUTH-ORIGIN", "LINK-NO-STEP", "CHAIN-JOIN", "CHAIN-BOUNDARY", "COMP-NO-LINK", "COMP-RECONSTRUCTED", "COMP-ARTIFACT", "COMP-PROPERTY", "COMP-UNSUPPORTED-PROPERTY", "COMP-LEDGER", "LINK-PREDICATE", "ANOM-MULTI-LINK"]


class TestT21ReportForm(ThreeChecksCase):
    def test_header_pass_byte_form(self):
        r = self.run_bundle()
        lines = r.report_text.splitlines()
        self.assertEqual(lines[0], "tool=three-checks version=1.0.0")
        self.assertEqual(lines[1], "stage=stage-1")
        self.assertEqual(lines[2], "outcome=PASS")
        self.assertEqual(lines[3], "consequence=none")
        self.assertEqual(lines[4], "context=none")

    def test_header_failure_byte_form(self):
        def mut(b):
            b["claim"]["ledger_claims"] = ["E9"]
        r = self.run_bundle(self.mutate(mut))
        lines = r.report_text.splitlines()
        self.assertEqual(lines[2], "outcome=FAIL")
        self.assertEqual(lines[3], "consequence=PARTIAL")

    def test_header_barred_byte_form(self):
        r = self.run_bundle(verifier="agent-1")
        lines = r.report_text.splitlines()
        self.assertEqual(lines[0], "tool=three-checks version=1.0.0")
        self.assertEqual(lines[1], "stage=stage-1")
        self.assertEqual(lines[2], "outcome=BARRED")
        self.assertEqual(lines[3], "consequence=none")
        self.assertEqual(lines[4], "context=none")
        self.assertEqual(lines[5], "barred: verifier is performer")

    def test_triage_and_subresult_lines(self):
        r = self.run_bundle()
        lines = r.report_text.splitlines()
        self.assertEqual(lines[5:11], [
            "authenticity: pass",
            "chain: pass",
            "completeness: pass",
            "  links: pass",
            "  artifacts: pass",
            "  ledger: pass",
        ])

    def test_provenance_block_and_section_lists(self):
        r = self.run_bundle()
        with open(os.path.join(r.workdir, "bundle.json"), "rb") as handle:
            bundle_digest = hashlib.sha256(handle.read()).hexdigest()
        lines = r.report_text.splitlines()
        self.assertEqual(lines[11:18], [
            "bundle_sha256=" + bundle_digest,
            "verifier=verifier-1",
            "exporter=runtime exported_at=2026-01-01T00:00:00Z scoping=identity_list",
            "source_database=spawn-db",
            "sections present: layout, roster, links, spawn_records, identities, claim, push_record, ledger_entries",
            "sections absent: previous_stage",
            "push: repo=repo-1 verified_by=verifier-x verified_at=2026-01-01T00:00:00Z origin=api-verification at assembly",
        ])

    def test_sections_absent_none_when_all_sections_present(self):
        def mut(b):
            b["previous_stage"] = {"stage_id": "prev", "outputs": []}
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))
        self.assertIn("sections present: layout, roster, links, spawn_records, identities, claim, push_record, previous_stage, ledger_entries", r.report_text)
        self.assertIn("sections absent: none", r.report_text)
        self.assertEqual(r.results["provenance"]["sections_absent"], [])

    def test_bundle_sha256_equals_digest_of_written_bundle_bytes(self):
        # The expected digest is computed in the test from the exact bundle
        # bytes the test wrote, never read back from the program output.
        r = self.run_bundle()
        with open(os.path.join(r.workdir, "bundle.json"), "rb") as handle:
            expected = hashlib.sha256(handle.read()).hexdigest()
        self.assertEqual(r.results["bundle_sha256"], expected)
        self.assertIn("bundle_sha256=" + expected, r.report_text)
        self.assertIn("bundle_sha256=" + expected, r.closure_text)

    def test_cross_form_shared_blocks_on_absent_sections_bundle(self):
        # One bundle with an absent section (identities), read in three forms:
        # the ordinary report, the barred report for the same bundle, and the
        # closure form. Appendix A requires the header block, the provenance
        # block, and the strength line to come from one shared block renderer,
        # so the shared parts must be identical across forms wherever the form
        # carries them, apart from the lines each form defines differently
        # (the outcome line, and the verifier line where the verifier differs).
        def mut(b):
            del b["identities"]
        bundle = self.mutate(mut)
        ordinary = self.run_bundle(bundle)
        barred = self.run_bundle(bundle, verifier="agent-1")
        self.assertEqual(barred.exit_status, 4)
        ordinary_lines = ordinary.report_text.splitlines()
        barred_lines = barred.report_text.splitlines()
        self.assertEqual(len(ordinary_lines[:5]), 5)
        self.assertEqual(len(barred_lines[:5]), 5)
        for index in (0, 1, 4):
            self.assertEqual(ordinary_lines[index], barred_lines[index])
        self.assertEqual(ordinary_lines[2], "outcome=FAIL")
        self.assertEqual(barred_lines[2], "outcome=BARRED")
        def provenance(lines):
            start = [i for i, line in enumerate(lines) if line.startswith("bundle_sha256=")][0]
            end = [i for i, line in enumerate(lines) if line.startswith("sections absent:")][0]
            return lines[start:end + 2]
        ordinary_prov = provenance(ordinary_lines)
        barred_prov = provenance(barred_lines)
        self.assertEqual(len(ordinary_prov), len(barred_prov))
        for ordinary_line, barred_line in zip(ordinary_prov, barred_prov):
            if ordinary_line.startswith("verifier="):
                self.assertEqual(ordinary_line, "verifier=verifier-1")
                self.assertEqual(barred_line, "verifier=agent-1")
            else:
                self.assertEqual(ordinary_line, barred_line)
        self.assertIn(STRENGTH_LINE, ordinary.report_text)
        self.assertIn(STRENGTH_LINE, barred.report_text)
        # The closure form applies only on a full pass. This bundle fails, so
        # no closure file is created in either form, and the strength line the
        # closure would carry is the same line asserted in both reports above.
        self.assert_no_file(ordinary.closure_path)
        self.assert_no_file(barred.closure_path)

    def test_push_provenance_line_absent_without_push_record(self):
        def mut(b):
            del b["push_record"]
            b["layout"]["record_sources"] = [e for e in b["layout"]["record_sources"] if e["record_kind"] != "push"]
        r = self.run_bundle(self.mutate(mut))
        self.assertNotIn("push: repo=", r.report_text)
        self.assertIsNone(r.results["provenance"]["push"])

    def test_strength_line_head_footer_closure(self):
        def mut(b):
            b["claim"]["ledger_claims"] = ["E9"]
        r = self.run_bundle(self.mutate(mut))
        self.assertGreaterEqual(r.report_text.count(STRENGTH_LINE), 2)
        r2 = self.run_bundle()
        self.assertIn(STRENGTH_LINE, r2.closure_text)

    def test_boundary_line_values(self):
        r = self.run_bundle()
        self.assertIn("boundary: not applicable", r.report_text)
        def mut(b):
            b["claim"]["predecessor_inputs"] = [{"name": "m1", "sha256": "a" * 64}]
            b["previous_stage"] = {"stage_id": "prev", "outputs": [{"name": "m1", "sha256": "a" * 64}]}
        r2 = self.run_bundle(self.mutate(mut))
        self.assertIn("boundary: matched", r2.report_text)

    def test_part_headings_and_worked_listing(self):
        r = self.run_bundle()
        self.assertIn("part 1: advance layout seats", r.report_text)
        self.assertIn("part 2: seats added under R-50", r.report_text)
        self.assertIn("step S1 seat=builder recorded=2026-01-01T00:00:00Z authenticity=pass matching=pass", r.report_text)
        self.assertIn("join S1 -> S2: pass", r.report_text)

    def test_worked_discrepancy_entry_block(self):
        def mut(b):
            b["layout"]["steps"].append({"step_id": "S3", "seat": "extra", "predicate_type": "extra"})
            b["claim"]["steps_claimed"].append("S3")
            b["claim"]["step_completions"].append({"step_id": "S3", "completed_at": "2026-01-03T00:00:00Z"})
        r = self.run_bundle(self.mutate(mut))
        block = "\n".join([
            "  - code=COMP-NO-LINK subject=S3",
            "    check=completeness",
            "    expected=at least one matching link",
            "    found=no matching link",
            "    consequence=PARTIAL",
            "    cure=supply a genuine link for the step, or withdraw the step from the layout",
        ])
        self.assertIn(block, r.report_text)

    def test_results_translation_table(self):
        def mut(b):
            del b["layout"]
        r = self.run_bundle(self.mutate(mut))
        self.assertIsNone(r.results["stage_id"])
        self.assertIn("stage=absent", r.report_text)
        self.assertEqual(r.results["checks"]["authenticity"], "cannot_run")
        self.assertIn("authenticity: cannot run", r.report_text)
        self.assertIsNone(r.results["gate_context"] if "gate_context" in r.results else None) if False else self.assertIsNone(r.results["gate_context"])
        self.assertIn("context=none", r.report_text)

    def test_anomaly_consequence_none_in_both_outputs(self):
        def mut(b):
            b["links"].insert(1, dict(b["links"][0]))
        r = self.run_bundle(self.mutate(mut))
        entry = r.entries("ANOM-MULTI-LINK")[0]
        self.assertEqual(entry["consequence"], "none")
        self.assertIn("consequence=none", r.report_text)

    def test_results_keys_and_no_barred_field(self):
        r = self.run_bundle()
        self.assertEqual(list(r.results.keys()), ["tool", "version", "stage_id", "bundle_sha256", "outcome", "consequence", "gate_context", "checks", "subresults", "provenance", "discrepancies"])
        self.assertNotIn("barred", json.dumps(r.results))
        self.assertEqual(set(r.results["subresults"].keys()), {"links", "artifacts", "ledger"})
        for entry in r.results["discrepancies"]:
            self.assertIn(entry["part"], ("stage", "part1", "part2"))
            self.assertIn(entry["check"], ("authenticity", "chain", "completeness", "stage"))

    def test_final_newline_exactly_one(self):
        expected = os.path.join(FIXTURES, "expected_final_newline.txt")
        if not os.path.isfile(expected):
            self.fail("missing shipped companion in tests: hand written final newline expected file")
        r = self.run_bundle()
        for text in (r.report_text, open(r.results_path).read(), r.closure_text):
            self.assertTrue(text.endswith("\n"))
            self.assertFalse(text.endswith("\n\n"))

    def test_version_literal_not_imported(self):
        r = self.run_bundle()
        self.assertIn("version=1.0.0", r.report_text)
        self.assertEqual(r.results["version"], "1.0.0")


class TestT21ExamplesAndReadme(ThreeChecksCase):
    def test_examples_pair_regeneration(self):
        bundle = os.path.join(EXAMPLES_DIR, "example_bundle.json")
        expected_report = os.path.join(EXAMPLES_DIR, "expected_report.txt")
        expected_results = os.path.join(EXAMPLES_DIR, "expected_results.json")
        for path in (bundle, expected_report, expected_results):
            if not os.path.isfile(path):
                self.fail("missing shipped companion: examples pair file " + path + " (lands at build step 10)")
        self.require_program()
        # Run the tool on the example bundle, with the example artifact files
        # in place beside the bundle in the examples folder, writing the
        # produced report and results to a separate temporary folder. The
        # produced pair is then compared with the hand authored shipped pair:
        # the report byte for byte, and the results field for field.
        with tempfile.TemporaryDirectory() as outdir:
            report_path = os.path.join(outdir, "report.txt")
            results_path = os.path.join(outdir, "results.json")
            closure_path = os.path.join(outdir, "closure.txt")
            proc = self.run_argv([bundle, report_path, results_path, closure_path, "--verifier", VERIFIER])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(expected_report, "rb") as handle:
                expected_report_bytes = handle.read()
            with open(report_path, "rb") as handle:
                produced_report_bytes = handle.read()
            self.assertEqual(produced_report_bytes, expected_report_bytes)
            with open(expected_results, encoding="utf-8") as handle:
                expected_results_obj = json.load(handle)
            with open(results_path, encoding="utf-8") as handle:
                produced_results_obj = json.load(handle)
            self.assertEqual(produced_results_obj, expected_results_obj)

    def test_readme_content(self):
        if not os.path.isfile(README_PATH):
            self.fail("missing shipped companion: README at " + README_PATH + " (lands at build step 10)")
        with open(README_PATH, encoding="utf-8") as handle:
            text = handle.read()
        for code in CODES:
            self.assertIn(code, text)
        for phrase in ("assembly", "spawn", "push", "strength", "OP-3"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
