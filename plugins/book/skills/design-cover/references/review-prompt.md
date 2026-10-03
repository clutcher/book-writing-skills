# Cover review: seven lenses

This page is the brief for the `review` mode. It judges the cover as a designed object: front,
spine and back as artwork. The words on the back and the store listing belong to the `prepare-sales-text`
skill; this review only checks that the artwork supports them.

Wanted: a rigorous, honest critique from several viewpoints, not encouragement and not vague
design talk. The author wants to ship a cover that competes.

## 1. Scope first

A wrap has three surfaces seen in different conditions. Name the surfaces in scope before
anything else.

| Surface | Seen | Shelf screenshots |
|---|---|---|
| Front | in the store grid, as a thumbnail, and in the hand | **required** |
| Spine | only on a physical shelf | not needed |
| Back | in the hand, sometimes in the store's extra images | not needed |

For a spine-only or back-only review, lens 1 is skipped or kept short (it is about the grid); run
lenses 2-7 in full.

## 2. Context gate

Before reviewing, have all of this. If something is missing, ask for it; never review blind.

- **The book**: title, subtitle, author, language, genre and sub-genre, target reader, the books
  it should feel like, formats, price. Read the book's audience file and `book.yaml` first,
  and ask only for what they do not say. The orchestrator finds the audience file with
  `python3 "${CLAUDE_PLUGIN_ROOT}/lib/book_config.py" get thinking.audience` and gives each
  lens the path; a lens never guesses it.
- **Decisions**: read the index of the book's decisions file (`decisions.py index`; SKILL.md
  shows how) and open the entries you need with `decisions.py show ID`. A finding that contradicts a
  DECIDED item is not a finding: say that it touches a decided item, give the item's id, and stop.
  Never re-open it as a recommendation.
- **The shelf** (front in scope): screenshots of the store's bestseller grid for the deepest,
  most specific category the book will sit in, not "Books" or "Nonfiction". At least the top 30-50
  covers. They live in `cover.shelf_screenshots`. If they are missing, stop and explain how to
  take them: open the category's bestseller list, capture the grid pages.
- **The cover**: the made PNGs at full size (`make.py` output), the thumbnails from `compare.py`,
  the design file, and the outputs of `color-check.py`, `font-check.py`, `layout-check.py` and
  `overlay.py`.

## 3. Technical checks before taste

A file that breaks a KDP rule is rejected however good it looks. Check first, from
`kdp-print.md`: bleed, safe area, 300 dpi, PDF with embedded fonts and flattened transparency,
spine text only on more than 79 pages, barcode area clear, CMYK channel limit, ebook specs. Run the
scripts and quote their output; never assert that a color passes or fails without it.

**Sizes in the design are pixels at 300 dpi, not points.** 200 px is 48 pt. Convert before
quoting a size anywhere. Read the final values from the design class and its base class
(`cover_design.py`), since the design overrides the defaults; reading only the base class gives
wrong numbers.

**Never quote the canvas size as a constant.** It follows the page count; see `kdp-print.md`.

## 4. The seven lenses, in order

Run each lens as its own cold subagent: give it the images, the scripts' output, this page and
the lens text, and nothing about how the cover got here. The first lens sets the weight of the
others, so it runs first.

### Lens 1: Category strategist (front only)

Covers are not sold alone. Judge the competitive position on the shelf in the screenshots
before judging quality.

- Group the top 30-50 covers into 3-5 visual families (for example: publisher template with
  illustration; dark cover with bright accent; white with one strong element; saturated brand
  color; type only). Give the share of each. A family with 40% of the shelf is the dominant
  vocabulary; one with 2 covers is a niche.
- Where does this cover sit? Which neighbours does it join, and how does it differ from them? If
  it joins no family, is it the one unique cover (high reward) or an outlier nobody places (low)?
- The dominant composition on this shelf: centred or asymmetric, top-weighted, image-led or
  type-led. The cover should match it or break it on purpose; slightly off without a reason
  reads as an accident.
- The top 5: what makes each one top 5? Usually strong category fit plus one difference.
- Where would this cover rank on this page? Top 10, bottom half, not seen? No flattery.
- About 75% conformity to the category's codes and 25% confident difference on ONE axis. Which
  axis, and is it the right one?
