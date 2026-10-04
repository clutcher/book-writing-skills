import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SCRIPT = TESTS.parent / "match-added-files.py"
sys.path.insert(0, str(TESTS))
sys.path.insert(0, str(TESTS.parents[3] / "lib"))

from book_config import load_config
from pdf_fixtures import write_scanned_pdf, write_text_pdf
from source_files import FETCH, OCR, folders_from_config

HAS_PDFTOTEXT = shutil.which("pdftotext") is not None
HAS_OCR = all(shutil.which(tool) for tool in ("tesseract", "pdftoppm", "pdfinfo"))

BOOK_YAML = "version: 1\nbook:\n  title: A Small Bread Book\n  author: Sam Example\nwork: .book\n"

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

### [Ols19]

**Access URLs:** https://example.org/salt-and-gluten

---

### [Ros15]

**Note:** a library copy

---

### [Web21]

**Note:** no copy known

---
"""

BIBLIOGRAPHY = """@article{Mil08,
  author = {Miller, Hannah},
  title = {Crumb Structure in Long Fermented Sourdough},
  journal = {Journal of Bread Science},
  year = {2008},
  doi = {10.5555/crumb.2008.17},
}

@article{Ols19,
  author = {Olsen, Peter},
  title = {Salt Levels and Gluten Networks in Wheat Dough},
  journal = {Journal of Bread Science},
  year = {2019},
  doi = {10.5555/salt.2019.4},
}

@book{Ros15,
  author = {Rossi, Giulia},
  title = {The Chemistry of Slow Fermentation},
  publisher = {Example Press},
  year = {2015},
  isbn = {9780306406157},
}

@misc{Web21,
  author = {Weber, Lena},
  title = {Measuring Oven Spring in Home Ovens},
  year = {2021},
}
"""

QUOTES_BANK = """# Quotes Bank

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)

