"""T4, amendment and declaration syntax. Brief sections 3 and 5; plan parts 3.1, 3.2, 3.5."""

import unittest

from rcg_common import (
    RcgTestCase, assert_ie, assert_no_files, IE_WORDINGS, amendment_text,
    declaration_text, default_spec, sha256_hex, AUTHOR, DECLARER, CONFIRMER,
)


class TestAmendmentCases(RcgTestCase):
    def test_empty_amendment_ie14(self):
        w = self.world()
        w.amendment.write_bytes(b"")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-14", IE_WORDINGS["IE-14"])
        assert_no_files(self, w.out1, w.out2)

    def test_text_before_first_label_ie15(self):
        w = self.world()
        w.amendment.write_text("Stray wording with no label.\nitem: A1\nThe wording stands.\n")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-15", IE_WORDINGS["IE-15"].format(n=1))

    def test_empty_label_ie15(self):
        w = self.world()
        w.amendment.write_text("item: \nThe wording stands.\n")
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("input error IE-15:", p.stderr)

    def test_duplicated_label_ie16(self):
        w = self.world()
        w.set_amendment([("A1", "First wording."), ("A1", "Second wording.")])
        p = w.run("worksheet")
        assert_ie(self, p, "IE-16", IE_WORDINGS["IE-16"].format(label="A1"))

    def test_no_wording_text_ie17(self):
        w = self.world()
        w.set_amendment([("A1", ""), ("A2", "The wording stands.")])
        p = w.run("worksheet")
        assert_ie(self, p, "IE-17", IE_WORDINGS["IE-17"].format(label="A1"))

    def test_all_blank_lines_after_label_ie17(self):
        w = self.world()
        w.amendment.write_text("item: A1\n\n\nitem: A2\nThe wording stands.\n")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-17", IE_WORDINGS["IE-17"].format(label="A1"))

    def test_comment_lines_only_count_as_wording(self):
        w = self.world()
        w.amendment.write_text("item: A1\n# a comment line stands as wording\nitem: A2\nThe wording stands.\n")
        w.amendment_bytes = w.amendment.read_bytes()
        w.set_declaration(default_spec())
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)

    def test_indented_marker_line_is_wording(self):
        w = self.world()
        w.amendment.write_text("item: A1\n item: A2 quoted with one leading space\nitem: A2\nThe wording stands.\n")
        w.amendment_bytes = w.amendment.read_bytes()
        w.set_declaration(default_spec())
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)

    def test_unindented_marker_line_splits_item(self):
        w = self.world()
        w.amendment.write_text("item: A1\nitem: A2\nThe wording stands.\n")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-17", IE_WORDINGS["IE-17"].format(label="A1"))


