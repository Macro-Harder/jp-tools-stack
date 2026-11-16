import json
import os
import unittest
from helpers import ThreeChecksCase, base_bundle

PREFIX = "three-checks: input error: "


class TestT02ReadingGates(ThreeChecksCase):
    def raw(self, data):
        return self.run_bundle(bundle_bytes=data if isinstance(data, bytes) else data.encode("utf-8"))

    def test_unreadable_missing_file(self):
        self.require_program()
        import subprocess, sys
        from helpers import PROGRAM
        proc = subprocess.run([sys.executable, PROGRAM, "/nonexistent-dir/bundle.json", "/tmp/r.txt", "/tmp/res.json", "/tmp/c.txt", "--verifier", "v"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(PREFIX + "cannot read the bundle file", proc.stderr)

    def test_unreadable_directory_path(self):
        self.require_program()
        import subprocess, sys, tempfile
        from helpers import PROGRAM
        with tempfile.TemporaryDirectory() as workdir:
            proc = subprocess.run([sys.executable, PROGRAM, workdir, "/tmp/r.txt", "/tmp/res.json", "/tmp/c.txt", "--verifier", "v"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn(PREFIX + "cannot read the bundle file", proc.stderr)

    def test_exactly_limit_passes_size_gate(self):
        bundle = json.dumps(base_bundle()).encode("utf-8")
        padded = bundle + b" " * (2000000 - len(bundle))
        self.assertEqual(len(padded), 2000000)
        result = self.raw(padded)
        self.assertNotIn("over the limit", result.stderr)
        self.assertEqual(result.exit_status, 0, result.stderr)
        self.assertTrue(os.path.isfile(result.report_path))
        self.assertTrue(os.path.isfile(result.results_path))

    def test_one_over_limit_fails(self):
        data = b"x" * 2000001
        result = self.raw(data)
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle file is 2000001 bytes, over the limit of 2000000 bytes", result.stderr)

    def test_not_utf8(self):
        result = self.raw(b"\xff\xfe{}")
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle file is not UTF-8 text without a byte order mark", result.stderr)

    def test_byte_order_mark(self):
        result = self.raw(b"\xef\xbb\xbf{}")
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle file is not UTF-8 text without a byte order mark", result.stderr)

    def test_valid_utf8_not_json(self):
        result = self.raw("this is not json")
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle file is not valid JSON", result.stderr)

    def test_nan_token(self):
        result = self.raw('{"layout": NaN}')
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle file is not valid JSON", result.stderr)

    def test_infinity_token(self):
        result = self.raw('{"layout": Infinity}')
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle file is not valid JSON", result.stderr)

    def test_negative_infinity_token(self):
        result = self.raw('{"layout": -Infinity}')
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle file is not valid JSON", result.stderr)

    def test_deep_nesting_objects_depth_10000(self):
        data = ('{"a":' * 10000) + "1" + ("}" * 10000)
        result = self.raw(data)
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle file is not valid JSON", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_top_level_list(self):
        result = self.raw("[1, 2]")
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle top level is not an object", result.stderr)

    def test_top_level_string(self):
        result = self.raw('"hello"')
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle top level is not an object", result.stderr)

    def test_top_level_null(self):
        result = self.raw("null")
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "the bundle top level is not an object", result.stderr)

    def test_first_failure_only_size_over_invalid_json(self):
        data = b"not json " + b"x" * 2000001
        result = self.raw(data)
        lines = [line for line in result.stderr.strip().splitlines() if line]
        self.assertEqual(len(lines), 1)
        self.assertIn("over the limit", lines[0])


if __name__ == "__main__":
    unittest.main()
