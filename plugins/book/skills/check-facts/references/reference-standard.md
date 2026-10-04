# A reference is not a citation

This is the standard every verdict is graded against. Read it before grading anything. Grading
references as if they were strict citations is a common source of false findings, including
findings graded SIGNIFICANT that later have to be withdrawn.

An `@Key` in the book (`[@Key]`) is a **reference**. It points a reader to where an idea lives. It is NOT a
claim that:

- the source contains the book's exact words;
- every clause of the sentence is separately sourced;
- the source is the sole or the original authority for the idea.

**A reference is sound when the source holds the IDEA or the GIST.**

## Corollaries that decide real cases

- **A bracket attaches to the claim immediately before it**, not to the whole sentence. Grade the
  clause the bracket sits behind.
- Naming an illustrative domain is not claiming the cited paper ran that experiment.
- "So in the kitchen, ..." marks a sentence as an APPLICATION of a mechanism established earlier,
  not a claim that the source studied kitchens.
- A source whose author sums up their own criteria in a short phrase may be described by that
  phrase.
- **A well-known fact of the field needs no reference at all**, and two authors reaching
  for the same familiar example is convergence, not borrowing. Where the book leaves comparable
  facts unbracketed nearby, that is its convention: check the neighbours before raising a missing
  key.
- **A named pattern points at whoever named it, once.** It does not need re-attributing at every use.
- A reference at the end of a passage may already cover the passage.

## What this rules out as a method

- **A word-frequency grep cannot decide whether a source holds an idea.** A zero count on a word
  the source phrases differently ("farmers" for "farming") proves nothing. Open the source and
  read around the passage.
- **A bank guardrail is evidence, never authority.** Where a guardrail and the source disagree, the
  source wins, and the guardrail is what needs correcting. Check a proposed guardrail against the
  source before writing it: a false guardrail would put an error into the book.
- **An argument file that grades the book is not a source.** A verdict about the book expires the
  moment the sentence is rewritten; an argument file that still carries it produces a finding against
  text that is fine. `stale-argument-pointer-check.py` finds these.

## Cite ideas, not credentials

An `@Key` attaches to an **idea taken from a work**, never to a work named as a credential. "An
author known for a famous series of books applied..." carries the key on the guideline, and the
famous series stays uncited and out of the reference list. The reference list is a set of
sources for claims, not a reading list: before proposing a new citation, ask what idea it
supplies to the argument. If the answer is "it shows the author is worth listening to", cite
nothing.

The person-introduction pattern shows the rule: "X was a market gardener whose notes on Y became
a foundation..." (uncited), then "X tackled this directly in a short field guide [@Key]" (cited).

**Direct mention or inline reference?** Name the person when their authority matters to the
sentence; use the bracket alone when the source only supports a claim with evidence. Either way
the bracket is present.

## Verdicts, graded against this standard

| Verdict | Meaning |
|---|---|
| VERIFIED | the source holds the idea as the book states it. Say how you verified |
| MINOR ISSUE | the substance is right, a detail is off: a year, a word in a quote, an imprecise paraphrase, a missing qualifier. The fix is small |
| SIGNIFICANT ISSUE | the source does not hold the IDEA, the attribution is wrong, or a quote is materially different. Needs the author |
| UNVERIFIABLE | the source or enough information cannot be found. Say what was tried; that is itself a finding |

A source that holds the idea in different words is VERIFIED, not a SIGNIFICANT ISSUE.
