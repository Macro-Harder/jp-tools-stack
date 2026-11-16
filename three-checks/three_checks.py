import codecs
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime
from pathlib import Path

TOOL_NAME = "three-checks"
VERSION = "1.0.0"
BUNDLE_BYTE_LIMIT = 2000000
ARTIFACT_BYTE_LIMIT = 2000000
SECTION_ORDER = ["layout", "roster", "links", "spawn_records", "identities", "claim", "push_record", "previous_stage", "ledger_entries"]
REQUIRED_SECTIONS = ["layout", "roster", "links", "spawn_records", "identities", "claim"]
STRENGTH_LINE = "strength: the checks count at the closure record L2 grade and no higher, and only where the origin tests passed; the seat association rests on the roster record."
SCOPE_PARAGRAPH = "This record attests that the three checks of R-80 were run by the named verifier, who is not the performer, not the coordinator, and not the commissioner, over the records in the named bundle, and that every check passed. Provenance attests how the stage artifacts were produced; it is not evidence of their quality. The roster authenticity rests on spawn records captured by the runtime and on the roster record for the seat association; the push record rests on verification through the API at bundle assembly. No strength above grade L2 is claimed."
USAGE_LINE = "usage: three-checks BUNDLE REPORT RESULTS CLOSURE --verifier IDENTITY"
EVALUATED_KINDS = ["exists", "sha256_equals", "contains_line", "first_line_equals", "line_count_at_least", "line_count_at_most", "byte_size_at_most"]
RECORD_KINDS = ["roster", "push", "links", "claim", "ledger"]
RECORD_SOURCES_BY_KIND = {
    "roster": ["runtime-spawn-records", "self-reported-file"],
    "push": ["api-verification", "self-reported-file"],
    "links": ["stage-record", "self-reported-file"],
    "claim": ["stage-record", "self-reported-file"],
    "ledger": ["stage-record", "self-reported-file"],
}
PROPERTY_FIELDS_BY_KIND = {
    "exists": [],
    "sha256_equals": ["sha256"],
    "contains_line": ["line"],
    "first_line_equals": ["line"],
    "line_count_at_least": ["count"],
    "line_count_at_most": ["count"],
    "byte_size_at_most": ["count"],
}
EXPECTED_TEXT = {
    "ABSENT-SECTION": "the required section {subject} is present",
    "AUTH-NO-SPAWN": "exactly one spawn record for the performer identity",
    "AUTH-NO-ROSTER": "a roster entry authorising the seat for the performer at or before the step run time",
    "AUTH-STEP-TIME": "the spawn record creation time is at or before the step run time and both times parse",
    "AUTH-LATE-RECORD": "a roster entry recorded at or before the step run time",
    "AUTH-NO-REPUB": "a republication for the seat at or before the step run time",
    "AUTH-NO-PUSH": "a push record where a push link is in play",
    "AUTH-ORIGIN": "the record kind passes its origin test",
    "LINK-NO-STEP": "the link step_id names a layout step",
    "CHAIN-JOIN": "the outputs of the earlier step match the inputs of the later step on every name",
    "CHAIN-BOUNDARY": "the claim predecessor inputs match the previous stage outputs on every name",
    "COMP-NO-LINK": "at least one matching link",
    "COMP-RECONSTRUCTED": "a link produced at or before the recorded completion time and at or after its run time, with a production time present",
    "COMP-ARTIFACT": "the artifact file stands at its path, within the size limit, with the stated digest, and named by a presented link with the stated digest",
    "COMP-PROPERTY": "the stated property holds for the artifact file",
    "COMP-UNSUPPORTED-PROPERTY": "the stated property kind is one of the seven evaluated kinds",
    "COMP-LEDGER": "a path ledger entry for the claimed element",
    "LINK-PREDICATE": "the link predicate_type equals the layout step predicate_type",
    "ANOM-MULTI-LINK": "one matching link for the step",
}
CURE_TEXT = {
    "AUTH-NO-SPAWN": "supply exactly one spawn record for the performer identity in the export.",
    "AUTH-NO-ROSTER": "supply a roster entry authorising the seat for the performer with a parseable recorded_at at or before the step run time.",
    "AUTH-STEP-TIME": "supply a spawn record whose created_at parses and is at or before the step run time, and, for the ran_at variant, supply a link whose ran_at parses.",
    "AUTH-LATE-RECORD": "supply a roster entry for the seat and performer recorded at or before the step run time.",
    "AUTH-NO-REPUB": "supply a republication for the seat with a parseable republished_at at or before the step run time.",
    "AUTH-NO-PUSH": "supply the push_record section for the push link in play.",
    "AUTH-ORIGIN": "supply the record kind from its required origin, runtime-spawn-records for roster or api-verification for push, or correct the differing push field.",
    "LINK-NO-STEP": "supply the step in the layout, or withdraw the link.",
    "CHAIN-JOIN": "supply matching links whose outputs and inputs agree on every name, or correct the differing material entry.",
    "CHAIN-BOUNDARY": "supply previous stage outputs matching the predecessor inputs on every name, or withdraw the predecessor inputs claim.",
    "COMP-NO-LINK": "supply a genuine link for the step, or withdraw the step from the layout.",
    "COMP-RECONSTRUCTED": "supply a genuine link produced within the step run and completion times, with its completion time recorded.",
    "COMP-ARTIFACT": "supply the artifact file at its path with the stated digest, or correct the stated digest and the link naming it.",
    "COMP-PROPERTY": "supply an artifact file for which the stated property holds, or correct the stated property.",
    "COMP-UNSUPPORTED-PROPERTY": "state the property in one of the seven evaluated kinds, or withdraw the property.",
    "COMP-LEDGER": "supply the path ledger entry for the claimed element, or withdraw the claim for that element.",
    "LINK-PREDICATE": "supply a link whose predicate_type equals the layout step predicate_type.",
    "ANOM-MULTI-LINK": "no cure is required; the anomaly is reported and the run is not failed by it.",
}
CHECK_OF_CODE = {
    "ABSENT-SECTION": "stage",
    "AUTH-NO-SPAWN": "authenticity",
    "AUTH-NO-ROSTER": "authenticity",
    "AUTH-STEP-TIME": "authenticity",
    "AUTH-LATE-RECORD": "authenticity",
    "AUTH-NO-REPUB": "authenticity",
    "AUTH-NO-PUSH": "authenticity",
    "AUTH-ORIGIN": "authenticity",
    "LINK-NO-STEP": "authenticity",
    "CHAIN-JOIN": "chain",
    "CHAIN-BOUNDARY": "chain",
    "COMP-NO-LINK": "completeness",
    "COMP-RECONSTRUCTED": "completeness",
    "COMP-ARTIFACT": "completeness",
    "COMP-PROPERTY": "completeness",
    "COMP-UNSUPPORTED-PROPERTY": "completeness",
    "COMP-LEDGER": "completeness",
    "LINK-PREDICATE": "completeness",
    "ANOM-MULTI-LINK": "completeness",
}


class _Absent:
    def __repr__(self):
        return "ABSENT"


ABSENT = _Absent()

TIME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?Z$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_time_value(raw):
    match = TIME_RE.match(raw)
    instant = None
    if match:
        year, month, day, hour, minute, second = (int(match.group(i)) for i in range(1, 7))
        frac = match.group(7) or ""
        try:
            base = datetime(year, month, day, hour, minute, second)
            instant = (base, frac.ljust(18, "0")[:18])
        except ValueError:
            instant = None
    return {"raw": raw, "parses": instant is not None, "instant": instant}


def digest_value(raw):
    return {"raw": raw, "in_form": bool(DIGEST_RE.match(raw))}


def render_name(name):
    return json.dumps(name, ensure_ascii=False)[1:-1]


def render_value(value):
    if not isinstance(value, str):
        value = str(value)
    for char in value:
        code = ord(char)
        if code < 0x20 or code == 0x7F:
            return json.dumps(value, ensure_ascii=True)
    if _has_unpaired_surrogate(value):
        return json.dumps(value, ensure_ascii=True)
    return value


def resolve_quietly(path):
    try:
        return str(path.resolve())
    except (OSError, ValueError, RuntimeError):
        return str(path)


def file_identity(path):
    try:
        info = os.stat(path)
    except (OSError, ValueError):
        return None
    return (info.st_dev, info.st_ino)


def render_path(path):
    parts = []
    for component in path:
        if isinstance(component, int):
            parts.append(str(component))
        else:
            parts.append(render_name(component))
    return ".".join(parts)


# Argument parsing


def parse_arguments(argv):
    names = ["BUNDLE", "REPORT", "RESULTS", "CLOSURE"]
    positionals = []
    index = 0
    while index < len(argv) and len(positionals) < 4:
        token = argv[index]
        if token.startswith("--"):
            break
        positionals.append(token)
        index += 1
    if len(positionals) < 4:
        if index < len(argv) and argv[index].startswith("--") and argv[index] != "--verifier":
            return None, "unknown flag " + render_value(argv[index])
        return None, "missing argument " + names[len(positionals)]
    rest = argv[index:]
    if not rest:
        return None, "missing value for --verifier"
    if rest[0] != "--verifier":
        if rest[0].startswith("--"):
            return None, "unknown flag " + render_value(rest[0])
        return None, "unexpected argument " + render_value(rest[0])
    if len(rest) == 1:
        return None, "missing value for --verifier"
    verifier = rest[1]
    if len(rest) > 2:
        return None, "unexpected argument " + render_value(rest[2])
    return (positionals[0], positionals[1], positionals[2], positionals[3], verifier), None


def write_stderr(text):
    try:
        data = text.encode("utf-8", "backslashreplace")
        offset = 0
        while offset < len(data):
            written = os.write(2, data[offset:])
            if written <= 0:
                raise OSError("short write on standard error")
            offset += written
    except OSError:
        try:
            devnull = os.open("/dev/null", os.O_WRONLY)
            try:
                os.dup2(devnull, 2)
            finally:
                if devnull != 2:
                    os.close(devnull)
        except OSError:
            pass


def usage_failure(text):
    write_stderr("three-checks: usage error: " + text + "\n")
    write_stderr(USAGE_LINE + "\n")
    return 2


def resolved(path_text):
    return Path(path_text).resolve()


# Reading gates and strict parsing


class _InvalidJSON(ValueError):
    pass


_SURROGATE_RE = re.compile("[\ud800-\udfff]")


def _has_unpaired_surrogate(text):
    if _SURROGATE_RE.search(text) is None:
        return False
    index = 0
    while index < len(text):
        code = ord(text[index])
        if 0xD800 <= code <= 0xDBFF:
            if index + 1 < len(text) and 0xDC00 <= ord(text[index + 1]) <= 0xDFFF:
                index += 2
                continue
            return True
        if 0xDC00 <= code <= 0xDFFF:
            return True
        index += 1
    return False


def _scan_strings(value):
    if isinstance(value, str):
        if _has_unpaired_surrogate(value):
            raise _InvalidJSON("unpaired surrogate")
    elif isinstance(value, list):
        for item in value:
            _scan_strings(item)
    elif isinstance(value, _Obj):
        return


class _Obj(dict):
    pass


_hook_state = {"seq": 0, "objects": []}


def _object_pairs_hook(pairs):
    obj = _Obj()
    seen = {}
    local_dups = []
    for position, (key, value) in enumerate(pairs):
        if _has_unpaired_surrogate(key):
            raise _InvalidJSON("unpaired surrogate in field name")
        _scan_strings(value)
        if key in seen:
            local_dups.append((key, position))
        else:
            seen[key] = value
            obj[key] = value
    obj.all_pairs = pairs
    obj.local_dups = local_dups
    obj.close_seq = _hook_state["seq"]
    _hook_state["seq"] += 1
    _hook_state["objects"].append(obj)
    return obj


def _reject_constant(token):
    raise ValueError("invalid constant " + token)


def collect_duplicates(top):
    records = []

    def walk(value, path):
        if isinstance(value, _Obj):
            for key, position in value.local_dups:
                records.append((value.close_seq, position, path + (key,)))
            for key, item in value.all_pairs:
                walk(item, path + (key,))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                walk(item, path + (idx,))

    walk(top, ())
    records.sort(key=lambda record: (record[0], record[1]))
    return [record[2] for record in records]


