# The listing: every surface that sells the book

How to build and review the surfaces a buyer meets before buying, and the buyer profile under
all of them. The text lenses are in `copy-review.md`; the store rules in `store-limits.md`.

## The surface map

Seven surfaces, in the order a stranger meets them on a store:

| # | Surface | Job | Drives store search? | Editable after publish? |
|---|---|---|---|---|
| 1 | Title and subtitle | rank and promise | yes, heavily | **no, locks at publish** |
| 2 | Categories (3 per format) | browse placement and rank | yes | yes |
| 3 | Keyword slots (7) | rank and shelving | yes | yes |
| 4 | Cover thumbnail | earns the click (the `design-cover` skill) | no | yes |
| 5 | Store description | turns the click into a sale | unresolved | yes |
| 6 | A+ content | turns the scroller | no | yes |
| 7 | Back cover and the free sample | the reader holding the book, the sampler | the interior is indexed | print needs a new file |

- **The back cover is the surface an online buyer is least likely to see.** Polishing it first
  is polishing the window nobody walks past. Plan the work from surface 1 down.
- **Title and subtitle are the one irreversible choice.** Everything else can change after
  launch, which argues for shipping a strong description rather than waiting for a perfect one.
  Method for the title: `title-and-discoverability.md`.

## The buyer profile

A list of job titles is a constraint on tone, not a buyer. Build the profile from the book's own
text, usually the preface paragraph that says who the book is for.

1. **Define roles by their relationship to the book's subject**, not by seniority (for a
   book on vegetable gardening, for example: whoever plants, whoever plans the plot, whoever
   teaches others to grow food). Roles defined this way map to different buying motives and
   survive any rule the book sets on how it addresses its reader.
2. **Find the competence gate.** Not years: the moment the book's problem becomes recognisable
   (for example, for a book on running a kitchen, "has had to feed a full room on a busy
   night"). That is the line the copy
   qualifies on.
3. **Record the span and what it costs.** A wide span (for example from a first-year practitioner
   to a department head, with readers whose English is basic) is a writing constraint: one sentence must clear both ends. It is
   an author decision about who the book is for; do not defend it with lexical-coverage
   thresholds (see `marketing-evidence.md`).
4. **A motives table**, one row per role: why they buy, what convinces them.

The profile lives in the book's audience file (`thinking.audience`), not in the skill and not in the copy
notes.

## Reading the category

Before writing a description, measure the shelf. Descriptive only: what publishers do, never an
optimisation target (no listing in any category was ever tested for wording against sales).

1. **Pick 10-15 comparable titles** a buyer would hold the book against, including at least one
   self-published one. Record the list and the date.
2. **Tear down each store description:** word count, bulleted list (and bullet count), what the
   first ten words do, whether it names the reader, author credential, endorsement, opening type
   (problem, credential, claim, scene, question, flat topic). Note publisher habits; they
   explain much of the variance.
3. **Tear down the back covers** where they can be read (store "From the Back Cover" fields are
   publisher metadata and are not always the printed panel; check product photos where it
   matters).
4. **List the claims this book cannot make** that competitors can: typically sales proof,
   accumulated reputation, name endorsements, series membership, institutional titles, awards,
   publisher bundles, audiobook editions. Lens 5 flags any draft leaning on one of these shapes.
5. **List the unoccupied promises:** promises no listing in the set makes. Mark which ones this
   book can honestly make. The central promise of the copy should be one of these.
6. **Find the precedent that matters:** a book that wins the shelf without the unavailable
   claims. It proves the shelf can be won and shows which levers (price, reputation off the
   page) did the work instead of the copy.

Record the results in the book's keywords file (`sales_text.keywords`, category evidence section), with
dates and how each figure was read.

## The store description

- **Its canonical home is the `sales_text.amazon` file.** It is a different surface from the one-line
  ebook description and from the back cover: the three must not contradict; they are not
  copies.
- **The first two sentences carry the whole pitch** (the fold is undocumented), and an early
  paragraph break spends visible space.
- **The reading path.** The store shows the description right above the free sample, which opens
  on the front matter and the preface. Rule C3 applies: the description must not spend an
  opening move the preface owns. The thesis is shared; the door is not.
- **Not a clone of the back cover.** Same argument, different length, different job.
- **Length targets the category, not the cover** (the measured band), except where a block
  earns its place on evidence (next point).
- **The structure block earns its space on evidence, not on convention.** The strongest
  behavioural finding on book choice says contents, organisation and structure decide selection
  (`marketing-evidence.md`, purchase drivers). A short block of the book's parts, each with a
  clause saying what it delivers, carries all three. Do not cut it to hit the category band.
- **Bullets are expected** on this surface in many non-fiction categories; check the category
  teardown. Bold labels at the start of list items are labels, not emphasis.
- **Name the reader explicitly**, in the category's idiom, and use that line to carry the
  prerequisite (for example the skills or tools the book assumes). It answers "is this for me" and prevents the
  wrong-expectations refund.
- **Credibility the author actually owns** (concrete, checkable, unclaimed by competitors, such
  as named client work) is stronger than a title or a superlative. It is not a testimonial, so
  stores allow it.
- **Keep the store description close to the limit only knowingly:** run
  `store-description-check.py` before any addition.

## A+ content

Check what the comparable self-published books do before building any; in some categories
self-published books ship none while large publishers ship many. Amazon's "up to 8% sales lift" is
general-retail internal data with no method: treat it as unverified for books. If built later:
no competitor comparison of any kind, and endorsements only from well-known publications or
public figures.

## Cross-surface consistency

Every surface agrees on these, and `sync-check.py` does the mechanical part:

1. **One noun for what the book delivers**, in one sense, everywhere.
2. **One wording per quantity** (`twelve walks` and `a dozen walks` in one argument reads as a
   slip or as two claims).
3. **The book's central claims unhedged where the book states them unhedged**, and hedged
   where the book hedges them. A surface never states more strongly than the book.
4. **Lists from the book in the book's order.**
5. **Title, subtitle and author exactly as in the book config.**

## Provenance levels

Every figure in the book's sales-text files carries one of these, and a review weighs it
accordingly:

| Level | Means |
|---|---|
| verified here | read directly in a session from the page, endpoint or image, with the date |
| agent, single run | read by a research agent against live pages once; recheck before a real decision |
| withdrawn | found wrong or invented and taken back; kept only as a warning, never used |
| unknowable | the store publishes no data (search volume, the fold, description indexing) |
