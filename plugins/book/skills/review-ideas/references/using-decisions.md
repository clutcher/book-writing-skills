# How a review uses decisions.md

The book's `decisions.md` (path: `rules.decisions` in the book's config) holds every idea about
the book that was discussed and decided, or is still open. It opens with a generated `## Index`
(id, status, title); a run reads only the index (`decisions.py index`) and opens the entries it
needs (`decisions.py show ID`). Its format, the six statuses and what a run may
do with each are defined once, in the plugin's `${CLAUDE_PLUGIN_ROOT}/lib/decisions-format.md`; `${CLAUDE_PLUGIN_ROOT}/lib/decisions.py`
reads, checks, matches and writes it. This page says only how this skill uses it.

## The review never argues a decided item again

- The three stage agents read the manuscript and nothing else about the book, so they never
  open `decisions.md`. The book's earlier rulings reach Stage 3 through one artifact:
  `artifacts/decision-matches.md`, written by `match-decisions.py` from `stage-2-attack.md`.
- Stage 3 applies it as false-positive pattern FP-11: a finding that repeats a DECIDED entry is
  not reported; an `OPEN / fix owed` match is a regression check of the agreed fix; an
  `OPEN / decision owed` match is a reminder that an answer is owed; an `OPEN / undiscussed` match
  is reported normally, citing the entry.
- The main agent runs `match-decisions.py` again on `stage-3-judge.md` before it reports, so an
  M- finding that repeats a decision is caught too.

## Matching is by alias and keyword, never by run id

Every run reuses the same ids (`A-1`, `IC-2`) for different findings, so `match-decisions.py`
removes a finding's own run ids before it matches. An alias only counts when the finding's text
names it. A match is a lead: read the entry before acting on it.

## A review suggests decisions, it never writes them

Only revise-from-notes writes `decisions.md`. A review writes notes. When a finding that survives
(VALID after Stage 3, and upheld or narrowed by the verification pass) looks like something the
book should settle once, the note says so in its Note text: "Suggested decision: ...", with the
run's finding id. When the author answers the note, revise-from-notes records the decision, and
the note id becomes an alias of the entry so the next run can join it.

What belongs in `decisions.md` is only what was discussed or reasoned about. A mechanical fix (a
typo, a wrong page number) never becomes an entry. The date on an entry is when the decision was
made; it is provenance, not audit state.

## Run output stays in the run folder

Findings, verdicts and counts are true only of the text they were made against, and the book
changes every session. They live in the run folder (`<work.runs>/<YYYY-MM-DD-HHMM>-review-ideas-<mode>/`) and nowhere else.
Never record an audit as "done" in a bank, in `decisions.md` or in any other lasting file; treat
every chapter as changed since the last run.
