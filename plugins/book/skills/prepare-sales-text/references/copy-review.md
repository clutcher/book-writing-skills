# Copy review: the ten lenses

How to review the words that sell a book: the back cover, the store description and the
ebook description. The visual cover is the `design-cover` skill's job. What the surfaces *signal*
(about the author, the ideas, the seriousness) is `impression-review.md`, run after this one.

A cover is not a short chapter. The manuscript rules assume a reader who has already bought the
book and reads in order. A back cover is read by a stranger, in about fifteen seconds, out of
order, while deciding whether to buy at all. So some writing rules bind harder here, some are
suspended and two are turned around. `rules-transfer.md` has the table. Reviewing cover copy
against chapter rules word for word produces confident wrong findings.

## Before the lenses

0. **Find the real paths.** Run `sales-text-files.py` (SKILL.md, "Find the real paths first").
   File names below are the default names; use the paths it prints, and say so when a file is
   missing.
1. **Read the decisions index first** (`decisions.py index`, then `decisions.py show ID` for
   an entry). A decided item is not a finding. If
   a finding contradicts a DECIDED entry, say so in one sentence, cite the entry and stop. Run
   `python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py match --text-file F` on every finding before
   it is reported.
2. **Measure the current state; never quote a number or a sentence from prose.** Review files
   and old notes lag the copy. Run `copy-stats.py --text` and `sync-check.py` and read the
   surfaces from their output. A finding that turns on what the copy says is reportable only if
   this session read it from the file.
3. **Read the book's intended impression** (`sales_text.intended_impression`) and its
   audience (`thinking.audience`), and the glossary (`rules.glossary`) for every
   defined term the copy uses.

## Run this first: the decomposition test

For each unit of the copy (each paragraph, the bullet block, the closer) ask: **does it split
into two halves that each make sense alone?** If it does and it is read as one block, split it.

This is grounded in cognition, not in publishing habit: holding the material constant and
varying only whether a problem splits into two independently solvable halves, the splittable
version was easier on accuracy, time and confidence (Halford, Baker, McCredden and Bain, "How
Many Variables Can Humans Process?", *Psychological Science* 16(1), 2005, DOI
10.1111/j.0956-7976.2005.00782.x).
A related result: holding three items instead of one did **not** slow reading, but it cost
comprehension accuracy (Fedorenko, Gibson and Rohde, *Journal of Memory and Language* 54(4),
2006, DOI 10.1016/j.jml.2005.12.006). A dense cover does not make a
stranger read slower; it makes them understand less, and they do not come back.

**Do not count concepts against a fixed number.** Working-memory limits are measured under
conditions built to prevent chunking, and prose is exactly where readers chunk freely. The
question is whether a block asks the reader to hold two separate things as one, not how many
nouns it holds.

## Three rules the manuscript does not have

**C1. One qualifier per sentence.** Count subordinate clauses per sentence: `which`, `that`,
`who`, `where`, `because`, `so that`, and an appended contrast (`but never`, `and never`). Two
in one sentence is a finding. Two in one sentence three times in a row is why copy reads as
interruptive. Fix by promoting the qualifier to its own short sentence, or by cutting it.
Coordination (`takes X and builds Y`) is not a second qualifier.

**C2. Concrete subjects.** Every sentence's grammatical subject should be something the reader
can picture: a person, the reader, the book, the thing the book is about (the garden, the
dish, the river, the battle). List the subjects of all sentences in a column. Where the column
is a list of abstract nouns (`the method`, `the approach`), the copy narrates a concept instead
of putting the reader in a scene. Watch long fronted phrases too: a long run of words before the
main verb, such as a list of the author's credentials, delays the subject and reads as a CV.

**C3. No repeated entry point along the buyer's path.** The buyer meets the surfaces in one
sitting: thumbnail, store description, then the free sample, which opens on the front matter
and the preface. A move spent on the cover is spent for the preface too, and a buyer who meets
it twice concludes the book has one idea.

