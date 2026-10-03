# Book Writing Skills

A Claude Code plugin that helps you write, check, review and publish a non-fiction book.

Your book keeps one config file, `book.yaml`, next to its text. Every skill reads its paths and settings from that file, so the skills work with any folder layout and any book. The skills are not written for any one book or author.

**Status:** early 0.x. Names, modes and config keys may still change. What changed in each version: [CHANGELOG.md](CHANGELOG.md).

## Install

```
/plugin marketplace add clutcher/book-writing-skills
/plugin install book@book-writing-skills
```

Then, in an empty folder, run `/book:init new`. It writes a starter book, and tells you which outside tools are missing on your machine and what each one turns off.

## A first session

```
/book:init new                    a starter book in this folder
/book:write-text                  "write the first chapter about ..."
/book:review-text                 a review of the chapter; the findings become notes
/book:revise-from-notes           go through the notes, one decision at a time
/book:build-editions              the print PDF, the screen PDF and the EPUB, as drafts
```

## Have a manuscript already?

Run `/book:init existing` in the folder that holds it, whatever its shape. Claude first asks you to make a backup, then reads the folder and drafts a move plan as a table: which files are chapters and in what order (they go to `manuscript/NNN-name.md`, the number sets the book order), which are notes, sources and images, and which stay where they are. You edit the plan; nothing moves until you agree. The files then move as they are: no byte changes, nothing is deleted, nothing is written over. After that, init adds only what is still missing and never changes your text.

If your chapters are already in a `manuscript/` folder as `NNN-name.md` files (for example `110-first-steps.md`), `/book:init new` in the folder above it is enough.

## The eleven skills

| Skill | Call | What it does |
|---|---|---|
| init | `/book:init` | Sets up a new book, or a book from any folder by a move plan you agree to; checks the tools on this machine |
| write-text | `/book:write-text` | Writes and rewrites prose; holds the prose rules and the text checks |
| review-text | `/book:review-text` | Reviews the prose of a chapter or the whole book; findings become notes |
| review-ideas | `/book:review-ideas` | Reviews the argument and evidence: `editor` in three stages, or `readers`, a cold review in a clean room; findings become notes |
| check-facts | `/book:check-facts` | Checks claims, quotes, figures and citations against the sources; findings become notes |
| collect-sources | `/book:collect-sources` | Finds, downloads, backs up and restores the source files |
| revise-from-notes | `/book:revise-from-notes` | Works through the open notes, yours and the reviews', one decision at a time |
| build-editions | `/book:build-editions` | Builds the print PDF, the screen PDF and the EPUB |
| design-cover | `/book:design-cover` | Makes, checks, compares and reviews the KDP print cover and the ebook cover; its review writes notes |
| prepare-sales-text | `/book:prepare-sales-text` | Writes and checks the back cover, the store description and the keywords, and exports store files; its review writes notes |
| run-checks | `/book:run-checks` | Runs every script check of the plugin on the book (text, facts, cover, sales text, setup) and writes a report |

You can also just say what you want ("build the book", "fact-check chapter 3"), and Claude picks the skill.

Every skill that reviews the book or proposes changes reads your `decisions.md` first. A point you already decided is not raised again.

The reviews (review-text, review-ideas, check-facts, and the review modes of design-cover and prepare-sales-text) write what they find as notes in `notes/`: one notes file for each file that has a finding, plus one for the whole book. `run-checks` writes a report instead, and the checks of collect-sources print their results. `revise-from-notes` goes through the notes with you: it shows a few small fixes, applies the one you pick, records the decision in `decisions.md` and deletes the note.

## What it assumes

- A **non-fiction** book.
- **English** prose for the prose checks. A book in another language still builds, but the English-only checks say `SKIPPED`.
- A **Markdown** manuscript, one file per chapter, named `NNN-name.md`.
- Citation keys in the **alpha BibTeX style**, such as `[Abc99]`.
- **KDP and Amazon** as the print and store target (cover geometry, store description, keywords).
- An opinionated **house style**: plain A2 English, ASCII punctuation (Latin letters with accents are allowed), no bold in running text, no phrase wrapped in a pair of dashes. The rules live in the write-text skill, and your own voice profile (`rules/voice.md`) can change many of them.

## Cost and the first run

