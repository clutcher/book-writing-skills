#!/usr/bin/env python3
"""Match the citations in the manuscript against the bibliography (the .bib file).

Reads every manuscript file except the references page (manuscript.references), finds each
pandoc citation (`[@Key]`, `[@A; @B, p. 12]`, narrative `@Key`, `@{Key}`; lib/citations.py),
and compares the keys with the entries of sources.bibliography. Text inside code is skipped.

Findings (exit codes and output shape: lib/check_contract.md):
  not-in-bibliography  defect         a key is cited but has no .bib entry
  not-cited            informational  a .bib entry the manuscript never cites (the .bib holds
                                      every source the author tracks; the build prints only
                                      the cited ones)
  adjacent-brackets    defect         `[@A][@B]` where `[@A; @B]` is the form
  density-outlier      informational  a chapter whose citations per 1,000 words is more than
                                      50% away from the chapter average
  old-citation         defect         `[Key]`, `[Key, p. 12]` or `[A, B]` written without `@`,
                                      where every key is in the .bib or the sources list: pandoc
                                      prints it as plain text; write `[@Key]`, `[@Key, p. 12]`,
                                      `[@A; @B]`
  hand-written-references  defect     the references file (manuscript.references) holds more
                                      than its heading and the `::: {#refs}` div; the build
                                      fills the list from the .bib, so a hand-written list
                                      prints twice or goes out of step

--report writes the full markdown report that Stage 2 of the review reads: counts and density
per file, single-use keys, the most cited keys, and the file pairs that share the most keys.
"""

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import script_tests
from book_config import (KIND_CHAPTER, KIND_REFERENCES, MANUSCRIPT_KINDS, ConfigError,
                         add_config_arguments, config_from_args)
from bibliography import BibliographyError, read_bibliography
from check_output import (DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing, tool_failed)
from citations import hide_code
from manuscript_text import cited_keys, prose_lines, word_count
from source_registry import read_bank

TOOL = "citation-check"
CLASSES = {
    "not-in-bibliography": DEFECT,
    "not-cited": INFORMATIONAL,
    "adjacent-brackets": DEFECT,
    "density-outlier": INFORMATIONAL,
    "old-citation": DEFECT,
    "hand-written-references": DEFECT,
}
CITATION_GROUP = r"\[([^\[\]]*@[^\[\]]*)\]"
ADJACENT = re.compile(CITATION_GROUP + r"[ \t]*" + CITATION_GROUP + r"(?!\()")
OLD_CITATION = re.compile(r"(?<!\])\[([^\[\]@]+)\](?![(\[:{])")
LOCATOR = re.compile(r"(?:pp?|ch|chap|sec|fig|vol|no|§)\.?\s*\S+|\d+(?:[-–]\d+)?", re.IGNORECASE)
HEADING = re.compile(r"#{1,6}\s")
LIST_HEADING = re.compile(r"^### \[", re.MULTILINE)
REFS_DIV_OPEN = re.compile(r":{3,}\s*\{\s*#refs\b[^}]*\}")
DIV_CLOSE = re.compile(r":{3,}")
SINGLE_USE_SHOWN = 30
MOST_CITED_SHOWN = 15
OVERLAPS_SHOWN = 10
OVERLAP_KEYS_SHOWN = 8
OUTLIER_SHARE = 0.5


@dataclass
class FileCitations:
    name: str
    kind: str
    words: int
    lines_by_key: dict = field(default_factory=dict)
    adjacent: list = field(default_factory=list)
    old_citations: list = field(default_factory=list)

    @property
    def unique_count(self):
        return len(self.lines_by_key)

    @property
    def mention_count(self):
        return sum(len(lines) for lines in self.lines_by_key.values())

    @property
    def density(self):
        return self.unique_count / self.words * 1000 if self.words else 0


