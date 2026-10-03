# Keywords and categories

The store keywords, categories and subject codes of this book, with a reason per row and how
far each is verified. Checked by the prepare-sales-text skill (`keyword-check.py`). Keep the
headings "Keywords", "Categories" and "Avoid" and their column names: the script reads them. A cell or line written
as <...> is a placeholder: the script skips it, so fill it in or delete the row.

## Book inputs

- Price per format, primary market, page count, what the reader must already know, audience span.
- Nearest books on the shelf (for positioning only; never named in a slot or on a surface).

## Keywords

| Slot | Keyword | Chars | Why this term | Search suggestions (date) |
|------|---------|-------|---------------|---------------------------|
| 1 | <keyword of up to 50 characters> | <chars> | what the title does not say; manuscript count | what the store suggests |

Characters used and index words added (from `keyword-check.py`): record them here when a set
is chosen, and record any set this one replaces, with its numbers, under a sub-heading.

## Categories

| Format | Slot | Category | Why | Browse node | Picker |
|--------|------|----------|-----|-------------|--------|
| Paperback | 1 | <store path down to the leaf category> | why this shelf | node id, date | not yet |

`Picker` is `yes` or the date the leaf was seen in the signed-in store picker; anything else
is reported as not confirmed.

## Avoid

Other authors, their book titles, brands this book does not own. One per line.

- <other author name>
- <other book title>

## Subjects (BISAC and other stores)

- Heading, code (checked against the current BISAC list on <date>)

## Category evidence

Comparable titles, their descriptions and back covers, search-suggestion results, category
trees with node ids, the free-sample reach. Every figure with its date and how it was read.
