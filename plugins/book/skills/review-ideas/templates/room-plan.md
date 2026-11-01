# Outside review plan: {{title}}

**Round {{round}}, room made {{date}}.**
**Goal:** find what a real reviewer or paying reader will hit, while it can still be fixed.
**Not the goal:** helping to shape or rebuild the book.

This folder is a clean room. It holds a frozen copy of the manuscript and nothing about how or why the book was written. The book skills are switched off here on purpose: reviewers must meet the book cold, the way a stranger does.

## Before you start

1. Check that no skill of the book plugin is listed in this session (for example with `/skills`). If one is, stop and tell the author: the room's settings did not switch the skills off, and the review would not be cold.
2. The settings switch off plugin skills only. The author's own user-level instructions, skills and memory still load here. If you see instructions about this book in them, tell the author before any agent starts, and name them in the report's coverage section.
3. The commands below point into the installed plugin. If the plugin is updated during the review and a command stops working, ask the author for the new path; do not remake the room.

## Read these, in this order

1. This file.
2. `plan/readers.md`: the four stages, the gates, and how to resume.
3. `plan/lenses.md`: the pre-read contract and every lens.
4. `plan/skeptic-rules.md`: the fixed process, tiers, severity, verdicts.
5. `plan/merge-and-verify.md`: Stage B.
6. `decisions.md`, its `## Index` first, then the entries you need: settled items are not findings.

Templates for every file the review writes are in `plan/templates/`.

## What is in the room

| Path | What it is |
|---|---|
| `manuscript/` | the frozen manuscript; never edit it |
| `book/facts.md` | title, subtitle, author: they live outside the manuscript |
| `book/back-cover.md` | the cover text, if the book has one |
| `sources/references.bib` | the book's sources: authors, title, year, one entry per citation key |
| `sources/list.md` | the book's sources list: where to read each source |
| `sources/sources-for-reviewer.md` | neutral primary sources for the load-bearing claims {{sources_for_reviewer_note}} |
| `decisions.md` | settled and open decisions |
| `review/` | everything this round writes; `review/mechanical-checks.txt` is the author's citation check |

Earlier rounds are not in the room. Do not look for them.

## Lenses

| # | Lens | Owns the question | Weight | Report file |
|---|------|-------------------|--------|-------------|
{{lens_table}}

Lens batches: at most {{lens_batch}} agents at once. Skeptics: at most {{skeptic_batch}} at once.

## Priority

priority = how likely a real reader or critic is to hit it × how much damage it does × how fixable it still is now.

## Tools

The orchestrator never reads the book. These commands read only the files in `review/`:

```bash
{{state_command}} status        # what is done, what runs next
{{state_command}} findings      # every finding, one line each
{{state_command}} queue         # the verification queue and its verdicts
{{state_command}} check         # format problems; run before writing the report
{{decisions_command}}
```

Mechanical checks: {{mechanical_checks_note}}

## Files this round writes

```
review/
  mechanical-checks.txt       the citation checks, made before the room (if run)
  lens-<n>-<name>.md          one per lens, written by its agent
  merge-map.md                Stage B: merges, links, the verification queue
  verification/<id>.md        one per checked finding
  REVIEW-REPORT.md            Stage D: the report
```
