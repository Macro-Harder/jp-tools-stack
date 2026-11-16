"""T13, re-ruling verification. Brief section 8; plan part 4.9."""

import unittest

from rcg_common import (
    RcgTestCase, queue_text, pass_specs, sha256_hex, JUDGE,
    STATUS_MAPPING_ROWS, FIXTURES, CANONICAL_CORPUS,
)


def claim_specs(queue_item="DQ-101", cid="C-001", label="A1", date="2026-11-01"):
    specs = pass_specs()
    for s in specs:
        if s["id"] == cid and s["label"] == label:
            s["word"] = "FAIL"
            s["claim"] = {"queue_item": queue_item, "ruling_date": date, "confirming_judge": JUDGE}
    return specs


def run_claim(tc, w, specs=None, **run_kw):
    w.write_verdicts(claim_specs() if specs is None else specs)
    return w.run("finalise", context="stated", queue=True, **run_kw)


class TestConfirmedMatch(RcgTestCase):
    def test_ruled_entry_confirms(self):
        w = self.world()
        p = run_claim(self, w)
        self.assertEqual(p.returncode, 5, p.stderr)
        text = w.read_out1()
        self.assertIn("match: A1, C-001, DQ-101, 2026-11-01, status as read RULED, closed", text)
        self.assertIn("excuses only the named corpus ID and incident through the decision queue", text)
        data = w.read_results()
        self.assertEqual(data["outcome"], "re-ruled pass")
        self.assertEqual(data["re_ruling_matches"][0]["status_as_read"], "RULED, closed")
        self.assertEqual(data["re_ruling_matches"][0]["queue_item"], "DQ-101")
        self.assertEqual(data["fingerprints"]["queue"], sha256_hex(w.queue_bytes))
        self.assertEqual(data["counts"]["failed_excused"], 1)

    def test_standing_entry_confirms_on_synthetic_queue(self):
        w = self.world()
        w.queue_bytes = queue_text([
            ("### DQ-201: a standing entry naming one row", "standing",
             ["This entry stands for the incident at C-001."]),
        ]).encode()
        w.queue.write_bytes(w.queue_bytes)
        p = run_claim(self, w, claim_specs("DQ-201"))
        self.assertEqual(p.returncode, 5, p.stderr)
        text = w.read_out1()
        self.assertIn("status as read standing", text)
        self.assertNotIn("no entry in the queue as read carries the status standing", text)

    def test_no_standing_fact_line_where_none_reads_standing(self):
        w = self.world()
        p = run_claim(self, w)
        self.assertEqual(p.returncode, 5, p.stderr)
        self.assertIn("no entry in the queue as read carries the status standing", w.read_out1())


class TestStatusMapping(RcgTestCase):
    pass


for _status, _ruled, _standing in STATUS_MAPPING_ROWS:
    def _make(status=_status, ruled=_ruled, standing=_standing):
        def test(self):
            w = self.world()
            w.queue_bytes = queue_text([
                ("### DQ-201: an entry naming one row", status,
                 ["This entry concerns the incident at C-001 in full."]),
            ]).encode()
            w.queue.write_bytes(w.queue_bytes)
            p = run_claim(self, w, claim_specs("DQ-201"))
            if ruled or standing:
                self.assertEqual(p.returncode, 5, p.stderr)
            else:
                self.assertEqual(p.returncode, 1, p.stderr)
                data = w.read_results()
                self.assertEqual(data["unverified_excuses"][0]["reason"], "status does not count as a ruling")
        return test
    setattr(TestStatusMapping, "test_status_%s" % _status.replace(" ", "_").replace(",", ""), _make())


