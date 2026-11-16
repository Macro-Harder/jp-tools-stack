"""Shared helpers and test side transcriptions for the regression-corpus-gate suite.

The transcriptions in this module are written from the design plan text and
are held as data independent of the program constants. Fixture builders build
small synthetic inputs. Expected fingerprints asserted as oracles are literals
recorded in this module, computed outside the tool.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
WORK_DIR = TESTS_DIR.parent
FIXTURES = TESTS_DIR / "fixtures"

STAGING_PROGRAM = (
    WORK_DIR / "staging" / "regression-corpus-gate" / "regression_corpus_gate.py"
)
LANDED_PROGRAM = Path.home() / "workspace" / "tools" / "regression-corpus-gate" / "regression_corpus_gate.py"
PROGRAM = STAGING_PROGRAM if STAGING_PROGRAM.exists() else LANDED_PROGRAM if LANDED_PROGRAM.exists() else STAGING_PROGRAM
EXAMPLES_DIR = (
    WORK_DIR / "staging" / "regression-corpus-gate" / "examples"
    if (WORK_DIR / "staging" / "regression-corpus-gate" / "examples").exists()
    else Path.home() / "workspace" / "tools" / "regression-corpus-gate" / "examples"
)

CANONICAL_CORPUS = Path.home() / "workspace" / "build-flow-expansion" / "REGRESSION-CORPUS.md"
CANONICAL_QUEUE = Path.home() / "workspace" / "build-flow-expansion" / "DECISION-QUEUE.md"

BYTE_LIMIT = 2000000
ZERO_BYTE_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
ORACLE_TEXT = "item: A1\nThe wording stands here.\n"
ORACLE_SHA256 = "9d6576a9ba563c28e478ced78817d793e0d9f1a214f1285daaf9e25a535391a0"

RUNNER = "Runner Seat"
JUDGE = "Judge Seat"
AUTHOR = "Author Seat"
RULER = "Ruler Seat"
COORDINATOR = "Coordinator Seat"
DECLARER = "Declarer Seat"
CONFIRMER = "Confirmer Seat"
READER = "Reader Seat"
PANEL = "Panel Seat"
PANEL2 = "Panel Two Seat"
SECOND = "Second Seat"

USAGE_SUMMARY = "usage: regression_corpus_gate.py --form worksheet|remaining|finalise [arguments]"

STATUS_TABLE = {
    0: "pass",
    1: "fail",
    2: "input error",
    3: "incomplete",
    4: "unverifiable",
    5: "re-ruled pass",
    6: "barred",
    7: "declaration conflict",
    8: "self test failure",
    9: "remaining rows report",
    10: "worksheet issued",
}

SENTENCES = {
    "pass": "The amendment passed every checked row and may go forward to filing and reading.",
    "fail": "The amendment is blocked because at least one checked row failed and no confirmed re-ruling excuses that fail.",
    "re-ruled pass": "The amendment may go forward because every fail is excused by a confirmed re-ruling that names its incident.",
    "incomplete": "The run is not finished because at least one checked row has no verdict, and an unfinished run is blocked.",
    "unverifiable": "The run could not settle the amendment because at least one checked row could not be judged or could not be tested.",
    "barred": "The run is barred because a judge is the author, the ruler, or the coordinator of the step, so no verdict may stand.",
    "input error": "The run could not start because an input is missing, malformed, or inconsistent, and the error line names the exact fault.",
    "declaration conflict": "The declaration does not cover an index that the wording itself names, so the declaration must be amended and confirmed again before any judging.",
    "self test failure": "The tool failed its own synthetic checks, so the run stopped before judging and no result from this run may be relied on.",
}

TRIGGER_ORDER = [
    "tier-plaid",
    "change-index-system",
    "change-gate-rule",
    "change-corpus",
    "change-definition",
    "change-counting-method",
    "change-verdict-form",
    "change-closure-rule",
    "context-unstated",
    "context-mixed",
    "context-disputed",
]

CHANGE_FLAGS = [
    ("--change-index-system", "index_system", "change-index-system"),
    ("--change-gate-rule", "gate_rule", "change-gate-rule"),
    ("--change-corpus", "corpus", "change-corpus"),
    ("--change-definition", "definition", "change-definition"),
    ("--change-counting-method", "counting_method", "change-counting-method"),
    ("--change-verdict-form", "verdict_form", "change-verdict-form"),
    ("--change-closure-rule", "closure_rule", "change-closure-rule"),
]

PROBE_NAMES = [
    "selection_probe",
    "pass_probe",
    "blocking_probe",
    "excused_fail_probe",
    "binding_probe",
]

SELF_TEST_RECORD_LINE = (
    "The self test proves the selection, the blocking arithmetic including the excused fail path, "
    "and the binding checks, over synthetic cases only, and proves nothing about the judging. "
    "In this line, selection means the one token, one item synthetic case of the selection probe, "
    "and binding checks means the one fingerprint alteration of the binding probe; no probe exercises "
    "the other binding values, the per item form of selection across several items, or any other part."
)

READBACK_FOOTER = (
    "this page shows what the declaration and the tripwire produced; a declaration wrong in a way "
    "no tripwire catches is not guarded by this page; it is guarded by the runner confirmation and "
    "the Auditor addition right"
)

NO_CLAUSE_STATEMENT = "no closing fail clause stands"

TEMPLATE_CLOSING_LINE = (
    "template: fill one block per checked pair. An untouched slot is empty on purpose. "
    "A FAIL verdict that claims an excuse carries exactly one claim block under its reason line."
)

WORKSHEET_FIXED_LINE = "worksheet: no verdicts exist yet in this form"

REMAINING_FIXED_LINES = [
    "remaining rows report: this report names the checked pairs that still lack a verdict. It issues no verdict and finalises nothing.",
    "an incomplete run is blocked, and a count of work left is not progress toward a pass",
]

NEXT_STEP_LINE = (
    "next step: The caller files this record into the trace the standing procedure names. "
    "This record informs a closure decision and makes none."
)

SIZING_LINE = (
    "sizing as measured: Gap 1 selects 159 rows, the Gap 1 to 4 union selects 218 rows, "
    "FM tokens together reach 34 rows, and a full run checks 224 rows per wording item; "
    "record size grows in proportion to rows checked times wording items; no output byte limit applies"
)

LIMIT_LINES_FIXED = [
    "a judge whose reasoning is wrong while the forms are complete is not detectable by this program; the layered answer is the fresh Auditor oversight of part 4.6 and the reader designate duty of part 5.4",
    "a declaration wrong from the start in a way no tripwire catches is not guarded by the readback page; the layered answer is the runner confirmation and the Auditor addition right",
    "the verdicts binding carries no run identifier in version 1; a verdicts input from an earlier run over unchanged inputs verifies against a later run over the same inputs",
    "a corpus content change that keeps the structure valid is visible only as a different fingerprint",
    "index tokens written in forms outside the tripwire extraction grammar are not extracted; ranges and compressed lists are outside the grammar",
    "judge fatigue across a long run is not detectable by this program; judging may proceed in sittings, and sittings change pacing and never the bar",
    "trigger facts are attestations by the runner; a wrong attestation is not detectable by this program; the layered answer is the Auditor oversight, the dispute attestation, and the record printing the attested facts beside the attester name",
]

GLOSSARY_LINES = [
    "pass: every checked row passed.",
    "fail: an unexcused fail blocks the amendment.",
    "re-ruled pass: a pass that stands only because a confirmed re-ruling excuses every fail.",
    "incomplete: a checked pair has no verdict, so no gate verdict is issued.",
    "unverifiable: a checked row could not be judged, or a claimed touch could not be tested.",
    "barred: a judge is the author, the ruler, or the coordinator, so the run may not proceed.",
    "checked pair: one corpus row taken with one wording item.",
    "excused fail: a fail whose incident a confirmed re-ruling names through the decision queue.",
    "reader designate: the named reader who must read this record outside it before the amendment takes effect.",
    "gate amendment run: a run whose amendment is attested as changing the gate, its selection rule, its exception rule, or the corpus front matter.",
]

PLAYBOOK_LINES = [
    "If the declaration conflicts: amend the declaration to cover every token the wording names, have it freshly confirmed, and rerun the worksheet form. No judging can start until the conflict clears.",
    "If the self test fails: stop. Do not judge any row. File the self test report reference with the state name and report the tool fault.",
    "If the run is barred: stop. A different judge of record must be named by the caller. Do not rename a judge inside the verdicts to get around the bar.",
    "If a verdicts file fails binding at finalise: an input changed or a trigger fired after the worksheet. Issue a fresh worksheet and template from the current inputs and judge again from them.",
    "If the run is incomplete: use the remaining form to name the pairs still missing verdicts. A partly filled run never finalises as anything but incomplete.",
    "If the queue cannot be verified at finalise: every claimed excuse stands unverified and its fail stands unexcused. Fix the queue path or the queue file and finalise again with a fresh verdicts binding where any input changed.",
    "If an output path already exists: name fresh output paths. The tool never overwrites a finished record.",
]

STATUS_MAPPING_ROWS = [
    ("RULED, closed", True, False),
    ("RULED", True, False),
    ("Ruled by Captain JP on the day", True, False),
    ("standing", False, True),
    ("SETTLED, closed", False, False),
    ("SETTLED as a Manager fill-in", False, False),
    ("Settled by the Manager under the grant", False, False),
    ("Banked", False, False),
    ("BANKED", False, False),
    ("PARKED", False, False),
    ("ORDERED", False, False),
    ("open", False, False),
    ("superseded", False, False),
    ("withdrawn", False, False),
    ("no status stated", False, False),
]

JSON_TOP_KEYS = [
    "tool", "version", "outcome", "exit_status", "trace_word", "runner",
    "judge_of_record", "panel_judges", "wording_author", "ruler",
    "step_coordinator", "reader_designate", "declarer", "confirming_seat",
    "fingerprints", "corpus_row_count", "paths", "declared_mode",
    "effective_mode", "triggers", "gate_amendment_run", "attestations",
    "indexes_searched", "tokens_with_no_rows", "checked_ids", "items",
    "re_ruling_candidates", "re_ruling_matches", "unverified_excuses",
    "blocked_items", "counts", "missing", "self_test", "limits",
    "reader_designate_line", "auditor_oversight_line",
]
JSON_NESTED_KEYS = {
    "fingerprints": ["corpus", "amendment", "declaration", "verdicts", "queue"],
    "paths": ["corpus", "amendment", "declaration", "verdicts", "queue"],
    "attestations": ["attester", "tier", "context", "effective_context", "change_flags", "second_attester"],
    "change_flags": ["index_system", "gate_rule", "corpus", "definition", "counting_method", "verdict_form", "closure_rule"],
    "second_attester": ["seat", "tier", "context", "change_flags", "disagreements"],
    "disagreement": ["field", "primary_value", "second_value"],
    "item": ["label", "outcome", "no_touch", "overridden", "checked_ids", "verdicts"],
    "verdict": ["corpus_id", "judge", "clause", "word", "reason", "flagged", "row_note", "claim", "excused", "trace_excerpt"],
    "claim": ["queue_item", "ruling_date", "confirming_judge"],
    "trace_excerpt": ["word", "queue_item"],
    "candidate": ["corpus_id", "queue_item", "status_as_read", "heading", "first_line", "last_line"],
    "match": ["item", "corpus_id", "queue_item", "ruling_date", "status_as_read", "confirming_judge"],
    "unverified": ["item", "corpus_id", "queue_item", "reason"],
    "blocked_item": ["item", "unexcused_fail_count"],
    "counts": ["checks_run", "passed", "failed", "failed_excused", "failed_unexcused", "unjudgeable", "missing"],
    "missing_entry": ["item", "corpus_id"],
    "self_test": ["probes", "counted_separately"],
    "probe": ["name", "result"],
}

PRECEDENCE = {
    "worksheet": ["input errors", "barred", "self test failure", "declaration conflict", "worksheet issued"],
    "finalise": ["input errors", "self test failure then declaration conflict", "binding mismatch", "barred", "incomplete", "re-ruling verification", "arithmetic outcomes"],
    "remaining": ["input errors", "binding mismatch", "declaration conflict", "remaining rows report"],
}

IE_WORDINGS = {
    "IE-01": "an output path names an input file: {output} is {input}",
    "IE-02": "two output paths name one file: {first} and {second}",
    "IE-03": "the output path already exists and the tool never overwrites: {path}",
    "IE-04": "the {kind} file is missing: {path}",
    "IE-05": "the {kind} file cannot be read: {path}",
    "IE-06": "the {kind} file is {measured} bytes, over the limit of 2000000 bytes: {path}",
    "IE-07": "the corpus file is empty: {path}",
    "IE-08": "the {kind} file is not valid UTF-8 text: {path}",
    "IE-09": "a corpus row does not split into six cells at line {n}",
    "IE-10": "a duplicate corpus ID stands in the corpus: {id}",
    "IE-11": "a corpus ID is missing from the counted sequence: {id}",
    "IE-12": "the corpus counts disagree: front matter states {a}, closing check states {b}, rows found {c}",
    "IE-13": "the corpus file is not valid UTF-8 text: {path}",
    "IE-14": "the amendment file is empty, which is a refusal and never a no touch run",
    "IE-15": "wording text stands with no item label at line {n}",
    "IE-16": "a duplicated amendment item label stands in the file: {label}",
    "IE-17": "a wording item has no wording text: {label}",
    "IE-18": "the declaration was made against a different amendment: declaration fingerprint {a}, amendment as read {b}",
    "IE-19": "the confirmation does not cover the declaration as read for item {label}: a stale confirmation",
    "IE-20": "the declaration file is missing, which is a refusal in any mode: {path}",
    "IE-21": "the declaration file is a bare empty file, which is not a no touch assertion",
    "IE-22": "the declaration for item {label} holds an empty token list, which is not a no touch assertion",
    "IE-23": "an unparseable declaration token stands for item {label}: {token}",
    "IE-24": "the declaration names an item the amendment does not hold: {label}",
    "IE-25": "the declaration holds no block for amendment item: {label}",
    "IE-26": "the declaration block for item {label} mixes token lines with a no touch assertion, or holds neither",
    "IE-27": "the declaration holds no confirmation block, or the confirmation names no confirming seat",
    "IE-28": "the declarer is the wording author, so the confirmation must come from a different seat: confirmer {seat}",
    "IE-29": "the declaration header names no declarer",
    "IE-30": "a token line for item {label} carries no subject basis",
    "IE-31": "the verdicts file is missing at the remaining form, so no remaining count can be made: {path}",
    "IE-32": "a verdict word outside the vocabulary stands for item {label}, row {id}: {word}",
    "IE-33": "a duplicated verdict stands for item {label}, row {id}",
    "IE-34": "a verdict stands for a row that is not checked for item {label}: {id}",
    "IE-35": "a verdict carries an empty reason for item {label}, row {id}",
    "IE-36": "a verdict for a flagged row stands in a word other than UNJUDGEABLE for item {label}, row {id}: {word}",
    "IE-37": "a verdict names a judge who is neither the judge of record nor a roster member for item {label}, row {id}: {judge}",
    "IE-38": "the verdicts binding does not match the recomputed run: {value} differs",
    "IE-39": "a claim block stands on a verdict that is not a FAIL for item {label}, row {id}",
    "IE-40": "a claim block confirming judge differs from the verdict judge for item {label}, row {id}",
    "IE-41": "a claim block carries no confirming judge for item {label}, row {id}",
    "IE-42": "a second claim block stands on one verdict for item {label}, row {id}",
    "IE-43": "a claim block carries no queue item for item {label}, row {id}",
    "IE-44": "a claim block carries no ruling date for item {label}, row {id}",
    "IE-45": "a verdict block stands with an empty judge, clause, or word slot for item {label}, row {id}: {slot}",
    "IE-46": "the verdicts file holds no binding header line: {line}",
    "IE-47": "a required identity argument is absent: {flag}",
    "IE-48": "a required attestation argument is absent: {flag}",
    "IE-49": "a second attester is required and its seat is absent or names the author or the runner",
    "IE-50": "a second attester is required and a value of its set is absent: {flag}",
    "IE-51": "the reader designate argument is absent at the finalise form",
    "IE-52": "a required argument is absent: {flag}",
    "IE-53": "a verdict clause does not match the closing fail clause for item {label}, row {id}",
    "IE-54": "the declaration block for item {label} stands out of amendment order",
    "IE-55": "the declaration block for item {label} carries the same token line twice: {token}",
    "IE-56": "a declaration header line stands twice: {line}",
    "IE-57": "the no touch line for item {label} carries no basis prose",
}

CLAUSE_A = "fail if the amendment permits the named failure shape."
CLAUSE_B = "fail if the row is judged by a seat with a conflict."
CLAUSE_C = "fail if the counts do not reconcile at the end."
CLAUSE_D = "fail if a fourth family condition stands in the row."

def procedure(clause):
    return "Inspect the amendment for the named shape; " + clause

def row(cid, incident, index, clause, source="synthetic source", test_core=None, proc=None, extra_incident=""):
    core = test_core if test_core is not None else incident
    return {
        "id": cid,
        "source": source,
        "incident": incident + extra_incident,
        "test": "An implementation that permits " + core + " fails",
        "index": index,
        "proc": proc if proc is not None else procedure(clause),
        "clause": clause,
    }

DEFAULT_ROWS = [
    row("C-001", "Alpha incident happened", "Gap 1", CLAUSE_A),
    row("C-002", "Beta incident happened", "FM-1", CLAUSE_B),
    row("C-003", "Gamma incident happened", "Gap 1, FM-2", CLAUSE_C),
    row("C-004", "Delta incident happened", "Gap 2", CLAUSE_A),
    row("C-005", "Epsilon incident happened", "Gap 3", CLAUSE_B,
        extra_incident=" Cross-ref: C-006 (same event, other lens)."),
    row("C-006", "Epsilon incident happened", "Gap 4", CLAUSE_B),
]
ROW_BY_ID = {r["id"]: r for r in DEFAULT_ROWS}

def corpus_text(rows, front=None, closing=None, annex_bullets=True, headings=True):
    n = len(rows)
    if front is None:
        front = n
    lines = []
    if front != "absent":
        lines.append("This corpus contains %s incident entries. That is the governing count." % front)
    lines.append("")
    lines.append("| Corpus ID | Source | Incident in one line | Test statement | Gap/FM index | Pass procedure |")
    lines.append("|---|---|---|---|---|---|")
    half = (n + 1) // 2
    for i, r in enumerate(rows):
        if headings and i == 0:
            lines.append("## Annex 1")
        if headings and i == half and n > 1:
            lines.append("## Annex 2")
        lines.append("| %s | %s | %s | %s | %s | %s |" % (r["id"], r["source"], r["incident"], r["test"], r["index"], r["proc"]))
    lines.append("")
    if closing != "absent":
        total = closing if isinstance(closing, int) else n
        if annex_bullets:
            lines.append("- Annex 1, synthetic: %d rows, %s to %s." % (half, rows[0]["id"], rows[half - 1]["id"]))
            if n > 1:
                lines.append("- Annex 2, synthetic: %d rows, %s to %s." % (n - half, rows[half]["id"], rows[-1]["id"]))
        lines.append("- Total: %d + %d = %d rows." % (half, n - half, total))
    return "\n".join(lines) + "\n"

DEFAULT_AMENDMENT_ITEMS = [
    ("A1", "The amendment changes the staffing rule text."),
    ("A2", "The amendment changes the counting text."),
]

def amendment_text(items):
    out = []
    for label, wording in items:
        out.append("item: " + label)
        out.append(wording)
    return "\n".join(out) + "\n"

def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()

def declaration_text(amendment_bytes, spec, declarer=DECLARER, confirmer=CONFIRMER,
                     fingerprint=None, confirmation_spec=None, header_extra=None):
    """spec: list of (label, tokens list or None for no touch, basis dict or basis string)."""
    fp = fingerprint if fingerprint is not None else sha256_hex(amendment_bytes)
    lines = ["declarer: " + declarer, "amendment-fingerprint: " + fp]
    if header_extra:
        lines.extend(header_extra)
    for label, tokens, basis in spec:
        lines.append("item: " + label)
        if tokens is None:
            lines.append("no-touch: " + basis)
        else:
            for tok in tokens:
                b = basis[tok] if isinstance(basis, dict) else basis
                lines.append("token: %s | basis: %s" % (tok, b))
    conf = confirmation_spec if confirmation_spec is not None else spec
    lines.append("confirmation:")
    lines.append("confirmer: " + confirmer)
    for label, tokens, basis in conf:
        lines.append("item: " + label)
        if tokens is None:
            lines.append("tokens: no-touch")
        else:
            lines.append("tokens: " + ", ".join(tokens))
    lines.append("end-confirmation:")
    return "\n".join(lines) + "\n"

def default_spec():
    return [
        ("A1", ["Gap 1"], {"Gap 1": "Basis prose for Gap 1 on A1."}),
        ("A2", ["FM-1"], {"FM-1": "Basis prose for FM-1 on A2."}),
    ]

def queue_text(entries):
    """entries: list of (heading, status line or None, body lines)."""
    out = ["# Decision Queue", ""]
    for heading, status, body in entries:
        out.append(heading)
        out.append("")
        if status is not None:
            out.append("Status: " + status)
            out.append("")
        out.extend(body)
        out.append("")
    return "\n".join(out) + "\n"

RULED_QUEUE = queue_text([
    ("### DQ-101: a ruled entry naming one row", "RULED, closed",
     ["This entry rules the incident at C-001 on the named day.", "Ruling date: 2026-11-01"]),
    ("### DQ-102: a settled entry naming one row", "SETTLED, closed",
     ["This entry settles the incident at C-002 as a Manager settlement."]),
    ("## DQ-103: an open entry naming one row", "Banked",
     ["This entry is open and names C-003."]),
])

DEFAULT_CHECKED = [("A1", "C-001"), ("A1", "C-003"), ("A2", "C-002")]
CHECKED_IDS = ["C-001", "C-002", "C-003"]

def verdicts_text(corpus_bytes, amendment_bytes, declaration_bytes, specs,
                  declared_mode="subset", effective_mode="subset", triggers=None,
                  judge_of_record=JUDGE, panel=(), checked_ids=None, header_overrides=None):
    """specs: list of dicts with keys label, id, judge, clause, word, reason, claim."""
    checked_ids = CHECKED_IDS if checked_ids is None else checked_ids
    trig = "none" if not triggers else ", ".join(triggers)
    lines = [
        "amendment-fingerprint: " + sha256_hex(amendment_bytes),
        "corpus-fingerprint: " + sha256_hex(corpus_bytes),
        "declaration-fingerprint: " + sha256_hex(declaration_bytes),
        "declared-mode: " + declared_mode,
        "effective-mode: " + effective_mode,
        "triggers: " + trig,
    ]
    for cid in checked_ids:
        lines.append("checked: " + cid)
    lines.append("judge-of-record: " + judge_of_record)
    for p in panel:
        lines.append("panel-judge: " + p)
    if header_overrides:
        lines = header_overrides(lines)
    for s in specs:
        lines.append("verdict: %s %s" % (s["label"], s["id"]))
        lines.append("judge: " + s.get("judge", JUDGE))
        lines.append("clause: " + s.get("clause", ROW_BY_ID[s["id"]]["clause"]))
        lines.append("word: " + s.get("word", "PASS"))
        lines.append("reason: " + s.get("reason", "The row was judged on its own procedure."))
        claim = s.get("claim")
        if claim is not None:
            lines.append("claim:")
            lines.append("queue-item: " + claim.get("queue_item", "DQ-101"))
            lines.append("ruling-date: " + claim.get("ruling_date", "2026-11-01"))
            lines.append("confirming-judge: " + claim.get("confirming_judge", s.get("judge", JUDGE)))
    return "\n".join(lines) + "\n"

def scan_tokens(index_cell):
    import re
    found = []
    for m in re.finditer(r"(?<![A-Za-z0-9])(Gap) (\d+)(?![A-Za-z])|(?<![A-Za-z0-9])(FM)-(\d+)(?![A-Za-z])", index_cell):
        if m.group(1):
            tok = "Gap %d" % int(m.group(2))
        else:
            tok = "FM-%d" % int(m.group(4))
        if tok not in found:
            found.append(tok)
    return found

def scan_checked_ids(corpus_bytes, declared_tokens):
    """Test side scan used only to build binding headers for large fixtures."""
    ids = []
    for line in corpus_bytes.decode().splitlines():
        if not line.startswith("| C-"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) != 6:
            continue
        toks = scan_tokens(cells[4])
        if any(t in toks for t in declared_tokens):
            ids.append(cells[0])
    return ids

def pass_specs(pairs=None):
    pairs = DEFAULT_CHECKED if pairs is None else pairs
    return [{"label": label, "id": cid} for label, cid in pairs]

class World:
    """One temporary run directory holding a small synthetic input set."""

    def __init__(self, tc):
        self.tc = tc
        self.dir = Path(tempfile.mkdtemp(prefix="rcg-", dir=os.environ.get("TMPDIR") or None))
        tc.addCleanup(self._cleanup)
        self.corpus = self.dir / "corpus.md"
        self.amendment = self.dir / "amendment.md"
        self.declaration = self.dir / "declaration.txt"
        self.queue = self.dir / "queue.md"
        self.verdicts = self.dir / "verdicts.txt"
        self.out1 = self.dir / "out1.txt"
        self.out2 = self.dir / "out2.txt"
        self.corpus_bytes = corpus_text(DEFAULT_ROWS).encode()
        self.amendment_bytes = amendment_text(DEFAULT_AMENDMENT_ITEMS).encode()
        self.declaration_bytes = declaration_text(self.amendment_bytes, default_spec()).encode()
        self.queue_bytes = RULED_QUEUE.encode()
        self.write_all()

    def _cleanup(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_all(self):
        self.corpus.write_bytes(self.corpus_bytes)
        self.amendment.write_bytes(self.amendment_bytes)
        self.declaration.write_bytes(self.declaration_bytes)
        self.queue.write_bytes(self.queue_bytes)

    def set_declaration(self, spec=None, **kw):
        spec = default_spec() if spec is None else spec
        self.declaration_bytes = declaration_text(self.amendment_bytes, spec, **kw).encode()
        self.declaration.write_bytes(self.declaration_bytes)

    def set_amendment(self, items):
        self.amendment_bytes = amendment_text(items).encode()
        self.amendment.write_bytes(self.amendment_bytes)

    def set_corpus(self, rows, **kw):
        self.corpus_bytes = corpus_text(rows, **kw).encode()
        self.corpus.write_bytes(self.corpus_bytes)

    def args(self, form, drop=(), extra=(), **over):
        a = ["--form", form,
             "--runner", over.get("runner", RUNNER),
             "--judge", over.get("judge", JUDGE),
             "--author", over.get("author", AUTHOR),
             "--ruler", over.get("ruler", RULER),
             "--coordinator", over.get("coordinator", COORDINATOR),
             "--corpus", str(self.corpus),
             "--amendment", str(self.amendment),
             "--declaration", str(self.declaration),
             "--declared-mode", over.get("declared_mode", "subset"),
             "--tier", over.get("tier", "Low")]
        if "context" in over:
            a += ["--context", over["context"]]
        flags = over.get("change_flags", {})
        for flag, key, _trig in CHANGE_FLAGS:
            a += [flag, flags.get(key, "no")]
        if form == "worksheet":
            a += ["--worksheet-out", str(self.out1), "--template-out", str(self.out2)]
        elif form == "remaining":
            a += ["--verdicts", str(self.verdicts), "--remaining-out", str(self.out1)]
        elif form == "finalise":
            a += ["--reader-designate", over.get("reader", READER),
                  "--verdicts", str(self.verdicts),
                  "--report-out", str(self.out1), "--results-out", str(self.out2)]
        if over.get("panel"):
            for p in over["panel"]:
                a += ["--panel-judge", p]
        if over.get("queue"):
            a += ["--queue", str(self.queue)]
        if over.get("second"):
            s = over["second"]
            a += ["--second-attester", s.get("seat", SECOND),
                  "--second-tier", s.get("tier", over.get("tier", "Low")),
                  "--second-context", s.get("context", over.get("context", "stated"))]
            sflags = s.get("change_flags", {})
            for flag, key, _trig in CHANGE_FLAGS:
                a += ["--second-" + flag[2:], sflags.get(key, flags.get(key, "no"))]
        a += list(extra)
        out = []
        skip = set(drop)
        i = 0
        while i < len(a):
            if a[i] in skip:
                i += 2
                continue
            out.append(a[i])
            i += 1
        return out

    def run(self, form, **kw):
        return run_program(self.args(form, **kw))

    def write_verdicts(self, specs, **kw):
        text = verdicts_text(self.corpus_bytes, self.amendment_bytes, self.declaration_bytes, specs, **kw)
        self.verdicts.write_text(text)
        return text

    def read_out1(self):
        self.tc.assertTrue(self.out1.exists(),
                           "the run wrote no first output at %s" % self.out1)
        return self.out1.read_text()

    def read_results(self):
        self.tc.assertTrue(self.out2.exists(),
                           "the run wrote no results file at %s" % self.out2)
        return json.loads(self.out2.read_text())

def run_program(args, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(PROGRAM)] + [str(x) for x in args],
        capture_output=True, text=True, env=env, timeout=120,
    )

def assert_ie(tc, proc, ie_id, wording, status=2):
    tc.assertEqual(proc.returncode, status, proc.stderr + proc.stdout)
    lines = proc.stderr.splitlines()
    tc.assertGreaterEqual(len(lines), 2, proc.stderr)
    tc.assertEqual(lines[0], "input error: " + SENTENCES["input error"])
    tc.assertEqual(lines[1], "input error %s: %s" % (ie_id, wording))

def assert_usage(tc, proc):
    tc.assertEqual(proc.returncode, 2, proc.stderr + proc.stdout)
    tc.assertIn("usage error: ", proc.stderr)
    tc.assertIn(USAGE_SUMMARY, proc.stderr)

def assert_no_files(tc, *paths):
    for p in paths:
        tc.assertFalse(Path(p).exists(), "unexpected file at %s" % p)

def assert_outcome_line(tc, text, term):
    tc.assertIn("%s: %s" % (term, SENTENCES[term]), text.splitlines())

def derive_example_args(examples, form, out1, out2):
    """Build run arguments for the shipped example set from its own files.

    The verdicts header of the example set carries the modes and triggers the
    example run used, and its judge roster. The remaining identities are the
    canonical example run seats recorded in plan part 7 at stage 14.
    """
    verdicts = (examples / "example_verdicts.txt").read_text()
    header = {}
    panel = []
    judges = set()
    for line in verdicts.splitlines():
        if line.startswith("judge-of-record: "):
            header["judge"] = line.split(": ", 1)[1]
            judges.add(header["judge"])
        elif line.startswith("panel-judge: "):
            panel.append(line.split(": ", 1)[1])
            judges.add(panel[-1])
        elif line.startswith("declared-mode: "):
            header["declared"] = line.split(": ", 1)[1]
        elif line.startswith("effective-mode: "):
            header["effective"] = line.split(": ", 1)[1]
        elif line.startswith("triggers: "):
            header["triggers"] = line.split(": ", 1)[1]
        elif line.startswith("judge: "):
            judges.add(line.split(": ", 1)[1])
    triggers = [] if header.get("triggers", "none") == "none" else header["triggers"].split(", ")
    tier = "Low"
    context = "stated"
    for t in triggers:
        if t.startswith("context-"):
            context = t[len("context-"):]
    flags = {}
    for _flag, key, trig in CHANGE_FLAGS:
        flags[key] = "yes" if trig in triggers else "no"
    seats = {
        "runner": "Example Runner Seat",
        "author": "Example Author Seat",
        "ruler": "Example Ruler Seat",
        "coordinator": "Example Coordinator Seat",
        "reader": "Example Reader Seat",
    }
    args = ["--form", form, "--runner", seats["runner"], "--judge", header["judge"],
            "--author", seats["author"], "--ruler", seats["ruler"],
            "--coordinator", seats["coordinator"],
            "--corpus", str(examples / "example_corpus.md"),
            "--amendment", str(examples / "example_amendment.md"),
            "--declaration", str(examples / "example_declaration.txt"),
            "--declared-mode", header.get("declared", "subset"),
            "--tier", tier, "--context", context]
    for flag, key, _trig in CHANGE_FLAGS:
        args += [flag, flags[key]]
    for p in panel:
        args += ["--panel-judge", p]
    if form == "worksheet":
        args += ["--worksheet-out", str(out1), "--template-out", str(out2),
                 "--queue", str(examples / "example_queue.md")]
    elif form == "finalise":
        args += ["--reader-designate", seats["reader"],
                 "--verdicts", str(examples / "example_verdicts.txt"),
                 "--queue", str(examples / "example_queue.md"),
                 "--report-out", str(out1), "--results-out", str(out2)]
    return args


class RcgTestCase(unittest.TestCase):
    def world(self):
        return World(self)
