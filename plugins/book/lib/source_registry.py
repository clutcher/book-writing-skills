#!/usr/bin/env python3
import argparse
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path

from citation_key import ENTRY_HEADING, is_placeholder, sort_position
from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import tool_failed

CONTRACT = "source-registry/1"

TOOL = "source_registry"

SOURCE_FIELDS = frozenset({
    "Full title", "Authors", "Year", "Edition", "Venue", "Publisher",
    "DOI", "ISBN", "Identifier", "DOI/URL",
    "Access URLs", "Access status", "Cached text", "Cached original",
    "Record history", "Fetch note", "Note", "Findings",
})

SOURCE_REQUIRED = ("Full title", "Authors", "Year")

FINDINGS_FIELDS = frozenset({
    "Verified quotes", "Key findings", "Role", "Scope", "Guardrail",
    "Quote origin", "Relation", "Last verified", "Source",
})

POINTER_FROM_SOURCES = "Findings"
POINTER_FROM_FINDINGS = "Source"

FINDINGS_TITLE_WORDS = ("findings", "quotes")


def fields_for(is_findings):
    return FINDINGS_FIELDS if is_findings else SOURCE_FIELDS


_FIELD_LINE = re.compile(r"^\*\*([^*:\n]+):\*\*[ \t]*(.*)$")

FIELD_LINE = _FIELD_LINE
FIELD_LINE_M = re.compile(_FIELD_LINE.pattern, re.M)

_HEADING = re.compile(r"^(#{1,6})\s")

_SECTION_HEADING = re.compile(r"^(#{1,3})\s")

_FENCE = re.compile(r"^```")

ENTRY_SEPARATOR = "\n\n---\n\n"

_SEPARATOR_LINE = "---"


def _fenced_lines(lines):
    inside, states = False, []
    for line in lines:
        if _FENCE.match(line):
            states.append(True)
            inside = not inside
            continue
        states.append(inside)
    return states


def split_separator(raw):
    lines = raw.split("\n")
    body = lines[:-1] if lines and lines[-1] == "" else lines
    fenced = _fenced_lines(body)

    cut = len(body)
    while cut > 0:
        line = body[cut - 1].strip()
        if fenced[cut - 1] or (line and line != _SEPARATOR_LINE):
            break
        cut -= 1
    if cut == 0:
        cut = len(body)

    content = "\n".join(body[:cut])
    return content, raw[len(content):]


def with_separator(raw, separator=ENTRY_SEPARATOR):
    content, _ = split_separator(raw)
    return content + separator


def separator_defects(bank):
    found = []
    preceding = bank.header
    for segment in bank.segments:
        if isinstance(segment, Entry):
            _, written = split_separator(preceding)
            if written != ENTRY_SEPARATOR:
                found.append((segment.key, written))
        preceding = segment.raw
    return found


def show_separator(text):
    return text.replace("\n", "\\n")


class Field:
    __slots__ = ("name", "value", "lineno", "raw")

    def __init__(self, name, value, lineno, raw):
        self.name = name
        self.value = value
        self.lineno = lineno
        self.raw = raw

    @property
    def line_value(self):
        first = self.raw.split("\n", 1)[0]
        found = _FIELD_LINE.match(first)
        return found.group(2).strip() if found else ""

    def __repr__(self):
        return f"Field({self.name!r}, line {self.lineno})"


class Entry:
    __slots__ = ("key", "heading_tail", "lineno", "raw", "preamble", "fields", "trailer")

    def __init__(self, key, heading_tail, lineno, raw, preamble, fields, trailer):
        self.key = key
        self.heading_tail = heading_tail
        self.lineno = lineno
        self.raw = raw
        self.preamble = preamble
        self.fields = fields
        self.trailer = trailer

    @property
    def heading(self):
        return self.raw.split("\n", 1)[0]

    def field(self, name):
        for found in self.fields:
            if found.name == name:
                return found.value
        return None

    def field_names(self):
        return [found.name for found in self.fields]

    def unapproved(self, is_findings):
        approved = fields_for(is_findings)
        return [n for n in self.field_names() if n not in approved]

    def missing(self, is_findings):
        if is_findings:
            return []
        present = set(self.field_names())
        return [n for n in SOURCE_REQUIRED if n not in present]

    def serialise(self):
        return self.raw

    def rebuild(self):
        return (self.heading + "\n" + self.preamble
                + "".join(found.raw for found in self.fields) + self.trailer)

    def __repr__(self):
        return f"Entry({self.key!r}, line {self.lineno}, {len(self.fields)} fields)"


