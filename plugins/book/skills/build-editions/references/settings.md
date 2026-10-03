# Build settings

Every value is taken in this order: command-line option (or `--set key=value`) > `book.yaml` >
the built-in default.

In `book.yaml` the build settings sit under `book:`, in lower case with underscores.

```yaml
book:
  title: My Book Title
  subtitle: A Subtitle
  author: Author Name
  format: 6x9
  font: cochineal
  font_size: 11pt
  chapter_style: canonical
  page_style: footer
  page_ornament: spiral-curly
  epub_identifier: urn:uuid:...        # never change once published
  language: en-US
manuscript:
  dir: manuscript
work:
  dir: .book                           # output goes to .book/output/
tools:
  pandoc_image: pandoc/extra:3.8.3
  pandoc_volume: book-to-pdf-texlive
  epubcheck: 5.1.0
```

## Book keys (`book:`)

| Key | Option | Values | Default |
|-----|--------|--------|---------|
| `title`, `subtitle`, `author` | `--title`, `--subtitle`, `--author` | text | none |
| `format` | `--format` | `8x10`, `7.5x9.25`, `7x10`, `6.69x9.61`, `6.5x9.25`, `6.14x9.21`, `6x9`, `5.5x8.5`, `5x8`, or any `WxH` in inches | `6x9` |
| `layout` | `--twoside` / `--oneside` | `twoside`, `oneside` | `twoside` |
| `font` | `--font` | `cochineal`, `garamond`, `cormorant-garamond`, `crimson-pro`, `baskerville`, `palatino`, `latin-modern` | `latin-modern` (ships with TeX, so it needs no extra install; choose another face for a final book) |
| `italic_font` | `--italic-font` | any `font` value; bold italic comes from the same family | none |
| `heading_font` | `--heading-font` | `match-body`, `source-sans`, `gyre-heros`, `latin-modern-sans`, any `font` value | `match-body` |
| `font_size` | `--font-size` | `10pt`, `10.5pt`, `11pt`, `11.5pt`, `12pt` | `11pt` |
| `leading` | `--leading` | a `\setstretch` number | computed |
| `heading_scale` | `--proportional-headings` | `proportional` | the LaTeX ladder |
| `code_scale` | `--code-scale` | code block x-height as a fraction of the body, e.g. `0.68` | `0.85` |
| `inline_code_scale` | `--inline-code-scale` | inline code x-height as a fraction of the body, e.g. `0.9` | `1.0` |
| `chapter_style` | `--chapter-style` | `canonical`, `classic`, `technical`, `bold`, `elegant` | `canonical` |
| `section_style` | `--section-style` | `technical`, `scholarly`, `literary`, `editorial`, `classic` | `technical` |
| `ornament` | `--ornament` | `hexagon`, `varhexagon`, `star`, `sun`, `square`, `fleuron` | `hexagon` |
| `pages` | `--pages` | a page count, or `auto`; the digital edition takes `auto` as 250, since its margins do not depend on the count; the design-cover skill reads the same key for the spine width | `auto` |
| `quote_style` | `--quote-style` | `italic`, `plain`, `small`, `border`, `dash`, `guillemet`, `quote` | `italic` |
| `page_style` | `--page-style` | `header`, `footer` | `header` |
| `page_ornament` | `--page-ornament` | `none`, `spiral-straight`, `spiral-curly`, `wasy-hexagon`, `wasy-verhexagon`, `wasy-star`, `wasy-sun`, `adforn-fleuron`, `adforn-leaf`, `adforn-vine` | `none` |
| `page_ornament_size` | `--page-ornament-size` | `small`, `medium`, `large` | `medium` |
| `all_page_folios` | `--all-page-folios` | `true`, `false` | `false` |
| `highlight` | `--highlight` | `monochrome`, `pygments`, `tango`, `kate`, `none` | `monochrome` |
| `top_level` | `--top-level` | `part`, `chapter`, `section` | `chapter` |
| `toc_depth` | `--toc-depth` | `1`, `2`, `3` | `2` |
| `toc` | `--toc` / `--no-toc` | `true`, `false` | `true` |
| `numbered` | `--numbered` | `true`, `false` | `false` |
| `pattern` | `--pattern` | file-name glob; keeps only the book's files that match | `*.md` |
| `exclude` | `--exclude` | regex of files to leave out | none |
| `part_pages` | `--part-pages` / `--no-part-pages` | `true`, `false` | `true` |
| `part_overview` | `--part-overview` | `true`, `false`; needs `part_pages` ([part-pages.md](part-pages.md)) | `false` |
| `cover_front`, `cover_back` | `front.png`, `back.png` in `cover.final`, when the design-cover skill shipped them | image path from the book root; bound into the digital PDF only | none |
| `ebook_cover` | `ebook.png` in `cover.final`, when shipped | EPUB cover image; KDP wants at least 2560 px on the long side | none |
| `hyphenation_language` | none | babel language name for the print hyphenation, e.g. `ngerman` | `english` |
| `placeholder_text` | none | the text reported as still open after a build | `TO BE ASSIGNED` |

