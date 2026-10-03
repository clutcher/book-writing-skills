#!/usr/bin/env python3
"""Bring existing entries of both source banks to the declared format.

The companion of entry-format-check.py, which reports deviations. This fixes the
mechanical subset of them and refuses the rest. The gate and this fixer are one rule:
when they disagree the gate reports clean while a backlog grows, so change both
together, and after a clean fix this script must report `0 changed`.

What it fixes:
  field-name    a bespoke field name becomes **Note:**. Where the name carried
                information the prose does not ("Relationship to [Kim19]", "Why it is
                here"), it is folded into the note as a lead-in; a plain synonym for
                "note" just disappears.
  dated-field   a field name carrying a tracking stamp becomes **Note:** with the date
                moved into the prose (banks are dateless).
  doi-misfiled  a DOI buried in DOI/URL or Venue prose gets its own **DOI:** field;
                a source whose DOI no tool can read cannot be resolved or looked up.
  doi-url       a DOI/URL holding a citation string moves to Venue (when Venue is
                empty); every fetcher expects something it can request there.
  doi-url-redundant / venue-had-doi   the DOI repeated in DOI/URL or Venue is removed
                once it has its own field.
  pointer       a list entry whose key has a quotes entry gains the **Findings:**
                pointer, derived from the quotes bank's headings, after the LAST FIELD
                of the entry (never after its `---`, where it would belong to the next
                entry).
  separator     an entry heading not introduced by one `---` with a blank line either
                side gets it. A doubled rule hides entries from every parser. Only the
                run of blank and `---` lines before an entry is rewritten.
  cache-folder  a cache line naming the other layout's cache folder is rewritten to
                the book's `sources.library` folder.

What it refuses: anything that needs knowing the source. A missing Full title cannot
be invented, a URL cannot be guessed, a Venue already holding different content is
left alone. And a field outside the QUOTES bank's closed vocabulary is reported, not
renamed, because that bank has no Note field to fold it into (renaming Note to itself
would rewrite the file on every run).

Entry boundaries, the field marker and both vocabularies come from lib/source_registry.py.

Usage:
  entry-format-fix.py                   dry run over both banks: show every change
  entry-format-fix.py --fix             apply
  entry-format-fix.py --bank quotes     one bank
  entry-format-fix.py --fix --backup PATH
  entry-format-fix.py --self-test

Exit 0 nothing to change, 1 changes pending (dry run) or a refusal, 2 the tool failed.
"""

import argparse
import collections
import contextlib
import io
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (SourceFolders, add_config_arguments, cache_references,
                          folders_from_config, is_configured_prefix, load_book,
                          shown_path, tool_failed)
from source_registry import (ENTRY_SEPARATOR, FIELD_LINE, FIELD_LINE_M,
                             SOURCE_FIELDS, Entry, fields_for, is_findings_bank,
                             parse_bank, read_bank, separator_defects,
                             show_separator, split_separator, with_separator)
from check_output import skipped_for_missing

TOOL = "entry-format-fix"


GENERIC = {"note", "notes", "content note", "access note", "note s"}
DATE_STAMP = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|\b(fix|fixed|applied|resolved|corrected|correction|updated|checked)\b[^,]{0,20}\b(19|20)\d{2}\b",
    re.I,
)

FENCE = re.compile(r"^```.*?^```", re.M | re.S)


def strip_fenced(text):
    return FENCE.sub("", text)


def find_field(block, name):
    for found in FIELD_LINE_M.finditer(strip_fenced(block)):
        if found.group(1) == name:
            return found
    return None


def field_value(found):
    return found.group(2).strip() if found else ""


def lead_in(name):
    text = name.strip().rstrip(".:")
    return text[0].lower() + text[1:] if text else text


DOI_IN_TEXT = re.compile(r"\b(10\.\d{4,9}/[^\s<>\"',;\]]+)")


def trim_doi(doi):
    doi = doi.rstrip(".,;")
    while doi.endswith(")") and doi.count(")") > doi.count("("):
        doi = doi[:-1].rstrip(".,;")
    return doi


