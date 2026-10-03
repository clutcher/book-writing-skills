# The design file

The cover is code. One Python file in the book, `cover.design` in `book.yaml` (usually
`publishing/cover/design.py`), holds the artwork. The skill holds everything else: the KDP geometry, the
panel layout, the back-cover typesetting, the spine, the conversion to PNG, JPEG and PDF, and
the checks.

```
design.py  ->  SVG (one per panel)  ->  rsvg-convert  ->  PNG, ebook PNG + JPEG, print PDF
```

Nothing is drawn by hand and nothing is edited in the SVG. To change the cover, change the
design file and make it again.

## The smallest design

```python
from cover_design import CoverDesign
from svg_parts import rect


class MyCover(CoverDesign):

    TITLE_COLOR = '#1A2030'
    TITLE_SIZE = 140

    def front(self, wrap):
        width = wrap.front_panel_width
        svg = rect(0, 0, width, wrap.height, self.BACKGROUND)
        svg += self.place_text(width / 2, wrap.height * 0.45, self.book.title, self.DISPLAY_FONT,
                               self.TITLE_SIZE, self.TITLE_COLOR, anchor='middle')
        return svg
```

This design uses the base class fonts. Name a real font family with a generic fallback, as in
`DISPLAY_FONT = 'DejaVu Serif, serif'`, and use only weights the family has: `font-check.py`
reports a font named only as `serif` or `sans-serif`, and a weight the font does not have. The
starter design that `/book:init new` writes does this.

Draw text with `self.place_text`, not with `text` from `svg_parts`: `place_text` records the
text's box, so `layout-check.py` can say when a title runs past the safe area. Text drawn with
plain `text` is invisible to the check. A title too long for one line at `TITLE_SIZE` gets a
smaller size or a second `place_text` line.

`make.py` puts the skill's `scripts/` folder on the import path before it loads the file, so
`from cover_design import CoverDesign` works. The file must define exactly one subclass of
`CoverDesign`, or name the one to use with `DESIGN = MyCover`.

## What the design can draw

| Method | Draws | Coordinates | Default |
|---|---|---|---|
| `front(wrap)` | the front panel | the front panel's own: `0..wrap.front_panel_width`, `0..wrap.height` | none, required |
| `across(wrap)` | artwork that runs over back and spine | the whole wrap | nothing |
| `back(wrap)` | the back panel | the whole wrap | title, subtitle, then the back-cover text |
| `spine(wrap)` | the spine | the whole wrap | title and author, turned 90 degrees |

Each method returns SVG markup as a string. The engine puts them together:

| Panel | Made of | Used for |
|---|---|---|
| `wrap` | across + back + spine + front | the print PDF and the KDP template check |
| `back`, `spine`, `front` | one part, with bleed | looking at one part |
| `front-trim` | front, bleed cut off | the ebook cover, the digital book, the store image |
| `back-trim` | across + back, bleed cut off | the digital book |

The trim panels are cut from the vector SVG with a `viewBox`, never by cropping a PNG. Cropping
a picture would copy the bleed and trim sizes into a second place where they can drift.

The front panel stands alone: `across` is not drawn on `front` or `front-trim`, so the ebook cover
is the front and nothing else. If the across artwork enters the front panel, make it meet the
front artwork smoothly, because the two are only seen together on the printed wrap.

## Placing text: `place_text` and `place_back_copy`

`layout-check.py` can only measure text it knows about. So a design that draws its own text calls
the two helpers of `CoverDesign` instead of writing `<text>` markup, and every text box is
recorded for the part being drawn:

| Helper | Draws | Returns |
|---|---|---|
| `self.place_text(x, y, content, font_family, font_size, fill, anchor='start', weight=500, style='normal', letter_spacing=0, opacity=1.0, turn=0)` | one line of text at baseline `y`; `turn=90` turns it about `(x, y)`, as on a spine | the SVG markup |
| `self.place_back_copy(left, width, top)` | the back-cover text, typeset as the default back does it | the SVG markup and the y where it ends |

The box is an estimate from the body width table (`BODY_WIDTHS`), with the ascent and descent the
back typesetter uses. The check then tests every recorded box:

