#!/usr/bin/env python3
"""Join the sources list and the quotes bank by citation key and report what does not line up.

The two banks are separate files on purpose: identity and access in the list, what the
source says in the quotes bank. A chapter agent greps the half it needs. The cost is
that two files keyed identically can drift, and a format check that reads each bank
alone cannot see it.

This is not the manuscript join. A source registered but never cited is a good entry;
list-bibliography-check.py owns the manuscript-to-list join. The manuscript is never
read here.

The two directions are not equally bad:

  quotes entry with no list entry     DEFECT  no-list-entry: a quote with no title,
                                              author or URL, so it can be neither
                                              re-checked nor re-fetched
  list entry with no quotes entry     INFORMATIONAL not-read: registered but not
                                              read yet, or read with nothing to record
  Findings: pointer, no such entry    DEFECT  dangling-pointer
  entries in both, no Findings: line  DEFECT  missing-pointer: an agent reading only
                                              the list re-verifies quotes already held
  quotes entry, no Source: line       DEFECT  missing-backlink
  same key twice in one bank          DEFECT  duplicate-entry: tools read the first
                                              and never see the second (one source
                                              under two keys is duplicate-source-check)
  Last verified older than --stale    INFORMATIONAL stale-reading: a published source
                                              does not change, so an old reading is
                                              unconfirmed, not wrong

Fenced blocks are masked before parsing, because each bank documents its own format
with a `### [<Key>]` template inside a fence.

Usage:
  list-quotes-join-check.py
  list-quotes-join-check.py --list <path> --quotes <path>
  list-quotes-join-check.py --stale 365
  list-quotes-join-check.py --self-test
"""

import argparse
import contextlib
import datetime
import io
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, tool_failed
from check_output import (DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing)
from citation_key import ENTRY_HEADING, is_placeholder

TOOL = "list-quotes-join-check"
CLASSES = {
    "duplicate-entry": DEFECT,
    "no-list-entry": DEFECT,
    "dangling-pointer": DEFECT,
    "missing-pointer": DEFECT,
    "missing-backlink": DEFECT,
    "not-read": INFORMATIONAL,
    "stale-reading": INFORMATIONAL,
}

HEADING = ENTRY_HEADING
FENCE = re.compile(r"^```.*?^```", re.M | re.S)
POINTER_TO_FINDINGS = re.compile(r"^\*\*Findings:\*\*", re.M)
POINTER_TO_SOURCES = re.compile(r"^\*\*Source:\*\*", re.M)
LAST_VERIFIED = re.compile(r"^\*\*Last verified:\*\*[ \t]*(\d{4}-\d{2}-\d{2})", re.M)


def mask_fenced(text):
    return FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def read_bank(path):
    text = mask_fenced(Path(path).read_text(encoding="utf-8"))
    lines = text.splitlines()
    entries, duplicates, order = {}, [], []
    starts = [(n, HEADING.match(line).group(1))
              for n, line in enumerate(lines, 1)
              if HEADING.match(line) and not is_placeholder(HEADING.match(line).group(1))]
    for index, (number, key) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        body = "\n".join(lines[number:end])
        if key in entries:
            duplicates.append((key, number))
        else:
            entries[key] = (number, body)
            order.append(key)
    return entries, duplicates, order


def stale_readings(findings, cutoff_days, today):
    aged = []
    for key, (number, body) in findings.items():
        match = LAST_VERIFIED.search(body)
        if not match:
            continue
        try:
            when = datetime.date.fromisoformat(match.group(1))
        except ValueError:
            continue
        age = (today - when).days
        if age > cutoff_days:
            aged.append((age, key, number, match.group(1)))
    return sorted(aged, reverse=True)


