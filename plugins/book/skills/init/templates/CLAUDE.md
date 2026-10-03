# CLAUDE.md

This folder holds the book *{{title}}* by {{author}}: its text, the evidence behind it, and the
settings the book plugin's skills read. Nothing here is code to compile; the build turns the
manuscript into a print PDF, a screen PDF and an EPUB.

## What the book is

Write two or three sentences here: what the book is about, who it is for, and what the reader
can do after the last page. Every skill reads this section to learn the book's aim.

## Where things live

This table is the only description of the folders; no folder holds a README or index file.

| Path | Holds |
|---|---|
| `book.yaml` | The one config: metadata, coined terms, and any path that is not the default |
| `manuscript/` | The book, one `NNN-name.md` file per unit; the number prefix is the book order; `images/` inside |
| `thinking/author/` | `thinking/author/stance.md` and `thinking/author/stance-details.md` (the author's positions), `thinking/author/audience.md` (who the book is for and what it must show) |
| `thinking/argument/` | Why the book says what it says: the main claims and one file per topic, named by what it holds |
| `thinking/doubts/` | Counterarguments and open questions |
| `rules/decisions.md` | Settled and open decisions: a generated `## Index`, then `## Details` |
| `rules/glossary.md` | The terms the book defines, with their canonical wording |
| `rules/voice.md` | The author's voice, when wanted |
| `rules/vale/` | `vale.ini`, the book's own Vale rules, and `config/vocabularies/Book/` (accepted and rejected spellings) |
| `sources/` | `sources/list.md` (who wrote what, where to get it), `sources/quotes.md` (what each source says), `sources/library-index/` (one record per library file); `sources/library/` holds the copies and is kept out of git |
| `publishing/cover/` | `design.py` (the cover artwork), `font-widths/` and `final/` (the files that ship to the printer and the stores) |
| `publishing/sales-text/` | Back-cover text, store descriptions, keywords and categories, intended impression |
| `notes/` | Open notes only, one file per manuscript file, plus `whole-book.md` |
| `.book/` | Work state, kept out of git: `runs/` (one folder per run, newest three per skill and mode), `output/` (editions, cover renders), `caches/`, `sources-to-add/` |
| `.claude/` | `settings.json`: the tools Claude Code may use without asking |

## Which skill to use

Start a skill of the book plugin with `/book:<skill>`.

| Skill | Does |
|---|---|
| `/book:init` | Sets up a new book, or moves an older one into this layout |
| `/book:write-text` | Writes and rewrites prose in `manuscript/` and `thinking/`: plan, draft, show, apply |
| `/book:review-text` | Reviews the prose of one chapter or of the whole book; findings become notes |
| `/book:review-ideas` | Reviews the argument, structure and evidence (`editor`, or a cold `readers` review); findings become notes |
| `/book:check-facts` | Checks claims, quotes and numbers against the library copies; findings become notes |
| `/book:revise-from-notes` | Works through the open notes in `notes/`, one fix at a time, and records each decision |
| `/book:collect-sources` | Finds, downloads, backs up and restores the source library |
| `/book:build-editions` | Builds the print PDF, the digital PDF and the EPUB |
| `/book:design-cover` | Makes, compares and reviews the cover from `publishing/cover/design.py` |
| `/book:prepare-sales-text` | Writes and reviews the back cover, store texts, keywords and categories |
| `/book:run-checks` | Runs every script check of the plugin; every finding is reported until it is fixed |

## Working rules

- **Do not commit or push unless the author asks.** When a change cannot be undone, say so and
  copy the file before editing.
- **Draft, show, then apply.** Show the full proposed text first; edit files only after the
  author approves, and apply the approved words exactly.
- **A minimal change stays minimal**, and a passage patched twice is rewritten from its idea.
- **Truth over punch.** Every claim must survive a fact-check.
- **Keep copies in sync.** When the same text lives in two places, change both.
- **Read only the decisions index first** (`## Index` in `rules/decisions.md`), then open the
  one entry you need under `## Details`. Never raise or re-propose an item marked DECIDED.
  `/book:run-checks setup` says when the index is out of date, and `setup --fix` rebuilds it.
- **`book.yaml` is data.** Check it after every edit with `/book:run-checks setup`.
