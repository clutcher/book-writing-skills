# Leading, x-height and point size

The written basis of `scripts/compute-leading.py`. It takes the font's x-height, the point size
and the measure (characters per line) and gives the leading in points and the LaTeX
`\setstretch` value.

## 1. Core principle: x-height sets apparent size; point size is the lever

- **Apparent size comes from the x-height, not the nominal point size.** Two fonts at the same
  size can look like different sizes; how much of the em the lowercase letters fill decides it.
- **A face that looks small needs a larger point size, not more leading.** Leading does not make
  letters bigger; it only adds space between lines. Fixing a small-looking face with leading gives
  "small letters, wide gaps", the worst of both.

> **A small x-height calls for LESS leading, not more.** Smaller letters already leave more white
> between lines. Once the point size is right, use normal leading for that size and measure; do
> not compensate twice.

## 2. Three rules

1. **Leading suits typeface, text and measure together** (Bringhurst). No single ratio fits every
   face, content and line length.
2. **Body leading sits in the 120-145% band** of the point size; faces that run small sit at the
   lower end (Butterick).
3. **Leading grows with the measure.** Longer lines need more leading to help the eye find the
   next line.

## 3. Optical-size normalisation

To express one font's size as the equivalent of a reference face (the same maths as CSS
`font-size-adjust`):

```
apparent_size = s * (x / x_ref)      how big a font at size s looks
s_nom         = s_ref * (x_ref / x)  size needed to match a reference set at s_ref
```

`x` is the font's x-height per em; `x_ref` a normal book serif, **0.448 em**.

## 4. Measure and the leading coefficient

Good measure is **45-90 cpl**, with **45-75** the book target and **about 66** the classic ideal.
The coefficient `k` (leading / point size) rises with the measure:

| Measure (cpl) | `k` |
|---------------|-----|
| 45-55 | 1.20-1.28 |
| 55-66 | 1.28-1.35 |
| 66-80 | 1.35-1.42 |
| 80-90 | 1.42-1.45 |

## 5. The formula

```
STEP 1  point size fixes apparent size: s_nom = s * (x_ref / x), rounded to a body size
STEP 2  k from the measure (table above), interpolated between the anchors
STEP 3  leading L = k * size * xfactor, xfactor = 0.5 + 0.5 * (x / x_ref)
STEP 4  N = L / D, D = the default baselineskip of the chosen size:
          10pt class 12.0pt, 11pt class 13.6pt, 12pt class 14.5pt,
          half-point sizes (fontsize package) 1.2 x size
```

The `xfactor` damps the leading by half the x-height difference, which is how a small x-height
takes less leading. `compute-leading.py` reads `x` and the average lowercase advance from the
font file that `fc-match` finds, computes the measure from the text-block width, and prints `N`.
When the family is not installed on the host it fails, and the template's `\setstretch{1.05}`
is used instead, rather than measuring whatever font `fc-match` offered in its place.

### How `\setstretch` works

`\setstretch{N}` multiplies the class **default baselineskip**, which already carries about 1.2x
the point size. It does not multiply the point size:

```
final leading = N * D        (not N * point size)
```

At the 11pt class, `\setstretch{1.2}` gives 1.2 x 13.6 = 16.3pt = 148% of the font, not 120%.
Always derive `N = target leading / D`.

## 6. A worked example

A Garamond revival with x-height 0.400 em, a 6.14 x 9.21 in trim and a text block of about
4.6 in:

```
apparent size at 11pt = 11 * (0.400 / 0.448) = 9.8pt      reads like 9.8pt
s_nom                 = 11 * (0.448 / 0.400) = 12.3pt     -> 12pt
```

| Size | Apparent | Measure | Leading L (formula) | D | N |
|------|----------|---------|---------------------|---|---|
| 11pt | 9.8pt | ~69 cpl | ~14.2pt | 13.6 | ~1.045 |
| 11.5pt | 10.3pt | ~66 cpl (the ideal) | ~14.7pt | 13.8 | ~1.065 |
| 12pt | 10.7pt | ~63 cpl | ~15.1pt | 14.5 | ~1.04 |

Without the x-height damping (plain `k * size`), 12pt gives about 16pt leading
(`\setstretch{1.10}`, a "12/16" setting) and 11pt about 14.4pt (`\setstretch{1.05}`); the
damped formula sets a small-x-height face a little tighter, as rule 2 asks.

- 12pt fixes apparent size best and lands the measure near the ideal, at the cost of more pages
  (and a wider cover spine).
- 11pt keeps the page count low and accepts an optically small body; being a small-x-height face
  it takes less leading, not more.
- 11.5pt closes about half the apparent-size gap and puts the measure closest to 66 cpl. It is not
  a native `book` class size (the class accepts only 10, 11 or 12pt and falls back silently), so
  the build uses the `fontsize` package, whose default baselineskip is 1.2 x size.

Which size a book uses is the author's decision; record it in the book's `decisions.md`.

An italic face with an x-height about 5% larger than the roman needs no compensation. A code face
with a 20% larger x-height is matched to the body by fontspec's `MatchLowercase`, then scaled by
`code_scale`.

## 7. Misconceptions

| Myth | Reality |
|------|---------|
| A small x-height needs more leading | It needs less; small letters already leave more white between lines |
| Add leading to fix text that looks small | Wrong lever; raise the point size |
| `\setstretch{1.2}` = 120% leading | It is 1.2 x the class default, about 148% at 11pt |
| 11pt is the universal body size | The right size depends on the face's x-height |
| Leading is a flat 1.3-1.5x the size | It depends on x-height and measure, within 120-145% |

## 8. Assumptions

- `x_ref = 0.448 em` stands for a normal book serif. Anything from 0.43 to 0.47 moves `s_nom` for
  the example above between about 11.8 and 12.9pt; all round toward 12pt.
- The `\setstretch` conversion assumes the standard `book` class defaults (12.0 / 13.6 / 14.5pt).
- A larger body size means more pages, higher print cost and a wider spine: a print-economics
  input to weigh with the typographic result.

## 9. Sources

| Source | Used for |
|--------|----------|
| Bringhurst, *The Elements of Typographic Style* 2.2.1 | leading suits typeface, text and measure together |
| Butterick, *Practical Typography* (line spacing, line length, point size) | the 120-145% band; small faces need less leading; measure targets |
| MDN, `font-size-adjust` | optical normalisation |
| pimpmytype.com (line length, line height) | leading grows with the measure |
| TUG Font Catalogue, EB Garamond | a Garamond revival that renders small |
| Hochuli, *Detail in Typography* | interline spacing at the detail level |
