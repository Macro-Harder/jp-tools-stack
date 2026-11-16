"""Transcription tests of plan part 8.

Pure structure tests that pass without the program. Each asserts that a test
side transcription held in rcg_common is complete against the plan text it
transcribes, by reading the plan text itself and comparing in full.
"""

import re
import unittest

from rcg_common import (
    STATUS_TABLE, SENTENCES, IE_WORDINGS, TRIGGER_ORDER, STATUS_MAPPING_ROWS,
    PROBE_NAMES, JSON_TOP_KEYS, JSON_NESTED_KEYS, WORK_DIR,
)

PLAN_PATH = WORK_DIR / "plan.md"
PLAN_MISSING_REASON = (
    "plan.md is missing at %s; the transcription tests need the design "
    "plan file and skip without it" % PLAN_PATH
)
PLAN_AVAILABLE = PLAN_PATH.exists()
if PLAN_AVAILABLE:
    PLAN = PLAN_PATH.read_text()
else:
    PLAN = ""


def plan_section(start, end):
    return PLAN.split(start)[1].split(end)[0]


@unittest.skipUnless(PLAN_AVAILABLE, PLAN_MISSING_REASON)
class TestStatusTranscription(unittest.TestCase):
    def test_every_status_of_part_1_1_present(self):
        self.assertEqual(sorted(STATUS_TABLE.keys()), list(range(0, 11)))
        section = plan_section("## 1. Exit statuses", "## 2.")
        for status in range(0, 11):
            self.assertIn("| %d |" % status, section)

    def test_status_number_term_pairing_matches_part_1_1_table(self):
        section = plan_section("### 1.1", "### 1.2")
        rows = re.findall(r"\| (\d+) \| ([^|]+?) \|", section)
        plan_table = {int(num): term.strip() for num, term in rows}
        self.assertEqual(plan_table, STATUS_TABLE)

    def test_every_sentence_of_part_1_3_present(self):
        self.assertEqual(len(SENTENCES), 9)
        for term, sentence in SENTENCES.items():
            self.assertIn(sentence, PLAN)


@unittest.skipUnless(PLAN_AVAILABLE, PLAN_MISSING_REASON)
class TestIeTranscription(unittest.TestCase):
    def test_every_ie_identifier_of_part_6_present_with_wording(self):
        found = sorted(set(re.findall(r"IE-(\d{2})", PLAN)))
        expected = ["%02d" % n for n in range(1, 58)]
        self.assertEqual(found, expected)
        self.assertEqual(sorted(IE_WORDINGS.keys()), ["IE-" + n for n in expected])
        section = plan_section("## 6. Input error wordings", "## 7.")
        for ie_id, template in IE_WORDINGS.items():
            match = re.search(r"- %s: `([^`]+)`" % ie_id, section)
            self.assertIsNotNone(match, ie_id)
            plan_wording = match.group(1)
            plan_segments = re.split(r"<[^>]+>", plan_wording)
            template_segments = re.split(r"\{[^}]+\}", template)
            self.assertEqual(template_segments, plan_segments, ie_id)
            plan_slots = re.findall(r"<([^>]+)>", plan_wording)
            template_slots = re.findall(r"\{([^}]+)\}", template)
            self.assertEqual(len(template_slots), len(plan_slots), ie_id)


@unittest.skipUnless(PLAN_AVAILABLE, PLAN_MISSING_REASON)
class TestTriggerTranscription(unittest.TestCase):
    def test_every_trigger_of_part_4_7_present(self):
        self.assertEqual(len(TRIGGER_ORDER), 11)
        for name in TRIGGER_ORDER:
            self.assertIn("`%s`" % name, PLAN)

    def test_trigger_order_matches_part_4_7_fixed_order(self):
        listing = PLAN.split("Trigger names, in fixed record order:")[1].split("The effective mode")[0]
        plan_order = re.findall(r"`([^`]+)`", listing)
        self.assertEqual(plan_order, TRIGGER_ORDER)


