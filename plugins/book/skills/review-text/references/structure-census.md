# Structure census: finding outlier chapters

A census of heading depth and paragraphs per section shows which chapters differ from the book's
own rhythm. It is an **outlier finder, not a rule**: a chapter that differs may do so on purpose
(an argument chapter is flatter than a catalog chapter). Do not build a rigid chapter template
from it.

## Method

1. For each chapter, count the headings at each level (`#`, `##`, `###`, deeper).
2. For each section, count its paragraphs; separate `##` sections with and without `###`
   subsections, the introduction (before the first `##`) and the summary.
3. Compute the book's own typical value for each (median and spread).
4. Flag the chapters and sections far from the book's own values, and read them: is the
   difference a choice the chapter needs, or drift?

**Recompute every time; never store the numbers.** A stored census goes stale with the next edit
and then misleads. The same holds for any count that a grep can produce.

## What a census can show

One example of the shapes a census of one finished book showed; another book has its own:

- at most three heading levels (`#`, `##`, `###`), never `####`;
- a one-paragraph chapter introduction that bridges from the previous chapter;
- a summary of a few paragraphs that ends on the question the next chapter takes up;
- short `###` subsections, and longer `##` sections when they have no subsections.

A book that records such a rhythm in `decisions.md` records it as observed norms to recompute,
not as limits.

## Tools

`sentence-and-paragraph-check.py --stats` gives sentence and paragraph statistics per file. No script
counts paragraphs per section yet; until one exists, count by hand or with a short one-off
script, and do not save its output in the book.
