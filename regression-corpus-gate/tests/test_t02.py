"""T2, reading, limits, and fingerprints. Brief section 3."""

import unittest

from rcg_common import (
    RcgTestCase, assert_ie, assert_no_files, IE_WORDINGS,
    ORACLE_TEXT, ORACLE_SHA256, ZERO_BYTE_SHA256, BYTE_LIMIT,
)


class TestMissingAndUnreadable(RcgTestCase):
    def test_missing_corpus(self):
        w = self.world()
        w.corpus.unlink()
        p = w.run("worksheet")
        assert_ie(self, p, "IE-04", IE_WORDINGS["IE-04"].format(kind="corpus", path=str(w.corpus)))
        assert_no_files(self, w.out1, w.out2)

    def test_missing_amendment(self):
        w = self.world()
        w.amendment.unlink()
        p = w.run("worksheet")
        assert_ie(self, p, "IE-04", IE_WORDINGS["IE-04"].format(kind="amendment", path=str(w.amendment)))

    def test_missing_declaration_uses_ie20(self):
        w = self.world()
        w.declaration.unlink()
        p = w.run("worksheet")
        assert_ie(self, p, "IE-20", IE_WORDINGS["IE-20"].format(path=str(w.declaration)))

    def test_missing_verdicts_at_remaining_is_ie31(self):
        w = self.world()
        p = w.run("remaining")
        assert_ie(self, p, "IE-31", IE_WORDINGS["IE-31"].format(path=str(w.verdicts)))

    def test_unreadable_corpus_by_directory(self):
        w = self.world()
        w.corpus.unlink()
        w.corpus.mkdir()
        p = w.run("worksheet")
        assert_ie(self, p, "IE-05", IE_WORDINGS["IE-05"].format(kind="corpus", path=str(w.corpus)))

    def test_unreadable_amendment_by_directory(self):
        w = self.world()
        w.amendment.unlink()
        w.amendment.mkdir()
        p = w.run("worksheet")
        assert_ie(self, p, "IE-05", IE_WORDINGS["IE-05"].format(kind="amendment", path=str(w.amendment)))

    def test_unreadable_declaration_by_directory(self):
        w = self.world()
        w.declaration.unlink()
        w.declaration.mkdir()
        p = w.run("worksheet")
        assert_ie(self, p, "IE-05", IE_WORDINGS["IE-05"].format(kind="declaration", path=str(w.declaration)))


class TestSizeLimits(RcgTestCase):
    def _padded_corpus(self, w, total):
        base = w.corpus_bytes
        pad = total - len(base)
        assert pad >= 0
        text = base.decode() + ("# padding line\n" * (pad // 15)) + ("x" * (pad % 15))
        data = text.encode()
        assert len(data) == total, len(data)
        w.corpus.write_bytes(data)
        return data

    def test_exactly_at_limit_passes_size_gate(self):
        w = self.world()
        self._padded_corpus(w, BYTE_LIMIT)
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)

    def test_one_byte_over_limit_refused(self):
        w = self.world()
        self._padded_corpus(w, BYTE_LIMIT + 1)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-06", IE_WORDINGS["IE-06"].format(kind="corpus", measured=2000001, path=str(w.corpus)))
        assert_no_files(self, w.out1, w.out2)

    def test_oversize_measured_value_is_file_system_size(self):
        w = self.world()
        self._padded_corpus(w, 2000100)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-06", IE_WORDINGS["IE-06"].format(kind="corpus", measured=2000100, path=str(w.corpus)))
        self.assertNotIn("is 2000000 bytes, over the limit", p.stderr)

    def test_oversize_amendment(self):
        w = self.world()
        data = b"item: A1\n" + b"x" * 2000001
        w.amendment.write_bytes(data)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-06", IE_WORDINGS["IE-06"].format(kind="amendment", measured=len(data), path=str(w.amendment)))
        assert_no_files(self, w.out1, w.out2)


class TestEmptyAndEncoding(RcgTestCase):
    def test_empty_corpus_distinct_wording(self):
        w = self.world()
        w.corpus.write_bytes(b"")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-07", IE_WORDINGS["IE-07"].format(path=str(w.corpus)))

    def test_non_utf8_corpus(self):
        w = self.world()
        w.corpus.write_bytes(b"\xff\xfe not text")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-13", IE_WORDINGS["IE-13"].format(path=str(w.corpus)))

    def test_non_utf8_amendment(self):
        w = self.world()
        w.amendment.write_bytes(b"item: A1\n\xff\xfe")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-08", IE_WORDINGS["IE-08"].format(kind="amendment", path=str(w.amendment)))

    def test_non_utf8_declaration(self):
        w = self.world()
        w.declaration.write_bytes(b"declarer: X\n\xff")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-08", IE_WORDINGS["IE-08"].format(kind="declaration", path=str(w.declaration)))

    def test_non_utf8_verdicts(self):
        w = self.world()
        w.verdicts.write_bytes(b"\xff\xfe")
        p = w.run("finalise")
        assert_ie(self, p, "IE-08", IE_WORDINGS["IE-08"].format(kind="verdicts", path=str(w.verdicts)))


class TestFingerprints(RcgTestCase):
    def test_oracle_fingerprint_literal_in_record(self):
        w = self.world()
        w.amendment_bytes = ORACLE_TEXT.encode()
        w.amendment.write_bytes(w.amendment_bytes)
        w.set_declaration([("A1", ["Gap 1"], {"Gap 1": "Basis prose for Gap 1 on A1."})])
        from rcg_common import JUDGE, AUTHOR
        p = w.run("worksheet", judge=AUTHOR)
        self.assertEqual(p.returncode, 6, p.stderr)
        self.assertIn(ORACLE_SHA256, w.read_out1())

    def test_zero_byte_fingerprint_literal(self):
        w = self.world()
        w.verdicts.write_bytes(b"")
        from rcg_common import pass_specs
        p = w.run("finalise")
        self.assertEqual(p.returncode, 3, p.stderr)
        text = w.read_out1()
        self.assertIn(ZERO_BYTE_SHA256, text)
        data = w.read_results()
        self.assertEqual(data["fingerprints"]["verdicts"], ZERO_BYTE_SHA256)

    def test_non_default_path_printed_in_record(self):
        w = self.world()
        from rcg_common import pass_specs
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)
        text = w.read_out1()
        self.assertIn(str(w.corpus), text)
        self.assertNotIn("default", text.split("corpus path")[1].splitlines()[0] if "corpus path" in text else "")


if __name__ == "__main__":
    unittest.main()
