#!/usr/bin/env python3
import argparse
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1] / "tests"


def main():
    parser = argparse.ArgumentParser(
        prog="self-check.py",
        description="Run the revise-from-notes skill's own tests against its fixture book only. "
                    "It never reads or changes a real book.")
    parser.add_argument("--quiet", action="store_true", help="print only the summary")
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    suite = unittest.defaultTestLoader.discover(str(TESTS), top_level_dir=str(TESTS))
    result = unittest.TextTestRunner(verbosity=1 if args.quiet else 2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
