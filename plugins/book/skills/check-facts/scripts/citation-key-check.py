#!/usr/bin/env python3
"""Check every .bib key against the alpha key rule, and rename the wrong ones with --fix.

The rule lives in lib/citation_key.py (real BibTeX alpha) and the names come from the .bib
entry (lib/bibliography.py); this script only applies it:
  1 author   the surname fragment, or its first three letters when the fragment is one
             character                                              Smi99
  2-4        one fragment per author, NO '+'                        ABCD94
  5 or more  the first THREE fragments, then '+'; `and others` counts as a name
                                                                    ABC+20
A fragment is the first letter of every token of the surname: lower-case particles are
kept (van Berg -> vB), every word of a multi-word surname counts (Perez Molina -> PM), a
hyphen splits tokens (Owen-Price -> OP), and each token keeps its own case.
Several entries with the same computed key get a, b, c, in the order alpha.bst sorts them
(names, then year, then title without a leading "A", "An" or "The"). A work with no year
takes `--` in the key (Wal--). An entry with a `crossref` takes the author, editor and
year it lacks from the entry it names, as BibTeX does.

Classes:
  key-rename        DEFECT        the key differs from the one the entry's names derive
  org-or-unparsed   INFORMATIONAL (shared) no author or editor to build a key from, or a
                                  name with no Latin letters: a person chooses the key
  no-year           INFORMATIONAL the entry has no year, so the key ends in `--`

--fix renames each key in one pass: the .bib entry, the sources list and quotes bank
headings (and `[Key]` pointers inside the two banks), and every citation in the manuscript
and the thinking files (`[@Key]`, `@Key`, `@{Key}`). It then proves that every cited key
still resolves in the .bib, and exits 1 if one does not. A `crossref` that names a renamed
key is renamed too.

Usage:
  citation-key-check.py
  citation-key-check.py --fix
  citation-key-check.py --self-test
"""

import argparse
import re
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from bibliography import (BibliographyError, expected_key, parse_bibliography, plain_text,
                          read_bibliography, write_bibliography)
from check_output import (DEFECT, INFORMATIONAL, SHARED_CLASSES, CheckReport,
                          add_output_arguments, skipped_for_missing)
from citations import cited_keys, rename_key
from source_files import (add_config_arguments, load_book, manuscript_paths,
                          markdown_files_under, thinking_paths, tool_failed)

TOOL = "citation-key-check"
CLASSES = {
    "key-rename": DEFECT,
    "org-or-unparsed": SHARED_CLASSES["org-or-unparsed"],
    "no-year": INFORMATIONAL,
}
PASSING_KEY = "rename-in-progress-{}!"


def label_of(entry):
    try:
        return expected_key(entry), None
    except ValueError as error:
        return None, str(error)


def labeled_entries(bibliography):
    return [bibliography.with_inherited_fields(entry) for entry in bibliography.entries.values()]


def sorted_title(title):
    for article in ("The ", "An ", "A "):
        if title.startswith(article):
            title = title[len(article):]
    title = re.sub(r"[-~]", " ", title)
    return re.sub(r"[^\w\s]", "", title).lower()


def alpha_sort_position(entry):
    names = " ".join(f"{name.surname} {plain_text(name.first)}"
                     for name in entry.authors or entry.editors)
    return (names.lower(), entry.plain("year"), sorted_title(entry.plain("title")), entry.line)


def build_rename_map(entries):
    by_label = defaultdict(list)
    for entry in entries:
        label, _ = label_of(entry)
        if label:
            by_label[label].append(entry)
    rename = {}
    for label, group in by_label.items():
        group.sort(key=alpha_sort_position)
        letters = [""] if len(group) == 1 else [chr(ord("a") + index)
                                                for index in range(len(group))]
        for entry, letter in zip(group, letters):
            if entry.key != label + letter:
                rename[entry.key] = label + letter
    return rename


def unkeyed_entries(entries):
    found = []
    for entry in entries:
        label, problem = label_of(entry)
        if label is None:
            found.append((entry, problem or "no author or editor to build a key from"))
    return found


def rename_in_text(text, rename):
    passing = {old: PASSING_KEY.format(index) for index, old in enumerate(rename)}
    for old, middle in passing.items():
        text, _ = rename_key(text, old, middle)
        text = rename_bank_pointer(text, old, middle)
    for old, middle in passing.items():
        text, _ = rename_key(text, middle, rename[old])
        text = rename_bank_pointer(text, middle, rename[old])
    return text


