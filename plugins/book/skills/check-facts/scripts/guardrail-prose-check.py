#!/usr/bin/env python3
"""Pair each `Guardrail:` in the quotes bank with the book's sentences that cite its key.

IT SURFACES, IT NEVER ENFORCES. A guardrail is a present-tense instruction about how a
source may be cited. Written, banked and never read again, it protects nothing: a book
can print exactly the attribution its own bank forbids. But a guardrail can itself be
false (one said every measure was self-reported, over an outcome the paper's own words
call logs-based), so a tool that enforced guardrails would put errors INTO the book.
So there is no verdict on compliance and no DEFECT class: the output is a pairing for a
person, and the source outranks the guardrail. When they disagree, open the page, then
correct whichever of the two is wrong.

Classes:
  phrase-in-prose        ADVISORY  a DISTINCTIVE multi-word span the guardrail forbids in
                                   so many words appears verbatim in a paragraph that
                                   cites the key (marked quoted: or unquoted:, because a
                                   wording guardrail usually turns on that)
  absent-term            ADVISORY  the guardrail says a word is absent from the source
                                   ("appears zero times") and that word appears in a
                                   paragraph citing the key
  unreachable-guardrail  INFORMATIONAL  the key is cited nowhere, so the guardrail
                                   protects nothing (dropped citation, or a source kept
                                   for later); listed with --unreachable only
  phrase-no-citation-nearby INFORMATIONAL  a forbidden phrase with no citation in its
                                   paragraph; --wide only

Phrase matching is conservative, because a false positive teaches the author to stop
reading. A quoted span is forbidden only when a prohibition (do not, never, must not,
may not, cannot, not supported, does not support, sentence-initial avoid) sits in the
same clause WITH THE QUOTED SPANS MASKED, so a quotation containing "avoid" cannot
license itself. The nearest cue before a quoted span decides it: after an endorsement
(supports, supported by, is correct, sentence-initial cite for) the span is one the
source SUPPORTS and is not flagged, unless a prohibition comes right before that
endorsement ("do not say it supports"). A span with no cue before it is forbidden
when the clause holds a prohibition anywhere. Clauses split on ; and : as well as
. ! ?, after bold marks are removed. Other "does not" and "did not" describe the
source and are not prohibitions.
A phrase needs 4+ words and 20+ characters, and the key must be cited in the same
paragraph. Code fences are ignored. The bibliography is excluded, because it prints
every key and would make every source look cited.

Usage:
  guardrail-prose-check.py                  every guardrail beside its citing sentences
  guardrail-prose-check.py --key Smi99      one key (repeatable)
  guardrail-prose-check.py --flagged        only guardrails with a phrase or term flag
  guardrail-prose-check.py --unreachable    guardrails whose key is cited nowhere
  guardrail-prose-check.py --directives     only guardrails carrying a prohibition
  guardrail-prose-check.py --wide           also forbidden phrases with no citation nearby
  guardrail-prose-check.py --self-test

It always exits 0 when it ran: there is no exit code meaning "a guardrail was violated".
"""

import argparse
import collections
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (add_config_arguments, load_book, manuscript_paths,
                          markdown_files_under, tool_failed)
from check_output import (ADVISORY, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing)
from citation_key import KEY_SHAPE
from source_registry import read_bank

TOOL = "guardrail-prose-check"
CLASSES = {
    "phrase-in-prose": ADVISORY,
    "absent-term": ADVISORY,
    "unreachable-guardrail": INFORMATIONAL,
    "phrase-no-citation-nearby": INFORMATIONAL,
}

BRACKET = re.compile(r"\[([^\]\[\n]{1,160})\]")
FENCE = re.compile(r"^```.*?^```", re.M | re.S)
QUOTED = re.compile(r'"([^"\n]{10,240})"|\u201c([^\u201d\n]{10,240})\u201d')
DIRECTIVE = re.compile(r"\bdo not\b|\bdon't\b|\bnever\b|\bmust not\b|\bmay not\b"
                       r"|\bnot be cited\b|\bnot supported\b|\bdoes not support\b"
                       r"|\bunsupported\b|\bcannot\b|\bcan't\b|^\s*avoid\b", re.I)
