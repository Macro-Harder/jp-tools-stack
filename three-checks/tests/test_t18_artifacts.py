import hashlib
import os
import unittest
from helpers import ThreeChecksCase, ART_TEXT, ART_DIGEST, FIXTURES

ART_DIR = os.path.join(FIXTURES, "artifacts")


def digest_of(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def bundle_with_artifact(content, properties=None, stated=None, path="artifact1.txt"):
    def mut(b):
        b["layout"]["required_artifacts"][0]["path"] = path
        b["layout"]["required_artifacts"][0]["sha256"] = stated if stated is not None else digest_of(content)
        b["layout"]["required_artifacts"][0]["properties"] = properties or []
        b["links"][0]["subject_artifacts"] = [{"artifact_id": "A1", "sha256": b["layout"]["required_artifacts"][0]["sha256"]}]
    return mut


class TestT18LineDefinition(ThreeChecksCase):
    def run_with(self, content, properties, stated=None):
        bundle = self.mutate(bundle_with_artifact(content, properties, stated))
        return self.run_bundle(bundle, artifacts={"artifact1.txt": content})

    def test_crlf_line_end_excluded(self):
        content = b"alpha\r\nbeta\r\n"
        r = self.run_with(content, [{"kind": "contains_line", "line": "alpha"}, {"kind": "first_line_equals", "line": "alpha"}])
        self.assertEqual(r.results["subresults"]["artifacts"], "pass", repr(r.results))

    def test_trailing_newline_no_empty_final_line(self):
        r = self.run_with("one\ntwo\n", [{"kind": "line_count_at_least", "count": 2}, {"kind": "line_count_at_most", "count": 2}])
        self.assertEqual(r.results["subresults"]["artifacts"], "pass", repr(r.results))

    def test_no_trailing_newline(self):
        r = self.run_with("one\ntwo", [{"kind": "line_count_at_most", "count": 2}])
        self.assertEqual(r.results["subresults"]["artifacts"], "pass", repr(r.results))

    def test_empty_file_zero_lines_no_first_line(self):
        r = self.run_with("", [{"kind": "line_count_at_most", "count": 0}])
        self.assertEqual(r.results["subresults"]["artifacts"], "pass", repr(r.results))
        r2 = self.run_with("", [{"kind": "first_line_equals", "line": "x"}])
        self.assert_entry(r2, "COMP-PROPERTY", subject="A1")

    def test_copied_real_fixtures_traits(self):
        for name in ("copied_brief_excerpt.txt", "copied_plan_excerpt.txt"):
            with open(os.path.join(ART_DIR, name), "rb") as handle:
                data = handle.read()
            self.assertTrue(data.endswith(b"\n"), name)
            self.assertNotIn(b"\r", data, name)
            r = self.run_with(data, [{"kind": "line_count_at_least", "count": 1}])
            self.assertEqual(r.results["subresults"]["artifacts"], "pass", name + repr(r.results))


class TestT18StandingAndCoverage(ThreeChecksCase):
    def test_unreadable_missing_file_one_entry(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["path"] = "missing-artifact.txt"
        r = self.run_bundle(self.mutate(mut), artifacts={})
        entries = [e for e in r.entries("COMP-ARTIFACT") if e["subject"] == "A1"]
        self.assertEqual(len(entries), 1, repr(entries))
        self.assertIn("cannot be read", entries[0]["found"])

    def test_directory_named_as_artifact_unreadable(self):
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            os.mkdir(os.path.join(workdir, "adir"))
            bundle = base_bundle()
            bundle["layout"]["required_artifacts"][0]["path"] = "adir"
            path = os.path.join(workdir, "bundle.json")
            with open(path, "w") as handle:
                json.dump(bundle, handle)
            proc = subprocess.run([sys.executable, PROGRAM, path, os.path.join(workdir, "r.txt"), os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 1)
            data = json.load(open(os.path.join(workdir, "res.json")))
            self.assertTrue(any(e["code"] == "COMP-ARTIFACT" for e in data["discrepancies"]))

    def test_symlink_to_regular_file_read_through(self):
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            target = os.path.join(workdir, "real.txt")
            with open(target, "w") as handle:
                handle.write(ART_TEXT)
            os.symlink(target, os.path.join(workdir, "artifact1.txt"))
            bundle = base_bundle()
            path = os.path.join(workdir, "bundle.json")
            with open(path, "w") as handle:
                json.dump(bundle, handle)
            proc = subprocess.run([sys.executable, PROGRAM, path, os.path.join(workdir, "r.txt"), os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_symlink_to_bundle_file_no_collision_evaluated_normally(self):
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            bundle = base_bundle()
            path = os.path.join(workdir, "bundle.json")
            with open(path, "w") as handle:
                json.dump(bundle, handle)
            bundle_bytes = open(path, "rb").read()
            bundle["layout"]["required_artifacts"][0]["path"] = "selflink.txt"
            bundle["layout"]["required_artifacts"][0]["sha256"] = digest_of(bundle_bytes)
            bundle["links"][0]["subject_artifacts"] = [{"artifact_id": "A1", "sha256": digest_of(bundle_bytes)}]
            with open(path, "w") as handle:
                json.dump(bundle, handle)
            os.symlink(path, os.path.join(workdir, "selflink.txt"))
            proc = subprocess.run([sys.executable, PROGRAM, path, os.path.join(workdir, "r.txt"), os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 2, proc.stderr)

    def test_two_artifact_paths_symlink_same_file_duplicate_error(self):
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            with open(os.path.join(workdir, "artifact1.txt"), "w") as handle:
                handle.write(ART_TEXT)
            os.symlink(os.path.join(workdir, "artifact1.txt"), os.path.join(workdir, "link-to-artifact.txt"))
            bundle = base_bundle()
            entry = dict(bundle["layout"]["required_artifacts"][0])
            entry["artifact_id"] = "A2"
            entry["path"] = "link-to-artifact.txt"
            bundle["layout"]["required_artifacts"].append(entry)
            path = os.path.join(workdir, "bundle.json")
            with open(path, "w") as handle:
                json.dump(bundle, handle)
            proc = subprocess.run([sys.executable, PROGRAM, path, os.path.join(workdir, "r.txt"), os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("layout.required_artifacts", proc.stderr)

    def test_artifact_path_through_symlinked_directory_resolved(self):
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as workdir:
            realdir = os.path.join(workdir, "realdir")
            os.mkdir(realdir)
            with open(os.path.join(realdir, "artifact1.txt"), "w") as handle:
                handle.write(ART_TEXT)
            os.symlink(realdir, os.path.join(workdir, "aliasdir"))
            bundle = base_bundle()
            bundle["layout"]["required_artifacts"][0]["path"] = "aliasdir/artifact1.txt"
            path = os.path.join(workdir, "bundle.json")
            with open(path, "w") as handle:
                json.dump(bundle, handle)
            proc = subprocess.run([sys.executable, PROGRAM, path, os.path.join(workdir, "r.txt"), os.path.join(workdir, "res.json"), os.path.join(workdir, "c.txt"), "--verifier", "verifier-1"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_exactly_limit_passes_size(self):
        content = b"x" * 2000000
        bundle = self.mutate(bundle_with_artifact(content))
        r = self.run_bundle(bundle, artifacts={"artifact1.txt": content})
        self.assertEqual(r.results["subresults"]["artifacts"], "pass", repr(r.results))

    def test_over_limit_fails_with_values(self):
        content = b"x" * 2000001
        bundle = self.mutate(bundle_with_artifact(content))
        r = self.run_bundle(bundle, artifacts={"artifact1.txt": content})
        entry = self.assert_entry(r, "COMP-ARTIFACT", subject="A1")
        self.assertIn("2000001", entry["found"])
        self.assertIn("2000000", entry["found"])

    def test_digest_mismatch_found_names_both_digests(self):
        bundle = self.mutate(bundle_with_artifact(ART_TEXT, stated="c" * 64))
        r = self.run_bundle(bundle, artifacts={"artifact1.txt": ART_TEXT})
        entry = self.assert_entry(r, "COMP-ARTIFACT", subject="A1")
        self.assertIn(ART_DIGEST, entry["found"])
        self.assertIn("c" * 64, entry["found"])

    def test_standing_failure_properties_not_evaluated_coverage_still_runs(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["sha256"] = "c" * 64
            b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "contains_line", "line": "hello artifact"}]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.entries("COMP-PROPERTY"), [])
        self.assert_entry(r, "COMP-ARTIFACT", subject="A1")

    def test_coverage_from_other_step_link_passes(self):
        def mut(b):
            b["links"][0]["subject_artifacts"] = []
            b["links"][1]["subject_artifacts"] = [{"artifact_id": "A1", "sha256": ART_DIGEST}]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["subresults"]["artifacts"], "pass", repr(r.results))

    def test_coverage_differing_digest_fails(self):
        def mut(b):
            b["links"][0]["subject_artifacts"] = [{"artifact_id": "A1", "sha256": "c" * 64}]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-ARTIFACT", subject="A1")
        self.assertIn("no presented link names this artifact with the stated digest", entry["found"])

    def test_coverage_absent_fails(self):
        def mut(b):
            b["links"][0]["subject_artifacts"] = []
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-ARTIFACT", subject="A1")
        self.assertIn("no presented link names this artifact with the stated digest", entry["found"])

    def test_relative_path_resolved_against_bundle_directory(self):
        # The bundle and the artifact stand in one temporary directory, and
        # the program runs with a different working directory, so a program
        # that resolved the relative artifact path against the working
        # directory instead of the bundle directory would fail this case.
        import tempfile, json, subprocess, sys
        from helpers import PROGRAM, base_bundle
        self.require_program()
        with tempfile.TemporaryDirectory() as bundle_dir:
            with tempfile.TemporaryDirectory() as other_dir:
                with open(os.path.join(bundle_dir, "artifact1.txt"), "w") as handle:
                    handle.write(ART_TEXT)
                bundle_path = os.path.join(bundle_dir, "bundle.json")
                with open(bundle_path, "w") as handle:
                    json.dump(base_bundle(), handle)
                proc = subprocess.run([sys.executable, PROGRAM, bundle_path, os.path.join(bundle_dir, "r.txt"), os.path.join(bundle_dir, "res.json"), os.path.join(bundle_dir, "c.txt"), "--verifier", "verifier-1"], capture_output=True, text=True, cwd=other_dir)
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_standing_digest_from_oracle_literal(self):
        # The stated digest in this standing test is the oracle literal
        # recorded in transcriptions/oracle_literals.json for the artifact
        # one contents, read from that file, not taken from helpers alone.
        import json as json_module
        from helpers import TRANSCRIPTIONS
        with open(os.path.join(TRANSCRIPTIONS, "oracle_literals.json"), encoding="utf-8") as handle:
            oracle_digest = json_module.load(handle)["sha256"]["artifact_one"]
        bundle = self.mutate(bundle_with_artifact(ART_TEXT, stated=oracle_digest))
        r = self.run_bundle(bundle, artifacts={"artifact1.txt": ART_TEXT})
        self.assertEqual(r.results["subresults"]["artifacts"], "pass", repr(r.results))
        self.assertEqual(r.entries("COMP-ARTIFACT"), [])

    def test_empty_required_artifacts_passes_vacuously(self):
        def mut(b):
            b["layout"]["required_artifacts"] = []
        r = self.run_bundle(self.mutate(mut), artifacts={})
        self.assertEqual(r.results["subresults"]["artifacts"], "pass")


PROPERTY_CASES = [
    ("exists", {"kind": "exists"}, ART_TEXT, True),
    ("sha256_equals_pass", {"kind": "sha256_equals", "sha256": ART_DIGEST}, ART_TEXT, True),
    ("sha256_equals_fail", {"kind": "sha256_equals", "sha256": "c" * 64}, ART_TEXT, False),
    ("contains_line_pass", {"kind": "contains_line", "line": "second line"}, ART_TEXT, True),
    ("contains_line_fail", {"kind": "contains_line", "line": "nope"}, ART_TEXT, False),
    ("first_line_pass", {"kind": "first_line_equals", "line": "hello artifact"}, ART_TEXT, True),
    ("first_line_fail", {"kind": "first_line_equals", "line": "nope"}, ART_TEXT, False),
    ("line_count_at_least_pass_exact", {"kind": "line_count_at_least", "count": 2}, ART_TEXT, True),
    ("line_count_at_least_fail_beyond", {"kind": "line_count_at_least", "count": 3}, ART_TEXT, False),
    ("line_count_at_most_pass_exact", {"kind": "line_count_at_most", "count": 2}, ART_TEXT, True),
    ("line_count_at_most_fail_beyond", {"kind": "line_count_at_most", "count": 1}, ART_TEXT, False),
    ("byte_size_at_most_pass_exact", {"kind": "byte_size_at_most", "count": len(ART_TEXT)}, ART_TEXT, True),
    ("byte_size_at_most_fail", {"kind": "byte_size_at_most", "count": 1}, ART_TEXT, False),
]


class TestT18Properties(ThreeChecksCase):
    def test_sha256_property_compares_property_digest_not_standing(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "sha256_equals", "sha256": "c" * 64}]
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "COMP-PROPERTY", subject="A1")

    def test_unsupported_property_named(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "bogus-kind"}]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-UNSUPPORTED-PROPERTY", subject="A1")
        self.assertIn("bogus-kind", entry["found"])

    def test_non_utf8_file_line_properties_fail_byte_and_digest_evaluated(self):
        content = b"\xff\xfe\x00binary\n"
        props = [
            {"kind": "contains_line", "line": "x"},
            {"kind": "first_line_equals", "line": "x"},
            {"kind": "line_count_at_least", "count": 0},
            {"kind": "line_count_at_most", "count": 99},
            {"kind": "byte_size_at_most", "count": 99},
            {"kind": "sha256_equals", "sha256": digest_of(content)},
        ]
        bundle = self.mutate(bundle_with_artifact(content, props))
        r = self.run_bundle(bundle, artifacts={"artifact1.txt": content})
        self.assertEqual(len(r.entries("COMP-PROPERTY")), 4, repr(r.entries("COMP-PROPERTY")))


for name, prop, content, passes in PROPERTY_CASES:
    def make(prop=prop, content=content, passes=passes):
        def test(self):
            bundle = self.mutate(bundle_with_artifact(content, [prop]))
            r = self.run_bundle(bundle, artifacts={"artifact1.txt": content})
            if passes:
                self.assertEqual(r.results["subresults"]["artifacts"], "pass", repr(r.results))
            else:
                self.assert_entry(r, "COMP-PROPERTY", subject="A1")
        return test
    setattr(TestT18Properties, "test_property_" + name, make())

if __name__ == "__main__":
    unittest.main()
