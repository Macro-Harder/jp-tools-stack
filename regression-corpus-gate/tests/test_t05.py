"""T5, attestations, second attester, and triggers. Brief section 5; plan parts 3.5 and 4.7."""

import unittest

from rcg_common import (
    RcgTestCase, assert_ie, IE_WORDINGS, CHANGE_FLAGS, TRIGGER_ORDER,
    RUNNER, AUTHOR, JUDGE, SECOND,
)

SINGLE_TRIGGERS = [
    ("tier Plaid", {"tier": "Plaid", "context": "stated"}, ["tier-plaid"]),
    ("flag index system", {"context": "stated", "change_flags": {"index_system": "yes"}}, ["change-index-system"]),
    ("flag gate rule", {"context": "stated", "change_flags": {"gate_rule": "yes"}}, ["change-gate-rule"]),
    ("flag corpus", {"context": "stated", "change_flags": {"corpus": "yes"}}, ["change-corpus"]),
    ("flag definition", {"context": "stated", "change_flags": {"definition": "yes"}}, ["change-definition"]),
    ("flag counting method", {"context": "stated", "change_flags": {"counting_method": "yes"}}, ["change-counting-method"]),
    ("flag verdict form", {"context": "stated", "change_flags": {"verdict_form": "yes"}}, ["change-verdict-form"]),
    ("flag closure rule", {"context": "stated", "change_flags": {"closure_rule": "yes"}}, ["change-closure-rule"]),
    ("context mixed", {"context": "mixed"}, ["context-mixed"]),
    ("context disputed", {"context": "disputed"}, ["context-disputed"]),
    ("context omitted means unstated", {}, ["context-unstated"]),
]


class TestTriggerTable(RcgTestCase):
    pass


for _name, _over, _triggers in SINGLE_TRIGGERS:
    def _make(over=_over, triggers=_triggers):
        def test(self):
            w = self.world()
            p = w.run("worksheet", **over)
            self.assertEqual(p.returncode, 10, p.stderr)
            text = w.read_out1()
            self.assertIn("effective mode: full", text)
            for t in triggers:
                self.assertIn(t, text)
        return test
    setattr(TestTriggerTable, "test_trigger_%s" % _name.replace(" ", "_"), _make())