ENDORSEMENT = re.compile(r"\bsupports?\b|\bsupported by\b|\bis correct\b"
                         r"|^\s*cite (?:\w+ )?for\b", re.I)
BOLD = re.compile(r"\*+")
WARNING, ENDORSING, QUOTATION = "warning", "endorsing", "quotation"
CLAUSE_SPLIT = re.compile(r"(?<=[.!?;:])[\"'”)\]]?\s+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])[\"'”)\]]?\s+")
ABSENCE = re.compile(
    r"zero times|zero occurrences|occurs? nowhere|appears? nowhere"
    r"|never uses the (?:word|term)|does not use the (?:word|term)"
    r"|never mentions", re.I)
NO_LIST = re.compile(r"(?i:\bno)\s+((?:[a-z][a-z-]{3,}(?:,| or | and |,? )){0,5}[a-z][a-z-]{3,})\b")
MIN_PHRASE_WORDS = 4
MIN_PHRASE_CHARS = 20
MIN_TERM_CHARS = 5
TERM_STOPWORDS = frozenset((
    "paper", "papers", "study", "studies", "finding", "findings", "result",
    "results", "claim", "claims", "source", "sources", "quote", "quotes",
    "manuscript", "chapter", "section", "table", "figure", "authors", "author",
    "measure", "measures", "data", "evidence", "effect", "effects", "sample",
    "method", "methods", "there", "these", "those", "other", "another",
    "such", "which", "where", "about", "number", "numbers", "value", "values",
))


def strip_fenced(text):
    return FENCE.sub("", text)


def entries(path):
    for entry in read_bank(path).entries:
        yield entry.key, entry.heading_tail, entry


def field_block(block, name):
    return block.field(name) or ""


