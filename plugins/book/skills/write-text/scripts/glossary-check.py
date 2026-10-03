#!/usr/bin/env python3
"""Check how the manuscript uses the terms in the book's glossary.

For every glossary entry the check finds where the glossary says the term is defined, where the
manuscript first uses it, whether a use comes before the definition, and how often the term
appears in each file. It reads the glossary and never writes it.

Findings (exit codes and output shape: lib/check_contract.md):
  used-before-defined  advisory       the first use sits in a file before the one the glossary
                                      names; most are a plain everyday use of
                                      the word, the rest break rule 6.3
  never-found          advisory       no search form of the term appears in the whole book;
                                      most are a heading that does not match the form the
                                      book uses (off when only some files are checked)
  location-not-found   informational  the heading's location names no manuscript file

Front matter (manuscript.front_matter) previews the book's words, so a use there never counts as
"before the definition". The location notation comes from glossary_format.location_pattern
(lib/glossary-format.md). A book with no glossary yet is SKIPPED, not a failure.
"""

import argparse
import fnmatch
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import script_tests
from book_config import KIND_REFERENCES, ConfigError, add_config_arguments, config_from_args
from check_output import (ADVISORY, INFORMATIONAL, CheckReport, add_output_arguments, run_main,
                          tool_failed)
from glossary import locate_definition, notation_from_config, parse_glossary
from manuscript_text import prose_lines

TOOL = "glossary-check"
CLASSES = {
    "used-before-defined": ADVISORY,
    "never-found": ADVISORY,
    "location-not-found": INFORMATIONAL,
}
CONTEXT_WORDS = 10


@dataclass
class ScannedFile:
    name: str
    position: int
    exempt: bool
    lines: list


@dataclass
class Occurrence:
    file: ScannedFile
    line_number: int
    context: str

    @property
    def place(self):
        return f"{self.file.name}:{self.line_number}"


@dataclass
class TermResult:
    entry: object
    defined_position: object
    occurrences: list = field(default_factory=list)

    @property
    def first(self):
        return self.occurrences[0] if self.occurrences else None

    @property
    def first_outside_exempt(self):
        return next((found for found in self.occurrences if not found.file.exempt), None)

    @property
    def used_before_defined(self):
        first = self.first_outside_exempt
        return (first is not None and self.defined_position is not None
                and first.file.position < self.defined_position)

    @property
    def per_file(self):
        counts = Counter(found.file.name for found in self.occurrences)
        positions = {found.file.name: found.file.position for found in self.occurrences}
        return sorted(counts.items(), key=lambda item: positions[item[0]])


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", type=Path,
                        help="check only these manuscript files (the used-before-defined and "
                             "never-found checks need the whole book, so they are off)")
    parser.add_argument("--glossary", type=Path, help="glossary file (default: rules.glossary)")
    parser.add_argument("--location-pattern", help="regular expression for the heading location "
                                                   "(default: glossary_format.location_pattern)")
    parser.add_argument("--heading-separator", help="text between term and location "
                                                    "(default: glossary_format.heading_separator)")
    parser.add_argument("--exempt-paths", help="comma-separated file-name globs whose uses never "
                                               "count as early (default: manuscript.front_matter; "
                                               "\"\" for none)")
    parser.add_argument("--report", type=Path, help="also write the full markdown report here")
    parser.add_argument("--verbose", action="store_true",
                        help="put every use with its context in the report")
    parser.add_argument("--self-test", action="store_true", help="run the tests on the fixtures")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser.parse_args(argv)


def exempt_globs(arguments, config):
    if arguments.exempt_paths is None:
        return list(config.manuscript.front_matter)
    return [glob.strip() for glob in arguments.exempt_paths.split(",") if glob.strip()]


def scan_files(config, chosen_files, globs):
    book_files = [item for item in config.manuscript_files() if item.kind != KIND_REFERENCES]
    wanted = {path.resolve() for path in chosen_files}
    scanned = []
    for position, item in enumerate(book_files):
        if wanted and item.path.resolve() not in wanted:
            continue
        exempt = any(fnmatch.fnmatch(item.name, glob) for glob in globs)
        text = item.path.read_text(encoding="utf-8")
        scanned.append(ScannedFile(item.name, position, exempt, prose_lines(text)))
    return book_files, scanned


def term_pattern(form):
    return re.compile(r"\b" + r"\s+".join(re.escape(word) for word in form.split()) + r"\b",
                      re.IGNORECASE)


def context_window(line, start, end):
    before = re.findall(r"\S+", line[:start])[-CONTEXT_WORDS:]
    after = re.findall(r"\S+", line[end:])[:CONTEXT_WORDS]
    return " ".join(before + [line[start:end]] + after).strip()


def find_occurrences(forms, scanned_files):
    occurrences = []
    for form in forms:
        pattern = term_pattern(form)
        for scanned in scanned_files:
            for number, line in enumerate(scanned.lines, 1):
                if not line.strip() or line.lstrip().startswith("|"):
                    continue
                for match in pattern.finditer(line):
                    occurrences.append(Occurrence(scanned, number,
                                                  context_window(line, match.start(), match.end())))
    occurrences.sort(key=lambda found: (found.file.position, found.line_number))
    return occurrences


