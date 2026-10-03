---
name: run-checks
description: >-
  Runs every script check of the book plugin on one book (text, facts, cover, sales text,
  setup), grades each result and writes a report into a run folder. Use it when the author asks
  to run the checks, run the text checks on a chapter, run the source or citation checks, run
  the cover or sales-text checks, check the setup or "check my tools". It runs scripts only; to
  review prose, ideas or facts by reading, use review-text, review-ideas or check-facts.
argument-hint: "[all|text|facts|cover|sales-text|setup]"
---

# Run checks

Every skill of the plugin owns its check scripts: the prose checks live in write-text, the key
and bank checks in check-facts, the library checks in collect-sources, the cover checks in
design-cover, the selling-text checks in prepare-sales-text. This skill runs them all from
where they are, in one command, and grades the results the same way. It holds no copy of any
check.

## Modes

| Mode | Say | What it checks |
|---|---|---|
| `all` (default) | "run the checks", "run all the checks on the book" | every group below |
| `text` | "run the text checks", "run the checks on this chapter" | sentence and paragraph length, connectors, inversions, ASCII, unclear "this", one word for two things, word senses, person introductions, definitions, coined-term density, the glossary, the code font, the open notes, Vale |
| `facts` | "run the citation checks", "run the source checks" | citation keys, the bibliography, the sources list and the quotes bank, the library files; every `[Key]` in the manuscript and the thinking files |
| `cover` | "run the cover checks" | colors and contrast, fonts, text placement, the KDP template overlay |
| `sales-text` | "run the sales-text checks" | the surfaces agree, the store description, the keywords |
| `setup` | "check the setup", "check my tools" | book.yaml is valid, the decisions index is current, the outside tools are installed |

Options:

- `PATH...` (text): the path checks read only these files or folders.
- `--only-changed` (text): the path checks read only the files changed since the last run of
  the same mode. There is no `--resume`: a run takes seconds to minutes, so a stopped run is
  simply run again.
- `--slow` (facts): also the checks that read every library file (quote-in-file,
  statistic-integrity, scan-origin, scan-marker-sweep). Without it they say SKIPPED.
- `--fix`: rebuild what is generated (the decisions index).
- `--no-vale`, `--no-report`, `--quiet`, `--config FILE`, `--set KEY=VALUE`.

## Run

From the book folder:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py              # all
python3 ${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py text manuscript/110-chapter-1.md
python3 ${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py facts --slow
python3 ${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py setup
```

**Trust.** The cover file `design.py` and the Docker images named
under `tools:` in `book.yaml` run as code on your machine. Only run cover checks and builds on
books you trust.

The book is found through `book.yaml` (walking up from the working folder, or above the first
PATH); `--config` names it. Each check runs from the book root with the same config. The
report goes into `<work.runs>/<YYYY-MM-DD-HHMM>-run-checks-<mode>/report.md`, with every
item of every graded check in `results.json` beside it. The newest three runs per mode are
kept.

## How a result is graded

Each line of the output is one check, under its group:

| State | Meaning |
|---|---|
| `OK` | no finding; informational counts may still be shown |
| `FIND` | at least one finding: a DEFECT or ADVISORY item, or a check read by exit code that exits 1 |
| `SKIP` | the check did not run, and the line says why: a missing tool, a feature the book does not use, `--slow` not given |
| `FAIL` | the check could not run: it crashed, timed out or printed no report |

Exit 0 when nothing is `FIND` or `FAIL`, 1 for a `FIND`, 2 for a `FAIL`.

A check that prints the JSON report of `${CLAUDE_PLUGIN_ROOT}/lib/check_contract.md` is graded by the category of
its items. A check without it (most prose checks) is read by its exit code: exit 1 is a
finding, and the line shows its last line ("Total issues: 2"). Run it by hand for its full
report. The list of checks and what each needs is in `references/checks.md`.

## Every finding is reported until it is fixed

There are no accepted counts. A DEFECT or ADVISORY item makes its check `FIND` on every run,
however many runs have shown it, until the file is fixed. An INFORMATIONAL item is an expected
state or a worklist (a source read and not cited, a reading queue, a key with no person as
author): it is counted on the `OK` line and is never a finding. Which classes are which is
declared in each check script, not in the book.

- **Never hide a finding.** Fix it, or ask the author. A class that marks no problem is changed
  to INFORMATIONAL in its script, for every book; nothing in a book turns a finding off.

## Reporting a run

1. Say which mode ran and give the counts per state.
2. Name every `FIND` and `FAIL` with its line.
3. Name every `SKIP` and its reason. **A skipped check is not a passed check.**
4. Give the report path.

Do not fix the findings in this skill. Prose findings go to write-text or review-text, source
findings to check-facts or collect-sources, cover findings to design-cover, selling-text
findings to prepare-sales-text, a stale decisions index to `setup --fix`.

## Scripts

| Script | Does |
|---|---|
| `run-checks.py` | runs the checks of a mode, grades them, writes the report |
| `check_list.py` | the list of checks: group, owning skill, options, what each needs |
| `grading.py` | grades one check's JSON report: a DEFECT or ADVISORY item is a finding |
| `self-check.py` | maintainer check: the listed scripts exist, and the tests pass on test books |
