import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "run-checks.py"

LIST_TEXT = """# Sources list

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
```

### [Smi99] Smith, "Kitchen Gardens" (1999)

**Full title:** Kitchen Gardens
**Authors:** Smith, J.
**Year:** 1999
"""

QUOTES_TEXT = """# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Verified quotes:** exact strings, in quotation marks
**Source:** see `sources/list.md`
```

---

### [Smi99] Smith, "Kitchen Gardens" (1999)

**Verified quotes:**
- p. 3: "Beans need full sun"
**Source:** see `sources/list.md`
"""

REFERENCES_TEXT = """# References

[Smi99] Smith, J. (1999). *Kitchen Gardens*. Example Press. ISBN 9780000000002.
"""

DECISIONS_TEXT = """# Decisions

## Index

| Id | Status | Title |
|---|---|---|

## Details

## D-1 Keep short chapter titles

- **Status:** DECIDED / no change
- **Aliases:** none
- **Idea:** x
- **Decision:** y
- **Change:** None
- **Why:** z
- **Decided:** 2025-04-01
- **Refs:** None
"""


class RunChecksTest(unittest.TestCase):
    def setUp(self):
        self.book = Path(tempfile.mkdtemp(prefix="run-checks-test-"))
        self.write("book.yaml", "version: 1\nbook:\n  title: A Test Book\n  author: Sam Example\n")
        self.write("manuscript/110-chapter-1.md",
                   "# Chapter 1: Sun\n\nBeans need full sun for most of the day, so a bed under "
                   "a tree gives a poor crop [Smi99]. A sunny bed lets the plants flower early. "
                   "A shady one makes them grow tall and thin.\n")
        self.write("manuscript/900-references.md", REFERENCES_TEXT)
        self.write("sources/list.md", LIST_TEXT)
        self.write("sources/quotes.md", QUOTES_TEXT)
        self.write("sources/library/Smi99.txt", "Beans need full sun.\n")
        self.write("thinking/argument/sun.md", "Shade slows the crop [Lee05].\n")
        self.write("rules/decisions.md", DECISIONS_TEXT)

    def tearDown(self):
        shutil.rmtree(self.book, ignore_errors=True)

    def write(self, name, text):
        path = self.book / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_checks(self, *arguments):
        completed = subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=self.book,
                                   capture_output=True, encoding="utf-8", errors="replace",
                                   stdin=subprocess.DEVNULL,
                                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        return completed.returncode, completed.stdout

    def line_of(self, output, check):
        return next(line for line in output.splitlines() if f"] {check} " in line + " ")

    def test_shouldFindAThinkingKeyWhenTheSourcesListHasNoEntryForIt(self):
        # when
        exit_code, output = self.run_checks("facts", "--no-report")

        # then
        self.assertIn("[FIND] cited-source-check.py", output)
        self.assertIn("not-in-list 1", self.line_of(output, "cited-source-check.py"))
        self.assertEqual(exit_code, 1)

    def test_shouldFindALineAnchorIntoTheBookWhenItSitsInADoubtsFile(self):
        # given
        self.write("thinking/doubts/open-questions.md",
                   "# Open questions\n\nIs the claim at 110-chapter-1.md:3 too strong?\n")

        # when
        exit_code, output = self.run_checks("facts", "--no-report")

        # then
        self.assertIn("line-anchor 1", self.line_of(output, "stale-argument-pointer-check.py"))
        self.assertEqual(exit_code, 1)

    def test_shouldFindABookOwnedKeyWhenADoubtsFileCitesTheSourceUnderAnotherKey(self):
        # given
        self.write("thinking/doubts/counterarguments.md",
                   "# Counterarguments\n\nSome say beans grow anywhere [Smith99].\n\n"
                   "## References\n\n"
                   "[Smith99] Smith, J. (1999). *Kitchen Gardens*. Example Press.\n")

        # when
        exit_code, output = self.run_checks("facts", "--no-report")

        # then
        self.assertIn("book-owned 1", self.line_of(output, "argument-key-check.py"))
        self.assertEqual(exit_code, 1)

    def test_shouldSkipTheBibliographyChecksWhenTheBookHasNoBibliography(self):
        # given
        (self.book / "manuscript" / "900-references.md").unlink()

        # when
        exit_code, output = self.run_checks("facts", "--no-report")

        # then
        self.assertIn("[SKIP] reference-sort.py", output)
        self.assertNotIn("[FAIL]", output)

    def test_shouldStillFindAFindingWhenAnOldAcceptedFlagsFileListsIt(self):
        # given
        self.write("rules/accepted-flags.json", '{"cited-source-check": {"not-in-list": 1}}\n')

        # when
        exit_code, output = self.run_checks("facts", "--no-report")

        # then
        self.assertIn("[FIND] cited-source-check.py", output)
        self.assertEqual(exit_code, 1)

    def test_shouldAskToDeleteAnOldAcceptedFlagsFileWhenTheSetupIsChecked(self):
        # given
        self.write("rules/accepted-flags.json", "{}\n")

        # when
        _, output = self.run_checks("setup", "--no-report")

        # then
        self.assertIn("unused-file 1", self.line_of(output, "book_config.py check"))

    def test_shouldPassAndShowTheCountWhenACheckReportsOnlyAnExpectedState(self):
        # given
        self.write("thinking/argument/sun.md", "Shade slows the crop [Smi99].\n")
        (self.book / "sources" / "library" / "Smi99.txt").unlink()
        self.write(".book/sources-to-add/needed.txt", "Smi99\n")

        # when
        _, output = self.run_checks("facts", "--no-report")

        # then
        self.assertIn("[OK  ] cited-source-check.py", output)
        self.assertIn("waits-in-needed 1", self.line_of(output, "cited-source-check.py"))

    def test_shouldRunTheSlowLibraryChecksOnlyWhenAskedTo(self):
        # when
        _, output = self.run_checks("facts", "--no-report")

        # then
        self.assertIn("pass --slow", self.line_of(output, "quote-in-file-check.py"))

    def test_shouldFindAStaleDecisionsIndexAndRebuildItWithFix(self):
        # given
        exit_code_before, output_before = self.run_checks("setup", "--no-report")

        # when
        self.run_checks("setup", "--fix", "--no-report")

        # then
        self.assertIn("index-stale", self.line_of(output_before, "decisions.py check"))
        self.assertEqual(exit_code_before, 1)
        self.assertIn("| D-1 | DECIDED / no change | Keep short chapter titles |",
                      (self.book / "rules" / "decisions.md").read_text())

    def test_shouldSkipTheCoverAndSalesTextWhenTheBookHasNone(self):
        # when
        exit_code, output = self.run_checks("cover", "--no-report")

        # then
        self.assertIn("the book has no cover design", self.line_of(output, "color-check.py"))
        self.assertEqual(exit_code, 0)

    def test_shouldWriteAReportIntoARunFolder(self):
        # when
        self.run_checks("setup")

        # then
        reports = list((self.book / ".book" / "runs").glob("*-run-checks-setup/report.md"))
        self.assertEqual(len(reports), 1)
        self.assertIn("## setup", reports[0].read_text())

    def test_shouldFindAProseCheckEveryTimeItExitsWithFlags(self):
        # given
        self.write("manuscript/120-chapter-2.md",
                   "# Chapter 2: Short\n\nOne sentence only.\n\nAnother short one.\n")
        _, first = self.run_checks("text", "--no-vale", "--no-report")

        # when
        exit_code, output = self.run_checks("text", "--no-vale", "--no-report")

        # then
        self.assertIn("[FIND]", self.line_of(first, "sentence-and-paragraph-check.py"))
        self.assertIn("[FIND]", self.line_of(output, "sentence-and-paragraph-check.py"))
        self.assertEqual(exit_code, 1)

    def test_shouldShowAPathInsideTheBookRelativeToTheBookInTheTerminal(self):
        # given
        self.write("sources/list.md", "# Sources list\n")

        # when
        _, output = self.run_checks("all", "--no-report", "--no-vale")

        # then
        self.assertNotIn(str(self.book) + os.sep, output.split("\n", 1)[1])

    def test_shouldCheckOnlyTheChangedFilesWhenAskedTo(self):
        # given
        self.run_checks("text", "--no-vale")

        # when
        _, output = self.run_checks("text", "--no-vale", "--only-changed")

        # then
        self.assertIn("no file changed since the last run",
                      self.line_of(output, "unclear-this-check.py"))


if __name__ == "__main__":
    unittest.main()
