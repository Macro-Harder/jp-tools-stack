"""Stage 15 fix regressions. Audit findings F1 to F7 of audit-stage15-code.md.

Each test stages one audited defect against the plan behaviour that governs
it. The F1 and F3 tests drive the program parts directly through a module
import, in the manner of tests/selftest_driver.py, because neither defect
can be staged reliably through the command line: the selection probe result
is observable only as a pass or fail line while the inline copy agrees with
the real part, and a file that appears between path validation and writing
cannot be timed from outside the process.
"""

import importlib.util
import unittest

from rcg_common import (
    RcgTestCase, assert_ie, assert_no_files, IE_WORDINGS, pass_specs,
    declaration_text, default_spec, sha256_hex, run_program,
    row, CLAUSE_A, CLAUSE_B, CLAUSE_C,
    JUDGE, PANEL, SECOND, PROGRAM,
)


def load_program_module(tag):
    spec = importlib.util.spec_from_file_location("rcg_stage15_%s" % tag, PROGRAM)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestF1SelectionProbe(RcgTestCase):
    def test_probes_pass_on_the_program_as_built(self):
        module = load_program_module("f1_clean")
        probes = module.run_self_test(None)
        results = {p["name"]: p["result"] for p in probes}
        self.assertEqual(results["selection_probe"], "pass")
        self.assertEqual(results["pass_probe"], "pass")
        self.assertEqual(results["blocking_probe"], "pass")
        self.assertEqual(results["excused_fail_probe"], "pass")
        self.assertEqual(results["binding_probe"], "pass")

    def test_selection_probe_fails_when_the_real_selection_part_is_broken(self):
        module = load_program_module("f1_broken")
        original = module.compute_selection

        def broken(corpus, items, declaration, attestations):
            result = original(corpus, items, declaration, attestations)
            for info in result["per_item"].values():
                info["checked_ids"] = []
            return result

        module.compute_selection = broken
        try:
            probes = module.run_self_test(None)
        finally:
            module.compute_selection = original
        results = {p["name"]: p["result"] for p in probes}
        self.assertEqual(results["selection_probe"], "fail")
        self.assertEqual(results["pass_probe"], "pass")
        self.assertEqual(results["blocking_probe"], "pass")


class TestF2RosterBindingPosition(RcgTestCase):
    def test_panel_judge_verdict_with_differing_run_roster_is_binding_ie38_finalise(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = PANEL
        w.write_verdicts(specs, panel=[PANEL])
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="judge roster"))
        assert_no_files(self, w.out1, w.out2)

    def test_panel_judge_verdict_with_differing_run_roster_is_binding_ie38_remaining(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = PANEL
        w.write_verdicts(specs, panel=[PANEL])
        p = w.run("remaining", context="stated")
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="judge roster"))
        assert_no_files(self, w.out1)

    def test_judge_on_no_roster_is_ie37_even_where_rosters_differ(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = "Stranger Seat"
        w.write_verdicts(specs, panel=[PANEL])
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-37", IE_WORDINGS["IE-37"].format(
            label="A1", id="C-001", judge="Stranger Seat"))
        assert_no_files(self, w.out1, w.out2)


class TestF3WritingPartRecheck(RcgTestCase):
    def test_write_output_refuses_a_path_that_already_stands(self):
        module = load_program_module("f3_existing")
        w = self.world()
        target = w.dir / "standing.txt"
        target.write_text("standing content\n")
        with self.assertRaises(module.DeliveryFailure):
            module.write_output(str(target), "replacement content\n")
        self.assertEqual(target.read_text(), "standing content\n")

    def test_write_output_writes_a_fresh_path(self):
        module = load_program_module("f3_fresh")
        w = self.world()
        target = w.dir / "fresh.txt"
        module.write_output(str(target), "fresh content\n")
        self.assertEqual(target.read_text(), "fresh content\n")


class TestF4CrossReferenceFallback(RcgTestCase):
    def test_row_section_related_line_for_an_unpadded_id(self):
        w = self.world()
        rows = [
            row("C-1", "Alpha incident happened", "Gap 1", CLAUSE_A,
                extra_incident=" Cross-ref: C-2 (same event, other lens)."),
            row("C-2", "Beta incident happened", "Gap 2", CLAUSE_B),
            row("C-3", "Gamma incident happened", "Gap 3", CLAUSE_C),
        ]
        w.set_corpus(rows)
        spec = [("A1", ["Gap 1"], {"Gap 1": "Basis prose for Gap 1 on A1."}),
                ("A2", ["Gap 3"], {"Gap 3": "Basis prose for Gap 3 on A2."})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("related but not selected: C-2", text)
        self.assertIn("related: C-2 is related and is not checked by this item", text)


class TestF5FingerprintOmission(RcgTestCase):
    def test_declaration_without_a_fingerprint_line_is_ie18(self):
        w = self.world()
        text = declaration_text(w.amendment_bytes, default_spec())
        kept = [l for l in text.splitlines() if not l.startswith("amendment-fingerprint:")]
        w.declaration.write_text("\n".join(kept) + "\n")
        p = w.run("worksheet", context="stated")
        assert_ie(self, p, "IE-18", IE_WORDINGS["IE-18"].format(
            a="absent", b=sha256_hex(w.amendment_bytes)))
        assert_no_files(self, w.out1, w.out2)


class TestF6DuplicatedDeclarationBlock(RcgTestCase):
    def test_duplicated_block_names_the_duplicated_item(self):
        w = self.world()
        text = declaration_text(w.amendment_bytes, default_spec())
        duplicate = "item: A2\ntoken: FM-1 | basis: Basis prose for FM-1 on A2.\n"
        text = text.replace("confirmation:", duplicate + "confirmation:", 1)
        w.declaration.write_text(text)
        p = w.run("worksheet", context="stated")
        assert_ie(self, p, "IE-54", IE_WORDINGS["IE-54"].format(label="A2"))
        assert_no_files(self, w.out1, w.out2)


class TestF7PartialSecondAttesterSet(RcgTestCase):
    def test_supplied_incomplete_second_set_is_refused_ie50(self):
        w = self.world()
        args = w.args("worksheet", context="stated") + [
            "--second-attester", SECOND, "--second-tier", "Plaid"]
        p = run_program(args)
        assert_ie(self, p, "IE-50", IE_WORDINGS["IE-50"].format(flag="--second-context"))
        assert_no_files(self, w.out1, w.out2)


if __name__ == "__main__":
    unittest.main()
