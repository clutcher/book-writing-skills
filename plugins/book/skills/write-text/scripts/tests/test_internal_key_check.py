import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import CopyOfBook, run_script

SCRIPTS = Path(__file__).resolve().parents[1]
SCRIPT = SCRIPTS / "internal-key-check.py"
SAMPLE_BOOK = SCRIPTS / "fixtures" / "sample-book"
CHAPTER = Path("manuscript") / "110-chapter-1.md"
CHAPTER_KEY = "manuscript/110-chapter-1.md"

TEXT_WITH_KEYS = """# Watering

As D-12 settled, the beds get water at dawn, and finding L3-2 asked for a second season.
"""

KEYS_THE_READER_DOES_NOT_READ = """# Watering

The id `D-12` names the decision in code.

```
L3-2 stays in a code block.
```

> A gardener wrote "D-7 was wrong" in a letter.

The old note "R-4 holds" is quoted. The source [@Abc99, p. 2] and the page [link](notes/D-3.md)
say the same.
"""


class InternalKeyCheckTest(unittest.TestCase):
    def run_on_chapter(self, text, *arguments, settings=""):
        with CopyOfBook(SAMPLE_BOOK) as book:
            (book / CHAPTER).write_text(text, encoding="utf-8")
            if settings:
                with (book / "book.yaml").open("a", encoding="utf-8") as config:
                    config.write(settings)
            return run_script(SCRIPT, "--format", "tsv", *arguments, book=book)

    def test_shouldPassWhenTheTextHoldsNoKey(self):
        # when
        run = run_script(SCRIPT, "--format", "tsv", book=SAMPLE_BOOK)

        # then
        self.assertEqual(run.exit_code, 0, run.stdout + run.stderr)
        self.assertEqual(run.findings, [])

    def test_shouldFindADecisionIdAndAReviewIdWhenTheProseNamesThem(self):
        # when
        run = self.run_on_chapter(TEXT_WITH_KEYS)

        # then
        self.assertEqual(run.exit_code, 1, run.stdout + run.stderr)
        self.assertEqual(run.keys_of("internal-key"), [f"{CHAPTER_KEY}:3", f"{CHAPTER_KEY}:3"])
        self.assertIn("D-12", run.message_of(f"{CHAPTER_KEY}:3", "internal-key"))

    def test_shouldPassWhenTheKeysStandInCodeQuotesCitationsAndLinks(self):
        # when
        run = self.run_on_chapter(KEYS_THE_READER_DOES_NOT_READ)

        # then
        self.assertEqual(run.exit_code, 0, run.stdout + run.stderr)

    def test_shouldFindTheBooksOwnKeyShapeWhenTheConfigNamesIt(self):
        # given
        settings = "\nwriting:\n  internal_key_patterns: ['\\bP\\d+\\b']\n"

        # when
        run = self.run_on_chapter("# Watering\n\nThe beds confirm P4 in the second season.\n",
                                  settings=settings)

        # then
        self.assertEqual(run.keys_of("internal-key"), [f"{CHAPTER_KEY}:3"])

    def test_shouldPassWhenTheTokenIsANameTheBookAllows(self):
        # given
        settings = "\nwriting:\n  internal_key_allow: [K-12]\n"

        # when
        run = self.run_on_chapter("# Watering\n\nSchool gardens serve K-12 pupils.\n",
                                  settings=settings)

        # then
        self.assertEqual(run.exit_code, 0, run.stdout + run.stderr)

    def test_shouldFailWhenTheBooksKeyShapeIsNoRegularExpression(self):
        # when
        run = self.run_on_chapter(TEXT_WITH_KEYS,
                                  settings="\nwriting:\n  internal_key_patterns: ['P(']\n")

        # then
        self.assertEqual(run.exit_code, 2)

    def test_shouldReadOnlyTheGivenFileWhenAPathIsGiven(self):
        # given
        with CopyOfBook(SAMPLE_BOOK) as book:
            draft = book / "draft.md"
            draft.write_text("A draft for the author answers D-4.\n", encoding="utf-8")

            # when
            run = run_script(SCRIPT, "--format", "tsv", str(draft), book=book)

        # then
        self.assertEqual(len(run.keys_of("internal-key")), 1, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
