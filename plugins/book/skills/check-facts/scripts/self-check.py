#!/usr/bin/env python3
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
COLLECT_SCRIPTS = SKILL.parent / "collect-sources" / "scripts"
FIXTURES = SKILL / "tests" / "fixtures"
LIB = SKILL.parents[1] / "lib"
sys.path.insert(0, str(LIB))

from command_runs import python_command, run_command

RUNNERS = {"self-check.py"}
SKILL_CHOICES = ("check-facts", "collect-sources")
FIXTURE_BOOKS = ("standard-book/book.yaml", "renamed-book/book.yaml")
STANDARD_BOOK = "standard-book/book.yaml"
STANDARD_BOOK_CHECKS = ("cited-source-check.py",)
FIXTURE_CHECKS = (
    "entry-format-check.py",
    "entry-format-fix.py",
    "list-quotes-join-check.py",
    "files-hash-check.py",
    "ocr-marker-check.py",
    "duplicate-source-check.py",
    "list-bibliography-check.py --no-verdicts",
    "citation-check.py",
    "citation-key-check.py",
    "reference-format-check.py",
    "reference-format-check.py --titles",
    "edition-duplicate-check.py",
    "guardrail-prose-check.py",
    "stale-argument-pointer-check.py",
    "uncited-claim-check.py",
    "quote-in-file-check.py",
    "statistic-integrity-check.py",
    "scan-origin-check.py",
    "scan-marker-sweep.py",
    "restore.py --backup-only",
    "unread-sources.py",
    "manual-downloads.py",
    "match-added-files.py",
    "fetch.py --all --dry-run",
)
LIB_SELF_TESTS = ("check_output.py", "citation_key.py")
MISSING_MANUSCRIPT_FOLDER = "manuscrpt"
MANUSCRIPT_READING_CHECKS = (
    "cited-source-check.py",
    "reference-format-check.py --titles",
    "edition-duplicate-check.py",
    "guardrail-prose-check.py",
    "stale-argument-pointer-check.py",
    "uncited-claim-check.py",
    "duplicate-source-check.py",
)

HELP = """Maintainer check of the check-facts and collect-sources scripts; no book needed.

  A. script self-tests   every script must answer --help with exit 0 and offer --self-test,
                         and every self-test must pass; also the self-tests of the shared lib
  B. fixture books       the checks run against two small books kept with the skill (one
                         with the standard folder names, one with its own folder and file
                         names and a listed file order), copied to a temporary folder; every
                         check must exit 0, and the standard book also runs the cited-source
                         check over its manuscript and thinking files
  C. a book with no sources: only book.yaml and one chapter; every check must say SKIPPED
                         or find nothing, and exit 0
  D. no manuscript file: the standard book with manuscript.dir set to a folder that does
                         not exist; every check that reads the manuscript must say SKIPPED
                         with "no manuscript files at", and exit 0

To check a book, use the run-checks skill (run-checks.py facts).

Nothing gets a short time limit: a killed check prints nothing, which reads like a pass.
The limits are --help 60s and a check 900s; the environment variables HELP_TIMEOUT and
CHECK_TIMEOUT change them."""

EPILOG = "exit codes: 1 on any failure; warnings never fail the run."


