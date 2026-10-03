#!/usr/bin/env python3
"""Check every bibliography key against the alpha key rule, and fix the renames with --fix.

The rule lives in lib/citation_key.py (real BibTeX alpha); this script only applies it:
  1 author   the surname fragment, or its first three letters when the fragment is one
             character                                              Smi99
  2-4        one fragment per author, NO '+'                        ABCD94
  5 or more  the first THREE fragments, then '+'                    ABC+20
A fragment is the first letter of every token of the surname: lower-case particles are
kept (van Berg -> vB), every word of a multi-word surname counts (Perez Molina -> PM), a
hyphen splits tokens (Owen-Price -> OP), and each token keeps its own case.
Several entries with the same computed key get a, b, c. A work whose date cannot be
established takes `--` in the entry and the key (Wal--); an access date is never a date.

Organisation, "et al." and "eds." entries are listed for a person rather than guessed:
their author list cannot be parsed into "Surname, Initials" units reliably.

Classes:
  key-rename        DEFECT        the key differs from the one the author list derives
  org-or-unparsed   INFORMATIONAL (shared) an organisation or an unparsed author list
  et-al             INFORMATIONAL a truncated author list
  no-year           INFORMATIONAL no year and no `--` in the entry

--fix renames across the bibliography and every manuscript file the config lists
(keys inside [A, B, C] brackets too), then proves two-way integrity: every cited key
still resolves. It exits 1 if any citation no longer resolves.

Usage:
  citation-key-check.py
  citation-key-check.py --references <refs.md> --fix
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
from source_files import (add_config_arguments, load_book, manuscript_paths,
                          markdown_files_under, tool_failed)
from check_output import (DEFECT, INFORMATIONAL, SHARED_CLASSES, CheckReport,
                          add_output_arguments, skipped_for_missing)
from citation_key import BIB_ENTRY_ANY, KEY_BODY, derive, surnames_from_author_text

TOOL = "citation-key-check"
CLASSES = {
    "key-rename": DEFECT,
    "org-or-unparsed": SHARED_CLASSES["org-or-unparsed"],
    "et-al": INFORMATIONAL,
    "no-year": INFORMATIONAL,
}

KEY_RE = BIB_ENTRY_ANY
YEAR_RE = re.compile(r'\((?:c\.\s*)?((?:1[89]|20)\d{2})')
NO_DATE_RE = re.compile(r'\((?:--|n\.d\.)\)')
MANUAL_FLAGS = ("org-or-unparsed", "et-al", "no-year")


def load_entries(refs_path):
    entries = []
    for lineno, line in enumerate(Path(refs_path).read_text(encoding='utf-8').splitlines(), 1):
        m = KEY_RE.match(line)
        if not m:
            continue
        key, rest = m.group(1), m.group(2)
        ym = YEAR_RE.search(rest)
        nd = NO_DATE_RE.search(rest)
        if not ym and not nd:
            entries.append({'key': key, 'line': lineno, 'year': None,
                            'surnames': [], 'flags': ['no-year'], 'expected': None})
            continue
        year2 = ym.group(1)[-2:] if ym else '--'
        author_text = rest[:(ym or nd).start()]
        surnames, flags = surnames_from_author_text(author_text)
        expected = derive(surnames, year2) if surnames else None
        entries.append({'key': key, 'line': lineno, 'year': year2,
                        'surnames': surnames, 'flags': flags, 'expected': expected})
    return entries


def build_rename_map(entries):
    by_base = defaultdict(list)
    for e in entries:
        if e['expected'] and 'org-or-unparsed' not in e['flags'] and 'et-al' not in e['flags']:
            by_base[e['expected']].append(e)
    rename = {}
    for base, group in by_base.items():
        group.sort(key=lambda e: e['line'])
        if len(group) == 1:
            if group[0]['key'] != base:
                rename[group[0]['key']] = base
            continue
        for index, e in enumerate(group):
            proposed = base + chr(ord('a') + index)
            if e['key'] != proposed:
                rename[e['key']] = proposed
    return rename


def apply_fix(rename, refs_path, manuscript_files):
    files = [Path(refs_path)] + [Path(path) for path in manuscript_files]
    files = list(dict.fromkeys(path.resolve() for path in files))
    ordered = sorted(rename, key=len, reverse=True)
    changed = 0
    for path in files:
        text = path.read_text(encoding='utf-8')
        original = text
        for old in ordered:
            text = re.sub(r'(?<=[\[,\s])' + re.escape(old) + r'(?=[\],\s])', rename[old], text)
        if text != original:
            path.write_text(text, encoding='utf-8')
            changed += 1
    return changed


CITE_BLOCK = re.compile(r'\[(' + KEY_BODY + r'(?:\s*,\s*' + KEY_BODY + r')*)\]')


def collect_cited_keys(manuscript_files, refs_path):
    refs_resolved = Path(refs_path).resolve()
    cited = defaultdict(set)
    for path in (Path(item) for item in manuscript_files):
        if path.resolve() == refs_resolved:
            continue
        for match in CITE_BLOCK.finditer(path.read_text(encoding='utf-8')):
            for key in (k.strip() for k in match.group(1).split(',')):
                cited[key].add(path.name)
    return cited


def verify_integrity(refs_path, manuscript_files, entries):
    bib_keys = {e['key'] for e in entries}
    cited = collect_cited_keys(manuscript_files, refs_path)
    missing = sorted(k for k in cited if k not in bib_keys)
    print("Integrity check: %d cited keys, %d bibliography entries." % (len(cited), len(bib_keys)))
    for key in missing:
        print("  ERROR [%s] cited in %s but not in the bibliography"
              % (key, ", ".join(sorted(cited[key]))))
    return not missing


FIXTURE_REFERENCES = """# References

