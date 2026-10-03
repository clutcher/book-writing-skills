#!/usr/bin/env python3
"""Find thinking files that still point INTO the book, and quotations of the book that went stale.

It reads every markdown file in the book's thinking folder (`thinking.dir`, all subfolders:
the argument, the doubts and the author files), or, in a layout with no thinking folder, the
stance, audience, argument and doubts places the config names. `--argument <folder>` reads
only that folder.

An argument file (any file of the thinking folder) must hold what the
LITERATURE says, never what the book currently says about it. A verdict about the book
expires the moment a sentence is rewritten, and an argument file has no expiry date:
nothing announces when the two separate, so a later review reads the old verdict,
believes it, and raises a finding against a sentence that is fine. A dated verdict
about the book belongs in a run report under the work folder, whose name carries the
date. Never pin a verdict to a bare line number of the book.

It reports and never fixes: the repair for a stale verdict is usually to delete a
paragraph, and no script should delete an argument file's text.

Two questions:

1. Does an argument file point INTO the book?
     manuscript-path      ADVISORY  a `<manuscript folder>/<name>.md` path, or a bare
                                    file name that is a manuscript file or a chapter
                                    by the config's `manuscript.chapter_pattern`
     line-anchor          DEFECT    `ch4:212`, `<manuscript file>:212`: line numbers
                                    drift on every edit; move it to a run report
     section-pointer      ADVISORY  a CHAPTER-QUALIFIED section (`Ch4 §4.5`); a bare
                                    `Section 9.13` is the argument file's own structure;
                                    a list of chapters (`Ch1, Ch2`) qualifies no section,
                                    and `pre-§3.3` names a place, not a section
     manuscript-verdict   ADVISORY  "the book says" / "the chapter reads" with no
                                    quotable span: it reports current wording, which
                                    expires
     guardrail-verdict    INFORMATIONAL a MODAL or negated statement ("what the book
                                    may say"): a standing constraint, not a verdict

2. Where an argument file QUOTES the book, does the wording still exist?
     graded-quote         DEFECT    a quotation of the book that still matches: the
                                    exposure that becomes the next stale verdict;
                                    move it to a run report
     stale-quote          DEFECT    the wording is GONE from the book
     stale-manuscript-path / stale-line-anchor / stale-section-pointer   DEFECT
                                    the file, line or numbered section does not exist

A quoted span counts as a quotation OF THE BOOK only when an attribution cue ("the book
says", a `ch4:212` anchor) sits in its own sentence or in a lead-in sentence ending in a
colon or dash; argument files are full of quotations of SOURCES. Quoted spans are masked
before the cue search. Two markers cancel the attribution:
     historical-quote     INFORMATIONAL "used to read", "was rewritten": a record of
                                    retired wording
     disclaimed-quote     INFORMATIONAL quoted to say the book does NOT carry it
A `<manuscript>/` path on a line that also names a `.py` script is a live command
(live-invocation, INFORMATIONAL). The unit is the paragraph, because argument files hard-wrap.

Argument files whose subject IS the book's own structure are listed in the book's config
as `terms.watch_words.notes_about_the_book` (paths from the book root). For them the
pointer and verdict rules become `exempt`; stale-quote and line-anchor still apply.

The manuscript is the set of files the config lists (`manuscript.order`, `manuscript.files`),
so any folder and file names work. Chapter numbers come from `manuscript.chapter_pattern`.

Usage:
  stale-argument-pointer-check.py                   the whole thinking folder (thinking.dir)
  stale-argument-pointer-check.py --argument <folder>   only this folder
  stale-argument-pointer-check.py --file <path>
  stale-argument-pointer-check.py --self-test
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from source_files import (add_config_arguments, load_book, manuscript_paths,
                          markdown_files_under, shown_path, thinking_paths, tool_failed,
                          visible_markdown_files_under)
from check_output import ADVISORY, DEFECT, INFORMATIONAL, CheckReport, add_output_arguments

TOOL = "stale-argument-pointer-check"
CLASSES = {
    "stale-quote": DEFECT, "stale-line-anchor": DEFECT, "stale-manuscript-path": DEFECT,
    "stale-section-pointer": DEFECT, "line-anchor": DEFECT, "graded-quote": DEFECT,
    "manuscript-verdict": ADVISORY, "manuscript-path": ADVISORY, "section-pointer": ADVISORY,
    "historical-quote": INFORMATIONAL, "disclaimed-quote": INFORMATIONAL,
    "guardrail-verdict": INFORMATIONAL, "live-invocation": INFORMATIONAL,
    "exempt": INFORMATIONAL,
}
EXEMPT_RULES = frozenset({"manuscript-path", "stale-manuscript-path", "section-pointer",
                          "stale-section-pointer", "manuscript-verdict", "graded-quote"})
EXEMPT_REASON = ("the file's subject is the book's own structure, so a pointer here is "
                 "content; stale-quote and line-anchor still apply")

FENCE = re.compile(r"^\s*```")
QUOTED = re.compile(r'"([^"\n]{10,400})"|“([^”\n]{10,400})”')
FILE_NAME = r"[\w.-]+\.md"
CHAPTER_SHORT_NAME = re.compile(r"^ch(?:apter)?-?(\d{1,2})\.md$")
CHAPTER_SHORT_ANCHOR = re.compile(r"\bch(\d{1,2}):(\d{1,5})\b")
CHAPTER_MENTION = r"\b(?:Ch|Chapter)\.?\s*\d"
SECTION_POINTER = re.compile(
    r"\b(?:Ch|Chapter)\.?\s*(\d{1,2})\b(?:(?!%s)[^.\n]){0,24}?"
    r"(?<!\w-)(?:§|\bS(?=\d)|\bSection\s+)\s*(\d{1,2}\.\d{1,2})" % CHAPTER_MENTION)
SCRIPT_ON_LINE = re.compile(r"[\w./-]+\.py\b")

_SUBJECT = r"(?:manuscript|book|chapter|draft)"
_DETERMINER = r"\b(?:a|an|the|its|his|her|their|this|that|these|those|no|any|some|every|one|another)\b"
_VERB = (r"(?:says?|said|claims?|claimed|reads?|states?|stated"
         r"|asserts?|asserted|writes?|wrote)")
CUE = re.compile(
    (r"\bthe\s+{s}\s+(?:(?!{d})\w+\s+){{0,2}}?{v}\b"
     r"|\bthe\s+(?:current|present|existing)\s+(?:wording|sentence|text|phrasing|draft)\b"
     r"|\bmanuscript\s+(?:sentence|wording|text)\b"
     r"|\bin\s+the\s+{s}\s*,?\s*(?:the\s+)?(?:sentence|wording|passage)\b"
     ).format(s=_SUBJECT, v=_VERB, d=_DETERMINER),
    re.I)

HISTORICAL = re.compile(
    r"\bused\s+to\s+(?:read|say|be|end|carry|contain|refer)\b"
    r"|\bpreviously\s+(?:read|said|claimed|carried|contained|ended)\b"
    r"|\b(?:sentence|paragraph|section|line|wording|phrasing)\s+above\s+(?:read|said|ended)\b"
    r"|\bno\s+longer\s+(?:says|reads|carries|contains|appears|holds)\b"
    r"|\bhas\s+been\s+(?:rewritten|replaced|changed|retired|removed|dropped)\b"
    r"|\bwas\s+(?:rewritten|replaced|retired|removed|dropped|superseded)\b"
    r"|\bsuperseded\b|\bretired\b|\bformerly\b|\bstale\b"
    r"|\boriginally\s+(?:read|said|claimed|ended)\b"
    r"|\bcorrection\b|\bthis\s+file\s+used\s+to\b",
    re.I)

NEGATED = re.compile(
    r"\bthe\s+(?:manuscript|book|chapter|draft)\s+(?:\w+\s+){0,2}?"
    r"(?:does\s+not|do\s+not|did\s+not|never|must\s+not|cannot|can't|is\s+not|are\s+not"
    r"|has\s+no|have\s+no|asserts?\s+n(?:o|one)|makes?\s+no|claims?\s+no)\b"
    r"|\bnever\s+(?:write|writes|state|states|say|says|claim|claims)\b"
    r"|\bis\s+not\s+a\s+(?:law|rule|claim)\b",
    re.I)

MODAL = re.compile(r"\b(?:may|must|cannot|can't|can|should|would|shall|licen[sc]es?|"
                   r"entitled|permitted|allowed|safely)\b", re.I)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?;:])\s+")
MIN_WORDS = 5
MIN_CHARS = 25

def normalise(text):
    text = (text.replace("“", '"').replace("”", '"')
                .replace("‘", "'").replace("’", "'")
                .replace("—", "-").replace("–", "-"))
    text = re.sub(r"\[([^\]\n]*)\]\([^)\n]*\)", r"\1", text)
    text = re.sub(r"[*_`~]+", "", text)
    text = re.sub(r"[^0-9A-Za-z]+", " ", text.lower())
    return text.strip()


class BookFiles:
    def __init__(self, folder_name, files, chapter_pattern):
        self.folder_name = folder_name
        self.chapter_pattern = re.compile(chapter_pattern)
        self.lines_by_name = {}
        self.chapters = {}
        texts = []
        for path, chapter in files:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            texts.append(text)
            lines = text.splitlines()
            self.lines_by_name[Path(path).name] = len(lines)
            if chapter is not None:
                self.chapters[chapter] = {"lines": len(lines), "sections": numbered_sections(lines)}
        self.text = normalise("\n".join(texts))
        self.path_pattern = self._path_pattern()
        self.anchor_pattern = self._anchor_pattern()

    def _path_pattern(self):
        folder = re.escape(self.folder_name)
        return re.compile(r"\b%s/(%s)\b" % (folder, FILE_NAME)
                          + r"|(?<![\w/.-])(%s)\b" % FILE_NAME
                          + r"|(?<![\w/])(%s/)(?![\w.-]*\.md)" % folder)

    def _anchor_pattern(self):
        folder = re.escape(self.folder_name)
        return re.compile(r"(?:\b(%s/)|(?<![\w/.-]))(%s):(\d{1,5})\b" % (folder, FILE_NAME))

    def is_known_file(self, name):
        return name in self.lines_by_name

    def is_chapter_name(self, name):
        return bool(self.chapter_pattern.search(name))

    def is_manuscript_name(self, name):
        return (self.is_known_file(name) or self.is_chapter_name(name)
                or bool(CHAPTER_SHORT_NAME.match(name)))

    def paths(self, text):
        for match in self.path_pattern.finditer(text):
            folder_name, bare_name = match.group(1), match.group(2)
            if bare_name and not self.is_manuscript_name(bare_name):
                continue
            yield match, folder_name or bare_name

    def anchors(self, text):
        for match in self.anchor_pattern.finditer(text):
            with_folder, name, line = match.group(1), match.group(2), int(match.group(3))
            if not (with_folder or self.is_manuscript_name(name)):
                continue
            yield match, name, line, self.lines_of(name)
        for match in CHAPTER_SHORT_ANCHOR.finditer(text):
            number = int(match.group(1))
            yield match, "chapter %d" % number, int(match.group(2)), self.chapter_lines(number)

    def has_anchor(self, text):
        return any(True for _ in self.anchors(text))

    def lines_of(self, name):
        if name in self.lines_by_name:
            return self.lines_by_name[name]
        short = CHAPTER_SHORT_NAME.match(name)
        return self.chapter_lines(int(short.group(1))) if short else None

    def chapter_lines(self, number):
        chapter = self.chapters.get(number)
        return chapter["lines"] if chapter else None


def numbered_sections(lines):
    sections = set()
    for line in lines:
        found = re.match(r"^#{2,3}\s+(\d{1,2}\.\d{1,2})\b", line)
        if found:
            sections.add(found.group(1))
    return sections


def quote_segments(raw):
    pieces = re.split(r"\s*(?:\.\.\.|…|\[\s*\.\.\.\s*\])\s*", raw)
    return [normalise(piece) for piece in pieces]


def checkable(segment):
    return len(segment) >= MIN_CHARS and len(segment.split()) >= MIN_WORDS


def strip_fences(text):
    out, inside = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return out


def paragraphs(lines):
    blocks, current, starts = [], [], []
    number = 0
    for index, line in enumerate(lines, start=1):
        if line.strip():
            if not current:
                number = index
            starts.append((sum(len(part) + 1 for part in current), index))
            current.append(line)
        elif current:
            blocks.append((number, " ".join(current), starts))
            current, starts = [], []
    if current:
        blocks.append((number, " ".join(current), starts))
    return blocks


def line_at(starts, position):
    found = starts[0][1]
    for offset, number in starts:
        if offset <= position:
            found = number
        else:
            break
    return found


def split_sentences(line):
    masked = list(line)
    for match in QUOTED.finditer(line):
        for index in range(match.start(), match.end()):
            masked[index] = " "
    masked = "".join(masked)
    spans, start = [], 0
    for part in SENTENCE_SPLIT.split(masked):
        end = start + len(part)
        spans.append((start, end, masked[start:end]))
        start = end + 1
    return spans


def _finding(rule, path, lineno, text, detail=""):
    return {"rule": rule, "path": path, "line": lineno, "text": text, "detail": detail}


def assess(paths, book, root, exempt_files=()):
    exempt_paths = {Path(item).as_posix() for item in exempt_files}
    findings = []

    for path in paths:
        rel = shown_path(root, path)
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = strip_fences(handle.read())

        for _first, line, starts in paragraphs(lines):
            has_script = bool(SCRIPT_ON_LINE.search(line))

            for match, name in book.paths(line):
                if has_script:
                    findings.append(_finding("live-invocation", rel, line_at(starts, match.start()), match.group(0),
                                             "a `.py` invocation in the same paragraph"))
                    continue
                intact = name is None or book.is_known_file(name)
                rule = "manuscript-path" if intact else "stale-manuscript-path"
                findings.append(_finding(rule, rel, line_at(starts, match.start()), match.group(0),
                                         "" if intact else "no such file in the manuscript"))

            for match, target, anchor, line_count in book.anchors(line):
                if line_count is None:
                    findings.append(_finding("stale-line-anchor", rel, line_at(starts, match.start()), match.group(0),
                                             "no %s in the manuscript" % target))
                elif anchor > line_count:
                    findings.append(_finding("stale-line-anchor", rel, line_at(starts, match.start()), match.group(0),
                                             "%s has %d lines" % (target, line_count)))
                else:
                    findings.append(_finding("line-anchor", rel, line_at(starts, match.start()), match.group(0),
                                             "line numbers drift on every edit"))

            for match in SECTION_POINTER.finditer(line):
                number, section = int(match.group(1)), match.group(2)
                chapter = book.chapters.get(number)
                if chapter is None or section not in chapter["sections"]:
                    findings.append(_finding("stale-section-pointer", rel, line_at(starts, match.start()), match.group(0),
                                             "chapter %d declares no section %s" % (number, section)))
                else:
                    findings.append(_finding("section-pointer", rel, line_at(starts, match.start()), match.group(0)))

            spans = split_sentences(line)
            cues = [bool(CUE.search(text)) for _s, _e, text in spans]
            anchors = [book.has_anchor(text) for _s, _e, text in spans]
            historical = [bool(HISTORICAL.search(text)) for _s, _e, text in spans]
            negated = [bool(NEGATED.search(text)) for _s, _e, text in spans]
            leadin = [text.rstrip().endswith((":", "--", "—")) for _s, _e, text in spans]
            quoted_here = False

            for match in QUOTED.finditer(line):
                raw = match.group(1) or match.group(2)
                where = 0
                for position, (start, end, _text) in enumerate(spans):
                    if start <= match.start() <= end:
                        where = position
                        break
                attributed = (cues[where] or anchors[where]
                              or (where and leadin[where - 1]
                                  and (cues[where - 1] or anchors[where - 1])))
                if not attributed:
                    continue
                quoted_here = True
                if historical[where] or (where and leadin[where - 1] and historical[where - 1]):
                    findings.append(_finding("historical-quote", rel, line_at(starts, match.start()), raw,
                                             "a record of retired wording"))
                    continue
                if negated[where] or (where and leadin[where - 1] and negated[where - 1]):
                    findings.append(_finding("disclaimed-quote", rel, line_at(starts, match.start()), raw,
                                             "quoted to say the book does NOT carry it"))
                    continue
                segments = [seg for seg in quote_segments(raw) if checkable(seg)]
                if not segments:
                    continue
                missing = [seg for seg in segments if seg not in book.text]
                if missing:
                    findings.append(_finding("stale-quote", rel, line_at(starts, match.start()), raw,
                                             "not in the manuscript: \"%s\"" % missing[0][:90]))
                else:
                    findings.append(_finding("graded-quote", rel, line_at(starts, match.start()), raw,
                                             "still matches; it is the exposure, not the defect"))

            if not quoted_here:
                for position, (_s, _e, text) in enumerate(spans):
                    if not cues[position] or historical[position]:
                        continue
                    if MODAL.search(text) or negated[position]:
                        findings.append(_finding("guardrail-verdict", rel, line_at(starts, _s), text.strip(),
                                                 "constrains future prose; it does not expire on a rewrite"))
                    else:
                        findings.append(_finding("manuscript-verdict", rel, line_at(starts, _s), text.strip(),
                                                 "reports what the book currently says -- that expires"))
                    break

    for finding in findings:
        if finding["path"] in exempt_paths and finding["rule"] in EXEMPT_RULES:
            finding["rule"], finding["detail"] = "exempt", EXEMPT_REASON
    return findings


FIXTURE_CHAPTER = """# Chapter 1: What Quality Means

