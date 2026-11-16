"""T14, arithmetic, counts, and precedence. Brief section 9; plan part 4.11."""

import unittest

from rcg_common import (
    RcgTestCase, pass_specs, assert_ie, IE_WORDINGS, JUDGE, AUTHOR,
    default_spec,
)


def finalise(tc, w, specs, **kw):
    w.write_verdicts(specs, **kw.get("verdict_kw", {}))
    return w.run("finalise", context="stated", **kw.get("run_kw", {}))


class TestItemRuleOrder(RcgTestCase):
    def test_unexcused_fail_beats_unjudgeable(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        specs[1]["word"] = "UNJUDGEABLE"
        p = finalise(self, w, specs)
        self.assertEqual(p.returncode, 1, p.stderr)
        data = w.read_results()
        item = [i for i in data["items"] if i["label"] == "A1"][0]
        self.assertEqual(item["outcome"], "fail")

    def test_excused_fail_with_unjudgeable_is_unverifiable(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        specs[0]["claim"] = {"queue_item": "DQ-101", "ruling_date": "2026-11-01", "confirming_judge": JUDGE}
        specs[1]["word"] = "UNJUDGEABLE"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 4, p.stderr)
        data = w.read_results()
        item = [i for i in data["items"] if i["label"] == "A1"][0]
        self.assertEqual(item["outcome"], "unverifiable")
        self.assertEqual(data["counts"]["failed_excused"], 1)

    def test_excused_fail_alone_is_re_ruled_pass(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        specs[0]["claim"] = {"queue_item": "DQ-101", "ruling_date": "2026-11-01", "confirming_judge": JUDGE}
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 5, p.stderr)

    def test_all_pass_is_pass(self):
        w = self.world()
        p = finalise(self, w, pass_specs())
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        self.assertEqual(data["counts"], {"checks_run": 3, "passed": 3, "failed": 0,
                                          "failed_excused": 0, "failed_unexcused": 0,
                                          "unjudgeable": 0, "missing": 0})


class TestSubsetSpecialItems(RcgTestCase):
    def test_no_touch_item_passes_with_zero_checks(self):
        w = self.world()
        spec = [("A1", None, "No touch basis for A1."),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        w.write_verdicts([{"label": "A2", "id": "C-002"}], checked_ids=["C-002"])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        item = [i for i in data["items"] if i["label"] == "A1"][0]
        self.assertEqual(item["outcome"], "pass")
        self.assertTrue(item["no_touch"])
        self.assertEqual(item["checked_ids"], [])
        self.assertIn("no-touch", w.read_out1())

    def test_empty_selection_item_is_unverifiable_subset(self):
        w = self.world()
        spec = [("A1", ["Gap 9"], {"Gap 9": "Basis prose."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        w.write_verdicts([{"label": "A2", "id": "C-002"}], checked_ids=["C-002"])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 4, p.stderr)
        data = w.read_results()
        item = [i for i in data["items"] if i["label"] == "A1"][0]
        self.assertEqual(item["outcome"], "unverifiable")

    def test_no_touch_run_completes_as_pass(self):
        w = self.world()
        spec = [("A1", None, "No touch basis for A1."), ("A2", None, "No touch basis for A2.")]
        w.set_declaration(spec)
        w.write_verdicts([], checked_ids=[])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        self.assertEqual(data["outcome"], "pass")
        self.assertEqual(data["counts"]["checks_run"], 0)
        text = w.read_out1()
        self.assertIn("no entry was touched", text)
        self.assertIn("indexes searched: none", text)

    def test_full_mode_no_touch_rule_silent(self):
        w = self.world()
        spec = [("A1", None, "No touch basis for A1."),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        from rcg_common import ROW_BY_ID
        pairs = [(label, cid) for label in ("A1", "A2") for cid in sorted(ROW_BY_ID)]
        w.write_verdicts([{"label": l, "id": c} for l, c in pairs],
                         declared_mode="full", effective_mode="full",
                         checked_ids=sorted(ROW_BY_ID))
        p = w.run("finalise", context="stated", declared_mode="full")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        item = [i for i in data["items"] if i["label"] == "A1"][0]
        self.assertEqual(len(item["checked_ids"]), 6)


class TestRunOutcomeOrder(RcgTestCase):
    def test_fail_over_unverifiable_over_re_ruled_over_pass(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        specs[0]["claim"] = {"queue_item": "DQ-101", "ruling_date": "2026-11-01", "confirming_judge": JUDGE}
        specs[2]["word"] = "UNJUDGEABLE"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 4, p.stderr)
        self.assertEqual(w.read_results()["outcome"], "unverifiable")

    def test_blocked_item_lines_carry_unexcused_counts_only(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        specs[0]["claim"] = {"queue_item": "DQ-101", "ruling_date": "2026-11-01", "confirming_judge": JUDGE}
        specs[1]["word"] = "FAIL"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 1, p.stderr)
        text = w.read_out1()
        self.assertIn("blocked item: A1, unexcused fails: 1", text)
        self.assertNotIn("blocked item: A1, unexcused fails: 2", text)


class TestCountsReconciliation(RcgTestCase):
    def test_reconciliation_on_mixed_record(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        specs[1]["word"] = "UNJUDGEABLE"
        p = finalise(self, w, specs)
        data = w.read_results()
        c = data["counts"]
        self.assertEqual(c["passed"] + c["failed"] + c["unjudgeable"] + c["missing"], c["checks_run"])
        self.assertEqual(c["failed"], c["failed_excused"] + c["failed_unexcused"])

    def test_incomplete_item_with_present_pass_is_incomplete_never_pass(self):
        w = self.world()
        specs = [s for s in pass_specs() if not (s["label"] == "A1" and s["id"] == "C-003")]
        p = finalise(self, w, specs)
        self.assertEqual(p.returncode, 3, p.stderr)
        data = w.read_results()
        item = [i for i in data["items"] if i["label"] == "A1"][0]
        self.assertEqual(item["outcome"], "incomplete")
        self.assertEqual(data["outcome"], "incomplete")

    def test_incomplete_record_still_classifies_confirmed_excuse(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        specs[0]["claim"] = {"queue_item": "DQ-101", "ruling_date": "2026-11-01", "confirming_judge": JUDGE}
        specs = [s for s in specs if not (s["label"] == "A2")]
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 3, p.stderr)
        data = w.read_results()
        self.assertEqual(data["outcome"], "incomplete")
        self.assertEqual(data["counts"]["failed_excused"], 1)
        self.assertEqual(data["counts"]["missing"], 1)
        text = w.read_out1()
        self.assertIn("trace excerpt: RE-RULED, queue item DQ-101", text)


def drive_seam(tc, w, form, probe, **run_kw):
    import subprocess, sys
    from rcg_common import TESTS_DIR
    args_file = w.dir / "seam_args.txt"
    result_file = w.dir / "seam_result.txt"
    args_file.write_text("\n".join(w.args(form, context="stated", **run_kw)) + "\n")
    proc = subprocess.run(
        [sys.executable, str(TESTS_DIR / "selftest_driver.py"), probe,
         str(args_file), str(result_file)],
        capture_output=True, text=True, timeout=120)
    tc.assertEqual(proc.returncode, 0, proc.stderr)
    return result_file.read_text().splitlines()[0]


class TestPrecedence(RcgTestCase):
    def test_barred_before_self_test_at_worksheet(self):
        w = self.world()
        status = drive_seam(self, w, "worksheet", "blocking_probe", judge=AUTHOR)
        self.assertEqual(status, "6")
        text = w.read_out1()
        self.assertIn("barred:", text)
        self.assertNotIn("probe blocking_probe: fail", text)

    def test_self_test_before_declaration_conflict_at_finalise(self):
        w = self.world()
        w.set_amendment([("A1", "The wording names Gap 7 plainly."),
                         ("A2", "The amendment changes the counting text.")])
        w.set_declaration(default_spec())
        w.write_verdicts(pass_specs())
        status = drive_seam(self, w, "finalise", "blocking_probe")
        self.assertEqual(status, "8")
        text = w.read_out1()
        self.assertIn("probe blocking_probe: fail, forced by the test seam", text)
        self.assertIn("exit status: 8", text)
        self.assertFalse(w.out2.exists())

    def test_binding_before_barred_at_finalise(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["judge"] = AUTHOR
        text = w.write_verdicts(specs, panel=[AUTHOR])
        text = text.replace("effective-mode: subset", "effective-mode: full")
        w.verdicts.write_text(text)
        p = w.run("finalise", context="stated", panel=[AUTHOR])
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="effective mode"))

    def test_input_error_governs_over_barred_at_worksheet(self):
        w = self.world()
        p = w.run("worksheet", context="stated", judge=AUTHOR, runner=AUTHOR)
        assert_ie(self, p, "IE-49", IE_WORDINGS["IE-49"])
        self.assertFalse(w.out1.exists())

    def test_remaining_form_order_binding_then_conflict(self):
        w = self.world()
        w.set_amendment([("A1", "The wording names Gap 7 plainly."),
                         ("A2", "The amendment changes the counting text.")])
        w.set_declaration(default_spec())
        text = w.write_verdicts(pass_specs())
        text = text.replace("effective-mode: subset", "effective-mode: full")
        w.verdicts.write_text(text)
        p = w.run("remaining", context="stated")
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="effective mode"))


if __name__ == "__main__":
    unittest.main()
