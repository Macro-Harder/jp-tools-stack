import json
import unittest
from helpers import ThreeChecksCase, base_bundle

PREFIX = "three-checks: input error: "


def cases():
    def boolean_int(b):
        b["spawn_records"]["records"][0]["depth"] = True
    def float_int(b):
        b["spawn_records"]["records"][0]["depth"] = 1.5
    def float_digest(b):
        b["layout"]["required_artifacts"][0]["sha256"] = 1.5
    def int_string(b):
        b["layout"]["stage_id"] = 7
    def null_string(b):
        b["layout"]["stage_id"] = None
    return [
        ("boolean_where_integer", boolean_int, "spawn_records.records.0.depth must be integer"),
        ("float_where_integer", float_int, "spawn_records.records.0.depth must be integer"),
        ("float_where_digest", float_digest, "layout.required_artifacts.0.sha256 must be string"),
        ("integer_where_string", int_string, "layout.stage_id must be string"),
        ("null_where_string_not_allowed", null_string, "layout.stage_id must be string"),
    ]


class TestT03ScalarKinds(ThreeChecksCase):
    def test_null_agent_type_allowed(self):
        result = self.run_bundle()
        self.assertEqual(result.exit_status, 0, result.stderr)

    def test_null_gate_context_allowed(self):
        result = self.run_bundle()
        self.assertEqual(result.exit_status, 0, result.stderr)

    def test_null_push_link_allowed(self):
        result = self.run_bundle()
        self.assertEqual(result.exit_status, 0, result.stderr)

    def test_overflow_float_where_integer_raw_bytes(self):
        # Written as raw bundle bytes carrying the literal text 1e999, bypassing
        # json.dump, so the parser produces a float and field validation is reached.
        # json.dump would serialise the Python float infinity as the token Infinity,
        # which the JSON validity gate must reject before field validation.
        raw = json.dumps(base_bundle())
        raw = raw.replace('"depth": 0', '"depth": 1e999', 1)
        result = self.run_bundle(bundle_bytes=raw.encode("utf-8"))
        self.assertEqual(result.exit_status, 2)
        self.assertIn(PREFIX + "spawn_records.records.0.depth must be integer", result.stderr)
        self.assert_no_file(result.report_path)
        self.assert_no_file(result.results_path)

    def test_surrogate_in_value_is_gate_failure(self):
        result = self.run_bundle(bundle_bytes=b'{"layout": "\\ud800"}')
        self.assertEqual(result.exit_status, 2)
        lines = [line for line in result.stderr.strip().splitlines() if line]
        self.assertEqual(lines, [PREFIX + "the bundle file is not valid JSON"])

    def test_surrogate_in_field_name_is_gate_failure(self):
        result = self.run_bundle(bundle_bytes=b'{"lay\\ud800out": {}}')
        self.assertEqual(result.exit_status, 2)
        lines = [line for line in result.stderr.strip().splitlines() if line]
        self.assertEqual(lines, [PREFIX + "the bundle file is not valid JSON"])


for name, mutator, expected in cases():
    def make(mutator=mutator, expected=expected):
        def test(self):
            bundle = self.mutate(mutator)
            result = self.run_bundle(bundle)
            self.assertEqual(result.exit_status, 2)
            self.assertIn(PREFIX + expected, result.stderr)
            self.assert_no_file(result.report_path)
            self.assert_no_file(result.results_path)
        return test
    setattr(TestT03ScalarKinds, "test_case_" + name, make())

if __name__ == "__main__":
    unittest.main()
