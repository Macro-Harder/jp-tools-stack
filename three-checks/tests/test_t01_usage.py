import os
import unittest
from helpers import ThreeChecksCase, USAGE_LINE, VERIFIER


class TestT01Usage(ThreeChecksCase):
    def invoke(self, argv):
        result = self.run_argv(argv)
        return result

    def check_usage(self, argv, expected_text):
        proc = self.invoke(argv)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("three-checks: usage error: " + expected_text, proc.stderr)
        self.assertIn(USAGE_LINE, proc.stderr)
        # The output positions of the invocation are real paths passed to the
        # program (positions 1 to 3, where the invocation carries them); a
        # usage error must create none of them.
        for path in argv[1:4]:
            if path.startswith("--"):
                continue
            self.assertFalse(os.path.exists(path), "usage error created output file: " + path)

    def test_correct_invocation_shape(self):
        result = self.run_bundle()
        self.assertEqual(result.exit_status, 0, result.stderr)

    def test_missing_bundle_argument(self):
        self.check_usage([], "missing argument BUNDLE")

    def test_missing_report_argument(self):
        self.check_usage(["b.json"], "missing argument REPORT")

    def test_missing_results_argument(self):
        self.check_usage(["b.json", "r.txt"], "missing argument RESULTS")

    def test_missing_closure_argument(self):
        self.check_usage(["b.json", "r.txt", "res.json"], "missing argument CLOSURE")

    def test_extra_argument(self):
        self.check_usage(["b.json", "r.txt", "res.json", "c.txt", "--verifier", VERIFIER, "extra"], "unexpected argument extra")

    def test_unknown_flag(self):
        self.check_usage(["b.json", "r.txt", "res.json", "c.txt", "--bogus", "x"], "unknown flag --bogus")

    def test_missing_verifier_value(self):
        self.check_usage(["b.json", "r.txt", "res.json", "c.txt", "--verifier"], "missing value for --verifier")

    def test_verifier_flag_given_twice(self):
        proc = self.invoke(["b.json", "r.txt", "res.json", "c.txt", "--verifier", VERIFIER, "--verifier", VERIFIER])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("three-checks: usage error:", proc.stderr)
        self.assertIn(USAGE_LINE, proc.stderr)

    def test_output_resolving_to_bundle(self):
        import tempfile, json
        from helpers import base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle = os.path.join(workdir, "bundle.json")
            with open(bundle, "w") as handle:
                json.dump(base_bundle(), handle)
            proc = self.run_argv([bundle, bundle, os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", VERIFIER])
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: usage error: output path " + bundle + " names an input file", proc.stderr)
            self.assertIn(USAGE_LINE, proc.stderr)

    def test_two_outputs_same_file(self):
        import tempfile, json
        from helpers import base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle = os.path.join(workdir, "bundle.json")
            with open(bundle, "w") as handle:
                json.dump(base_bundle(), handle)
            same = os.path.join(workdir, "same.txt")
            proc = self.run_argv([bundle, same, same, os.path.join(workdir, "c.txt"), "--verifier", VERIFIER])
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: usage error: output paths " + same + " and " + same + " name the same file", proc.stderr)
            self.assertIn(USAGE_LINE, proc.stderr)

    def test_output_resolving_to_artifact(self):
        result = None
        import tempfile, json
        from helpers import base_bundle, ART_TEXT
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle = os.path.join(workdir, "bundle.json")
            with open(bundle, "w") as handle:
                json.dump(base_bundle(), handle)
            art = os.path.join(workdir, "artifact1.txt")
            with open(art, "w") as handle:
                handle.write(ART_TEXT)
            proc = self.run_argv([bundle, art, os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", VERIFIER])
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: usage error: output path " + art + " names an input file", proc.stderr)
            self.assertIn(USAGE_LINE, proc.stderr)

    def test_output_through_symlink_to_bundle(self):
        import tempfile, json
        from helpers import base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle = os.path.join(workdir, "bundle.json")
            with open(bundle, "w") as handle:
                json.dump(base_bundle(), handle)
            link = os.path.join(workdir, "link.json")
            os.symlink(bundle, link)
            proc = self.run_argv([bundle, link, os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", VERIFIER])
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: usage error: output path " + link + " names an input file", proc.stderr)
            self.assertIn(USAGE_LINE, proc.stderr)

    def test_output_parent_symlink_to_bundle_dir(self):
        import tempfile, json
        from helpers import base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle = os.path.join(workdir, "bundle.json")
            with open(bundle, "w") as handle:
                json.dump(base_bundle(), handle)
            alias = os.path.join(workdir, "alias")
            os.symlink(workdir, alias)
            out = os.path.join(alias, "bundle.json")
            proc = self.run_argv([bundle, out, os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", VERIFIER])
            self.assertEqual(proc.returncode, 2)
            self.assertIn("three-checks: usage error: output path " + out + " names an input file", proc.stderr)
            self.assertIn(USAGE_LINE, proc.stderr)

    def test_usage_creates_no_output_file(self):
        import tempfile
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            report = os.path.join(workdir, "r.txt")
            results = os.path.join(workdir, "res.json")
            closure = os.path.join(workdir, "c.txt")
            proc = self.run_argv(["b.json", report, results, closure, "--verifier", VERIFIER, "extra"])
            self.assertEqual(proc.returncode, 2)
            self.assertFalse(os.path.exists(report))
            self.assertFalse(os.path.exists(results))
            self.assertFalse(os.path.exists(closure))


if __name__ == "__main__":
    unittest.main()
