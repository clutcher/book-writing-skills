import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import OTHER_BOOK, PLAIN_BOOK, CopyOfBook, run_script

SCRIPT = Path(__file__).resolve().parents[1] / "citation-check.py"


class CitationCheckTest(unittest.TestCase):
    def test_shouldReportAMissingEntryWhenAKeyIsCitedButNotListed(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("not-in-bibliography"), ["Nob20"])
        self.assertEqual(run.exit_code, 1)

    def test_shouldCountAnUncitedEntryAsInformationWhenTheBibliographyTracksIt(self):
        with CopyOfBook(PLAIN_BOOK) as book:
            # given
            bibliography = book / "sources" / "references.bib"
            bibliography.write_text(bibliography.read_text(encoding="utf-8")
                                    + "\n@book{Unw18,\n  author = {Unwin, Clara},\n"
                                      "  title = {A Book Nobody Cites},\n  year = {2018},\n}\n",
                                    encoding="utf-8")

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.keys_of("not-cited"), ["Unw18"])
            self.assertEqual(run.exit_code, 0)

    def test_shouldCountTheCitationWhenItCarriesAPageNumber(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertNotIn("Kel17", run.keys_of("not-cited"))

    def test_shouldCountThePrefaceWhenItCitesAKey(self):
        with CopyOfBook(PLAIN_BOOK) as book:
            # given
            (book / "manuscript" / "110-chapter-1.md").write_text("# Chapter 1: Starting\n",
                                                                  encoding="utf-8")
            (book / "manuscript" / "040-preface.md").write_text("Bakers agree with @Hal19.\n",
                                                                encoding="utf-8")

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.keys_of("not-cited"), [])

    def test_shouldAskForOneBracketWhenTwoKeysSitInAdjacentBrackets(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("adjacent-brackets"), ["110-chapter-1.md:3"])
        self.assertIn("[@Hal19; @Mor21]", run.message_of("110-chapter-1.md:3", "adjacent-brackets"))

    def test_shouldIgnoreKeysWhenTheyAppearInsideCode(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertNotIn("Fake01", run.stdout)

    def test_shouldPassWhenEveryCitationMatchesTheBibliography(self):
        # when
        run = run_script(SCRIPT, book=PLAIN_BOOK)

        # then
        self.assertEqual(run.exit_code, 0)
        self.assertEqual(run.keys_of("not-in-bibliography") + run.keys_of("not-cited"), [])

    def test_shouldWriteTheStageTwoReportWhenAReportFileIsGiven(self):
        with CopyOfBook(PLAIN_BOOK) as book:
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
        self.assertEqual(run.keys_of("not-in-bibliography"), ["Vey20"])
        self.assertEqual(run.keys_of("not-cited"), ["Old11"])

    def test_shouldReportAnOldCitationWhenABracketHoldsAKnownKeyWithoutTheAtSign(self):
        with CopyOfBook(PLAIN_BOOK) as book:
            # given
            (book / "manuscript" / "120-chapter-2.md").write_text(
                "# Chapter 2: Time\n\nA long rest makes an even crumb [Hal19, p. 4].\n",
                encoding="utf-8")

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.keys_of("old-citation"), ["120-chapter-2.md:3"])
            self.assertIn("[@Hal19, p. 4]", run.message_of("120-chapter-2.md:3", "old-citation"))
            self.assertEqual(run.exit_code, 1)

    def test_shouldReportAnOldGroupWhenItsKeysAreInTheSourcesList(self):
        with CopyOfBook(PLAIN_BOOK) as book:
            # given
            (book / "sources" / "list.md").write_text(
                "# Sources List\n\n## Entry format\n\n```\n### [<Key>]\n```\n\n---\n\n### [Rye08]\n\n**Access URLs:** "
                "https://example.org/rye\n", encoding="utf-8")
            (book / "manuscript" / "120-chapter-2.md").write_text(
                "# Chapter 2: Time\n\nBakers agree [Hal19, Rye08].\n", encoding="utf-8")

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertIn("[@Hal19; @Rye08]",
                          run.message_of("120-chapter-2.md:3", "old-citation"))

    def test_shouldLeaveBracketsAloneWhenTheyHoldNoKnownKeyOrSitInCode(self):
        with CopyOfBook(PLAIN_BOOK) as book:
            # given
            (book / "manuscript" / "120-chapter-2.md").write_text(
                "# Chapter 2: Time\n\nFold twice [see below], then write `[Hal19]` in the "
                "log and read [Hal19](https://example.org/hal).\n", encoding="utf-8")

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.keys_of("old-citation"), [])
            self.assertEqual(run.exit_code, 0)

    def test_shouldReportHandWrittenReferencesWhenTheReferencesFileHoldsAList(self):
        with CopyOfBook(PLAIN_BOOK) as book:
            # given
            (book / "manuscript" / "900-references.md").write_text(
                "# References\n\n[Hal19] Hale, A. *Even Dough*. 2019.\n\n::: {#refs}\n:::\n",
                encoding="utf-8")

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.keys_of("hand-written-references"), ["900-references.md"])
            self.assertIn("first at line 3",
                          run.message_of("900-references.md", "hand-written-references"))
            self.assertEqual(run.exit_code, 1)

    def test_shouldAcceptTheReferencesFileWhenItHoldsOnlyTheHeadingTheDivAndRawCode(self):
        with CopyOfBook(PLAIN_BOOK) as book:
            # given
            (book / "manuscript" / "900-references.md").write_text(
                "```{=latex}\n\\backmatter\n```\n\n# References\n\n::: {#refs}\n:::\n",
                encoding="utf-8")

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.keys_of("hand-written-references"), [])
            self.assertEqual(run.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
