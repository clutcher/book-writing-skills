#!/usr/bin/env python3
"""Flag checkable claims in the book that have no citation nearby.

A checkable claim ("gardeners spend 70% of their time weeding", "fields were rotated
annually", "X was the first to describe it") is either grounded by a citation or
decorative. This script finds claims by pattern class, then checks whether a citation
key ([Abc99], [ABCD94]) appears within a 5-sentence window: the two sentences before,
the claim's own sentence, and the two after. Unmatched claims are listed for the author.

It is recall-first: expect false positives. It surfaces; it never blocks. An uncited
claim is not automatically a defect: common knowledge, the author's own experience and
conclusions argued from earlier material are all legitimate. The failure it prevents is
a checkable assertion nobody ever decided about.

Classes (all ADVISORY, reported as uncited-<class>):
  numeric    digits + unit: "70%", "5x", "3 kg", "20 years", "40 miles"
  spelled    the same written out: "seventy percent", "fifteen times", "tenfold". A
             style that spells numbers under a hundred moves most real quantitative
             claims out of digit range; without this class they are invisible. It
             uses measurement units only (not "four steps"), because a book
             counting its own example is not a claim
  magnitude  half, double, triple, dozens, hundreds, thousands, millions, billions
             ("hundreds of visitors" is rhetorical and skipped; vague words like
             "most" and "many" are left out on purpose)
  delta      "increase by 30%", "reduced 10x", "grew 200 acres"
  temporal   cadence and duration: "updated annually", "once a year", "every two
             weeks", "for decades". These assert common practice and carry no digit
  date       a bare year or decade pinning an event: "in 1989", "the 1970s"
  priority   "was the first to", "pioneered by", "coined by", "predates": earlier
             work usually exists
  consensus  "studies show", "widely accepted", "experts agree": the likeliest to
             overstate the evidence

Not flagged: cross-references (Chapter 5, Section 6.1, Figure 3, Part III, Step 4),
code fences, table rows, and bibliography lines.

Known gaps: the second half of a hyphenated percentage range (40-90%) is not detected;
temporal skips a cadence adverb after a modal or advice verb ("apply daily"), so a
descriptive claim phrased that way is skipped too; "the first <noun>" is skipped when
the noun names something inside the book (terms.watch_words.internal_first_nouns adds
the book's own nouns to the built-in list).

Usage:
  uncited-claim-check.py                    the manuscript files the config lists
  uncited-claim-check.py <file-or-folder>
  uncited-claim-check.py --only temporal,priority
  uncited-claim-check.py --exclude spelled
  uncited-claim-check.py --classes
  uncited-claim-check.py --self-test
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (add_config_arguments, load_book, manuscript_paths, shown_path,
                          tool_failed)
from check_output import ADVISORY, CheckReport, add_output_arguments
from citation_key import BIB_ENTRY

TOOL = "uncited-claim-check"

UNIT_WORDS = [
    "percent", "per cent", "pct", "%",
    "x", "fold", "times",
    "ms", "millisecond", "milliseconds",
    "microsecond", "microseconds",
    "ns", "nanosecond", "nanoseconds",
    "sec", "second", "seconds", "min", "minute", "minutes",
    "hr", "hour", "hours", "day", "days", "week", "weeks",
    "month", "months", "year", "years",
    "byte", "bytes", "KB", "MB", "GB", "TB",
    "hz", "khz", "mhz", "ghz",
    "line", "lines", "cycle", "cycles",
    "op", "ops", "operation", "operations",
    "request", "requests", "query", "queries",
    "kg", "kilogram", "kilograms", "gram", "grams",
    "pound", "pounds", "lb", "lbs",
    "km", "kilometre", "kilometres", "kilometer", "kilometers",
    "metre", "metres", "meter", "meters",
    "mile", "miles", "acre", "acres", "hectare", "hectares",
    "litre", "litres", "liter", "liters", "calorie", "calories", "kcal",
    "dollar", "dollars", "euro", "euros",
    "person", "people", "patient", "patients",
]

MAGNITUDE_WORDS = [
    "half", "double", "triple", "quadruple",
    "dozens", "hundreds", "thousands", "millions", "billions",
]

MEASUREMENT_UNITS = {
    "percent", "per cent", "%", "pct",
    "x", "fold", "times",
    "ms", "millisecond", "milliseconds",
    "us", "microsecond", "microseconds",
    "ns", "nanosecond", "nanoseconds",
    "s", "sec", "second", "seconds",
    "min", "minute", "minutes",
    "hr", "hour", "hours",
    "day", "days", "week", "weeks",
    "month", "months", "year", "years",
    "byte", "bytes", "kb", "mb", "gb", "tb",
    "hz", "khz", "mhz", "ghz",
    "cycle", "cycles",
    "kg", "kilogram", "kilograms", "gram", "grams",
    "pound", "pounds", "lb", "lbs",
    "km", "kilometre", "kilometres", "kilometer", "kilometers",
    "metre", "metres", "meter", "meters",
    "mile", "miles", "acre", "acres", "hectare", "hectares",
    "litre", "litres", "liter", "liters", "calorie", "calories", "kcal",
}

DELTA_VERBS = [
    "increase", "decrease", "improve", "reduce", "grow", "shrink",
    "increases", "decreases", "improves", "reduces", "grows", "shrinks",
    "increased", "decreased", "improved", "reduced", "grew", "shrank",
]

NUMBER_WORDS_TEENS = [
    "seventeen", "thirteen", "fourteen", "fifteen", "sixteen",
    "eighteen", "nineteen", "eleven", "twelve",
]
NUMBER_WORDS_TENS = [
    "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety",
]
NUMBER_WORDS_ONES = [
    "seven", "three", "eight", "four", "five", "nine", "six", "ten",
    "two", "one",
]
NUMBER_WORDS_SCALE = ["hundred", "thousand", "million", "billion", "trillion"]

_TENS_COMPOUND = (
    r"(?:" + "|".join(NUMBER_WORDS_TENS) + r")"
    r"(?:[-\s](?:" + "|".join(NUMBER_WORDS_ONES) + r"))?"
)
_NUMBER_WORD = (
    r"(?:" + _TENS_COMPOUND
    + r"|" + "|".join(NUMBER_WORDS_TEENS)
    + r"|" + "|".join(NUMBER_WORDS_SCALE)
    + r"|" + "|".join(NUMBER_WORDS_ONES)
    + r")"
)

CADENCE_ADVERBS = [
    "hourly", "daily", "nightly", "weekly", "biweekly", "fortnightly",
    "monthly", "bimonthly", "quarterly", "semiannually", "annually", "yearly",
]

_PERIOD_NOUN = r"(?:day|week|fortnight|month|quarter|year|decade|century)s?"

TEMPORAL_PHRASE_PATTERNS = [
    rf"\b(?:once|twice|thrice|\d+\s+times|{_NUMBER_WORD}\s+times)\s+"
    rf"(?:a|an|per|each|every)\s+{_PERIOD_NOUN}\b",
    rf"\bevery\s+(?:\d+|{_NUMBER_WORD}|other\s+)?\s*{_PERIOD_NOUN}\b",
    rf"\bfor\s+(?:over\s+|nearly\s+|almost\s+|the\s+past\s+)?"
    rf"(?:\d+\s+|{_NUMBER_WORD}\s+)?{_PERIOD_NOUN}\b",
    rf"\bon\s+an?\s+(?:\d+[-\s])?{_PERIOD_NOUN}\s+(?:cycle|cadence|schedule)\b",
]

PRESCRIPTIVE_MARKERS = [
    "should", "must", "ought", "can", "could", "may", "might", "will",
    "apply", "applies", "applying", "use", "uses", "using", "practice",
    "practise", "try", "aim", "want", "need", "start", "keep", "make",
]

PRIORITY_PATTERNS = [
    r"\b(?:was|were|is|are)\s+the\s+first\b",
    r"\bthe\s+first\s+(?:person|paper|book|language|system|company|team|"
    r"author|machine|device|product|conference|to)\b",
    r"\bfirst\s+(?:introduced|formalized|formalised|described|proposed|"
    r"published|coined|defined|identified|documented|implemented|named)\b",
    r"\b(?:pioneered|invented|coined|devised|formulated|originated)\b",
    r"\bcredited\s+(?:by|with|as)\b",
    r"\borigin(?:ated|ates)\s+(?:with|in|from)\b",
    r"\bpredates?\b",
    r"\bearliest\s+(?:known|recorded|use|example|reference)\b",
]

CONSENSUS_PATTERNS = [
    r"\b(?:studies|research|researchers|evidence|data|experiments)\s+"
    r"(?:show|shows|showed|indicate|indicates|indicated|suggest|suggests|"
    r"suggested|found|find|confirm|confirms|confirmed|demonstrate|"
    r"demonstrates|demonstrated|prove|proves|proved)\b",
    r"\bwidely\s+(?:accepted|regarded|believed|considered|recognized|"
    r"recognised|understood|used|adopted)\b",
    r"\b(?:experts|practitioners|academics|the\s+industry|the\s+community)\s+"
    r"(?:agree|agrees|agreed|recognize|recognizes|recognized|concluded|"
    r"realized|realised)\b",
    r"\bconsensus\b",
    r"\bit\s+is\s+(?:generally|commonly|widely)\s+"
    r"(?:agreed|accepted|understood|known|held)\b",
    r"\bevery(?:one|body)\s+(?:agrees|knows)\b",
]

NUMERIC_UNIT_PATTERN = re.compile(
    r"(?<![\w.+\-\^,])"
    r"(\d+(?:,\d{3})*(?:\.\d+)?)"
    r"[-\s]?"
    r"(" + "|".join(re.escape(u) for u in UNIT_WORDS) + r")"
    r"(?!\w)",
    re.IGNORECASE,
)

SPELLED_UNIT_PATTERN = re.compile(
    r"\b(" + _NUMBER_WORD + r")"
    r"[-\s]"
    r"(" + "|".join(re.escape(u) for u in sorted(MEASUREMENT_UNITS, key=len, reverse=True)) + r")"
    r"(?!\w)",
    re.IGNORECASE,
)

MAGNITUDE_PATTERN = re.compile(
    r"\b(" + "|".join(MAGNITUDE_WORDS) + r")\b",
    re.IGNORECASE,
)

DELTA_PATTERN = re.compile(
    r"\b(" + "|".join(DELTA_VERBS) + r")\s+(?:by\s+)?(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

CLOSED_COMPOUND_PATTERN = re.compile(
    r"\b(" + _NUMBER_WORD + r")-?fold\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"(?<![\w.\-/])"
    r"(?:1[5-9]\d{2}|20[0-4]\d)"
    r"(?:s\b|(?![\w.\-/%]))"
)

CADENCE_ADVERB_PATTERN = re.compile(
    r"\b(" + "|".join(CADENCE_ADVERBS) + r")\b",
    re.IGNORECASE,
)

TEMPORAL_PHRASE_PATTERN = re.compile(
    "|".join(f"(?:{p})" for p in TEMPORAL_PHRASE_PATTERNS),
    re.IGNORECASE,
)

PRIORITY_PATTERN = re.compile(
    "|".join(f"(?:{p})" for p in PRIORITY_PATTERNS),
    re.IGNORECASE,
)

CONSENSUS_PATTERN = re.compile(
    "|".join(f"(?:{p})" for p in CONSENSUS_PATTERNS),
    re.IGNORECASE,
)

PRESCRIPTIVE_PATTERN = re.compile(
    r"\b(" + "|".join(PRESCRIPTIVE_MARKERS) + r")\b",
    re.IGNORECASE,
)

_CITATION_KEY = r"[A-Za-z\+]+\d{2,4}[a-z]?"
CITATION_PATTERN = re.compile(
    rf"\[(?:{_CITATION_KEY})(?:\s*,\s*(?:{_CITATION_KEY}))*\]"
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")

CROSS_REF_PREFIXES = [
    "chapter", "chapters", "section", "sections",
    "figure", "figures", "table", "tables",
    "part", "parts", "appendix", "step", "steps",
    "rule", "rules", "item", "items",
    "footnote", "footnotes",
]

CROSS_REF_PATTERN = re.compile(
    r"\b(" + "|".join(CROSS_REF_PREFIXES) + r")\s+$",
    re.IGNORECASE,
)

INTERNAL_FIRST_NOUNS = ("chapter", "section", "part", "step", "question", "example",
                        "rule", "reason", "point", "half", "time", "two", "three",
                        "four", "five")


def internal_nouns_pattern(extra=()):
    words = sorted(set(INTERNAL_FIRST_NOUNS) | {str(word).lower() for word in extra})
    return re.compile(r"^\s*(?:" + "|".join(map(re.escape, words)) + r"|of\b)", re.IGNORECASE)


PRIORITY_INTERNAL_NOUNS = internal_nouns_pattern()

CONTEXT_SNIPPET_LEN = 140

CLASS_NAMES = [
    "numeric", "spelled", "magnitude", "delta",
    "temporal", "date", "priority", "consensus",
]
CLASSES = {"uncited-" + name: ADVISORY for name in CLASS_NAMES}


def strip_code_and_tables(text):
    out = []
    in_code = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            out.append("")
            continue
        if in_code:
            out.append("")
            continue
        if stripped.startswith("|"):
            out.append("")
            continue
        if BIB_ENTRY.match(stripped):
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def split_paragraphs(text):
    paragraphs = []
    buf = []
    buf_start = 0
    for i, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            if buf:
                paragraphs.append((buf_start, "\n".join(buf)))
                buf = []
            continue
        if line.startswith("#"):
            if buf:
                paragraphs.append((buf_start, "\n".join(buf)))
                buf = []
            continue
        if not buf:
            buf_start = i
        buf.append(line)
    if buf:
        paragraphs.append((buf_start, "\n".join(buf)))
    return paragraphs


def split_sentences(text):
    sentences = []
    start = 0
    for m in SENTENCE_SPLIT.finditer(text):
        sentences.append((start, text[start: m.start() + 1].strip()))
        start = m.end()
    tail = text[start:].strip()
    if tail:
        sentences.append((start, tail))
    return sentences


def is_cross_reference(text, match_start):
    head = text[:match_start]
    return bool(CROSS_REF_PATTERN.search(head))


def find_citation_window(sentences, claim_index):
    start = max(0, claim_index - 2)
    end = claim_index + 3
    window = sentences[start: end]
    combined = " ".join(s for _, s in window)
    m = CITATION_PATTERN.search(combined)
    return m.group(0) if m else None


def is_rhetorical_magnitude(sentence, match_end):
    tail = sentence[match_end:].lstrip()
    m = re.match(r"^of\s+(\S+)", tail, re.IGNORECASE)
    if not m:
        return False
    next_word = m.group(1).lower().rstrip(",.;:!?)")
    return next_word not in MEASUREMENT_UNITS


def is_prescriptive_cadence(sentence, match_start):
    head = sentence[:match_start]
    return bool(PRESCRIPTIVE_PATTERN.search(head))


def is_internal_first(sentence, match_start, match_text):
    if "first" not in match_text.lower():
        return False
    tail = sentence[match_start + len(match_text):]
    return bool(PRIORITY_INTERNAL_NOUNS.match(tail))


def snippet(text, limit=CONTEXT_SNIPPET_LEN):
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def class_patterns(active):
    registry = {
        "numeric": NUMERIC_UNIT_PATTERN,
        "magnitude": MAGNITUDE_PATTERN,
        "delta": DELTA_PATTERN,
        "date": DATE_PATTERN,
        "priority": PRIORITY_PATTERN,
        "consensus": CONSENSUS_PATTERN,
    }
    pairs = []
    for name in CLASS_NAMES:
        if name not in active:
            continue
        if name == "spelled":
            pairs.append(("spelled", SPELLED_UNIT_PATTERN))
            pairs.append(("spelled", CLOSED_COMPOUND_PATTERN))
        elif name == "temporal":
            pairs.append(("temporal", CADENCE_ADVERB_PATTERN))
            pairs.append(("temporal", TEMPORAL_PHRASE_PATTERN))
        else:
            pairs.append((name, registry[name]))
    return pairs


def is_suppressed(label, pattern, sentence, match):
    if label in ("numeric", "spelled", "delta"):
        return is_cross_reference(sentence, match.start())
    if label == "magnitude":
        return is_rhetorical_magnitude(sentence, match.end())
    if label == "temporal" and pattern is CADENCE_ADVERB_PATTERN:
        return is_prescriptive_cadence(sentence, match.start())
    if label == "priority":
        return is_internal_first(sentence, match.start(), match.group(0))
    return False


def find_claims_in_paragraph(para_start, paragraph, active):
    sentences = split_sentences(paragraph)
    if not sentences:
        return []

    claims = []
    for si, (sent_offset, sentence) in enumerate(sentences):
        seen_spans = set()
        for label, pattern in class_patterns(active):
            for m in pattern.finditer(sentence):
                if is_suppressed(label, pattern, sentence, m):
                    continue
                span = (label, m.start(), m.end())
                if span in seen_spans:
                    continue
                seen_spans.add(span)
                abs_offset = sent_offset + m.start()
                line_no = para_start + paragraph[:abs_offset].count("\n")
                cited_by = find_citation_window(sentences, si)
                claims.append(
                    {
                        "line": line_no,
                        "kind": label,
                        "match": m.group(0),
                        "sentence": sentence,
                        "cited_by": cited_by,
                    }
                )
    return claims


def find_claims(path, active):
    raw = path.read_text(encoding="utf-8")
    scrubbed = strip_code_and_tables(raw)
    claims = []
    for para_start, paragraph in split_paragraphs(scrubbed):
        for claim in find_claims_in_paragraph(para_start, paragraph, active):
            claim["file"] = str(path)
            claims.append(claim)
    return claims


def class_list(value):
    names = [n.strip().lower() for n in value.split(",") if n.strip()]
    unknown = [n for n in names if n not in CLASS_NAMES]
    if unknown:
        raise argparse.ArgumentTypeError(
            "unknown class %s; known: %s" % (", ".join(unknown), ", ".join(CLASS_NAMES)))
    return names


FIXTURE_CHAPTER = """# Chapter 1

