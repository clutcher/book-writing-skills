#!/usr/bin/env python3
"""Join the sources list to the .bib by key, and keep verdicts out of both banks.

Reads files, talks to nothing, writes nothing.

The .bib (sources.bibliography) holds who wrote each source and where it appeared; the
sources list (sources.list) holds how to reach it. Both are keyed by citation key and hold
the same sources, one entry each. A key spelled one character differently in the two files
is not cosmetic: every --only-changed run looks a citation up by key, a miss reads as
"never verified", and the source is fetched and verified again on every run while the
entry holding its access URLs sits unused.

Classes:
  near-miss                  DEFECT  an unmatched key from each file, 0-2 edits apart once
                                     the `+` and the trailing a/b letter are removed:
                                     probably one source under two names (ABC+06 vs ABC06)
  missing-from-list          DEFECT  a .bib entry with no sources list entry
  missing-from-bibliography  DEFECT  a sources list entry with no .bib entry
  --no-verdicts adds, for BOTH banks:
  verdict-field        DEFECT  a field label that IS a verdict (Verdict, Confidence, a bare
                               VERIFIED) or a dated verification claim ("Verified
                               2025-08-08"). Only the label is read, never the value, so
                               access data such as "READABLE (verified by curl, HTTP 200)"
                               is never flagged
  verdict-in-value     ADVISORY run-report vocabulary or a recorded book edit inside a
                               value; move it to the run report or rewrite it as a
                               present-tense guardrail
  misplaced-finding    DEFECT  a quotes-bank field (Key findings, Verified quotes, Role,
                               Scope, Guardrail, Quote origin, Last verified) standing in
                               the sources list. MOVE it, never delete it: it is a durable
                               fact about the source (--merged-bank turns this off for a
                               book that keeps one combined bank)

Near-miss candidates come only from keys that failed to match, compared across the two
files: one author's [Abc14]/[Abc16] or [Abc23a]/[Abc23b] are different sources by design.

Both verdict rules lean toward silence: a false positive sends someone to delete access
data that took a fetch to establish. A flagged entry is split line by line, never
rewritten as a block: access data and guardrails stay; only the dated verdict goes.
`Last verified` is the one permitted date in either bank.

Usage:
  list-bibliography-check.py
  list-bibliography-check.py --no-verdicts
  list-bibliography-check.py --bibliography <refs.bib> --list <list.md> --max-distance 1
  list-bibliography-check.py --self-test
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import add_config_arguments, load_book, tool_failed
from check_output import (ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing)
from bibliography import BibliographyError, read_bibliography
from citation_key import ENTRY_HEADING
from source_registry import is_findings_bank

TOOL = "list-bibliography-check"
CLASSES = {
    "near-miss": DEFECT, "missing-from-list": DEFECT, "missing-from-bibliography": DEFECT,
    "verdict-field": DEFECT, "verdict-in-value": ADVISORY, "misplaced-finding": DEFECT,
}

REGISTRY_HEADING_RE = ENTRY_HEADING

FIELD_LABEL_RE = re.compile(r'^\*\*(.+?)\*\*')
VERIFICATION_CLAIM_RE = re.compile(r'^(verified|verdict|unverified|unverifiable)\b')
DATE_RE = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')

ARCHIVE_FIELD_LABELS = frozenset((
    'verdict', 'last verdict', 'verified', 'confidence',
    'minor issue', 'significant issue', 'unverifiable',
))

EXCERPT_WIDTH = 96


def normalise_key(key):
    stripped = key.replace('+', '')
    stripped = re.sub(r'(?<=\d)[a-z]$', '', stripped)
    return stripped.lower()


def edit_distance(left, right, limit=3):
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        current = [i]
        for j, right_char in enumerate(right, 1):
            current.append(min(previous[j] + 1,
                               current[j - 1] + 1,
                               previous[j - 1] + (left_char != right_char)))
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


def read_keys(path, pattern):
    keys = {}
    fenced = False
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if line.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = pattern.match(line.strip())
        if match and match.group(1) not in keys:
            keys[match.group(1)] = number
    return keys


def bibliography_keys(path):
    return {key: entry.line for key, entry in read_bibliography(path).entries.items()}


def field_label(line):
    match = FIELD_LABEL_RE.match(line)
    if not match:
        return None
    return match.group(1).strip().rstrip(':.').strip()


def is_verdict_label(label):
    normalised = label.lower()
    if normalised in ARCHIVE_FIELD_LABELS:
        return True
    return bool(VERIFICATION_CLAIM_RE.match(normalised) and DATE_RE.search(normalised))


VERDICT_BODY_PATTERNS = (
    (re.compile(r'\b(VERIFIED|UNVERIFIABLE|MINOR ISSUE|SIGNIFICANT ISSUE)\b'),
     'run-report verdict vocabulary'),
    (re.compile(r'\b(fix|correction) applied\b', re.I), 'records a manuscript edit'),
    (re.compile(r'\bcorrection \d{4}-\d{2}-\d{2}\b', re.I), 'dated correction record'),
    (re.compile(r'\bverdict on\b', re.I), 'states a verdict about the book'),
    (re.compile(r'\bthis entry (previously|read)\b.{0,60}\b(was wrong|until)\b', re.I),
     'superseded marker; correct in place instead'),
    (re.compile(r'\b(Ch\s?\d+|S\d+\.\d+)\b[^.]{0,40}\bwording (aligned|changed|updated)\b', re.I),
     'records a manuscript edit'),
    (re.compile(r'\bno manuscript change needed\b', re.I), 'judges the manuscript'),
)


FINDINGS_FIELD_LABELS = frozenset((
    'key findings', 'verified quotes', 'quote origin', 'role', 'scope',
    'guardrail', 'last verified',
))


def find_misplaced_findings(path):
    findings = []
    key = None
    fenced = False
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = REGISTRY_HEADING_RE.match(stripped)
        if heading:
            key = heading.group(1)
            continue
        if key is None:
            continue
        label = field_label(stripped)
        if label and label.lower() in FINDINGS_FIELD_LABELS:
            findings.append((key, number, stripped))
    return findings


def find_verdict_bodies(path):
    findings = []
    key = None
    fenced = False
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('```'):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = REGISTRY_HEADING_RE.match(stripped)
        if heading:
            key = heading.group(1)
            continue
        if stripped.startswith('## '):
            key = '(outside any entry)' if key is not None else None
            continue
        if key is None or not stripped:
            continue
        for pattern, why in VERDICT_BODY_PATTERNS:
            if pattern.search(stripped):
                findings.append((key, number, stripped, why))
                break
    return findings


def find_verdict_content(path):
    findings = []
    key = None
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        stripped = line.strip()
        heading = REGISTRY_HEADING_RE.match(stripped)
        if heading:
            key = heading.group(1)
            continue
        if key is None:
            continue
        label = field_label(stripped)
        if label and is_verdict_label(label):
            findings.append((key, number, stripped))
    return findings


def excerpt(line):
    collapsed = ' '.join(line.split())
    if len(collapsed) <= EXCERPT_WIDTH:
        return collapsed
    return collapsed[:EXCERPT_WIDTH - 3] + '...'


def find_near_misses(bibliography_only, registry_only, max_distance):
    pairs = []
    for bibliography_key in sorted(bibliography_only):
        for registry_key in sorted(registry_only):
            distance = edit_distance(normalise_key(bibliography_key),
                                     normalise_key(registry_key),
                                     limit=max_distance)
            if distance <= max_distance:
                pairs.append((distance, bibliography_key, registry_key))
    return sorted(pairs)


def describe(distance):
    if distance == 0:
        return 'same key once filing marks are removed -- almost certainly one source'
    return 'differs by %d edit%s' % (distance, '' if distance == 1 else 's')


def join(bibliography, listed, max_distance):
    bibliography_only = sorted(set(bibliography) - set(listed))
    list_only = sorted(set(listed) - set(bibliography))
    near = find_near_misses(bibliography_only, list_only, max_distance)
    paired = {key for _, key, _ in near} | {key for _, _, key in near}
    return (near, [k for k in bibliography_only if k not in paired],
            [k for k in list_only if k not in paired],
            sorted(set(bibliography) & set(listed)))


def verdict_items(path, split_banks):
    items = []
    for key, number, line in find_verdict_content(path):
        items.append((key, "verdict-field", "line %d: %s" % (number, excerpt(line))))
    for key, number, line, why in find_verdict_bodies(path):
        items.append((key, "verdict-in-value", "line %d: %s -- %s" % (number, why, excerpt(line))))
    if split_banks:
        for key, number, line in find_misplaced_findings(path):
            items.append((key, "misplaced-finding", "line %d: %s" % (number, excerpt(line))))
    return items


FIXTURE_BIBLIOGRAPHY = """@article{ABC+06,
  author = {Adams, A. and Baker, B. and Clark, C. and Davis, D. and Evans, E.},
  title = {A Paper},
  year = {2006},
}

