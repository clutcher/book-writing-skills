#!/usr/bin/env python3
"""List the cached sources that have never been read, grouped for sharing out.

A source counts as READ when it has an entry in the quotes bank: that is the only lasting
record of having read it. The answer is recomputed from the two banks and the cache every
time, which is why this is a script and not a kept reading list: a kept list goes stale
the moment anything is read.

Two optional word lists in the book's config narrow and group the queue:

  terms.watch_words.reading_topics   words or regular expressions; only entries whose
                                     title, venue or note match one are queued
                                     (without it, every unread source is queued)
  terms.watch_words.reading_groups   a mapping of group name -> words; each queued
                                     source goes to the first group it matches, so a
                                     group can go to one reading agent

Titles and venues come from the .bib (sources.bibliography), notes from the sources list.
A cached text under 5000 bytes is listed apart as a stub to verify before use.

Usage:
  unread-sources.py                  counts, then groups
  unread-sources.py --keys-only      space-separated keys, for a prompt
  unread-sources.py --group 2        one group, by its number
  unread-sources.py --all            ignore reading_topics
  unread-sources.py --verbose        add title and text size
  unread-sources.py --self-test

A worklist: it always exits 0; an empty queue is a result, not an error.
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (add_config_arguments, folders_for_directory, folders_from_config,
                          load_book, tool_failed)
from bibliography import BibliographyError, parse_bibliography, read_identities
from source_registry import read_bank
from check_output import skipped_for_missing

TOOL = "unread-sources"
STUB_BYTES = 5000
UNGROUPED = "Not in any group -- read the entry before assigning"


def as_pattern(words):
    if not words:
        return None
    if isinstance(words, str):
        words = [words]
    return re.compile("|".join(str(word) for word in words), re.I)


def reading_groups(config_groups):
    groups = []
    for name, words in (config_groups or {}).items():
        pattern = as_pattern(words)
        if pattern:
            groups.append((str(name), pattern))
    return groups


def parse_bank(path, identities=None):
    identities = identities or {}
    found = {}
    for entry in read_bank(path).entries:
        identity = identities.get(entry.key)
        found[entry.key] = {
            "title": identity.plain("title") if identity else entry.heading_tail,
            "venue": identity.plain("journal", "booktitle", "publisher") if identity else "",
            "year": identity.plain("year") if identity else "",
            "note": next((f.line_value for f in entry.fields if f.name == "Note"), ""),
        }
    return found


def describe(key, entry, folders):
    text = folders.file(key + ".txt")
    exists = text.exists()
    return {
        "key": key,
        "title": entry["title"],
        "venue": entry["venue"],
        "year": entry["year"],
        "cached": exists,
        "size": text.stat().st_size if exists else 0,
        "blob": " ".join([entry["title"], entry["venue"], entry["note"]]),
    }


def group_of(row, groups):
    for number, (_name, pattern) in enumerate(groups, 1):
        if pattern.search(row["blob"] + " " + row["key"]):
            return number
    return len(groups) + 1


def build_queue(sources, findings, folders, topics, groups, all_topics):
    rows = [describe(key, value, folders) for key, value in sources.items()]
    cached = [row for row in rows if row["cached"]]
    unread = [row for row in cached if row["key"] not in findings]
    queue = unread if (all_topics or topics is None) else [
        row for row in unread if topics.search(row["blob"])]
    stubs = [row for row in queue if row["size"] < STUB_BYTES]
    queue = [row for row in queue if row["size"] >= STUB_BYTES]
    for row in queue:
        row["group"] = group_of(row, groups)
    queue.sort(key=lambda row: (row["group"], row["key"]))
    return rows, cached, unread, queue, stubs


def print_report(rows, cached, unread, queue, stubs, groups, filtered, verbose):
    print(f"list entries                {len(rows)}")
    print(f"cached (.txt on disk)       {len(cached)}")
    print(f"cached with NO quotes entry {len(unread)}   <- not read")
    label = "topically relevant" if filtered else "all topics"
    print(f"  {label:<25} {len(queue) + len(stubs)}")
    print(f"  minus stubs (<{STUB_BYTES}B)        {len(queue)}   <- THE READING QUEUE")
    if stubs:
        print(f"  stubs, verify before use  {len(stubs)}   {' '.join(r['key'] for r in stubs)}")
    print(f"not cached at all           {len(rows) - len(cached)}")
    names = {number: name for number, (name, _pattern) in enumerate(groups, 1)}
    names[len(groups) + 1] = UNGROUPED if groups else "Reading queue"
    by_group = {}
    for row in queue:
        by_group.setdefault(row["group"], []).append(row)
    for number in sorted(by_group):
        group = by_group[number]
        print(f"\n{number}. {names[number]}  [{len(group)}]")
        if verbose:
            for row in group:
                print(f"   {row['key']:<12} {row['size'] // 1024:>4}K  {row['title'][:72]}")
        else:
            print("   " + " ".join(row["key"] for row in group))


FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>]
```

### [Aaa01]

**Access URLs:** https://example.org/aaa01

---

### [Bbb02]

**Access URLs:** https://example.org/bbb02

---

### [Ccc03]

**Note:** a book on gardening

---

### [Ddd04]

**Access URLs:** https://example.org/ddd04

---
"""

