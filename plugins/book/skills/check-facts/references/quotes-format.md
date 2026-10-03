# The quotes bank: what each source says

The quotes bank (`sources.quotes`) answers: **what does this source actually say?** It is keyed
exactly like the sources list, and both banks are dateless, kept current, and never a log.

## Why two files, not one

Do not merge them. Two files keyed identically can
drift, but the two halves have different lifetimes: access data churns (a cache sweep touches
every entry, a dead URL is replaced, a hash changes on refetch), while a verbatim quote from a
published paper is true for good and expensive to establish again. One file means every routine
access update rewrites the quotes too, and the file grows too big to grep for either purpose. A
chapter agent needs what its sources say and pays nothing for access data it will never read.
`list-quotes-join-check.py` keeps the join honest.

## What goes where

| Kind | Example | Home |
|---|---|---|
| A durable fact about the source | a verbatim quote; "the paper states 41% in the text and 44% in Table 2"; "the words are the originator's, not the citing author's" | quotes bank |
| A dated verdict about the book | VERIFIED; "checked and the chapter is right" | run report only |
| A guardrail | "do not cite this for a per-person gain"; "do not recompute this figure from the chart" | quotes bank, in the present tense: it is an instruction, not a record |

## The entry

```markdown
### [<Key>] Author, "Title" (Year)

**Verified quotes:**
- p. 12 (Results): "the exact words from the source"
**Key findings:** what the source establishes, as a fact about the source.
**Role:** why the source is on file: what it supports, and what it was considered and rejected for.
**Scope:** population, sample size, design limits. The field that stops a small lab study being cited like a field trial.
**Guardrail:** a present-tense instruction: what it may not be cited for, which experiment to cite.
**Quote origin:** when the words belong to someone the source is itself quoting.
**Relation:** how this source bears on another key: corroborates, qualifies, is easily confused with.
**Last verified:** YYYY-MM-DD
**Source:** see `<sources.list>`
```

- **The vocabulary is closed at these nine names.** Add a tenth only when a new *kind* of content
  starts piling up; a one-off goes in the prose of the closest field. There is no `Note` here, so
  an unapproved field is reported, never renamed.
- **No `Last verdict`, no `Confidence`**: both are judgments about the book.
- **`Last verified` is the one permitted date.** It records when someone last read the source, so
  a bank can express its own staleness. `list-quotes-join-check.py --stale 365` lists old readings;
  a published source does not change, so an old reading is unconfirmed, not wrong.
- **Page or section anchors on quotes are welcome, never required.**
- **Correct an entry in place; never add a "superseded" marker.** A bank that collects "this
  earlier verdict is superseded" stops reading as currently true. Fold the lesson forward as a
  guardrail; git keeps the history.

## A quote must be a string the cache can match

`quote-in-file-check.py` holds every quoted string to the cached file. So:

- A **locator** (a running head plus a page number) is not a quotation; write it as prose.
- Text read off a page **render** that the OCR mangles cannot match the extraction; state it as
  prose out of quotation marks, and say it was read from the render.
- A quote from a page the list **deliberately did not cache** raises a false alarm every run: cache
  the page, or state the fact as prose.
- An entry claiming no quotes is never opened by the check, so a stub cache stays invisible until a
  `Verified quotes` field is added.
- Every digit taken from OCR text is confirmed against the page image, and the entry says so:
  `**Verified quotes:** confirmed against the page image.` (`ocr-marker-check.py` enforces this.)

## A guardrail is evidence, never authority

A guardrail nothing reads is a guardrail nothing obeys: a book can print exactly the attribution
its own bank forbids. `guardrail-prose-check.py` pairs every guardrail with the sentences that
cite its key. **It surfaces and never enforces**, because a guardrail can itself be false. When a
guardrail and the source disagree, the source wins, and the guardrail is what gets corrected.
Proposed guardrails are checked against the source before they are written.

## Parallel writers

Agents never write a bank directly. Each agent stages its entries in bank format as one file in
the run folder, `<run folder>/proposed-entries/quotes/<agent>.md`, and the run merges them at
its end:

```bash
LIB="${CLAUDE_PLUGIN_ROOT}/lib"
python3 $LIB/proposed_entries.py --run <run folder>          # dry run
python3 $LIB/proposed_entries.py --run <run folder> --fix    # never overwrites an entry; rejects the list's field names
```

When the same field already exists on an entry, fold the new text into it; a second field of the
same name is invisible to every tool.
