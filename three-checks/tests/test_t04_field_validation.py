import unittest
from helpers import ThreeChecksCase

PREFIX = "three-checks: input error: "


class TestT04FieldValidation(ThreeChecksCase):
    def check(self, mutator, expected):
        bundle = self.mutate(mutator)
        result = self.run_bundle(bundle)
        self.assertEqual(result.exit_status, 2, result.stderr)
        self.assertIn(PREFIX + expected, result.stderr)
        self.assert_no_file(result.report_path)
        self.assert_no_file(result.results_path)
        return result

    def test_unknown_top_level(self):
        self.check(lambda b: b.update({"bogus": 1}), "unknown field bogus")

    def test_unknown_inside_layout(self):
        self.check(lambda b: b["layout"].update({"bogus": 1}), "unknown field layout.bogus")

    def test_unknown_inside_roster(self):
        self.check(lambda b: b["roster"].update({"bogus": 1}), "unknown field roster.bogus")

    def test_unknown_inside_links_entry(self):
        self.check(lambda b: b["links"][0].update({"bogus": 1}), "unknown field links.0.bogus")

    def test_unknown_inside_spawn_records(self):
        self.check(lambda b: b["spawn_records"].update({"bogus": 1}), "unknown field spawn_records.bogus")

    def test_unknown_inside_identities(self):
        self.check(lambda b: b["identities"].update({"bogus": 1}), "unknown field identities.bogus")

    def test_unknown_inside_claim(self):
        self.check(lambda b: b["claim"].update({"bogus": 1}), "unknown field claim.bogus")

    def test_unknown_inside_push_record(self):
        self.check(lambda b: b["push_record"].update({"bogus": 1}), "unknown field push_record.bogus")

    def test_unknown_inside_previous_stage(self):
        def mut(b):
            b["previous_stage"] = {"stage_id": "prev", "outputs": [], "bogus": 1}
        self.check(mut, "unknown field previous_stage.bogus")

    def test_unknown_inside_ledger_entries(self):
        self.check(lambda b: b["ledger_entries"][0].update({"bogus": 1}), "unknown field ledger_entries.0.bogus")

    def test_unknown_nested_property_path_form(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["properties"] = [
                {"kind": "exists"}, {"kind": "exists", "bogus": 1}]
        result = self.mutate(mut)
        r = self.run_bundle(result)
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "unknown field layout.required_artifacts.0.properties.1.bogus", r.stderr)

    def test_unknown_nested_record_path_form(self):
        def mut(b):
            b["spawn_records"]["records"].append(dict(b["spawn_records"]["records"][0]))
            b["spawn_records"]["records"][2] = dict(b["spawn_records"]["records"][0])
            b["spawn_records"]["records"][2]["bogus"] = 1
        r = self.run_bundle(self.mutate(mut))
        self.assertEqual(r.exit_status, 2)
        self.assertIn(PREFIX + "unknown field spawn_records.records.2.bogus", r.stderr)

    def test_missing_required_field(self):
        def mut(b):
            del b["layout"]["stage_id"]
        self.check(mut, "layout.stage_id is missing")

    def test_wrong_kind_string(self):
        self.check(lambda b: b["layout"].update({"stage_id": []}), "layout.stage_id must be string")

    def test_wrong_kind_integer(self):
        self.check(lambda b: b["spawn_records"]["records"][0].update({"depth": "x"}), "spawn_records.records.0.depth must be integer")

    def test_wrong_kind_list(self):
        self.check(lambda b: b["layout"].update({"steps": {}}), "layout.steps must be list")

    def test_wrong_kind_object(self):
        self.check(lambda b: b.update({"layout": []}), "layout must be object")

    def test_allowed_set_origin(self):
        self.check(lambda b: b["roster"]["entries"][0].update({"origin": "bogus"}), "roster.entries.0.origin is outside its allowed set")

    def test_allowed_set_scoping_method(self):
        self.check(lambda b: b["spawn_records"]["scoping"].update({"method": "bogus"}), "spawn_records.scoping.method is outside its allowed set")

    def test_allowed_set_record_source_by_kind(self):
        self.check(lambda b: b["layout"]["record_sources"][0].update({"source": "api-verification"}), "layout.record_sources.0.source is outside its allowed set")

    def test_unknown_record_kind(self):
        def mut(b):
            b["layout"]["record_sources"][0]["record_kind"] = "bogus"
            b["layout"]["record_sources"][0]["source"] = "also-bogus-not-checked"
        result = self.check(mut, "layout.record_sources.0.record_kind is outside its allowed set")
        self.assertNotIn("record_sources.0.source", result.stderr)

    def test_empty_steps(self):
        self.check(lambda b: b["layout"].update({"steps": []}), "layout.steps is outside its allowed set")

    def test_count_below_zero(self):
        def mut(b):
            b["layout"]["required_artifacts"][0]["properties"] = [{"kind": "line_count_at_least", "count": -1}]
        self.check(mut, "layout.required_artifacts.0.properties.0.count is outside its allowed set")

    def test_depth_below_zero(self):
        self.check(lambda b: b["spawn_records"]["records"][0].update({"depth": -1}), "spawn_records.records.0.depth is outside its allowed set")

    def test_claim_stage_id_mismatch(self):
        def mut(b):
            b["claim"].update({"stage_id": "other-stage"})
            b["zzz_unknown"] = 1
        bundle = self.mutate(mut)
        result = self.run_bundle(bundle)
        self.assertEqual(result.exit_status, 2, result.stderr)
        self.assertIn(PREFIX + "claim.stage_id does not equal layout.stage_id", result.stderr)
        self.assert_no_file(result.report_path)
        self.assert_no_file(result.results_path)
        # Ordering position among the field errors: the per section claim
        # mismatch error stands before the unknown field error, which the
        # ordering rule places last. With no other field error in this bundle
        # the mismatch is the first error line and the unknown field follows.
        lines = [line for line in result.stderr.strip().splitlines() if line]
        self.assertEqual(lines[0], PREFIX + "claim.stage_id does not equal layout.stage_id")
        self.assertEqual(lines[1], PREFIX + "unknown field zzz_unknown")

    def test_field_name_with_quote_stays_one_line(self):
        def mut(b):
            b['we"ird'] = 1
        bundle = self.mutate(mut)
        r = self.run_bundle(bundle)
        self.assertEqual(r.exit_status, 2)
        for line in r.stderr.strip().splitlines():
            self.assertTrue(line.startswith(PREFIX))

    def test_field_name_with_newline_stays_one_line(self):
        def mut(b):
            b["we\nird"] = 1
        bundle = self.mutate(mut)
        r = self.run_bundle(bundle)
        self.assertEqual(r.exit_status, 2)
        lines = [line for line in r.stderr.strip().splitlines() if line]
        self.assertTrue(all(line.startswith(PREFIX) for line in lines))

    def test_mixed_error_ordering(self):
        raw = b'{"layout": {"stage_id": "stage-1", "stage_id": "x", "steps": [{"step_id": "S1", "seat": "s", "predicate_type": "p"}], "required_artifacts": [], "record_sources": []}, "zzz_unknown": 1, "aaa_unknown": 2}'
        r = self.run_bundle(bundle_bytes=raw)
        self.assertEqual(r.exit_status, 2)
        lines = r.stderr.strip().splitlines()
        self.assertIn("duplicate field", lines[0])
        self.assertLess(r.stderr.index("aaa_unknown"), r.stderr.index("zzz_unknown"))


if __name__ == "__main__":
    unittest.main()