- **Measure the sample.** Find how far the store's free sample reaches. The store shows a share
  of the pages (`store-limits.md`: print 20%, ebook 10%). Step one: that share of the pages
  holds about the same share of the words, so take the manuscript word count times the share.
  Step two: add up the words of the manuscript files in book order; the file where the sum
  passes that number is where the sample ends. `copy-stats.py --sample` does both steps and
  prints the last file inside each sample. Everything before that point is pre-purchase material: it can echo
  the copy, but it also PROVES the copy on the spot. Material after it cannot echo, but cannot
  be demonstrated either, so copy built on it promises what the free pages never show.
- **The test is delivery, not novelty.** Treat the description's last sentence and the
  preface's first as adjacent. The preface must move forward from there, not restart. An echo is
  a defect; a promise the sample then develops is how the page converts.
- **Separate the move from the thesis.** The book's central claim must appear on every surface;
  that is the pitch. What must not repeat is the entry point: the scene, the statistic or the
  question a surface opens with. **Vary the door, never the house.**
- Before approving any hook, grep the opening pages for the move it makes and count the uses.
  `sync-check.py` reports long shared word runs between the preface opening and each surface.
- The book decides which surface owns which opening move. Record it in `decisions.md` (an asset
  allocation), not in the copy notes.

## Where the copy lives

One site is canonical for each surface. Derived sites are checked, never hand-edited:

| Surface | Canonical file | Relationship |
|---|---|---|
| Back cover | `sales_text.back_cover` (the cover design reads it) | the one source; nothing copies it by hand |
| Store description | `sales_text.amazon` | its own text; must not contradict the back cover |
| Plain-text description | `sales_text.plain_description` | generated from the store description; never edited |
| Ebook description | the book's `description` metadata | one condensed line; must not contradict |
| Front and spine | title, subtitle, author from the book config | must match exactly |

The store description is **not** a shortened cover. It is read by a stranger deciding to spend
money, where the cover is read by someone already holding the book, and the category expects a
different length and a bulleted list. So the store description and the cover are checked for
**contradiction**, never for equality. A rule that the two must be word-for-word copies forces
one surface's limits onto the other; do not bring it back.

## The ten lenses

Run them in this order. **One subagent per lens**, each cold: it gets the surfaces, this file,
`rules-transfer.md`, the evidence references and `decisions.md`, and no edit history.

### 1. The Stranger

Read the back cover once at reading speed, look away, and answer from memory: what is this book
about, who is it for, what does it promise? Everything you cannot answer is a defect, however
good the prose. Then do the fifteen-second version, reading only what a scanner reads: the bold
spans, the bullet heading, the bullets, the last line. That path must carry the whole pitch
alone, because for most buyers it is the only path taken.

### 2. The Skeptic

List every checkable claim and grade it: can the book back it, and is it hedged to the right
strength? Absolute negatives (`no other book`), counts (`forty recipes`, `three rules`) and
priority claims (`the first`) are the ones that get tested. A claim the book does not back is
worse on a cover than in a chapter: the reader meets it before any trust exists, and it is what
a one-star review quotes. **Truth over punch: every claim must survive a fact-check.** Watch
for one quantity in two wordings (`twelve walks` / `a dozen walks`): readers read it as an
editing slip or as two different claims.

### 3. The Connector

The writing rules that transfer, sentence by sentence. Three failures cause most findings:

- **Pronouns and demonstratives with no antecedent.** For every `it`, `this`, `that`, `these`,
  name the exact noun it points at and how many words back it sits. If the antecedent is in
  another paragraph or must be inferred, it fails. **Check the NEAREST noun by hand:** an
  antecedent script passes a pronoun whose antecedent is present but not the nearest noun.
- **A noun phrase that changes referent between paragraphs.** `the method` meaning the old way
  in one paragraph and the way this book teaches in the next is a contradiction on the surface,
  even when the intent is clear.
- **More than one noun for the book's core offering.** Count the distinct nouns across the
  whole copy. Check each noun against a second sense in the same paragraph (`method` next to
  `the scientific method`, `diet` next to `going on a diet`).

Repeating a noun as the bridge between sentences is the fix, not a defect: one name per
concept. Do not replace it with a pronoun.

### 4. The Buyer

