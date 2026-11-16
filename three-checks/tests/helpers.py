import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_DIR = os.path.dirname(TESTS_DIR)
PROGRAM = os.path.join(TOOL_DIR, "three_checks.py")
FIXTURES = os.path.join(TESTS_DIR, "fixtures")
TRANSCRIPTIONS = os.path.join(TESTS_DIR, "transcriptions")
GOLDEN = os.path.join(TESTS_DIR, "golden")
EXAMPLES_DIR = os.path.join(TOOL_DIR, "examples")
README_PATH = os.path.join(TOOL_DIR, "README.md")

ART_TEXT = "hello artifact\nsecond line\n"
ART_DIGEST = "eb339a5b18ae2472905e5efe9632fa2bcf9c2cf9cfa3940efb25808f1984e8c2"
MAT_DIGEST = "a" * 64
MAT_DIGEST_B = "b" * 64
T_EARLY = "2026-01-01T00:00:00Z"
T_RAN = "2026-01-01T12:00:00Z"
T_PRODUCED = "2026-01-02T00:00:00Z"
T_DONE = "2026-01-03T00:00:00Z"
VERIFIER = "verifier-1"
USAGE_LINE = "usage: three-checks BUNDLE REPORT RESULTS CLOSURE --verifier IDENTITY"
STRENGTH_LINE = "strength: the checks count at the closure record L2 grade and no higher, and only where the origin tests passed; the seat association rests on the roster record."
SCOPE_PARAGRAPH = "This record attests that the three checks of R-80 were run by the named verifier, who is not the performer, not the coordinator, and not the commissioner, over the records in the named bundle, and that every check passed. Provenance attests how the stage artifacts were produced; it is not evidence of their quality. The roster authenticity rests on spawn records captured by the runtime and on the roster record for the seat association; the push record rests on verification through the API at bundle assembly. No strength above grade L2 is claimed."


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def base_bundle():
    return {
        "layout": {
            "stage_id": "stage-1",
            "steps": [
                {"step_id": "S1", "seat": "builder", "predicate_type": "build"},
                {"step_id": "S2", "seat": "reviewer", "predicate_type": "review"},
            ],
            "required_artifacts": [
                {"artifact_id": "A1", "path": "artifact1.txt", "sha256": ART_DIGEST, "properties": []}
            ],
            "record_sources": [
                {"record_kind": "roster", "source": "runtime-spawn-records"},
                {"record_kind": "push", "source": "api-verification"},
                {"record_kind": "links", "source": "stage-record"},
                {"record_kind": "claim", "source": "stage-record"},
                {"record_kind": "ledger", "source": "stage-record"},
            ],
        },
        "roster": {
            "entries": [
                {"seat": "builder", "agent_id": "agent-1", "recorded_at": T_EARLY, "origin": "layout"},
                {"seat": "reviewer", "agent_id": "agent-2", "recorded_at": T_EARLY, "origin": "layout"},
            ],
            "republications": [],
        },
        "links": [
            {
                "step_id": "S1", "predicate_type": "build", "performer_spawn_id": "agent-1",
                "builder": "builder-name", "produced_at": T_PRODUCED, "ran_at": T_RAN,
                "inputs": [], "outputs": [{"name": "m1", "sha256": MAT_DIGEST}],
                "subject_artifacts": [{"artifact_id": "A1", "sha256": ART_DIGEST}],
            },
            {
                "step_id": "S2", "predicate_type": "review", "performer_spawn_id": "agent-2",
                "builder": "builder-name", "produced_at": T_PRODUCED, "ran_at": T_RAN,
                "inputs": [{"name": "m1", "sha256": MAT_DIGEST}], "outputs": [],
                "subject_artifacts": [],
            },
        ],
        "spawn_records": {
            "exporter": "runtime", "exported_at": T_EARLY, "source_database": "spawn-db",
            "scoping": {"method": "identity_list", "detail": "two agents"},
            "records": [
                {"agent_id": "agent-1", "parent_agent_id": "root", "depth": 0, "kind": "spawn", "agent_type": None, "session_id": "sess-1", "created_at": T_EARLY},
                {"agent_id": "agent-2", "parent_agent_id": "root", "depth": 0, "kind": "spawn", "agent_type": None, "session_id": "sess-2", "created_at": T_EARLY},
            ],
        },
        "identities": {"coordinator": "coord-1", "commissioner_stage": "comm-stage", "commissioner_work": "comm-work"},
        "claim": {
            "stage_id": "stage-1", "steps_claimed": ["S1", "S2"],
            "step_completions": [
                {"step_id": "S1", "completed_at": T_DONE},
                {"step_id": "S2", "completed_at": T_DONE},
            ],
            "gate_context": None, "push_link": None, "predecessor_inputs": None,
            "ledger_claims": ["E1"],
        },
        "push_record": {"repo": "repo-1", "branch": "main", "head_sha": "h1", "tree_sha": "t1", "verified_by": "verifier-x", "verified_at": T_EARLY},
        "ledger_entries": [{"entry_id": "E1", "text": "ledger text"}],
    }