def lift_doi(key, block, changes):
    if field_value(find_field(block, "DOI")):
        return block
    for field_name in ("DOI/URL", "Venue"):
        holder = find_field(block, field_name)
        if not holder:
            continue
        found = DOI_IN_TEXT.search(holder.group(2))
        if not found:
            continue
        doi = trim_doi(found.group(1))
        anchor = holder.group(0)
        block = block.replace(anchor, "**DOI:** %s\n%s" % (doi, anchor), 1)
        changes.append((key, "doi-misfiled", "%s held %s" % (field_name, doi), "**DOI:**"))
        return block
    return block


def split_doi_url(key, block, changes):
    doi_field = find_field(block, "DOI")
    url_field = find_field(block, "DOI/URL")
    if not field_value(doi_field) or not url_field:
        return block
    value = field_value(url_field)
    if value.startswith("http") or not value:
        return block

    parenthetical = re.search(r"\(([^)]*(?:\([^)]*\)[^)]*)*)\)\s*$", value)
    has_venue = field_value(find_field(block, "Venue"))
    block = block.replace(url_field.group(0) + "\n", "", 1)
    if parenthetical and not has_venue:
        block = block.replace(doi_field.group(0), doi_field.group(0) + "\n**Venue:** " + parenthetical.group(1).strip(), 1)
        changes.append((key, "doi-url-redundant", "DOI/URL repeated the DOI", "**Venue:** " + parenthetical.group(1)[:34]))
    else:
        changes.append((key, "doi-url-redundant", "DOI/URL repeated the DOI", "removed"))
    return block


def clean_venue(key, block, changes):
    doi_field = find_field(block, "DOI")
    venue = find_field(block, "Venue")
    if not field_value(doi_field) or not venue:
        return block
    doi = field_value(doi_field).split()[0]
    value = venue.group(2)
    subbed = re.sub(r"[;.,]?\s*(https?://\S*)?" + re.escape(doi) + r"\S*", "", value)
    if subbed == value:
        return block
    cleaned = subbed.strip().rstrip(".;, ")
    if cleaned:
        block = block.replace(venue.group(0), "**Venue:** " + cleaned, 1)
        changes.append((key, "venue-had-doi", value[:44], cleaned[:44]))
    return block


SEPARATOR = "---"
CACHE_LINE = re.compile(r"^\*\*(Cached text|Cached original):\*\*.*$", re.M)


def pointer_line(quotes_shown):
    return "**Findings:** see `%s`" % quotes_shown


POINTER_VALUE = re.compile(r"^see `[^`]+`\s*$")


def rewrite_pointer_path(key, block, changes, wanted_line):
    if not wanted_line:
        return block
    label = wanted_line.split(":**", 1)[0][2:]
    found = find_field(block, label)
    if not found or not POINTER_VALUE.match(found.group(2).strip()):
        return block
    if found.group(0).strip() == wanted_line:
        return block
    changes.append((key, "pointer-path", found.group(2).strip()[:44], wanted_line.split(":** ", 1)[1]))
    return block.replace(found.group(0), wanted_line, 1)


def findings_keys(path):
    if not path or not Path(path).exists():
        return set()
    return set(read_bank(path).keys)


def rewrite_cache_folders(key, block, changes, folders):
    if folders is None:
        return block
    for line in CACHE_LINE.finditer(strip_fenced(block)):
        text = line.group(0)
        fixed = text
        for written, folder_part, name, _resolved in cache_references(folders, text):
            if not is_configured_prefix(folders, folder_part):
                fixed = fixed.replace(written, "`%s`" % folders.shown_file(name), 1)
        if fixed != text:
            block = block.replace(text, fixed, 1)
            changes.append((key, "cache-folder", text.split("`")[1][:44], folders.shown_files))
    return block


def field_line_numbers(block):
    inside_fence = False
    found = []
    for index, line in enumerate(block.split("\n")):
        if line.startswith("```"):
            inside_fence = not inside_fence
            continue
        if not inside_fence and FIELD_LINE.match(line):
            found.append(index)
    return found


