"""The ten named mutations of plan part 8, each one change on the shipped example set."""

import re
import shutil
import unittest
from pathlib import Path

from rcg_common import (
    RcgTestCase, EXAMPLES_DIR, run_program, derive_example_args, assert_ie,
    IE_WORDINGS, scan_checked_ids, scan_tokens,
)


class MutationWorld(RcgTestCase):
    def copy_examples(self):
        self.assertTrue(EXAMPLES_DIR.exists(),
                        "the shipped example set does not stand at %s" % EXAMPLES_DIR)
        w = self.world()
        target = w.dir / "examples"
        shutil.copytree(EXAMPLES_DIR, target)
        return w, target

    def run_finalise(self, w, target):
        args = derive_example_args(target, "finalise", w.out1, w.out2)
        return run_program(args)


def replace_line(text, prefix, new_line, count=1):
    lines = text.splitlines()
    done = 0
    for i, line in enumerate(lines):
        if line.startswith(prefix) and done < count:
            lines[i] = new_line
            done += 1
    assert done == count, prefix
    return "\n".join(lines) + "\n"


class TestMutations(MutationWorld):
    def test_mutation_01_token_removed_unverifiable(self):
        w, ex = self.copy_examples()
        corpus = (ex / "example_corpus.md").read_bytes()
        declaration = (ex / "example_declaration.txt").read_text()
        blocks = {}
        current = None
        in_confirmation = False
        for line in declaration.splitlines():
            if line == "confirmation:":
                in_confirmation = True
            if line.startswith("item: ") and not in_confirmation:
                current = line.split(": ", 1)[1]
                blocks[current] = []
            elif line.startswith("token: ") and current and not in_confirmation:
                blocks[current].append(line.split(" | ")[0].split(": ", 1)[1])
        chosen = None
        for label, tokens in blocks.items():
            for tok in tokens:
                remaining = [t for t in tokens if t != tok]
                if remaining and not scan_checked_ids(corpus, remaining):
                    chosen = (label, tok)
                    break
            if chosen:
                break
        self.assertIsNotNone(chosen, "no single token removal empties an item selection in the example set: "
                                     "stage 14 still owes an example set shape for mutation 1, namely at least one item "
                                     "declaring two or more tokens where exactly one of them selects rows, so that removing "
                                     "the selecting token leaves a nonempty declaration whose selection empties")
        label, tok = chosen
        lines = declaration.splitlines()
        out = []
        in_conf = False
        conf_item = None
        for line in lines:
            if line == "confirmation:":
                in_conf = True
            if not in_conf and line.startswith("token: %s |" % tok):
                continue
            if in_conf and line.startswith("item: "):
                conf_item = line.split(": ", 1)[1]
            if in_conf and conf_item == label and line.startswith("tokens: "):
                kept = [t for t in line.split(": ", 1)[1].split(", ") if t != tok]
                line = "tokens: " + ", ".join(kept)
            out.append(line)
        (ex / "example_declaration.txt").write_text("\n".join(out) + "\n")
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-34", IE_WORDINGS["IE-34"].format(label=label, id="C-001"))
        self.assertFalse(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_mutation_02_confirmation_altered_stale(self):
        w, ex = self.copy_examples()
        path = ex / "example_declaration.txt"
        text = path.read_text()
        head, sep, tail = text.partition("confirmation:")
        lines = tail.splitlines()
        altered_label = None
        current_item = None
        for i, line in enumerate(lines):
            if line.startswith("item: "):
                current_item = line.split(": ", 1)[1]
            if line.startswith("tokens: ") and "no-touch" not in line:
                lines[i] = line + ", Gap 999"
                altered_label = current_item
                break
        self.assertIsNotNone(altered_label)
        path.write_text(head + sep + "\n".join(lines) + "\n")
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-19", IE_WORDINGS["IE-19"].format(label=altered_label))
        self.assertFalse(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_mutation_03_claim_changed_to_settled_entry(self):
        w, ex = self.copy_examples()
        queue = (ex / "example_queue.md").read_text()
        settled_id = None
        current_id = None
        for line in queue.splitlines():
            m = re.search(r"DQ-\d+", line) if line.startswith("#") else None
            if m:
                current_id = m.group(0)
            if line.startswith("Status:") and "SETTLED" in line:
                settled_id = current_id
        self.assertIsNotNone(settled_id, "the example queue holds no settled entry")
        path = ex / "example_verdicts.txt"
        text = path.read_text()
        text = replace_line(text, "queue-item: ", "queue-item: " + settled_id)
        path.write_text(text)
        p = self.run_finalise(w, ex)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(w.read_results()["outcome"], "fail")

    def test_mutation_04_ruling_date_emptied(self):
        w, ex = self.copy_examples()
        path = ex / "example_verdicts.txt"
        label, cid = _claim_block_pair(path)
        path.write_text(replace_line(path.read_text(), "ruling-date: ", "ruling-date: "))
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-44", IE_WORDINGS["IE-44"].format(label=label, id=cid))
        self.assertFalse(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_mutation_05_word_outside_vocabulary(self):
        w, ex = self.copy_examples()
        path = ex / "example_verdicts.txt"
        text = path.read_text()
        self.assertIn("word: PASS", text)
        label, cid = _first_pass_pair(path)
        path.write_text(text.replace("word: PASS", "word: MAYBE", 1))
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-32", IE_WORDINGS["IE-32"].format(label=label, id=cid, word="MAYBE"))
        self.assertFalse(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_mutation_06_verdict_block_duplicated(self):
        w, ex = self.copy_examples()
        path = ex / "example_verdicts.txt"
        lines = path.read_text().splitlines()
        start = next(i for i, l in enumerate(lines) if l.startswith("verdict: "))
        label = lines[start].split(" ")[1]
        cid = lines[start].split(" ")[2]
        block = lines[start:start + 5]
        lines = lines[:start] + block + lines[start:]
        path.write_text("\n".join(lines) + "\n")
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-33", IE_WORDINGS["IE-33"].format(label=label, id=cid))
        self.assertFalse(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_mutation_07_verdict_for_flagged_row_added(self):
        w, ex = self.copy_examples()
        verdicts = (ex / "example_verdicts.txt").read_text()
        checked = [l.split(": ", 1)[1] for l in verdicts.splitlines() if l.startswith("checked: ")]
        corpus_lines = (ex / "example_corpus.md").read_text().splitlines()
        outside = None
        clause = None
        judge = [l.split(": ", 1)[1] for l in verdicts.splitlines() if l.startswith("judge-of-record: ")][0]
        label = [l.split(": ", 1)[1] for l in verdicts.splitlines() if l.startswith("verdict: ")][0].split(" ")[0]
        for line in corpus_lines:
            if line.startswith("| C-"):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) != 6:
                    continue
                if not _is_flagged_row(cells):
                    continue
                outside = cells[0]
                proc = cells[5]
                idx = proc.rfind("; fail if")
                if idx >= 0:
                    candidate = proc[idx + 2:].strip()
                    core = candidate.rstrip(". \t").strip()
                    clause = candidate if core != "fail if" else "no closing fail clause stands"
                else:
                    clause = "no closing fail clause stands"
                break
        self.assertIsNotNone(outside, "the example set holds no flagged row")
        self.assertNotIn(outside, checked, "the flagged row stands outside the checked set in the example set")
        addition = ("verdict: %s %s\njudge: %s\nclause: %s\nword: PASS\nreason: An added verdict.\n"
                    % (label, outside, judge, clause))
        (ex / "example_verdicts.txt").write_text(verdicts + addition)
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-34", IE_WORDINGS["IE-34"].format(label=label, id=outside))
        self.assertFalse(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_mutation_08_verdict_judge_changed_to_author(self):
        w, ex = self.copy_examples()
        path = ex / "example_verdicts.txt"
        label, cid = _first_verdict_pair(path)
        path.write_text(replace_line(path.read_text(), "judge: ", "judge: Example Author Seat"))
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-37", IE_WORDINGS["IE-37"].format(label=label, id=cid, judge="Example Author Seat"))
        self.assertFalse(w.out1.exists())
        self.assertFalse(w.out2.exists())

    def test_mutation_09_checked_line_removed(self):
        w, ex = self.copy_examples()
        path = ex / "example_verdicts.txt"
        all_lines = path.read_text().splitlines()
        first_checked = [l for l in all_lines if l.startswith("checked: ")][0]
        kept = [l for l in all_lines if l != first_checked]
        self.assertEqual(len(kept), len(all_lines) - 1)
        path.write_text("\n".join(kept) + "\n")
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-38", IE_WORDINGS["IE-38"].format(value="checked ID set"))

    def test_mutation_10_declaration_fingerprint_changed(self):
        w, ex = self.copy_examples()
        path = ex / "example_declaration.txt"
        text = path.read_text()
        old = [l for l in text.splitlines() if l.startswith("amendment-fingerprint: ")][0]
        fp = old.split(": ", 1)[1]
        changed = ("0" if fp[0] != "0" else "1") + fp[1:]
        path.write_text(text.replace(old, "amendment-fingerprint: " + changed))
        from rcg_common import sha256_hex
        amendment_fp = sha256_hex((ex / "example_amendment.md").read_bytes())
        p = self.run_finalise(w, ex)
        assert_ie(self, p, "IE-18", IE_WORDINGS["IE-18"].format(a=changed, b=amendment_fp))
        self.assertFalse(w.out1.exists())
        self.assertFalse(w.out2.exists())


def _first_verdict_pair(path):
    for line in path.read_text().splitlines():
        if line.startswith("verdict: "):
            parts = line.split(" ")
            return parts[1], parts[2]
    return "A1", None


def _first_pass_pair(path):
    current = None
    for line in path.read_text().splitlines():
        if line.startswith("verdict: "):
            parts = line.split(" ")
            current = (parts[1], parts[2])
        elif line == "word: PASS" and current is not None:
            return current
    return _first_verdict_pair(path)


def _claim_block_pair(path):
    current = None
    for line in path.read_text().splitlines():
        if line.startswith("verdict: "):
            parts = line.split(" ")
            current = (parts[1], parts[2])
        elif line == "claim:" and current is not None:
            return current
    return _first_verdict_pair(path)


def _is_flagged_row(cells):
    _cid, _source, incident, test, _index, proc = cells
    if not incident or not test or not proc:
        return True
    for cell in (incident, test, proc):
        trimmed = cell.strip()
        while trimmed and trimmed[-1] in "\"')]}":
            trimmed = trimmed[:-1].rstrip()
        if trimmed.endswith("\u2026") or trimmed.endswith("..."):
            return True
    if "; fail if" not in proc:
        return True
    clause = proc.split("; fail if", 1)[1]
    if ("fail if" + clause).rstrip(". \t").strip() == "fail if":
        return True
    return False


if __name__ == "__main__":
    unittest.main()
