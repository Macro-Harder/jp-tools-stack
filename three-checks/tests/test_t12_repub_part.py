import unittest
from helpers import ThreeChecksCase, T_EARLY


def addition_bundle(republications, extra_roster=None):
    def mut(b):
        b["roster"]["entries"][0] = {"seat": "builder", "agent_id": "agent-1", "recorded_at": T_EARLY, "origin": "addition"}
        b["roster"]["republications"] = republications
        if extra_roster:
            b["roster"]["entries"].extend(extra_roster)
    return mut


class TestT12Republication(ThreeChecksCase):
    def test_addition_seat_in_advance_layout_no_repub_required(self):
        mut = addition_bundle([], extra_roster=[{"seat": "builder", "agent_id": "agent-9", "recorded_at": T_EARLY, "origin": "layout"}])
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["checks"]["authenticity"], "pass", repr(r.results))

    def test_republication_exactly_at_ran_at_passes(self):
        mut = addition_bundle([{"seat": "builder", "republished_at": "2026-01-01T12:00:00Z"}])
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["checks"]["authenticity"], "pass", repr(r.results))

    def test_republication_one_second_after_fails(self):
        mut = addition_bundle([{"seat": "builder", "republished_at": "2026-01-01T12:00:01Z"}])
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-REPUB", subject="S1")

    def test_no_republication_fails(self):
        mut = addition_bundle([])
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-REPUB", subject="S1")

    def test_layout_entry_after_ran_at_not_standing(self):
        mut = addition_bundle([], extra_roster=[{"seat": "builder", "agent_id": "agent-9", "recorded_at": "2026-01-02T00:00:00Z", "origin": "layout"}])
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-REPUB", subject="S1")

    def test_later_layout_entry_addition_still_needs_repub(self):
        # Reading taken, per plan part 2.3 and plan part 1.8: a seat stands in
        # the advance layout only where an origin layout entry for the seat has
        # recorded_at not later than ran_at. The layout entry here is recorded
        # after ran_at (2026-01-01T12:00:00Z), so it is a later layout entry:
        # it never makes the seat stand and never exempts the seat from
        # subtest (d). Subtest (d) still applies, so AUTH-NO-REPUB stands.
        mut = addition_bundle([], extra_roster=[{"seat": "builder", "agent_id": "agent-1", "recorded_at": "2026-01-01T13:00:00Z", "origin": "layout"}])
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-REPUB", subject="S1")

    def test_earliest_republication_governs(self):
        mut = addition_bundle([{"seat": "builder", "republished_at": "2026-01-01T13:00:00Z"}, {"seat": "builder", "republished_at": "2026-01-01T11:00:00Z"}])
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["checks"]["authenticity"], "pass", repr(r.results))
        self.assertIn("republished=2026-01-01T11:00:00Z", r.report_text)

    def test_addition_first_authorisation_stays_part2(self):
        mut = addition_bundle([{"seat": "builder", "republished_at": "2026-01-01T11:00:00Z"}])
        r = self.run_bundle(self.mutate(mut))
        part2 = r.report_text.split("part 2: seats added under R-50")[1]
        self.assertIn("step S1", part2)

    def test_part2_line_republished_field_time_and_none(self):
        mut = addition_bundle([{"seat": "builder", "republished_at": "2026-01-01T11:00:00Z"}])
        r = self.run_bundle(self.mutate(mut))
        self.assertIn("republished=2026-01-01T11:00:00Z", r.report_text)
        mut2 = addition_bundle([])
        r2 = self.run_bundle(self.mutate(mut2))
        self.assertIn("republished=none", r2.report_text)

    def test_seat_part_follows_earliest_recorded_not_links_order(self):
        def mut(b):
            link = dict(b["links"][0])
            link["performer_spawn_id"] = "agent-3"
            b["links"].append(link)
            rec = dict(b["spawn_records"]["records"][0])
            rec["agent_id"] = "agent-3"
            rec["session_id"] = "sess-3"
            b["spawn_records"]["records"].append(rec)
            b["roster"]["entries"][0] = {"seat": "builder", "agent_id": "agent-1", "recorded_at": "2026-01-01T05:00:00Z", "origin": "layout"}
            b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-3", "recorded_at": "2026-01-01T01:00:00Z", "origin": "addition"})
            b["roster"]["republications"] = [{"seat": "builder", "republished_at": "2026-01-01T02:00:00Z"}]
        r = self.run_bundle(self.mutate(mut))
        part2 = r.report_text.split("part 2: seats added under R-50")[1]
        self.assertIn("step S1", part2)

    def test_never_authorised_seat_part_from_roster_and_no_roster_part1(self):
        def mut(b):
            b["layout"]["steps"].append({"step_id": "S3", "seat": "extra", "predicate_type": "extra"})
            b["roster"]["entries"].append({"seat": "extra", "agent_id": "agent-9", "recorded_at": T_EARLY, "origin": "addition"})
        r = self.run_bundle(self.mutate(mut))
        part2 = r.report_text.split("part 2: seats added under R-50")[1]
        self.assertIn("step S3", part2)
        def mut2(b):
            b["layout"]["steps"].append({"step_id": "S3", "seat": "extra", "predicate_type": "extra"})
        r2 = self.run_bundle(self.mutate(mut2))
        part1 = r2.report_text.split("part 2: seats added under R-50")[0]
        self.assertIn("step S3", part1)

    def test_tiebreak_addition_governs_part2(self):
        def mut(b):
            link = dict(b["links"][0])
            link["performer_spawn_id"] = "agent-3"
            b["links"].append(link)
            rec = dict(b["spawn_records"]["records"][0])
            rec["agent_id"] = "agent-3"
            rec["session_id"] = "sess-3"
            b["spawn_records"]["records"].append(rec)
            b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-3", "recorded_at": T_EARLY, "origin": "addition"})
            b["roster"]["republications"] = [{"seat": "builder", "republished_at": "2026-01-01T02:00:00Z"}]
        r = self.run_bundle(self.mutate(mut))
        part2 = r.report_text.split("part 2: seats added under R-50")[1]
        self.assertIn("step S1", part2)

    def test_fallback_unparseable_entries_skipped(self):
        def mut(b):
            b["layout"]["steps"].append({"step_id": "S3", "seat": "extra", "predicate_type": "extra"})
            b["roster"]["entries"].append({"seat": "extra", "agent_id": "agent-9", "recorded_at": "not-a-time", "origin": "layout"})
        r = self.run_bundle(self.mutate(mut))
        part1 = r.report_text.split("part 2: seats added under R-50")[0]
        self.assertIn("step S3", part1)

    def test_republished_field_follows_selected_link_standing(self):
        # Two presented links for step S1 sit on opposite sides of the layout
        # entry time. The layout entry for seat builder is recorded at
        # 2026-01-01T06:00:00Z. The link that ran at 2026-01-01T05:00:00Z has
        # its seat not standing in the advance layout for that link, because
        # the layout entry is later than its ran_at. The link that ran at
        # 2026-01-01T12:00:00Z has its seat standing, because the layout entry
        # is not later than its ran_at. The R8-1 selection picks the first
        # matching link in links list order, so link order states which link
        # is selected in each run below.
        def make_mut(first_is_standing):
            def mut(b):
                standing = dict(b["links"][0])
                standing["performer_spawn_id"] = "agent-1"
                standing["ran_at"] = "2026-01-01T12:00:00Z"
                standing["produced_at"] = "2026-01-02T00:00:00Z"
                not_standing = dict(b["links"][0])
                not_standing["performer_spawn_id"] = "agent-3"
                not_standing["ran_at"] = "2026-01-01T05:00:00Z"
                not_standing["produced_at"] = "2026-01-02T00:00:00Z"
                s1_links = [standing, not_standing] if first_is_standing else [not_standing, standing]
                b["links"] = s1_links + [b["links"][1]]
                rec = dict(b["spawn_records"]["records"][0])
                rec["agent_id"] = "agent-3"
                rec["session_id"] = "sess-3"
                b["spawn_records"]["records"].append(rec)
                b["roster"]["entries"][0] = {"seat": "builder", "agent_id": "agent-1", "recorded_at": T_EARLY, "origin": "addition"}
                b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-3", "recorded_at": T_EARLY, "origin": "addition"})
                b["roster"]["entries"].append({"seat": "builder", "agent_id": "agent-9", "recorded_at": "2026-01-01T06:00:00Z", "origin": "layout"})
                b["roster"]["republications"] = [{"seat": "builder", "republished_at": "2026-01-01T04:00:00Z"}]
            return mut
        def s1_part2_line(report_text):
            part2 = report_text.split("part 2: seats added under R-50")[1]
            for line in part2.splitlines():
                if line.startswith("step S1 "):
                    return line
            raise AssertionError("no step S1 line in part 2: " + report_text)
        r = self.run_bundle(self.mutate(make_mut(False)))
        line = s1_part2_line(r.report_text)
        self.assertIn("republished=2026-01-01T04:00:00Z", line)
        r2 = self.run_bundle(self.mutate(make_mut(True)))
        line2 = s1_part2_line(r2.report_text)
        self.assertNotIn("republished=", line2)


if __name__ == "__main__":
    unittest.main()
