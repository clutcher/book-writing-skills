# Every script, the order to run them, and the checklist after a run

The scripts live in two skills: the checks of the banks and the book in
`${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/`, the scripts of the cache in
`${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/scripts/` (the table "The cache" below), and
`sources-for-reviewer.py` in `${CLAUDE_PLUGIN_ROOT}/skills/review-ideas/scripts/`. Every one reads the book's
config (`book.yaml`, or an older book's `CLAUDE.md`), takes `--config FILE` and `--set KEY=VALUE`,
answers `--help`, and has a `--self-test` on built-in examples. Checks follow
`${CLAUDE_PLUGIN_ROOT}/lib/check_contract.md`: one `KEY<TAB>class<TAB>message` line per item, a summary with a `TOTAL`
line last, `--format text|tsv|json`, and exit 0 (no defects), 1 (defects), 2 (the tool failed). A
check that needs a missing tool prints `SKIPPED <reason>` and exits 0; say it was skipped.

**What writes without `--fix`.** Every write to a bank, to the manuscript or to the cache needs
`--fix`: `fetch.py` and `ocr.py` write into the cache (`sources.library`, kept out of git) only
with `--fix`. One script writes without it, because writing is its job:
`sources-for-reviewer.py draft --out` writes the file named by `--out`. `manual-downloads.py`
only prints the download list; with `--fix` it also writes it to `<sources.to_add>/needed.txt`.

**Which files a check reads.** A check reads the manuscript files the config lists: with
`manuscript.order: list`, only `manuscript.files`; otherwise every `*.md` file directly inside
`manuscript.dir`, in natural order. A file or folder given on the command line replaces that set
(a folder is read with its subfolders); it is the only way to widen it.

## What the source scripts read from book.yaml

Beyond the paths (`manuscript.*`, `sources.*`, `thinking.*`, `work.*`), a few keys change what a
check reports. When one is missing, the check runs without it; it never fails for that.

| Key | Used by | What it does | When it is missing |
|---|---|---|---|
| `terms.watch_words.titles_used_as_names` | `reference-format-check.py` | short titles that are also ordinary names in the prose (a language, a tool); matched only in full | every title is matched |
| `terms.watch_words.internal_first_nouns` | `uncited-claim-check.py` | the book's own nouns, so "the first principle" of the book is not a priority claim | only the built-in nouns |
| `terms.watch_words.notes_about_the_book` | `stale-argument-pointer-check.py` | argument files whose subject is the book's own structure (paths from the book root); their pointers are `exempt` | no file is exempt |
| `terms.watch_words.reading_topics` | `unread-sources.py` | words or regular expressions; only matching unread sources are queued | every unread source is queued |
| `terms.watch_words.reading_groups` | `unread-sources.py` | group name -> words, to share the queue out | one group |
| `manuscript.chapter_pattern`, `part_pattern` | `stale-argument-pointer-check.py` | which file names are chapters and parts, and the chapter number | the lib defaults (`NNN-chapter-N.md`) |
| `tools.bibtex_image` | `key-bibtex-check.py` | the docker image with `bibtex` and `alpha.bst` | the lib default |
| `sources.backup` | `backup.py`, `restore.py` | the private folder for files that cannot be downloaded again | `backup.py` stops and says so; `restore.py` uses the network only |

## The banks against their own format

| Script | What it checks |
|---|---|
| `entry-format-check.py` | both banks against the format each declares: required fields, closed vocabularies, label colons, DOI placement, dated or verdict field names, premature hashes, missing cache files, the other layout's cache folder, a pointer at an old bank path, truncated or two-key headings, key order, separators, fields after an entry's `---`, cached text with no entry, stale "not read" notes, a book entry that links an unofficial copy (a file in a person's GitHub repository or on a shadow-library site; advisory) |
| `entry-format-fix.py` | the mechanical subset of the same rules. **Must report 0 changed** on a clean bank: the gate and the fixer are one rule |
| `list-quotes-join-check.py` | the two banks against each other by key: quotes with no list entry, dangling or missing pointers, duplicate keys; `--stale DAYS` for old readings |
| `key-authors-check.py` | every key against its own Authors field |
| `key-bibtex-check.py` | every bibliography key against the label the real bibtex with alpha.bst prints (docker fallback, SKIPPED without either) |
| `duplicate-source-check.py` (collect-sources) | one source under two keys: same DOI, ISBN or cached text (defects); stubs, edition pairs, same headings (advisory) |

## The banks against the book

| Script | What it checks |
|---|---|
| `list-bibliography-check.py` | the list joins the bibliography by key; near-miss key pairs; `--no-verdicts` for verdicts and misplaced quotes-bank fields in either bank |
| `citation-key-check.py` | bibliography keys against the key rule; `--fix` renames across the book and proves every citation still resolves |
| `reference-format-check.py` | book titles in italics and paper titles in quotes in the prose; `--completeness` for cited-but-missing, never-cited and adjacent brackets |
| `reference-sort.py` | bibliography order; `--fix` sorts |
| `edition-duplicate-check.py` | one work under two editions, a designated edition with no `First published`, an unexplained pair, a moving-target URL |
| `guardrail-prose-check.py` | each guardrail beside the sentences citing its key. It surfaces and never enforces |
| `uncited-claim-check.py` | checkable claims with no citation nearby, eight classes; recall first |
| `stale-argument-pointer-check.py` | thinking files (all of `thinking.dir`; `--argument <folder>` for one folder) pointing into the book, and quotations of the book that went stale |
| `argument-key-check.py` | keys in thinking files (all of `thinking.dir`; a path for one file or folder) against the bibliography and the list; `--fix` for declared aliases, `--fix-derived` for derived renames |
| `cited-source-check.py` | every `[Key]` in the manuscript and the thinking files has a sources list entry, and a library copy or a line in `needed.txt` |

## The cache

In `${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/scripts/`, except the rows marked check-facts.

| Script | What it does |
|---|---|
| `fetch.py` | the only way a source enters the cache; `--fix` fetches, caches and files the cache lines |
| `ocr.py` | makes a scan searchable and marks it as OCR in all three places (with `--fix`) |
| `restore.py` | rebuilds missing cached files from the backup and the network, verifying hashes |
| `backup.py` | copies what cannot be downloaded again into `sources.backup` |
| `files-hash-check.py` | recorded sha256 and `from <URL>` against the bytes and the fetch record; `--fix` copies the on-disk truth into the list |
| `ocr-marker-check.py` | declared OCR marked in all three places; no digit quoted from OCR without a page-image check |
| `scan-origin-check.py` | finds scans whose text layer is someone else's OCR, from the PDF; `--fix` marks the confirmed ones |
| `scan-marker-sweep.py` | OCR declared only in prose; partly scanned files; pages with no text layer |
| `statistic-integrity-check.py` | corrupt statistics in extractions, and degrees of freedom that do not add up |
| `quote-in-file-check.py` (check-facts) | every verified quote against the cached file it claims to come from; wrong-document, stub and landing-page caches |
| `unread-sources.py` (check-facts) | cached sources with no quotes entry, grouped for sharing out (a worklist) |
| `manual-downloads.py` | sources a person must download by hand (a worklist) |
| `${CLAUDE_PLUGIN_ROOT}/lib/proposed_entries.py --run <run folder>` | fold the entries a run proposed into the banks, never overwriting |
| `link-check.py` | every URL against what it resolves to today (network; not in the suite) |
| `metadata-check.py` (check-facts) | bibliography metadata against two independent registries (network; not in the suite) |
| `sources-for-reviewer.py` (review-ideas) | drafts a list of neutral sources for the reviewer and checks one for bias |

## Run them all: the run-checks skill

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py facts          # the book
python3 ${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py facts --slow   # plus the four slow library checks
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/self-check.py               # the fixture books, no book needed
```

`run-checks.py facts` shows a check as a finding when it reports any DEFECT or ADVISORY item,
on every run, until the file is fixed. **There are no accepted counts.** An INFORMATIONAL item
(a source read and not cited, a reading queue) is counted and never a finding.

What the runner is built on:

- **Raw output is not a verdict.** Several checks report items on a healthy book (sources
  registered and not read, documented edition pairs), so "prints nothing" is the wrong success
  test; the category is. Such a class is INFORMATIONAL in its script, never a count the book
  accepts.
- **Empty output reads like a pass.** Nothing gets a short timeout; a killed check is a loud
  `TIMED OUT` failure.
- **Self-tests are discovered, not listed**: a script that gains one is picked up.
- **A gate that reports what its fixer cannot fix teaches the author to stop reading it.** Make
  the gate and the fixer agree instead.
- **A gate that checks only field names cannot see a field in the wrong place**, such as a pointer
  after an entry's separator; so the gate also checks where each field is.
- **A rule that says "keep the gate and the fixer in step" is not a control; a fixture is.** Each
  self-test includes the cases that must NOT be flagged.
- **Prefer a fix to a warning for anything mechanically derivable**: a warning that needs a person
  to edit dozens of entries gets postponed while the backlog grows.

## Before verifying anything: the first checks

Verification is the expensive step, so run the cheap structural checks first:

```bash
F="${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts"
C="${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/scripts"
python3 $F/citation-key-check.py
python3 $F/reference-format-check.py --completeness
python3 $F/reference-sort.py
python3 $F/list-bibliography-check.py            # before EVERY --only-changed run
python3 $F/list-quotes-join-check.py
python3 $F/entry-format-check.py && python3 $F/entry-format-fix.py      # the fixer must report 0 changed
python3 $C/files-hash-check.py                   # before a refetch: a stale hash makes every drift verdict lie
python3 $C/ocr-marker-check.py
python3 $C/scan-origin-check.py
python3 $C/scan-marker-sweep.py                  # before concluding a source does not say something
python3 $F/quote-in-file-check.py
python3 $F/guardrail-prose-check.py --flagged    # a pairing for review; never gate on it
python3 $F/stale-argument-pointer-check.py           # before trusting a thinking file during verification
python3 $F/metadata-check.py --only-disagreements
```

A citation with no entry, or an entry nothing cites, is a defect no fetching will reveal, and
fetching for a key about to be renamed wastes the run. A key spelled one character differently in
two files is silently verified from scratch on every run. **What the first checks cannot tell you:**
the structural checks check shape, not truth; a bibliography can pass them all with a wrong year, a
wrong author, or a title lifted from a file name.

## After a run: the checklist (every step ends in a number)

1. Write the chapter files and then the summary into the run folder (`verdict-format.md`).
2. Update the sources list with identity and access for **every** key checked; no verdicts, no
   quotes, no field for where the book cites it.
3. Update the quotes bank: verified quotes (anchored where the source allows), key findings,
   `Last verified` for every source read; correct wrong entries in place and fold the lesson forward
   as a guardrail.
4. **Completeness**: every cited key has a list entry. Report "List: N entries covering all N
   citations" (`list-bibliography-check.py`).
5. **No verdicts in the banks**: `list-bibliography-check.py --no-verdicts`. Report "Banks: 0
   entries carrying verdicts". A misplaced finding is MOVED to the quotes bank, never deleted.
6. **The banks join**: `list-quotes-join-check.py`. Report "N sources, M quotes, K joined";
   defects must be 0. A source with no quotes entry is not a defect.
7. **The cache matches the reading**: `fetch.py --keys <every key read> --dry-run`; every key must
   be `skipped` or `incomplete`. A `would-fetch` means a source was read and not cached: fetch it
   now. Report "Cache: N keys read, N cached".
8. **The cache lines describe the bytes**: `files-hash-check.py` (0 mismatches) and
   `ocr-marker-check.py` (0 unmarked).
9. **The gate and the fixer agree**: `entry-format-check.py` clean and `entry-format-fix.py`
   reporting `0 changed`. If they disagree, fix the disagreement, not only the entries.
10. **New files that cannot be downloaded again are backed up**: `backup.py --fix`.

`run-checks.py facts` runs steps 4, 5, 6, 8 and 9 in one command.
