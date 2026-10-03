# Reading a source before it enters any reasoning

A source can be well designed, well published, and still unusable for the claim you want it for.
The failure is rarely a bad paper; it is **a sound paper carrying one over-broad sentence,
amplified downstream**. Nothing about the source signals it, and a citation count will not either.

## The nine-step check, in order

1. **Is it held, and did someone read it?** A quotes entry with `Verified quotes` over a cached
   file is the only proof. A confidence label with no cache behind it is worse than none.
2. **What was the MATERIAL? Name an example.** A food diary, a meal served in a lab and a
   supermarket receipt are not interchangeable, nor are a practice worksheet and a real lesson. If the paper does not print its stimuli, say so:
   every claim about their shape then rests on a sentence.
3. **What was MANIPULATED, in the paper's own words?** Not what the abstract is about. A study
   read as a test of one variable can turn out to manipulate another.
4. **What was MEASURED, and what was NOT?** Time only, accuracy only, opinion only? A literature
   where every accuracy result favours a treatment and every time result goes against it reads as
   a disagreement until the measure is recorded. Count the dependent variables: a design that
   measures only opinion is a validity threat.
5. **Does the paper's conclusion exceed its data?** Check the Discussion against the Results, and
   look elsewhere in the same paper for a result that cuts against the sentence you want. An
   abstract can state as a finding what its own tests report as non-significant.
6. **Internal consistency**: dfs against stated N, table values against prose, one- versus
   two-tailed tests used consistently. `statistic-integrity-check.py` automates part of this.
7. **Population, and whether the paper claims past it.** Watch for contamination: participants
   taught the tested advice the same week.
8. **Is a null real or underpowered?** Check the power before treating an absence as evidence.
9. **Author and venue are context, never verdict.** Standing does not certify a claim, and its
   absence does not disqualify one.

Steps 1, 6 and part of 2 are scripted. **Steps 3, 4 and 5 are the judgment core and cannot be**:
a reading brief must ask for them by name, or they will not be produced.

**The rule under all nine: a book's own accumulated summaries are less reliable than its sources.**
Summaries drop scope every time they are restated, and nothing records the loss. Open the page.

## Recording what a source is

For every source read, record in its quotes entry:

- **what was measured**: what people did, what people judged (ratings, opinions), an instrument
  reading (a blood test, a scale), or nothing (a model, a review, an essay);
- **the analysed N, never the recruited N**, and the sample type (pupils, patients, volunteers,
  mixed);
- **what went in versus what came out**: an assumption or a premise the design imported cannot
  come out as a result; keep "measured", "assumed or imported" and "out of reach" apart.

## Figures: cite the source that MEASURED it

- A figure belongs to the source that measured it, not to one that repeats it. Label an estimate
  as an estimate.
- A computational model's parameters are not measurements, even when the model paper says they
  were "derived from empirical data".
- A study's design window (a task duration chosen for an experiment) is not a measured duration.
- An abstract-only cache cannot carry a figure the abstract does not print.
- A statistic repeated across several content sites under different years and headlines, with no
  primary document behind it, is the signature of a fabricated figure. One school's case is not a
  country's experience.
- Never derive a number by multiplying two unsupported factors.

## Amount versus kind

Words like "intensity", "exposure" and "dose" usually mean HOW MUCH (a count, a size, a
strength), not WHAT KIND (which type of thing). A study of how much exercise helps does not show
which exercise helps. Check each source against its methods section, never its abstract, before
recruiting it for a claim about kind.

## When your claim is a scope objection to a source

A construct objection that works by finding any dimension of difference will always work, which
makes it a filter rather than a check. Three mechanical rules:

1. **Name the dimension, quote the source's own words for it, and state what result would count
   against your objection.** An objection that cannot fail is not an objection.
2. **Apply it to favourable sources with the same force as to adverse ones.** If a second source
   takes its key variable from the first, either both bear on the claim or neither does.
3. **Never extend a catch about one study's stimuli to a sibling paper you have not opened.**

A render is cheaper than an argument: open the page before building the case.

## Claims of absence

- State a gap claim only in the **narrowest form** each held study leaves standing.
- A negative based on a literature census is **bounded by the census's own inclusion criteria**
  (its years, its fields, its search terms); say so.
- A result relayed by a secondary paper is an **acquisition target**, never a citation.
- Treat a missing source as **a trace, not a null**: follow the citation chain behind a stated rule
  to its end, so the negative survives a challenge.
- Before borrowing another field's word for an idea the book uses ("stress" in nursing, "load" in
  sports science), check that it means the same thing there.
- An argument from silence ("no source states X") prohibits claiming X; it never refutes X.
- An OpenAlex title-and-abstract search that returns zero is a failed query, not a null; a broad
  term such as "balance" returns noise from unrelated fields.

## Identity traps

- The same author and the same year can be a different work: check the title, not the key.
- One reference line can resolve to two works.
- A quote absent from the work it is attributed to may be **misattributed rather than fabricated**:
  search the author's other works before calling it fabricated. Quote anthologies turn paraphrases
  into quotation marks, so every anthology quote is checked in the primary text.
- An argument file with zero bracket keys escapes every holdings tool; check such files by author and
  year too, and beware author-year false matches.
- "Marked unverifiable" and "checked and wrong" are different states: mark, do not delete.
