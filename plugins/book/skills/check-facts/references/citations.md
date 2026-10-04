# Citation keys, citations and .bib entries

The key rule is executable in one place, `${CLAUDE_PLUGIN_ROOT}/lib/citation_key.py`, and every script uses it. Do not
derive a key by hand:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/citation_key.py --derive Adams Baker Clark Davis --year 1994    # ABCD94
python3 ${CLAUDE_PLUGIN_ROOT}/lib/citation_key.py --validate ABC+20
```

## The alpha rule (the style is `sources.citation_style`, default alpha)

| Authors | Key | Example |
|---|---|---|
| 1 | the surname fragment, or its first three letters when the fragment is one character | Smi99 |
| 2 to 4 | one fragment per author, NO `+` | ABCD94 |
| 5 or more | the first three fragments, then `+` | ABC+20 |
| organisation or no byline | a corporate author in double braces keys like one name; with no author or editor alpha takes the first three letters of the key, so choose it once | Acm17 |

A fragment is the first letter of every token of the surname, each token keeping its own case:
particles are kept (van Berg gives vB), every word of a multi-word surname counts (Perez Molina
gives PM), a hyphen splits tokens like a space (Owen-Price gives OP), and a lower-case word inside
a surname stays lower case (Rocha da Lima gives RdL; Rocha Da Lima gives RDL). The last two rules
live in bibtex's built-in `format.name$`, not in `alpha.bst`, which is why `key-bibtex-check.py`
runs the real bibtex rather than trusting a reading of the style file. A company blog post with a
personal byline keys to the person.

Two conventions sit on top of alpha and are reported as expected deviations, not errors: a
fragment is ASCII-folded (alpha keeps the accent), and an undatable work takes `--` for its year
(alpha appends nothing). The a/b letter is plain alpha: it disambiguates same-key same-year works
across the whole .bib, in the order alpha sorts them (names, then year, then title), so a letter
key whose sibling is in the .bib but uncited is correct.

**Derive the key from the author list, never from a memorable label.** A key spelling out a
nickname, an interviewer, a publisher or a project name looks plausible and hides who wrote the
work; keys built that way have carried "authors" who were never on the paper.

Write the names in the .bib in comma form (`Perez Molina, Maria`): in natural order bibtex reads
the first word of a multi-word surname as a given name. A company or project is a corporate
author in double braces (`{{Example Research}}`), or bibtex splits its words into names.

## One key space

The manuscript and the thinking files cite one .bib, so a key means one work everywhere.

- Resolve a key against the .bib before declaring a source missing or renaming anything; chasing
  a misspelled key as "missing" has created duplicate entries.
- A key and its entry must agree on the year (a preprint year kept after publication is the usual
  mismatch; `citation-key-check.py` reports it as `key-rename`).
- `citation-key-check.py --fix` renames a key in the .bib, the sources list, the quotes bank, the
  manuscript and the thinking files in one pass; the list entry's `Supersedes` keeps the old key.

## In the prose: pandoc citations

- `[@Smi99]`, several in one bracket `[@Smi99; @Jon01]`, with a locator `[@Smi99, p. 12]`, with a
  prefix `[see @Smi99, ch. 2; @Jon01]`, and narrative `@Smi99 says`. Never adjacent brackets
  `[@Smi99][@Jon01]` (`citation-check.py` reports `adjacent-brackets`).
- A key without `@` (`[Smi99]`, `[Smi99, p. 12]`, `[Smi99, Jon01]`) prints as plain text;
  `citation-check.py` reports `old-citation` when the keys are in the .bib or the sources list.
  The references file holds only its heading and `::: {#refs}` / `:::`; anything more is
  `hand-written-references`.
- A key with characters a bare citation ends on is written in braces: a key ending in `--` is
  `@{Wal--}`. `ABC+20` is fine bare. The full rule is in
  `${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/citing-in-prose.md`.
- `${CLAUDE_PLUGIN_ROOT}/lib/citations.py` reads citations for every script; a hand-rolled
  regular expression misses the narrative and braced forms, and reads an e-mail address as one.

## .bib entries

One BibTeX entry per source (fields and format: `list-format.md`). The references page of the
manuscript holds only its heading and `::: {#refs}`; the build prints the cited entries there,
sorted, in the book's citation style (`sources.citation_style`: alpha `[Smi99]` or numeric `[1]`).

- **One entry per work, dual-dated**, for the printing actually read, with the first publication
  in `origdate`: `edition = {2}`, `origdate = {1988}`. A quote or page number belongs to the
  printing the entry names; a dating claim in the prose rests on `origdate`. Never hang a quote
  on an edition nobody opened, and never label the later text with the earlier year.
- **The exception: editions that differ in the content cited.** Then two entries are right, and
  each says why it exists (in its list `Note`). Verify the difference in both cached texts before splitting.
- **Prefer the journal or conference version over the preprint**, and treat it as the stronger
  source: verify quotes and numbers in the published text (reviewers force changes); the entry
  names the published venue and the key takes the publication year, keeping the arXiv ID as a
  locator; state a preprint-only finding as provisional. arXiv-only is fine where no reviewed
  version exists. A paywalled paper of record is handled as in `${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/references/fetching.md`: the fallback to the
  preprint is the author's decision.
- **Never date a web source by when you read it** (see `list-format.md` for the routes). Write
  dates with the month spelled out, never as an ISO date. A recorded talk takes the date the
  recording was published.
- **Pin source code and living pages** to a tag or commit, with file and line. A permanent archive
  identifier is more rigorous but tells a book reader nothing; keep it for a host that has gone.
- **Entries nothing cites stay** in the .bib and the list: the build prints only cited entries,
  and a retired printing is edition history.

## Titles in the prose

| Work | Format | Example |
|---|---|---|
| book | *Italic*, title case | *A Book About Things* |
| paper, article, chapter | "Quotation marks", title case | "Notes on Winter Pruning" |

First mention names the author(s) (three or more: first author et al.); later mentions may use the
title alone. `reference-format-check.py --titles` checks the formatting against the .bib titles
(a book type in italics, an article or a chapter in quotes), and `citation-check.py` the join. A short title that is also an ordinary name in the prose (a language, a practice, a tool) is
listed as `terms.watch_words.titles_used_as_names`, so it is matched only in full.

## The reference pass, in order

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts"
python3 $SCRIPTS/citation-key-check.py                      # 1. keys against the rule (review, then --fix)
python3 $SCRIPTS/key-bibtex-check.py                        # 2. keys against the labels real bibtex prints
python3 $SCRIPTS/reference-format-check.py                  # 3. the .bib entries: fields, DOI, ISBN
python3 $SCRIPTS/citation-check.py                          # 4. every cited key has a .bib entry
python3 $SCRIPTS/list-bibliography-check.py                 # 5. the list and the .bib hold the same keys
```

A clean result: no key to rename, no label disagreement, no format defect, no cited key missing
from the .bib, and the list and the .bib joined. Always run step 4 again after a `--fix` in step 1.
