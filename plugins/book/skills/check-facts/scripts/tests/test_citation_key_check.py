import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import NEW_BOOK, CopyOfBook, run_script

SCRIPT = Path(__file__).resolve().parents[1] / "citation-key-check.py"

BIBLIOGRAPHY_WITH_WRONG_KEYS = """@book{Hale19,
  author = {Hale, Anna},
  title = {Bread at Home},
  year = {2019},
}

@book{Smi05b,
  author = {Smith, Ada},
  title = {Rye Notes},
  year = {2005},
}

@book{Smi05a,
  author = {Smith, Ben},
  title = {Wheat Notes},
  year = {2005},
}

@book{Kel17,
  author = {Keller, Dora},
  title = {Timing the Dough},
  year = {2017},
}
"""

CHAPTER_CITING_WRONG_KEYS = ("Rye first [@Smi05b], wheat second [@Smi05a], "
                             "a home loaf [@Hale19; @Kel17].\n")

THINKING_CITING_A_WRONG_KEY = "Home baking is old, as @Hale19 shows.\n"


def book_with_wrong_keys(book):
    (book / "sources" / "references.bib").write_text(BIBLIOGRAPHY_WITH_WRONG_KEYS,
                                                     encoding="utf-8")
    (book / "manuscript" / "110-chapter-1.md").write_text(CHAPTER_CITING_WRONG_KEYS,
                                                          encoding="utf-8")
    (book / "manuscript" / "010-preface.md").write_text("# Preface\n", encoding="utf-8")
    (book / "manuscript" / "120-chapter-2.md").write_text("# Chapter 2\n", encoding="utf-8")
    thinking = book / "thinking" / "argument"
    thinking.mkdir(parents=True)
    (thinking / "baking.md").write_text(THINKING_CITING_A_WRONG_KEY, encoding="utf-8")
    (book / "sources" / "list.md").write_text(
        "# Sources List\n\n## Entry format\n\n```\n### [<Key>]\n```\n\n"
        "### [Hale19]\n\n**Access URLs:** https://example.org/bread-at-home\n",
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
            thinking = (book / "thinking" / "argument" / "baking.md").read_text(encoding="utf-8")
            bibliography = (book / "sources" / "references.bib").read_text(encoding="utf-8")
            sources_list = (book / "sources" / "list.md").read_text(encoding="utf-8")
            self.assertEqual(run.exit_code, 0, run.stdout + run.stderr)
            self.assertEqual(chapter, "Rye first [@Smi05a], wheat second [@Smi05b], "
                                      "a home loaf [@Hal19; @Kel17].\n")
            self.assertEqual(thinking, "Home baking is old, as @Hal19 shows.\n")
            self.assertIn("@book{Hal19,", bibliography)
            self.assertIn("@book{Smi05a,\n  author = {Smith, Ada}", bibliography)
            self.assertIn("@book{Smi05b,\n  author = {Smith, Ben}", bibliography)
            self.assertIn("### [Hal19]", sources_list)

    def test_shouldRefuseToRenameWhenFixFindsNoManuscriptFiles(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            book_with_wrong_keys(book)
            empty_folder = book / "empty-drafts"
            empty_folder.mkdir()

            # when
            run = run_script(SCRIPT, "--fix", "--manuscript-dir", str(empty_folder), book=book)

            # then
            bibliography = (book / "sources" / "references.bib").read_text(encoding="utf-8")
            self.assertEqual(run.exit_code, 2, run.stdout + run.stderr)
            self.assertEqual(bibliography, BIBLIOGRAPHY_WITH_WRONG_KEYS)

    def test_shouldLeaveANameWithNoLatinLettersForAPersonWhenNoKeyCanBeBuilt(self):
        with CopyOfBook(NEW_BOOK) as book:
            # given
            (book / "sources" / "references.bib").write_text(
                "@book{Iva99,\n  author = {Иванов, Иван},\n  title = {Хлеб},\n"
                "  year = {1999},\n}\n", encoding="utf-8")

            # when
            run = run_script(SCRIPT, "--format", "tsv", book=book)

            # then
            self.assertEqual(run.keys_of("key-rename"), [])
            self.assertEqual(run.keys_of("org-or-unparsed"), ["Iva99"])

    def test_shouldPassWhenEveryKeyIsTheLabelOfItsNames(self):
        # when
        run = run_script(SCRIPT, "--format", "tsv")

        # then
        self.assertEqual(run.exit_code, 0, run.stdout + run.stderr)
        self.assertEqual(run.findings, [])


if __name__ == "__main__":
    unittest.main()