def read_and_parse(bundle_path):
    try:
        bundle_stat = os.stat(bundle_path)
    except (OSError, ValueError):
        return None, None, None, "cannot read the bundle file"
    if not stat.S_ISREG(bundle_stat.st_mode):
        return None, None, None, "cannot read the bundle file"
    try:
        with open(bundle_path, "rb") as handle:
            data = handle.read(BUNDLE_BYTE_LIMIT + 1)
    except (OSError, ValueError):
        return None, None, None, "cannot read the bundle file"
    if len(data) > BUNDLE_BYTE_LIMIT:
        return None, None, None, "the bundle file is %d bytes, over the limit of %d bytes" % (len(data), BUNDLE_BYTE_LIMIT)
    if data.startswith(b"\xef\xbb\xbf"):
        return None, None, None, "the bundle file is not UTF-8 text without a byte order mark"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, None, None, "the bundle file is not UTF-8 text without a byte order mark"
    _hook_state["seq"] = 0
    _hook_state["objects"] = []
    try:
        parsed = json.loads(text, object_pairs_hook=_object_pairs_hook, parse_constant=_reject_constant)
        _scan_strings(parsed)
        if isinstance(parsed, list):
            for item in parsed:
                _scan_strings(item)
        if not isinstance(parsed, dict):
            return None, None, None, "the bundle top level is not an object"
        dup_paths = collect_duplicates(parsed)
    except (ValueError, RecursionError):
        return None, None, None, "the bundle file is not valid JSON"
    digest = hashlib.sha256(data).hexdigest()
    return parsed, dup_paths, digest, None


# Field validation


class Validator:
    def __init__(self, dup_paths, bundle_dir):
        self.dup_paths = set(dup_paths)
        self.section_errors = []
        self.unknown_errors = []
        self._emitted = set()
        self._seq = 0

    def is_dupped(self, path):
        for end in range(1, len(path) + 1):
            if path[:end] in self.dup_paths:
                return True
        return False

    def field_error(self, section_index, path, text):
        if path in self._emitted:
            return
        self._emitted.add(path)
        self._seq += 1
        self.section_errors.append((section_index, self._seq, text))

    def unknown_error(self, path):
        self.unknown_errors.append((render_path(path), "unknown field " + render_path(path)))

    def ordered_lines(self, dup_paths):
        lines = []
        for path in dup_paths:
            lines.append("duplicate field " + render_path(path))
        for _sec, _seq, text in sorted(self.section_errors, key=lambda item: (item[0], item[1])):
            lines.append(text)
        for _rendered, text in sorted(self.unknown_errors, key=lambda item: item[0]):
            lines.append(text)
        return lines

    def has_errors(self, dup_paths):
        return bool(dup_paths or self.section_errors or self.unknown_errors)

    def unknown_fields(self, obj, path, allowed):
        for key in obj:
            if key not in allowed:
                if not self.is_dupped(path + (key,)):
                    self.unknown_error(path + (key,))

    def check_str(self, obj, name, path, sec, required=True, allow_null=False):
        field_path = path + (name,)
        if self.is_dupped(field_path):
            return None
        if name not in obj:
            if required:
                self.field_error(sec, field_path, render_path(field_path) + " is missing")
            return None
        value = obj[name]
        if value is None and allow_null:
            return None
        if not isinstance(value, str):
            self.field_error(sec, field_path, render_path(field_path) + " must be string")
            return None
        return value

    def check_int(self, obj, name, path, sec, required=True, minimum=None):
        field_path = path + (name,)
        if self.is_dupped(field_path):
            return None
        if name not in obj:
            if required:
                self.field_error(sec, field_path, render_path(field_path) + " is missing")
            return None
        value = obj[name]
        if type(value) is not int:
            self.field_error(sec, field_path, render_path(field_path) + " must be integer")
            return None
        if minimum is not None and value < minimum:
            self.field_error(sec, field_path, render_path(field_path) + " is outside its allowed set")
            return None
        return value

    def check_list(self, obj, name, path, sec, required=True):
        field_path = path + (name,)
        if self.is_dupped(field_path):
            return None
        if name not in obj:
            if required:
                self.field_error(sec, field_path, render_path(field_path) + " is missing")
            return None
        value = obj[name]
        if not isinstance(value, list):
            self.field_error(sec, field_path, render_path(field_path) + " must be list")
            return None
        return value

    def check_obj_field(self, obj, name, path, sec, required=True, allow_null=False):
        field_path = path + (name,)
        if self.is_dupped(field_path):
            return None
        if name not in obj:
            if required:
                self.field_error(sec, field_path, render_path(field_path) + " is missing")
            return None
        value = obj[name]
        if value is None and allow_null:
            return None
        if not isinstance(value, dict):
            self.field_error(sec, field_path, render_path(field_path) + " must be object")
            return None
        return value

    def check_allowed(self, obj, name, path, sec, allowed, required=True):
        value = self.check_str(obj, name, path, sec, required=required)
        if value is not None and value not in allowed:
            field_path = path + (name,)
            self.field_error(sec, field_path, render_path(field_path) + " is outside its allowed set")
            return None
        return value

    def check_section_obj(self, top, name, sec):
        if name not in top:
            return None
        if self.is_dupped((name,)):
            return None
        value = top[name]
        if not isinstance(value, dict):
            self.field_error(sec, (name,), name + " must be object")
            return None
        return value

    def check_section_list(self, top, name, sec):
        if name not in top:
            return None
        if self.is_dupped((name,)):
            return None
        value = top[name]
        if not isinstance(value, list):
            self.field_error(sec, (name,), name + " must be list")
            return None
        return value

    def check_material_list(self, value, path, sec):
        if value is None:
            return
        for idx, entry in enumerate(value):
            entry_path = path + (idx,)
            if self.is_dupped(entry_path):
                continue
            if not isinstance(entry, dict):
                self.field_error(sec, entry_path, render_path(entry_path) + " must be object")
                continue
            self.unknown_fields(entry, entry_path, ["name", "sha256"])
            self.check_str(entry, "name", entry_path, sec)
            self.check_str(entry, "sha256", entry_path, sec)

    def check_str_list(self, obj, name, path, sec):
        value = self.check_list(obj, name, path, sec)
        if value is None:
            return None
        for idx, item in enumerate(value):
            item_path = path + (name, idx)
            if self.is_dupped(item_path):
                continue
            if not isinstance(item, str):
                self.field_error(sec, item_path, render_path(item_path) + " must be string")
        return value


