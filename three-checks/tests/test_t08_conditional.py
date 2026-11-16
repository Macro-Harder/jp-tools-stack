import unittest
from helpers import ThreeChecksCase

PUSH = {"repo": "repo-1", "branch": "main", "head_sha": "h1", "tree_sha": "t1", "verified_by": "verifier-x", "verified_at": "2026-01-01T00:00:00Z"}


class TestT08Conditional(ThreeChecksCase):
    def test_push_absent_where_push_link_named(self):
        def mut(b):
            b["claim"]["push_link"] = {"repo": "repo-1", "head_sha": "h1", "tree_sha": "t1"}
            del b["push_record"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 1)
        self.assert_entry(r, "AUTH-NO-PUSH", subject="push", part="stage", check="authenticity")

    def test_push_absent_where_record_sources_names_push(self):
        def mut(b):
            del b["push_record"]
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "AUTH-NO-PUSH", subject="push", part="stage")

    def test_push_absent_no_trigger_no_defect(self):
        def mut(b):
            del b["push_record"]
            b["layout"]["record_sources"] = [e for e in b["layout"]["record_sources"] if e["record_kind"] != "push"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, r.stderr + repr(r.results))
        self.assertEqual(r.entries("AUTH-NO-PUSH"), [])
        self.assertEqual(r.entries("AUTH-ORIGIN"), [])

    def test_push_present_no_trigger_reported_untested(self):
        def mut(b):
            b["layout"]["record_sources"] = [e for e in b["layout"]["record_sources"] if e["record_kind"] != "push"]
            b["push_record"] = dict(PUSH)
            b["push_record"]["head_sha"] = "different"
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))
        self.assertIn("push: repo=repo-1", r.report_text)

    def test_previous_stage_absent_with_predecessor_inputs(self):
        def mut(b):
            b["claim"]["predecessor_inputs"] = [{"name": "m1", "sha256": "a" * 64}]
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary", part="stage", consequence="PARTIAL")
        self.assertEqual(entry["found"], "the stage claims predecessor inputs and the previous stage has no recorded outputs")

    def test_previous_stage_empty_outputs_with_predecessor_inputs(self):
        def mut(b):
            b["claim"]["predecessor_inputs"] = [{"name": "m1", "sha256": "a" * 64}]
            b["previous_stage"] = {"stage_id": "prev", "outputs": []}
        r = self.run_bundle(self.mutate(mut))
        entry = self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary")
        self.assertEqual(entry["found"], "the stage claims predecessor inputs and the previous stage has no recorded outputs")

    def test_ledger_entries_absent_with_claims(self):
        def mut(b):
            del b["ledger_entries"]
            b["claim"]["ledger_claims"] = ["E1", "E2"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(len(r.entries("COMP-LEDGER")), 2, repr(r.entries("COMP-LEDGER")))
        self.assert_entry_for_subject(r, "COMP-LEDGER", "E1", part="stage", count=1)
        self.assert_entry_for_subject(r, "COMP-LEDGER", "E2", part="stage", count=1)

    def test_ledger_entries_absent_claims_empty_no_defect(self):
        def mut(b):
            del b["ledger_entries"]
            b["claim"]["ledger_claims"] = []
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))
        self.assertEqual(r.entries("COMP-LEDGER"), [])

    def test_conditional_section_malformed_is_input_error(self):
        def mut(b):
            b["push_record"] = {"repo": 7}
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn("three-checks: input error:", r.stderr)


if __name__ == "__main__":
    unittest.main()
