"""T10, barred runs. Brief sections 2 and 7; plan part 5.5."""

import unittest

from rcg_common import (
    RcgTestCase, assert_outcome_line, assert_no_files, pass_specs,
    JUDGE, AUTHOR, RULER, COORDINATOR, PANEL,
)


class TestBarredWorksheet(RcgTestCase):
    def _barred(self, **over):
        w = self.world()
        p = w.run("worksheet", context="stated", **over)
        self.assertEqual(p.returncode, 6, p.stderr)
        return w

    def test_judge_is_author(self):
        w = self._barred(judge=AUTHOR)
        text = w.read_out1()
        assert_outcome_line(self, text, "barred")
        self.assertIn("bar: %s is the wording author" % AUTHOR, text)
        self.assertIn("filing: no trace verdict, filed by reference with the outcome name barred", text)
        self.assertIn("no verdicts were issued and no gate outcome stands", text)
        self.assertIn("exit status: 6", text)
        self.assertFalse(w.out2.exists())

    def test_judge_is_ruler(self):
        w = self._barred(judge=RULER)
        self.assertIn("bar: %s is the ruler of the step" % RULER, w.read_out1())

    def test_judge_is_coordinator(self):
        w = self._barred(judge=COORDINATOR)
        self.assertIn("bar: %s is the coordinator of the step" % COORDINATOR, w.read_out1())

    def test_panel_judge_in_roster_only_not_barred(self):
        w = self.world()
        p = w.run("worksheet", context="stated", panel=[AUTHOR])
        self.assertEqual(p.returncode, 10, p.stderr)


class TestBarredFinalise(RcgTestCase):
    def test_verdict_judge_is_author(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = AUTHOR
        w.write_verdicts(specs, panel=[AUTHOR], judge_of_record=JUDGE)
        p = w.run("finalise", context="stated", panel=[AUTHOR])
        self.assertEqual(p.returncode, 6, p.stderr)
        text = w.read_out1()
        self.assertIn("bar: %s is the wording author" % AUTHOR, text)
        self.assertFalse(w.out2.exists())

    def test_verdict_judge_is_ruler(self):
        w = self.world()
        specs = pass_specs()
        specs[1]["judge"] = RULER
        w.write_verdicts(specs, panel=[RULER])
        p = w.run("finalise", context="stated", panel=[RULER])
        self.assertEqual(p.returncode, 6, p.stderr)
        self.assertIn("bar: %s is the ruler of the step" % RULER, w.read_out1())

    def test_verdict_judge_is_coordinator(self):
        w = self.world()
        specs = pass_specs()
        specs[2]["judge"] = COORDINATOR
        w.write_verdicts(specs, panel=[COORDINATOR])
        p = w.run("finalise", context="stated", panel=[COORDINATOR])
        self.assertEqual(p.returncode, 6, p.stderr)
        self.assertIn("bar: %s is the coordinator of the step" % COORDINATOR, w.read_out1())

    def test_panel_judge_who_gives_verdict_bars(self):
        w = self.world()
        specs = pass_specs()
        for s in specs:
            s["judge"] = AUTHOR
        w.write_verdicts(specs, panel=[AUTHOR])
        p = w.run("finalise", context="stated", panel=[AUTHOR])
        self.assertEqual(p.returncode, 6, p.stderr)
        text = w.read_out1()
        assert_outcome_line(self, text, "barred")
        self.assertIn("bar: %s is the wording author" % AUTHOR, text)
        self.assertFalse(w.out2.exists())

    def test_panel_roster_only_judge_not_barred_finalise(self):
        w = self.world()
        w.write_verdicts(pass_specs(), panel=[AUTHOR])
        p = w.run("finalise", context="stated", panel=[AUTHOR])
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_several_bars_report_order(self):
        w = self.world()
        p = w.run("worksheet", context="stated", judge=AUTHOR, author=AUTHOR, ruler=AUTHOR, coordinator=AUTHOR)
        self.assertEqual(p.returncode, 6, p.stderr)
        text = w.read_out1()
        a = text.index("is the wording author")
        b = text.index("is the ruler of the step")
        c = text.index("is the coordinator of the step")
        self.assertLess(a, b)
        self.assertLess(b, c)


class TestRemainingNotBarred(RcgTestCase):
    def test_remaining_with_judge_as_author(self):
        w = self.world()
        w.write_verdicts([], judge_of_record=AUTHOR)
        p = w.run("remaining", context="stated", judge=AUTHOR)
        self.assertEqual(p.returncode, 9, p.stderr)
        self.assertNotIn("barred", w.read_out1().splitlines()[1] if len(w.read_out1().splitlines()) > 1 else "")


if __name__ == "__main__":
    unittest.main()
