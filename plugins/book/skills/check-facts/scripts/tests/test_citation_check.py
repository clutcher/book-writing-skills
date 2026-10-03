import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import OLD_BOOK, OTHER_BOOK, CopyOfBook, run_script

SCRIPT = Path(__file__).resolve().parents[1] / "citation-check.py"


class CitationCheckTest(unittest.TestCase):
    def test_shouldReportAMissingEntryWhenAKeyIsCitedButNotListed(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("cited-not-listed"), ["Nob20"])
        self.assertEqual(run.exit_code, 1)

    def test_shouldReportAnUnusedEntryWhenTheBibliographyListsAKeyNobodyCites(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("listed-not-cited"), ["Unu18"])

    def test_shouldCountTheCitationWhenItCarriesAPageNumber(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertNotIn("Kel17", run.keys_of("listed-not-cited"))

    def test_shouldCountThePrefaceWhenItCitesAKey(self):
        with CopyOfBook(OLD_BOOK) as book:
            # given
            (book / "manuscript" / "110-chapter-1.md").write_text("# Chapter 1: Starting\n",
                                                                  encoding="utf-8")
            (book / "manuscript" / "040-preface.md").write_text("Bakers agree [Hal19].\n",
                                                                encoding="utf-8")

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.keys_of("listed-not-cited"), [])

    def test_shouldAskForOneBracketWhenTwoKeysSitInAdjacentBrackets(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("adjacent-brackets"), ["110-chapter-1.md:3"])
        self.assertIn("[Hal19, Mor21]", run.message_of("110-chapter-1.md:3", "adjacent-brackets"))

    def test_shouldIgnoreKeysWhenTheyAppearInsideCode(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertNotIn("Fake01", run.stdout)

    def test_shouldPassWhenEveryCitationMatchesTheBibliography(self):
        # when
        run = run_script(SCRIPT, book=OLD_BOOK)

        # then
        self.assertEqual(run.exit_code, 0)
        self.assertEqual(run.keys_of("cited-not-listed") + run.keys_of("listed-not-cited"), [])

    def test_shouldWriteTheStageTwoReportWhenAReportFileIsGiven(self):
        with CopyOfBook(OLD_BOOK) as book:
            # when
            run_script(SCRIPT, "--report", "citation-report.md", book=book)

            # then
            report = (book / "citation-report.md").read_text(encoding="utf-8")
            self.assertIn("# Citation-Bibliography Check Report", report)
            self.assertIn("| 110-chapter-1.md |", report)
            self.assertIn("- Manuscript files checked: **3**", report)

    def test_shouldReadTheBibliographyFromTheConfigWhenTheBookUsesOtherFolderNames(self):
        # when
        run = run_script(SCRIPT, book=OTHER_BOOK)

        # then
        self.assertEqual(run.keys_of("cited-not-listed"), ["Vey20"])
        self.assertEqual(run.keys_of("listed-not-cited"), ["Old11"])


if __name__ == "__main__":
    unittest.main()