def validate_bundle(top, dup_paths, bundle_dir):
    v = Validator(dup_paths, bundle_dir)
    for key in top:
        if key not in SECTION_ORDER and not v.is_dupped((key,)):
            v.unknown_error((key,))

    layout = v.check_section_obj(top, "layout", 0)
    if layout is not None:
        path = ("layout",)
        v.unknown_fields(layout, path, ["stage_id", "steps", "required_artifacts", "record_sources"])
        v.check_str(layout, "stage_id", path, 0)
        steps = v.check_list(layout, "steps", path, 0)
        if steps is not None:
            if len(steps) == 0:
                v.field_error(0, path + ("steps",), "layout.steps is outside its allowed set")
            step_ids = []
            for idx, entry in enumerate(steps):
                entry_path = path + ("steps", idx)
                if v.is_dupped(entry_path):
                    continue
                if not isinstance(entry, dict):
                    v.field_error(0, entry_path, render_path(entry_path) + " must be object")
                    continue
                v.unknown_fields(entry, entry_path, ["step_id", "seat", "predicate_type"])
                step_id = v.check_str(entry, "step_id", entry_path, 0)
                v.check_str(entry, "seat", entry_path, 0)
                v.check_str(entry, "predicate_type", entry_path, 0)
                if isinstance(step_id, str):
                    step_ids.append(step_id)
            if len(step_ids) != len(set(step_ids)):
                v.field_error(0, path + ("steps",), "layout.steps is outside its allowed set")
        artifacts = v.check_list(layout, "required_artifacts", path, 0)
        if artifacts is not None:
            artifact_ids = []
            artifact_paths = []
            for idx, entry in enumerate(artifacts):
                entry_path = path + ("required_artifacts", idx)
                if v.is_dupped(entry_path):
                    continue
                if not isinstance(entry, dict):
                    v.field_error(0, entry_path, render_path(entry_path) + " must be object")
                    continue
                v.unknown_fields(entry, entry_path, ["artifact_id", "path", "sha256", "properties"])
                artifact_id = v.check_str(entry, "artifact_id", entry_path, 0)
                artifact_path = v.check_str(entry, "path", entry_path, 0)
                v.check_str(entry, "sha256", entry_path, 0)
                properties = v.check_list(entry, "properties", entry_path, 0)
                if isinstance(artifact_id, str):
                    artifact_ids.append(artifact_id)
                if isinstance(artifact_path, str):
                    supplied = Path(artifact_path)
                    if not supplied.is_absolute():
                        supplied = bundle_dir / supplied
                    artifact_paths.append(resolve_quietly(supplied))
                if properties is not None:
                    for p_idx, prop in enumerate(properties):
                        prop_path = entry_path + ("properties", p_idx)
                        if v.is_dupped(prop_path):
                            continue
                        if not isinstance(prop, dict):
                            v.field_error(0, prop_path, render_path(prop_path) + " must be object")
                            continue
                        v.unknown_fields(prop, prop_path, ["kind", "line", "count", "sha256"])
                        kind = v.check_str(prop, "kind", prop_path, 0)
                        if "line" in prop:
                            v.check_str(prop, "line", prop_path, 0, required=False)
                        if "count" in prop:
                            v.check_int(prop, "count", prop_path, 0, required=False, minimum=0)
                        if "sha256" in prop:
                            v.check_str(prop, "sha256", prop_path, 0, required=False)
                        if isinstance(kind, str) and kind in PROPERTY_FIELDS_BY_KIND:
                            carried = PROPERTY_FIELDS_BY_KIND[kind]
                            for field_name in ("line", "count", "sha256"):
                                field_path = prop_path + (field_name,)
                                if field_name in carried:
                                    if field_name not in prop and not v.is_dupped(field_path):
                                        v.field_error(0, field_path, render_path(field_path) + " is missing")
                                else:
                                    if field_name in prop and not v.is_dupped(field_path):
                                        v.field_error(0, field_path, render_path(field_path) + " is outside its allowed set")
            if len(artifact_ids) != len(set(artifact_ids)) or len(artifact_paths) != len(set(artifact_paths)):
                v.field_error(0, path + ("required_artifacts",), "layout.required_artifacts is outside its allowed set")
        sources = v.check_list(layout, "record_sources", path, 0)
        if sources is not None:
            for idx, entry in enumerate(sources):
                entry_path = path + ("record_sources", idx)
                if v.is_dupped(entry_path):
                    continue
                if not isinstance(entry, dict):
                    v.field_error(0, entry_path, render_path(entry_path) + " must be object")
                    continue
                v.unknown_fields(entry, entry_path, ["record_kind", "source"])
                kind = v.check_allowed(entry, "record_kind", entry_path, 0, RECORD_KINDS)
                if kind is not None:
                    v.check_allowed(entry, "source", entry_path, 0, RECORD_SOURCES_BY_KIND[kind])
                elif "record_kind" in entry and isinstance(entry.get("record_kind"), str):
                    pass
                else:
                    if "source" not in entry and not v.is_dupped(entry_path + ("record_kind",)):
                        v.field_error(0, entry_path + ("source",), render_path(entry_path + ("source",)) + " is missing")

    roster = v.check_section_obj(top, "roster", 1)
    if roster is not None:
        path = ("roster",)
        v.unknown_fields(roster, path, ["entries", "republications"])
        entries = v.check_list(roster, "entries", path, 1)
        if entries is not None:
            for idx, entry in enumerate(entries):
                entry_path = path + ("entries", idx)
                if v.is_dupped(entry_path):
                    continue
                if not isinstance(entry, dict):
                    v.field_error(1, entry_path, render_path(entry_path) + " must be object")
                    continue
                v.unknown_fields(entry, entry_path, ["seat", "agent_id", "recorded_at", "origin"])
                v.check_str(entry, "seat", entry_path, 1)
                v.check_str(entry, "agent_id", entry_path, 1)
                v.check_str(entry, "recorded_at", entry_path, 1)
                v.check_allowed(entry, "origin", entry_path, 1, ["layout", "addition"])
        republications = v.check_list(roster, "republications", path, 1)
        if republications is not None:
            for idx, entry in enumerate(republications):
                entry_path = path + ("republications", idx)
                if v.is_dupped(entry_path):
                    continue
                if not isinstance(entry, dict):
                    v.field_error(1, entry_path, render_path(entry_path) + " must be object")
                    continue
                v.unknown_fields(entry, entry_path, ["seat", "republished_at"])
                v.check_str(entry, "seat", entry_path, 1)
                v.check_str(entry, "republished_at", entry_path, 1)

    links = v.check_section_list(top, "links", 2)
    if links is not None:
        path = ("links",)
        for idx, entry in enumerate(links):
            entry_path = path + (idx,)
            if v.is_dupped(entry_path):
                continue
            if not isinstance(entry, dict):
                v.field_error(2, entry_path, render_path(entry_path) + " must be object")
                continue
            v.unknown_fields(entry, entry_path, ["step_id", "predicate_type", "performer_spawn_id", "builder", "produced_at", "ran_at", "inputs", "outputs", "subject_artifacts"])
            v.check_str(entry, "step_id", entry_path, 2)
            v.check_str(entry, "predicate_type", entry_path, 2)
            v.check_str(entry, "performer_spawn_id", entry_path, 2)
            v.check_str(entry, "builder", entry_path, 2)
            if "produced_at" in entry:
                v.check_str(entry, "produced_at", entry_path, 2, required=False)
            v.check_str(entry, "ran_at", entry_path, 2)
            inputs = v.check_list(entry, "inputs", entry_path, 2)
            v.check_material_list(inputs, entry_path + ("inputs",), 2)
            outputs = v.check_list(entry, "outputs", entry_path, 2)
            v.check_material_list(outputs, entry_path + ("outputs",), 2)
            subjects = v.check_list(entry, "subject_artifacts", entry_path, 2)
            if subjects is not None:
                for s_idx, subject in enumerate(subjects):
                    subject_path = entry_path + ("subject_artifacts", s_idx)
                    if v.is_dupped(subject_path):
                        continue
                    if not isinstance(subject, dict):
                        v.field_error(2, subject_path, render_path(subject_path) + " must be object")
                        continue
                    v.unknown_fields(subject, subject_path, ["artifact_id", "sha256"])
                    v.check_str(subject, "artifact_id", subject_path, 2)
                    v.check_str(subject, "sha256", subject_path, 2)

    spawn = v.check_section_obj(top, "spawn_records", 3)
    if spawn is not None:
        path = ("spawn_records",)
        v.unknown_fields(spawn, path, ["exporter", "exported_at", "source_database", "scoping", "records"])
        v.check_str(spawn, "exporter", path, 3)
        v.check_str(spawn, "exported_at", path, 3)
        v.check_str(spawn, "source_database", path, 3)
        scoping = v.check_obj_field(spawn, "scoping", path, 3)
        if scoping is not None:
            scoping_path = path + ("scoping",)
            v.unknown_fields(scoping, scoping_path, ["method", "detail"])
            v.check_allowed(scoping, "method", scoping_path, 3, ["identity_list", "parent_subtree", "time_window"])
            v.check_str(scoping, "detail", scoping_path, 3)
        records = v.check_list(spawn, "records", path, 3)
        if records is not None:
            for idx, entry in enumerate(records):
                entry_path = path + ("records", idx)
                if v.is_dupped(entry_path):
                    continue
                if not isinstance(entry, dict):
                    v.field_error(3, entry_path, render_path(entry_path) + " must be object")
                    continue
                v.unknown_fields(entry, entry_path, ["agent_id", "parent_agent_id", "depth", "kind", "agent_type", "session_id", "created_at"])
                v.check_str(entry, "agent_id", entry_path, 3)
                v.check_str(entry, "parent_agent_id", entry_path, 3)
                v.check_int(entry, "depth", entry_path, 3, minimum=0)
                v.check_str(entry, "kind", entry_path, 3)
                v.check_str(entry, "agent_type", entry_path, 3, allow_null=True)
                v.check_str(entry, "session_id", entry_path, 3)
                v.check_str(entry, "created_at", entry_path, 3)

    identities = v.check_section_obj(top, "identities", 4)
    if identities is not None:
        path = ("identities",)
        v.unknown_fields(identities, path, ["coordinator", "commissioner_stage", "commissioner_work"])
        v.check_str(identities, "coordinator", path, 4)
        v.check_str(identities, "commissioner_stage", path, 4)
        v.check_str(identities, "commissioner_work", path, 4)

    claim = v.check_section_obj(top, "claim", 5)
    if claim is not None:
        path = ("claim",)
        v.unknown_fields(claim, path, ["stage_id", "steps_claimed", "step_completions", "gate_context", "push_link", "predecessor_inputs", "ledger_claims"])
        claim_stage = v.check_str(claim, "stage_id", path, 5)
        if isinstance(claim_stage, str) and layout is not None and isinstance(layout.get("stage_id"), str):
            if claim_stage != layout["stage_id"] and not v.is_dupped(path + ("stage_id",)):
                v.field_error(5, path + ("stage_id",), "claim.stage_id does not equal layout.stage_id")
        claimed = v.check_str_list(claim, "steps_claimed", path, 5)
        if claimed is not None and all(isinstance(item, str) for item in claimed):
            if len(claimed) != len(set(claimed)):
                v.field_error(5, path + ("steps_claimed",), "claim.steps_claimed is outside its allowed set")
        completions = v.check_list(claim, "step_completions", path, 5)
        if completions is not None:
            completion_steps = []
            for idx, entry in enumerate(completions):
                entry_path = path + ("step_completions", idx)
                if v.is_dupped(entry_path):
                    continue
                if not isinstance(entry, dict):
                    v.field_error(5, entry_path, render_path(entry_path) + " must be object")
                    continue
                v.unknown_fields(entry, entry_path, ["step_id", "completed_at"])
                step_id = v.check_str(entry, "step_id", entry_path, 5)
                v.check_str(entry, "completed_at", entry_path, 5)
                if isinstance(step_id, str):
                    completion_steps.append(step_id)
            if len(completion_steps) != len(set(completion_steps)):
                v.field_error(5, path + ("step_completions",), "claim.step_completions is outside its allowed set")
        if "gate_context" in claim:
            v.check_str(claim, "gate_context", path, 5, required=False, allow_null=True)
        push_link = v.check_obj_field(claim, "push_link", path, 5, allow_null=True)
        if push_link is not None:
            push_path = path + ("push_link",)
            v.unknown_fields(push_link, push_path, ["repo", "head_sha", "tree_sha"])
            v.check_str(push_link, "repo", push_path, 5)
            v.check_str(push_link, "head_sha", push_path, 5)
            v.check_str(push_link, "tree_sha", push_path, 5)
        if "predecessor_inputs" not in claim:
            v.field_error(5, path + ("predecessor_inputs",), "claim.predecessor_inputs is missing")
        elif v.is_dupped(path + ("predecessor_inputs",)):
            pass
        elif claim["predecessor_inputs"] is not None:
            if not isinstance(claim["predecessor_inputs"], list):
                v.field_error(5, path + ("predecessor_inputs",), "claim.predecessor_inputs must be list")
            else:
                v.check_material_list(claim["predecessor_inputs"], path + ("predecessor_inputs",), 5)
        v.check_str_list(claim, "ledger_claims", path, 5)

    push_record = v.check_section_obj(top, "push_record", 6)
    if push_record is not None:
        path = ("push_record",)
        v.unknown_fields(push_record, path, ["repo", "branch", "head_sha", "tree_sha", "verified_by", "verified_at"])
        for field_name in ("repo", "branch", "head_sha", "tree_sha", "verified_by", "verified_at"):
            v.check_str(push_record, field_name, path, 6)

    previous_stage = v.check_section_obj(top, "previous_stage", 7)
    if previous_stage is not None:
        path = ("previous_stage",)
        v.unknown_fields(previous_stage, path, ["stage_id", "outputs"])
        v.check_str(previous_stage, "stage_id", path, 7)
        outputs = v.check_list(previous_stage, "outputs", path, 7)
        v.check_material_list(outputs, path + ("outputs",), 7)

    ledger_entries = v.check_section_list(top, "ledger_entries", 8)
    if ledger_entries is not None:
        path = ("ledger_entries",)
        entry_ids = []
        for idx, entry in enumerate(ledger_entries):
            entry_path = path + (idx,)
            if v.is_dupped(entry_path):
                continue
            if not isinstance(entry, dict):
                v.field_error(8, entry_path, render_path(entry_path) + " must be object")
                continue
            v.unknown_fields(entry, entry_path, ["entry_id", "text"])
            entry_id = v.check_str(entry, "entry_id", entry_path, 8)
            v.check_str(entry, "text", entry_path, 8)
            if isinstance(entry_id, str):
                entry_ids.append(entry_id)
        if len(entry_ids) != len(set(entry_ids)):
            v.field_error(8, path, "ledger_entries is outside its allowed set")

    return v


# Validated bundle shape


def _material(raw_list):
    return [{"name": item["name"], "sha256": digest_value(item["sha256"])} for item in raw_list]


def build_validated(top, bundle_digest, bundle_dir):
    vb = {"bundle_sha256": bundle_digest, "bundle_dir": bundle_dir}
    vb["sections_present"] = [name for name in SECTION_ORDER if name in top]
    vb["sections_absent"] = [name for name in SECTION_ORDER if name not in top]

    if "layout" in top:
        raw = top["layout"]
        artifacts = []
        for entry in raw["required_artifacts"]:
            supplied = Path(entry["path"])
            if not supplied.is_absolute():
                supplied = bundle_dir / supplied
            properties = []
            for prop in entry["properties"]:
                properties.append({
                    "kind": prop["kind"],
                    "line": prop.get("line", ABSENT),
                    "count": prop.get("count", ABSENT),
                    "sha256": digest_value(prop["sha256"]) if "sha256" in prop else ABSENT,
                })
            artifacts.append({
                "artifact_id": entry["artifact_id"],
                "path": entry["path"],
                "resolved_path": resolve_quietly(supplied),
                "sha256": digest_value(entry["sha256"]),
                "properties": properties,
            })
        vb["layout"] = {
            "stage_id": raw["stage_id"],
            "steps": [{"step_id": s["step_id"], "seat": s["seat"], "predicate_type": s["predicate_type"]} for s in raw["steps"]],
            "required_artifacts": artifacts,
            "record_sources": [{"record_kind": e["record_kind"], "source": e["source"]} for e in raw["record_sources"]],
        }
    else:
        vb["layout"] = ABSENT

    if "roster" in top:
        raw = top["roster"]
        vb["roster"] = {
            "entries": [{"seat": e["seat"], "agent_id": e["agent_id"], "recorded_at": parse_time_value(e["recorded_at"]), "origin": e["origin"]} for e in raw["entries"]],
            "republications": [{"seat": e["seat"], "republished_at": parse_time_value(e["republished_at"])} for e in raw["republications"]],
        }
    else:
        vb["roster"] = ABSENT

    if "links" in top:
        links = []
        for entry in top["links"]:
            links.append({
                "step_id": entry["step_id"],
                "predicate_type": entry["predicate_type"],
                "performer_spawn_id": entry["performer_spawn_id"],
                "builder": entry["builder"],
                "produced_at": parse_time_value(entry["produced_at"]) if "produced_at" in entry else ABSENT,
                "ran_at": parse_time_value(entry["ran_at"]),
                "inputs": _material(entry["inputs"]),
                "outputs": _material(entry["outputs"]),
                "subject_artifacts": [{"artifact_id": s["artifact_id"], "sha256": digest_value(s["sha256"])} for s in entry["subject_artifacts"]],
            })
        vb["links"] = links
    else:
        vb["links"] = ABSENT

    if "spawn_records" in top:
        raw = top["spawn_records"]
        vb["spawn_records"] = {
            "exporter": raw["exporter"],
            "exported_at": parse_time_value(raw["exported_at"]),
            "source_database": raw["source_database"],
            "scoping": {"method": raw["scoping"]["method"], "detail": raw["scoping"]["detail"]},
            "records": [{"agent_id": r["agent_id"], "parent_agent_id": r["parent_agent_id"], "depth": r["depth"], "kind": r["kind"], "agent_type": r["agent_type"], "session_id": r["session_id"], "created_at": parse_time_value(r["created_at"])} for r in raw["records"]],
        }
    else:
        vb["spawn_records"] = ABSENT

    if "identities" in top:
        raw = top["identities"]
        vb["identities"] = {"coordinator": raw["coordinator"], "commissioner_stage": raw["commissioner_stage"], "commissioner_work": raw["commissioner_work"]}
    else:
        vb["identities"] = ABSENT

    if "claim" in top:
        raw = top["claim"]
        vb["claim"] = {
            "stage_id": raw["stage_id"],
            "steps_claimed": list(raw["steps_claimed"]),
            "step_completions": [{"step_id": c["step_id"], "completed_at": parse_time_value(c["completed_at"])} for c in raw["step_completions"]],
            "gate_context": raw.get("gate_context"),
            "push_link": raw["push_link"],
            "predecessor_inputs": _material(raw["predecessor_inputs"]) if raw["predecessor_inputs"] is not None else None,
            "ledger_claims": list(raw["ledger_claims"]),
        }
    else:
        vb["claim"] = ABSENT

    if "push_record" in top:
        raw = top["push_record"]
        vb["push_record"] = {"repo": raw["repo"], "branch": raw["branch"], "head_sha": raw["head_sha"], "tree_sha": raw["tree_sha"], "verified_by": raw["verified_by"], "verified_at": parse_time_value(raw["verified_at"])}
    else:
        vb["push_record"] = ABSENT

    if "previous_stage" in top:
        raw = top["previous_stage"]
        vb["previous_stage"] = {"stage_id": raw["stage_id"], "outputs": _material(raw["outputs"])}
    else:
        vb["previous_stage"] = ABSENT

    if "ledger_entries" in top:
        vb["ledger_entries"] = [{"entry_id": e["entry_id"], "text": e["text"]} for e in top["ledger_entries"]]
    else:
        vb["ledger_entries"] = ABSENT

    return vb


