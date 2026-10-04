#!/usr/bin/env python3
"""Find one source registered under two citation keys in the .bib file and the sources list.

A list collects the same work twice by ordinary means: a source is added under a
guessed year, added again later under the corrected one, and both survive because
nothing compares them. The copies drift, and "what does this source say" gets two
answers.

Signals, strongest first:

    same DOI             two keys, one document                      duplicate  DEFECT
    same ISBN            likewise, unless one is a deliberate reprint duplicate DEFECT
    identical text       the cached text of both keys hashes the same duplicate DEFECT
    stub beside entry    a key with no .bib title and no citations,  suspect    ADVISORY
                         beside a cited key with the same author stem
    same title           edition words removed, so 1st and 2nd       suspect    ADVISORY
                         editions collide here on purpose; an
                         ordinal counts only before "ed." or
                         "edition", so "A First Work" and "A Second
                         Work" stay two titles

The DOI, ISBN and title come from the book's .bib file (`sources.bibliography`); the keys
are those of the .bib file and of the sources list together. Citations are the pandoc
citations (`[@Key]`, `@Key`) in the manuscript.

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
from bibliography import read_identities
from citations import find_citations
from source_files import (add_config_arguments, folders_for_directory, folders_from_config,
                          load_book, manuscript_paths, markdown_files_under, tool_failed)
from check_output import ADVISORY, DEFECT, CheckReport, add_output_arguments, skipped_for_missing
from source_registry import read_bank

TOOL = "duplicate-source-check"
CLASSES = {"duplicate": DEFECT, "suspect": ADVISORY}

EDITION_RE = re.compile(
    r"\b(\d+(st|nd|rd|th)|first|second|third|fourth|anniversary|revised|updated)[ ,]*ed(ition)?\b\.?",
    re.I,
)


class Source:
    def __init__(self, key, identity):
        self.key = key
        self.identity = identity

    def field(self, name):
        return self.identity.plain(name) if self.identity is not None else ""


def field(source, name):
    return source.field(name)


def parse(list_path, bibliography_path):
    identities = read_identities(bibliography_path)
    listed = ([entry.key for entry in read_bank(list_path).entries]
              if list_path and Path(list_path).is_file() else [])
    keys = list(identities) + [key for key in listed if key not in identities]
    return {key: Source(key, identities.get(key)) for key in keys}


def normalise_title(title):
    title = EDITION_RE.sub(" ", title.lower())
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", title).split())


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def citation_counts(entries, manuscript_files):
    counts = collections.Counter(
        citation.key for path in manuscript_files
        for citation in find_citations(Path(path).read_text(encoding="utf-8")))
    return {key: counts.get(key, 0) for key in entries}


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
        thin = [k for k in keys if not entries[k].field("title") and cites.get(k, 0) == 0]
        live = [k for k in keys if cites.get(k, 0) > 0]
        if thin and live:
            stale[value] = sorted(thin + live)

    checks = [
        ("duplicate", "same DOI", group(entries, lambda k, b: field(b, "doi").lower().rstrip("."))),
        ("duplicate", "same ISBN",
         group(entries, lambda k, b: re.sub(r"[^0-9X]", "", field(b, "isbn").upper()))),
        ("duplicate", "identical cached text", group(entries, cached_digest)),
        ("suspect", "stub beside a fuller entry by the same author", stale),
        ("suspect", "same title, editions ignored",
         group(entries, lambda k, b: normalise_title(field(b, "title")))),
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
### [<Key>]
```

### [Ddd10]

**Note:** added from a reading list, never filled in

---

### [Eee15]

**Access URLs:** https://example.org/shared.pdf

---

### [Fff16]

**Access URLs:** https://example.org/shared.pdf

---
"""

FIXTURE_BIBLIOGRAPHY = """@article{Aaa01,
  author = {Adams, Ann},
  title = {One paper},
  year = {2001},
  doi = {10.1234/one},
}

@article{Aaa02,
  author = {Adams, Ann},
  title = {One paper, filed again},
  year = {2002},
  doi = {10.1234/one},
}

@book{Bbb05,
  author = {Baker, Bob},
  title = {A Book About Things},
  year = {2005},
  isbn = {978-0-00-000000-2},
}

@book{Bbb06,
  author = {Baker, Bob},
  title = {A Book About Things, reprinted},
  year = {2006},
  isbn = {9780000000002},
}

@book{Ccc90,
  author = {Clark, Cat},
  title = {Bread Craft, 1st edition},
  year = {1990},
}

@book{Ccc04,
  author = {Clark, Cat},
  title = {Bread Craft, Second Edition},
  year = {2004},
}

@article{Ddd11,
  author = {Davis, Dan},
  title = {A cited paper},
  year = {2011},
}

@misc{Eee15,
  author = {Evans, Eve},
  title = {A page},
  year = {2015},
}

@misc{Fff16,
  author = {Ford, Fay},
  title = {Another page},
  year = {2016},
}

@book{Ggg74,
  author = {Green, Gus},
  title = {A First Work},
  year = {1974},
}

@book{Hhh99,
  author = {Hill, Hal},
  title = {A Second Work},
  year = {1999},
}
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        files = Path(root) / "files"
        files.mkdir()
        (files / "Eee15.txt").write_text("same bytes\n", encoding="utf-8")
        (files / "Fff16.txt").write_text("other bytes\n", encoding="utf-8")
        (Path(root) / "list.md").write_text(FIXTURE_LIST, encoding="utf-8")
        (Path(root) / "references.bib").write_text(FIXTURE_BIBLIOGRAPHY, encoding="utf-8")
        manuscript = Path(root) / "manuscript"
        manuscript.mkdir()
        (manuscript / "110-chapter-1.md").write_text(
            "As shown [@Ddd11; @Ccc04]. Again @Ccc90 says so.\n", encoding="utf-8")
        entries = parse(Path(root) / "list.md", Path(root) / "references.bib")
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
    parser.add_argument("--bibliography",
                        help="the .bib file (default: sources.bibliography)")
    parser.add_argument("--manuscript-dir", help="a manuscript folder (default: the book's manuscript files)")
    parser.add_argument("--self-test", action="store_true", help="run on a built-in example")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    sources_list = args.sources_list or config.sources.list
    bibliography = args.bibliography or config.sources.bibliography
    if args.sources_list and not Path(sources_list).exists():
        return tool_failed("sources list not found: %s" % sources_list, TOOL)
    if args.bibliography and not Path(bibliography).exists():
        return tool_failed(".bib file not found: %s" % bibliography, TOOL)
    if not Path(bibliography).exists() and skipped_for_missing(TOOL, sources_list,
                                                               "sources list", args.format):
        return 0

    report = CheckReport(TOOL, CLASSES)
    manuscript = manuscript_paths(config, TOOL, args.manuscript_dir)
    if not manuscript:
        report.skip("no manuscript files at %s" % (args.manuscript_dir or config.manuscript.dir))
        return report.emit(args.format)
    entries = parse(sources_list, bibliography)
    cites = citation_counts(entries, manuscript)
    for name, label, value, keys in find_groups(entries, cites, folders_from_config(config)):
        counted = ", ".join("%s (%d cites)" % (k, cites.get(k, 0)) for k in keys)
        report.add(",".join(keys), name, "%s: %s -- %s -- %s"
                   % (label, counted, str(value)[:80], advice(keys, cites)))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
