#!/usr/bin/env python3
"""Regression corpus gate: judge proposed amendments against the regression corpus."""

import hashlib
import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants and tables
# ---------------------------------------------------------------------------

TOOL_NAME = "regression-corpus-gate"
VERSION = "1.0.0"
BYTE_LIMIT = 2000000
DEFAULT_CORPUS = str(Path.home() / "workspace" / "build-flow-expansion" / "REGRESSION-CORPUS.md")
DEFAULT_QUEUE = str(Path.home() / "workspace" / "build-flow-expansion" / "DECISION-QUEUE.md")
USAGE_SUMMARY = "usage: regression_corpus_gate.py --form worksheet|remaining|finalise [arguments]"
NO_CLAUSE_STATEMENT = "no closing fail clause stands"

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

STATUS_FOR_OUTCOME = {
    "pass": 0,
    "fail": 1,
    "incomplete": 3,
    "unverifiable": 4,
    "re-ruled pass": 5,
    "barred": 6,
    "declaration conflict": 7,
    "self test failure": 8,
    "remaining rows report": 9,
    "worksheet issued": 10,
}

TRACE_WORD = {
    "pass": "PASS",
    "fail": "FAIL rejected",
    "re-ruled pass": "RE-RULED",
    "incomplete": None,
    "unverifiable": None,
    "barred": None,
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

CHANGE_KEYS = [
    "index_system",
    "gate_rule",
    "corpus",
    "definition",
    "counting_method",
    "verdict_form",
    "closure_rule",
]
CHANGE_FLAG_FOR_KEY = {
    "index_system": "--change-index-system",
    "gate_rule": "--change-gate-rule",
    "corpus": "--change-corpus",
    "definition": "--change-definition",
    "counting_method": "--change-counting-method",
    "verdict_form": "--change-verdict-form",
    "closure_rule": "--change-closure-rule",
}
CHANGE_TRIGGER_FOR_KEY = {
    "index_system": "change-index-system",
    "gate_rule": "change-gate-rule",
    "corpus": "change-corpus",
    "definition": "change-definition",
    "counting_method": "change-counting-method",
    "verdict_form": "change-verdict-form",
    "closure_rule": "change-closure-rule",
}
CHANGE_LABEL_FOR_KEY = {
    "index_system": "change index system",
    "gate_rule": "change gate rule",
    "corpus": "change corpus",
    "definition": "change definition",
    "counting_method": "change counting method",
    "verdict_form": "change verdict form",
    "closure_rule": "change closure rule",
}

TIERS = ["Low", "Medium", "High", "Extra High", "Plaid"]
CONTEXTS = ["stated", "unstated", "mixed", "disputed"]
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
SELF_TEST_COUNTED_LINE = "self test results are counted separately from corpus checks"
READBACK_FOOTER = (
    "this page shows what the declaration and the tripwire produced; a declaration wrong in a way "
    "no tripwire catches is not guarded by this page; it is guarded by the runner confirmation and "
    "the Auditor addition right"
)
NEXT_STEP_LINE = (
    "next step: The caller files this record into the trace the standing procedure names. "
    "This record informs a closure decision and makes none."
)
TEMPLATE_CLOSING_LINE = (
    "template: fill one block per checked pair. An untouched slot is empty on purpose. "
    "A FAIL verdict that claims an excuse carries exactly one claim block under its reason line."
)
WORKSHEET_FIXED_LINE = "worksheet: no verdicts exist yet in this form"
REMAINING_FIXED_LINES = [
    "remaining rows report: this report names the checked pairs that still lack a verdict. It issues no verdict and finalises nothing.",
    "an incomplete run is blocked, and a count of work left is not progress toward a pass",
]
SIZING_LINE = (
    "sizing as measured: Gap 1 selects 159 rows, the Gap 1 to 4 union selects 218 rows, "
    "FM tokens together reach 34 rows, and a full run checks 224 rows per wording item; "
    "record size grows in proportion to rows checked times wording items; no output byte limit applies"
)
LIMIT_JUDGE_REASONING = "a judge whose reasoning is wrong while the forms are complete is not detectable by this program; the layered answer is the fresh Auditor oversight of part 4.6 and the reader designate duty of part 5.4"
LIMIT_DECLARATION = "a declaration wrong from the start in a way no tripwire catches is not guarded by the readback page; the layered answer is the runner confirmation and the Auditor addition right"
LIMIT_BINDING = "the verdicts binding carries no run identifier in version 1; a verdicts input from an earlier run over unchanged inputs verifies against a later run over the same inputs"
LIMIT_CORPUS_CHANGE = "a corpus content change that keeps the structure valid is visible only as a different fingerprint"
LIMIT_EXTRACTION = "index tokens written in forms outside the tripwire extraction grammar are not extracted; ranges and compressed lists are outside the grammar"
LIMIT_FATIGUE = "judge fatigue across a long run is not detectable by this program; judging may proceed in sittings, and sittings change pacing and never the bar"
LIMIT_ATTESTATION = "trigger facts are attestations by the runner; a wrong attestation is not detectable by this program; the layered answer is the Auditor oversight, the dispute attestation, and the record printing the attested facts beside the attester name"
QUEUE_STANDING_LINE = "no entry in the queue as read carries the status standing"
EXCEPTION_LINE = "a confirmed re-ruling excuses only the named corpus ID and incident through the decision queue"

PLAYBOOK_LINES = [
    "If the declaration conflicts: amend the declaration to cover every token the wording names, have it freshly confirmed, and rerun the worksheet form. No judging can start until the conflict clears.",
    "If the self test fails: stop. Do not judge any row. File the self test report reference with the state name and report the tool fault.",
    "If the run is barred: stop. A different judge of record must be named by the caller. Do not rename a judge inside the verdicts to get around the bar.",
    "If a verdicts file fails binding at finalise: an input changed or a trigger fired after the worksheet. Issue a fresh worksheet and template from the current inputs and judge again from them.",
    "If the run is incomplete: use the remaining form to name the pairs still missing verdicts. A partly filled run never finalises as anything but incomplete.",
    "If the queue cannot be verified at finalise: every claimed excuse stands unverified and its fail stands unexcused. Fix the queue path or the queue file and finalise again with a fresh verdicts binding where any input changed.",
    "If an output path already exists: name fresh output paths. The tool never overwrites a finished record.",
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

AUDITOR_OVERSIGHT_LINE = (
    "a fresh Auditor oversees this run after reading the corpus and the wording set first hand, "
    "under the procedure of part 4.6. The overseeing seat and the fact of that reading are attested "
    "outside this record in the filed trace; this record states the duty and does not record that "
    "the oversight or the reading has happened."
)


IE_WORDINGS = {
    'IE-01': 'an output path names an input file: %s is %s',
    'IE-02': 'two output paths name one file: %s and %s',
    'IE-03': 'the output path already exists and the tool never overwrites: %s',
    'IE-04': 'the %s file is missing: %s',
    'IE-05': 'the %s file cannot be read: %s',
    'IE-06': 'the %s file is %d bytes, over the limit of 2000000 bytes: %s',
    'IE-07': 'the corpus file is empty: %s',
    'IE-08': 'the %s file is not valid UTF-8 text: %s',
    'IE-09': 'a corpus row does not split into six cells at line %d',
    'IE-10': 'a duplicate corpus ID stands in the corpus: %s',
    'IE-11': 'a corpus ID is missing from the counted sequence: C-%03d',
    'IE-12': 'the corpus counts disagree: front matter states %s, closing check states %s, rows found %d',
    'IE-13': 'the corpus file is not valid UTF-8 text: %s',
    'IE-14': 'the amendment file is empty, which is a refusal and never a no touch run',
    'IE-15': 'wording text stands with no item label at line %d',
    'IE-16': 'a duplicated amendment item label stands in the file: %s',
    'IE-17': 'a wording item has no wording text: %s',
    'IE-18': 'the declaration was made against a different amendment: declaration fingerprint %s, amendment as read %s',
    'IE-19': 'the confirmation does not cover the declaration as read for item %s: a stale confirmation',
    'IE-20': 'the declaration file is missing, which is a refusal in any mode: %s',
    'IE-21': 'the declaration file is a bare empty file, which is not a no touch assertion',
    'IE-22': 'the declaration for item %s holds an empty token list, which is not a no touch assertion',
    'IE-23': 'an unparseable declaration token stands for item %s: %s',
    'IE-24': 'the declaration names an item the amendment does not hold: %s',
    'IE-25': 'the declaration holds no block for amendment item: %s',
    'IE-26': 'the declaration block for item %s mixes token lines with a no touch assertion, or holds neither',
    'IE-27': 'the declaration holds no confirmation block, or the confirmation names no confirming seat',
    'IE-28': 'the declarer is the wording author, so the confirmation must come from a different seat: confirmer %s',
    'IE-29': 'the declaration header names no declarer',
    'IE-30': 'a token line for item %s carries no subject basis',
    'IE-31': 'the verdicts file is missing at the remaining form, so no remaining count can be made: %s',
    'IE-32': 'a verdict word outside the vocabulary stands for item %s, row %s: %s',
    'IE-33': 'a duplicated verdict stands for item %s, row %s',
    'IE-34': 'a verdict stands for a row that is not checked for item %s: %s',
    'IE-35': 'a verdict carries an empty reason for item %s, row %s',
    'IE-36': 'a verdict for a flagged row stands in a word other than UNJUDGEABLE for item %s, row %s: %s',
    'IE-37': 'a verdict names a judge who is neither the judge of record nor a roster member for item %s, row %s: %s',
    'IE-38': 'the verdicts binding does not match the recomputed run: %s differs',
    'IE-39': 'a claim block stands on a verdict that is not a FAIL for item %s, row %s',
    'IE-40': 'a claim block confirming judge differs from the verdict judge for item %s, row %s',
    'IE-41': 'a claim block carries no confirming judge for item %s, row %s',
    'IE-42': 'a second claim block stands on one verdict for item %s, row %s',
    'IE-43': 'a claim block carries no queue item for item %s, row %s',
    'IE-44': 'a claim block carries no ruling date for item %s, row %s',
    'IE-45': 'a verdict block stands with an empty judge, clause, or word slot for item %s, row %s: %s',
    'IE-46': 'the verdicts file holds no binding header line: %s',
    'IE-47': 'a required identity argument is absent: %s',
    'IE-48': 'a required attestation argument is absent: %s',
    'IE-49': 'a second attester is required and its seat is absent or names the author or the runner',
    'IE-50': 'a second attester is required and a value of its set is absent: %s',
    'IE-51': 'the reader designate argument is absent at the finalise form',
    'IE-52': 'a required argument is absent: %s',
    'IE-53': 'a verdict clause does not match the closing fail clause for item %s, row %s',
    'IE-54': 'the declaration block for item %s stands out of amendment order',
    'IE-55': 'the declaration block for item %s carries the same token line twice: %s',
    'IE-56': 'a declaration header line stands twice: %s',
    'IE-57': 'the no touch line for item %s carries no basis prose',
}


def reader_designate_line(seat):
    return (
        seat + ". An amendment takes effect only after the Auditor, or a named reader who is "
        "neither author nor ruler, has read this record. This record names the reader designate; "
        "it does not record that the reading has happened."
    )


class InputFailure(Exception):
    def __init__(self, ie_id, wording):
        super().__init__(wording)
        self.ie_id = ie_id
        self.wording = wording


class UsageFailure(Exception):
    pass


class DeliveryFailure(Exception):
    def __init__(self, path):
        super().__init__(path)
        self.path = path


def ie(ie_id, wording):
    raise InputFailure(ie_id, wording)


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def resolve_path(text):
    return str(Path(text).resolve())


def split_lines(text):
    lines = text.split("\n")
    out = []
    for line in lines:
        if line.endswith("\r"):
            line = line[:-1]
        out.append(line)
    return out


def canonical_token_key(token):
    if token.startswith("Gap "):
        return (0, int(token[4:]))
    return (1, int(token[3:]))


def sort_tokens(tokens):
    return sorted(tokens, key=canonical_token_key)


def format_token_list(tokens):
    if not tokens:
        return "none"
    return ", ".join(tokens)


CORPUS_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])Gap (\d+)(?![A-Za-z])|(?<![A-Za-z0-9])FM-(\d+)(?![A-Za-z])")
CORPUS_ID_RE = re.compile(r"^C-\d+$")
CROSS_REF_RE = re.compile(r"(?<![A-Za-z0-9])C-(\d+)(?![A-Za-z])")