# Absence effects (plan part 1.7)


def compute_absence_effects(vb):
    absent = set(vb["sections_absent"])
    triage = {"authenticity": "run", "chain": "run", "completeness": "run"}
    rank = {"run": 0, "fail": 1, "cannot_run": 2}
    label = {0: "run", 1: "fail", 2: "cannot_run"}

    def apply(check, effect):
        if rank[effect] > rank[triage[check]]:
            triage[check] = effect

    if "layout" in absent:
        apply("authenticity", "cannot_run")
        apply("chain", "cannot_run")
        apply("completeness", "cannot_run")
    if "roster" in absent:
        apply("authenticity", "cannot_run")
        apply("chain", "fail")
        apply("completeness", "fail")
    if "links" in absent:
        apply("authenticity", "cannot_run")
        apply("chain", "fail")
        apply("completeness", "fail")
    if "spawn_records" in absent:
        apply("authenticity", "cannot_run")
        apply("chain", "fail")
        apply("completeness", "fail")
    if "claim" in absent:
        apply("completeness", "cannot_run")
    return {
        "triage": triage,
        "identities_cap": "identities" in absent,
        "absent_required": [name for name in REQUIRED_SECTIONS if name in absent],
        "completeness_cannot_run": triage["completeness"] == "cannot_run",
        "authenticity_cannot_run": triage["authenticity"] == "cannot_run",
        "chain_cannot_run": triage["chain"] == "cannot_run",
        "chain_forced_fail": triage["chain"] == "fail",
    }


# Discrepancy entries


_creation_counter = {"value": 0}


def make_entry(code, part, subject, found, consequence=None):
    _creation_counter["value"] += 1
    if code == "ABSENT-SECTION":
        expected = EXPECTED_TEXT[code].format(subject=subject)
        cure = "supply the " + subject + " section in the bundle."
    else:
        expected = EXPECTED_TEXT[code]
        cure = CURE_TEXT[code]
    if consequence is None:
        consequence = "none" if code == "ANOM-MULTI-LINK" else "PARTIAL"
    return {
        "code": code,
        "part": part,
        "subject": subject,
        "check": CHECK_OF_CODE[code],
        "expected": expected,
        "found": found,
        "consequence": consequence,
        "cure": cure,
        "_creation": _creation_counter["value"],
    }


def public_entry(entry):
    return {key: entry[key] for key in ("code", "part", "subject", "check", "expected", "found", "consequence", "cure")}


# Authorisation record builder (plan part 1.8)


def build_authorisation_records(vb):
    records = []
    details = []
    layout = vb["layout"]
    roster = vb["roster"]
    spawn = vb["spawn_records"]
    steps_by_id = {step["step_id"]: step for step in layout["steps"]}
    spawn_records = spawn["records"]
    roster_entries = roster["entries"]
    republications = roster["republications"]
    spawn_by_agent = {}
    for item in spawn_records:
        spawn_by_agent.setdefault(item["agent_id"], []).append(item)
    roster_by_seat = {}
    roster_by_seat_and_agent = {}
    for entry in roster_entries:
        roster_by_seat.setdefault(entry["seat"], []).append(entry)
        roster_by_seat_and_agent.setdefault((entry["seat"], entry["agent_id"]), []).append(entry)
    repubs_by_seat = {}
    for entry in republications:
        repubs_by_seat.setdefault(entry["seat"], []).append(entry)
    seat_layout_earliest = {}
    for entry in roster_entries:
        if entry["origin"] == "layout" and entry["recorded_at"]["parses"]:
            instant = entry["recorded_at"]["instant"]
            if entry["seat"] not in seat_layout_earliest or instant < seat_layout_earliest[entry["seat"]]:
                seat_layout_earliest[entry["seat"]] = instant
    repub_facts_by_seat = {}
    for seat_key, seat_repubs_list in repubs_by_seat.items():
        parseable_repubs_list = [entry for entry in seat_repubs_list if entry["republished_at"]["parses"]]
        unparseable_repubs_list = [entry for entry in seat_repubs_list if not entry["republished_at"]["parses"]]
        governing_entry = None
        if parseable_repubs_list:
            governing_entry = parseable_repubs_list[0]
            for entry in parseable_repubs_list[1:]:
                if entry["republished_at"]["instant"] < governing_entry["republished_at"]["instant"]:
                    governing_entry = entry
        repub_facts_by_seat[seat_key] = {
            "has_repubs": bool(seat_repubs_list),
            "governing": governing_entry["republished_at"] if governing_entry is not None else None,
            "first_unparseable_raw": unparseable_repubs_list[0]["republished_at"]["raw"] if unparseable_repubs_list else None,
        }
    for index, link in enumerate(vb["links"]):
        detail = {"spawn_match_count": 0, "first_unparseable_republication": None, "empty_records": len(spawn_records) == 0, "empty_roster": len(roster_entries) == 0}
        step = steps_by_id.get(link["step_id"])
        record = {
            "link_index": index,
            "step_id": link["step_id"],
            "predicate_type": link["predicate_type"],
            "performer_spawn_id": link["performer_spawn_id"],
            "builder": link["builder"],
            "ran_at": link["ran_at"],
            "binding_outcome": "no match",
            "binding_spawn_record": None,
            "spawn_created_at": None,
            "time_anchor_outcome": "cannot be made",
            "roster_entries_considered": [],
            "authorising_entry": None,
            "authorisation_outcome": "no roster entry",
            "recorded_at_for_report": None,
            "origin_of_authorising_entry": "no entry",
            "seat_stands_in_advance_layout": False,
            "governing_republication": None,
            "republication_outcome": "not applicable",
            "all_unparseable_republication_marker": False,
            "first_failing_subtest": "none",
            "authenticity_outcome": "pass",
            "part_assignment_input": None,
        }
        if step is None:
            record["binding_outcome"] = "not run"
            record["time_anchor_outcome"] = "not run"
            record["authorisation_outcome"] = "not run"
            record["authenticity_outcome"] = "fail"
            records.append(record)
            details.append(detail)
            continue
        seat = step["seat"]
        ran_at = link["ran_at"]
        matches = spawn_by_agent.get(link["performer_spawn_id"], [])
        detail["spawn_match_count"] = len(matches)
        if len(matches) == 1:
            record["binding_outcome"] = "bound"
            record["binding_spawn_record"] = matches[0]
            record["spawn_created_at"] = matches[0]["created_at"]
        elif len(matches) > 1:
            record["binding_outcome"] = "multiple matches"
        failing = None
        if record["binding_outcome"] != "bound":
            failing = "a"
        else:
            created = record["spawn_created_at"]
            if not created["parses"] or not ran_at["parses"]:
                record["time_anchor_outcome"] = "cannot be made"
                failing = "b"
            elif created["instant"] > ran_at["instant"]:
                record["time_anchor_outcome"] = "fail"
                failing = "b"
            else:
                record["time_anchor_outcome"] = "pass"
        if failing is None:
            considered = []
            for entry in roster_by_seat_and_agent.get((seat, link["performer_spawn_id"]), []):
                considered.append({
                    "seat": entry["seat"],
                    "agent_id": entry["agent_id"],
                    "recorded_at": entry["recorded_at"],
                    "origin": entry["origin"],
                    "parseable": entry["recorded_at"]["parses"],
                    "set_aside": not entry["recorded_at"]["parses"],
                })
            record["roster_entries_considered"] = considered
            parseable = [item for item in considered if item["parseable"]]
            authorising = None
            if ran_at["parses"]:
                candidates = [item for item in parseable if item["recorded_at"]["instant"] <= ran_at["instant"]]
                if candidates:
                    best = candidates[0]
                    for item in candidates[1:]:
                        if item["recorded_at"]["instant"] < best["recorded_at"]["instant"]:
                            best = item
                    authorising = best
            if authorising is not None:
                record["authorising_entry"] = {"seat": authorising["seat"], "agent_id": authorising["agent_id"], "recorded_at": authorising["recorded_at"], "origin": authorising["origin"]}
                record["authorisation_outcome"] = "authorised"
                record["recorded_at_for_report"] = authorising["recorded_at"]["raw"]
                record["origin_of_authorising_entry"] = authorising["origin"]
            elif parseable:
                record["authorisation_outcome"] = "late recording"
                failing = "c"
            elif considered:
                record["authorisation_outcome"] = "no parseable roster entry"
                failing = "c"
            else:
                record["authorisation_outcome"] = "no roster entry"
                failing = "c"
        if failing is None and record["authorising_entry"] is not None:
            earliest_layout = seat_layout_earliest.get(seat)
            stands = bool(ran_at["parses"] and earliest_layout is not None and earliest_layout <= ran_at["instant"])
            record["seat_stands_in_advance_layout"] = stands
            repub_facts = repub_facts_by_seat.get(seat)
            governing = None
            if repub_facts is not None:
                if repub_facts["has_repubs"] and repub_facts["governing"] is None:
                    record["all_unparseable_republication_marker"] = True
                    detail["first_unparseable_republication"] = repub_facts["first_unparseable_raw"]
                governing = repub_facts["governing"]
                if governing is not None:
                    record["governing_republication"] = governing
            if record["authorising_entry"]["origin"] == "addition" and not stands:
                if governing is not None and ran_at["parses"] and governing["instant"] <= ran_at["instant"]:
                    record["republication_outcome"] = "pass"
                else:
                    record["republication_outcome"] = "fail"
                    failing = "d"
            else:
                record["republication_outcome"] = "not applicable"
        if failing is not None:
            record["first_failing_subtest"] = failing
            record["authenticity_outcome"] = "fail"
        records.append(record)
        details.append(detail)
    seat_parts_input = {}
    steps_by_id = {step["step_id"]: step for step in layout["steps"]}
    by_seat = {}
    for step in layout["steps"]:
        by_seat.setdefault(step["seat"], [])
    for record in records:
        step = steps_by_id.get(record["step_id"])
        if step is None:
            continue
        by_seat.setdefault(step["seat"], []).append(record)
    for seat, seat_records in by_seat.items():
        authorised = [item for item in seat_records if item["authorising_entry"] is not None]
        if authorised:
            best_instant = min(item["authorising_entry"]["recorded_at"]["instant"] for item in authorised)
            tied = [item for item in authorised if item["authorising_entry"]["recorded_at"]["instant"] == best_instant]
            origin = "addition" if any(item["authorising_entry"]["origin"] == "addition" for item in tied) else "layout"
            info = {"seat": seat, "earliest_authorising_recorded_at": tied[0]["authorising_entry"]["recorded_at"]["raw"], "origin": origin}
        else:
            parseable_entries = [entry for entry in roster_by_seat.get(seat, []) if entry["recorded_at"]["parses"]]
            if parseable_entries:
                best_instant = min(entry["recorded_at"]["instant"] for entry in parseable_entries)
                tied = [entry for entry in parseable_entries if entry["recorded_at"]["instant"] == best_instant]
                origin = "addition" if any(entry["origin"] == "addition" for entry in tied) else "layout"
                info = {"seat": seat, "earliest_authorising_recorded_at": tied[0]["recorded_at"]["raw"], "origin": origin}
            else:
                info = {"seat": seat, "earliest_authorising_recorded_at": None, "origin": "layout"}
        seat_parts_input[seat] = info
        for record in seat_records:
            record["part_assignment_input"] = info
    return records, details, seat_parts_input


