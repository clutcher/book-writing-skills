# Print specifications and font choice

Background for choosing a trim, a body face and sizes. The build implements the margins and
leading ([typography-research.md](typography-research.md), [leading-model.md](leading-model.md));
this file is the evidence behind the choices a book makes. Paper, ink, bleed and cover finish
belong to the design-cover skill.

## 1. Choosing a body face: the method

Judge candidate faces on seven dimensions and weight them for the book: authority in the
book's field, intellectual weight, modern feel, a sense of tradition, a canonical "will endure"
feel, readability for long text (with tables, recipes or code where the book has them), and
broad appeal. Then check each claim against what publishers
actually use, not what blogs recommend.

**What publishers use.** A survey of 1,000 novels from major U.S. trade publishers over 20 years
ranked the most used faces: Sabon (91 books), Bembo (86), Adobe Garamond (75), Janson Text (51),
Granjon (48), Electra (43), Adobe Caslon (39), Simoncini Garamond (38), Minion (34), Garamond
#3 (34). Garamond-family faces dominate.

**Verdicts on common candidates:**

| Face | Verdict |
|------|---------|
| Sabon | The most used book face; Tschichold's 1967 Garamond revival; the house face of many trade books. Commercial licence. |
| Minion | A polished industry standard, in the top ten. Commercial (Adobe). |
| Cochineal | A free fork of Crimson extended for LaTeX; drawn in the Garamond/Bembo tradition with Tschichold and Slimbach as named inspirations. The best single free stand-in for both Sabon and Minion. SIL OFL. |
| Baskerville (BaskervilleF) | Strong pedigree and a reputation for credibility. Free versions exist. |
| EB Garamond | Classical, free (SIL OFL); small x-height, so it needs a larger point size ([leading-model.md](leading-model.md)). |
| Palatino (Domitian) | Warm, humanist; on Amazon's suggested list. Free. |
| Freight Text, Equity, Charter, Utopia | Respected, but none shows up in book-publishing surveys; better for magazines, legal work or manuals. |
| Latin Modern | Made for mathematical typesetting; almost absent from professional book publishing and widely criticised for body text (thin, light). It reads as "a LaTeX document". It is the build's default because it ships with TeX and needs no extra font install; choose another face for a final book. |

**Free-font ranking for a final book interior:** Cochineal, BaskervilleF, EB Garamond,
Domitian. Latin Modern, the default, comes last.

## 2. How to measure a published book's typography

Books rarely print a colophon, and copyright pages name the printer, not the typeface. Measure
instead:

- Take the **publisher's own sample PDF**; read the embedded fonts with `pdffonts`, the point size
  from the text size operator and the leading from the baseline-to-baseline pitch on text-dense
  body pages (for example with `pdfplumber`). Round to the nearest standard value.
- **Pirated reflows are not evidence**: they are re-typeset, usually in Times New Roman.
- **Samples can be composite**: some splice real typeset front matter with a manuscript-style
  reflow. Measure only the typeset pages.
- **Ebook-only or self-published titles** often expose only a converter's substitute fonts, which
  say nothing about the print interior; report them as unknown.

Measure the comparable books of your own field before you choose: a history, a cookery and a
popular-science book can differ. Then check the result against the traditional ranges of
section 4, which hold for book text in general. A face with a large x-height reads well at its
nominal size with modest leading; a face with a smaller x-height needs a larger size or more
leading, so its leading can sit near the top of that band.

## 3. Trim sizes

Trim follows the field. Most trade non-fiction (history, memoir, popular science, self-help)
uses a standard size such as 5.5 x 8.5 or 6 x 9. Books with many pictures, tables or recipes,
such as cookery and garden books or workbooks, often use a large size. To choose, measure the
trim of a few comparable books on your shelf (width and height in inches, and the ratio
width/height), then take the nearest KDP size.

**KDP standard sizes:** 5 x 8, 5.06 x 7.81, 5.25 x 8, 5.5 x 8.5, 6 x 9 (the default and most
common). **Large sizes** (higher print cost): 6.14 x 9.21, 6.69 x 9.61, 7 x 10, 7.44 x 9.69,
7.5 x 9.25, 8 x 10, 8.25 x 6, 8.25 x 8.25, 8.5 x 8.5, 8.5 x 11, 8.27 x 11.69. Custom sizes:
width 4-8.5", height 6-11.69"; a large-trim surcharge applies above 6.12" wide or 9" high.
Paperbacks run 24-828 pages.

