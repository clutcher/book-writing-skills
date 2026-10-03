import sys
import unittest
from pathlib import Path


def run_self_test(script_file, test_file_name):
    tests_folder = Path(script_file).resolve().parent / "tests"
    suite = unittest.TestLoader().discover(str(tests_folder), pattern=test_file_name,
                                           top_level_dir=str(tests_folder))
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    passed = result.wasSuccessful() and result.testsRun > 0
    print(f"self-test: {'PASS' if passed else 'FAIL'} ({result.testsRun} tests)")
    return 0 if passed else 1
