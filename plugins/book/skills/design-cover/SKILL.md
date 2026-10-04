---
name: design-cover
description: >-
  Makes, checks, compares and reviews the KDP print cover and the ebook cover of a book, from a
  Python design file in the book. Use it when the author asks to make or update the cover, the
  wrap, the spine or the ebook cover image, to check cover colors, fonts, print safety or the
  KDP template, to compare cover versions, or to review or score the cover. For the words on the
  back cover or the store page use prepare-sales-text; for the book interior use build-editions.
argument-hint: "[make|compare|review]"
---

# Design cover

A book cover is three surfaces sold as one object: the front (seen as a small picture in the
store grid), the spine (seen on a shelf) and the back (seen in the hand). This skill turns the
book's own design file into every file KDP and the stores need, checks those files, and reviews
the result.

The artwork is **book content**, so it lives in the book: `publishing/cover/design.py`. Everything that is
the same for every book lives here. How to write a design file: `references/design-file.md`.

## Modes

| Mode | What it does | Main scripts |
|---|---|---|
| `make` (default) | SVG for every panel, PNG, ebook PNG and JPEG, print PDF, the KDP template (downloaded when missing) and its overlay, then the cover checks: color contrast and CMYK limit, fonts installed, text inside the safe area and out of the barcode box, spine text, template size; `--fix` ships the files into the book | `make.py`, then `color-check.py`, `font-check.py`, `layout-check.py`, `overlay.py` |
| `compare` | old against new: overlay, side by side, thumbnails, pixel count; grids of variants | `compare.py` |
| `review` | seven-lens review with scores at full size and thumbnail; findings become notes | `references/review-prompt.md` |

