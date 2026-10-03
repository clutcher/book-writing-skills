# Verifying the book's claims against its sources

Read `reference-standard.md` first: it is the standard every verdict is graded against.

## Inputs and runs

| Input | What | When |
|---|---|---|
| review artifacts | the citation and claim tables of a review-ideas `editor` run | after its Stage 1; faster, the claims are already extracted |
| manuscript | the chapter files and the bibliography | no review run, or quotes must be checked in context |

| Run | What | When |
|---|---|---|
| full | every citation and claim in scope (a chapter, a thinking file, or the whole book) | first run, or a clean re-verification |
| `--only-changed` | only files changed since the last check-facts run, and in them only keys missing from the list or whose claim text changed | after new citations |
| `--resume` | continues the newest check-facts run that stopped, skipping chapters whose files are complete | after a stop |

Before a full run of the whole book, count the items and ask the author to confirm. Runs on one
chapter and `--only-changed` runs go ahead. Everything goes into one run folder, made by
`python3 ${CLAUDE_PLUGIN_ROOT}/lib/run_folders.py start check-facts all --fix`
(`<work.runs>/<YYYY-MM-DD-HHMM>-check-facts-all/`; `--resume` uses `run_folders.py latest
check-facts all`, `--only-changed` uses `run_folders.py changed check-facts all <files>`, and the
run ends with `run_folders.py record <run folder> <files read> --fix`):
`fact-check.md` (summary) and `fact-check-ch<N>.md` (per chapter). Every MINOR ISSUE,
SIGNIFICANT ISSUE, UNVERIFIABLE and uncited item also becomes a note (see `verdict-format.md`).
Read the decisions index first (`python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py index`), open
entries with `decisions.py show ID`, and never raise an item it marks DECIDED.

## Setup: review mode

1. Find the newest run folder holding the review's citation and claim tables (or the one named).
   None: ask for a review stage 1 first, or use manuscript mode.
2. Filter to the chapter asked for; read the bibliography to decode keys before searching.
3. Deduplicate: verify each source once, and point every row that uses it at that finding.
4. `--only-changed`: skip keys already in the list whose claim text did not change.
5. **Run the detector and the missed-claims pass anyway.** Review mode inherits whatever stage 1
   extracted and is blind to whatever it missed. Run `uncited-claim-check.py` over the chapters,
   then `missed-claims-pass.md` with the review rows AND the script flags as the exclusion set.

## Setup: manuscript mode

1. Run `uncited-claim-check.py <chapters> > <run>/uncited-claim-report.md` first; its flags are
   candidates for the UNCITED list.
2. Read the chapters and the bibliography.
3. Extract every `[Key]` with the claim it supports, any direct quote, and the section.
4. Extract checkable claims by walking the categories below, not by scanning for what looks
   citable (attention anchors on citations and digits and skips the rest):

| Category | Looks like | Easy to miss because |
|---|---|---|
| empirical | studies, statistics, measurements, benchmarks | (these get found) |
| numerical | any specific quantity, **spelled out as well as in digits** | "seventy percent" reads as prose |
| historical event | dates, sequences, what happened when | (these get found) |
| **common practice** | how things were done in a period: how often, by whom, with what usual means | no digit, no date, no citation; still falsifiable |
| **priority** | "first", "pioneered by", "coined by", "predates" | reads as background; earlier work usually exists |
| consensus | "widely accepted", "experts agree", "studies show" | asserts agreement, not a fact |
| attributed position | "X argues that..." | the citation proves the source exists, not that it says this |

5. Flag an uncited checkable claim as "UNCITED -- consider adding a source"; do not verify it. An
   uncited claim is not automatically a defect: common knowledge, the author's own experience and
   conclusions argued from earlier material are legitimate. The failure prevented is a checkable
   assertion nobody ever decided about.
6. Run `missed-claims-pass.md`, as its own agent per chapter.
7. Cross-check every key against the bibliography for title, author and year.

## Priority

1. empirical claims (numbers, sample sizes, conclusions must match exactly)
2. historical claims (dates, sequences, "first" attributions, causal narratives)
3. attribution (the right person and work)
4. direct quotes (word for word; record the original wording and its location in the report)
5. consensus claims (the source must substantially support the characterization)
6. reasoning claims: check only that cited authorities are accurately attributed
7. remaining authority citations

Within that: consequence if wrong first, then how checkable it is.

## The six checks for a citation

1. **Attribution**: right person, right work, right edition? Ideas drift to their popularizer;
   co-authors get dropped.
2. **Quote**: read the quotes bank first (a pointer, not proof), then the cached text. A miss in
   the extraction is not yet a finding (see `${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/references/extraction-traps.md`). Compare every word; record the
   exact original and its location in the report AND return it for the quotes bank: the report is
   dated and the quote is not. Check every place the book uses the same quote. Watch for
   paraphrases shown as quotes, quotes stitched from two passages, and quotes of a secondary source
   credited to the original.