def scan_corpus_tokens(index_cell):
    found = []
    for m in CORPUS_TOKEN_RE.finditer(index_cell):
        if m.group(1) is not None:
            tok = "Gap %d" % int(m.group(1))
        else:
            tok = "FM-%d" % int(m.group(2))
        if tok not in found:
            found.append(tok)
    return found
# ---------------------------------------------------------------------------
# Argument parsing and path validation
# ---------------------------------------------------------------------------

SINGLETON_FLAGS = {
    "--form", "--runner", "--judge", "--author", "--ruler", "--coordinator",
    "--reader-designate", "--corpus", "--amendment", "--declaration",
    "--verdicts", "--queue", "--declared-mode", "--tier", "--context",
    "--second-attester", "--second-tier", "--second-context",
    "--worksheet-out", "--template-out", "--remaining-out",
    "--report-out", "--results-out",
}
for _key in CHANGE_KEYS:
    SINGLETON_FLAGS.add(CHANGE_FLAG_FOR_KEY[_key])
    SINGLETON_FLAGS.add("--second-" + CHANGE_FLAG_FOR_KEY[_key][2:])
REPEATABLE_FLAGS = {"--panel-judge"}
ALL_FLAGS = SINGLETON_FLAGS | REPEATABLE_FLAGS

ENUM_VALUES = {
    "--form": {"worksheet", "remaining", "finalise"},
    "--declared-mode": {"subset", "full"},
    "--tier": set(TIERS),
    "--context": set(CONTEXTS),
    "--second-tier": set(TIERS),
    "--second-context": set(CONTEXTS),
}
for _key in CHANGE_KEYS:
    ENUM_VALUES[CHANGE_FLAG_FOR_KEY[_key]] = {"yes", "no"}
    ENUM_VALUES["--second-" + CHANGE_FLAG_FOR_KEY[_key][2:]] = {"yes", "no"}

FORBIDDEN_BY_FORM = {
    "worksheet": {"--verdicts", "--reader-designate", "--remaining-out", "--report-out", "--results-out"},
    "remaining": {"--reader-designate", "--queue", "--worksheet-out", "--template-out", "--report-out", "--results-out"},
    "finalise": {"--worksheet-out", "--template-out", "--remaining-out"},
}

OUTPUT_FLAGS_BY_FORM = {
    "worksheet": ["--worksheet-out", "--template-out"],
    "remaining": ["--remaining-out"],
    "finalise": ["--report-out", "--results-out"],
}


def parse_arguments(argv):
    values = {}
    panel = []
    seen = set()
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in ALL_FLAGS:
            if token in SINGLETON_FLAGS and token in seen:
                raise UsageFailure("the flag %s was given twice" % token)
            if i + 1 >= len(argv):
                raise UsageFailure("the flag %s has no value" % token)
            value = argv[i + 1]
            seen.add(token)
            if token in REPEATABLE_FLAGS:
                panel.append(value)
            else:
                values[token] = value
            i += 2
        elif token.startswith("--"):
            raise UsageFailure("the flag %s is not known" % token)
        else:
            raise UsageFailure("the positional argument %s is not allowed" % token)
    if "--form" not in values:
        raise UsageFailure("the flag --form is absent")
    form = values["--form"]
    if form not in ENUM_VALUES["--form"]:
        raise UsageFailure("the form word %s is not one of worksheet, remaining, finalise" % form)
    for flag in sorted(seen):
        if flag in FORBIDDEN_BY_FORM[form]:
            raise UsageFailure("the flag %s is forbidden in the %s form" % (flag, form))
    if panel and "--panel-judge" in FORBIDDEN_BY_FORM.get(form, set()):
        raise UsageFailure("the flag --panel-judge is forbidden in the %s form" % form)
    for flag, allowed in ENUM_VALUES.items():
        if flag in values and values[flag] not in allowed:
            raise UsageFailure("the value %s for %s is not allowed" % (values[flag], flag))
    values["--panel-judge"] = panel
    return values


def check_required_arguments(values):
    form = values["--form"]
    for flag in ("--runner", "--judge", "--author", "--ruler", "--coordinator"):
        if flag not in values:
            ie("IE-47", IE_WORDINGS["IE-47"] % flag)
    if form == "finalise" and "--reader-designate" not in values:
        ie("IE-51", IE_WORDINGS["IE-51"])
    if "--tier" not in values:
        ie("IE-48", IE_WORDINGS["IE-48"] % '--tier')
    for key in CHANGE_KEYS:
        flag = CHANGE_FLAG_FOR_KEY[key]
        if flag not in values:
            ie("IE-48", IE_WORDINGS["IE-48"] % flag)
    if "--declared-mode" not in values:
        ie("IE-52", IE_WORDINGS["IE-52"] % '--declared-mode')
    for flag in ("--amendment", "--declaration"):
        if flag not in values:
            ie("IE-52", IE_WORDINGS["IE-52"] % flag)
    if form in ("remaining", "finalise") and "--verdicts" not in values:
        ie("IE-52", IE_WORDINGS["IE-52"] % '--verdicts')
    for flag in OUTPUT_FLAGS_BY_FORM[form]:
        if flag not in values:
            ie("IE-52", IE_WORDINGS["IE-52"] % flag)


class RunRequest:
    def __init__(self, values):
        self.values = values
        self.form = values["--form"]
        self.runner = values.get("--runner")
        self.judge = values.get("--judge")
        self.author = values.get("--author")
        self.ruler = values.get("--ruler")
        self.coordinator = values.get("--coordinator")
        self.panel = list(values.get("--panel-judge", []))
        self.reader = values.get("--reader-designate")
        self.corpus_supplied = "--corpus" in values
        self.corpus_path = resolve_path(values.get("--corpus", DEFAULT_CORPUS))
        self.amendment_path = resolve_path(values["--amendment"]) if "--amendment" in values else None
        self.declaration_path = resolve_path(values["--declaration"]) if "--declaration" in values else None
        self.verdicts_path = resolve_path(values["--verdicts"]) if "--verdicts" in values else None
        self.queue_supplied = "--queue" in values
        self.queue_path = resolve_path(values.get("--queue", DEFAULT_QUEUE))
        self.declared_mode = values.get("--declared-mode")
        self.output_paths = {}
        for flag in OUTPUT_FLAGS_BY_FORM[self.form]:
            if flag in values:
                self.output_paths[flag] = resolve_path(values[flag])

    def input_paths(self):
        paths = [self.corpus_path, self.amendment_path, self.declaration_path]
        if self.form in ("remaining", "finalise"):
            paths.append(self.verdicts_path)
        if self.queue_supplied and self.form in ("worksheet", "finalise"):
            paths.append(self.queue_path)
        return [p for p in paths if p]


def validate_paths(req):
    outputs = [req.output_paths[flag] for flag in OUTPUT_FLAGS_BY_FORM[req.form] if flag in req.output_paths]
    inputs = req.input_paths()
    for out in outputs:
        for inp in inputs:
            if out == inp:
                ie("IE-01", IE_WORDINGS["IE-01"] % (out, inp))
    for a in range(len(outputs)):
        for b in range(a + 1, len(outputs)):
            if outputs[a] == outputs[b]:
                ie("IE-02", IE_WORDINGS["IE-02"] % (outputs[a], outputs[b]))
    for out in outputs:
        if os.path.exists(out):
            ie("IE-03", IE_WORDINGS["IE-03"] % out)
# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------

def read_input_file(path, kind):
    """Returns bytes, or raises the reading input error for the kind."""
    if not os.path.exists(path):
        if kind == "declaration":
            ie("IE-20", IE_WORDINGS["IE-20"] % path)
        ie("IE-04", IE_WORDINGS["IE-04"] % (kind, path))
    if os.path.isdir(path):
        ie("IE-05", IE_WORDINGS["IE-05"] % (kind, path))
    try:
        measured = os.path.getsize(path)
    except OSError:
        ie("IE-05", IE_WORDINGS["IE-05"] % (kind, path))
    if measured > BYTE_LIMIT:
        ie("IE-06", IE_WORDINGS["IE-06"] % (kind, measured, path))
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        ie("IE-05", IE_WORDINGS["IE-05"] % (kind, path))


def decode_input(data, kind, path):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        if kind == "corpus":
            ie("IE-13", IE_WORDINGS["IE-13"] % path)
        ie("IE-08", IE_WORDINGS["IE-08"] % (kind, path))
# ---------------------------------------------------------------------------
# Corpus parser and integrity
# ---------------------------------------------------------------------------

FRONT_COUNT_RE = re.compile(r"^This corpus contains (\d+) incident entries\.")
CLOSING_COUNT_RE = re.compile(r"^- Total: (\d+(?: \+ \d+)*) = (\d+) rows\.$")
ANNEX_BULLET_RE = re.compile(r"^-\s+Annex\s+(\d+)\b.*?(C-\d+)\s+to\s+(C-\d+)")
HEADING_RE = re.compile(r"^#+\s+(.*)$")
ANNEX_IN_HEADING_RE = re.compile(r"Annex (\d+)")
SEPARATOR = "; fail if"


def extract_clause(proc):
    idx = proc.rfind(SEPARATOR)
    if idx < 0:
        return None, False
    clause = proc[idx + 2:].strip()
    core = clause.rstrip("".join([".", " ", "\t", '"', "'", ")", "]", "}"])).strip()
    if core == "fail if":
        return None, True
    return clause, False


def ends_with_ellipsis(cell):
    trimmed = cell.strip()
    while trimmed and trimmed[-1] in "\"')]}":
        trimmed = trimmed[:-1].rstrip()
    return trimmed.endswith("…") or trimmed.endswith("...")


def divergence_note(row):
    incident = row["incident"]
    cut = incident.find(" Cross-ref:")
    if cut >= 0:
        incident = incident[:cut]
    core = row["test"].strip()
    opening = "An implementation that permits "
    if core.startswith(opening):
        core = core[len(opening):]
    if core.endswith(" fails"):
        core = core[:-len(" fails")]
    if core == "":
        return "the incident line and the test statement diverge in wording"
    if core.lower() not in incident.lower():
        return "the incident line and the test statement diverge in wording"
    return None


