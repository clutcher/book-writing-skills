# Outside review report: <book title>

**Round <n>, <dates>.** <number> lenses each read the whole manuscript on their own (Stage A,
<number> findings). Mechanical citation checks: <result or "not run">. Merged in Stage B
(<number> merges). Every blocker and major was checked by a skeptic (Stage C: <n> confirmed,
<n> downgraded, <n> killed, <n> rebuttable). Only findings that survived appear below.
Records: `review/verification/<id>.md`.

## 1. Verdict: ship | fix-then-ship | hold

<one paragraph: why>

### Did the last round's agreed fixes land?

Copied from each lens's `## Agreed fixes from earlier rounds`. An entry no lens answered is
"not checked".

| Agreed fix (decisions.md entry) | Status in this draft | Checked by | Found again as |
|---|---|---|---|

## 2. Ranked hidden risks

Ranked by priority = likelihood × damage × still fixable.

### Blockers: fix before print

**#1 · <ID>: <statement>**
`<severity> · <tier> · <verification outcome>`
*Location:* <where>
<why it matters>
*Fix:* <smallest change>
*Verification note:* <corrections from the skeptic>

### Majors, grouped by what they break

<same shape as blockers>

## 3. Strengths to protect

<from the strengths lens; each with the kind of edit that would destroy it>

## 4. Positioning and title

<shelf, comparable books, difference, findability of title and subtitle, buyer>

## 5. Mechanics log

Kept apart from the findings above so it does not crowd them.

### Citation checks
### Downgraded by verification (now minors)
### Minors and nits not verified (tier as filed), grouped by kind

## 6. Coverage and confidence (no hidden gaps)

- Lenses that read the whole book: <all, or which did not>
- Code: desk-checked by reading only; compile errors may survive (known risk). Or: the book has
  no code.
- Sources fetched and read: <list>
- Sources not reachable: <list, and which findings depend on them>
- Not verified by design: strengths, minors, nits.
- Findings below the cut in each lens report: <count per lens, or "none">

*Written by the orchestrator from the files in `review/`. Killed findings never appear.*