Gardeners spend 70% of their time weeding. Nothing else here is cited.

Farmers used to rotate their fields annually, and yields grew slower for decades.

Seventy percent of the rain runs off bare soil before it soaks in.

Studies show that mulch helps, and one author was the first to describe it.

The harvest doubled when the beds were split [Smi99]. Water use fell by 30 percent.

As Chapter 5 shows, Section 6.1 has 12 examples. You should water the beds daily.

| Year | Value |
|------|-------|
| 1999 | 70% |

```
watering_minutes = 150  # 150 minutes
```

[Smi99] Smith, J. (1999). A study of 70% of gardens.
"""

FIXTURE_EXPECTED = {
    (3, "numeric"), (5, "temporal"), (7, "spelled"), (9, "consensus"), (9, "priority"),
}

SPELLED_UNITS_CHAPTER = """# Chapter 2

The card holds a twenty-line recipe for thirty people and five requests.

The full sack weighed seventy kilograms.

The card holds a 20-line recipe.
"""

SPELLED_UNITS_EXPECTED = {(5, "spelled"), (7, "numeric")}


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "110-chapter-1.md"
        path.write_text(FIXTURE_CHAPTER, encoding="utf-8")
        claims = find_claims(path, set(CLASS_NAMES))
        units_path = Path(root) / "120-chapter-2.md"
        units_path.write_text(SPELLED_UNITS_CHAPTER, encoding="utf-8")
        unit_claims = {(claim["line"], claim["kind"])
                       for claim in find_claims(units_path, {"numeric", "spelled"})}
    if unit_claims != SPELLED_UNITS_EXPECTED:
        failures.append("spelled counts of lines, people or requests must not be claims; "
                        "spelled measures and digit units must: got %s" % sorted(unit_claims))
    uncited = {(claim["line"], claim["kind"]) for claim in claims if not claim["cited_by"]}
    cited = {(claim["line"], claim["kind"]) for claim in claims if claim["cited_by"]}
    for item in sorted(FIXTURE_EXPECTED - uncited):
        failures.append("NOT REPORTED line %d %s" % item)
    unexpected = {item for item in uncited - FIXTURE_EXPECTED if item[0] != 5}
    for item in sorted(unexpected):
        failures.append("FALSE POSITIVE line %d %s" % item)
    if not any(line == 11 for line, _kind in cited):
        failures.append("a claim beside a citation was not counted as cited")
    if any(line >= 15 for line, _kind in uncited | cited):
        failures.append("a table row, code fence or bibliography line was read")
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def book_files(config, explicit_paths):
    if not explicit_paths:
        return manuscript_paths(config, TOOL)
    return [found for path in explicit_paths for found in manuscript_paths(config, TOOL, path)]


def main():
    global PRIORITY_INTERNAL_NOUNS
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("paths", nargs="*", help="files or folders (default: the book's manuscript files)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--only", type=class_list, help="comma-separated classes to run")
    group.add_argument("--exclude", type=class_list, help="comma-separated classes to skip")
    parser.add_argument("--classes", action="store_true", help="list the class names")
    parser.add_argument("--verbose", action="store_true", help="show the matched words too")
    parser.add_argument("--self-test", action="store_true", help="run the built-in examples")
    args = parser.parse_args()

    if args.classes:
        print("\n".join(CLASS_NAMES))
        return 0
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    extra = (config.terms.watch_words or {}).get("internal_first_nouns") or []
    PRIORITY_INTERNAL_NOUNS = internal_nouns_pattern(extra if isinstance(extra, list) else [extra])
    for path in args.paths:
        if not Path(path).exists():
            return tool_failed("not found: %s" % path, TOOL)
    active = set(args.only) if args.only else set(CLASS_NAMES) - set(args.exclude or [])

    report = CheckReport(TOOL, CLASSES)
    files = book_files(config, args.paths)
    if not files:
        report.skip("no manuscript files at %s"
                    % (", ".join(args.paths) or config.manuscript.dir))
        return report.emit(args.format)
    total = 0
    for path in files:
        claims = find_claims(path, active)
        total += len(claims)
        for claim in claims:
            if claim["cited_by"]:
                continue
            message = '"%s"' % snippet(claim["sentence"])
            if args.verbose:
                message = 'match "%s": %s' % (claim["match"], message)
            where = "%s:%d" % (shown_path(config.root, claim["file"]), claim["line"])
            report.add(where, "uncited-" + claim["kind"], message)
    if args.format == "text":
        print("%d file(s), %d claim(s) found; the uncited ones follow. Expect false positives:\n"
              "add a citation, soften the claim, or confirm it is common knowledge.\n"
              % (len(files), total))
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