def parse_corpus(data, path):
    text = decode_input(data, "corpus", path)
    if len(data) == 0:
        ie("IE-07", IE_WORDINGS["IE-07"] % path)
    lines = split_lines(text)
    raw_rows = []
    for idx, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if cells and CORPUS_ID_RE.match(cells[0]):
            raw_rows.append((idx, line, cells))
    rows = []
    for idx, line, cells in raw_rows:
        if len(cells) != 6:
            ie("IE-09", IE_WORDINGS["IE-09"] % (idx + 1))
        cid, source, incident, test, index, proc = cells
        rows.append({
            "id": cid,
            "num": int(cid[2:]),
            "source": source,
            "incident": incident,
            "test": test,
            "index": index,
            "proc": proc,
            "line_index": idx,
            "tokens": scan_corpus_tokens(index),
        })
    seen_ids = set()
    for row in rows:
        if row["id"] in seen_ids:
            ie("IE-10", IE_WORDINGS["IE-10"] % row["id"])
        seen_ids.add(row["id"])
    if rows:
        expected = rows[0]["num"]
        for row in rows:
            if row["num"] != expected:
                ie("IE-11", IE_WORDINGS["IE-11"] % expected)
            expected += 1
    first_row_idx = raw_rows[0][0] if raw_rows else len(lines)
    last_row_idx = raw_rows[-1][0] if raw_rows else -1
    front_count = None
    for idx, line in enumerate(lines):
        if idx >= first_row_idx:
            break
        m = FRONT_COUNT_RE.match(line.strip())
        if m:
            front_count = int(m.group(1))
            break
    closing_count = None
    for idx, line in enumerate(lines):
        if idx <= last_row_idx:
            continue
        m = CLOSING_COUNT_RE.match(line.strip())
        if m:
            closing_count = int(m.group(2))
            break
    front_slot = str(front_count) if front_count is not None else "absent"
    closing_slot = str(closing_count) if closing_count is not None else "absent"
    if front_count is None or closing_count is None or front_count != closing_count or front_count != len(rows):
        ie("IE-12", IE_WORDINGS["IE-12"] % (front_slot, closing_slot, len(rows)))
    annex_ranges = []
    for line in lines:
        m = ANNEX_BULLET_RE.match(line.strip())
        if m:
            annex_ranges.append((int(m.group(1)), int(m.group(2)[2:]), int(m.group(3)[2:])))
    current_group = "none stated"
    group_by_line = {}
    for idx, line in enumerate(lines):
        hm = HEADING_RE.match(line)
        if hm:
            am = ANNEX_IN_HEADING_RE.search(hm.group(1))
            if am:
                current_group = "Annex %d" % int(am.group(1))
        group_by_line[idx] = current_group
    for row in rows:
        clause, degenerate = extract_clause(row["proc"])
        row["clause"] = clause
        notes = []
        flagged = False
        if not row["incident"] or not row["test"] or not row["proc"]:
            flagged = True
            empty_names = []
            if not row["incident"]:
                empty_names.append("incident")
            if not row["test"]:
                empty_names.append("test statement")
            if not row["proc"]:
                empty_names.append("pass procedure")
            notes.append("the %s cell is empty" % " and ".join(empty_names))
        for cell, name in ((row["incident"], "incident"), (row["test"], "test statement"), (row["proc"], "pass procedure")):
            if cell and ends_with_ellipsis(cell):
                flagged = True
                notes.append("the %s cell ends with an ellipsis, marking truncation as written" % name)
        if SEPARATOR not in row["proc"]:
            if row["proc"]:
                flagged = True
                notes.append("no closing fail clause was found, because its test cannot be stated")
        elif degenerate:
            flagged = True
            notes.append("the closing fail clause states no condition, because its test cannot be stated")
        row["flagged"] = flagged
        row["flag_note"] = notes[0] if notes else None
        row["notes"] = notes
        row["divergence"] = divergence_note(row)
        group = None
        for annex_num, lo, hi in annex_ranges:
            if lo <= row["num"] <= hi:
                group = "Annex %d" % annex_num
                break
        if group is None:
            group = group_by_line[row["line_index"]]
        row["annex"] = group
        kinds = set()
        for tok in row["tokens"]:
            kinds.add("Gap" if tok.startswith("Gap ") else "FM")
        if kinds == {"Gap"}:
            row["arrangement"] = "Gap tokens only"
        elif kinds == {"FM"}:
            row["arrangement"] = "FM tokens only"
        elif kinds == {"Gap", "FM"}:
            row["arrangement"] = "both kinds"
        else:
            row["arrangement"] = "no tokens"
    all_tokens = []
    for row in rows:
        for tok in row["tokens"]:
            if tok not in all_tokens:
                all_tokens.append(tok)
    clause_families = []
    family_counts = {}
    for row in rows:
        if row["clause"] is not None:
            if row["clause"] not in family_counts:
                clause_families.append(row["clause"])
                family_counts[row["clause"]] = 0
            family_counts[row["clause"]] += 1
    return {
        "rows": rows,
        "row_count": len(rows),
        "all_tokens": all_tokens,
        "clause_families": clause_families,
        "family_counts": family_counts,
        "by_id": {r["id"]: r for r in rows},
    }


def dialect_line(corpus):
    groups = []
    for row in corpus["rows"]:
        if row["annex"] not in groups:
            groups.append(row["annex"])
    parts = []
    for group in groups:
        members = [r for r in corpus["rows"] if r["annex"] == group]
        counts = {}
        for r in members:
            counts[r["arrangement"]] = counts.get(r["arrangement"], 0) + 1
        segs = []
        for arrangement in ("Gap tokens only", "FM tokens only", "both kinds", "no tokens"):
            if arrangement in counts:
                segs.append("%s %d rows" % (arrangement, counts[arrangement]))
        parts.append("%s: %s" % (group, ", ".join(segs)))
    return "corpus dialects as read: " + "; ".join(parts)
# ---------------------------------------------------------------------------
# Amendment and declaration parsers
# ---------------------------------------------------------------------------

LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
DECLARED_TOKEN_RE = re.compile(r"^(Gap (0|[1-9]\d*)|FM-(0|[1-9]\d*))$")


def parse_amendment(data, path):
    text = decode_input(data, "amendment", path)
    if len(data) == 0:
        ie("IE-14", IE_WORDINGS["IE-14"])
    lines = split_lines(text)
    items = []
    labels = set()
    current = None
    for idx, line in enumerate(lines):
        if line.startswith("item:"):
            label = line[len("item:"):]
            if label.startswith(" "):
                label = label[1:]
            label = label.strip()
            if not label or not LABEL_RE.match(label):
                ie("IE-15", IE_WORDINGS["IE-15"] % (idx + 1))
            if label in labels:
                ie("IE-16", IE_WORDINGS["IE-16"] % label)
            labels.add(label)
            current = {"label": label, "lines": []}
            items.append(current)
        else:
            if current is None:
                if line.strip() == "" or line.startswith("#"):
                    continue
                ie("IE-15", IE_WORDINGS["IE-15"] % (idx + 1))
            current["lines"].append(line)
    if not items:
        first = 1
        ie("IE-15", IE_WORDINGS["IE-15"] % first)
    for item in items:
        wording_lines = item["lines"]
        if all(l.strip() == "" for l in wording_lines):
            ie("IE-17", IE_WORDINGS["IE-17"] % item["label"])
        item["wording"] = "\n".join(wording_lines)
    return items


def parse_declaration(data, path, amendment_items, amendment_fp):
    text = decode_input(data, "declaration", path)
    if len(data) == 0:
        ie("IE-21", IE_WORDINGS["IE-21"])
    lines = [l for l in split_lines(text) if l.strip() != "" and not l.startswith("#")]
    if not lines:
        ie("IE-21", IE_WORDINGS["IE-21"])
    labels = [it["label"] for it in amendment_items]
    declarer = None
    header_fp = None
    seen_header = set()
    pos = 0
    while pos < len(lines) and (lines[pos].startswith("declarer:") or lines[pos].startswith("amendment-fingerprint:")):
        line = lines[pos]
        name = line.split(":", 1)[0]
        if name in seen_header:
            ie("IE-56", IE_WORDINGS["IE-56"] % name)
        seen_header.add(name)
        value = line.split(":", 1)[1].strip()
        if name == "declarer":
            declarer = value
        else:
            header_fp = value
        pos += 1
    if not declarer:
        ie("IE-29", IE_WORDINGS["IE-29"])
    shown_fp = header_fp if header_fp is not None else "absent"
    if shown_fp != amendment_fp:
        ie("IE-18", IE_WORDINGS["IE-18"] % (shown_fp, amendment_fp))
    blocks = {}
    block_order = []
    confirmation = None
    confirmer = None
    conf_items = {}
    i = pos
    while i < len(lines):
        line = lines[i]
        if line == "confirmation:":
            confirmation = []
            i += 1
            while i < len(lines) and lines[i] != "end-confirmation:":
                cline = lines[i]
                if cline.startswith("confirmer:"):
                    confirmer = cline.split(":", 1)[1].strip()
                    i += 1
                    continue
                if cline.startswith("item:"):
                    clabel = cline[len("item:"):].strip()
                    confirmation.append(clabel)
                    if i + 1 < len(lines) and lines[i + 1].startswith("tokens:"):
                        tval = lines[i + 1][len("tokens:"):].strip()
                        if tval == "no-touch":
                            conf_items[clabel] = None
                        elif tval == "":
                            conf_items[clabel] = []
                        else:
                            conf_items[clabel] = [t.strip() for t in tval.split(", ")]
                        i += 2
                        continue
                    conf_items[clabel] = []
                    i += 1
                    continue
                i += 1
            break
        if line.startswith("item:"):
            label = line[len("item:"):].strip()
            if label not in labels:
                ie("IE-24", IE_WORDINGS["IE-24"] % label)
            if label in blocks:
                ie("IE-54", IE_WORDINGS["IE-54"] % label)
            expected = labels[len(block_order)] if len(block_order) < len(labels) else None
            if label != expected:
                ie("IE-54", IE_WORDINGS["IE-54"] % label)
            tokens = []
            bases = {}
            no_touch_basis = None
            has_token_lines = False
            has_no_touch = False
            i += 1
            while i < len(lines) and not lines[i].startswith("item:") and lines[i] != "confirmation:":
                bline = lines[i]
                if bline.startswith("token:"):
                    has_token_lines = True
                    rest = bline[len("token:"):]
                    if rest.startswith(" "):
                        rest = rest[1:]
                    if " | basis: " in rest:
                        token, basis = rest.split(" | basis: ", 1)
                    elif rest.endswith(" | basis:"):
                        token, basis = rest[: -len(" | basis:")], ""
                    else:
                        token, basis = rest, None
                    token = token.strip()
                    if not DECLARED_TOKEN_RE.match(token):
                        ie("IE-23", IE_WORDINGS["IE-23"] % (label, token))
                    if token in bases:
                        ie("IE-55", IE_WORDINGS["IE-55"] % (label, token))
                    if basis is None or basis.strip() == "":
                        ie("IE-30", IE_WORDINGS["IE-30"] % label)
                    bases[token] = basis
                    tokens.append(token)
                elif bline.startswith("no-touch:"):
                    has_no_touch = True
                    basis = bline[len("no-touch:"):]
                    if basis.startswith(" "):
                        basis = basis[1:]
                    if basis.strip() == "":
                        ie("IE-57", IE_WORDINGS["IE-57"] % label)
                    no_touch_basis = basis
                i += 1
            if has_token_lines and has_no_touch:
                ie("IE-26", IE_WORDINGS["IE-26"] % label)
            if not has_token_lines and not has_no_touch:
                blocks[label] = {"tokens": [], "bases": {}, "no_touch": False, "no_touch_basis": None, "empty": True}
                block_order.append(label)
                continue
            blocks[label] = {
                "tokens": tokens,
                "bases": bases,
                "no_touch": has_no_touch,
                "no_touch_basis": no_touch_basis,
                "empty": False,
            }
            block_order.append(label)
            continue
        i += 1
    for label in labels:
        if label not in blocks:
            ie("IE-25", IE_WORDINGS["IE-25"] % label)
    for label in labels:
        if blocks[label].get("empty"):
            ie("IE-22", IE_WORDINGS["IE-22"] % label)
    if confirmation is None or not confirmer:
        ie("IE-27", IE_WORDINGS["IE-27"])
    for label in labels:
        if label not in conf_items:
            ie("IE-19", IE_WORDINGS["IE-19"] % label)
        block = blocks[label]
        declared_set = None if block["no_touch"] else set(block["tokens"])
        conf_set = None if conf_items[label] is None else set(conf_items[label])
        if declared_set != conf_set:
            ie("IE-19", IE_WORDINGS["IE-19"] % label)
    return {
        "declarer": declarer,
        "confirmer": confirmer,
        "blocks": blocks,
    }
# ---------------------------------------------------------------------------
# Attestations, triggers, tripwire, and selection
# ---------------------------------------------------------------------------

FIELD_ORDER = ["tier", "context"] + CHANGE_KEYS


def build_attestations(req, declaration):
    values = req.values
    primary = {
        "tier": values.get("--tier"),
        "context": values.get("--context", "unstated"),
    }
    for key in CHANGE_KEYS:
        primary[key] = values.get(CHANGE_FLAG_FOR_KEY[key])
    second = None
    second_required = req.runner == req.author or declaration["declarer"] == req.author
    second_flags = ["--second-tier", "--second-context"] + ["--second-" + CHANGE_FLAG_FOR_KEY[k][2:] for k in CHANGE_KEYS]
    second_supplied = "--second-attester" in values or any(flag in values for flag in second_flags)
    if second_required or second_supplied:
        seat = values.get("--second-attester")
        if seat is None or seat.strip() == "" or seat == req.author or seat == req.runner:
            ie("IE-49", IE_WORDINGS["IE-49"])
        for flag in second_flags:
            if flag not in values:
                ie("IE-50", IE_WORDINGS["IE-50"] % flag)
        second = {"seat": seat, "tier": values["--second-tier"], "context": values["--second-context"]}
        for key in CHANGE_KEYS:
            second[key] = values["--second-" + CHANGE_FLAG_FOR_KEY[key][2:]]
    disagreements = []
    if second is not None:
        for field in FIELD_ORDER:
            if primary[field] != second[field]:
                disagreements.append({
                    "field": field,
                    "primary_value": primary[field],
                    "second_value": second[field],
                })
    effective_context = primary["context"]
    if primary["context"] == "disputed" or disagreements:
        effective_context = "disputed"
    triggers = []
    if primary["tier"] == "Plaid":
        triggers.append("tier-plaid")
    for key in CHANGE_KEYS:
        if primary[key] == "yes":
            triggers.append(CHANGE_TRIGGER_FOR_KEY[key])
    if effective_context in ("unstated", "mixed", "disputed"):
        triggers.append("context-" + effective_context)
    triggers = [t for t in TRIGGER_ORDER if t in triggers]
    effective_mode = "full" if (triggers or req.declared_mode == "full") else req.declared_mode
    gate_run = any(primary[k] == "yes" for k in ("gate_rule", "index_system", "corpus"))
    return {
        "primary": primary,
        "second": second,
        "disagreements": disagreements,
        "effective_context": effective_context,
        "triggers": triggers,
        "effective_mode": effective_mode,
        "gate_run": gate_run,
        "attester": req.runner,
    }