def normalise(text):
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2212", "-")
    text = re.sub(r"[*_`]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def cited_keys(line):
    found = set()
    for group in BRACKET.findall(line):
        for token in re.split(r"[,;]", group):
            token = token.strip()
            if KEY_SHAPE.match(token):
                found.add(token)
    return found


def read_manuscript(manuscript_files, references=None):
    files = {}
    index = collections.defaultdict(list)
    skip = Path(references).resolve() if references else None
    for path in manuscript_files:
        name = Path(path).name
        if "references" in name.lower() or (skip and Path(path).resolve() == skip):
            continue
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().split("\n")
        fenced = False
        kept = []
        for number, line in enumerate(lines, 1):
            if line.startswith("```"):
                fenced = not fenced
                kept.append("")
                continue
            kept.append("" if fenced else line)
            if fenced:
                continue
            for key in cited_keys(line):
                index[key].append((name, number))
        files[name] = kept
    return files, index


def citing_sentence(line, key):
    for sentence in SENTENCE_SPLIT.split(line):
        if "%s]" % key in sentence or "%s," % key in sentence or "%s;" % key in sentence:
            if re.search(r"\[[^\]\n]*%s" % re.escape(key), sentence):
                return sentence.strip()
    return line.strip()


def quote_spans(clause):
    return [(match.start(), (match.group(1) or match.group(2)))
            for match in QUOTED.finditer(clause)]


def blanked(text, pattern):
    return pattern.sub(lambda match: " " * len(match.group(0)), text)


def stance_cues(clause):
    unquoted = blanked(clause, QUOTED)
    events = [(match.end(), WARNING) for match in DIRECTIVE.finditer(unquoted)]
    events += [(match.end(), ENDORSING)
               for match in ENDORSEMENT.finditer(blanked(unquoted, DIRECTIVE))]
    events += [(position, QUOTATION) for position, _ in quote_spans(clause)]
    cues = []
    previous = None
    for position, kind in sorted(events):
        negated_endorsement = kind == ENDORSING and previous == WARNING
        if kind != QUOTATION and not negated_endorsement:
            cues.append((position, kind == WARNING))
        previous = kind
    return cues


def warns_against(position, cues):
    preceding = [warning for end, warning in cues if end <= position]
    if preceding:
        return preceding[-1]
    return any(warning for _, warning in cues)


def long_enough(quote):
    return len(quote.split()) >= MIN_PHRASE_WORDS and len(quote) >= MIN_PHRASE_CHARS


def forbidden_phrases(guardrail):
    phrases = []
    for clause in CLAUSE_SPLIT.split(BOLD.sub("", guardrail)):
        cues = stance_cues(clause)
        for position, quote in quote_spans(clause):
            if long_enough(quote) and warns_against(position, cues):
                phrases.append(quote.strip(" .,;:"))
    return phrases


def absent_terms(guardrail):
    guardrail = re.sub(r"\s+", " ", guardrail)
    terms = set()
    for clause in CLAUSE_SPLIT.split(guardrail):
        if not ABSENCE.search(clause):
            continue
        for match in QUOTED.finditer(clause):
            quote = (match.group(1) or match.group(2)).strip()
            if len(quote.split()) <= 3 and len(quote) >= MIN_TERM_CHARS:
                terms.add(quote.lower())
        for listing in NO_LIST.findall(clause):
            for item in re.split(r",| or | and ", listing):
                for word in item.split():
                    word = word.strip().lower()
                    if len(word) >= MIN_TERM_CHARS and word not in TERM_STOPWORDS:
                        terms.add(word)
    if not terms and ABSENCE.search(guardrail):
        for listing in NO_LIST.findall(guardrail):
            for item in re.split(r",| or | and ", listing):
                for word in item.split():
                    word = word.strip().lower()
                    if len(word) >= MIN_TERM_CHARS and word not in TERM_STOPWORDS:
                        terms.add(word)
    return sorted(terms)


def blocks(lines):
    start = None
    for number, line in enumerate(lines, 1):
        if line.strip():
            start = start or number
        elif start:
            yield start, " ".join(lines[start - 1:number - 1])
            start = None
    if start:
        yield start, " ".join(lines[start - 1:])


def find_phrase(files, phrase):
    needle = normalise(phrase)
    hits = []
    for name, lines in files.items():
        for start, text in blocks(lines):
            flat = normalise(text)
            position = flat.find(needle) if needle else -1
            if position >= 0:
                quoted = position > 0 and flat[position - 1] in '"“'
                hits.append((name, start, quoted))
    return hits


def paragraph(lines, number):
    if not lines[number - 1].strip():
        return number, lines[number - 1]
    start = number
    while start > 1 and lines[start - 2].strip():
        start -= 1
    end = number
    while end < len(lines) and lines[end].strip():
        end += 1
    return start, " ".join(lines[start - 1:end])


def find_term(files, index, key, term):
    needle = re.compile(r"\b%s\b" % re.escape(term.lower()))
    hits = []
    seen = set()
    for name, number in index.get(key, []):
        start, text = paragraph(files[name], number)
        if (name, start) in seen or not needle.search(normalise(text)):
            continue
        seen.add((name, start))
        for sentence in SENTENCE_SPLIT.split(text):
            if needle.search(normalise(sentence)):
                hits.append((name, number, key in cited_keys(sentence), sentence.strip()))
                break
    return hits


def assess(findings_path, manuscript_files, references=None):
    files, index = read_manuscript(manuscript_files, references)
    rows = []
    for key, heading, block in entries(findings_path):
        guardrail = field_block(block, "Guardrail")
        if not guardrail:
            continue
        sites = index.get(key, [])
        flags = []
        unreachable = []
        wide = []
        if not sites:
            unreachable.append(("unreachable-guardrail", "cited in no manuscript file"))
        for phrase in forbidden_phrases(guardrail):
            for name, number, quoted in find_phrase(files, phrase):
                where = '%s:%d %s "%s"' % (name, number,
                                           "quoted:" if quoted else "unquoted:", phrase)
                if key in cited_keys(paragraph(files[name], number)[1]):
                    flags.append(("phrase-in-prose", where))
                else:
                    wide.append(("phrase-no-citation-nearby",
                                 where + " (the key is not cited in that paragraph)"))
        for term in absent_terms(guardrail):
            for name, number, same, sentence in find_term(files, index, key, term):
                flags.append(("absent-term", '%s:%d "%s" %s -- %s' % (
                    name, number, term,
                    "in the citing sentence" if same else "elsewhere in the paragraph",
                    sentence)))
        rows.append({"key": key, "heading": heading, "guardrail": guardrail,
                     "sites": sites, "flags": flags, "unreachable": unreachable,
                     "wide": wide,
                     "directive": bool(DIRECTIVE.search(QUOTED.sub(" QUOTE ", guardrail))),
                     "files": files})
    return rows


def clip(text, limit, verbose):
    text = re.sub(r"\s+", " ", text).strip()
    if verbose or len(text) <= limit:
        return text
    return text[:limit].rstrip() + " ..."


def report(row, files, verbose, wide=False):
    print("\n== [%s] %s" % (row["key"], clip(row["heading"], 70, verbose)))
    print("   guardrail: %s" % clip(row["guardrail"], 400, verbose))
    if not row["sites"]:
        print("   (cited nowhere in the manuscript)")
    for name, number in row["sites"]:
        sentence = citing_sentence(paragraph(files[name], number)[1], row["key"])
        print("   %s:%d  %s" % (name, number, clip(sentence, 220, verbose)))
    rules = row["flags"] + row["unreachable"] + (row["wide"] if wide else [])
    for rule, detail in rules:
        print("   ! %-26s %s" % (rule, clip(detail, 240, verbose)))


FIXTURE_FINDINGS = '''# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Guardrail:** a present-tense instruction. Do not cite this for "a worked example".
```

---

### [SW16] Sower & Weiss, "Crop rotation" (2016)

**Guardrail:** the method's cost is an extra resting season, NOT extra
ploughing. Do not attribute "needs more ploughing passes each year" to this paper.
Weed control is also qualified in the source: "we skip weeding in every season of
the cycle except the last one, which still needs it".
**Source:** see `sources/list.md`

---

### [BMW18] Bell, Moss & Wells, "Road noise and sleep" (2018)

**Guardrail:** this paper contains NO anxiety, mood or well-being
finding -- those words appear zero times in the full text. Do not attach an anxiety
claim to this key.
**Source:** see `sources/list.md`

---

### [Gld20] Goldsmith, "A Source Cited Nowhere" (2020)

**Guardrail:** Do not cite this for the headline figure.
**Source:** see `sources/list.md`

---

### [Per19] Perez, "A Permitted Quotation" (2019)

**Guardrail:** The book's "night traffic wakes sleepers in a quarter of cases" is
this paper's own Finding 5 and does NOT conflate the two quarter-figures. Cite for
"a quarter of nights"; the wording in the book is correct as it stands.
**Source:** see `sources/list.md`

---

### [Hal15] Hale, "Tasting blindfolded" (2015)

**Guardrail:** 1. **The blindfold control supports "hide the label and the trained advantage fades", and so "the gain comes from reading the label rather than from taste".** It does not show that trained tasters do not sense more flavours.
**Source:** see `sources/list.md`

---

### [Orm12] Ormond, "Split shifts" (2012)

**Guardrail:** He reports a lower cost for the split, so do not cite him for "the price is comfort for raw output" or for "only a scheduling trick".
**Source:** see `sources/list.md`

---

### [Vey09] Vey, "Market stalls in bad weather" (2009)

**Guardrail:** So this source cannot support "small stalls sell most in the rain" -- that finding belongs to an older study it only mentions.
**Source:** see `sources/list.md`

---

### [Ryn21] Ryan, "A Guardrail With No Instruction" (2021)

**Guardrail:** the sample is 19 undergraduates, so any claim is provisional.
**Source:** see `sources/list.md`

---
'''

FIXTURE_CHAPTER = """# Chapter 1

A rotation that needs more ploughing passes each year gave substantially larger
harvests by ending this wasted effort [SW16].

Field studies confirmed the effect: night traffic wakes sleepers in a
quarter of cases [BMW18]. The same research found that road noise shortens
sleep every night and raises their anxiety.

The wording in the book is "night traffic wakes sleepers in a quarter of cases"
[Per19], and a scope caution applies [Ryn21].

Trained tasters lose their edge when blindfolded, so the gain comes from reading
the label rather than from taste [Hal15].

At open markets, small stalls sell most in the rain [Vey09].

Splitting the shift looks like a play for output, and the price is comfort for raw
output [Orm12].

```
we skip weeding in every season of the cycle except the last one
```
"""

FIXTURE_EXPECTED = {
    ("SW16", "phrase-in-prose"),
    ("BMW18", "absent-term"),
    ("Gld20", "unreachable-guardrail"),
    ("Orm12", "phrase-in-prose"),
    ("Vey09", "phrase-in-prose"),
}


def self_test():
    with tempfile.TemporaryDirectory() as root:
        quotes = Path(root, "quotes.md")
        manuscript = Path(root, "manuscript")
        Path(manuscript).mkdir(parents=True)
        with open(quotes, "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_FINDINGS)
        with open(Path(manuscript, "110-chapter-1.md"), "w", encoding="utf-8") as handle:
            handle.write(FIXTURE_CHAPTER)
        rows = assess(quotes, markdown_files_under(manuscript))

    found = set((row["key"], rule) for row in rows
                for rule, _ in row["flags"] + row["unreachable"] + row["wide"])
    failures = 0
    for key, rule in sorted(FIXTURE_EXPECTED - found):
        print("FAIL %-10s %-22s NOT REPORTED" % (key, rule))
        failures += 1
    for key, rule in sorted(found - FIXTURE_EXPECTED):
        print("FAIL %-10s %-22s FALSE POSITIVE" % (key, rule))
        failures += 1
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % failures))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--quotes", help="the quotes bank (default: sources.quotes)")
    parser.add_argument("--manuscript", help="a manuscript file or folder (default: the book's manuscript files)")
    parser.add_argument("--key", action="append", help="only this key (repeatable)")
    parser.add_argument("--flagged", action="store_true",
                        help="only guardrails with a phrase or absent-term flag")
    parser.add_argument("--unreachable", action="store_true",
                        help="guardrails whose key the manuscript does not cite")
    parser.add_argument("--directives", action="store_true",
                        help="pair only guardrails carrying a prohibition")
    parser.add_argument("--wide", action="store_true",
                        help="also report a forbidden phrase with no citation nearby")
    parser.add_argument("--pairs", action="store_true",
                        help="print each guardrail beside its citing sentences (text format)")
    parser.add_argument("--verbose", action="store_true",
                        help="full guardrail text and full sentences")
    parser.add_argument("--self-test", action="store_true",
                        help="only check the rules against built-in fixtures")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    config = load_book(args, TOOL)
    quotes = args.quotes or config.sources.quotes
    if args.quotes and not Path(quotes).exists():
        return tool_failed("quotes bank not found: %s" % quotes, TOOL)
    if skipped_for_missing(TOOL, quotes, "quotes bank", args.format):
        return 0
    if args.manuscript and not Path(args.manuscript).exists():
        return tool_failed("manuscript not found: %s" % args.manuscript, TOOL)

    rows = assess(quotes, manuscript_paths(config, TOOL, args.manuscript),
                  config.manuscript.references)
    if args.key:
        wanted = set(args.key)
        rows = [row for row in rows if row["key"] in wanted]
    files = rows[0]["files"] if rows else {}

    shown = rows
    if args.flagged:
        shown = [row for row in rows if row["flags"] or (args.wide and row["wide"])]
    elif args.unreachable:
        shown = [row for row in rows if row["unreachable"]]
    elif args.directives:
        shown = [row for row in rows if row["directive"] or row["flags"]]

    if args.format == "text" and (args.pairs or args.key or args.directives):
        for row in sorted(shown, key=lambda r: (not r["flags"], r["key"].lower())):
            report(row, files, args.verbose, args.wide)
        print()

    report_out = CheckReport(TOOL, CLASSES)
    for row in rows:
        for rule, detail in row["flags"]:
            report_out.add(row["key"], rule, clip(detail, 240, args.verbose))
        if args.unreachable:
            for rule, detail in row["unreachable"]:
                report_out.add(row["key"], rule, detail)
        if args.wide:
            for rule, detail in row["wide"]:
                report_out.add(row["key"], rule, clip(detail, 240, args.verbose))
    if args.format == "text":
        print("guardrails %d, with a prohibition %d, cited in the book %d, cited nowhere %d"
              % (len(rows), sum(1 for row in rows if row["directive"]),
                 sum(1 for row in rows if row["sites"]),
                 sum(1 for row in rows if row["unreachable"])))
        print("A PAIRING FOR REVIEW, not a verdict: the source outranks the guardrail.\n")
    return report_out.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
