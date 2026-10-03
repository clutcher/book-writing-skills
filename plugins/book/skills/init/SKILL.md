---
name: init
description: >-
  Sets up a book for the book plugin: in a new folder it writes book.yaml, CLAUDE.md, the
  folders and the starter files, then checks which outside tools are missing (Docker, tesseract,
  poppler, Java and others) and what each one turns off. It also moves a book made with an
  earlier version of these skills into the layout, after the author agrees to a plan. Use it to
  start a new book or set up a book folder. To check the tools later, use run-checks; for text,
  sources, editions or cover, use the skill for that job.
argument-hint: "[new|existing] [folder]"
---

# Init

Every skill of the book plugin finds a book's files through one config, `book.yaml`, and one
layout. This skill makes both: for a new book from nothing, and for an existing book from what
it has.

Scripts live in `${CLAUDE_PLUGIN_ROOT}/skills/init/scripts/`. Each is a dry run by default and
writes only with `--fix`; each answers `--help`.

## Working rules

- **This skill never runs git and never commits.** The author decides what to commit.
- **Draft, show, then apply.** Show the dry run (and for `existing`, the move plan) to the author
  before any `--fix`, and wait for the answer.
- **Never overwrite.** `new.py` writes only files that do not exist; `existing.py` refuses a plan
  whose target exists. Neither edits the manuscript.
- **Move, then change, never both at once.** A moved file keeps every byte; every later change
  (book.yaml, a path line) is its own step, named in the report.
- **Say what was skipped.** A tool check that finds a tool missing is not a failure, but the
  author must hear which features it turns off.

## Modes

| Mode | Say | What happens |
|---|---|---|
| `new` (default) | "start a new book", "set up a book in this folder", `/book:init new [folder]` | `new.py`: the starter book, the Vale style, then the tool check |
| `existing` | "move my book into the layout", "set up this existing repo", `/book:init existing [folder]` | `existing.py draft`, the author edits the plan, then `existing.py move` |

With no mode, look at the folder. A folder with a `CLAUDE.md` holding `## Book Metadata` or
with `review/*-registry.md` is in the old layout. A folder with a `book.yaml` beside `author/`,
`reasons/`, `vocabulary/`, `style/`, `marketing/`, `reading-notes/` or `sources/files/` and no
`thinking/`, `rules/`, `notes/` or `publishing/` is in the previous layout. Both are older
books, so use `existing`; `new.py` refuses both. An empty or new folder uses `new`. Ask when unsure.

`new` runs the tool check as its last step. For "check my tools" on a book already set up, use
the run-checks skill (`run-checks.py setup`), which runs `toolchain-check.py` with the other setup
checks.

## new: a new book

1. **Ask** for the folder, the title and the author's name (and a subtitle, if there is one).
   Missing values are written as `TO BE ASSIGNED`, which the build reports on every run.
2. **Dry run and show it:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/init/scripts/new.py FOLDER --title "..." --author "..."
   ```
3. **On approval, write:** the same command with `--fix`. Add `--pull-images` to pull the pinned
   Docker images now instead of on first use. After the files, `--fix` runs the write-text
   skill's `vale-sync.py --fix`: it copies the Vale style into the book and runs `vale sync` in
   Docker. Without Docker it says SKIPPED and the book is still made.
4. **Report** what was written, the Vale sync result, and the tool check's `missing` lines with
   what each turns off.
5. **Point to the next steps:** fill in "What the book is" in `CLAUDE.md`, the author files in
   `thinking/author/`, `book.description`; then the write-text skill for the first chapter. `rules/voice.md` starts as a copy of the write-text skill's
   default voice profile; the author edits it into their own voice. The starter cover
   (`publishing/cover/design.py`) and the sales-text files hold placeholders for the
   design-cover and prepare-sales-text skills to replace.

What it writes, and what each file is for: [references/book-layout.md](references/book-layout.md).
Every book.yaml key: [references/book-yaml.md](references/book-yaml.md). Only the keys a new
author sets are in the new file; every path keeps its default.

The new book passes `book_config.py check` with no unknown key and `build-book.sh
--show-settings`. `run-checks.py all` on a new book shows one expected `FIND`: the sync check
of the selling texts reports `surface-missing` until the author writes `book.description`.
A check with nothing to read yet says `SKIPPED` with the reason and exits 0: every facts check that needs sources while the source banks hold
only their `## Entry format` headers and no file cites a `[Key]` (`uncited-claim-check.py` and
`stale-argument-pointer-check.py` read only the book's own text, so they run); `definition-check.py` until the glossary
has an entry; `term-density-check.py` until `terms.families` is set; Vale when Docker is missing; the cover checks that need a page count until the first build.

