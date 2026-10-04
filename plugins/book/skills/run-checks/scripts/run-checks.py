#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS.parents[2] / "lib"))
sys.path.insert(0, str(SCRIPTS))

import grading
from book_config import ConfigError, load_config, start_folder
from check_output import run_main
from check_list import ALL, GROUPS, MISSING_IN_A_PAPER, MODES, ON_PATHS, checks_of
from command_runs import python_command, run_command
from run_folders import changed_files, record_checksums, start_run
from source_files import markdown_files_under

SKILL = "run-checks"
REPORT_FILE = "report.md"
RESULTS_FILE = "results.json"

DESCRIPTION = """Run every script check of the book plugin on one book, grouped and graded, with a
report in a run folder.

Modes (the part of the book checked):
  all (default)  every group below
  text           the prose checks of write-text, the glossary, the code font, the open notes,
                 Vale; for a paper also the paper check and the arXiv bundle check
  facts          citation keys, the .bib, the sources list and quotes bank, the library;
                 every @Key in the manuscript and the thinking files must be in the .bib and
                 the sources list and have a library copy or a needed.txt line
  cover          colors, fonts, text placement and the KDP template of the cover design
  sales-text     the selling texts agree, the store description and the keywords
  setup          book.yaml is valid, the decisions index is current, the outside tools are
                 installed

A paper (kind: paper in book.yaml) has no cover and no sales text: those groups say SKIPPED.

The scripts stay in the skill that owns them; this runs them where they are.

Grading. Every finding is reported until it is fixed; there are no accepted counts. A check
that prints the JSON report is a finding when it holds any DEFECT or ADVISORY item; its
INFORMATIONAL items (an expected state, a worklist) are counted and shown, never a finding. A
check without the JSON report is read by its exit code: exit 1 is a finding. A check whose
tool or feature is missing says SKIPPED, with the reason.

Fast by default. The slow library checks (quote-in-file, statistic-integrity, scan-origin,
scan-marker-sweep) read every library file and run only with --slow. Link and metadata
checks use the network and are never run here.

--fix rebuilds what is generated (the decisions index).

The report goes into <work.runs>/<YYYY-MM-DD-HHMM>-run-checks-<mode>/ (report.md and
results.json; the newest three runs per mode are kept), unless --no-report."""

EPILOG = """exit codes: 0 every check passed or was skipped, 1 a check found something,
2 a check could not run (or the book config cannot be read)."""

OK = "OK"
SKIP = "SKIP"
FIND = "FIND"
FAIL = "FAIL"
STATES = (FAIL, FIND, OK, SKIP)
TERMINAL_WIDTH = 100
PYTHON_CRASH_MARK = "Traceback (most recent call last)"