- **Tokens.** `review-ideas` (above all its `readers` mode), `check-facts`, the review of `design-cover` and the review of `prepare-sales-text` start many subagents, and many of them read the whole book. That costs many tokens. Each of these skills says how big a run is and asks before it starts a batch.
- **The first build.** The first `/book:build-editions` downloads the `pandoc/extra` Docker image and fills a TeX Live volume. That is large and takes minutes, but it happens once.

## Permission prompts

The starter `.claude/settings.json` that `/book:init new` writes allows only a few tools that list and search files. So Claude asks you before it runs each script. If you trust the plugin's scripts, you can allow `python3` in `.claude/settings.json`.

## Trust

The cover file `publishing/cover/design.py` and the Docker images named under `tools:` in `book.yaml` run as code on your machine. Only run cover checks and builds on books you trust.

## Requirements

Needed:

- Claude Code.
- Python 3.9 or later, standard library only (tested on 3.13 and 3.14).

Needed to build the book:

- Docker, and bash. On Windows, use WSL.

Optional tools. Each one turns on some features. When a tool is missing, the check that needs it says `SKIPPED` and why, and nothing fails.

| Tool | Turns on |
|---|---|
| Docker | the build (all three editions), the Vale prose review, the BibTeX key check; the images are pinned by default, and you can override them under `tools:` in `book.yaml` |
| curl | fetching sources |
| tesseract, poppler | reading scanned sources (OCR) and text from PDF sources |
| Java | checking the EPUB with epubcheck (downloaded once, on first use) |
| rsvg-convert or cairosvg, ImageMagick | drawing and checking the cover |
| fc-match (fontconfig) | font lookups for the build and the cover |
| qpdf | draft protection and page counts without Docker |
| a word list at `/usr/share/dict/words` | finding scanned text in sources |
| calibre (not checked) | the `--azw3` Kindle file |
| git (not checked) | only the `--changes-since` copy of build-editions, which shows what changed since a commit |

To see what is on your machine, say "check my tools": the run-checks skill runs its `setup` mode. It checks every tool above except the two marked "not checked".

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
notes/                   open notes, from your reading and from the reviews
.book/                   work state: runs, build output, caches, files to add; kept out of git
```

It also writes a `.gitignore` and a `.claude/settings.json` that lets Claude look through the book without asking.

Every path is a `book.yaml` key, so you can change any of them. Every key is described in [book-yaml.md](plugins/book/skills/init/references/book-yaml.md).

## Publishing on KDP

KDP asks you to declare text, images and translations made with AI. Answer truthfully. The launch checklist of prepare-sales-text includes this step.

Not affiliated with or endorsed by Amazon or Anthropic. Kindle and KDP are trademarks of Amazon.com, Inc. or its affiliates.

## Problems and ideas

Open an issue: https://github.com/clutcher/book-writing-skills/issues

## Licence

Copyright (c) 2026 Igor Zarvanskyi.

The code and the text of the skills are under the MIT License, in [`LICENSE`](LICENSE). A copy is also inside the plugin folder, so an installed copy carries it.

A few files come from other projects and keep their own licences:

- `build-editions/assets/epub3-template*.html`: pandoc templates, BSD 3-Clause (see `epub3-template-LICENSE.txt` next to them);
- the JetBrains Mono fonts in `build-editions/assets/fonts/`: SIL Open Font License 1.1 (see `OFL.txt`; the same text is also inside `epub.css`);
- a few standard lines from pandoc's LaTeX template in `book-template.tex`: BSD 3-Clause.

The full list: [plugins/book/THIRD-PARTY.md](plugins/book/THIRD-PARTY.md).

## For maintainers

```
python3 tools/check-plugin.py [--with-other-book]
```

`tools/check-plugin.sh` does the same for those used to it.

It runs the lib tests, every skill's self-check, `--help` of every script, the leak scan, the named-files check, the skill-shape check, and the bytecode check. `--with-other-book` also runs every skill against a second, unrelated book (slow).

The leak scan reads a private word list from the folder named in the environment variable `BOOK_LEAK_LIST`, which holds `leak-words.txt` and `leak-allow.txt`. Without it, the scan looks in `.workspace/leak/`; when neither exists, it says `SKIPPED`.

```
BOOK_LEAK_LIST=/path/to/your-leak-list python3 tools/check-plugin.py
```