def rename_bank_pointer(text, old_key, new_key):
    return re.sub(r"(?<=\[)" + re.escape(old_key) + r"(?=\])", lambda _: new_key, text)


def rename_in_bibliography(bibliography, rename):
    passing = {old: PASSING_KEY.format(index) for index, old in enumerate(rename)}
    for old, middle in passing.items():
        bibliography.rename(old, middle)
    for old, middle in passing.items():
        bibliography.rename(middle, rename[old])


def apply_fix(rename, bibliography, text_files):
    if not rename:
        return 0
    rename_in_bibliography(bibliography, rename)
    write_bibliography(bibliography.path, bibliography)
    changed = 1
    for path in dict.fromkeys(Path(item).resolve() for item in text_files):
        original = path.read_text(encoding="utf-8")
        text = rename_in_text(original, rename)
        if text != original:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(text)
            changed += 1
    return changed


def cited_places(text_files):
    cited = defaultdict(set)
    for path in (Path(item) for item in text_files):
        for key in cited_keys(path.read_text(encoding="utf-8")):
            cited[key].add(path.name)
    return cited


def verify_integrity(bibliography_path, text_files):
    known = set(read_bibliography(bibliography_path).keys)
    cited = cited_places(text_files)
    missing = sorted(key for key in cited if key not in known)
    print(f"Integrity check: {len(cited)} cited keys, {len(known)} bibliography entries.")
    for key in missing:
        print(f"  ERROR @{key} cited in {', '.join(sorted(cited[key]))} but not in the .bib")
    return not missing


def library_files_under(library, keys):
    if not library or not Path(library).is_dir():
        return []
    return sorted(path.name for path in Path(library).iterdir()
                  if path.is_file() and path.name.split(".", 1)[0] in keys)


FIXTURE_BIBLIOGRAPHY = """@book{Smith01,
  author = {Smith, John},
  title = {A Thing},
  year = {2001},
}

@book{AB95,
  author = {Adams, Ann and Baker, Bob},
  title = {Two Authors},
  year = {1995},
}

@book{Jon05x,
  author = {Jones, Bea},
  title = {Second of Two},
  year = {2005},
}

@book{Jon05y,
  author = {Jones, Amy},
  title = {First of Two},
  year = {2005},
}

@techreport{Exa17,
  institution = {Example Research},
  title = {A Report},
  year = {2017},
}

@misc{Wal--,
  author = {Walsh, Kim},
  title = {Undated},
}
"""

FIXTURE_CHAPTER = "As shown [@Smith01; @AB95, p. 3]. Again @Jon05x and @{Wal--}.\n"

