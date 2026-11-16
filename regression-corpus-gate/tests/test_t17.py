"""T17, remaining form. Brief sections 2 and 9; plan part 5.5."""

import unittest

from rcg_common import (
    RcgTestCase, pass_specs, assert_ie, IE_WORDINGS, REMAINING_FIXED_LINES,
    verdicts_text, JUDGE, ROW_BY_ID,
)


class TestRemainingReports(RcgTestCase):
    def test_partly_filled_reports_remaining_ids(self):
        w = self.world()
        w.write_verdicts(pass_specs()[:1])
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 9, p.stderr)
        text = w.read_out1()
        self.assertEqual(text.splitlines()[0], "regression-corpus-gate 1.0.0")
        for line in REMAINING_FIXED_LINES:
            self.assertIn(line, text)
        self.assertIn("item A1: missing 1: C-003", text)
        self.assertIn("item A2: missing 1: C-002", text)
        self.assertIn("pairs remaining: 2 of 3 checked pairs", text)
        self.assertIn("exit status: 9", text)

    def test_fully_filled_reports_zero_remaining(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 9, p.stderr)
        text = w.read_out1()
        self.assertIn("pairs remaining: 0 of 3 checked pairs", text)

    def test_empty_verdicts_reports_every_pair_remaining(self):
        w = self.world()
        w.verdicts.write_bytes(b"")
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 9, p.stderr)
        self.assertIn("pairs remaining: 3 of 3 checked pairs", w.read_out1())

    def test_untouched_template_blocks_count_as_remaining(self):
        w = self.world()
        blocks = []
        header = verdicts_text(w.corpus_bytes, w.amendment_bytes, w.declaration_bytes, [])
        text = header
        for label, cid in (("A1", "C-001"), ("A1", "C-003"), ("A2", "C-002")):
            text += "verdict: %s %s\njudge: \nclause: \nword: \nreason: \n" % (label, cid)
        w.verdicts.write_text(text)
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 9, p.stderr)
        self.assertIn("pairs remaining: 3 of 3 checked pairs", w.read_out1())

    def test_partly_filled_block_is_structural_error(self):
        w = self.world()
        header = verdicts_text(w.corpus_bytes, w.amendment_bytes, w.declaration_bytes, [])
        text = header + "verdict: A1 C-001\njudge: %s\nclause: \nword: \nreason: \n" % JUDGE
        w.verdicts.write_text(text)
        p = w.run("remaining", context="stated")
        assert_ie(self, p, "IE-45", IE_WORDINGS["IE-45"].format(label="A1", id="C-001", slot="clause"))

    def test_recompute_beats_claimed_checked_set(self):
        w = self.world()
        w.write_verdicts(pass_specs(), checked_ids=["C-001"])
        p = w.run("remaining", context="stated")
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="checked ID set"))

    def test_declaration_conflict_at_remaining_path(self):
        w = self.world()
        w.set_amendment([("A1", "The wording names Gap 7 plainly."),
                         ("A2", "The amendment changes the counting text.")])
        from rcg_common import default_spec
        w.set_declaration(default_spec())
        w.write_verdicts([])
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 7, p.stderr)
        self.assertIn("exit status: 7", w.read_out1())

    def test_missing_verdicts_ie31(self):
        w = self.world()
        p = w.run("remaining", context="stated")
        assert_ie(self, p, "IE-31", IE_WORDINGS["IE-31"].format(path=str(w.verdicts)))

    def test_no_barred_no_self_test_in_remaining(self):
        w = self.world()
        from rcg_common import AUTHOR
        specs = pass_specs()[:1]
        specs[0]["judge"] = AUTHOR
        w.write_verdicts(specs, judge_of_record=AUTHOR)
        p = w.run("remaining", context="stated", judge=AUTHOR)
        self.assertEqual(p.returncode, 9, p.stderr)
        text = w.read_out1()
        self.assertNotIn("probe selection_probe", text)
        self.assertNotIn("barred", text.splitlines()[1])


if __name__ == "__main__":
    unittest.main()
