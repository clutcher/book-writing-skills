#!/usr/bin/env python3
"""Find one source registered under two citation keys in the sources list.

A list collects the same work twice by ordinary means: a source is added under a
guessed year, added again later under the corrected one, and both survive because
nothing compares them. The copies drift, and "what does this source say" gets two
answers.

Signals, strongest first:

    same DOI             two keys, one document                      duplicate  DEFECT
    same ISBN            likewise, unless one is a deliberate reprint duplicate DEFECT
    identical text       the cached text of both keys hashes the same duplicate DEFECT
    stub beside entry    a key with no Full title and no citations,  suspect    ADVISORY
                         beside a cited key with the same author stem
    same title           edition words removed, so 1st and 2nd       suspect    ADVISORY
                         editions collide here on purpose
    same heading         the `### [Key] ...` line matches word for   suspect    ADVISORY
                         word

A suspect group is ADVISORY because two printings of one book correctly hold two keys
when both were read; the script cannot tell that from a real duplicate. Each group
carries manuscript citation counts, which decide the action: an uncited key beside a
cited twin is a stale registration to fold in; two cited keys are two sources the book
distinguishes, and merging them would break citations. There is no accepted count: a
suspect group is reported on every run.

URLs are NOT a signal: entries point at each other's copies on purpose.

Usage:
  duplicate-source-check.py
  duplicate-source-check.py --self-test
"""

import argparse
import collections
import hashlib
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (add_config_arguments, folders_for_directory, folders_from_config,
                          load_book, manuscript_paths, markdown_files_under, tool_failed)
from check_output import ADVISORY, DEFECT, CheckReport, add_output_arguments, skipped_for_missing
from source_registry import read_bank

TOOL = "duplicate-source-check"
CLASSES = {"duplicate": DEFECT, "suspect": ADVISORY}

EDITION_RE = re.compile(
    r"\b(\d+(st|nd|rd|th)|first|second|third|fourth|anniversary|revised|updated)\b[ ,]*(ed(ition)?\.?)?",
    re.I,
)


def field(block, name):
    return block.field(name) or ""


def parse(path):
    return {entry.key: entry for entry in read_bank(path).entries}


def normalise_title(title):
    title = EDITION_RE.sub(" ", title.lower())
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", title).split())


def normalise_heading(block):
    head = block.heading
    head = re.sub(r"^### \[[^\]]+\]\s*[-—–]*\s*", "", head)
    head = EDITION_RE.sub(" ", head.lower())
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", head).split())


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def citation_counts(entries, manuscript_files):
    text = " ".join(Path(path).read_text(encoding="utf-8") for path in manuscript_files)
    return {key: len(re.findall(r"\[[^\]]*\b%s\b[^\]]*\]" % re.escape(key), text))
            for key in entries}


def group(entries, keyfunc):
    buckets = collections.defaultdict(list)
    for key, block in entries.items():
        value = keyfunc(key, block)
        if value:
            buckets[value].append(key)
    return {v: sorted(ks) for v, ks in buckets.items() if len(ks) > 1}


def find_groups(entries, cites, folders):
    def cached_digest(key, _block):
        path = folders.file(key + ".txt")
        return digest(path) if path.exists() else ""

    def stem(key, _block):
        match = re.match(r"[A-Za-z+]+", key)
        return match.group(0).lower() if match else ""

    stale = {}
    for value, keys in group(entries, stem).items():
        thin = [k for k in keys if entries[k].field("Full title") is None and cites.get(k, 0) == 0]
        live = [k for k in keys if cites.get(k, 0) > 0]
        if thin and live:
            stale[value] = sorted(thin + live)

    checks = [
        ("duplicate", "same DOI", group(entries, lambda k, b: field(b, "DOI").lower().rstrip("."))),
        ("duplicate", "same ISBN",
         group(entries, lambda k, b: re.sub(r"[^0-9X]", "", field(b, "ISBN").upper()))),
        ("duplicate", "identical cached text", group(entries, cached_digest)),
        ("suspect", "stub beside a fuller entry by the same author", stale),
        ("suspect", "same title, editions ignored",
         group(entries, lambda k, b: normalise_title(field(b, "Full title")))),
        ("suspect", "same heading", group(entries, lambda k, b: normalise_heading(b))),
    ]
    seen, found = set(), []
    for name, label, groups in checks:
        for value, keys in sorted(groups.items()):
            signature = tuple(keys)
            if signature in seen:
                continue
            seen.add(signature)
            found.append((name, label, value, keys))
    return found


