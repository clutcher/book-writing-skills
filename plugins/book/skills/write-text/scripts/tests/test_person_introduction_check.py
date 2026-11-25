import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import NEW_BOOK, CopyOfBook

SCRIPT = Path(__file__).resolve().parents[1] / "person-introduction-check.py"
SAMPLE_BOOK = SCRIPT.parent / "fixtures" / "sample-book"


class PersonIntroductionCheckTest(unittest.TestCase):
    def test_shouldPrintTheReportWhenTheOutputCannotHoldLineDrawing(self):
        # when
        completed = subprocess.run([sys.executable, str(SCRIPT)], cwd=NEW_BOOK,
                                   capture_output=True,
                                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                                        "PYTHONIOENCODING": "cp1252"})

        # then
        self.assertIn(completed.returncode, (0, 1), completed.stderr)
        self.assertNotIn(b"UnicodeEncodeError", completed.stderr)
        self.assertIn("PERSON INTRODUCTION CHECK", completed.stdout.decode("utf-8"))

    def test_shouldAcceptASurnameWithItsCitationWhenTheVoiceAsksForIt(self):
        # when
        run = run_check(SAMPLE_BOOK, "--set", "writing.person_first_mention=surname_with_citation")

        # then
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertNotIn("BARE_SURNAME", run.stdout)

    def test_shouldFlagABareSurnameWhenTheVoiceAsksForACitationAndNoneFollows(self):
        with CopyOfBook(SAMPLE_BOOK) as book:
            # given
            chapter = book / "manuscript" / "110-chapter-1.md"
            chapter.write_text(chapter.read_text(encoding="utf-8").replace(" [@Riv19]", ""),
                               encoding="utf-8")
            (book / "manuscript" / "120-chapter-2.md").write_text(
                "# Chapter 2\n\nThe source of the claim is [@Riv19].\n", encoding="utf-8")

            # when
            run = run_check(book, "--set", "writing.person_first_mention=surname_with_citation")

        # then
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("or a citation of their work", run.stdout)

    def test_shouldFlagABareSurnameWhenTheVoiceAsksForTheFullName(self):
        # when
        run = run_check(SAMPLE_BOOK)

        # then
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("BARE_SURNAME", run.stdout)

    def test_shouldFailWhenTheVoiceNamesAnUnknownFirstMentionChoice(self):
        # when
        run = run_check(SAMPLE_BOOK, "--set", "writing.person_first_mention=initials")

        # then
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)


def run_check(book, *arguments):
    return subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=book,
                          capture_output=True, encoding="utf-8",
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


if __name__ == "__main__":
    unittest.main()
