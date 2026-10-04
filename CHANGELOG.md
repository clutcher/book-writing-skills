# Changelog

The plugin is in early 0.x versions: names, modes and config keys may still change between
versions. A change that needs work in an existing book is named here.

## 0.6.0

Real BibTeX citations, for books and papers.

### Changes that need work in your book

- Sources live in `sources/references.bib` (`sources.bibliography`): one BibTeX entry per source,
  whose key is the citation key. `sources/list.md` keeps only access and work fields (Access URLs,
  Access status, Fetch note, Cached text, Cached original, Findings, Note, Record history,
  Supersedes) under `### [Key]` headings; identity fields there are reported as
  `identity-in-list`.
- The text cites with pandoc citations: `[@Key]`, `[@A; @B]`, `[@A, p. 12]`, `[see @A]`, narrative
  `@A`, and `@{Key--}` for a key pandoc would cut short. Old `[Key]` text citations are no longer
  read.
- The references file holds only its heading and `::: {#refs}` / `:::`; every edition builds the
  list with pandoc citeproc from the `.bib`.
- `sources.citation_style`: `alpha` (labels are the keys, APA-like entries) or `numeric`
  (IEEE-like). The styles ship in `skills/build-editions/assets/csl/`; `numeric.csl` comes from the
  CSL project under CC BY-SA 3.0 (`THIRD-PARTY.md`). `sources.citation_style_file` names a `.csl`
  of the book's own instead; `null` keeps the style the build ships.

### What to do in an existing book

1. Create `sources/references.bib` with one BibTeX entry per source; the key of each entry is
   the citation key the book already uses.
2. Move the identity fields (authors, title, year, publisher and the like) out of
   `sources/list.md` into those entries; the list keeps only the access and work fields.
3. Turn the text citations into pandoc citations: `[Key]` becomes `[@Key]`, `[Key, p. 12]`
   becomes `[@Key, p. 12]` and `[A, B]` becomes `[@A; @B]`.
4. Replace the body of the references file with `::: {#refs}` and `:::` under its heading.
5. Run `/book:run-checks facts`. What is left is reported: `old-citation` for a text citation in
   the old form, `hand-written-references` for a references file that still holds entries, and
   `identity-in-list` for a list entry that still holds identity fields.

### Checks

- Every cited key must exist in the `.bib`; the list and the `.bib` hold the same keys;
  `key-bibtex-check.py` runs real BibTeX (`alpha.bst`) on the `.bib` and compares each label with
  its key; `citation-key-check.py --fix` renames a key everywhere in one pass;
  `reference-format-check.py` checks the `.bib` entries.
- Removed: `reference-sort.py`, `key-authors-check.py`, `argument-key-check.py` and
  build-editions' `key-pattern-check.py`, which only served the hand-written references file.
- collect-sources: new `add-source.py` writes a source's `.bib` entry and list entry under one
  checked key. It refuses an entry type that is not letters, a field name outside
  `[A-Za-z][\w\-:.+]*` and unpaired braces, and takes a chosen `--key` when the names hold no
  Latin letters.
- A `crossref` child takes its parent's author, editor and year for its key, as BibTeX does, and a
  key rename follows `crossref`.
- For a paper, `key-bibtex-check.py` runs BibTeX in `tools.paper_tex_image`, so a paper needs one
  TeX image; every check container runs with no network.
- A bare web address (`https://example.org/@name`) and an e-mail-like word (`x_@Key`) are not
  citations, the same as in the pandoc build.
- `citation_key.py` takes `--year n.d.` for a work with no year (`--year=--` breaks on Python 3.9).

### Also in this version

- An anonymous paper hides an included PDF's properties under pdflatex, and the build and
  `arxiv-bundle-check.py` report an image whose metadata names someone (`image-metadata`).
- design-cover: `overlay.py` writes the overlay image only with `--fix` or `--out`, so
  `run-checks` never writes into the book.
- A title or author still holding the placeholder text no longer goes into the output file name.
- A cited key with no `.bib` entry stops the build with a clear message and no Lua stack trace.
- Containers that need no network run with `--network none`.

## 0.5.0

Research papers, next to books.

- New top-level `book.yaml` key `kind`: `book` (the default) or `paper`. A paper's settings live
  under `paper:` (authors, abstract, template, engine, anonymous, arxiv_category,
  abstract_max_words, format); every key and its default is in
  `plugins/book/skills/init/references/book-yaml.md`.
- `/book:init new paper` writes a starter paper (abstract, introduction with a numbered
  contribution list, related work, method, results, threats to validity, conclusion,
  references), with no cover and no sales text. It works in a folder that already holds other
  files and never writes over one.
- build-editions: a `paper` edition (pandoc to a kept `.tex`, then xelatex or pdflatex),
  `--anonymous` for double-blind review, and `--arxiv` for the arXiv source bundle. New check
  `arxiv-bundle-check.py` compiles the bundle in a clean folder.
- build-editions: four built-in paper templates, chosen by `paper.template`: `article` (the
  default), `acm` (`acmart` sigconf), `ieee` (`IEEEtran` conference) and `lncs` (`llncs`). The
  author switches venue by changing that one key; each builds with xelatex and pdflatex, and an
  anonymous build leaves out every author (`acm` also turns on the class's `anonymous,review`).
  Any other value, a template file included, is a `wrong-value` defect; a new venue is added
  to the plugin as a new built-in template. Citations keep their alpha labels in every template (until 0.6.0).
- New tool key `tools.paper_tex_image`, full TeX Live 2025 pinned by digest
  (`texlive/texlive:TL2025-historic`, 2.6 GB, pulled on the first paper build). Every paper
  PDF and every arXiv bundle check compiles there, with the same classes arXiv has; the pandoc
  step stays in `tools.pandoc_image`, and a paper never uses `tools.pandoc_volume`.
- write-text: a paper voice profile (`profiles/paper-voice.md`) and paper rules (section 13);
  new check `paper-check.py` (abstract length, contribution list, every figure and table
  referenced, a threats-to-validity section).
- run-checks: a paper skips the cover and sales-text groups and runs the two paper checks.
- review-text and review-ideas read a paper as sections, not chapters.

Nothing changes for a book: `kind` defaults to `book`.

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
