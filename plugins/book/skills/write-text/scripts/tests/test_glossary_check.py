import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import OLD_BOOK, OTHER_BOOK, CopyOfBook, run_script

SCRIPT = Path(__file__).resolve().parents[1] / "glossary-check.py"


class GlossaryCheckTest(unittest.TestCase):
    def test_shouldFlagEarlyUseWhenAChapterUsesATermBeforeItsDefinitionChapter(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("used-before-defined"), ["rest window"])
        self.assertIn("110-chapter-1.md:3", run.message_of("rest window", "used-before-defined"))

    def test_shouldNotFlagEarlyUseWhenOnlyThePrefacePreviewsTheTerm(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertNotIn("even dough", run.keys_of("used-before-defined"))
        self.assertNotIn("even dough", run.keys_of("never-found"))

    def test_shouldReportNeverFoundWhenNoSearchFormAppearsInTheBook(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("never-found"), ["crumb map"])

    def test_shouldReportLocationNotFoundWhenTheHeadingNamesNoManuscriptFile(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("location-not-found"), ["timing (word discipline)"])

    def test_shouldFindTheQualifiedTermWhenTheHeadingHasTwoSeparators(self):
        # when
        new_book_run = run_script(SCRIPT)
        old_book_run = run_script(SCRIPT, book=OLD_BOOK)

        # then
        self.assertNotIn("rise speed", new_book_run.keys_of("never-found"))
        self.assertNotIn("strong flour", old_book_run.keys_of("never-found"))

    def test_shouldReadTheChapterNotationWhenTheBookKeepsItsSettingsInClaudeMd(self):
        # when
        run = run_script(SCRIPT, book=OLD_BOOK)

        # then
        self.assertEqual(run.exit_code, 0)
        self.assertEqual(run.keys_of("used-before-defined"), ["rest window"])

    def test_shouldNeverGateWhenOnlyAdvisoryFindingsExist(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.exit_code, 0)
        self.assertTrue(run.stdout.rstrip().endswith("0 defects, 1 informational, 2 advisory"))

    def test_shouldSkipTheEarlyUseCheckWhenOnlySomeFilesAreChecked(self):
        # when
        run = run_script(SCRIPT, "manuscript/110-chapter-1.md")

        # then
        self.assertEqual(run.keys_of("used-before-defined"), [])

    def test_shouldWriteTheMarkdownReportWhenAReportFileIsGiven(self):
        with CopyOfBook(OLD_BOOK) as book:
            # when
            run_script(SCRIPT, "--report", "glossary-report.md", "--verbose", book=book)

            # then
            report = (book / "glossary-report.md").read_text(encoding="utf-8")
            self.assertIn("- Used before defined (flagged): **1**", report)
            self.assertIn("### strong flour", report)
            self.assertIn("Post-definition context windows", report)

    def test_shouldSkipWithoutFailingWhenTheBookHasNoGlossaryYet(self):
        with CopyOfBook(OLD_BOOK) as book:
            # given
            (book / "review" / "glossary-registry.md").unlink()

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.exit_code, 0)
            self.assertIn("SKIPPED", run.stdout)
            self.assertIn("no glossary yet", run.stdout)

    def test_shouldNotReportNeverFoundWhenOnlySomeFilesAreChecked(self):
        # when
        run = run_script(SCRIPT, "manuscript/110-chapter-1.md")

        # then
        self.assertEqual(run.keys_of("never-found"), [])

    def test_shouldReadTheChapterWhenTheLocationWritesItWithADot(self):
        # when
        run = run_script(SCRIPT, book=OTHER_BOOK)

        # then
        self.assertEqual(run.keys_of("used-before-defined"), ["sour rye"])
        self.assertIn("01-starter.md:3", run.message_of("sour rye", "used-before-defined"))

    def test_shouldReportLocationNotFoundWhenTheLocationWordIsOnlyPartOfAFileNameWord(self):
        # when
        run = run_script(SCRIPT, book=OTHER_BOOK)

        # then
        self.assertEqual(run.keys_of("location-not-found"), ["timing"])
        self.assertNotIn("starter", run.keys_of("location-not-found"))

if __name__ == "__main__":
    unittest.main()