def read_citations(path, kind, known_keys):
    text = path.read_text(encoding="utf-8")
    citations = FileCitations(path.name, kind, word_count(text))
    for number, line in enumerate(prose_lines(text), 1):
        visible = hide_code(line)
        for match in ADJACENT.finditer(visible):
            citations.adjacent.append((number, [match.group(1).strip(), match.group(2).strip()],
                                       match.group(0)))
        for match in OLD_CITATION.finditer(visible):
            keys = old_citation_keys(match.group(1), known_keys)
            if keys:
                citations.old_citations.append((number, match.group(0), keys))
        for key in cited_keys(line):
            citations.lines_by_key.setdefault(key, []).append(number)
    return citations


def old_citation_keys(content, known_keys):
    pieces = [piece.strip() for piece in re.split(r"[,;]", content)]
    keys = [piece for piece in pieces if piece in known_keys]
    rest = [piece for piece in pieces if piece not in known_keys]
    if not keys or not all(LOCATOR.fullmatch(piece) for piece in rest):
        return []
    return keys


def pandoc_form(old_text, keys):
    locators = [piece.strip() for piece in re.split(r"[,;]", old_text[1:-1])
                if piece.strip() not in keys]
    cited = "; ".join(f"@{key}" for key in keys)
    return f"[{cited}, {', '.join(locators)}]" if locators else f"[{cited}]"


def bibliography_keys(path):
    return set(read_bibliography(path).keys)


def list_keys(path):
    if not path or not Path(path).is_file():
        return set()
    if not LIST_HEADING.search(Path(path).read_text(encoding="utf-8")):
        return set()
    return set(read_bank(path).keys)


def hand_written_lines(path):
    if not path or not Path(path).is_file():
        return []
    visible = hide_code(Path(path).read_text(encoding="utf-8"))
    return [number for number, line in enumerate(visible.split("\n"), 1)
            if line.strip() and not HEADING.match(line.strip())
            and not REFS_DIV_OPEN.fullmatch(line.strip()) and not DIV_CLOSE.fullmatch(line.strip())]


@dataclass
class CitationSummary:
    files: list
    listed: set

    @property
    def cited(self):
        return {key for item in self.files for key in item.lines_by_key}

    @property
    def files_per_key(self):
        return Counter(key for item in self.files for key in item.lines_by_key)

    @property
    def not_in_bibliography(self):
        return sorted(self.cited - self.listed)

    @property
    def not_cited(self):
        return sorted(self.listed - self.cited)

    @property
    def single_use(self):
        return sorted(key for key, count in self.files_per_key.items() if count == 1)

    @property
    def total_words(self):
        return sum(item.words for item in self.files)

    @property
    def density_files(self):
        chapters = [item for item in self.files if item.kind == KIND_CHAPTER]
        return chapters or self.files

    @property
    def average_density(self):
        densities = [item.density for item in self.density_files]
        return sum(densities) / len(densities) if densities else 0

    @property
    def density_outliers(self):
        average = self.average_density
        return [item for item in self.density_files
                if abs(item.density - average) > average * OUTLIER_SHARE]

    def files_citing(self, key):
        return [item for item in self.files if key in item.lines_by_key]

    def shared_keys_by_pair(self):
        pairs = {}
        for index, first in enumerate(self.files):
            for second in self.files[index + 1:]:
                shared = set(first.lines_by_key) & set(second.lines_by_key)
                if shared:
                    pairs[(first.name, second.name)] = shared
        return sorted(pairs.items(), key=lambda pair: len(pair[1]), reverse=True)


def line_list(lines):
    return ", ".join(f"L{number}" for number in lines)


def counts_section(summary, verbose):
    lines = ["## Per-File Citation Counts\n",
             "| File | Words | Unique Citations | Total Mentions | Density (per 1K words) |",
             "|------|-------|-----------------|----------------|----------------------|"]
    lines += [f"| {item.name} | {item.words:,} | {item.unique_count} | {item.mention_count} | "
              f"{item.density:.1f} |" for item in summary.files]
    total_mentions = sum(item.mention_count for item in summary.files)
    overall = len(summary.cited) / summary.total_words * 1000 if summary.total_words else 0
    lines += [f"| **Total** | **{summary.total_words:,}** | **{len(summary.cited)}** | "
              f"**{total_mentions}** | **{overall:.1f}** |", ""]
    if summary.density_outliers:
        average = summary.average_density
        lines += ["### Density Outliers\n",
                  f"Average density: {average:.1f} per 1K words. Chapters deviating >50% from "
                  f"average:\n"]
        lines += [f"- **{item.name}**: {item.density:.1f} "
                  f"({'above' if item.density > average else 'below'} average)"
                  for item in summary.density_outliers]
        lines.append("")
    if verbose:
        lines.append("### Per-File Citation Details\n")
        for item in summary.files:
            if item.lines_by_key:
                lines.append(f"**{item.name}** ({item.unique_count} unique):\n")
                lines += [f"- @{key} at {line_list(item.lines_by_key[key])}"
                          for key in sorted(item.lines_by_key)]
                lines.append("")
    return lines