def roster_entries_for_seat(vb, seat):
    if vb["roster"] is ABSENT:
        return []
    return [entry for entry in vb["roster"]["entries"] if entry["seat"] == seat]


def seat_part_map(vb, seat_parts_input):
    result = {}
    for step in vb["layout"]["steps"]:
        seat = step["seat"]
        if seat in result:
            continue
        info = seat_parts_input.get(seat)
        if info is not None and info["origin"] == "addition":
            result[seat] = "part2"
        else:
            result[seat] = "part1"
    return result


# Export scan (plan part 1.9a)


def scan_export(vb):
    bound = {link["performer_spawn_id"] for link in vb["links"]}
    counts = {}
    for record in vb["spawn_records"]["records"]:
        counts[record["agent_id"]] = counts.get(record["agent_id"], 0) + 1
    duplicated = []
    seen = set()
    for record in vb["spawn_records"]["records"]:
        agent_id = record["agent_id"]
        if counts[agent_id] > 1 and agent_id not in bound and agent_id not in seen:
            seen.add(agent_id)
            duplicated.append({"agent_id": agent_id})
    unparseable = []
    for record in vb["spawn_records"]["records"]:
        if record["agent_id"] not in bound and not record["created_at"]["parses"]:
            unparseable.append({"agent_id": record["agent_id"], "session_id": record["session_id"], "created_at_raw": record["created_at"]["raw"]})
    return {"duplicated_export_identities": duplicated, "unbound_unparseable_creation_facts": unparseable}


# Authenticity part (plan part 1.9)


def run_authenticity(vb, records, details, export_facts, seat_parts):
    entries = []
    steps_by_id = {step["step_id"]: step for step in vb["layout"]["steps"]}
    per_link_outcomes = []
    for record, detail in zip(records, details):
        link_index = record["link_index"]
        if record["step_id"] not in steps_by_id:
            per_link_outcomes.append({"link_index": link_index, "outcome": "fail", "first_failing_subtest": "none", "code": "LINK-NO-STEP"})
            continue
        step = steps_by_id[record["step_id"]]
        part = seat_parts.get(step["seat"], "part1")
        performer = record["performer_spawn_id"]
        code = None
        found = None
        consequence = "PARTIAL"
        failing = record["first_failing_subtest"]
        if failing == "a":
            code = "AUTH-NO-SPAWN"
            if detail["empty_records"]:
                found = "the spawn records list is empty"
                consequence = "UNVERIFIABLE"
            else:
                found = "%d spawn records match performer %s" % (detail["spawn_match_count"], performer)
        elif failing == "b":
            code = "AUTH-STEP-TIME"
            created = record["spawn_created_at"]
            ran_at = record["ran_at"]
            if created is not None and not created["parses"]:
                found = "the time anchor cannot be made because created_at %s does not parse" % created["raw"]
            elif not ran_at["parses"]:
                found = "the time anchor cannot be made because ran_at %s does not parse" % ran_at["raw"]
            else:
                found = "spawn record created_at %s is later than ran_at %s" % (created["raw"], ran_at["raw"])
        elif failing == "c":
            if record["authorisation_outcome"] == "late recording":
                code = "AUTH-LATE-RECORD"
                parseable = [item for item in record["roster_entries_considered"] if item["parseable"]]
                earliest_entry = None
                for item in parseable:
                    if earliest_entry is None or item["recorded_at"]["instant"] < earliest_entry["recorded_at"]["instant"]:
                        earliest_entry = item
                found = "every parseable roster entry for the seat and performer is recorded after ran_at, earliest %s" % earliest_entry["recorded_at"]["raw"]
            else:
                code = "AUTH-NO-ROSTER"
                if detail["empty_roster"]:
                    found = "the roster entries list is empty"
                    consequence = "UNVERIFIABLE"
                elif record["authorisation_outcome"] == "no parseable roster entry":
                    set_aside = [item for item in record["roster_entries_considered"] if item["set_aside"]]
                    found = "every roster entry for seat %s and performer %s has an unparseable recorded_at, first value %s" % (step["seat"], performer, set_aside[0]["recorded_at"]["raw"])
                else:
                    found = "no roster entry for seat %s and performer %s stands" % (step["seat"], performer)
        elif failing == "d":
            code = "AUTH-NO-REPUB"
            if detail["first_unparseable_republication"] is not None and record["governing_republication"] is None:
                found = "the republication value %s does not parse and cannot count" % detail["first_unparseable_republication"]
            elif record["governing_republication"] is not None:
                found = "the governing republication %s is later than ran_at %s" % (record["governing_republication"]["raw"], record["ran_at"]["raw"])
            else:
                found = "no republication for seat %s stands at or before ran_at %s" % (step["seat"], record["ran_at"]["raw"])
        if code is not None:
            entries.append(make_entry(code, part, record["step_id"], found, consequence))
            per_link_outcomes.append({"link_index": link_index, "outcome": "fail", "first_failing_subtest": failing, "code": code})
        else:
            per_link_outcomes.append({"link_index": link_index, "outcome": "pass", "first_failing_subtest": "none", "code": None})
    for fact in export_facts["duplicated_export_identities"]:
        entries.append(make_entry("AUTH-NO-SPAWN", "stage", fact["agent_id"], "agent_id %s appears more than once in the export and no link binds it" % fact["agent_id"]))
    for fact in export_facts["unbound_unparseable_creation_facts"]:
        entries.append(make_entry("AUTH-STEP-TIME", "stage", fact["agent_id"], "created_at %s on the record with session_id %s does not parse" % (fact["created_at_raw"], fact["session_id"])))
    for record in records:
        if record["step_id"] not in steps_by_id:
            entries.append(make_entry("LINK-NO-STEP", "stage", record["step_id"], "link for step %s names no layout step" % record["step_id"]))

    origin_outcomes = {}
    record_sources = vb["layout"]["record_sources"]

    def sources_for(kind):
        return [entry["source"] for entry in record_sources if entry["record_kind"] == kind]

    roster_sources = sources_for("roster")
    if not roster_sources:
        entries.append(make_entry("AUTH-ORIGIN", "stage", "roster", "record_sources names no entry for record kind roster"))
        origin_outcomes["roster"] = {"result": "fail", "code": "AUTH-ORIGIN"}
    elif "self-reported-file" in roster_sources:
        entries.append(make_entry("AUTH-ORIGIN", "stage", "roster", "record kind roster names source self-reported-file"))
        origin_outcomes["roster"] = {"result": "fail", "code": "AUTH-ORIGIN"}
    else:
        origin_outcomes["roster"] = {"result": "pass", "code": None}

    claim = vb["claim"]
    push_link_present = claim is not ABSENT and claim["push_link"] is not None
    push_in_play = push_link_present or bool(sources_for("push"))
    push_origin_pass = False
    if push_in_play:
        push_sources = sources_for("push")
        if not push_sources:
            entries.append(make_entry("AUTH-ORIGIN", "stage", "push", "record_sources names no entry for record kind push"))
            origin_outcomes["push"] = {"result": "fail", "code": "AUTH-ORIGIN"}
        elif "self-reported-file" in push_sources:
            entries.append(make_entry("AUTH-ORIGIN", "stage", "push", "record kind push names source self-reported-file"))
            origin_outcomes["push"] = {"result": "fail", "code": "AUTH-ORIGIN"}
        else:
            origin_outcomes["push"] = {"result": "pass", "code": None}
            push_origin_pass = True
        if vb["push_record"] is ABSENT:
            entries.append(make_entry("AUTH-NO-PUSH", "stage", "push", "push_record is absent while a push link is in play"))
        else:
            push_record = vb["push_record"]
            if push_link_present:
                for field_name in ("repo", "head_sha", "tree_sha"):
                    if claim["push_link"][field_name] != push_record[field_name]:
                        entries.append(make_entry("AUTH-ORIGIN", "stage", "push", "push field %s differs between the claim push link and the push record" % field_name))
            if not push_record["verified_at"]["parses"]:
                entries.append(make_entry("AUTH-ORIGIN", "stage", "push", "push verified_at %s does not parse" % push_record["verified_at"]["raw"]))
    for kind in ("links", "claim", "ledger"):
        kind_sources = sources_for(kind)
        if "self-reported-file" in kind_sources:
            entries.append(make_entry("AUTH-ORIGIN", "stage", kind, "record kind %s names source self-reported-file" % kind))
            origin_outcomes[kind] = {"result": "fail", "code": "AUTH-ORIGIN"}
        else:
            origin_outcomes[kind] = {"result": "no origin result", "code": None}
    roster_origin_pass = origin_outcomes.get("roster", {}).get("result") == "pass"
    result = {
        "check": "fail" if entries else "pass",
        "per_link_outcomes": per_link_outcomes,
        "entries": entries,
        "origin_outcomes": origin_outcomes,
        "full_pass_origin_facts": {"roster_origin_pass": roster_origin_pass, "push_in_play": push_in_play, "push_origin_pass": push_origin_pass if push_in_play else True},
    }
    return result


# Matching builder (plan part 1.11)


def build_matching(vb, records):
    layout = vb["layout"]
    claim = vb["claim"]
    completions = {}
    claimed = []
    if claim is not ABSENT:
        claimed = claim["steps_claimed"]
        for entry in claim["step_completions"]:
            completions[entry["step_id"]] = entry["completed_at"]
    records_by_step = {}
    for record in records:
        records_by_step.setdefault(record["step_id"], []).append(record)
    links_by_index = {index: link for index, link in enumerate(vb["links"])} if vb["links"] is not ABSENT else {}
    steps_out = []
    for step in layout["steps"]:
        presented = records_by_step.get(step["step_id"], [])
        completion = completions.get(step["step_id"])
        reconstruction = []
        matching = []
        for record in presented:
            link = links_by_index[record["link_index"]]
            if claim is ABSENT:
                outcome = {"link_index": record["link_index"], "outcome": "untestable", "reason": "no completion time recorded"}
            elif completion is None:
                outcome = {"link_index": record["link_index"], "outcome": "untestable", "reason": "no completion time recorded"}
            elif not completion["parses"]:
                outcome = {"link_index": record["link_index"], "outcome": "untestable", "reason": "the completion time does not parse"}
            else:
                produced = link["produced_at"]
                if produced is ABSENT:
                    outcome = {"link_index": record["link_index"], "outcome": "reconstructed", "reason": "no produced_at field"}
                elif not produced["parses"]:
                    outcome = {"link_index": record["link_index"], "outcome": "reconstructed", "reason": "produced_at does not parse"}
                elif produced["instant"] > completion["instant"]:
                    outcome = {"link_index": record["link_index"], "outcome": "reconstructed", "reason": "produced_at later than the recorded completion time"}
                elif link["ran_at"]["parses"] and produced["instant"] < link["ran_at"]["instant"]:
                    outcome = {"link_index": record["link_index"], "outcome": "reconstructed", "reason": "produced_at earlier than ran_at"}
                else:
                    outcome = {"link_index": record["link_index"], "outcome": "pass", "reason": None}
            reconstruction.append(outcome)
            if (record["predicate_type"] == step["predicate_type"] and record["authenticity_outcome"] == "pass" and outcome["outcome"] == "pass"):
                matching.append(record)
        per_step_auth = "pass" if any(item["authenticity_outcome"] == "pass" for item in presented) else "fail"
        steps_out.append({
            "step": step,
            "presented_links": presented,
            "per_step_authenticity": per_step_auth,
            "reconstruction_outcomes": reconstruction,
            "matching_links": matching,
            "per_step_matching": "pass" if matching else "fail",
            "multi_link": len(matching) > 1,
            "predicate_mismatch_links": [item for item in presented if item["predicate_type"] != step["predicate_type"]],
        })
    layout_ids = [step["step_id"] for step in layout["steps"]]
    claimed_set = set(claimed)
    layout_id_set = set(layout_ids)
    return {
        "steps": steps_out,
        "layout_steps_not_claimed": [step_id for step_id in layout_ids if step_id not in claimed_set] if claim is not ABSENT else [],
        "claimed_steps_naming_no_layout_step": [step_id for step_id in claimed if step_id not in layout_id_set] if claim is not ABSENT else [],
        "orphan_links": [record for record in records if record["step_id"] not in layout_id_set],
    }


