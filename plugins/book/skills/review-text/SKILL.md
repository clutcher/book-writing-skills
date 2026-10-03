---
name: review-text
description: >-
  Reviews the prose of a non-fiction book against the book's prose rules and voice, and writes
  every finding as a note in the notes folder. Five modes, no default: for one chapter
  common-problems, flow and all-problems; for the whole book consistency and hard-words. Use it
  when the author asks to review, critique or check the writing of a chapter or of the book:
  flow, transitions, structure, term drift, voice shifts, or words that block a new reader. To
  change the text itself, use write-text; to answer the notes, use revise-from-notes; for the
  argument and evidence, use review-ideas; for facts, quotes and numbers, use check-facts.
  Stance: a review finds and explains, it never edits the manuscript.
---

# Review text

A prose review reads the text the way the book's rules describe it and reports what breaks
them. The rules, the voice profile and the text check scripts live in the write-text skill; this
skill holds the review workflows. Every finding becomes a note, and the revise-from-notes skill
answers the notes with the author.

## Modes

There is no default mode. With no mode named, ask which one, and say what each covers.

| Mode | Reads | File | What it checks |
|---|---|---|---|
| `common-problems` | one chapter | `references/common-problems.md` | The six most frequent issues and the four cascades behind them. Start here for any chapter. |
| `flow` | one chapter | `references/flow.md` | Topic-develop-conclude at every level, sentence and paragraph chains, transitions, openings, summaries, forward disclosure. |
| `all-problems` | one chapter | `references/all-problems.md` | A full scan over every rule category, the most thorough chapter review. |
| `consistency` | the whole book | `references/consistency.md` | Term drift, voice shifts, repeated examples, Part boundaries, references between chapters. |
| `hard-words` | the whole book (one chapter when the author names it) | `references/hard-words.md` | Terms that block the least experienced reader the book names. |

Read the mode's file and follow it. A chapter mode needs a chapter: take the one the author
names, or ask.

Every mode takes two options:

- `--only-changed`: only the files changed since the last run of the same mode
  (`python3 ${CLAUDE_PLUGIN_ROOT}/lib/run_folders.py changed review-text <mode>`). For a chapter
  mode this tells whether the named chapter changed at all; for `consistency` and `hard-words`
  every chapter is still read, but findings are kept only in the changed chapters (for
  `hard-words`, the last run is also the baseline).
- `--resume`: continue the newest run of the same mode that stopped, in its own run folder
  (`run_folders.py latest review-text <mode>`), skipping the files already done.

## Before any review

1. **Find the book.** `python3 ${CLAUDE_PLUGIN_ROOT}/lib/book_config.py show` prints the paths.
2. **Read the rules.** The Rules Summary in `${CLAUDE_PLUGIN_ROOT}/skills/write-text/SKILL.md`,
   with the full text in `${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/rules-explained.md`.
   Every finding names the rule it applies, by number.
3. **Read the voice profile** (`rules.voice`, or
   `${CLAUDE_PLUGIN_ROOT}/skills/write-text/profiles/default.md` when the book has none).
4. **Read only the decisions index** (`python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py index`)
   and open the entries you need (`decisions.py show ID`). Never report an item marked DECIDED.
   Match each finding before writing it:
   `python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py match "<finding text>"`.
5. **Read the glossary** (`rules.glossary`): the terms the book defines.
6. **Run the text checks first** where the mode's file says so. They live in
   `${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts/`; the run-checks skill runs them all
   (`${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py text <chapter file>`).
   In `common-problems` and `all-problems`, also run Vale on the chapter
   (`${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/vale-check.md`): every alert at warning
   or error level becomes a note like any other finding, with `From: review-text <mode>`.
7. **Start the run folder:**
   `python3 ${CLAUDE_PLUGIN_ROOT}/lib/run_folders.py start review-text <mode> --fix` prints
   `<work.runs>/<YYYY-MM-DD-HHMM>-review-text-<mode>/` and keeps only the newest three runs of
   that mode. With `--resume`, use the folder `run_folders.py latest review-text <mode>` prints
   instead.

## Findings become notes

Each mode's file has an output format. Every finding in that format becomes one note in the
notes file of its manuscript file (a finding about the whole book goes to `whole-book.md`). The
notes folder is `notes` in book.yaml. The note format is in
`${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/note-format.md`. Write the fields a
note gets when it is created, from the mode's output like this:

| Note field | From the mode's output |
|---|---|
| **From** | `review-text <mode>, <YYYY-MM-DD HH:MM>` (the run time) |
| **Tier** | `Flow` for a `flow` finding; otherwise the tier the fix needs, by the tier table of revise-from-notes: `Surface` for one word or mark, `Flow` for sentences and their order, `Content` for a claim, a definition or a term the book defines (a `consistency` term drift and a `hard-words` defined term are Content) |
| **Root cause** | the a-g label of `${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/analysis-method.md` that fits the problem |
| **Paragraph** | the heading text of the Location (or Section), then the paragraph quoted word for word |
| **Text** | the Text, in quotes |
| **Note** | the Problem (or Issue), with the rule number |
| **Options** | the Suggestion (or Suggested fix), in full context |

- Get each id with
  `python3 ${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/open-notes.py next-id <file>`.
- A finding that repeats an open note is not written twice: add to the open note instead.

Summaries, counts, paragraph walks and the "what works well" part of a report go to the run
folder, never into the notes. After writing the notes, run `open-notes.py check`, record the
files the run read (`run_folders.py record <run folder> <files> --fix`, for the next
`--only-changed`), and report the number of notes written per file and the run folder.

## Rules that hold in every mode

- **A review never edits the manuscript.** It writes notes; the author decides with
  revise-from-notes.
- **Decided items are not findings.** Never re-propose an option the decisions say was
  rejected. A review never writes a decision: revise-from-notes records it when the author
  answers the note.
- **Read before you flag.** Read the paragraph and its neighbours before reporting a sentence;
  a flagged word is often explained in the next sentence.
- **Truth over punch.** A suggested fix must itself survive a fact-check and the book's rules.
- **One finding per defect, not per symptom.** When several findings share a root cause, write
  one note that names the cause and links the places.

## References

| File | Holds |
|---|---|
| `references/common-problems.md` | the `common-problems` review |
| `references/flow.md` | the `flow` review |
| `references/all-problems.md` | the `all-problems` review |
| `references/consistency.md` | the `consistency` review of the whole book |
| `references/hard-words.md` | the `hard-words` review: method, severity, run folder |
| `${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/vale-check.md` | what Vale catches, how to read its alerts, which fixes are mechanical |
| `references/hard-words-criteria.md` | when a word or phrase is worth flagging for a reader new to English or the field |
| `references/review-checks.md` | book conventions a review can check (definition blockquotes, exemptions, hidden questions) |
| `references/mechanics-checklist.md` | mechanical consistency checks before print |
| `references/structure-census.md` | heading and paragraph census as an outlier finder |
