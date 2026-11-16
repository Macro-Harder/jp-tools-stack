"""T8, self test. Brief section 6; plan parts 1.2, 4.8, and 5.5."""

import subprocess
import sys
import unittest
from pathlib import Path

from rcg_common import (
    RcgTestCase, PROBE_NAMES, SELF_TEST_RECORD_LINE, TESTS_DIR, pass_specs,
    assert_outcome_line,
)


class TestProbesPass(RcgTestCase):
    def test_probes_pass_in_worksheet_summary(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        for name in PROBE_NAMES:
            self.assertIn("probe %s: pass" % name, text)
        self.assertIn(SELF_TEST_RECORD_LINE, text)

    def test_probes_pass_in_finalise_record(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        self.assertIn("self test", text)
        for name in PROBE_NAMES:
            self.assertIn("probe %s: pass" % name, text)
        self.assertIn("self test results are counted separately from corpus checks", text)
        data = w.read_results()
        self.assertEqual([pr["name"] for pr in data["self_test"]["probes"]], PROBE_NAMES)
        self.assertTrue(all(pr["result"] == "pass" for pr in data["self_test"]["probes"]))
        self.assertTrue(data["self_test"]["counted_separately"])


class TestFaultInjectionSeam(RcgTestCase):
    def _drive(self, w, probe):
        args_file = w.dir / "seam_args.txt"
        result_file = w.dir / "seam_result.txt"
        args_file.write_text("\n".join(w.args("worksheet", context="stated")) + "\n")
        proc = subprocess.run(
            [sys.executable, str(TESTS_DIR / "selftest_driver.py"), probe,
             str(args_file), str(result_file)],
            capture_output=True, text=True, timeout=120)
        return proc, result_file

    def test_forced_probe_failure_writes_self_test_report_status_8(self):
        w = self.world()
        proc, result_file = self._drive(w, "blocking_probe")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(result_file.read_text().splitlines()[0], "8")
        text = w.read_out1()
        assert_outcome_line(self, text, "self test failure")
        self.assertIn("probe blocking_probe: fail, forced by the test seam", text)
        self.assertIn("probe selection_probe: pass", text)
        self.assertIn(SELF_TEST_RECORD_LINE, text)
        self.assertIn("exit status: 8", text)
        self.assertFalse(w.out2.exists())

    def test_forced_probe_failure_at_finalise(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        args_file = w.dir / "seam_args.txt"
        result_file = w.dir / "seam_result.txt"
        args_file.write_text("\n".join(w.args("finalise", context="stated")) + "\n")
        proc = subprocess.run(
            [sys.executable, str(TESTS_DIR / "selftest_driver.py"), "selection_probe",
             str(args_file), str(result_file)],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(result_file.read_text().splitlines()[0], "8")
        self.assertIn("probe selection_probe: fail, forced by the test seam", w.read_out1())
        self.assertFalse(w.out2.exists())

    def test_no_command_line_route_to_seam(self):
        w = self.world()
        p = w.run("worksheet", context="stated", extra=["--force-probe-failure", "blocking_probe"])
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("usage error: ", p.stderr)

    def test_no_environment_route_to_seam(self):
        w = self.world()
        from rcg_common import run_program
        p = run_program(w.args("worksheet", context="stated"),
                        env_extra={"RCG_FORCE_PROBE_FAILURE": "blocking_probe"})
        self.assertEqual(p.returncode, 10, p.stderr)


class TestRemainingRunsNoSelfTest(RcgTestCase):
    def test_remaining_report_has_no_self_test_summary(self):
        w = self.world()
        w.write_verdicts([])
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 9, p.stderr)
        text = w.read_out1()
        self.assertNotIn("probe selection_probe", text)
        self.assertNotIn(SELF_TEST_RECORD_LINE, text)


if __name__ == "__main__":
    unittest.main()
