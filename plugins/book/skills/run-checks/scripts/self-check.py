#!/usr/bin/env python3
import argparse
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS.parents[2] / "lib"))

from check_list import CHECKS, RUN_CHECKS

DESCRIPTION = """Maintainer check for the run-checks skill; no real book is read.

  1. every script the check list names exists in the folder of the skill that owns it
     and no check is listed twice
  2. the tests in scripts/tests: the grading of one report, and runs of every mode
     on small test books made in a temporary folder"""

EPILOG = "exit codes: 0 all passed, 1 a check failed."


def listed_scripts_exist():
    problems = []
    seen = set()
    for check in CHECKS:
        if not check.path.is_file():
            problems.append(f"{check.label}: no script at {check.path}")
        if (check.group, check.label) in seen:
            problems.append(f"{check.label}: listed twice in {check.group}")
        seen.add((check.group, check.label))
        if check.skill == RUN_CHECKS and check.path.parent != SCRIPTS:
            problems.append(f"{check.label}: not in this skill's scripts folder")
    if not problems:
        print(f"  [OK]   {len(CHECKS)} listed checks, each in its own skill")
    return problems


def tests_pass():
    suite = unittest.TestLoader().discover(str(SCRIPTS / "tests"), pattern="test_*.py",
                                           top_level_dir=str(SCRIPTS / "tests"))
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    if result.wasSuccessful() and result.testsRun:
        print(f"  [OK]   {result.testsRun} tests")
        return []
    return [f"tests failed ({len(result.failures)} failures, {len(result.errors)} errors)"]


def main(argv=None):
    argparse.ArgumentParser(prog="self-check.py", description=DESCRIPTION, epilog=EPILOG,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)
    problems = listed_scripts_exist() + tests_pass()
    for problem in problems:
        print(f"  [FAIL] {problem}")
    print(f"self-check: {'FAILED' if problems else 'passed'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
