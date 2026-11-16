"""T12, flagged rows and panel discipline. Brief sections 4 and 7."""

import unittest

from rcg_common import (
    RcgTestCase, assert_ie, IE_WORDINGS, pass_specs, DEFAULT_ROWS,
    NO_CLAUSE_STATEMENT, CLAUSE_A,
)


def flagged_world(tc, mutate):
    w = tc.world()
    rows = [dict(r) for r in DEFAULT_ROWS]
    mutate(rows)
    w.set_corpus(rows)
    return w


def empty_cell(rows):
    rows[0]["incident"] = ""
    rows[0]["test"] = "An implementation that permits  fails"


class TestFlaggedVerdicts(RcgTestCase):
    def test_flagged_unjudgeable_stands(self):
        w = flagged_world(self, empty_cell)
        specs = pass_specs()
        specs[0]["word"] = "UNJUDGEABLE"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 4, p.stderr)
        data = w.read_results()
        self.assertEqual(data["outcome"], "unverifiable")
        self.assertEqual(data["counts"]["unjudgeable"], 1)

    def test_flagged_pass_refused_ie36(self):
        w = flagged_world(self, empty_cell)
        specs = pass_specs()
        specs[0]["word"] = "PASS"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-36", IE_WORDINGS["IE-36"].format(label="A1", id="C-001", word="PASS"))

    def test_flagged_fail_refused_ie36(self):
        w = flagged_world(self, empty_cell)
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        assert_ie(self, p, "IE-36", IE_WORDINGS["IE-36"].format(label="A1", id="C-001", word="FAIL"))

    def test_flagged_no_verdict_counts_missing(self):
        w = flagged_world(self, empty_cell)
        specs = [s for s in pass_specs() if s["id"] != "C-001"]
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        data = w.read_results()
        self.assertEqual(data["counts"]["missing"], 1)
        self.assertEqual(data["missing"], [{"item": "A1", "corpus_id": "C-001"}])


class TestNoClauseFlaggedShapes(RcgTestCase):
    def _run_shape(self, proc, word, clause):
        def mutate(rows):
            rows[0]["proc"] = proc
        w = flagged_world(self, mutate)
        specs = pass_specs()
        specs[0]["word"] = word
        specs[0]["clause"] = clause
        w.write_verdicts(specs)
        return w, w.run("finalise", context="stated")

    def test_no_separator_shape_unjudgeable_unverifiable(self):
        w, p = self._run_shape("Inspect the amendment for the named shape.", "UNJUDGEABLE", NO_CLAUSE_STATEMENT)
        self.assertEqual(p.returncode, 4, p.stderr)

    def test_degenerate_shape_unjudgeable_unverifiable(self):
        w, p = self._run_shape("Inspect the amendment; fail if", "UNJUDGEABLE", NO_CLAUSE_STATEMENT)
        self.assertEqual(p.returncode, 4, p.stderr)

    def test_no_separator_shape_empty_clause_ie45(self):
        w, p = self._run_shape("Inspect the amendment for the named shape.", "UNJUDGEABLE", "")
        assert_ie(self, p, "IE-45", IE_WORDINGS["IE-45"].format(label="A1", id="C-001", slot="clause"))

    def test_no_separator_shape_other_clause_ie53(self):
        w, p = self._run_shape("Inspect the amendment for the named shape.", "UNJUDGEABLE", CLAUSE_A)
        assert_ie(self, p, "IE-53", IE_WORDINGS["IE-53"].format(label="A1", id="C-001"))


class TestPanelDiscipline(RcgTestCase):
    def test_second_verdict_from_different_judge_is_duplicate(self):
        w = self.world()
        specs = pass_specs()
        dup = dict(specs[0])
        from rcg_common import PANEL
        dup["judge"] = PANEL
        specs.append(dup)
        w.write_verdicts(specs, panel=[PANEL])
        p = w.run("finalise", context="stated", panel=[PANEL])
        assert_ie(self, p, "IE-33", IE_WORDINGS["IE-33"].format(label="A1", id="C-001"))

    def test_paired_rows_disagreeing_verdicts_both_stand(self):
        w = self.world()
        spec = [("A1", ["Gap 3", "Gap 4"], {"Gap 3": "Basis one.", "Gap 4": "Basis two."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        specs = [
            {"label": "A1", "id": "C-005", "word": "PASS"},
            {"label": "A1", "id": "C-006", "word": "FAIL"},
            {"label": "A2", "id": "C-002", "word": "PASS"},
        ]
        w.write_verdicts(specs, checked_ids=["C-002", "C-005", "C-006"])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 1, p.stderr)
        data = w.read_results()
        item = [i for i in data["items"] if i["label"] == "A1"][0]
        self.assertEqual(item["outcome"], "fail")
        words = {v["corpus_id"]: v["word"] for v in item["verdicts"]}
        self.assertEqual(words, {"C-005": "PASS", "C-006": "FAIL"})


if __name__ == "__main__":
    unittest.main()
