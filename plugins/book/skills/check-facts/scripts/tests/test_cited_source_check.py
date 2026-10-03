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
### [<Key>] Author(s), "Short Title" (Year)
```

### [Smi99] Smith, "Kitchen Gardens" (1999)

**Full title:** Kitchen Gardens

---

### [Lee05] Lee, "Pond Life" (2005)

**Full title:** Pond Life

---

### [Ngu12] Nguyen, "Names That Help" (2012)

**Full title:** Names That Help
"""


class CitedSourceCheckTest(unittest.TestCase):
    def setUp(self):
        self.book = Path(tempfile.mkdtemp(prefix="cited-source-test-"))
        self.write("book.yaml", "version: 1\nbook:\n  title: A Test Book\n  author: Sam Example\n")
        self.write("manuscript/110-chapter-1.md",
                   "# Chapter 1\n\nSmall beds give the most [Smi99, p. 4].\n")
        self.write("sources/list.md", LIST_TEXT)
        self.write("sources/library/Smi99.pdf", "copy")
        self.write("thinking/argument/ponds.md", "Ponds dry out in August [Lee05].\n")

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

    def test_shouldReportAKeyWhenTheSourcesListHasNoEntryForIt(self):
        # given
        self.write("thinking/doubts/open-questions.md", "Is it true? [Kim20]\n")

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertEqual(run.keys_of("not-in-list"), ["Kim20"])
        self.assertIn("thinking/doubts/open-questions.md:1", run.message_of("Kim20", "not-in-list"))

    def test_shouldIgnoreAKeyWhenItStandsInFencedCode(self):
        # given
        self.write("manuscript/120-chapter-2.md", "# Chapter 2\n\n```\nx = [Abc01]\n```\n")

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertEqual(run.keys_of("not-in-list"), [])

    def test_shouldNotAskForAListedKeyWhenNothingCitesIt(self):
        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertNotIn("Ngu12", run.keys_of("no-library-copy"))

    def test_shouldSkipWhenTheBookHasNoSourcesList(self):
        # given
        (self.book / "sources" / "list.md").unlink()

        # when
        run = run_script(SCRIPT, book=self.book)

        # then
        self.assertTrue(run.stdout.strip().splitlines()[-1].startswith("SKIPPED"))
        self.assertEqual(run.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
