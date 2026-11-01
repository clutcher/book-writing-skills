#!/usr/bin/env python3
import argparse
import datetime
import json
import math
import re
import sys
sys.dont_write_bytecode = True
from dataclasses import dataclass, field
from pathlib import Path

from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport,
                          add_output_arguments, run_main, tool_failed)

DECIDED_NO_CHANGE = "DECIDED / no change"
DECIDED_CHANGED = "DECIDED / changed"
DECIDED_NOT_A_FINDING = "DECIDED / not a finding"
OPEN_FIX_OWED = "OPEN / fix owed"
OPEN_DECISION_OWED = "OPEN / decision owed"
OPEN_UNDISCUSSED = "OPEN / undiscussed"

STATUSES = (DECIDED_NO_CHANGE, DECIDED_CHANGED, DECIDED_NOT_A_FINDING,
            OPEN_FIX_OWED, OPEN_DECISION_OWED, OPEN_UNDISCUSSED)

FIELD_STATUS = "Status"
FIELD_ALIASES = "Aliases"
FIELD_IDEA = "Idea"
FIELD_DECISION = "Decision"
FIELD_CHANGE = "Change"
FIELD_WHY = "Why"
FIELD_DECIDED = "Decided"
FIELD_REFS = "Refs"
FIELD_KEYWORDS = "Keywords"
FIELD_MERGED = "Merged"

FIELD_ORDER = (FIELD_STATUS, FIELD_ALIASES, FIELD_IDEA, FIELD_DECISION, FIELD_CHANGE,
               FIELD_WHY, FIELD_DECIDED, FIELD_REFS, FIELD_KEYWORDS, FIELD_MERGED)
REQUIRED_FIELDS = (FIELD_IDEA, FIELD_DECISION, FIELD_DECIDED)
REQUIRED_WHEN_DECIDED = (FIELD_WHY,)

ENTRY_ID = r"(?:[A-Za-z]+-?)?\d+(?:\.\d+)*"
_ENTRY_HEADING = re.compile(rf"^##\s+(?:\[({ENTRY_ID})\]|({ENTRY_ID})[.:]?)(?:\s+(.*?))?\s*$")
_ID_LIKE_HEADING = re.compile(r"^##\s+\[?[A-Za-z]*-?\d")
_SECTION_HEADING = re.compile(r"^#\s+(.*?)\s*$")
_FIELD_LINE = re.compile(r"^-\s+\*\*([^*\n]+?)[:.]\*\*[ \t]*(.*)$")
_FENCE = re.compile(r"^\s*```")
_STATUS_TEXT = re.compile(r"\b(DECIDED|OPEN)\s*[/:—–-]\s*"
                          r"(no change|changed|not a finding|fix owed|decision owed|undiscussed)",
                          re.I)
_BACKTICKED = re.compile(r"`([^`]+)`")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")

INDEX_HEADING = "## Index"
DETAILS_HEADING = "## Details"
INDEX_COLUMNS = ("Id", "Status", "Title")

STOPWORDS = frozenset("""
a an the and or but if then than that this these those there their them they it its
is are was were be been being do does did done has have had having of in on at by for
with from into onto upon about as to too not no nor so such very can could should would
may might must will shall which who whom whose what when where why how all any each
every some more most other own same only also just over under again further once here
book chapter section page line text reader readers says said one two three
""".split())


@dataclass
class RunPolicy:
    status: str
    action: str
    may_report: bool
    rule: str


