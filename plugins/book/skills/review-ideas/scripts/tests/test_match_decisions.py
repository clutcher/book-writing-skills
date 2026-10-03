import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import (NEW_BOOK, NEW_BOOK_RUN, OTHER_BOOK, OTHER_BOOK_RUN, PLAIN_BOOK,
                         CopyOfBook, run_script)

SCRIPT = Path(__file__).resolve().parents[1] / "match-decisions.py"
STAGE_TWO = str(NEW_BOOK_RUN / "stage-2-attack.md")
STAGE_THREE = str(OTHER_BOOK_RUN / "stage-3-judge.md")


class MatchDecisionsTest(unittest.TestCase):
    def test_shouldMarkTheFindingDecidedWhenItRepeatsADecidedEntry(self):
        # when
        run = run_script(SCRIPT, STAGE_TWO)

        # then
        self.assertEqual(run.keys_of("matches-decided"), ["IC-1"])
        self.assertIn("D-1", run.message_of("IC-1", "matches-decided"))

    def test_shouldAskForARegressionCheckWhenTheFindingMatchesAFixOwed(self):
        # when
        run = run_script(SCRIPT, STAGE_TWO)

        # then
        self.assertEqual(run.keys_of("matches-fix-owed"), ["A-2"])

    def test_shouldCallTheFindingNewWhenNoEntryMatches(self):
        # when
        run = run_script(SCRIPT, STAGE_TWO)

        # then
        self.assertEqual(run.keys_of("new-finding"), ["T-3"])
        self.assertEqual(run.exit_code, 0)

    def test_shouldSayThereIsNoFileWhenTheBookHasNoDecisionsYet(self):
        # when
        run = run_script(SCRIPT, STAGE_TWO, book=PLAIN_BOOK)

        # then
        self.assertEqual(run.keys_of("no-decisions-file"), ["-"])
        self.assertEqual(run.exit_code, 0)

    def test_shouldIgnoreTheRunIdWhenAnOldEntryHasTheSameIdAsAnAlias(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            stage = book / "stage-2-attack.md"
            stage.write_text("#### IC-9: Kneading guidance assumes wheat\n\nRye behaves in "
                             "another way entirely.\n", encoding="utf-8")

            # when
            run = run_script(SCRIPT, str(stage), book=book)

            # then
            self.assertEqual(run.keys_of("new-finding"), ["IC-9"])

    def test_shouldWriteTheTableForStageThreeWhenAReportFileIsGiven(self):
        with CopyOfBook(NEW_BOOK) as book:
            # when
            run_script(SCRIPT, STAGE_TWO, "--report", "decision-matches.md", book=book)

            # then
            table = (book / "decision-matches.md").read_text(encoding="utf-8")
            self.assertIn("| IC-1 | D-1 ", table)
            self.assertIn("- T-3: Kneading guidance assumes wheat", table)

    def test_shouldMatchOnlyTheAddedFindingsWhenAStageThreeFileIsReadWithTheirPrefix(self):
        # when
        run = run_script(SCRIPT, STAGE_THREE, "--id-prefix", "M", book=OTHER_BOOK)

        # then
        self.assertEqual(run.keys_of("matches-decided"), ["M-1"])
        self.assertEqual(run.keys_of("new-finding"), ["M-2"])
        self.assertNotIn("IC-1", [key for key, _, _ in run.findings])

    def test_shouldReadTheDecisionsFromTheConfigWhenTheBookKeepsThemElsewhere(self):
        # when
        run = run_script(SCRIPT, STAGE_THREE, book=OTHER_BOOK)

        # then
        self.assertNotIn("no-decisions-file", [name for _, name, _ in run.findings])
        self.assertIn("D-1", run.message_of("M-1", "matches-decided"))


if __name__ == "__main__":
    unittest.main()
