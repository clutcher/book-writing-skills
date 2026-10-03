import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import NEW_BOOK, OTHER_BOOK, OTHER_BOOK_RUN, CopyOfBook, run_script

SCRIPT = Path(__file__).resolve().parents[1] / "glossary-seed.py"
INDEX = ".book/runs/2025-04-01-100000/artifacts/definitions-index.md"
OTHER_INDEX = str(OTHER_BOOK_RUN / "artifacts" / "definitions-index.md")


class GlossarySeedTest(unittest.TestCase):
    def test_shouldListNewTermsWhenTheDefinitionsIndexHoldsTermsTheGlossaryLacks(self):
        # when
        run = run_script(SCRIPT, INDEX)

        # then
        self.assertEqual(run.keys_of("new-term"), ["oven spring", "crust colour"])

    def test_shouldFlagADefinitionWhenTheManuscriptDefinesATermTheGlossaryLacks(self):
        # when
        run = run_script(SCRIPT)

        # then
        self.assertEqual(run.keys_of("unregistered-definition"), ["Oven spring"])
        self.assertNotIn("rest window", [key.lower() for key in
                                         run.keys_of("unregistered-definition")])

    def test_shouldLeaveTheGlossaryAloneWhenFixIsNotGiven(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            glossary = book / "vocabulary" / "glossary.md"
            before = glossary.read_text(encoding="utf-8")

            # when
            run_script(SCRIPT, INDEX, book=book)

            # then
            self.assertEqual(glossary.read_text(encoding="utf-8"), before)

    def test_shouldAddDatelessEntriesToCurateWhenFixIsGiven(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            glossary = book / "vocabulary" / "glossary.md"
            before = glossary.read_text(encoding="utf-8")

            # when
            run_script(SCRIPT, INDEX, "--fix", "--section", "## Defined terms", book=book)

            # then
            after = glossary.read_text(encoding="utf-8")
            self.assertIn("### oven spring -- §2\n**Canonical definition:** [TO CURATE]", after)
            self.assertLess(after.index("### crust colour"), after.index("## Usage and drift"))
            self.assertNotRegex(after, r"20\d\d-\d\d-\d\d")
            self.assertNotIn("### oven spring -- §2\n**Canonical definition:** [TO CURATE]\n**Invariants:**",
                             after)
            for line in before.splitlines():
                self.assertIn(line, after)

    def test_shouldFindNothingNewWhenTheSameIndexIsSeededTwice(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            run_script(SCRIPT, INDEX, "--fix", book=book)

            # when
            run = run_script(SCRIPT, INDEX, book=book)

            # then
            self.assertEqual(run.keys_of("new-term"), [])
            self.assertEqual(run.keys_of("unregistered-definition"), [])

    def test_shouldReportAnUnknownLocationWhenANewTermIsNotInTheBookNotation(self):
        # when
        run = run_script(SCRIPT, OTHER_INDEX, book=OTHER_BOOK)

        # then
        self.assertEqual(run.keys_of("new-term"), ["hydration", "levain"])
        self.assertEqual(run.keys_of("location-not-found"), ["levain"])

    def test_shouldFlagADefinitionWhenTheSentenceAfterAHeadingDefinesTheHeading(self):
        # when
        run = run_script(SCRIPT, book=OTHER_BOOK)

        # then
        self.assertEqual(run.keys_of("unregistered-definition"), ["Hydration"])
        self.assertIn("02-rye.md:9", run.message_of("Hydration", "unregistered-definition"))

    def test_shouldFailAndWriteNothingWhenTheSectionIsNotInTheGlossary(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            glossary = book / "vocabulary" / "glossary.md"
            before = glossary.read_text(encoding="utf-8")

            # when
            run = run_script(SCRIPT, INDEX, "--fix", "--section", "## No such section", book=book)

            # then
            self.assertEqual(run.exit_code, 2)
            self.assertIn("no section", run.stderr)
            self.assertEqual(glossary.read_text(encoding="utf-8"), before)

    def test_shouldStartTheGlossaryWithAHeaderWhenTheBookHasNoGlossaryYet(self):
        with CopyOfBook(OTHER_BOOK) as book:
            # given
            glossary = book / "meta" / "terms.md"
            glossary.unlink()
            index = book / "state" / "runs" / "2025-05-01-090000" / "artifacts" / "definitions-index.md"

            # when
            run_script(SCRIPT, str(index), "--fix", book=book)

            # then
            created = glossary.read_text(encoding="utf-8")
            self.assertTrue(created.startswith("# Glossary\n"))
            self.assertIn("### hydration -- Ch2 S2.2\n**Canonical definition:** [TO CURATE]", created)
            self.assertNotRegex(created, r"20\d\d-\d\d-\d\d")


if __name__ == "__main__":
    unittest.main()