TRIPWIRE_RE = re.compile(r"(?<![A-Za-z0-9])(Gap|FM)([- ]?)(\d+)(?![A-Za-z])", re.IGNORECASE)
RANGE_AFTER_RE = re.compile(r"^(-\d| +\- +\d)")


def extract_tripwire(wording):
    found = []
    for m in TRIPWIRE_RE.finditer(wording):
        rest = wording[m.end():]
        if RANGE_AFTER_RE.match(rest):
            continue
        kind = m.group(1).lower()
        number = int(m.group(3))
        tok = "Gap %d" % number if kind == "gap" else "FM-%d" % number
        if tok not in found:
            found.append(tok)
    return found


def resolve_cross_ref(corpus, target_num):
    target = corpus["by_id"].get("C-%03d" % target_num)
    if target is not None:
        return target
    for row in corpus["rows"]:
        if row["num"] == target_num:
            return row
    return None


def compute_selection(corpus, amendment_items, declaration, attestations):
    effective_mode = attestations["effective_mode"]
    per_item = {}
    conflicts = {}
    related_per_item = {}
    for item in amendment_items:
        label = item["label"]
        block = declaration["blocks"][label]
        declared = [] if block["no_touch"] else list(block["tokens"])
        extracted = extract_tripwire(item["wording"])
        item["declared_tokens"] = declared
        item["extracted_tokens"] = extracted
        omitted = [t for t in extracted if t not in declared]
        if omitted:
            conflicts[label] = omitted
        if effective_mode == "full":
            checked = [r["id"] for r in corpus["rows"]]
            overridden = bool(block["no_touch"])
            is_no_touch = False
        else:
            if block["no_touch"]:
                checked = []
                overridden = False
                is_no_touch = True
            else:
                checked = [r["id"] for r in corpus["rows"] if any(t in r["tokens"] for t in declared)]
                overridden = False
                is_no_touch = False
        per_item[label] = {
            "checked_ids": checked,
            "no_touch": is_no_touch,
            "overridden": overridden,
            "declared": declared,
            "extracted": extracted,
        }
    checked_union = []
    for row in corpus["rows"]:
        if any(row["id"] in per_item[it["label"]]["checked_ids"] for it in amendment_items):
            checked_union.append(row["id"])
    for item in amendment_items:
        label = item["label"]
        selected = set(per_item[label]["checked_ids"])
        related = []
        for row in corpus["rows"]:
            if row["id"] not in selected:
                continue
            for cell in (row["incident"], row["test"], row["proc"]):
                for m in CROSS_REF_RE.finditer(cell):
                    target = resolve_cross_ref(corpus, int(m.group(1)))
                    if target is not None and target["id"] not in selected and target["id"] not in related:
                        related.append(target["id"])
        related_per_item[label] = related
    declared_all = []
    for item in amendment_items:
        for tok in per_item[item["label"]]["declared"]:
            if tok not in declared_all:
                declared_all.append(tok)
    token_row_counts = {}
    for tok in declared_all:
        token_row_counts[tok] = sum(1 for r in corpus["rows"] if tok in r["tokens"])
    multi = []
    for row in corpus["rows"]:
        if row["id"] not in checked_union:
            continue
        hits = [t for t in declared_all if t in row["tokens"]]
        if len(hits) >= 2:
            multi.append(row["id"])
    tokens_with_no_rows = [t for t in declared_all if token_row_counts.get(t, 0) == 0]
    related_union = []
    for item in amendment_items:
        for rid in related_per_item[item["label"]]:
            if rid not in checked_union and rid not in related_union:
                related_union.append(rid)
    related_union.sort(key=lambda cid: corpus["by_id"][cid]["num"])
    return {
        "per_item": per_item,
        "conflicts": conflicts,
        "checked_union": checked_union,
        "related_per_item": related_per_item,
        "related_union": related_union,
        "declared_all": declared_all,
        "token_row_counts": token_row_counts,
        "multi": multi,
        "tokens_with_no_rows": tokens_with_no_rows,
    }


def readback_lines(declaration, amendment_items, selection, corpus):
    lines = ["selection readback"]
    lines.append("declarer: %s" % declaration["declarer"])
    lines.append("confirming seat: %s" % declaration["confirmer"])
    for item in amendment_items:
        label = item["label"]
        info = selection["per_item"][label]
        block = declaration["blocks"][label]
        declared_text = "no-touch" if block["no_touch"] else format_token_list(info["declared"])
        extracted_text = format_token_list(info["extracted"]) if info["extracted"] else "none"
        lines.append("item %s: declared: %s; extracted: %s; rows selected: %d"
                     % (label, declared_text, extracted_text, len(info["checked_ids"])))
        if block["no_touch"]:
            lines.append("basis for %s no-touch: %s" % (label, block["no_touch_basis"]))
        else:
            for tok in info["declared"]:
                lines.append("basis for %s %s: %s" % (label, tok, block["bases"][tok]))
    lines.append("distinct rows selected: %d" % len(selection["checked_union"]))
    for tok in sort_tokens(selection["declared_all"]):
        lines.append("index %s: %d rows" % (tok, selection["token_row_counts"].get(tok, 0)))
    lines.append("rows selected by more than one index: %s" % format_token_list(selection["multi"]))
    lines.append("related but not selected: %s" % format_token_list(selection["related_union"]))
    lines.append(READBACK_FOOTER)
    return lines
# ---------------------------------------------------------------------------
# Self test probes
# ---------------------------------------------------------------------------


def run_self_test(forced_failure):
    results = {}

    def probe_selection():
        rows = [
            {"id": "C-001", "num": 1, "tokens": ["Gap 1"], "incident": "", "test": "", "proc": ""},
            {"id": "C-002", "num": 2, "tokens": ["FM-1"], "incident": "", "test": "", "proc": ""},
            {"id": "C-003", "num": 3, "tokens": ["Gap 1", "FM-2"], "incident": "", "test": "", "proc": ""},
        ]
        corpus = {"rows": rows, "by_id": {r["id"]: r for r in rows}}
        items = [{"label": "A1", "wording": "Synthetic wording with no index token."}]
        declaration = {"blocks": {"A1": {
            "tokens": ["Gap 1"], "bases": {"Gap 1": "synthetic basis"},
            "no_touch": False, "no_touch_basis": None,
        }}}
        attestations = {"effective_mode": "subset"}
        selection = compute_selection(corpus, items, declaration, attestations)
        return selection["per_item"]["A1"]["checked_ids"] == ["C-001", "C-003"]

    def probe_pass():
        verdicts = [{"word": "PASS", "excused": False}, {"word": "PASS", "excused": False}]
        return item_outcome_from_verdicts("subset", False, ["C-001", "C-002"], verdicts) == "pass"

    def probe_blocking():
        verdicts = [{"word": "FAIL", "excused": False}]
        return item_outcome_from_verdicts("subset", False, ["C-001"], verdicts) == "fail"

    def probe_excused():
        verdicts = [{"word": "FAIL", "excused": True}]
        return item_outcome_from_verdicts("subset", False, ["C-001"], verdicts) == "re-ruled pass"

    def probe_binding():
        header = {
            "amendment_fp": "a" * 64, "corpus_fp": "b" * 64, "declaration_fp": "c" * 64,
            "declared_mode": "subset", "effective_mode": "subset", "triggers": [],
            "checked_ids": ["C-001"], "roster": ["Judge Seat"],
        }
        recomputed = dict(header)
        recomputed["amendment_fp"] = "d" * 64
        return binding_mismatch_name(header, recomputed) == "amendment fingerprint"

    probes = [
        ("selection_probe", probe_selection, "the selection probe selected the wrong synthetic rows"),
        ("pass_probe", probe_pass, "the pass probe did not produce a pass"),
        ("blocking_probe", probe_blocking, "the blocking probe did not produce a fail"),
        ("excused_fail_probe", probe_excused, "the excused fail probe did not produce a re-ruled pass"),
        ("binding_probe", probe_binding, "the binding probe accepted a broken binding"),
    ]
    out = []
    for name, fn, observed in probes:
        if forced_failure == name:
            out.append({"name": name, "result": "fail", "observed": "forced by the test seam"})
            continue
        try:
            ok = bool(fn())
        except Exception:
            ok = False
        out.append({"name": name, "result": "pass" if ok else "fail",
                    "observed": None if ok else observed})
    return out


def self_test_failed(probes):
    return any(p["result"] == "fail" for p in probes)


def self_test_report_text(probes):
    lines = ["regression-corpus-gate 1.0.0"]
    lines.append("self test failure: %s" % SENTENCES["self test failure"])
    for p in probes:
        if p["result"] == "pass":
            lines.append("probe %s: pass" % p["name"])
        else:
            lines.append("probe %s: fail, %s" % (p["name"], p["observed"]))
    lines.append(SELF_TEST_RECORD_LINE)
    lines.append("exit status: 8")
    return join_text(lines)


def self_test_section_lines(probes):
    lines = ["self test"]
    for p in probes:
        lines.append("probe %s: %s" % (p["name"], p["result"]))
    lines.append(SELF_TEST_COUNTED_LINE)
    lines.append(SELF_TEST_RECORD_LINE)
    return lines
# ---------------------------------------------------------------------------
# Queue search and re-ruling verification
# ---------------------------------------------------------------------------

ENTRY_HEADING_RE = re.compile(r"^#{2,3} ")
PASSAGE_HEADING_RE = re.compile(r"^#{4,}")
QUEUE_ID_RE = re.compile(r"DQ-\d+")
STATUS_WORDS = ["RULED", "SETTLED", "BANKED", "PARKED", "ORDERED", "standing", "open", "superseded", "withdrawn"]


def read_queue(path):
    """Returns a dict with kind, bytes, measured, and entries where read."""
    if not os.path.exists(path):
        return {"kind": "missing", "bytes": None, "measured": None, "entries": None}
    if os.path.isdir(path):
        return {"kind": "unreadable", "bytes": None, "measured": None, "entries": None}
    try:
        measured = os.path.getsize(path)
    except OSError:
        return {"kind": "unreadable", "bytes": None, "measured": None, "entries": None}
    if measured > BYTE_LIMIT:
        return {"kind": "oversize", "bytes": None, "measured": measured, "entries": None}
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return {"kind": "unreadable", "bytes": None, "measured": measured, "entries": None}
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return {"kind": "malformed", "bytes": data, "measured": measured, "entries": None}
    entries = parse_queue_entries(text)
    if not entries:
        return {"kind": "empty", "bytes": data, "measured": measured, "entries": []}
    return {"kind": "ok", "bytes": data, "measured": measured, "entries": entries}


def entry_status(lines):
    for line in lines[1:]:
        if PASSAGE_HEADING_RE.match(line):
            break
        if line.startswith("Status:"):
            return line[len("Status:"):].strip()
    heading = lines[0]
    m = QUEUE_ID_RE.search(heading)
    rest = heading[m.end():] if m else heading
    best = None
    best_pos = None
    for word in STATUS_WORDS:
        wm = re.search(r"\b%s\b" % re.escape(word), rest, re.IGNORECASE)
        if wm and (best_pos is None or wm.start() < best_pos):
            best = wm.group(0)
            best_pos = wm.start()
    if best is not None:
        return best
    return "no status stated"


def parse_queue_entries(text):
    lines = split_lines(text)
    entries = []
    start = None
    for idx, line in enumerate(lines):
        if ENTRY_HEADING_RE.match(line):
            if start is not None:
                entries.append(make_entry(lines, start, idx))
            start = idx
    if start is not None:
        entries.append(make_entry(lines, start, len(lines)))
    return entries