Run in a folder that already has some of these files, `new.py` adds only what is missing (and
the missing `.gitignore` lines, written for the paths this book's `book.yaml` sets). The
starter manuscript, cover design and sales-text files are written only while the manuscript
folder has no `.md` file, so a book that already has text never gets placeholders. It
refuses a book in an older layout: that book needs `existing` first.

## existing: an existing book

Full procedure, the plan format and the rules for moving text: [references/existing.md](references/existing.md).

1. **Backup first.** Ask the author to zip the book folder, or confirm where a backup is.
   `existing.py move` deletes what the plan marks DROP (`--keep-dropped DIR` keeps it
   instead). Save the output of the run-checks skill (`run-checks.py facts` and
   `run-checks.py text`) now, for step 6.
2. **Draft the plan and show it:**
   ```bash
   S=${CLAUDE_PLUGIN_ROOT}/skills/init/scripts
   python3 $S/existing.py draft BOOK           # show
   python3 $S/existing.py draft BOOK --fix     # write BOOK/move-plan.tsv
   ```
   The draft finds the older layout: old (settings in `CLAUDE.md`, `review/*-registry.md`,
   `review/sources/`, `research/`, `personal-review/`) or previous (`book.yaml` with `author/`,
   `reasons/`, `vocabulary/`, `style/`, `sources/files/`, `sources/origin/`, `cover/`,
   `marketing/`, `reading-notes/`, `.book/inbox/`). It proposes a row for every path, with
   rules taken from the shared config reader. Walk the author through the rows that move or
   drop; the author edits the file.
3. **Dry run the move and show it:** `python3 $S/existing.py move BOOK`. It prints the moves, the
   merged origin files, the drops, the book.yaml it would write, and every problem. A plan with
   a problem moves nothing. A move that still fails stops the move at that file; the report and
   `moves.tsv` say what moved, and the same plan run again moves the rest.
4. **On approval:** `python3 $S/existing.py move BOOK --fix`. It moves every file byte for byte
   (sha256 checked) and never over a file, merges each old-layout source's fetch and OCR records
   into `sources/library-index/<Key>.json`, and drops what the plan says. An old-layout book
   gets a new book.yaml from its `CLAUDE.md` sections; a previous-layout book.yaml has its keys
   renamed in place, comments kept (the old file stays in the run folder). Either way the file
   must read back to the intended values. Then it points the Vale config and the source banks at
   the new paths, adds `.gitignore` lines, and writes the report to
   `.book/runs/<YYYY-MM-DD-HHMM>-init-existing/move-report.md` with `moves.tsv` and the plan.
5. **Fill the gaps:** `python3 $S/new.py BOOK --fix` adds what the layout still lacks
   (`rules/decisions.md`, `rules/voice.md`, the glossary header,
   empty folders) and changes nothing that exists. A moved `decisions.md` without a current
   `## Index` fails `run-checks.py setup` until `decisions.py check --fix` rebuilds it; show
   that change to the author as its own step.
6. **Check:** the run-checks skill: `run-checks.py setup`, then `run-checks.py facts` and
   `run-checks.py text`. Compare their findings with the output saved in step 1: a move must not
   add a finding.
7. **Report** the numbers: files moved and checked, origin files, drops, problems, and the list
   of files that still name an old path (the author updates those, often `CLAUDE.md`).

## The tools on this machine

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/init/scripts/toolchain-check.py [--book DIR] [--pull]
```

It lists docker and the pinned images from `book.yaml`, bash, tesseract, poppler, java, curl, the
cover renderers, fc-match, qpdf and the word list, and says for each missing one which feature it
turns off. Missing tools are advisory: the check exits 0. Details and the reasons for pinned
images: [references/toolchain.md](references/toolchain.md).

## Scripts

| Script | Does |
|---|---|
| `new.py` | Writes a new book's starter files, or adds what an existing layout lacks |
| `existing.py` | `draft` a move plan from an older layout; `move` carries it out and writes the report |
| `toolchain-check.py` | Lists the outside tools and what each missing one turns off; `--pull` pulls images |
| `book_yaml.py` | Shared by the two: writes book.yaml and proves it reads back to the intended values |
| `self-check.py` | Maintainer check on fixtures only: new (with `run-checks.py all`), existing on `scripts/fixtures/old-book` and `scripts/fixtures/previous-book`, the tool check |

## Templates

The files `new.py` copies live in `${CLAUDE_PLUGIN_ROOT}/skills/init/templates/`: `book.yaml`,
`CLAUDE.md`, `gitignore`, `claude-settings.json`, `vale.ini`, the starter `manuscript/`,
`sources-list.md`, `sources-quotes.md`, `glossary.md` and `cover/design.py`. No folder gets a
README or index file: the book's `CLAUDE.md` describes every folder and lists the eleven skills.
The sales-text files come straight from the prepare-sales-text skill's `templates/`, and
`rules/voice.md` from `${CLAUDE_PLUGIN_ROOT}/skills/write-text/profiles/default.md`. Three templates copy text
owned by another skill: the two bank
headers copy the entry formats in the check-facts skill's references, and `templates/cover/design.py`
follows "The smallest design" in `${CLAUDE_PLUGIN_ROOT}/skills/design-cover/references/design-file.md`. When one changes,
change the other with it.