POLICIES = {
    DECIDED_NO_CHANGE: RunPolicy(DECIDED_NO_CHANGE, "silent", False,
                                 "Do not report. To dispute it, cite the entry in one "
                                 "sentence; do not argue it again."),
    DECIDED_CHANGED: RunPolicy(DECIDED_CHANGED, "silent", False,
                               "Do not report. To dispute it, cite the entry in one "
                               "sentence; do not argue it again."),
    DECIDED_NOT_A_FINDING: RunPolicy(DECIDED_NOT_A_FINDING, "silent", False,
                                     "Do not report. To dispute it, cite the entry in one "
                                     "sentence; do not argue it again."),
    OPEN_FIX_OWED: RunPolicy(OPEN_FIX_OWED, "regression-check", True,
                             "Report as a regression check: cite the entry and the fix "
                             "already agreed."),
    OPEN_DECISION_OWED: RunPolicy(OPEN_DECISION_OWED, "reminder", True,
                                  "Report only as a reminder that an answer is owed. Do "
                                  "not argue the options again."),
    OPEN_UNDISCUSSED: RunPolicy(OPEN_UNDISCUSSED, "normal", True,
                                "Report normally, citing the entry so its history travels "
                                "with the finding."),
}


def normalise_status(text):
    if not text:
        return None
    found = _STATUS_TEXT.search(text)
    if not found:
        return None
    return f"{found.group(1).upper()} / {found.group(2).lower()}"


def run_policy(status):
    return POLICIES[status]


def canonical_field_name(name):
    cleaned = name.strip()
    for canonical in FIELD_ORDER:
        if cleaned == canonical or cleaned.lower().startswith(canonical.lower() + " "):
            return canonical
    return cleaned


@dataclass
class DecisionField:
    name: str
    written_name: str
    value: str
    line_number: int


@dataclass
class Decision:
    id: str
    title: str
    status: str
    line_number: int
    end_line: int
    fields: list = field(default_factory=list)
    notes: str = ""

    def field(self, name):
        found = next((item for item in self.fields if item.name == name), None)
        return found.value if found else None

    @property
    def aliases(self):
        return parse_aliases(self.field(FIELD_ALIASES) or "")

    @property
    def keywords(self):
        text = self.field(FIELD_KEYWORDS) or ""
        return [word.strip().lower() for word in re.split(r"[,;]", text) if word.strip()]

    @property
    def is_decided(self):
        return bool(self.status) and self.status.startswith("DECIDED")

    @property
    def policy(self):
        return POLICIES.get(self.status)


@dataclass
class Decisions:
    path: Path
    text: str
    entries: list
    unread_headings: list = field(default_factory=list)
    newline: str = "\n"

    @property
    def lines(self):
        return self.text.split("\n")

    def entry(self, entry_id):
        return next((item for item in self.entries if item.id == entry_id), None)

    def with_status(self, status):
        return [item for item in self.entries if item.status == status]


def parse_aliases(text):
    backticked = _BACKTICKED.findall(text)
    if backticked:
        return [alias.strip() for alias in backticked
                if alias.strip() and alias.strip().lower() != "none"]
    parts = re.split(r"\s+-\s+|[,;]", text)
    aliases = []
    for part in parts:
        words = re.sub(r"\([^)]*\)", "", part).split()
        if words and words[0].lower() not in ("none", "-"):
            aliases.append(words[0])
    return aliases


