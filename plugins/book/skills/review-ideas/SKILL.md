---
name: review-ideas
description: >-
  Reviews the argument, structure and evidence of a non-fiction book and writes every finding
  that survives as a note in the notes folder. Two modes. editor (the default) knows the book's
  decisions and thinking files and runs three cold stages (map, attack, judge) and a blind
  verification pass. readers is a clean room next to the book that knows nothing about it: one
  cold reader per lens, skeptics that try to prove each serious finding wrong, and its own list
  of neutral sources for the reviewer. Use it when the author asks to review the book or a
  draft, critique the argument, find contradictions, weak evidence, unfair treatment of other
  authors or a defined idea that changes meaning across chapters, or wants an outside,
  independent or pre-print review. For prose
  style use review-text; to check one claim, quote or figure against its source use check-facts;
  to answer the notes use revise-from-notes. Stance: only findings that survive a check reach
  the author, and the author decides.
---

# Review ideas

A review of what the book says, not how it says it: ideas, arguments, facts, consistency and
what a reader experiences. Prose style is out of scope (review-text).

## Modes

| Mode | Where | Knows | Full procedure |
|---|---|---|---|
| `editor` (default) | this session, in the book folder | the manuscript and bibliography in the stages; `decisions.md` and the thinking files in the main agent | `references/editor.md` |
| `readers` | a clean room next to the book, then a new session in it | nothing but a frozen copy of the manuscript, the sources list, a neutral list of sources and `decisions.md` | `references/readers-room.md` |

Both modes take two options:

- `--resume`: continue the newest run of the same mode that stopped, from the files already
  written (`run_folders.py latest review-ideas <mode>`). A file that is complete is never made
  again.
- `--only-changed`: the reviewers still read the whole book, because an argument runs across
  chapters, but findings are kept only for the files changed since the last run of the same
  mode (`run_folders.py changed review-ideas <mode>`). Open notes from earlier runs stay as they
  are.

Every run has its own folder, `<work.runs>/<YYYY-MM-DD-HHMM>-review-ideas-<mode>/`, made with
`python3 ${CLAUDE_PLUGIN_ROOT}/lib/run_folders.py start review-ideas <mode> --fix` (editor) or by
`clean-room.py collect` (readers); the newest three per mode are kept. A run ends with
`run_folders.py record <run folder> <files read> --fix`, so the next `--only-changed` run has
checksums to compare.

Pick `readers` when the author asks for an outside, independent, cold, multi-lens or pre-print
review; otherwise `editor`. Ask when unsure: `readers` costs far more.

## Before either mode

1. **Find the book.** Every path comes from `book.yaml` through the plugin's lib:
   `python3 ${CLAUDE_PLUGIN_ROOT}/lib/book_config.py show`. Never hardcode a book path.
2. **Read only the decisions index** (`python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py index`)
   and open the entries you need (`decisions.py show ID`). The main agent knows what the book
   has settled; it does not pass the file to cold agents, except as each mode's procedure says. See `references/using-decisions.md`.

## editor, in short

Each stage is a fresh subagent with no edit history that reads the whole manuscript:

1. **Map** (`references/stage-1-map.md`): claims, definitions, citations, stances, mainstream
   map. Then the main agent seeds the glossary with the terms Stage 1 found, only after the
   author agrees (`glossary-seed.py`, dry run first, `--fix` on yes; format in
   `${CLAUDE_PLUGIN_ROOT}/lib/glossary-format.md`).
2. **Attack** (`references/stage-2-attack.md`): six passes over every claim, with the citation
   report of check-facts and the glossary report of write-text as inputs.
3. **Judge** (`references/stage-3-judge.md`): sorts every finding, matched against
   `decisions.md` with `match-decisions.py`; adds what Stage 2 missed; reads as the target reader.
4. **Verify** (`references/verification-pass.md`): every serious finding against the chapter and
   the cached sources, blind.

Then the surviving findings become notes. The run folder, the commands and every script:
`references/editor.md`.

## readers, in short

