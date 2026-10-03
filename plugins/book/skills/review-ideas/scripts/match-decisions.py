#!/usr/bin/env python3
"""Match every finding in a review file against the book's decisions.md.

Reads a stage file of a review run (stage-2-attack.md or stage-3-judge.md). A finding starts at a
heading that holds its id, such as `#### A-3: ...` or `### Finding IC-2: NOISE`, and runs to the
next heading. A line that is all bold and starts with an id (`**A-3 -- ...**`) also starts one.
The finding's own run ids are removed before matching, because every run reuses the same ids for
different findings. Each finding is matched with lib/decisions.py (alias first, then keywords), and the
best entry decides what the run may do with it (lib/decisions-format.md).

Findings (exit codes and output shape: lib/check_contract.md):
  matches-decided         advisory       the finding repeats a DECIDED entry: do not report it
  matches-fix-owed        advisory       report it only as a regression check of the agreed fix
  matches-decision-owed   advisory       report it only as a reminder that an answer is owed
  matches-undiscussed     advisory       report it normally, citing the entry
  new-finding             informational  no entry matches; after the run, propose one
  no-decisions-file       informational  the book has no decisions.md yet

A match is a lead, not a verdict: read the entry before acting on it. --report writes the table
that Stage 3 reads (artifacts/decision-matches.md). On a Stage 3 file, --id-prefix M keeps only
the findings Stage 3 added (`#### M-1: ...`) and leaves out the Stage 2 findings it sorted.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import script_tests
from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import ADVISORY, INFORMATIONAL, CheckReport, add_output_arguments, tool_failed
from decisions import match_finding, read_decisions, run_policy

TOOL = "match-decisions"
CLASSES = {
    "matches-decided": ADVISORY,
    "matches-fix-owed": ADVISORY,
    "matches-decision-owed": ADVISORY,
    "matches-undiscussed": ADVISORY,
    "new-finding": INFORMATIONAL,
    "no-decisions-file": INFORMATIONAL,
}
CLASS_BY_ACTION = {
    "silent": "matches-decided",
    "regression-check": "matches-fix-owed",
    "reminder": "matches-decision-owed",
    "normal": "matches-undiscussed",
}
FINDING_ID = r"[A-Z]{1,4}-\d+[a-z]?"
HEADING = re.compile(r"^#{2,6}\s+(.*)$")
BOLD_LINE = re.compile(r"^\*\*(.+?)\*\*\s*$")
FINDING_OPENING = re.compile(rf"^(?:Findings?\s+)?({FINDING_ID}(?:\s*[,/&]\s*{FINDING_ID})*)"
                             rf"\s*[:.\-]*\s*(.*)$")


@dataclass
class Finding:
    ids: list
    title: str
    text: str

    @property
    def label(self):
        return " / ".join(self.ids)

    @property
    def text_without_run_ids(self):
        return re.sub(FINDING_ID, " ", self.text)

    def has_id_prefix(self, prefix):
        return any(finding_id.startswith(f"{prefix}-") for finding_id in self.ids)


def opening_of(line):
    heading = HEADING.match(line)
    bold = BOLD_LINE.match(line)
    candidate = heading.group(1) if heading else bold.group(1) if bold else None
    opening = FINDING_OPENING.match(candidate.strip()) if candidate else None
    return bool(heading), opening


def read_findings(text):
    findings = []
    current = None
    for line in text.split("\n"):
        is_heading, opening = opening_of(line)
        if opening:
            current = Finding(re.findall(FINDING_ID, opening.group(1)),
                              opening.group(2).strip(), opening.group(2))
            findings.append(current)
        elif is_heading:
            current = None
        elif current is not None:
            current.text += "\n" + line
    return findings


def add_findings(report, matched):
    for finding, matches in matched:
        if not matches:
            report.add(finding.label, "new-finding", finding.title or "no entry matches")
            continue
        best = matches[0]
        policy = run_policy(best.entry.status)
        report.add(finding.label, CLASS_BY_ACTION[policy.action],
                   f"{best.entry.id} ({best.entry.status}, score {best.score}): {best.entry.title}")


def markdown_report(matched, decisions_path):
    lines = ["# Findings matched against decisions.md", "",
             f"Decisions file: `{decisions_path}`", "",
             "A match is a lead, not a verdict. Read the entry before acting on it. A finding "
             "that repeats a DECIDED entry is NOISE; cite the entry in one sentence if you "
             "dispute it.", "",
             "| Finding | Entry | Status | What the run may do | Score | Why it matched |",
             "|---|---|---|---|---|---|"]
    for finding, matches in matched:
        for found in matches:
            policy = run_policy(found.entry.status)
            lines.append(f"| {finding.label} | {found.entry.id} {found.entry.title} | "
                         f"{found.entry.status} | {policy.rule} | {found.score} | "
                         f"{found.reason} |")
    new = [finding for finding, matches in matched if not matches]
    lines += ["", "## Findings with no entry", ""]
    lines += [f"- {finding.label}: {finding.title}" for finding in new] or ["- none"]
    return "\n".join(lines)


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage_file", nargs="?", type=Path,
                        help="stage-2-attack.md or stage-3-judge.md of a review run")
    parser.add_argument("--decisions", type=Path, help="decisions file (default: the book's `decisions` setting)")
    parser.add_argument("--threshold", type=float, default=0.25,
                        help="lowest keyword score shown (default 0.25)")
    parser.add_argument("--limit", type=int, default=3, help="entries shown per finding")
    parser.add_argument("--id-prefix", help="match only findings whose id starts with this "
                                            "prefix, such as M for the findings Stage 3 added")
    parser.add_argument("--report", type=Path, help="also write the markdown table here")
    parser.add_argument("--self-test", action="store_true", help="run the tests on the fixtures")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser, parser.parse_args(argv)


def main(argv=None):
    parser, arguments = parse_arguments(argv)
    if arguments.self_test:
        return script_tests.run_self_test(__file__, "test_match_decisions.py")
    if arguments.stage_file is None:
        parser.error("a stage file is required")
    if not arguments.stage_file.is_file():
        return tool_failed(f"no stage file at {arguments.stage_file}", TOOL)
    try:
        config = config_from_args(arguments)
    except ConfigError as error:
        return tool_failed(str(error), TOOL)
    report = CheckReport(TOOL, CLASSES)
    decisions_path = arguments.decisions or config.rules.decisions
    if decisions_path is None or not Path(decisions_path).is_file():
        report.add("-", "no-decisions-file", f"no decisions file at {decisions_path}")
        return report.emit(arguments.format)
    decisions = read_decisions(decisions_path)
    findings = read_findings(arguments.stage_file.read_text(encoding="utf-8"))
    if arguments.id_prefix:
        findings = [finding for finding in findings if finding.has_id_prefix(arguments.id_prefix)]
    matched = [(finding, match_finding(decisions, finding.text_without_run_ids, threshold=arguments.threshold,
                                       limit=arguments.limit, ignore_alias_pattern=FINDING_ID))
               for finding in findings]
    if arguments.report:
        arguments.report.parent.mkdir(parents=True, exist_ok=True)
        arguments.report.write_text(markdown_report(matched, decisions_path) + "\n",
                                    encoding="utf-8")
    add_findings(report, matched)
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
