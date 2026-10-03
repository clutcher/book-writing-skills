# The sources list: what an entry holds

The sources list (`sources.list` in book.yaml) answers one question: **where do I read this
source?** It holds identity and access only. What the source *says* goes to the quotes bank
(see `quotes-format.md`); a verdict about the book goes to a dated run report, and to neither
bank.

| What | Where | Why there |
|---|---|---|
| Identity and access: title, authors, year, ISBN, DOI, URLs, cache lines | sources list | Static facts about the work; they let any later run fetch the source again without searching |
| What the source says: verbatim quotes, findings, scope, guardrails | quotes bank | Durable and expensive to establish again; some sources can no longer be fetched at all |
| Verdicts about the book: VERIFIED / MINOR ISSUE, confidence, suggested fix | run report under `<work.runs>/<YYYY-MM-DD-HHMM>-check-facts-all/` | They expire the moment the book is edited, and the run folder carries the date |

A list entry is a **pointer to the real source**, never the source itself. Its fields can be
stale or wrong, so verification never trusts the entry as ground truth: it follows the cache
and reads the source again.

## The entry

```markdown
### [<Key>] Author, "Short Title" (Year)

**Full title:** the exact title of the work
**Authors:** the full author list
**Year:** the year of the printing read (and the basis, for a web page)
**Edition:** which printing this is, and how it relates to another entry
**Venue:** journal, conference, publisher or platform
**Publisher:** when Venue carries something else
**DOI:** a bare DOI, the permanent identifier
**ISBN:** 13 digits, no hyphens
**Identifier:** an LCCN or OCLC number, for a work older than ISBNs
**DOI/URL:** the canonical landing page (a URL or a DOI, never a citation string)
**Access URLs:** where the source can be read: full text, abstract, mirrors
**Access status:** present only when something blocks or qualifies the reading
**Cached text:** `<sources.library>/<Key>.txt` (fetched <date>, sha256 <hash>)
**Cached original:** `<sources.library>/<Key>.pdf` (fetched <date>, sha256 <hash>, from <URL>)
**Record history:** key renames and corrections to this entry's own identity fields
**Fetch note:** dead hosts, bot checks, extraction traps, what the cache really holds
**Note:** anything else durable: naming traps, attribution cautions, why an uncited source is kept
**Findings:** see `<sources.quotes>`
```

Rules, each one enforced by `entry-format-check.py` and repaired where it is mechanical by
`entry-format-fix.py` (a gate and a fixer over one rule: change both together):

- **The heading names exactly one key**, then a space, then author, short title and year, with
  no separator. A heading naming two keys hides the second from every tool.
- **Only Full title, Authors and Year are required.** Every other field appears when it applies;
  an omitted field is the signal, so never write `none`.
- **Fields appear in the order above.** Order is guidance for new entries; old ones are not
  reordered.
- **The field vocabulary is closed.** A field name outside the list is invisible to every tool
  that reads by name. A qualifier on an approved name (`**Scope, and first:**`) is a new name:
  use the bare name and put the qualifier in the prose. A label ends in `:**`: `**Key findings.**`
  and `**Verified quotes** (pages):` both read as fields to a person and as prose to a tool.
- **No dates in field names, and no verdicts** (Verdict, Confidence, Last verdict). The one
  permitted date in either bank is `Last verified` in the quotes bank.
- **A sha256 describes a file on disk**; never write one on a `NOT YET FETCHED` line.
- **A DOI has its own field.** A DOI buried in DOI/URL or Venue prose is a source nothing can
  resolve, look up on Unpaywall or check against a registry.
- **One `---` with a blank line either side before every entry heading.** A doubled rule hides
  entries from parsers; a `---` directly under prose is a heading in Markdown.
- **Write `Findings:` in the same step as the quotes entry**, not as a later clean-up.
- **Keys are sorted**, case-insensitively, within a section.
- **A list entry is never removed when the book stops citing it**; only the bibliography loses
  the entry. The data about the source may be useful later, and its cache stays verifiable.

## A bank stores what cannot be recomputed

