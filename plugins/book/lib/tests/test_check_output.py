import io
import os
import subprocess
import sys
import unittest

from support import LIB, NEW_BOOK, TemporaryBook, run_script

from check_output import (ADVISORY, DEFECT, EXIT_CLEAN, EXIT_DEFECTS, INFORMATIONAL,
                          CheckReport)

CRASHING_CHECK = """import sys
sys.path.insert(0, {lib!r})
from check_output import run_main


def main():
    print("chapter 1 \u2500 checked")
    return {{}}["manuscript"]


run_main(main)
"""


def run_python_file(path, encoding):
    return subprocess.run([sys.executable, str(path)], capture_output=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                               "PYTHONIOENCODING": encoding})


class CheckOutputTest(unittest.TestCase):
    def test_should_pass_its_own_self_test(self):
        # when
        result = run_script("check_output.py", "--self-test")

        # then
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_should_exit_clean_when_only_worklists_and_advice_are_found(self):
        # given
        report = CheckReport("demo", {"queue": INFORMATIONAL, "maybe": ADVISORY})

        # when
        report.add("Smi99", "queue", "not read yet")
        report.add("Jon74", "maybe", "check this pairing")

        # then
        self.assertEqual(report.exit_code(), EXIT_CLEAN)

    def test_should_count_every_defect_when_one_class_is_found_twice(self):
        # given
        report = CheckReport("demo", {"duplicate-group": DEFECT})

        # when
        report.add("Smi99", "duplicate-group", "two printings of one book")
        report.add("Smi99b", "duplicate-group", "two printings of one book")

        # then
        self.assertEqual(report.exit_code(), EXIT_DEFECTS)
        self.assertTrue(report.render().endswith("TOTAL     2 defects, 0 informational, 0 advisory"))

    def test_should_print_only_items_when_format_is_tsv(self):
        # given
        report = CheckReport("demo", {"hash-stale": DEFECT})
        report.add("Smi99", "hash-stale", "changed")

        # then
        self.assertEqual(report.render("tsv"), "Smi99\thash-stale\tchanged")

    def test_should_skip_and_exit_clean_when_the_book_does_not_use_the_feature(self):
        # given
        report = CheckReport("glossary-check", {"undefined-term": DEFECT})
        missing = NEW_BOOK / "rules" / "glossary.md"

        # when
        skipped = report.skip_unless_present(missing, "glossary")

        # then
        self.assertTrue(skipped)
        self.assertEqual(report.exit_code(), EXIT_CLEAN)
        self.assertEqual(report.render(), f"SKIPPED   the book has no glossary ({missing} not found)")

    def test_should_run_when_the_book_uses_the_feature(self):
        # given
        report = CheckReport("decisions", {"no-status": DEFECT})

        # when
        skipped = report.skip_unless_present(NEW_BOOK / "rules" / "decisions.md", "decisions file")

        # then
        self.assertFalse(skipped)
        self.assertIsNone(report.skipped_reason)

    def test_should_name_the_skip_on_the_error_stream_when_format_is_tsv(self):
        # given
        report = CheckReport("glossary-check", {"undefined-term": DEFECT})
        report.skip("the book has no glossary (rules/glossary.md not found)")
        items, errors = io.StringIO(), io.StringIO()

        # when
        exit_code = report.emit("tsv", items, errors)

        # then
        self.assertEqual(exit_code, EXIT_CLEAN)
        self.assertEqual(items.getvalue(), "")
        self.assertEqual(errors.getvalue(),
                         "SKIPPED   the book has no glossary (rules/glossary.md not found)\n")

    def test_should_fail_as_a_tool_in_one_line_when_a_check_crashes(self):
        with TemporaryBook() as folder:
            # given
            script = folder / "crashing-check.py"
            script.write_text(CRASHING_CHECK.format(lib=str(LIB)), encoding="utf-8")

            # when
            result = run_python_file(script, "cp1252")

        # then
        errors = result.stderr.decode("utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertIn("\u2500", result.stdout.decode("utf-8"))
        self.assertNotIn("Traceback", errors)
        self.assertEqual(len(errors.strip().splitlines()), 1)
        self.assertIn("crashing-check: the tool failed: KeyError: 'manuscript'", errors)

    def test_should_print_help_when_asked(self):
        # then
        self.assertEqual(run_script("check_output.py", "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