All values given in `book.yaml` are checked the same way as options: an unknown font or style
stops the build before anything runs.

### Ebook package keys

| Key | Goes to | Notes |
|-----|---------|-------|
| `epub_identifier` | `dc:identifier` | Set it and never change it. An ISBN in any punctuation becomes `urn:isbn:` with its ONIX scheme. Missing: pandoc makes up a UUID per build and the build warns. |
| `publication_date` | `dc:date`, and the year in `dc:rights` | `YYYY`, `YYYY-MM` or `YYYY-MM-DD`; the book's date, not the build's |
| `publisher` | `dc:publisher` | left out when missing |
| `subjects` | one `dc:subject` each | comma-separated; no authority is named, because naming BISAC would demand real BISAC codes |
| `description` | `dc:description` | the blurb stores show |
| `language` | `dc:language` and `xml:lang` | BCP 47, e.g. `en-US` (default) |
| `accessibility_summary` | `schema:accessibilitySummary` | no default: left out when missing, and the build warns ([epub.md](epub.md)) |

Why each of these matters: [epub.md](epub.md).

### Filter keys (read by the Lua filters)

`filter-settings.py` hands these to the filters. A key left out keeps the filter's default.

| Key | Default | Use |
|-----|---------|-----|
| `latex_commands_to_drop` | none | more LaTeX commands (with their arguments) the ebook may drop because they only shape the printed page, e.g. `[enlargethispage]` |
| `language_codes` | latin, french, german, spanish, italian | babel name to BCP 47 code for `\langtext{name}{...}`, e.g. `{greek: el}` |
| `heading_types` | Preface, Acknowledgments, References | top-level heading text to EPUB section type, e.g. `{Foreword: foreword}` |
| `chapter_heading_word` | `Chapter` | a heading that starts with this word and a number is a chapter |
| `front_matter_pages` | `[Dedication, Epigraph]` | names, in order, for the front-matter raw blocks that are not the copyright page |
| `copyright_markers` | `[rights reserved, ISBN]` | text that marks a raw block as the copyright page |
| `emblem_alt` | `Publisher emblem` | alt text of an image placed with a `tikzpicture` (the publisher emblem) |
| `references_heading` | `References` | the level-1 heading of the bibliography, where citation links point |

## Paper keys (`paper:`)

Read only when `book.yaml` has `kind: paper` (the default is `kind: book`). The title comes from
`book.title`; `book.subtitle`, the page format and the font keys above are not used for a paper.

```yaml
kind: paper
book:
  title: My Paper Title
  author: Author Name                  # used when paper.authors is empty
paper:
  authors:
    - {name: Author Name, affiliation: A University, email: author@example.org}
  abstract: manuscript/010-abstract.md
  template: article
  engine: xelatex
  anonymous: false
  arxiv_category: null
  format: a4
```

| Key | Option | Values | Default |
|-----|--------|--------|---------|
| `authors` | none | a list of `{name, affiliation, email}`; affiliation and email may be left out | `[]`, which means `book.author` alone |
| `abstract` | none | the abstract file; it fills the abstract field and is left out of the body | `manuscript/010-abstract.md` |
| `template` | `--set paper.template=acm` | a built-in template: `article`, `acm` (`acmart` sigconf), `ieee` (`IEEEtran` conference), `lncs` (`llncs`); anything else is refused | `article` |
| `engine` | `--set paper.engine=pdflatex` | `xelatex`, `pdflatex` (arXiv supports both; lualatex is refused) | `xelatex` |
| `anonymous` | `--anonymous` | `true` builds with no author, affiliation or email; the file names end in `-anonymous` | `false` |
| `arxiv_category` | none | an arXiv category such as `cs.SE`; shown in the build report only | none |
| `format` | `--set paper.format=letter` | `a4`, `letter` | `a4` |
| `abstract_max_words` | none | not read by the build; the write-text paper check reads it | `250` |

The four templates take the same title block: `title`, the authors with affiliation and
email, the abstract, the body and the references section, which stays the hand-written
references file. `paper.format` sets the paper size of `article`, `ieee` and `lncs`; `acm`
keeps the page size of `acmart`. The `acm` template prints no ACM copyright block, reference
format or CCS concepts (`\setcopyright{none}`, `printacmref=false`), so a preprint builds without
ACM boilerplate; add those when the venue gives them. A venue not in the list is added to the
plugin as a new built-in template (`assets/templates/paper-<name>.tex`), not kept as a file
in one paper.

