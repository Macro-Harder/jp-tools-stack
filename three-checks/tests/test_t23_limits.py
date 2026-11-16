import os
import unittest
from helpers import ThreeChecksCase, STRENGTH_LINE


class TestT23Limits(ThreeChecksCase):
    def all_outputs(self):
        outputs = []
        outputs.append(self.run_bundle())
        def mut(b):
            b["claim"]["ledger_claims"] = ["E9"]
        outputs.append(self.run_bundle(self.mutate(mut)))
        outputs.append(self.run_bundle(verifier="agent-1"))
        return outputs

    def test_artifact_outside_landing_folder_read_not_written(self):
        # The bundle names an artifact by an absolute path standing in a
        # separate folder outside the folder the run writes its outputs to.
        # The artifact is read as an artifact file and never written: its
        # bytes and its modification time are recorded before the run and
        # asserted unchanged after it.
        import tempfile
        from helpers import ART_TEXT, ART_DIGEST
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_path = os.path.join(outside_dir, "outside-artifact.txt")
            with open(outside_path, "w") as handle:
                handle.write(ART_TEXT)
            before_bytes = open(outside_path, "rb").read()
            before_stat = os.stat(outside_path)
            def mut(b):
                b["layout"]["required_artifacts"][0]["path"] = outside_path
                b["layout"]["required_artifacts"][0]["sha256"] = ART_DIGEST
                b["links"][0]["subject_artifacts"] = [{"artifact_id": "A1", "sha256": ART_DIGEST}]
            r = self.run_bundle(self.mutate(mut), artifacts={})
            self.assertEqual(r.exit_status, 0, repr(r.results))
            after_bytes = open(outside_path, "rb").read()
            after_stat = os.stat(outside_path)
            self.assertEqual(after_bytes, before_bytes)
            self.assertEqual(after_stat.st_mtime_ns, before_stat.st_mtime_ns)

    def test_no_grade_above_l2_anywhere(self):
        for r in self.all_outputs():
            for text in (r.report_text or "", r.closure_text or ""):
                self.assertNotIn("L3", text)
                self.assertNotIn("grade=L", text.replace("grade=L2", ""))

    def test_no_per_link_grade_label(self):
        for r in self.all_outputs():
            self.assertNotIn("link grade", (r.report_text or "").lower())

    def test_unsupported_absent_and_cannot_run_never_silent(self):
        # Three elements, run as three separate runs, so no element rests on
        # an absence that would suppress its own entry. Each element is
        # asserted as reported, and never as silently passed.
        # One, an unsupported property, on a bundle whose completeness check
        # can run for the artifacts subresult.
        def mut_unsupported(b):
            b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "bogus-kind"}]
        r1 = self.run_bundle(self.mutate(mut_unsupported))
        self.assertEqual(r1.results["checks"]["completeness"], "fail")
        self.assert_entry(r1, "COMP-UNSUPPORTED-PROPERTY", subject="A1", part="stage", check="completeness")
        # Two, an absent record kind: the roster kind is absent from
        # record_sources while the roster section itself is present. That
        # absence is asserted under AUTH-ORIGIN for the kind roster.
        def mut_absent_kind(b):
            b["layout"]["record_sources"] = [e for e in b["layout"]["record_sources"] if e["record_kind"] != "roster"]
        r2 = self.run_bundle(self.mutate(mut_absent_kind))
        self.assert_entry(r2, "AUTH-ORIGIN", subject="roster", part="stage", check="authenticity")
        # Three, a check that cannot run: with the claim section absent,
        # completeness cannot run, and that state is reported through the
        # ABSENT-SECTION entry and the cannot_run check value.
        def mut_cannot_run(b):
            del b["claim"]
        r3 = self.run_bundle(self.mutate(mut_cannot_run))
        self.assert_entry(r3, "ABSENT-SECTION", subject="claim", part="stage", check="stage")
        self.assertEqual(r3.results["checks"]["completeness"], "cannot_run")
        self.assertEqual(r3.results["subresults"], {"links": "fail", "artifacts": "fail", "ledger": "fail"})

    def test_strength_line_seat_bound_wording(self):
        r = self.run_bundle()
        self.assertIn(STRENGTH_LINE, r.report_text)
        self.assertNotIn("runtime captured", r.report_text)

    def test_no_quality_or_gate_verdict_wording(self):
        for r in self.all_outputs():
            text = (r.report_text or "") + (r.closure_text or "")
            lowered = text.lower()
            self.assertNotIn("evidence of their quality", text.replace("it is not evidence of their quality", ""))
            self.assertNotIn("gate verdict", lowered)
            self.assertNotIn("high quality", lowered)

    def test_no_rederivation_as_pass_condition(self):
        for r in self.all_outputs():
            text = (r.report_text or "") + (r.closure_text or "")
            self.assertNotIn("re-derivation", text)
            self.assertNotIn("rederivation", text.lower().replace("re-derivation", ""))

    def test_run_writes_only_three_named_outputs(self):
        r = self.run_bundle()
        names = set(os.listdir(r.workdir))
        self.assertEqual(names, {"bundle.json", "artifact1.txt", "report.txt", "results.json", "closure.txt"}, repr(names))


if __name__ == "__main__":
    unittest.main()
