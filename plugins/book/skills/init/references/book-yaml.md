# book.yaml: every key

`book.yaml` is the one config of a book. Every script of every skill of the book plugin finds it by
walking up from the folder it works in (`--config FILE` names it), through
`lib/book_config.py`. It is data, not prose: a malformed value gives a confident wrong report
somewhere else rather than an error, so check it after every edit:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/book_config.py check     # unknown, retired and old key names, missing paths, unused files
python3 ${CLAUDE_PLUGIN_ROOT}/lib/book_config.py show      # every value, and where it came from
```

## Rules

- **Every key is optional.** A missing key takes the default below; `null` means "none", and the
  script then computes a value, falls back, or skips.
- **Which value wins:** `--set KEY=VALUE` on the command line > `book.yaml` > the `## Book Metadata` and
  `## Coined Terminology` sections of an older book's `CLAUDE.md` > the default.
- **Paths are relative to the folder that holds `book.yaml`**; `~` is expanded.
- **`book:` keys** also accept the older spelling `Title-Case-With-Hyphens`; `Cover-Front` and
  `cover_front` are the same key. A key no script reads is reported by `check`.
- **The YAML is a subset:** mappings, lists, plain and quoted scalars, one-line `[...]` and
  `{...}`, `|` and `>` blocks, `#` comments. No anchors, tags or several documents in one file.
- **`epub_identifier` is set once and never changed**: a reading system files bookmarks and
  highlights under it, and a store reads a new identifier as a new title.
- **`publication_date` is the book's date, not the build's**; it also sets the copyright year.

## What a new book starts with

`new.py` writes only the keys a new author sets on day one: `title`, `subtitle`, `author`,
`language`, `format`, `font`, `description`, `publication_date`, `epub_identifier`,
`sources.backup` (null until the author names a private folder), and a commented `terms:`
example. Every path keeps its default, so the file stays short; add a key
only to change its value.

## The full schema

The value shown is the default of the standard layout.

