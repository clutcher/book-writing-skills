#!/usr/bin/env python3
"""Self-check of the review-ideas skill: `--help` and `--self-test` of every script, on the
fixture books only, then readers-self-check.py for the clean room. It never reads or changes a
real book.

Exit 0 when every script passes, 1 when one fails.
"""

import argparse
import os
import subprocess
import sys
sys.dont_write_bytecode = True
from pathlib import Path

SCRIPTS_FOLDER = Path(__file__).resolve().parent
CHECKED_SCRIPTS = ("glossary-seed.py", "match-decisions.py", "sources-for-reviewer.py")
READERS_SELF_CHECK = "readers-self-check.py"


def run_script(script_name, *arguments):
    completed = subprocess.run([sys.executable, str(SCRIPTS_FOLDER / script_name), *arguments],
                               capture_output=True, encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return completed.returncode, completed.stdout + completed.stderr


def check_script(script_name, verbose):
    failures = []
    help_exit, help_output = run_script(script_name, "--help")
    if help_exit != 0 or "usage" not in help_output:
        failures.append(f"{script_name} --help")
    test_exit, test_output = run_script(script_name, "--self-test")
    if test_exit != 0:
        failures.append(f"{script_name} --self-test")
    if verbose or test_exit != 0:
        print(test_output.rstrip())
    last_line = test_output.strip().splitlines()[-1] if test_output.strip() else ""
    print(f"{'FAIL' if failures else 'PASS'}  {script_name}  {last_line}")
    return failures


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="print every test result")
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse_arguments(argv)
    failures = [failure for script_name in CHECKED_SCRIPTS
                for failure in check_script(script_name, arguments.verbose)]
    readers_exit, readers_output = run_script(READERS_SELF_CHECK)
    if arguments.verbose or readers_exit != 0:
        print(readers_output.rstrip())
    print(f"{'FAIL' if readers_exit else 'PASS'}  {READERS_SELF_CHECK}")
    if readers_exit:
        failures.append(READERS_SELF_CHECK)
    if failures:
        print(f"self-check: {len(failures)} failure(s): {', '.join(failures)}")
        return 1
    print("self-check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
