"""T1, usage and paths. Brief sections 2 and 11; plan parts 2 and 4.3."""

import unittest
from pathlib import Path

from rcg_common import (
    RcgTestCase, World, run_program, assert_ie, assert_usage, assert_no_files,
    IE_WORDINGS, JUDGE, AUTHOR,
)


class TestCorrectShapes(RcgTestCase):
    def test_worksheet_shape_accepted(self):
        w = self.world()
        p = w.run("worksheet")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertTrue(w.out1.exists())
        self.assertTrue(w.out2.exists())

    def test_remaining_shape_accepted(self):
        w = self.world()
        w.write_verdicts([])
        p = w.run("remaining", context="stated")
        self.assertEqual(p.returncode, 9, p.stderr)

    def test_finalise_shape_accepted(self):
        w = self.world()
        from rcg_common import pass_specs
        w.write_verdicts(pass_specs())
        p = w.run("finalise", context="stated")
        self.assertEqual(p.returncode, 0, p.stderr)


MISSING_CASES = [
    ("worksheet", "--judge", "IE-47", "--judge"),
    ("worksheet", "--runner", "IE-47", "--runner"),
    ("worksheet", "--author", "IE-47", "--author"),
    ("worksheet", "--ruler", "IE-47", "--ruler"),
    ("worksheet", "--coordinator", "IE-47", "--coordinator"),
    ("finalise", "--judge", "IE-47", "--judge"),
    ("worksheet", "--tier", "IE-48", "--tier"),
    ("worksheet", "--change-index-system", "IE-48", "--change-index-system"),
    ("worksheet", "--change-gate-rule", "IE-48", "--change-gate-rule"),
    ("worksheet", "--change-corpus", "IE-48", "--change-corpus"),
    ("worksheet", "--change-definition", "IE-48", "--change-definition"),
    ("worksheet", "--change-counting-method", "IE-48", "--change-counting-method"),
    ("worksheet", "--change-verdict-form", "IE-48", "--change-verdict-form"),
    ("worksheet", "--change-closure-rule", "IE-48", "--change-closure-rule"),
    ("finalise", "--reader-designate", "IE-51", None),
    ("worksheet", "--amendment", "IE-52", "--amendment"),
    ("worksheet", "--declaration", "IE-52", "--declaration"),
    ("worksheet", "--worksheet-out", "IE-52", "--worksheet-out"),
    ("worksheet", "--template-out", "IE-52", "--template-out"),
    ("remaining", "--remaining-out", "IE-52", "--remaining-out"),
    ("finalise", "--report-out", "IE-52", "--report-out"),
    ("finalise", "--results-out", "IE-52", "--results-out"),
    ("remaining", "--verdicts", "IE-52", "--verdicts"),
    ("worksheet", "--declared-mode", "IE-52", "--declared-mode"),
    ("remaining", "--judge", "IE-47", "--judge"),
    ("remaining", "--runner", "IE-47", "--runner"),
    ("remaining", "--author", "IE-47", "--author"),
    ("remaining", "--ruler", "IE-47", "--ruler"),
    ("remaining", "--coordinator", "IE-47", "--coordinator"),
    ("finalise", "--runner", "IE-47", "--runner"),
    ("finalise", "--author", "IE-47", "--author"),
    ("finalise", "--ruler", "IE-47", "--ruler"),
    ("finalise", "--coordinator", "IE-47", "--coordinator"),
    ("remaining", "--tier", "IE-48", "--tier"),
    ("finalise", "--tier", "IE-48", "--tier"),
    ("remaining", "--change-corpus", "IE-48", "--change-corpus"),
    ("finalise", "--change-corpus", "IE-48", "--change-corpus"),
    ("remaining", "--declared-mode", "IE-52", "--declared-mode"),
    ("finalise", "--declared-mode", "IE-52", "--declared-mode"),
    ("remaining", "--amendment", "IE-52", "--amendment"),
    ("finalise", "--amendment", "IE-52", "--amendment"),
    ("remaining", "--declaration", "IE-52", "--declaration"),
    ("finalise", "--declaration", "IE-52", "--declaration"),
    ("finalise", "--verdicts", "IE-52", "--verdicts"),
]


class TestMissingRequired(RcgTestCase):
    pass


for _form, _flag, _ie, _named in MISSING_CASES:
    def _make(form=_form, flag=_flag, ie=_ie, named=_named):
        def test(self):
            w = self.world()
            p = w.run(form, drop=(flag,))
            if ie == "IE-51":
                wording = IE_WORDINGS["IE-51"]
            else:
                wording = IE_WORDINGS[ie].format(flag=named)
            assert_ie(self, p, ie, wording)
            assert_no_files(self, w.out1, w.out2)
        return test
    setattr(TestMissingRequired, "test_missing_%s_%s" % (_form, _flag.strip("-").replace("-", "_")), _make())


