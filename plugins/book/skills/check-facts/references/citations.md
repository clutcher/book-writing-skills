# Citation keys and bibliography entries

The key rule is executable in one place, `lib/citation_key.py`, and every script uses it. Do not
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
| organisation or no byline | assigned once and left alone; do not run the rule over it | Acm17 |

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
across the whole key namespace, so a letter key whose sibling is registered but uncited is correct.

**Derive the key from the author list, never from a memorable label.** A key spelling out a
nickname, an interviewer, a publisher or a project name looks plausible and hides who wrote the
work; keys built that way have carried "authors" who were never on the paper.

When `key-bibtex-check.py` generates its `.bib`, a corporate author is brace-protected (or bibtex
splits its words into first and last names), `A & B` is two corporate authors, and the author
segment is written in comma form (`Perez Molina, M.`), because natural order makes bibtex read the
first word of a multi-word surname as a given name.

## Keys are scope-local

An a/b letter resolves a clash inside ONE scope. The bibliography is one scope; each argument file
is another. The same key can mean different works in the two, with neither wrong.

- Never assume a key means the same work in two places. Resolve it against the bibliography before
  declaring a source missing or renaming anything; chasing an argument-file spelling as "missing" has
  created duplicate list entries.
- A key and its entry must agree on the year (a preprint year kept after publication is the usual
  mismatch; `argument-key-check.py` reports it as `bibliography-key`).
- A `_formerly registered as [Old]_` line in the list's `Record history` is the declared alias.
- Promoting a source used only in argument files into the book merges the two scopes, and that is when a reuse becomes
  a real collision needing a/b. `argument-key-check.py` reports these as `cross-scope` until then.

## In the prose

- Group keys in one bracket: `[Smi99, Jon01]`. Never adjacent brackets `[Smi99][Jon01]`.
- A multi-key bracket is split before matching; a naive `\[[^]]+\]` treats it as one key.

## Bibliography entries

`[Key] Authors (Year). Title. Venue or Publisher. Identifier.`, one line per entry, sorted by key
case-insensitively, one blank line between entries, under a `# References` heading.

- **One entry per work, dual-dated**, for the printing actually read, with the first publication
  inside it: `... 2nd ed. Example Press. First published 1988.` A quote or page number belongs to
  the printing named first; a dating claim in the prose rests on the `First published` line.
  Never hang a quote on an edition nobody opened, and never label the later text with the earlier
  year.
- **The exception: editions that differ in the content cited.** Then two entries are right, and
  each says why it exists. Verify the difference in both cached texts before splitting.
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
- **Entries nothing cites are removed**; the sources list keeps retired printings as edition history.

## Titles in the prose

| Work | Format | Example |
|---|---|---|
| book | *Italic*, title case | *A Book About Things* |
| paper, article, chapter | "Quotation marks", title case | "Notes on Winter Pruning" |

First mention names the author(s) (three or more: first author et al.); later mentions may use the
title alone. `reference-format-check.py` checks the formatting and `--completeness` the two-way
join. A short title that is also an ordinary name in the prose (a language, a practice, a tool) is
listed as `terms.watch_words.titles_used_as_names`, so it is matched only in full.

## The reference pass, in order

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts"
python3 $SCRIPTS/citation-key-check.py                      # 1. keys against the rule (review, then --fix)
python3 $SCRIPTS/reference-sort.py --fix                    # 2. sort the bibliography
python3 $SCRIPTS/reference-format-check.py --completeness   # 3. two-way integrity: cited == entries
python3 $SCRIPTS/list-bibliography-check.py                 # 4. the list joins the bibliography by key
```

A clean result: equal citation and entry counts, no missing key, no uncited entry, no adjacent
brackets. Always run step 3 again after a `--fix` in step 1.
