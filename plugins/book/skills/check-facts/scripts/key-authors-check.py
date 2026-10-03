#!/usr/bin/env python3
"""Hold every key in the sources list to the entry's own Authors field.

A key is derived data: lib/citation_key.derive computes it from the author list, so an
entry whose key disagrees with its own Authors field is wrong in one of the two. Nothing
else notices, because a wrong key is still a well-formed key: it points at a real entry,
joins cleanly across both banks, and reads as correct.

Classes:
  mismatch            DEFECT  the Authors field is readable and derives a different key
  incomplete-authors  DEFECT  the key implies MORE authors than the entry records, so
                              deriving would "correct" the key from a field that is
                              short. Which one is wrong is a judgment: the key may be a
                              typo, or the field may be missing authors. Never derive
                              silently.
  malformed-key       DEFECT  the key is not a well-formed key at all
  not-checkable       INFORMATIONAL  the Authors field cannot be read confidently: an
                              organisation has no derivable key, a truncated list has no
                              knowable count, and "Nash, Dan" cannot be told from a
                              two-author given-first list. Listed, never guessed.

A retired pointer record (`Full title: RETIRED KEY ...`) is skipped: it carries the
authors of the entry it points at, so it always disagrees by design.

Usage:
  key-authors-check.py
  key-authors-check.py --self-test
"""

import argparse
import re
import sys

sys.dont_write_bytecode = True

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, tool_failed
from check_output import (DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing)
from citation_key import (_fragment, derive, is_placeholder, parse,
                          surnames_from_registry_field)

TOOL = "key-authors-check"
CLASSES = {
    "mismatch": DEFECT,
    "incomplete-authors": DEFECT,
    "malformed-key": DEFECT,
    "not-checkable": INFORMATIONAL,
}

ENTRY_SPLIT = re.compile(r"\n(?=### \[)")
AUTHORS_FIELD = re.compile(r"^\*\*Authors:\*\*\s*(.+)$", re.M)
RETIRED = re.compile(r"^\*\*Full title:\*\*\s*RETIRED KEY\b", re.M)


def entries(text):
    for block in ENTRY_SPLIT.split(text):
        head = re.match(r"### \[([^\]]+)\]", block)
        if not head or is_placeholder(head.group(1)) or RETIRED.search(block):
            continue
        field = AUTHORS_FIELD.search(block)
        yield head.group(1).strip(), (field.group(1).strip() if field else "")


def implied_authors(stem):
    return len(stem) if stem.isupper() and len(stem) >= 2 else None


def one_letter_each(names):
    return all(len(_fragment(name)) == 1 for name in names)


def check(text):
    findings, skipped = [], []
    for key, field in entries(text):
        names, confidence, reason = surnames_from_registry_field(field)
        if confidence != "high" or not names:
            skipped.append((key, reason))
            continue
        parsed = parse(key)
        if not parsed:
            findings.append((key, "malformed-key",
                             f"{key!r} is not a well-formed key, and its author list "
                             f"derives {derive(names, '00')[:-2]}<year>"))
            continue
        stem, plus, year, letter = parsed

        claimed = implied_authors(stem)
        if claimed and not plus and len(names) < claimed and one_letter_each(names):
            findings.append((key, "incomplete-authors",
                             f"the key implies {claimed} authors, the entry records "
                             f"{len(names)}: {field[:60]!r}"))
            continue

        expected = derive(names, year) + letter
        if expected != key:
            findings.append((key, "mismatch",
                             f"the Authors field derives {expected}, not {key} "
                             f"({len(names)} author(s): {'; '.join(names[:4])})"))
    return findings, skipped


def _self_test():
    failures = []

    def bank(*entries_text):
        header = ('# Sources List\n\n## Entry format\n\n```\n'
                  '### [<Key>] Author(s), "Short Title" (Year)\n```\n\n')
        return header + "\n\n---\n\n".join(entries_text) + "\n"

    def entry(key, authors):
        return f'### [{key}] X, "T" (2000)\n\n**Authors:** {authors}'

    def verdicts(*entries_text):
        found, skip = check(bank(*entries_text))
        return {k: kind for k, kind, _ in found}, {k: r for k, r in skip}

    clean = [
        entry("ABCD94", "Ann Adams, Bob Baker, Cat Clark, Dan Davis"),
        entry("Smi01", "Nora Smith"),
        entry("HPY12", "Hill, Mark; Porter, Frank; Young, Jeffrey M."),
        entry("vSGvL98", "Rita van Soest; Egon Grant; Frank van Loon"),
        entry("OP83", "Paul Owen-Price"),
        entry("MPBD08", "Carl A. Moss, J. Greg Pell, Dora A. Bell-Dunn"),
        entry("Nas06", "Dan Nash"),
    ]
    found, _ = verdicts(*clean)
    if found:
        failures.append(f"clean entries reported findings: {found}")

    cases = [
        (entry("ABC+94", "Ann Adams, Bob Baker, Cat Clark, Dan Davis"),
         "ABC+94", "mismatch", "old-scheme key"),
        (entry("HMP+12", "Hill, Mark; Porter, Frank; Young, Jeffrey M."),
         "HMP+12", "mismatch", "surname-first misread"),
        (entry("SGL+98", "Rita van Soest; Egon Grant; Frank van Loon"),
         "SGL+98", "mismatch", "particle dropped"),
        (entry("Owe83", "Paul Owen-Price"), "Owe83", "mismatch", "hyphen"),
        (entry("DRW02", "Alan Dunmore"), "DRW02", "incomplete-authors", "short field"),
    ]
    for text, key, want, label in cases:
        found, _ = verdicts(text)
        if found.get(key) != want:
            failures.append(f"{label}: {key} reported {found.get(key)}, want {want}")

    for authors, label in [
        ("Acme Technologies", "organisation"),
        ("Widget Project", "organisation"),
        ("Anna A. Ivers et al.", "truncated list"),
        ("no author is printed in the document", "prose, not an author list"),
        ("Nash, Dan", "'Surname, Given' vs two authors"),
        ("Jon Sills, Gail C. Moore, Kris De Vries", "compound surname"),
        ("Maria Perez Molina, Max Wolf, Sara Weiss", "compound, given-first"),
        ("published by the forum user `riverwalker`; the page states no author name",
         "a handle, with no author list to check against"),
        ("Jose Aldo Rocha da Lima, Rita Gomez, Marco Ramos", "compound with a particle"),
    ]:
        found, skip = verdicts(entry("Xxx99", authors))
        if "Xxx99" not in skip or found:
            failures.append(f"{label}: {authors!r} was not skipped ({found})")

    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--list", dest="sources_list", help="the sources list (default: sources.list)")
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()

    config = load_book(args, TOOL)
    sources_list = args.sources_list or config.sources.list
    if not args.sources_list and skipped_for_missing(TOOL, sources_list, "sources list",
                                                     args.format):
        return 0
    try:
        with open(sources_list, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, TypeError) as error:
        return tool_failed(f"cannot read the sources list: {error}", TOOL)

    findings, skipped = check(text)
    report = CheckReport(TOOL, CLASSES)
    for key, kind, detail in sorted(findings):
        report.add(key, kind, detail)
    for key, reason in sorted(skipped):
        report.add(key, "not-checkable", reason)
    if args.format == "text":
        print("keys checked against their Authors field: %d\n"
              % (sum(1 for _ in entries(text)) - len(skipped)))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