def time_limit(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


CHECK_TIME_LIMIT = time_limit("CHECK_TIMEOUT", 900)
SLOW_TIME_LIMIT = time_limit("SLOW_TIMEOUT", 3600)


@dataclass
class Result:
    check: object
    state: str
    summary: str
    report: dict = None
    output: str = ""
    problems: list = field(default_factory=list)

    def as_dict(self):
        return {"group": self.check.group, "skill": self.check.skill, "check": self.check.label,
                "state": self.state, "summary": self.summary, "problems": self.problems,
                "report": self.report, "output": None if self.report else self.output}


def parse_arguments(argv):
    parser = argparse.ArgumentParser(prog="run-checks.py", description=DESCRIPTION,
                                     epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", nargs="?", default=ALL, choices=MODES,
                        help="the part of the book to check (default all)")
    parser.add_argument("paths", nargs="*", metavar="PATH",
                        help="text mode: the files or folders the path checks read")
    parser.add_argument("--config", metavar="FILE", help="the book's book.yaml")
    parser.add_argument("--set", dest="config_overrides", action="append", default=[],
                        metavar="KEY=VALUE", help="override one config value (repeatable)")
    parser.add_argument("--slow", action="store_true",
                        help="also run the slow checks that read every library file")
    parser.add_argument("--fix", action="store_true",
                        help="rebuild what is generated (the decisions index)")
    parser.add_argument("--only-changed", action="store_true",
                        help="text mode: the path checks read only the files changed since "
                             "the last run of the same mode")
    parser.add_argument("--no-vale", action="store_true", help="do not run Vale")
    parser.add_argument("--no-report", action="store_true", help="write no run folder")
    parser.add_argument("--quiet", action="store_true", help="print only what did not pass")
    return parser.parse_args(argv)


def config_arguments(config, overrides, takes_set):
    found = []
    if config.config_file:
        found += ["--config", str(config.config_file)]
    if takes_set:
        for override in overrides:
            found += ["--set", override]
    return found


def missing_feature(check, config):
    for missing in check.needs:
        reason = missing(config)
        if reason:
            return reason
    return None


def skip_reason(check, config, arguments):
    if config.is_paper and check.group in MISSING_IN_A_PAPER:
        return MISSING_IN_A_PAPER[check.group]
    if check.slow and not arguments.slow:
        return "slow: it reads every library file; pass --slow"
    if check.uses_vale and arguments.no_vale:
        return "--no-vale given"
    return missing_feature(check, config)


def graded_result(check, run):
    try:
        report = json.loads(run.output)
    except ValueError:
        return Result(check, FAIL, "the check did not print its JSON report", output=run.output)
    if report.get("skipped"):
        return Result(check, SKIP, report["skipped"], report)
    grade = grading.grade(report)
    state = FIND if grade.state == grading.FOUND else OK
    return Result(check, state, grade.summary, report, problems=grade.findings)


def last_line_with_words(output):
    lines = [line.strip() for line in output.splitlines() if any(c.isalnum() for c in line)]
    return lines[-1] if lines else ""


def exit_code_result(check, run):
    last = last_line_with_words(run.output)
    if run.exit_code == 0:
        return Result(check, SKIP if last.startswith("SKIPPED") else OK, last, output=run.output)
    return Result(check, FIND, last, output=run.output, problems=[last])


def run_one(check, book, arguments, paths):
    limit = SLOW_TIME_LIMIT if check.slow else CHECK_TIME_LIMIT
    command = python_command(check.path, *config_arguments(book, arguments.config_overrides,
                                                          check.takes_set),
                             *check.arguments(arguments.fix),
                             *(("--format", "json") if check.graded else ()),
                             *(paths if check.reach == ON_PATHS else ()))
    run = run_command(command, limit, cwd=book.root, keep_error_output=not check.graded)
    return result_of_run(check, run, limit)


def result_of_run(check, run, limit):
    if run.timed_out:
        return Result(check, FAIL, f"TIMED OUT after {limit}s; empty output is not a pass")
    if run.exit_code not in (0, 1) or crashed(run):
        reason = last_line_with_words(run.error_output or run.output)
        return Result(check, FAIL, f"the tool failed (exit {run.exit_code}): {reason}",
                      output=run.output + run.error_output)
    if check.graded:
        return graded_result(check, run)
    return exit_code_result(check, run)


def crashed(run):
    return run.exit_code != 0 and PYTHON_CRASH_MARK in run.output + run.error_output


class Printer:
    def __init__(self, quiet, book_root):
        self.quiet = quiet
        self.book_root = str(book_root)
        self.group = None

    def show(self, result):
        if self.quiet and result.state in (OK, SKIP):
            return
        if result.check.group != self.group:
            self.group = result.check.group
            print(f"\n== {self.group} ==", flush=True)
        print(f"  [{result.state:<4}] {result.check.label:<44} {self.shortened(result.summary)}",
              flush=True)

    def shortened(self, summary):
        text = (summary or "").replace(self.book_root + os.sep, "").replace(self.book_root, ".")
        if len(text) <= TERMINAL_WIDTH:
            return text
        half = (TERMINAL_WIDTH - 5) // 2
        return f"{text[:half]} ... {text[-half:]}"


def given_files(arguments):
    return [path for name in arguments.paths for path in markdown_files_under(name)]


def path_targets(book, arguments):
    files = given_files(arguments) if arguments.paths else [
        item.path for item in book.manuscript_files()]
    if not arguments.only_changed:
        return [str(path) for path in arguments.paths], files
    changed = changed_files(book.work.runs, SKILL, arguments.mode, files, book.root)
    return [str(path) for path in changed], files


def run_checks(book, arguments):
    paths, recorded = path_targets(book, arguments)
    printer = Printer(arguments.quiet, book.root)
    results = []
    for check in checks_of(arguments.mode):
        reason = skip_reason(check, book, arguments)
        if reason is None and arguments.only_changed and check.reach == ON_PATHS and not paths:
            reason = "no file changed since the last run"
        result = Result(check, SKIP, reason) if reason else run_one(check, book, arguments,
                                                                    paths)
        printer.show(result)
        results.append(result)
    return results, recorded


def report_text(book, arguments, results, started):
    lines = [f"# run-checks {arguments.mode}", "",
             f"- Book: {book.root}",
             f"- Started: {started:%Y-%m-%d %H:%M}",
             f"- Slow checks: {'run' if arguments.slow else 'not run (pass --slow)'}",
             "", "| State | Count |", "|---|---|"]
    for state in STATES:
        lines.append(f"| {state} | {sum(1 for result in results if result.state == state)} |")
    for group in GROUPS:
        chosen = [result for result in results if result.check.group == group]
        if not chosen:
            continue
        lines += ["", f"## {group}", "", "| State | Check | Skill | Result |", "|---|---|---|---|"]
        for result in chosen:
            summary = result.summary.replace("|", "\\|")
            lines.append(f"| {result.state} | `{result.check.label}` | {result.check.skill} | "
                         f"{summary} |")
    lines += ["", "Full items of every graded check: results.json. Run one script by hand for "
                  "its full text report.", ""]
    return "\n".join(lines)


def write_report(book, arguments, results, started, recorded):
    folder = start_run(book.work.runs, SKILL, arguments.mode, started)
    (folder / REPORT_FILE).write_text(report_text(book, arguments, results, started),
                                      encoding="utf-8")
    (folder / RESULTS_FILE).write_text(
        json.dumps([result.as_dict() for result in results], indent=1) + "\n", encoding="utf-8")
    record_checksums(folder, recorded, book.root)
    return folder


def exit_code(results):
    states = {result.state for result in results}
    counts = ", ".join(f"{sum(1 for result in results if result.state == state)} {state}"
                       for state in STATES)
    print(f"\nrun-checks: {counts}")
    if FAIL in states:
        return 2
    return 1 if FIND in states else 0


def main(argv=None):
    arguments = parse_arguments(argv)
    try:
        book = load_config(arguments.config, start_folder(arguments.paths),
                           arguments.config_overrides)
    except ConfigError as error:
        print(f"run-checks: cannot read the book config: {error}", file=sys.stderr)
        return 2
    started = datetime.datetime.now()
    print(f"book: {book.root}", flush=True)
    results, recorded = run_checks(book, arguments)
    if not arguments.no_report:
        try:
            print(f"report: {write_report(book, arguments, results, started, recorded)}"
                  f"/{REPORT_FILE}")
        except (OSError, ConfigError, ValueError) as error:
            print(f"report: could not write it: {error}", file=sys.stderr)
    return exit_code(results)


if __name__ == "__main__":
    run_main(main)
