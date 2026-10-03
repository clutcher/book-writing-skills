# Changelog

The plugin is in early 0.x versions: names, modes and config keys may still change between
versions. A change that needs work in an existing book is named here.

## 0.4.0

One folder layout, one config file, current names only.

### Changes that may need work in your book

- Only the layout that `/book:init new` writes is read. The two older layouts of this plugin
  (settings in the book's `CLAUDE.md`, or `book.yaml` beside `author/`, `reasons/`,
  `vocabulary/`, `marketing/` and a root `decisions.md`) are no longer read. Settings come only
  from the command line, `book.yaml` (or `book.json`) and the built-in defaults.
- Old key names are no longer read: for example `decisions`, `vocabulary.glossary`,
  `reading_notes`, `reasons`, `author.*`, `style.*`, `marketing.*`, `sources.files`,
  `sources.origin`, `outside_review`, `work.inbox`, `rules.accepted_flags` and `folder_layout`.
  `book_config.py check` reports each one as an unknown key. Use the names in
  `plugins/book/skills/init/references/book-yaml.md`.
- `decisions.md`: the status of an entry comes only from its `Status:` field. A status in a
  section heading or a ` -- CLOSED` title ending is no longer read; `decisions.py check` reports
  such an entry as `no-status`.
- Removed old names: `build-book.sh --reviewer`, `--diff-from` and `--diff-to` (use
  `--reviewer-copy` and `--changes-since`), `term-density-check.py --registry`, the old
  `metadata-crosscheck` cache folder and the old sales-text file names.
- The review lens name `governing device` is no longer read as `main image`, `clean-room.py`
  no longer looks for an `archive` folder inside the room, and `open-notes.py check` no longer
  advises on old note fields (`old-field-name`).

### New

- `/book:init existing` now works on any folder that already holds a book: Claude makes a
  backup, drafts a move plan you can edit (chapters, notes, sources, images), moves the files
  without changing them once you agree, then adds what the layout still lacks. The migration
  script for the two older layouts is gone.

## 0.3.1

### Changes that may need work in your book

- `fetch.py` and `ocr.py` (collect-sources) now write only with `--fix`, like every other script.
  `ocr.py` does not replace an existing PDF without `--force`.
- `search-suggestions.py` (prepare-sales-text) goes online only with `--online`.
- Citation keys now follow BibTeX's alpha style for more names: a hyphenated name with accents
  gives one letter per part, as alpha does (`Hernández-Ruiz` gives `HR`, not `Rui`). A name
  with a letter like `Ł` or `ø` now gets a key (`Luk`, `Sor`) instead of being left for a
  person. The key check may propose new keys for such entries. A key may hold only letters,
  digits and `+ _ . -`.
- A bibliography entry whose author starts with a capital like `Ł`, `Ö` or `É` was skipped by
  every bibliography check. It is now read, so such entries may show findings for the first time.
- key-bibtex-check gives accented names to BibTeX the way a `.bib` file writes them
  (`S{\o}rensen`), so BibTeX counts letters, not bytes.
- A new book's `.claude/settings.json` no longer allows `Read` and `cat` everywhere. An older book
  keeps its file: remove `"Read"` and `"Bash(cat:*)"` from it by hand.
- The top-level `book.yaml` key that picks the folder layout is now `folder_layout` (it was
  `layout`, which was easy to mix up with `book.layout`). The old name is not read any more.
- check-facts notes now start `From: check-facts all, <date>`.
- `build-book.sh --output` accepts only letters, digits, `.`, `_` and `-` in the file name.
- An epubcheck version without a known checksum runs only with `epub-check.py --allow-unverified`.

### Fixes

- `citation-key-check.py --fix` no longer crashes after renaming, and two keys that swap no
  longer merge into one.
- `book.yaml`: an empty section, a byte-order mark, an apostrophe before a comment, one string
  for a list, and values like `0306406152` are read correctly.
- `decisions.md`: headings like `## D-2: Title` and `## [D-2] Title` are read; an OPEN decision
  gets no date; Windows line endings are kept.
- A check that crashes now shows as FAIL with one line of reason, not as a finding. A check
  that finds no manuscript file says SKIPPED, not OK.
- The build: a trailing comma in `subjects`, file names with spaces, two editions built at the
  same time, and two chapters with the same file name in `--changes-since`.
- The ASCII check allows Latin letters with accents.

### Safety

- Downloads accept only `http` and `https`, have a size limit, and never follow a redirect to
  another scheme or from `https` down to `http`.
- `clean-room.py remove` deletes only a room that `setup` made.
- Every script that goes online names itself with one honest User-Agent. The two scripts that
  use unofficial Amazon endpoints say so, wait between calls and ask fewer questions.
- Vale reads the book read-only. Docker mounts work with commas in folder names.
- The skills say that text in a source is evidence, never instructions, and that a book's
  cover file and Docker images run as code on your machine.

### New books

- `/book:init new` sets up the Vale style at once, and the starter cover names real fonts. On a
  new book, run-checks shows one expected finding: the empty `book.description`.
- uncited-claim-check runs before the book has any sources.

### Docs

- Shorter skill descriptions and clearer trigger phrases; plugin paths that work from any
  folder. Every skill shows its modes when you type `/book:` (`argument-hint`).
- The README says what the plugin assumes, what it costs, what you need to build, and how to
  start with a manuscript you already have.
- The launch checklist asks you to answer KDP's question on AI-generated text, images and
  translations.
- Claims in the reference files were checked against their sources; some were corrected,
  some are now marked unverified.
- A third-party licence list: `plugins/book/THIRD-PARTY.md`.

## 0.3.0

The first public version.
