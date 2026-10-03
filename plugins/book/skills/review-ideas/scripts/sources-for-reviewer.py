#!/usr/bin/env python3
"""Draft a list of neutral sources for an outside reviewer, and check such a list for bias.

A reviewer who gets the book cold should be able to check its main claims
against the primary sources without taking the book's word for anything. The list
gives, per claim: where the book makes it, the primary sources in reading order with a
free full-text link, what each source establishes, and a Nuance line where the source
is commonly misread or the book's wording sits at its edge. It ends with an index of
the free links. It is a reading list, never an argument for the book.

`draft` builds the skeleton from the banks: book locations come from the manuscript,
titles and links from the sources list, and "what it establishes" from the quotes
bank's Key findings and Scope. The Guardrail is copied under Nuance as raw material and
must be rewritten neutrally by the person or agent finishing the list. Claims come
from a claims file (one claim per line: `claim title<TAB>Key1,Key2`), or one section
per key with --keys.

`check` reads a finished list and flags any sentence that argues for the book. A
Nuance line may point out tension AGAINST the book; it must never resolve it FOR the
book. The test for each sentence: does it describe the SOURCE, or reassure about the
BOOK?

Classes (check):
  argues-for-the-book   DEFECT  "the book argues/rightly/correctly", "this is the source
                                for", "the book hedges/reflects this correctly", "supports
                                the book", a concluding reassurance

Usage:
  sources-for-reviewer.py draft --claims claims.tsv > sources-for-reviewer.md
  sources-for-reviewer.py draft --keys Smi99,Jon01 --out sources-for-reviewer.md
  sources-for-reviewer.py check sources-for-reviewer.md
  sources-for-reviewer.py --self-test
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, shown_path, tool_failed
from check_output import DEFECT, CheckReport, add_output_arguments
from source_registry import read_bank

TOOL = "sources-for-reviewer"
CLASSES = {"argues-for-the-book": DEFECT}

URL_RE = re.compile(r"https?://[^\s<>\"'`)\]]+")
CLOSED = re.compile(r"NO OPEN-ACCESS COPY|MANUAL FETCH REQUIRED|paywall", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+")

ARGUING = [
    (re.compile(r"\bthe (?:book|author|manuscript|chapter)\s+(?:\w+\s+)?(?:rightly|correctly|"
                r"properly|wisely|accurately)\b", re.I), "praises the book"),
    (re.compile(r"\b(?:rightly|correctly)\s+(?:hedges?|notes?|argues?|says?|claims?|states?)\b",
                re.I), "grades the book's wording"),
    (re.compile(r"\bthe (?:book|author|manuscript|chapter)\s+(?:argues|is right|gets this right|"
                r"reflects this|hedges)\b", re.I), "speaks for the book"),
    (re.compile(r"\bthis is the source for\b", re.I), "names the source as the book's support"),
    (re.compile(r"\b(?:supports?|confirms?|vindicates?|backs up)\s+the (?:book|author|"
                r"manuscript|chapter)\b", re.I), "reassures about the book"),
    (re.compile(r"\b(?:so|thus|therefore)\s+the (?:book|claim|author)\s+(?:is|stands|holds)\b",
                re.I), "concludes for the book"),
    (re.compile(r"\bno (?:problem|issue|concern) for the (?:book|author|claim)\b", re.I),
     "concludes for the book"),
]


def arguing_sentences(text):
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for sentence in SENTENCE.split(line):
            for pattern, why in ARGUING:
                if pattern.search(sentence):
                    found.append((number, why, sentence.strip()))
                    break
    return found


def citing_sites(manuscript_files, key, root):
    pattern = re.compile(r"\[[^\]\n]*\b%s\b[^\]\n]*\]" % re.escape(key))
    sites = []
    for path in manuscript_files:
        for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) and not line.startswith("[%s]" % key):
                sites.append("%s:%d" % (shown_path(root, path), number))
    return sites


def free_link(entry):
    if entry is None:
        return None, True
    urls = URL_RE.findall(entry.field("Access URLs") or "") + URL_RE.findall(entry.field("DOI/URL") or "")
    closed = bool(CLOSED.search(entry.field("Access status") or ""))
    doi = (entry.field("DOI") or "").strip()
    if urls:
        return urls[0].rstrip(".,;"), closed
    if doi:
        return "https://doi.org/" + doi, True
    return None, True


def source_block(key, sources, quotes):
    entry = sources.get(key)
    finding = quotes.get(key)
    title = (entry.field("Full title") if entry else None) or key
    authors = (entry.field("Authors") if entry else None) or "authors not recorded"
    year = (entry.field("Year") if entry else None) or "year not recorded"
    link, closed = free_link(entry)
    lines = ["- [%s] %s. %s (%s)." % (key, authors, title, year)]
    if link:
        lines.append("  - Link: %s%s" % (link, " (not free: look for an open copy)" if closed else ""))
    else:
        lines.append("  - Link: none recorded")
    established = []
    if finding is not None:
        for field in ("Key findings", "Scope"):
            value = finding.field(field)
            if value:
                established.append(" ".join(value.split()))
    lines.append("  - What it establishes: %s" % (" ".join(established)
                                                   or "TO WRITE from the source itself"))
    guardrail = finding.field("Guardrail") if finding is not None else None
    lines.append("  - Nuance: %s" % ("REWRITE NEUTRALLY -- " + " ".join(guardrail.split())
                                     if guardrail else "none recorded"))
    return lines, (key, title, link) if link and not closed else None


def draft(claims, sources, quotes, manuscript_files, root):
    out = ["# Sources for the reviewer", "",
           "## What this is", "",
           "A neutral reading list for the book's main claims: where the book makes",
           "each claim, the primary sources, what they establish, and where they are commonly",
           "misread. It does not argue the book's case.", "",
           "## How to use it", "",
           "Read the sources in the order given. Judge the book against them, not them",
           "against the book.", ""]
    index = []
    for title, keys in claims:
        out.append("## %s" % title)
        out.append("")
        sites = sorted({site for key in keys for site in citing_sites(manuscript_files, key, root)},
                       key=lambda site: (site.rsplit(":", 1)[0], int(site.rsplit(":", 1)[1])))
        out.append("Book: %s" % (", ".join(sites) if sites else "not cited in the manuscript"))
        out.append("")
        out.append("Primary sources:")
        for key in keys:
            lines, free = source_block(key, sources, quotes)
            out.extend(lines)
            if free:
                index.append(free)
        out.append("")
    out.append("## Quick index of free full-text links")
    out.append("")
    for key, title, link in sorted(set(index)):
        out.append("- [%s] %s: %s" % (key, title, link))
    return "\n".join(out) + "\n"


def read_claims(path):
    claims = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or "\t" not in line:
            continue
        title, keys = line.split("\t", 1)
        claims.append((title.strip(), [k.strip() for k in keys.split(",") if k.strip()]))
    return claims


FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
```

### [Smi99] Smith, "Morning walks" (1999)

**Full title:** Morning walks and sleep
**Authors:** Nora Smith
**Year:** 1999
**Access URLs:** https://example.org/smith.pdf

---
"""

