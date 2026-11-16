import os
import unittest
from helpers import ThreeChecksCase, STRENGTH_LINE, SCOPE_PARAGRAPH


class TestT22ClosureDelivery(ThreeChecksCase):
    def test_full_pass_closure_record_form(self):
        r = self.run_bundle()
        self.assertEqual(r.exit_status, 0)
        lines = r.closure_text.splitlines()
        self.assertEqual(lines[0], "tool=three-checks")
        self.assertEqual(lines[1], "stage=stage-1")
        self.assertEqual(lines[2], "verifier=verifier-1")
        self.assertTrue(lines[3].startswith("bundle_sha256="))
        self.assertEqual(lines[4], "grade=L2")
        self.assertEqual(lines[5], STRENGTH_LINE)
        self.assertEqual(lines[6], SCOPE_PARAGRAPH)

    def test_failing_run_no_closure_existing_untouched(self):
        def mut(b):
            b["claim"]["ledger_claims"] = ["E9"]
        r = self.run_bundle(self.mutate(mut), preexisting={"closure": "old closure"})
        self.assertNotEqual(r.exit_status, 0)
        with open(r.closure_path) as handle:
            self.assertEqual(handle.read(), "old closure")

    def test_failing_run_replaces_report_and_results(self):
        def mut(b):
            b["claim"]["ledger_claims"] = ["E9"]
        r = self.run_bundle(self.mutate(mut), preexisting={"report": "old report", "results": "old results"})
        self.assertNotEqual(r.report_text, "old report")
        self.assertIsNotNone(r.results)

    def test_delivery_failure_at_results_report_stands(self):
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle, ART_TEXT
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle_path = os.path.join(workdir, "bundle.json")
            with open(bundle_path, "w") as handle:
                json.dump(base_bundle(), handle)
            with open(os.path.join(workdir, "artifact1.txt"), "w") as handle:
                handle.write(ART_TEXT)
            results_dir = os.path.join(workdir, "results-dir")
            os.mkdir(results_dir)
            proc = subprocess.run([sys.executable, PROGRAM, bundle_path, os.path.join(workdir, "report.txt"), results_dir, os.path.join(workdir, "closure.txt"), "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: delivery failure: cannot write " + results_dir, proc.stderr)
            self.assertTrue(os.path.isfile(os.path.join(workdir, "report.txt")))

    def test_delivery_failure_at_report_no_results(self):
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle, ART_TEXT
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle_path = os.path.join(workdir, "bundle.json")
            with open(bundle_path, "w") as handle:
                json.dump(base_bundle(), handle)
            with open(os.path.join(workdir, "artifact1.txt"), "w") as handle:
                handle.write(ART_TEXT)
            report_dir = os.path.join(workdir, "report-dir")
            os.mkdir(report_dir)
            results_path = os.path.join(workdir, "results.json")
            proc = subprocess.run([sys.executable, PROGRAM, bundle_path, report_dir, results_path, os.path.join(workdir, "closure.txt"), "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: delivery failure:", proc.stderr)
            self.assertFalse(os.path.exists(results_path))

    def test_delivery_failure_at_closure_report_results_stand(self):
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle, ART_TEXT
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle_path = os.path.join(workdir, "bundle.json")
            with open(bundle_path, "w") as handle:
                json.dump(base_bundle(), handle)
            with open(os.path.join(workdir, "artifact1.txt"), "w") as handle:
                handle.write(ART_TEXT)
            closure_dir = os.path.join(workdir, "closure-dir")
            os.mkdir(closure_dir)
            proc = subprocess.run([sys.executable, PROGRAM, bundle_path, os.path.join(workdir, "report.txt"), os.path.join(workdir, "results.json"), closure_dir, "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: delivery failure:", proc.stderr)
            self.assertNotIn("input error", proc.stderr)
            self.assertTrue(os.path.isfile(os.path.join(workdir, "report.txt")))
            self.assertTrue(os.path.isfile(os.path.join(workdir, "results.json")))

    def test_delivery_failure_only_at_flush_or_close_full_device(self):
        # The full device path accepts the open and the buffered write, and
        # the failure surfaces only at flush or close. Under condition C-7
        # that is judged as a delivery failure, naming the path, with exit
        # status 2.
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle, ART_TEXT
        self.require_program()
        if not os.path.exists("/dev/full"):
            self.fail("missing fixture device: /dev/full is not present in this environment")
        with tempfile.TemporaryDirectory() as workdir:
            bundle_path = os.path.join(workdir, "bundle.json")
            with open(bundle_path, "w") as handle:
                json.dump(base_bundle(), handle)
            with open(os.path.join(workdir, "artifact1.txt"), "w") as handle:
                handle.write(ART_TEXT)
            results_path = os.path.join(workdir, "results.json")
            proc = subprocess.run([sys.executable, PROGRAM, bundle_path, "/dev/full", results_path, os.path.join(workdir, "closure.txt"), "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: delivery failure: cannot write /dev/full", proc.stderr)
            self.assertFalse(os.path.exists(results_path))

    def test_input_error_writes_nothing(self):
        r = self.run_bundle(bundle_bytes=b"not json")
        self.assertEqual(r.exit_status, 2)
        self.assert_no_file(r.report_path)
        self.assert_no_file(r.results_path)
        self.assert_no_file(r.closure_path)


if __name__ == "__main__":
    unittest.main()