3. **Claim-source alignment**: does the source support what the book says it supports, or a
   weaker version, with caveats dropped, or causation read into correlation?
4. **Date and edition**: the key's year against the printing; first-edition year with
   second-edition content; submission versus publication year.
5. **Context fairness**: cherry-picked lines from a nuanced argument; a tentative finding shown as
   settled; the author's own later corrections ignored.
6. **Priority**: "first" claims. Earlier work usually exists; "first to formalize" differs from
   "first to practise".

## Claim types

- **Empirical**: identify the study, read the methods and results (never only the abstract), and
  verify sample size, method, conclusion, effect size and the generality the book implies.
- **Historical**: dates, sequence, attribution, and whether the simplified narrative distorts
  what happened. Cross-check two independent sources.
- **Common practice**: identify the practice, the period and the implied scope; prefer sources
  from the period over later retrospectives (which tidy the past). Ask: typical or merely common?
  Does the scope match (small and large farms, or city and village schools, often differ)? Is
  the period right? Is the then-versus-now contrast fair? A typical-but-not-universal practice
  stated without a qualifier is a MINOR ISSUE with a one-word fix ("often", "typically").
- **Consensus**: is it a consensus, or a majority with real dissent? Has it moved since the source?
- **Numerical**: the exact number, the right year and study, the right unit, not one end of a range.
- **Multi-citation**: verify each source alone and report per source; a range must be supported by
  the data, not built from the endpoints of different studies; a cross-study range should read as
  a synthesis.

## When a finding comes from review artifacts

An artifact summarizes what the book says, and the summary can be imprecise. Before reporting a
SIGNIFICANT ISSUE from review mode, read the chapter itself.

## Working in parallel

One agent per chapter. Each agent greps both banks for its keys, fetches every uncached source
through `fetch.py` (the cache mandate binds subagents; see `${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/references/files-and-cache.md`), reads
`reference-standard.md` and this file, never resolves a paywall on its own authority, and returns
three blocks for EVERY key: list data, quotes data and the verdict. The missed-claims pass runs as its
own agent, given only the chapter, the script flags and `missed-claims-pass.md`: an agent that has just
verified a list of claims is the worst reader for what the list missed.

The main agent writes the reports, stages or merges the bank data, checks completeness, runs the
cross-citation pass and writes the summary.

**Cross-citation consistency (full runs)**: when a source is cited in several chapters, check that
what the book says it argues is consistent across them. A contradiction neither chapter check
could see is a SIGNIFICANT ISSUE in the summary.

## Common citation errors

- **Attribution drift**: an idea credited to the book the author learned it from, not its originator.
- **Amalgamation**: two studies' findings compressed into one citation.
- **Precision inflation**: "about half" becomes "47.3%"; one end of a range becomes "the" number.
- **Temporal confusion**: content from a later edition under an earlier year; an old statistic as current.
- **Survivorship framing**: one small study written as "research shows".
- **The dominant class**: a citation that proves the work exists while not supporting the claim.
  It also hides the claim from the uncited-claim detector.

## Calibration: too quick to verify, too quick to flag

- **Confirmation rush**: one secondary source matching the claim is not verification; books cite
  each other and repeat each other's errors.
- **Authority assumption**: a respected source can be wrong; verify the claim, not the reputation.
- **Premature debunking**: one wrong detail does not void the citation; verify each part apart.
- **Over-sensitivity to form**: a paraphrase that keeps the meaning is not a significant issue.
- **Scope**: verify facts, not reasoning; do not judge whether arguments convince or how the prose
  reads (the `review-text` and `review-ideas` skills own those).

## Lessons that keep producing false findings

- A **word-frequency grep** standing in for reading; a **bank guardrail** treated as authority over
  the source; an **argument file** grading superseded book text. Every retraction was a case where the
  citation was fine and the bank or the method was not.
- A quote-versus-cache miss is often the extraction: font subsetting in slide decks maps letters to
  other glyphs, OCR turns units into words ("2 set" for "2 sec"), articles render as symbols, line
  wraps and multi-column panels split sentences, captions are absent from the text layer, and a
  running head or a page number banked as a quote can never match.
- The banks can drift behind the book in the direction that brings an error back: check whether a
  known violation survives only in a bank.
- Never pin a verdict to a bare line number of the book: lines drift on every edit.
- A mislabelled section reference spreads through notes and banks: fix every copy.
- A dated catalogue record settles when an item was published: an archive or dataset portal's
  record date, a law gazette's publication date, or (for software) a package registry's timestamp.

## Output

See `verdict-format.md` for the templates, verdicts and confidence levels, and `checks.md`
for the post-run checklist. Every step of the checklist ends in a number.
