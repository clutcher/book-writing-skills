# Color on a book cover

Read this before arguing palette. Print safety is in `kdp-print.md`; this page is about what
color does for a buyer, and how strong the evidence for each claim is.

## First: color is a weak lever

- In one eye-tracking study of book choice (Nakahata et al. 2016, 23 people, 96 books, wearable
  tracker), **cover color had no measured effect** on gaze time or choice. Typeface mattered only
  when the title carried meaning; the title's meaning outweighed every visual variable. Strong
  design, small sample.
- In a 2025 eye-tracking study ("Judging a Book by Its Cover", an APA journal, online November
  2025; two studies, sample size not retrievable), **the cover that caught the eye fastest did not
  predict purchase intent**; the less-looked-at cover had the stronger link to willingness to buy.
  Grade: moderate to strong, but the paper was only partly retrieved.
- Qubit, *What works in e-commerce: a meta-analysis of 6,700 online experiments* (2017): the 81
  color tests had a mean uplift of 0.0% on revenue per visitor, with a 49% chance of being
  positive. Grade: strong, but the data is Qubit's own client base, and it is web shops, not
  books.

None of this makes a bad palette free: print safety, contrast and category fit still matter. It
does mean composition, title legibility and silhouette come before hue, and a long hue debate is
usually time the evidence cannot pay back.

## Category conventions

| Shelf | Color character |
|---|---|
| University presses | muted, restrained, 2-3 colors, lots of white; navy, black and white plus one accent; type-forward. Says "from an institution" |
| Technical and professional publishers | white or light ground plus one strong identity element; color used as information (series, subject), often one brand color |
| Cookery, gardening and lifestyle | usually led by a photograph; color comes from the food, the plants or the place |
| History and biography | often a period image, map or portrait; muted or aged tones with one strong title color |
| Literary and trade non-fiction | color used for mood: limited, analogous, muted or earthy, textured |

Some shelves use color to inform; others use it to set a mood. A book dressed in another shelf's
palette reads as the wrong shelf. These are tendencies, not rules: count the book's own shelf.

What makes a cover look self-published: four or more colors competing; neon or over-saturated
colors no publisher uses; multi-hue gradient backgrounds; thin or decorative type that dies at
thumbnail size; text over a busy ground without a contrast treatment; a favourite color chosen
over the genre's color; every inch filled. Professional covers use fewer elements with more
deliberate placement.

**Priors are not the shelf.** "Navy is overused in business books" or "a light cover stands out" are claims
about the whole market. Count the actual bestseller grid of the book's deepest category before
saying either. On a shelf where most covers are white or light, a white cover is conformity,
not distinctiveness.

## How many colors

Two or three chromatic colors at most, plus neutrals; type-led non-fiction covers often use one
or two. A photograph-led cover counts its type and accent colors, not the photograph's. Neutrals (white ground, near-black type, grey subtitle) are the frame, not palette members.
A gradient between close hues counts as about one and a half colors, not two.

Typical areas on type-led covers: background 65-80%, type 10-20%, artwork 5-15%. A general form
is 60-30-10 (dominant field, supporting structure, focal accent).

## Pairing

| Relationship | Effect | On a book cover |
|---|---|---|
| Analogous (30-60 degrees) | calm, unified | the main tool for a restrained palette, cool or warm; vary lightness and saturation, not hue |
| Complementary (180) | maximum energy | one small accent only; equal areas vibrate |
| Split-complementary | contrast with less tension | for adding a single accent of the other temperature |
| Triadic (120) | busy | usually too much for non-fiction |

Two neighbouring hues (two blues, two reds) need about 30 degrees of hue between them to read as different; under 15-20
degrees they merge, especially at thumbnail size and in print. At thumbnail size single lines
blur, so a color change across artwork has to work as an area of color, not as line colors.

Gradients look professional between close hues, or one hue at two lightnesses. They look amateur
across complementary hues (muddy middle), with many hue stops, at full saturation throughout, or
with visible banding.

## Harmony tools

- **Itten's contrasts** are independent levers: hue, light-dark, warm-cool, saturation,
  complementary, extension (area) and simultaneous contrast. A palette of one temperature (all cool or
  all warm) has no warm-cool contrast, so it must get its energy from lightness range (push toward 10% and 90%) and from
  saturated color next to near-neutral color.
