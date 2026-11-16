"""T3, corpus parsing and integrity. Brief sections 3 and 4; plan part 4.5."""

import unittest

from rcg_common import (
    RcgTestCase, World, run_program, assert_ie, IE_WORDINGS, corpus_text, row,
    CLAUSE_A, CLAUSE_B, CLAUSE_C, CLAUSE_D, DEFAULT_ROWS, ROW_BY_ID,
    CANONICAL_CORPUS, FIXTURES, DECLARER, CONFIRMER,
)

CANON_CLAUSES = [
    ("fail if allowed or if distinct-agent spawn evidence is not required.", 111),
    ("fail if allowed, left unnamed, or closed on a report alone.", 75),
    ("fail if allowed, if the resulting state has no name in the amendment, or if verification rests on the reporter alone.", 38),
]


def worksheet_ok(tc, w):
    p = w.run("worksheet")
    tc.assertEqual(p.returncode, 10, p.stderr)
    return w.read_out1()


class TestDialectsAndTokens(RcgTestCase):
    def test_gap_only_row_parses(self):
        w = self.world()
        text = worksheet_ok(self, w)
        self.assertIn("row C-001 for item A1", text)

    def test_fm_only_row_parses(self):
        w = self.world()
        text = worksheet_ok(self, w)
        self.assertIn("row C-002 for item A2", text)

    def test_both_kinds_row_parses(self):
        w = self.world()
        w.set_declaration([("A1", ["FM-2"], {"FM-2": "Basis prose for FM-2 on A1."}),
                           ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})])
        text = worksheet_ok(self, w)
        self.assertIn("row C-003 for item A1", text)

    def test_token_duplicates_inside_one_cell(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["index"] = "Gap 1, Gap 1, Gap 1"
        w.set_corpus(rows)
        text = worksheet_ok(self, w)
        self.assertIn("index Gap 1: 2 rows", text)

    def test_empty_index_cell_no_token_no_failure(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[3]["index"] = "no token stated in this cell"
        w.set_corpus(rows)
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)

    def test_index_cell_ellipsis_in_annotation_not_flagged(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["index"] = "Gap 1; annotation prose trails off..."
        w.set_corpus(rows)
        text = worksheet_ok(self, w)
        section = text.split("row C-001 for item A1")[1].split("row C-")[0]
        self.assertNotIn("flagged:", section)
        self.assertIn("index Gap 1:", text)

    def test_index_cell_ellipsis_before_comma_with_token(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["index"] = "Gap 1..., FM-9"
        w.set_corpus(rows)
        text = worksheet_ok(self, w)
        self.assertIn("index Gap 1:", text)


class TestIntegrityErrors(RcgTestCase):
    def test_row_not_six_cells(self):
        w = self.world()
        text = corpus_text(DEFAULT_ROWS).replace(
            "| C-002 | synthetic source |", "| C-002 |")
        w.corpus.write_text(text)
        line_no = [i + 1 for i, l in enumerate(text.splitlines()) if l.startswith("| C-002")][0]
        p = w.run("worksheet")
        assert_ie(self, p, "IE-09", IE_WORDINGS["IE-09"].format(n=line_no))

    def test_duplicate_id(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[1]["id"] = "C-001"
        w.set_corpus(rows)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-10", IE_WORDINGS["IE-10"].format(id="C-001"))

    def test_duplicate_id_with_different_texts(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[1]["id"] = "C-001"
        rows[1]["incident"] = "A wholly different incident text"
        w.set_corpus(rows)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-10", IE_WORDINGS["IE-10"].format(id="C-001"))

    def test_missing_id_in_sequence(self):
        w = self.world()
        rows = [r for r in DEFAULT_ROWS if r["id"] != "C-003"]
        w.set_corpus(rows)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-11", IE_WORDINGS["IE-11"].format(id="C-003"))

    def test_count_mismatch_front_against_rows(self):
        w = self.world()
        w.set_corpus(DEFAULT_ROWS, front=7)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-12", IE_WORDINGS["IE-12"].format(a=7, b=6, c=6))

    def test_count_mismatch_closing_against_rows(self):
        w = self.world()
        w.set_corpus(DEFAULT_ROWS, closing=9)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-12", IE_WORDINGS["IE-12"].format(a=6, b=9, c=6))

    def test_count_mismatch_front_against_closing_rows_agree_with_one(self):
        w = self.world()
        w.set_corpus(DEFAULT_ROWS, front=6, closing=8)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-12", IE_WORDINGS["IE-12"].format(a=6, b=8, c=6))

    def test_absent_front_matter_statement(self):
        w = self.world()
        w.set_corpus(DEFAULT_ROWS, front="absent")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-12", IE_WORDINGS["IE-12"].format(a="absent", b=6, c=6))

    def test_absent_closing_statement(self):
        w = self.world()
        w.set_corpus(DEFAULT_ROWS, closing="absent")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-12", IE_WORDINGS["IE-12"].format(a=6, b="absent", c=6))

    def test_only_one_count_statement_either_form(self):
        w = self.world()
        w.set_corpus(DEFAULT_ROWS, front="absent", closing=6)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-12", IE_WORDINGS["IE-12"].format(a="absent", b=6, c=6))

    def test_digits_entries_line_is_not_a_count_statement(self):
        w = self.world()
        text = corpus_text(DEFAULT_ROWS).replace(
            "This corpus contains 6 incident entries. That is the governing count.", "6 entries")
        w.corpus.write_text(text)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-12", IE_WORDINGS["IE-12"].format(a="absent", b=6, c=6))

    def test_duplicate_and_missing_fail_under_ie10_first(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS if r["id"] != "C-003"]
        rows[1]["id"] = "C-001"
        w.set_corpus(rows)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-10", IE_WORDINGS["IE-10"].format(id="C-001"))


class TestRealCountForms(RcgTestCase):
    def test_real_forms_recognised_and_extracted(self):
        w = self.world()
        excerpt = (FIXTURES / "real_corpus_excerpt.md").read_bytes()
        w.corpus.write_bytes(excerpt)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-11", IE_WORDINGS["IE-11"].format(id="C-002"))

    def test_excerpt_missing_closing_check(self):
        w = self.world()
        text = (FIXTURES / "real_corpus_excerpt.md").read_text()
        kept = [l for l in text.splitlines() if not l.startswith("- Total:")]
        w.corpus.write_text("\n".join(kept) + "\n")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-11", IE_WORDINGS["IE-11"].format(id="C-002"))


class TestFlagging(RcgTestCase):
    def _worksheet_with_row(self, mutated):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        mutated(rows)
        w.set_corpus(rows)
        return w, w.run("worksheet")

    def test_flagged_by_empty_incident_cell(self):
        w, p = self._worksheet_with_row(lambda rows: rows[0].update(incident="", test="An implementation that permits  fails"))
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", w.read_out1())

    def test_flagged_by_ellipsis_end_of_cell(self):
        w, p = self._worksheet_with_row(lambda rows: rows[0].update(incident="Alpha incident happened..."))
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", w.read_out1())

    def test_flagged_by_three_dots_before_closing_quote(self):
        def m(rows):
            rows[0]["incident"] = 'Alpha incident happened..."'
            rows[0]["test"] = 'An implementation that permits Alpha incident happened..." fails'
        w, p = self._worksheet_with_row(m)
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", w.read_out1())

    def test_flagged_by_no_separator_form(self):
        w, p = self._worksheet_with_row(lambda rows: rows[0].update(proc="Inspect the amendment for the named shape."))
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", text)
        self.assertIn("no closing fail clause was found", text)
        self.assertIn("test: no closing fail clause stands", text)

    def test_flagged_by_degenerate_clause(self):
        w, p = self._worksheet_with_row(lambda rows: rows[0].update(proc="Inspect the amendment; fail if"))
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("the closing fail clause states no condition", text)
        self.assertIn("test: no closing fail clause stands", text)

    def test_flagged_by_degenerate_clause_full_stop_only(self):
        w, p = self._worksheet_with_row(lambda rows: rows[0].update(proc="Inspect the amendment; fail if."))
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("the closing fail clause states no condition", text)
        self.assertIn("test: no closing fail clause stands", text)

    def test_flagged_by_single_character_ellipsis_in_incident(self):
        w, p = self._worksheet_with_row(lambda rows: rows[0].update(incident="Alpha incident happened\u2026"))
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", w.read_out1())

    def test_flagged_by_single_character_ellipsis_in_test_statement(self):
        def m(rows):
            rows[0]["test"] = "An implementation that permits Alpha incident happened\u2026"
        w, p = self._worksheet_with_row(m)
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", w.read_out1())

    def test_flagged_by_single_character_ellipsis_in_pass_procedure(self):
        def m(rows):
            rows[0]["proc"] = "Inspect the amendment for the named shape; fail if the amendment permits the named failure shape.\u2026"
        w, p = self._worksheet_with_row(m)
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", w.read_out1())

    def test_flagged_by_empty_test_statement_cell_only(self):
        def m(rows):
            rows[0]["test"] = ""
        w, p = self._worksheet_with_row(m)
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", w.read_out1())

    def test_flagged_by_empty_pass_procedure_cell_only(self):
        def m(rows):
            rows[0]["proc"] = ""
        w, p = self._worksheet_with_row(m)
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", w.read_out1())

    def test_index_cell_single_character_ellipsis_in_annotation_not_flagged(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["index"] = "Gap 1; annotation prose trails off\u2026"
        w.set_corpus(rows)
        text = worksheet_ok(self, w)
        section = text.split("row C-001 for item A1")[1].split("row C-")[0]
        self.assertNotIn("flagged:", section)
        self.assertIn("index Gap 1:", text)

    def test_malformed_prose_flags_nothing_and_fails_nothing(self):
        w, p = self._worksheet_with_row(lambda rows: rows[0].update(incident="Alpha incident happened, oddly worded ### with stray marks"))
        self.assertEqual(p.returncode, 10, p.stderr)
        section = w.read_out1().split("row C-001 for item A1")[1].split("row C-")[0]
        self.assertNotIn("flagged:", section)


class TestClauseExtraction(RcgTestCase):
    def test_one_row_per_family(self):
        w = self.world()
        text = worksheet_ok(self, w)
        for clause in (CLAUSE_A, CLAUSE_B, CLAUSE_C):
            self.assertIn("test: " + clause, text)

    def test_clause_after_last_separator(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["proc"] = "First part; fail if an early condition stands. Second part; " + CLAUSE_A
        w.set_corpus(rows)
        text = worksheet_ok(self, w)
        section = text.split("row C-001 for item A1")[1].split("row C-")[0]
        test_line = [l for l in section.splitlines() if l.startswith("test:")][0]
        self.assertEqual(test_line, "test: " + CLAUSE_A)

    def test_fourth_clause_family_line(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[3]["proc"] = "Inspect the amendment for the named shape; " + CLAUSE_D
        rows[3]["clause"] = CLAUSE_D
        w.set_corpus(rows)
        from rcg_common import pass_specs
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        self.assertIn("clause family as read: %s, 1 rows" % CLAUSE_D, text)


class TestDivergence(RcgTestCase):
    def test_core_standing_in_incident_gives_no_note(self):
        w = self.world()
        text = worksheet_ok(self, w)
        section = text.split("row C-001 for item A1")[1].split("row C-")[0]
        self.assertNotIn("diverge in wording", section)

    def test_core_not_standing_gives_note(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["test"] = "An implementation that permits a wholly other wording fails"
        w.set_corpus(rows)
        text = worksheet_ok(self, w)
        self.assertIn("the incident line and the test statement diverge in wording", text)

    def test_frame_only_test_statement_gives_note(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["test"] = "An implementation that permits  fails"
        w.set_corpus(rows)
        text = worksheet_ok(self, w)
        self.assertIn("the incident line and the test statement diverge in wording", text)

    def test_opening_words_in_middle_are_kept(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["test"] = "An implementation that permits Alpha incident happened An implementation that permits repetition fails"
        w.set_corpus(rows)
        text = worksheet_ok(self, w)
        self.assertIn("the incident line and the test statement diverge in wording", text)


class TestCanonicalCorpus(RcgTestCase):
    def _canonical_world(self):
        w = self.world()
        w.corpus_bytes = CANONICAL_CORPUS.read_bytes()
        w.corpus.write_bytes(w.corpus_bytes)
        w.set_declaration([("A1", ["Gap 1"], {"Gap 1": "Basis prose for Gap 1 on A1."}),
                           ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})])
        return w

    def test_canonical_counts_and_clause_census(self):
        w = self._canonical_world()
        from rcg_common import scan_checked_ids
        ids = scan_checked_ids(w.corpus_bytes, ["Gap 1", "FM-1"])
        w.write_verdicts([], checked_ids=ids)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        text = w.read_out1()
        for clause, n in CANON_CLAUSES:
            self.assertIn("clause family as read: %s, %d rows" % (clause, n), text)

    def test_canonical_annex_and_arrangement_counts(self):
        w = self._canonical_world()
        from rcg_common import scan_checked_ids
        ids = scan_checked_ids(w.corpus_bytes, ["Gap 1", "FM-1"])
        w.write_verdicts([], checked_ids=ids)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        text = w.read_out1()
        limits = text.split("\nlimits\n")[1]
        import re
        pairings = [
            (r"Annex 1\b.{0,120}Gap tokens only.{0,40}78 rows", "Annex 1 Gap tokens only 78 rows"),
            (r"Annex 1\b.{0,160}both kinds.{0,40}33 rows", "Annex 1 both kinds 33 rows"),
            (r"Annex 2\b.{0,120}Gap tokens only.{0,40}35 rows", "Annex 2 Gap tokens only 35 rows"),
            (r"Annex 3\b.{0,120}Gap tokens only.{0,40}40 rows", "Annex 3 Gap tokens only 40 rows"),
            (r"Annex 4\b.{0,120}Gap tokens only.{0,40}37 rows", "Annex 4 Gap tokens only 37 rows"),
            (r"Annex 4\b.{0,160}both kinds.{0,40}1 rows?\b", "Annex 4 both kinds 1 row"),
        ]
        for pattern, label in pairings:
            self.assertTrue(re.search(pattern, limits, re.DOTALL), label + " not paired in limits section: " + limits[:800])
        from rcg_common import scan_tokens
        row_194 = None
        for line in CANONICAL_CORPUS.read_text().splitlines():
            if line.startswith("| C-194 |"):
                row_194 = [c.strip() for c in line.split("|")[1:-1]]
        self.assertIsNotNone(row_194, "C-194 stands in the canonical corpus")
        kinds_194 = {t.split("-")[0].split(" ")[0] for t in scan_tokens(row_194[4])}
        self.assertEqual(kinds_194, {"Gap", "FM"}, "the Annex 4 both kinds row at C-194 carries both kinds")

    def test_row_before_first_annex_heading_group_none_stated(self):
        w = self.world()
        text = corpus_text(DEFAULT_ROWS, headings=False, annex_bullets=False)
        w.corpus.write_text(text)
        w.corpus_bytes = text.encode()
        from rcg_common import pass_specs
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("none stated", w.read_out1())


if __name__ == "__main__":
    unittest.main()
