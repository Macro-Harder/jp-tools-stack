import unittest
from helpers import ThreeChecksCase


class TestT10AuthBinding(ThreeChecksCase):
    def test_bound_to_exactly_one_record_passes(self):
        r = self.run_bundle()
        self.assertEqual(r.exit_status, 0, repr(r.results))
        self.assertEqual(r.results["checks"]["authenticity"], "pass")

    def test_no_matching_spawn_record(self):
        def mut(b):
            b["links"][0]["performer_spawn_id"] = "agent-unknown"
            b["roster"]["entries"][0]["agent_id"] = "agent-unknown"
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 1)
        self.assert_entry(r, "AUTH-NO-SPAWN", subject="S1", check="authenticity", consequence="PARTIAL")

    def test_two_matching_spawn_records(self):
        def mut(b):
            b["spawn_records"]["records"].append(dict(b["spawn_records"]["records"][0]))
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-SPAWN", subject="S1")

    def test_duplicated_export_identity_no_link_binds(self):
        def mut(b):
            rec = dict(b["spawn_records"]["records"][0])
            rec["agent_id"] = "agent-x"
            rec["session_id"] = "sess-x1"
            b["spawn_records"]["records"].append(rec)
            rec2 = dict(rec)
            rec2["session_id"] = "sess-x2"
            b["spawn_records"]["records"].append(rec2)
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-SPAWN", subject="agent-x", part="stage")

    def test_two_unbound_unparseable_creation_entries_creation_order(self):
        def mut(b):
            for sess in ("sess-u1", "sess-u2"):
                rec = dict(b["spawn_records"]["records"][0])
                rec["agent_id"] = "agent-u"
                rec["session_id"] = sess
                rec["created_at"] = "not-a-time"
                b["spawn_records"]["records"].append(rec)
        r = self.run_bundle(self.mutate(mut))
        entries = r.entries("AUTH-STEP-TIME")
        stage_entries = [e for e in entries if e["part"] == "stage" and e["subject"] == "agent-u"]
        self.assertEqual(len(stage_entries), 2)
        self.assertIn("sess-u1", stage_entries[0]["found"])
        self.assertIn("sess-u2", stage_entries[1]["found"])

    def test_unbound_shared_agent_one_unparseable(self):
        def mut(b):
            rec = dict(b["spawn_records"]["records"][0])
            rec["agent_id"] = "agent-u"
            rec["session_id"] = "sess-good"
            b["spawn_records"]["records"].append(rec)
            rec2 = dict(rec)
            rec2["session_id"] = "sess-bad"
            rec2["created_at"] = "not-a-time"
            b["spawn_records"]["records"].append(rec2)
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-STEP-TIME", subject="agent-u", part="stage")
        self.assertIn("sess-bad", entry["found"])

    def test_creation_equal_to_ran_at_passes(self):
        def mut(b):
            b["spawn_records"]["records"][0]["created_at"] = b["links"][0]["ran_at"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["checks"]["authenticity"], "pass")

    def test_creation_one_second_after_ran_at_fails(self):
        def mut(b):
            b["spawn_records"]["records"][0]["created_at"] = "2026-01-01T12:00:01Z"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-STEP-TIME", subject="S1", check="authenticity")

    def test_creation_one_second_before_ran_at_passes(self):
        def mut(b):
            b["spawn_records"]["records"][0]["created_at"] = "2026-01-01T11:59:59Z"
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.results["checks"]["authenticity"], "pass")

    def test_only_first_failing_subtest_reported(self):
        def mut(b):
            b["links"][0]["performer_spawn_id"] = "agent-unknown"
            b["roster"]["entries"] = []
        r = self.run_bundle(self.mutate(mut))
        s1_codes = [e["code"] for e in r.results["discrepancies"] if e["subject"] == "S1"]
        self.assertIn("AUTH-NO-SPAWN", s1_codes)
        self.assertNotIn("AUTH-NO-ROSTER", s1_codes)

    def test_authenticity_applied_in_links_order(self):
        def mut(b):
            for link in b["links"]:
                link["performer_spawn_id"] = "agent-unknown-" + link["step_id"]
        r = self.run_bundle(self.mutate(mut))
        subjects = [e["subject"] for e in r.entries("AUTH-NO-SPAWN")]
        self.assertEqual(subjects, ["S1", "S2"])

    def test_orphan_link_only_link_no_step_entry(self):
        def mut(b):
            link = dict(b["links"][0])
            link["step_id"] = "S9"
            link["performer_spawn_id"] = "agent-unknown"
            b["links"].append(link)
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "LINK-NO-STEP", subject="S9", part="stage", check="authenticity", consequence="PARTIAL")
        orphan_entries = [e for e in r.results["discrepancies"] if e["subject"] == "S9"]
        self.assertEqual([e["code"] for e in orphan_entries], ["LINK-NO-STEP"])
        self.assertEqual(r.results["checks"]["authenticity"], "fail")


if __name__ == "__main__":
    unittest.main()
