# The editor mode

A critical review of the whole manuscript in three stages and a verification pass, about content
only: ideas, arguments, facts, consistency and what a reader experiences. Prose style is out of
scope (review-text).

| Stage | Name | Reads | Writes |
|---|---|---|---|
| 1 | **Map** | the manuscript | `stage-1-map.md` + five artifacts |
| 2 | **Attack** | the manuscript + Stage 1 + two script reports | `stage-2-attack.md`, updates `mainstream-map.md` |
| 3 | **Judge** | the manuscript + Stages 1-2 + the decision matches | `stage-3-judge.md`, final artifacts |
| 4 | **Verify** | the accusation, the chapter, the cached sources | `verification/*.md` |

A run starts with Stage 1 and ends with the notes. `--resume` continues the newest editor run
that stopped: it finds the first stage whose file is missing or incomplete and starts there.

## Paths come from the book's config

Every path below comes from the book's `book.yaml` (an older book's `CLAUDE.md` also works),
read through the plugin's lib. Never hardcode a book path.

```bash
LIB="${CLAUDE_PLUGIN_ROOT}/lib"
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/review-ideas/scripts"
TEXT="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"
FACTS="${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts"
eval "$(python3 "$LIB/book_config.py" paths --shell)"      # BOOK_ROOT, BOOK_WORK_RUNS, BOOK_RULES_GLOSSARY, ...
python3 "$LIB/book_config.py" files                         # manuscript files in reading order, with their kind
```

Keys this skill uses: `manuscript.dir`, `manuscript.references` (the bibliography),
`manuscript.summary_heading`, `rules.glossary`, `glossary_format.location_pattern`,
`glossary_format.heading_separator`, `rules.decisions`, `work.runs`, and for Verify `sources.library`,
`sources.list`, `sources.quotes`.

## The run folder

Each run gets its own folder, made with
`python3 "$LIB/run_folders.py" start review-ideas editor --fix`, which prints
`$BOOK_WORK_RUNS/<YYYY-MM-DD-HHMM>-review-ideas-editor/` and keeps only the newest three editor
runs:

```
<run>/
  stage-1-map.md
  stage-2-attack.md
  stage-3-judge.md
  artifacts/
    stances.md  definitions-index.md  citations-index.md  claims-evidence.md  mainstream-map.md
    citation-report.md  glossary-report.md  decision-matches.md
  verification/
    <group>.md  summary.md
```

A run started with `--resume` continues the newest editor run that stopped, in its own folder
(`python3 "$LIB/run_folders.py" latest review-ideas editor`): a stage whose file is complete is
never made again, and the next stage starts from the files already there.

A run started with `--only-changed` gets its file list from
`python3 "$LIB/run_folders.py" changed review-ideas editor`. Every stage still reads the whole
manuscript, but Stage 3 keeps only the findings located in those files, and only they become
notes. At the end of every run, write the checksums of the files it read:
`python3 "$LIB/run_folders.py" record <run folder> --fix`.

**The run folder holds the stages; the notes folder holds the findings.** Stage files are true
of the text they were made against, and the book changes every session. Never record a review,
or any part of it, as "done" anywhere else. Findings that survive reach the author as notes
("After the run" below).

## What the stage agents read

**The manuscript and the bibliography, and nothing else about the book**: no notes, plans,
style guides, author position files, source banks or `decisions.md`. The review judges the book
as a reader meets it. List the files with `book_config.py files` and give them in that order;
never assume a chapter count or a file-name shape.

Every agent is cold: a fresh subagent per stage with no edit history and no summary of earlier
conversations. It gets its reference file, the run folder, the file list, and the earlier stage
files it needs. Start each prompt with: "Write all output files to `<run>/`. Read every file
listed below before beginning analysis."

Subagents never write the glossary, `decisions.md`, the manuscript or any bank. Only the main
agent touches a lasting file, and only as described below.

## Before Stage 1: read the decisions index

The main agent (not a stage agent) reads the index of the book's `decisions.md` first, if there
is one (`python3 "$LIB/decisions.py" index`), and opens the entries it needs
(`python3 "$LIB/decisions.py" show ID`), so it knows what the book has already settled. It does not
pass the file to the stages; decided items reach Stage 3 only through `decision-matches.md`.
See [references/using-decisions.md](using-decisions.md).

## Stage 1: Map

1. Spawn the agent with [references/stage-1-map.md](stage-1-map.md). It writes
   `stage-1-map.md` and the five artifacts. Tell it the location notation of the glossary: copy
   one example heading from the glossary, or give the default `Ch3 S3.1` when there is none.
   The agent may not read the glossary itself, and the seed script copies its locations as
   written.
2. **Seed the glossary** (main agent). Dry run first:

   ```bash
   python3 "$SCRIPTS/glossary-seed.py" "<run>/artifacts/definitions-index.md"
   ```

   `new-term` lines are terms Stage 1 found that the glossary lacks; a `location-not-found`
   line means a new term's location is not in the book's notation (correct it in the index
   first). `unregistered-definition` lines are definition-shaped sentences in the manuscript for
   terms the glossary lacks (report them as gaps for the next run; they are never added
   automatically). Show the new terms to the author. Add them only after the author agrees:

   ```bash
   python3 "$SCRIPTS/glossary-seed.py" "<run>/artifacts/definitions-index.md" --fix
   ```

   `--section "<a ## heading of the glossary>"` puts the new entries at the end of that section
   instead of the end of the file (a section that does not exist stops the script). The script
   adds `### term -- location` entries with `**Canonical definition:** [TO CURATE]`, and starts
   the file with a short header when there is no glossary yet. It never changes an existing
   entry and never writes a date. Format and rules:
   `${CLAUDE_PLUGIN_ROOT}/lib/glossary-format.md`.

