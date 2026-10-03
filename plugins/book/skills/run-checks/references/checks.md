# The checks run-checks runs

`scripts/check_list.py` is the one place this list is kept; this page explains it. Each check
stays in the skill that owns its domain. "Needs" is what the book must have for the check to
run; without it the check says SKIPPED with the reason.

Reach: **paths** checks read the PATH arguments (else the whole manuscript); **book** checks
always read the whole book. Grading: **classes** checks print the JSON report and are a
finding when any item is DEFECT or ADVISORY (INFORMATIONAL items are counted, never a
finding); **exit** checks are read by exit code, and exit 1 is a finding. There are no accepted
counts.

A paper (`kind: paper` in `book.yaml`) has no cover and no sales text: every check of those two
groups says SKIPPED ("a paper has no cover", "a paper has no sales text"). The checks of the
other groups read the paper's sections as they read chapters.

## text

| Check | Skill | Reach | Grading | Needs |
|---|---|---|---|---|
| `sentence-and-paragraph-check.py` | write-text | paths | exit | |
| `sentence-and-paragraph-check.py --connectors` | write-text | paths | exit | |
| `sentence-and-paragraph-check.py --meta` | write-text | paths | exit | |
| `sentence-and-paragraph-check.py --inversions` | write-text | book | exit | |
| `ascii-normalize.py` | write-text | paths | exit | |
| `unclear-this-check.py` | write-text | paths | exit | |
| `word-for-two-things-check.py` | write-text | paths | exit | |
| `word-sense-check.py` | write-text | paths | exit | |
| `person-introduction-check.py` | write-text | book | exit | |
| `definition-check.py` | write-text | paths | exit | glossary |
| `term-density-check.py` | write-text | book | exit | coined terms; a book (it says SKIPPED itself on a paper) |
| `glossary-check.py` | write-text | book | classes | |
| `paper-check.py` | write-text | book | classes | a paper (it says SKIPPED itself on a book) |
| `code-font-check.py` | build-editions | book | classes | |
| `arxiv-bundle-check.py` | build-editions | book | classes | a paper; Docker (it says SKIPPED itself) |
| `open-notes.py check` | revise-from-notes | book | classes | |
| `vale-run.py` | write-text | paths | exit | Docker; off with `--no-vale` |

## facts

Every facts check needs the sources list, and sources in use: an entry in the sources list or
the bibliography, or a `[Key]` cited in a manuscript or thinking file. A book with none (a new
book, or one that cites nothing) gets SKIPPED for every facts check. The slow ones run only
with `--slow`.

| Check | Skill | Grading | Needs |
|---|---|---|---|
| `cited-source-check.py` | check-facts | classes | |
| `citation-check.py` | check-facts | classes | bibliography |
| `entry-format-check.py` | check-facts | classes | quotes bank |
| `entry-format-fix.py` (dry run) | check-facts | exit | quotes bank |
| `list-quotes-join-check.py` | check-facts | classes | quotes bank |
| `key-authors-check.py` | check-facts | classes | |
| `list-bibliography-check.py --no-verdicts` | check-facts | classes | bibliography, quotes bank |
| `citation-key-check.py` | check-facts | classes | bibliography |
| `key-bibtex-check.py` | check-facts | classes | bibliography |
| `reference-format-check.py` | check-facts | classes | bibliography |
| `reference-format-check.py --completeness` | check-facts | classes | bibliography |
| `reference-sort.py` | check-facts | classes | bibliography |
| `edition-duplicate-check.py` | check-facts | classes | bibliography |
| `guardrail-prose-check.py` | check-facts | classes | quotes bank |
| `uncited-claim-check.py` | check-facts | classes | |
| `stale-argument-pointer-check.py` | check-facts | classes | thinking files |
| `argument-key-check.py` | check-facts | classes | bibliography, thinking files |
| `files-hash-check.py` | collect-sources | classes | |
| `ocr-marker-check.py` | collect-sources | classes | quotes bank |
| `duplicate-source-check.py` | collect-sources | classes | |
| `quote-in-file-check.py` | check-facts | classes | quotes bank; slow |
| `statistic-integrity-check.py` | collect-sources | classes | quotes bank; slow |
| `scan-origin-check.py` | collect-sources | classes | slow |
| `scan-marker-sweep.py` | collect-sources | classes | slow |

`cited-source-check.py` reads the manuscript and the thinking files (the `thinking` folder).
Every `[Key]` must have an entry in the sources list, and a library copy (`<Key>.<ext>` in
`sources.library`) or a line in `needed.txt` in the sources-to-add folder. A key that waits in `needed.txt` is
informational. There are no per-file reference sections: the sources list is the one place a
key resolves.

Never run here: `link-check.py`, `metadata-check.py` (they use the network), `restore.py`,
`fetch.py` (they write the library). Run them through collect-sources.

## cover

| Check | Skill | Needs |
|---|---|---|
| `color-check.py` | design-cover | cover design |
| `font-check.py` | design-cover | cover design |
| `layout-check.py` | design-cover | cover design; a page count (`book.pages`, `cover.book_pdf` or a built print PDF) |
| `overlay.py` | design-cover | the above, and the rendered wrap (`design-cover make`) |

`overlay.py` is the one check that writes a file: the overlay image `png/wrap-overlay.png` next
to the rendered wrap in `cover.output` (under `.book/output/`, work state that is not in git).
It is only for looking; nothing in the book changes.

## sales-text

| Check | Skill | Needs |
|---|---|---|
| `sync-check.py` | prepare-sales-text | two selling surfaces (it says SKIPPED itself) |
| `store-description-check.py` | prepare-sales-text | the store description |
| `keyword-check.py` | prepare-sales-text | the keywords file |

## setup

| Check | Where | With `--fix` |
|---|---|---|
| `book_config.py check` | lib | |
| `decisions.py check` | lib | `check --fix`: writes missing Status lines and rebuilds the index |
| `toolchain-check.py` | init | |

`book_config.py check` names every key in `book.yaml` that no script reads, and every path
key whose file or folder is missing.

## Adding a check

1. Write the check in the skill that owns its domain, to `${CLAUDE_PLUGIN_ROOT}/lib/check_contract.md` (JSON report,
   exit codes, SKIPPED when a tool or feature is missing).
2. Add one line to `CHECKS` in `scripts/check_list.py`, with its group, skill and needs.
3. Add it to the tables above. `self-check.py` fails when a listed script does not exist.
