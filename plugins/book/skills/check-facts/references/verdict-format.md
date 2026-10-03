# Writing the verdicts of a run

Verdicts about the book live in the run folder,
`<work.runs>/<YYYY-MM-DD-HHMM>-check-facts-all/` (made by `run_folders.py start check-facts all
--fix`, see SKILL.md): a verdict expires when the book is edited, and the folder name carries the
date. What needs the author's decision also
becomes a note ("Findings become notes" below). Durable facts about a
source go to the quotes bank as well (see `quotes-format.md`); a verified quote written only here
has to be established again next time.

## Per chapter: `fact-check-ch<N>.md`

```markdown
# Fact-Check: Chapter N -- <Chapter Title>

**Run:** Full / --only-changed / --resume
**Input mode:** Review / Manuscript
**Date:** YYYY-MM-DD
**Items checked:** N citations, M claims
**Items skipped:** what this run did NOT check (other citations, the missed-claims pass, the
uncited-claim sweep, the cross-citation pass). A clean line says nothing about the rest.

### [Key] (the review's citation id, if any)

**Book says:** what the chapter claims, with its section
**Source says:** what the source says, and how you verified it
**Source URLs:** every URL where the source was found, one per line
**Original quote:** the exact wording from the source, with its location (omit if no quote)
**Verdict:** VERIFIED / MINOR ISSUE / SIGNIFICANT ISSUE / UNVERIFIABLE
**Confidence:** Strong / Moderate / Weak / Very weak, from the table below
**Details:** the discrepancy, or how it was confirmed
**Suggested fix:** concrete replacement text (omit when VERIFIED)

### Claim <id> (review mode)

**Book says:** ... **Source says:** ... **Verdict:** ... **Confidence:** ... **Details:** ...
**Suggested fix:** ...

## Uncited

Items from the uncited-claim check, and under a `Missed claims` subheading, the missed-claims pass rows.

## Detector candidates

Categories the missed-claims pass found in two or more chapters (see `missed-claims-pass.md`).
```

Omit fields that do not apply. An item-scoped or `--only-changed` run MUST carry the "Items skipped"
line, so that a clean result is not read as a clean chapter.

## Summary: `fact-check.md`

Written last. Run mode, input mode, date, scope, totals (and items skipped in an `--only-changed` run),
a results table per chapter (verified / minor / significant / unverifiable / total), every
SIGNIFICANT ISSUE with its chapter, cross-citation consistency issues, every UNVERIFIABLE item with
what was tried, and links to the chapter files.

## Verdicts

Graded against `reference-standard.md`: VERIFIED (the source holds the idea), MINOR ISSUE (a detail
is off; a small fix), SIGNIFICANT ISSUE (the source does not hold the idea, the attribution is
wrong, or a quote differs materially), UNVERIFIABLE (say what was tried). Every MINOR and
SIGNIFICANT item carries a suggested fix with concrete text.

## Confidence

| Level | Evidence | Confidence |
|---|---|---|
| 1 | the source itself: full text, abstract for an abstract-level claim, an official record | Strong |
| 2 | the book's notes or quotes bank, pointing to a primary source you then read | Strong |
| 3 | a secondary source that cites the paper and confirms the claim | Moderate |
| 4 | several independent sources attributing the same fact | Moderate |
| 5 | one secondary source or an encyclopedia | Weak |
| 6 | general knowledge only, no external check | Very weak: say so explicitly |

A single secondary source confirming a claim is not the original: it may repeat the same error.

## Findings become notes

Every MINOR ISSUE, SIGNIFICANT ISSUE and UNVERIFIABLE item, and every uncited claim the run keeps,
becomes one note in the notes file of the file it is in (a manuscript file or a thinking file:
`thinking/argument/claims.md` -> `notes/claims.md`), in the folder `notes` of book.yaml, in the format of
`${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/note-format.md`:

- `**From:** check-facts, <YYYY-MM-DD HH:MM>`, and the key in the Note (`[Smi99]: the source
  gives 1987, the book says 1978`);
- the paragraph quoted word for word, the flagged sentence as Text, the suggested fix in Options,
  and what was verified (the quote from the source, with its location) in Analysis;
- an id from `python3 ${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/open-notes.py next-id <file>`.

VERIFIED items do not become notes. A verified quote goes into the quotes bank (staged, then
merged) whatever the verdict, because it is a fact about the source, not about the book.