## Stage 2: Attack

1. Run the two mechanical checks so the agent can skip hand matching:

   ```bash
   python3 "$FACTS/citation-check.py" --report "<run>/artifacts/citation-report.md"
   python3 "$TEXT/glossary-check.py" --report "<run>/artifacts/glossary-report.md"
   ```

   If the book has no glossary yet, `glossary-check.py` prints `SKIPPED` and exits 0; Stage 2
   then extracts definitions from the manuscript itself.
2. Spawn the agent with [references/stage-2-attack.md](stage-2-attack.md). It runs
   six passes (2A argument critique, 2B internal consistency, 2C facts and citations,
   2D technical accuracy, 2E mainstream mapping and fair representation, 2F rules the book
   demonstrates but never states), screens every finding with
   [references/false-positives.md](false-positives.md), and grades evidence with
   [references/evidence-grades.md](evidence-grades.md). Tell it the book's summary
   heading (`manuscript.summary_heading`) for the three-location check.

## Stage 3: Judge

1. Match the Stage 2 findings against the book's decisions:

   ```bash
   python3 "$SCRIPTS/match-decisions.py" "<run>/stage-2-attack.md" --report "<run>/artifacts/decision-matches.md"
   ```

   With no `decisions.md` the script says so and writes nothing; tell Stage 3 there are no
   earlier decisions.
2. Spawn the agent with [references/stage-3-judge.md](stage-3-judge.md). It sorts
   every Stage 2 finding (VALID-Critical / Significant / Minor, NOISE, or DECIDED), adds what
   Stage 2 missed (`M-` ids), reads as the target reader, and writes the chapter health table and
   the strengths.
3. Match the findings Stage 3 added (`#### M-<n>:` headings) against the decisions too, and drop
   any M- finding that repeats a DECIDED entry:

   ```bash
   python3 "$SCRIPTS/match-decisions.py" "<run>/stage-3-judge.md" --id-prefix M
   ```

## Verify

Every VALID-Critical and VALID-Significant finding goes to a blind verification pass, one
subagent per chapter group, each given only the accusation, the chapter, the bibliography and
the cached sources (read-only). Four verdicts: UPHELD, UPHELD-BUT-NARROWER, OVERTURNED,
UNRESOLVED. The main agent writes `verification/summary.md`. Full procedure:
[references/verification-pass.md](verification-pass.md).

## After the run

1. **Write the findings as notes.** Every VALID-Critical, VALID-Significant and VALID-Minor
   finding of Stage 3 that Verify did not overturn becomes one note in the notes file of the
   manuscript file it is about (`whole-book.md` for the whole book), in the format of
   `${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/note-format.md`, with
   `**From:** review-ideas editor, <run time>` and the finding id (`F-12`, `M-3`) in the Note. An
   UPHELD-BUT-NARROWER verdict writes the narrower finding. NOISE, DECIDED and OVERTURNED
   findings stay in the run folder. Get each id with `open-notes.py next-id <file>`, then run
   `open-notes.py check`.
2. **Report** to the author, without summarising the findings (they read the notes):
   - which stages ran, and any check that was skipped and why
   - the run folder, and the number of notes written per file
   - counts by severity from Stage 3, and by verdict from Verify, if they ran
   - the glossary terms waiting for the author's yes (Stage 1), and the unregistered definitions
   - that `artifacts/stances.md` can be compared with the author's own positions
     (`thinking.stance`), and `artifacts/claims-evidence.md` fed to the check-facts skill

The decisions behind each note are recorded when revise-from-notes answers it, never by this
review. A note may suggest a decision in its Note text ("Suggested decision: ...").

## Scripts

All follow the plugin's check contract (`${CLAUDE_PLUGIN_ROOT}/lib/check_contract.md`): one `KEY<TAB>class<TAB>message`
line per finding, a summary, exit 0 clean / 1 defects / 2 the tool failed. All take `--config`,
`--set KEY=VALUE`, `--format text|tsv|json` and `--self-test`, and work on all three book layouts.

| Script | What it does | Classes |
|---|---|---|
| `citation-check.py` (check-facts) | citations in every manuscript file vs the bibliography; `--report` writes the Stage 2 report (counts and density per file, single-use keys, most cited, shared keys, `[K1][K2]` misuse) | `cited-not-listed`, `listed-not-cited`, `adjacent-brackets` (defects); `density-outlier` |
| `glossary-check.py` (write-text) | every glossary term in the manuscript: first use vs the definition's file, uses per file; `--verbose` adds context windows | `used-before-defined`, `never-found` (advisory); `location-not-found` |
| `glossary-seed.py` | terms the glossary lacks, from the definitions index and from definition-shaped sentences; `--fix` adds the index terms | `new-term`, `location-not-found`; `unregistered-definition` (advisory) |
| `match-decisions.py` | each finding of a stage file vs `decisions.md`; `--id-prefix M` keeps only Stage 3's own findings; `--report` writes `decision-matches.md` | `matches-decided`, `matches-fix-owed`, `matches-decision-owed`, `matches-undiscussed` (advisory); `new-finding`, `no-decisions-file` |
| `self-check.py` | `--help` and `--self-test` of every script of this skill, on the fixture books only, then `readers-self-check.py` | |

How to read two of them:

- **`used-before-defined`** is usually a deliberate forward reference, and front matter never
  counts (it previews the book's words). A person decides.
- **`never-found`** is usually a glossary heading that does not match the form the book uses,
  not a term the book dropped. Search for the concept before calling it missing.

Scripts never change the book. `--report` writes one file into the run folder; only
`glossary-seed.py --fix` changes a lasting file. Never run it without the author's agreement.