def advice(keys, cites):
    live = [k for k in keys if cites.get(k, 0) > 0]
    dead = [k for k in keys if cites.get(k, 0) == 0]
    if dead and live:
        return "%s uncited; %s carries the citations" % (", ".join(dead), ", ".join(live))
    if not live:
        return "none cited in the manuscript"
    return "all cited; keep separate unless they are truly one work"


FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
```

### [Aaa01] Adams, "One paper" (2001)

**Full title:** One paper
**DOI:** 10.1234/one

---

### [Aaa02] Adams, "One paper, again" (2002)

**Full title:** One paper, filed again
**DOI:** 10.1234/one

---

### [Bbb05] Baker, "A book" (2005)

**Full title:** A Book About Things
**ISBN:** 978-0-00-000000-2

---

### [Bbb06] Baker, "A book reprint" (2006)

**Full title:** A Book About Things, reprinted
**ISBN:** 9780000000002

---

### [Ccc90] Clark, "Bread Craft" (1990)

**Full title:** Bread Craft, 1st edition

---

### [Ccc04] Clark, "Bread Craft" (2004)

**Full title:** Bread Craft, Second Edition

---

### [Ddd10] Davis

---

### [Ddd11] Davis, "A cited paper" (2011)

**Full title:** A cited paper

---

### [Eee15] Evans, "A page" (2015)

**Full title:** A page
**Access URLs:** https://example.org/shared.pdf

---

### [Fff16] Ford, "Another page" (2016)

**Full title:** Another page
**Access URLs:** https://example.org/shared.pdf

---
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        files = Path(root) / "files"
        files.mkdir()
        (files / "Eee15.txt").write_text("same bytes\n", encoding="utf-8")
        (files / "Fff16.txt").write_text("other bytes\n", encoding="utf-8")
        (Path(root) / "list.md").write_text(FIXTURE_LIST, encoding="utf-8")
        manuscript = Path(root) / "manuscript"
        manuscript.mkdir()
        (manuscript / "110-chapter-1.md").write_text(
            "As shown [Ddd11, Ccc04]. Again [Ccc90].\n", encoding="utf-8")
        entries = parse(Path(root) / "list.md")
        cites = citation_counts(entries, markdown_files_under(manuscript))
        found = find_groups(entries, cites, folders_for_directory(files))
    got = {(name, label, tuple(keys)) for name, label, _value, keys in found}
    want = {
        ("duplicate", "same DOI", ("Aaa01", "Aaa02")),
        ("duplicate", "same ISBN", ("Bbb05", "Bbb06")),
        ("suspect", "stub beside a fuller entry by the same author", ("Ddd10", "Ddd11")),
        ("suspect", "same title, editions ignored", ("Ccc04", "Ccc90")),
    }
    for item in sorted(want - got):
        failures.append("NOT REPORTED %s" % (item,))
    for item in sorted(got - want):
        failures.append("FALSE POSITIVE %s" % (item,))
    if advice(["Ccc04", "Ccc90"], cites) != "all cited; keep separate unless they are truly one work":
        failures.append("two cited editions must be kept apart")
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
    parser.add_argument("--manuscript-dir", help="a manuscript folder (default: the book's manuscript files)")
    parser.add_argument("--self-test", action="store_true", help="run on a built-in example")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    sources_list = args.sources_list or config.sources.list
    if args.sources_list and not Path(sources_list).exists():
        return tool_failed("sources list not found: %s" % sources_list, TOOL)
    if skipped_for_missing(TOOL, sources_list, "sources list", args.format):
        return 0

    entries = parse(sources_list)
    cites = citation_counts(entries, manuscript_paths(config, TOOL, args.manuscript_dir))
    report = CheckReport(TOOL, CLASSES)
    for name, label, value, keys in find_groups(entries, cites, folders_from_config(config)):
        counted = ", ".join("%s (%d cites)" % (k, cites.get(k, 0)) for k in keys)
        report.add(",".join(keys), name, "%s: %s -- %s -- %s"
                   % (label, counted, str(value)[:80], advice(keys, cites)))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
