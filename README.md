# Book Writing Skills

A Claude Code plugin that helps you write, check, review and publish a non-fiction book.

Your book keeps one config file, `book.yaml`, next to its text. Every skill reads its paths and settings from that file, so the skills work with any folder layout and any book. The skills are not written for any one book or author.

## Install

```
/plugin marketplace add clutcher/book-writing-skills
/plugin install book@book-writing-skills
```

Then, in an empty folder, run `/book:init new`. It writes a starter book, and tells you which outside tools are missing on your machine and what each one turns off.

## The eleven skills

| Skill | Call | What it does |
|---|---|---|
| init | `/book:init` | Sets up a new book, or moves an existing book into the layout; checks the tools on this machine |
| write-text | `/book:write-text` | Writes and rewrites prose; holds the prose rules and the text checks |
| review-text | `/book:review-text` | Reviews the prose of a chapter or the whole book; findings become notes |
| review-ideas | `/book:review-ideas` | Reviews the argument and evidence: `editor` in three stages, or `readers`, a cold review in a clean room; findings become notes |
| check-facts | `/book:check-facts` | Checks claims, quotes, figures and citations against the sources; findings become notes |
| collect-sources | `/book:collect-sources` | Finds, downloads, backs up and restores the source files |
| revise-from-notes | `/book:revise-from-notes` | Works through the open notes, yours and the reviews', one decision at a time |
| build-editions | `/book:build-editions` | Builds the print PDF, the screen PDF and the EPUB |
| design-cover | `/book:design-cover` | Makes, checks, compares and reviews the KDP print cover and the ebook cover |
| prepare-sales-text | `/book:prepare-sales-text` | Writes and checks the back cover, the store description and the keywords, and exports store files |
| run-checks | `/book:run-checks` | Runs every script check of the plugin on the book (text, facts, cover, sales text, setup), every finding reported until it is fixed, with a report |

You can also just say what you want ("build the book", "check the sources of chapter 3"), and Claude picks the skill.

Every skill that reviews the book or proposes changes reads your `decisions.md` first. A point you already decided is not raised again.

Every review and check writes what it finds as notes in `notes/`, one notes file per
file it read, plus one for the whole book. `revise-from-notes` goes through them with you: it shows a few small fixes,
applies the one you pick, records the decision in `decisions.md` and deletes the note.

## Requirements

- Claude Code.
- Python 3.9 or later, standard library only (tested on 3.13 and 3.14).

Optional tools. Each one turns on some features. When a tool is missing, the check that needs it says `SKIPPED` and why, and nothing fails.

| Tool | Turns on |
|---|---|
| Docker | the build (all three editions), the Vale prose review, the BibTeX key check; the images are pinned in `book.yaml` under `tools:` |
| tesseract, poppler | reading scanned sources (OCR) and text from PDF sources |
| Java | checking the EPUB with epubcheck (downloaded once, on first use) |
| rsvg-convert or cairosvg, ImageMagick | drawing and checking the cover |
| qpdf | draft protection and page counts without Docker |
| calibre | the `--azw3` Kindle file |
| git | only the `--changes-since` copy of build-editions, which shows what changed since a commit |

To see what is on your machine, say "check my tools": the run-checks skill runs its `setup` mode.

## Your book's files

`/book:init new` writes this layout:

```
book.yaml                the one config: title, author, build settings, coined terms, paths
CLAUDE.md                what the book is, where things live, which skill to use
manuscript/              NNN-name.md files; the number sets the book order; images/ inside
thinking/author/         your stance and your audience
thinking/argument/       why the book says what it says: claims.md and one file per topic
thinking/doubts/         counterarguments.md and open-questions.md
rules/decisions.md       settled and open decisions
rules/glossary.md        the terms the book defines
rules/voice.md           your voice profile
rules/vale/              the Vale config and the book's own style rules and word lists
sources/list.md          who wrote what, and where to get it
sources/quotes.md        what each source says
sources/library-index/   how each library file was fetched and read
sources/library/         the copies of the sources, kept out of git
publishing/cover/        design.py (the artwork), font-widths/ and final/ (the files that ship)
publishing/sales-text/   back-cover.md, the store texts, keywords and categories
notes/                   open notes, from your reading and from the reviews and checks
.book/                   work state: runs, build output, caches, files to add; kept out of git
```

It also writes a `.gitignore` and a `.claude/settings.json` that lets Claude read the book without asking.

Every path is a `book.yaml` key, so you can change any of them. Every key is described in `plugins/book/skills/init/references/book-yaml.md`.

A book in an older layout of this plugin can move into the new one: `/book:init existing` drafts a move plan you can edit, and moves nothing until you agree.

## Licence

Copyright (c) 2026 Igor Zarvanskyi.

Everything here, the code and the text of the skills, is under the MIT License, in [`LICENSE`](LICENSE). A copy is also inside the plugin folder, so an installed copy carries it.

## For maintainers

```
python3 tools/check-plugin.py [--with-other-book]
```

`tools/check-plugin.sh` does the same for those used to it.

It runs the lib tests, every skill's self-check, `--help` of every script, the leak scan, the named-files check, the skill-shape check, and the bytecode check. `--with-other-book` also runs every skill against a second, unrelated book (slow).
