import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import NEW_BOOK, CopyOfBook, run_script

SCRIPT = Path(__file__).resolve().parents[1] / "citation-key-check.py"

REFERENCES_WITH_WRONG_KEYS = """# References

[Hale19] Hale, A. (2019). *Bread at Home*. Example Press.

[Smi05b] Smith, A. (2005). *Rye Notes*. Example Press.

[Smi05a] Smith, B. (2005). *Wheat Notes*. Example Press.

[Kel17] Keller, D. (2017). *Timing the Dough*. Example Press.

[Nob20] Noble, E. (2020). *Oven Spring*. Example Press.
"""

CHAPTER_CITING_WRONG_KEYS = "Rye first [Smi05b], wheat second [Smi05a], a home loaf [Hale19, Kel17].\n"


def book_with_wrong_keys(book):
    (book / "manuscript" / "900-references.md").write_text(REFERENCES_WITH_WRONG_KEYS,
                                                           encoding="utf-8")
    (book / "manuscript" / "110-chapter-1.md").write_text(CHAPTER_CITING_WRONG_KEYS,
                                                          encoding="utf-8")


class CitationKeyCheckTest(unittest.TestCase):
    def test_shouldReportRenamesWithoutWritingWhenFixIsNotGiven(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            book_with_wrong_keys(book)

            # when
            run = run_script(SCRIPT, book=book)

            # then
            self.assertEqual(run.exit_code, 1, run.stdout + run.stderr)
            self.assertEqual(sorted(run.keys_of("key-rename")), ["Hale19", "Smi05a", "Smi05b"])
            self.assertEqual((book / "manuscript" / "110-chapter-1.md").read_text(encoding="utf-8"),
                             CHAPTER_CITING_WRONG_KEYS)

    def test_shouldRenameKeysEverywhereWhenFixIsGiven(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            book_with_wrong_keys(book)

            # when
            run = run_script(SCRIPT, "--fix", book=book)

            # then
            chapter = (book / "manuscript" / "110-chapter-1.md").read_text(encoding="utf-8")
            references = (book / "manuscript" / "900-references.md").read_text(encoding="utf-8")
            self.assertEqual(run.exit_code, 0, run.stdout + run.stderr)
            self.assertEqual(chapter, "Rye first [Smi05a], wheat second [Smi05b], "
                                      "a home loaf [Hal19, Kel17].\n")
            self.assertIn("[Hal19] Hale, A. (2019)", references)
            self.assertIn("[Smi05a] Smith, A. (2005)", references)
            self.assertIn("[Smi05b] Smith, B. (2005)", references)

    def test_shouldRefuseToRenameWhenFixFindsNoManuscriptFiles(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            book_with_wrong_keys(book)
            empty_folder = book / "empty-drafts"
            empty_folder.mkdir()

            # when
            run = run_script(SCRIPT, "--fix", "--manuscript-dir", str(empty_folder), book=book)

            # then
            references = (book / "manuscript" / "900-references.md").read_text(encoding="utf-8")
            self.assertEqual(run.exit_code, 2, run.stdout + run.stderr)
            self.assertEqual(references, REFERENCES_WITH_WRONG_KEYS)

    def test_shouldLeaveANameWithNoLatinLettersForAPersonWhenNoKeyCanBeBuilt(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            (book / "manuscript" / "900-references.md").write_text(
                "# References\n\n[Iva99] Иванов, И. (1999). *Хлеб*. Example Press.\n",
                encoding="utf-8")

            # when
            run = run_script(SCRIPT, "--format", "tsv", book=book)

            # then
            self.assertEqual(run.keys_of("key-rename"), [])
            self.assertEqual(run.keys_of("org-or-unparsed"), ["Iva99"])


if __name__ == "__main__":
    unittest.main()
