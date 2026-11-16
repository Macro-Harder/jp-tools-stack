"""Stage 17 fix regressions. Breaks 1 to 3 of breakit-stage17.md.

Each test stages one staged break input against the plan behaviour that
governs it. Break 1 is the identity trimming rule of plan part 3. Break 2
is the one line per field block form of plan part 3.3. Break 3 is the
triggers line form of plan part 3.3 together with the trigger list binding
of plan part 4.10.
"""

import unittest

from rcg_common import (
    RcgTestCase, assert_ie, assert_no_files, IE_WORDINGS, pass_specs,
    verdicts_text, JUDGE, AUTHOR, PANEL, ROW_BY_ID,
)


def verdicts_with_first_block_changed(tc, w, change, specs=None, **kw):
    specs = pass_specs() if specs is None else specs
    text = verdicts_text(w.corpus_bytes, w.amendment_bytes, w.declaration_bytes, specs, **kw)
    text = change(text)
    w.verdicts.write_text(text)
    return text


def replace_first(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


class TestBreak1JudgeWhitespace(RcgTestCase):
    def _run_padded(self, padded_line):
        w = self.world()
        verdicts_with_first_block_changed(
            self, w,
            lambda t: replace_first(t, "\njudge: " + JUDGE + "\n", "\n" + padded_line + "\n"))
        return w, w.run("finalise", context="stated")

    def test_judge_line_with_one_trailing_space_passes_and_records_the_trimmed_judge(self):
        w, p = self._run_padded("judge: " + JUDGE + " ")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        self.assertEqual(data["outcome"], "pass")
        first = data["items"][0]["verdicts"][0]
        self.assertEqual(first["corpus_id"], "C-001")
        self.assertEqual(first["judge"], JUDGE)

    def test_judge_line_with_two_spaces_after_the_colon_passes(self):
        w, p = self._run_padded("judge:  " + JUDGE)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        self.assertEqual(data["items"][0]["verdicts"][0]["judge"], JUDGE)

    def test_judge_line_with_a_tab_after_the_colon_passes(self):
        w, p = self._run_padded("judge:\t" + JUDGE)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        self.assertEqual(data["items"][0]["verdicts"][0]["judge"], JUDGE)

    def test_padded_panel_judge_line_passes_the_roster_check(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = PANEL
        verdicts_with_first_block_changed(
            self, w,
            lambda t: replace_first(t, "\njudge: " + PANEL + "\n", "\njudge: " + PANEL + " \n"),
            specs=specs, panel=[PANEL])
        p = w.run("finalise", context="stated", panel=[PANEL])
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        self.assertEqual(data["items"][0]["verdicts"][0]["judge"], PANEL)

    def test_padded_author_judge_line_is_seen_by_the_barred_check(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = AUTHOR
        verdicts_with_first_block_changed(
            self, w,
            lambda t: replace_first(t, "\njudge: " + AUTHOR + "\n", "\njudge: " + AUTHOR + " \n"),
            specs=specs, panel=[AUTHOR])
        p = w.run("finalise", context="stated", panel=[AUTHOR])
        self.assertEqual(p.returncode, 6, p.stderr)
        text = w.read_out1()
        self.assertIn("bar: %s is the wording author" % AUTHOR, text)
        assert_no_files(self, w.out2)


class TestBreak2DuplicatedFieldLines(RcgTestCase):
    def _run_duplicated(self, change, form="finalise"):
        w = self.world()
        verdicts_with_first_block_changed(self, w, change)
        return w, w.run(form, context="stated")

    def _assert_duplicate_refused(self, w, p):
        assert_ie(self, p, "IE-33", IE_WORDINGS["IE-33"].format(label="A1", id="C-001"))
        assert_no_files(self, w.out1, w.out2)

    def test_duplicated_word_line_fail_then_pass_is_refused(self):
        w, p = self._run_duplicated(
            lambda t: replace_first(t, "word: PASS\n", "word: FAIL\nword: PASS\n"))
        self._assert_duplicate_refused(w, p)

    def test_duplicated_judge_line_author_then_judge_is_refused(self):
        w, p = self._run_duplicated(
            lambda t: replace_first(t, "\njudge: " + JUDGE + "\n",
                                    "\njudge: " + AUTHOR + "\njudge: " + JUDGE + "\n"))
        self._assert_duplicate_refused(w, p)

    def test_duplicated_clause_line_is_refused(self):
        clause_line = "clause: " + ROW_BY_ID["C-001"]["clause"] + "\n"
        w, p = self._run_duplicated(
            lambda t: replace_first(t, clause_line, clause_line + clause_line))
        self._assert_duplicate_refused(w, p)

    def test_duplicated_reason_line_is_refused(self):
        reason_line = "reason: The row was judged on its own procedure.\n"
        w, p = self._run_duplicated(
            lambda t: replace_first(t, reason_line, reason_line + reason_line))
        self._assert_duplicate_refused(w, p)

    def test_duplicated_word_line_is_refused_at_the_remaining_form(self):
        w, p = self._run_duplicated(
            lambda t: replace_first(t, "word: PASS\n", "word: FAIL\nword: PASS\n"),
            form="remaining")
        assert_ie(self, p, "IE-33", IE_WORDINGS["IE-33"].format(label="A1", id="C-001"))
        assert_no_files(self, w.out1)


class TestBreak3EmptiedTriggersLine(RcgTestCase):
    def _world_with_empty_triggers(self):
        w = self.world()
        verdicts_with_first_block_changed(
            self, w, lambda t: replace_first(t, "triggers: none\n", "triggers: \n"))
        return w

    def test_empty_triggers_value_fails_binding_at_finalise(self):
        w = self._world_with_empty_triggers()
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="trigger list"))
        assert_no_files(self, w.out1, w.out2)

    def test_empty_triggers_value_fails_binding_at_remaining(self):
        w = self._world_with_empty_triggers()
        p = w.run("remaining", context="stated")
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="trigger list"))
        assert_no_files(self, w.out1)


if __name__ == "__main__":
    unittest.main()
