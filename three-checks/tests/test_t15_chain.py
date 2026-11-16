import unittest
from helpers import ThreeChecksCase, MAT_DIGEST, MAT_DIGEST_B


class TestT15Chain(ThreeChecksCase):
    def test_matching_join_passes(self):
        r = self.run_bundle()
        self.assertEqual(r.results["checks"]["chain"], "pass")
        self.assertIn("join S1 -> S2: pass", r.report_text)

    def test_extra_name_on_later_side(self):
        def mut(b):
            b["links"][1]["inputs"].append({"name": "extra", "sha256": MAT_DIGEST})
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")
        self.assertIn("extra", entry["found"])

    def test_missing_name_on_later_side(self):
        def mut(b):
            b["links"][1]["inputs"] = []
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")
        self.assertIn("m1", entry["found"])

    def test_differing_digest_named(self):
        def mut(b):
            b["links"][1]["inputs"][0]["sha256"] = MAT_DIGEST_B
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")
        self.assertIn("m1", entry["found"])

    def test_one_mismatching_pair_among_many_fails(self):
        def mut(b):
            link = dict(b["links"][0])
            link["outputs"] = [{"name": "m1", "sha256": MAT_DIGEST_B}]
            b["links"].insert(1, link)
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")

    def test_two_distinct_failing_names_two_entries(self):
        def mut(b):
            b["links"][0]["outputs"] = [{"name": "m1", "sha256": MAT_DIGEST}, {"name": "m2", "sha256": MAT_DIGEST}]
            b["links"][1]["inputs"] = [{"name": "m1", "sha256": MAT_DIGEST_B}, {"name": "m2", "sha256": MAT_DIGEST_B}]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(len(r.entries("CHAIN-JOIN")), 2)

    def test_duplicated_name_agreeing_digests(self):
        def mut(b):
            b["links"][0]["outputs"].append({"name": "m1", "sha256": MAT_DIGEST})
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")
        self.assertIn("duplicated", entry["found"])

    def test_duplicated_name_differing_digests(self):
        def mut(b):
            b["links"][0]["outputs"].append({"name": "m1", "sha256": MAT_DIGEST_B})
            b["links"][1]["inputs"][0]["sha256"] = MAT_DIGEST_B
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")

    def test_duplicated_and_mismatching_two_entries(self):
        def mut(b):
            b["links"][0]["outputs"].append({"name": "m1", "sha256": MAT_DIGEST})
            b["links"][1]["inputs"][0]["sha256"] = MAT_DIGEST_B
        r = self.run_bundle(self.mutate(mut))
        entries = r.entries("CHAIN-JOIN")
        self.assertEqual(len(entries), 2, repr(entries))
        founds = [e["found"] for e in entries]
        self.assertTrue(any("duplicated" in f for f in founds))
        self.assertTrue(any("differs" in f for f in founds))

    def test_duplicated_and_mismatching_overlap_digests_differing(self):
        # The R9-4 overlap with its digests differing: the duplicated name
        # inside the earlier outputs list carries two differing digests, and
        # the name also mismatches the later side, so two entries stand, one
        # duplicated name entry and one failing name entry.
        def mut(b):
            b["links"][0]["outputs"].append({"name": "m1", "sha256": MAT_DIGEST_B})
        r = self.run_bundle(self.mutate(mut))
        entries = r.entries("CHAIN-JOIN")
        self.assertEqual(len(entries), 2, repr(entries))
        founds = [e["found"] for e in entries]
        self.assertTrue(any("duplicated" in f for f in founds))
        self.assertTrue(any("differs" in f for f in founds))

    def test_step_with_no_matching_link_both_joins_unable(self):
        # A middle step with no matching link: each of its joins, on both
        # sides of the step, fails as unable to run, one entry per join.
        def mut(b):
            b["layout"]["steps"].append({"step_id": "S3", "seat": "reviewer", "predicate_type": "review"})
            b["claim"]["steps_claimed"].append("S3")
            b["claim"]["step_completions"].append({"step_id": "S3", "completed_at": "2026-01-03T00:00:00Z"})
            link = dict(b["links"][1])
            link["step_id"] = "S3"
            link["inputs"] = []
            link["outputs"] = []
            b["links"].append(link)
            b["links"] = [item for item in b["links"] if item["step_id"] != "S2"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(len(r.entries("CHAIN-JOIN")), 2, repr(r.entries("CHAIN-JOIN")))
        first = self.assert_entry_for_subject(r, "CHAIN-JOIN", "S1 -> S2", count=1)
        self.assertIn("no matching link", first["found"])
        second = self.assert_entry_for_subject(r, "CHAIN-JOIN", "S2 -> S3", count=1)
        self.assertIn("no matching link", second["found"])

    def test_step_no_matching_link_joins_unable(self):
        def mut(b):
            b["links"] = [link for link in b["links"] if link["step_id"] != "S1"]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")
        self.assertIn("no matching link", entry["found"])

    def test_both_steps_no_matching_link_one_entry(self):
        def mut(b):
            b["links"] = []
        r = self.run_bundle(self.mutate(mut))
        entries = r.entries("CHAIN-JOIN")
        self.assertEqual(len(entries), 1, repr(entries))
        self.assertIn("S1", entries[0]["found"])
        self.assertIn("S2", entries[0]["found"])

    def test_only_reconstructed_links_joins_unable_no_double_count(self):
        def mut(b):
            del b["links"][0]["produced_at"]
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")
        s1_auth = [e for e in r.results["discrepancies"] if e["subject"] == "S1" and e["check"] == "authenticity"]
        self.assertEqual(s1_auth, [])

    def test_single_step_layout_no_joins(self):
        def mut(b):
            b["layout"]["steps"] = b["layout"]["steps"][:1]
            b["links"] = b["links"][:1]
            b["claim"]["steps_claimed"] = ["S1"]
            b["claim"]["step_completions"] = b["claim"]["step_completions"][:1]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))
        self.assertNotIn("join ", r.report_text)

    def test_identical_out_of_form_digest_both_sides_fails(self):
        def mut(b):
            b["links"][0]["outputs"][0]["sha256"] = "XYZ"
            b["links"][1]["inputs"][0]["sha256"] = "XYZ"
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "CHAIN-JOIN", subject="S1 -> S2")


if __name__ == "__main__":
    unittest.main()