class Break:
    __slots__ = ("heading", "lineno", "raw")

    def __init__(self, heading, lineno, raw):
        self.heading = heading
        self.lineno = lineno
        self.raw = raw

    def __repr__(self):
        return f"Break({self.heading[:40]!r}, line {self.lineno})"


class Bank:
    __slots__ = ("text", "header", "segments", "path")

    def __init__(self, text, header, segments, path=None):
        self.text = text
        self.header = header
        self.segments = segments
        self.path = path

    @property
    def entries(self):
        return [s for s in self.segments if isinstance(s, Entry)]

    @property
    def breaks(self):
        return [s for s in self.segments if isinstance(s, Break)]

    @property
    def keys(self):
        return [e.key for e in self.entries]

    def entry(self, key):
        for found in self.entries:
            if found.key == key:
                return found
        return None

    def out_of_order(self):
        pairs, run = [], []

        def flush():
            for a, b in zip(run, run[1:]):
                if sort_position(b) < sort_position(a):
                    pairs.append((a, b))
            run.clear()

        for segment in self.segments:
            if isinstance(segment, Entry):
                run.append(segment.key)
            else:
                flush()
        flush()
        return pairs

    def sort_entries(self):
        moved = 0
        run = []

        def flush():
            nonlocal moved
            if len(run) < 2:
                run.clear()
                return
            pieces = [split_separator(self.segments[i].raw) for i in run]
            separators = [sep for _, sep in pieces]
            order = sorted(range(len(run)),
                           key=lambda j: sort_position(self.segments[run[j]].key))
            if order != list(range(len(run))):
                contents = [pieces[j][0] for j in order]
                entries = [self.segments[run[j]] for j in order]
                for index, entry, content, separator in zip(run, entries, contents,
                                                            separators):
                    if self.segments[index].key != entry.key:
                        moved += 1
                    entry.raw = content + separator
                    self.segments[index] = entry
            run.clear()

        for index, segment in enumerate(self.segments):
            if isinstance(segment, Entry):
                run.append(index)
            else:
                flush()
        flush()
        return moved

    def serialise(self):
        return self.header + "".join(s.raw for s in self.segments)


