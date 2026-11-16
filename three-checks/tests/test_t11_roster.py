import unittest
from helpers import ThreeChecksCase, T_EARLY, T_RAN


class TestT11Roster(ThreeChecksCase):
    def test_recorded_exactly_at_ran_at_passes(self):
        def mut(b):
            b["roster"]["entries"][0]["recorded_at"] = T_RAN
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["checks"]["authenticity"], "pass")

    def test_earliest_entry_chosen_and_printed(self):
        def mut(b):
            b["roster"]["entries"].insert(0, {"seat": "builder", "agent_id": "agent-1", "recorded_at": "2026-01-01T06:00:00Z", "origin": "layout"})
            b["roster"]["entries"][1]["recorded_at"] = "2026-01-01T01:00:00Z"
        r = self.run_bundle(self.mutate(mut))
        self.assertIn("step S1 seat=builder recorded=2026-01-01T01:00:00Z", r.report_text)

    def test_tie_broken_by_list_order(self):
        # Two entries for the seat and performer with the same recorded_at,
        # one of origin addition and one of origin layout. The authorising
        # entry is the first of the tied entries in list order, so the part
        # the step is listed in follows that first entry origin, which makes
        # the list order tiebreak observable. In both runs the seat stands in
        # the advance layout through the layout entry at the same instant, so
        # both runs pass authenticity.
        def mut_addition_first(b):
            b["roster"]["entries"].insert(0, {"seat": "builder", "agent_id": "agent-1", "recorded_at": T_EARLY, "origin": "addition"})
        r = self.run_bundle(self.mutate(mut_addition_first))
        self.assertEqual(r.results["checks"]["authenticity"], "pass")
        part2 = r.report_text.split("part 2: seats added under R-50")[1]
        self.assertIn("step S1", part2)
        self.assertIn("recorded=" + T_EARLY, r.report_text)
        def mut_layout_first(b):
            b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-1", "recorded_at": T_EARLY, "origin": "addition"})
        r2 = self.run_bundle(self.mutate(mut_layout_first))
        self.assertEqual(r2.results["checks"]["authenticity"], "pass")
        part1 = r2.report_text.split("part 2: seats added under R-50")[0]
        self.assertIn("step S1", part1)

    def test_later_entry_produces_no_entry(self):
        def mut(b):
            b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-1", "recorded_at": "2026-01-02T00:00:00Z", "origin": "layout"})
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))

    def test_entries_only_after_ran_at_late_record(self):
        def mut(b):
            b["roster"]["entries"][0]["recorded_at"] = "2026-01-01T12:00:01Z"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-LATE-RECORD", subject="S1", check="authenticity", consequence="PARTIAL")

    def test_no_entry_for_seat_and_performer(self):
        def mut(b):
            b["roster"]["entries"] = [e for e in b["roster"]["entries"] if e["seat"] != "builder"]
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-ROSTER", subject="S1")

    def test_entry_with_different_agent_no_authorisation(self):
        def mut(b):
            b["roster"]["entries"][0]["agent_id"] = "agent-other"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-ROSTER", subject="S1")

    def test_entry_at_different_seat_no_authorisation(self):
        def mut(b):
            b["roster"]["entries"][0]["seat"] = "other-seat"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-ROSTER", subject="S1")

    def test_per_step_recorded_follows_first_matching_link(self):
        def mut(b):
            link = dict(b["links"][0])
            link["performer_spawn_id"] = "agent-3"
            b["links"].insert(0, link)
            rec = dict(b["spawn_records"]["records"][0])
            rec["agent_id"] = "agent-3"
            rec["session_id"] = "sess-3"
            b["spawn_records"]["records"].append(rec)
            b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-3", "recorded_at": "2026-01-01T02:00:00Z", "origin": "layout"})
        r = self.run_bundle(self.mutate(mut))
        self.assertIn("step S1 seat=builder recorded=2026-01-01T02:00:00Z", r.report_text)

    def test_per_step_recorded_no_matching_link_from_first_passing_link(self):
        # The second R8-1 branch: the step has no matching link, because
        # every presented link for it is reconstructed, so the per step
        # recorded value comes from the first presented link passing
        # subtests (a) to (d), in links list order.
        def mut(b):
            link = dict(b["links"][0])
            link["performer_spawn_id"] = "agent-3"
            del link["produced_at"]
            b["links"].insert(0, link)
            del b["links"][1]["produced_at"]
            rec = dict(b["spawn_records"]["records"][0])
            rec["agent_id"] = "agent-3"
            rec["session_id"] = "sess-3"
            b["spawn_records"]["records"].append(rec)
            b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-3", "recorded_at": "2026-01-01T02:00:00Z", "origin": "layout"})
        r = self.run_bundle(self.mutate(mut))
        self.assertIn("step S1 seat=builder recorded=2026-01-01T02:00:00Z authenticity=pass matching=fail", r.report_text)


if __name__ == "__main__":
    unittest.main()