A book that wants a shape KDP does not offer takes the nearest listed size, or a custom size
inside the limits above.

## 4. Traditional specifications

| Element | Specification |
|---------|---------------|
| Body size | 10-11pt for a normal x-height; larger for a small one |
| Leading | 120-145% of the size, by x-height and measure |
| Line length | 45-75 characters (about 10-12 words), ~66 ideal |
| Code face | Source Code Pro, Consolas, Fira Code or Inconsolata; 9-10pt; leading 110-115% |
| Chapter title | 18-24pt |
| Section heading | 14-16pt |
| Subsection | 12-14pt |
| First paragraph | no indent |
| Other paragraphs | indent 0.2-0.25" (about 1em), never with the Tab key |
| Paragraph spacing | first-line indent **or** a blank line, never both; books use the indent |
| Justification | full, with hyphenation |
| Hyphenation | at most 2 hyphenated lines in a row; never the last word of a paragraph; avoid proper nouns |
| Widows / orphans | keep 2-3 lines together |

**Widow**: the last line of a paragraph alone at the top of a page. **Orphan**: the first line
alone at the bottom. **Runt**: a single short word ending a paragraph. Fix with tracking
(+/-5% is invisible), word spacing, a small rewrite, or the software's controls.

**Chapter openings:** drop cap, small caps for the first words, no indent, or a run-in heading.

## 5. KDP requirements

- **Inside margin by page count:** KDP's table is in
  [typography-research.md](typography-research.md#kdp-gutter-floor). Outside, top and bottom at
  least 0.25". Mirror the margins so the gutter alternates.
- **Fonts must be embedded.** XeLaTeX and LuaLaTeX with fontspec embed them. Check with
  `pdffonts` (every row "emb yes") or the Fonts tab of a PDF viewer.
- **Suggested faces:** Georgia, Times New Roman, Garamond, Palatino; body 10-12pt.
- **Files:** PDF preferred; images at least 300 DPI; lines at least 0.75pt; at most 650 MB; no
  crop or trim marks, no comments.

## 6. LaTeX notes

- Classes: `book` (what the build uses), `memoir` (highly configurable), `tufte-book` (side
  notes).
- Never add a `bindingoffset` on top of KDP's inside margin; it already includes the binding.
- `\setstretch{N}` multiplies the class default baselineskip, not the point size
  ([leading-model.md](leading-model.md)).

## 7. Common mistakes

| Mistake | Instead |
|---------|---------|
| Times Roman for body text | a book face (Garamond family, Sabon, Minion, Baskerville) |
| Two spaces after a full stop | one |
| Default office fonts | book fonts |
| Tab key for indents | paragraph settings |
| Indent and space between paragraphs | one of them |
| Ignoring widows and orphans | the software's controls |
| Lines longer than 75 characters | adjust margins or size |
| Leading outside 120-145% | x-height and measure decide within the band |
| Adding leading to fix small-looking text | raise the point size |
| Reading `\setstretch{N}` as N x point size | N x the class default |
| Fonts not embedded | embed every font |
| Gutter below KDP's table | follow the table by page count |
| Images below 300 DPI | 300+ DPI |
| Crop or trim marks in the upload | remove them |

## 8. Font licences

| Face | Licence |
|------|---------|
| Sabon | commercial |
| Minion | commercial (Adobe) |
| Cochineal, EB Garamond, Crimson Pro, Cormorant Garamond | SIL OFL, free |
| BaskervilleF, Domitian | free |
| Latin Modern | GUST Font License, free |
| Source Code Pro, JetBrains Mono | SIL OFL, free |
| Charter | free |

## 9. Quick specification for a non-fiction book

| Element | Specification |
|---------|---------------|
| Trim | 5.5 x 8.5 or 6 x 9 (economical, common in trade non-fiction); a large size for a book with many pictures or tables |
| Body face | a Garamond-family face or Cochineal |
| Body size | 10-11pt for a normal x-height; about 12pt for a small one |
| Leading | computed ([leading-model.md](leading-model.md)) |
| Code face (if the book has code) | Source Code Pro, 9-10pt |
| Indent / first paragraph / paragraph space | 1em / none / 0 |
| Margins | computed ([typography-research.md](typography-research.md)) |
| Justification | full, hyphenated, at most 2 hyphens in a row |
| Chapter title / section heading | 18-24pt / 14-16pt |