- **Simultaneous contrast** (Chevreul, Albers): a light surround makes an enclosed color look
  darker and richer, and the eye adds a faint warm edge where a cool color meets white. White
  margin around a color makes it look stronger.
- **Warm advances, cool recedes.** In a palette of one temperature, depth comes from lightness
  (darkest looks closest), saturation, size and overlap.

## Light backgrounds

Most cover advice assumes a dark ground. A light cover has three problems of its own:

- **Energy.** With no dark mass it can look washed out at thumbnail size. One clearly saturated
  element (more saturated than would be needed on a dark ground) gives it energy.
- **Type weight.** Dark type on white reads well, but thin weights disappear when small; use a
  medium or semibold weight for small type.
- **Presence.** Among dark neighbours a light cover needs strong shapes and a high-contrast title
  to hold its place. Among light neighbours it is simply conforming (count the shelf).

A light ground also helps: next to white, moderately saturated colors look vivid, so a
print-safe, less extreme color can still read strongly.

## Color and type

Legibility depends on luminance contrast, not hue. Small type needs lightness contrast above all
and moderate saturation: saturated small type looks brighter than it measures and loses its edge.
Large display type can carry more saturation. `color-check.py` grades every type color with WCAG
2.1 AA at its real printed size: 4.5:1 for normal text, 3:1 for large text (18 pt, or 14 pt bold).
Sizes in the design are pixels at 300 dpi, so a 30 px body line is 7.2 pt and needs 4.5:1. A
color chosen for artwork and later reused for type is the usual way a failure gets in.

## Evidence on color and buying

Treat all of this as weaker than it sounds; most of it is not about books.

| Claim | Source and strength |
|---|---|
| "90% of snap judgements are based on color" | a literature review citing industry surveys; weak, do not repeat |
| Saturation and lightness shape brand personality: saturated reads as excitement, muted as sincerity and competence | Labrecque, Patrick and Milne 2013; moderate effects |
| Color that fits the product category matters more than any one color | Bottomley and Doyle 2006 |
| Restrained, muted designs read as higher quality for serious products; loud contrasting designs read as discount | Orth and Malkewitz 2008 |
| In print ads, dense perceptual clutter ("feature complexity") hurt attention to the brand and liking of the ad, while an elaborate creative design ("design complexity") helped attention, comprehension and liking. Inference for a cover: cut visual noise, not ideas | Pieters, Wedel and Batra 2010, *J. Marketing* 74(5) 48-60, DOI [10.1509/jmkg.74.5.048](https://doi.org/10.1509/jmkg.74.5.048); 249 ads, eye tracking; ads, not books |
| Blue is linked with competence and is the most widely liked color across countries | Labrecque and Milne 2012; Madden, Hewett and Roth 2000 |
| Moderate difference from the category beats both copying it and breaking it | Schoormans and Robben 1997 |
| Distinct items in a set are remembered and looked at longer | Von Restorff 1933, Hunt 1995 (only true if the cover really is distinct on that shelf) |
| White space raises perceived quality and price, but empty space around a message can reduce persuasion | Pracejus, Olsen and O'Guinn 2006; Kwan, Dai and Wyer 2017 |
| Left-to-right readers read a left-to-right change as progress | Tversky 2011 |
| In shops, the pleasure a store gives predicted wanting to stay and to spend more than planned; arousal mattered less clearly. "Do not over-saturate to pop" is an inference from this, not a finding about covers | Donovan and Rossiter 1982, *J. Retailing* 58(1) 34-57; store atmosphere, not covers |
| Color images are recognised 5-10% better than grey ones | Wichmann, Sharpe and Gegenfurtner 2002 |

## What designers do

- Start from the book, not from color theory: color follows the content's emotional core.
  "Fonts equal genre, colors equal mood."
- Judge every design at 100 px before approving it. High contrast survives the store's image
  compression. One dominant visual element, not several.
- If the cover blends into its neighbours in the grid, change contrast or composition before hue.
- For a possible series, fix the layout and type and vary one color per volume.