```yaml
version: 1

book:                                  # metadata and build settings (Title-Case-With-Hyphens also accepted)
  title: null
  subtitle: null
  author: null
  language: en-US                      # BCP 47; dc:language and xml:lang
  description: null                    # the blurb stores show (dc:description)
  publication_date: null               # YYYY, YYYY-MM or YYYY-MM-DD; the book's date
  publisher: null
  subjects: null                       # comma-separated
  epub_identifier: null                # set once (ISBN or urn:uuid), never change
  accessibility_summary: null          # the build warns when missing
  format: 6x9                          # trim WxH in inches, or a KDP name; 6x9 when not set
  layout: twoside                      # twoside | oneside
  pages: auto                          # interior page count; build gutter and cover spine
  font: latin-modern                   # cochineal garamond cormorant-garamond crimson-pro baskerville palatino latin-modern
  italic_font: null                    # any font value
  heading_font: match-body             # match-body source-sans gyre-heros latin-modern-sans or a font
  font_size: 11pt                      # 10pt 10.5pt 11pt 11.5pt 12pt
  leading: null                        # \setstretch number; computed when null
  heading_scale: null                  # proportional, else the LaTeX ladder
  code_scale: 0.85
  inline_code_scale: 1.0
  chapter_style: canonical             # canonical classic technical bold elegant
  section_style: technical             # technical scholarly literary editorial classic
  ornament: hexagon                    # hexagon varhexagon star sun square fleuron
  quote_style: italic                  # italic plain small border dash guillemet quote
  page_style: header                   # header | footer
  page_ornament: none                  # none spiral-straight spiral-curly wasy-* adforn-*
  page_ornament_size: medium           # small medium large
  all_page_folios: false
  highlight: monochrome                # monochrome pygments tango kate none
  top_level: chapter                   # part chapter section
  toc_depth: 2
  toc: true
  numbered: false
  pattern: "*.md"                      # keep only matching manuscript files
  exclude: null                        # regex of files to leave out
  part_pages: true
  part_overview: false
  cover_front: null                    # image bound into the digital PDF; null = <cover.final>/front.png when it exists
  cover_back: null                     # null = <cover.final>/back.png when it exists
  ebook_cover: null                    # EPUB cover, >= 2560 px long side; null = <cover.final>/ebook.png when it exists
  hyphenation_language: english        # babel name
  placeholder_text: TO BE ASSIGNED
  latex_commands_to_drop: []           # ebook filter
  language_codes: {}                   # added to latin french german spanish italian
  heading_types: {}                    # added to Preface Acknowledgments References
  chapter_heading_word: Chapter
  front_matter_pages: [Dedication, Epigraph]
  copyright_markers: [rights reserved, ISBN]
  emblem_alt: Publisher emblem
  references_heading: References

manuscript:
  dir: manuscript
  order: natural                       # natural (sort -V by name) | list
  files: []                            # with order: list, the file names in book order
  chapter_pattern: '(?:^|-)chapter-(\d+)\.md$'
  part_pattern: '^(\d+-)?part-[\w-]+\.md$'
  front_matter: ["0[0-9][0-9]-*.md"]
  back_matter: ["9[0-9][0-9]-*.md"]
  references: manuscript/900-references.md
  summary_heading: Summary

terms:                                 # coined terms
  families: []                         # - {term: X, role: primary|antonym|borrowed, also: [forms]}
                                       # several pairs are fine: each antonym pairs with the nearest primary above it
  compounds: []                        # legal compounds, lower case
  watch_words:                         # word lists some checks read; every one may be left out
    container_terms:                   # word-for-two-things-check
      outside_names: []                # terms.watch_words.container_terms.outside_names: named
                                       # outside things, e.g. [Square Foot Gardening, Montessori];
                                       # empty: the check is SKIPPED
      book_terms: []                   # terms.watch_words.container_terms.book_terms: the book's
                                       # own words besides terms.families, e.g. [open bed]
      watchlist: []                    # terms.watch_words.container_terms.watchlist: replaces the
                                       # built-in watched words, e.g. [method, [system, systems]]
    people:                            # person-introduction-check
      eponyms: {}                      # terms.watch_words.people.eponyms: surname: [patterns] of
                                       # named laws or tests to skip, e.g. {Rivera: ["Rivera'?s rule"]}
      aliases: {}                      # terms.watch_words.people.aliases: bibliography name: [other
                                       # names], e.g. {"Rivera, M.L.": [Maria Rivera]}
    word_sense:                        # word-sense-check
      name: null                       # terms.watch_words.word_sense.name: what the avoided sense
                                       # is called, e.g. counted flavours
      reason: null                     # terms.watch_words.word_sense.reason: why the book avoids
                                       # it; for the reader, no script reads it
      words: []                        # terms.watch_words.word_sense.words: e.g. [[flavour,
                                       # flavours], [note, notes]]; empty: the check is SKIPPED
      scope_targets: []                # terms.watch_words.word_sense.scope_targets: nouns after
                                       # "<word> of the", e.g. [dish, loaf]; empty: no scope signal
    notes_about_the_book: []           # terms.watch_words.notes_about_the_book (check-facts
                                       # stale-argument-pointer-check): argument files about the
                                       # book's own structure, e.g. [thinking/argument/plan.md]
    internal_first_nouns: []           # terms.watch_words.internal_first_nouns (uncited-claim-check):
                                       # nouns inside the book for "the first <noun>", e.g. [recipe]
    titles_used_as_names: []           # terms.watch_words.titles_used_as_names
                                       # (reference-format-check): short titles that are also
                                       # ordinary names, matched only in full, e.g. [Compost]
    reading_topics: []                 # terms.watch_words.reading_topics (unread-sources): words or
                                       # patterns; only matching unread sources are queued
    reading_groups: {}                 # terms.watch_words.reading_groups (unread-sources): group:
                                       # [words], e.g. {soil: [soil, compost], pests: [aphid, slug]}

glossary_format:                       # how the glossary is written
  heading_separator: " -- "            # ### term -- where
  location_pattern: '^(?:Ch(?:apter)?\.?\s*(?P<chapter>\d+)\b|(?P<file>[A-Za-z][\w-]*))'

thinking:                              # the author's thinking: read by the skills, never printed
  dir: thinking
  stance: thinking/author/stance.md
  stance_details: thinking/author/stance-details.md
  audience: thinking/author/audience.md
  argument: thinking/argument          # claims.md and one file per topic
  doubts: thinking/doubts              # counterarguments.md, open-questions.md

rules:                                 # what the book has settled
  dir: rules
  decisions: rules/decisions.md        # ## Index (generated) + ## Details
  glossary: rules/glossary.md
  voice: rules/voice.md                # voice profile; skills/write-text/profiles/default.md when missing
  vale: rules/vale                     # the Vale styles folder
  vale_ini: rules/vale/vale.ini

sources:
  list: sources/list.md
  quotes: sources/quotes.md
  library: sources/library             # the copies; keep out of git
  library_index: sources/library-index # one record per library file; in git
  backup: null                         # private folder for files that cannot be downloaded again
  to_add: null                         # null = <work.dir>/sources-to-add
  citation_style: alpha                # alpha only; for information

notes: notes                           # open notes only

publishing:
  cover: publishing/cover              # design.py, font-widths/, final/
  sales_text: publishing/sales-text    # back cover, store texts, keywords

work:                                  # or just `work: .book`
  dir: .book                           # keep out of git
  runs: null                           # null = <work.dir>/runs; one folder per run
  output: null                         # null = <work.dir>/output
  caches: null                         # null = <work.dir>/caches

writing:                               # null = the value in the voice profile
  sentence_min_words: null             # profile default 10
  sentence_max_words: null             # 25
  sentence_review_below: null          # 6
  sentence_review_above: null          # 40
  sentence_target_share: null          # 0.8
  paragraph_min_sentences: null        # 3
  paragraph_max_sentences: null        # 8
  inversion_gap_words: null            # 0
  inversion_min_paragraph_gap: null    # 3
  inversions_per_section: null         # 0
  paragraph_length_exempt: []          # [] = the built-in exemptions
  term_phases: null                    # e.g. "1-4:basics,5-10:practice,11-12:depth"
  words_per_page: null                 # 390 when null

cover:
  design: null                         # null = <publishing.cover>/design.py
  final: null                          # null = <publishing.cover>/final, the shipping files
  trim: null                           # null = book.format
  paper: bw-white                      # bw-white bw-cream color-premium color-standard
  book_pdf: null                       # null = the final print PDF in work.output, else
                                       # the newest print PDF there
  output: null                         # null = <work.output>/cover
  templates: null                      # null = <work.caches>/kdp-templates
  shelf_screenshots: null              # null = <work.caches>/shelf-screenshots
  cmyk_limit: 88                       # percent per channel
  icc: null                            # CMYK profile for a real conversion
  srgb_profile: null                   # null = searched in the system folders

sales_text:
  back_cover: null                     # null = <publishing.sales_text>/back-cover.md, the single source of the back-cover text
  amazon: null                         # null = <publishing.sales_text>/amazon.html
  keywords: null                       # null = <publishing.sales_text>/keywords-and-categories.md
  intended_impression: null            # null = <publishing.sales_text>/intended-impression.md
  plain_description: null              # null = <publishing.sales_text>/plain-description.txt (generated)
  contents: null                       # null = <publishing.sales_text>/contents.html (generated)
  contents_full: null                  # null = <publishing.sales_text>/contents-full.html (generated)
  preface: null                        # null = the first front-matter file named *preface*
  retired_phrases: []
  shared_spans: []
  contents_skip: []                    # file-name globs left out of the contents pages
  amazon_limit: 4000
  keyword_slots: 7
  keyword_chars: 50
  categories_per_format: 3
  sample_print_share: 0.2
  sample_ebook_share: 0.1

readers_review:                        # the readers mode of review-ideas
  room: null                           # null = <book folder>-readers-review, next to the book
  sources_for_reviewer: null           # null = <work.output>/sources-for-reviewer.md
  main_metaphor: null                  # Lens 8
  key_sources: []                      # Lens 2 checks these hardest
  research_field: null                 # Lens 3
  similar_books: []                    # Lens 6
  author_background: null              # Lens 6
  audience: null                       # the contract and Lens 4
  lens_batch: 3
  skeptic_batch: 2
  skills_off: []                       # other skills to switch off in the room
  plugin_id: null                      # null = book@book-writing-skills
  lenses: []                           # [] = the nine default lenses; items are names or {name, question, weight, detail}

tools:                                 # docker images pinned to a tag or digest
  pandoc_image: pandoc/extra:3.8.3
  pandoc_volume: book-to-pdf-texlive
  vale_image: jdkato/vale:v3.14.2
  bibtex_image: blang/latex:ubuntu@sha256:2c32abc3555a01e180528d542955e2730f7f3793cdeba49b1655de9b897cbafb
  render_image: null                   # an image with rsvg-convert, only when none is installed
  epubcheck: 5.1.0
```

