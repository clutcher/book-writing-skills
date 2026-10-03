#!/usr/bin/env python3
"""Hold the entries of both source banks to the format each bank declares.

A format written into a file's header and enforced by nothing drifts back within a few
passes. Field-name sprawl is not cosmetic: every tool reads a bank by field name, so a
synonym is invisible to the reader that needs it (a URL filed under `Source link` is a
URL nothing will fetch). Each bank's `## Entry format` header is the specification; the
field lists live once, in lib/source_registry.py.

Classes (DEFECT unless marked):
  required            Full title, Authors, Year (sources list only)
  known-field         the field name is outside this bank's closed vocabulary
  label-colon         a label ends `.**`, or the bold closes before the colon; both
                      read as a field to a person and as prose to every tool
  doi-shape           DOI holds a bare DOI; DOI/URL holds a URL or a DOI
  doi-misfiled        a DOI reachable only inside DOI/URL or Venue prose, so nothing
                      resolves it (entry-format-fix.py moves it; same rule)
  dated-field         a date inside a field name (banks are dateless)
  verdict-field       a judgment about the book as a field name
  superseded          a "this supersedes the earlier entry" marker; correct in place
  premature-hash      a sha256 on a NOT YET FETCHED line
  cache-pointer       a cache line names a file that is not there
  cache-folder        a cache line names the default folder (sources/library) while
                      the book keeps its library in its own folder
                      (entry-format-fix.py rewrites it to sources.library)
  heading-truncated   the heading's short title is a mid-word cut of Full title
  heading-multi-key   a heading naming two keys hides the second
  entry-order         entries sorted by key, case-insensitively, within a section
  entry-separator     one `---` with a blank line either side before every entry;
                      a doubled rule hides entries and a rule under prose is a heading
  field-outside-entry a field after the entry's `---`, owned by no entry
  orphan-cache        cached text with no list entry claiming it
  pointer-path        a `Findings:` / `Source:` pointer names another path than the
                      configured bank (after the bank was moved; entry-format-fix.py rewrites it)
  unofficial-copy     ADVISORY. A book entry (one with an ISBN) links a file in a person's
                      GitHub repository or on a shadow-library site. In a public repository
                      that reads as linking to pirated books: link the publisher page or give
                      the ISBN only, and keep the download link in the private backup
  stale-not-read      INFORMATIONAL. A Note says the source was not read while the
                      quotes bank holds verified quotes from it. It only reports: the
                      repair is a prose rewrite per entry, and "abstract only" in
                      Access status can be a true, current limit, so only Note is read

Field ORDER is not checked: reordering old entries makes a huge diff for no reader.
Key order is checked, because an insertion point that depends on memory drifts.

Usage:
  entry-format-check.py                   both banks
  entry-format-check.py --bank list       one bank
  entry-format-check.py --file PATH       any bank file (its title decides the vocabulary)
  entry-format-check.py --self-test
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (SourceFolders, add_config_arguments, cache_references,
                          folders_from_config, is_configured_prefix, load_book, shown_path,
                          tool_failed)
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, SHARED_CLASSES, CheckReport,
                          add_output_arguments)
from citation_key import KEY_SHAPE
from source_registry import (FIELD_LINE_M, FINDINGS_FIELDS, SOURCE_FIELDS,
                             SOURCE_REQUIRED, is_findings_bank, read_bank,
                             separator_defects, show_separator)

TOOL = "entry-format-check"
CLASSES = {
    "required": DEFECT, "known-field": DEFECT, "label-colon": DEFECT, "doi-shape": DEFECT,
    "doi-misfiled": SHARED_CLASSES["doi-misfiled"], "dated-field": SHARED_CLASSES["dated-field"],
    "verdict-field": DEFECT, "superseded": DEFECT, "premature-hash": DEFECT,
    "cache-pointer": DEFECT, "cache-folder": DEFECT, "heading-truncated": DEFECT,
    "heading-multi-key": DEFECT, "entry-order": DEFECT, "entry-separator": DEFECT,
    "field-outside-entry": DEFECT, "orphan-cache": DEFECT, "stale-not-read": INFORMATIONAL,
    "pointer-path": DEFECT, "unofficial-copy": ADVISORY,
}
UNOFFICIAL_COPY = re.compile(
    r"https?://github\.com/[^/\s]+/[^/\s]+/raw/\S+"
    r"|\b(?:z-lib(?:rary)?|zlibrary|pdfdrive|libgen|dokumen\.pub|annas-archive)\b",
    re.I)
POINTER_PATH = re.compile(r"^see `([^`]+)`\s*$")

REQUIRED = SOURCE_REQUIRED
KNOWN = SOURCE_FIELDS
KNOWN_FINDINGS = FINDINGS_FIELDS

DATE_IN_NAME = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|\b(fix|fixed|applied|resolved|corrected|correction|updated|checked)\b[^,]{0,20}\b(19|20)\d{2}\b",
    re.I,
)
VERDICT_WORDS = re.compile(r"\b(verdict|resolved|fix applied|correction|supersedes?|superseded)\b", re.I)
DOI_SHAPE = re.compile(r"^10\.\d{4,9}/\S+$")
BARE_DOI = re.compile(r"^(doi:)?10\.\d{4,9}/\S+$", re.I)
DOI_IN_TEXT = re.compile(r"\b(10\.\d{4,9}/[^\s,;)\]]+)")
SUPERSEDED_LEAD = re.compile(
    r"^\*\*[^*\n]{0,80}\b(supersedes|superseded|replaces the (prior|previous|earlier))\b",
    re.I | re.M,
)
DOT_LABEL = re.compile(r"^\*\*([^*\n]+?)\.\*\*", re.M)
LOOSE_LABEL = re.compile(r"^\*\*([^*\n]+?)\*\*[^:*\n]{0,160}:", re.M)
FIELD_LINE = re.compile(r"^\*\*([^*:]+):\*\*")
SEPARATOR = "---"
NOT_READ_CLAIM = re.compile(
    r"abstract[- ]derived"
    r"|(?<!do )(?<!does )(?<!to )(?<!can )(?<!may )(?<!must )(?<!should )(?<!will )"
    r"\b(?:not|never)\s+(?:(?:yet|been|ever)\s+){0,2}read\b(?!\s+(?:it|them|this)\b)",
    re.I,
)
VERIFIED_QUOTES = re.compile(r"^\*\*Verified quotes:\*\*", re.M)


def strip_fenced(text):
    return re.sub(r"^```.*?^```", "", text, flags=re.M | re.S)


def entries(path):
    for entry in read_bank(path).entries:
        yield entry.key, entry.raw


def fields(block):
    return [m.groups() for m in FIELD_LINE_M.finditer(block)]


def misplaced_fields(block):
    found = []
    previous = None
    for line in block.split("\n"):
        if not line.strip():
            continue
        match = FIELD_LINE.match(line)
        if match and previous == SEPARATOR:
            found.append(match.group(1))
        previous = line.strip()
    return found


def quoted_keys(quotes_path):
    if not quotes_path or not Path(quotes_path).exists():
        return frozenset()
    return frozenset(key for key, block in entries(quotes_path) if VERIFIED_QUOTES.search(block))


def cache_line_issues(key, values, folders):
    issues = []
    for label in ("Cached text", "Cached original"):
        value = values.get(label, "")
        if "NOT YET FETCHED" in value:
            continue
        for written, folder_part, _name, resolved in cache_references(folders, value):
            if not resolved.exists():
                issues.append((key, "cache-pointer",
                               "%s points at a missing file: %s" % (label, written.strip("`"))))
            if not is_configured_prefix(folders, folder_part):
                issues.append((key, "cache-folder",
                               "%s names %s/, the cache folder is %s/"
                               % (label, folder_part, folders.shown_files)))
    return issues


def check(path, folders, quotes_path=None, is_findings=None, pointer_paths=None):
    issues = []
    pointer_paths = pointer_paths or {}
    if is_findings is None:
        is_findings = is_findings_bank(path)
    known = KNOWN_FINDINGS if is_findings else KNOWN
    required = () if is_findings else REQUIRED
    with_quotes = frozenset() if is_findings else quoted_keys(quotes_path)

    try:
        misordered = {b for _, b in read_bank(path).out_of_order()}
    except Exception:
        misordered = None

    previous_key = None
    for key, block in entries(path):
        names = [n for n, _ in fields(block)]
        values = dict(fields(block))
        heading = block.split("\n")[0]

        out_of_place = (key in misordered) if misordered is not None else (
            previous_key is not None and key.lower() < previous_key.lower())
        if out_of_place:
            issues.append((key, "entry-order", "sorts before [%s], which precedes it" % previous_key))
        previous_key = key

        extra_keys = [k for k in re.findall(r"\[([^\]]+)\]", heading)[1:] if KEY_SHAPE.match(k)]
        for extra in extra_keys:
            issues.append((key, "heading-multi-key", "heading also names [%s]; give it its own entry" % extra))

        for pattern, shape in ((DOT_LABEL, "%s.**"), (LOOSE_LABEL, "%s** ... :")):
            for match in pattern.finditer(block):
                base = re.split(r"[,(]| -- | -| — ", match.group(1))[0].strip()
                if base in known:
                    issues.append((key, "label-colon",
                                   "label written `**%s`; a field label ends in ':**'" % (shape % base)))

        if SUPERSEDED_LEAD.search(block):
            issues.append((key, "superseded", "carries a supersession marker; correct the entry in place instead"))

        for name in misplaced_fields(block):
            issues.append((key, "field-outside-entry",
                           "**%s:** sits after the entry's `---`; move it into this entry's field list" % name))

        if "not a citation key" in block.split("\n")[0].lower():
            continue

        for req in required:
            if req not in names:
                issues.append((key, "required", "missing **%s:**" % req))

        for name in names:
            if name in known:
                continue
            if DATE_IN_NAME.search(name):
                issues.append((key, "dated-field", "field name carries a date: %r" % name))
            elif VERDICT_WORDS.search(name):
                issues.append((key, "verdict-field", "field name states a verdict: %r" % name))
            else:
                issues.append((key, "known-field", "unapproved field name: %r -- not in this bank's vocabulary" % name))

        doi = values.get("DOI", "").strip()
        if doi and not DOI_SHAPE.match(doi):
            issues.append((key, "doi-shape", "DOI is not a bare DOI: %r" % doi[:60]))

        url = values.get("DOI/URL", "").strip()
        if url and not re.match(r"https?://", url) and not BARE_DOI.match(url):
            issues.append((key, "doi-shape", "DOI/URL holds neither URL nor DOI: %r" % url[:60]))

        if not doi:
            for carrier in ("DOI/URL", "Venue"):
                buried = DOI_IN_TEXT.search(values.get(carrier, ""))
                if buried:
                    issues.append((key, "doi-misfiled",
                                   "%s holds %s but there is no **DOI:** field" % (carrier, buried.group(1)[:40])))
                    break

        full_title = values.get("Full title", "").strip()
        quoted = re.search(r'"([^"]*)"', heading)
        if full_title and quoted:
            short = quoted.group(1)
            stem = short.rstrip()
            if stem and len(stem) < len(full_title) and full_title.lower().startswith(stem.lower()):
                following = full_title[len(stem):len(stem) + 1]
                if short != stem or (following and following not in " :,.;-"):
                    issues.append((key, "heading-truncated",
                                   "heading title %r is a mid-word cut of Full title" % short[-40:]))

        cached = values.get("Cached text", "")
        if "NOT YET FETCHED" in cached and "sha256" in cached:
            issues.append((key, "premature-hash", "checksum written before the file exists"))

        if key in with_quotes:
            for name, value in fields(block):
                claim = NOT_READ_CLAIM.search(value) if name == "Note" else None
                if claim:
                    issues.append((key, "stale-not-read",
                                   "Note says %r, but the quotes entry carries verified quotes"
                                   % claim.group(0)))
                    break

        if "ISBN" in values:
            for name in ("Access URLs", "Cached original", "DOI/URL"):
                found = UNOFFICIAL_COPY.search(values.get(name, ""))
                if found:
                    issues.append((key, "unofficial-copy",
                                   "**%s:** links %s; give the publisher page or the ISBN, and keep "
                                   "the download link in the private backup" % (name, found.group(0)[:60])))
                    break

        issues.extend(cache_line_issues(key, values, folders))
        for label, wanted in pointer_paths.items():
            pointed = POINTER_PATH.match(values.get(label, "").strip())
            if pointed and pointed.group(1) != wanted:
                issues.append((key, "pointer-path", "**%s:** points at %s; the bank is %s"
                               % (label, pointed.group(1), wanted)))

    for key, written in separator_defects(read_bank(path)):
        issues.append((key, "entry-separator",
                       "introduced by `%s`; entries are separated by one `---` with a "
                       "blank line either side" % show_separator(written)))

    if not is_findings:
        issues.extend(orphan_caches(path, folders))
    return issues


def orphan_caches(sources_list, folders):
    known = {key for key, _ in entries(sources_list)}
    found = []
    folder = Path(folders.files)
    if not folder.is_dir():
        return found
    for path in sorted(folder.iterdir()):
        name = path.name
        if not name.endswith(".txt") or name.endswith(".src.txt"):
            continue
        key = name.split(".", 1)[0]
        if key not in known:
            found.append((key, "orphan-cache",
                          "cached text with no list entry: %s" % folders.shown_file(name)))
    return found


FIXTURE_SOURCES = '''# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Full title:** the title as printed on the work
**Findings:** see `sources/quotes.md`
```

---

### [Aaa01] Aaa, "A Field In Its Place" (2001)

**Full title:** A Field In Its Place
**Authors:** A. Aaa
**Year:** 2001
**Cached text:** `{d}/Aaa01.txt` (fetched 2025-01-01, sha256 abc)
**Findings:** see `sources/quotes.md`

---

### [Bbb02] Bbb, "A Field Past The Separator" (2002)

**Full title:** A Field Past The Separator
**Authors:** B. Bbb
**Year:** 2002
**Cached text:** `{other}/Bbb02.txt` (fetched 2025-01-01, sha256 abc)

---

**Findings:** see `sources/quotes.md`

---

### [Ccc03] Ccc, "Read, And Recorded As Unread" (2003)

**Full title:** Read, And Recorded As Unread
**Authors:** C. Ccc
**Year:** 2003
**Note:** Surfaced by a keyword search; the paper was not read.
**Findings:** see `sources/quotes.md`

---

### [Ddd04] Ddd, "Genuinely Unread" (2004)

**Full title:** Genuinely Unread
**Authors:** D. Ddd
**Year:** 2004
**Note:** Not read; nothing in the book may rest on it.
**Cached text:** `{d}/Ddd04.txt` (fetched 2025-01-01, sha256 abc)

---
### [Eee05] Eee, "Findings Without Quotes" (2005)

**Full title:** Findings Without Quotes
**Authors:** E. Eee
**Year:** 2005
**Note:** Not yet read, so the summary here is the abstract only.
**Findings:** see `sources/quotes.md`

---

### [Fff06] Fff, "Abstract Only Is An Access Limit" (2006)

**Full title:** Abstract Only Is An Access Limit
**Authors:** F. Fff
**Year:** 2006
**Access status:** READABLE (abstract only), a recorded talk with no transcript
**Findings:** see `sources/quotes.md`

---

### [Ggg07] Ggg, "Do Not Read It As Evidence" (2007)

**Full title:** Do Not Read It As Evidence
**Authors:** G. Ggg
**Year:** 2007
**Note:** The page is an error in the printed book, so do not read it as evidence that the extraction is corrupt.
**Findings:** see `sources/quotes.md`

---

### [Iii09] Iii, "Abstract-Derived Beside Full-Text Quotes" (2009)

**Full title:** Abstract-Derived Beside Full-Text Quotes
**Authors:** I. Iii
**Year:** 2009
**Note:** Surfaced by a keyword search. Abstract-derived (paper-level).
**Findings:** see `sources/quotes.md`

---

### [Jjj10] Jjj, "A Book Linked From Someone's Repository" (2010)

**Full title:** A Book Linked From Someone's Repository
**Authors:** J. Jjj
**Year:** 2010
**ISBN:** 9780000000002
**Access URLs:** https://github.com/someone/books/raw/master/a-book.pdf
**Findings:** see `sources/quotes.md`

---

### [Kkk11] Kkk, "A Paper The Author Shares Freely" (2011)

**Full title:** A Paper The Author Shares Freely
**Authors:** K. Kkk
**Year:** 2011
**Access URLs:** https://github.com/kkk/papers/raw/main/paper.pdf
**Findings:** see `sources/quotes.md`

---
'''

FIXTURE_FINDINGS = '''# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Verified quotes:** exact strings, in quotation marks
**Source:** see `sources/list.md`
```

The header is required: the bank parser refuses a bank whose `## Entry format` block
is missing, because that block is how it proves the header and entries split cleanly.

---
---

### [Aaa01] Aaa, "A Field In Its Place" (2001)

**Verified quotes:** "the words as printed"
**Source:** see `sources/list.md`

---

### [Ccc03] Ccc, "Read, And Recorded As Unread" (2003)

**Verified quotes:**
- Results: "the words as printed"
**Source:** see `sources/list.md`

---

### [Eee05] Eee, "Findings Without Quotes" (2005)

**Role:** registered for a reading-order question
**Source:** see `sources/list.md`

---

### [Fff06] Fff, "Abstract Only Is An Access Limit" (2006)

**Verified quotes:** "the words as spoken"
**Source:** see `sources/list.md`

---

### [Ggg07] Ggg, "Do Not Read It As Evidence" (2007)

**Verified quotes:** "the words as printed"
**Source:** see `sources/list.md`

---

### [Hhh08] Hhh, "A Field Past The Separator" (2008)

**Verified quotes:** "the words as printed"

---

**Source:** see `sources/list.md`

---

### [Iii09] Iii, "Abstract-Derived Beside Full-Text Quotes" (2009)

**Verified quotes:**
- Conclusions (p. 12): "the words as printed"
**Source:** see `sources/list.md`

---
'''

FIXTURE_EXPECTED = {
    "list.md": {
        ("Bbb02", "field-outside-entry"),
        ("Bbb02", "cache-folder"),
        ("Ccc03", "stale-not-read"),
        ("Iii09", "stale-not-read"),
        ("Eee05", "entry-separator"),
        ("Ddd04", "cache-pointer"),
        ("Zzz99", "orphan-cache"),
        ("Jjj10", "unofficial-copy"),
    },
    "quotes.md": {
        ("Hhh08", "field-outside-entry"),
        ("Aaa01", "entry-separator"),
    },
}


def self_test():
    failures = 0
    with tempfile.TemporaryDirectory() as root:
        files = Path(root) / "evidence" / "cache"
        files.mkdir(parents=True)
        folders = SourceFolders(root=Path(root), files=files, origin=files)
        other = "sources/library"
        for name in ("Aaa01.txt", "Zzz99.txt"):
            (files / name).write_text("cached\n", encoding="utf-8")
        (files / "Bbb02.txt").write_text("cached\n", encoding="utf-8")
        list_path = Path(root) / "list.md"
        quotes_path = Path(root) / "quotes.md"
        list_path.write_text(FIXTURE_SOURCES.replace("{d}", folders.shown_files)
                             .replace("{other}", other), encoding="utf-8")
        quotes_path.write_text(FIXTURE_FINDINGS, encoding="utf-8")
        found = {
            "list.md": {(k, r) for k, r, _ in check(list_path, folders, quotes_path, False)},
            "quotes.md": {(k, r) for k, r, _ in check(quotes_path, folders, None, True)},
        }

    for name, expected in sorted(FIXTURE_EXPECTED.items()):
        for key, rule in sorted(expected - found[name]):
            print("FAIL %-10s %-14s NOT REPORTED in %s" % (key, rule, name))
            failures += 1
        for key, rule in sorted(found[name] - expected):
            print("FAIL %-10s %-14s FALSE POSITIVE in %s" % (key, rule, name))
            failures += 1
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % failures))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--bank", choices=("list", "quotes", "both"), default="both")
    parser.add_argument("--file", help="check this bank file instead (its title decides the vocabulary)")
    parser.add_argument("--self-test", action="store_true",
                        help="only check the rules against built-in fixtures")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    folders = folders_from_config(config)
    quotes_path = config.sources.quotes
    if args.file:
        targets = [(Path(args.file), None)]
    else:
        targets = []
        if args.bank in ("list", "both"):
            targets.append((config.sources.list, False))
        if args.bank in ("quotes", "both"):
            targets.append((config.sources.quotes, True))

    report = CheckReport(TOOL, CLASSES)
    for path, is_findings in targets:
        if args.file and not Path(path).exists():
            return tool_failed("bank not found: %s" % path, TOOL)
        if report.skip_unless_present(path, "quotes bank" if is_findings else "sources list"):
            return report.emit(args.format)
        label = "quotes" if (is_findings if is_findings is not None else is_findings_bank(path, config)) else "list"
        pointers = {"Findings": shown_path(config.root, config.sources.quotes),
                    "Source": shown_path(config.root, config.sources.list)}
        for key, rule, detail in check(path, folders, quotes_path, is_findings, pointers):
            report.add(key, rule, "%s: %s" % (label, detail))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