@unittest.skipUnless(PLAN_AVAILABLE, PLAN_MISSING_REASON)
class TestStatusMappingTranscription(unittest.TestCase):
    def test_status_mapping_matches_part_4_9_step_5(self):
        section = plan_section("5. Status mapping, fixed:", "6. The queue item identifier")
        self.assertIn("counts as ruled where it carries the word `RULED` as a whole word, case insensitively", section)
        self.assertIn("counts as standing where the status string, trimmed and case folded, reads exactly `standing`", section)
        self.assertIn("Every other status counts as not ruled", section)
        for word in ("SETTLED", "Banked", "PARKED", "ORDERED", "open", "superseded", "withdrawn"):
            self.assertIn(word, section)
        self.assertGreaterEqual(len([row for row in STATUS_MAPPING_ROWS if "SETTLED" in row[0] or "Settled" in row[0]]), 3)
        for status, ruled, standing in STATUS_MAPPING_ROWS:
            expected_ruled = re.search(r"\bRULED\b", status, re.IGNORECASE) is not None
            expected_standing = status.strip().casefold() == "standing"
            self.assertEqual(ruled, expected_ruled, status)
            self.assertEqual(standing, expected_standing, status)
            self.assertFalse(ruled and standing, status)
        statuses = [row[0] for row in STATUS_MAPPING_ROWS]
        for needle in ("Banked", "PARKED", "ORDERED", "open", "superseded", "withdrawn", "standing", "no status stated"):
            self.assertTrue(any(needle in s for s in statuses), needle)
        self.assertTrue(any(re.search(r"\bRULED\b", s) for s in statuses))
        self.assertTrue(any("SETTLED" in s for s in statuses))


@unittest.skipUnless(PLAN_AVAILABLE, PLAN_MISSING_REASON)
class TestProbeTranscription(unittest.TestCase):
    def test_probe_names_present_in_probe_order(self):
        self.assertEqual(PROBE_NAMES, ["selection_probe", "pass_probe", "blocking_probe",
                                       "excused_fail_probe", "binding_probe"])
        positions = [PLAN.index("`%s`" % name) for name in PROBE_NAMES]
        self.assertEqual(positions, sorted(positions))


JSON_NESTED_ANCHORS = {
    "fingerprints": r"`fingerprints`, in order:",
    "paths": r"`paths`, in order:",
    "attestations": r"`attestations`, in order:",
    "change_flags": r"`change_flags` holds, in order:",
    "second_attester": r"`second_attester` is null[^\n]*?an object with keys in order:",
    "disagreement": r"disagreements is a list of objects with keys in order:",
    "item": r"`items` is a list[^\n]*?objects with keys in order:",
    "verdict": r"Each verdict object has keys in order:",
    "claim": r"`claim` is null or an object with keys in order:",
    "trace_excerpt": r"as an object with keys in order:",
    "candidate": r"`re_ruling_candidates` is a list of objects with keys in order:",
    "match": r"`re_ruling_matches` is a list of objects with keys in order:",
    "unverified": r"`unverified_excuses` is a list of objects with keys in order:",
    "blocked_item": r"`blocked_items` is a list of objects with keys in order:",
    "counts": r"`counts`, in order:",
    "missing_entry": r"`missing` is a list of objects with keys in order:",
    "self_test": r"`self_test` is an object with keys in order:",
    "probe": r"Probes is a list of objects with keys in order:",
}


@unittest.skipUnless(PLAN_AVAILABLE, PLAN_MISSING_REASON)
class TestJsonKeyOrderTranscription(unittest.TestCase):
    def test_key_order_matches_part_5_8(self):
        section = plan_section("### 5.8 JSON results", "## 6.")
        listing = section.split("top level:")[1].split("`auditor_oversight_line`.")[0] + "`auditor_oversight_line`"
        top = re.findall(r"`([a-z_]+)`", listing)
        self.assertEqual(top, JSON_TOP_KEYS)

    def test_nested_key_orders_match_part_5_8_level_by_level(self):
        section = plan_section("### 5.8 JSON results", "## 6.")
        for key, expected in JSON_NESTED_KEYS.items():
            anchor = JSON_NESTED_ANCHORS[key]
            match = re.search(anchor, section)
            self.assertIsNotNone(match, key)
            rest = section[match.end():]
            segment = re.split(r"\.|, where|, each with|, in each case", rest, maxsplit=1)[0]
            found = re.findall(r"`([a-z_]+)`", segment)
            self.assertEqual(found, expected, key)


if __name__ == "__main__":
    unittest.main()
