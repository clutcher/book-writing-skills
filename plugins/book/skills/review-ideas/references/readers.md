# The review workflow

The review runs in four stages, inside the clean room. The orchestrator is the session opened in
the room, the one that runs the review. It dispatches agents, merges, ranks and writes. **It never reads the book itself.**

```
Stage A  lens review         one cold agent per lens, whole book each, at most 3 at once
Stage B  merge               orchestrator only: mechanical results, duplicates merged, queue
Stage C  skeptics            adversarial check of every blocker and major, at most 2 at once
Stage D  report              orchestrator only, from the files on disk
```

## What makes the review succeed

It is ranked, checkable, and honest about how sure it is, and it changes at least one decision
before print. A review that lists 40 findings of equal weight has failed, even if every one of
them is true.

## Gates: ask before every batch

No stage starts without the author saying yes. Inside Stage A and Stage C, no batch or wave starts
without its own yes either. Each gate says:

- what is finished (from `review-state.py status`);
- what the next batch holds (lenses, or finding ids and their groups);
- a rough cost (each agent reads the whole book once).

"Not yet" never touches the files already on disk.

## Stage A: lens review

- One agent per lens, in batches of at most 3 (`readers_review.lens_batch`). The blocker lenses
  go in the first batch; the rest follow in number order. `review-state.py status` prints the
  next batch.
- Each agent starts with a clean context: no edit history, no thinking files, no other lens's
  report. It reads the plan, the pre-read pack (`lenses.md`), then the whole manuscript start to
  end, then writes `review/lens-<n>-<name>.md` from `plan/templates/lens-report.md`.
- Ids are `L<lens>-<n>`. They stay the same through the rest of the run.

## Stage B: merge

Follow `merge-and-verify.md`. The orchestrator reads only the lens reports (never the book) and
writes `review/merge-map.md` from `plan/templates/merge-map.md`. The map ends with the
verification queue, which `review-state.py` reads.

## Stage C: skeptics

- Every blocker and major in the queue gets a skeptic. Minors, nits and strengths do not.
- **Grouping.** Most of a skeptic's cost is reading the book, but independence matters most where
  the verdict matters most. So:
  - each `blocker`: one skeptic alone (group `solo`);
  - findings that need an outside source (a cited study, a quote, a figure): batched **by source
    family**, so one agent fetches a family of sources once;
  - the other majors: batches of 3 to 4 **on one theme** (same chapters or passages). Never put
    unrelated findings in one batch.
- A skeptic with several findings checks them **one at a time, and starts each with fresh
  doubt**. It writes `review/verification/<id>.md` before it starts the next one. So a batch
  gives the same files as solo work.
- **Waves by severity.** Wave 1 is the blocker skeptics, wave 2 the source checks, wave 3 the
  major batches. Each wave needs its own yes. If the run stops early, the most important verdicts
  are already on disk.
- At most 2 skeptics at once (`readers_review.skeptic_batch`).
- The skeptic uses `plan/templates/verification.md` and the rules in `skeptic-rules.md`.

## Stage D: report

The orchestrator applies the priority formula and "truth before sales" to the surviving findings
and writes `review/REVIEW-REPORT.md` from `plan/templates/final-report.md`. It fills the
continuity table by copying each lens's `## Agreed fixes from earlier rounds` answers; an
`OPEN / fix owed` entry no lens answered is listed as "not checked". Killed findings never
appear. Before writing, it runs `review-state.py check`: it must report no defects, and no killed
id may appear in the report.

## Resume: the files are the checkpoint

The run must survive a usage limit at any point and go on in a later session.

- **Write as you go.** Every file is written the moment its step finishes: each lens report as its
  agent ends (not at the end of the batch), the merge map when Stage B ends, each verification file
  as its verdict lands. No result lives only in the orchestrator's memory.
- **Resume.** On restart, run `review-state.py status`. It skips every step whose file exists and
  names the next step. Only missing files are made. A file is never made again once written.
- **One agent is the unit of loss.** A limit hit inside an agent loses only that agent's work; it
  runs again from the start.
- **Files stand alone.** Each lens report and verification file carries its ids, locations and
  severities inline, so a fresh session can resume from the files alone.
- A lens report counts as finished only when it has its `## Coverage log` section.

## How to run the agents

**If the Workflow tool is available**, put the control flow in a workflow script: the stages,
the batch limits, the merge barrier, the waves. It is fixed logic and should not be improvised
turn by turn. Load the `workflow-authoring` skill first. Let each agent return JSON with its ids
and severities, and still write its file to disk: the workflow's own cache helps inside one
session, but the files are what survive between sessions.

**If not**, run the agents yourself as subagents, one batch at a time, never more than the batch
limit at once, and ask at every gate.

**Every agent uses the session's model.** Reading for a lens and trying to refute a finding are
judgment work. A weaker skeptic approves findings without really testing them. Save tokens with
scripts and good grouping, not with cheaper models.

## What each agent is told

Lens agent:

```
You are Lens <n>, <name>, in a cold outside review of a book. You have never seen this book.
Read REVIEW-PLAN.md, plan/lenses.md (the pre-read pack and your lens), plan/skeptic-rules.md,
the "## Index" of decisions.md (then only the entries you need), book/facts.md, book/back-cover.md and review/mechanical-checks.txt (if it
exists). Then read every file in manuscript/ in name order, start to end. Only then write
review/lens-<n>-<file name>.md from plan/templates/lens-report.md. Ids L<n>-1, L<n>-2 ... At
most about 12 findings; the rest one line each under "## Below the cut". Answer every
OPEN / fix owed entry in your area. Read nothing outside this folder, and nothing in review/
but the mechanical checks. Do not edit anything outside review/. Return: {"lens": <n>, "file": "...", "findings": [{"id", "severity",
"tier", "title"}]}.
```

Skeptic agent:

```
You are a skeptic in Stage C of a cold outside review. Your job is to find the strongest case
that each finding below is WRONG. Read REVIEW-PLAN.md, plan/skeptic-rules.md, the "## Index"
of decisions.md (then only the entries you need), book/facts.md, then the whole manuscript start to end. Then, for each finding in turn, with fresh
doubt each time: read the lens report entry and every linked finding in review/merge-map.md
(nothing else in review/, and nothing outside this folder),
check every quoted line, fetch the sources the finding depends on, and write
review/verification/<id>.md from plan/templates/verification.md before starting the next one.
Findings: <ids>. Return: [{"id", "verdict", "severity_after", "tier_after"}].
```
