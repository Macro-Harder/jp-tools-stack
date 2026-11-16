import os
import unittest
from helpers import ThreeChecksCase, STRENGTH_LINE


class TestT09Barred(ThreeChecksCase):
    def barred(self, verifier, mutator=None, preexisting=None):
        bundle = self.mutate(mutator) if mutator else None
        return self.run_bundle(bundle, verifier=verifier, preexisting=preexisting)

    def check_barred(self, verifier, bar_word, mutator=None):
        r = self.barred(verifier, mutator)
        self.assertEqual(r.exit_status, 4, r.stderr)
        self.assertIn("outcome=BARRED", r.report_text)
        self.assertIn("barred: verifier is " + bar_word, r.report_text)
        self.assertIn(STRENGTH_LINE, r.report_text)
        # The barred report form exactly: no check lines appear in it.
        self.assertNotIn("authenticity:", r.report_text)
        self.assertNotIn("chain:", r.report_text)
        self.assertNotIn("completeness:", r.report_text)
        self.assertNotIn("  links:", r.report_text)
        self.assertNotIn("boundary:", r.report_text)
        self.assert_no_file(r.results_path)
        self.assert_no_file(r.closure_path)
        return r

    def test_verifier_is_performer(self):
        self.check_barred("agent-1", "performer")

    def test_verifier_is_coordinator(self):
        self.check_barred("coord-1", "coordinator")

    def test_verifier_is_commissioner_stage(self):
        self.check_barred("comm-stage", "commissioner_stage")

    def test_verifier_is_commissioner_work(self):
        self.check_barred("comm-work", "commissioner_work")

    def test_precedence_performer_first(self):
        def mut(b):
            b["identities"]["coordinator"] = "agent-1"
        self.check_barred("agent-1", "performer", mut)

    def test_precedence_commissioner_stage_over_commissioner_work(self):
        def mut(b):
            b["identities"]["commissioner_work"] = "comm-stage"
        self.check_barred("comm-stage", "commissioner_stage", mut)

    def test_precedence_coordinator_over_commissioners(self):
        def mut(b):
            b["identities"]["commissioner_stage"] = "coord-1"
            b["identities"]["commissioner_work"] = "coord-1"
        self.check_barred("coord-1", "coordinator", mut)

    def test_identities_absent_performer_match_barred(self):
        def mut(b):
            del b["identities"]
        self.check_barred("agent-2", "performer", mut)

    def test_identities_absent_no_match_not_barred(self):
        def mut(b):
            del b["identities"]
        r = self.barred("verifier-1", mut)
        self.assertNotEqual(r.exit_status, 4)
        self.assertEqual(r.exit_status, 3)

    def test_barred_with_layout_absent_header_fallback(self):
        def mut(b):
            del b["layout"]
        r = self.check_barred("agent-1", "performer", mut)
        self.assertIn("stage=absent", r.report_text)

    def test_barred_with_spawn_records_absent_provenance_fallbacks(self):
        def mut(b):
            del b["spawn_records"]
        r = self.check_barred("agent-1", "performer", mut)
        self.assertIn("exporter=absent", r.report_text)
        self.assertIn("exported_at=absent", r.report_text)
        self.assertIn("scoping=absent", r.report_text)
        self.assertIn("source_database=absent", r.report_text)

    def test_barred_leaves_existing_results_and_closure_untouched(self):
        r = self.barred("agent-1", preexisting={"results": "old results", "closure": "old closure"})
        self.assertEqual(r.exit_status, 4)
        with open(r.results_path) as handle:
            self.assertEqual(handle.read(), "old results")
        with open(r.closure_path) as handle:
            self.assertEqual(handle.read(), "old closure")

    def test_barred_report_form_exact_provenance_block(self):
        import hashlib
        r = self.check_barred("agent-1", "performer")
        with open(os.path.join(r.workdir, "bundle.json"), "rb") as handle:
            bundle_digest = hashlib.sha256(handle.read()).hexdigest()
        lines = r.report_text.splitlines()
        self.assertEqual(lines, [
            "tool=three-checks version=1.0.0",
            "stage=stage-1",
            "outcome=BARRED",
            "consequence=none",
            "context=none",
            "barred: verifier is performer",
            "bundle_sha256=" + bundle_digest,
            "verifier=agent-1",
            "exporter=runtime exported_at=2026-01-01T00:00:00Z scoping=identity_list",
            "source_database=spawn-db",
            "sections present: layout, roster, links, spawn_records, identities, claim, push_record, ledger_entries",
            "sections absent: previous_stage",
            "push: repo=repo-1 verified_by=verifier-x verified_at=2026-01-01T00:00:00Z origin=api-verification at assembly",
            STRENGTH_LINE,
        ])

    def test_verifier_equal_only_to_exporter_not_barred(self):
        r = self.barred("runtime")
        self.assertEqual(r.exit_status, 0, repr(r.results))

    def test_verifier_equal_only_to_verified_by_not_barred(self):
        r = self.barred("verifier-x")
        self.assertEqual(r.exit_status, 0, repr(r.results))


if __name__ == "__main__":
    unittest.main()