def add_pointer(key, block, changes, have_findings, pointer):
    if key not in have_findings:
        return block

    lines = block.split("\n")
    positions = field_line_numbers(block)
    if any(FIELD_LINE.match(lines[index]).group(1) == "Findings" for index in positions):
        return block

    changes.append((key, "pointer", "no **Findings:** field", pointer[:34] + "..."))

    if not positions:
        body = block.rstrip("\n")
        return body + "\n" + pointer + block[len(body):]

    insert_at = positions[-1] + 1
    while insert_at < len(lines):
        nxt = lines[insert_at]
        if not nxt.strip() or nxt.strip() == SEPARATOR or nxt.startswith("### "):
            break
        if insert_at in positions:
            break
        insert_at += 1

    return "\n".join(lines[:insert_at] + [pointer] + lines[insert_at:])


def normalise_entry(entry, changes, refusals, known=SOURCE_FIELDS, have_findings=frozenset(),
                    pointer=pointer_line("sources/quotes.md"), folders=None, backlink=None):
    key = entry.key
    out = entry.raw
    can_fold_into_note = "Note" in known

    for field in entry.fields:
        if field.name in known:
            continue
        label_line = field.raw.split("\n", 1)[0]
        value = field.line_value
        if not can_fold_into_note:
            refusals.append((key, "unapproved",
                             "**%s:** is outside this bank's closed vocabulary, which has "
                             "no Note field to fold it into: %s" % (field.name, value[:40])))
            continue
        if label_line not in out:
            continue
        if field.name.strip().lower() in GENERIC:
            replacement = "**Note:** %s" % value
            kind = "field-name"
        elif DATE_STAMP.search(field.name):
            replacement = "**Note:** %s: %s" % (lead_in(field.name), value)
            kind = "dated-field"
        else:
            replacement = "**Note:** %s -- %s" % (lead_in(field.name), value)
            kind = "field-name"
        out = out.replace(label_line, replacement, 1)
        changes.append((key, kind, "**%s:**" % field.name, "**Note:**"))

    out = lift_doi(key, out, changes)
    out = split_doi_url(key, out, changes)
    out = clean_venue(key, out, changes)

    url_field = find_field(out, "DOI/URL")
    if url_field:
        value = field_value(url_field)
        looks_fetchable = value.startswith("http") or value.startswith("10.")
        if value and not looks_fetchable:
            if find_field(out, "Venue"):
                refusals.append((key, "doi-url", "Venue already occupied; citation string left in DOI/URL: %s" % value[:52]))
            else:
                out = out.replace(url_field.group(0), "**Venue:** %s" % value, 1)
                changes.append((key, "doi-url", "**DOI/URL:** %s" % value[:44], "**Venue:**"))

    out = rewrite_cache_folders(key, out, changes, folders)
    out = rewrite_pointer_path(key, out, changes, backlink if backlink else pointer)
    out = add_pointer(key, out, changes, have_findings, pointer)
    return out


def normalise_separators(header, texts, segments, changes):
    pieces = [header] + list(texts)
    for index, segment in enumerate(segments):
        if not isinstance(segment, Entry):
            continue
        written = split_separator(pieces[index])[1]
        if written == ENTRY_SEPARATOR:
            continue
        pieces[index] = with_separator(pieces[index])
        changes.append((segment.key, "separator", show_separator(written),
                        show_separator(ENTRY_SEPARATOR)))
    return pieces[0], pieces[1:]


