import unittest
from helpers import ThreeChecksCase


class TestT17Matching(ThreeChecksCase):
    def test_one_matching_link_passes(self):
        r = self.run_bundle()
        self.assertEqual(r.exit_status, 0, repr(r.results))
        self.assertEqual(r.results["subresults"]["links"], "pass")

    def test_step_with_no_presented_link(self):
        def mut(b):
            b["links"] = [link for link in b["links"] if link["step_id"] != "S2"]
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "COMP-NO-LINK", subject="S2", check="completeness")

    def test_more_than_one_matching_link_anomaly_still_passes(self):
        def mut(b):
            b["links"].insert(1, dict(b["links"][0]))
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))
        entry = self.assert_entry(r, "ANOM-MULTI-LINK", subject="S1", consequence="none")
        self.assertIsNotNone(r.closure_text)

    def test_layout_step_not_claimed_stage_level(self):
        def mut(b):
            b["claim"]["steps_claimed"] = ["S1"]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-NO-LINK", subject="S2", part="stage")
        self.assertEqual(entry["found"], "the step is not claimed")

    def test_claimed_step_naming_no_layout_step(self):
        def mut(b):
            b["claim"]["steps_claimed"] = ["S1", "S2", "S9"]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-NO-LINK", subject="S9", part="stage")
        self.assertEqual(entry["found"], "it names no layout step")

    def test_completion_for_unclaimed_step_used_by_reconstruction(self):
        def mut(b):
            b["claim"]["steps_claimed"] = ["S1"]
        r = self.run_bundle(self.mutate(mut))
        s2_entries = [e for e in r.entries("COMP-RECONSTRUCTED") if e["subject"] == "S2"]
        self.assertEqual(s2_entries, [])
        self.assertIn("step S2", r.report_text)
        # Under R8-5 the recorded completion time for S2 is read although S2
        # is not claimed, so the S2 link counts as matching on that time, the
        # chain join reads that matching result, and the stage level
        # COMP-NO-LINK not claimed entry for S2 stands separately.
        self.assertIn("step S2 seat=reviewer recorded=2026-01-01T00:00:00Z authenticity=pass matching=pass", r.report_text)
        self.assertIn("join S1 -> S2: pass", r.report_text)
        entry = self.assert_entry(r, "COMP-NO-LINK", subject="S2", part="stage")
        self.assertEqual(entry["found"], "the step is not claimed")

    def test_predicate_differs_link_predicate(self):
        def mut(b):
            b["links"][0]["predicate_type"] = "other"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "LINK-PREDICATE", subject="S1", check="completeness")

    def test_predicate_differs_with_another_link_matching(self):
        # The LINK-PREDICATE entry stands whether or not another link matches
        # the step. Here a second, matching link for S1 stands beside the
        # link whose predicate differs.
        def mut(b):
            good = dict(b["links"][0])
            b["links"][0]["predicate_type"] = "other"
            b["links"].insert(1, good)
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "LINK-PREDICATE", subject="S1", check="completeness")
        self.assertIn("step S1 seat=builder recorded=2026-01-01T00:00:00Z authenticity=pass matching=pass", r.report_text)

    def test_link_naming_no_layout_step(self):
        def mut(b):
            link = dict(b["links"][0])
            link["step_id"] = "S9"
            b["links"].append(link)
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "LINK-NO-STEP", subject="S9", check="authenticity")

    def test_produced_after_completion_reconstructed(self):
        def mut(b):
            b["links"][0]["produced_at"] = "2026-01-03T00:00:01Z"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "COMP-RECONSTRUCTED", subject="S1")

    def test_produced_exactly_at_completion_passes(self):
        def mut(b):
            b["links"][0]["produced_at"] = "2026-01-03T00:00:00Z"
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual([e for e in r.entries("COMP-RECONSTRUCTED") if e["subject"] == "S1"], [])

    def test_produced_before_ran_at_reconstructed(self):
        def mut(b):
            b["links"][0]["produced_at"] = "2026-01-01T11:59:59Z"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "COMP-RECONSTRUCTED", subject="S1")

    def test_produced_exactly_at_ran_at_passes(self):
        def mut(b):
            b["links"][0]["produced_at"] = b["links"][0]["ran_at"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual([e for e in r.entries("COMP-RECONSTRUCTED") if e["subject"] == "S1"], [])

    def test_no_produced_at_reconstructed(self):
        def mut(b):
            del b["links"][0]["produced_at"]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-RECONSTRUCTED", subject="S1")
        self.assertIn("no produced_at", entry["found"])

    def test_no_completion_time_recorded(self):
        def mut(b):
            b["claim"]["step_completions"] = [c for c in b["claim"]["step_completions"] if c["step_id"] != "S1"]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "COMP-RECONSTRUCTED", subject="S1")
        self.assertEqual(entry["found"], "no completion time is recorded")

    def test_only_reconstructed_step_carries_both_entries(self):
        def mut(b):
            del b["links"][0]["produced_at"]
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "COMP-RECONSTRUCTED", subject="S1")
        self.assert_entry(r, "COMP-NO-LINK", subject="S1")

    def test_auth_failure_named_even_where_another_link_matches(self):
        def mut(b):
            bad = dict(b["links"][0])
            bad["performer_spawn_id"] = "agent-unknown"
            b["links"].append(bad)
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-SPAWN", subject="S1")
        self.assertIn("step S1 seat=builder", r.report_text)
        self.assertIn("matching=pass", r.report_text)


if __name__ == "__main__":
    unittest.main()
