#!/usr/bin/env python3
"""Fold the entries a run proposed into the sources list and the quotes bank.

Parallel agents never write to a bank: several writers on one file corrupt it. Each
agent of a run stages its entries in bank format as one file in the run folder,

    <run folder>/proposed-entries/list/*.md     identity and access, for sources.list
    <run folder>/proposed-entries/quotes/*.md   what each source says, for sources.quotes

and the run merges them at its end with this script.

What a merge never does:
  * overwrite an existing entry. A key already in the bank is a COLLISION and is
    skipped, because merging two accounts of one source needs judgment.
  * accept the other bank's vocabulary. A staged entry carrying a field the target
    bank does not approve is REJECTED and reported by field name.
  * touch prose that is not an entry. Any heading that is not `### [Key]` ends the
    entry above it and is left for a person.

Entries go in at their case-insensitive sorted position; the bank's `## Entry format`
example is kept intact, or nothing is written.

Usage:
  proposed_entries.py --run <run folder>                 dry run, both banks
  proposed_entries.py --run <run folder> --fix           merge both banks
  proposed_entries.py --run <run folder> --bank quotes   one bank
  proposed_entries.py --bank list --file <file>          one staged file

Exit 0 clean, 1 a collision or a rejected entry, 2 a bank is missing or damaged.
"""

import argparse
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import tool_failed
from citation_key import ENTRY_HEADING, is_placeholder
from source_registry import FINDINGS_FIELDS, SOURCE_FIELDS

TOOL = "proposed_entries"

ENTRY = ENTRY_HEADING
FIELD = re.compile(r"^\*\*([^:*]+):\*\*")
NON_ENTRY_HEADING = re.compile(r"^#{1,6} (?!\[)")
SEPARATOR = "---"
PLACEHOLDER = "<Key>"

BANKS = ("list", "quotes")
FOLDER_NAME = "proposed-entries"
NEXT_STEPS = ("the check-facts skill's entry-format-check.py, entry-format-fix.py and "
              "list-quotes-join-check.py")


def proposed_folder(run_folder, bank):
    return Path(run_folder) / FOLDER_NAME / bank


def proposed_files(run_folder, bank):
    folder = proposed_folder(run_folder, bank)
    return sorted(str(path) for path in folder.glob("*.md")) if folder.is_dir() else []


def bank_path(config, bank):
    return config.sources.list if bank == "list" else config.sources.quotes


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def split_entries(text):
    entries, key, buffer, leftovers = [], None, [], []

    def close():
        if key:
            entries.append((key, "\n".join(buffer).rstrip()))

    for line in text.split("\n"):
        found = ENTRY.match(line)
        if found:
            close()
            key = found.group(1).strip()
            buffer = [line]
            continue
        if NON_ENTRY_HEADING.match(line):
            close()
            key, buffer = None, []
            leftovers.append(line)
            continue
        if key:
            buffer.append(line)
        elif leftovers:
            leftovers.append(line)
    close()
    return entries, "\n".join(leftovers)


def bank_keys(bank_text):
    keys = []
    for line in bank_text.split("\n"):
        found = ENTRY.match(line)
        if found and not is_placeholder(found.group(1).strip()):
            keys.append(found.group(1).strip())
    return keys


def field_problems(entry_body, approved, other_bank):
    misplaced, unapproved = [], []
    for line in entry_body.split("\n"):
        found = FIELD.match(line)
        if not found:
            continue
        name = found.group(1).strip()
        if name in approved:
            continue
        if name in other_bank:
            misplaced.append(name)
        else:
            unapproved.append(name)
    return misplaced, unapproved


def header_intact(bank_text):
    head = bank_text.split("\n### [", 1)[0]
    if "## Entry format" not in head:
        return False
    after = head.split("## Entry format", 1)[1]
    return after.count("```") >= 1 and PLACEHOLDER in bank_text


def insert(bank_text, key, entry_body):
    lines = bank_text.split("\n")
    positions = []
    for index, line in enumerate(lines):
        found = ENTRY.match(line)
        if found and not is_placeholder(found.group(1).strip()):
            positions.append((index, found.group(1).strip()))

    target = None
    for index, existing in positions:
        if existing.lower() > key.lower():
            target = index
            break

    block = entry_body.rstrip().split("\n") + ["", SEPARATOR, ""]
    if target is None:
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines + [""] + block).rstrip() + "\n"
    return "\n".join(lines[:target] + block + lines[target:])


