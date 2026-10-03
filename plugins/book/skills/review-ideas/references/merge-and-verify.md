# Stage B: merge before verifying

The orchestrator does Stage B alone, with no agents. It reads the lens reports, never the book.
The aim: every separate issue is checked exactly once, with the context of every lens that hit it.

## Steps

1. **Mechanical checks first.** The citation checks were run before the room was made, with zero
   model tokens, and their output is in `review/mechanical-checks.txt`. Record the result at the
   top of the merge map: clean, or what failed. If the file is missing, say "mechanical checks not
   run" in the map and in the report's coverage section. Never leave it out silently.
2. **List every finding.** `review-state.py findings` prints one line per finding with its lens,
   severity, tier and title.
3. **Merge near-duplicates.** Findings from different lenses that name the same defect with the
   same fix become one unit, `M1`, `M2` ... The unit keeps the **strictest severity** and lists
   **every** contributing id. Mark the lead id; the verification file is named after the merged id.
4. **Link, do not merge, related findings.** Findings that are related but different (same
   passage, different defect; one instance and the general pattern) are cross-linked, so each
   skeptic gets the other's context.
5. **Mark tensions.** When the strengths lens defends what another lens attacks, write the pair
   down. The skeptic gets the strength as defence. Stage D decides.
6. **Write down what you did not merge, and why.** "Same chapter, different defect." "A fix for
   one does not fix the other." A merge you did not make is a judgment, and it must be on record.
7. **Build the verification queue.** Blockers first, then majors in priority order. Give each
   row a wave (1 blocker skeptics, 2 source checks, 3 major batches) and a group (`solo`, a
   source family name, or a theme name). Minors, nits and strengths are listed as skipped.
8. **Recall-based minor citations.** List them, and offer the author one batched fact-check agent
   for them at the Stage C gate.

## The queue table

`review-state.py` reads the table under the heading `## Verification queue`. Keep these column
names: `#`, `ID`, `Severity`, `Wave`, `Group`, `Finding`. `ID` is a finding id (`L2-4`) or a
merged id (`M3`); a merged id must also appear in the `## Merged findings` table with its members.

```
| # | ID | Severity | Wave | Group | Finding |
|---|----|----------|------|-------|---------|
| 1 | L1-1 | blocker | 1 | solo | one line |
| 2 | M1 | major | 2 | family: productivity studies | one line |
| 3 | L4-2 | major | 3 | theme: chapter 9 examples | one line |
```

## Fetching sources

A source check fetches the primary source. Links and bibliographic data may come from the sources
list and the sources for the reviewer. What that list says a source means is a lead only (see
`skeptic-rules.md`).
