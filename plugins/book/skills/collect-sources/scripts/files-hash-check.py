#!/usr/bin/env python3
"""Hold the sources list's cache lines to the cached files on disk.

Other checks ask whether a cached file exists (entry-format-check) or whether a key is
cached at all (fetch --dry-run). None asks whether the sha256 an entry records is the
hash of the file it names. That hash matters in one place: a refetch downloads a
source and compares the new hash with the recorded one to decide whether the content
drifted. A stale recorded hash makes that comparison wrong in both directions.

fetch.py writes an origin record for every fetch: the URL it requested and both hashes
as written. This check compares the list with the files and with those records.

Classes:
  hash-stale        DEFECT  the recorded sha256 does not match the file it names
  hash-missing      DEFECT  a cache line with no sha256 at all
  url-mismatch      DEFECT  `from <URL>` disagrees with the URL in the fetch record
                            (scheme, a leading www. and a trailing slash are ignored)
  file-missing      DEFECT  the line names a file that is not there
  no-fetch-record   INFORMATIONAL  a key with no fetch record: ingested by hand or before
                            records existed; counted so the number stays visible

A `NOT YET FETCHED` line is skipped: it is a destination, not a pointer. A hash on one
is entry-format-check's premature-hash rule.

--fix only copies what is on disk into the list. It cannot invent a hash, and it does
not touch a line whose file is missing.

Usage:
  files-hash-check.py
  files-hash-check.py --fix
  files-hash-check.py --self-test
"""

import argparse
import hashlib
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (FETCH, SourceFolders, add_config_arguments, cache_references,
                          folders_from_config, load_book, tool_failed)
from check_output import (DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing)
from citation_key import ENTRY_HEADING

TOOL = "files-hash-check"
CLASSES = {
    "hash-stale": DEFECT,
    "hash-missing": DEFECT,
    "url-mismatch": DEFECT,
    "file-missing": DEFECT,
    "no-fetch-record": INFORMATIONAL,
}

SHA = re.compile(r"sha256[: ]+([0-9a-f]{64})")
PATH_IN_BACKTICKS = re.compile(r"`([^`]+)`")
FROM_URL = re.compile(r"from (\S+?)\)?\s*$")


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def canonical(url):
    url = re.sub(r"^https?://", "", url.strip().rstrip(")"))
    url = re.sub(r"^www\.", "", url)
    return url.rstrip("/")


def walk(lines):
    fenced = False
    key = None
    for index, line in enumerate(lines):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = ENTRY_HEADING.match(line)
        if heading:
            key = heading.group(1)
            continue
        field = re.match(r"^\*\*(Cached text|Cached original):\*\* (.*)$", line)
        if field and key:
            yield index, key, field.group(1), field.group(2)


def named_file(folders, value):
    references = cache_references(folders, value)
    if references:
        return references[0][3], references[0][0].strip("`")
    pointer = PATH_IN_BACKTICKS.search(value)
    if not pointer:
        return None, None
    return Path(folders.root) / pointer.group(1), pointer.group(1)


def add_hash(value, on_disk):
    if re.search(r"\((?:fetched|obtained) \d{4}-\d{2}-\d{2}", value):
        return re.sub(r"(\((?:fetched|obtained) \d{4}-\d{2}-\d{2})",
                      r"\1, sha256 " + on_disk, value, count=1)
    if value.rstrip().endswith(")"):
        return value.rstrip()[:-1].rstrip() + ", sha256 %s)" % on_disk
    return value.rstrip() + " (sha256 %s)" % on_disk


def check(path, folders, fix=False):
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    issues = []
    unrecorded = set()
    repairs = 0

    for index, key, field, value in walk(lines):
        if "NOT YET FETCHED" in value:
            continue
        target, shown = named_file(folders, value)
        if target is None:
            continue
        if not target.exists():
            issues.append((key, "file-missing", "%s names %s" % (field, shown)))
            continue

        new_value = value
        on_disk = digest(target)
        recorded = SHA.search(value)
        if recorded and recorded.group(1) != on_disk:
            issues.append((key, "hash-stale",
                           "%s records %s..., the file hashes to %s..."
                           % (field, recorded.group(1)[:12], on_disk[:12])))
            new_value = new_value.replace(recorded.group(1), on_disk)
        elif not recorded:
            issues.append((key, "hash-missing", "%s has no sha256" % field))
            new_value = add_hash(new_value, on_disk)

        record = folders.read_origin_record(key, FETCH)
        if record is None:
            unrecorded.add(key)
        elif field == "Cached original":
            actual = record.get("url")
            stated = FROM_URL.search(new_value)
            same_bytes = record.get("original_sha256") == on_disk
            if actual and stated and same_bytes and canonical(stated.group(1)) != canonical(actual):
                issues.append((key, "url-mismatch",
                               "records from %s, the fetch record says %s"
                               % (stated.group(1)[:50], actual[:50])))
                new_value = new_value[:stated.start(1)] + actual + new_value[stated.end(1):]

        if fix and new_value != value:
            lines[index] = "**%s:** %s" % (field, new_value)
            repairs += 1

    if fix and repairs:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
    return issues, sorted(unrecorded), repairs