FIXTURE_SOURCES = '''# Sources List

**Kind:** Bank -- dateless truth, kept current. Git is the history.
**Does NOT hold:** what the source says. Verbatim quotes live in the other bank.

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Full title:** the title as printed on the work
**Cited in chapters:** RETIRED -- one grep produces it, so the field went stale
**Findings:** see `sources/quotes.md`
```

---

### [Aaa01] Alpha, "A cached paper" (2001)

**Full title:** A cached paper whose last field wraps onto a second line
**Authors:** A. Alpha
**Year:** 2001
**DOI:** 10.5555/aaa01
**DOI/URL:** https://doi.org/10.5555/aaa01
**Fetch note:** the cached PDF is the whole package plus the peer commentary, so a
grep hit may be a commentator rather than the author.

---
---

### [Bbb02] Beta, "A hand-named note field" (2002)

**Full title:** An entry whose note field was named by hand
**Authors:** B. Beta
**Year:** 2002
**Relationship to [Kim19]:** the earlier study this one replicates

---

### [Ccc03] Charlie, "A generic label" (2003)

**Full title:** An entry whose label means nothing beyond "this is a note"
**Authors:** C. Charlie
**Year:** 2003
**Notes:** the plural label carried no information the prose does not

---

### [Ddd04] Delta, "A dated field name" (2004)

**Full title:** An entry that dated its own field name
**Authors:** D. Delta
**Year:** 2004
**Cached text:** `review/sources/Ddd04.txt` (fetched 2025-01-01, sha256 abc)
**Fix applied 2025-05-04:** the DOI was resolved and the entry corrected

---

### [Wal--] Walsh, "A living catalog" (--)

**Full title:** A living catalog
**Authors:** Kay Walsh
**Year:** --
**Access URLs:** https://catalog.example.org/

---

### [SFD+25a] Sigma, Delta & Foxtrot, "First of two 2025 papers" (2025)

**Full title:** The first of two papers by the same authors in one year
**Authors:** S. Sigma, D. Delta, F. Foxtrot
**Year:** 2025
**Venue:** Journal of Nothing In Particular, 12(3), 1-20
**Access status:** PAYWALLED at the publisher

---

### [Tan94] Tanner, "A Field Guide to Pond Plants" (1994)

**Full title:** A Field Guide to Pond Plants
**Authors:** Sarah Tanner
**Year:** 1994
**Edition:** 2nd ed.; quotations come from this printing. First published 1986.
**Publisher:** Example Press
**Venue:** Example Press
**ISBN:** 9780000000019
**DOI/URL:** Example Press, 2nd ed., 412 pp.

---

### [Dun88] Dunmore, "Coastal Hedges" (1988)

**Full title:** Hedges for Exposed Coastal Farms
**Authors:** Fiona E. Dunmore
**Year:** 1988
**DOI/URL:** Bulletin of an Example Society, 13(2), 88-95

---

### [Kem77] Kemp, "Soil Colour" (1977)

**Full title:** Reading the Colour of Field Soil
**Authors:** Clara Kemp
**Year:** 1977
**Venue:** Bulletin of an Example Society, 9(3), 140-147, 10.5555/100200.100201

---

### [Fen04] Fenwick, "The Allotment Year" (2004)

**Full title:** The Allotment Year
**Authors:** Lucy Fenwick
**Year:** 2004
**Edition:** 2nd ed.; the manuscript cites the 3rd ed. as [Fen15]. Edition history.
**Publisher:** Example Press
**Identifier:** LCCN 1996-000000
**ISBN:** 9780000000026
**Record history:** kept when the 3rd ed. was acquired under its own key
**Fetch note:** the cache holds the publisher sample chapter only
**Note:** do not hang a 3rd ed. page number on this entry
**Findings:** see `sources/quotes.md`

---

### [BGMW20] Bell, Grant, Moss & Wells, "Lost sleep" (2020)

**Full title:** The effect of road noise on sleep quality
**Authors:** Tara Bell, Hugo Grant, Anton Moss, Jan Wells
**Year:** 2020
**Relation:** replaces [BMW18] for the lost-sleep figure in chapter 12

---
'''