def vocabularies(bank):
    if bank == "list":
        return SOURCE_FIELDS, FINDINGS_FIELDS
    return FINDINGS_FIELDS, SOURCE_FIELDS


def merge(bank, bank_path, staged_files, fix, verbose, next_steps=NEXT_STEPS):
    if not Path(bank_path).exists():
        sys.stderr.write(f"bank not found: {bank_path}\n")
        return 2
    if not staged_files:
        print(f"no proposed {bank} entries -- nothing to merge")
        return 0

    bank_text = read(bank_path)
    if not header_intact(bank_text):
        sys.stderr.write("REFUSING: the bank header looks damaged -- its `## Entry format` "
                         "block, fence or `<Key>` example is missing. Repair it first.\n")
        return 2

    approved, other_bank = vocabularies(bank)
    existing = {k.lower() for k in bank_keys(bank_text)}
    merged, collisions, rejected, leftovers_found = [], [], [], []

    for path in staged_files:
        text = read(path)
        entries, leftovers = split_entries(text)
        raw = len(re.findall(r"^### \[", text, re.M))
        if leftovers.strip():
            leftovers_found.append((path, len(leftovers.split("\n"))))
        note = "  + non-entry prose left for a person" if leftovers.strip() else ""
        warn = "" if raw == len(entries) else f"  ** raw headings {raw}, parsed {len(entries)}"
        print(f"\n{Path(path).name:<28} {len(entries):>3} entries{note}{warn}")

        for key, body in entries:
            if is_placeholder(key):
                continue
            misplaced, unapproved = field_problems(body, approved, other_bank)
            if misplaced:
                rejected.append((key, "other bank's field: " + ", ".join(misplaced)))
                print(f"   REJECT     [{key}] carries the other bank's field(s): {', '.join(misplaced)}")
                continue
            if unapproved:
                rejected.append((key, "unapproved: " + ", ".join(unapproved)))
                print(f"   REJECT     [{key}] unapproved field(s): {', '.join(unapproved)}")
                continue
            if key.lower() in existing:
                collisions.append((path, key))
                print(f"   COLLISION  [{key}] already in the bank -- skipped")
                continue
            merged.append((key, body))
            existing.add(key.lower())
            if verbose:
                print(f"   merge      [{key}]  ({len(body.split(chr(10)))} lines)")

    print(f"\n{'=' * 62}")
    print(f"to merge      {len(merged)}")
    print(f"collisions    {len(collisions)}   (existing entries are never overwritten)")
    print(f"rejected      {len(rejected)}   (wrong vocabulary -- fix the entry)")
    print(f"prose sections left for a person: {len(leftovers_found)}")
    for path, count in leftovers_found:
        print(f"   {Path(path).name}  ({count} lines)")

    if not fix:
        print("\ndry run -- pass --fix to apply")
        return 1 if (collisions or rejected) else 0

    for key, body in sorted(merged, key=lambda pair: pair[0].lower()):
        bank_text = insert(bank_text, key, body)
    if not header_intact(bank_text):
        sys.stderr.write("ABORTED before writing: the insert damaged the header. Bank unchanged.\n")
        return 2
    with open(bank_path, "w", encoding="utf-8") as handle:
        handle.write(bank_text)
    print(f"\nAPPLIED. The bank now holds {len(bank_keys(bank_text))} entries.")
    print("Now run: " + next_steps)
    return 1 if (collisions or rejected) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--run", help="the run folder whose proposed-entries/ to merge")
    parser.add_argument("--bank", choices=BANKS, help="only this bank (default: both)")
    parser.add_argument("--file", help="one staged file instead of a run folder (needs --bank)")
    parser.add_argument("--bank-file", help="the bank to merge into (default: from the config)")
    parser.add_argument("--fix", action="store_true", help="apply; otherwise a dry run")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    if not args.run and not args.file:
        parser.error("--run <run folder> or --file <file> is required")
    if args.file and not args.bank:
        parser.error("--file needs --bank list or --bank quotes")
    try:
        config = config_from_args(args)
    except ConfigError as error:
        return tool_failed(str(error), TOOL)
    worst = 0
    for bank in ([args.bank] if args.bank else BANKS):
        staged = [args.file] if args.file else proposed_files(args.run, bank)
        if not staged and not args.bank:
            continue
        print(f"== {bank} ==")
        target = args.bank_file or bank_path(config, bank)
        worst = max(worst, merge(bank, str(target), staged, args.fix, args.verbose))
    return worst


if __name__ == "__main__":
    sys.exit(main())
