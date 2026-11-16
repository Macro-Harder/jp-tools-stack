"""Stage 19 fix regressions. Defect D1 of audit-stage19-product.md.

The settled ruling is that the ruling date value in a claim block is the
date the queue entry states for its ruling, copied where the entry states
one, and the fixed words no date stated where the entry states no date.
An empty value still raises IE-44. No other claim field, check, or outcome
changes.

Honest staging note: the first test below is unstageable under the old
texts, because the old brief and plan required a ruling date as read from
the entry and the entry staged here states no date at all, so no truthful
value stood for the judge to enter. The test passes on the program as it
already stood, because the program already recorded the entered value
verbatim and raised IE-44 only on an empty value. The defect was in the
texts, not in the program. The second and third tests pin behaviour that
already stood and must not change under the settlement.
"""

import unittest

from rcg_common import (
    RcgTestCase, assert_ie, assert_no_files, IE_WORDINGS, JUDGE,
    pass_specs, queue_text,
)

NO_DATE = "no date stated"
DATED = "2026-11-01"


def specs_with_claim(queue_item, ruling_date, cid="C-001", label="A1"):
    specs = pass_specs()
    for s in specs:
        if s["id"] == cid and s["label"] == label:
            s["word"] = "FAIL"
            s["claim"] = {
                "queue_item": queue_item,
                "ruling_date": ruling_date,
                "confirming_judge": JUDGE,
            }
    return specs


def set_queue(w, entries):
    w.queue_bytes = queue_text(entries).encode()
    w.queue.write_bytes(w.queue_bytes)


class TestNoDateStatedClaim(RcgTestCase):
    def test_ruled_entry_stating_no_date_confirms_with_no_date_stated(self):
        w = self.world()
        set_queue(w, [
            ("### DQ-201: a ruled entry naming one row", "RULED, closed",
             ["This entry rules the incident at C-001."]),
            ("### DQ-202: a settled entry naming one row", "SETTLED, closed",
             ["This entry settles the incident at C-002 as a Manager settlement."]),
            ("## DQ-203: an open entry naming one row", "Banked",
             ["This entry is open and names C-003."]),
        ])
        w.write_verdicts(specs_with_claim("DQ-201", NO_DATE))
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 5, p.stderr)
        text = w.read_out1()
        self.assertIn(
            "match: A1, C-001, DQ-201, no date stated, status as read RULED, closed",
            text)
        data = w.read_results()
        self.assertEqual(data["outcome"], "re-ruled pass")
        self.assertEqual(data["exit_status"], 5)
        self.assertEqual(len(data["re_ruling_matches"]), 1)
        match = data["re_ruling_matches"][0]
        self.assertEqual(match["queue_item"], "DQ-201")
        self.assertEqual(match["ruling_date"], NO_DATE)
        self.assertEqual(data["counts"]["failed_excused"], 1)
        self.assertEqual(data["counts"]["failed_unexcused"], 0)
        verdicts = data["items"][0]["verdicts"]
        claimed = [v for v in verdicts if v["corpus_id"] == "C-001"]
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0]["claim"]["ruling_date"], NO_DATE)
        self.assertTrue(claimed[0]["excused"])


class TestEmptyRulingDateStillRefused(RcgTestCase):
    def test_empty_ruling_date_value_raises_ie44(self):
        w = self.world()
        w.write_verdicts(specs_with_claim("DQ-101", ""))
        p = w.run("finalise", context="stated", queue=True)
        assert_ie(self, p, "IE-44",
                  IE_WORDINGS["IE-44"].format(label="A1", id="C-001"))
        assert_no_files(self, w.out1, w.out2)


class TestDatedEntryStillCopiesItsDate(RcgTestCase):
    def test_dated_ruled_entry_claim_still_carries_its_stated_date(self):
        w = self.world()
        w.write_verdicts(specs_with_claim("DQ-101", DATED))
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 5, p.stderr)
        text = w.read_out1()
        self.assertIn(
            "match: A1, C-001, DQ-101, 2026-11-01, status as read RULED, closed",
            text)
        data = w.read_results()
        self.assertEqual(data["outcome"], "re-ruled pass")
        self.assertEqual(data["re_ruling_matches"][0]["ruling_date"], DATED)
        verdicts = data["items"][0]["verdicts"]
        claimed = [v for v in verdicts if v["corpus_id"] == "C-001"]
        self.assertEqual(claimed[0]["claim"]["ruling_date"], DATED)


if __name__ == "__main__":
    unittest.main()