Answer from the copy alone: (1) What problem do I have that this solves, in my words? (2) Why is
this different from the five books already on my shelf? (3) Why this author? (4) Is this for
someone like me? Question 4 is the one covers skip. A bullet that says what I will do does not
tell me I am the person meant to do it. Check the reader named against the book's positioning.

### 5. The Marketer

Does the copy win on the real shelf? Read the category evidence in the book's
`keywords-and-categories.md` first.

- **Match the conventions, then depart on exactly one axis,** and be able to name which. Copy
  that ignores three category conventions reads as amateur; copy that matches all reads as
  interchangeable.
- **The claims this book cannot make.** List the credibility moves open to competitors and
  closed to this book (typically: sales proof, reputation, name endorsements, series
  membership, institutional titles, awards, publisher bundles, audiobook editions). A draft that
  leans on one of these shapes borrows authority it does not have.
- **Promise-to-proof ratio.** Count promises, then the specific things offered as proof: a
  number, a named debate, a concrete scene. A cover has no citations, so proof means
  specificity. More than two unproved promises in a row is where a stranger stops believing.
- **Differentiation against the real gaps.** Check the central promise against the promises no
  listing in the category makes. A promise every competitor makes competes on execution alone.
- **Price coherence.** The claim must justify the price to a buyer who has never heard of the
  author.
- **Comparable books.** Name the two or three books a buyer would hold this against. The copy
  should make the difference legible without naming them (stores prohibit naming competitors).

### 6. The Psychologist

The text side of a five-theory frame, plus four ideas that apply only to prose. Use them as
questions to ask, not as laws: they are lenses for looking at the copy, and only the items that
name a measured finding are evidence. Freud and Jung in particular are labels for a way of
reading, not tested causes of sales. An unknown author has no borrowed authority, so everything
here is carried by wording alone.

- **Freud, tension then resolution.** The copy opens a tension and closes it. The chaos must
  feel solvable, never hopeless.
- **Jung, the archetype and the threshold.** Name the archetype the book speaks as (for example
  sage, hero, rebel, caregiver, explorer) and keep the copy in it. For a sage, authority comes
  through restraint, and every superlative weakens it. Show a before state and an after state. Keep the problem finite and named.
- **Cialdini.** Social proof is often absent for a new author and reciprocity has little surface
  on a cover, so four principles carry the weight. *Authority:* earned by precision and by stating a limit, lost by loudness.
  *Commitment:* find the sentence that lets the reader think "this is written for someone like
  me". *Liking:* written by a peer who did the work, not a vendor; first person for experience,
  third person for the author sentence. ("Say *you* and conversions rise" is folklore; see
  `marketing-evidence.md`. Keep `you` for style, never as a tactic.) *Distinctiveness:* the
  difference must be legible in one reading.
- **Kahneman, processing ease.** The first two sentences must land without effort. Do **not**
  argue that easier copy is believed more (the fluency-truth effect is weak). Argue that a
  sentence needing two passes costs comprehension, which is separately evidenced. Anchoring:
  the first number on the page sets the scale for every claim after it.
- **Maslow, aspirational not remedial.** For a cookery book, for example, "Cook a good dinner
  on any weeknight" and not "your cooking is dull". Place the fault with a condition the reader
  did not choose, never with the reader.
- **Brehm, reactance.** A sentence that puts the reader's current practice in the wrong turns
  curiosity into defence, and a cover has no evidence to win that fight. Synthesis attracts;
  negation repels.
- **Festinger, dissonance.** The buyer already owns the famous books. Copy implying those were a
  waste asks them to admit a bad decision. Position the book as **completing** the shelf, not
  replacing it.
- **Zeigarnik, the open loop.** When the book coins a term, the unexplained word opens a loop
  the reader wants closed; that is why it works as a hook. A loop never closed anywhere on the page reads as evasion.