- The 250 ms test: after one glance, what kind of book was that?

### Lens 2: Designer

Composition, hierarchy, balance, negative space, the relation between elements. One clear
primary fixation point and one secondary; three equal anchors fail. Do the elements feel
inevitable or arbitrary? Is there a signature that survives at thumbnail size? Check optical (not
geometric) balance, how the title block sits in the whole, whether decoration does structural
work, and whether empty space is intended.

### Lens 3: Typographer

Font choice against the register. Count families and challenge any beyond two. Optical sizing:
does the visual weight of the lines balance (a longer word at the same size looks bigger)?
Tracking, leading, kerning at large sizes. Hyphenation (a compound adjective before a noun takes a
hyphen). Widows, orphans, runts. Hyphen, en dash and em dash. Double spaces used as separators.
Straight against curly quotes. Letters that pass for each other in the chosen face, such as a
lowercase l that reads as a capital I. Wrong italic files (an italic in one weight is a separate file
from the roman). Weight asked for against weight rendered (`font-check.py`). The font licence for
commercial print (most open fonts are fine; check).

### Lens 4: Colorist

Run `color-check.py` first, with `--icc` when a CMYK profile is available, and read it. Then read
`color.md`, "First: color is a weak lever": weigh palette findings below composition, title legibility
and silhouette.

Palette construction: hue relations, saturation, lightness, tension or harmony. CMYK gamut and the
channel limit, from the profile run rather than the naive figures. Type contrast at printed size.
Color signature against the **actual shelf**: never say "navy is overused" without counting navy
covers in the screenshots. Cite hex values: not "the title feels cold" but "the title at
`#2A3040` reads cold against the warm band; `#302A36` keeps the contrast and moves toward the
band".

Gradients: the dark end crushes first in print. Keep the deepest dark near `#0A0A0A` or lighter,
and check it in the `--icc` run, not only in the naive figures.

### Lens 5: UX and eye-tracking

The thumbnail is the main viewing condition, not the exception: about 150-180 px tall on
desktop, 100-140 px on mobile, 200-300 ms per cover while scanning. Use the true-size thumbnails
from `compare.py` (250, 180, 120 px). At each size:

- What survives: title, subtitle, artwork, color signature, author?
- What is the silhouette? Peripheral vision sees shape, then color, then detail.
- Where does the eye land first? The largest, highest-contrast element wins. Is it the title?
- Is there one secondary anchor?

Western buyers scan roughly in a Z. Only the title is in sharp focus on the first fixation. On a
centred cover the centre of the upper third gets the most fixation; top right and bottom left are
weak places for anything that must be seen.
Detail only visible at full size may reward a close look but must carry no meaning at thumbnail
size. Mock the cover into a 5 x 5 grid of real neighbours from the screenshots (`compare.py
--grid`), at full size and at 180 px: the only honest test of visibility.

One correction from the evidence: the cover that catches the eye fastest did not predict
purchase intent in a 2025 study. Keep every legibility finding (being unreadable at 180 px is a
real defect), but treat "what grabs the eye first" as a weak proxy for buying, and say so when a
recommendation rests on it.

### Lens 6: Front and back consistency

The artwork and the words are sold as one object. Read the current back-cover text from
`sales_text.back_cover` (never from memory or an old review; copy goes stale). Check three things:
does the visual resolve clearly enough that a reader of those words recognises what they see? Does
the artwork carry the idea the copy promises, with enough weight? Does anything in the artwork
contradict a claim in the copy? When image and words diverge, the reader believes the words and
distrusts the cover.

### Lens 7: Psychologist

What does the cover promise, and what feeling does it give in the first second: authority,
calm, urgency, mastery, transformation? Does it embody its message or only describe it? Does it
perform the category's codes ("dressed like a serious book") or own them ("is a serious book")?
Self-labels (BESTSELLER, MUST-READ, FIELD MANUAL) signal the first. What is the gut reaction of a
stranger scrolling past? Is it the right feeling for this book and reader?

Five lenses from psychology, as questions, not as laws:

| Lens | Question for the cover |
|---|---|
| Freud: tension and release | Does it show tension resolving? Does the problem look solvable, with enough weight on the resolved side to pay off? |
| Jung: archetype and threshold | Which archetype (for example sage, hero, rebel, caregiver, explorer) and does the design match it? Is a change visible? Is disorder bounded, is the whole composition contained? |
| Cialdini: persuasion | Authority from restraint and deliberate choices, not from labels. Does the buyer think "this is for someone like me" (identity)? Is it one of a kind on this shelf (scarcity)? |
| Kahneman: fast thinking | Is it read in one glance, with no zone where "designed" turns into "empty"? What carries the thumbnail? |
| Maslow: needs | Aspirational or remedial? Most non-fiction wants "become better at X", not "stop being bad at X". |

## 5. Output

1. **One honest paragraph**: what the cover is, what it tries to do, how close it gets. Two
   scores out of 10: full size and 180 px thumbnail. They often differ; the thumbnail score
   usually matters more.
2. **One section per lens**, in order. Specific: pixel positions, hex values, point sizes,
   contrast ratios. If a lens has nothing real to say, say it is strong and move on.
3. **Cross-cutting issues** that belong to no single lens.
4. **Calibration pass.** Go back over every structural claim, above all from lenses 1 and 4, and
   check each against the screenshots and the script output. A claim from priors ("asymmetric
   covers look misaligned in grids", "light covers stand out") is confirmed from the evidence or
   retracted. Show retractions openly, so the author knows which claims rest on evidence. A claim
   with no screenshot or measurement behind it does not stay in the review.
5. **What to change, in priority order.** A sequence of concrete edits, each with the lens that
   raised it and an honest size: small refinement, real improvement, or structural change. The
   first three should move the cover most.
6. **What not to change, and why.** Defending what works is as important as criticism.
7. **Ranking**, when there are variants: best to worst with a paragraph each, or name the
   trade-off the author must decide.

Nothing is applied from a review directly. Changes to the design are drafted, made in a scratch
output and shown side by side with `compare.py`; the author approves before anything is shipped.

## 6. Scoring rubric (default weights)

When ranking variants, a weighted score keeps the ranking honest. The weights below are a
starting guess with no study behind them; adjust them to the book and record its own in its
decisions file. Color
story 15%, print safety 10%, thumbnail 15%, difference from the shelf 15%, professional finish
10%, fits the book's idea 10%, fits the register 10%, fits today's shelf 15%. Show each sub-score,
not only the total.

## 7. Rules of engagement

- Honesty over politeness. A 6 that thinks it is an 8 is told so. A strong cover is not given
  invented problems.
- Specific over abstract. "Improve the hierarchy" is useless; "move the subtitle from 44 px to
  52 px and track it +1.5 so its slant does not lean right" is useful.
- A review that finds nothing is probably missing something; one that finds only surface issues
  is probably missing the structural one under them.
- Keep full-size quality, thumbnail quality and shelf position apart. A cover can be 9, 5 and 8
  at once.
- Priors about categories are usually wrong for a specific sub-category. Judge against the
  visible shelf.
- **Banned words** unless followed by the concrete reason: elegant, clean, sophisticated, modern,
  premium, refined, polished, professional, eye-catching, striking, beautiful, gorgeous,
  stunning.
- Search the web for current KDP rules and for any research claim, rather than trusting memory.
  Every research claim in the review names its source.

## 8. Two failure modes

1. **Reviewing in isolation**: judging the cover as if it hung alone on a wall. It sits edge to
   edge with 24 competitors. The question is always "surrounded by these covers, does this
   silhouette and color catch the eye?" Reasoning such as "the white cover bleeds into the page
   background" is wrong for the same reason: in the grid, covers sit edge to edge, and the
   neighbours, not the page, are the background.
2. **Priors instead of evidence**: "covers in this genre are usually...", "buyers in this segment...". If
   it cannot be checked in the screenshots, leave it out or label it a hypothesis.

Both have one cause: putting a model of the world in place of the world. The screenshots are the
world.

## 9. After the first review

Do not lower the bar on the next version. Run all lenses again against the same screenshots; if
three things got better and one got worse, say so. Ask whether a change improved the cover
against the shelf or only against the previous version. Re-run lens 1 on every real iteration.
If iterations stop helping, say it plainly: the problem may be the concept, not the details.
Resist drifting into encouragement as the author gets more invested in the cover; the tenth
review is held to the same bar as the first.