def check_terms(entries, notation, book_files, scanned_files):
    return [TermResult(entry, locate_definition(entry.location, notation, book_files),
                       find_occurrences(entry.search_forms, scanned_files))
            for entry in entries]


def add_findings(report, results, whole_book):
    for result in results:
        entry = result.entry
        if whole_book and result.used_before_defined:
            report.add(entry.term, "used-before-defined",
                       f"defined in {entry.location} but first used at "
                       f"{result.first_outside_exempt.place}")
        if whole_book and not result.occurrences:
            report.add(entry.term, "never-found",
                       f"defined in {entry.location or 'unknown'}; searched for: "
                       + ", ".join(entry.search_forms))
        if entry.location and result.defined_position is None:
            report.add(entry.term, "location-not-found",
                       f"location '{entry.location}' names no manuscript file")


def markdown_report(results, verbose, whole_book):
    flagged = [result for result in results if whole_book and result.used_before_defined]
    never_found = [result for result in results if whole_book and not result.occurrences]
    lines = ["# Glossary Drift and Pre-Introduction Check\n", "## Summary\n",
             f"- Total glossary terms: **{len(results)}**",
             f"- Terms with occurrences: **{sum(1 for result in results if result.occurrences)}**",
             f"- Used before defined (flagged): **{len(flagged)}**",
             f"- Never found in manuscript: **{len(never_found)}**", ""]
    if flagged:
        lines += ["## Used-Before-Defined\n",
                  "The following terms first appear in the manuscript earlier than their "
                  "registered definition chapter. Verify whether the earlier use is a plain "
                  "everyday use of the word, a rename, or a definition that should move "
                  "earlier (Rule 6.3).\n"]
        lines += [f"- **{result.entry.term}**: defined in {result.entry.location} but first used "
                  f"at `{result.first_outside_exempt.place}`" for result in flagged]
        lines.append("")
    if never_found:
        lines += ["## Never Found in Manuscript\n",
                  "Registry terms not found anywhere in the scanned manuscript. The entry may be "
                  "stale, or the search form may not match the usage form.\n"]
        lines += [f"- **{result.entry.term}** (defined in {result.entry.location or 'unknown'})"
                  for result in never_found]
        lines.append("")
    lines.append("## Per-Term Detail\n")
    for result in results:
        lines += term_detail(result, verbose, whole_book)
    return "\n".join(lines)


def term_detail(result, verbose, whole_book):
    entry = result.entry
    lines = [f"### {entry.term}", f"- Defined in: {entry.location or 'unknown'}"]
    if entry.canonical_definition:
        lines.append(f"- Canonical: {entry.canonical_definition}")
    if entry.invariants:
        lines.append(f"- Invariants: {entry.invariants}")
    lines.append(f"- Total occurrences: {len(result.occurrences)}")
    if not result.occurrences:
        return lines + ["- **No occurrences found.**", ""]
    warning = ""
    if whole_book and result.used_before_defined:
        warning = (f" -- **WARNING: used before defined (first non-exempt use at "
                   f"`{result.first_outside_exempt.place}`)**")
    lines.append(f"- First occurrence: `{result.first.place}`{warning}")
    lines.append("- Per-chapter: " + ", ".join(f"{name}:{count}"
                                                for name, count in result.per_file))
    if verbose:
        lines.append("- Post-definition context windows:")
        lines += [f"  - `{found.place}` ...{found.context}..." for found in result.occurrences]
    return lines + [""]


def main(argv=None):
    arguments = parse_arguments(argv)
    if arguments.self_test:
        return script_tests.run_self_test(__file__, "test_glossary_check.py")
    try:
        config = config_from_args(arguments, targets=arguments.files)
    except ConfigError as error:
        return tool_failed(str(error), TOOL)
    if arguments.glossary and not arguments.glossary.is_file():
        return tool_failed(f"glossary file not found: {arguments.glossary}", TOOL)
    glossary_path = arguments.glossary or config.rules.glossary
    if glossary_path is None or not Path(glossary_path).is_file():
        report = CheckReport(TOOL, CLASSES)
        report.skip(f"no glossary yet at {glossary_path}; Stage 1 of the review seeds it")
        return report.emit(arguments.format)
    notation = notation_from_config(config, arguments.heading_separator,
                                    arguments.location_pattern)
    entries = parse_glossary(Path(glossary_path).read_text(encoding="utf-8"), notation)
    book_files, scanned_files = scan_files(config, arguments.files, exempt_globs(arguments, config))
    if not scanned_files:
        return tool_failed(f"no manuscript files found in {config.manuscript.dir}", TOOL)
    whole_book = not arguments.files
    results = check_terms(entries, notation, book_files, scanned_files)
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(markdown_report(results, arguments.verbose, whole_book) + "\n",
                                    encoding="utf-8")
    report = CheckReport(TOOL, CLASSES)
    add_findings(report, results, whole_book)
    return report.emit(arguments.format)


if __name__ == "__main__":
    run_main(main)