def parse_decisions(text, path=None):
    lines = text.split("\n")
    entries = []
    current = None
    current_field = None
    fenced = False
    notes = []
    unread_headings = []

    def close(end_index):
        nonlocal current, current_field, notes
        if current is not None:
            current.end_line = end_index
            current.notes = "\n".join(notes).strip()
            entries.append(current)
        current, current_field, notes = None, None, []

    for index, line in enumerate(lines):
        number = index + 1
        if _FENCE.match(line):
            fenced = not fenced
            if current is not None:
                notes.append(line)
            continue
        if fenced:
            if current is not None:
                notes.append(line)
            continue
        if _SECTION_HEADING.match(line):
            close(index)
            continue
        heading = _ENTRY_HEADING.match(line)
        if heading:
            close(index)
            entry_id = heading.group(1) or heading.group(2)
            title = (heading.group(3) or "").strip()
            current = Decision(entry_id, title, None, number, number)
            continue
        if line.startswith("## "):
            close(index)
            if _ID_LIKE_HEADING.match(line):
                unread_headings.append((number, line.strip()))
            continue
        if current is None:
            continue
        found_field = _FIELD_LINE.match(line)
        if found_field:
            written = found_field.group(1).strip()
            current_field = DecisionField(canonical_field_name(written), written,
                                          found_field.group(2).strip(), number)
            current.fields.append(current_field)
            if current_field.name == FIELD_STATUS:
                explicit = normalise_status(current_field.value)
                current.status = explicit or current_field.value.strip()
            continue
        if current_field is not None and line.strip() and (line.startswith((" ", "\t"))
                                                           or not line.startswith("- ")):
            current_field.value = (current_field.value + " " + line.strip()).strip()
            continue
        if not line.strip():
            current_field = None
            continue
        notes.append(line)
    close(len(lines))
    return Decisions(Path(path) if path else None, text, entries, unread_headings)


def read_decisions(path):
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as handle:
        written = handle.read()
    decisions = parse_decisions(written.replace("\r\n", "\n"), path)
    decisions.newline = "\r\n" if "\r\n" in written else "\n"
    return decisions


def write_decisions_text(path, text, newline="\n"):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\r\n", "\n").replace("\n", newline))


CHECK_CLASSES = {
    "no-status": DEFECT,
    "unknown-status": DEFECT,
    "duplicate-id": DEFECT,
    "unread-heading": DEFECT,
    "missing-field": DEFECT,
    "empty-field": DEFECT,
    "unknown-field": DEFECT,
    "duplicate-field": DEFECT,
    "index-missing": DEFECT,
    "index-stale": DEFECT,
    "fix-owed": INFORMATIONAL,
    "decision-owed": INFORMATIONAL,
    "undiscussed": INFORMATIONAL,
    "shared-alias": ADVISORY,
    "undated-decision": ADVISORY,
}

_OPEN_CLASS = {OPEN_FIX_OWED: "fix-owed", OPEN_DECISION_OWED: "decision-owed",
               OPEN_UNDISCUSSED: "undiscussed"}


def required_fields(entry):
    if entry.is_decided:
        return REQUIRED_FIELDS + REQUIRED_WHEN_DECIDED
    return REQUIRED_FIELDS


def check_decisions(decisions, report):
    seen_ids = {}
    alias_owners = {}
    for number, heading in decisions.unread_headings:
        report.add(heading, "unread-heading",
                   f"line {number}: looks like an entry but is not read as one; write it as "
                   f"'## D-1 Short title'")
    for entry in decisions.entries:
        if entry.id in seen_ids:
            report.add(entry.id, "duplicate-id",
                       f"line {entry.line_number}: also used at line {seen_ids[entry.id]}")
        seen_ids.setdefault(entry.id, entry.line_number)

        if entry.status is None:
            report.add(entry.id, "no-status", f"line {entry.line_number}: no Status field")
        elif entry.status not in STATUSES:
            report.add(entry.id, "unknown-status", f"'{entry.status}' is not one of: "
                                                   + "; ".join(STATUSES))
        if entry.status in _OPEN_CLASS:
            report.add(entry.id, _OPEN_CLASS[entry.status], entry.title)

        names = [item.name for item in entry.fields]
        for name in required_fields(entry):
            if name not in names:
                report.add(entry.id, "missing-field", f"no {name} field")
        for item in entry.fields:
            if item.name not in FIELD_ORDER:
                report.add(entry.id, "unknown-field",
                           f"line {item.line_number}: '{item.written_name}' is not a field "
                           f"name ({', '.join(FIELD_ORDER)})")
            elif not item.value:
                report.add(entry.id, "empty-field", f"line {item.line_number}: {item.name}")
        for name in sorted({name for name in names if names.count(name) > 1}):
            report.add(entry.id, "duplicate-field", f"{name} appears {names.count(name)} times")
        decided = entry.field(FIELD_DECIDED)
        if decided and entry.is_decided and not _DATE.search(decided):
            report.add(entry.id, "undated-decision", "the Decided field carries no YYYY-MM-DD date")
        for alias in dict.fromkeys(entry.aliases):
            alias_owners.setdefault(alias, []).append(entry.id)
    for alias, owners in sorted(alias_owners.items()):
        if len(owners) > 1:
            report.add(alias, "shared-alias", "alias on several entries: " + ", ".join(owners))
    return report


