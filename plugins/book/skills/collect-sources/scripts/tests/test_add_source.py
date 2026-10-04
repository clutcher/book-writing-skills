import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SCRIPT = TESTS.parent / "add-source.py"
sys.path.insert(0, str(TESTS.parents[3] / "lib"))

from bibliography import read_bibliography
from source_registry import read_bank

BOOK_YAML = "version: 1\nbook:\n  title: A Small Bread Book\n  author: Sam Example\n"

SOURCES_LIST = """# Sources List

## Entry format

```
### [<Key>]

**Access URLs:** where the source can be read
```

---

### [Mil08]

**Access status:** MANUAL FETCH REQUIRED (gate)

---
"""

BIBLIOGRAPHY = """@article{Mil08,
  author = {Miller, Hannah},
  title = {Crumb Structure in Long Fermented Sourdough},
  journal = {Journal of Bread Science},
  year = {2008},
}
"""

HALE_BOOK = ["--type", "book", "--field", "author=Hale, Ruth", "--field", "title=Bread at Home",
             "--field", "publisher=Example Press", "--field", "year=2019"]


class SmallBook:
    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="add-source-")).resolve()
        (self.root / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
        (self.root / "sources").mkdir()
        self.list_path = self.root / "sources" / "list.md"
        self.bibliography_path = self.root / "sources" / "references.bib"
        self.list_path.write_text(SOURCES_LIST, encoding="utf-8")
        self.bibliography_path.write_text(BIBLIOGRAPHY, encoding="utf-8")
        return self

    def __exit__(self, *exception):
        shutil.rmtree(self.root, ignore_errors=True)
        return False

    def run(self, *arguments):
        completed = subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=self.root,
                                   capture_output=True, encoding="utf-8", errors="replace",
                                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.output = completed.stdout + completed.stderr
        return completed.returncode


class AddSourceTest(unittest.TestCase):
    def test_shouldWriteIdentityToTheBibAndAccessToTheListWhenFixIsGiven(self):
        with SmallBook() as book:
            # when
            exit_code = book.run(*HALE_BOOK, "--access-url", "https://example.org/hale", "--fix")

            # then
            self.assertEqual(exit_code, 0, book.output)
            entry = read_bibliography(book.bibliography_path).entry("Hal19")
            self.assertEqual(entry.field("title"), "Bread at Home")
            self.assertEqual(entry.field("publisher"), "Example Press")
            listed = read_bank(book.list_path).entry("Hal19")
            self.assertEqual(listed.field_names(), ["Access URLs"])
            self.assertEqual(listed.identity_problems(), [])
            self.assertEqual(read_bank(book.list_path).keys, ["Hal19", "Mil08"])

    def test_shouldOnlyShowBothEntriesWhenRunWithoutFix(self):
        with SmallBook() as book:
            # when
            exit_code = book.run(*HALE_BOOK)

            # then
            self.assertEqual(exit_code, 0, book.output)
            self.assertIn("@book{Hal19,", book.output)
            self.assertIn("### [Hal19]", book.output)
            self.assertEqual(book.bibliography_path.read_text(encoding="utf-8"), BIBLIOGRAPHY)
            self.assertEqual(book.list_path.read_text(encoding="utf-8"), SOURCES_LIST)

    def test_shouldRefuseAKeyThatTheNamesDoNotGive(self):
        with SmallBook() as book:
            # when
            exit_code = book.run(*HALE_BOOK, "--key", "Hale2019", "--fix")

            # then
            self.assertEqual(exit_code, 1)
            self.assertIn("give the key Hal19", book.output)
            self.assertEqual(book.bibliography_path.read_text(encoding="utf-8"), BIBLIOGRAPHY)

    def test_shouldAcceptALetterThatTellsTwoWorksWithOneLabelApart(self):
        with SmallBook() as book:
            # when
            exit_code = book.run(*HALE_BOOK, "--key", "Hal19a", "--fix")

            # then
            self.assertEqual(exit_code, 0, book.output)
            self.assertIn("Hal19a", read_bibliography(book.bibliography_path).keys)

    def test_shouldRefuseAKeyAlreadyInTheBib(self):
        with SmallBook() as book:
            # when
            exit_code = book.run("--type", "article", "--field", "author=Miller, Hannah",
                                 "--field", "title=Another Crumb Paper", "--field", "year=2008",
                                 "--fix")

            # then
            self.assertEqual(exit_code, 1)
            self.assertIn("Mil08 is already in", book.output)

    def test_shouldRefuseAnEntryWithNoAuthorOrEditor(self):
        with SmallBook() as book:
            # when
            exit_code = book.run("--field", "title=A page with no author", "--fix")

            # then
            self.assertEqual(exit_code, 1)
            self.assertIn("no author or editor", book.output)

    def test_shouldStartBothFilesWhenTheBookHasNeither(self):
        with SmallBook() as book:
            # given
            book.list_path.unlink()
            book.bibliography_path.unlink()

            # when
            exit_code = book.run(*HALE_BOOK, "--fix")

            # then
            self.assertEqual(exit_code, 0, book.output)
            self.assertEqual(read_bibliography(book.bibliography_path).keys, ["Hal19"])
            self.assertEqual(read_bank(book.list_path).keys, ["Hal19"])

    def test_shouldRefuseAValueThatClosesTheEntryEarly(self):
        with SmallBook() as book:
            # when
            exit_code = book.run(*HALE_BOOK, "--field", "note=Bread}, url = {https://example.org",
                                 "--fix")

            # then
            self.assertEqual(exit_code, 1)
            self.assertIn("braces that do not pair up", book.output)
            self.assertEqual(book.bibliography_path.read_text(encoding="utf-8"), BIBLIOGRAPHY)
            self.assertEqual(book.list_path.read_text(encoding="utf-8"), SOURCES_LIST)

    def test_shouldRefuseAValueWithAnUnclosedBrace(self):
        with SmallBook() as book:
            # when
            exit_code = book.run(*HALE_BOOK, "--field", "note=Printed in {Example", "--fix")

            # then
            self.assertEqual(exit_code, 1)
            self.assertIn("braces that do not pair up", book.output)
            self.assertEqual(book.bibliography_path.read_text(encoding="utf-8"), BIBLIOGRAPHY)

    def test_shouldRefuseAFieldNameThatIsNotABibtexName(self):
        with SmallBook() as book:
            # when
            exit_code = book.run(*HALE_BOOK, "--field", "note}, url = {x=https://example.org",
                                 "--fix")

            # then
            self.assertEqual(exit_code, 1)
            self.assertIn("is not a field name", book.output)
            self.assertEqual(book.bibliography_path.read_text(encoding="utf-8"), BIBLIOGRAPHY)

    def test_shouldRefuseAnEntryTypeThatIsNotLettersOnly(self):
        with SmallBook() as book:
            # when
            exit_code = book.run("--type", "book{Evil99,", "--field", "author=Hale, Ruth",
                                 "--field", "title=Bread at Home", "--field", "year=2019",
                                 "--fix")

            # then
            self.assertEqual(exit_code, 1)
            self.assertIn("is not an entry type", book.output)
            self.assertEqual(book.bibliography_path.read_text(encoding="utf-8"), BIBLIOGRAPHY)

    def test_shouldTakeAChosenKeyWhenTheNamesHoldNoLatinLetters(self):
        with SmallBook() as book:
            # when
            exit_code = book.run("--type", "book", "--field", "author=Петренко, Олена",
                                 "--field", "title=Хліб удома", "--field", "year=2016",
                                 "--key", "Pet16", "--fix")

            # then
            self.assertEqual(exit_code, 0, book.output)
            self.assertIn("Pet16", read_bibliography(book.bibliography_path).keys)
            self.assertIn("Pet16", read_bank(book.list_path).keys)

    def test_shouldAskForAKeyWhenTheNamesHoldNoLatinLettersAndNoneIsGiven(self):
        with SmallBook() as book:
            # when
            exit_code = book.run("--type", "book", "--field", "author=Петренко, Олена",
                                 "--field", "title=Хліб удома", "--field", "year=2016", "--fix")

            # then
            self.assertEqual(exit_code, 1)
            self.assertIn("--key", book.output)
            self.assertEqual(book.bibliography_path.read_text(encoding="utf-8"), BIBLIOGRAPHY)


if __name__ == "__main__":
    unittest.main()
