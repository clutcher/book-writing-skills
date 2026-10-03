#!/usr/bin/env python3
import argparse
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS.parents[2] / 'lib'))
sys.path.insert(0, str(SCRIPTS))

from check_output import DEFECT, INFORMATIONAL, CheckReport, add_output_arguments

TOOL = 'cover-self-check'
CLASSES = {'case-failed': DEFECT, 'case-passed': INFORMATIONAL, 'case-skipped': INFORMATIONAL}


class CollectingResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.passed = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.append(test)


def case_name(test):
    return test.id().rsplit('.', 1)[-1]


def main():
    parser = argparse.ArgumentParser(
        description='Run the cover scripts against the fixture book in scripts/tests/fixtures. '
                    'Uses no real book and no network; the fixture is copied to a temporary '
                    'folder first. Tests that need an SVG renderer are skipped, and said so, '
                    'when none is installed.')
    add_output_arguments(parser)
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover(str(SCRIPTS / 'tests'), top_level_dir=str(SCRIPTS / 'tests'))
    result = CollectingResult()
    suite.run(result)
    report = CheckReport(TOOL, CLASSES)
    for test in result.passed:
        report.add(case_name(test), 'case-passed', 'as expected')
    for test, reason in result.skipped:
        report.add(case_name(test), 'case-skipped', reason)
    for test, trace in result.failures + result.errors:
        report.add(case_name(test), 'case-failed', trace.strip().splitlines()[-1])
    return report.emit(args.format)


if __name__ == '__main__':
    sys.exit(main())
