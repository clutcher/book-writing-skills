# The list of neutral sources for the reviewer

A reviewer who reads the book cold (the `readers` mode of this skill) gets a reading list of the
primary sources behind the book's main claims, so they can extend their own knowledge and
judge the book **independently**. The list puts the same sources in front of the reviewer, not
the same answers. A list that argues the book's case makes the review worthless as a check.

## Making one

1. Choose the main claims: the empirical claims an argument rests on, and
   the ones a reviewer is most likely to question. Write a claims file, one claim per line:
   `claim title<TAB>Key1,Key2`.
2. Draft the skeleton from the banks:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/review-ideas/scripts/sources-for-reviewer.py draft --claims claims.tsv --out <readers_review.sources_for_reviewer>
   ```

   It fills in, per claim: where the book makes it (`file:line`), each source with a free link
   (a source with no free copy is flagged), "What it establishes" from the quotes bank's Key
   findings and Scope, and the Guardrail as raw material under Nuance.
3. Finish it by hand: rewrite every Nuance neutrally, order sources in the order to read them,
   add a free mirror for a paywalled source where one exists, and cut anything that is not about
   a source.
4. Check it: `sources-for-reviewer.py check <file>`. It must report nothing.
5. Keep it with the run, not in the book: it goes out with one review.

## Shape

```markdown
# Sources for the reviewer

## What this is
A neutral reading list for the book's main claims ... It does not argue the book's case.

## How to use it
Read the sources in the order given. Judge the book against them, not them against the book.

## <Claim>
Book: <file:line>, <file:line>

Primary sources:
- [Key] Authors. Title (Year).
  - Link: <free full text>
  - What it establishes: <what the SOURCE shows, in its own terms and scope>
  - Nuance: <where the source is commonly misread, or where the book's wording sits at its edge>

## Quick index of free full-text links
- [Key] Title: <link>
```

## Neutrality rules

The test for every sentence: **does it describe the SOURCE, or reassure about the BOOK?** Only the
first belongs.

- Include only: pointers to where the book makes a claim, source links, a neutral "what this
  source establishes", and a neutral Nuance.
- Never explain or defend an authorial choice. If the only thing to add is the reason for a choice,
  add nothing; most fixes made after a review need no entry in this list at all.
- Three phrasings that break the rule:
  1. "this is the source for the book's X claim": it pre-answers whether the claim is sourced,
     which is the reviewer's job;
  2. "the book reflects / hedges / discloses this correctly": grading the book's wording is a
     defence, not a source fact;
  3. any concluding reassurance ("neither point undercuts the claim", "so the book is safe").
- **A Nuance may point out tension AGAINST the book freely. It must never resolve it FOR the book.**
- Neutral attribution and rounding facts are fine; favourable descriptions of the book's caution
  are not.
- Short quotes from sources are fine; a long quotation from a copyrighted source is not. The
  list also shows the review strategy, so it is never published.