There is no field for where the book cites a source. That is one grep, and a stored copy goes
stale while nobody notices:

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts"
grep -n '\[Smi99[,\]]' manuscript/*.md
python3 $SCRIPTS/list-bibliography-check.py            # every listed source nothing cites
```

What is NOT derivable belongs in `Note`: why an uncited source is on file, what it was
considered for, why it must never be cited. Before adding a field to either bank, ask whether a
grep produces it. If it does, the field will go stale, and the grep was always the better answer.

## Access status versus a fetch outcome

`fetch.py` reports lower-case **attempt outcomes** about one request (`paywalled`, `blocked`,
`too-short`, `abstract-only`). `Access status` is an upper-case **judgment** about the source,
reached after the free routes were tried (see `${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/references/fetching.md`). An outcome is evidence toward a
status and is never copied in as one.

| Status | Meaning |
|---|---|
| `READABLE` | cached and read; often left out, since that is the normal case |
| `READABLE VIA OCR` | the text is machine-read: search it, never quote a digit from it unchecked |
| `MANUAL FETCH REQUIRED (gate)` | free, but behind a check meant for a person; `Access URLs` holds the direct link and `Cached text` says `NOT YET FETCHED -- save the PDF above as <path>` |
| `NO OPEN-ACCESS COPY` | checked (Unpaywall included): no free copy exists; it needs a library or a purchase |
| `NOT CACHED` | a fetch stored something that was not the source (a sales page); nothing in the entry is verified |

Say which wall it is. A 403 from a bot check looks identical to a 403 from a subscription, and a
free source written off as "paywalled" is never tried again. A source that was never read can
support a bibliography entry and nothing else, and any report that cites it must say it was not
read.

## Keys: resolve before concluding a source is missing

- **Keys are scope-local.** An a/b letter resolves a clash inside one file; the bibliography is
  one scope and each argument file another. A key that "does not match" may belong to another scope:
  grep the bibliography first.
- **A one-character key error makes a held source look unheld.** Before recording UNHELD, try the
  key with and without its `+`, and with the author count corrected.
- **Derive the key from the author list, never from a label.** When an entry's key cannot be
  derived from its own author list, re-read the source: keys built from a memorable label have
  hidden authors who were never on the paper. `key-authors-check.py` and `key-bibtex-check.py`
  check this.
- **A rename is identity, recorded in `Record history`**, and a `_formerly registered as [Old]_`
  line there is the declared alias that `argument-key-check.py` rewrites. Do not invent a
  `Supersedes` field.

## Editions: one entry per printing here, one per work in the bibliography

A cached second edition and a cached first printing are two files with two checksums, so each
needs its own list entry to be verifiable. The bibliography cites the printing that was read and
records the first publication inside that one entry (`First published 1988.`).

- **A printing the book no longer cites stays**, as edition history. Its `Edition:` names the
  entry that replaced it and why. Retiring it would orphan its cache.
- **`Edition:` carries the warning, not just the fact.** The dangerous case is a key whose year
  names one printing while its cache holds another; say so in `Access status`, or the next run
  quotes the wrong text under the right-looking key.
- **Verify an edition difference in both cached texts before acting on it**: grep both for the
  exact term.

`duplicate-source-check.py` reports edition pairs as suspects: a prompt to look, not a defect.

## Dating a web source

An access date describes the reader, never the source. In descending authority:

1. a date printed on the page, or an `article:published_time` / `datePublished` meta tag
2. the server `Last-Modified` header (`curl -sI <url> | grep -i last-modified`)
3. for an item in a catalogue or registry that records when it was added (a museum or archive
   catalogue, a public dataset portal, a package registry for software), that timestamp
4. the earliest Wayback capture through the CDX API, as a creation proxy and an upper bound
   (a capture older than the entry's year means the year is wrong)
5. for a video, the upload date in the watch page; a recorded talk takes the date the recording
   was published, not the date of the event
6. for Wikipedia history, the MediaWiki revisions API

Put the basis in the field: `**Year:** 2026 (from the server Last-Modified; the page shows no
date)`. When nothing can be established, the year is `--` in the entry and the key, and the
entry says which routes were tried.

## Source code and living pages

Pin a release tag or a commit, name the file and line, and fetch the raw file at that tag.
Confirm the line number in the CACHED copy, not the live response. One key may need two cached
files when its figures sit in two files: give the second its own key with `b` and name the
first in its entry. A generated documentation page is not acceptable: it is regenerated on a
schedule and its checksum churns without the release changing. `link-check.py` and
`edition-duplicate-check.py` report unpinned addresses as `moving-target`.

## Splitting a contaminated entry

When a check flags an entry, split it line by line, never move the whole block:

| Content | Example | Where it goes |
|---|---|---|
| Access data | "this host answers a script with a redirect stub"; "the scan has no text layer" | stays in the list |
| A durable fact about the source | a verbatim quote; what the paper says | moves to the quotes bank |
| A dated verdict about the book | VERIFIED; "checked, the chapter is right" | neither bank: the run report |
| A guardrail | "a review claimed X; that was not verified, do not repeat it" | the bank it guards, in the present tense: about reaching the source, the list; about what it says, the quotes bank |

## Parsing traps (why no one hand-rolls a split)

- Each bank documents its format with a `### [<Key>]` example inside a fence under
  `## Entry format`. A parser that splits on a bare `^### ` cuts that apart. The placeholder is
  `<Key>`, not `Key`, so a fence-blind parser does not read it as a real entry.
- A `###` heading that is not an entry heading (a note block) must end the entry above it.
- A heading glued onto the end of a field line is invisible to every parser.
- A field name written twice in one entry: every tool reads the first and never the second.
- ${CLAUDE_PLUGIN_ROOT}/lib/source_registry.py owns entry boundaries, fields and separators; every script uses it.
- Never write a historical reason into a bank header ("this drifted twice") without checking the
  history first: an unsupported reason misleads whoever next merges or splits the banks.
