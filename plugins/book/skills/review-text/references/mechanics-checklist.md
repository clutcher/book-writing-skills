# Pre-print mechanics checklist

Mechanical consistency checks to run over the whole manuscript before a print or a review copy.
None of them needs judgment about the argument; most are one grep each. Items marked
**(script)** are covered by a check in the write-text skill or the check-facts skill; the rest are candidates
for a script and are done by hand until one exists.

## Structure and references inside the book

- Every "Chapter N" names a chapter that exists; every "Section X.Y" names a section that exists.
- No chapter title is repeated as a section heading inside that chapter.
- Headings use one capitalization style (title case or sentence case) per level.
- Every chapter has an introduction before its first `##` and, when the book uses them, a summary
  under the book's summary heading (`manuscript.summary_heading`).

## Words

- Doubled words ("the the", "a a").
- An acronym used before it is spelled out, and acronyms never spelled out at all.
- Spelling variants of one word (e-commerce / ecommerce, email / e-mail): pick one.
- Digits versus words for the same count ("three layers" in one place, "3 layers" in another).
- Percent style: one of "70%", "70 percent", "seventy percent".
- One label per platform or product in the text and the bibliography (not two names for one
  service).
- Fixed phrases keep one casing (for example Cold War).

## Punctuation

- One dash style, per the voice profile (**script:** `PlainBook.EmDashWrap`, `ascii-normalize.py`).
- Punctuation placed the same way relative to closing quotation marks everywhere.
- ASCII only when the book requires it (**script:** `ascii-normalize.py`).

## Citations

- Several keys in one bracket are in one agreed order (**script:** check-facts skill).
- Every cited key is in the bibliography and every entry is cited (**script:** check-facts skill,
  `python3 ${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/reference-format-check.py --completeness`).
- The bibliography is sorted (**script:** check-facts skill, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/reference-sort.py`).

## Diagrams in text

- In an ASCII diagram every line of a box has the same width, so the edges line up.
- Arrows use one form (`->`).

## How to report

List findings as `file:line  kind  text`, group by kind, and give counts. For a kind with many
hits, propose one sweep with the chosen form and let the author approve the form before any edit
(`${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/presenting-changes.md`).