def make_entry(lines, start, end):
    entry_lines = lines[start:end]
    heading = entry_lines[0]
    m = QUEUE_ID_RE.search(heading)
    return {
        "heading": heading,
        "first_line": start + 1,
        "last_line": end,
        "queue_item": m.group(0) if m else "no queue item identifier in heading",
        "status": entry_status(entry_lines),
        "text": "\n".join(entry_lines),
    }


def status_counts(status):
    if re.search(r"\bRULED\b", status, re.IGNORECASE):
        return "ruled"
    if status.strip().lower() == "standing":
        return "standing"
    return "not ruled"


def candidates_for(entries, corpus_id):
    pattern = re.compile(r"(?<![A-Za-z0-9-])%s(?![A-Za-z0-9-])" % re.escape(corpus_id))
    return [e for e in entries if pattern.search(e["text"])]


def candidate_line(entry, corpus_id):
    return ("candidate for %s: %s, status as read %s, heading: %s, entry lines %d to %d"
            % (corpus_id, entry["queue_item"], entry["status"], entry["heading"],
               entry["first_line"], entry["last_line"]))


def verify_claim(queue, corpus_id, queue_item):
    """Returns (confirmed, candidate_or_none, reason_or_none, candidates)."""
    if queue["kind"] in ("missing", "unreadable"):
        return False, None, "queue could not be verified: %s" % queue["kind"], []
    if queue["kind"] == "oversize":
        return False, None, "queue could not be verified: oversize, measured %d bytes" % queue["measured"], []
    if queue["kind"] in ("empty", "malformed"):
        return False, None, "queue could not be verified: %s" % queue["kind"], []
    cands = candidates_for(queue["entries"], corpus_id)
    for cand in cands:
        if cand["queue_item"] == queue_item and status_counts(cand["status"]) in ("ruled", "standing"):
            return True, cand, None, cands
    for cand in cands:
        if cand["queue_item"] == queue_item:
            return False, cand, "status does not count as a ruling", cands
    return False, None, "queue item not found for this corpus ID", cands
# ---------------------------------------------------------------------------
# Worksheet and template rendering
# ---------------------------------------------------------------------------

def row_section_lines(corpus, selection, label, row):
    lines = ["row %s for item %s" % (row["id"], label)]
    lines.append("incident: %s" % row["incident"])
    lines.append("pass procedure: %s" % row["proc"])
    clause_text = row["clause"] if row["clause"] is not None else NO_CLAUSE_STATEMENT
    lines.append("test: %s" % clause_text)
    if row["divergence"]:
        lines.append("row note: %s" % row["divergence"])
    if row["flagged"]:
        lines.append("flagged: only UNJUDGEABLE may be entered for this row")
        if row["flag_note"]:
            lines.append("row note: %s" % row["flag_note"])
    selected = set(selection["per_item"][label]["checked_ids"])
    related_here = []
    for cell in (row["incident"], row["test"], row["proc"]):
        for m in CROSS_REF_RE.finditer(cell):
            target = resolve_cross_ref(corpus, int(m.group(1)))
            if target is not None and target["id"] not in selected and target["id"] not in related_here:
                related_here.append(target["id"])
    for rid in related_here:
        lines.append("related: %s is related and is not checked by this item" % rid)
    return lines


def worksheet_text(req, corpus, declaration, selection, attestations, probes,
                   corpus_fp, amendment_fp, declaration_fp, queue_state, amendment_items):
    lines = []
    lines.extend(readback_lines(declaration, amendment_items, selection, corpus))
    lines.append("regression-corpus-gate 1.0.0")
    lines.append(WORKSHEET_FIXED_LINE)
    lines.append("runner: %s" % req.runner)
    lines.append("judge of record: %s" % req.judge)
    lines.append("panel judges: %s" % (", ".join(req.panel) if req.panel else "none"))
    lines.append("wording author: %s" % req.author)
    lines.append("ruler: %s" % req.ruler)
    lines.append("step coordinator: %s" % req.coordinator)
    lines.append("declarer: %s" % declaration["declarer"])
    lines.append("confirming seat: %s" % declaration["confirmer"])
    lines.append("declared mode: %s" % req.declared_mode)
    lines.append("effective mode: %s" % attestations["effective_mode"])
    lines.append("triggers: %s" % (", ".join(attestations["triggers"]) if attestations["triggers"] else "none"))
    lines.append("corpus fingerprint: %s" % corpus_fp)
    lines.append("amendment fingerprint: %s" % amendment_fp)
    lines.append("declaration fingerprint: %s" % declaration_fp)
    for p in probes:
        lines.append("probe %s: pass" % p["name"])
    lines.append(SELF_TEST_RECORD_LINE)
    lines.append("worst day playbook")
    lines.extend(PLAYBOOK_LINES)
    if not req.queue_supplied:
        lines.append("candidates not listed: no queue path was supplied")
    elif queue_state is None or queue_state["kind"] not in ("ok", "empty"):
        lines.append("candidates not listed: the queue could not be read at this form")
    else:
        lines.append("queue as read: %d bytes of the 2000000 byte limit" % queue_state["measured"])
        candidate_lines = []
        if queue_state["kind"] == "ok":
            for cid in selection["checked_union"]:
                for entry in candidates_for(queue_state["entries"], cid):
                    candidate_lines.append(candidate_line(entry, cid))
        if candidate_lines:
            lines.extend(candidate_lines)
        else:
            lines.append("no candidates stand for the selected rows")
    for item in amendment_items:
        label = item["label"]
        for cid in selection["per_item"][label]["checked_ids"]:
            lines.extend(row_section_lines(corpus, selection, label, corpus["by_id"][cid]))
    return join_text(lines)


def template_text(req, selection, attestations, corpus_fp, amendment_fp, declaration_fp, amendment_items):
    lines = []
    lines.append("amendment-fingerprint: %s" % amendment_fp)
    lines.append("corpus-fingerprint: %s" % corpus_fp)
    lines.append("declaration-fingerprint: %s" % declaration_fp)
    lines.append("declared-mode: %s" % req.declared_mode)
    lines.append("effective-mode: %s" % attestations["effective_mode"])
    lines.append("triggers: %s" % (", ".join(attestations["triggers"]) if attestations["triggers"] else "none"))
    for cid in selection["checked_union"]:
        lines.append("checked: %s" % cid)
    lines.append("judge-of-record: %s" % req.judge)
    for judge in req.panel:
        lines.append("panel-judge: %s" % judge)
    for item in amendment_items:
        label = item["label"]
        for cid in selection["per_item"][label]["checked_ids"]:
            lines.append("verdict: %s %s" % (label, cid))
            lines.append("judge: ")
            lines.append("clause: ")
            lines.append("word: ")
            lines.append("reason: ")
    lines.append(TEMPLATE_CLOSING_LINE)
    return join_text(lines)
# ---------------------------------------------------------------------------
# Verdicts parsing, binding, and the barred check
# ---------------------------------------------------------------------------

HEADER_SINGLETONS = [
    "amendment-fingerprint", "corpus-fingerprint", "declaration-fingerprint",
    "declared-mode", "effective-mode", "triggers", "judge-of-record",
]
VERDICT_WORDS = {"PASS", "FAIL", "UNJUDGEABLE"}


def binding_mismatch_name(header, recomputed):
    order = [
        ("amendment fingerprint", header["amendment_fp"], recomputed["amendment_fp"]),
        ("corpus fingerprint", header["corpus_fp"], recomputed["corpus_fp"]),
        ("declaration fingerprint", header["declaration_fp"], recomputed["declaration_fp"]),
        ("declared mode", header["declared_mode"], recomputed["declared_mode"]),
        ("effective mode", header["effective_mode"], recomputed["effective_mode"]),
        ("trigger list", header["triggers"], recomputed["triggers"]),
        ("checked ID set", header["checked_ids"], recomputed["checked_ids"]),
        ("judge roster", header["roster"], recomputed["roster"]),
    ]
    for name, got, want in order:
        if got != want:
            return name
    return None


def verdicts_content_lines(text):
    return [l for l in split_lines(text) if l.strip() != "" and not l.startswith("#")]


def parse_verdicts(text, corpus, selection, form, run_roster):
    lines = verdicts_content_lines(text)
    header = {
        "amendment_fp": None, "corpus_fp": None, "declaration_fp": None,
        "declared_mode": None, "effective_mode": None, "triggers": None,
        "checked_ids": [], "judge_of_record": None, "panel": [],
    }
    seen_singletons = set()
    blocks_raw = []
    current = None
    in_header = True
    for line in lines:
        if line.startswith("verdict:"):
            in_header = False
            current = {"header_line": line, "lines": []}
            blocks_raw.append(current)
            continue
        if in_header:
            matched = False
            for name in HEADER_SINGLETONS + ["checked", "panel-judge"]:
                if line.startswith(name + ":"):
                    matched = True
                    value = line[len(name) + 1:].strip()
                    if name == "checked":
                        header["checked_ids"].append(value)
                    elif name == "panel-judge":
                        header["panel"].append(value)
                    else:
                        if name in seen_singletons:
                            ie("IE-46", IE_WORDINGS["IE-46"] % name)
                        seen_singletons.add(name)
                        if name == "amendment-fingerprint":
                            header["amendment_fp"] = value
                        elif name == "corpus-fingerprint":
                            header["corpus_fp"] = value
                        elif name == "declaration-fingerprint":
                            header["declaration_fp"] = value
                        elif name == "declared-mode":
                            header["declared_mode"] = value
                        elif name == "effective-mode":
                            header["effective_mode"] = value
                        elif name == "triggers":
                            if value == "":
                                # An empty value is held as a list no recomputed
                                # trigger list can equal, so the binding comparison
                                # refuses it under IE-38 naming the trigger list.
                                header["triggers"] = [""]
                            elif value == "none":
                                header["triggers"] = []
                            else:
                                header["triggers"] = [t.strip() for t in value.split(", ")]
                        elif name == "judge-of-record":
                            header["judge_of_record"] = value
                    break
            if not matched:
                current = None
            continue
        if current is not None:
            current["lines"].append(line)
    for name in HEADER_SINGLETONS:
        key = {
            "amendment-fingerprint": "amendment_fp", "corpus-fingerprint": "corpus_fp",
            "declaration-fingerprint": "declaration_fp", "declared-mode": "declared_mode",
            "effective-mode": "effective_mode", "triggers": "triggers",
            "judge-of-record": "judge_of_record",
        }[name]
        if header[key] is None:
            ie("IE-46", IE_WORDINGS["IE-46"] % name)
    header["roster"] = [header["judge_of_record"]] + header["panel"]
    verdicts = []
    seen_pairs = set()
    for raw in blocks_raw:
        parts = raw["header_line"][len("verdict:"):].strip().split(" ")
        label = parts[0] if parts else ""
        cid = parts[1] if len(parts) > 1 else ""
        fields = {"judge": None, "clause": None, "word": None, "reason": None}
        claim = None
        claim_count = 0
        in_claim = False
        for line in raw["lines"]:
            if line == "claim:":
                claim_count += 1
                if claim_count > 1:
                    ie("IE-42", IE_WORDINGS["IE-42"] % (label, cid))
                claim = {"queue_item": None, "ruling_date": None, "confirming_judge": None}
                in_claim = True
                continue
            if in_claim:
                if line.startswith("queue-item:"):
                    if claim["queue_item"] is not None:
                        ie("IE-33", IE_WORDINGS["IE-33"] % (label, cid))
                    claim["queue_item"] = line[len("queue-item:"):].strip()
                    continue
                if line.startswith("ruling-date:"):
                    if claim["ruling_date"] is not None:
                        ie("IE-33", IE_WORDINGS["IE-33"] % (label, cid))
                    claim["ruling_date"] = line[len("ruling-date:"):].strip()
                    continue
                if line.startswith("confirming-judge:"):
                    if claim["confirming_judge"] is not None:
                        ie("IE-33", IE_WORDINGS["IE-33"] % (label, cid))
                    claim["confirming_judge"] = line[len("confirming-judge:"):].strip()
                    continue
                in_claim = False
            for fname in ("judge", "clause", "word", "reason"):
                if line.startswith(fname + ":"):
                    if fields[fname] is not None:
                        ie("IE-33", IE_WORDINGS["IE-33"] % (label, cid))
                    value = line[len(fname) + 1:]
                    if value.startswith(" "):
                        value = value[1:]
                    if fname == "judge":
                        value = value.strip()
                    fields[fname] = value
                    break
        verdict = {
            "label": label, "id": cid,
            "judge": fields["judge"], "clause": fields["clause"],
            "word": fields["word"], "reason": fields["reason"],
            "claim": claim,
        }
        if form == "remaining" and claim is None and all(
                fields[f] is not None and fields[f].strip() == "" for f in ("judge", "clause", "word", "reason")):
            verdict["untouched"] = True
            verdicts.append(verdict)
            continue
        verdict["untouched"] = False
        pair = (label, cid)
        if pair in seen_pairs:
            ie("IE-33", IE_WORDINGS["IE-33"] % (label, cid))
        seen_pairs.add(pair)
        checked_for_item = selection["per_item"].get(label, {}).get("checked_ids", [])
        if cid not in checked_for_item:
            ie("IE-34", IE_WORDINGS["IE-34"] % (label, cid))
        for slot in ("judge", "clause", "word"):
            if fields[slot] is None or fields[slot].strip() == "":
                ie("IE-45", IE_WORDINGS["IE-45"] % (label, cid, slot))
        if fields["word"] not in VERDICT_WORDS:
            ie("IE-32", IE_WORDINGS["IE-32"] % (label, cid, fields["word"]))
        if fields["reason"] is None or fields["reason"].strip() == "":
            ie("IE-35", IE_WORDINGS["IE-35"] % (label, cid))
        row = corpus["by_id"][cid]
        if row["flagged"] and fields["word"] != "UNJUDGEABLE":
            ie("IE-36", IE_WORDINGS["IE-36"] % (label, cid, fields["word"]))
        if fields["judge"] not in run_roster and fields["judge"] not in header["roster"]:
            ie("IE-37", IE_WORDINGS["IE-37"] % (label, cid, fields["judge"]))
        target = row["clause"] if row["clause"] is not None else NO_CLAUSE_STATEMENT
        if fields["clause"] != target:
            ie("IE-53", IE_WORDINGS["IE-53"] % (label, cid))
        if claim is not None:
            if fields["word"] != "FAIL":
                ie("IE-39", IE_WORDINGS["IE-39"] % (label, cid))
            if claim["queue_item"] is None or claim["queue_item"] == "":
                ie("IE-43", IE_WORDINGS["IE-43"] % (label, cid))
            if claim["ruling_date"] is None or claim["ruling_date"] == "":
                ie("IE-44", IE_WORDINGS["IE-44"] % (label, cid))
            if claim["confirming_judge"] is None or claim["confirming_judge"] == "":
                ie("IE-41", IE_WORDINGS["IE-41"] % (label, cid))
            if claim["confirming_judge"] != fields["judge"]:
                ie("IE-40", IE_WORDINGS["IE-40"] % (label, cid))
        verdicts.append(verdict)
    return header, verdicts