**Citations.** Every template keeps the book's alpha labels (`[Abc99]`) and links each one to
its entry in the references file. A venue that requires numeric citations (`[1]`) is not
covered: the labels are not renumbered.

## Folder keys

| Key | Option | Default |
|-----|--------|---------|
| `manuscript.dir` | `--manuscript` | `manuscript` |
| `work.output` | `--output-dir` | `.book/output` |
| `manuscript.references` | none | `manuscript/900-references.md` |
| `manuscript.order` | none | `natural` (sorted by file name); `list` takes the order from `manuscript.files` |
| `manuscript.files` | none | none; with `order: list`, the file names in book order ([manuscript-layout.md](manuscript-layout.md)) |

A folder given as the last argument that sits directly under the book root is used as the
manuscript folder. Without that argument the build always uses `manuscript.dir`, whatever folder
of the book it runs from.

## Tool keys (`tools:`)

| Key | Default | Use |
|-----|---------|-----|
| `pandoc_image` | `pandoc/extra:3.8.3` | the pinned image; must match the pandoc the EPUB template was taken from ([epub.md](epub.md)) |
| `pandoc_volume` | `book-to-pdf-texlive` | Docker volume holding TeX Live packages and fonts (a book only) |
| `paper_tex_image` | `texlive/texlive:TL2025-historic@sha256:7056390e...` (pinned by digest) | full TeX Live 2025 (2.6 GB), as on arXiv; latexmk for every paper and the arXiv bundle check run here |
| `epubcheck` | `5.1.0` | epubcheck release, written like `5.1.0`; the jar is checked against a pinned sha256 for this version. Another version has no known sha256 and is refused unless `epub-check.py` runs with `--allow-unverified` |

## Other options

| Option | Does | Default |
|--------|------|---------|
| `--edition <name>` | `print`, `digital`, `epub`, `all` for a book; `paper` (or `all`) for a paper | `all`, which is `paper` for a paper |
| `--arxiv` | paper only: also write the arXiv source bundle and check it | off |
| `--anonymous` | paper only: no authors, affiliations or emails | `paper.anonymous` |
| `--parallel` / `--sequential` | build the editions together or one by one | parallel |
| `--azw3` | also convert the EPUB to AZW3 (needs calibre) | off |
| `--final` / `--draft` | final or draft mode | draft |
| `--reviewer-copy <name>` | reviewer name on a draft | none |
| `--protected` / `--unprotected` | PDF copy/print protection for drafts | protected |
| `--changes-since <ref>`, `--changes-until <ref>` | changes copy ([changes-since.md](changes-since.md)) | none |
| `--output <file>` | output file name: letters, digits, `.`, `_` and `-` only | generated |
| `--template <file>` | another LaTeX template, for a book only; a paper refuses it and names its template in `paper.template` | bundled |
| `--config <file>`, `--set key=value` | config file, one override (repeatable) | found by walking up |

## Structure mapping

| `--top-level` | `#` becomes | `##` becomes | `###` becomes |
|---------------|-------------|--------------|---------------|
| `part` | Part | Chapter | Section |
| `chapter` | Chapter | Section | Subsection |
| `section` | Section | Subsection | Subsubsection |

## Page formats and margins

All formats are Amazon KDP sizes; any other `WxH` also works.

| Format | Use |
|--------|-----|
| `8x10` | large format, textbooks |
| `7.5x9.25` | wide page: reference and how-to books |
| `7x10` | tall format: illustrated how-to books |
| `6.69x9.61` | between 6x9 and 7x10 |
| `6.5x9.25` | common European size (16.5 x 23.5 cm) |
| `6.14x9.21` | like 6x9, a little larger |
| `6x9` | KDP standard (default) |
| `5.5x8.5` | digest |
| `5x8` | compact |

Margins are computed from the trim and the page count, never set per format:

```
inner  = max(KDP_gutter_for(pages), 0.143 * width)
outer  = 0.106 * width
top    = 0.076 * height
bottom = 0.0923 * height
```

KDP's inside-margin minimums by page count ([table](typography-research.md#kdp-gutter-floor))
are the floor under `inner`. KDP's inside margin already
includes the binding allowance, so no separate `bindingoffset` is set. With `pages: auto` the
build runs once with 250 pages assumed, reads the real count from the PDF, and builds again
only when the count lands in another KDP gutter band. A fixed `pages` skips the second pass.
The digital PDF keeps the print text width and only centres it. Why the formula is this way:
[typography-research.md](typography-research.md).
