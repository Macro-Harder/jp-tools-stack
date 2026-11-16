import unittest
from helpers import ThreeChecksCase


def set_source(b, kind, source):
    for entry in b["layout"]["record_sources"]:
        if entry["record_kind"] == kind:
            entry["source"] = source


class TestT13OriginPush(ThreeChecksCase):
    def test_roster_runtime_source_passes(self):
        r = self.run_bundle()
        self.assertEqual(r.exit_status, 0, repr(r.results))

    def test_roster_self_reported_fails(self):
        r = self.run_bundle(self.mutate(lambda b: set_source(b, "roster", "self-reported-file")))
        self.assert_entry(r, "AUTH-ORIGIN", subject="roster", part="stage")

    def test_roster_no_entry_fails(self):
        def mut(b):
            b["layout"]["record_sources"] = [e for e in b["layout"]["record_sources"] if e["record_kind"] != "roster"]
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-ORIGIN", subject="roster", part="stage")

    def test_roster_duplicate_failing_source_governs(self):
        def mut(b):
            b["layout"]["record_sources"].append({"record_kind": "roster", "source": "self-reported-file"})
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-ORIGIN", subject="roster")

    def test_push_api_source_in_play_passes(self):
        def mut(b):
            b["claim"]["push_link"] = {"repo": "repo-1", "head_sha": "h1", "tree_sha": "t1"}
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))

    def test_push_self_reported_in_play_fails(self):
        def mut(b):
            set_source(b, "push", "self-reported-file")
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-ORIGIN", subject="push", part="stage")

    def test_push_no_entry_in_play_fails(self):
        def mut(b):
            b["layout"]["record_sources"] = [e for e in b["layout"]["record_sources"] if e["record_kind"] != "push"]
            b["claim"]["push_link"] = {"repo": "repo-1", "head_sha": "h1", "tree_sha": "t1"}
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-ORIGIN", subject="push")

    def test_push_in_play_record_absent(self):
        def mut(b):
            del b["push_record"]
            b["claim"]["push_link"] = {"repo": "repo-1", "head_sha": "h1", "tree_sha": "t1"}
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-PUSH", subject="push")

    def test_push_link_equal_all_fields_passes(self):
        def mut(b):
            b["claim"]["push_link"] = {"repo": "repo-1", "head_sha": "h1", "tree_sha": "t1"}
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))

    def test_push_mismatch_repo(self):
        def mut(b):
            b["claim"]["push_link"] = {"repo": "other", "head_sha": "h1", "tree_sha": "t1"}
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-ORIGIN", subject="push")
        self.assertIn("repo", entry["found"])

    def test_push_mismatch_head_sha(self):
        def mut(b):
            b["claim"]["push_link"] = {"repo": "repo-1", "head_sha": "other", "tree_sha": "t1"}
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-ORIGIN", subject="push")
        self.assertIn("head_sha", entry["found"])

    def test_push_mismatch_tree_sha(self):
        def mut(b):
            b["claim"]["push_link"] = {"repo": "repo-1", "head_sha": "h1", "tree_sha": "other"}
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "AUTH-ORIGIN", subject="push")
        self.assertIn("tree_sha", entry["found"])

    def test_push_in_play_by_sources_alone_no_hash_comparison(self):
        def mut(b):
            b["push_record"]["head_sha"] = "different"
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))

    def test_push_record_present_no_push_in_play_no_test(self):
        def mut(b):
            b["layout"]["record_sources"] = [e for e in b["layout"]["record_sources"] if e["record_kind"] != "push"]
            b["push_record"]["verified_at"] = "not-a-time"
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))

    def test_self_reported_links_kind(self):
        r = self.run_bundle(self.mutate(lambda b: set_source(b, "links", "self-reported-file")))
        self.assert_entry(r, "AUTH-ORIGIN", subject="links", part="stage")

    def test_self_reported_claim_kind(self):
        r = self.run_bundle(self.mutate(lambda b: set_source(b, "claim", "self-reported-file")))
        self.assert_entry(r, "AUTH-ORIGIN", subject="claim", part="stage")

    def test_self_reported_ledger_kind(self):
        r = self.run_bundle(self.mutate(lambda b: set_source(b, "ledger", "self-reported-file")))
        self.assert_entry(r, "AUTH-ORIGIN", subject="ledger", part="stage")

    def test_stage_record_kinds_no_origin_result(self):
        r = self.run_bundle()
        self.assertEqual(r.entries("AUTH-ORIGIN"), [])


if __name__ == "__main__":
    unittest.main()