This chapter opens with the exact sentence that is present in the book today.

## 1.1 What Quality Is

Quality is what a reader can act on.
"""

FIXTURE_DRIFT = """# History notes

The book says "a sentence that no longer exists anywhere in the chapters".

The book says "the exact sentence that is present in the book today".

The chapter used to read "a sentence that no longer exists anywhere in the
chapters" before it was rewritten.

Graded at ch1:3, and again at ch1:9999.

See manuscript/110-chapter-1.md, and also manuscript/990-chapter-99.md.

Recompute density live with `term-density-check.py` over `manuscript/`.

The manuscript currently claims something without quoting it.

What the book may say about this is limited by the sample size.

An author writes "a crop rotation rule that is nowhere in the book".

A proof result refutes "a wording the book has never carried anywhere", which
the book does not claim.

Ch1 §1.1 covers this, while Ch1 §1.9 does not.

This file's own Section 9.13 and §13.6 are internal structure.

```
manuscript/210-chapter-2.md:15 inside a fence is not a pointer.
```
"""

FIXTURE_STRUCTURE = """# Notes about the book's structure

Ch1 §1.1 opens the first idea, and the book says "the idea deepens".

The book says "a wording that has left the manuscript entirely".
"""

FIXTURE_PLACES = """# Where a term may appear