@book{Smi99,
  author = {Smith, J.},
  title = {A Book},
  year = {1999},
}

@misc{Jon24,
  author = {Jones, K.},
  title = {A Post},
  year = {2024},
}
"""

FIXTURE_LIST = """# Sources List

## Entry format

```
### [<Key>]
**Access URLs:** where it can be read
```

---

### [ABC06]

**Access URLs:** https://example.org/a-paper

---

### [Smi99]

**Access status:** READABLE (verified by curl, HTTP 200)
**Verdict:** VERIFIED
**Key findings:** the book says what the chapter says it says

---

### [Old80]

**Note:** fix applied to the chapter wording

---
"""


def self_test():
    failures = []
    with tempfile.TemporaryDirectory() as root:
        refs = Path(root) / "references.bib"
        listed = Path(root) / "list.md"
        refs.write_text(FIXTURE_BIBLIOGRAPHY, encoding="utf-8")
        listed.write_text(FIXTURE_LIST, encoding="utf-8")
        near, missing, orphans, matched = join(bibliography_keys(refs),
                                               read_keys(listed, REGISTRY_HEADING_RE), 2)
        items = {(key, name) for key, name, _m in verdict_items(listed, True)}
    if [(d, a, b) for d, a, b in near] != [(0, "ABC+06", "ABC06")]:
        failures.append("the '+' near miss was not paired at distance 0: %s" % near)
    if missing != ["Jon24"] or orphans != ["Old80"] or matched != ["Smi99"]:
        failures.append("wrong join: missing %s, orphans %s, matched %s" % (missing, orphans, matched))
    want = {("Smi99", "verdict-field"), ("Smi99", "verdict-in-value"),
            ("Smi99", "misplaced-finding"), ("Old80", "verdict-in-value")}
    if items != want:
        failures.append("verdict items %s, want %s" % (sorted(items), sorted(want)))
    for line in failures:
        print("FAIL %s" % line)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument('--bibliography', help='the .bib file (default: sources.bibliography)')
    parser.add_argument('--list', dest='sources_list', help='the sources list (default: sources.list)')
    parser.add_argument('--quotes', help='the quotes bank (default: sources.quotes)')
    parser.add_argument('--max-distance', type=int, default=2,
                        help='near-miss edit-distance threshold (default 2)')
    parser.add_argument('--no-verdicts', action='store_true',
                        help='also check both banks for verdict content and misplaced findings')
    parser.add_argument('--merged-bank', action='store_true',
                        help='the book keeps one combined bank: no misplaced-finding')
    parser.add_argument('--self-test', action='store_true', help='run the built-in examples')
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    config = load_book(args, TOOL)
    references = args.bibliography or config.sources.bibliography
    sources_list = args.sources_list or config.sources.list
    quotes = args.quotes or config.sources.quotes
    for path, label, given in ((references, 'bibliography', args.bibliography),
                               (sources_list, 'sources list', args.sources_list)):
        if given and not Path(path).exists():
            return tool_failed('no such file: %s' % path, TOOL)
        if skipped_for_missing(TOOL, path, label, args.format):
            return 0

    try:
        bibliography = bibliography_keys(references)
    except (OSError, BibliographyError) as error:
        return tool_failed('cannot read %s: %s' % (references, error), TOOL)
    listed = read_keys(sources_list, REGISTRY_HEADING_RE)
    near, missing, orphans, matched = join(bibliography, listed, args.max_distance)

    report = CheckReport(TOOL, CLASSES)
    for distance, bib_key, list_key in near:
        report.add(bib_key, 'near-miss', '.bib %s line %d <-> list [%s] line %d: %s'
                   % (bib_key, bibliography[bib_key], list_key, listed[list_key], describe(distance)))
    for key in missing:
        report.add(key, 'missing-from-list', '.bib line %d: no sources list entry'
                   % bibliography[key])
    for key in orphans:
        report.add(key, 'missing-from-bibliography', 'list line %d: no .bib entry' % listed[key])
    if args.no_verdicts:
        banks = [(sources_list, not args.merged_bank)]
        if quotes and Path(quotes).exists():
            banks.append((quotes, False))
        for path, may_misplace in banks:
            split = may_misplace and not is_findings_bank(path, config)
            for key, name, message in verdict_items(path, split):
                report.add(key, name, '%s %s' % (Path(path).name, message))
    if args.format == 'text':
        print('.bib entries: %d   List entries: %d   Joined by key: %d\n'
              % (len(bibliography), len(listed), len(matched)))
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
