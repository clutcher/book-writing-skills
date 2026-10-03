# Part divider pages

Whether a book in parts should give each part its own divider page, what to do with a part that
holds a single chapter, and how the build renders a divider with a short overview.

## Publishing convention

- **Part dividers are an established but optional device**, justified by the value of a
  higher-level organisation, not by the chapter count: use them when a large conceptual,
  historical or structural logic suggests the division and readers benefit from it.
- **Layout.** The divider opens on a recto (right-hand page) with the part number and title, and
  may carry nothing, a few lines or several pages of text. The verso is usually blank and the next
  chapter opens recto. Part-title pages have no running heads (and a blind folio,
  [page-styles.md](page-styles.md)). An introduction before Part I needs no part of its own; a
  closing chapter after the last part should open recto so it does not look like part of it.
- **Ornament.** When chapter openers are ornamented, part openers use a similar, simpler ornament.
- **Thin parts.** There is no hard rule, but editors agree a part needs a stronger reason to exist
  than a chapter. A one-chapter part is acceptable when its weight justifies it, but it is not
  common and risks reading as padding (a divider, then at once one chapter).
- **Cost.** Each divider takes a leaf (recto plus blank verso): more pages and a wider spine.

## Why a boundary helps, and what kind

- **Event segmentation** (Zacks and colleagues): readers split continuous text into events, slow
  down at boundaries, and **remember information at boundaries better**. A part divider is a
  strong, explicit boundary.
- **Advance organisers** (Ausubel; a meta-analysis of 112 studies): an organiser helps both
  learning and retention, though not in every study, by preparing the frame the next material
  attaches to. **A bare title page is not an advance organiser; a short overview paragraph is.**
- **Signalling** (Lorch): titles, overviews and headings improve memory for the signalled content
  and help readers encode the text's organisation.

Both functions, boundary and organiser, come from a **short overview paragraph**, not from a bare
title page. A bare divider before a single chapter adds little; a 2-4 sentence overview can make
even a one-chapter part page earn its leaf.

## Choosing

| Option | When |
|--------|------|
| A. No dividers | the lowest cost; the table of contents and chapter openers carry the structure. Defensible when several parts hold one chapter. |
| B. Dividers, each with a short overview | strongest on the evidence. **Test each one-chapter part**: its overview must do real orienting work (say why this one chapter is its own movement). If any part fails, prefer A. |
| C. Dividers only on multi-chapter parts | gives an inconsistent contents hierarchy; usually worse than all or nothing |
| D. Restructure so one-chapter parts merge | a large structural change |

Record the choice in the book's `decisions.md`.

## How the build renders it

- `part_pages: true` (default) gives each `\part{...}` its own divider page;
  `--no-part-pages` / `part_pages: false` shows parts only in the table of contents.
- `part_overview: true` (default off; needs `part_pages`) changes `\part` so the ornament,
  "Part N" and the title sit near the top of a recto and the page does **not** end with the stock
  forced blank verso. The markdown paragraph that follows the `\part{...}` block then flows onto
  the same page; the next `\chapter` makes its own `\cleardoublepage`. `--no-part-overview`
  turns it off for one build. A book without the flag gets the stock `\part`, unchanged.
- Keep each part in its own manuscript file: the `\part{...}` raw block plus the overview
  paragraph ([manuscript-layout.md](manuscript-layout.md)).
- Caveat: with `--no-part-pages`, the overview paragraphs show inline before each part's first
  chapter.
- In the EPUB the divider becomes a numbered level-1 heading ("Part II: Title") and the overview a
  centred italic paragraph ([editions.md](editions.md)).

## Sources

- The Book Designer, "Parts of a Book" and "Chapter Openers and Part Openers"
- Chicago Manual of Style, 17th ed., parts of a publication
- Zacks et al., "Segmentation in the perception and memory of events"
- "Segmentation in Reading and Film Comprehension"
- Luiten et al., "A Meta-Analysis of the Effects of Advance Organizers on Learning and Retention"
- Lorch, "Text-signaling devices and their effects on reading and memory"