Use plain words in Ch1, Ch2, or pre-§3.3 of Ch3 until the terms are defined.
"""

FIXTURE_EXPECTED = {
    ("reasons/drift.md", "stale-quote"),
    ("reasons/drift.md", "graded-quote"),
    ("reasons/drift.md", "historical-quote"),
    ("reasons/drift.md", "disclaimed-quote"),
    ("reasons/drift.md", "line-anchor"),
    ("reasons/drift.md", "stale-line-anchor"),
    ("reasons/drift.md", "manuscript-path"),
    ("reasons/drift.md", "stale-manuscript-path"),
    ("reasons/drift.md", "live-invocation"),
    ("reasons/drift.md", "manuscript-verdict"),
    ("reasons/drift.md", "guardrail-verdict"),
    ("reasons/drift.md", "section-pointer"),
    ("reasons/drift.md", "stale-section-pointer"),
    ("reasons/structure.md", "exempt"),
    ("reasons/structure.md", "stale-quote"),
}

RENAMED_NOTES = """# Notes in a book with its own folder and file names

See text/ch99-gone.md for the old version, and text/ch01-reading.md:4 for the line.

The last line is text/ch01-reading.md:999, which the chapter never had.

The README.md:3 of a tool is not the book.
"""

RENAMED_EXPECTED = [
    (3, "stale-manuscript-path"), (3, "manuscript-path"), (3, "line-anchor"),
    (5, "manuscript-path"), (5, "stale-line-anchor"),
]


def write_fixture(root, files):
    for name, body in files:
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


def fixture_book(root, folder, chapter_pattern):
    paths = markdown_files_under(Path(root) / folder)
    chapters = [(path, chapter_of(path, chapter_pattern)) for path in paths]
    return BookFiles(folder, chapters, chapter_pattern)


def chapter_of(path, chapter_pattern):
    found = re.search(chapter_pattern, Path(path).name)
    return int(found.group(1)) if found else None


def default_layout_failures():
    with tempfile.TemporaryDirectory() as root:
        write_fixture(root, (("manuscript/110-chapter-1.md", FIXTURE_CHAPTER),
                             ("reasons/drift.md", FIXTURE_DRIFT),
                             ("reasons/structure.md", FIXTURE_STRUCTURE),
                             ("reasons/places.md", FIXTURE_PLACES)))
        book = fixture_book(root, "manuscript", r"(?:^|-)chapter-(\d+)\.md$")
        findings = assess(visible_markdown_files_under(Path(root, "reasons")), book, root,
                          ["reasons/structure.md"])
    found = set((f["path"], f["rule"]) for f in findings)
    failures = ["%-30s %-22s NOT REPORTED" % item for item in sorted(FIXTURE_EXPECTED - found)]
    failures += ["%-30s %-22s FALSE POSITIVE" % item for item in sorted(found - FIXTURE_EXPECTED)]
    return failures


def renamed_layout_failures():
    with tempfile.TemporaryDirectory() as root:
        write_fixture(root, (("text/ch01-reading.md", FIXTURE_CHAPTER),
                             ("notes/renamed.md", RENAMED_NOTES)))
        book = fixture_book(root, "text", r"^ch(\d+)-")
        findings = assess(visible_markdown_files_under(Path(root, "notes")), book, root)
    found = sorted((f["line"], f["rule"]) for f in findings)
    if found == sorted(RENAMED_EXPECTED):
        return []
    return ["renamed folder: expected %s, found %s" % (sorted(RENAMED_EXPECTED), found)]


def self_test():
    failures = default_layout_failures() + renamed_layout_failures()
    for failure in failures:
        print("FAIL %s" % failure)
    print("self-test: %s" % ("PASS" if not failures else "%d failure(s)" % len(failures)))
    return 1 if failures else 0


def book_files(config, explicit_folder):
    folder = explicit_folder or config.manuscript.dir
    paths = manuscript_paths(config, TOOL, explicit_folder)
    return BookFiles(Path(folder).resolve().name,
                     [(path, config.chapter_number(path)) for path in paths],
                     config.manuscript.chapter_pattern)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--argument", "--notes", dest="argument",
                        help="only this folder (default: the whole thinking folder)")
    parser.add_argument("--manuscript",
                        help="a manuscript folder (default: the book's manuscript files)")
    parser.add_argument("--file", help="only this thinking file")
    parser.add_argument("--verbose", action="store_true",
                        help="also the informational classes, with the reason for each")
    parser.add_argument("--self-test", action="store_true",
                        help="only check the rules against built-in fixtures")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    config = load_book(args, TOOL)
    if args.argument and not Path(args.argument).is_dir():
        return tool_failed("argument folder not found: %s" % args.argument, TOOL)
    report = CheckReport(TOOL, CLASSES)
    paths = visible_markdown_files_under(args.argument) if args.argument else thinking_paths(config)
    if not paths:
        report.skip("the book has no thinking files")
        return report.emit(args.format)
    if args.manuscript and not Path(args.manuscript).is_dir():
        return tool_failed("manuscript not found: %s" % args.manuscript, TOOL)

    exempt = (config.terms.watch_words or {}).get("notes_about_the_book") or []
    book = book_files(config, args.manuscript)
    if not book.lines_by_name:
        report.skip("no manuscript files at %s" % (args.manuscript or config.manuscript.dir))
        return report.emit(args.format)
    findings = assess(paths, book, config.root, exempt if isinstance(exempt, list) else [exempt])
    if args.file:
        wanted = shown_path(config.root, args.file)
        findings = [f for f in findings if f["path"] == wanted]

    for finding in findings:
        if CLASSES[finding["rule"]] == INFORMATIONAL and not args.verbose:
            continue
        text = finding["text"].strip()
        if not args.verbose and len(text) > 96:
            text = text[:93] + "..."
        detail = (" -- " + finding["detail"]) if (args.verbose and finding["detail"]) else ""
        report.add("%s:%d" % (finding["path"], finding["line"]), finding["rule"], text + detail)
    if args.format == "text":
        print("A report, never a fix: a stale verdict is usually repaired by deleting a\n"
              "paragraph. What the book currently says belongs in a dated run report.\n")
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