1. **Setup**, in the book folder: make the list of neutral sources for the reviewer with
   `sources-for-reviewer.py` (`references/sources-for-reviewer.md`), save the mechanical citation
   checks, then `clean-room.py setup` makes the room next to the book with the plugin switched
   off there.
2. **Run**, in a new session in the room: the room's `REVIEW-PLAN.md` (this skill's
   `references/readers.md` with the book's lenses filled in): lenses, merge, skeptics, report.
3. **Status**, in the room: `review-state.py status`.
4. **Bring back**, in the book folder: `clean-room.py collect --fix`, then every surviving finding
   becomes a note. Killed findings never do. Then `clean-room.py remove --fix` takes the room
   away.

Full procedure, the room's contents and the `readers_review` settings in book.yaml:
`references/readers-room.md`.

## Findings become notes

Both modes end the same way. Every finding that survives becomes one note in the notes file of
its manuscript file (`whole-book.md` for a finding about the whole book), in the folder
`notes` of book.yaml, in the format of
`${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/note-format.md`:

- `**From:** review-ideas <mode>, <YYYY-MM-DD HH:MM>`, and the run's finding id in the Note;
- the paragraph quoted word for word, the flagged sentence as Text, the suggested fix in Options;
- an id from `python3 ${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/open-notes.py next-id <file>`.

A finding that matches a DECIDED entry is not written. A finding that repeats an open note is
added to that note, not written twice. After writing, run `open-notes.py check`. The stage
files, artifacts and reports stay in the run folder (`work.runs`); the decisions are recorded
by revise-from-notes when the author answers each note, never by the review (a note may suggest one).

## Rules that hold in both modes

- **Decided items are not findings.** A finding that repeats a DECIDED entry is not reported and
  not argued again; never propose an option an entry says was rejected.
- **Cold reviewers.** Every stage, lens and skeptic is a fresh agent with no edit history and no
  other agent's report. Every agent reads the whole book before writing.
- **Read the unit that governs a flagged sentence before reporting it**: its paragraph, the
  chapter's citation list, the prose around a listing, the book's rulings on vocabulary
  (`references/false-positives.md`).
- **Truth over punch.** A finding must survive the verification pass or the skeptics; a
  confident finding from an abstract, a secondary quote or memory is not evidence.
- **A fix is for the whole defect class.** Search the book for the same defect elsewhere, not
  only at the reported line (`references/why-findings-return.md`).
- **The review never edits the manuscript.** Only the glossary seed writes a lasting file, and
  only after the author agrees.
- For the perspectives a professional review covers, and which skill owns each:
  `references/review-dimensions.md`.

## Scripts

All in `${CLAUDE_PLUGIN_ROOT}/skills/review-ideas/scripts/`; each has `--help` and writes
nothing without `--fix` (or `--report`, which writes one file into the run folder).

| Script | Mode | What it does |
|---|---|---|
| `glossary-seed.py` | editor | terms the glossary lacks, from the Stage 1 definitions index; `--fix` adds them |
| `match-decisions.py` | editor | each finding of a stage file against `decisions.md` |
| `sources-for-reviewer.py` | readers | drafts the list of neutral sources for the reviewer; `check` tests one for bias |
| `clean-room.py` | readers | `setup` makes or refreshes the room; `collect` brings the results back; `remove` takes the room away once collected |
| `review-state.py` | readers | `status`, `findings`, `queue`, `check` of a room or a collected run |
| `self-check.py` | - | maintainer check on fixtures only; runs `readers-self-check.py` too |

## References

| File | Holds |
|---|---|
| `references/editor.md`, `stage-1-map.md`, `stage-2-attack.md`, `stage-3-judge.md`, `verification-pass.md` | the editor mode |
| `references/evidence-grades.md`, `false-positives.md`, `why-findings-return.md`, `using-decisions.md` | how findings are graded and screened |
| `references/readers-room.md`, `readers.md`, `lenses.md`, `skeptic-rules.md`, `merge-and-verify.md` | the readers mode |
| `references/sources-for-reviewer.md` | the list of neutral sources for the reviewer |
| `references/review-dimensions.md`, `publisher-review-practice.md` | what professional reviews cover |
| `templates/` | the files the room writes, and the room's plan and CLAUDE.md |