FORBIDDEN_CASES = [
    ("worksheet", ["--verdicts", "x.txt"]),
    ("worksheet", ["--reader-designate", "Reader Seat"]),
    ("worksheet", ["--remaining-out", "x.txt"]),
    ("worksheet", ["--report-out", "x.txt"]),
    ("worksheet", ["--results-out", "x.txt"]),
    ("remaining", ["--reader-designate", "Reader Seat"]),
    ("remaining", ["--queue", "x.txt"]),
    ("remaining", ["--worksheet-out", "x.txt"]),
    ("remaining", ["--template-out", "x.txt"]),
    ("remaining", ["--report-out", "x.txt"]),
    ("remaining", ["--results-out", "x.txt"]),
    ("finalise", ["--worksheet-out", "x.txt"]),
    ("finalise", ["--template-out", "x.txt"]),
    ("finalise", ["--remaining-out", "x.txt"]),
]


class TestUsageErrors(RcgTestCase):
    def test_missing_form_is_usage(self):
        w = self.world()
        args = w.args("worksheet")
        args = args[2:]
        p = run_program(args)
        assert_usage(self, p)
        assert_no_files(self, w.out1, w.out2)

    def test_bad_form_word_is_usage(self):
        w = self.world()
        args = w.args("worksheet")
        args[1] = "finalize"
        p = run_program(args)
        assert_usage(self, p)

    def test_duplicated_singleton_flag(self):
        w = self.world()
        p = w.run("worksheet", extra=["--runner", "Other Seat"])
        assert_usage(self, p)
        assert_no_files(self, w.out1, w.out2)

    def test_unknown_flag(self):
        w = self.world()
        p = w.run("worksheet", extra=["--bogus", "x"])
        assert_usage(self, p)

    def test_flag_with_no_value(self):
        w = self.world()
        args = w.args("worksheet") + ["--tier"]
        p = run_program(args)
        assert_usage(self, p)

    def test_positional_argument(self):
        w = self.world()
        p = w.run("worksheet", extra=["stray"])
        assert_usage(self, p)

    def test_bad_declared_mode_value(self):
        w = self.world()
        p = w.run("worksheet", declared_mode="partial")
        assert_usage(self, p)

    def test_bad_context_value(self):
        w = self.world()
        p = w.run("worksheet", context="clear")
        assert_usage(self, p)

    def test_bad_tier_value(self):
        w = self.world()
        p = w.run("worksheet", tier="Huge")
        assert_usage(self, p)

    def test_bad_change_flag_value(self):
        w = self.world()
        p = w.run("worksheet", change_flags={"corpus": "maybe"})
        assert_usage(self, p)


for _i, (_form, _extra) in enumerate(FORBIDDEN_CASES):
    def _make(form=_form, extra=_extra):
        def test(self):
            w = self.world()
            p = w.run(form, extra=extra)
            assert_usage(self, p)
            assert_no_files(self, w.out1, w.out2)
        return test
    setattr(TestUsageErrors, "test_forbidden_%02d_%s" % (_i, _form), _make())


class TestPaths(RcgTestCase):
    def test_output_names_input(self):
        w = self.world()
        args = w.args("worksheet")
        args[args.index("--worksheet-out") + 1] = str(w.corpus)
        p = run_program(args)
        assert_ie(self, p, "IE-01", IE_WORDINGS["IE-01"].format(output=str(w.corpus), input=str(w.corpus)))

    def test_two_outputs_name_one_file(self):
        w = self.world()
        args = w.args("worksheet")
        args[args.index("--template-out") + 1] = str(w.out1)
        p = run_program(args)
        assert_ie(self, p, "IE-02", IE_WORDINGS["IE-02"].format(first=str(w.out1), second=str(w.out1)))

    def test_output_already_exists_as_file(self):
        w = self.world()
        w.out1.write_text("standing\n")
        p = w.run("worksheet")
        assert_ie(self, p, "IE-03", IE_WORDINGS["IE-03"].format(path=str(w.out1)))
        self.assertEqual(w.out1.read_text(), "standing\n")

    def test_output_already_exists_as_directory(self):
        w = self.world()
        w.out1.mkdir()
        p = w.run("worksheet")
        assert_ie(self, p, "IE-03", IE_WORDINGS["IE-03"].format(path=str(w.out1)))

    def test_symlink_output_resolves_to_input(self):
        w = self.world()
        link = w.dir / "link.txt"
        link.symlink_to(w.corpus)
        args = w.args("worksheet")
        args[args.index("--worksheet-out") + 1] = str(link)
        p = run_program(args)
        resolved = str(Path(w.corpus).resolve())
        assert_ie(self, p, "IE-01", IE_WORDINGS["IE-01"].format(output=resolved, input=resolved))

    def test_delivery_failure_parent_is_regular_file(self):
        w = self.world()
        blocker = w.dir / "blocker"
        blocker.write_text("x\n")
        target = blocker / "out.txt"
        args = w.args("worksheet")
        args[args.index("--worksheet-out") + 1] = str(target)
        p = run_program(args)
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("delivery failure: the output at %s could not be written" % target, p.stderr)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
