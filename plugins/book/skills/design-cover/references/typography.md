# Cover typography: rules that prevent shipped defects

Each rule prevents a defect that is easy to miss and easy to ship.

## Measure, do not guess

- **Measure text with the face that renders it.** Line breaks computed from another font's widths
  can be more than 10% off, break early and leave runts. Use `font-widths.py`.
- Summing advance widths ignores kerning, which only pulls letters closer, so the sum is a small
  over-estimate (0.2-2.2% against the rendered ink). No extra safety margin is needed.
- **A space is not always the width you think.** A thin space (U+2009) can be wider than a normal
  space in some faces (245 against 213 thousandths of an em in one Garamond). Check the advances
  before using one in a wordmark.
- **SVG collapses repeated spaces.** Five spaces written to widen a gap render as one. Set a gap
  as `dx` on the next word, never as a run of spaces.
- **rsvg-convert does not implement `word-spacing`.** Anything that relies on it silently renders
  with normal spaces. This is why the back text is always ragged-right: the engine has no
  justify option, and a design that still sets `BACK_JUSTIFY` stops with an error.
- Fonts render only if installed. A missing face is replaced without an error, so run
  `font-check.py` before trusting a PNG.

## Line breaking on the back panel

- **Break where the sentence wants, not where the measure runs out.** A greedy break can cut an
  article and its adjective from their noun ("from the old / orchard"). The copy marks
  such a break (a line ending in `\`); the width does not.
- **A runt is measured by width, not by word count.** A two-word last line at 10% of the measure
  passes a "one word only" rule and still looks like a runt. The engine pulls a word down when the last line is
  under `BACK_RUNT_FRACTION` of the width.
- **Same markup, same device.** A bold lead-in always gets its own line and the same gap after it
  as a bold-only paragraph; otherwise short and long lead-ins behave differently for no reason
  but sentence length.
- A hard break must not end a bold lead-in group: an all-bold paragraph with a break inside stays
  one group.
- **Justify only with a short measure or with hyphenation.** At about 100 characters per line
  with greedy breaking, a stretch limit binds line after line and the right edge wanders by a
  fifth of the measure, which reads as broken setting. Ragged-right is the honest choice, and the
  only one the engine offers.

## Optical alignment

- A round capital (O, S, C) set flush with flat stems looks indented. Let it overhang the left
  edge by about 3% of the cap height.
- An italic line under a roman one: set it 2-4 px right of the roman axis, never left of it.
  Check the italic's left side bearing, which differs between faces.
- A middle dot in an all-caps wordmark sits at lowercase height in many faces. Lift it onto the
  cap band with `dy` and put the baseline back on the next word (`svg_parts.spaced_name`).
- A scaled-up bullet glyph rises with its size. Push its baseline down by the ink-centre lift so
  it stays centred on the x-height of its line.

## Spacing and hierarchy

- **Tracked capitals want a word gap 3-4 times the letter gap.** A 9:1 gap reads as three
  separate words; a plain space in tracked caps reads as no gap.
- **A gap bounded by type on both sides is a third element with no job.** If the largest white
  area on the front sits between two text blocks, move one of them so the largest white area is a
  margin instead.
- The eye needs one primary anchor and one secondary; three equal anchors read as clutter.
- Count type families. Two is the norm (display plus text); challenge a third.
- Check the italic actually renders as a true italic in the weight asked for; a looped or
  unexpected italic letter can read as a different letter.

## Artwork against type

- **Stroke width changes the amount of ink, not its darkness.** A pale line that fades at
  thumbnail size fades because it averages with the white ground; a thicker stroke adds ink but
  not contrast. The lever for thumbnail survival is a darker color.
- When artwork strokes get as heavy as the title's strokes, the artwork competes with the title.
  Keep the art visibly lighter than the type it sits near.
- Interpolate segment boundaries when drawing a line in pieces: integer division can leave the
  tail of every line undrawn and lose the bleed on the right edge.