def render_index(decisions):
    lines = [INDEX_HEADING, "", "| " + " | ".join(INDEX_COLUMNS) + " |",
             "|" + "---|" * len(INDEX_COLUMNS)]
    for entry in decisions.entries:
        cells = (entry.id, entry.status or "-", entry.title)
        lines.append("| " + " | ".join(_table_cell(cell) for cell in cells) + " |")
    return "\n".join(lines)


def _table_cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def _heading_lines(lines):
    fenced = False
    for index, line in enumerate(lines):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            yield index, line


def _index_section(lines):
    headings = list(_heading_lines(lines))
    for position, (index, line) in enumerate(headings):
        if line.rstrip() == INDEX_HEADING:
            end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
            return index, end
    return None


def written_index(decisions):
    lines = decisions.lines
    section = _index_section(lines)
    if section is None:
        return None
    start, end = section
    return "\n".join(lines[start:end]).strip()


def index_is_current(decisions):
    return written_index(decisions) == render_index(decisions)


def _details_insertion_point(lines, decisions):
    for index, line in _heading_lines(lines):
        if line.rstrip() == DETAILS_HEADING:
            return index, False
    if not decisions.entries:
        return len(lines), True
    point = decisions.entries[0].line_number - 1
    while point > 0:
        above = lines[point - 1]
        if not above.strip() or above.strip() == "---":
            point -= 1
        elif _SECTION_HEADING.match(above) and point > 1:
            point -= 1
        else:
            break
    return point, True


def with_current_index(text):
    decisions = parse_decisions(text)
    lines = text.split("\n")
    index_lines = render_index(decisions).split("\n") + [""]
    section = _index_section(lines)
    if section is not None:
        start, end = section
        lines[start:end] = index_lines
        return "\n".join(lines)
    point, needs_details = _details_insertion_point(lines, decisions)
    new_lines = [""] if point > 0 and lines[point - 1].strip() else []
    new_lines += index_lines
    if needs_details:
        new_lines.append(DETAILS_HEADING)
        if point >= len(lines) or lines[point].strip():
            new_lines.append("")
    lines[point:point] = new_lines
    return "\n".join(lines).rstrip("\n") + "\n"


def check_index(decisions, report):
    written = written_index(decisions)
    if written is None:
        report.add("index", "index-missing", "no index; --fix builds it")
    elif written != render_index(decisions):
        report.add("index", "index-stale",
                   "the index does not match the entries; --fix rebuilds it")
    return report


@dataclass
class Match:
    entry: Decision
    score: float
    aliases: list
    phrases: list
    words: list

    @property
    def reason(self):
        parts = []
        if self.aliases:
            parts.append("alias " + ", ".join(self.aliases))
        if self.phrases:
            parts.append("keyword " + ", ".join(self.phrases))
        if self.words:
            parts.append("words " + ", ".join(self.words[:8]))
        return "; ".join(parts)


def words_of(text):
    words = []
    for word in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text.lower()):
        word = word.strip("'-")
        if word in STOPWORDS or len(word) < 3:
            continue
        for ending in ("ing", "s"):
            if (word.endswith(ending) and not word.endswith("ss")
                    and len(word) - len(ending) >= 4):
                word = word[: -len(ending)]
                break
        words.append(word)
    return words


