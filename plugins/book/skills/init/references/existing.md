# existing: set up a book from any folder

`existing` turns a folder that already holds a book (chapters, notes, sources, images, in any
shape) into the layout every skill expects ([book-layout.md](book-layout.md)). No script decides
where a file goes. Claude reads the folder and drafts a move plan, the author agrees to it, and
the files move with plain moves. Then `new.py` adds what is still missing.

One promise: **moving never changes a byte, never deletes, and never writes over a file.**

## Before you start

1. **Make a backup.** Zip the whole folder into a file next to it (for example
   `my-book-backup-2025-01-02.zip` beside `my-book/`) and tell the author where it is. Do not
   go on without a backup.
2. **This mode never runs git and never commits.** The author commits the result.

## 1. Read the folder and draft the move plan

List every file in the folder (skip `.git/`). Open the files you cannot place by name. Then
draft the plan as a table, one row per file or folder:

| Now | Goes to | Why |
|---|---|---|
| `drafts/intro.md` | `manuscript/010-introduction.md` | front matter |
| `drafts/ch1-the-river.md` | `manuscript/110-the-river.md` | chapter 1 |
| `drafts/ch2-the-mill.md` | `manuscript/120-the-mill.md` | chapter 2 |
| `ideas.txt` | `notes/ideas.txt` | the author's notes |
| `papers/` | `sources/library/` | copies of sources |
| `research/reading-list.md` | `sources/list.md` | the list of sources |
| `pics/map.png` | `manuscript/images/map.png` | an image in the text |
| `old-stuff/` | stays | not clear; ask the author |

Rules for the plan:

- **Chapters and their order** go to `manuscript/NNN-name.md`. Number them like the starter
  book: front matter `000`-`099`, parts at `100`, `200`, ..., chapters in steps of 10 (`110`,
  `120`, ...), back matter `900`-`999`. The number gives the book order, so ask the author when
  the order is not clear. `name` is short, lower case, words joined by `-`.
- **Notes** (ideas, to-do lists, reader comments) go to `notes/`.
- **Sources**: copies of papers, books and web pages go to `sources/library/`. One file that
  lists the sources goes to `sources/list.md`.
- **Images** go to `manuscript/images/`.
- **Anything unclear stays where it is.** Write `stays` and ask. A file that stays is never lost.
- A file that would have to be split, joined or rewritten moves whole. Changing text is a later
  step, done with the author, after the move.

## 2. The author edits and agrees

Show the table. The author knows things the folder does not show: a draft that is dead, two
files that are one chapter, a different order. Change the table until the author says yes. Do
not move anything before that.

## 3. Move the files

Use plain moves (`mv` on Linux and macOS, `Move-Item` on Windows), one row at a time:

- **Never change a byte.** A move is only a move. Do not fix text, names inside files or line
  endings in the same step.
- **Never delete** a file, even one that looks empty or old.
- **Never write over a file.** Before each move, check that the target does not exist. On a
  name clash, stop and ask the author; do not pick a new name alone.
- Make the target folder first when it does not exist.

When all rows are done, list the folder again and show what moved and what stayed.

## 4. Add what is missing

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/init/scripts/new.py FOLDER --title "..." --author "..."
python3 ${CLAUDE_PLUGIN_ROOT}/skills/init/scripts/new.py FOLDER --title "..." --author "..." --fix
```

Show the dry run first. `new.py` writes only files that do not exist: `book.yaml`, `CLAUDE.md`,
`rules/`, the source banks, the empty folders. A `.gitignore` keeps its lines and gains only the
missing ones. While `manuscript/` has a `.md` file, no starter chapter, cover design or
sales text is written, so the moved text gets no placeholders. A `CLAUDE.md` the folder already
had stays as it was; show the author the template (`templates/CLAUDE.md`) to take the parts they
want.

## 5. Check

Run the run-checks skill: `run-checks.py setup`. Then `run-checks.py facts` and
`run-checks.py text` show what the moved files still need, for example a source list whose
entries are not in the entry format yet. Each of these is its own step with the author.

## 6. Report

Tell the author: where the backup is, how many files moved, which stayed and why, what `new.py`
added, and what the checks found. The author commits.