def bibliography_sections(summary):
    lines = ["## Cited but Missing from Bibliography\n"]
    if summary.not_in_bibliography:
        lines.append(f"**{len(summary.not_in_bibliography)} citation(s) found in the manuscript "
                     f"but not in the bibliography:**\n")
        for key in summary.not_in_bibliography:
            places = [f"{item.name} ({line_list(item.lines_by_key[key])})"
                      for item in summary.files_citing(key)]
            lines.append(f"- **@{key}** in {', '.join(places)}")
        lines.append("")
    else:
        lines.append("All cited keys found in bibliography.\n")
    lines.append("## In Bibliography but Never Cited\n")
    if summary.not_cited:
        lines.append(f"**{len(summary.not_cited)} bibliography entries never cited in "
                     f"any manuscript file:**\n")
        lines += [f"- @{key}" for key in summary.not_cited]
        lines.append("")
    else:
        lines.append("All bibliography entries are cited.\n")
    return lines


def usage_sections(summary):
    single_use = summary.single_use
    lines = ["## Single-Use Citations\n",
             f"**{len(single_use)} citations appear in only one file** (may indicate weak "
             f"grounding if supporting a major claim):\n"]
    lines += [f"- @{key} only in {summary.files_citing(key)[0].name}"
              for key in single_use[:SINGLE_USE_SHOWN]]
    if len(single_use) > SINGLE_USE_SHOWN:
        lines.append(f"- ... and {len(single_use) - SINGLE_USE_SHOWN} more")
    lines += ["", "## Most-Cited Sources\n",
              "Sources cited across the most files (authority dependencies):\n",
              "| Citation | Files | Locations |", "|----------|-------|-----------|"]
    for key, count in summary.files_per_key.most_common(MOST_CITED_SHOWN):
        names = ", ".join(item.name for item in summary.files_citing(key))
        lines.append(f"| @{key} | {count} | {names} |")
    lines.append("")
    overlaps = summary.shared_keys_by_pair()[:OVERLAPS_SHOWN]
    if overlaps:
        lines += ["## Cross-File Citation Overlap\n", "File pairs sharing the most sources:\n",
                  "| File Pair | Shared Citations | Keys |",
                  "|-----------|-----------------|------|"]
        for (first, second), shared in overlaps:
            shown = ", ".join(f"@{key}" for key in sorted(shared)[:OVERLAP_KEYS_SHOWN])
            if len(shared) > OVERLAP_KEYS_SHOWN:
                shown += f" +{len(shared) - OVERLAP_KEYS_SHOWN} more"
            lines.append(f"| {first} + {second} | {len(shared)} | {shown} |")
        lines.append("")
    return lines


def adjacency_section(summary):
    total = sum(len(item.adjacent) for item in summary.files)
    lines = ["## Adjacent Bracket Violations\n"]
    if not total:
        return lines + ["No adjacent bracket violations found.\n"]
    lines.append(f"**{total} violation(s) found.** Use `[@A; @B]` instead of `[@A][@B]`:\n")
    for item in summary.files:
        lines += [f"- **{item.name}** L{number}: `{text}` -> `[{'; '.join(keys)}]`"
                  for number, keys, text in item.adjacent]
    return lines + [""]


