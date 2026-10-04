import unittest

import support

from bibliography import parse_bibliography
from source_registry import parse_bank
from sources_to_add import describe, needed_line

GATED_ENTRY = """# Sources List

## Entry format

```
### [<Key>]
```

---

### [Hal19]

**Access status:** MANUAL FETCH REQUIRED
"""

HALE_RECORD = """@book{Hal19,
  author = {Hale, Ruth},
  title = {Bread at Home},
  publisher = {Example Press},
  year = {2019},
  url = {https://example.org/hale-bread},
}
"""


class NeededLineTest(unittest.TestCase):
    def test_should_give_the_page_link_from_the_bib_when_the_entry_has_no_access_link(self):
        # given
        entry = parse_bank(GATED_ENTRY).entries[0]
        identity = parse_bibliography(HALE_RECORD).entry("Hal19")

        # when
        line = needed_line(describe(entry, "MANUAL FETCH REQUIRED", identity))

        # then
        self.assertEqual(line, "Hal19 | Bread at Home | Hale, Ruth | 2019 | "
                               "https://example.org/hale-bread")

    def test_should_still_give_a_line_when_the_bib_has_no_entry_for_the_key(self):
        # given
        entry = parse_bank(GATED_ENTRY).entries[0]

        # when
        line = needed_line(describe(entry, "MANUAL FETCH REQUIRED"))

        # then
        self.assertEqual(line, "Hal19 | (no title recorded) | - | - | no link known")


if __name__ == "__main__":
    unittest.main()
