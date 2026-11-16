import unittest
from helpers import ThreeChecksCase, ART_DIGEST

VALID = [
    ("exists", {"kind": "exists"}),
    ("sha256_equals", {"kind": "sha256_equals", "sha256": ART_DIGEST}),
    ("contains_line", {"kind": "contains_line", "line": "hello artifact"}),
    ("first_line_equals", {"kind": "first_line_equals", "line": "hello artifact"}),
    ("line_count_at_least", {"kind": "line_count_at_least", "count": 1}),
    ("line_count_at_most", {"kind": "line_count_at_most", "count": 5}),
    ("byte_size_at_most", {"kind": "byte_size_at_most", "count": 100}),
]
MISSING = [
    ("sha256_equals_missing_sha256", {"kind": "sha256_equals"}, "sha256"),
    ("contains_line_missing_line", {"kind": "contains_line"}, "line"),
    ("first_line_equals_missing_line", {"kind": "first_line_equals"}, "line"),
    ("line_count_at_least_missing_count", {"kind": "line_count_at_least"}, "count"),
    ("line_count_at_most_missing_count", {"kind": "line_count_at_most"}, "count"),
    ("byte_size_at_most_missing_count", {"kind": "byte_size_at_most"}, "count"),
]
EXTRA = [
    ("exists_with_line", {"kind": "exists", "line": "x"}),
    ("exists_with_count", {"kind": "exists", "count": 1}),
    ("exists_with_sha256", {"kind": "exists", "sha256": ART_DIGEST}),
    ("sha256_equals_with_line", {"kind": "sha256_equals", "sha256": ART_DIGEST, "line": "x"}),
    ("contains_line_with_count", {"kind": "contains_line", "line": "x", "count": 1}),
    ("line_count_with_line", {"kind": "line_count_at_least", "count": 1, "line": "x"}),
    ("byte_size_with_sha256", {"kind": "byte_size_at_most", "count": 1, "sha256": ART_DIGEST}),
    ("sha256_equals_with_count", {"kind": "sha256_equals", "sha256": ART_DIGEST, "count": 1}),
    ("contains_line_with_sha256", {"kind": "contains_line", "line": "x", "sha256": ART_DIGEST}),
    ("first_line_equals_with_count", {"kind": "first_line_equals", "line": "x", "count": 1}),
    ("first_line_equals_with_sha256", {"kind": "first_line_equals", "line": "x", "sha256": ART_DIGEST}),
    ("line_count_at_least_with_sha256", {"kind": "line_count_at_least", "count": 1, "sha256": ART_DIGEST}),
    ("line_count_at_most_with_line", {"kind": "line_count_at_most", "count": 1, "line": "x"}),
    ("line_count_at_most_with_sha256", {"kind": "line_count_at_most", "count": 1, "sha256": ART_DIGEST}),
    ("byte_size_with_line", {"kind": "byte_size_at_most", "count": 1, "line": "x"}),
]


class TestT06PropertyValidation(ThreeChecksCase):
    def with_property(self, prop):
        def mut(b):
            b["layout"]["required_artifacts"][0]["properties"] = [prop]
        return self.mutate(mut)


for name, prop in VALID:
    def make(prop=prop):
        def test(self):
            r = self.run_bundle(self.with_property(prop))
            self.assertEqual(r.exit_status, 0, r.stderr)
        return test
    setattr(TestT06PropertyValidation, "test_valid_" + name, make())

for name, prop, field in MISSING:
    def make(prop=prop, field=field):
        def test(self):
            r = self.run_bundle(self.with_property(prop))
            self.assertEqual(r.exit_status, 2, r.stderr)
            self.assertIn("properties.0." + field, r.stderr)
        return test
    setattr(TestT06PropertyValidation, "test_missing_" + name, make())

for name, prop in EXTRA:
    def make(prop=prop):
        def test(self):
            r = self.run_bundle(self.with_property(prop))
            self.assertEqual(r.exit_status, 2, r.stderr)
            self.assertIn("properties.0", r.stderr)
        return test
    setattr(TestT06PropertyValidation, "test_extra_" + name, make())


class TestT06Unsupported(ThreeChecksCase):
    def test_unsupported_well_typed_passes_validation_fails_check(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "bogus-kind", "line": "x", "count": 1, "sha256": ART_DIGEST}]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 1, r.stderr)
        self.assert_entry(r, "COMP-UNSUPPORTED-PROPERTY", subject="A1", check="completeness")

    def test_unsupported_wrongly_typed_is_validation_error(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "bogus-kind", "count": "x"}]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2, r.stderr)
        self.assertIn("properties.0.count must be integer", r.stderr)

    def test_kind_not_a_string_is_type_error(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["properties"] = [{"kind": 7}]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2, r.stderr)
        self.assertIn("properties.0.kind must be string", r.stderr)
        self.assertNotIn("outside its allowed set", r.stderr)


if __name__ == "__main__":
    unittest.main()
