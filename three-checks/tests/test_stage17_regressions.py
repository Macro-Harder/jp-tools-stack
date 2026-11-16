import json
import os
import resource
import shlex
import subprocess
import sys
import tempfile
import unittest

from helpers import (
    ART_TEXT,
    PROGRAM,
    ThreeChecksCase,
    base_bundle,
)

PREFIX = "three-checks: input error: "


def base_text():
    return json.dumps(base_bundle())


def run_program(args, timeout=30, rlimit_as=None, stderr=None):
    def limit():
        if rlimit_as is not None:
            resource.setrlimit(resource.RLIMIT_AS, (rlimit_as, rlimit_as))

    return subprocess.run(
        [sys.executable, PROGRAM] + args,
        capture_output=stderr is None,
        text=True,
        timeout=timeout,
        preexec_fn=limit if rlimit_as is not None else None,
        stderr=stderr,
    )


def stage_bundle(workdir, bundle=None, bundle_bytes=None, artifacts=None):
    bundle_path = os.path.join(workdir, "bundle.json")
    if bundle_bytes is not None:
        with open(bundle_path, "wb") as handle:
            handle.write(bundle_bytes)
    else:
        with open(bundle_path, "w", encoding="utf-8") as handle:
            json.dump(bundle if bundle is not None else base_bundle(), handle)
    files = {"artifact1.txt": ART_TEXT} if artifacts is None else artifacts
    for name, content in files.items():
        target = os.path.join(workdir, name)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(target, mode) as handle:
            handle.write(content)
    return bundle_path


def output_args(workdir):
    return [
        os.path.join(workdir, "report.txt"),
        os.path.join(workdir, "results.json"),
        os.path.join(workdir, "closure.txt"),
    ]