**Verified quotes:** "a string the header must not be searched for at all"
```

---

### [Mil08] Miller, "Crumb Structure" (2008)

**Verified quotes:** "an open crumb follows from a long and cool first rise of the dough" and
"bakers who shorten the rise get a tight and even crumb every time"

---

### [Ros15] Rossi, "Slow Fermentation" (2015)

**Verified quotes:** "acetic acid builds up when the dough rests at a low temperature"

---

### [Web21] Weber, "Oven Spring" (2021)

**Verified quotes:** "steam in the first ten minutes adds most of the oven spring we measured"

---
"""

NEEDED = ("# Sources to download by hand.\n"
          "Mil08 | Crumb Structure in Long Fermented Sourdough | Hannah Miller | 2008 | "
          "https://doi.org/10.5555/crumb.2008.17\n"
          "Web21 | Measuring Oven Spring in Home Ovens | Lena Weber | 2021 | no link known\n")

FILLER = ["Further notes on flour, water, salt and time, kept here to fill the page number %d."
          % number for number in range(60)]


def paper(title, author, opening, body):
    return [title, author, ""] + opening + [""] + body + FILLER


MILLER_BODY = ["We found that an open crumb follows from a long and cool first rise",
               "of the dough, while bakers who shorten the rise get a tight and even",
               "crumb every time they bake."]
MILLER_WITH_DOI = paper("Crumb Structure in Long Fermented Sourdough", "Hannah Miller",
                        ["Journal of Bread Science, doi:10.5555/crumb.2008.17"], MILLER_BODY)
MILLER_WITHOUT_DOI = paper("Crumb Structure in Long Fermented Sourdough", "Hannah Miller",
                           ["Journal of Bread Science"], MILLER_BODY)
MILLER_OTHER_TEXT = paper("Crumb Structure in Long Fermented Sourdough", "Hannah Miller",
                          ["A talk given to a baking club"],
                          ["This talk is about rye, and says nothing on the first rise."])
OLSEN = paper("Salt Levels and Gluten Networks in Wheat Dough", "Peter Olsen",
              ["https://doi.org/10.5555/salt.2019.4"], ["Salt makes the gluten network stronger."])
ROSSI = paper("The Chemistry of Slow Fermentation", "Giulia Rossi",
              ["ISBN 978-0-306-40615-7"],
              ["In a cold room, acetic acid builds up when the dough rests at a low",
               "temperature, and the bread tastes more sour."])
UNKNOWN = paper("A Short History of Rye Bread", "Tom Baker", [], ["Rye was the bread of the north."])


class AddedFilesBook:
    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="added-files-")).resolve()
        (self.root / "book.yaml").write_text(BOOK_YAML, encoding="utf-8")
        (self.root / "sources").mkdir()
        (self.root / "sources" / "list.md").write_text(SOURCES_LIST, encoding="utf-8")
        (self.root / "sources" / "references.bib").write_text(BIBLIOGRAPHY, encoding="utf-8")
        (self.root / "sources" / "quotes.md").write_text(QUOTES_BANK, encoding="utf-8")
        self.config = load_config(str(self.root / "book.yaml"))
        self.folders = folders_from_config(self.config)
        self.to_add = Path(self.config.sources.to_add)
        self.to_add.mkdir(parents=True)
        (self.to_add / "needed.txt").write_text(NEEDED, encoding="utf-8")
        return self

    def __exit__(self, *exception):
        shutil.rmtree(self.root, ignore_errors=True)
        return False

    def add(self, name, lines, scanned=False):
        path = self.to_add / name
        (write_scanned_pdf if scanned else write_text_pdf)(path, lines)
        return path

    def run(self, *arguments):
        completed = subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=self.root,
                                   capture_output=True, encoding="utf-8", errors="replace",
                                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.output = completed.stdout + completed.stderr
        return completed.returncode

    def in_library(self, name):
        return self.folders.file(name).exists()

    def needed_keys(self):
        lines = (self.to_add / "needed.txt").read_text(encoding="utf-8").splitlines()
        return [line.split(" | ")[0] for line in lines if line and not line.startswith("#")]

    def sources_list(self):
        return (self.root / "sources" / "list.md").read_text(encoding="utf-8")


@unittest.skipUnless(HAS_PDFTOTEXT, "pdftotext is not on PATH")
class MatchAddedFilesTest(unittest.TestCase):
    def test_shouldFileAPdfUnderItsKeyWhenItsDoiAndQuotesMatch(self):
        with AddedFilesBook() as book:
            # given
            added = book.add("download (3).pdf", MILLER_WITH_DOI)

            # when
            exit_code = book.run("--fix")

            # then
            self.assertEqual(exit_code, 0, book.output)
            self.assertIn("FILED", book.output)
            self.assertTrue(book.in_library("Mil08.pdf"))
            self.assertTrue(book.in_library("Mil08.txt"))
            self.assertEqual(book.folders.read_origin_record("Mil08", FETCH)["status"], "cached")
            self.assertFalse(added.exists())
            self.assertEqual(book.needed_keys(), ["Web21"])
            self.assertIn("Mil08.txt` (fetched", book.sources_list())

    def test_shouldOnlyReportTheMatchWhenRunWithoutFix(self):
        with AddedFilesBook() as book:
            # given
            added = book.add("download (3).pdf", MILLER_WITH_DOI)

            # when
            exit_code = book.run()

            # then
            self.assertEqual(exit_code, 0, book.output)
            self.assertIn("MATCH", book.output)
            self.assertIn("would file as", book.output)
            self.assertTrue(added.exists())
            self.assertFalse(book.in_library("Mil08.pdf"))
            self.assertEqual(book.needed_keys(), ["Mil08", "Web21"])

    def test_shouldFindTheEntryByTitleAndAuthorWhenTheFileCarriesNoIdentifier(self):
        with AddedFilesBook() as book:
            # given
            book.add("paper.pdf", MILLER_WITHOUT_DOI)

            # when
            book.run("--fix")

            # then
            self.assertTrue(book.in_library("Mil08.pdf"), book.output)

    def test_shouldLeaveTheFileAndAskWhenTheVerifiedQuotesAreNotInIt(self):
        with AddedFilesBook() as book:
            # given
            added = book.add("talk.pdf", MILLER_OTHER_TEXT)

            # when
            book.run("--fix")

            # then
            self.assertIn("ASK", book.output)
            self.assertIn("0 of 2 verified quotes found", book.output)
            self.assertTrue(added.exists())
            self.assertFalse(book.in_library("Mil08.pdf"))

    def test_shouldLeaveTheFileAndAskWhenNoEntryMatches(self):
        with AddedFilesBook() as book:
            # given
            added = book.add("rye.pdf", UNKNOWN)

            # when
            book.run("--fix")

            # then
            self.assertIn("no entry in the sources list matches", book.output)
            self.assertTrue(added.exists())

    def test_shouldNeverOverwriteASourceAlreadyInTheLibrary(self):
        with AddedFilesBook() as book:
            # given
            book.folders.file("Mil08.txt").parent.mkdir(parents=True, exist_ok=True)
            book.folders.file("Mil08.txt").write_text("the copy read earlier\n", encoding="utf-8")
            added = book.add("again.pdf", MILLER_WITH_DOI)

            # when
            book.run("--fix")

            # then
            self.assertIn("already in the library", book.output)
            self.assertTrue(added.exists())
            self.assertEqual(book.folders.file("Mil08.txt").read_text(encoding="utf-8"),
                             "the copy read earlier\n")

    def test_shouldFileAnEntryWithoutQuotesWhenItsDoiAndTitleAreOnTheFirstPage(self):
        with AddedFilesBook() as book:
            # given
            book.add("salt.pdf", OLSEN)

            # when
            book.run("--fix")

            # then
            self.assertTrue(book.in_library("Ols19.pdf"), book.output)

    def test_shouldFileTheFileUnderTheKeyTheAuthorChoseAfterAnAsk(self):
        with AddedFilesBook() as book:
            # given
            added = book.add("talk.pdf", MILLER_OTHER_TEXT)
            book.run()

            # when
            exit_code = book.run("--file", "talk.pdf", "--key", "Mil08", "--fix")

            # then
            self.assertEqual(exit_code, 0, book.output)
            self.assertIn("FILED", book.output)
            self.assertTrue(book.in_library("Mil08.pdf"))
            self.assertFalse(added.exists())
            self.assertEqual(book.needed_keys(), ["Web21"])

    def test_shouldRefuseAChosenKeyThatIsNotInTheSourcesList(self):
        with AddedFilesBook() as book:
            # given
            added = book.add("rye.pdf", UNKNOWN)

            # when
            exit_code = book.run("--file", "rye.pdf", "--key", "Bak99", "--fix")

            # then
            self.assertEqual(exit_code, 2)
            self.assertIn("not an entry in the sources list", book.output)
            self.assertTrue(added.exists())

    def test_shouldAskInsteadOfFilingWhenTheMatchingKeyIsNotAPlainFileName(self):
        with AddedFilesBook() as book:
            # given
            listed = book.root / "sources" / "list.md"
            listed.write_text(SOURCES_LIST.replace("### [Mil08]", "### [../../../outside/Mil08]"),
                              encoding="utf-8")
            bibliography = book.root / "sources" / "references.bib"
            bibliography.write_text(BIBLIOGRAPHY.replace("{Mil08,", "{../../../outside/Mil08,"),
                                    encoding="utf-8")
            added = book.add("download (3).pdf", MILLER_WITH_DOI)

            # when
            exit_code = book.run("--fix")

            # then
            self.assertEqual(exit_code, 0, book.output)
            self.assertIn("ASK", book.output)
            self.assertIn("not a plain file name", book.output)
            self.assertTrue(added.exists())
            self.assertFalse((book.root.parent / "outside").exists())

    def test_shouldRefuseAChosenFileGivenAsAPathOutsideTheFolder(self):
        with AddedFilesBook() as book:
            # given
            outside = book.root / "private-notes.txt"
            outside.write_text("notes that are not a source\n", encoding="utf-8")

            # when
            exit_code = book.run("--file", "../../private-notes.txt", "--key", "Web21", "--fix")

            # then
            self.assertEqual(exit_code, 2)
            self.assertIn("not a path", book.output)
            self.assertTrue(outside.exists())

    def test_shouldSayThereIsNothingToAddWhenTheFolderHoldsOnlyTheNeededList(self):
        with AddedFilesBook() as book:
            # when
            exit_code = book.run()

            # then
            self.assertEqual(exit_code, 0)
            self.assertIn("nothing to add", book.output)

    @unittest.skipUnless(HAS_OCR, "tesseract, pdftoppm or pdfinfo is not on PATH")
    def test_shouldReadAScanWithOcrAndFileItByItsIsbn(self):
        with AddedFilesBook() as book:
            # given
            book.add("scan0001.pdf", ROSSI, scanned=True)

            # when
            book.run("--fix")

            # then
            self.assertTrue(book.in_library("Ros15.pdf"), book.output)
            self.assertTrue(book.folders.file("Ros15.txt").read_text(encoding="utf-8")
                            .startswith("=== OCR-PROVENANCE ==="))
            self.assertIsNotNone(book.folders.read_origin_record("Ros15", OCR))
            self.assertIn("READABLE VIA OCR", book.output)


if __name__ == "__main__":
    unittest.main()
