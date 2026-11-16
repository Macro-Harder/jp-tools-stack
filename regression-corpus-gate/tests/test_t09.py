"""T9, worksheet and template. Brief sections 2, 3, 5, 7; plan parts 5.6 and 3.3."""

import unittest

from rcg_common import (
    RcgTestCase, PLAYBOOK_LINES, TEMPLATE_CLOSING_LINE, WORKSHEET_FIXED_LINE,
    sha256_hex, JUDGE, ROW_BY_ID, assert_ie, IE_WORDINGS,
)


class TestWorksheetLayout(RcgTestCase):
    def test_section_order_readback_first(self):
        w = self.world()
        p = w.run("worksheet", context="stated", queue=True)
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        lines = text.splitlines()
        self.assertEqual(lines[0], "selection readback")
        head_at = lines.index("regression-corpus-gate 1.0.0")
        self.assertGreater(head_at, 0)
        self.assertIn(WORKSHEET_FIXED_LINE, text)
        play_at = text.index("worst day playbook")
        self.assertGreater(play_at, text.index("regression-corpus-gate 1.0.0"))
        for line in PLAYBOOK_LINES:
            self.assertIn(line, text)

    def test_row_sections_carry_governing_text(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("incident: Alpha incident happened", text)
        self.assertIn("pass procedure: Inspect the amendment for the named shape; fail if the amendment permits the named failure shape.", text)
        self.assertIn("test: fail if the amendment permits the named failure shape.", text)

    def test_queue_size_line_and_candidates_where_supplied(self):
        w = self.world()
        p = w.run("worksheet", context="stated", queue=True)
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        size = len(w.queue_bytes)
        self.assertIn("queue as read: %d bytes of the 2000000 byte limit" % size, text)
        self.assertIn("candidate for C-001: DQ-101, status as read RULED, closed", text)
        self.assertIn("entry lines 3 to", text)

    def test_candidates_not_listed_no_queue_supplied(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("candidates not listed: no queue path was supplied", text)
        self.assertNotIn("queue as read:", text)

    def test_candidates_not_listed_unreadable_queue_no_size_line(self):
        w = self.world()
        w.queue.unlink()
        w.queue.mkdir()
        p = w.run("worksheet", context="stated", queue=True)
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.read_out1()
        self.assertIn("candidates not listed: the queue could not be read at this form", text)
        self.assertNotIn("queue as read:", text)


class TestTemplate(RcgTestCase):
    def test_template_binding_header_filled(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.out2.read_text()
        self.assertIn("amendment-fingerprint: " + sha256_hex(w.amendment_bytes), text)
        self.assertIn("corpus-fingerprint: " + sha256_hex(w.corpus_bytes), text)
        self.assertIn("declaration-fingerprint: " + sha256_hex(w.declaration_bytes), text)
        self.assertIn("declared-mode: subset", text)
        self.assertIn("effective-mode: subset", text)
        self.assertIn("triggers: none", text)
        self.assertIn("checked: C-001", text)
        self.assertIn("judge-of-record: " + JUDGE, text)

    def test_template_slots_all_empty(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.out2.read_text()
        self.assertIn("verdict: A1 C-001", text)
        for slot in ("judge: ", "clause: ", "word: ", "reason: "):
            self.assertIn("\n" + slot + "\n", "\n" + text)
        self.assertNotIn("word: PASS", text)
        self.assertNotIn("word: FAIL", text)
        self.assertNotIn("claim:", text)
        self.assertTrue(text.rstrip().endswith(TEMPLATE_CLOSING_LINE))

    def test_template_block_order_item_then_id(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        text = w.out2.read_text()
        order = [text.index("verdict: A1 C-001"), text.index("verdict: A1 C-003"), text.index("verdict: A2 C-002")]
        self.assertEqual(order, sorted(order))


class TestNoWorksheetSubstitution(RcgTestCase):
    def test_input_change_after_worksheet_fails_binding(self):
        w = self.world()
        p = w.run("worksheet", context="stated")
        self.assertEqual(p.returncode, 10, p.stderr)
        template = w.out2.read_text()
        filled = []
        current_id = None
        for line in template.splitlines():
            if line.startswith("verdict: "):
                current_id = line.split(" ")[2]
                filled.append(line)
            elif line == "judge: ":
                filled.append("judge: " + JUDGE)
            elif line == "clause: ":
                filled.append("clause: " + ROW_BY_ID[current_id]["clause"])
            elif line == "word: ":
                filled.append("word: PASS")
            elif line == "reason: ":
                filled.append("reason: The row was judged on its own procedure.")
            else:
                filled.append(line)
        w.verdicts.write_text("\n".join(filled) + "\n")
        w.corpus_bytes = w.corpus_bytes.replace(b"Alpha incident happened", b"Alpha incident occurred")
        w.corpus.write_bytes(w.corpus_bytes)
        w.out1 = w.dir / "fresh_report.txt"
        w.out2 = w.dir / "fresh_results.txt"
        p2 = w.run("finalise", context="stated")
        assert_ie(self, p2, "IE-38", IE_WORDINGS["IE-38"].format(value="corpus fingerprint"))


if __name__ == "__main__":
    unittest.main()