Scripts are in `${CLAUDE_PLUGIN_ROOT}/skills/design-cover/scripts/`. Every block below starts from

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/design-cover/scripts"
```

and runs from the book folder.

**Trust.** The cover file `design.py` and the Docker images named under `tools:` in `book.yaml`
run as code on your machine. Only run cover checks and builds on books you trust.

Every script has `--help`, finds
`book.yaml` by walking up from the working folder (`--config FILE` picks another,
`--set KEY=VALUE` overrides one value), and changes nothing in the book without `--fix`.

## Book settings

| Key in `book.yaml` | Default | Meaning |
|---|---|---|
| `book.title`, `book.subtitle`, `book.author` | | printed on the cover; never repeat them in the design |
| `cover.design` | `<publishing.cover>/design.py` | the design file |
| `cover.trim` | the book `format` | trim size, for example `6x9` |
| `cover.paper` | `bw-white` | `bw-white`, `bw-cream`, `color-premium`, `color-standard` |
| `book.pages` | counted in the print PDF | interior page count (the build-editions skill reads the same key for the KDP gutter; `auto` means count it) |
| `cover.book_pdf` | the final print PDF in `work.output`, else the newest print PDF there (the run names the one it used) | where to count pages |
| `cover.final` | `<publishing.cover>/final` | shipping files (`front.png`, `back.png`, `ebook.png`, `ebook.jpg`, `paperback-cover.pdf`) |
| `book.cover_front`, `book.cover_back`, `book.ebook_cover` | `front.png`, `back.png`, `ebook.png` in `cover.final`, when shipped | the images the build-editions skill binds into the editions; set them only to use other files |
| `cover.output` | `<work.output>/cover` | everything `make.py` renders |
| `cover.templates` | `<work.caches>/kdp-templates` | KDP template PNGs (third-party, keep out of git) |
| `cover.shelf_screenshots` | `<work.caches>/shelf-screenshots` | store grid screenshots for review |
| `cover.cmyk_limit` | `88` | highest allowed CMYK channel, in percent |
| `cover.icc` | none | CMYK profile for a real conversion (for example SWOP coated) |
| `cover.srgb_profile` | found on the system | sRGB profile embedded in the ebook JPEG |
| `tools.render_image` | none | a docker image with `rsvg-convert`, used only when neither `rsvg-convert` nor `cairosvg` is installed; it must be pinned to a version tag (not `latest`) or a digest, or it is not used |
| `sales_text.back_cover` | `<publishing.sales_text>/back-cover.md` | the back-cover text; the single source |

## Before the first cover

1. Write `publishing/cover/design.py`: a subclass of `CoverDesign` with at least `front(wrap)`
   (`references/design-file.md`, "The smallest design").
2. Write the back-cover text in `sales_text.back_cover` (the `prepare-sales-text` skill owns the words;
   the markdown it may use is in `references/design-file.md`, "The back-cover text"). Check how
   it is read: `python3 "$SCRIPTS/back-copy.py"`.
3. Make the width table of the back-cover font, so lines break where they really end:
   `python3 "$SCRIPTS/font-widths.py" --family '<font>' --italic <file> --fix`, then point
   `BODY_WIDTHS` at it.
4. The KDP paperback template for the trim, page count and paper is downloaded by `make.py`
   when it is missing; this step is only for getting it by hand. `python3 "$SCRIPTS/kdp-template.py"`
   shows the request and the target files, `--fix` downloads the PNG and PDF into
   `cover.templates` (a file already there with the same bytes is left alone). The script asks
   the same address the public KDP cover calculator page asks. That address is not a documented
   interface: when the answer changes, the script stops with exit 2 and prints how to download
   the template by hand (`references/kdp-print.md`, "The KDP template"). With no network it says
   `SKIPPED`.
5. Tools: `rsvg-convert` (librsvg) or `cairosvg` for SVG to PNG and PDF, ImageMagick for the
   JPEG, overlay and compare images, `pdfinfo` (poppler) to count pages, `fc-match`
   (fontconfig) for the font check. A script whose tool is missing says `SKIPPED` and why; a
   skipped step is not a passed step, so report it.

## Mode: make

```bash
python3 "$SCRIPTS/cover-size.py"            # spine and full size from pages, paper, trim
python3 "$SCRIPTS/make.py"                  # render everything into cover.output
python3 "$SCRIPTS/make.py" --pages 312      # after the page count changed
python3 "$SCRIPTS/make.py" --fix            # also copy the shipping files into cover.final
```

- The geometry is **derived** from page count, paper and trim (`references/kdp-print.md`). Make
  the cover again after every manuscript change that moves the page count, and never write a
  cover size into any document.
- Panels: `wrap` (print), `front`, `spine`, `back` (with bleed), `front-trim` and `back-trim`
  (bleed cut off in the vector file, for ebook and digital editions).
- Ebook: rendered from the trim SVG at 2560 px tall; PNG for the EPUB, JPEG (sRGB, quality 95,
  no chroma subsampling, flattened on white) for the KDP dashboard.
- Print: `paperback-cover-<pages>.pdf`, vector, fonts embedded by the renderer.
- `make.py` prints a `note` for every `layout-check.py` finding: back text past the safe area or
  in the barcode box, spine type wider than the spine. The default spine draws nothing when the
  book has 79 pages or fewer, because KDP prints no spine text on it.
- After the wrap PNG, `make.py` writes `png/wrap-overlay.png` (the KDP template over the art);
  a missing KDP template is downloaded into `cover.templates` first (`--no-download` turns this
  off; no network is a note, not a failure).
- Without `--fix`, `make.py` lists what it would ship. Ship only what the author has seen:
  run `compare.py` first and show the result.

## The cover checks, after every make

`make.py` already prints the layout notes and writes the overlay; the run-checks skill runs all
of these at once (`run-checks.py cover`). Run one by hand to see its full report.

```bash
python3 "$SCRIPTS/color-check.py"                          # color roles, contrast, CMYK
python3 "$SCRIPTS/color-check.py" --icc <cmyk-profile.icc> # real conversion, with and without BPC
python3 "$SCRIPTS/font-check.py"                           # every font the cover asks for is installed
python3 "$SCRIPTS/layout-check.py"                         # safe area, barcode box, spine text
python3 "$SCRIPTS/overlay.py"                              # art against the KDP template (--fix: overlay image)
```

- `color-check.py` finds every color constant in the design and its base class, changes it,
  renders again and looks at what moved, so a color constant used as type is always graded as
  type. Type colors written into the markup with no constant are graded too, under
  `untraced:<hex>`. Type is graded with WCAG 2.1 AA at its printed size (pixels at 300 dpi
  turned into points). Every color gets the naive CMYK figures; with a profile, a color over
  the limit in both black point modes is a defect, in only one mode an advisory for the printed
  proof. It also warns about tints so light they may not print.
- `color-check.py` and `font-check.py` do not need the page count. Before the first interior
  build they use a nominal page count and say so (`geometry-nominal`).
- `layout-check.py` measures every back-text line against the safe area and the KDP barcode box,
  and the spine type against the spine width. The spine length is an estimate from the body width
  table, so it is an advisory: look at the spine panel.
- `font-check.py` reads the rendered SVG and asks fontconfig for each family, weight and style.
  A missing font is replaced without an error when rendering, so a PNG is not proof.
- `overlay.py` picks the KDP template by page count, checks that art and template have the size
  the formula gives (1 px allowed), that trim and paper in the template name match the book;
  with `--fix` it also writes `wrap-overlay.png` (run-checks never passes it, so a check run
  writes nothing). The overlay is for looking; never upload it. With no template for
  the page count it says `SKIPPED` or `template-nearest` and names `kdp-template.py --fix`.
- All checks follow the plugin's check contract (`${CLAUDE_PLUGIN_ROOT}/lib/check_contract.md`):
  exit 0 clean, 1 defects, 2 the tool failed; `--format tsv|json` for machines.
- Print facts behind the checks: `references/kdp-print.md`. Color evidence:
  `references/color.md`.

## Mode: compare

```bash
python3 "$SCRIPTS/compare.py"                          # shipped front against the new front
python3 "$SCRIPTS/compare.py" old.png new.png          # any two images
python3 "$SCRIPTS/compare.py" --grid a.png b.png c.png --labels A B C
```

For two images it writes, in `<cover.output>/compare/<name>/`: `overlay.png` (the new cover with
the old one laid over it at half opacity, so every moved element shows twice), `side-by-side.png`,
`thumbnails-250.png`, `-180`, `-120` (true store sizes), and `difference.png` with the count of
pixels that differ. Before the first ship there is no old front: `compare.py` with no files then
writes the thumbnails of the new front alone and says `nothing-shipped-yet`. Show the author the
side-by-side and the thumbnails for every change; an unchanged pixel count proves a refactor
changed nothing.

For variants, make each one into its own `--out` folder from a scratch subclass of the design,
then put them in one `--grid`. Keep the grid, delete the rest (`references/design-file.md`,
"Trying variants").

## Mode: review

1. **Read the book's decisions first, the index only.**
   `python3 "${CLAUDE_PLUGIN_ROOT}/lib/decisions.py" index` shows one line per entry (the script
   finds the book's decisions file), and `decisions.py show ID` opens one entry; `python3 "${CLAUDE_PLUGIN_ROOT}/lib/decisions.py" policy` shows what a review may do for each
   status. A DECIDED item is never a finding: before reporting, run
   `python3 "${CLAUDE_PLUGIN_ROOT}/lib/decisions.py" match "<finding>"`, and when it matches a
   decided item, name the item and drop the finding. An OPEN "fix owed" item is checked against the
   cover as it is now (is the fix in yet?), not raised as new.
2. Make the cover (`make.py`), run all checks, and make thumbnails (`compare.py`). For a front
   review, the shelf screenshots in `cover.shelf_screenshots` are **required**; without them,
   stop and ask (`references/review-prompt.md`, "Context gate").
3. Run the seven lenses of `references/review-prompt.md`: category strategist, designer,
   typographer, colorist, UX and eye-tracking, front and back consistency, psychologist. **One
   cold subagent per lens**: it gets the images, the script output, the review prompt and its
   lens, and never the history of the design or earlier reviews. Run up to three at a time.
4. Collect the lenses into one report: two scores (full size and 180 px thumbnail), one section
   per lens, and the issues that cross lenses. Then the **claim check** (step 4 of the review
   prompt): every claim about the shelf or the colors is checked against a screenshot or a script
   output, and taken back openly if it cannot be. Then changes in priority order, what not to change, and a ranking of variants.
5. Read `references/review-lessons.md` before proposing any change.

Write the report into the run folder that this command makes,
`<work.runs>/<YYYY-MM-DD-HHMM>-design-cover-review/` (the newest three review runs are kept):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/run_folders.py" start design-cover review --fix
```

