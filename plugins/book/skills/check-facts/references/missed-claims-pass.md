# The missed-claims pass

A reading pass whose target is not "claims" but "claims the earlier steps did not produce". It
runs after `uncited-claim-check.py` and after the ordinary extraction read, and it takes both
outputs as the *already-covered* set.

"Find the checkable claims in this chapter" and "find the checkable claims a regex and one careful
read both missed" are different searches and return different things. Asked the first way,
attention lands on claims that announce themselves (a citation, a number, a date). Asked the
second way, it has to go somewhere else.

## Why a pattern detector cannot cover this

`uncited-claim-check.py` finds eight classes and is worth running first: exhaustive within its
classes, and free. But three limits are structural:

1. **Claims with no lexical marker.** "X was a Welsh hill farmer." No number, date,
   cadence word or citation; fully checkable; no regex that would not also match half the book.
2. **The proximity rule cuts both ways.** A claim counts as cited when any citation sits in the
   5-sentence window, whether or not that citation supports it. A date sentence can be suppressed
   by a citation covering a different sentence. The script cannot tell which suppressions are wrong.
3. **Noise filters trade recall for precision.** "Hundreds of X" is skipped when X is not a unit
   (right for "hundreds of visitors", wrong for "a herd counted in hundreds of head"); item
   nouns are skipped in the spelled class (right for "four steps", wrong for "three volumes").

## Input, per chapter

- the chapter text;
- the script's flags for that chapter (**excluded**: already covered). To produce them:
  `${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/uncited-claim-check.py <chapter>`;
- the claims already extracted (also excluded).

Run it as its own agent, given only these and this file. An agent that has just verified a list of
claims is primed by the list.

## What to hunt

| Category | Example shape | Why nothing else catches it |
|---|---|---|
| biographical fact | "X was a Portuguese botanist"; "Y would later receive the royal medal of her society" | no marker; nationality and affiliation are details books get wrong in passing, and readers notice |
| active-voice priority | "X pioneered seed banks for farmers"; "Y, who invented the method" | reads as narration, not assertion |
| superlative | "one of the largest bridges ever attempted at the time" | a claim about everything it ranks against; hard to support |
| universal negative | "no other country adopted it"; never, always, the only | one counterexample falsifies it; high risk, cheap to check |
| a quantity the filters dropped | "a herd counted in hundreds of head"; "three volumes"; "around fifty midwives" | removed by the unit filters on purpose |
| suppressed by proximity | any claim near a citation that covers a different sentence | the script counted it cited |
| attributed position | "X argues that...", "Y saw something deeper" | a characterization of an argument is itself a claim |
| causal narrative | "allotments spread because...", "this led directly to..." | reads as connective tissue; the causal link is usually the author's synthesis |
| edition-pinned fact | "since the 1998 edition the guide allows..."; "since version 2 of the tool..." | an edition or version is a date in disguise |
| population quantifier | "most families", "every nurse" used as fact | a consensus claim without the consensus words |

## How to report

One row per finding. Never report a claim without quoting it, so an invented claim cannot survive
into the report.

```markdown
| Line | Category | Exact sentence (quoted) | Why checkable | Already cited nearby? |
|------|----------|-------------------------|---------------|-----------------------|
```

`Why checkable` is meant to be hard to fill in. "A reader could disagree" is an argument, and
arguments are out of scope. It must name a fact a source could confirm or refute.
`Already cited nearby?` says which citation and whether it plausibly covers the sentence; a "no"
upgrades the finding.

## Calibration

- **The pass must be able to return nothing.** A pass that always finds something is generating,
  not reading.
- **Do not report the author's own experience** as a gap. Mark it `experience` only if the book
  leans on it for a main empirical claim.
- **Do not report arguments.** Verify facts, not reasoning.
- **Do not re-report script flags.** Re-reporting inflates the yield and hides the real finding.
- **Expect a single-digit yield per chapter.** Dozens means it is reporting arguments or flags;
  zero across every chapter means it is not reading.
- Where the missed-claims pass and the verification disagree about a claim, the verification wins.
  When the item could be raised again, suggest a decision in a note; revise-from-notes records it.

## Feeding the detector

When the same category turns up in two chapters, it is a candidate class for
`uncited-claim-check.py`: the expensive reading pass discovers shapes, and the cheap pattern pass
absorbs whichever ones a pattern can express. Record candidates in the run's `Detector
candidates` section. Open candidates, not yet in the script: markdown table cells (the script
blanks table rows), edition- or version-pinned claims, superlatives, population quantifiers
as consensus, temporal spans it misses, universal negatives (with the book's own definitions
excluded), and biographical copulas including the past tense for living people. What no pattern
can express (biography, attributed positions) stays here for good, and that is not a defect.
