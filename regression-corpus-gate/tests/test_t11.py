"""T11, verdicts parsing and binding. Brief sections 3 and 7; plan parts 3.3 and 4.10."""

import unittest

from rcg_common import (
    RcgTestCase, assert_ie, assert_no_files, IE_WORDINGS, pass_specs,
    verdicts_text, sha256_hex, JUDGE, AUTHOR, PANEL, NO_CLAUSE_STATEMENT,
    ROW_BY_ID, row, CLAUSE_A, corpus_text, DEFAULT_ROWS,
)


def finalise_with(tc, w, specs, **kw):
    w.write_verdicts(specs, **kw)
    return w.run("finalise", context="stated")


class TestStructuralCases(RcgTestCase):
    def test_word_outside_vocabulary_ie32(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "MAYBE"
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-32", IE_WORDINGS["IE-32"].format(label="A1", id="C-001", word="MAYBE"))

    def test_duplicate_verdict_ie33(self):
        w = self.world()
        specs = pass_specs()
        specs.append(dict(specs[0]))
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-33", IE_WORDINGS["IE-33"].format(label="A1", id="C-001"))

    def test_unchecked_row_ie34(self):
        w = self.world()
        specs = pass_specs()
        specs.append({"label": "A1", "id": "C-004"})
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-34", IE_WORDINGS["IE-34"].format(label="A1", id="C-004"))

    def test_empty_reason_ie35(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["reason"] = ""
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-35", IE_WORDINGS["IE-35"].format(label="A1", id="C-001"))

    def test_empty_word_slot_ie45_not_missing(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = ""
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-45", IE_WORDINGS["IE-45"].format(label="A1", id="C-001", slot="word"))

    def test_empty_judge_slot_ie45(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = ""
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-45", IE_WORDINGS["IE-45"].format(label="A1", id="C-001", slot="judge"))

    def test_out_of_roster_judge_ie37(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = "Stranger Seat"
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-37", IE_WORDINGS["IE-37"].format(label="A1", id="C-001", judge="Stranger Seat"))

    def test_blocks_out_of_order_acceptable(self):
        w = self.world()
        specs = list(reversed(pass_specs()))
        p = finalise_with(self, w, specs)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_panel_partition_acceptable(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = PANEL
        specs[2]["judge"] = JUDGE
        w.write_verdicts(specs, panel=[PANEL])
        p = w.run("finalise", context="stated", panel=[PANEL])
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_missing_binding_header_line_ie46(self):
        w = self.world()
        text = verdicts_text(w.corpus_bytes, w.amendment_bytes, w.declaration_bytes, pass_specs())
        text = "\n".join(l for l in text.splitlines() if not l.startswith("triggers:")) + "\n"
        w.verdicts.write_text(text)
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-46", IE_WORDINGS["IE-46"].format(line="triggers"))


CLAIM_SHAPES = [
    ("claim on pass verdict", "IE-39", {"word": "PASS", "claim": {}}),
    ("confirming judge differs", "IE-40", {"word": "FAIL", "claim": {"confirming_judge": "Other Seat"}}),
    ("confirming judge absent", "IE-41", {"word": "FAIL", "claim": {"confirming_judge": ""}}),
    ("empty queue item", "IE-43", {"word": "FAIL", "claim": {"queue_item": ""}}),
    ("empty ruling date", "IE-44", {"word": "FAIL", "claim": {"ruling_date": ""}}),
]


class TestClaimShapes(RcgTestCase):
    pass


for _name, _ie, _patch in CLAIM_SHAPES:
    def _make(ie=_ie, patch=_patch):
        def test(self):
            w = self.world()
            specs = pass_specs()
            specs[0].update(patch)
            if patch.get("claim") is not None and patch["claim"].get("confirming_judge", JUDGE) == "Other Seat":
                specs[0]["claim"] = dict(patch["claim"])
            p = finalise_with(self, w, specs)
            assert_ie(self, p, ie, IE_WORDINGS[ie].format(label="A1", id="C-001"))
        return test
    setattr(TestClaimShapes, "test_claim_%s" % _name.replace(" ", "_"), _make())


class TestSecondClaimBlock(RcgTestCase):
    def test_second_claim_block_ie42(self):
        w = self.world()
        text = verdicts_text(w.corpus_bytes, w.amendment_bytes, w.declaration_bytes,
                             [dict(pass_specs()[0], word="FAIL", claim={})] + pass_specs()[1:])
        extra = "claim:\nqueue-item: DQ-101\nruling-date: 2026-11-01\nconfirming-judge: %s\n" % JUDGE
        text = text.replace("verdict: A1 C-003", extra + "verdict: A1 C-003")
        w.verdicts.write_text(text)
        p = w.run("finalise", context="stated", queue=True)
        assert_ie(self, p, "IE-42", IE_WORDINGS["IE-42"].format(label="A1", id="C-001"))


class TestBindingValues(RcgTestCase):
    def _run_with_header_change(self, change):
        w = self.world()
        text = verdicts_text(w.corpus_bytes, w.amendment_bytes, w.declaration_bytes, pass_specs())
        text = change(text, w)
        w.verdicts.write_text(text)
        return w, w.run("finalise", context="stated")

    def test_amendment_fingerprint_differs(self):
        w, p = self._run_with_header_change(lambda t, w: t.replace(sha256_hex(w.amendment_bytes), "0" * 64, 1))
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="amendment fingerprint"))

    def test_corpus_fingerprint_differs(self):
        w, p = self._run_with_header_change(lambda t, w: t.replace(sha256_hex(w.corpus_bytes), "1" * 64, 1))
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="corpus fingerprint"))

    def test_declaration_fingerprint_differs(self):
        w, p = self._run_with_header_change(lambda t, w: t.replace(sha256_hex(w.declaration_bytes), "2" * 64, 1))
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="declaration fingerprint"))

    def test_declared_mode_differs(self):
        w, p = self._run_with_header_change(lambda t, w: t.replace("declared-mode: subset", "declared-mode: full"))
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="declared mode"))

    def test_effective_mode_differs(self):
        w, p = self._run_with_header_change(lambda t, w: t.replace("effective-mode: subset", "effective-mode: full"))
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="effective mode"))

    def test_trigger_list_differs(self):
        w, p = self._run_with_header_change(lambda t, w: t.replace("triggers: none", "triggers: context-mixed"))
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="trigger list"))

    def test_checked_set_differs(self):
        w, p = self._run_with_header_change(lambda t, w: t.replace("checked: C-002\n", ""))
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="checked ID set"))

    def test_judge_roster_differs(self):
        w, p = self._run_with_header_change(lambda t, w: t.replace("judge-of-record: " + JUDGE, "judge-of-record: Other Seat"))
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="judge roster"))

    def test_two_values_differ_first_in_order_wins(self):
        def change(t, w):
            t = t.replace(sha256_hex(w.corpus_bytes), "1" * 64, 1)
            t = t.replace("effective-mode: subset", "effective-mode: full")
            return t
        w, p = self._run_with_header_change(change)
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="corpus fingerprint"))

    def test_panel_order_reversed_is_roster_mismatch(self):
        w = self.world()
        from rcg_common import PANEL2
        text = verdicts_text(w.corpus_bytes, w.amendment_bytes, w.declaration_bytes, pass_specs(),
                             panel=[PANEL, PANEL2])
        lines = text.splitlines()
        idx = [i for i, l in enumerate(lines) if l.startswith("panel-judge:")]
        lines[idx[0]], lines[idx[1]] = lines[idx[1]], lines[idx[0]]
        w.verdicts.write_text("\n".join(lines) + "\n")
        p = w.run("finalise", context="stated", panel=[PANEL, PANEL2])
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="judge roster"))

    def test_duplicated_panel_line_is_roster_mismatch(self):
        w = self.world()
        text = verdicts_text(w.corpus_bytes, w.amendment_bytes, w.declaration_bytes, pass_specs(), panel=[PANEL])
        text = text.replace("panel-judge: " + PANEL + "\n", "panel-judge: " + PANEL + "\npanel-judge: " + PANEL + "\n")
        w.verdicts.write_text(text)
        p = w.run("finalise", context="stated", panel=[PANEL])
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="judge roster"))

    def test_trigger_arising_after_worksheet_fails_binding(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="disputed")
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="effective mode"))


