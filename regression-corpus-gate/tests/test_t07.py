"""T7, selection and readback. Brief section 5; plan part 4.7."""

import unittest

from rcg_common import (
    RcgTestCase, default_spec, READBACK_FOOTER, SIZING_LINE, CANONICAL_CORPUS,
    scan_checked_ids,
)


class TestSelection(RcgTestCase):
    def test_subset_by_one_token(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("item A2: declared: FM-1; extracted: none; rows selected: 1", text)

    def test_subset_by_several_tokens(self):
        w = self.world()
        spec = [("A1", ["Gap 1", "Gap 2"], {"Gap 1": "Basis one.", "Gap 2": "Basis two."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("item A1: declared: Gap 1, Gap 2; extracted: none; rows selected: 3", w.read_out1())

    def test_subset_by_fm_token(self):
        w = self.world()
        spec = [("A1", ["FM-2"], {"FM-2": "Basis prose."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("row C-003 for item A1", w.read_out1())

    def test_declared_token_selecting_no_row_recorded(self):
        w = self.world()
        spec = [("A1", ["Gap 9"], {"Gap 9": "Basis prose."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        from rcg_common import pass_specs
        w.write_verdicts([{"label": "A2", "id": "C-002"}], checked_ids=["C-002"])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 4, p.stderr)
        text = w.read_out1()
        self.assertIn("declared tokens that selected no row: Gap 9", text)
        self.assertIn("item A1: declared: Gap 9; extracted: none; rows selected: 0", text)

    def test_row_selected_by_two_tokens_multi_index_line(self):
        w = self.world()
        spec = [("A1", ["Gap 1", "FM-2"], {"Gap 1": "Basis one.", "FM-2": "Basis two."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("rows selected by more than one index: C-003", w.read_out1())

    def test_paired_row_related_not_selected(self):
        w = self.world()
        spec = [("A1", ["Gap 3"], {"Gap 3": "Basis prose."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("related but not selected: C-006", text)
        self.assertIn("related: C-006 is related and is not checked by this item", text)
        self.assertNotIn("row C-006 for item A1", text)

    def test_paired_row_selected_where_own_index_touched(self):
        w = self.world()
        spec = [("A1", ["Gap 3", "Gap 4"], {"Gap 3": "Basis one.", "Gap 4": "Basis two."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("row C-006 for item A1", w.read_out1())

    def test_paired_row_checked_in_full_run(self):
        w = self.world()
        p = w.run("worksheet", declared_mode="full", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("row C-006 for item A1", w.read_out1())

    def test_full_mode_selects_every_row_for_every_item(self):
        w = self.world()
        p = w.run("worksheet", declared_mode="full", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("distinct rows selected: 6", text)
        self.assertIn("row C-006 for item A2", text)

    def test_no_touch_overridden_in_full_mode(self):
        w = self.world()
        spec = [("A1", None, "No touch basis for A1."),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        from rcg_common import ROW_BY_ID
        pairs = [(label, cid) for label in ("A1", "A2") for cid in ROW_BY_ID]
        w.write_verdicts([{"label": l, "id": c} for l, c in pairs],
                         declared_mode="full", effective_mode="full",
                         checked_ids=sorted(ROW_BY_ID))
        p = w.run("finalise", declared_mode="full", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        self.assertIn("overridden", text)
        data = w.read_results()
        item_a1 = [i for i in data["items"] if i["label"] == "A1"][0]
        self.assertTrue(item_a1["overridden"])


class TestReadback(RcgTestCase):
    def test_readback_page_lines(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        lines = text.splitlines()
        self.assertEqual(lines[0], "selection readback")
        self.assertIn("declarer: Declarer Seat", lines[1])
        self.assertIn("confirming seat: Confirmer Seat", text)
        self.assertIn("distinct rows selected: 3", text)
        self.assertIn("index Gap 1: 2 rows", text)
        self.assertIn("index FM-1: 1 rows", text)
        self.assertIn(READBACK_FOOTER, text)

    def test_readback_basis_lines_token_item(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("basis for A1 Gap 1: Basis prose for Gap 1 on A1.", text)
        self.assertIn("basis for A2 FM-1: Basis prose for FM-1 on A2.", text)

    def test_readback_basis_line_no_touch_item(self):
        w = self.world()
        spec = [("A1", None, "No touch basis for A1."),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("basis for A1 no-touch: No touch basis for A1.", w.read_out1())


class TestSizing(RcgTestCase):
    def test_sizing_figures_verbatim_in_limits(self):
        w = self.world()
        w.corpus_bytes = CANONICAL_CORPUS.read_bytes()
        w.corpus.write_bytes(w.corpus_bytes)
        w.set_amendment([("A1", "The amendment changes the staffing rule text.")])
        w.set_declaration([("A1", ["Gap 1"], {"Gap 1": "Basis prose for Gap 1 on A1."})])
        ids = scan_checked_ids(w.corpus_bytes, ["Gap 1"])
        self.assertEqual(len(ids), 159)
        w.write_verdicts([], checked_ids=ids)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        text = w.read_out1()
        self.assertIn(SIZING_LINE, text)
        self.assertIn("distinct rows selected: 159", text)

    def test_gap_union_and_fm_figures_on_canonical(self):
        w = self.world()
        w.corpus_bytes = CANONICAL_CORPUS.read_bytes()
        w.corpus.write_bytes(w.corpus_bytes)
        w.set_amendment([("A1", "The amendment changes the staffing rule text.")])
        spec = [("A1", ["Gap 1", "Gap 2", "Gap 3", "Gap 4"],
                 {"Gap 1": "B1.", "Gap 2": "B2.", "Gap 3": "B3.", "Gap 4": "B4."})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("distinct rows selected: 218", w.read_out1())


    def test_synthetic_scaled_to_upper_bound_shape_no_truncation(self):
        w = self.world()
        from rcg_common import row as make_row, CLAUSE_A, CLAUSE_B, CLAUSE_C
        clauses = [CLAUSE_A, CLAUSE_B, CLAUSE_C]
        rows = []
        for n in range(1, 225):
            rows.append(make_row("C-%03d" % n, "Synthetic incident %d happened" % n,
                                 "Gap 1", clauses[n % 3]))
        w.set_corpus(rows)
        w.set_amendment([("A1", "The amendment changes the staffing rule text.")])
        w.set_declaration([("A1", ["Gap 1"], {"Gap 1": "Basis prose for Gap 1 on A1."})])
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("distinct rows selected: 224", text)
        self.assertIn("item A1: declared: Gap 1; extracted: none; rows selected: 224", text)
        headings = [l for l in text.splitlines() if l.startswith("row C-")]
        self.assertEqual(len(headings), 224)
        expected = ["row C-%03d for item A1" % n for n in range(1, 225)]
        self.assertEqual(headings, expected)
        self.assertEqual(text.splitlines()[0], "selection readback")

    def test_fm_tokens_together_reach_34_rows_on_canonical(self):
        w = self.world()
        w.corpus_bytes = CANONICAL_CORPUS.read_bytes()
        w.corpus.write_bytes(w.corpus_bytes)
        w.set_amendment([("A1", "The amendment changes the staffing rule text.")])
        tokens = ["FM-%d" % n for n in range(1, 15)]
        spec = [("A1", tokens, {t: "Basis for %s." % t for t in tokens})]
        w.set_declaration(spec)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("distinct rows selected: 34", w.read_out1())


if __name__ == "__main__":
    unittest.main()
