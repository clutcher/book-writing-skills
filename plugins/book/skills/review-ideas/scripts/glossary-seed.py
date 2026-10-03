#!/usr/bin/env python3
"""Find the terms the glossary is missing, and add them for the author to curate.

Two sources of missing terms:

  1. The definitions index that Stage 1 of a review writes (artifacts/definitions-index.md).
     Every term in it with no glossary entry is a `new-term`. With --fix each one is added as
     `### term -- location` with `**Canonical definition:** [TO CURATE]`. Existing entries are
     never changed and no date is written: the glossary is dateless. A glossary file that does
     not exist yet is started with a short header.
  2. The manuscript itself. A sentence that looks like a definition, for a term the glossary does
     not hold, is an `unregistered-definition`: a blockquote "X is ...", a `**X** is ...`
     sentence, or a heading followed by "<heading> is ...". These need a person and are never
     added.

Findings (exit codes and output shape: lib/check_contract.md):
  new-term                 informational  in the definitions index, not in the glossary; --fix adds
  location-not-found       informational  a new term's location names no manuscript file in the
                                          book's notation (glossary_format.location_pattern)
  unregistered-definition  advisory       a definition-shaped sentence for a term with no entry

Dry run by default. The glossary heading format is in lib/glossary-format.md.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import script_tests
from book_config import KIND_REFERENCES, ConfigError, add_config_arguments, config_from_args
from check_output import ADVISORY, INFORMATIONAL, CheckReport, add_output_arguments, tool_failed
from glossary import (FIELD_CANONICAL_DEFINITION, TO_CURATE, known_forms, locate_definition,
                           notation_from_config, parse_glossary, search_forms_of)
from manuscript_text import prose_lines

TOOL = "glossary-seed"
CLASSES = {
    "new-term": INFORMATIONAL,
    "location-not-found": INFORMATIONAL,
    "unregistered-definition": ADVISORY,
}
TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
SEPARATOR_ROW = re.compile(r"^\s*\|?\s*:?-{2,}")
MARKUP = re.compile(r"[*`_]")
DEFINING_VERB = r"\s+(?:is|are|means)\s"
BLOCKQUOTE_DEFINITION = re.compile(r"^>\s*(?:\*\*)?(?:(?:An?|The)\s+)?"
                                   r"(?P<term>[A-Za-z][^*.,;:>\"]{1,60}?)(?:\*\*)?" + DEFINING_VERB)
BOLD_DEFINITION = re.compile(r"\*\*(?P<term>[^*]{2,60})\*\*" + DEFINING_VERB)
SECTION_HEADING = re.compile(r"^#{2,6}\s+(?:[\d.]+\s+)?(?P<title>[^#].*?)\s*$")
LEADING_WORD = re.compile(r"^(?:an?|the|to)\s+", re.IGNORECASE)
MAX_TERM_WORDS = 6


@dataclass
class IndexedTerm:
    term: str
    location: str


@dataclass
class DefinitionSentence:
    term: str
    place: str


def table_cells(line):
    row = TABLE_ROW.match(line)
    return [cell.strip() for cell in row.group(1).split("|")] if row else None


def read_definitions_index(text, term_column, location_column):
    terms = []
    columns = None
    for line in text.split("\n"):
        cells = table_cells(line)
        if cells is None:
            columns = None
            continue
        if SEPARATOR_ROW.match(line):
            continue
        lowered = [cell.lower() for cell in cells]
        if columns is None:
            if term_column.lower() in lowered:
                columns = (lowered.index(term_column.lower()),
                           lowered.index(location_column.lower())
                           if location_column.lower() in lowered else None)
            continue
        term_index, location_index = columns
        term = MARKUP.sub("", cells[term_index]).strip() if term_index < len(cells) else ""
        location = cells[location_index].strip() \
            if location_index is not None and location_index < len(cells) else ""
        if term:
            terms.append(IndexedTerm(term, location))
    return terms


def spellings(term):
    bare = LEADING_WORD.sub("", MARKUP.sub("", term).strip())
    names = {name.lower() for name in [bare, *search_forms_of(bare)] if name}
    return names | {name.rstrip("s") for name in names} | {f"{name}s" for name in names}


def is_known(term, forms):
    return bool(spellings(term) & forms)


def not_in_glossary(items, forms):
    seen = set()
    missing = []
    for item in items:
        if not is_known(item.term, forms) and item.term.lower() not in seen:
            seen.add(item.term.lower())
            missing.append(item)
    return missing


def is_term_sized(term):
    return 0 < len(term.split()) <= MAX_TERM_WORDS


def sentence_definitions(file_name, lines):
    found = []
    for number, line in enumerate(lines, 1):
        for pattern in (BLOCKQUOTE_DEFINITION, BOLD_DEFINITION):
            for match in pattern.finditer(line):
                term = MARKUP.sub("", match.group("term")).strip()
                if is_term_sized(term):
                    found.append(DefinitionSentence(term, f"{file_name}:{number}"))
    return found


def defines_heading(title, line):
    definition = re.compile(r"^(?:(?:An?|The)\s+)?" + re.escape(title) + DEFINING_VERB,
                            re.IGNORECASE)
    return bool(definition.match(MARKUP.sub("", line.strip())))


def heading_definitions(file_name, lines):
    found = []
    open_title = None
    for number, line in enumerate(lines, 1):
        heading = SECTION_HEADING.match(line)
        if heading:
            title = MARKUP.sub("", heading.group("title")).strip()
            open_title = title if is_term_sized(title) else None
            continue
        if not line.strip():
            continue
        if open_title and defines_heading(open_title, line):
            found.append(DefinitionSentence(open_title, f"{file_name}:{number}"))
        open_title = None
    return found


def definition_sentences(manuscript_files):
    found = []
    for item in manuscript_files:
        lines = prose_lines(item.path.read_text(encoding="utf-8"))
        found += sentence_definitions(item.name, lines)
        found += heading_definitions(item.name, lines)
    return found


def entry_text(item, separator):
    heading = f"### {item.term}{separator}{item.location}" if item.location else f"### {item.term}"
    return "\n".join([heading, f"**{FIELD_CANONICAL_DEFINITION}:** {TO_CURATE}"])


def new_glossary_header(separator):
    return "\n".join([
        "# Glossary",
        "",
        f"The terms this book formally defines. Each entry is a `### term{separator}location (kind)`",
        "heading and a `**Canonical definition:**` line. Format and rules: the plugin's lib,",
        "lib/glossary-format.md.",
    ])


def section_start(lines, section):
    return next((index for index, line in enumerate(lines) if line.strip() == section), None)


def section_end(lines, start):
    return next((index for index in range(start + 1, len(lines))
                 if lines[index].startswith("## ")), len(lines))


def insert_entries(glossary_text, entries_text, section):
    lines = glossary_text.rstrip("\n").split("\n")
    insert_at = section_end(lines, section_start(lines, section)) if section else len(lines)
    before = "\n".join(lines[:insert_at]).rstrip("\n")
    after = "\n".join(lines[insert_at:])
    block = "\n\n".join(entries_text)
    parts = [part for part in (before, block, after) if part]
    return "\n\n".join(parts) + "\n"


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("definitions_index", nargs="?", type=Path,
                        help="artifacts/definitions-index.md of a review run (optional; without "
                             "it only the manuscript is searched)")
    parser.add_argument("--glossary", type=Path, help="glossary file (default: rules.glossary)")
    parser.add_argument("--section", help="add new entries at the end of this `## ` section "
                                          "(default: the end of the file)")
    parser.add_argument("--term-column", default="Term", help="index column with the term")
    parser.add_argument("--location-column", default="Introduced",
                        help="index column with the location, written in the glossary notation")
    parser.add_argument("--heading-separator", help="text between term and location "
                                                    "(default: glossary_format.heading_separator)")
    parser.add_argument("--location-pattern", help="regular expression for the heading location "
                                                   "(default: glossary_format.location_pattern)")
    parser.add_argument("--fix", action="store_true", help="add the new terms to the glossary")
    parser.add_argument("--self-test", action="store_true", help="run the tests on the fixtures")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser.parse_args(argv)


def unreadable_locations(items, notation, manuscript):
    return [item for item in items
            if item.location and locate_definition(item.location, notation, manuscript) is None]


def write_new_entries(glossary_path, glossary_text, missing, notation, section):
    starting_text = glossary_text or new_glossary_header(notation.heading_separator)
    new_text = insert_entries(starting_text,
                              [entry_text(item, notation.heading_separator) for item in missing],
                              section)
    glossary_path.parent.mkdir(parents=True, exist_ok=True)
    glossary_path.write_text(new_text, encoding="utf-8")


def main(argv=None):
    arguments = parse_arguments(argv)
    if arguments.self_test:
        return script_tests.run_self_test(__file__, "test_glossary_seed.py")
    try:
        config = config_from_args(arguments)
    except ConfigError as error:
        return tool_failed(str(error), TOOL)
    glossary_path = arguments.glossary or config.rules.glossary
    if glossary_path is None:
        return tool_failed("the book has no rules.glossary path", TOOL)
    notation = notation_from_config(config, arguments.heading_separator,
                                    arguments.location_pattern)
    glossary_text = glossary_path.read_text(encoding="utf-8") if glossary_path.is_file() else ""
    if arguments.section and section_start(glossary_text.split("\n"), arguments.section) is None:
        return tool_failed(f"no section '{arguments.section}' in the glossary {glossary_path}", TOOL)
    forms = known_forms(parse_glossary(glossary_text, notation))
    manuscript = [item for item in config.manuscript_files() if item.kind != KIND_REFERENCES]
    report = CheckReport(TOOL, CLASSES)
    if not manuscript:
        report.skip(f"no manuscript files at {config.manuscript.dir}")
        return report.emit(arguments.format)
    missing = []
    if arguments.definitions_index:
        if not arguments.definitions_index.is_file():
            return tool_failed(f"no definitions index at {arguments.definitions_index}", TOOL)
        indexed = read_definitions_index(arguments.definitions_index.read_text(encoding="utf-8"),
                                         arguments.term_column, arguments.location_column)
        missing = not_in_glossary(indexed, forms)
    unregistered = not_in_glossary(definition_sentences(manuscript), forms)
    for item in missing:
        report.add(item.term, "new-term", f"at {item.location or 'unknown location'}; "
                                          + ("added" if arguments.fix else "--fix adds it"))
    for item in unreadable_locations(missing, notation, manuscript):
        report.add(item.term, "location-not-found",
                   f"location '{item.location}' names no manuscript file in the book's notation")
    for sentence in unregistered:
        report.add(sentence.term, "unregistered-definition", f"defined at {sentence.place}")
    if arguments.fix and missing:
        write_new_entries(glossary_path, glossary_text, missing, notation, arguments.section)
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