def time_limit(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


HELP_TIME_LIMIT = time_limit("HELP_TIMEOUT", 60)
CHECK_TIME_LIMIT = time_limit("CHECK_TIMEOUT", 900)


def parse_arguments(argv):
    parser = argparse.ArgumentParser(prog="self-check.py", description=HELP, epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quiet", action="store_true", help="print failures and warnings only")
    parser.add_argument("--skill", choices=SKILL_CHOICES, default="check-facts",
                        help="the skill whose scripts are checked (default check-facts)")
    return parser.parse_args(argv)


class Tally:
    def __init__(self, quiet):
        self.quiet = quiet
        self.passed = 0
        self.failed = False
        self.warnings = 0

    def say(self, text):
        if not self.quiet:
            print(text, flush=True)

    def section(self, title):
        if not self.quiet:
            print(f"\n{title}", flush=True)

    def ok(self, text):
        self.passed += 1
        self.say(f"  [OK]   {text}")

    def bad(self, text):
        self.failed = True
        print(f"  [FAIL] {text}", flush=True)

    def soft(self, text):
        self.warnings += 1
        print(f"  [WARN] {text}", flush=True)

    def exit_code(self):
        print()
        if self.failed:
            print(f"self-check: FAILED ({self.passed} ok, {self.warnings} warning(s))")
            return 1
        if self.warnings:
            print(f"self-check: passed with {self.warnings} warning(s) ({self.passed} ok)")
            return 0
        print(f"self-check: passed ({self.passed} ok)")
        return 0


def script_path(name):
    own = SCRIPTS / name
    return own if own.is_file() else COLLECT_SCRIPTS / name


def in_chosen_skill(name, chosen_skill):
    if chosen_skill is None:
        return True
    folder = SCRIPTS if chosen_skill == "check-facts" else COLLECT_SCRIPTS
    return (folder / name).is_file()


def checked_scripts(chosen_skill):
    found = sorted((path for folder in (SCRIPTS, COLLECT_SCRIPTS) for path in folder.glob("*.py")
                    if "_" not in path.name and path.name not in RUNNERS),
                   key=lambda path: str(path))
    return [path for path in found if in_chosen_skill(path.name, chosen_skill)]


def label(text):
    return f"{text:<34}"


def script_self_tests(tally, chosen_skill):
    tally.section("== A. Script self-tests (built-in examples) ==")
    candidates = checked_scripts(chosen_skill)
    if not candidates:
        tally.bad(f"no scripts found under {SCRIPTS} or {COLLECT_SCRIPTS}")
    with_self_test = []
    for script in candidates:
        result = run_command(python_command(script, "--help"), HELP_TIME_LIMIT)
        if not result.passed:
            tally.bad(f"{label(script.name)} --help exits {result.exit_code}")
        elif "--self-test" in result.output:
            with_self_test.append(script)
        else:
            tally.bad(f"{label(script.name)} offers no --self-test")
    tally.say(f"  {len(with_self_test)} of {len(candidates)} scripts offer --self-test")
    for script in with_self_test:
        result = run_command(python_command(script, "--self-test"), CHECK_TIME_LIMIT)
        if result.passed:
            tally.ok(f"{label(script.name)} {result.last_line()}")
        elif result.timed_out:
            tally.bad(f"{label(script.name)} TIMED OUT")
        else:
            tally.bad(f"{label(script.name)} exit {result.exit_code} :: {result.last_line()}")
    lib_modules = () if chosen_skill == "collect-sources" else LIB_SELF_TESTS
    for module in lib_modules:
        result = run_command(python_command(LIB / module, "--self-test"), CHECK_TIME_LIMIT)
        if result.passed:
            tally.ok(f"{label('lib/' + module)} {result.last_line()}")
        else:
            tally.bad(f"{label('lib/' + module)} exit {result.exit_code} :: "
                      f"{result.last_line()}")


def fixture_books(tally, chosen_skill):
    tally.section("== B. Fixture books (copied to a temporary folder) ==")
    work = Path(tempfile.mkdtemp(prefix="self-check-"))
    try:
        shutil.copytree(FIXTURES, work, dirs_exist_ok=True)
        for book in FIXTURE_BOOKS:
            book_name = book.split("/")[0]
            checks = FIXTURE_CHECKS + (STANDARD_BOOK_CHECKS if book == STANDARD_BOOK else ())
            for check in checks:
                name, *options = check.split()
                if not in_chosen_skill(name, chosen_skill):
                    continue
                result = run_command(python_command(script_path(name), *options, "--config",
                                                    work / book), CHECK_TIME_LIMIT, cwd=work)
                text = f"{book_name:<13} {check:<34}"
                if result.passed:
                    tally.ok(f"{text} {result.last_line(60)}")
                else:
                    tally.bad(f"{text} exit {result.exit_code} :: {result.last_line(80)}")
            result = run_command(python_command(LIB / "source_registry.py", "--self-test",
                                                "--config", work / book), CHECK_TIME_LIMIT)
            text = f"{book_name:<13} {'lib/source_registry.py --self-test':<34}"
            if result.passed:
                tally.ok(f"{text} {result.last_line(60)}")
            else:
                tally.bad(f"{text} exit {result.exit_code} :: {result.last_line()}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def book_with_no_sources(tally, chosen_skill):
    tally.section("== C. A book with no sources, no thinking folder and no notes ==")
    work = Path(tempfile.mkdtemp(prefix="self-check-bare-"))
    try:
        (work / "book.yaml").write_text("book:\n  title: A Book With No Sources\n",
                                        encoding="utf-8")
        (work / "manuscript").mkdir()
        (work / "manuscript" / "110-chapter-1.md").write_text(
            "# 1 One\n\nA chapter that cites nothing.\n", encoding="utf-8")
        for check in FIXTURE_CHECKS:
            name, *options = check.split()
            if not in_chosen_skill(name, chosen_skill):
                continue
            result = run_command(python_command(script_path(name), *options, "--config",
                                                work / "book.yaml"), CHECK_TIME_LIMIT, cwd=work)
            text = f"{'no sources':<12} {check:<34}"
            if result.passed:
                tally.ok(f"{text} {result.last_line(60)}")
            else:
                tally.bad(f"{text} exit {result.exit_code} :: {result.last_line(80)}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def book_with_no_manuscript_file(tally, chosen_skill):
    tally.section("== D. A book whose manuscript folder holds no file ==")
    work = Path(tempfile.mkdtemp(prefix="self-check-no-manuscript-"))
    try:
        shutil.copytree(FIXTURES, work, dirs_exist_ok=True)
        for check in MANUSCRIPT_READING_CHECKS:
            name, *options = check.split()
            if not in_chosen_skill(name, chosen_skill):
                continue
            result = run_command(python_command(script_path(name), *options, "--config",
                                                work / STANDARD_BOOK, "--set",
                                                f"manuscript.dir={MISSING_MANUSCRIPT_FOLDER}"),
                                 CHECK_TIME_LIMIT, cwd=work)
            text = f"{'no files':<12} {check:<34}"
            last_line = result.last_line(200)
            if result.exit_code == 0 and last_line.startswith("SKIPPED   no manuscript files at"):
                tally.ok(f"{text} {result.last_line(60)}")
            else:
                tally.bad(f"{text} exit {result.exit_code} :: {last_line}")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    arguments = parse_arguments(argv)
    tally = Tally(arguments.quiet)
    script_self_tests(tally, arguments.skill)
    fixture_books(tally, arguments.skill)
    book_with_no_sources(tally, arguments.skill)
    book_with_no_manuscript_file(tally, arguments.skill)
    return tally.exit_code()


if __name__ == "__main__":
    sys.exit(main())
