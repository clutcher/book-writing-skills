import unittest

import support

from source_registry import parse_bank
from sources_to_add import describe, needed_line

ENTRY_WITH_PAGE_LINK = """# Sources List

## Entry format

```
### [<Key>] Author(s), "Short Title" (Year)
```

---

### [Hal19] Hale, "Bread at Home" (2019)

**Full title:** Bread at Home
**Authors:** Ruth Hale
**Year:** 2019
**DOI/URL:** https://example.org/hale-bread
**Access status:** MANUAL FETCH REQUIRED
"""


class NeededLineTest(unittest.TestCase):
    def test_should_give_the_page_link_when_the_entry_has_no_access_link(self):
        # given
        entry = parse_bank(ENTRY_WITH_PAGE_LINK).entries[0]

        # when
        line = needed_line(describe(entry, "MANUAL FETCH REQUIRED"))

        # then
        self.assertEqual(line, "Hal19 | Bread at Home | Ruth Hale | 2019 | "
                               "https://example.org/hale-bread")


if __name__ == "__main__":
    unittest.main()
