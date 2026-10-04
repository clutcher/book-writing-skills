# Checking bibliography metadata against registries

**The rule:** never report that an entry has the wrong year, venue, volume, issue or pages on the
evidence of one metadata lookup. A second, independent registry must agree first. If the two
disagree, the disagreement IS the finding: report it and leave the entry alone. A single-registry
"correction" looks like diligence while it introduces the error: a publisher can deposit a
proceedings volume under the wrong year, and the DOI registry republishes it.

The metadata lives in the book's `.bib` file (`sources.bibliography`, by default
`sources/references.bib`), as BibTeX fields: `author`, `editor`, `title`, `journal` or `booktitle`,
`year`, `volume`, `number`, `pages`, `publisher`, `doi`, `isbn`, `url`, `origdate` (first publication
of a reprint). The sources list (`sources/list.md`) holds no metadata, only access and cache lines.
A correction that survives is made in the `.bib` entry; the script never writes it.

`metadata-check.py` runs this over every `.bib` entry, caches the answers, and reruns for free:

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts"
python3 $SCRIPTS/metadata-check.py --only-disagreements          # every entry of the book's .bib
python3 $SCRIPTS/metadata-check.py --key Smi99
python3 $SCRIPTS/metadata-check.py --kind book --discover-isbn --json candidates.json
python3 $SCRIPTS/metadata-check.py --doi 10.1234/abc --isbn 9780000000002
export CROSSREF_CONTACT='mailto:you@example.org'     # before running at any scale
```

A DISAGREE row is a prompt to open the source, never a correction to apply.

**Which registries the script asks.** For a DOI entry it asks Crossref first. The second registry
is DBLP, which covers computer science only; for any other field DBLP has no record, and the
script falls back to OpenAlex, whose agreement is weak because it copies Crossref. For a book in
another field, treat a DOI result with only OpenAlex behind it as one source, and confirm it on
the publisher's page, in PubMed (medicine) or in the source itself.

## No registry is the source of truth; the source is

Both directions happen: a registry wrong while the entry is right, and an entry wrong while the
registry is right. No ranking of registries is right in advance. What CAN be ranked is how much
work a kind of evidence saves before you open the source:

1. the source itself, or a cached copy: settles it outright
2. a curated domain index (DBLP for computer science, PubMed for medicine)
3. a general registry or aggregator (Crossref, Semantic Scholar, OpenAlex, publisher pages)
4. library catalogues: good for books, ISBN and publisher; often vague on the year of a reprint

The page image outranks two agreeing registries: registries that share an upstream can propagate
one error.

**Identifiers are different in kind.** A DOI or an ISBN is an exact key, not an opinion: asking
what it resolves to has one answer. It needs to be the RIGHT key, which is checked by other means
(a check digit, a round trip returning the expected title and author).

- **An identifier that is merely real is not thereby right.** A wrong-but-real DOI agrees with
  itself everywhere; only the title comparison catches it.
- **"Two sources agree" ends the search only when the entry does not matter.** Two sources that
  share an upstream are one source with extra steps.

## Independence

- OpenAlex ingests Crossref and inherits its errors; agreement backed only by OpenAlex is weak.
  DBLP is separately curated. DBLP's API is a search endpoint and does not accept a DOI as a
  query: search by title and subtitle (a registry can store the subtitle separately, and a
  truncated title loses the match), then confirm the DOI on the hit. A DBLP that answered HTTP
  500 is unreachable, never "no record". Outside computer science, pair Crossref with PubMed, the
  publisher's page or OpenAlex.
- Open Library and Google Books share an upstream (library MARC through LoC and OCLC), so their
  agreement is corroboration, not proof. Google Books has a documented history of bad dates.
  Without an API key Google answers HTTP 429 to everything, so a run without a key means "Open
  Library had no objection", not a cross-check.
- A catalogue whose year set is so broad that the cited year is almost always inside it agrees
  with everything and confirms nothing. **A source must be able to say no.** Library of Congress
  (too imprecise for recent books, and upstream of the others anyway), Wikidata (too
  thin), and national catalogues that hold translations (they manufacture disagreement) were
  tested and rejected as third sources.
- Same-title collisions (a journal article and a proceedings paper of one title) fool title-keyed
  lookups. Catalogue word order can be wrong against the title page.

## Books

- **The edition trap**: compare a book's year as MEMBERSHIP in the set of edition years a
  catalogue holds, never as equality with a "first published" year: the bibliography cites a later
  edition on purpose. Never compare edition statements.
- **Copyright year versus retail release**: catalogues record the title-page year, booksellers the
  release; a one-year difference is usually this.
- A book entry is an `@book` with no `doi` and no `url` field; an entry with a `doi` is checked
  by its DOI. Books are matched on title AND author. A catalogue title that is a whole-word prefix of the cited
  one is a dropped subtitle; a catalogue title LONGER than the cited one is usually a different book
  (a companion, a summary) and is refused.
- **ISBN discovery** searches Open Library edition records (not work records, which flatten every
  printing) and offers a candidate only when title, author, year and publisher all agree. The check
  digit is checked on every candidate. The output is a candidate list for a person, never a patch.
- **Pre-ISBN works** (before 1970) need an LCCN or OCLC number in the entry's `note` field, not a forced ISBN
  match (a catalogue will happily return a later reprint). A 979-8 ISBN has no ISBN-10 form. A
  retailer's product id is not an ISBN.

## Titles

Titles escalate through rungs, and the rung is the finding: exact, folded (case, punctuation,
articles), joined (the registry's separate subtitle glued back on), component (one title is a run
of the other's parts: reported only when the ENTRY is the shorter), alphanumeric (soft), none
(hard: DISAGREE). A registry that expands a contraction or re-punctuates a title into different
words produces a false hard mismatch now and then: read those rather than trusting them.

## What it cannot do

It reaches a minority of a typical bibliography: talks, blog posts, vendor reports and old
articles have no registry. A clean run says nothing about the entries it could not see, and those
are the ones most worth doubting. It does not verify authors or editions, does not check that a
DOI belongs to the cited work, treats a start-page-only registry record as agreement, and pools
matching catalogue records (so a wide year span is a weak AGREE: the output prints the span).

When a correction survives, record both registries in the run report so a later run does not
argue it again. When it fails, record the disagreement in the sources-list entry's
`Record history` or the quotes bank, not only in a dated report.
