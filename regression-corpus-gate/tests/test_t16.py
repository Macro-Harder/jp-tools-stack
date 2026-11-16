"""T16, report forms and JSON. Brief section 10; plan part 5."""

import json
import unittest

from rcg_common import (
    RcgTestCase, pass_specs, JSON_TOP_KEYS, JSON_NESTED_KEYS, SENTENCES,
    NEXT_STEP_LINE, GLOSSARY_LINES, LIMIT_LINES_FIXED, JUDGE,
)


def pass_record(tc):
    w = tc.world()
    w.write_verdicts(pass_specs())
    p = w.run("finalise", context="stated")
    tc.assertEqual(p.returncode, 0, p.stderr)
    return w


class TestHeadBlock(RcgTestCase):
    def test_head_block_on_pass(self):
        w = pass_record(self)
        lines = w.read_out1().splitlines()
        self.assertEqual(lines[0], "regression-corpus-gate 1.0.0")
        self.assertEqual(lines[1], "pass: " + SENTENCES["pass"])
        self.assertEqual(lines[2], "blocked items: none")
        self.assertEqual(lines[3], "filing: PASS")
        self.assertEqual(lines[4], NEXT_STEP_LINE)
        self.assertEqual(lines[5], "exit status: 0")

    def test_head_block_on_fail_with_blocked_items(self):
        w = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        w.write_verdicts(specs)
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 1, p.stderr)
        lines = w.read_out1().splitlines()
        self.assertEqual(lines[1], "fail: " + SENTENCES["fail"])
        self.assertIn("blocked item: A1, unexcused fails: 1", lines)
        self.assertNotIn("blocked items: none", lines)
        self.assertEqual(lines[lines.index("blocked item: A1, unexcused fails: 1") + 1], "filing: FAIL rejected")

    def test_head_block_on_incomplete(self):
        w = self.world()
        w.write_verdicts(pass_specs()[:1])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        lines = w.read_out1().splitlines()
        self.assertEqual(lines[1], "incomplete: " + SENTENCES["incomplete"])
        self.assertIn("exit status: 3", lines)


class TestCoverageForms(RcgTestCase):
    def test_coverage_subset_form(self):
        w = pass_record(self)
        text = w.read_out1()
        self.assertIn("coverage:", text)
        self.assertIn("indexes searched: Gap 1, FM-1", text)
        self.assertIn("rows checked: 3 distinct rows", text)
        self.assertIn("rows not checked: 3", text)
        self.assertIn("indexes not searched:", text)

    def test_coverage_full_form(self):
        w = self.world()
        from rcg_common import ROW_BY_ID
        pairs = [(label, cid) for label in ("A1", "A2") for cid in sorted(ROW_BY_ID)]
        w.write_verdicts([{"label": l, "id": c} for l, c in pairs],
                         declared_mode="full", effective_mode="full",
                         checked_ids=sorted(ROW_BY_ID))
        p = w.run("finalise", context="stated", declared_mode="full")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("all indexes were searched and no rows were left unchecked", w.read_out1())

    def test_coverage_no_touch_form(self):
        w = self.world()
        from rcg_common import default_spec
        spec = [("A1", None, "No touch basis for A1."), ("A2", None, "No touch basis for A2.")]
        w.set_declaration(spec)
        w.write_verdicts([], checked_ids=[])
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        self.assertIn("indexes searched: none", text)
        self.assertIn("no entry was touched", text)