class TestDeclarationCases(RcgTestCase):
    def test_fingerprint_mismatch_ie18(self):
        w = self.world()
        wrong = "0" * 64
        w.set_declaration(default_spec(), fingerprint=wrong)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-18", IE_WORDINGS["IE-18"].format(a=wrong, b=sha256_hex(w.amendment_bytes)))

    def test_stale_confirmation_one_token_changed_ie19(self):
        w = self.world()
        conf = [("A1", ["Gap 2"], {"Gap 2": "x"}), ("A2", ["FM-1"], {"FM-1": "y"})]
        w.set_declaration(default_spec(), confirmation_spec=conf)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-19", IE_WORDINGS["IE-19"].format(label="A1"))

    def test_confirmation_order_differs_sets_equal_passes(self):
        w = self.world()
        spec = [("A1", ["Gap 1", "Gap 2"], {"Gap 1": "Basis one.", "Gap 2": "Basis two."}),
                ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."})]
        conf = [("A1", ["Gap 2", "Gap 1"], {}), ("A2", ["FM-1"], {})]
        w.set_declaration(spec, confirmation_spec=conf)
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)

    def test_bare_empty_declaration_ie21(self):
        w = self.world()
        w.declaration.write_bytes(b"")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-21", IE_WORDINGS["IE-21"])

    def test_empty_token_list_ie22(self):
        w = self.world()
        text = declaration_text(w.amendment_bytes, default_spec())
        lines = text.splitlines()
        lines = [l for l in lines if not l.startswith("token: Gap 1")]
        w.declaration.write_text("\n".join(lines) + "\n")
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 2, p.stderr)
        lines_out = p.stderr.splitlines()
        self.assertGreaterEqual(len(lines_out), 2, p.stderr)
        allowed = {
            "input error IE-22: " + IE_WORDINGS["IE-22"].format(label="A1"),
            "input error IE-26: " + IE_WORDINGS["IE-26"].format(label="A1"),
        }
        self.assertIn(lines_out[1], allowed)

    def test_explicit_no_touch_form_is_valid(self):
        w = self.world()
        spec = [("A1", None, "No touch basis for A1."), ("A2", None, "No touch basis for A2.")]
        w.set_declaration(spec)
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)

    def test_declaration_names_unknown_item_ie24(self):
        w = self.world()
        spec = default_spec() + [("A9", ["Gap 1"], {"Gap 1": "Basis."})]
        w.set_declaration(spec)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-24", IE_WORDINGS["IE-24"].format(label="A9"))

    def test_declaration_missing_block_ie25(self):
        w = self.world()
        w.set_declaration([default_spec()[0]])
        p = w.run("worksheet")
        assert_ie(self, p, "IE-25", IE_WORDINGS["IE-25"].format(label="A2"))

    def test_block_mixing_tokens_and_no_touch_ie26(self):
        w = self.world()
        text = declaration_text(w.amendment_bytes, default_spec())
        text = text.replace("item: A1\n", "item: A1\nno-touch: A stray assertion.\n", 1)
        w.declaration.write_text(text)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-26", IE_WORDINGS["IE-26"].format(label="A1"))

    def test_no_confirmation_block_ie27(self):
        w = self.world()
        text = declaration_text(w.amendment_bytes, default_spec())
        text = text.split("confirmation:")[0]
        w.declaration.write_text(text)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-27", IE_WORDINGS["IE-27"])

    def test_declarer_is_author_confirmer_is_author_ie28(self):
        w = self.world()
        w.set_declaration(default_spec(), declarer=AUTHOR, confirmer=AUTHOR)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-28", IE_WORDINGS["IE-28"].format(seat=AUTHOR))

    def test_declarer_is_author_confirmer_differs_passes(self):
        w = self.world()
        w.set_declaration(default_spec(), declarer=AUTHOR, confirmer=CONFIRMER)
        p = w.run("worksheet", second={"seat": "Second Seat", "context": "stated"})
        self.assertEqual(p.returncode, 10, p.stderr)

    def test_header_names_no_declarer_ie29(self):
        w = self.world()
        text = declaration_text(w.amendment_bytes, default_spec())
        text = text.replace("declarer: " + DECLARER + "\n", "")
        w.declaration.write_text(text)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-29", IE_WORDINGS["IE-29"])

    def test_token_line_without_basis_ie30(self):
        w = self.world()
        spec = [("A1", ["Gap 1"], {"Gap 1": ""}), ("A2", ["FM-1"], {"FM-1": "Basis."})]
        text = declaration_text(w.amendment_bytes, spec)
        w.declaration.write_text(text)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-30", IE_WORDINGS["IE-30"].format(label="A1"))

    def test_block_out_of_order_ie54(self):
        w = self.world()
        spec = [default_spec()[1], default_spec()[0]]
        w.set_declaration(spec)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-54", IE_WORDINGS["IE-54"].format(label="A2"))

    def test_duplicated_token_line_ie55(self):
        w = self.world()
        text = declaration_text(w.amendment_bytes, default_spec())
        text = text.replace("token: Gap 1 | basis: Basis prose for Gap 1 on A1.\n",
                            "token: Gap 1 | basis: Basis prose for Gap 1 on A1.\ntoken: Gap 1 | basis: Basis prose for Gap 1 on A1.\n")
        w.declaration.write_text(text)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-55", IE_WORDINGS["IE-55"].format(label="A1", token="Gap 1"))

    def test_duplicated_header_line_ie56(self):
        w = self.world()
        w.set_declaration(default_spec(), header_extra=["declarer: Other Seat"])
        p = w.run("worksheet")
        assert_ie(self, p, "IE-56", IE_WORDINGS["IE-56"].format(line="declarer"))

    def test_no_touch_empty_basis_ie57(self):
        w = self.world()
        spec = [("A1", None, ""), ("A2", ["FM-1"], {"FM-1": "Basis."})]
        text = declaration_text(w.amendment_bytes, spec)
        w.declaration.write_text(text)
        p = w.run("worksheet")
        assert_ie(self, p, "IE-57", IE_WORDINGS["IE-57"].format(label="A1"))


UNPARSEABLE = [
    ("Gap1", "missing space"),
    ("FM 1", "space in place of the FM hyphen"),
    ("gap 1", "lowercase kind word"),
    ("Gap 01", "leading zero"),
    ("fm-1", "lowercase FM"),
]


class TestUnparseableTokens(RcgTestCase):
    pass


for _tok, _name in UNPARSEABLE:
    def _make(tok=_tok):
        def test(self):
            w = self.world()
            spec = [("A1", [tok], {tok: "Basis prose."}), ("A2", ["FM-1"], {"FM-1": "Basis."})]
            w.set_declaration(spec)
            p = w.run("worksheet")
            assert_ie(self, p, "IE-23", IE_WORDINGS["IE-23"].format(label="A1", token=tok))
        return test
    setattr(TestUnparseableTokens, "test_unparseable_%s" % _name.replace(" ", "_"), _make())


if __name__ == "__main__":
    unittest.main()
