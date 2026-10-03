# Page styles, typography and fonts

All of this lives in `assets/templates/book-template.tex` and is chosen with the settings in
[settings.md](settings.md).

## Folios (page numbers)

The default follows trade and academic convention (Chicago Manual of Style 1.5-1.7):

| Page | Treatment |
|------|-----------|
| Blank versos added so a chapter or part opens on the right | **Blind**: counted, nothing printed |
| Half title, title, copyright, dedication, epigraph | **Blind** |
| Part-title pages and their versos | **Blind** |
| Chapter-opening pages | **Drop folio**: number at the foot |
| Ordinary text pages | Normal folio |

A blind folio still counts; nothing at all prints on it (no number, ornament or running head).
`all_page_folios: true` (or `--all-page-folios`) prints a number on every page; chapter openings
keep their drop folio either way. The choice does not change the page count, so a spine width
computed from the interior stays right.

Blank pages use a named `blankpage` fancyhdr style, and so does the part-divider page:
`\thispagestyle{empty}`, which `\cleardoublepage` asks for on its blank, does not remove the
footer ornament and number.

## Page layout

| Option | Use | Features |
|--------|-----|----------|
| `--twoside` (default) | print | alternating margins, numbers on the outer edge, chapters open on the right |
| `--oneside` | screen | same margins on every page, simpler headers |

## Body text

| Setting | Value | Why |
|---------|-------|-----|
| Font size | `font_size`, default 11pt | For a face with a small x-height the point size is the lever for apparent size, not leading ([leading-model.md](leading-model.md)) |
| Leading | computed by `compute-leading.py` | from the font x-height and the text width; `--leading N` overrides; `\setstretch{1.05}` when the helper cannot run. N multiplies the class default baselineskip (13.6pt at 11pt, 14.5pt at 12pt), **not** the point size |
| Half-point sizes | 10.5pt, 11.5pt | the `book` class accepts only 10/11/12pt, so the nearest one goes to `\documentclass` and the `fontsize` package sets the real size (default baselineskip 1.2 x size) |
| Paragraphs | first-line indent 1.5em, no space between | book convention; never both |
| First paragraph after a heading | no indent | book convention |
| Numbers | lining | aligned numerals |
| Microtypography | on | even text colour |
| Widows and orphans | penalties 10000 | no single lines at a page top or bottom |
| Justification | full, with `\emergencystretch=3em` | avoids overfull lines |

**Proportional headings** (`heading_scale: proportional`) redefine `\small` to `\Huge` as fixed
multiples of the body size (the 11pt-class ratios: chapter 1.885x, section 1.309x, subsection
1.091x), so heading ratios stay the same at every body size. Without it, the `fontsize` package's
steeper ladder makes headings noticeably larger at a half-point body size. The body size itself is
not touched.

## Code

| Setting | Value | Why |
|---------|-------|-----|
| Code font | Source Code Pro | common, clear programming face |
| Inline code | `inline_code_scale` x body (default 1.0) | x-height matched to the body (`MatchLowercase`), optionally a little smaller |
| Code blocks | `code_scale` x body (default 0.85) | block size and block leading both derive from the body, so they follow both the size and the leading |

When inline code is scaled, the block font ratio becomes `code_scale / inline_code_scale`, so the
block x-height stays at `code_scale` x body. The shrink is on the block environment, not on
`\setmonofont`, so it touches blocks only.

## Other template behaviour

- **`\langtext{language}{text}`** prints the text as it is. It exists for the EPUB, where it
  becomes a `lang` span ([editions.md](editions.md)). It is not babel's `\foreignlanguage`,
  which needs that language installed in TeX Live.
- **Hyphenation language** comes from `hyphenation_language` (a babel name, default `english`).
  The language must be available in the TeX Live volume.
- **Ornament symbols** use the `wasy10` font directly through a legacy font encoding: `wasysym`
  maps its symbols to Unicode, and the book fonts under XeLaTeX have no glyphs there.
- **Strikethrough** (`~~text~~` becomes `\st{...}`) needs `soul`, which is always loaded, so a
  review copy can show removed text struck through without a `--changes-since` copy.
- **Symbols soul would drop.** `soul` re-typesets highlighted text through an 8-bit fallback
  font. The template registers `\ldots` and the smart-punctuation macros with `soul`, or the
  ellipsis and closing quotes vanish with only a log warning ([changes-since.md](changes-since.md)).
- **Contents lines** for parts read "Part I  Title", and the whole contents line is a link,
  page number included.