| Part | Check |
|---|---|
| `back` | inside the back safe area and out of the barcode box |
| `spine` | inside the safe area from top to bottom (an advisory, because the length is estimated); the font size against the spine width, as for any spine text |
| `front` | inside the safe area of the front trim, in front panel coordinates |
| `across` | not checked: put text in `back`, `spine` or `front` |

The default `back()` and `spine()` already use the recorded boxes. Text written as raw markup, for
example with `svg_parts.text`, still renders, but the layout check cannot see it.

```python
class MyCover(CoverDesign):

    def back(self, wrap):
        left = wrap.back_trim_x + wrap.inches(0.75)
        width = wrap.trim_width - 2 * wrap.inches(0.75)
        title_y = wrap.back_trim_y + 360
        svg = self.place_text(left, title_y, self.book.title, self.DISPLAY_FONT, 72,
                              self.TITLE_COLOR)
        body, _end = self.place_back_copy(left, width, title_y + 120)
        return svg + body

    def spine(self, wrap):
        if not wrap.size.spine_text_allowed:
            return ''
        centre = wrap.spine_x + wrap.spine_width / 2
        return self.place_text(centre, wrap.height * 0.4, self.book.title.upper(),
                               self.DISPLAY_FONT, 40, self.TITLE_COLOR, anchor='middle',
                               turn=90)
```

Gradients and other `<defs>` need an `id` that is different in every part: `across` and `front`
end up in one SVG file, and two gradients with the same `id` draw the same one twice.

## What `wrap` gives the design

All sizes are pixels at 300 dpi, derived from the page count, paper and trim (see
`kdp-print.md`). Never write one of these numbers into the design as a constant: the spine moves
with every manuscript edit that changes the page count.

| Name | Meaning |
|---|---|
| `wrap.width`, `wrap.height` | the whole canvas, bleed included |
| `wrap.bleed` | bleed, 0.125 in |
| `wrap.trim_width`, `wrap.trim_height` | one panel without bleed |
| `wrap.spine_width`, `wrap.spine_x` | the spine and where it starts |
| `wrap.front_x`, `wrap.front_panel_width` | where the front starts; its width is trim plus the outer bleed |
| `wrap.back_trim_x`, `wrap.back_trim_y` | top left corner of the back panel's trim area |
| `wrap.safe` | the 0.375 in safe margin |
| `wrap.inches(value)` | inches to pixels |
| `wrap.size.page_count`, `wrap.size.paper` | what the geometry came from |

The front panel carries its bleed on the **right** (outer) edge and the back panel on the
**left**. So a right-hand margin on the front is measured from `wrap.front_panel_width -
wrap.bleed`, not from the panel width, or it is 38 px too wide on the trimmed ebook cover.

## What the design reads from the book

`self.book` holds `title`, `subtitle`, `author`, `title_words`, `author_words`, `back_copy` (the
parsed back-cover text) and `folder` (the folder of the design file). They come from
`book.yaml`, so the design never repeats the title or the back-cover text. Book-specific
artwork, colors, sizes and positions belong in the design file.

## Settings the design can change

Colors: `BACKGROUND`, `TITLE_COLOR`, `SUBTITLE_COLOR`, `AUTHOR_COLOR`, `BODY_COLOR` (the back
text), `ACCENT_COLOR` (back heading and bullet marks). `BODY_COLOR` does not follow
`TITLE_COLOR`: when a design changes the title color for a dark background, it sets
`BODY_COLOR` too. Fonts: `DISPLAY_FONT`, `DISPLAY_ITALIC_FONT`, `BODY_FONT`,
`BODY_ITALIC_FONT` as CSS font-family lists. `AUTHOR_SEPARATOR` puts a mark such as a middle dot
between the words of the author name on the spine; `svg_parts.spaced_name` does the same on the
front.

Back panel: every `BACK_*` value in `cover_design.py` (margins, sizes, gaps, bullet size, narrow
width, bold lead-ins, widow and runt rules). The back text is always ragged-right. Spine: every `SPINE_*` value
(position as a fraction of the height, size, weight, tracking, word gap, baseline). The default
spine draws nothing when the book is too thin for spine text.