- **Gain or loss framing.** Does the copy name the cost of the problem, the gain of the
  solution, or both? Neither frame is generally more persuasive: meta-analyses of gain-framed
  against loss-framed messages found no overall advantage for loss frames (O'Keefe & Jensen 2006,
  *Communication Yearbook* 30, 1-43, DOI [10.1080/23808985.2006.11679054](https://doi.org/10.1080/23808985.2006.11679054);
  2007, *J. Health Communication* 12(7) 623-644, DOI [10.1080/10810730701615198](https://doi.org/10.1080/10810730701615198);
  2009, *J. Communication* 59(2) 296-316, DOI [10.1111/j.1460-2466.2009.01417.x](https://doi.org/10.1111/j.1460-2466.2009.01417.x)).
  These studies measured health and compliance messages, not book copy.
  Choose by tone: a page built on loss reads as fear-selling.

### 7. The Editor

Delete each sentence and re-read: if the pitch survives, it was filler. Then check whether each
surviving claim is made twice. A deliberate callback across a distance is fine; the same claim
restated inside a paragraph is not. **A weaker restatement after a strong claim caps it**: this
is how a scale claim gets softened with nobody deciding to soften it.

### 8. The Consistency Auditor

- Against the other surfaces: no contradiction (see "Where the copy lives").
- Against the book: every concept named must match what the manuscript and the glossary say it
  is, and every position must match the author's stance files.
- Front and spine: title, subtitle and author exactly as in the book config, hyphens included.
- One wording per quantity; the book's own order when a list from the book is repeated.

### 9. The Non-Native Reader

Read as a reader in the book's audience, with solid vocabulary in the book's field and ordinary
general English. Flag any word whose meaning cannot be recovered from its parts and is not
standard language of the field. Judge by whether a working reader of the field stumbles, not
by CEFR level: `which suggests` is transparent,
`comes down to` is made of easy words and is opaque. Terms of the field are free; general
vocabulary used to impress is not. When the book coins a term, test it: replace it with the plainest
word that keeps its meaning and re-read. If a line collapses, it depends on a definition the
reader does not have yet.

### 10. The Typographer of Text

- **Characters:** set type uses true curly quotes, a real en dash in ranges, a true ellipsis.
  An ASCII-only rule for the manuscript source does not apply to set type.
- **Hyphens** in attributive compounds (`high-quality work`).
- **Widows and orphans:** check the rendered image, never the source; the wrap is computed at
  render time.
- **Bold spans:** each must end at a clause boundary and read correctly alone; the scan path
  (bold spans read together, `copy-stats.py`) must be complete sentences that flow. Two parallel
  bold spans with near-synonym verbs (`works from` / `rests on`) merge for a fast scanner.
- **Where emphasis pays:** emphasis stops a skip; it does not win the first look. The opening is
  already over-read, so bold at the top is spent where attention already is (a supported
  inference, not a tested finding). Bold as a display anchor is a design choice; record it as
  one, not as science.
- **Never capitals for emphasis** in running copy. If colour marks anything, contrast is the
  variable, not hue. Do not claim emphasis helps understanding. Sources and grades:
  `emphasis-evidence.md`.

## Output format

Report in the same shape as the review-text skill's review, so both merge into one worklist:

```
### Finding [N] -- [lens name]

**Site:** [surface, plus paragraph or bullet]
**Text:** "[exact text, as read from the file this session]"
**Problem:** [why it fails, naming the lens and the rule]
**Suggestion:** [full replacement sentence, or the decision the author must make]
**Decision check:** [decisions.py match result: no match / entry id and status]
```

Close with the three findings with the highest impact, say plainly which are defects and which
are decisions only the author can make, and give **a score out of 10 per surface with the
reason** (what keeps it from the next point). If a surface is a 6 that thinks it is an 8, say
so. A reviewer proposes; copy is a positioning decision the author owns.

## Lessons that keep coming back

- The prose in review notes lags the copy it describes. The file wins; fix the note.
- Read the bold spans alone, every time. A fragment in the scan path survives many reviews when
  nobody reads the path by itself.
- A demonstrative check passes a pronoun that points at the wrong nearest noun. Read by hand.
- Compute word counts from the source, and read wrap, widows and empty space off the rendered
  image. Never quote a figure that was not re-measured in this session.
- A word-frequency grep cannot decide whether the book holds an idea; the book may state it in
  other words. Read the section before saying the book does not back a claim.
- Write copy only from claims that have passed the book's fact-check. Copy built on a claim the
  book later corrects inherits the error.
