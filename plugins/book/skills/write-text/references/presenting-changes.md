# Presenting changes to the author

The author reviews every change before it lands. How a change is shown decides how fast and how
well it is judged. This format is also used by the revise-from-notes and prepare-sales-text skills.

## The order: draft, show, apply

1. **Draft** the change.
2. **Show** the full proposed text in the reply, with formatting markers visible (`*italic*`,
   `**bold**`, backticks), plus what changed and why.
3. **Wait** for an explicit approval.
4. **Apply** only then. A request that says "draft, review, update" still means: stop after
   showing. "Update" is the step after approval.

Why: copy and prose are the author's decisions, not defects with one correct answer. Applying a
draft moves the baseline before the author has read it, so the review becomes a diff against the
agent's choice instead of a judgment of the author's own text.

## Each item

1. **The full sentence**, never a fragment, before and after, with **bold on only the changed
   span**.
2. **Quotation or the book's own words?** Say which. A quotation must match its source word for
   word; the book's own words only have to be true.
3. **Verification status** against the cached source (the check-facts skill): verified word for
   word, partly verified, or not cached. When a source is missing, apply and report rather than
   stall.
4. **Counts near the limits:** words in the sentence when it approaches the voice profile's
   range or ceiling, and sentences in the paragraph against the profile's range.

## Batches

Group items by the size of the change and present one group at a time:

1. reference only (a key, a page number)
2. one word
3. two to four words
4. one sentence
5. a paragraph

Expect several items in each batch to be rejected or redirected. The author picks per item.

For an audit with many findings (a terminology sweep, a vocabulary pass), present ONE table
sorted by how much each finding matters, with the full before and after sentences and the
changed words in bold. Mark findings the author ruled on before as prior rulings and expect a
high rejection rate; show them anyway unless `decisions.md` marks them DECIDED.

## What the author will ask, so answer it first

- Does the new wording fit the paragraph, the section, the chapter, the book?
- Does the change need the same change elsewhere (a sweep)? Say where, with counts.
- Does it keep the author's own words? Prefer adding to them over replacing them. For example, a
  sentence that says "that plan" is often better fixed by adding "for the spring planting"
  after it than by swapping "plan" for another word.
- Is any clause circular or self-evident? Remove it before showing.

## Applying

**Apply the approved wording exactly.** Do not substitute a refinement, even a better one, and
even when the improvement was mentioned in the same message. If a flaw turns up while applying
approved text, say so and ask; do not fix it in the act of applying. A change of mind is the
author's to make.

## Options

Show at most two options per item, each fully checked against the rules (`write.md`, Step 5).
Replacement words must themselves be plain (`${CLAUDE_PLUGIN_ROOT}/skills/review-text/references/hard-words-criteria.md`): a "precise" swap to a harder
word is not an improvement.