`color-check.py` finds every upper-case constant that holds a color (a hex string such as
`'#1A2030'`, or an `(r, g, b)` tuple when the constant name has `COLOR` in it), in the design and
in its base classes, and names its role. Type colors written straight into the markup, with no
constant, are still graded for contrast, under the key `untraced:<hex>`; give them a constant so
the report can name them.

`layout-check.py` checks where the text landed: every back-text line inside the safe area and out
of the barcode box, spine type that fits the spine, and every text placed with `place_text` inside
the safe area of its part. `make.py` prints the same findings as notes.

## The back-cover text

The back panel reads `sales_text.back_cover`, a markdown file. It is the single source: the store
description, the ebook description and the cover must never hold their own copy of it.

| Markdown | On the cover |
|---|---|
| a paragraph | body text, full width |
| `**bold**`, `*italic*` inside a paragraph | bold or italic words; an `_` inside a word, as in `snake_case`, stays a plain character |
| a paragraph that starts with bold | the bold part is a lead-in on its own line, then the rest |
| a line ending in `\` | a hard line break at that point |
| `## Heading` | a heading in the accent color |
| `- item` | a bullet |
| `> text` | a narrow paragraph (`BACK_NARROW_FRACTION` of the width) |
| `> *text*` (all italic) | a narrow emphasised paragraph |
| `*text*` as a whole paragraph | an emphasised paragraph |
| `<!-- gap 48 -->` | 48 px of extra space |
| `# Title` | the file's own title; not printed |
| any other `<!-- ... -->` | a note; not printed |

`back-copy.py` shows how the file is read, block by block. Run it after every edit of the text.

A hard break belongs to the sentence, not to the measure: use it where a greedy line break would
cut a phrase ("into the whole / system"), never to fix a runt caused by the width.

## Line breaking needs the real font widths

The back text is broken into lines by measuring each word. The measurement must come from the
font the cover renders in: a table from another font measures lines too wide or too narrow,
breaks them in the wrong places and leaves short runts. Write the table once, and again after a
font update:

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/design-cover/scripts"
python3 "$SCRIPTS/font-widths.py" --family '<family>' --italic <italic font file>          # dry run
python3 "$SCRIPTS/font-widths.py" --family '<family>' --italic <italic font file> --fix
```

Give `--italic` the face the emphasised text actually renders in, weight included (weight 500
italic is not the regular italic). The table goes to `<publishing.cover>/font-widths/<family>.json`;
point `BODY_WIDTHS` at it, relative to the design file. Without a table the engine uses an
average width and the breaks are only rough.

The table also records where the bullet glyph's ink centre sits, so a bullet scaled up with
`BACK_BULLET_SIZE_SCALE` stays centred on its line.

## Trying variants

To compare ideas, subclass the design in a scratch file, change one thing per variant, make each
one with `--design <scratch file> --out <folder>`, and put them side by side with
`compare.py --grid`. Keep the grid image and delete the rest. Never leave variant files in the
book's cover folder, and never keep a variant as a flag in the shipping design: dead options
make every later reader of the design wonder which one ships.

## Where the files go

`make.py` writes to the work output folder (`cover.output`, default `<work.output>/cover`).
After the wrap PNG it also writes `png/wrap-overlay.png`, the KDP template at 55% over the art,
for looking only. When `cover.templates` has no template for this trim, page count and paper,
`make.py` downloads it first; with no network, or when the KDP answer has changed, it prints a
note and the way to download it by hand, and the rest of the cover is still made.
`--no-download` uses only the templates already there.
Only `--fix` copies the shipping files into the book: `front.png`, `back.png`, `ebook.png`,
`ebook.jpg` and `paperback-cover.pdf` in `cover.final`, or the paths the book metadata names
(`cover_front`, `cover_back`, `ebook_cover`). When those keys are not set, the book build takes
`front.png`, `back.png` and `ebook.png` from `cover.final`, so the digital editions pick up a
new cover without another step. Set `book.cover_front`, `book.cover_back` and `book.ebook_cover`
only to use other files.