class TestStage17B1DuplicateWrongType(ThreeChecksCase):
    def check_dup(self, raw, expected_path):
        r = self.run_bundle(bundle_bytes=raw if isinstance(raw, bytes) else raw.encode("utf-8"))
        self.assertEqual(r.exit_status, 2, r.stderr)
        self.assertIn(PREFIX + "duplicate field " + expected_path, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assert_no_file(r.report_path)
        self.assert_no_file(r.results_path)

    def test_layout_int(self):
        self.check_dup('{"layout": 1, "layout": 2}', "layout")

    def test_layout_list(self):
        self.check_dup('{"layout": [], "layout": {}}', "layout")

    def test_roster_int(self):
        self.check_dup('{"roster": 1, "roster": 2}', "roster")

    def test_links_int(self):
        self.check_dup('{"links": 1, "links": 2}', "links")

    def test_ledger_entries_int(self):
        self.check_dup('{"ledger_entries": 5, "ledger_entries": []}', "ledger_entries")

    def test_layout_steps_int(self):
        raw = base_text().replace('"steps": [', '"steps": 5, "steps": [', 1)
        self.check_dup(raw, "layout.steps")

    def test_roster_entries_int(self):
        raw = base_text().replace('"entries": [', '"entries": 5, "entries": [', 1)
        self.check_dup(raw, "roster.entries")

    def test_spawn_records_int(self):
        raw = base_text().replace('"records": [', '"records": 5, "records": [', 1)
        self.check_dup(raw, "spawn_records.records")

    def test_spawn_scoping_int(self):
        raw = base_text().replace('"scoping": {', '"scoping": 5, "scoping": {', 1)
        self.check_dup(raw, "spawn_records.scoping")

    def test_claim_push_link_int(self):
        raw = base_text().replace('"push_link": null', '"push_link": 5, "push_link": null', 1)
        self.check_dup(raw, "claim.push_link")

    def test_link_inputs_int(self):
        raw = base_text().replace('"inputs": []', '"inputs": 5, "inputs": []', 1)
        self.check_dup(raw, "links.0.inputs")

    def test_claim_step_completions_int(self):
        raw = base_text().replace('"step_completions": [', '"step_completions": 5, "step_completions": [', 1)
        self.check_dup(raw, "claim.step_completions")


class TestStage17B2DeepNesting(ThreeChecksCase):
    def check_validity_gate(self, raw):
        r = self.run_bundle(bundle_bytes=raw.encode("utf-8"))
        self.assertEqual(r.exit_status, 2, r.stderr)
        self.assertIn(PREFIX + "the bundle file is not valid JSON", r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertNotIn("RecursionError", r.stderr)

    def test_object_depth_995(self):
        inner = '{"a":' * 995 + "1" + "}" * 995
        self.check_validity_gate('{"layout": 1, "zz": ' + inner + "}")

    def test_object_depth_1500(self):
        inner = '{"a":' * 1500 + "1" + "}" * 1500
        self.check_validity_gate('{"layout": 1, "zz": ' + inner + "}")

    def test_object_depth_2000(self):
        inner = '{"a":' * 2000 + "1" + "}" * 2000
        self.check_validity_gate('{"layout": 1, "zz": ' + inner + "}")

    def test_array_depth_995(self):
        inner = "[" * 995 + "1" + "]" * 995
        self.check_validity_gate('{"layout": 1, "zz": ' + inner + "}")

    def test_object_depth_100_still_field_errors(self):
        inner = '{"a":' * 100 + "1" + "}" * 100
        r = self.run_bundle(bundle_bytes=('{"layout": 1, "zz": ' + inner + "}").encode("utf-8"))
        self.assertEqual(r.exit_status, 2, r.stderr)
        self.assertIn(PREFIX + "layout must be object", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class TestStage17B3NullByteArtifactPath(ThreeChecksCase):
    def test_null_byte_artifact_path_is_comp_artifact(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["path"] = "artifact\u0000x.txt"

        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 1, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        entry = self.assert_entry(r, "COMP-ARTIFACT", subject="A1")
        self.assertIn("cannot be read", entry["found"])


class TestStage17B4BoundedRegularReads(ThreeChecksCase):
    def test_dev_zero_bundle_fails_fast_at_cannot_read(self):
        with tempfile.TemporaryDirectory() as workdir:
            args = ["/dev/zero"] + output_args(workdir) + ["--verifier", "verifier-1"]
            proc = run_program(args, timeout=15, rlimit_as=1 << 30)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn(PREFIX + "cannot read the bundle file", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_dev_null_bundle_is_cannot_read(self):
        with tempfile.TemporaryDirectory() as workdir:
            args = ["/dev/null"] + output_args(workdir) + ["--verifier", "verifier-1"]
            proc = run_program(args, timeout=15)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn(PREFIX + "cannot read the bundle file", proc.stderr)

    def test_unserved_fifo_bundle_fails_fast(self):
        with tempfile.TemporaryDirectory() as workdir:
            fifo = os.path.join(workdir, "bundle.fifo")
            os.mkfifo(fifo)
            args = [fifo] + output_args(workdir) + ["--verifier", "verifier-1"]
            proc = run_program(args, timeout=15)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn(PREFIX + "cannot read the bundle file", proc.stderr)

    def test_symlink_to_regular_bundle_still_passes(self):
        with tempfile.TemporaryDirectory() as workdir:
            real = stage_bundle(workdir)
            link = os.path.join(workdir, "link-bundle.json")
            os.symlink(real, link)
            outs = output_args(workdir)
            proc = run_program([link] + outs + ["--verifier", "verifier-1"], timeout=15)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_oversized_bundle_refusal_names_bytes_read(self):
        with tempfile.TemporaryDirectory() as workdir:
            bundle_path = stage_bundle(workdir, bundle_bytes=b"x" * 3000000)
            args = [bundle_path] + output_args(workdir) + ["--verifier", "verifier-1"]
            proc = run_program(args, timeout=15)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn(PREFIX + "the bundle file is 2000001 bytes, over the limit of 2000000 bytes", proc.stderr)

    def test_dev_zero_artifact_fails_fast_as_comp_artifact(self):
        with tempfile.TemporaryDirectory() as workdir:
            bundle = base_bundle()
            bundle["layout"]["required_artifacts"][0]["path"] = "/dev/zero"
            bundle_path = stage_bundle(workdir, bundle=bundle, artifacts={})
            args = [bundle_path] + output_args(workdir) + ["--verifier", "verifier-1"]
            proc = run_program(args, timeout=15, rlimit_as=1 << 30)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            with open(os.path.join(workdir, "results.json")) as handle:
                data = json.load(handle)
            found = [e["found"] for e in data["discrepancies"] if e["code"] == "COMP-ARTIFACT"]
            self.assertTrue(any("cannot be read" in text for text in found), repr(found))

    def test_unserved_fifo_artifact_fails_fast_as_comp_artifact(self):
        with tempfile.TemporaryDirectory() as workdir:
            fifo = os.path.join(workdir, "artifact.fifo")
            os.mkfifo(fifo)
            bundle = base_bundle()
            bundle["layout"]["required_artifacts"][0]["path"] = fifo
            bundle_path = stage_bundle(workdir, bundle=bundle, artifacts={})
            args = [bundle_path] + output_args(workdir) + ["--verifier", "verifier-1"]
            proc = run_program(args, timeout=15)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            with open(os.path.join(workdir, "results.json")) as handle:
                data = json.load(handle)
            found = [e["found"] for e in data["discrepancies"] if e["code"] == "COMP-ARTIFACT"]
            self.assertTrue(any("cannot be read" in text for text in found), repr(found))

    def test_oversized_artifact_not_read_whole(self):
        content = b"x" * 3000001
        def mut(b):
            import hashlib
            b["layout"]["required_artifacts"][0]["sha256"] = hashlib.sha256(content).hexdigest()
            b["links"][0]["subject_artifacts"] = [{"artifact_id": "A1", "sha256": b["layout"]["required_artifacts"][0]["sha256"]}]

        r = self.run_bundle(self.mutate(mut), artifacts={"artifact1.txt": content})
        self.assertEqual(r.exit_status, 1, r.stderr)
        entries = [e for e in r.entries("COMP-ARTIFACT") if "over the limit" in e["found"]]
        self.assertEqual(len(entries), 1, repr(r.entries("COMP-ARTIFACT")))
        self.assertIn("3000001", entries[0]["found"])
        self.assertIn("2000000", entries[0]["found"])
        self.assertNotIn("2000001", entries[0]["found"])


class TestStage17B5B7Rendering(ThreeChecksCase):
    def failing_bundle(self):
        bundle = base_bundle()
        bundle["claim"]["ledger_claims"] = ["E9"]
        return bundle

    def test_stage_id_newline_cannot_forge_outcome_line(self):
        bundle = self.failing_bundle()
        bundle["layout"]["stage_id"] = "s1\noutcome=PASS"
        bundle["claim"]["stage_id"] = "s1\noutcome=PASS"
        r = self.run_bundle(bundle)
        self.assertEqual(r.exit_status, 1, r.stderr)
        lines = r.report_text.splitlines()
        self.assertIn("outcome=FAIL", lines)
        self.assertNotIn("outcome=PASS", lines)
        self.assertIn('stage="s1\\noutcome=PASS"', lines)

    def test_verifier_newline_cannot_forge_outcome_line(self):
        r = self.run_bundle(self.failing_bundle(), verifier="v1\noutcome=PASS")
        self.assertEqual(r.exit_status, 1, r.stderr)
        lines = r.report_text.splitlines()
        self.assertIn("outcome=FAIL", lines)
        self.assertNotIn("outcome=PASS", lines)
        self.assertIn('verifier="v1\\noutcome=PASS"', lines)

    def test_verifier_newline_escaped_in_closure_on_pass(self):
        r = self.run_bundle(verifier="v1\noutcome=PASS")
        self.assertEqual(r.exit_status, 0, r.stderr)
        self.assertIn('verifier="v1\\noutcome=PASS"', r.closure_text.splitlines())

    def test_non_utf8_verifier_renders_as_json_string(self):
        r = self.run_bundle(verifier="v\udcff")
        self.assertEqual(r.exit_status, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn('verifier="v\\udcff"', r.report_text.splitlines())
        self.assertIn('verifier="v\\udcff"', r.closure_text.splitlines())
        self.assertEqual(r.results["provenance"]["verifier"], "v\udcff")

    def test_found_text_with_newline_renders_escaped(self):
        bundle = base_bundle()
        bundle["claim"]["ledger_claims"] = ["E9\noutcome=PASS"]
        r = self.run_bundle(bundle)
        self.assertEqual(r.exit_status, 1, r.stderr)
        lines = r.report_text.splitlines()
        self.assertNotIn("outcome=PASS", lines)
        self.assertTrue(any("E9\\noutcome=PASS" in line for line in lines), r.report_text)


class TestStage17B6StderrGuard(ThreeChecksCase):
    def missing_bundle_args(self, workdir):
        return [os.path.join(workdir, "no-bundle.json")] + output_args(workdir) + ["--verifier", "verifier-1"]

    def test_input_error_exit_2_with_stderr_closed(self):
        with tempfile.TemporaryDirectory() as workdir:
            argv = [sys.executable, PROGRAM] + self.missing_bundle_args(workdir)
            command = "exec 2>&-; exec " + shlex.join(argv)
            proc = subprocess.run(["/bin/bash", "-c", command], capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_input_error_exit_2_with_stderr_dev_full(self):
        with tempfile.TemporaryDirectory() as workdir:
            fd = os.open("/dev/full", os.O_WRONLY)
            try:
                proc = subprocess.run(
                    [sys.executable, PROGRAM] + self.missing_bundle_args(workdir),
                    stdout=subprocess.PIPE, stderr=fd, text=True, timeout=15)
            finally:
                os.close(fd)
            self.assertEqual(proc.returncode, 2, proc.stdout)


class TestStage17B8ScaleShape(ThreeChecksCase):
    def test_chain_600_steps_passes_with_cached_maps_and_indexes(self):
        t0 = "2026-01-01T00:00:00Z"
        bundle = base_bundle()
        n = 600
        bundle["layout"]["steps"] = [{"step_id": "S%d" % i, "seat": "builder", "predicate_type": "build"} for i in range(n)]
        bundle["roster"]["entries"] = [{"seat": "builder", "agent_id": "agent-%d" % i, "recorded_at": t0, "origin": "layout"} for i in range(n)]
        bundle["spawn_records"]["records"] = [{"agent_id": "agent-%d" % i, "parent_agent_id": "root", "depth": 0, "kind": "spawn", "agent_type": None, "session_id": "s%d" % i, "created_at": t0} for i in range(n)]
        digest = "a" * 64
        links = []
        for i in range(n):
            links.append({
                "step_id": "S%d" % i, "predicate_type": "build", "performer_spawn_id": "agent-%d" % i,
                "builder": "x", "produced_at": "2026-01-02T00:00:00Z", "ran_at": "2026-01-01T12:00:00Z",
                "inputs": ([{"name": "m%d" % (i - 1), "sha256": digest}] if i else []),
                "outputs": [{"name": "m%d" % i, "sha256": digest}],
                "subject_artifacts": ([{"artifact_id": "A1", "sha256": bundle["layout"]["required_artifacts"][0]["sha256"]}] if i == 0 else []),
            })
        bundle["links"] = links
        bundle["claim"]["steps_claimed"] = ["S%d" % i for i in range(n)]
        bundle["claim"]["step_completions"] = [{"step_id": "S%d" % i, "completed_at": "2026-01-03T00:00:00Z"} for i in range(n)]
        r = self.run_bundle(bundle)
        self.assertEqual(r.exit_status, 0, r.stderr)


class TestStage17B9HardlinkOutputs(ThreeChecksCase):
    def test_report_hardlink_to_bundle_refused(self):
        with tempfile.TemporaryDirectory() as workdir:
            bundle_path = stage_bundle(workdir)
            with open(bundle_path, "rb") as handle:
                before = handle.read()
            report_path = os.path.join(workdir, "report.txt")
            os.link(bundle_path, report_path)
            args = [bundle_path, report_path, os.path.join(workdir, "results.json"), os.path.join(workdir, "closure.txt"), "--verifier", "verifier-1"]
            proc = run_program(args, timeout=15)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("three-checks: usage error: output path " + report_path + " names an input file", proc.stderr)
            with open(bundle_path, "rb") as handle:
                self.assertEqual(handle.read(), before)

    def test_results_hardlink_to_artifact_refused(self):
        with tempfile.TemporaryDirectory() as workdir:
            bundle_path = stage_bundle(workdir)
            artifact_path = os.path.join(workdir, "artifact1.txt")
            with open(artifact_path, "rb") as handle:
                before = handle.read()
            results_path = os.path.join(workdir, "results.json")
            os.link(artifact_path, results_path)
            args = [bundle_path, os.path.join(workdir, "report.txt"), results_path, os.path.join(workdir, "closure.txt"), "--verifier", "verifier-1"]
            proc = run_program(args, timeout=15)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("three-checks: usage error: output path " + results_path + " names an input file", proc.stderr)
            with open(artifact_path, "rb") as handle:
                self.assertEqual(handle.read(), before)


if __name__ == "__main__":
    unittest.main()
