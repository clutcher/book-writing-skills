---
name: init
description: >-
  Sets up a book for the book plugin: in a new folder it writes book.yaml, CLAUDE.md, the
  folders and the starter files, then checks which outside tools are missing and what each one
  turns off. It also sets up a book from any folder that already holds one: it drafts a move
  plan and moves the files only after the author agrees. Use it to start a new book or set up a
  book folder. To check the tools later, use run-checks; for text, sources, editions or cover,
  use the skill for that job.
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
  before any `--fix` or move, and wait for the answer.
- **Never overwrite, never delete.** `new.py` writes only files that do not exist and never
  edits the manuscript. A move never goes over a file and never deletes one.
- **Move, then change, never both at once.** A moved file keeps every byte; every later change
  to its text is its own step, with the author.
- **Say what was skipped.** A tool check that finds a tool missing is not a failure, but the
  author must hear which features it turns off.

## Modes

| Mode | Say | What happens |
|---|---|---|
| `new` (default) | "start a new book", "set up a book in this folder", `/book:init new [folder]` | `new.py`: the starter book, the Vale style, then the tool check |
| `existing` | "set up my book from this folder", "I have a manuscript already", `/book:init existing [folder]` | Claude drafts a move plan, the author agrees, the files move, then `new.py` adds what is missing |

With no mode, look at the folder. An empty or new folder, or one that already has `book.yaml`,
uses `new`. A folder with chapters, notes or sources in its own shape uses `existing`. Ask when
unsure.

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
refuses a folder inside another book (a `book.yaml` above it).

## existing: a book from any folder

No script decides where a file goes: Claude reads the folder, the author decides. Full
procedure and the plan rules: [references/existing.md](references/existing.md).

1. **Backup first.** Zip the whole folder into a file next to it and tell the author where it
   is.
2. **Draft the move plan and show it.** Read every file name (open the unclear ones) and write
   a table: file, where it goes, why. Chapters in book order go to `manuscript/NNN-name.md`,
   numbered like the starter book (`110`, `120`, ...). Notes go to `notes/`, copies of sources to
   `sources/library/`, one list of sources to `sources/list.md`, images to
   `manuscript/images/`. Anything unclear stays where it is.
3. **The author edits the table and agrees.** Move nothing before that.
4. **Move** with plain moves, one row at a time: never change a byte, never delete, never write
   over a file. On a name clash, stop and ask.
5. **Add what is missing:** `new.py FOLDER` (dry run, show it), then the same with `--fix`. It
   writes only files that do not exist; moved chapters get no starter files beside them.
6. **Check:** the run-checks skill, `run-checks.py setup`, then `run-checks.py facts` and
   `run-checks.py text`. Each finding is its own step with the author.
7. **Report** where the backup is, what moved, what stayed, what `new.py` added and what the
   checks found. The author commits.

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
| `new.py` | Writes a new book's starter files, or adds what a book folder lacks |
| `toolchain-check.py` | Lists the outside tools and what each missing one turns off; `--pull` pulls images |
| `book_yaml.py` | Used by `new.py`: writes book.yaml values and proves they read back as intended |
| `self-check.py` | Maintainer check in a temporary folder: new (with `run-checks.py all`), `new.py` on a folder that already holds a book, the tool check |

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
