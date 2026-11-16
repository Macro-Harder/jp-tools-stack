"""T19, examples and README. Brief section 13; plan part 7."""

import json
import re
import tempfile
import unittest
from pathlib import Path

from rcg_common import (
    RcgTestCase, EXAMPLES_DIR, run_program, derive_example_args,
    STATUS_TABLE, SENTENCES,
)

EXAMPLE_FILES = [
    "example_corpus.md", "example_amendment.md", "example_declaration.txt",
    "example_queue.md", "example_verdicts.txt", "example_report.txt",
    "example_results.json",
]

PATH_PLACEHOLDER = b"<EXAMPLES_DIR>"


def normalised_for_compare(produced, golden):
    """Return both outputs with the example directory prefix normalised.

    The produced bytes carry the actual example directory path of the tree
    the run used. The golden bytes carry the prefix recorded when the golden
    was generated, which names the tree of that generation. Both prefixes
    are replaced with one fixed placeholder. Every other byte is left
    exactly as it stands, so any other difference still fails the compare.
    """
    actual = str(EXAMPLES_DIR).encode()
    produced_norm = produced.replace(actual, PATH_PLACEHOLDER)
    golden_norm = golden.replace(actual, PATH_PLACEHOLDER)
    recorded = rb"[^\s\"']+/examples(?=/example_)"
    produced_norm = re.sub(recorded, PATH_PLACEHOLDER, produced_norm)
    golden_norm = re.sub(recorded, PATH_PLACEHOLDER, golden_norm)
    return produced_norm, golden_norm


def flagged_rows(corpus_text):
    flagged = []
    for line in corpus_text.splitlines():
        if not line.startswith("| C-"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) != 6:
            continue
        cid, _source, incident, test, _index, proc = cells
        is_flagged = False
        if not incident or not test or not proc:
            is_flagged = True
        for cell in (incident, test, proc):
            trimmed = cell.strip()
            while trimmed and trimmed[-1] in "\"')]}":
                trimmed = trimmed[:-1].rstrip()
            if trimmed.endswith("\u2026") or trimmed.endswith("..."):
                is_flagged = True
        if "; fail if" not in proc:
            is_flagged = True
        else:
            clause = proc.split("; fail if", 1)[1]
            clause_core = ("fail if" + clause).rstrip(". \t").strip()
            if clause_core == "fail if":
                is_flagged = True
        if is_flagged:
            flagged.append(cid)
    return flagged


