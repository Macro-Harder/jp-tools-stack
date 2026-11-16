import unittest
from helpers import ThreeChecksCase, MAT_DIGEST, MAT_DIGEST_B

SOURCE_WORDS = "the stage claims predecessor inputs and the previous stage has no recorded outputs"


def with_boundary(b, pred=None, prev_outputs=None, prev_absent=False):
    b["claim"]["predecessor_inputs"] = pred
    if prev_absent:
        b.pop("previous_stage", None)
    elif prev_outputs is not None:
        b["previous_stage"] = {"stage_id": "prev", "outputs": prev_outputs}


class TestT16Boundary(ThreeChecksCase):
    def test_predecessor_null_not_applicable(self):
        r = self.run_bundle()
        self.assertIn("boundary: not applicable", r.report_text)

    def test_predecessor_empty_list_not_applicable(self):
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[])))
        self.assertIn("boundary: not applicable", r.report_text)

    def test_predecessor_matched(self):
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST}], prev_outputs=[{"name": "m1", "sha256": MAT_DIGEST}])))
        self.assertIn("boundary: matched", r.report_text)
        self.assertEqual(r.exit_status, 0, repr(r.results))

    def test_name_mismatch(self):
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST}], prev_outputs=[{"name": "m2", "sha256": MAT_DIGEST}])))
        self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary", part="stage")

    def test_digest_mismatch(self):
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST}], prev_outputs=[{"name": "m1", "sha256": MAT_DIGEST_B}])))
        self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary")

    def test_duplicated_name_in_predecessor(self):
        pred = [{"name": "m1", "sha256": MAT_DIGEST}, {"name": "m1", "sha256": MAT_DIGEST}]
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=pred, prev_outputs=[{"name": "m1", "sha256": MAT_DIGEST}])))
        entry = self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary")
        self.assertIn("duplicated", entry["found"])

    def test_duplicated_name_in_previous_outputs(self):
        prev = [{"name": "m1", "sha256": MAT_DIGEST}, {"name": "m1", "sha256": MAT_DIGEST}]
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST}], prev_outputs=prev)))
        self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary")

    def test_previous_absent_source_words_partial(self):
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST}], prev_absent=True)))
        entry = self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary", consequence="PARTIAL")
        self.assertEqual(entry["found"], SOURCE_WORDS)

    def test_previous_empty_outputs_source_words(self):
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST}], prev_outputs=[])))
        entry = self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary")
        self.assertEqual(entry["found"], SOURCE_WORDS)

    def test_duplicated_and_mismatching_two_entries(self):
        pred = [{"name": "m1", "sha256": MAT_DIGEST}, {"name": "m1", "sha256": MAT_DIGEST}]
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=pred, prev_outputs=[{"name": "m1", "sha256": MAT_DIGEST_B}])))
        self.assertEqual(len(r.entries("CHAIN-BOUNDARY")), 2, repr(r.entries("CHAIN-BOUNDARY")))

    def test_duplicated_and_mismatching_overlap_in_previous_outputs(self):
        # The R9-4 overlap with the duplication inside previous_stage outputs:
        # the name is duplicated inside the previous stage outputs and also
        # mismatches the predecessor inputs, so two entries stand.
        prev = [{"name": "m1", "sha256": MAT_DIGEST}, {"name": "m1", "sha256": MAT_DIGEST}]
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST_B}], prev_outputs=prev)))
        entries = r.entries("CHAIN-BOUNDARY")
        self.assertEqual(len(entries), 2, repr(entries))
        founds = [e["found"] for e in entries]
        self.assertTrue(any("duplicated" in f for f in founds))

    def test_boundary_runs_under_absences(self):
        for section in ("roster", "links", "spawn_records", "identities"):
            with self.subTest(section=section):
                def mut(b, section=section):
                    del b[section]
                    with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST}], prev_outputs=[{"name": "m1", "sha256": MAT_DIGEST_B}])
                r = self.run_bundle(self.mutate(mut))
                self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary")

    def test_boundary_not_run_layout_absent(self):
        def mut(b):
            del b["layout"]
            with_boundary(b, pred=[{"name": "m1", "sha256": MAT_DIGEST}], prev_absent=True)
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.entries("CHAIN-BOUNDARY"), [])
        self.assertIn("boundary: not applicable", r.report_text)

    def test_identical_out_of_form_digest_both_sides_fails(self):
        r = self.run_bundle(self.mutate(lambda b: with_boundary(b, pred=[{"name": "m1", "sha256": "XYZ"}], prev_outputs=[{"name": "m1", "sha256": "XYZ"}])))
        self.assert_entry(r, "CHAIN-BOUNDARY", subject="boundary")


if __name__ == "__main__":
    unittest.main()