## Older layouts and old key names

Two older layouts are still read, so a book keeps working until `existing.py` moves it
([existing.md](existing.md)). `layout: new`, `layout: previous` or `layout: old` at the top of
`book.yaml` chooses one by hand; otherwise the folders decide.

- **previous**: a `book.yaml` book with `decisions.md`, `vocabulary/`, `reading-notes/`,
  `reasons/`, `author/`, `style/`, `marketing/` or `sources/files/`, and none of `thinking/`,
  `rules/`, `notes/`, `publishing/`.
- **old**: no `book.yaml`, and a `CLAUDE.md` holding `## Book Metadata` (or
  `review/sources-registry.md`).

| Key | previous | old |
|---|---|---|
| `thinking.stance`, `thinking.stance_details` | `author/stance.md`, `author/stance-details.md` | my-stance.md and my-stance-details.md at the book root |
| `thinking.audience` | `author/positioning.md` | book-positioning.md at the book root |
| `thinking.argument` | `reasons` | `research` |
| `thinking.dir`, `thinking.doubts`, `rules.dir` | none | none |
| `rules.decisions` | `decisions.md` | `decisions.md` |
| `rules.glossary` | `vocabulary/glossary.md` | `review/glossary-registry.md` |
| `rules.voice` | `author/voice.md` | none |
| `rules.vale`, `rules.vale_ini` | `style`, `style/vale.ini` | `.vale`, `.vale.ini` |
| `sources.list`, `sources.quotes` | `sources/list.md`, `sources/quotes.md` | `review/sources-registry.md`, `review/fact-check-findings-registry.md` |
| `sources.library`, `sources.library_index` | `sources/files`, `sources/origin` | `review/sources` (fetch and OCR records sit beside each file) |
| `sources.to_add` | `<work.dir>/sources-to-add` | `review/sources/incoming` |
| `notes` | `reading-notes` | `personal-review` |
| `publishing.cover`, `publishing.sales_text` | `cover`, `marketing` | `cover`, `cover` |
| `cover.design`, `cover.final` | `cover/design.py`, `cover/final` | none, `cover` |
| `sales_text.back_cover` | `marketing/back-cover.md` | none |
| `sales_text.amazon` | as new | `cover/kdp-description.html` |
| `sales_text.plain_description` | as new | `cover/plain-description.txt` |
| `sales_text.contents`, `sales_text.contents_full` | as new | `cover/contents.html`, `cover/contents-full.html` |
| `work` | `.book` | `.`, with runs in `review`, output in `output`, caches at the root |