FIXTURE_FINDINGS = '''# Quotes Bank

**Kind:** Bank -- dateless truth, kept current. Git is the history.

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Verified quotes:** exact strings, in quotation marks
**Relation:** how this source bears on another key
**Source:** see `sources/list.md`
```

---

### [Aaa01] Alpha, "A cached paper" (2001)

**Verified quotes:** confirmed against the page image.
- p. 87 (Abstract): "a single, central yield averaging about four tonnes"
**Key findings:** the four-tonne figure is a regional average across farms
**Role:** the grounding for one chapter
**Scope:** small farms, one region
**Guardrail:** THE FIGURE IS A REGIONAL AVERAGE, NOT ONE FARM'S YIELD.
**Quote origin:** the words are the author's own, not a commentator's
**Relation:** corroborates [Mor56] on yield while revising the number
**Last verified:** 2025-08-12
**Source:** see `sources/list.md`

---

### [Wal--] Walsh, "A living catalog" (--)

**Key findings:** the catalog renamed one entry between versions
**Last verified:** 2025-08-12
**Source:** see `sources/list.md`

---

### [Fen04] Fenwick, "The Allotment Year" (2004)

**Key findings:** chapter 4 argues for keeping the beds covered
**Last verified:** 2025-08-12
**Source:** see `sources/list.md`

---
'''

EXPECTED_SOURCE_CHANGES = {
    ("Aaa01", "pointer"),
    ("Bbb02", "separator"),
    ("Bbb02", "field-name"),
    ("Ccc03", "field-name"),
    ("Ddd04", "dated-field"),
    ("Ddd04", "cache-folder"),
    ("Wal--", "pointer"),
    ("Dun88", "doi-url"),
    ("Kem77", "doi-misfiled"),
    ("Kem77", "venue-had-doi"),
    ("BGMW20", "field-name"),
}
EXPECTED_SOURCE_REFUSALS = {("Tan94", "doi-url")}

FIXTURE_FINDINGS_NOTE = '''# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Key findings:** what the source establishes, in the source's own terms
**Source:** see `sources/list.md`
```

---

### [Aaa01] Alpha, "A cached paper" (2001)

**Key findings:** the four-tonne figure is a regional average
**Note:** a Note field, which this bank's closed vocabulary does not include
**Last verified:** 2025-08-12
**Source:** see `sources/list.md`

---
'''

FIXTURE_NON_ENTRY_SECTION = '''# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Full title:** the title as printed on the work
```

---

### [Aaa01] Alpha, "An entry followed by a section" (2001)

**Full title:** An entry whose pointer must land inside it, not after the section below
**Authors:** A. Alpha
**Year:** 2001
**Access URLs:** https://example.org/aaa01

---

## Works identified and not fetched

**Bespoke name here:** a field-shaped line that belongs to no entry

---
'''

CHANGE_LINE = re.compile(r"^(\S+)[ \t]+(\S+)[ \t]+.* -> .*$", re.M)
REFUSAL_LINE = re.compile(r"^  (\S+)[ \t]+(\S+)[ \t]+\S.*$", re.M)


