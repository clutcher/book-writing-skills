#!/usr/bin/env python3
"""Match the citations in the manuscript against the bibliography.

Reads every manuscript file except the bibliography (manuscript.references), finds each `[Key]`,
`[Key1, Key2]` and `[Key, p. 12]`, and compares the keys with the bibliography entries. The key
shape comes from the plugin's lib/citation_key.py. Text inside fenced code is skipped.

Findings (exit codes and output shape: lib/check_contract.md):
  cited-not-listed   defect         a key is cited but has no bibliography entry
  listed-not-cited   defect         a bibliography entry is never cited
  adjacent-brackets  defect         `[Key1][Key2]` where `[Key1, Key2]` is the form
  density-outlier    informational  a chapter whose citations per 1,000 words is more than
                                    50% away from the chapter average

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
from check_output import (DEFECT, INFORMATIONAL, CheckReport, add_output_arguments,
                          skipped_for_missing, tool_failed)
from citation_key import KEY_BODY, bib_entries
from manuscript_text import cited_keys, prose_lines, word_count

TOOL = "citation-check"
CLASSES = {
    "cited-not-listed": DEFECT,
    "listed-not-cited": DEFECT,
    "adjacent-brackets": DEFECT,
    "density-outlier": INFORMATIONAL,
}
ADJACENT = re.compile(rf"\[({KEY_BODY})\]\s*\[({KEY_BODY})\]")
BIBLIOGRAPHY_LINE = re.compile(rf"^\[({KEY_BODY})\]\s+\w")
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

    @property
    def unique_count(self):
        return len(self.lines_by_key)

    @property
    def mention_count(self):
        return sum(len(lines) for lines in self.lines_by_key.values())

    @property
    def density(self):
        return self.unique_count / self.words * 1000 if self.words else 0


def read_citations(path, kind):
    text = path.read_text(encoding="utf-8")
    citations = FileCitations(path.name, kind, word_count(text))
    for number, line in enumerate(prose_lines(text), 1):
        if BIBLIOGRAPHY_LINE.match(line.strip()):
            continue
        for match in ADJACENT.finditer(line):
            citations.adjacent.append((number, [match.group(1), match.group(2)], match.group(0)))
        for key in cited_keys(line):
            citations.lines_by_key.setdefault(key, []).append(number)
    return citations


def bibliography_keys(path):
    return {key for _, key, _ in bib_entries(path.read_text(encoding="utf-8"))}


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
    def cited_not_listed(self):
        return sorted(self.cited - self.listed)

    @property
    def listed_not_cited(self):
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
                lines += [f"- [{key}] at {line_list(item.lines_by_key[key])}"
                          for key in sorted(item.lines_by_key)]
                lines.append("")
    return lines


def bibliography_sections(summary):
    lines = ["## Cited but Missing from Bibliography\n"]
    if summary.cited_not_listed:
        lines.append(f"**{len(summary.cited_not_listed)} citation(s) found in the manuscript but not "
                     f"in the bibliography:**\n")
        for key in summary.cited_not_listed:
            places = [f"{item.name} ({line_list(item.lines_by_key[key])})"
                      for item in summary.files_citing(key)]
            lines.append(f"- **[{key}]** in {', '.join(places)}")
        lines.append("")
    else:
        lines.append("All cited keys found in bibliography.\n")
    lines.append("## In Bibliography but Never Cited\n")
    if summary.listed_not_cited:
        lines.append(f"**{len(summary.listed_not_cited)} bibliography entries never cited in "
                     f"any manuscript file:**\n")
        lines += [f"- [{key}]" for key in summary.listed_not_cited]
        lines.append("")
    else:
        lines.append("All bibliography entries are cited.\n")
    return lines


def usage_sections(summary):
    single_use = summary.single_use
    lines = ["## Single-Use Citations\n",
             f"**{len(single_use)} citations appear in only one file** (may indicate weak "
             f"grounding if supporting a major claim):\n"]
    lines += [f"- [{key}] only in {summary.files_citing(key)[0].name}"
              for key in single_use[:SINGLE_USE_SHOWN]]
    if len(single_use) > SINGLE_USE_SHOWN:
        lines.append(f"- ... and {len(single_use) - SINGLE_USE_SHOWN} more")
    lines += ["", "## Most-Cited Sources\n",
              "Sources cited across the most files (authority dependencies):\n",
              "| Citation | Files | Locations |", "|----------|-------|-----------|"]
    for key, count in summary.files_per_key.most_common(MOST_CITED_SHOWN):
        names = ", ".join(item.name for item in summary.files_citing(key))
        lines.append(f"| [{key}] | {count} | {names} |")
    lines.append("")
    overlaps = summary.shared_keys_by_pair()[:OVERLAPS_SHOWN]
    if overlaps:
        lines += ["## Cross-File Citation Overlap\n", "File pairs sharing the most sources:\n",
                  "| File Pair | Shared Citations | Keys |",
                  "|-----------|-----------------|------|"]
        for (first, second), shared in overlaps:
            shown = ", ".join(f"[{key}]" for key in sorted(shared)[:OVERLAP_KEYS_SHOWN])
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
    lines.append(f"**{total} violation(s) found.** Use `[Key1, Key2]` instead of `[Key1][Key2]`:\n")
    for item in summary.files:
        lines += [f"- **{item.name}** L{number}: `{text}` -> `[{', '.join(keys)}]`"
                  for number, keys, text in item.adjacent]
    return lines + [""]


def summary_section(summary):
    return ["## Summary\n",
            f"- Total unique citations: **{len(summary.cited)}**",
            f"- Total bibliography entries: **{len(summary.listed)}**",
            f"- Cited but missing from bibliography: **{len(summary.cited_not_listed)}**",
            f"- In bibliography but never cited: **{len(summary.listed_not_cited)}**",
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


def add_findings(report, summary, whole_book):
    for key in summary.cited_not_listed:
        places = "; ".join(f"{item.name} {line_list(item.lines_by_key[key])}"
                           for item in summary.files_citing(key))
        report.add(key, "cited-not-listed", f"cited in {places}")
    if whole_book:
        for key in summary.listed_not_cited:
            report.add(key, "listed-not-cited", "in the bibliography, cited nowhere")
    for item in summary.files:
        for number, keys, text in item.adjacent:
            report.add(f"{item.name}:{number}", "adjacent-brackets",
                       f"{text} -> [{', '.join(keys)}]")
    for item in summary.density_outliers:
        report.add(item.name, "density-outlier",
                   f"{item.density:.1f} per 1K words, average {summary.average_density:.1f}")


def chosen_files(config, arguments):
    if arguments.files:
        return [(path.resolve(), config.classify(path)[0]) for path in arguments.files]
    kinds = arguments.kind or [kind for kind in MANUSCRIPT_KINDS if kind != KIND_REFERENCES]
    return [(item.path, item.kind) for item in config.manuscript_files(kinds)]


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", type=Path,
                        help="check only these files (the never-cited check needs the whole "
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
    references = config.manuscript.references
    if skipped_for_missing(TOOL, references, "bibliography", arguments.format):
        return 0
    paths = chosen_files(config, arguments)
    if not paths:
        return tool_failed(f"no manuscript files found in {config.manuscript.dir}", TOOL)
    summary = CitationSummary([read_citations(path, kind) for path, kind in paths],
                              bibliography_keys(references))
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(markdown_report(summary, arguments.verbose) + "\n",
                                    encoding="utf-8")
    report = CheckReport(TOOL, CLASSES)
    add_findings(report, summary, whole_book=not arguments.files and not arguments.kind)
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
