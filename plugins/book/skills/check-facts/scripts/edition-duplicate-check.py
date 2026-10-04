#!/usr/bin/env python3
"""Find works kept under more than one edition, and URLs that point at a moving target.

A book cites some works for a date and others for their wording, and the two pull in
opposite directions: the date belongs to the first edition, the wording to the
printing actually read. The citation rule resolves it with one .bib entry per work, for
the printing read, with its first publication in `origdate` (`edition = {2}`,
`origdate = {1988}`). This script finds where that rule was not followed; such entries
look ordinary to every other check. It reads the .bib (sources.bibliography) and, for
the reason a pair is kept, the Note of each sources list entry.

Classes:
  edition-pair   INFORMATIONAL  two or more entries for one work (same first surname, same
                           title once edition words are removed). The exception is real
                           when the editions differ in the content cited (verify it in
                           both cached texts), so each row shows citation counts
  no-first-pub   DEFECT    an entry with a later `edition` and no `origdate`
  unexplained    DEFECT    an entry in an edition pair with no `origdate` and no reason in
                           its .bib note or its sources list Note; months later it is
                           indistinguishable from a duplicate
  moving-target  DEFECT    a URL at a mutable ref (a main/master branch, a /latest/ docs
                           path, a generated doxygen page): it keeps resolving while the
                           content drifts away from the claim. Pin a tag or a commit

Usage:
  edition-duplicate-check.py                       the .bib, with citation counts
  edition-duplicate-check.py --bibliography <refs.bib> [manuscript folder or file]
  edition-duplicate-check.py --self-test
"""

import argparse
import collections
import re
import sys
import tempfile

sys.dont_write_bytecode = True

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, manuscript_paths, tool_failed
from check_output import (DEFECT, INFORMATIONAL, SHARED_CLASSES, CheckReport,
                          add_output_arguments, skipped_for_missing)
from bibliography import BibliographyError, parse_bibliography, read_bibliography
from citations import find_citations
from source_registry import read_bank

TOOL = "edition-duplicate-check"
CLASSES = {"edition-pair": INFORMATIONAL, "no-first-pub": DEFECT, "unexplained": DEFECT,
           "moving-target": SHARED_CLASSES["moving-target"]}
EDITION_WORD = re.compile(
    r"\b(\d+(st|nd|rd|th)|first|second|third|fourth|fifth|sixth|revised|updated"
    r"|anniversary|edition|ed\.?|reprint)\b", re.I)
FIRST_EDITION = re.compile(r"^\s*(1|1st|first)\b", re.I)
EXPLAINS_THE_PAIR = re.compile(
    r"\b(kept alongside|superseded|first edition is|edition history|cited for)\b", re.I)
MOVING_REF = re.compile(
    r"/blob/(?:main|master)/|/tree/(?:main|master)/|/raw/(?:main|master)/"
    r"|/latest/|/en/stable/|/current/|doxygen", re.I)
NOISE = re.compile(r"\b(the|a|an|of|in|for|and|to|on)\b")
URL = re.compile(r"https?://[^\s}]+")


