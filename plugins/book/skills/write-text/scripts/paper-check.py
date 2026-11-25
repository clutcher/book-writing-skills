#!/usr/bin/env python3
"""Check the parts of a research paper that a reader and a reviewer look for first.

Runs only on a paper (`kind: paper` in book.yaml); a book says SKIPPED. Four checks:

  the abstract       the file paper.abstract exists, holds words, and has no more of them
                     than paper.abstract_max_words
  the contributions  the introduction (the section headed "Introduction", else the first
                     section) holds a numbered list of at least two items
  figures and tables every figure (an image with a caption, alone in its paragraph) and every
                     table with a caption ("Table: ..." or ": ..." next to the table) is
                     pointed to from the text, by number ("Figure 2", "Fig. 2", "Figures 2
                     and 3", "Table 1") or by its label (@fig:name, \\ref{tbl:name})
  the threats        a heading names the threats to validity ("Threats to Validity",
                     "Validity Threats" or "Limitations")

Figures and tables are numbered in the order they appear across the paper, as the LaTeX
article class numbers them. From the file `paper.appendix` names on, they are numbered A1,
A2, ... as the paper build prints them, and the text points to them as "Figure A1". The words this check looks for are English, so a paper whose
book.language is not English says SKIPPED.

Findings (exit codes and output shape: lib/check_contract.md):
  abstract-missing        defect         the abstract file does not exist
  abstract-empty          defect         the abstract holds a heading and no words
  abstract-too-long       defect         more words than paper.abstract_max_words
  abstract-length         informational  the word count of the abstract against the limit
  no-contribution-list    defect         the introduction holds no numbered list
  figure-not-referenced   defect         no sentence points to the figure
  table-not-referenced    defect         no sentence points to the table
  no-threats-section      defect         no heading names the threats to validity
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import script_tests
from book_config import (KIND_CHAPTER, KIND_REFERENCES, ConfigError, add_config_arguments,
                         config_from_args)
from check_output import (DEFECT, INFORMATIONAL, CheckReport, add_output_arguments, run_main,
                          tool_failed)
from manuscript_text import prose_lines, word_count

TOOL = "paper-check"
CLASSES = {
    "abstract-missing": DEFECT,
    "abstract-empty": DEFECT,
    "abstract-too-long": DEFECT,
    "abstract-length": INFORMATIONAL,
    "no-contribution-list": DEFECT,
    "figure-not-referenced": DEFECT,
    "table-not-referenced": DEFECT,
    "no-threats-section": DEFECT,
}

HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
NUMBERED_ITEM = re.compile(r"^\s{0,3}\d+[.)]\s+\S")
INTRODUCTION_HEADING = re.compile(r"\bintroduction\b", re.IGNORECASE)
THREATS_HEADING = re.compile(r"\bthreats?\s+to\s+(?:the\s+)?validity\b|\bvalidity\s+threats?\b"
                             r"|\blimitations\b", re.IGNORECASE)
FIGURE_LINE = re.compile(r"^\s*!\[(?P<caption>[^\]]+)\]\([^)]*\)(?P<attributes>\{[^}]*\})?\s*$")
TABLE_ROW = re.compile(r"^\s*(?:\||\+[-=+])")
TABLE_CAPTION = re.compile(r"^\s*(?:Table)?:\s+\S")
LABEL = re.compile(r"#([\w:.-]+)")
NUMBER_LIST = r"(A?\d+(?:\s*(?:,|and|or|to|-{1,2})\s*A?\d+)*)"
FIGURE_MENTION = re.compile(r"\b(?:Figures?|Figs?\.)\s+" + NUMBER_LIST, re.IGNORECASE)
TABLE_MENTION = re.compile(r"\b(?:Tables?|Tabs?\.)\s+" + NUMBER_LIST, re.IGNORECASE)
RANGE = re.compile(r"(A?)(\d+)\s*(?:to|-{1,2})\s*A?(\d+)")
PRINTED_NUMBER = re.compile(r"(A?)(\d+)")
APPENDIX_PREFIX = "A"
MIN_CONTRIBUTIONS = 2


@dataclass
class Section:
    path: Path
    lines: list

    @property
    def name(self):
        return self.path.name

    @property
    def headings(self):
        return [found.group(1) for found in map(HEADING.match, self.lines) if found]


@dataclass
class Display:
    kind: str
    number: str
    label: str
    place: str
    line_index: int
    section: Section


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true", help="run the tests on small papers")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser.parse_args(argv)


def read_sections(config):
    return [Section(item.path, prose_lines(item.path.read_text(encoding="utf-8")))
            for item in config.manuscript_files() if item.kind != KIND_REFERENCES]


def check_abstract(report, config):
    abstract = config.paper.abstract
    limit = config.paper.abstract_max_words
    if abstract is None or not abstract.is_file():
        report.add("abstract", "abstract-missing", f"no abstract file at {abstract}")
        return
    words = word_count(abstract.read_text(encoding="utf-8"))
    if words == 0:
        report.add(abstract.name, "abstract-empty", "the abstract holds a heading and no words")
    elif words > limit:
        report.add(abstract.name, "abstract-too-long",
                   f"{words} words; paper.abstract_max_words is {limit}")
    else:
        report.add(abstract.name, "abstract-length", f"{words} of {limit} words")


def introduction_of(sections):
    for section in sections:
        if any(INTRODUCTION_HEADING.search(heading) for heading in section.headings[:1]):
            return section
    return sections[0] if sections else None


def check_contributions(report, sections):
    introduction = introduction_of(sections)
    if introduction is None:
        report.add("introduction", "no-contribution-list", "the paper has no sections yet")
        return
    items = sum(1 for line in introduction.lines if NUMBERED_ITEM.match(line))
    if items < MIN_CONTRIBUTIONS:
        report.add(introduction.name, "no-contribution-list",
                   "the introduction holds no numbered list of contributions "
                   f"(found {items} numbered items, at least {MIN_CONTRIBUTIONS} expected)")


def check_threats(report, sections):
    if any(THREATS_HEADING.search(heading) for section in sections
           for heading in section.headings):
        return
    report.add("threats", "no-threats-section",
               "no heading names the threats to validity (\"Threats to Validity\", "
               "\"Validity Threats\" or \"Limitations\")")


def label_of(attributes):
    found = LABEL.search(attributes or "")
    return found.group(1) if found else None


def figures_in(section, prefix, first_number):
    found = []
    for index, line in enumerate(section.lines):
        match = FIGURE_LINE.match(line)
        if match and stands_alone(section.lines, index):
            found.append(Display("figure", f"{prefix}{first_number + len(found)}",
                                 label_of(match.group("attributes")),
                                 f"{section.name}:{index + 1}", index, section))
    return found


def stands_alone(lines, index):
    before = lines[index - 1].strip() if index > 0 else ""
    after = lines[index + 1].strip() if index + 1 < len(lines) else ""
    return not before and not after


def table_blocks(lines):
    blocks = []
    start = None
    for index, line in enumerate([*lines, ""]):
        if TABLE_ROW.match(line):
            start = index if start is None else start
        elif start is not None:
            blocks.append((start, index - 1))
            start = None
    return blocks


def nearest_text_line(lines, index, step):
    index += step
    while 0 <= index < len(lines) and not lines[index].strip():
        index += step
    return index if 0 <= index < len(lines) else None


def caption_line_of(lines, first, last):
    for candidate in (nearest_text_line(lines, last, 1), nearest_text_line(lines, first, -1)):
        if candidate is not None and TABLE_CAPTION.match(lines[candidate]):
            return candidate
    return None


def tables_in(section, prefix, first_number):
    found = []
    for first, last in table_blocks(section.lines):
        caption = caption_line_of(section.lines, first, last)
        if caption is None:
            continue
        found.append(Display("table", f"{prefix}{first_number + len(found)}",
                             label_of(section.lines[caption]),
                             f"{section.name}:{first + 1}", caption, section))
    return found


def displays_of(sections, appendix):
    figures, tables = [], []
    in_appendix = False
    for section in sections:
        in_appendix = in_appendix or is_same_file(section.path, appendix)
        prefix = APPENDIX_PREFIX if in_appendix else ""
        figures += figures_in(section, prefix, count_with_prefix(figures, prefix) + 1)
        tables += tables_in(section, prefix, count_with_prefix(tables, prefix) + 1)
    return figures, tables


def is_same_file(path, other):
    return other is not None and Path(path).resolve() == Path(other).resolve()


def count_with_prefix(displays, prefix):
    return sum(1 for display in displays if display.number.startswith(prefix)
               and display.number[len(prefix):].isdigit())


def mentioned_numbers(text, pattern):
    numbers = set()
    for found in pattern.finditer(text):
        listed = found.group(1)
        for prefix, start, end in RANGE.findall(listed):
            numbers.update(f"{prefix}{number}" for number in range(int(start), int(end) + 1))
        numbers.update(prefix + number for prefix, number in PRINTED_NUMBER.findall(listed))
    return numbers


def running_text(sections, displays):
    skipped = {(display.section.path, display.line_index) for display in displays}
    return "\n".join(line for section in sections
                     for index, line in enumerate(section.lines)
                     if (section.path, index) not in skipped)


def label_is_used(label, text):
    if label is None:
        return False
    pointer = re.compile(r"(?:@|\{|\(#)" + re.escape(label) + r"(?![\w:-]|\.\w)")
    return pointer.search(text) is not None


def check_displays(report, sections, appendix):
    figures, tables = displays_of(sections, appendix)
    text = running_text(sections, figures + tables)
    for displays, pattern in ((figures, FIGURE_MENTION), (tables, TABLE_MENTION)):
        numbers = mentioned_numbers(text, pattern)
        for display in displays:
            if display.number in numbers or label_is_used(display.label, text):
                continue
            report.add(display.place, f"{display.kind}-not-referenced",
                       f"{display.kind.capitalize()} {display.number}"
                       + (f" ({display.label})" if display.label else "")
                       + " is never pointed to from the text")


def is_english(config):
    return str(config.book.language or "en").lower().startswith("en")


def main(argv=None):
    arguments = parse_arguments(argv)
    if arguments.self_test:
        return script_tests.run_self_test(__file__, "test_paper_check.py")
    try:
        config = config_from_args(arguments)
    except ConfigError as error:
        return tool_failed(str(error), TOOL)
    report = CheckReport(TOOL, CLASSES)
    if not config.is_paper:
        report.skip("a book has no abstract or contribution list; this check reads only "
                    "kind: paper")
        return report.emit(arguments.format)
    if not is_english(config):
        report.skip(f"the words this check looks for are English, and book.language is "
                    f"{config.book.language}")
        return report.emit(arguments.format)
    sections = read_sections(config)
    body = [section for section in sections
            if config.classify(section.path)[0] == KIND_CHAPTER]
    check_abstract(report, config)
    check_contributions(report, body)
    check_displays(report, sections, config.paper.appendix)
    check_threats(report, body)
    return report.emit(arguments.format)


if __name__ == "__main__":
    run_main(main)