class TestRecordSections(RcgTestCase):
    def test_run_record_facts_present(self):
        w = pass_record(self)
        text = w.read_out1()
        for needle in ("runner: Runner Seat", "judge of record: Judge Seat",
                       "wording author: Author Seat", "reader designate: Reader Seat",
                       "declared mode: subset", "effective mode: subset",
                       "triggers", "gate amendment run: no",
                       "attested tier: Low", "attester: Runner Seat"):
            self.assertIn(needle, text)

    def test_input_change_between_forms_changes_binding(self):
        w = self.world()
        p1 = w.run("worksheet", context="stated")
        self.assertEqual(p1.returncode, 10, p1.stderr)
        worksheet_text = w.read_out1()
        readback_ws = worksheet_text.split("selection readback")[1].split("regression-corpus-gate")[0]
        w.out1.unlink()
        w.out2.unlink()
        w.write_verdicts(pass_specs())
        p2 = w.run("finalise", context="mixed")
        self.assertEqual(p2.returncode, 2, p2.stderr)

    def test_readback_regenerated_not_copied(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        self.assertIn("selection readback", text)
        self.assertIn("basis for A1 Gap 1: Basis prose for Gap 1 on A1.", text)

    def test_readback_matches_finalise_regeneration_after_input_change(self):
        w = self.world()
        p1 = w.run("worksheet", context="stated")
        self.assertEqual(p1.returncode, 10, p1.stderr)
        self.assertIn("basis for A1 Gap 1: Basis prose for Gap 1 on A1.", w.read_out1())
        w.out1.unlink()
        w.out2.unlink()
        spec = [("A1", ["Gap 2"], {"Gap 2": "Changed basis prose for Gap 2 on A1."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        specs = [{"label": "A1", "id": "C-004"}, {"label": "A2", "id": "C-002"}]
        w.write_verdicts(specs, checked_ids=["C-002", "C-004"])
        p2 = w.run("finalise", context="stated")
        self.assertEqual(p2.returncode, 0, p2.stderr)
        text = w.read_out1()
        readback = text.split("selection readback")[1].split("\nself test\n")[0]
        self.assertIn("item A1: declared: Gap 2;", readback)
        self.assertIn("basis for A1 Gap 2: Changed basis prose for Gap 2 on A1.", readback)
        self.assertNotIn("basis for A1 Gap 1", readback)
        self.assertNotIn("item A1: declared: Gap 1;", readback)

    def test_counts_section_order(self):
        w = pass_record(self)
        text = w.read_out1()
        order = [text.index("checks run:"), text.index("passed:"), text.index("failed:"),
                 text.index("failed excused:"), text.index("failed unexcused:"),
                 text.index("unjudgeable:"), text.index("missing:")]
        self.assertEqual(order, sorted(order))

    def test_limits_section_lines(self):
        w = pass_record(self)
        text = w.read_out1()
        for line in LIMIT_LINES_FIXED:
            self.assertIn(line, text)
        self.assertIn("declared tokens that selected no row: none", text)
        limits = text.split("\nlimits\n")[1].split("\nreader designate:")[0]
        ordered_needles = [
            LIMIT_LINES_FIXED[0],
            LIMIT_LINES_FIXED[1],
            "corpus dialects as read:",
            "clause family as read:",
            "declared tokens that selected no row:",
            LIMIT_LINES_FIXED[2],
            LIMIT_LINES_FIXED[3],
            LIMIT_LINES_FIXED[4],
            LIMIT_LINES_FIXED[5],
            LIMIT_LINES_FIXED[6],
            "sizing as measured:",
        ]
        positions = [limits.index(n) for n in ordered_needles]
        self.assertEqual(positions, sorted(positions))

    def test_reader_and_oversight_lines_verbatim(self):
        w = pass_record(self)
        text = w.read_out1()
        self.assertIn("reader designate: Reader Seat. An amendment takes effect only after the Auditor, or a named reader who is neither author nor ruler, has read this record. This record names the reader designate; it does not record that the reading has happened.", text)
        self.assertIn("auditor oversight: a fresh Auditor oversees this run after reading the corpus and the wording set first hand, under the procedure of part 4.6. The overseeing seat and the fact of that reading are attested outside this record in the filed trace; this record states the duty and does not record that the oversight or the reading has happened.", text)

    def test_glossary_strip_is_final_section(self):
        w = pass_record(self)
        text = w.read_out1()
        tail = text.split("glossary")[1]
        for line in GLOSSARY_LINES:
            self.assertIn(line, tail)
        self.assertTrue(text.rstrip().endswith(GLOSSARY_LINES[-1]))

    def test_no_re_ruling_claimed_line(self):
        w = pass_record(self)
        self.assertIn("no re-ruling was claimed", w.read_out1())


class TestJsonShape(RcgTestCase):
    def test_top_level_key_order(self):
        w = pass_record(self)
        data = w.read_results()
        self.assertEqual(list(data.keys()), JSON_TOP_KEYS)

    def test_nested_key_orders(self):
        w = pass_record(self)
        data = w.read_results()
        self.assertEqual(list(data["fingerprints"].keys()), JSON_NESTED_KEYS["fingerprints"])
        self.assertEqual(list(data["paths"].keys()), JSON_NESTED_KEYS["paths"])
        self.assertEqual(list(data["attestations"].keys()), JSON_NESTED_KEYS["attestations"])
        self.assertEqual(list(data["attestations"]["change_flags"].keys()), JSON_NESTED_KEYS["change_flags"])
        self.assertEqual(list(data["counts"].keys()), JSON_NESTED_KEYS["counts"])
        self.assertEqual(list(data["self_test"].keys()), JSON_NESTED_KEYS["self_test"])
        self.assertEqual(list(data["self_test"]["probes"][0].keys()), JSON_NESTED_KEYS["probe"])
        item = data["items"][0]
        self.assertEqual(list(item.keys()), JSON_NESTED_KEYS["item"])
        verdict = item["verdicts"][0]
        self.assertEqual(list(verdict.keys()), JSON_NESTED_KEYS["verdict"])
        self.assertEqual(list(verdict["trace_excerpt"].keys()), JSON_NESTED_KEYS["trace_excerpt"])

    def test_json_and_text_agree_field_by_field(self):
        w = pass_record(self)
        data = w.read_results()
        text = w.read_out1()
        self.assertEqual(data["tool"], "regression-corpus-gate")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["outcome"], "pass")
        self.assertEqual(data["exit_status"], 0)
        self.assertEqual(data["corpus_row_count"], 6)
        self.assertEqual(data["declared_mode"], "subset")
        self.assertEqual(data["effective_mode"], "subset")
        self.assertEqual(data["triggers"], [])
        self.assertEqual(data["checked_ids"], ["C-001", "C-002", "C-003"])
        self.assertIn("corpus rows as read: 6", text)
        self.assertEqual(data["counts"]["checks_run"], 3)
        for item in data["items"]:
            self.assertIn("item %s: %s" % (item["label"], item["outcome"]), text)

    def test_json_two_space_indent_and_final_newline(self):
        w = pass_record(self)
        raw = w.out2.read_bytes()
        self.assertTrue(raw.endswith(b"\n"))
        self.assertFalse(raw.endswith(b"\n\n"))
        self.assertIn(b'\n  "version": "1.0.0"', raw)
        self.assertNotIn(b"\r", raw)


class TestQuotingBound(RcgTestCase):
    def test_no_full_row_reproduction_in_reports(self):
        worlds = []
        worlds.append(pass_record(self))
        w_fail = self.world()
        specs = pass_specs()
        specs[0]["word"] = "FAIL"
        w_fail.write_verdicts(specs)
        p = w_fail.run("finalise", context="stated")
        self.assertEqual(p.returncode, 1, p.stderr)
        worlds.append(w_fail)
        w_inc = self.world()
        w_inc.write_verdicts(pass_specs()[:1])
        p = w_inc.run("finalise", context="stated")
        self.assertEqual(p.returncode, 3, p.stderr)
        worlds.append(w_inc)
        w_ws = self.world()
        p = w_ws.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        worlds.append(w_ws)
        for w in worlds:
            text = w.read_out1()
            for line in w.corpus_bytes.decode().splitlines():
                if line.startswith("| C-"):
                    self.assertNotIn(line, text)


if __name__ == "__main__":
    unittest.main()