# Canonical material maps (plan part 1.10)


def canonical_map(material_list):
    mapping = {}
    order = []
    duplicated = []
    for item in material_list:
        name = item["name"]
        if name not in mapping:
            mapping[name] = []
            order.append(name)
        mapping[name].append(item["sha256"])
        if len(mapping[name]) == 2:
            duplicated.append(name)
    digest_sets = {}
    bad_form = set()
    for name in order:
        digest_sets[name] = frozenset(item["raw"] for item in mapping[name])
        if any(not item["in_form"] for item in mapping[name]):
            bad_form.add(name)
    signature = (tuple(order), tuple(digest_sets[name] for name in order), frozenset(duplicated), frozenset(bad_form))
    return {"map": mapping, "order": order, "duplicated": duplicated, "digest_sets": digest_sets, "bad_form": bad_form, "signature": signature}


def compare_maps(earlier, later):
    earlier_duplicated = set(earlier["duplicated"])
    later_duplicated = set(later["duplicated"])
    combined_order = earlier["order"] + later["order"]
    duplicated_names = []
    seen_duplicated = set()
    for name in combined_order:
        if (name in earlier_duplicated or name in later_duplicated) and name not in seen_duplicated:
            seen_duplicated.add(name)
            duplicated_names.append(name)
    failing_names = []
    all_names = []
    seen_names = set()
    for name in combined_order:
        if name not in seen_names:
            seen_names.add(name)
            all_names.append(name)
    for name in all_names:
        in_earlier = name in earlier["map"]
        in_later = name in later["map"]
        if not in_earlier or not in_later:
            failing_names.append(name)
            continue
        if name in earlier["bad_form"] or name in later["bad_form"]:
            failing_names.append(name)
            continue
        if earlier["digest_sets"][name] != later["digest_sets"][name]:
            failing_names.append(name)
    return duplicated_names, failing_names


# Chain part (plan part 1.12)


def run_chain(vb, matching, seat_parts, suppress_joins):
    entries = []
    join_outcomes = []
    steps = matching["steps"]
    layout_steps = vb["layout"]["steps"]
    input_maps = {}
    output_maps = {}

    def inputs_map(link_index):
        if link_index not in input_maps:
            input_maps[link_index] = canonical_map(vb["links"][link_index]["inputs"])
        return input_maps[link_index]

    def outputs_map(link_index):
        if link_index not in output_maps:
            output_maps[link_index] = canonical_map(vb["links"][link_index]["outputs"])
        return output_maps[link_index]

    compare_cache = {}

    def compare_cached(earlier_map, later_map):
        key = (earlier_map["signature"], later_map["signature"])
        result = compare_cache.get(key)
        if result is None:
            result = compare_maps(earlier_map, later_map)
            compare_cache[key] = result
        return result
    for position in range(len(layout_steps) - 1):
        earlier_step = layout_steps[position]
        later_step = layout_steps[position + 1]
        earlier_matching = steps[position]["matching_links"]
        later_matching = steps[position + 1]["matching_links"]
        subject = "%s -> %s" % (earlier_step["step_id"], later_step["step_id"])
        part = seat_parts.get(earlier_step["seat"], "part1")
        join_entries = []
        if not earlier_matching or not later_matching:
            if not suppress_joins:
                if not earlier_matching and not later_matching:
                    found = "steps %s and %s have no matching link" % (earlier_step["step_id"], later_step["step_id"])
                elif not earlier_matching:
                    found = "step %s has no matching link" % earlier_step["step_id"]
                else:
                    found = "step %s has no matching link" % later_step["step_id"]
                join_entries.append(make_entry("CHAIN-JOIN", part, subject, found))
        else:
            duplicated_all = []
            failing_all = []
            for earlier_record in earlier_matching:
                earlier_map = outputs_map(earlier_record["link_index"])
                for later_record in later_matching:
                    later_map = inputs_map(later_record["link_index"])
                    duplicated_names, failing_names = compare_cached(earlier_map, later_map)
                    for name in duplicated_names:
                        if name not in duplicated_all:
                            duplicated_all.append(name)
                    for name in failing_names:
                        if name not in failing_all:
                            failing_all.append(name)
            if not suppress_joins:
                for name in duplicated_all:
                    join_entries.append(make_entry("CHAIN-JOIN", part, subject, "name %s is duplicated in one material list" % name))
                for name in failing_all:
                    join_entries.append(make_entry("CHAIN-JOIN", part, subject, "name %s differs between step %s outputs and step %s inputs" % (name, earlier_step["step_id"], later_step["step_id"])))
        entries.extend(join_entries)
        join_outcomes.append({"earlier_step": earlier_step["step_id"], "later_step": later_step["step_id"], "result": "fail" if (join_entries or not earlier_matching or not later_matching) else "pass", "entries": join_entries})
    boundary_entries = []
    boundary_status = "not applicable"
    claim = vb["claim"]
    if claim is not ABSENT and vb["layout"] is not ABSENT:
        predecessor = claim["predecessor_inputs"]
        if predecessor:
            previous = vb["previous_stage"]
            if previous is ABSENT or not previous["outputs"]:
                boundary_entries.append(make_entry("CHAIN-BOUNDARY", "stage", "boundary", "the stage claims predecessor inputs and the previous stage has no recorded outputs"))
                boundary_status = "failed"
            else:
                pred_map = canonical_map(predecessor)
                prev_map = canonical_map(previous["outputs"])
                duplicated_names, failing_names = compare_maps(pred_map, prev_map)
                for name in duplicated_names:
                    boundary_entries.append(make_entry("CHAIN-BOUNDARY", "stage", "boundary", "name %s is duplicated in predecessor inputs or in previous stage outputs" % name))
                for name in failing_names:
                    boundary_entries.append(make_entry("CHAIN-BOUNDARY", "stage", "boundary", "name %s differs between predecessor inputs and previous stage outputs" % name))
                boundary_status = "failed" if boundary_entries else "matched"
    entries.extend(boundary_entries)
    return {
        "check": "fail" if entries else "pass",
        "join_outcomes": join_outcomes,
        "boundary_outcome": {"status": boundary_status, "entries": boundary_entries},
        "entries": entries,
    }


# Completeness part (plan part 1.13, 1.14, 1.15)


def read_artifact(artifact, properties=None):
    unreadable = {"readable": False, "bytes": None, "size": None, "sha256": None, "lines": None, "decodable": False, "line_count": None, "first_line": None, "first_line_oversized": False, "contains_found": set()}
    try:
        artifact_stat = os.stat(artifact["resolved_path"])
    except (OSError, ValueError):
        return unreadable
    if not stat.S_ISREG(artifact_stat.st_mode):
        return unreadable
    contains_targets = set()
    first_targets = set()
    if properties is not None:
        for prop in properties:
            if prop["kind"] == "contains_line" and prop["line"] is not ABSENT:
                contains_targets.add(prop["line"])
            if prop["kind"] == "first_line_equals" and prop["line"] is not ABSENT:
                first_targets.add(prop["line"])
    max_target_len = 0
    for target in contains_targets | first_targets:
        if len(target) > max_target_len:
            max_target_len = len(target)
    store_lines = properties is None
    cap = None if store_lines else max_target_len + 1
    hasher = hashlib.sha256()
    size = 0
    decoder = codecs.getincrementaldecoder("utf-8")()
    decodable = True
    line_count = 0
    lines = [] if store_lines else None
    contains_found = set()
    first_line = None
    first_line_oversized = False
    current_parts = []
    current_len = 0
    current_exceeds = False
    saw_text = False
    last_was_newline = False

    def append_segment(segment):
        nonlocal current_len, current_exceeds
        if segment == "":
            return
        if cap is None:
            current_parts.append(segment)
            current_len += len(segment)
            return
        if current_exceeds:
            return
        room = cap - current_len
        if len(segment) <= room:
            current_parts.append(segment)
            current_len += len(segment)
        else:
            if room > 0:
                current_parts.append(segment[:room])
                current_len += room
            current_exceeds = True

    def finalize_line():
        nonlocal line_count, first_line, first_line_oversized, current_parts, current_len, current_exceeds
        joined = None
        if store_lines:
            joined = "".join(current_parts)
            if joined.endswith("\r"):
                joined = joined[:-1]
            lines.append(joined)
        elif not current_exceeds:
            joined = "".join(current_parts)
            if joined.endswith("\r"):
                joined = joined[:-1]
            if line_count == 0:
                first_line = joined
            if joined in contains_targets:
                contains_found.add(joined)
        else:
            if line_count == 0:
                first_line_oversized = True
        line_count += 1
        current_parts = []
        current_len = 0
        current_exceeds = False

    def feed(text):
        nonlocal saw_text, last_was_newline
        if text == "":
            return
        saw_text = True
        segments = text.split("\n")
        for index, segment in enumerate(segments):
            if index > 0:
                finalize_line()
            append_segment(segment)
        last_was_newline = text.endswith("\n")

    try:
        with open(artifact["resolved_path"], "rb") as handle:
            while True:
                chunk = handle.read(65536)
                if not chunk:
                    break
                hasher.update(chunk)
                size += len(chunk)
                if decodable:
                    try:
                        feed(decoder.decode(chunk))
                    except UnicodeDecodeError:
                        decodable = False
    except (OSError, ValueError):
        return unreadable
    if decodable:
        try:
            feed(decoder.decode(b"", True))
        except UnicodeDecodeError:
            decodable = False
    if not decodable:
        return {"readable": True, "bytes": None, "size": size, "sha256": hasher.hexdigest(), "lines": None, "decodable": False, "line_count": None, "first_line": None, "first_line_oversized": False, "contains_found": set()}
    if saw_text and not last_was_newline:
        finalize_line()
    if store_lines:
        first_line = lines[0] if lines else None
        contains_found = set(lines)
    return {"readable": True, "bytes": None, "size": size, "sha256": hasher.hexdigest(), "lines": lines, "decodable": True, "line_count": line_count, "first_line": first_line, "first_line_oversized": first_line_oversized, "contains_found": contains_found}


def evaluate_property(prop, artifact_file):
    kind = prop["kind"]
    if kind not in EVALUATED_KINDS:
        return "unsupported"
    if kind == "exists":
        return "pass" if artifact_file["readable"] else "fail"
    if kind == "sha256_equals":
        return "pass" if artifact_file["sha256"] == prop["sha256"]["raw"] else "fail"
    if kind == "byte_size_at_most":
        return "pass" if artifact_file["size"] <= prop["count"] else "fail"
    if not artifact_file["decodable"]:
        return "fail"
    lines = artifact_file["lines"]
    if kind == "contains_line":
        if lines is not None:
            return "pass" if prop["line"] in lines else "fail"
        return "pass" if prop["line"] in artifact_file["contains_found"] else "fail"
    if kind == "first_line_equals":
        if lines is not None:
            return "pass" if lines and lines[0] == prop["line"] else "fail"
        if artifact_file["line_count"] == 0 or artifact_file["first_line_oversized"]:
            return "fail"
        return "pass" if artifact_file["first_line"] == prop["line"] else "fail"
    if kind == "line_count_at_least":
        return "pass" if artifact_file["line_count"] >= prop["count"] else "fail"
    if kind == "line_count_at_most":
        return "pass" if artifact_file["line_count"] <= prop["count"] else "fail"
    return "unsupported"