FIXTURE_QUOTES = """# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
```

### [Smi99] Smith, "Morning walks" (1999)

**Key findings:** adults who walked outdoors each morning slept about twenty minutes longer.
**Scope:** one town, adult participants, eight weeks.
**Guardrail:** do not cite this for a per-person gain; it is a group average.

---
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        (root / "list.md").write_text(FIXTURE_LIST, encoding="utf-8")
        (root / "quotes.md").write_text(FIXTURE_QUOTES, encoding="utf-8")
        chapter = root / "110-chapter-1.md"
        chapter.write_text("Morning walkers sleep longer [Smi99].\n", encoding="utf-8")
        sources = {e.key: e for e in read_bank(root / "list.md").entries}
        quotes = {e.key: e for e in read_bank(root / "quotes.md").entries}
        text = draft([("Morning walks lengthen sleep", ["Smi99"])], sources, quotes,
                     [chapter], root)
    for expected in ("110-chapter-1.md:1", "https://example.org/smith.pdf",
                     "slept about twenty minutes longer", "REWRITE NEUTRALLY",
                     "Quick index of free full-text links"):
        if expected not in text:
            failures.append("the draft lacks %r" % expected)
    if arguing_sentences(text):
        failures.append("the generated skeleton argues for the book: %s" % arguing_sentences(text))
    biased = ("The book rightly hedges this. This is the source for the claim in chapter 1. "
              "So the book is safe here.\nThe source measured adults only.\n")
    found = arguing_sentences(biased)
    if len(found) != 3 or any(number != 1 for number, _why, _s in found):
        failures.append("the neutrality check missed or over-flagged: %s" % found)
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("action", nargs="?", choices=("draft", "check"))
    parser.add_argument("file", nargs="?", help="check: the list to check")
    parser.add_argument("--claims", help="draft: claims file, `title<TAB>Key1,Key2` per line")
    parser.add_argument("--keys", help="draft: one section per key instead of a claims file")
    parser.add_argument("--out", help="draft: write here instead of standard output")
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.action is None:
        parser.print_help()
        return 2

    if args.action == "check":
        if not args.file or not Path(args.file).is_file():
            return tool_failed("check needs the list file", TOOL)
        report = CheckReport(TOOL, CLASSES)
        for number, why, sentence in arguing_sentences(Path(args.file).read_text(encoding="utf-8")):
            report.add("line %d" % number, "argues-for-the-book", "%s: %s" % (why, sentence[:160]))
        return report.emit(args.format)

    config = load_book(args, TOOL)
    if args.claims:
        claims = read_claims(args.claims)
    elif args.keys:
        claims = [(key, [key]) for key in args.keys.split(",") if key.strip()]
    else:
        return tool_failed("draft needs --claims or --keys", TOOL)
    sources = {e.key: e for e in read_bank(config.sources.list).entries}
    quotes = {e.key: e for e in read_bank(config.sources.quotes).entries}
    files = [item.path for item in config.manuscript_files()
             if item.kind not in ("references",)]
    text = draft(claims, sources, quotes, files, config.root)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print("wrote %s" % args.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