**Old key names still work**, as other names of the new keys; `book_config.py check` names the
new key for each one (`old-key-name`):

| Old name | New name |
|---|---|
| `decisions` | `rules.decisions` |
| `vocabulary.glossary` | `rules.glossary` |
| `reading_notes` | `notes` |
| `reasons` | `thinking.argument` |
| `author.stance`, `author.stance_details` | `thinking.stance`, `thinking.stance_details` |
| `author.positioning` | `thinking.audience` |
| `author.voice` | `rules.voice` |
| `style.dir`, `style.vale_ini` | `rules.vale`, `rules.vale_ini` |
| `sources.files`, `sources.origin` | `sources.library`, `sources.library_index` |
| `cover.dir` | `publishing.cover` |
| `marketing.dir` | `publishing.sales_text` |
| `marketing.<name>` | `sales_text.<name>` |
| `sales_text.google_books` | `sales_text.plain_description` |
| `outside_review.<name>` | `readers_review.<name>` |
| `vocabulary.heading_separator`, `vocabulary.location_pattern` | `glossary_format.heading_separator`, `glossary_format.location_pattern` |

When a book sets both names of one key, the new name wins. Three keys are retired and reported
as defects (`retired-key`): `work.inbox` (entries a run proposes are staged inside its own run
folder), `sources.incoming` (files added by hand go to `sources.to_add`) and
`rules.accepted_flags` (no check reads accepted counts: every finding is reported until it is
fixed). An accepted counts file left in the book (`rules/accepted-flags.json`,
`<work.dir>/baselines/sources.json`) is reported as `unused-file`, to delete.

The plain-text description was named `google-books.txt` (`cover/google-books-description.txt` in
the oldest layout); while only that file exists, it is still read and written. The generated
contents pages had store-named files; they are made again under the new names, and the old
files can be deleted.
