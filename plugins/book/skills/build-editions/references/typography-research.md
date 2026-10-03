# Book typography: margins and headings

The rules behind the page margins and the heading styles, with the evidence for each. Read it
before changing the margin formula or adding a heading style.

These rules drive:
- the margin formula and the KDP gutter floor in `scripts/page-settings.sh` (`compute_geometry`)
- the section and subsection style blocks in `assets/templates/book-template.tex`
- the chapter style blocks (`canonical`, `technical`, and the others)

---

## 1. Two kinds of evidence

**What typographers recommend.** Bringhurst's *Elements of Typographic Style*, the classical
canons of Van de Graaf and Tschichold, and the self-publishing guides built on them
(TheBookDesigner, Reedsy, Wikibooks Basic Book Design, KDP's own help). The classical canon puts
the margins in the order inner : top : outer : bottom = 1 : 1 : 2 : 2 on a spread.

**What published books do.** Measure a handful of printed books on the shelf where the new book
will stand: trade non-fiction, professional books, academic monographs. Modern trade books run
a little looser on the top and outer margins than the canon, and a little less heavy at the
bottom.

**Rule: calibrate to what published books do, and use the canon as a check.** A new book sits
next to existing books, and looking like them is the goal. The numbers must still satisfy the
canon's two inequalities, `inner > outer` and `bottom > top`. A book in any field can check the
pattern against a few comparable books of its own shelf.

---

## 2. Margins

### The formula

For trim WxH (in inches) and page count P:

```
inner  = max(KDP_gutter(P), 0.143 * W)
outer  = 0.106 * W
top    = 0.076 * H
bottom = 0.0923 * H
```

Inner is 14.3% of the width and never below KDP's floor; outer is 10.6% of the width; top is
7.6% of the height; bottom is 9.23% of the height, so bottom stays above top.

### KDP gutter floor

This is the one copy of KDP's table in the plugin; other files link here. KDP publishes minimum
inside margins that grow with the page count. The build uses them as a hard floor on `inner`:

| Page count | Min inside |
|---|---|
| 24-150 | 0.375" |
| 151-300 | 0.500" |
| 301-500 | 0.625" |
| 501-700 | 0.750" |
| 701-828 | 0.875" |

Outside, top and bottom must each be at least 0.25". KDP's "inside margin" already includes the
binding allowance: do not add a separate `bindingoffset` in LaTeX `geometry` on top of it.

### What the formula gives (250 pages)

| Trim | inner | outer | top | bottom | text block |
|---|---|---|---|---|---|
| 5×8     | 0.715 | 0.530 | 0.608 | 0.738 | 3.755 × 6.654 |
| 5.5×8.5 | 0.787 | 0.583 | 0.646 | 0.785 | 4.130 × 7.069 |
| 6×9     | 0.858 | 0.636 | 0.684 | 0.831 | 4.506 × 7.485 |
| 6.14×9.21 | 0.878 | 0.651 | 0.700 | 0.850 | 4.611 × 7.660 |
| 6.5×9.25  | 0.930 | 0.689 | 0.703 | 0.854 | 4.881 × 7.693 |
| 7×10    | 1.001 | 0.742 | 0.760 | 0.923 | 5.257 × 8.317 |
| 7.5×9.25 | 1.073 | 0.795 | 0.703 | 0.854 | 5.633 × 7.693 |
| 8×10    | 1.144 | 0.848 | 0.760 | 0.923 | 6.008 × 8.317 |

Every row keeps `inner > outer` and `bottom > top`, and every row is above KDP's minimums. On a
6.14×9.21 page the canon alone would give a tighter top (about 0.625") and a heavier bottom
(about 0.875"); the formula gives 0.70" and 0.85", as modern books do.

### Gutter words: do not mix them up

| Term | Meaning |
|---|---|
| **Inner / inside / spine margin** | Whitespace between text and spine on a single page. |
| **Gutter** | Two senses: (a) combined whitespace at the spine across the spread; (b) the *binding allowance* added to the inside margin. KDP and MS Word use sense (b). |
| **Binding offset** | LaTeX `geometry` package's term for the binding allowance. The same as KDP's "gutter" sense (b). |

KDP's inside-margin minimums **already include** the binding allowance. Do not count it twice.
In LaTeX:

```
\usepackage[inner=0.875in, outer=0.65in, ...]{geometry}
```

and never:

```
\usepackage[inner=0.875in, bindingoffset=0.125in, ...]{geometry}
```

---

## 3. Heading typography

### Chapter openings

Three patterns cover most printed non-fiction:

| Pattern | How common |
|---|---|
| Centered serif title in the body family, small "CHAPTER N" above, sunk 25-33% down the page, no rule, no drop cap | the most common, especially in professional books and academic monographs |
| Big display numeral (60-120pt), then the title, then a 2-3 line drop cap | common in popular trade non-fiction |
| A quiet roman number or "ONE" in small caps, then the title, then the body at once | the least common |

True for all three:
- The title sits 25-33% down the page, almost never at the top.
- Drop folio: the page number centered at the bottom, no running head on the opening page.
- Trade non-fiction starts chapters on a right-hand page; professional books often start them on
  either side.
- The title uses the body family or a related serif; sans-serif chapter titles are a minority.

### Section headings (`##`)

**Most common:** bold serif in the body family, about 1.3-1.5x the body size, flush left, more
space above than below, **no rule**.

**Less common:** bold sans-serif (Helvetica, Myriad, Frutiger) over a serif body. This is the
house style of many manual and reference publishers.

**Rare:** small caps or italic display, mostly in literary non-fiction and university-press
monographs.

Professional books number sections (3.2, 4.1); trade non-fiction does not.

Rule: more space above a heading than below it. The heading belongs to the text it introduces
(Bringhurst).

### Subsection headings (`###`)

Two patterns, about equally common:

| Pattern | Detail |
|---|---|
| Display | The section family, smaller (about 1.1-1.2x body), bold or **bold italic**, flush left, on its own line |
| Run-in | An italic phrase at the start of a paragraph, ending in a full stop or an em space; the body goes on in the same line |

Rule: no sans-serif at the subsection level over a serif body. Sans-serif belongs to the chapter
or section level, not deeper.

Numbering rarely goes three deep (3.1.1) outside academic textbooks.

### Why bold italic at the subsection level

In an 11pt serif body, a `\large\bfseries` subsection heading is only about 12pt, hard to tell
from a bold word in the running text. Italic as well removes the doubt: a heading is bold *and*
italic, while an emphasized word in the body is usually one or the other. Many printed books
with display subsections do this, and the `technical` style applies it.

---

## 4. The style options

### `--section-style` choices

| Style | Pattern | When to use |
|---|---|---|
| `technical` | The most common pattern: bold serif, no rule, more space above than below, **bold italic subsection** | Default for any serif non-fiction book with sections: how-to, history, popular science, professional books. |
| `scholarly` | A bigger size jump (LARGE), thin rule under the section | Academic monograph, university-press look. |
| `literary` | Small caps section and run-in italic subsection | Literary non-fiction, essay collections. Quiet pages. |
| `editorial` | Sans-serif heads and rules over a serif body | Manuals, reference books, magazines. The minority sans-over-serif look. |
| `classic` | LaTeX defaults, plain bold | Old builds only. The `\large\bfseries` subsection blends into bold body words, which `technical` solves. |

Default is `technical`. Override per build with `--section-style` or per book with
`section_style` in `book.yaml`.

### `--chapter-style` choices

| Style | Maps to |
|---|---|
| `canonical` | Centered ornament, small caps "CHAPTER N", serif title. The most common pattern. |
| `classic` | LaTeX default "Chapter N" header. |
| `technical` | Big number and a horizontal rule. |
| `bold` | Oversized gray number, small caps title. |
| `elegant` | Left-aligned italic "Chapter N", rule under the title. |

---

## 5. Why the formula is this way

- **Calibrated to published books, not to the classical canon.** A new book sits on a shelf
  beside published books, and modern practice has moved away from the canon.
- **Bottom coefficient 0.0923** gives 0.850" at a 9.21" page height, the bottom margin of
  modern trade books at that trim.
- **Bold italic subsections in `technical`.** Bold alone at `\large` is too close to a bold word
  in the body; italic tells them apart.
- **`technical` is the default section style.** Plain bold serif with no rule is more common
  than a rule under the section.
- **The KDP gutter is a floor on `inner`, not a `bindingoffset`.** KDP's table already includes
  the binding allowance.
- **One formula, not a case per trim.** Adding a trim size is one line (its dimensions); margins
  are derived, never hand-tuned.
- **Two passes for the page count.** The inside margin depends on the page count through the KDP
  floor, and the page count depends on the margins, so the build runs again only when the count
  crosses a KDP gutter band.

---

## Sources

- Amazon KDP. "Set Trim Size, Bleed, and Margins." <https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6>
- Amazon KDP. "Paperback Submission Guidelines." <https://kdp.amazon.com/en_US/help/topic/G201857950>
- Joel Friedlander (TheBookDesigner). "Book Layouts and Page Margins." <https://www.thebookdesigner.com/book-layouts-page-margins/>
- Joel Friedlander (TheBookDesigner). "Book Chapters and Subheads." <https://www.thebookdesigner.com/book-chapters-and-subheads/>
- Reedsy. "Book Layout Guide." <https://blog.reedsy.com/book-layout/>
- Kindlepreneur. "Book Gutter: Definition and How to Format Your Margins." <https://kindlepreneur.com/book-gutter/>
- Wikibooks. "Basic Book Design / Margins." <https://en.wikibooks.org/wiki/Basic_Book_Design/Margins>
- Wikipedia. "Canons of page construction (Van de Graaf, Tschichold)." <https://en.wikipedia.org/wiki/Canons_of_page_construction>
- Wikipedia. "The Elements of Typographic Style (Bringhurst overview)." <https://en.wikipedia.org/wiki/The_Elements_of_Typographic_Style>
- Inkwell.ie. "Bringhurst typography summary." <https://www.inkwell.ie/typography/bringhurst.html>
- Foglio Print. "Jan Tschichold's Book Design Rules." <https://www.foglioprint.com/blog/jan-tschicholds-timeless-rules-what-modern-self-publishers-can-learn-from-the-father-of-book-design>
- Retinart. "The Secret Law of Page Harmony." <https://retinart.net/graphic-design/secret-law-of-page-harmony/>
- Butterick, Matthew. *Practical Typography* -- "Headings." <https://practicaltypography.com/headings.html>
- LaTeX `geometry` package documentation. <https://texdoc.org/serve/geometry.pdf/0>
- Freya Larsen. "How to Set Margins for KDP Paperbacks." <https://www.freyalarsen.com/2021/01/set-margins-KDP-paperbacks.html>
- Clear Sight Books. "Tips for Creating Effective Headings." <https://clearsightbooks.com/tips-creating-effective-headings/>