class TestClauseBinding(RcgTestCase):
    def test_other_family_clause_ie53(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["clause"] = ROW_BY_ID["C-002"]["clause"]
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-53", IE_WORDINGS["IE-53"].format(label="A1", id="C-001"))

    def test_invented_clause_ie53(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["clause"] = "fail if something invented stands."
        p = finalise_with(self, w, specs)
        assert_ie(self, p, "IE-53", IE_WORDINGS["IE-53"].format(label="A1", id="C-001"))


class TestMissingEmptyUnreadable(RcgTestCase):
    def test_missing_verdicts_finalise_incomplete(self):
        w = self.world()
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        text = w.read_out1()
        self.assertIn("no verdicts file was read: missing", text)
        data = w.read_results()
        self.assertEqual(data["fingerprints"]["verdicts"], "no verdicts file was read: missing")
        self.assertEqual(data["outcome"], "incomplete")

    def test_empty_verdicts_finalise_incomplete_with_zero_fingerprint(self):
        w = self.world()
        w.verdicts.write_bytes(b"")
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        data = w.read_results()
        from rcg_common import ZERO_BYTE_SHA256
        self.assertEqual(data["fingerprints"]["verdicts"], ZERO_BYTE_SHA256)

    def test_blank_and_comment_only_verdicts_is_empty(self):
        w = self.world()
        w.verdicts.write_text("\n# only a comment\n\n")
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertNotIn("IE-46", p.stderr)

    def test_missing_verdicts_with_barred_judge_is_barred(self):
        w = self.world()
        p = w.run("finalise", context="stated", judge=AUTHOR)
        self.assertEqual(p.returncode, 6, p.stderr)
        self.assertFalse(w.out2.exists())

    def test_unreadable_verdicts_finalise_ie05(self):
        w = self.world()
        w.verdicts.mkdir()
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-05", IE_WORDINGS["IE-05"].format(kind="verdicts", path=str(w.verdicts)))
        assert_no_files(self, w.out1, w.out2)

    def test_unreadable_verdicts_remaining_ie05_not_ie31(self):
        w = self.world()
        w.verdicts.mkdir()
        p = w.run("remaining", context="stated")
        assert_ie(self, p, "IE-05", IE_WORDINGS["IE-05"].format(kind="verdicts", path=str(w.verdicts)))


class TestNoClauseRowVerdicts(RcgTestCase):
    def _no_clause_world(self):
        w = self.world()
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["proc"] = "Inspect the amendment for the named shape."
        w.set_corpus(rows)
        return w

    def test_no_clause_statement_with_unjudgeable_stands(self):
        w = self._no_clause_world()
        specs = pass_specs()
        specs[0]["clause"] = NO_CLAUSE_STATEMENT
        specs[0]["word"] = "UNJUDGEABLE"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 4, p.stderr)

    def test_no_clause_row_other_clause_text_ie53(self):
        w = self._no_clause_world()
        specs = pass_specs()
        specs[0]["clause"] = CLAUSE_A
        specs[0]["word"] = "UNJUDGEABLE"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-53", IE_WORDINGS["IE-53"].format(label="A1", id="C-001"))

    def test_no_clause_row_empty_clause_slot_ie45(self):
        w = self._no_clause_world()
        specs = pass_specs()
        specs[0]["clause"] = ""
        specs[0]["word"] = "UNJUDGEABLE"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-45", IE_WORDINGS["IE-45"].format(label="A1", id="C-001", slot="clause"))


if __name__ == "__main__":
    unittest.main()