class TestExampleSet(RcgTestCase):
    def setUp(self):
        self.assertTrue(EXAMPLES_DIR.exists(),
                        "the shipped example set does not stand at %s" % EXAMPLES_DIR)

    def test_example_files_exist(self):
        for name in EXAMPLE_FILES:
            self.assertTrue((EXAMPLES_DIR / name).exists(), "missing example file %s" % name)

    def test_example_regeneration_byte_for_byte(self):
        w = self.world()
        args = derive_example_args(EXAMPLES_DIR, "finalise", w.out1, w.out2)
        p = run_program(args)
        self.assertEqual(p.returncode, 5, p.stderr)
        produced_report, golden_report = normalised_for_compare(
            w.out1.read_bytes(), (EXAMPLES_DIR / "example_report.txt").read_bytes())
        self.assertEqual(produced_report, golden_report)
        produced_results, golden_results = normalised_for_compare(
            w.out2.read_bytes(), (EXAMPLES_DIR / "example_results.json").read_bytes())
        self.assertEqual(produced_results, golden_results)
        data = w.read_results()
        self.assertEqual(data["outcome"], "re-ruled pass")

    def test_example_flagged_row_outside_checked_set(self):
        verdicts = (EXAMPLES_DIR / "example_verdicts.txt").read_text()
        corpus = (EXAMPLES_DIR / "example_corpus.md").read_text()
        report = (EXAMPLES_DIR / "example_report.txt").read_text()
        results_text = (EXAMPLES_DIR / "example_results.json").read_text()
        results = json.loads(results_text)
        flagged = flagged_rows(corpus)
        self.assertEqual(len(flagged), 1, "the example corpus holds exactly one flagged row, found %s" % flagged)
        flagged_id = flagged[0]
        checked = [l.split(": ", 1)[1] for l in verdicts.splitlines() if l.startswith("checked: ")]
        self.assertTrue(checked)
        self.assertNotIn(flagged_id, checked)
        verdict_pairs = [l for l in verdicts.splitlines() if l.startswith("verdict: ")]
        for line in verdict_pairs:
            self.assertNotEqual(line.split(" ")[2], flagged_id, "a verdict stands on the flagged row")
        self.assertNotIn(flagged_id, results["checked_ids"])
        for item in results["items"]:
            self.assertNotIn(flagged_id, item["checked_ids"])
            for verdict in item["verdicts"]:
                self.assertNotEqual(verdict["corpus_id"], flagged_id)
        self.assertNotIn("row %s for item" % flagged_id, report)
        for line in report.splitlines():
            if line.startswith("checked:"):
                self.assertNotEqual(line.split(": ", 1)[1], flagged_id)

    def test_example_template_regeneration(self):
        w = self.world()
        args = derive_example_args(EXAMPLES_DIR, "worksheet", w.out1, w.out2)
        p = run_program(args)
        self.assertEqual(p.returncode, 10, p.stderr)
        template = w.out2.read_text()
        example_verdicts = (EXAMPLES_DIR / "example_verdicts.txt").read_text()
        template_blocks = sorted(l for l in template.splitlines() if l.startswith("verdict: "))
        example_blocks = sorted(l for l in example_verdicts.splitlines() if l.startswith("verdict: "))
        self.assertEqual(template_blocks, example_blocks)
        for line in example_verdicts.splitlines():
            if line.startswith(("amendment-fingerprint:", "corpus-fingerprint:", "declaration-fingerprint:",
                                "declared-mode:", "effective-mode:", "triggers:", "checked:", "judge-of-record:")):
                self.assertIn(line, template)


class TestReadme(RcgTestCase):
    def _readme(self):
        path = EXAMPLES_DIR.parent / "README.md"
        self.assertTrue(path.exists(), "the shipped README does not stand at %s" % path)
        return path.read_text()

    def test_readme_names_three_forms(self):
        text = self._readme()
        for form in ("worksheet", "remaining", "finalise"):
            self.assertIn(form, text)

    def test_readme_outcome_table_and_sentences(self):
        text = self._readme()
        lines = text.splitlines()
        for status, term in STATUS_TABLE.items():
            paired = any(
                re.search(r"\b%d\b" % status, line) and term in line
                for line in lines
            )
            self.assertTrue(paired, "no README line pairs status %d with %s" % (status, term))
        for term, sentence in SENTENCES.items():
            self.assertIn(sentence, text, "the plain sentence for %s is not stated" % term)

    def test_readme_distinctions_and_bounds(self):
        text = self._readme()
        self.assertIn("this gate judges proposed amendments against the corpus before they take effect, while the suite replays known failures against a built thing", text)
        self.assertIn("informs a closure decision and makes none", text)
        self.assertIn("Python 3.12 or later", text)

    def test_readme_three_checks_status_difference(self):
        text = self._readme()
        self.assertIn("three-checks", text)
        self.assertIn("status 3 is incomplete in this tool and UNVERIFIABLE in three-checks", text)
        self.assertIn("status 4 is unverifiable in this tool and barred in three-checks", text)
        self.assertIn("status 6 is barred in this tool, and three-checks has no status 6, its barred run being status 4", text)

    def test_readme_syntax_summaries_and_input_error_rule(self):
        text = self._readme()
        for marker in ("item:", "token:", "no-touch:", "verdict:", "claim:", "confirmation:"):
            self.assertIn(marker, text, "no file syntax summary carries %s" % marker)
        self.assertIn("every input error is printed with its distinct wording and writes no file", text)


if __name__ == "__main__":
    unittest.main()
