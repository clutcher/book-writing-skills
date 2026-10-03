# The impression review

**What it owns:** the signal the selling surfaces send when a stranger meets them together:
what they say about the book, the author, the ideas, the authority behind them, and how serious
the whole thing looks. It is the only review that holds the front cover, the back cover and the
store description at once.

**Why it is separate from the ten lenses.** The lenses are prose rules on text surfaces; the
visual cover belongs to the `design-cover` skill. An impression read spans both, and one question
belongs in one place.

**What it is not.** Not a defect hunt. The other reviews find what is wrong. This one reports
what is *received*, including where the copy is flawless and the signal is still wrong. A
surface can pass every copy lens and still read as a weekend side project.

## The question

A reader in the book's audience, with no prior knowledge of the author, sees the thumbnail, then
the store description, then the back cover. **What do they now believe** about:

1. **The book.** What kind of book is this: a manual, a manifesto, a synthesis, a textbook, a
   collection of tips? How much looks like argument and how much like advice? Read once, or
   kept?
2. **The author.** What standing, what seniority, and from what evidence? A practitioner, an
   academic, a consultant, a teacher? Is there a person here, or only a voice?
3. **The ideas.** Original, borrowed, or a synthesis? The author's own position, or a
   restatement of what the field already agrees on? Is there a thesis, and can the reader state
   it?
4. **The authority.** What does it rest on: evidence, experience, reasoning, reputation or
   assertion? Where on the page does it come from, and would a hostile reader accept it?
5. **The seriousness.** Years of work, or a weekend? What exactly creates that impression:
   typography, claim density, hedging, structure, sentence shape?
6. **The category.** Trade book, self-published, academic press, vanity project? Name the shelf
   and say what put it there.

Answer each **from the surfaces alone**. Never from the manuscript, the book's notes or its
repository. The buyer has none of that.

## The intended impression

The book keeps its intended impression in the file `sales_text.intended_impression` names (template in
`templates/`). Read it before the review, never during the reading steps below (it would colour
them). The usual constraint: the impression must be produced by the same means the book uses
(precision, structure, a claim the reader can test) and never by a credential, a superlative or
a borrowed name.

**A gap in either direction is a finding.** Reading as more authoritative than the book can back
is as damaging as reading as less, because the first buyer to test it writes the review.

## Method

Run in the buyer's real order and write down the impression after each step before moving on:
later surfaces colour the earlier reading and cannot be unseen. One cold subagent does steps 1
to 5; it gets the surfaces and nothing else.

1. **Thumbnail only**, at the size a search result shows it (the `design-cover` skill makes one). What
   is legible, what is guessed, what is the genre?
2. **Front cover at full size.** Same questions; what changed from the thumbnail?
3. **The store description**, read once at reading speed.
4. **The back cover**, from the `sales_text.back_cover` file and from the rendered back panel image.
5. **All together.** One person, one project: do they sound like the same author? Does the
   confidence level match?

Then answer the six questions.

## What to report

For each of the six:

```
### [Dimension]

**Received:** [what a stranger now believes, in their words]
**Produced by:** [the specific words, typographic choices or absences that caused it]
**Intended:** [what intended-impression.md calls for]
**Gap:** [none / describe it, and say which surface is responsible]
```

Close with three things:

- **The single strongest signal** across the surfaces, and which surface carries it.
- **The single weakest**, and whether it is a defect or the known cost of a decided item.
- **One sentence** a stranger would use to describe this book to a colleague. That sentence is
  the real output of the whole positioning effort, and no other review produces it.

## Rules

- **Report the impression, not a fix.** Recommend only where the gap is real and the fix does not
  reopen a decided item.
- **A decided item is not a finding.** If the impression suffers because of one, say so plainly
  and name the entry in `decisions.md`; do not propose a reversal.
- **Close a gap with the book's own means.** If the intended impression is "shown through the
  writing, never claimed", a new credential on the page closes the gap with the one tool the
  intent rules out. Propose precision, structure or a testable claim instead.
- **No conversion evidence** (`marketing-evidence.md`, the section on conversion testing).
- **No estimates.** If a figure is not in front of you, write "not verified".
- **Verify state first.** Read the surfaces from the files in this session.
