# Stage B: merge map

**Date:** <date>
**Input:** <number> lens reports, <number> findings (per lens: L1 <n>, L2 <n>, ...)
**Rule:** near-duplicates merged before verification; a merged unit keeps the strictest severity
and lists every contributing id.

## Mechanical checks

<result from review/mechanical-checks.txt: clean, or what failed. If the file is missing: "mechanical checks not run".>

## Merged findings

| Merged ID | Members | Kept severity | One-line statement |
|---|---|---|---|
| M1 | **L4-4** + L7-2 | major | <statement> |

## Linked, not merged

- **L1-1 ↔ L3-3**: <why they are related, and why they stay separate>

## Tensions with the strengths lens

- **L7-1 ↔ L9-7**: <what the strength defends; the skeptic gets it as defence>

## Not merged despite looking alike

- **L3-3 vs M2**: <reason: same topic, different defect or fix>

## Verification queue

| # | ID | Severity | Wave | Group | Finding |
|---|----|----------|------|-------|---------|
| 1 | L1-1 | blocker | 1 | solo | <one line> |
| 2 | M1 | major | 2 | family: <source family> | <one line> |
| 3 | L4-2 | major | 3 | theme: <theme> | <one line> |

## Skipped verification

- **Strengths:** <ids>
- **Minors:** <ids>
- **Nits:** <ids>
- **Recall-based minor citations** (offer one batched fact-check agent at the Stage C gate): <ids>