STALE_ONE_BYTE = "01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b"
LANDING_PAGE = "https://journal.example.org/article/abs/four-items"
FETCHED_FROM = "https://journal.example.org/content/view/S0000000000000000a.pdf"
FULL_TEXT = "https://archive.example.org/articles/PMC0000001/"
PUBLISHER = "https://publisher.example.org/doi/10.0000/example.0001"

FIXTURE_FILES = {
    "Smi01": [("Smi01.txt", b"the extracted text of the target article\n"),
              ("Smi01.pdf", b"%PDF-1.4 the whole journal package\n")],
    "Kem77": [("Kem77.txt", b"Reading the colour of field soil, in full\n")],
    "Vin00": [("Vin00.txt", b"a talk transcript\n")],
    "VM98": [("VM98.txt", b"a seed catalogue\n")],
    "KFR11": [("KFR11.html", b"<html>the full text</html>\n")],
    "Ree74": [("Ree74.txt", b"On a river: old flood marks\n")],
    "TR73": [("TR73.txt", b"=== OCR-PROVENANCE ===\nthe scanned pages\n")],
}

FIXTURE_EXPECTED = {
    ("Smi01", "hash-stale"),
    ("Smi01", "url-mismatch"),
    ("Kem77", "hash-stale"),
    ("Vin00", "hash-missing"),
    ("VM98", "hash-missing"),
    ("KFR11", "url-mismatch"),
    ("Bla15", "file-missing"),
}


def _fixture_list(shown, hashes):
    return """# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Cached text:** `{d}/<Key>.txt` (fetched YYYY-MM-DD, sha256 ...)
```

### [Smi01] Smith, "Winter sowing" (2001)

**Cached text:** `{d}/Smi01.txt` (fetched 2025-08-09, sha256 {stale})
**Cached original:** `{d}/Smi01.pdf` (fetched 2025-08-09, sha256 {stale}, from {landing})

---

### [Kem77] Kemp, "Reading the colour of field soil" (1977)

**Cached text:** `{d}/Kem77.txt` (fetched 2025-08-01, sha256 {stale})

---

### [Vin00] Vince, "A talk" (2000)

**Cached text:** `{d}/Vin00.txt` (fetched 2025-08-10)

---

### [VM98] Voss & Moreau, "A seed catalogue" (1998)

**Cached text:** `{d}/VM98.txt`

---

### [KFR11] Kern & Fisher, "A review" (2011)

**Cached original:** `{d}/KFR11.html` (fetched 2025-08-11, sha256 {kfr11}, from {publisher})

---

### [Ree74] Reed, "On a river: old flood marks" (1974)

**Cached text:** `{d}/Ree74.txt` (fetched 2025-08-12, sha256 {ree74}, from http://www.publisher.example.org/chapter/10.0000/ree74/)

---

### [Bla15] Blake, "A script-rendered page" (2015)

**Cached text:** `{d}/Bla15.txt` (fetched 2025-08-09, sha256 {stale})

---

### [Pet21] Peters, "Abstract only" (2021)

**Cached text:** NOT YET FETCHED
**Cached original:** NOT YET FETCHED

---

### [TR73] Thomas & Rowe, "A hand-ingested scan" (1973)

**Cached text:** `{d}/TR73.txt` (fetched 2025-08-01, sha256 {tr73})

---
""".format(d=shown, stale=STALE_ONE_BYTE, landing=LANDING_PAGE,
           publisher=PUBLISHER, kfr11=hashes["KFR11.html"],
           ree74=hashes["Ree74.txt"], tr73=hashes["TR73.txt"])