def _alias_in_text(alias, text):
    pattern = rf"(?<![\w.-]){re.escape(alias)}(?![\w-]|\.\d)"
    return re.search(pattern, text, re.I) is not None


def _entry_word_weights(entry):
    weights = {}
    for word in words_of(entry.field(FIELD_IDEA) or ""):
        weights[word] = max(weights.get(word, 0), 1.0)
    for word in words_of(entry.title):
        weights[word] = max(weights.get(word, 0), 2.0)
    for word in words_of(" ".join(entry.keywords)):
        weights[word] = max(weights.get(word, 0), 3.0)
    return weights


def match_finding(decisions, finding, threshold=0.25, limit=5, ignore_alias_pattern=None):
    ignored = re.compile(ignore_alias_pattern) if isinstance(ignore_alias_pattern, str) \
        else ignore_alias_pattern
    entries = decisions.entries
    weights = {entry.id: _entry_word_weights(entry) for entry in entries}
    document_frequency = {}
    for entry_weights in weights.values():
        for word in entry_weights:
            document_frequency[word] = document_frequency.get(word, 0) + 1
    total = max(len(entries), 1)

    def rarity(word):
        return math.log(1 + total / (1 + document_frequency.get(word, 0)))

    finding_words = set(words_of(finding))
    finding_weight = sum(rarity(word) for word in finding_words) or 1.0
    lowered = finding.lower()
    matches = []
    for entry in entries:
        aliases = [alias for alias in entry.aliases
                   if not (ignored and ignored.fullmatch(alias))
                   and _alias_in_text(alias, finding)]
        phrases = [phrase for phrase in entry.keywords if " " in phrase and phrase in lowered]
        shared = sorted(finding_words & set(weights[entry.id]),
                        key=lambda word: -rarity(word) * weights[entry.id][word])
        score = sum(rarity(word) * weights[entry.id][word] for word in shared) / finding_weight
        score += len(phrases)
        if aliases:
            score += 100.0
        if score >= threshold:
            matches.append(Match(entry, round(score, 3), aliases, phrases, shared))
    matches.sort(key=lambda found: -found.score)
    return matches[:limit] if limit else matches


def format_entry(entry_id, title, values):
    lines = [f"## {entry_id} {title}", ""]
    for name in FIELD_ORDER:
        value = values.get(name)
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, (list, tuple)):
            value = " - ".join(f"`{item}`" for item in value) if name == FIELD_ALIASES \
                else ", ".join(value)
        text_lines = str(value).strip().split("\n")
        lines.append(f"- **{name}:** {text_lines[0]}")
        lines.extend(f"  {line}" for line in text_lines[1:])
    return "\n".join(lines) + "\n"


def next_entry_id(decisions, prefix="D-"):
    numbers = [int(match.group(1)) for entry in decisions.entries
               for match in [re.fullmatch(re.escape(prefix) + r"(\d+)", entry.id)] if match]
    return f"{prefix}{max(numbers, default=0) + 1}"


def append_entry(text, entry_text):
    body = text.rstrip("\n")
    return f"{body}\n\n---\n\n{entry_text}"


def set_status(decisions, entry_id, status):
    entry = decisions.entry(entry_id)
    if entry is None:
        raise KeyError(entry_id)
    lines = decisions.lines
    status_line = f"- **{FIELD_STATUS}:** {status}"
    existing = next((item for item in entry.fields if item.name == FIELD_STATUS), None)
    if existing:
        lines[existing.line_number - 1] = status_line
    elif entry.fields:
        lines.insert(entry.fields[0].line_number - 1, status_line)
    else:
        lines[entry.line_number:entry.line_number] = ["", status_line]
    return "\n".join(lines)


TEMPLATE = """# Decisions

Every idea about this book that was discussed and decided, or is still open. Review runs read only the index (`decisions.py index`), open an entry with `decisions.py show ID`, and never raise a DECIDED item again. `decisions.py check --fix` rebuilds the index. The format is described in the book plugin, `lib/decisions-format.md`.

## Details
"""


