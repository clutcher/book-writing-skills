# The readers mode

A review by readers who have never seen the book: no notes, no thinking files, no edit history. Each lens
is one cold agent with one question. Skeptics then try to prove every serious finding wrong. Only
findings that survive reach the author, as notes.

**The goal:** find what a real reviewer or paying reader will hit, while it can still be fixed.
**Not the goal:** shaping or rebuilding the book. Use it on a nearly finished book.

The mode runs in four steps: `setup` in the book folder, `run` in a new session in the room
(`--resume` continues a stopped run there), `status` in the room, and bringing the findings back
as notes in the book folder.

## Rules for the readers mode

1. **Read the `## Index` of `decisions.md` first**, then only the entries you need. A DECIDED
   item is not a finding. What each status allows is in
   `references/skeptic-rules.md`. Never raise a DECIDED item again.
2. **A skeptic's verdict is not the author's ruling.** "Killed" means the finding failed a check.
   Only the author decides, when revise-from-notes answers the notes.
3. **Cold reviewers, one agent per lens.** No agent sees another lens's report, the author's
   notes, or the edit history. Every agent reads the whole book before writing.
4. **Priority = likelihood a real reader hits it × damage × still fixable now.** Serious problems
   are reported as hidden risks (the author may choose to fix them: "decide whether to
   fix this before print"), not as rebuild plans.
5. **Ask before every batch.** No stage, lens batch or skeptic wave starts without the author's
   yes. Say what is done, what comes next, and the rough cost.
6. **Write every file the moment it is done.** The files are the checkpoint. A finished file is
   never made again.
7. **No hidden gaps.** What was not checked is stated, never dressed up as full coverage.
8. **Truth before sales.** When soundness and marketing disagree, soundness wins.
9. **The orchestrator never reads the book.** The orchestrator is the session that runs the review
   in the room. It starts the agents, merges, ranks and writes.
10. **Run output is dated.** Results live in the run folder (`work.runs` in `book.yaml`), never in
    a bank or in memory as "done". The book changes; a verdict is true only for the draft it read.

## Step 1, setup

Run in the book folder. The commands in this file use two shell variables:

```bash
LIB="${CLAUDE_PLUGIN_ROOT}/lib"
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/review-ideas/scripts"
```

1. **Check `decisions.md` is current.** Run `python3 "$LIB/decisions.py" check`; with `--fix` it
   only writes missing Status lines and rebuilds the index, and never adds an entry. If an agreed
   fix from an earlier round is not yet an entry, stop and ask the author to answer that note with
   revise-from-notes first: only revise-from-notes adds entries.
2. **Make the list of neutral sources for the reviewer** with this skill's
   `sources-for-reviewer.py` (rules and shape: `references/sources-for-reviewer.md`). It lists
   neutral primary sources for the claims the book stands on, and never argues the book's case:

   ```bash
   python3 "$SCRIPTS/sources-for-reviewer.py" draft --claims claims.tsv --out <readers_review.sources_for_reviewer>
   python3 "$SCRIPTS/sources-for-reviewer.py" check <that file>
   ```

   The room script looks for it at `readers_review.sources_for_reviewer`, else
   `<work.output>/sources-for-reviewer.md`.
3. **Run the mechanical citation checks** and save the output to a file:
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py" facts --no-report > <file>`. They cost no model tokens, and the room
   gets the result as `review/mechanical-checks.txt`, so no lens redoes them.
4. **Dry run, show the author, then make the room:**

```bash
python3 "$SCRIPTS/clean-room.py" setup --checks <saved check output>
python3 "$SCRIPTS/clean-room.py" setup --checks <saved check output> --fix
```

The room is a folder next to the book (`<book folder>-readers-review`, or `readers_review.room`).
It gets:

- `manuscript/`: a frozen copy;
- `sources/list.md` and `sources/sources-for-reviewer.md`;
- `decisions.md`;
- `book/facts.md` and `book/back-cover.md`: title, subtitle and cover text live outside the
  manuscript, and a lens that does not see them reports "no subtitle" as a blocker;
- `REVIEW-PLAN.md`, `plan/` (the rules and templates the agents need) and `CLAUDE.md`;
- `.claude/settings.local.json`, which switches this plugin and its skills off, plus any names in
  `readers_review.skills_off`. The author's own rules must not steer a cold reader;
- `room.json`: the round number and the lens list.

The room holds nothing from `thinking/`, `notes/` or the quotes bank.

Running `setup` again on a room with results takes `review/` out of the room and starts the next
round with a fresh copy of the manuscript. Results that `collect` already copied are removed from
the room; results that were never collected move to a new run folder,
`<work.runs>/<YYYY-MM-DD-HHMM>-review-ideas-readers/`. Earlier rounds never stay in the room, where a cold reviewer could read them. Running
`setup` on a room with no results yet only refreshes it and keeps the round.

5. **Tell the author what still reaches the room.** The settings switch off plugin skills only.
   The author's own user-level instructions (a global `CLAUDE.md`), user-level skills and memory
   still load there and in every agent. Ask the author to check them for anything about this
   book, and to list every user-level skill that knows the book in `readers_review.skills_off`.
6. **Tell the author:** open a new Claude Code session in the room folder and say "run the review
   in REVIEW-PLAN.md". This skill is off there on purpose; the plan in the room carries
   everything the session needs. The first thing the session does is check that no skill of
   the book plugin is listed (for example with `/skills`). If one is, it stops and says so: the settings
   did not work, and the room is not cold.

## Step 2, run

In the room, follow `REVIEW-PLAN.md`. It is `references/readers.md` with this book's lenses
filled in. In short:

- **Stage A, lenses.** One agent per lens, at most 3 at once, blocker lenses first. Each writes
  `review/lens-<n>-<name>.md` from the lens report template, with ids `L<n>-<k>`, at most about
  12 findings (the rest one line each under `## Below the cut`), and a coverage log. Every lens
  also says, for each `OPEN / fix owed` entry in its area, whether the agreed fix landed.
- **Stage B, merge.** The orchestrator merges near-duplicates (strictest severity kept, all ids
  listed), links related findings, records what it did not merge and why, and writes the
  verification queue into `review/merge-map.md`. See `references/merge-and-verify.md`.
- **Stage C, skeptics.** At most 2 at once, in waves: blockers one skeptic each; source checks
  batched by source family; other majors in batches of 3 to 4 on one theme. Verdicts:
  `confirmed`, `downgraded`, `killed`, `rebuttable-misreading`. One file per finding in
  `review/verification/`.
- **Stage D, report.** `review/REVIEW-REPORT.md` from the final report template: verdict (ship,
  fix-then-ship, hold), the continuity table (copied from what the lenses said about each
  `OPEN / fix owed` entry), ranked hidden risks,
  strengths to protect, positioning, mechanics log, coverage. Killed findings never appear.

**Use the Workflow tool if it is available** (load `workflow-authoring` first): the stages, batch
limits, merge barrier and waves are fixed logic, not something to improvise. **Otherwise** run the
agents as subagents yourself, one batch at a time. Every agent uses the session's model; save
tokens with scripts and grouping, never with a weaker skeptic.

## Step 3, status

```bash
python3 "$SCRIPTS/review-state.py" --room <room> status     # done, and what runs next
python3 "$SCRIPTS/review-state.py" --room <room> findings   # every finding, one line each
python3 "$SCRIPTS/review-state.py" --room <room> queue      # verification queue and verdicts
python3 "$SCRIPTS/review-state.py" --room <room> check      # malformed files (check contract)
```

The room's `REVIEW-PLAN.md` carries the same commands with the full paths filled in. `status`
reads only `review/` and `room.json`, never the book, so the orchestrator can resume in a fresh
session from the files alone. `check` must be clean before the report is written, and fails if a
killed finding appears in the report.

## Step 4, bring the findings back as notes

Back in the book folder, with the skills on.

1. Copy the results into a run folder (dry run first):
   `python3 "$SCRIPTS/clean-room.py" collect --fix`. It makes
   `<work.runs>/<YYYY-MM-DD-HHMM>-review-ideas-readers/` and keeps the newest three such runs. Then
   `python3 "$SCRIPTS/review-state.py" --room <run folder> findings` lists every finding.
2. Read the decisions index (`python3 "$LIB/decisions.py" index`) before writing a single
   note, and match each surviving finding:
   `python3 "$LIB/decisions.py" match "<finding>"`. A finding that matches a DECIDED entry is
   dropped. An `OPEN / fix owed` entry the report's continuity table says has landed is named to
   the author; revise-from-notes closes it on the author's yes ("Fixes owed that have landed").
3. Framing check on thesis findings: is this a problem the book sets up on purpose and solves
   later? If yes, drop it and say why in the run folder.
4. Write every surviving finding as one note in the notes file of its manuscript file
   (`whole-book.md` when it is about the whole book), in the format of
   `${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/note-format.md`, with
   `**From:** review-ideas readers, <run time>` and the finding id (`L3-2`) in the Note. Killed
   findings are never written. With `--only-changed`, only findings in the files that
   `python3 "$LIB/run_folders.py" changed review-ideas readers` lists become notes; the room
   still holds the whole book, because a cold reader must read all of it. Then run
   `open-notes.py check` and record what the run read:
   `python3 "$LIB/run_folders.py" record <run folder> --fix`.
5. Remove the room once its findings are notes and the author agrees, dry run first:
   `python3 "$SCRIPTS/clean-room.py" remove --fix`. It refuses while the room holds results that
   `collect` has not copied.

## Configuration (`book.yaml`)

```yaml
readers_review:
  room: ../my-book-readers-review                   # default: <book folder>-readers-review
  sources_for_reviewer: .book/output/sources-for-reviewer.md   # made with sources-for-reviewer.py
  main_metaphor: "the metaphor in the title"        # Lens 8
  key_sources: ["[Key1]", "[Key2]"]                 # Lens 2 checks these hardest
  research_field: "the field the book leans on"     # Lens 3
  similar_books: ["Similar Book One", "Two"]        # Lens 6
  author_background: "years in the field, roles"    # Lens 6
  audience: "who the book is for"                   # the contract and Lens 4
  lens_batch: 3
  skeptic_batch: 2
  skills_off: ["another-skill-of-the-author"]       # also switched off in the room
  plugin_id: book@book-writing-skills               # if installed from another marketplace
  lenses: [...]                                     # replaces the default nine
```

The nine default lenses: thesis and argument, correctness and evidence, borrowed research, teaching,
mechanics and consistency, market and positioning, reader drop-off and clarity, main image,
strengths to protect. How to change them: the end of `references/lenses.md`. A book with no
code skips the code part of Lens 2 on its own; Lens 3 applies only when the book borrows research
from another field; such a book can also drop it by listing the other lenses in `lenses:`.