def join(sources, source_dupes, findings, finding_dupes):
    items = []
    for key, number in source_dupes:
        items.append(("duplicate-entry", key, number,
                      "second entry under this key in the sources list; "
                      "tools match the first and never see it"))
    for key, number in finding_dupes:
        items.append(("duplicate-entry", key, number,
                      "second entry under this key in the quotes bank; "
                      "tools match the first and never see it"))
    for key in sorted(set(findings) - set(sources)):
        items.append(("no-list-entry", key, findings[key][0],
                      "quotes with no identity or access data: nothing records "
                      "what this source is or where to read it"))
    for key in sorted(sources):
        number, body = sources[key]
        if POINTER_TO_FINDINGS.search(body) and key not in findings:
            items.append(("dangling-pointer", key, number,
                          "points at a quotes entry that does not exist"))
        elif key in findings and not POINTER_TO_FINDINGS.search(body):
            items.append(("missing-pointer", key, number,
                          "quotes exist for this key but the list does not say so, "
                          "so an agent reading only the list re-verifies them"))
    for key in sorted(findings):
        number, body = findings[key]
        if key in sources and not POINTER_TO_SOURCES.search(body):
            items.append(("missing-backlink", key, number, "no Source: line"))
    flagged = {key for _, key, _, _ in items}
    unread = sorted(set(sources) - set(findings) - flagged)
    joined = sorted(set(sources) & set(findings))
    return items, joined, unread


FIXTURE_SOURCES = '''# Sources List

## Entry format

```
### [<Key>]

**Access URLs:** where the source can be read
**Findings:** see `sources/quotes.md`
```

### [Aaa01]

**Note:** a paper held in both banks
**Findings:** see `sources/quotes.md`

---

### [Bbb02]

**Note:** an entry pointing at a quotes entry that was never written
**Findings:** see `sources/quotes.md`

---

### [Ccc03]

**Note:** an entry whose quotes exist and are not advertised

---

### [Ddd04]

**Note:** an entry whose quotes entry forgot the Source line
**Findings:** see `sources/quotes.md`

### DELTA for the existing Ddd04 entry

**Note:** a non-entry heading terminates nothing, so this stays inside [Ddd04]

---

### [Eee05]

**Note:** the surviving entry
**Findings:** see `sources/quotes.md`

---

### [Eee05]

**Note:** the second entry, which every tool that matches by key never sees
**Findings:** see `sources/quotes.md`

---

### [Wal--]

**Note:** a living catalog
**Findings:** see `sources/quotes.md`

---

### [SFD+25a]

**Note:** registered for identity and access only, never read

---
'''

FIXTURE_FINDINGS = '''# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Verified quotes:** exact strings, in quotation marks
**Source:** see `sources/list.md`
```

### [Aaa01] Alpha, "A cached paper" (2001)

**Key findings:** the four-item figure is a population average
**Last verified:** 2025-01-01
**Source:** see `sources/list.md`

---

### [Ccc03] Charlie, "Read, but the entry does not say so" (2003)

**Key findings:** read and recorded here, with nothing on the list side
**Last verified:** 2025-01-01
**Source:** see `sources/list.md`

---

### [Ddd04] Delta, "No backlink on the other side" (2004)

**Key findings:** recorded without a Source line
**Last verified:** 2025-01-01

---

### [Eee05] Echo, "Merged twice" (2005)

**Key findings:** one quotes entry against two list entries
**Last verified:** 2025-01-01
**Source:** see `sources/list.md`

---

### [Kim10] Kim, "A paper filed under another year" (2010)

**Key findings:** the quote is on the cached page, which the list files as Kim11
**Last verified:** 2020-01-01
**Source:** see `sources/list.md`

---

### [Wal--] Walsh, "A living catalog" (--)

**Key findings:** the catalog renamed one entry between versions
**Last verified:** 2025-01-01
**Source:** see `sources/list.md`

---
'''

EXPECTED = {
    ("duplicate-entry", "Eee05"),
    ("no-list-entry", "Kim10"),
    ("dangling-pointer", "Bbb02"),
    ("missing-pointer", "Ccc03"),
    ("missing-backlink", "Ddd04"),
}


