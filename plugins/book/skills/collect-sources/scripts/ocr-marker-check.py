#!/usr/bin/env python3
"""Keep machine-read (OCR) text marked as OCR in all three places.

An OCR extraction reads exactly like a clean one, and its errors cluster where they
hurt most: l/1, O/0, 5/S, 8/B, rn/m. The failure is a quoted FIGURE that was never in
the paper, carried into the book with a citation attached. "224 ms" and "22A ms" are
one glyph apart.

Three markers make an OCR source hard to mistake:

  1. an OCR origin record (engine, dpi, pages)
  2. an `=== OCR-PROVENANCE ===` header at the top of `<Key>.txt`
  3. `Access status: ... READABLE VIA OCR` in the sources list

ocr.py writes all three. Any other route writes some subset, and a marker present on
most sources and absent on a few is worse than none: it teaches a reader that unmarked
means clean.

Classes (all DEFECT):
  unmarked-ocr        OCR on disk, the list does not say READABLE VIA OCR
  claimed-not-ocr     the list says READABLE VIA OCR, no OCR marker on disk
  missing-ocr-record  provenance header but no OCR origin record (engine, dpi unknown)
  missing-header      OCR origin record but the extraction carries no warning
  unconfirmed-digits  a quotes entry quotes DIGITS from OCR text and does not record
                      that they were checked against the page image

`unconfirmed-digits` counts only the digits INSIDE quotation marks, because page
anchors (`p. 19:`, `II-2:`) are digits too and carry no figure a book could inherit.
When quotation marks are missing or do not pair up, the whole field is counted: for
this rule a false positive costs a sentence and a false negative costs a wrong figure
in print. The accepted confirmations are matched loosely (page image, page render,
read visually, at NNN dpi); the form for new entries is:

    **Verified quotes:** confirmed against the page image.

This check cannot see INHERITED OCR: a scan that arrived with someone else's OCR
already in its text layer carries no marker at all, exactly like a clean born-digital
file. Finding that from the PDF itself is scan-origin-check.py's job.

Usage:
  ocr-marker-check.py
  ocr-marker-check.py --self-test
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (OCR, SourceFolders, add_config_arguments, folders_from_config,
                          load_book, tool_failed)
from check_output import DEFECT, CheckReport, add_output_arguments, skipped_for_missing
from source_registry import read_bank

TOOL = "ocr-marker-check"
CLASSES = {
    "unmarked-ocr": DEFECT,
    "claimed-not-ocr": DEFECT,
    "missing-ocr-record": DEFECT,
    "missing-header": DEFECT,
    "unconfirmed-digits": DEFECT,
}

PROVENANCE = re.compile(r"OCR[- ]PROVENANCE")
IMAGE_CONFIRMED = re.compile(
    r"page image|page render|read visually|reading the scan|at \d{2,4}\s*dpi|"
    r"\d{2,4}\s*dpi (page )?(image|render|scan)",
    re.I,
)
QUOTED = re.compile(r'"([^"]*)"|“([^”]*)”')


def entries(path):
    for entry in read_bank(path).entries:
        yield entry.key, entry


def field(entry, name):
    return entry.field(name) or ""


def quoted_digits(value):
    unbalanced = value.count('"') % 2 or value.count("“") != value.count("”")
    spans = [group for found in QUOTED.finditer(value)
             for group in found.groups() if group is not None]
    if spans and not unbalanced:
        return re.findall(r"\d", " ".join(spans)), "quoted material"
    return re.findall(r"\d", value), "whole field (quotation marks missing or unpaired)"


def ocr_on_disk(folders):
    recorded = folders.keys_with_origin_record(OCR)
    header = set()
    folder = Path(folders.files)
    if folder.is_dir():
        for path in folder.glob("*.txt"):
            with open(path, errors="ignore", encoding="utf-8") as handle:
                if PROVENANCE.search(handle.read(600)):
                    header.add(path.name.split(".", 1)[0])
    return recorded, header


def check(sources_list, quotes, folders):
    issues = []
    recorded, header = ocr_on_disk(folders)
    on_disk = recorded | header

    declared = set()
    for key, entry in entries(sources_list):
        if "READABLE VIA OCR" in field(entry, "Access status").upper():
            declared.add(key)

    for key in sorted(on_disk - declared):
        issues.append((key, "unmarked-ocr",
                       "extraction is OCR but Access status does not say READABLE VIA OCR"))
    for key in sorted(declared - on_disk):
        issues.append((key, "claimed-not-ocr",
                       "the list says READABLE VIA OCR but there is no OCR record and no header"))
    for key in sorted(header - recorded):
        issues.append((key, "missing-ocr-record",
                       "provenance header but no OCR origin record, so engine and dpi are unknown"))
    for key in sorted(recorded - header):
        issues.append((key, "missing-header",
                       "OCR origin record exists but %s.txt carries no warning to whoever greps it"
                       % key))

    for key, entry in entries(quotes):
        if key not in on_disk:
            continue
        digits, scope = quoted_digits(field(entry, "Verified quotes"))
        if not digits or IMAGE_CONFIRMED.search(entry.raw):
            continue
        issues.append((key, "unconfirmed-digits",
                       "%d digit(s) in the %s, from OCR text with no record of a "
                       "page-image check" % (len(digits), scope)))
    return issues


DISK = {
    "TR81": (True, True, True),
    "SAB11": (True, True, False),
    "TWC88": (True, False, True),
    "Cro91": (True, True, True),
    "Yat83": (True, True, True),
    "Yat83.second-scan": (True, True, True),
    "Bro96": (True, True, True),
    "Pen97": (True, True, True),
    "Ree74": (True, True, True),
    "Smi01": (True, False, False),
    "Wes02": (True, False, False),
    "KL00": (False, False, False),
}
DECLARED = {"SAB11", "TWC88", "Cro91", "Yat83", "Bro96", "Pen97", "Ree74", "KL00"}

FIXTURE_LIST_HEADER = '''# Sources List

## Entry format

```
### [<Key>]

**Access status:** READABLE VIA OCR (engine at NNN dpi)
```

'''

FIXTURE_LIST_ENTRY = '''### [%s]

**Access status:** %s

---

'''

FIXTURE_QUOTES = '''# Quotes Bank

## Entry format

```
### [<Key>]

**Verified quotes:** exact strings, in quotation marks
```

### [Cro91]

**Verified quotes:**
- p. 4: "the tide had to turn within 100 minutes"
**Key findings:** the figure is quoted straight out of the extraction
**Last verified:** 2025-08-12

---

### [Yat83]

**Verified quotes:** confirmed against the page image at 150 dpi.
- p. 12: "we kept 64 hives and lost none of them that winter"
**Key findings:** the figure was read off the render, not the extraction
**Last verified:** 2025-08-12

---

### [Bro96]

**Verified quotes:**
- p. 19: "a field guide to the hedgerow plants of one county"
**Key findings:** prose only, so a bad glyph is visible to a reader
**Last verified:** 2025-08-12

---

### [TWC88]

**Verified quotes:** II-2: "the well nearest the market - namely the old pump."
**Key findings:** the only digit in the field is the section anchor
**Last verified:** 2025-08-12

---

### [Pen97]

**Verified quotes:**
- p. 88, paraphrased rather than quoted, so no quotation marks are present at all
**Key findings:** nothing separates the anchor from the wording, so the whole field counts
**Last verified:** 2025-08-12

---

### [Ree74]

**Verified quotes:**
- p. 336: "the 12 weirs, and the quotation is never closed
**Key findings:** the quotation marks do not pair up, so the whole field counts
**Last verified:** 2025-08-12

---

### [Smi01]

**Verified quotes:**
- p. 114: "the average garden kept between three and five beds in use"
**Key findings:** born-digital, and its operator remapping belongs to another check
**Last verified:** 2025-08-12

---

### [Wes02]

**Verified quotes:**
- p. 297: "a thick mulch cut the watering time by 40 per cent"
**Key findings:** the scan arrived with someone else's OCR already in its text layer
**Last verified:** 2025-08-12

---
'''

FIXTURE_EXPECTED = {
    ("TR81", "unmarked-ocr"),
    ("KL00", "claimed-not-ocr"),
    ("SAB11", "missing-ocr-record"),
    ("TWC88", "missing-header"),
    ("Cro91", "unconfirmed-digits"),
    ("Pen97", "unconfirmed-digits"),
    ("Ree74", "unconfirmed-digits"),
}
FIXTURE_SILENT = ("Yat83", "Smi01", "Wes02", "Bro96")


def run_fixture(root, merged):
    files = Path(root) / "files"
    files.mkdir()
    origin = Path(root) / "origin" if merged else files
    folders = SourceFolders(root=Path(root), files=files, origin=origin)
    for key, (has_text, has_header, has_record) in DISK.items():
        if has_text:
            body = "=== OCR-PROVENANCE ===\nengine: tesseract 5\n\n" if has_header else ""
            body += "the extracted text of the source\n"
            (files / ("%s.txt" % key)).write_text(body, encoding="utf-8")
        if has_record:
            folders.write_origin_record(key, OCR, {"engine": "tesseract 5", "dpi": 300})
    sources_list = Path(root) / "list.md"
    text = FIXTURE_LIST_HEADER
    for key in sorted(key for key in DISK if "." not in key):
        status = ("READABLE VIA OCR (tesseract 5 at 300 dpi)" if key in DECLARED
                  else "READABLE at the publisher")
        text += FIXTURE_LIST_ENTRY % (key, status)
    sources_list.write_text(text, encoding="utf-8")
    quotes = Path(root) / "quotes.md"
    quotes.write_text(FIXTURE_QUOTES, encoding="utf-8")
    return check(sources_list, quotes, folders)


def self_test():
    failures = []
    for merged in (False, True):
        layout = "merged origin" if merged else "records beside files"
        with tempfile.TemporaryDirectory() as root:
            issues = run_fixture(root, merged)
        found = {(key, rule) for key, rule, _detail in issues}
        details = {(key, rule): detail for key, rule, detail in issues}
        for key, rule in sorted(FIXTURE_EXPECTED - found):
            failures.append("%s: %s %s NOT REPORTED" % (layout, key, rule))
        for key, rule in sorted(found - FIXTURE_EXPECTED):
            failures.append("%s: %s %s FALSE POSITIVE" % (layout, key, rule))
        for key in FIXTURE_SILENT:
            if any(hit == key for hit, _rule in found):
                failures.append("%s: %s should be silent" % (layout, key))
        if "3 digit(s) in the quoted material" not in details.get(("Cro91", "unconfirmed-digits"), ""):
            failures.append("%s: [Cro91] must count the three quoted digits only" % layout)
        for key in ("Pen97", "Ree74"):
            if "whole field" not in details.get((key, "unconfirmed-digits"), ""):
                failures.append("%s: [%s] should fall back to the whole field" % (layout, key))
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--list", dest="sources_list", help="the sources list (default: sources.list)")
    parser.add_argument("--quotes", help="the quotes bank (default: sources.quotes)")
    parser.add_argument("--self-test", action="store_true",
                        help="only check the rules against built-in fixtures")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    sources_list = args.sources_list or config.sources.list
    quotes = args.quotes or config.sources.quotes
    for path, label, given in ((sources_list, "sources list", args.sources_list),
                               (quotes, "quotes bank", args.quotes)):
        if given and not Path(path).exists():
            return tool_failed("not found: %s" % path, TOOL)
        if skipped_for_missing(TOOL, path, label, args.format):
            return 0

    report = CheckReport(TOOL, CLASSES)
    for key, rule, detail in check(sources_list, quotes, folders_from_config(config)):
        report.add(key, rule, detail)
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