def compute_bars(judges_in_order, req):
    bars = []
    roles = [(req.author, "the wording author"), (req.ruler, "the ruler of the step"),
             (req.coordinator, "the coordinator of the step")]
    for judge in judges_in_order:
        for seat, role in roles:
            if judge == seat:
                bars.append((judge, role))
    return bars


def barred_report_text(req, bars, corpus_fp, amendment_fp, declaration_fp):
    lines = ["regression-corpus-gate 1.0.0"]
    lines.append("barred: %s" % SENTENCES["barred"])
    lines.append("filing: no trace verdict, filed by reference with the outcome name barred")
    for judge, role in bars:
        lines.append("bar: %s is %s" % (judge, role))
    lines.append("no verdicts were issued and no gate outcome stands")
    lines.append("runner: %s" % req.runner)
    lines.append("judge of record: %s" % req.judge)
    lines.append("panel judges: %s" % (", ".join(req.panel) if req.panel else "none"))
    lines.append("wording author: %s" % req.author)
    lines.append("ruler: %s" % req.ruler)
    lines.append("step coordinator: %s" % req.coordinator)
    lines.append("corpus fingerprint: %s" % corpus_fp)
    lines.append("amendment fingerprint: %s" % amendment_fp)
    lines.append("declaration fingerprint: %s" % declaration_fp)
    lines.append("exit status: 6")
    return join_text(lines)


def declaration_conflict_report_text(declaration, selection, amendment_fp, declaration_fp):
    lines = ["regression-corpus-gate 1.0.0"]
    lines.append("declaration conflict: %s" % SENTENCES["declaration conflict"])
    for label, omitted in selection["conflicts"].items():
        lines.append("item %s: omitted tokens: %s" % (label, ", ".join(omitted)))
    lines.append("the declaration must be amended, freshly confirmed, and rerun before any judging")
    lines.append("declarer: %s" % declaration["declarer"])
    lines.append("confirming seat: %s" % declaration["confirmer"])
    lines.append("amendment fingerprint: %s" % amendment_fp)
    lines.append("declaration fingerprint: %s" % declaration_fp)
    lines.append("exit status: 7")
    return join_text(lines)
# ---------------------------------------------------------------------------
# Arithmetic, counts, and the record composer
# ---------------------------------------------------------------------------

def item_outcome_from_verdicts(mode, is_no_touch, checked_ids, verdicts):
    """verdicts: list of dicts with word and excused, one per present verdict."""
    if mode == "subset" and is_no_touch:
        return "pass"
    if mode == "subset" and not is_no_touch and not checked_ids:
        return "unverifiable"
    words = [v["word"] for v in verdicts]
    if any(v["word"] == "FAIL" and not v["excused"] for v in verdicts):
        return "fail"
    if any(w == "UNJUDGEABLE" for w in words):
        return "unverifiable"
    if any(v["word"] == "FAIL" and v["excused"] for v in verdicts):
        return "re-ruled pass"
    return "pass"

def counts_start():
    return {"checks_run": 0, "passed": 0, "failed": 0, "failed_excused": 0,
            "failed_unexcused": 0, "unjudgeable": 0, "missing": 0}


def counts_add_checks(counts, number):
    counts["checks_run"] += number


def counts_add_word(counts, word, excused):
    if word == "PASS":
        counts["passed"] += 1
    elif word == "FAIL":
        counts["failed"] += 1
        if excused:
            counts["failed_excused"] += 1
        else:
            counts["failed_unexcused"] += 1
    else:
        counts["unjudgeable"] += 1


def counts_add_missing(counts, number):
    counts["missing"] += number


def run_outcome_from_item_outcomes(outcomes, any_missing):
    if any_missing:
        return "incomplete"
    if "fail" in outcomes:
        return "fail"
    if "unverifiable" in outcomes:
        return "unverifiable"
    if "re-ruled pass" in outcomes:
        return "re-ruled pass"
    return "pass"


def build_finalise_record(req, corpus, declaration, selection, attestations, verdicts,
                          probes, fps, verdicts_state, amendment_items):
    """fps: dict of fingerprints and paths facts. Returns the record dict."""
    verdict_by_pair = {}
    for v in verdicts:
        verdict_by_pair[(v["label"], v["id"])] = v
    claims = [v for v in verdicts if v["claim"] is not None]
    queue = None
    queue_fp_value = None
    if claims:
        queue = read_queue(req.queue_path)
        if queue["kind"] in ("missing", "unreadable", "oversize"):
            queue_fp_value = "no queue file was read: %s" % queue["kind"]
        else:
            queue_fp_value = fingerprint(queue["bytes"])
    verification = {}
    candidates_by_id = {}
    matches = []
    unverified = []
    for v in claims:
        cid = v["id"]
        confirmed, cand, reason, cands = (False, None, "queue item not found for this corpus ID", [])
        if queue is not None:
            confirmed, cand, reason, cands = verify_claim(queue, cid, v["claim"]["queue_item"])
        verification[(v["label"], cid)] = confirmed
        if cid not in candidates_by_id:
            candidates_by_id[cid] = cands
        if confirmed:
            matches.append({
                "item": v["label"], "corpus_id": cid,
                "queue_item": v["claim"]["queue_item"],
                "ruling_date": v["claim"]["ruling_date"],
                "status_as_read": cand["status"],
                "confirming_judge": v["claim"]["confirming_judge"],
            })
        else:
            unverified.append({
                "item": v["label"], "corpus_id": cid,
                "queue_item": v["claim"]["queue_item"],
                "reason": reason,
            })
    items_out = []
    missing_pairs = []
    counts = counts_start()
    blocked = []
    any_missing = False
    for item in amendment_items:
        label = item["label"]
        info = selection["per_item"][label]
        checked = info["checked_ids"]
        counts_add_checks(counts, len(checked))
        verdict_objs = []
        present = []
        item_missing = []
        for cid in checked:
            row = corpus["by_id"][cid]
            v = verdict_by_pair.get((label, cid))
            row_note = row["flag_note"] if row["flagged"] else (row["divergence"] or None)
            if row["flagged"] and row["divergence"]:
                row_note = (row["flag_note"] + " " + row["divergence"]) if row["flag_note"] else row["divergence"]
            if v is None:
                item_missing.append(cid)
                missing_pairs.append({"item": label, "corpus_id": cid})
                verdict_objs.append({
                    "corpus_id": cid, "judge": None, "clause": None, "word": None,
                    "reason": None, "flagged": row["flagged"], "row_note": row_note,
                    "claim": None, "excused": False,
                    "trace_excerpt": {"word": "not judged", "queue_item": None},
                    "missing": True, "incident": row["incident"], "proc": row["proc"],
                })
                continue
            excused = bool(v["claim"] is not None and verification.get((label, cid), False))
            present.append({"word": v["word"], "excused": excused})
            counts_add_word(counts, v["word"], excused)
            if v["word"] == "PASS":
                trace = {"word": "PASS", "queue_item": None}
            elif v["word"] == "FAIL":
                if excused:
                    trace = {"word": "RE-RULED", "queue_item": v["claim"]["queue_item"]}
                else:
                    trace = {"word": "FAIL", "queue_item": None}
            else:
                trace = {"word": "not judged", "queue_item": None}
            verdict_objs.append({
                "corpus_id": cid, "judge": v["judge"], "clause": v["clause"],
                "word": v["word"], "reason": v["reason"], "flagged": row["flagged"],
                "row_note": row_note,
                "claim": ({"queue_item": v["claim"]["queue_item"],
                           "ruling_date": v["claim"]["ruling_date"],
                           "confirming_judge": v["claim"]["confirming_judge"]}
                          if v["claim"] is not None else None),
                "excused": excused, "trace_excerpt": trace,
                "incident": row["incident"], "proc": row["proc"],
            })
        counts_add_missing(counts, len(item_missing))
        if item_missing:
            any_missing = True
            outcome = "incomplete"
        else:
            outcome = item_outcome_from_verdicts(
                attestations["effective_mode"], info["no_touch"], checked, present)
        unexcused_fails = sum(1 for p in present if p["word"] == "FAIL" and not p["excused"])
        if outcome == "fail":
            blocked.append({"item": label, "unexcused_fail_count": unexcused_fails})
        items_out.append({
            "label": label, "outcome": outcome, "no_touch": info["no_touch"],
            "overridden": info["overridden"], "checked_ids": list(checked),
            "verdicts": verdict_objs,
        })
    run_outcome = run_outcome_from_item_outcomes([i["outcome"] for i in items_out], any_missing)
    candidates_out = []
    for cid in sorted(candidates_by_id, key=lambda c: corpus["by_id"][c]["num"] if c in corpus["by_id"] else 0):
        for entry in candidates_by_id[cid]:
            candidates_out.append({
                "corpus_id": cid, "queue_item": entry["queue_item"],
                "status_as_read": entry["status"], "heading": entry["heading"],
                "first_line": entry["first_line"], "last_line": entry["last_line"],
            })
    queue_has_standing = None
    if queue is not None and queue["kind"] == "ok":
        queue_has_standing = any(status_counts(e["status"]) == "standing" for e in queue["entries"])
    standing_fact = bool(claims) and queue is not None and queue["kind"] == "ok" and queue_has_standing is False
    record = {
        "outcome": run_outcome,
        "exit_status": STATUS_FOR_OUTCOME[run_outcome],
        "items": items_out,
        "counts": counts,
        "missing": missing_pairs,
        "blocked_items": blocked,
        "matches": matches,
        "unverified": unverified,
        "candidates": candidates_out,
        "candidates_by_id": candidates_by_id,
        "queue_fp_value": queue_fp_value,
        "queue_read": queue is not None,
        "standing_fact": standing_fact,
        "verdicts_state": verdicts_state,
    }
    return record
# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def remaining_report_text(req, selection, attestations, missing_pairs, total_pairs, amendment_items):
    lines = ["regression-corpus-gate 1.0.0"]
    lines.extend(REMAINING_FIXED_LINES)
    lines.append("declared mode: %s" % req.declared_mode)
    lines.append("effective mode: %s" % attestations["effective_mode"])
    lines.append("triggers: %s" % (", ".join(attestations["triggers"]) if attestations["triggers"] else "none"))
    lines.append("checked pairs: %d" % total_pairs)
    per_item_missing = {}
    for label, cid in missing_pairs:
        per_item_missing.setdefault(label, []).append(cid)
    for item in amendment_items:
        label = item["label"]
        if label in per_item_missing:
            ids = per_item_missing[label]
            lines.append("item %s: missing %d: %s" % (label, len(ids), ", ".join(ids)))
    lines.append("pairs remaining: %d of %d checked pairs" % (len(missing_pairs), total_pairs))
    lines.append("exit status: 9")
    return join_text(lines)


def limit_lines(corpus, selection, record):
    lines = [LIMIT_JUDGE_REASONING, LIMIT_DECLARATION, dialect_line(corpus)]
    for clause in corpus["clause_families"]:
        lines.append("clause family as read: %s, %d rows" % (clause, corpus["family_counts"][clause]))
    lines.append("declared tokens that selected no row: %s"
                 % format_token_list(sort_tokens(selection["tokens_with_no_rows"])))
    if record["standing_fact"]:
        lines.append(QUEUE_STANDING_LINE)
    lines.append(LIMIT_BINDING)
    lines.append(LIMIT_CORPUS_CHANGE)
    lines.append(LIMIT_EXTRACTION)
    lines.append(LIMIT_FATIGUE)
    lines.append(LIMIT_ATTESTATION)
    lines.append(SIZING_LINE)
    return lines


def path_display(path, supplied, default_path):
    if not supplied and resolve_path(default_path) == path:
        return "%s (default)" % path
    return path


def finalise_text_report(req, corpus, declaration, selection, attestations, record,
                         probes, fps, amendment_items):
    outcome = record["outcome"]
    lines = ["regression-corpus-gate 1.0.0"]
    lines.append("%s: %s" % (outcome, SENTENCES[outcome]))
    if record["blocked_items"]:
        for b in record["blocked_items"]:
            lines.append("blocked item: %s, unexcused fails: %d" % (b["item"], b["unexcused_fail_count"]))
    else:
        lines.append("blocked items: none")
    trace_word = TRACE_WORD[outcome]
    if trace_word is not None:
        lines.append("filing: %s" % trace_word)
    else:
        lines.append("filing: no trace verdict, filed by reference with the outcome name %s" % outcome)
    lines.append(NEXT_STEP_LINE)
    lines.append("exit status: %d" % record["exit_status"])
    lines.append("coverage:")
    searched = selection["declared_all"] if attestations["effective_mode"] == "subset" else corpus["all_tokens"]
    searched_sorted = sort_tokens(searched)
    distinct_checked = len(selection["checked_union"])
    if attestations["effective_mode"] == "full":
        lines.append("all indexes were searched and no rows were left unchecked")
        lines.append("rows checked: %d distinct rows" % distinct_checked)
    else:
        lines.append("indexes searched: %s" % format_token_list(searched_sorted))
        lines.append("rows checked: %d distinct rows" % distinct_checked)
        lines.append("rows not checked: %d" % (corpus["row_count"] - distinct_checked))
        not_searched = [t for t in sort_tokens(corpus["all_tokens"]) if t not in searched]
        lines.append("indexes not searched: %s" % format_token_list(not_searched))
    if all(i["no_touch"] for i in record["items"]) and record["items"]:
        lines.append("no entry was touched")
    lines.append("runner: %s" % req.runner)
    lines.append("judge of record: %s" % req.judge)
    lines.append("panel judges: %s" % (", ".join(req.panel) if req.panel else "none"))
    lines.append("wording author: %s" % req.author)
    lines.append("ruler: %s" % req.ruler)
    lines.append("step coordinator: %s" % req.coordinator)
    lines.append("reader designate: %s" % req.reader)
    lines.append("declarer: %s" % declaration["declarer"])
    lines.append("confirming seat: %s" % declaration["confirmer"])
    lines.append("auditor oversight: %s" % AUDITOR_OVERSIGHT_LINE)
    lines.append("corpus path: %s" % path_display(req.corpus_path, req.corpus_supplied, DEFAULT_CORPUS))
    lines.append("amendment path: %s" % req.amendment_path)
    lines.append("declaration path: %s" % req.declaration_path)
    lines.append("verdicts path: %s" % req.verdicts_path)
    if record["queue_read"]:
        lines.append("queue path: %s" % path_display(req.queue_path, req.queue_supplied, DEFAULT_QUEUE))
    elif req.queue_supplied:
        lines.append("queue path: %s" % req.queue_path)
    else:
        lines.append("queue path: %s" % path_display(req.queue_path, False, DEFAULT_QUEUE))
    lines.append("corpus fingerprint: %s" % fps["corpus"])
    lines.append("amendment fingerprint: %s" % fps["amendment"])
    lines.append("declaration fingerprint: %s" % fps["declaration"])
    if record["verdicts_state"] == "missing":
        lines.append("verdicts fingerprint: no verdicts file was read: missing")
    else:
        lines.append("verdicts fingerprint: %s" % fps["verdicts"])
    if record["queue_fp_value"] is not None:
        lines.append("queue fingerprint: %s" % record["queue_fp_value"])
    elif record["queue_read"]:
        lines.append("queue fingerprint: %s" % fps.get("queue", ""))
    else:
        lines.append("queue fingerprint: no queue file was read: not read")
    lines.append("corpus rows as read: %d" % corpus["row_count"])
    lines.append("declared mode: %s" % req.declared_mode)
    lines.append("effective mode: %s" % attestations["effective_mode"])
    lines.append("triggers fired: %s" % (", ".join(attestations["triggers"]) if attestations["triggers"] else "none"))
    lines.append("gate amendment run: %s" % ("yes" if attestations["gate_run"] else "no"))
    primary = attestations["primary"]
    lines.append("attested tier: %s" % primary["tier"])
    lines.append("attested context: %s" % primary["context"])
    if attestations["effective_context"] != primary["context"]:
        lines.append("effective context: %s" % attestations["effective_context"])
    for key in CHANGE_KEYS:
        lines.append("%s: %s" % (CHANGE_LABEL_FOR_KEY[key], primary[key]))
    lines.append("attester: %s" % attestations["attester"])
    second = attestations["second"]
    if second is not None:
        lines.append("second attester: %s" % second["seat"])
        lines.append("second attested tier: %s" % second["tier"])
        lines.append("second attested context: %s" % second["context"])
        for key in CHANGE_KEYS:
            lines.append("second %s: %s" % (CHANGE_LABEL_FOR_KEY[key], second[key]))
        for d in attestations["disagreements"]:
            lines.append("attestation disagreement: %s, %s, %s, attesters %s and %s"
                         % (d["field"], d["primary_value"], d["second_value"],
                            attestations["attester"], second["seat"]))
    if declaration["declarer"] == req.author:
        lines.append("role overlap: %s is both the declarer and the wording author" % declaration["declarer"])
    if req.runner == req.author:
        lines.append("role overlap: the runner %s is also the wording author" % req.runner)
    lines.extend(readback_lines(declaration, amendment_items, selection, corpus))
    lines.extend(self_test_section_lines(probes))
    lines.append("re-ruling matches")
    if not record["candidates"] and not record["matches"] and not record["unverified"]:
        lines.append("no re-ruling was claimed")
    else:
        for cand in record["candidates"]:
            lines.append(candidate_line_from_obj(cand))
        matched_ids = set()
        for m in record["matches"]:
            row = corpus["by_id"][m["corpus_id"]]
            lines.append("match: %s, %s, %s, %s, status as read %s, confirming judge %s, incident: %s"
                         % (m["item"], m["corpus_id"], m["queue_item"], m["ruling_date"],
                            m["status_as_read"], m["confirming_judge"], row["incident"]))
            matched_ids.add(m["corpus_id"])
        if record["matches"]:
            lines.append(EXCEPTION_LINE)
        for u in record["unverified"]:
            lines.append("unverified excuse: %s, %s, %s, %s"
                         % (u["item"], u["corpus_id"], u["queue_item"] if u["queue_item"] else "none claimed in block", u["reason"]))
        lines.append("matches: %d, unverified excuses: %d" % (len(record["matches"]), len(record["unverified"])))
        if record["standing_fact"]:
            lines.append(QUEUE_STANDING_LINE)
    lines.append("checked rows")
    for item_out in record["items"]:
        for v in item_out["verdicts"]:
            lines.extend(filled_section_lines(corpus, item_out["label"], v))
    lines.append("item outcomes")
    for item_out in record["items"]:
        label = item_out["label"]
        if item_out["overridden"]:
            lines.append("item %s: %s (no touch assertion overridden)" % (label, item_out["outcome"]))
        elif item_out["no_touch"]:
            lines.append("item %s: %s (no touch item, confirming seat %s)" % (label, item_out["outcome"], declaration["confirmer"]))
        else:
            lines.append("item %s: %s" % (label, item_out["outcome"]))
    lines.append("counts")
    counts = record["counts"]
    lines.append("checks run: %d" % counts["checks_run"])
    lines.append("passed: %d" % counts["passed"])
    lines.append("failed: %d" % counts["failed"])
    lines.append("failed excused: %d" % counts["failed_excused"])
    lines.append("failed unexcused: %d" % counts["failed_unexcused"])
    lines.append("unjudgeable: %d" % counts["unjudgeable"])
    lines.append("missing: %d" % counts["missing"])
    lines.append("limits")
    lines.extend(limit_lines(corpus, selection, record))
    lines.append("reader designate: %s" % reader_designate_line(req.reader))
    lines.append("auditor oversight: %s" % AUDITOR_OVERSIGHT_LINE)
    lines.append("glossary")
    lines.extend(GLOSSARY_LINES)
    return join_text(lines)


def candidate_line_from_obj(cand):
    return ("candidate for %s: %s, status as read %s, heading: %s, entry lines %d to %d"
            % (cand["corpus_id"], cand["queue_item"], cand["status_as_read"],
               cand["heading"], cand["first_line"], cand["last_line"]))


def filled_section_lines(corpus, label, v):
    row = corpus["by_id"][v["corpus_id"]]
    lines = ["row %s for item %s" % (v["corpus_id"], label)]
    if v["word"] == "FAIL":
        lines.append("incident: %s" % row["incident"])
    lines.append("pass procedure: %s" % row["proc"])
    if v.get("missing"):
        lines.append("verdict: missing")
        lines.append("judge: absent")
        lines.append("clause applied: absent")
        lines.append("reason: absent")
    else:
        lines.append("verdict: %s" % v["word"])
        lines.append("judge: %s" % v["judge"])
        lines.append("clause applied: %s" % v["clause"])
        lines.append("reason: %s" % v["reason"])
    if v["row_note"]:
        lines.append("row note: %s" % v["row_note"])
    trace = v["trace_excerpt"]
    if trace["word"] == "RE-RULED":
        lines.append("trace excerpt: RE-RULED, queue item %s" % trace["queue_item"])
    else:
        lines.append("trace excerpt: %s" % trace["word"])
    return lines