[Smith01] Smith, J. (2001). A thing.
[AB95] Adams, A. & Baker, B. (1995). Two authors.
[Jon05] Jones, A. (2005). First of two.
[Jon05] Jones, B. (2005). Second of two.
[Acm17] Acme Research. (2017). A report.
[ABC+20] Adams, A., Baker, B., Clark, C., et al. (2020). Truncated.
[Wal--] Walsh, K. (--). Undated.
"""

FIXTURE_CHAPTER = "As shown [Smith01, AB95]. Again [Jon05].\n"


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        manuscript = Path(root) / "manuscript"
        manuscript.mkdir()
        refs = manuscript / "900-references.md"
        refs.write_text(FIXTURE_REFERENCES, encoding="utf-8")
        (manuscript / "110-chapter-1.md").write_text(FIXTURE_CHAPTER, encoding="utf-8")
        entries = load_entries(refs)
        rename = build_rename_map(entries)
        manual = {e['key']: e['flags'] for e in entries if set(e['flags']) & set(MANUAL_FLAGS)}
        if rename.get("Smith01") != "Smi01":
            failures.append("Smith01 should become Smi01: %s" % rename)
        if "AB95" in rename or "Wal--" in rename:
            failures.append("a correct key was renamed: %s" % rename)
        if "org-or-unparsed" not in manual.get("Acm17", []):
            failures.append("an organisation was not left for a person")
        if "et-al" not in manual.get("ABC+20", []):
            failures.append("a truncated list was not left for a person")
        files = markdown_files_under(manuscript)
        apply_fix({"Smith01": "Smi01"}, refs, files)
        chapter = (manuscript / "110-chapter-1.md").read_text(encoding="utf-8")
        if "[Smi01, AB95]" not in chapter:
            failures.append("a key inside a multi-key bracket was not renamed: %r" % chapter)
        if not verify_integrity(refs, files, load_entries(refs)):
            failures.append("integrity failed after a clean rename")
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument('--references', help='the bibliography (default: manuscript.references)')
    parser.add_argument('--manuscript-dir', help="folder --fix renames in (default: the book's manuscript files)")
    parser.add_argument('--fix', action='store_true',
                        help='apply the renames across the bibliography and the manuscript')
    parser.add_argument('--self-test', action='store_true', help='run the built-in examples')
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    refs = args.references or config.manuscript.references
    manuscript = manuscript_paths(config, TOOL, args.manuscript_dir)
    if args.references and not Path(refs).is_file():
        return tool_failed("bibliography not found: %s" % refs, TOOL)
    if skipped_for_missing(TOOL, refs, "bibliography", args.format):
        return 0

    entries = load_entries(refs)
    rename = build_rename_map(entries)
    if args.fix and rename:
        changed = apply_fix(rename, refs, manuscript)
        print("Applied %d renames across %d file(s)." % (len(rename), changed))
        if not verify_integrity(refs, files, load_entries(refs)):
            return 1
        entries = load_entries(refs)
        rename = build_rename_map(entries)

    report = CheckReport(TOOL, CLASSES)
    line_of = {e['key']: e['line'] for e in entries}
    for key in sorted(rename, key=lambda k: line_of.get(k, 0)):
        report.add(key, "key-rename", "line %d: should be %s" % (line_of.get(key, 0), rename[key]))
    for e in entries:
        for flag in e['flags']:
            if flag in MANUAL_FLAGS:
                report.add(e['key'], flag, "line %d: author list is not machine-parseable" % e['line'])
    if args.format == "text":
        print("Entries parsed: %d\n" % len(entries))
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
