"""T6, tripwire. Brief section 5; plan part 4.7."""

import unittest

from rcg_common import (
    RcgTestCase, assert_outcome_line, default_spec, SENTENCES,
)


def conflict_world(tc, wording, spec=None):
    w = tc.world()
    w.set_amendment([("A1", wording), ("A2", "The amendment changes the counting text.")])
    w.set_declaration(default_spec() if spec is None else spec)
    return w


class TestAcceptedForms(RcgTestCase):
    pass


ACCEPTED = [
    ("space gap", "The wording names Gap 1 in space form.", "Gap 1"),
    ("hyphen gap", "The wording names Gap-1 in hyphen form.", "Gap 1"),
    ("bare gap", "The wording names Gap1 in bare form.", "Gap 1"),
    ("space fm", "The wording names FM 1 in space form.", "FM-1"),
    ("hyphen fm", "The wording names FM-1 in hyphen form.", "FM-1"),
    ("bare fm", "The wording names FM1 in bare form.", "FM-1"),
    ("mixed case gap", "The wording names gAP 1 in mixed case.", "Gap 1"),
    ("mixed case fm", "The wording names fM-1 in mixed case.", "FM-1"),
    ("leading zero canonicalised", "The wording names Gap 01 in zero form.", "Gap 1"),
]

for _name, _wording, _tok in ACCEPTED:
    def _make(wording=_wording, tok=_tok):
        def test(self):
            spec = [("A1", [tok], {tok: "Basis prose."}),
                    ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
            if tok == "FM-1":
                spec = [("A1", ["FM-1"], {"FM-1": "Basis prose."}),
                        ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
            w = conflict_world(self, wording, spec)
            p = w.run("worksheet")
            self.assertEqual(p.returncode, 10, p.stderr)
            text = w.read_out1()
            self.assertIn("item A1: declared: %s; extracted: %s;" % (tok, tok), text)
        return test
    setattr(TestAcceptedForms, "test_accepted_%s" % _name.replace(" ", "_"), _make())


class TestConflicts(RcgTestCase):
    def test_token_for_other_item_does_not_cover(self):
        w = conflict_world(self, "The wording names Gap 2 plainly.")
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 7, p.stderr)
        text = w.read_out1()
        assert_outcome_line(self, text, "declaration conflict")
        self.assertIn("item A1: omitted tokens: Gap 2", text)
        self.assertFalse(w.out2.exists())

    def test_range_form_extracts_nothing(self):
        w = conflict_world(self, "The wording names Gap 1 to Gap 4 as a range.")
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 7, p.stderr)
        text = w.read_out1()
        self.assertIn("item A1: omitted tokens: Gap 4", text)
        self.assertNotIn("omitted tokens: Gap 1", text)

    def test_hyphen_range_extracts_nothing(self):
        spec = [("A1", ["Gap 9"], {"Gap 9": "Basis prose."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w = conflict_world(self, "The wording names Gap 1-4 as a range.", spec)
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("item A1: declared: Gap 9; extracted: none;", text)

    def test_spaced_range_extracts_nothing(self):
        spec = [("A1", ["Gap 9"], {"Gap 9": "Basis prose."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w = conflict_world(self, "The wording names Gap 1 - 4 as a range.", spec)
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("item A1: declared: Gap 9; extracted: none;", text)

    def test_compressed_list_extracts_only_worded_number(self):
        w = conflict_world(self, "The wording names Gap 1, 2, 3 as a list.")
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("item A1: declared: Gap 1; extracted: Gap 1;", text)

    def test_token_preceded_by_digit_extracts_nothing(self):
        w = conflict_world(self, "The wording names 9Gap 2 in a code string.")
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("item A1: declared: Gap 1; extracted: none;", text)

    def test_no_touch_item_wording_token_conflicts(self):
        spec = [("A1", None, "No touch basis for A1."),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w = conflict_world(self, "The wording names Gap 5 plainly.", spec)
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 7, p.stderr)
        self.assertIn("item A1: omitted tokens: Gap 5", w.read_out1())

    def test_clean_item_no_conflict(self):
        w = conflict_world(self, "The wording names no index at all.")
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("item A1: declared: Gap 1; extracted: none;", text)


class TestConflictReportForms(RcgTestCase):
    def test_conflict_at_worksheet_path(self):
        w = conflict_world(self, "The wording names Gap 7 plainly.")
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 7, p.stderr)
        text = w.read_out1()
        self.assertIn("regression-corpus-gate 1.0.0", text.splitlines()[0])
        self.assertIn("the declaration must be amended, freshly confirmed, and rerun before any judging", text)
        self.assertIn("exit status: 7", text)
        self.assertFalse(w.out2.exists())

    def test_conflict_at_finalise_path(self):
        w = conflict_world(self, "The wording names Gap 7 plainly.")
        from rcg_common import pass_specs
        w.write_verdicts(pass_specs())
        p = w.run("finalise")
        self.assertEqual(p.returncode, 7, p.stderr)
        self.assertIn("exit status: 7", w.read_out1())
        self.assertFalse(w.out2.exists())

    def test_conflict_at_remaining_path(self):
        w = conflict_world(self, "The wording names Gap 7 plainly.")
        w.write_verdicts([])
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 7, p.stderr)
        self.assertIn("exit status: 7", w.read_out1())


if __name__ == "__main__":
    unittest.main()