def _parse_fields(body):
    lines = body.split("\n")
    pieces = [line + "\n" for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

    preamble, fields, current = [], [], None
    fenced = False
    for offset, piece in enumerate(pieces):
        stripped = piece.rstrip("\n")
        if _FENCE.match(stripped):
            fenced = not fenced
            if current is None:
                preamble.append(piece)
            else:
                current[3].append(piece)
            continue
        found = None if fenced else _FIELD_LINE.match(stripped)
        if found:
            current = [found.group(1), found.group(2), offset, [piece]]
            fields.append(current)
            continue
        if current is None:
            preamble.append(piece)
        else:
            current[3].append(piece)

    if not fields:
        return "", [], body

    built = []
    for name, first_value, offset, raw_lines in fields:
        raw = "".join(raw_lines)
        tail = []
        for piece in raw_lines[1:]:
            stripped = piece.rstrip("\n")
            if stripped.startswith("---") or _HEADING.match(stripped):
                break
            tail.append(piece)
        joined = "".join(tail)
        value = first_value if not joined else first_value + "\n" + joined.rstrip("\n")
        built.append(Field(name, value.strip(), offset, raw))
    return "".join(preamble), built, ""


ENTRY_FORMAT_HEADING = "## Entry format"


def parse_bank(text, path=None):
    lines = text.split("\n")
    pieces = [line + "\n" for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

    boundaries = []
    fenced = False
    for index, piece in enumerate(pieces):
        stripped = piece.rstrip("\n")
        if _FENCE.match(stripped):
            fenced = not fenced
            continue
        if fenced or not _SECTION_HEADING.match(stripped):
            continue
        entry = ENTRY_HEADING.match(stripped)
        if entry and not is_placeholder(entry.group(1)):
            boundaries.append((index, entry.group(1).strip(), entry.group(2).strip()))
        else:
            boundaries.append((index, None, stripped))

    first_entry = next((i for i, (_, key, _) in enumerate(boundaries) if key), None)
    if first_entry is None:
        if ENTRY_FORMAT_HEADING in (line.rstrip() for line in lines):
            return Bank(text, text, [], path)
        raise ValueError("no entry headings found -- this does not look like a bank")

    header_end = boundaries[first_entry][0]
    header = "".join(pieces[:header_end])
    if not header.strip():
        raise ValueError("the bank header did not survive the split")
    if "## Entry format" not in header:
        raise ValueError(
            "the bank header has no '## Entry format' block -- a bank documents its own "
            "format before its first entry")

    segments = []
    for position in range(first_entry, len(boundaries)):
        start, key, tail = boundaries[position]
        end = boundaries[position + 1][0] if position + 1 < len(boundaries) else len(pieces)
        raw = "".join(pieces[start:end])
        if key is None:
            segments.append(Break(tail, start + 1, raw))
            continue
        body = raw.split("\n", 1)[1] if "\n" in raw else ""
        preamble, fields, trailer = _parse_fields(body)
        segments.append(Entry(key, tail, start + 1, raw, preamble, fields, trailer))

    bank = Bank(text, header, segments, path)
    if bank.serialise() != text:
        raise ValueError("internal error: the bank did not round-trip")
    return bank


def read_bank(path):
    with open(path, encoding="utf-8") as handle:
        return parse_bank(handle.read(), path)


def line_ending_of(path):
    with open(path, "rb") as handle:
        return "\r\n" if b"\r\n" in handle.read() else "\n"


def is_findings_bank(path_or_text, config=None):
    if config is not None and "\n" not in str(path_or_text):
        resolved = Path(path_or_text).resolve()
        if config.sources.quotes and resolved == config.sources.quotes:
            return True
        if config.sources.list and resolved == config.sources.list:
            return False
    text = path_or_text if "\n" in str(path_or_text) else ""
    if not text:
        try:
            with open(path_or_text, encoding="utf-8") as handle:
                text = handle.read(4096)
        except OSError:
            return any(word in str(path_or_text).lower() for word in FINDINGS_TITLE_WORDS)
    title = text.split("\n", 1)[0].lower()
    return title.startswith("#") and any(word in title for word in FINDINGS_TITLE_WORDS)


def _round_trip(path, failures, counts, config=None):
    try:
        bank = read_bank(path)
    except (OSError, ValueError) as error:
        failures.append(f"{path}: {error}")
        return None

    if bank.serialise() != bank.text:
        failures.append(f"{path}: bank did not round-trip")

    bad = [e.key for e in bank.entries if e.rebuild() != e.raw]
    if bad:
        failures.append(
            f"{path}: {len(bad)} entr{'y' if len(bad) == 1 else 'ies'} did not rebuild "
            f"from their parsed fields: {' '.join(bad[:8])}")

    findings = is_findings_bank(path, config)
    counts[path] = {
        "entries": len(bank.entries),
        "breaks": len(bank.breaks),
        "fields": sum(len(e.fields) for e in bank.entries),
        "rebuilt": len(bank.entries) - len(bad),
        "findings_bank": findings,
        "header_lines": bank.header.count("\n"),
        "unapproved": sorted({n for e in bank.entries for n in e.unapproved(findings)}),
        "missing": sorted({n for e in bank.entries for n in e.missing(findings)}),
        "out_of_order": len(bank.out_of_order()),
        "bad_separators": len(separator_defects(bank)),
    }
    if "<Key>" in bank.keys:
        failures.append(f"{path}: the <Key> placeholder was counted as an entry")
    return bank


def _sort_test(failures):
    bank_text = (
        "# Sources List\n\n## Entry format\n\n```\n"
        '### [<Key>] Author(s), "Short Title" (Year)\n```\n\n'
        "### [Smi01] S, \"Third\" (2001)\n\n**Full title:** Third\n\n---\n\n"
        "### [Ada85] A, \"First\" (1985)\n\n**Full title:** First\n\n---\n\n"
        "### [Bak02] B, \"Second\" (2002)\n\n**Full title:** Second\n\n"
        "## Section 4 -- a section that groups what follows\n\n"
        "### [Zed20] Z, \"Fifth\" (2020)\n\n**Full title:** Fifth\n\n---\n\n"
        "### [Jon72] J, \"Fourth\" (1972)\n\n**Full title:** Fourth\n"
    )
    bank = parse_bank(bank_text)
    if bank.serialise() != bank_text:
        failures.append("sort fixture did not round-trip before sorting")
    before = sorted(split_separator(e.raw)[0] for e in bank.entries)
    bank.sort_entries()

    if bank.keys != ["Ada85", "Bak02", "Smi01", "Jon72", "Zed20"]:
        failures.append(f"sort_entries wrong order: {bank.keys}")
    if (set(bank.keys[:3]) != {"Ada85", "Bak02", "Smi01"}
            or set(bank.keys[3:]) != {"Jon72", "Zed20"}):
        failures.append(f"sort_entries sorted across a section break: {bank.keys}")
    if sorted(split_separator(e.raw)[0] for e in bank.entries) != before:
        failures.append("sort_entries altered an entry's content")
    if bank_text.count("---") != bank.serialise().count("---"):
        failures.append("sort_entries changed the number of separators")
    if "## Section 4" not in bank.serialise():
        failures.append("sort_entries lost a non-entry section")
    again = parse_bank(bank.serialise())
    if again.serialise() != bank.serialise():
        failures.append("a sorted bank does not round-trip")
    if again.keys != bank.keys:
        failures.append("a sorted bank re-parses to different keys")
    if bank.sort_entries() != 0:
        failures.append("sorting an already-sorted bank still reports movement")
    if bank.out_of_order():
        failures.append(f"out_of_order still reports {bank.out_of_order()} after sorting: "
                        f"it compares across a section break that sort_entries will not cross")


def _self_test(bank_paths, config=None):
    failures, counts = [], {}
    _sort_test(failures)

    fixture = (
        "# Sources List\n"
        "\n"
        "## Entry format\n"
        "\n"
        "```\n"
        '### [<Key>] Author(s), "Short Title" (Year)\n'
        "\n"
        "**Full title:** the title as printed\n"
        "```\n"
        "\n"
        "---\n"
        "---\n"
        '### [AAA01] A, "First" (2001)\n'
        "\n"
        "**Full title:** First\n"
        "**Authors:** Author, A.\n"
        "**Year:** 2001\n"
        "**Note:** a value that runs on\n"
        "  and continues here with **bold** inside it\n"
        "**Findings:** see the other bank\n"
        "\n"
        "---\n"
        "\n"
        "### Works identified and not fetched\n"
        "\n"
        "| Key | Work |\n"
        "|---|---|\n"
        "`SJ04` | Smith & Jones |\n"
        "\n"
        "---\n"
        '### [BBB02] B, "Second" (2002)\n'
        "\n"
        "**Full title:** Second\n"
        "**Key findings.** a dot label, which is NOT a field\n"
        "**Relation:** a quotes-bank name in the sources list\n"
    )
    bank = parse_bank(fixture)

    def check(got, want, label):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    check(bank.serialise(), fixture, "fixture round-trip")
    check(bank.keys, ["AAA01", "BBB02"], "the <Key> placeholder is not an entry")
    check("## Entry format" in bank.header, True, "header survived")
    check([b.heading for b in bank.breaks],
          ["### Works identified and not fetched"],
          "a non-entry ### heading became a Break, not part of the entry above")

    first = bank.entry("AAA01")
    check(first.field_names(), ["Full title", "Authors", "Year", "Note", "Findings"],
          "fields in written order")
    check(first.field("Year"), "2001", "single-line value")
    check("continues here" in first.field("Note"), True,
          "multi-line value continued by absence of a label")
    check("**bold**" in first.field("Note"), True, "bold inside a value survives")
    check(first.rebuild(), first.raw, "entry rebuilt from its parsed fields")
    check(first.missing(False), [], "required fields present")
    check(first.field("Findings"), "see the other bank",
          "the value stops at the `---` separator")
    check("---" in first.raw, True, "the separator is still inside raw, so raw round-trips")

    second = bank.entry("BBB02")
    check("Key findings" in second.field_names(), False, "a `.**` label is not a field")
    check(second.unapproved(False), ["Relation"],
          "a quotes-bank name in the sources list is reported, not approved")
    check(second.unapproved(True), ["Full title"],
          "the two field lists are separate and neither approves the other's names")
    check(second.missing(False), ["Authors", "Year"], "missing required fields")
    check(second.rebuild(), second.raw, "second entry rebuilt")

    if "Relation" in SOURCE_FIELDS or "Full title" in FINDINGS_FIELDS:
        failures.append("the two field lists have been merged")
    if FINDINGS_FIELDS & SOURCE_FIELDS:
        failures.append(f"field lists overlap: {sorted(FINDINGS_FIELDS & SOURCE_FIELDS)}")
    check(len(FINDINGS_FIELDS), 9, "the quotes-bank field list is nine names")

    check(separator_defects(bank),
          [("AAA01", "\n\n---\n---\n"), ("BBB02", "\n\n---\n")],
          "every entry not introduced by the declared separator, and only those")
    check(split_separator("### [X] x\n\n**Full title:** T\n\n---\n\n"),
          ("### [X] x\n\n**Full title:** T", ENTRY_SEPARATOR),
          "a canonical segment splits into content and the declared separator")
    check(with_separator("### [X] x\n\n**Full title:** T\n\n---\n\n"),
          "### [X] x\n\n**Full title:** T\n\n---\n\n",
          "normalising an already-canonical segment changes nothing")
    check(with_separator("### [X] x\n\n**Full title:** T\n---\n---\n"),
          "### [X] x\n\n**Full title:** T\n\n---\n\n",
          "a doubled rule collapses and the missing blank line is restored")
    fenced_tail = "### [X] x\n\n**Note:** an example\n```\n---\n```\n\n---\n\n"
    check(split_separator(fenced_tail)[1], ENTRY_SEPARATOR,
          "a fenced `---` is content, not part of the separator run")
    check(with_separator(fenced_tail), fenced_tail, "and it survives normalisation")

    fenced = parse_bank(
        "# X\n\n## Entry format\n\n```\n### [<Key>] x\n```\n\n"
        '### [CCC03] C, "Third" (2003)\n\n'
        "**Full title:** Third\n"
        "**Note:** an example follows\n"
        "```\n"
        "**Not A Field:** inside a fence\n"
        "```\n")
    third = fenced.entry("CCC03")
    check("Not A Field" in third.field_names(), False, "a fenced label is not a field")
    check(third.rebuild(), third.raw, "fenced value rebuilt")

    for broken, label in [
        ('### [AAA01] A, "First" (2001)\n\n**Full title:** First\n', "no header"),
        ("# Bank\n\nno entries here at all\n", "no entries"),
    ]:
        try:
            parse_bank(broken)
            failures.append(f"parse_bank accepted a bank with {label}")
        except ValueError:
            pass

    check(is_findings_bank("# Quotes (Bank)\n\n"), True, "a quotes title is the quotes bank")
    check(is_findings_bank("# Findings Registry\n\n"), True, "a findings title too")
    check(is_findings_bank("# Sources List\n\n"), False, "a sources title is not")

    skipped = []
    for path in bank_paths:
        if path and Path(path).is_file():
            _round_trip(path, failures, counts, config)
        elif path:
            skipped.append(str(path))

    for line in failures:
        print(f"FAIL  {line}")
    print()
    for path, data in counts.items():
        kind = "quotes " if data["findings_bank"] else "sources"
        print(f"{kind} {path}")
        print(f"    entries parsed        {data['entries']}")
        print(f"    round-tripped         {data['rebuilt']}/{data['entries']}"
              f"{'  (all)' if data['rebuilt'] == data['entries'] else '  <-- MISMATCH'}")
        print(f"    fields parsed         {data['fields']}")
        print(f"    non-entry breaks      {data['breaks']}")
        print(f"    header lines kept     {data['header_lines']}")
        print(f"    entries out of order  {data['out_of_order']}")
        print(f"    bad entry separators  {data['bad_separators']}")
        if data["unapproved"]:
            print(f"    unapproved names      {', '.join(data['unapproved'])}")
        if data["missing"]:
            print(f"    missing required      {', '.join(data['missing'])}")
    for path in skipped:
        print(f"not found, not round-tripped: {path}")
    print(f"\ncontract {CONTRACT}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(
        description="Parse, check and sort the two source banks (the sources list and the "
                    "quotes bank). Paths come from the book's config.")
    add_config_arguments(ap)
    ap.add_argument("--self-test", action="store_true",
                    help="grammar tests plus a byte-identical round-trip of both banks")
    ap.add_argument("--sources", help="the sources list (default: sources.list from config)")
    ap.add_argument("--findings", help="the quotes bank (default: sources.quotes from config)")
    ap.add_argument("--sort", metavar="BANK",
                    help="report entries that are out of the bank's declared order")
    ap.add_argument("--fix", action="store_true",
                    help="with --sort, rewrite the bank with its entries in order")
    ap.add_argument("--fields", metavar="BANK",
                    help="list every field name used in a bank, with counts")
    args = ap.parse_args()

    try:
        config = config_from_args(args)
    except ConfigError as error:
        sys.stderr.write(f"source_registry: {error}\n")
        return 2

    if args.self_test:
        sources = args.sources or config.sources.list
        findings = args.findings or config.sources.quotes
        return _self_test([sources, findings], config)
    if args.sort:
        try:
            bank = read_bank(args.sort)
        except (OSError, ValueError) as error:
            return tool_failed(f"cannot sort {args.sort}: {error}", TOOL)
        if bank.serialise() != bank.text:
            sys.stderr.write(f"{args.sort} does not round-trip; refusing to sort\n")
            return 1
        pairs = bank.out_of_order()
        moved = bank.sort_entries()
        print(f"{args.sort}: {len(pairs)} out-of-order pair(s), {moved} entry/entries move")
        for previous, current in pairs[:20]:
            print(f"   {previous} then {current}")
        if args.fix and moved:
            rebuilt = bank.serialise()
            check = parse_bank(rebuilt)
            if check.keys != bank.keys or check.serialise() != rebuilt:
                sys.stderr.write("the sorted bank does not re-parse; nothing written\n")
                return 1
            if sorted(split_separator(e.raw)[0] for e in check.entries) != sorted(
                    split_separator(e.raw)[0] for e in read_bank(args.sort).entries):
                sys.stderr.write("entry contents changed; nothing written\n")
                return 1
            with open(args.sort, "w", encoding="utf-8",
                      newline=line_ending_of(args.sort)) as handle:
                handle.write(rebuilt)
            print(f"   wrote {args.sort}")
        elif moved:
            print("   pass --fix to apply")
        return 0
    if args.fields:
        bank = read_bank(args.fields)
        findings = is_findings_bank(args.fields, config)
        tally = {}
        for entry in bank.entries:
            for name in entry.field_names():
                tally[name] = tally.get(name, 0) + 1
        approved = fields_for(findings)
        print(f"{args.fields}  ({'quotes' if findings else 'sources'} field list)")
        for name, count in sorted(tally.items(), key=lambda kv: -kv[1]):
            mark = "" if name in approved else "   <-- NOT IN THIS BANK'S FIELD LIST"
            print(f"  {count:5}  {name}{mark}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