def _build_fixture(root, merged_origin):
    files = Path(root) / "evidence" / "cache"
    origin = Path(root) / "evidence" / "origin" if merged_origin else files
    files.mkdir(parents=True)
    folders = SourceFolders(root=Path(root), files=files, origin=origin)
    hashes = {}
    for key, entries in FIXTURE_FILES.items():
        for name, body in entries:
            (files / name).write_bytes(body)
            hashes[name] = hashlib.sha256(body).hexdigest()
        if key == "TR73":
            continue
        record = {"key": key, "url": {
            "Smi01": FETCHED_FROM,
            "KFR11": FULL_TEXT,
            "Ree74": "https://publisher.example.org/chapter/10.0000/ree74",
        }.get(key, "https://example.org/%s" % key)}
        for name, _body in entries:
            record["text_sha256" if name.endswith(".txt") else "original_sha256"] = hashes[name]
        folders.write_origin_record(key, FETCH, record)
    list_path = Path(root) / "list.md"
    list_path.write_text(_fixture_list(folders.shown_files, hashes), encoding="utf-8")
    return folders, list_path


def self_test():
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    for merged_origin in (False, True):
        layout = "one origin file per key" if merged_origin else "records beside the files"
        with tempfile.TemporaryDirectory() as root:
            folders, list_path = _build_fixture(root, merged_origin)
            issues, unrecorded, _repairs = check(list_path, folders)
            _fixed, _unrecorded, repairs = check(list_path, folders, fix=True)
            after, still_unrecorded, _repairs = check(list_path, folders)
            repaired_text = list_path.read_text(encoding="utf-8")
            shown = folders.shown_files

        found = {(key, rule) for key, rule, _detail in issues}
        for key, rule in sorted(FIXTURE_EXPECTED - found):
            failures.append("%s: %s %s NOT REPORTED" % (layout, key, rule))
        for key, rule in sorted(found - FIXTURE_EXPECTED):
            failures.append("%s: %s %s FALSE POSITIVE" % (layout, key, rule))
        require(sum(1 for key, rule, _d in issues if key == "Smi01" and rule == "hash-stale") == 2,
                "%s: [Smi01] has two stale hashes and both must be reported" % layout)
        require(unrecorded == ["TR73"], "%s: only [TR73] lacks a fetch record" % layout)
        require([(key, rule) for key, rule, _d in after] == [("Bla15", "file-missing")],
                "%s: after --fix the only finding must be the missing file: %s"
                % (layout, [(key, rule) for key, rule, _d in after]))
        require(repairs == 6, "%s: expected 6 repaired lines, got %d" % (layout, repairs))
        require(FETCHED_FROM in repaired_text and LANDING_PAGE not in repaired_text,
                "%s: [Smi01]'s from-URL was not replaced" % layout)
        require(FULL_TEXT in repaired_text and PUBLISHER not in repaired_text,
                "%s: [KFR11]'s from-URL was not replaced" % layout)
        require("(fetched 2025-08-10, sha256 " in repaired_text,
                "%s: [Vin00]: the hash was not inserted into the parenthetical" % layout)
        require("`%s/VM98.txt` (sha256 " % shown in repaired_text,
                "%s: [VM98]: a parenthetical was not added where there was none" % layout)
        require(still_unrecorded == unrecorded, "%s: --fix changed the fetch records" % layout)

    with tempfile.TemporaryDirectory() as root:
        folders, list_path = _build_fixture(root, False)
        text = list_path.read_text(encoding="utf-8").replace(
            "`%s/Kem77.txt`" % folders.shown_files, "`sources/library/Kem77.txt`")
        list_path.write_text(text, encoding="utf-8")
        issues, _unrecorded, _repairs = check(list_path, folders)
        require(("Kem77", "hash-stale") in {(k, r) for k, r, _d in issues},
                "a value written with the default folder must still resolve")

    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--list", dest="sources_list",
                        help="the sources list (default: sources.list)")
    parser.add_argument("--fix", action="store_true",
                        help="copy hashes and provenance from disk into the list")
    parser.add_argument("--self-test", action="store_true",
                        help="only check the rules against built-in fixtures")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    list_path = args.sources_list or config.sources.list
    if args.sources_list and not Path(list_path).exists():
        return tool_failed("sources list not found: %s" % list_path, TOOL)
    if skipped_for_missing(TOOL, list_path, "sources list", args.format):
        return 0

    folders = folders_from_config(config)
    issues, unrecorded, repairs = check(list_path, folders, fix=args.fix)
    if args.fix and repairs:
        issues, unrecorded, _repairs = check(list_path, folders)
    report = CheckReport(TOOL, CLASSES)
    for key, rule, detail in issues:
        report.add(key, rule, detail)
    for key in unrecorded:
        report.add(key, "no-fetch-record", "no fetch record: ingested by hand or before records existed")
    if args.format == "text" and args.fix:
        print("repaired %d cache line(s) in %s\n" % (repairs, list_path))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