Put the report there, with one file per lens beside it. Two options:

- `--resume`: continue the newest review that stopped, in its folder
  (`run_folders.py latest design-cover review`); a lens whose file is complete is not run again.
- `--only-changed`: review only when the design file, the back-cover text or the rendered PNGs
  changed since the last review (`run_folders.py changed design-cover review <design file>
  <back-cover file> <cover.output>/png/*.png`); if nothing changed, say so and stop. End every
  review with `run_folders.py record <run folder> <the same files> --fix`.

Then every change the report proposes becomes one note, in the format of
`${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/note-format.md`, with
`**From:** design-cover review, <YYYY-MM-DD HH:MM>`. A note about the back-cover text goes to the
notes file named after the back-cover file. Every other cover note goes to `whole-book.md` and
names the panel. Get ids with
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/open-notes.py next-id <file>`.
The decisions the author makes are recorded when revise-from-notes answers the notes.

## Working rules

- **Draft, show, then apply.** Render a change into the work output, show it with
  `compare.py`, and ship with `--fix` only after the author approves. Never write into
  `cover.final` or the design file before that.
- **Minimal means minimal.** A request to move one element changes that element. Do not tidy the
  rest of the design in the same step.
- **Rewrite, do not patch a patch.** When a part of the design has had several fixes on top of
  each other, rewrite that part cleanly and prove with `compare.py` that the pixels are the same.
- **Decided items are not findings.** Never re-propose what the decisions file marks DECIDED, even
  as a small suggestion.
- **Truth over punch.** Every claim in a review, about the shelf, about color, about research,
  must survive a fact-check. Name the source; label a judgement as a judgement.
- **One source per text.** The title, subtitle and author come from `book.yaml`; the back-cover
  text from `sales_text.back_cover`. The design never holds its own copy. When the words change,
  make the cover again; the `prepare-sales-text` skill keeps the other selling texts in step.
- **Plain English on the cover too.** Short sentences a non-native reader follows; the
  `prepare-sales-text` skill reviews the words, this skill only checks that the artwork supports them.
- **Nothing third-party in git.** KDP templates and shelf screenshots stay in the work caches.

## Files

Scripts you run have a hyphen in the name (`make.py`, `cover-size.py`, `color-check.py`); files
with an underscore are parts the scripts and the design file import.

| File | Holds |
|---|---|
| `scripts/make.py` | render, convert, ship |
| `scripts/cover-size.py`, `scripts/cover_geometry.py` | prints the KDP geometry; the geometry itself |
| `scripts/cover_design.py` | `CoverDesign`, the base class a book design extends; default back and spine |
| `scripts/cover_wrap.py` | panels and the canvas |
| `scripts/back-copy.py`, `scripts/back_copy_text.py`, `scripts/back_layout.py` | showing, reading and typesetting the back-cover text |
| `scripts/text_width.py`, `scripts/font-widths.py` | font advance widths |
| `scripts/svg_parts.py` | small SVG helpers for design files |
| `scripts/color-check.py`, `font-check.py`, `layout-check.py`, `overlay.py`, `compare.py` | checks and comparisons |
| `scripts/kdp-template.py`, `scripts/kdp_download.py` | downloads the KDP template; the request, the answer and the zip |
| `scripts/kdp_overlay.py`, `scripts/cover_loader.py`, `scripts/cover_settings.py`, `scripts/cover_tools.py` | template choice and overlay; loading the design; cover settings from book.yaml; finding renderers |
| `scripts/layout_rules.py` | the safe area, barcode and spine rules behind `layout-check.py` |
| `scripts/self-check.py` | runs the fixture tests in `scripts/tests/` (no real book, no network) |
| `references/design-file.md` | how to write and change a design file; back-cover markdown |
| `references/kdp-print.md` | geometry, KDP print and ebook rules, CMYK, profiles, finish, proof |
| `references/color.md` | color conventions and the strength of the evidence |
| `references/typography.md` | cover typography rules learned from real defects |
| `references/review-prompt.md` | the seven-lens review brief |
| `references/review-lessons.md` | mistakes reviewers made, as rules |
