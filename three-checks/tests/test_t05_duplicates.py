import unittest
from helpers import ThreeChecksCase

PREFIX = "three-checks: input error: "


class TestT05Duplicates(ThreeChecksCase):
    def raw_check(self, raw, expected):
        r = self.run_bundle(bundle_bytes=raw)
        self.assertEqual(r.exit_status, 2, r.stderr)
        self.assertIn(PREFIX + expected, r.stderr)
        return r

    def test_duplicate_key_top_level(self):
        self.raw_check(b'{"layout": {}, "layout": {}}', "duplicate field layout")

    def test_duplicate_key_inside_section(self):
        self.raw_check(b'{"layout": {"stage_id": "a", "stage_id": "b"}}', "duplicate field layout.stage_id")

    def test_duplicate_key_inside_list_entry(self):
        self.raw_check(b'{"layout": {"steps": [{"step_id": "S1", "step_id": "S2"}]}}', "duplicate field layout.steps.0.step_id")

    def test_two_duplicates_encounter_order(self):
        r = self.raw_check(b'{"a": 1, "a": 2, "b": 1, "b": 2}', "duplicate field a")
        self.assertLess(r.stderr.index("duplicate field a"), r.stderr.index("duplicate field b"))

    def test_nested_duplicate_inner_before_outer(self):
        raw = b'{"x": 1, "x": {"y": 1, "y": 2}}'
        r = self.run_bundle(bundle_bytes=raw)
        self.assertEqual(r.exit_status, 2)
        lines = r.stderr.strip().splitlines()
        inner = [i for i, line in enumerate(lines) if line.endswith("duplicate field x.y")][0]
        outer = [i for i, line in enumerate(lines) if line.endswith("duplicate field x")][0]
        self.assertLess(inner, outer)

    def test_duplicated_field_not_validated_further(self):
        raw = b'{"layout": {"stage_id": 123, "stage_id": "ok"}}'
        r = self.run_bundle(bundle_bytes=raw)
        self.assertIn("duplicate field layout.stage_id", r.stderr)
        self.assertNotIn("layout.stage_id must be string", r.stderr)

    def test_two_steps_same_step_id(self):
        def mut(b):
            b["layout"]["steps"].append(dict(b["layout"]["steps"][0]))
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "layout.steps is outside its allowed set", r.stderr)

    def test_two_artifacts_same_artifact_id(self):
        def mut(b):
            b["layout"]["required_artifacts"].append(dict(b["layout"]["required_artifacts"][0]))
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "layout.required_artifacts is outside its allowed set", r.stderr)

    def test_two_artifacts_same_resolved_path(self):
        def mut(b):
            entry = dict(b["layout"]["required_artifacts"][0])
            entry["artifact_id"] = "A2"
            b["layout"]["required_artifacts"].append(entry)
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "layout.required_artifacts is outside its allowed set", r.stderr)

    def test_two_artifacts_same_path_different_spelling(self):
        def mut(b):
            entry = dict(b["layout"]["required_artifacts"][0])
            entry["artifact_id"] = "A2"
            entry["path"] = "./artifact1.txt"
            b["layout"]["required_artifacts"].append(entry)
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "layout.required_artifacts is outside its allowed set", r.stderr)

    def test_duplicated_steps_claimed(self):
        r = self.run_bundle(self.mutate(lambda b: b["claim"].update({"steps_claimed": ["S1", "S1"]})))
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "claim.steps_claimed is outside its allowed set", r.stderr)

    def test_two_completions_for_one_step(self):
        def mut(b):
            b["claim"]["step_completions"].append(dict(b["claim"]["step_completions"][0]))
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "claim.step_completions is outside its allowed set", r.stderr)

    def test_two_ledger_entries_same_entry_id(self):
        def mut(b):
            b["ledger_entries"].append(dict(b["ledger_entries"][0]))
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "ledger_entries is outside its allowed set", r.stderr)

    def test_duplicated_field_in_list_entry_not_validated_further(self):
        raw = b'{"layout": {"steps": [{"step_id": 123, "step_id": "S1"}]}}'
        r = self.run_bundle(bundle_bytes=raw)
        self.assertIn("duplicate field layout.steps.0.step_id", r.stderr)
        self.assertNotIn("layout.steps.0.step_id must be string", r.stderr)

    def test_duplicated_agent_id_bound_by_link(self):
        def mut(b):
            b["spawn_records"]["records"].append(dict(b["spawn_records"]["records"][0]))
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 1)
        self.assert_entry(r, "AUTH-NO-SPAWN", subject="S1", check="authenticity")

    def test_duplicated_agent_id_no_link_binds(self):
        def mut(b):
            rec = dict(b["spawn_records"]["records"][0])
            rec["agent_id"] = "agent-x"
            rec["session_id"] = "sess-x1"
            b["spawn_records"]["records"].append(rec)
            rec2 = dict(rec)
            rec2["session_id"] = "sess-x2"
            b["spawn_records"]["records"].append(rec2)
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 1)
        self.assert_entry(r, "AUTH-NO-SPAWN", subject="agent-x", part="stage", check="authenticity")


if __name__ == "__main__":
    unittest.main()
