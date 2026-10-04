import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib" / "tests"))

from script_books import run_script

SCRIPT = Path(__file__).resolve().parents[1] / "cited-source-check.py"

LIST_TEXT = """# Sources list

## Entry format

```
### [<Key>]
```

### [Smi99]

**Access URLs:** https://example.org/kitchen-gardens

---

### [Lee05]

**Access URLs:** https://example.org/pond-life

---

### [Ngu12]

**Access URLs:** https://example.org/names-that-help
"""

BIBLIOGRAPHY_TEXT = """@book{Smi99,
  author = {Smith, Ann},
  title = {Kitchen Gardens},
  year = {1999},
}

@book{Lee05,
  author = {Lee, Bo},
  title = {Pond Life},
  year = {2005},
}

@book{Ngu12,
  author = {Nguyen, Cam},
  title = {Names That Help},
  year = {2012},
}
"""


class CitedSourceCheckTest(unittest.TestCase):
    def setUp(self):
        self.book = Path(tempfile.mkdtemp(prefix="cited-source-test-"))
        self.write("book.yaml", "version: 1\nbook:\n  title: A Test Book\n  author: Sam Example\n")
        self.write("manuscript/110-chapter-1.md",
                   "# Chapter 1\n\nSmall beds give the most [@Smi99, p. 4].\n")
        self.write("sources/list.md", LIST_TEXT)
        self.write("sources/references.bib", BIBLIOGRAPHY_TEXT)
        self.write("sources/library/Smi99.pdf", "copy")
        self.write("thinking/argument/ponds.md", "Ponds dry out in August [@Lee05].\n")

    def tearDown(self):
        shutil.rmtree(self.book, ignore_errors=True)

    def write(self, name, text):
        path = self.book / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_shouldReportAThinkingKeyWhenItHasNoLibraryCopyAndNoNeededLine(self):
        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertEqual(run.keys_of("no-library-copy"), ["Lee05"])
        self.assertEqual(run.exit_code, 1)

    def test_shouldAcceptAKeyWhenNeededTxtAsksForIt(self):
        # given
        self.write(".book/sources-to-add/needed.txt",
                   "# header\nLee05 | Pond Life | Lee, A. | 2005 | no link known\n")

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertEqual(run.keys_of("waits-in-needed"), ["Lee05"])
        self.assertEqual(run.exit_code, 0)

    def test_shouldReportAKeyWhenTheBibliographyHasNoEntryForIt(self):
        # given
        self.write("thinking/doubts/open-questions.md", "Is it true? [@Kim20]\n")

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertEqual(run.keys_of("not-in-bibliography"), ["Kim20"])
        self.assertIn("thinking/doubts/open-questions.md:1",
                      run.message_of("Kim20", "not-in-bibliography"))

    def test_shouldReportAKeyWhenTheSourcesListHasNoEntryForIt(self):
        # given
        self.write("sources/list.md", LIST_TEXT.replace("### [Lee05]", "### [Lea05]"))

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertEqual(run.keys_of("not-in-list"), ["Lee05"])
        self.assertEqual(run.keys_of("not-in-bibliography"), [])

    def test_shouldFindAKeyWhenItIsCitedNarrativelyOrInBraces(self):
        # given
        self.write("manuscript/120-chapter-2.md",
                   "# Chapter 2\n\nAs @Ngu12 says, and @{Wal--} too.\n")

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertEqual(run.keys_of("no-library-copy"), ["Lee05", "Ngu12"])
        self.assertEqual(run.keys_of("not-in-bibliography"), ["Wal--"])

    def test_shouldIgnoreAKeyWhenItStandsInFencedCode(self):
        # given
        self.write("manuscript/120-chapter-2.md", "# Chapter 2\n\n```\nx = [@Abc01]\n```\n\nWrite to me at sam@example.org.\n")

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertEqual(run.keys_of("not-in-list") + run.keys_of("not-in-bibliography"), [])

    def test_shouldNotAskForAListedKeyWhenNothingCitesIt(self):
        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertNotIn("Ngu12", run.keys_of("no-library-copy"))

    def test_shouldSkipWhenTheBookHasNoBibliographyAndNoSourcesList(self):
        # given
        (self.book / "sources" / "list.md").unlink()
        (self.book / "sources" / "references.bib").unlink()

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertTrue(run.stdout.strip().splitlines()[-1].startswith("SKIPPED"))
        self.assertEqual(run.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
