"""T18, limits and never do rules. Brief sections 11 and 12; plan parts 4 and 5.7."""

import unittest
from pathlib import Path

from rcg_common import (
    RcgTestCase, pass_specs, LIMIT_LINES_FIXED, JUDGE,
)


def snapshot(directory):
    return {str(p.relative_to(directory)): p.read_bytes() for p in Path(directory).rglob("*") if p.is_file()}


class TestNeverDo(RcgTestCase):
    def _run_and_check_inputs_untouched(self, form, prepare=None):
        w = self.world()
        if prepare:
            prepare(w)
        before = snapshot(w.dir)
        p = w.run(form, context="stated")
        after = snapshot(w.dir)
        for name, data in before.items():
            self.assertEqual(after.get(name), data, "input file changed: %s" % name)
        named = {str(w.out1), str(w.out2)}
        for path in after:
            full = str(w.dir / path)
            if full not in named and path not in before:
                self.fail("run wrote to an unnamed path: %s" % full)
        return w, p

    def test_worksheet_writes_only_named_outputs(self):
        w, p = self._run_and_check_inputs_untouched("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)

    def test_finalise_writes_only_named_outputs(self):
        def prep(w):
            w.write_verdicts(pass_specs())
        w, p = self._run_and_check_inputs_untouched("finalise", prep)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_remaining_writes_only_named_outputs(self):
        def prep(w):
            w.write_verdicts(pass_specs()[:1])
        w, p = self._run_and_check_inputs_untouched("remaining", prep)
        self.assertEqual(p.returncode, 9, p.stderr)

    def test_no_record_claims_reading_happened(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        self.assertIn("reader designate: Reader Seat.", text)
        self.assertIn("it does not record that the reading has happened", text)
        self.assertNotIn("the reader has read this record", text)

    def test_no_record_claims_oversight_happened(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        self.assertIn("does not record that the oversight or the reading has happened", text)

    def test_seven_standing_limit_lines_in_every_record(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        data = w.read_results()
        for line in LIMIT_LINES_FIXED:
            self.assertIn(line, text)
            self.assertIn(line, data["limits"])

    def test_limits_present_in_incomplete_record(self):
        w = self.world()
        w.write_verdicts(pass_specs()[:1])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        text = w.read_out1()
        for line in LIMIT_LINES_FIXED:
            self.assertIn(line, text)

    def test_no_flag_presented_as_verdict(self):
        w = self.world()
        from rcg_common import DEFAULT_ROWS
        rows = [dict(r) for r in DEFAULT_ROWS]
        rows[0]["incident"] = ""
        rows[0]["test"] = "An implementation that permits  fails"
        w.set_corpus(rows)
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("flagged: only UNJUDGEABLE may be entered for this row", text)
        self.assertNotIn("verdict: PASS", text)
        self.assertNotIn("verdict: FAIL", text)

    def test_no_softening_for_cost_or_time(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 1, p.stderr)
        text = w.read_out1().lower()
        for phrase in ("for cost", "for time", "to save time", "to save cost", "good enough"):
            self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