def summary_section(summary):
    return ["## Summary\n",
            f"- Total unique citations: **{len(summary.cited)}**",
            f"- Total bibliography entries: **{len(summary.listed)}**",
            f"- Cited but missing from bibliography: **{len(summary.not_in_bibliography)}**",
            f"- In bibliography but never cited: **{len(summary.not_cited)}**",
            f"- Adjacent bracket violations: "
            f"**{sum(len(item.adjacent) for item in summary.files)}**",
            f"- Single-use citations: **{len(summary.single_use)}**",
            f"- Manuscript files checked: **{len(summary.files)}**"]


def markdown_report(summary, verbose):
    lines = ["# Citation-Bibliography Check Report\n"]
    lines += counts_section(summary, verbose)
    lines += bibliography_sections(summary)
    lines += usage_sections(summary)
    lines += adjacency_section(summary)
    lines += summary_section(summary)
    return "\n".join(lines)


def add_findings(report, summary, whole_book, references_path):
    for key in summary.not_in_bibliography:
        places = "; ".join(f"{item.name} {line_list(item.lines_by_key[key])}"
                           for item in summary.files_citing(key))
        report.add(key, "not-in-bibliography", f"cited in {places}")
    if whole_book:
        for key in summary.not_cited:
            report.add(key, "not-cited", "in the .bib, cited nowhere in the manuscript")
    for item in summary.files:
        for number, keys, text in item.adjacent:
            report.add(f"{item.name}:{number}", "adjacent-brackets",
                       f"{text} -> [{'; '.join(keys)}]")
    for item in summary.density_outliers:
        report.add(item.name, "density-outlier",
                   f"{item.density:.1f} per 1K words, average {summary.average_density:.1f}")
    for item in summary.files:
        for number, text, keys in item.old_citations:
            report.add(f"{item.name}:{number}", "old-citation",
                       f"{text} prints as plain text -> {pandoc_form(text, keys)}")
    hand_written = hand_written_lines(references_path) if whole_book else []
    if hand_written:
        report.add(Path(references_path).name, "hand-written-references",
                   f"{len(hand_written)} line(s) besides the heading and the ::: {{#refs}} div, "
                   f"first at line {hand_written[0]}; keep only those, the build fills the "
                   f"references from the .bib")


def chosen_files(config, arguments):
    if arguments.files:
        return [(path.resolve(), config.classify(path)[0]) for path in arguments.files]
    kinds = arguments.kind or [kind for kind in MANUSCRIPT_KINDS if kind != KIND_REFERENCES]
    return [(item.path, item.kind) for item in config.manuscript_files(kinds)]


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", type=Path,
                        help="check only these files (the not-cited count needs the whole "
                             "book, so it is off)")
    parser.add_argument("--kind", action="append", choices=MANUSCRIPT_KINDS,
                        help="check only manuscript files of this kind (repeatable; default: "
                             "every kind except references)")
    parser.add_argument("--report", type=Path, help="also write the full markdown report here")
    parser.add_argument("--verbose", action="store_true",
                        help="list every citation with its lines in the report")
    parser.add_argument("--self-test", action="store_true", help="run the tests on the fixtures")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse_arguments(argv)
    if arguments.self_test:
        return script_tests.run_self_test(__file__, "test_citation_check.py")
    try:
        config = config_from_args(arguments, targets=arguments.files)
    except ConfigError as error:
        return tool_failed(str(error), TOOL)
    bibliography = config.sources.bibliography
    if skipped_for_missing(TOOL, bibliography, "bibliography", arguments.format):
        return 0
    paths = chosen_files(config, arguments)
    if not paths:
        return tool_failed(f"no manuscript files found in {config.manuscript.dir}", TOOL)
    try:
        listed = bibliography_keys(bibliography)
        known_keys = listed | list_keys(config.sources.list)
        summary = CitationSummary([read_citations(path, kind, known_keys)
                                   for path, kind in paths], listed)
    except (OSError, ValueError, BibliographyError) as error:
        return tool_failed(f"cannot read the sources: {error}", TOOL)
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(markdown_report(summary, arguments.verbose) + "\n",
                                    encoding="utf-8")
    report = CheckReport(TOOL, CLASSES)
    add_findings(report, summary, not arguments.files and not arguments.kind,
                 config.manuscript.references)
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
