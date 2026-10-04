# KDP print and ebook facts

KDP changes its rules from time to time. Before a final upload, check the current KDP help pages
(paperback cover, ebook cover) instead of trusting this page or memory. Every fact below says
where it matters in the skill.

The print facts were read on 3 October 2026 from these KDP help pages:
[Create a Paperback Cover](https://kdp.amazon.com/en_US/help/topic/G201953020) (cover page),
[Print Options](https://kdp.amazon.com/en_US/help/topic/G201834180) (print options page) and
[Color Ink Options](https://kdp.amazon.com/en_US/help/topic/GX56BFPW4BKNPGFW) (color ink page) and
[Paperback Submission Guidelines](https://kdp.amazon.com/en_US/help/topic/G201857950) (interior page).
A line marked **unverified** has no KDP source: it is common practice advice, so treat it as a
guess to check on the printed proof.

## Geometry: derived, never quoted

```
spine width  = page count x paper factor
cover width  = bleed + trim width + spine + trim width + bleed
cover height = bleed + trim height + bleed
```

| Paper (`cover.paper`) | Inches per page |
|---|---|
| `bw-white` | 0.002252 |
| `bw-cream` | 0.0025 |
| `color-premium` | 0.002347 |
| `color-standard` | 0.002252 |

Bleed is 0.125 in on every outer edge. At 300 dpi the formula reproduces KDP's own template
images to within one pixel of rounding (the templates are drawn at twice that size).

`cover-size.py` prints the numbers. **Never write a cover size into a document or a review as a
constant.** Every manuscript edit that changes the page count moves the spine and the canvas, so
a literal size is wrong on the next build and hands a reviewer a confident false finding about a
cover that is right. The page count comes from `--pages`, `book.pages`, or the built print PDF
(`pdfinfo`); with none of them the scripts stop rather than guess.

## Paperback: hard constraints

These reject a file, so check them before any taste question.

| What | Rule |
|---|---|
| Bleed | 0.125 in on the outer edges (case-laminate hardcovers need more) |
| Safe area | text at least 0.125 in inside the trim lines (cover page); this skill uses 0.375 in to leave room for trim drift |
| Resolution | 300 dpi or more for every image |
| File | one PDF, fonts embedded, transparency flattened, no spot colors, no crop or trim marks, under 650 MB |
| Spine text | only on books with more than 79 pages (KDP: "We only print spine text on books with more than 79 pages"), at least 0.0625 in from each spine edge. The default spine draws nothing below that, and `layout-check.py` flags a design that does |
| Barcode | KDP prints the barcode on the back, bottom right: a 2.0 x 1.2 in box, 0.25 in from the spine fold and from the bottom trim (the KDP help page names a barcode margin but not these sizes; they come from published KDP cover guides, so check them against the template in the overlay). KDP prints over whatever is there. `layout-check.py` flags back text inside this box |
| Thin lines | at least 0.75 pt (the interior page gives this for charts and tables inside the book; the cover page gives no figure). Text at least 7 pt (cover page) |

### The KDP template

The KDP template for the exact trim, page count and paper comes from the KDP cover calculator.
`kdp-template.py --fix` downloads it into `cover.templates` (default
`<work.caches>/kdp-templates`; the file is third-party, so it stays out of git). It needs no
login. It sends the request the calculator page itself sends:

| Form field | Value |
|---|---|
| `bindingType` | `PAPERBACK` |
| `trimSize` | width and height in inches, `.` written as `_`, `X` between, `IN` after: `6X9IN`, `6_14X9_21IN`, `5_5X8_5IN` |
| `pageCount` | the interior page count |
| `paperType`, `interiorType` | `bw-white`: `WHITE`, `BLACK_AND_WHITE`; `bw-cream`: `CREAM`, `BLACK_AND_WHITE`; `color-premium`: `COLOR`, `PREMIUM_COLOR`; `color-standard`: `WHITE`, `STANDARD_COLOR` |
| `rightToLeft`, `printLocale` | `false`, `en_US` (`--print-locale` changes it) |

The answer is JSON with a short-lived download address of a zip file
(`cover-template-download:success`); the zip holds the template PNG, the same template as PDF,
and a readme. The script keeps the PNG and the PDF, named as KDP names them, for example
`PAPERBACK_6.000x9.000_120_BW_WHITE_en_US.png` (`PREMIUM_WHITE`, `STANDARD_WHITE` and
`BW_CREAM` for the other papers). A file already there with the same bytes is left alone; a
different one is replaced and reported, so look at the overlay again.

This address is not a documented interface and KDP may change it at any time. When the answer
has another shape, or KDP refuses the request, the script stops with exit 2 and prints the
manual way: open the KDP cover calculator, choose paperback, the trim, the page count and the
paper, download the template, unzip it and put the PNG in `cover.templates`. Without a network
it says `SKIPPED`.

`overlay.py` picks the template by page count, checks that the art and
the template have the size the formula says, and with `--fix` writes an overlay image. **The overlay is for
looking only. Never upload it.** Review every layout change with the overlay on, so the barcode
box and the spine folds are visible.

## Ebook cover: different rules

| | Required | Ideal |
|---|---|---|
| Format for the KDP dashboard | JPEG or TIFF (JPEG preferred) | |
| Color | RGB with an sRGB profile | |
| Bleed | none | |
| Size | at least 625 x 1000 px, at most 10,000 px on a side | 2560 px tall, height/width ratio 1.6 or more |
| Shown on the store | only when the shortest side is 500 px or more | |

Keep the required and the ideal apart: only the required list can reject a file. KDP documents
no penalty for a ratio under 1.6, so keeping the print proportion (one artwork for print and
ebook) is a choice, not a risk.

`make.py` renders the ebook cover from the trim SVG at 2560 px tall, so it is sharp at any size
rather than resampled from the print PNG. It writes a PNG (the EPUB embeds PNG) and a JPEG for the
dashboard: flattened on white, quality 95, no chroma subsampling, sRGB profile embedded.

## How KDP prints the cover

- Digital print on demand, not offset. KDP does not name its presses.
- KDP publishes no ICC profile and does "not recommend including color profiles" in the file
  (cover page). Soft-proof with U.S. Web Coated (SWOP) v2 (practice advice, **unverified**); U.S. Sheetfed Coated
  v2 is a little closer for digital presses, and the difference is small.
- "Covers are printed on 80 pound (220 GSM) white paper stock" (print options page), with a
  glossy or matte finish.
- An RGB PDF is converted to CMYK by KDP with an unknown profile.
- KDP publishes no total ink limit (checked on the cover page). Keep total ink (all four
  channels added) moderate and check dark areas on the proof; any exact percentage is
  **unverified**.
- **Tints vanish** (practice advice, **unverified**; the interior page recommends "a minimum
  grayscale fill of 10%" for grey backgrounds inside a black-ink book). Under 5% in every
  channel a color may print as white or show banding; under 10-15% results are unreliable. For a tint that must be seen, aim for 15% or more in some
  channel. A near-white background such as `#F0F2F5` (C2 M1 Y0 K4) prints as white: commit to
  white, or push the tint until it is clearly visible.
- **No single CMYK channel above the limit** (`cover.cmyk_limit`, default 88%). Colors near the
  gamut edge dull and shift in print; saturated cyans, greens and oranges and very deep blues are
  most at risk. A blue with some black in it survives conversion better than a pure cyan and
  magenta mix.

### The naive CMYK number is not a proof

`color-check.py` always prints a naive RGB to CMYK conversion. It is an approximation with no
profile. On dark saturated colors it can be wrong by 20-30 points in one channel, so the limit
has not really been tested until a real profile has been used:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/design-cover/scripts/color-check.py" --icc /path/to/SWOP-coated.icc
```

The profile run reports each color with and without black point compensation. **Whether a dark
color breaks the limit can flip between the two**, and the printer, not you, decides which is
used. So the dark end of a palette cannot be settled by soft proof at all: a color over the
limit in only one mode is an advisory that says "look at this one on the printed proof".

**Order a physical proof before the final upload.** Colors also vary between print runs. Check
the darkest and most saturated colors on it first.

## Finish: glossy or matte

| | Matte | Glossy |
|---|---|---|
| Color | mutes saturation and brightness | keeps saturation |
| Light background | can look washed out | reflective, keeps small color differences |
| Gradients | compresses hue differences | keeps them |
| Fingerprints | hides them | shows them |
| Feel | quiet and rich on dark covers | brighter |

A light cover with small color differences wants glossy. A dark, rich cover can take matte. The
table above is practice advice, **unverified** by KDP. KDP itself says only that glossy "makes
black covers darker and artwork more striking" and is "typical for textbooks, children's books,
and nonfiction", and that matte is "typical for novels and other fiction" (print options page).

## Paper and ink

| Choice | Notes |
|---|---|
| White paper | non-fiction, technical books, books with diagrams (practice advice; KDP gives no genre advice for paper). Color books print on white only |
| Cream paper | fiction and memoir (practice advice); thicker, so the spine is wider (see the table above) |
| Black and white ink | the cheapest |
| Standard color | printed "using inkjet printers" on the same lighter paper as black and white (color ink page) |
| Premium color | heavier paper (60-71 lb) and sharper color for image-heavy books (color ink page); KDP does not say which press prints it. Its own spine factor |

The paper changes the spine width, so `cover.paper` must match what is chosen in KDP.

## Color blindness

About 1 man in 12 has a color vision deficiency, mostly red-green. Never let hue alone carry
meaning: two elements that must read as different need a difference in lightness too.