def run_completeness(vb, matching, seat_parts, suppress_no_link):
    links_entries = []
    anomaly_entries = []
    claim = vb["claim"]
    claimed = claim["steps_claimed"] if claim is not ABSENT else []
    completions_by_step = {}
    if claim is not ABSENT:
        for completion_entry in claim["step_completions"]:
            completions_by_step[completion_entry["step_id"]] = completion_entry["completed_at"]
    for step_result in matching["steps"]:
        step = step_result["step"]
        part = seat_parts.get(step["seat"], "part1")
        for record, outcome in zip(step_result["presented_links"], step_result["reconstruction_outcomes"]):
            if outcome["outcome"] in ("reconstructed", "untestable"):
                link = vb["links"][record["link_index"]]
                if outcome["reason"] == "no completion time recorded":
                    found = "no completion time is recorded"
                elif outcome["reason"] == "the completion time does not parse":
                    found = "the completion time does not parse"
                elif outcome["reason"] == "no produced_at field":
                    found = "the link carries no produced_at"
                elif outcome["reason"] == "produced_at does not parse":
                    found = "produced_at %s does not parse" % link["produced_at"]["raw"]
                elif outcome["reason"] == "produced_at later than the recorded completion time":
                    completion = completions_by_step.get(step["step_id"])
                    found = "produced_at %s is later than the recorded completion time %s" % (link["produced_at"]["raw"], completion["raw"])
                elif outcome["reason"] == "produced_at earlier than ran_at":
                    found = "produced_at %s is earlier than ran_at %s" % (link["produced_at"]["raw"], link["ran_at"]["raw"])
                else:
                    found = outcome["reason"]
                links_entries.append(make_entry("COMP-RECONSTRUCTED", part, step["step_id"], found))
        for record in step_result["predicate_mismatch_links"]:
            link = vb["links"][record["link_index"]]
            links_entries.append(make_entry("LINK-PREDICATE", part, step["step_id"], "link predicate_type %s differs from layout step predicate_type %s for step %s" % (link["predicate_type"], step["predicate_type"], step["step_id"])))
        if step["step_id"] not in claimed and claim is not ABSENT:
            links_entries.append(make_entry("COMP-NO-LINK", "stage", step["step_id"], "the step is not claimed"))
        if not step_result["matching_links"] and not suppress_no_link:
            links_entries.append(make_entry("COMP-NO-LINK", part, step["step_id"], "no matching link"))
        if step_result["multi_link"]:
            anomaly_entries.append(make_entry("ANOM-MULTI-LINK", part, step["step_id"], "%d matching links stand for step %s" % (len(step_result["matching_links"]), step["step_id"])))
    if claim is not ABSENT:
        for step_id in matching["claimed_steps_naming_no_layout_step"]:
            links_entries.append(make_entry("COMP-NO-LINK", "stage", step_id, "it names no layout step"))
    links_value = "fail" if links_entries else "pass"

    artifact_entries = []
    per_artifact = []
    presented_links = vb["links"] if vb["links"] is not ABSENT else []
    covered_pairs = set()
    for link in presented_links:
        for subject in link["subject_artifacts"]:
            covered_pairs.add((subject["artifact_id"], subject["sha256"]["raw"]))
    for artifact in vb["layout"]["required_artifacts"]:
        artifact_file = read_artifact(artifact, artifact["properties"])
        coverage = "pass"
        coverage_found = None
        covered = (artifact["artifact_id"], artifact["sha256"]["raw"]) in covered_pairs
        if not covered:
            coverage = "fail"
            coverage_found = "no presented link names this artifact with the stated digest"
        standing = []
        if not artifact_file["readable"]:
            standing.append({"test": "readable", "outcome": "fail"})
            standing.append({"test": "size", "outcome": "not run"})
            standing.append({"test": "digest", "outcome": "not run"})
            artifact_entries.append(make_entry("COMP-ARTIFACT", "stage", artifact["artifact_id"], "the artifact file at %s cannot be read" % artifact["path"]))
        else:
            standing.append({"test": "readable", "outcome": "pass"})
            if artifact_file["size"] > ARTIFACT_BYTE_LIMIT:
                standing.append({"test": "size", "outcome": "fail"})
                artifact_entries.append(make_entry("COMP-ARTIFACT", "stage", artifact["artifact_id"], "the artifact file is %d bytes, over the limit of %d bytes" % (artifact_file["size"], ARTIFACT_BYTE_LIMIT)))
            else:
                standing.append({"test": "size", "outcome": "pass"})
            if artifact_file["sha256"] is None:
                standing.append({"test": "digest", "outcome": "not run"})
            elif artifact_file["sha256"] != artifact["sha256"]["raw"]:
                standing.append({"test": "digest", "outcome": "fail"})
                artifact_entries.append(make_entry("COMP-ARTIFACT", "stage", artifact["artifact_id"], "the file digest %s differs from the stated digest %s" % (artifact_file["sha256"], artifact["sha256"]["raw"])))
            else:
                standing.append({"test": "digest", "outcome": "pass"})
        if coverage == "fail":
            artifact_entries.append(make_entry("COMP-ARTIFACT", "stage", artifact["artifact_id"], coverage_found))
        property_outcomes = []
        property_blocked = any(item["outcome"] == "fail" and item["test"] in ("readable", "digest") for item in standing)
        if not property_blocked:
            for prop in artifact["properties"]:
                outcome = evaluate_property(prop, artifact_file)
                property_outcomes.append({"kind": prop["kind"], "outcome": outcome})
                if outcome == "fail":
                    artifact_entries.append(make_entry("COMP-PROPERTY", "stage", artifact["artifact_id"], "property %s fails for artifact %s" % (prop["kind"], artifact["artifact_id"])))
                elif outcome == "unsupported":
                    artifact_entries.append(make_entry("COMP-UNSUPPORTED-PROPERTY", "stage", artifact["artifact_id"], "property kind %s for artifact %s is not an evaluated kind" % (prop["kind"], artifact["artifact_id"])))
        per_artifact.append({"artifact_id": artifact["artifact_id"], "coverage_outcome": coverage, "standing_outcomes": standing, "property_outcomes": property_outcomes})
    artifacts_value = "fail" if artifact_entries else "pass"

    ledger_entries_list = []
    per_element = []
    if claim is not ABSENT:
        known_ids = set()
        if vb["ledger_entries"] is not ABSENT:
            known_ids = {entry["entry_id"] for entry in vb["ledger_entries"]}
        for element in claim["ledger_claims"]:
            if element in known_ids:
                per_element.append({"entry_id": element, "outcome": "pass"})
            else:
                per_element.append({"entry_id": element, "outcome": "fail"})
                ledger_entries_list.append(make_entry("COMP-LEDGER", "stage", element, "no ledger entry with entry_id %s stands" % element))
    ledger_value = "fail" if ledger_entries_list else "pass"

    return {
        "check": "fail" if (links_value == "fail" or artifacts_value == "fail" or ledger_value == "fail") else "pass",
        "links": {"value": links_value, "entries": links_entries, "anomaly_entries": anomaly_entries},
        "artifacts": {"value": artifacts_value, "per_artifact": per_artifact, "entries": artifact_entries},
        "ledger": {"value": ledger_value, "per_element": per_element, "entries": ledger_entries_list},
    }


# Shared blocks, composer, renderers (plan parts 1.16 to 1.19)


def header_lines(vb, outcome, consequence_text, verifier):
    if vb["layout"] is ABSENT:
        stage_text = "absent"
    else:
        stage_text = vb["layout"]["stage_id"]
    gate_context = None
    if vb["claim"] is not ABSENT:
        gate_context = vb["claim"]["gate_context"]
    return [
        "tool=" + TOOL_NAME + " version=" + VERSION,
        "stage=" + render_value(stage_text),
        "outcome=" + outcome,
        "consequence=" + consequence_text,
        "context=" + render_value(gate_context if gate_context else "none"),
    ]


def provenance_lines(vb, verifier):
    if vb["spawn_records"] is ABSENT:
        exporter_line = "exporter=absent exported_at=absent scoping=absent"
        source_line = "source_database=absent"
    else:
        spawn = vb["spawn_records"]
        exporter_line = "exporter=%s exported_at=%s scoping=%s" % (render_value(spawn["exporter"]), render_value(spawn["exported_at"]["raw"]), render_value(spawn["scoping"]["method"]))
        source_line = "source_database=%s" % render_value(spawn["source_database"])
    present = ", ".join(vb["sections_present"]) if vb["sections_present"] else "none"
    absent = ", ".join(vb["sections_absent"]) if vb["sections_absent"] else "none"
    lines = [
        "bundle_sha256=" + vb["bundle_sha256"],
        "verifier=" + render_value(verifier),
        exporter_line,
        source_line,
        "sections present: " + present,
        "sections absent: " + absent,
    ]
    if vb["push_record"] is not ABSENT:
        push = vb["push_record"]
        lines.append("push: repo=%s verified_by=%s verified_at=%s origin=api-verification at assembly" % (render_value(push["repo"]), render_value(push["verified_by"]), render_value(push["verified_at"]["raw"])))
    return lines


def entry_sort_key(entry):
    group_rank = {"stage": 0, "part1": 1, "part2": 2}[entry["part"]]
    if entry["code"] == "ANOM-MULTI-LINK":
        blocking = 4
    elif entry["consequence"] == "UNVERIFIABLE":
        blocking = 0
    elif entry["check"] == "chain":
        blocking = 1
    elif entry["check"] == "authenticity":
        blocking = 2
    elif entry["check"] == "completeness":
        blocking = 3
    else:
        blocking = 0
    return (group_rank, blocking, entry["code"], entry["subject"], entry["_creation"])


def select_step_values(vb, matching):
    selected = {}
    if vb["links"] is ABSENT:
        return selected
    for step_result in matching["steps"]:
        step = step_result["step"]
        chosen = None
        if step_result["matching_links"]:
            chosen = step_result["matching_links"][0]
        else:
            for record in step_result["presented_links"]:
                if record["authenticity_outcome"] == "pass":
                    chosen = record
                    break
        fallback = None
        if chosen is None and step_result["presented_links"]:
            fallback = step_result["presented_links"][0]
        recorded = "none"
        if chosen is not None and chosen["recorded_at_for_report"] is not None:
            recorded = chosen["recorded_at_for_report"]
        repub_link = chosen if chosen is not None else fallback
        show_repub = False
        repub_value = "none"
        if repub_link is not None and not repub_link["seat_stands_in_advance_layout"]:
            show_repub = True
            if repub_link["governing_republication"] is not None:
                repub_value = repub_link["governing_republication"]["raw"]
        selected[step["step_id"]] = {"recorded": recorded, "show_republished": show_repub, "republished": repub_value}
    return selected


