# Reviewer mistakes that recur

Each mistake below is written as the rule that prevents it. Read them before a review and before
proposing any change.

## Preferences and decisions

1. **Never override a stated preference and then defend the override.** If the author asked for
   one color family, do not build a variant in another. A stated preference is a constraint, not
   an opinion to argue with.
2. **When a finding contradicts a decided item, say so and stop.** Name the decision, give its
   id from the book's decisions file, and do not quietly re-argue it through a "small suggestion".
3. **A review critiques the execution of the chosen concept.** Density and weight of the artwork
   against the text, CMYK safety of saturated colors, spine continuity, type hierarchy. It does
   not propose a new concept unless the author asks, or unless iterations have clearly stopped
   helping (and then it says so directly).

## Seeing correctly

4. **Compare sizes, not impressions.** Light type on a dark ground looks larger than it is
   (irradiation), so a title can look too big when it is not. Measure before changing.
5. **Fix the thing that was named.** If the author says an element is in the wrong place, change
   its position, not its size or color.
6. **Diagnose with evidence.** Top-selling covers win with large central imagery, high color
   energy or brand recognition, not with small corner details. Say what the shelf shows, not
   what a detail might add.

## Changing the design

7. **Keep the color discipline you stated.** If the rule says three accent elements at most,
   count them after every change.
8. **Never replace the signature element.** The one element that makes the cover recognisable
   (a figure, a pattern, a mark) is kept; experiments work around it. Replacing it to try an idea
   destroys what makes the cover the book's.
9. **Do not add to a balanced composition.** If the composition already balances, a new element
   in a corner is clutter, however small.
10. **The levers for "this side should dominate" are geometry before color**: the area the
   element takes, its amplitude, its weight. Changing opacity or palette to shift dominance
   usually undoes an earlier color decision.

## Claims

11. **Count before claiming.** "A light cover stands out on a dark shelf" is only true if the
    shelf is dark; on many shelves most covers are light. Every claim about the shelf comes from
    counting the screenshots.
12. **Look at the competitor's actual cover, all of it.** Before saying a competitor "does not
    have" a device, look at every panel of its cover.
13. **A color reused as type must pass contrast.** A color picked for artwork and later used for
    a heading or bullet marks can fail WCAG at its printed size. `color-check` traces every color
    to where it is drawn; run it after every color change.
14. **Numbers are measured, not felt.** A threshold such as "below about 2:1 a thin line stops
    reading" is a judgement until someone measures it. Label a judgement as a judgement, and do
    not build a design change on it.
