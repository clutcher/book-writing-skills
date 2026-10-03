#!/usr/bin/env python3
"""Find works cited under more than one edition, and URLs that point at a moving target.

A book cites some works for a date and others for their wording, and the two pull in
opposite directions: the date belongs to the first edition, the wording to the
printing actually read. The citation rule resolves it with one entry per work,
dual-dated ("2nd ed. ... First published 1988."). This script finds where that rule
was not followed; such entries look ordinary to every other check.

Classes:
  edition-pair   INFORMATIONAL  two or more entries for one work. The exception is real
                           when the editions differ in the content cited (verify it in
                           both cached texts), so each row shows citation counts and
                           whether each entry explains itself. A pair whose entries
                           explain themselves is the documented exception; an entry that
                           does not is `unexplained`
  no-first-pub   DEFECT    an entry that designates a later edition ("2nd ed." right
                           after the title) with no `First published` date. Position
                           decides: an edition merely MENTIONED in the prose (a first
                           edition explaining why it is kept) is not a designation
  unexplained    DEFECT    an entry in an edition pair that says nothing about why the
                           split exists; months later it is indistinguishable from a
                           duplicate
  moving-target  DEFECT    a URL at a mutable ref (a main/master branch, a /latest/ docs
                           path, a generated doxygen page): it keeps resolving while the
                           content drifts away from the claim. Pin a tag or a commit

Two parsing traps: books italicise the TITLE and papers italicise the JOURNAL, so the
italic run is taken only when it follows the year; and a bare ordinal must be stripped
with "edition", or "Title 2nd" and "Title" hide the pair.

Usage:
  edition-duplicate-check.py                       the bibliography, with citation counts
  edition-duplicate-check.py --references <refs.md> [manuscript folder or file]
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
from citation_key import bib_blocks

TOOL = "edition-duplicate-check"
CLASSES = {"edition-pair": INFORMATIONAL, "no-first-pub": DEFECT, "unexplained": DEFECT,
           "moving-target": SHARED_CLASSES["moving-target"]}
EDITION_WORD = re.compile(
    r"\b(\d+(st|nd|rd|th)|first|second|third|fourth|fifth|sixth|revised|updated"
    r"|anniversary|edition|ed\.?|reprint)\b", re.I)
_EDITION_PHRASE = (
    r"\d+(?:st|nd|rd|th)\s+ed\b|\d+(?:st|nd|rd|th)\s+edition|anniversary ed|revised ed"
    r"|updated ed|second edition|third edition")
EDITION_MARKER = re.compile(r"\b(%s)" % _EDITION_PHRASE, re.I)

DESIGNATION_AT_TITLE = re.compile(
    r"^\*?[.,]?\s*(?:\(\s*)?(%s)" % _EDITION_PHRASE, re.I)

EDITION_FIELD = re.compile(r"\*\*Edition:\*\*|(?<![A-Za-z])Edition:", re.I)

FIRST_PUB = re.compile(r"First published\s+\d{4}", re.I)
MOVING_REF = re.compile(
    r"/blob/(?:main|master)/|/tree/(?:main|master)/|/raw/(?:main|master)/"
    r"|/latest/|/en/stable/|/current/|doxygen", re.I)
NOISE = re.compile(r"\b(the|a|an|of|in|for|and|to|on)\b")



def normalise(title):
    t = title.split(":")[0].replace("*", "").lower()
    t = EDITION_WORD.sub(" ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = NOISE.sub(" ", t)
    return " ".join(t.split())


def parse_references(path):
    entries = {}
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    for _lineno, key, block in bib_blocks(content, any_key=True):
        rest = block.strip().replace("\n", " ")
        ym = re.search(r"\((c\.\s*)?(\d{4}|--)[a-z]?\)\.", rest)
        year = ym.group(2) if ym else ""
        authors = rest[:ym.start()] if ym else ""
        after = rest[ym.end():].strip() if ym else rest
        if after.startswith("*"):
            im = re.match(r"\*([^*]+)\*", after)
            title = im.group(1) if im else after
            after_title = after[im.end():] if im else ""
        elif ". *" in after:
            title = after.split(". *")[0]
            after_title = after[len(title):]
        else:
            title = after.split(". ")[0]
            after_title = after[len(title):]
        surnames = re.findall(r"[A-Z][A-Za-z'\-]{2,}", authors)
        entries[key] = dict(
            key=key, year=year, raw=rest, title=title.replace("*", "").strip(),
            norm=normalise(title), surname=(surnames[0].lower() if surnames else ""),
            designation=designation(after_title, rest))
    return entries


def designation(after_title, raw):
    found = DESIGNATION_AT_TITLE.match(after_title)
    if found:
        return found.group(1)
    field = EDITION_FIELD.search(raw)
    if field:
        found = DESIGNATION_AT_TITLE.match(raw[field.end():])
        if found:
            return found.group(1)
    return ""


def citation_counts(manuscript_files, keys):
    counts = collections.Counter()
    where = collections.defaultdict(set)
    for path in manuscript_files:
        with open(path, encoding="utf-8", errors="replace") as handle:
            body = handle.read()
        for key in keys:
            n = len(re.findall(r"\[[^\]\n]*\b%s\b[^\]\n]*\]" % re.escape(key), body))
            if Path(path).name.endswith("references.md"):
                n = max(0, n - 1)
            if n:
                counts[key] += n
                where[key].add(Path(path).name)
    return counts, where


def analyse(entries, counts):
    groups = collections.defaultdict(list)
    for key, e in entries.items():
        if e["norm"]:
            groups[(e["surname"], e["norm"])].append(key)
    pairs = {g: sorted(ks, key=lambda k: entries[k]["year"])
             for g, ks in groups.items() if len(ks) > 1}
    no_first_pub = sorted(k for k, e in entries.items()
                          if e["designation"] and not FIRST_PUB.search(e["raw"]))
    unexplained = []
    for ks in pairs.values():
        for k in ks:
            raw = entries[k]["raw"]
            explains = FIRST_PUB.search(raw) or re.search(
                r"\b(kept alongside|superseded|first edition is|edition history|cited for)\b",
                raw, re.I)
            if not explains:
                unexplained.append(k)
    moving = []
    for k, e in entries.items():
        for url in re.findall(r"https?://\S+", e["raw"]):
            if MOVING_REF.search(url):
                moving.append((k, url))
                break
    return pairs, no_first_pub, sorted(set(unexplained)), sorted(moving)


FIXTURE_REFERENCES = '''# References

[Fen04] Fenwick, L. (2004). *The Allotment Year* (2nd ed.). Example Press. ISBN 9780000000026.

[Fen15] Fenwick, L. (2015). *The Allotment Year*. 3rd ed. Example Press. First published 1996. ISBN 9780000000033.

[Ols82a] Olsen, T.B. (1982). A Note on Winter Leeks. *Journal of Examples*, 9(1), 33-35. https://doi.org/10.5555/ols82a

[Ols82b] Olsen, T.B. (1982). Seed Saving on Small Plots. *Journal of Examples*, 9(3), 70-77. https://doi.org/10.5555/ols82b

[Wal--] Walsh, K. (--). A page whose date could not be established. https://catalog.example.org/

[Hug03] Hughes, P. (2003). *Mending Old Hedges*. Example Press. Kept alongside [Hug17] because one named method appears here and not in the 2nd ed. The printed 1st edition runs 312 pages. ISBN 9780000000040.

[Hug17] Hughes, P. (2017). *Mending Old Hedges* (2nd ed.). Example Press. First published 2003. ISBN 9780000000057.

[WID24] River Data Project. (2024). Flow tables, release 18.1.0: flood-threshold = 150 in data/levels.csv line 171. https://github.com/riverdata/riverdata/tree/riverdata-18.1.0

[WID25] River Data Project. (2025). levels.csv. https://github.com/riverdata/riverdata/blob/main/data/levels.csv

[Tan94] Tanner, S. (1994). *A Field Guide to Pond Plants*. 2nd ed. Example Press. First published 1986. ISBN 9780000000019.

[ABCD25] Adams, V., Baker, J., Clark, J., & Davis, D. (2025). Tide Tables. Data file *tides.csv*, read at release 25: CUTOFF = 44 at line 69. https://github.com/example/tides/blob/release-25/data/tides.csv
'''

FIXTURE_CHAPTER = '''# Chapter 7

The method is named in [Hug17], and [Fen15] chapter 4 argues the same. The threshold is
a published constant [WID24], and the cutoff is another [ABCD25]. The letter came
first [Ols82a], twice [Ols82b].
'''


def self_test():
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    with tempfile.TemporaryDirectory() as root:
        references = Path(root, "900-references.md")
        chapter = Path(root, "170-chapter-7.md")
        with open(references, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_REFERENCES)
        with open(chapter, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_CHAPTER)
        entries = parse_references(references)
        counts, _where = citation_counts([chapter], set(entries))
    pairs, no_first_pub, unexplained, moving = analyse(entries, counts)
    paired = sorted(k for ks in pairs.values() for k in ks)
    require(paired == ["Fen04", "Fen15", "Hug03", "Hug17"], "wrong pairs: %s" % paired)
    require(no_first_pub == ["Fen04"], "wrong no-first-pub: %s" % no_first_pub)
    require(unexplained == ["Fen04"], "wrong unexplained: %s" % unexplained)
    require([k for k, _u in moving] == ["WID25"], "wrong moving targets: %s" % moving)
    require(entries["Ols82a"]["title"] == "A Note on Winter Leeks",
            "a paper's title must come from the plain text: %r" % entries["Ols82a"]["title"])
    require(entries["Wal--"]["year"] == "--", "the dateless form must parse as '--'")
    require(normalise("The Allotment Year 2nd Edition") == normalise("The Allotment Year"),
            "a bare ordinal must normalise away")
    require(counts.get("Hug17") == 1 and counts.get("Hug03") is None,
            "citation counts wrong: the uncited half of a pair is the useful half")
    require(entries["Hug03"]["designation"] == "" and EDITION_MARKER.search(entries["Hug03"]["raw"]),
            "a printing MENTIONED in prose is not a designation")
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
    parser.add_argument("--references", help="the bibliography (default: manuscript.references)")
    parser.add_argument("--verbose", action="store_true", help="show each entry's text")
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    references = args.references or config.manuscript.references
    if args.references and not Path(references).exists():
        return tool_failed("no bibliography at %s" % references, TOOL)
    if skipped_for_missing(TOOL, references, "bibliography", args.format):
        return 0
    report = CheckReport(TOOL, CLASSES)
    manuscript = manuscript_paths(config, TOOL, args.target)
    if not manuscript:
        report.skip("no manuscript files at %s" % (args.target or config.manuscript.dir))
        return report.emit(args.format)
    entries = parse_references(references)
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
            advice = "uncited: %s (the bibliography holds only what the book cites)" % ", ".join(
                k for k in keys if not counts.get(k, 0))
        report.add(",".join(keys), "edition-pair", "%s -- %s -- %s"
                   % (entries[keys[0]]["title"].split(":")[0], cited, advice))
    for key in no_first_pub:
        report.add(key, "no-first-pub", "names an edition but records no original date: %s"
                   % entries[key]["title"][:70])
    for key in unexplained:
        report.add(key, "unexplained", "in an edition pair and says nothing about why: %s"
                   % entries[key]["title"][:70])
    for key, url in moving:
        report.add(key, "moving-target", "pin a tag or commit: %s" % url[:110])
    if args.verbose and args.format == "text":
        for keys in pairs.values():
            for key in keys:
                print("[%s] %s" % (key, entries[key]["raw"][:150]))
        print()
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