def _run(argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main([str(argument) for argument in argv])
    return buffer.getvalue()


def _reported(output):
    body, _, refused = output.partition("REFUSED (needs a person):")
    changes = {(key, kind) for key, kind in CHANGE_LINE.findall(body)}
    refusals = {(key, kind) for key, kind in REFUSAL_LINE.findall(refused)}
    return changes, refusals


def self_test():
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as root:
        Path(root, "sources", "library").mkdir(parents=True)
        sources = Path(root, "sources", "list.md")
        findings = Path(root, "sources", "quotes.md")
        with open(sources, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_SOURCES)
        with open(findings, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_FINDINGS)
        os.chdir(root)
        try:
            def fix(path):
                return _run(["--file", path, "--quotes", findings, "--fix"])

            first = fix(sources)
            after_one = open(sources, encoding="utf-8").read()
            second = fix(sources)
            after_two = open(sources, encoding="utf-8").read()
            findings_first = fix(findings)
            findings_one = open(findings, encoding="utf-8").read()
            findings_second = fix(findings)
            findings_two = open(findings, encoding="utf-8").read()

            note_bank = Path(root, "note-in-quotes.md")
            with open(note_bank, "w", encoding="utf-8") as handle:
                handle.write(FIXTURE_FINDINGS_NOTE)
            fix(note_bank)
            note_one = open(note_bank, encoding="utf-8").read()
            note_second = fix(note_bank)
            note_two = open(note_bank, encoding="utf-8").read()

            section_bank = Path(root, "non-entry-section.md")
            with open(section_bank, "w", encoding="utf-8") as handle:
                handle.write(FIXTURE_NON_ENTRY_SECTION)
            section_first = fix(section_bank)
            section_one = open(section_bank, encoding="utf-8").read()
            section_second = fix(section_bank)
            section_two = open(section_bank, encoding="utf-8").read()
        finally:
            os.chdir(cwd)

    print("== bank detection")
    require("bank: list" in first, "the list fixture was not read as the sources list")
    require("bank: quotes" in findings_first,
            "the quotes fixture was not read as the quotes bank")
    require("**Cached text:** `sources/library/Ddd04.txt`" in after_one,
            "[Ddd04]'s cache line was not moved to the configured folder")

    print("\n== changes reported")
    changes, refusals = _reported(first)
    for key, kind in sorted(EXPECTED_SOURCE_CHANGES - changes):
        failures.append("%s %s NOT REPORTED" % (key, kind))
    for key, kind in sorted(changes - EXPECTED_SOURCE_CHANGES):
        failures.append("%s %s FALSE POSITIVE" % (key, kind))
    for key, kind in sorted(EXPECTED_SOURCE_REFUSALS - refusals):
        failures.append("%s %s NOT REFUSED" % (key, kind))
    for key, kind in sorted(refusals - EXPECTED_SOURCE_REFUSALS):
        failures.append("%s %s REFUSED UNEXPECTEDLY" % (key, kind))
    for key, kind in sorted(changes):
        print("  %-8s %s" % (key, kind))
    for key, kind in sorted(refusals):
        print("  %-8s %s (refused)" % (key, kind))

    print("\n== where the pointer lands")
    wrapped = ("grep hit may be a commentator rather than the author.\n"
               "**Findings:** see `sources/quotes.md`\n\n---")
    require(wrapped in after_one,
            "the pointer did not land after the wrapped last field of [Aaa01]")
    require("---\n**Findings:**" not in after_one and "---\n\n**Findings:**" not in after_one,
            "a pointer landed after a separator: the 95-entry bug is back")
    require("**Access URLs:** https://catalog.example.org/\n**Findings:**" in after_one,
            "[Wal--] did not get a pointer, so the -- year key was not read as an entry")
    print("  after the last field, never after a separator")

    print("\n== the entry separator")
    require("**Findings:** see `sources/quotes.md`\n\n---\n\n"
            '### [Bbb02] Beta, "A hand-named note field" (2002)' in after_one,
            "the doubled rule before [Bbb02] was not collapsed")
    require("---\n---" not in after_one, "a doubled rule survived, and it hides entries")
    for text, label in ((after_one, "sources"), (findings_one, "findings"),
                        (note_one, "note"), (section_one, "section")):
        left = separator_defects(parse_bank(text))
        require(not left, "%s fixture still has mis-separated entries: %s" % (label, left))
    require("**Access URLs:** https://example.org/aaa01\n**Findings:** see "
            "`sources/quotes.md`\n\n---\n\n"
            "## Works identified and not fetched" in section_one,
            "the boundary before a NON-entry section was rewritten; only entry "
            "separators are this script's business")
    print("  one `---`, blank line either side, before every entry heading")

    print("\n== renames")
    for fragment, label in (
            ("**Note:** relationship to [Kim19] -- the earlier study this one replicates",
             "bespoke name folded in as a lead-in"),
            ("**Note:** the plural label carried no information the prose does not",
             "generic name dropped whole"),
            ("**Note:** fix applied 2025-05-04: the DOI was resolved and the entry corrected",
             "tracking stamp moved into the prose"),
            ("**Note:** relation -- replaces [BMW18] for the lost-sleep figure",
             "findings field in the sources bank"),
            ("**Venue:** Bulletin of an Example Society, 13(2), 88-95",
             "citation string out of DOI/URL and into Venue"),
            ("**DOI:** 10.5555/100200.100201\n**Venue:** Bulletin of an Example Society, 9(3), 140-147\n",
             "DOI lifted out of a Venue string, and the Venue then cleaned")):
        require(fragment in after_one, "%s: not applied" % label)
        print("  %s" % label)
    require("**Notes:**" not in after_one, "a generic label survived")
    require("**Relation:**" not in after_one, "a findings field survived in the sources bank")

    print("\n== left alone")
    for block, label in (
            ("**Cited in chapters:** RETIRED", "the fenced format template"),
            ("**Kind:** Bank -- dateless truth", "the header prose before the first entry"),
            ("**Edition:** 2nd ed.; the manuscript cites the 3rd ed. as [Fen15]. Edition history.\n"
             "**Publisher:** Example Press\n"
             "**Identifier:** LCCN 1996-000000\n"
             "**ISBN:** 9780000000026\n"
             "**Record history:** kept when the 3rd ed. was acquired under its own key\n"
             "**Fetch note:** the cache holds the publisher sample chapter only\n"
             "**Note:** do not hang a 3rd ed. page number on this entry\n"
             "**Findings:** see `sources/quotes.md`",
             "[Fen04]'s six-name vocabulary, and no second pointer"),
            ("**Venue:** Journal of Nothing In Particular, 12(3), 1-20\n"
             "**Access status:** PAYWALLED at the publisher",
             "[SFD+25a], the a/b/c discriminator, unchanged"),
            ("**DOI/URL:** Example Press, 2nd ed., 412 pp.",
             "[Tan94]'s refused DOI/URL, still in place")):
        require(block in after_one, "%s: was modified" % label)
        print("  %s" % label)

    print("\n== idempotence")
    require(after_one == after_two, "the sources bank changed on the second run")
    second_changes, _ = _reported(second)
    require(not second_changes,
            "the second sources run still reports: %s" % sorted(second_changes))
    require(findings_one == findings_two, "the findings bank changed on the second run")
    print("  sources: byte-identical and silent on the second run")
    print("  findings: byte-identical on the second run")
    findings_changes, _ = _reported(findings_second)
    require(not findings_changes,
            "the findings run reports without changing bytes: %s" % sorted(findings_changes))

    print("\n== an unapproved field in the findings bank is refused, not rewritten")
    require(note_one == FIXTURE_FINDINGS_NOTE,
            "the findings fixture was rewritten; an unapproved name must not be folded "
            "into a field this bank's vocabulary does not have")
    require(note_one == note_two, "the note fixture changed on the second run")
    require("**Note:** a Note field" in note_two, "the unapproved field was not left intact")
    note_changes, note_refusals = _reported(note_second)
    require(not note_changes,
            "an unapproved findings field is still reported as a change: %s" % sorted(note_changes))
    require(note_refusals == {("Aaa01", "unapproved")},
            "the refusal did not come out as expected: %s" % sorted(note_refusals))
    print("  refused and reported, zero changes, and the file is never rewritten,")
    print("  so 'the normaliser reports 0 changed' stays reachable.")

    print("\n== a mid-file section that is not an entry")
    require("**Access URLs:** https://example.org/aaa01\n**Findings:**" in section_one,
            "the pointer did not land inside [Aaa01]; a non-entry section absorbed it")
    require("**Bespoke name here:** a field-shaped line that belongs to no entry" in section_one,
            "a field-shaped line in a non-entry section was renamed")
    require(section_one.count("**Findings:**") == 1,
            "the pointer was written more than once")
    section_changes, _ = _reported(section_first)
    require(section_changes == {("Aaa01", "pointer")},
            "the section fixture reported unexpected changes: %s" % sorted(section_changes))
    require(section_one == section_two, "the section fixture changed on the second run")
    require(not _reported(section_second)[0], "the section fixture still reports on rerun")
    print("  passed through verbatim, and the pointer stayed inside the entry that owns it")

    print()
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %d expected changes, %d refusals, %d discrepancies"
          % (len(EXPECTED_SOURCE_CHANGES), len(EXPECTED_SOURCE_REFUSALS), len(failures)))
    return 1 if failures else 0