class TestNeverConfirming(RcgTestCase):
    def test_settled_narrative_naming_id_inside_settlement_passage(self):
        w = self.world()
        w.queue_bytes = queue_text([
            ("### DQ-201: a settled entry", "SETTLED, closed",
             ["#### Settlement", "The settlement respects the incident at C-001 among others."]),
        ]).encode()
        w.queue.write_bytes(w.queue_bytes)
        p = run_claim(self, w, claim_specs("DQ-201"))
        self.assertEqual(p.returncode, 1, p.stderr)

    def test_claimed_item_found_for_different_id(self):
        w = self.world()
        w.queue_bytes = queue_text([
            ("### DQ-201: a ruled entry for another row", "RULED, closed",
             ["This entry rules the incident at C-002 only."]),
        ]).encode()
        w.queue.write_bytes(w.queue_bytes)
        p = run_claim(self, w, claim_specs("DQ-201"))
        self.assertEqual(p.returncode, 1, p.stderr)
        data = w.read_results()
        self.assertEqual(data["unverified_excuses"][0]["reason"], "queue item not found for this corpus ID")

    def test_claimed_item_absent_from_candidates(self):
        w = self.world()
        p = run_claim(self, w, claim_specs("DQ-999"))
        self.assertEqual(p.returncode, 1, p.stderr)
        data = w.read_results()
        self.assertEqual(data["unverified_excuses"][0]["reason"], "queue item not found for this corpus ID")

    def test_general_approval_entry_never_confirms(self):
        w = self.world()
        w.queue_bytes = queue_text([
            ("### DQ-201: a general approval", "RULED, closed",
             ["A general approval of all amendments is recorded here, naming no incident."]),
        ]).encode()
        w.queue.write_bytes(w.queue_bytes)
        p = run_claim(self, w, claim_specs("DQ-201"))
        self.assertEqual(p.returncode, 1, p.stderr)

    def test_sibling_row_not_excused_by_pair_match(self):
        w = self.world()
        spec = [("A1", ["Gap 3", "Gap 4"], {"Gap 3": "Basis one.", "Gap 4": "Basis two."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        w.set_declaration(spec)
        w.queue_bytes = queue_text([
            ("### DQ-201: a ruled entry for one sibling", "RULED, closed",
             ["This entry rules the incident at C-005."]),
        ]).encode()
        w.queue.write_bytes(w.queue_bytes)
        specs = [
            {"label": "A1", "id": "C-005", "word": "FAIL",
             "claim": {"queue_item": "DQ-201", "ruling_date": "2026-11-02", "confirming_judge": JUDGE}},
            {"label": "A1", "id": "C-006", "word": "FAIL"},
            {"label": "A2", "id": "C-002", "word": "PASS"},
        ]
        w.write_verdicts(specs, checked_ids=["C-002", "C-005", "C-006"])
        p = w.run("finalise", context="stated", queue=True)
        self.assertEqual(p.returncode, 1, p.stderr)
        data = w.read_results()
        self.assertEqual(data["counts"]["failed_excused"], 1)
        self.assertEqual(data["counts"]["failed_unexcused"], 1)
        self.assertEqual(data["blocked_items"], [{"item": "A1", "unexcused_fail_count": 1}])

    def test_all_candidates_presented_in_record(self):
        w = self.world()
        w.queue_bytes = queue_text([
            ("### DQ-201: a ruled entry naming one row", "RULED, closed",
             ["This entry rules the incident at C-001."]),
            ("### DQ-202: a settled entry naming the same row", "SETTLED, closed",
             ["This entry settles a matter at C-001 as a Manager settlement."]),
        ]).encode()
        w.queue.write_bytes(w.queue_bytes)
        p = run_claim(self, w, claim_specs("DQ-201"))
        self.assertEqual(p.returncode, 5, p.stderr)
        text = w.read_out1()
        self.assertIn("candidate for C-001: DQ-201, status as read RULED, closed", text)
        self.assertIn("candidate for C-001: DQ-202, status as read SETTLED, closed", text)
        data = w.read_results()
        self.assertEqual(len(data["re_ruling_candidates"]), 2)


class TestStatusDeterminationShapes(RcgTestCase):
    def _run_with_queue(self, queue_bytes, item="DQ-201"):
        w = self.world()
        w.queue_bytes = queue_bytes
        w.queue.write_bytes(queue_bytes)
        p = run_claim(self, w, claim_specs(item))
        return w, p

    def test_open_entry_banked_with_ruling_passage_is_banked(self):
        q = queue_text([
            ("### DQ-201: an open entry naming one row", "Banked",
             ["The question stands open for the incident at C-001.", "#### Ruling passage",
              "A ruling passage stands inside this entry but its status line reads Banked."]),
        ]).encode()
        w, p = self._run_with_queue(q)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("candidate for C-001: DQ-201, status as read Banked", w.read_out1())

    def test_ruled_record_entry_status_line_ruled_counts(self):
        q = queue_text([
            ("### DQ-201: a ruled record entry", "RULED, closed",
             ["#### Ruling", "This entry rules the incident at C-001."]),
        ]).encode()
        w, p = self._run_with_queue(q)
        self.assertEqual(p.returncode, 5, p.stderr)

    def test_tail_heading_ruled_counts(self):
        q = queue_text([
            ("## DQ-201: a tail entry about the incident at C-001. RULED by the decider 2026-11-01", None,
             ["The tail entry body names C-001 as well."]),
        ]).encode()
        w, p = self._run_with_queue(q)
        self.assertEqual(p.returncode, 5, p.stderr)

    def test_tail_heading_settled_never_counts(self):
        q = queue_text([
            ("## DQ-201: a tail entry about the incident at C-001. SETTLED by the Manager 2026-11-01", None,
             ["The tail entry body names C-001 as well."]),
        ]).encode()
        w, p = self._run_with_queue(q)
        self.assertEqual(p.returncode, 1, p.stderr)

    def test_tail_heading_ruled_initial_capital_counts(self):
        q = queue_text([
            ("## DQ-201: a tail entry about the incident at C-001. Ruled by the decider 2026-11-01", None,
             ["The tail entry body names C-001 as well."]),
        ]).encode()
        w, p = self._run_with_queue(q)
        self.assertEqual(p.returncode, 5, p.stderr)

    def test_tail_heading_standing_uppercase_counts(self):
        q = queue_text([
            ("## DQ-201: a tail entry about the incident at C-001. STANDING as of 2026-11-01", None,
             ["The tail entry body names C-001 as well."]),
        ]).encode()
        w, p = self._run_with_queue(q)
        self.assertEqual(p.returncode, 5, p.stderr)

    def test_ruling_passage_without_status_is_no_status_stated(self):
        q = queue_text([
            ("### DQ-201: an entry naming one row", None,
             ["#### Ruling", "A passage rules the incident at C-001 in prose."]),
        ]).encode()
        w, p = self._run_with_queue(q)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("status as read no status stated", w.read_out1())

    def test_level_four_heading_starts_no_new_entry(self):
        q = queue_text([
            ("### DQ-201: an entry naming one row", "RULED, closed",
             ["This entry rules the incident at C-001.", "#### DQ-999: a passage heading inside the entry",
              "Passage text follows inside the same entry."]),
        ]).encode()
        w, p = self._run_with_queue(q)
        self.assertEqual(p.returncode, 5, p.stderr)
        data = w.read_results()
        self.assertEqual(len(data["re_ruling_candidates"]), 1)
        self.assertEqual(data["re_ruling_candidates"][0]["queue_item"], "DQ-201")

    def test_quoted_status_line_does_not_govern(self):
        text = ("# Decision Queue\n\n### DQ-201: an entry naming one row\n\n"
                "The body of this entry first quotes an earlier passage in full:\n\n"
                "> Quoted passage begins here.\n"
                "> Status: RULED, closed\n"
                "> Quoted passage ends here.\n\n"
                "Status: Banked\n\n"
                "This entry concerns the incident at C-001.\n")
        w, p = self._run_with_queue(text.encode())
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("candidate for C-001: DQ-201, status as read Banked", w.read_out1())


class TestQueueFailures(RcgTestCase):
    def _failure(self, mutate, kind_reason):
        w = self.world()
        mutate(w)
        p = run_claim(self, w)
        self.assertEqual(p.returncode, 1, p.stderr)
        data = w.read_results()
        self.assertEqual(data["unverified_excuses"][0]["reason"], kind_reason)
        self.assertEqual(data["counts"]["failed_unexcused"], 1)
        return w, data

    def test_missing_queue(self):
        def m(w):
            w.queue.unlink()
        w, data = self._failure(m, "queue could not be verified: missing")
        self.assertEqual(data["fingerprints"]["queue"], "no queue file was read: missing")

    def test_empty_queue_zero_bytes(self):
        def m(w):
            w.queue.write_bytes(b"")
            w.queue_bytes = b""
        w, data = self._failure(m, "queue could not be verified: empty")
        from rcg_common import ZERO_BYTE_SHA256
        self.assertEqual(data["fingerprints"]["queue"], ZERO_BYTE_SHA256)
        self.assertIn(ZERO_BYTE_SHA256, w.read_out1())

    def test_empty_queue_no_entry_heading(self):
        def m(w):
            w.queue.write_text("# A queue with prose but no entries\n")
            w.queue_bytes = w.queue.read_bytes()
        w, data = self._failure(m, "queue could not be verified: empty")
        self.assertEqual(data["fingerprints"]["queue"], sha256_hex(w.queue_bytes))

    def test_malformed_queue_non_utf8(self):
        def m(w):
            w.queue.write_bytes(b"\xff\xfe\x00 bad")
            w.queue_bytes = b"\xff\xfe\x00 bad"
        w, data = self._failure(m, "queue could not be verified: malformed")
        self.assertEqual(data["fingerprints"]["queue"], sha256_hex(b"\xff\xfe\x00 bad"))

    def test_unreadable_queue_directory(self):
        def m(w):
            w.queue.unlink()
            w.queue.mkdir()
        w, data = self._failure(m, "queue could not be verified: unreadable")
        self.assertEqual(data["fingerprints"]["queue"], "no queue file was read: unreadable")
        self.assertIn("no queue file was read: unreadable", w.read_out1())

    def test_oversize_queue_measured_value(self):
        def m(w):
            w.queue.write_bytes(b"# Decision Queue\n" + b"x" * (2000100 - 17))
            w.queue_bytes = w.queue.read_bytes()
            assert len(w.queue_bytes) == 2000100
        w, data = self._failure(m, "queue could not be verified: oversize, measured 2000100 bytes")
        self.assertEqual(data["fingerprints"]["queue"], "no queue file was read: oversize")
        self.assertIn("no queue file was read: oversize", w.read_out1())

    def test_queue_failure_leaves_other_items_unaffected(self):
        w = self.world()
        w.queue.unlink()
        specs = claim_specs()
        p = run_claim(self, w, specs)
        self.assertEqual(p.returncode, 1, p.stderr)
        data = w.read_results()
        outcomes = {i["label"]: i["outcome"] for i in data["items"]}
        self.assertEqual(outcomes["A2"], "pass")
        self.assertEqual(outcomes["A1"], "fail")

    def test_no_claim_means_no_queue_entry_in_chain(self):
        w = self.world()
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        data = w.read_results()
        self.assertIsNone(data["fingerprints"]["queue"])
        self.assertEqual(data["re_ruling_candidates"], [])


class TestRealQueueExcerpts(RcgTestCase):
    def _canonical_worksheet(self, excerpt_name):
        w = self.world()
        w.corpus_bytes = CANONICAL_CORPUS.read_bytes()
        w.corpus.write_bytes(w.corpus_bytes)
        w.set_amendment([("A1", "The amendment changes the staffing rule text.")])
        w.set_declaration([("A1", ["Gap 5"], {"Gap 5": "Basis prose for Gap 5 on A1."})])
        w.queue_bytes = (FIXTURES / excerpt_name).read_bytes()
        w.queue.write_bytes(w.queue_bytes)
        return w

    def test_real_open_excerpt_status_banked(self):
        w = self._canonical_worksheet("real_queue_open_excerpt.md")
        p = w.run("worksheet", context="stated", queue=True)
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("candidate for C-137: DQ-070, status as read Banked", w.read_out1())

    def test_real_ruled_excerpt_status_ruled(self):
        w = self._canonical_worksheet("real_queue_ruled_excerpt.md")
        p = w.run("worksheet", context="stated", queue=True)
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("candidate for C-137: DQ-138, status as read RULED, closed", w.read_out1())


if __name__ == "__main__":
    unittest.main()