def _default_decided(status):
    if status.startswith("DECIDED"):
        return datetime.date.today().isoformat()
    return "None"


def render_template():
    return with_current_index(TEMPLATE)


def _decisions_path(args):
    if args.file:
        return Path(args.file)
    return config_from_args(args).rules.decisions


def _read_input_text(args):
    if args.text_file:
        return Path(args.text_file).read_text(encoding="utf-8")
    if args.text == ["-"] or not args.text:
        return sys.stdin.read()
    return " ".join(args.text)


def _write_or_show(path, new_text, fix, summary, newline="\n"):
    if fix:
        write_decisions_text(path, with_current_index(new_text), newline)
        print(f"{summary}; wrote {path}")
    else:
        print(f"{summary}; dry run, pass --fix to write {path}")
    return 0


def _no_decisions_file(args, path):
    if args.command == "check":
        report = CheckReport("decisions", CHECK_CLASSES)
        report.skip_unless_present(path, "decisions file")
        return report.emit(args.format)
    if args.command in ("index", "match"):
        sys.stderr.write(f"no decisions file at {path}: nothing is decided yet\n")
        return 0
    return tool_failed(f"{path} not found (create it with: decisions.py init --fix)",
                       "decisions")


def _fix_index(path, decisions):
    new_text = with_current_index(decisions.text)
    if new_text != decisions.text:
        write_decisions_text(path, new_text, decisions.newline)
        sys.stderr.write(f"rebuilt the index in {path}\n")
    return read_decisions(path)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read, check, match and write the book's decisions.md.")
    add_config_arguments(parser)
    parser.add_argument("--file",
                        help="decisions.md to use (default: rules.decisions from book.yaml)")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="format problems and a stale or missing "
                                              "index, per check_contract.md")
    add_output_arguments(check)
    check.add_argument("--fix", action="store_true",
                       help="rebuild the index")

    commands.add_parser("index", help="the index (id, status, title), built from the entries")

    listing = commands.add_parser("list", help="one line per entry")
    listing.add_argument("--status", choices=STATUSES)
    listing.add_argument("--json", action="store_true")

    show = commands.add_parser("show", help="one entry as written")
    show.add_argument("id")

    match = commands.add_parser("match", help="entries a finding may repeat, best first")
    match.add_argument("text", nargs="*", help="the finding text; '-' or nothing reads stdin")
    match.add_argument("--text-file", help="read the finding text from this file")
    match.add_argument("--threshold", type=float, default=0.25,
                       help="lowest score shown (default 0.25; an alias match scores 100+)")
    match.add_argument("--limit", type=int, default=5, help="most entries shown (0 = all)")
    match.add_argument("--json", action="store_true")

    commands.add_parser("policy", help="what a review run may do for each status")

    add = commands.add_parser("add", help="a new entry; dry run prints it")
    add.add_argument("--title", required=True)
    add.add_argument("--status", required=True, choices=STATUSES)
    add.add_argument("--id", help="the entry id (default: the next D-n)")
    add.add_argument("--alias", action="append", default=[], help="repeatable")
    add.add_argument("--idea", required=True)
    add.add_argument("--decision", required=True)
    add.add_argument("--change")
    add.add_argument("--why", help="required for a DECIDED status")
    add.add_argument("--decided", help="default: today's date for a DECIDED status, "
                                       "'None' for an OPEN one")
    add.add_argument("--refs")
    add.add_argument("--keywords", help="comma-separated words and phrases")
    add.add_argument("--fix", action="store_true", help="write the entry to the file")

    status = commands.add_parser("set-status", help="change one entry's status")
    status.add_argument("id")
    status.add_argument("status", choices=STATUSES)
    status.add_argument("--fix", action="store_true", help="write the change")

    init = commands.add_parser("init", help="a new, empty decisions.md")
    init.add_argument("--fix", action="store_true", help="write the file")

    args = parser.parse_args(argv)

    try:
        path = _decisions_path(args)
    except ConfigError as error:
        return tool_failed(str(error), "decisions")

    if args.command == "policy":
        for policy in POLICIES.values():
            print(f"{policy.status}\t{policy.action}\t{policy.rule}")
        return 0

    if args.command == "init":
        if path.exists():
            return tool_failed(f"{path} already exists; nothing written", "decisions")
        print(render_template())
        if args.fix:
            path.parent.mkdir(parents=True, exist_ok=True)
        return _write_or_show(path, render_template(), args.fix, "new decisions.md")

    if not path.is_file():
        return _no_decisions_file(args, path)
    decisions = read_decisions(path)

    if args.command == "check":
        if args.fix:
            decisions = _fix_index(path, decisions)
        report = check_decisions(decisions, CheckReport("decisions", CHECK_CLASSES))
        check_index(decisions, report)
        return report.emit(args.format)

    if args.command == "index":
        print(render_index(decisions))
        return 0

    if args.command == "list":
        entries = decisions.with_status(args.status) if args.status else decisions.entries
        if args.json:
            print(json.dumps([{"id": item.id, "title": item.title, "status": item.status,
                               "aliases": item.aliases, "line": item.line_number}
                              for item in entries], indent=2, ensure_ascii=False))
        else:
            for item in entries:
                print(f"{item.id}\t{item.status or '-'}\t{item.title}")
        return 0

    if args.command == "show":
        entry = decisions.entry(args.id)
        if entry is None:
            return tool_failed(f"no entry {args.id}", "decisions")
        print("\n".join(decisions.lines[entry.line_number - 1: entry.end_line]).rstrip())
        return 0

    if args.command == "match":
        finding = _read_input_text(args)
        found = match_finding(decisions, finding, args.threshold, args.limit)
        if args.json:
            print(json.dumps([{
                "id": item.entry.id, "title": item.entry.title, "status": item.entry.status,
                "score": item.score, "reason": item.reason,
                "may_report": item.entry.policy.may_report if item.entry.policy else None,
                "action": item.entry.policy.action if item.entry.policy else None,
            } for item in found], indent=2, ensure_ascii=False))
        else:
            for item in found:
                action = item.entry.policy.action if item.entry.policy else "unknown-status"
                print(f"{item.entry.id}\t{item.entry.status}\t{item.score}\t{action}\t"
                      f"{item.entry.title}\t{item.reason}")
        return 0

    if args.command == "add":
        if args.status.startswith("DECIDED") and not args.why:
            return tool_failed("a DECIDED entry needs --why", "decisions")
        entry_id = args.id or next_entry_id(decisions)
        if decisions.entry(entry_id):
            return tool_failed(f"id {entry_id} is already used", "decisions")
        entry_text = format_entry(entry_id, args.title, {
            FIELD_STATUS: args.status,
            FIELD_ALIASES: args.alias,
            FIELD_IDEA: args.idea,
            FIELD_DECISION: args.decision,
            FIELD_CHANGE: args.change,
            FIELD_WHY: args.why,
            FIELD_DECIDED: args.decided or _default_decided(args.status),
            FIELD_REFS: args.refs,
            FIELD_KEYWORDS: args.keywords,
        })
        print(entry_text)
        return _write_or_show(path, append_entry(decisions.text, entry_text), args.fix,
                              f"new entry {entry_id}", decisions.newline)

    if args.command == "set-status":
        try:
            new_text = set_status(decisions, args.id, args.status)
        except KeyError:
            return tool_failed(f"no entry {args.id}", "decisions")
        entry = decisions.entry(args.id)
        return _write_or_show(path, new_text, args.fix,
                              f"{args.id}: {entry.status or '-'} -> {args.status}",
                              decisions.newline)
    return 0


if __name__ == "__main__":
    run_main(main)
