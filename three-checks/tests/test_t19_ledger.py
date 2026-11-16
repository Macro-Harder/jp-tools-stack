import unittest
from helpers import ThreeChecksCase


class TestT19Ledger(ThreeChecksCase):
    def test_every_claimed_element_present_passes(self):
        r = self.run_bundle()
        self.assertEqual(r.results["subresults"]["ledger"], "pass")

    def test_one_missing_element(self):
        def mut(b):
            b["claim"]["ledger_claims"] = ["E1", "E9"]
        r = self.run_bundle(self.mutate(mut))
        self.assert_entry(r, "COMP-LEDGER", subject="E9", part="stage", check="completeness", consequence="PARTIAL")

    def test_several_missing_one_entry_each(self):
        def mut(b):
            b["claim"]["ledger_claims"] = ["E8", "E9"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(len(r.entries("COMP-LEDGER")), 2)

    def test_ledger_entries_absent_one_per_element(self):
        def mut(b):
            del b["ledger_entries"]
            b["claim"]["ledger_claims"] = ["E1", "E2"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(len(r.entries("COMP-LEDGER")), 2)

    def test_empty_claims_pass_vacuously(self):
        def mut(b):
            b["claim"]["ledger_claims"] = []
            del b["ledger_entries"]
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 0, repr(r.results))
        self.assertEqual(r.results["subresults"]["ledger"], "pass")

    def test_exact_match_passes_case_difference_fails(self):
        r = self.run_bundle()
        self.assertEqual(r.results["subresults"]["ledger"], "pass")
        def mut(b):
            b["claim"]["ledger_claims"] = ["e1"]
        r2 = self.run_bundle(self.mutate(mut))
        self.assert_entry(r2, "COMP-LEDGER", subject="e1")


if __name__ == "__main__":
    unittest.main()