def _run(argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        status = main([str(argument) for argument in argv])
    return buffer.getvalue(), status


def self_test():
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    with tempfile.TemporaryDirectory() as root:
        sources = Path(root, "list.md")
        findings = Path(root, "quotes.md")
        for path, text in ((sources, FIXTURE_SOURCES), (findings, FIXTURE_FINDINGS)):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        common = ["--list", sources, "--quotes", findings, "--format", "tsv"]
        output, status = _run(common)
        stale_output, stale_status = _run(common + ["--stale", "365"])
        parsed, duplicates, _order = read_bank(sources)
        found, _dupes, _order = read_bank(findings)

    reported = {tuple(line.split("\t")[1::-1]) for line in output.splitlines() if line}
    defects = {(name, key) for name, key in reported if CLASSES[name] == DEFECT}
    for name, key in sorted(EXPECTED - defects):
        failures.append(f"{name} [{key}] NOT REPORTED")
    for name, key in sorted(defects - EXPECTED):
        failures.append(f"{name} [{key}] FALSE POSITIVE")
    require(len(parsed) == 7 and len(found) == 6, "wrong entry counts: %d list, %d quotes"
            % (len(parsed), len(found)))
    require("<Key>" not in str(sorted(parsed)), "the fenced template was parsed as an entry")
    require("DELTA" not in str(sorted(parsed)), "a non-entry ### heading was parsed as an entry")
    require(duplicates == [("Eee05", 50)],
            "the duplicate was not caught once, at its second heading: %s" % duplicates)
    require(("not-read", "SFD+25a") in reported,
            "[SFD+25a] is registered and unread, which must be listed as not-read")
    require(not any(key == "Wal--" for _, key in reported),
            "[Wal--] joins on both sides, so the -- year key must report nothing")
    require(status == 1, "defects were reported and the exit status was not 1")
    aged = stale_readings(found, 365, datetime.date(2025, 6, 1))
    require([key for _age, key, _n, _when in aged] == ["Kim10"],
            "wrong stale set: %s" % [key for _a, key, _n, _w in aged])
    require("stale-reading" in stale_output and stale_status == 1,
            "--stale printed nothing or changed the exit status")

    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--list", dest="sources_list",
                        help="the sources list (default: sources.list)")
    parser.add_argument("--quotes", help="the quotes bank (default: sources.quotes)")
    parser.add_argument("--stale", type=int, metavar="DAYS",
                        help="also list readings older than DAYS (informational)")
    parser.add_argument("--self-test", action="store_true",
                        help="only check the rules against built-in fixtures")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    if args.sources_list and args.quotes:
        sources_path, quotes_path = args.sources_list, args.quotes
    else:
        config = load_book(args, TOOL)
        sources_path = args.sources_list or config.sources.list
        quotes_path = args.quotes or config.sources.quotes
    for path, label, given in ((sources_path, "sources list", args.sources_list),
                               (quotes_path, "quotes bank", args.quotes)):
        if given and not Path(path).exists():
            return tool_failed("no such file: %s" % path, TOOL)
        if skipped_for_missing(TOOL, path, label, args.format):
            return 0

    sources, source_dupes, _ = read_bank(sources_path)
    findings, finding_dupes, _ = read_bank(quotes_path)
    items, joined, unread = join(sources, source_dupes, findings, finding_dupes)

    report = CheckReport(TOOL, CLASSES)
    for name, key, number, why in items:
        report.add(key, name, "line %d: %s" % (number, why))
    for key in unread:
        report.add(key, "not-read", "registered but not read, or read with nothing to record")
    if args.stale:
        for age, key, number, when in stale_readings(findings, args.stale, datetime.date.today()):
            report.add(key, "stale-reading",
                       "line %d: last verified %s, %d days ago" % (number, when, age))
    if args.format == "text":
        print("List: %d   Quotes: %d   Joined by key: %d\n"
              % (len(sources), len(findings), len(joined)))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