class TestNoTrigger(RcgTestCase):
    def test_declared_full_no_trigger(self):
        w = self.world()
        p = w.run("worksheet", declared_mode="full", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("effective mode: full", text)
        self.assertIn("triggers: none", text)

    def test_declared_subset_no_trigger_stands_subset(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("effective mode: subset", text)
        self.assertIn("triggers: none", text)


class TestGateAmendmentRun(RcgTestCase):
    def _finalise_record(self, over):
        w = self.world()
        from rcg_common import pass_specs
        all_ids = ["C-001", "C-002", "C-003", "C-004", "C-005", "C-006"]
        all_pairs = [(label, cid) for label in ("A1", "A2") for cid in all_ids]
        w.write_verdicts(pass_specs(all_pairs),
                         effective_mode="full",
                         triggers=over[1],
                         checked_ids=all_ids)
        p = w.run("finalise", **over[0])
        self.assertEqual(p.returncode, 0, p.stderr)
        return w.read_results()

    def test_gate_rule_flag_names_gate_run(self):
        data = self._finalise_record(({"context": "stated", "change_flags": {"gate_rule": "yes"}}, ["change-gate-rule"]))
        self.assertTrue(data["gate_amendment_run"])

    def test_index_system_flag_names_gate_run(self):
        data = self._finalise_record(({"context": "stated", "change_flags": {"index_system": "yes"}}, ["change-index-system"]))
        self.assertTrue(data["gate_amendment_run"])

    def test_corpus_flag_names_gate_run(self):
        data = self._finalise_record(({"context": "stated", "change_flags": {"corpus": "yes"}}, ["change-corpus"]))
        self.assertTrue(data["gate_amendment_run"])

    def test_definition_flag_does_not_name_gate_run(self):
        data = self._finalise_record(({"context": "stated", "change_flags": {"definition": "yes"}}, ["change-definition"]))
        self.assertFalse(data["gate_amendment_run"])


class TestSecondAttester(RcgTestCase):
    def test_required_when_runner_is_author(self):
        w = self.world()
        p = w.run("worksheet", runner=AUTHOR)
        assert_ie(self, p, "IE-49", IE_WORDINGS["IE-49"])

    def test_required_when_declarer_is_author(self):
        w = self.world()
        from rcg_common import AUTHOR as A, CONFIRMER
        w.set_declaration(declarer=A, confirmer=CONFIRMER)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-49", IE_WORDINGS["IE-49"])

    def test_second_seat_naming_runner_refused(self):
        w = self.world()
        p = w.run("worksheet", runner=AUTHOR, second={"seat": AUTHOR, "context": "stated"})
        assert_ie(self, p, "IE-49", IE_WORDINGS["IE-49"])

    def test_second_seat_naming_author_refused(self):
        w = self.world()
        p = w.run("worksheet", runner=AUTHOR,
                  second={"seat": AUTHOR, "context": "stated"})
        assert_ie(self, p, "IE-49", IE_WORDINGS["IE-49"])

    def test_second_set_missing_one_value(self):
        w = self.world()
        args = w.args("worksheet", runner=AUTHOR,
                      second={"seat": SECOND, "context": "stated"})
        idx = args.index("--second-change-corpus")
        del args[idx:idx + 2]
        from rcg_common import run_program
        p = run_program(args)
        assert_ie(self, p, "IE-50", IE_WORDINGS["IE-50"].format(flag="--second-change-corpus"))

    def test_second_set_missing_context_is_ie50(self):
        w = self.world()
        args = w.args("worksheet", runner=AUTHOR,
                      second={"seat": SECOND, "context": "stated"})
        idx = args.index("--second-context")
        del args[idx:idx + 2]
        from rcg_common import run_program
        p = run_program(args)
        assert_ie(self, p, "IE-50", IE_WORDINGS["IE-50"].format(flag="--second-context"))

    def _disagreement_record(self, second_over, primary_over=None):
        w = self.world()
        primary_over = primary_over or {"context": "stated"}
        all_pairs = [(label, cid) for label in ("A1", "A2") for cid in
                     ["C-001", "C-002", "C-003", "C-004", "C-005", "C-006"]]
        w.write_verdicts([{"label": l, "id": c} for l, c in all_pairs],
                         declared_mode="subset", effective_mode="full",
                         triggers=["context-disputed"], checked_ids=["C-001", "C-002", "C-003", "C-004", "C-005", "C-006"])
        over = dict(primary_over)
        over["runner"] = AUTHOR
        over["second"] = second_over
        p = w.run("finalise", **over)
        self.assertEqual(p.returncode, 0, p.stderr)
        return w

    def test_disagreement_on_tier(self):
        w = self._disagreement_record({"seat": SECOND, "tier": "High", "context": "stated"})
        text = w.read_out1()
        self.assertIn("attestation disagreement: tier, Low, High", text)
        data = w.read_results()
        self.assertEqual(data["attestations"]["effective_context"], "disputed")
        self.assertEqual(data["triggers"], ["context-disputed"])

    def test_disagreement_on_context(self):
        w = self._disagreement_record({"seat": SECOND, "tier": "Low", "context": "mixed"})
        text = w.read_out1()
        self.assertIn("attestation disagreement: context, stated, mixed", text)
        data = w.read_results()
        self.assertEqual(data["attestations"]["effective_context"], "disputed")

    def test_disagreement_on_one_flag(self):
        w = self._disagreement_record({"seat": SECOND, "tier": "Low", "context": "stated",
                                       "change_flags": {"definition": "yes"}})
        text = w.read_out1()
        self.assertIn("attestation disagreement: definition, no, yes", text)
        data = w.read_results()
        self.assertEqual(data["effective_mode"], "full")
        self.assertEqual(data["triggers"], ["context-disputed"])
        self.assertFalse(data["gate_amendment_run"])
        self.assertEqual(data["attestations"]["change_flags"]["definition"], "no")

    def test_disagreement_on_two_fields_two_records_in_order(self):
        w = self._disagreement_record({"seat": SECOND, "tier": "High", "context": "stated",
                                       "change_flags": {"corpus": "yes"}})
        data = w.read_results()
        disagreements = data["attestations"]["second_attester"]["disagreements"]
        self.assertEqual([d["field"] for d in disagreements], ["tier", "corpus"])
        self.assertEqual(disagreements[0]["primary_value"], "Low")
        self.assertEqual(disagreements[0]["second_value"], "High")
        text = w.read_out1()
        self.assertLess(text.index("attestation disagreement: tier"), text.index("attestation disagreement: corpus"))


if __name__ == "__main__":
    unittest.main()