def normalise_text(text, path, is_findings, have_findings, pointer, folders, backlink=None):
    known = fields_for(is_findings)
    bank = parse_bank(text, path)
    changes, refusals, out = [], [], []
    for segment in bank.segments:
        out.append(normalise_entry(segment, changes, refusals, known, have_findings,
                                   pointer, None if is_findings else folders,
                                   backlink if is_findings else None)
                   if isinstance(segment, Entry) else segment.raw)
    header, out = normalise_separators(bank.header, out, bank.segments, changes)
    result = header + "".join(out)
    after = parse_bank(result, path)
    if after.keys != bank.keys:
        raise RuntimeError("the entry list changed -- %d keys before, %d after"
                           % (len(bank.keys), len(after.keys)))
    if not changes and result != text:
        raise RuntimeError("nothing reported changed, but the bytes differ")
    return result, changes, refusals


def print_changes(changes, refusals):
    for key, kind, before, after in changes:
        print("%-10s %-12s %s -> %s" % (key, kind, before[:58], after))
    if refusals:
        print("\nREFUSED (needs a person):")
        for key, kind, detail in refusals:
            print("  %-10s %-10s %s" % (key, kind, detail))
    counts = collections.Counter(kind for _, kind, _, _ in changes)
    print()
    for kind, number in counts.most_common():
        print("%-12s %d" % (kind, number))
    print("%-12s %d changed, %d refused" % ("TOTAL", len(changes), len(refusals)))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--bank", choices=("list", "quotes", "both"), default="both")
    parser.add_argument("--file", help="normalise this bank file instead (its title decides the vocabulary)")
    parser.add_argument("--quotes", help="the quotes bank the pointers are derived from "
                                         "(default: sources.quotes)")
    parser.add_argument("--fix", action="store_true", help="apply changes (default is a dry run)")
    parser.add_argument("--backup", metavar="PATH", help="copy the bank here before writing")
    parser.add_argument("--self-test", action="store_true",
                        help="only check the rules against built-in fixtures")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    folders = folders_from_config(config)
    quotes_path = args.quotes or config.sources.quotes
    pointer = pointer_line(shown_path(config.root, quotes_path)) if quotes_path else None
    backlink = ("**Source:** see `%s`" % shown_path(config.root, config.sources.list)
                if config.sources.list else None)
    if args.file:
        targets = [Path(args.file)]
    else:
        targets = []
        if args.bank in ("list", "both"):
            targets.append(config.sources.list)
        if args.bank in ("quotes", "both"):
            targets.append(config.sources.quotes)

    pending = refused = 0
    for path in targets:
        if args.file and not Path(path).exists():
            return tool_failed("bank not found: %s" % path, TOOL)
        if skipped_for_missing(TOOL, path, "bank"):
            return 0
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        is_findings = is_findings_bank(text)
        have_findings = set() if is_findings else findings_keys(quotes_path)
        print("bank: %s (%s)" % ("quotes" if is_findings else "list", shown_path(config.root, path)))
        try:
            result, changes, refusals = normalise_text(text, str(path), is_findings,
                                                       have_findings, pointer, folders, backlink)
        except RuntimeError as error:
            return tool_failed("internal error: %s" % error, TOOL)
        print_changes(changes, refusals)
        refused += len(refusals)
        if args.fix:
            if result == text:
                print("\nunchanged -- nothing written to %s" % path)
            else:
                if args.backup:
                    shutil.copy(path, args.backup)
                    print("\nbacked up to %s" % args.backup)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(result)
                print("applied to %s" % path)
        else:
            pending += len(changes)
            print("\ndry run -- pass --fix to apply")
        print()
    return 1 if (pending or refused) else 0


if __name__ == "__main__":
    sys.exit(main())