FIXTURE_LIST = ("# Sources List\n\n## Entry format\n\n```\n### [<Key>]\n```\n\n"
                "### [Smith01]\n\n**Note:** see [Smith01] and [Smith012]\n")


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        bibliography_path = Path(root) / "references.bib"
        bibliography_path.write_text(FIXTURE_BIBLIOGRAPHY, encoding="utf-8")
        manuscript = Path(root) / "manuscript"
        manuscript.mkdir()
        chapter = manuscript / "110-chapter-1.md"
        chapter.write_text(FIXTURE_CHAPTER, encoding="utf-8")
        sources_list = Path(root) / "list.md"
        sources_list.write_text(FIXTURE_LIST, encoding="utf-8")
        bibliography = read_bibliography(bibliography_path)
        entries = list(bibliography.entries.values())
        rename = build_rename_map(entries)
        expected = {"Smith01": "Smi01", "Jon05y": "Jon05a", "Jon05x": "Jon05b"}
        if rename != expected:
            failures.append(f"renames should be {expected}: {rename}")
        unkeyed = [entry.key for entry, _ in unkeyed_entries(entries)]
        if unkeyed != ["Exa17"]:
            failures.append(f"an entry with no names was not left for a person: {unkeyed}")
        apply_fix(rename, bibliography, markdown_files_under(manuscript) + [sources_list])
        text = chapter.read_text(encoding="utf-8")
        if text != "As shown [@Smi01; @AB95, p. 3]. Again @Jon05b and @{Wal--}.\n":
            failures.append(f"the chapter was not renamed as expected: {text!r}")
        listed = sources_list.read_text(encoding="utf-8")
        if "### [Smi01]" not in listed or "see [Smi01] and [Smith012]" not in listed:
            failures.append(f"the sources list was not renamed as expected: {listed!r}")
        keys = read_bibliography(bibliography_path).keys
        if sorted(keys) != sorted(["Smi01", "AB95", "Jon05b", "Jon05a", "Exa17", "Wal--"]):
            failures.append(f"the .bib keys after the fix are wrong: {keys}")
        if not verify_integrity(bibliography_path, [chapter]):
            failures.append("integrity failed after a clean rename")
        same_author = parse_bibliography(
            "@article{Ken72a, author = {Kent, Ada}, title = {The Plain Road}, year = {1972}}\n"
            "@article{Ken72b, author = {Kent, Ada}, title = {Notes on Hills}, year = {1972}}\n")
        letters = build_rename_map(list(same_author.entries.values()))
        if letters != {"Ken72a": "Ken72b", "Ken72b": "Ken72a"}:
            failures.append(f"a leading 'The' should not count when sorting titles: {letters}")
        swapped = rename_in_text("First [@Smi05b]. Then [@Smi05a].\n",
                                 {"Smi05b": "Smi05a", "Smi05a": "Smi05b"})
        if swapped != "First [@Smi05a]. Then [@Smi05b].\n":
            failures.append(f"two keys that swap places were merged: {swapped!r}")
    for line in failures:
        print(f"FAIL {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--bibliography", help="the .bib file (default: sources.bibliography)")
    parser.add_argument("--manuscript-dir",
                        help="folder --fix renames in (default: the book's manuscript files)")
    parser.add_argument("--fix", action="store_true",
                        help="rename the keys in the .bib, the two banks, the manuscript and "
                             "the thinking files")
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    return parser.parse_args()


def text_files_of(config, manuscript):
    banks = [path for path in (config.sources.list, config.sources.quotes)
             if path and Path(path).is_file()]
    references = config.manuscript.references
    return [path for path in manuscript + thinking_paths(config) + banks
            if not references or Path(path).resolve() != Path(references).resolve()]


def report_findings(args, entries, rename):
    report = CheckReport(TOOL, CLASSES)
    line_of = {entry.key: entry.line for entry in entries}
    for key in sorted(rename, key=lambda found: line_of.get(found, 0)):
        report.add(key, "key-rename", f"line {line_of.get(key, 0)}: should be {rename[key]}")
    for entry, problem in unkeyed_entries(entries):
        report.add(entry.key, "org-or-unparsed", f"line {entry.line}: {problem}")
    for entry in entries:
        if not entry.field("year"):
            report.add(entry.key, "no-year", f"line {entry.line}: no year, so the key ends in --")
    if args.format == "text":
        print(f"Entries read: {len(entries)}\n")
    return report.emit(args.format)


def main():
    args = parse_arguments()
    if args.self_test:
        return self_test()
    config = load_book(args, TOOL)
    bibliography_path = args.bibliography or config.sources.bibliography
    if args.bibliography and not Path(bibliography_path).is_file():
        return tool_failed(f"bibliography not found: {bibliography_path}", TOOL)
    if skipped_for_missing(TOOL, bibliography_path, "bibliography", args.format):
        return 0
    manuscript = manuscript_paths(config, TOOL, args.manuscript_dir)
    try:
        bibliography = read_bibliography(bibliography_path)
    except (OSError, BibliographyError) as error:
        return tool_failed(f"cannot read {bibliography_path}: {error}", TOOL)
    entries = labeled_entries(bibliography)
    rename = build_rename_map(entries)
    if args.fix and rename and not manuscript:
        return tool_failed("no manuscript files found; --fix would rename keys in the .bib "
                           "but not in the text", TOOL)
    if args.fix and rename:
        text_files = text_files_of(config, manuscript)
        changed = apply_fix(rename, bibliography, text_files)
        print(f"Applied {len(rename)} renames across {changed} file(s).")
        left = library_files_under(config.sources.library, set(rename))
        if left:
            print(f"Library files still named by the old key: {', '.join(left)}")
        if not verify_integrity(bibliography_path, text_files):
            return 1
        entries = labeled_entries(read_bibliography(bibliography_path))
        rename = build_rename_map(entries)
    return report_findings(args, entries, rename)


if __name__ == "__main__":
    sys.exit(main())