def normalise(title):
    t = title.split(":")[0].replace("*", "").lower()
    t = EDITION_WORD.sub(" ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = NOISE.sub(" ", t)
    return " ".join(t.split())


def first_surname(entry):
    names = [name for name in entry.authors or entry.editors if not name.others]
    return names[0].surname.lower() if names else ""


def read_entries(bibliography, notes):
    entries = {}
    for key, entry in bibliography.entries.items():
        title = entry.plain("title")
        edition = entry.plain("edition")
        entries[key] = dict(
            key=key, year=entry.plain("year") or "--", title=title, norm=normalise(title),
            surname=first_surname(entry),
            designation="" if not edition or FIRST_EDITION.match(edition) else edition,
            first_published=entry.plain("origdate"),
            reason=" ".join(part for part in (entry.plain("note"), notes.get(key, "")) if part),
            urls=[url for name in ("url", "howpublished", "note")
                  for url in URL.findall(entry.field(name) or "")])
    return entries


def list_notes(sources_list):
    if not sources_list or not Path(sources_list).is_file():
        return {}
    return {entry.key: entry.field("Note") or "" for entry in read_bank(sources_list).entries}


def citation_counts(manuscript_files, keys):
    counts = collections.Counter()
    where = collections.defaultdict(set)
    for path in manuscript_files:
        with open(path, encoding="utf-8", errors="replace") as handle:
            body = handle.read()
        for citation in find_citations(body):
            if citation.key in keys:
                counts[citation.key] += 1
                where[citation.key].add(Path(path).name)
    return counts, where


def analyse(entries, counts):
    groups = collections.defaultdict(list)
    for key, e in entries.items():
        if e["norm"]:
            groups[(e["surname"], e["norm"])].append(key)
    pairs = {g: sorted(ks, key=lambda k: entries[k]["year"])
             for g, ks in groups.items() if len(ks) > 1}
    no_first_pub = sorted(k for k, e in entries.items()
                          if e["designation"] and not e["first_published"])
    unexplained = sorted({k for ks in pairs.values() for k in ks
                          if not entries[k]["first_published"]
                          and not EXPLAINS_THE_PAIR.search(entries[k]["reason"])})
    moving = []
    for k, e in entries.items():
        for url in e["urls"]:
            if MOVING_REF.search(url):
                moving.append((k, url))
                break
    return pairs, no_first_pub, unexplained, sorted(moving)


FIXTURE_BIBLIOGRAPHY = '''@book{Fen04,
  author = {Fenwick, L.},
  title = {The Allotment Year},
  edition = {2},
  publisher = {Example Press},
  year = {2004},
}

@book{Fen15,
  author = {Fenwick, L.},
  title = {The Allotment Year},
  edition = {3},
  publisher = {Example Press},
  year = {2015},
  origdate = {1996},
}

@article{Ols82a,
  author = {Olsen, T. B.},
  title = {A Note on Winter Leeks},
  journal = {Journal of Examples},
  year = {1982},
}

@article{Ols82b,
  author = {Olsen, T. B.},
  title = {Seed Saving on Small Plots},
  journal = {Journal of Examples},
  year = {1982},
}

@book{Hug03,
  author = {Hughes, P.},
  title = {Mending Old Hedges},
  publisher = {Example Press},
  year = {2003},
}

@book{Hug17,
  author = {Hughes, P.},
  title = {Mending Old Hedges},
  edition = {2},
  publisher = {Example Press},
  year = {2017},
  origdate = {2003},
}

@misc{WID24,
  author = {{River Data Project}},
  title = {Flow tables, release 18.1.0},
  year = {2024},
  url = {https://github.com/riverdata/riverdata/tree/riverdata-18.1.0},
}

@misc{WID25,
  author = {{River Data Project}},
  title = {levels.csv},
  year = {2025},
  url = {https://github.com/riverdata/riverdata/blob/main/data/levels.csv},
}

@book{Tan94,
  author = {Tanner, S.},
  title = {A Field Guide to Pond Plants},
  edition = {Second},
  publisher = {Example Press},
  year = {1994},
  origdate = {1986},
}
'''

FIXTURE_NOTES = {"Hug03": "Kept alongside Hug17 because one named method appears here only."}

FIXTURE_CHAPTER = '''# Chapter 7

The method is named in [@Hug17], and [@Fen15, ch. 4] argues the same. The threshold is
a published constant [@WID24]. The letter came first [@Ols82a], twice [@Ols82b; @Ols82a].

```
[@Hug03] inside code is not a citation
```
'''


def self_test():
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    with tempfile.TemporaryDirectory() as root:
        chapter = Path(root, "170-chapter-7.md")
        chapter.write_text(FIXTURE_CHAPTER, encoding="utf-8")
        entries = read_entries(parse_bibliography(FIXTURE_BIBLIOGRAPHY), FIXTURE_NOTES)
        counts, _where = citation_counts([chapter], set(entries))
    pairs, no_first_pub, unexplained, moving = analyse(entries, counts)
    paired = sorted(k for ks in pairs.values() for k in ks)
    require(paired == ["Fen04", "Fen15", "Hug03", "Hug17"], "wrong pairs: %s" % paired)
    require(no_first_pub == ["Fen04"], "wrong no-first-pub: %s" % no_first_pub)
    require(unexplained == ["Fen04"], "wrong unexplained: %s" % unexplained)
    require([k for k, _u in moving] == ["WID25"], "wrong moving targets: %s" % moving)
    require(normalise("The Allotment Year 2nd Edition") == normalise("The Allotment Year"),
            "a bare ordinal must normalise away")
    require(counts.get("Hug17") == 1 and counts.get("Hug03") is None,
            "citation counts wrong: the uncited half of a pair is the useful half")
    require(counts.get("Ols82a") == 2, "a key cited twice counts twice: %s" % counts)
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("target", nargs="?",
                        help="manuscript file or folder for citation counts (default: the book's manuscript files)")
    parser.add_argument("--bibliography", help="the .bib file (default: sources.bibliography)")
    parser.add_argument("--verbose", action="store_true", help="show each entry's text")
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    references = args.bibliography or config.sources.bibliography
    if args.bibliography and not Path(references).exists():
        return tool_failed("no bibliography at %s" % references, TOOL)
    if skipped_for_missing(TOOL, references, "bibliography", args.format):
        return 0
    report = CheckReport(TOOL, CLASSES)
    manuscript = manuscript_paths(config, TOOL, args.target)
    if not manuscript:
        report.skip("no manuscript files at %s" % (args.target or config.manuscript.dir))
        return report.emit(args.format)
    try:
        entries = read_entries(read_bibliography(references), list_notes(config.sources.list))
    except (OSError, ValueError, BibliographyError) as error:
        return tool_failed("cannot read %s: %s" % (references, error), TOOL)
    counts, where = citation_counts(manuscript, set(entries))
    pairs, no_first_pub, unexplained, moving = analyse(entries, counts)

    for group in sorted(pairs, key=lambda g: entries[pairs[g][0]]["title"].lower()):
        keys = pairs[group]
        cited = ", ".join("%s %s cites=%d in %s" % (k, entries[k]["year"], counts.get(k, 0),
                                                     ",".join(sorted(where.get(k, ()))) or "-")
                          for k in keys)
        if all(counts.get(k, 0) > 0 for k in keys):
            advice = "all cited: keep only if the editions differ in the content cited"
        else:
            advice = "uncited: %s" % ", ".join(
                k for k in keys if not counts.get(k, 0))
        report.add(",".join(keys), "edition-pair", "%s -- %s -- %s"
                   % (entries[keys[0]]["title"].split(":")[0], cited, advice))
    for key in no_first_pub:
        report.add(key, "no-first-pub", "names an edition but has no origdate: %s"
                   % entries[key]["title"][:70])
    for key in unexplained:
        report.add(key, "unexplained", "in an edition pair and says nothing about why: %s"
                   % entries[key]["title"][:70])
    for key, url in moving:
        report.add(key, "moving-target", "pin a tag or commit: %s" % url[:110])
    if args.verbose and args.format == "text":
        for keys in pairs.values():
            for key in keys:
                print("%s %s, %s" % (key, entries[key]["title"][:120], entries[key]["year"]))
        print()
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