FIXTURE_BIBLIOGRAPHY = """@book{Aaa01, author = {Adams, A.}, title = {Baking bread}, year = {2001}}
@book{Bbb02, author = {Baker, B.}, title = {Sourdough starters}, year = {2002}}
@book{Ccc03, author = {Clark, C.}, title = {Gardening}, year = {2003}}
@book{Ddd04, author = {Davis, D.}, title = {Reading, already read}, year = {2004}}
"""

FIXTURE_QUOTES = """# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
```

### [Ddd04] Davis, "Read already" (2004)

**Key findings:** read

---
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        files = Path(root) / "files"
        files.mkdir()
        for key in ("Aaa01", "Bbb02", "Ccc03", "Ddd04"):
            (files / f"{key}.txt").write_text("x" * 6000, encoding="utf-8")
        (Path(root) / "list.md").write_text(FIXTURE_LIST, encoding="utf-8")
        (Path(root) / "quotes.md").write_text(FIXTURE_QUOTES, encoding="utf-8")
        identities = parse_bibliography(FIXTURE_BIBLIOGRAPHY).entries
        sources = parse_bank(Path(root) / "list.md", identities)
        findings = parse_bank(Path(root) / "quotes.md")
        folders = folders_for_directory(files)
        groups = reading_groups({"Bread": ["bread", "loaf"], "Starters": ["starter"]})
        _rows, _cached, unread, queue, _stubs = build_queue(
            sources, findings, folders, as_pattern(["bread", "starter"]), groups, False)
        everything = build_queue(sources, findings, folders, None, [], False)[3]
    if sorted(row["key"] for row in unread) != ["Aaa01", "Bbb02", "Ccc03"]:
        failures.append("a source with a quotes entry is counted as unread")
    if [(row["key"], row["group"]) for row in queue] != [("Aaa01", 1), ("Bbb02", 2)]:
        failures.append("topic filter or grouping is wrong: %s"
                        % [(row["key"], row["group"]) for row in queue])
    if sorted(row["key"] for row in everything) != ["Aaa01", "Bbb02", "Ccc03"]:
        failures.append("without reading_topics every unread source must be queued")
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    parser.add_argument("--list", dest="sources_list", help="the sources list (default: sources.list)")
    parser.add_argument("--quotes", help="the quotes bank (default: sources.quotes)")
    parser.add_argument("--all", action="store_true", help="ignore terms.watch_words.reading_topics")
    parser.add_argument("--group", type=int, help="one group, by its number")
    parser.add_argument("--keys-only", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true", help="run on a built-in example")
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    sources_list = args.sources_list or config.sources.list
    quotes = args.quotes or config.sources.quotes
    for path, label, given in ((sources_list, "sources list", args.sources_list),
                               (quotes, "quotes bank", args.quotes)):
        if given and not Path(path).exists():
            return tool_failed("cannot read %s" % path, TOOL)
        if skipped_for_missing(TOOL, path, label, "json" if args.json else "text"):
            return 0

    watch = config.terms.watch_words or {}
    topics = as_pattern(watch.get("reading_topics"))
    groups = reading_groups(watch.get("reading_groups"))
    try:
        identities = read_identities(config.sources.bibliography)
    except (OSError, BibliographyError) as error:
        return tool_failed("cannot read %s: %s" % (config.sources.bibliography, error), TOOL)
    rows, cached, unread, queue, stubs = build_queue(
        parse_bank(sources_list, identities), parse_bank(quotes), folders_from_config(config),
        topics, groups, args.all)
    if args.group:
        queue = [row for row in queue if row["group"] == args.group]

    if args.json:
        print(json.dumps(queue, indent=1))
    elif args.keys_only:
        print(" ".join(row["key"] for row in queue))
    else:
        print_report(rows, cached, unread, queue, stubs, groups,
                     topics is not None and not args.all, args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())