def render_report(model):
    vb = model["vb"]
    lines = []
    lines.extend(header_lines(vb, model["outcome"], model["consequence_text"], model["verifier"]))
    checks = model["checks"]
    lines.append("authenticity: " + checks["authenticity"].replace("_", " "))
    lines.append("chain: " + checks["chain"].replace("_", " "))
    lines.append("completeness: " + checks["completeness"].replace("_", " "))
    lines.append("  links: " + model["subresults"]["links"])
    lines.append("  artifacts: " + model["subresults"]["artifacts"])
    lines.append("  ledger: " + model["subresults"]["ledger"])
    lines.extend(provenance_lines(vb, model["verifier"]))
    lines.append(STRENGTH_LINE)
    lines.append("boundary: " + model["boundary_status"])
    seat_parts = model["seat_parts"]
    matching_by_id = {item["step"]["step_id"]: item for item in model["matching"]["steps"]} if model["matching"] else {}
    join_by_earlier = {}
    if model["chain_result"]:
        for join in model["chain_result"]["join_outcomes"]:
            join_by_earlier.setdefault(join["earlier_step"], []).append(join)
    selected = model["selected"]
    layout_steps = vb["layout"]["steps"] if vb["layout"] is not ABSENT else []
    for part_name, heading in (("part1", "part 1: advance layout seats"), ("part2", "part 2: seats added under R-50")):
        lines.append(heading)
        part_steps = [step for step in layout_steps if seat_parts.get(step["seat"], "part1") == part_name]
        for step in part_steps:
            step_result = matching_by_id.get(step["step_id"])
            authenticity = step_result["per_step_authenticity"] if step_result else "fail"
            matching_value = step_result["per_step_matching"] if step_result else "fail"
            values = selected.get(step["step_id"], {"recorded": "none", "show_republished": False, "republished": "none"})
            line = "step %s seat=%s recorded=%s" % (render_value(step["step_id"]), render_value(step["seat"]), render_value(values["recorded"]))
            if part_name == "part2" and values["show_republished"]:
                line += " republished=" + render_value(values["republished"])
            line += " authenticity=%s matching=%s" % (authenticity, matching_value)
            lines.append(line)
        for step in part_steps:
            for join in join_by_earlier.get(step["step_id"], []):
                lines.append("join %s -> %s: %s" % (render_value(join["earlier_step"]), render_value(join["later_step"]), join["result"]))
    entries = model["entries"]
    if model["outcome"] == "FAIL" or any(entry["code"] == "ANOM-MULTI-LINK" for entry in entries):
        for entry in entries:
            lines.append("  - code=%s subject=%s" % (entry["code"], render_value(entry["subject"])))
            lines.append("    check=" + entry["check"])
            lines.append("    expected=" + render_value(entry["expected"]))
            lines.append("    found=" + render_value(entry["found"]))
            lines.append("    consequence=" + entry["consequence"])
            lines.append("    cure=" + render_value(entry["cure"]))
        lines.append(STRENGTH_LINE)
    return "\n".join(lines) + "\n"


def render_barred(vb, verifier, bar_word):
    lines = []
    lines.extend(header_lines(vb, "BARRED", "none", verifier))
    lines.append("barred: verifier is " + bar_word)
    lines.extend(provenance_lines(vb, verifier))
    lines.append(STRENGTH_LINE)
    return "\n".join(lines) + "\n"


def render_closure(vb, verifier):
    lines = [
        "tool=" + TOOL_NAME,
        "stage=" + render_value(vb["layout"]["stage_id"]),
        "verifier=" + render_value(verifier),
        "bundle_sha256=" + vb["bundle_sha256"],
        "grade=L2",
        STRENGTH_LINE,
        SCOPE_PARAGRAPH,
    ]
    return "\n".join(lines) + "\n"


def write_outputs(pairs):
    for path_text, text in pairs:
        try:
            with open(path_text, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
                handle.flush()
        except (OSError, UnicodeEncodeError):
            return path_text
    return None


def delivery_failure(path_text):
    write_stderr("three-checks: delivery failure: cannot write " + render_value(path_text) + "\n")
    return 2


# Orchestration (plan part 1.20)


def main(argv):
    parsed_args, usage_error = parse_arguments(argv)
    if usage_error is not None:
        return usage_failure(usage_error)
    bundle_supplied, report_path, results_path, closure_path, verifier = parsed_args
    bundle_resolved = resolved(bundle_supplied)
    output_resolved = [resolved(report_path), resolved(results_path), resolved(closure_path)]
    output_supplied = [report_path, results_path, closure_path]
    for supplied, res in zip(output_supplied, output_resolved):
        if res == bundle_resolved:
            return usage_failure("output path " + render_value(supplied) + " names an input file")
    bundle_identity = file_identity(bundle_resolved)
    if bundle_identity is not None:
        for supplied, res in zip(output_supplied, output_resolved):
            if file_identity(res) == bundle_identity:
                return usage_failure("output path " + render_value(supplied) + " names an input file")
    for first in range(3):
        for second in range(first + 1, 3):
            if output_resolved[first] == output_resolved[second]:
                return usage_failure("output paths " + render_value(output_supplied[first]) + " and " + render_value(output_supplied[second]) + " name the same file")

    top, dup_paths, bundle_digest, gate_error = read_and_parse(bundle_supplied)
    if gate_error is not None:
        write_stderr("three-checks: input error: " + gate_error + "\n")
        return 2

    bundle_dir = bundle_resolved.parent
    validator = validate_bundle(top, dup_paths, bundle_dir)
    if validator.has_errors(dup_paths):
        for line in validator.ordered_lines(dup_paths):
            write_stderr("three-checks: input error: " + line + "\n")
        return 2

    vb = build_validated(top, bundle_digest, bundle_dir)

    if vb["layout"] is not ABSENT:
        artifact_resolved = [Path(artifact["resolved_path"]) for artifact in vb["layout"]["required_artifacts"]]
        artifact_identities = set()
        for artifact_path in artifact_resolved:
            identity = file_identity(artifact_path)
            if identity is not None:
                artifact_identities.add(identity)
        for supplied, res in zip(output_supplied, output_resolved):
            if res in artifact_resolved or file_identity(res) in artifact_identities:
                return usage_failure("output path " + render_value(supplied) + " names an input file")

    absence = compute_absence_effects(vb)

    bar_word = None
    if vb["links"] is not ABSENT:
        if any(link["performer_spawn_id"] == verifier for link in vb["links"]):
            bar_word = "performer"
    if bar_word is None and vb["identities"] is not ABSENT:
        identities = vb["identities"]
        if verifier == identities["coordinator"]:
            bar_word = "coordinator"
        elif verifier == identities["commissioner_stage"]:
            bar_word = "commissioner_stage"
        elif verifier == identities["commissioner_work"]:
            bar_word = "commissioner_work"
    if bar_word is not None:
        barred_text = render_barred(vb, verifier, bar_word)
        failed_path = write_outputs([(report_path, barred_text)])
        if failed_path is not None:
            return delivery_failure(failed_path)
        return 4

    _creation_counter["value"] = 0
    all_entries = []
    for section in absence["absent_required"]:
        all_entries.append(make_entry("ABSENT-SECTION", "stage", section, "section %s is absent" % section, "UNVERIFIABLE"))

    auth_can_run = not absence["authenticity_cannot_run"]
    records = []
    details = []
    seat_parts_input = {}
    seat_parts = {}
    export_facts = {"duplicated_export_identities": [], "unbound_unparseable_creation_facts": []}
    authenticity_result = None
    if vb["layout"] is not ABSENT:
        if auth_can_run:
            records, details, seat_parts_input = build_authorisation_records(vb)
            export_facts = scan_export(vb)
        seat_parts = seat_part_map(vb, seat_parts_input)
        if auth_can_run:
            authenticity_result = run_authenticity(vb, records, details, export_facts, seat_parts)
            all_entries.extend(authenticity_result["entries"])

    matching = None
    if vb["layout"] is not ABSENT:
        matching = build_matching(vb, records)

    chain_result = None
    boundary_status = "not applicable"
    if vb["layout"] is not ABSENT:
        suppress_joins = absence["chain_forced_fail"]
        chain_result = run_chain(vb, matching, seat_parts, suppress_joins)
        all_entries.extend(chain_result["entries"])
        boundary_status = chain_result["boundary_outcome"]["status"]

    completeness_result = None
    if vb["layout"] is not ABSENT and not absence["completeness_cannot_run"]:
        suppress_no_link = absence["chain_forced_fail"] or vb["links"] is ABSENT
        completeness_result = run_completeness(vb, matching, seat_parts, suppress_no_link)
        all_entries.extend(completeness_result["links"]["entries"])
        all_entries.extend(completeness_result["links"]["anomaly_entries"])
        all_entries.extend(completeness_result["artifacts"]["entries"])
        all_entries.extend(completeness_result["ledger"]["entries"])

    if absence["authenticity_cannot_run"]:
        auth_value = "cannot_run"
    elif authenticity_result is not None:
        auth_value = authenticity_result["check"]
    else:
        auth_value = "pass"
    if absence["chain_cannot_run"]:
        chain_value = "cannot_run"
    elif absence["chain_forced_fail"]:
        chain_value = "fail"
    elif chain_result is not None:
        chain_value = chain_result["check"]
    else:
        chain_value = "pass"
    if absence["completeness_cannot_run"]:
        comp_value = "cannot_run"
        subresults = {"links": "fail", "artifacts": "fail", "ledger": "fail"}
    elif completeness_result is not None:
        subresults = {
            "links": "fail" if (completeness_result["links"]["value"] == "fail" or absence["chain_forced_fail"] or vb["links"] is ABSENT) else "pass",
            "artifacts": completeness_result["artifacts"]["value"],
            "ledger": completeness_result["ledger"]["value"],
        }
        comp_value = "fail" if "fail" in subresults.values() else "pass"
    else:
        subresults = {"links": "fail", "artifacts": "fail", "ledger": "fail"}
        comp_value = "fail"

    checks = {"authenticity": auth_value, "chain": chain_value, "completeness": comp_value}
    ordered_entries = sorted(all_entries, key=entry_sort_key)
    has_unverifiable = any(entry["consequence"] == "UNVERIFIABLE" for entry in ordered_entries)
    checks_pass = auth_value == "pass" and chain_value == "pass" and comp_value == "pass"
    if checks_pass and not absence["identities_cap"]:
        outcome = "PASS"
        consequence = None
        exit_status = 0
    else:
        outcome = "FAIL"
        if has_unverifiable or absence["identities_cap"]:
            consequence = "UNVERIFIABLE"
            exit_status = 3
        else:
            consequence = "PARTIAL"
            exit_status = 1

    selected = select_step_values(vb, matching) if matching is not None else {}
    model = {
        "vb": vb,
        "verifier": verifier,
        "outcome": outcome,
        "consequence_text": consequence if consequence else "none",
        "checks": checks,
        "subresults": subresults,
        "boundary_status": boundary_status,
        "seat_parts": seat_parts,
        "matching": matching,
        "chain_result": chain_result,
        "selected": selected,
        "entries": ordered_entries,
    }
    report_text = render_report(model)

    if vb["layout"] is ABSENT:
        stage_id_value = None
    else:
        stage_id_value = vb["layout"]["stage_id"]
    if vb["spawn_records"] is ABSENT:
        provenance = {"exporter": None, "exported_at": None, "scoping_method": None, "source_database": None}
    else:
        spawn = vb["spawn_records"]
        provenance = {"exporter": spawn["exporter"], "exported_at": spawn["exported_at"]["raw"], "scoping_method": spawn["scoping"]["method"], "source_database": spawn["source_database"]}
    provenance["verifier"] = verifier
    provenance["sections_present"] = vb["sections_present"]
    provenance["sections_absent"] = vb["sections_absent"]
    if vb["push_record"] is ABSENT:
        provenance["push"] = None
    else:
        push = vb["push_record"]
        provenance["push"] = {"repo": push["repo"], "verified_by": push["verified_by"], "verified_at": push["verified_at"]["raw"]}
    results_obj = {
        "tool": TOOL_NAME,
        "version": VERSION,
        "stage_id": stage_id_value,
        "bundle_sha256": bundle_digest,
        "outcome": outcome,
        "consequence": consequence,
        "gate_context": vb["claim"]["gate_context"] if vb["claim"] is not ABSENT else None,
        "checks": checks,
        "subresults": subresults,
        "provenance": provenance,
        "discrepancies": [public_entry(entry) for entry in ordered_entries],
    }
    results_text = json.dumps(results_obj, ensure_ascii=False, indent=2) + "\n"
    try:
        results_text.encode("utf-8")
    except UnicodeEncodeError:
        results_text = json.dumps(results_obj, ensure_ascii=True, indent=2) + "\n"

    pairs = [(report_path, report_text), (results_path, results_text)]
    if outcome == "PASS":
        pairs.append((closure_path, render_closure(vb, verifier)))
    failed_path = write_outputs(pairs)
    if failed_path is not None:
        return delivery_failure(failed_path)
    return exit_status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
