import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import CopyOfBook, run_script

SCRIPTS = Path(__file__).resolve().parents[1]
SCRIPT = SCRIPTS / "paper-check.py"
SAMPLE_PAPER = SCRIPTS / "fixtures" / "sample-paper"
SAMPLE_BOOK = SCRIPTS / "fixtures" / "sample-book"

INTRODUCTION_WITHOUT_LIST = """# Introduction

Many people water a small garden when they come home. We ask how much the time of watering
changes the water the soil keeps, and we answer it with one season of data.
"""

UNREFERENCED_TABLE = """

| Month | Rain |
|---|---|
| May | 40 mm |

Table: Rain in each month. {#tbl:rain}
"""


class PaperCheckTest(unittest.TestCase):
    def run_on_copy(self, change):
        with CopyOfBook(SAMPLE_PAPER) as paper:
            change(paper)
            return run_script(SCRIPT, book=paper)

    def test_shouldPassWhenThePaperHasEveryPartAReaderLooksFor(self):
        # when
        run = run_script(SCRIPT, book=SAMPLE_PAPER)

        # then
        self.assertEqual(run.exit_code, 0, run.stdout)
        self.assertEqual(run.keys_of("abstract-length"), ["010-abstract.md"])
        self.assertIn("35 of 40 words", run.message_of("010-abstract.md", "abstract-length"))

    def test_shouldFindALongAbstractWhenItHasMoreWordsThanTheLimit(self):
        # when
        run = self.run_on_copy(lambda paper: (paper / "manuscript" / "010-abstract.md").write_text(
            "# Abstract\n\n" + "water " * 41 + "\n", encoding="utf-8"))

        # then
        self.assertEqual(run.exit_code, 1)
        self.assertIn("41 words", run.message_of("010-abstract.md", "abstract-too-long"))

    def test_shouldFindAnEmptyAbstractWhenItHoldsOnlyAHeading(self):
        # when
        run = self.run_on_copy(lambda paper: (paper / "manuscript" / "010-abstract.md").write_text(
            "# Abstract\n", encoding="utf-8"))

        # then
        self.assertEqual(run.keys_of("abstract-empty"), ["010-abstract.md"])

    def test_shouldFindAMissingAbstractWhenTheFileIsGone(self):
        # when
        run = self.run_on_copy(lambda paper: (paper / "manuscript" / "010-abstract.md").unlink())

        # then
        self.assertEqual(run.keys_of("abstract-missing"), ["abstract"])

    def test_shouldFindNoContributionListWhenTheIntroductionHasNoNumberedList(self):
        # when
        run = self.run_on_copy(lambda paper: (paper / "manuscript" / "020-introduction.md")
                               .write_text(INTRODUCTION_WITHOUT_LIST, encoding="utf-8"))

        # then
        self.assertEqual(run.keys_of("no-contribution-list"), ["020-introduction.md"])

    def test_shouldFindAFigureWhenNoSentencePointsToIt(self):
        # when
        run = self.run_on_copy(lambda paper: replace_in(
            paper / "manuscript" / "030-method.md", "as Figure 1 shows", "as the plan shows"))

        # then
        self.assertEqual(run.keys_of("figure-not-referenced"), ["030-method.md:6"])
        self.assertIn("Figure 1 is never", run.message_of("030-method.md:6",
                                                          "figure-not-referenced"))

    def test_shouldAcceptAFigureWhenItsLabelIsUsedInTheText(self):
        # when
        run = run_script(SCRIPT, book=SAMPLE_PAPER)

        # then
        self.assertEqual(run.keys_of("figure-not-referenced"), [])

    def test_shouldFindATableWhenNeitherItsNumberNorItsLabelIsUsed(self):
        # when
        run = self.run_on_copy(lambda paper: append_to(
            paper / "manuscript" / "030-method.md", UNREFERENCED_TABLE))

        # then
        self.assertEqual(run.keys_of("table-not-referenced"), ["030-method.md:18"])
        self.assertIn("Table 2 (tbl:rain)", run.message_of("030-method.md:18",
                                                           "table-not-referenced"))

    def test_shouldAcceptTwoTablesWhenOneSentenceNamesBothNumbers(self):
        # when
        run = self.run_on_copy(lambda paper: (
            append_to(paper / "manuscript" / "030-method.md", UNREFERENCED_TABLE),
            replace_in(paper / "manuscript" / "030-method.md", "Table 1 lists",
                       "Tables 1 and 2 list")))

        # then
        self.assertEqual(run.keys_of("table-not-referenced"), [])

    def test_shouldFindNoThreatsSectionWhenNoHeadingNamesThem(self):
        # when
        run = self.run_on_copy(lambda paper: replace_in(
            paper / "manuscript" / "040-threats-to-validity.md", "# Threats to Validity",
            "# Discussion"))

        # then
        self.assertEqual(run.keys_of("no-threats-section"), ["threats"])

    def test_shouldAcceptALimitationsSectionAsTheThreatsToValidity(self):
        # when
        run = self.run_on_copy(lambda paper: replace_in(
            paper / "manuscript" / "040-threats-to-validity.md", "# Threats to Validity",
            "# Limitations"))

        # then
        self.assertEqual(run.keys_of("no-threats-section"), [])

    def test_shouldSkipWhenTheBookIsNotAPaper(self):
        # when
        run = run_script(SCRIPT, "--format", "json", book=SAMPLE_BOOK)

        # then
        self.assertEqual(run.exit_code, 0)
        self.assertIn("a book has no abstract", json.loads(run.stdout)["skipped"])


def replace_in(path, old, new):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"{old!r} is not in {path}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def append_to(path, text):
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
