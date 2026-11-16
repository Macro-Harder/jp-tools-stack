"""T15, outcomes, exit statuses, and the output matrix. Brief sections 9 and 10; plan parts 1.1 and 5."""

import unittest

from rcg_common import (
    RcgTestCase, pass_specs, assert_no_files, STATUS_TABLE, JUDGE, AUTHOR,
)


class TestEveryStatus(RcgTestCase):
    def test_status_0_pass(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(w.read_results()["outcome"], "pass")
        self.assertTrue(w.out1.exists() and w.out2.exists())

    def test_status_1_fail(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 1)
        self.assertTrue(w.out1.exists() and w.out2.exists())

    def test_status_2_input_error_writes_nothing_each_form(self):
        from rcg_common import IE_WORDINGS
        for form in ("worksheet", "remaining", "finalise"):
            w = self.world()
            w.corpus.unlink()
            p = w.run(form, context="stated")
            self.assertEqual(p.returncode, 2, form)
            self.assertIn("input error IE-04: " + IE_WORDINGS["IE-04"].format(kind="corpus", path=str(w.corpus)), p.stderr)
            assert_no_files(self, w.out1, w.out2)

    def test_status_3_incomplete(self):
        w = self.world()
        w.write_verdicts(pass_specs()[:2])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3)
        self.assertTrue(w.out1.exists() and w.out2.exists())

    def test_status_4_unverifiable(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "UNJUDGEABLE"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 4)

    def test_status_5_re_ruled_pass(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        specs[0]["claim"] = {"queue_item": "DQ-101", "ruling_date": "2026-11-01", "confirming_judge": JUDGE}
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 5)

    def test_status_6_barred_writes_only_report(self):
        w = self.world()
        p = w.run("worksheet", context="stated", judge=AUTHOR)
        self.assertEqual(p.returncode, 6)
        self.assertTrue(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_status_7_declaration_conflict(self):
        w = self.world()
        w.set_amendment([("A1", "The wording names Gap 7 plainly."),
                         ("A2", "The amendment changes the counting text.")])
        from rcg_common import default_spec
        w.set_declaration(default_spec())
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 7)
        self.assertFalse(w.out2.exists())

    def test_status_9_remaining_report(self):
        w = self.world()
        w.write_verdicts(pass_specs()[:1])
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 9)
        self.assertTrue(w.out1.exists())

    def test_status_10_worksheet_issuance(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10)
        self.assertTrue(w.out1.exists() and w.out2.exists())

    def test_status_0_never_for_remaining_or_worksheet(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 9, p.stderr)
        self.assertNotEqual(p.returncode, 0)
        w2 = self.world()
        p2 = w2.run("worksheet", context="stated")
        self.assertEqual(p2.returncode, 10, p2.stderr)
        self.assertNotEqual(p2.returncode, 0)


class TestFilingMapping(RcgTestCase):
    def _record(self, mutate=None, queue=False):
        w = self.world()
        specs = pass_specs()
        if mutate:
            mutate(specs)
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated", queue=queue)
        return w, p

    def test_pass_files_as_pass(self):
        w, p = self._record()
        self.assertIn("filing: PASS", w.read_out1())
        self.assertEqual(w.read_results()["trace_word"], "PASS")

    def test_fail_files_as_fail_rejected(self):
        w, p = self._record(lambda s: s[0].update(word="FAIL"))
        self.assertIn("filing: FAIL rejected", w.read_out1())
        self.assertEqual(w.read_results()["trace_word"], "FAIL rejected")

    def test_re_ruled_pass_files_as_re_ruled(self):
        def m(s):
            s[0].update(word="FAIL", claim={"queue_item": "DQ-101", "ruling_date": "2026-11-01", "confirming_judge": JUDGE})
        w, p = self._record(m, queue=True)
        self.assertIn("filing: RE-RULED", w.read_out1())
        self.assertEqual(w.read_results()["trace_word"], "RE-RULED")

    def test_unverifiable_files_no_trace_word(self):
        w, p = self._record(lambda s: s[0].update(word="UNJUDGEABLE"))
        self.assertIn("filing: no trace verdict, filed by reference with the outcome name unverifiable", w.read_out1())
        self.assertIsNone(w.read_results()["trace_word"])

    def test_incomplete_files_no_trace_word(self):
        w = self.world()
        w.write_verdicts(pass_specs()[:1])
        p = w.run("finalise", context="stated")
        self.assertIn("filing: no trace verdict, filed by reference with the outcome name incomplete", w.read_out1())
        self.assertIsNone(w.read_results()["trace_word"])

    def test_per_row_trace_excerpts(self):
        def m(s):
            s[0].update(word="FAIL", claim={"queue_item": "DQ-101", "ruling_date": "2026-11-01", "confirming_judge": JUDGE})
            s[1].update(word="FAIL")
            s[2].update(word="UNJUDGEABLE")
        w, p = self._record(m, queue=True)
        text = w.read_out1()
        self.assertIn("trace excerpt: RE-RULED, queue item DQ-101", text)
        self.assertIn("trace excerpt: FAIL", text)
        self.assertIn("trace excerpt: not judged", text)
        data = w.read_results()
        words = {}
        for item in data["items"]:
            for v in item["verdicts"]:
                words[v["corpus_id"]] = v["trace_excerpt"]["word"]
        self.assertEqual(words["C-001"], "RE-RULED")
        self.assertEqual(words["C-003"], "FAIL")
        self.assertEqual(words["C-002"], "not judged")

    def test_pass_row_trace_excerpt(self):
        w, p = self._record()
        self.assertIn("trace excerpt: PASS", w.read_out1())


class TestOutputMatrix(RcgTestCase):
    def test_barred_leaves_no_results_at_fresh_path(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = AUTHOR
        w.write_verdicts(specs, panel=[AUTHOR], judge_of_record=JUDGE)
        p = w.run("finalise", context="stated", panel=[AUTHOR])
        self.assertEqual(p.returncode, 6)
        self.assertTrue(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_state_reports_write_no_results(self):
        w = self.world()
        w.set_amendment([("A1", "The wording names Gap 7 plainly."),
                         ("A2", "The amendment changes the counting text.")])
        from rcg_common import default_spec
        w.set_declaration(default_spec())
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 7)
        self.assertFalse(w.out2.exists())


if __name__ == "__main__":
    unittest.main()