- **URLs** may break at any character.
- **Tables** get a dummy `none` counter that pandoc's unnumbered tables need.

## Fonts

All fonts are free for commercial use and are installed on first use into the TeX Live volume.

| Option | Font | Character | Suits |
|--------|------|-----------|-------|
| `cochineal` | Cochineal | readable, warm | how-to and reference books, foundational texts (free Minion/Sabon alternative) |
| `garamond` | EB Garamond | classical, elegant | literary and historical texts. Its italic `h` has a looped descender faithful to the 1592 specimen, which some readers see as `b` |
| `cormorant-garamond` | Cormorant Garamond | refined modern Garamond | elegant feel with a conventional italic `h`; sharper contrast |
| `crimson-pro` | Crimson Pro | Garamond-inspired book face | long-form interiors; conventional italic |
| `baskerville` | BaskervilleF | intellectual, refined | professional and academic |
| `palatino` | Domitian | warm, humanist | general non-fiction |
| `latin-modern` | Latin Modern Roman | neutral | the build's default because it ships with TeX; reads as a LaTeX document, so choose another face for a final book ([print-specs.md](print-specs.md)) |

To keep a Garamond roman but use a conventional italic `h`, set `italic_font: crimson-pro`
(`--italic-font crimson-pro`): the roman stays EB Garamond, italic and bold italic come from
Crimson Pro through fontspec's `ItalicFont`. Cormorant Garamond has no bold italic in TeX Live,
so its semibold italic is used.

`heading_font` may be `match-body`, a sans (`source-sans`, `gyre-heros`, `latin-modern-sans`) or
any body font.

```bash
build-book.sh --font garamond --italic-font crimson-pro
```

## Chapter styles (`chapter_style`)

| Style | Look | Suits |
|-------|------|-------|
| `canonical` | centred ornament, small caps "CHAPTER N", centred title (default) | foundational, formal |
| `classic` | LaTeX's "Chapter N" and title | general |
| `technical` | large number, rule, title below | how-to and reference books |
| `bold` | oversized grey number, small caps title | modern |
| `elegant` | left-aligned italic "Chapter N", rule under the title | quiet, refined |

The canonical ornament sits in the heading's "before" code, not its label, so it shows even with
section numbering off.

## Section styles (`section_style`)

Independent of the chapter style.

| Style | Look | Suits |
|-------|------|-------|
| `technical` | bold serif in the body family, modest size steps, no rule, more space above; subsections bold italic (default) | most non-fiction with sections, the most common pattern |
| `scholarly` | serif bold, larger step, thin rule under sections | academic monographs |
| `literary` | spaced small caps sections, run-in italic subsections | essays, trade non-fiction |
| `editorial` | sans headings over serif body, with rules | manuals, practitioner books |
| `classic` | plain bold | older builds |

Each style changes two of Bringhurst's variables per level (size, weight, family, small caps,
space), not all of them. Why subsections are bold italic: [typography-research.md](typography-research.md).

## Ornaments (`ornament`, canonical style)

`hexagon` (default), `varhexagon` (vertical hexagon), `star`, `sun`, `square`, `fleuron`
(classical leaf). Part divider pages use the same ornament.

## Quote styles (`quote_style`)

| Style | Look |
|-------|------|
| `italic` | italic, 3em indent (default) |
| `plain` | 3em indent only |
| `small` | smaller type, 3em indent (Chicago) |
| `border` | left rule the full height of the quote, 3em indent |
| `dash` | em dash before, 3em indent |
| `guillemet` | » before, 3em indent |
| `quote` | opening quote mark, 3em indent |

## Page number styles

`page_style`: `header` (default; two-sided puts the number on the outer edge and the chapter on
the inner) or `footer` (centred number, clean top). With `footer`, `page_ornament` adds a pair of
ornaments around the number: `spiral-straight` and `spiral-curly` (golden spirals),
`wasy-hexagon`, `wasy-verhexagon`, `wasy-star`, `wasy-sun`, `adforn-fleuron`, `adforn-leaf`,
`adforn-vine`. `page_ornament_size`: `small` (0.10), `medium` (0.12, default), `large` (0.15).

```bash
build-book.sh --page-style footer --page-ornament spiral-curly --page-ornament-size small
```

## Drafts and covers in the template

- Draft mode: a diagonal DRAFT watermark and a copyright notice along the right edge of every
  page, both drawn at shipout; the reviewer's name when given.
- The digital edition binds `cover_front` full-bleed as the first page and `cover_back` as the
  last, with a tikz overlay, so no geometry changes are needed.