def passing_bundle():
    return base_bundle()


class RunResult:
    def __init__(self, proc, workdir, report_path, results_path, closure_path):
        self.proc = proc
        self.exit_status = proc.returncode
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.workdir = workdir
        self.report_path = report_path
        self.results_path = results_path
        self.closure_path = closure_path

    @property
    def report_text(self):
        if not os.path.exists(self.report_path):
            return None
        with open(self.report_path, "r", encoding="utf-8") as handle:
            return handle.read()

    @property
    def closure_text(self):
        if not os.path.exists(self.closure_path):
            return None
        with open(self.closure_path, "r", encoding="utf-8") as handle:
            return handle.read()

    @property
    def results(self):
        if not os.path.exists(self.results_path):
            return None
        return load_json(self.results_path)

    def entries(self, code=None):
        data = self.results
        if data is None:
            return []
        items = data.get("discrepancies", [])
        if code is None:
            return items
        return [item for item in items if item.get("code") == code]

    def entries_for(self, code, subject=None):
        items = self.entries(code)
        if subject is None:
            return items
        return [item for item in items if item.get("subject") == subject]


class ThreeChecksCase(unittest.TestCase):
    def require_program(self):
        if not os.path.isfile(PROGRAM):
            self.fail("missing program: " + PROGRAM + " (expected failure at stage 13, before stage 14 builds it)")

    def run_argv(self, argv, cwd=None):
        self.require_program()
        return subprocess.run([sys.executable, PROGRAM] + argv, capture_output=True, text=True, cwd=cwd)

    def run_bundle(self, bundle=None, verifier=VERIFIER, bundle_bytes=None, artifacts=None,
                   preexisting=None, bundle_name="bundle.json", extra_files=None):
        self.require_program()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        workdir = tmp.name
        bundle_path = os.path.join(workdir, bundle_name)
        if bundle_bytes is not None:
            with open(bundle_path, "wb") as handle:
                handle.write(bundle_bytes)
        else:
            with open(bundle_path, "w", encoding="utf-8") as handle:
                json.dump(bundle if bundle is not None else base_bundle(), handle)
        files = {"artifact1.txt": ART_TEXT}
        if artifacts is not None:
            files = artifacts
        for name, content in files.items():
            target = os.path.join(workdir, name)
            os.makedirs(os.path.dirname(target), exist_ok=True) if os.path.dirname(name) else None
            if isinstance(content, bytes):
                with open(target, "wb") as handle:
                    handle.write(content)
            else:
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write(content)
        if extra_files:
            for name, content in extra_files.items():
                target = os.path.join(workdir, name)
                if isinstance(content, bytes):
                    with open(target, "wb") as handle:
                        handle.write(content)
                else:
                    with open(target, "w", encoding="utf-8") as handle:
                        handle.write(content)
        report_path = os.path.join(workdir, "report.txt")
        results_path = os.path.join(workdir, "results.json")
        closure_path = os.path.join(workdir, "closure.txt")
        if preexisting:
            for which, content in preexisting.items():
                target = {"report": report_path, "results": results_path, "closure": closure_path}[which]
                mode = "wb" if isinstance(content, bytes) else "w"
                with open(target, mode) as handle:
                    handle.write(content)
        proc = subprocess.run(
            [sys.executable, PROGRAM, bundle_path, report_path, results_path, closure_path, "--verifier", verifier],
            capture_output=True, text=True, cwd=workdir)
        return RunResult(proc, workdir, report_path, results_path, closure_path)

    def assert_entry(self, result, code, subject=None, part=None, check=None, consequence=None, count=None):
        found = result.entries(code)
        if count is not None:
            self.assertEqual(len(found), count, "entry count for " + code + ": " + repr(found))
        self.assertTrue(found, "no entry with code " + code + " in " + repr(result.results))
        for entry in found:
            if subject is not None:
                self.assertEqual(entry.get("subject"), subject)
            if part is not None:
                self.assertEqual(entry.get("part"), part)
            if check is not None:
                self.assertEqual(entry.get("check"), check)
            if consequence is not None:
                self.assertEqual(entry.get("consequence"), consequence)
        return found[0] if found else None

    def assert_entry_for_subject(self, result, code, subject, part=None, check=None, consequence=None, count=1):
        found = result.entries_for(code, subject)
        if count is not None:
            self.assertEqual(len(found), count, "entry count for " + code + " with subject " + str(subject) + ": " + repr(found))
        self.assertTrue(found, "no entry with code " + code + " and subject " + str(subject) + " in " + repr(result.results))
        for entry in found:
            if part is not None:
                self.assertEqual(entry.get("part"), part)
            if check is not None:
                self.assertEqual(entry.get("check"), check)
            if consequence is not None:
                self.assertEqual(entry.get("consequence"), consequence)
        return found[0] if found else None

    def assert_no_file(self, path):
        self.assertFalse(os.path.exists(path), "file should not exist: " + path)

    def mutate(self, fn):
        bundle = base_bundle()
        fn(bundle)
        return bundle


def sha256_hex(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