def finalise_json_text(req, corpus, declaration, selection, attestations, record, probes, fps):
    primary = attestations["primary"]
    second = attestations["second"]
    if second is None:
        second_obj = None
    else:
        second_obj = {
            "seat": second["seat"],
            "tier": second["tier"],
            "context": second["context"],
            "change_flags": {k: second[k] for k in CHANGE_KEYS},
            "disagreements": [
                {"field": d["field"], "primary_value": d["primary_value"], "second_value": d["second_value"]}
                for d in attestations["disagreements"]
            ],
        }
    items_json = []
    for item_out in record["items"]:
        verdicts_json = []
        for v in item_out["verdicts"]:
            obj = {
                "corpus_id": v["corpus_id"],
                "judge": v["judge"],
                "clause": v["clause"],
                "word": v["word"],
                "reason": v["reason"],
                "flagged": v["flagged"],
                "row_note": v["row_note"],
                "claim": v["claim"],
                "excused": v["excused"],
                "trace_excerpt": {"word": v["trace_excerpt"]["word"], "queue_item": v["trace_excerpt"]["queue_item"]},
            }
            if v.get("missing"):
                obj["missing"] = True
            verdicts_json.append(obj)
        items_json.append({
            "label": item_out["label"],
            "outcome": item_out["outcome"],
            "no_touch": item_out["no_touch"],
            "overridden": item_out["overridden"],
            "checked_ids": item_out["checked_ids"],
            "verdicts": verdicts_json,
        })
    if record["verdicts_state"] == "missing":
        verdicts_fp = "no verdicts file was read: missing"
    else:
        verdicts_fp = fps["verdicts"]
    if record["queue_read"]:
        queue_fp = record["queue_fp_value"]
        queue_path_value = req.queue_path
    else:
        queue_fp = None
        queue_path_value = req.queue_path if req.queue_supplied else None
    searched = selection["declared_all"] if attestations["effective_mode"] == "subset" else corpus["all_tokens"]
    data = {
        "tool": TOOL_NAME,
        "version": VERSION,
        "outcome": record["outcome"],
        "exit_status": record["exit_status"],
        "trace_word": TRACE_WORD[record["outcome"]],
        "runner": req.runner,
        "judge_of_record": req.judge,
        "panel_judges": list(req.panel),
        "wording_author": req.author,
        "ruler": req.ruler,
        "step_coordinator": req.coordinator,
        "reader_designate": req.reader,
        "declarer": declaration["declarer"],
        "confirming_seat": declaration["confirmer"],
        "fingerprints": {
            "corpus": fps["corpus"],
            "amendment": fps["amendment"],
            "declaration": fps["declaration"],
            "verdicts": verdicts_fp,
            "queue": queue_fp,
        },
        "corpus_row_count": corpus["row_count"],
        "paths": {
            "corpus": req.corpus_path,
            "amendment": req.amendment_path,
            "declaration": req.declaration_path,
            "verdicts": req.verdicts_path,
            "queue": queue_path_value,
        },
        "declared_mode": req.declared_mode,
        "effective_mode": attestations["effective_mode"],
        "triggers": list(attestations["triggers"]),
        "gate_amendment_run": attestations["gate_run"],
        "attestations": {
            "attester": attestations["attester"],
            "tier": primary["tier"],
            "context": primary["context"],
            "effective_context": attestations["effective_context"],
            "change_flags": {k: primary[k] for k in CHANGE_KEYS},
            "second_attester": second_obj,
        },
        "indexes_searched": sort_tokens(searched),
        "tokens_with_no_rows": sort_tokens(selection["tokens_with_no_rows"]),
        "checked_ids": list(selection["checked_union"]),
        "items": items_json,
        "re_ruling_candidates": [
            {"corpus_id": c["corpus_id"], "queue_item": c["queue_item"],
             "status_as_read": c["status_as_read"], "heading": c["heading"],
             "first_line": c["first_line"], "last_line": c["last_line"]}
            for c in record["candidates"]
        ],
        "re_ruling_matches": [
            {"item": m["item"], "corpus_id": m["corpus_id"], "queue_item": m["queue_item"],
             "ruling_date": m["ruling_date"], "status_as_read": m["status_as_read"],
             "confirming_judge": m["confirming_judge"]}
            for m in record["matches"]
        ],
        "unverified_excuses": [
            {"item": u["item"], "corpus_id": u["corpus_id"], "queue_item": u["queue_item"],
             "reason": u["reason"]}
            for u in record["unverified"]
        ],
        "blocked_items": [
            {"item": b["item"], "unexcused_fail_count": b["unexcused_fail_count"]}
            for b in record["blocked_items"]
        ],
        "counts": {
            "checks_run": record["counts"]["checks_run"],
            "passed": record["counts"]["passed"],
            "failed": record["counts"]["failed"],
            "failed_excused": record["counts"]["failed_excused"],
            "failed_unexcused": record["counts"]["failed_unexcused"],
            "unjudgeable": record["counts"]["unjudgeable"],
            "missing": record["counts"]["missing"],
        },
        "missing": [{"item": m["item"], "corpus_id": m["corpus_id"]} for m in record["missing"]],
        "self_test": {
            "probes": [{"name": p["name"], "result": p["result"]} for p in probes],
            "counted_separately": True,
        },
        "limits": limit_lines(corpus, selection, record),
        "reader_designate_line": reader_designate_line(req.reader),
        "auditor_oversight_line": AUDITOR_OVERSIGHT_LINE,
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def write_output(path, text):
    if os.path.exists(path):
        raise DeliveryFailure(path)
    try:
        with open(path, "x", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        raise DeliveryFailure(path)


def join_text(lines):
    return "\n".join(lines) + "\n"
# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def load_front_end(req):
    corpus_data = read_input_file(req.corpus_path, "corpus")
    corpus = parse_corpus(corpus_data, req.corpus_path)
    amendment_data = read_input_file(req.amendment_path, "amendment")
    amendment_items = parse_amendment(amendment_data, req.amendment_path)
    declaration_data = read_input_file(req.declaration_path, "declaration")
    amendment_fp = fingerprint(amendment_data)
    declaration = parse_declaration(declaration_data, req.declaration_path, amendment_items, amendment_fp)
    if declaration["declarer"] == req.author and declaration["confirmer"] == req.author:
        ie("IE-28", IE_WORDINGS["IE-28"] % declaration["confirmer"])
    attestations = build_attestations(req, declaration)
    selection = compute_selection(corpus, amendment_items, declaration, attestations)
    fps = {
        "corpus": fingerprint(corpus_data),
        "amendment": amendment_fp,
        "declaration": fingerprint(declaration_data),
    }
    return corpus, amendment_items, declaration, attestations, selection, fps


def run_worksheet(req, forced_failure):
    corpus, amendment_items, declaration, attestations, selection, fps = load_front_end(req)
    bars = compute_bars([req.judge], req)
    out_path = req.output_paths["--worksheet-out"]
    if bars:
        write_output(out_path, barred_report_text(req, bars, fps["corpus"], fps["amendment"], fps["declaration"]))
        return 6
    probes = run_self_test(forced_failure)
    if self_test_failed(probes):
        write_output(out_path, self_test_report_text(probes))
        return 8
    if selection["conflicts"]:
        write_output(out_path, declaration_conflict_report_text(declaration, selection, fps["amendment"], fps["declaration"]))
        return 7
    queue_state = read_queue(req.queue_path) if req.queue_supplied else None
    worksheet = worksheet_text(req, corpus, declaration, selection, attestations, probes,
                               fps["corpus"], fps["amendment"], fps["declaration"], queue_state, amendment_items)
    template = template_text(req, selection, attestations, fps["corpus"], fps["amendment"], fps["declaration"], amendment_items)
    write_output(out_path, worksheet)
    write_output(req.output_paths["--template-out"], template)
    return 10


def read_verdicts_state(req):
    """Returns (state, data) where state is missing, empty, or content."""
    path = req.verdicts_path
    if not os.path.exists(path):
        return "missing", None
    if os.path.isdir(path):
        ie("IE-05", IE_WORDINGS["IE-05"] % ("verdicts", path))
    try:
        measured = os.path.getsize(path)
    except OSError:
        ie("IE-05", IE_WORDINGS["IE-05"] % ("verdicts", path))
    if measured > BYTE_LIMIT:
        ie("IE-06", IE_WORDINGS["IE-06"] % (("verdicts",) + (measured, path)))
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        ie("IE-05", IE_WORDINGS["IE-05"] % ("verdicts", path))
    text = decode_input(data, "verdicts", path)
    if not verdicts_content_lines(text):
        return "empty", data
    return "content", data


def run_finalise(req, forced_failure):
    corpus, amendment_items, declaration, attestations, selection, fps = load_front_end(req)
    state, verdicts_data = read_verdicts_state(req)
    header = None
    verdicts = []
    if state == "content":
        text = verdicts_data.decode("utf-8")
        header, verdicts = parse_verdicts(text, corpus, selection, "finalise", [req.judge] + list(req.panel))
    probes = run_self_test(forced_failure)
    report_path = req.output_paths["--report-out"]
    if self_test_failed(probes):
        write_output(report_path, self_test_report_text(probes))
        return 8
    if selection["conflicts"]:
        write_output(report_path, declaration_conflict_report_text(declaration, selection, fps["amendment"], fps["declaration"]))
        return 7
    if state == "content":
        recomputed = {
            "amendment_fp": fps["amendment"],
            "corpus_fp": fps["corpus"],
            "declaration_fp": fps["declaration"],
            "declared_mode": req.declared_mode,
            "effective_mode": attestations["effective_mode"],
            "triggers": attestations["triggers"],
            "checked_ids": selection["checked_union"],
            "roster": [req.judge] + list(req.panel),
        }
        mismatch = binding_mismatch_name(header, recomputed)
        if mismatch is not None:
            ie("IE-38", IE_WORDINGS["IE-38"] % mismatch)
    judges_in_order = [req.judge]
    for v in verdicts:
        if v["judge"] not in judges_in_order:
            judges_in_order.append(v["judge"])
    roster_order = [req.judge] + list(req.panel)
    judges_in_order.sort(key=lambda j: roster_order.index(j) if j in roster_order else len(roster_order))
    bars = compute_bars(judges_in_order, req)
    if bars:
        write_output(report_path, barred_report_text(req, bars, fps["corpus"], fps["amendment"], fps["declaration"]))
        return 6
    fps_full = dict(fps)
    fps_full["verdicts"] = fingerprint(verdicts_data) if verdicts_data is not None else None
    record = build_finalise_record(req, corpus, declaration, selection, attestations, verdicts,
                                   probes, fps_full, state, amendment_items)
    text_report = finalise_text_report(req, corpus, declaration, selection, attestations, record,
                                       probes, fps_full, amendment_items)
    json_text = finalise_json_text(req, corpus, declaration, selection, attestations, record, probes, fps_full)
    write_output(report_path, text_report)
    write_output(req.output_paths["--results-out"], json_text)
    return record["exit_status"]


def run_remaining(req):
    corpus, amendment_items, declaration, attestations, selection, fps = load_front_end(req)
    path = req.verdicts_path
    if not os.path.exists(path):
        ie("IE-31", IE_WORDINGS["IE-31"] % path)
    state, verdicts_data = read_verdicts_state(req)
    header = None
    verdicts = []
    if state == "content":
        text = verdicts_data.decode("utf-8")
        header, verdicts = parse_verdicts(text, corpus, selection, "remaining", [req.judge] + list(req.panel))
    if state == "content":
        recomputed = {
            "amendment_fp": fps["amendment"],
            "corpus_fp": fps["corpus"],
            "declaration_fp": fps["declaration"],
            "declared_mode": req.declared_mode,
            "effective_mode": attestations["effective_mode"],
            "triggers": attestations["triggers"],
            "checked_ids": selection["checked_union"],
            "roster": [req.judge] + list(req.panel),
        }
        mismatch = binding_mismatch_name(header, recomputed)
        if mismatch is not None:
            ie("IE-38", IE_WORDINGS["IE-38"] % mismatch)
    out_path = req.output_paths["--remaining-out"]
    if selection["conflicts"]:
        write_output(out_path, declaration_conflict_report_text(declaration, selection, fps["amendment"], fps["declaration"]))
        return 7
    present = {(v["label"], v["id"]) for v in verdicts if not v.get("untouched")}
    missing_pairs = []
    total = 0
    for item in amendment_items:
        label = item["label"]
        for cid in selection["per_item"][label]["checked_ids"]:
            total += 1
            if (label, cid) not in present:
                missing_pairs.append((label, cid))
    text = remaining_report_text(req, selection, attestations, missing_pairs, total, amendment_items)
    write_output(out_path, text)
    return 9


def main(argv=None, forced_failure=None):
    if argv is None:
        argv = sys.argv[1:]
    try:
        values = parse_arguments(list(argv))
    except UsageFailure as exc:
        sys.stderr.write("usage error: %s\n" % exc)
        sys.stderr.write(USAGE_SUMMARY + "\n")
        return 2
    try:
        check_required_arguments(values)
        req = RunRequest(values)
        validate_paths(req)
        if req.form == "worksheet":
            return run_worksheet(req, forced_failure)
        if req.form == "finalise":
            return run_finalise(req, forced_failure)
        return run_remaining(req)
    except InputFailure as exc:
        sys.stderr.write("input error: %s\n" % SENTENCES["input error"])
        sys.stderr.write("input error %s: %s\n" % (exc.ie_id, exc.wording))
        return 2
    except DeliveryFailure as exc:
        sys.stderr.write("delivery failure: the output at %s could not be written\n" % exc.path)
        return 2


if __name__ == "__main__":
    sys.exit(main())
