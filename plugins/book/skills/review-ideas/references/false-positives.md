# False-positive patterns

One list, used by Stage 2 before it reports a finding, by Stage 3 before it classifies one as VALID, and by the verification pass. Each pattern is a common way a review produces a confident, wrong finding. If a finding fits a pattern, it is NOISE; name the pattern.

Most false positives share a common root: the finding was raised from the flagged sentence in isolation, without reading the book's surrounding rhetorical structure. Patterns FP-1, FP-2, FP-4, FP-5, FP-7, FP-8 all manifest under-reading of context. Patterns FP-3 and FP-6 manifest challenging an external claim without verifying what the external source actually says.

**FP-1: Temporal anchors misread as dating risk.** When flagging "this will date," separate two cases:
- (a) The claim's truth depends on dated facts staying true. Real dating risk.
- (b) Dated facts are used as examples or anchors for an argument whose truth does not depend on them, and the text generalizes past the specifics ("Whether in two years or fifteen...", "regardless of which tool...", "this pattern has repeated across every era"). Not a dating risk -- the temporal detail is evidence for a transcendent argument, and a future reader reads it as a historical snapshot that reinforces the general claim.

Check the surrounding paragraph (often the concluding sentence of the section) for the generalizing move before flagging.

**FP-2: Definition tension that dissolves into goal-vs-technique.** When flagging that a term is used differently across chapters, check whether one chapter explicitly distinguishes the goal from the techniques that achieve it. If chapter X says "Y is a technique for achieving the goal, not a definition of the goal," then later chapters referring to Y by name are not redefining the goal -- they are invoking the technique. This is not tension; it is the book's own framing. The same applies to other goal/tool pairs: purpose/mechanism, outcome/practice, quality/discipline.

**FP-3: Causation overclaim judged by trial standards for observational research.** When flagging "causes" / "causal" as overclaim, read the methodology the book describes in the same paragraph. Observational causal inference has a standard threshold:
- Temporal precedence (cause measured before effect)
- Baseline control (rules out confound by prior level of effect)
- Reverse-direction test (rules out reverse causation)
- Confounder adjustment

If the book describes this methodology and then says "causes," the claim is calibrated to the evidence. Do not apply randomized-trial standards uniformly to observational research.

**FP-4: The unit that governs the flagged text went unread.** Before reporting anything, identify the
specific unit that governs it and read that unit. The unit differs by what is flagged:

| Flagged thing | Unit that governs it |
|---|---|
| a sentence or an absolute rule | its paragraph, then the rest of the section and chapter |
| an attribution ("X is cited for Y") | the chapter's citation list -- grep it before asserting |
| a code listing, tree, or diagram | the prose that introduces and maps it |
| a claim's vocabulary | any book-wide ruling retiring or reserving that vocabulary: at Stage 2, the invariants in the glossary report and the manuscript's own rulings; at Stage 3, also the book's decisions (through `decision-matches.md`) |

This is the most common false positive. Typical shapes: an attribution
disproved by one grep of the chapter's citation list; an "overclaim" already scoped by the second
half of its own sentence; a listing-continuity finding answered by three sentences of connecting
prose; and a whole argument made in vocabulary the book had formally retired book-wide. In each
shape the disproof is one sentence or one grep away.

When flagging a "never X", "always Y", "is a separate phase" type of rule, search the same section and the rest of the chapter for named alternatives, scoped exceptions, and qualifying clauses. Authors often state a rule forcefully, then qualify it in the next paragraph, later in the same chapter, or in the chapter summary. The qualifier may be 50+ lines away from the rule. Your objection "but what about case Z" may be exactly what the qualifier addresses. Trace the qualifier through a specific Z before flagging.

**FP-5: Universal reduction claim flagged for insufficient examples.** When flagging "all X reduce to Y" as overclaim because only N examples were shown, check whether the claim is a synthesis (one principle reveals a pattern across a catalogue) or a proof (each case must be individually verified). Books teach principles through representative examples that span the conceptual space, not exhaustive enumeration. If the shown examples cover the catalogue's distinct categories (e.g., one root crop, one leaf crop and one fruiting crop from a vegetable guide; or one case from each school), the synthesis holds for the remainder by the same mechanism. Flag only if the unexamined cases genuinely would not fit, not because fewer than N were shown.

**FP-6: Primary source misrepresentation claimed without verification.** When flagging that a book misrepresents a cited paper (e.g., "the actual finding was graded, not binary," "the author never actually said that"), verify against the primary source before classifying. In Stages 2 and 3, which read only the manuscript, check the book's own bibliography entry and what the manuscript itself quotes; if that cannot settle it, mark the finding for the verification pass, which reads the book's cached sources and its quotes bank (`sources.library`, `sources.quotes`). Never judge a paper from its abstract. Do not characterize research findings from memory. A common failure mode: the reviewer remembers a general methodological caveat about the field (e.g., "small diet studies are usually underpowered," "historical attributions are usually contested") and applies it to a specific paper whose actual finding or attribution was stronger. If the primary source explicitly supports the book's framing, the finding is NOISE regardless of the reviewer's intuition about the field.

**FP-7: Textbook opposing argument cited without testing whether it still holds.** When flagging that the book "doesn't engage argument X" from the opposing camp, do two checks before classifying as VALID:
1. Does argument X still hold under modern conditions that the book's chapter assumes? An argument that was strong in an earlier technological or research era may be much weaker now. The book may have legitimately set aside a historical argument because its premise no longer holds.
2. Does the book's existing text accommodate the argument implicitly via a carve-out or scope qualifier? A book's rule plus carve-out may handle the opposing argument's real use cases even without naming the argument.

If the opposing argument is weaker today than when it was canonical, or if a carve-out already handles its real use cases, classify as NOISE. Flag only if the argument still holds AND the book's text has no accommodating clause.

**FP-8: Caveat established once, flagged as missing in later cross-references.** When flagging that a claim's qualifier (e.g., "I have observed," "in my experience," "within this framework," "as defined above") is "dropped" in later usages, check whether the later usages are cross-references to the authoritative location where the qualifier was given. A book that establishes a framework in chapter X with an honest caveat, and then refers to that framework by its name in later chapters ("the X that chapter X ranked most dangerous," "the Y established above"), is not dropping the caveat -- it is invoking the framework by its established name. Requiring re-caveating on every usage makes prose defensive and tedious. Flag only if the later usage drops the label word that cues the reader to the framework and asserts the claim as absolute fact about the world rather than a position within the framework.

**FP-9: Synthesis chapter pre-empts the finding.** When flagging an earlier chapter for overreach, scope creep, or unsupported scaling, check the book's synthesis chapter (typically the final chapter or the Part wrap-up). Books with a definitional or unifying final chapter often commit to a position book-wide that the earlier chapter prefigures in scaled-down form. If the synthesis chapter explicitly establishes the position the finding attacks, and the earlier chapter is invoking that book-wide position within its own scope (e.g., a Part-wrap claim that reads as universal but corresponds to the synthesis chapter's later unification), the finding is NOISE. The earlier chapter is allowed to state its Part-thesis with rhetorical strength when the book as a whole earns the claim. Flag only if the synthesis chapter does NOT commit to the position or if the earlier chapter overreaches beyond what the synthesis itself argues.

**FP-10: A prior fix judged absent because the prescribed wording is absent.** When checking whether
an agreed fix landed, search for the **concern**, not for the wording the fix plan prescribed. A
concern is often resolved in a form the plan never named: by rewriting the passage that created it,
by a ruling that the proposed device would misrepresent the book, or by unrelated work that removed
the premise. Finding none of the prescribed text and concluding "never landed" produces a confident,
wrong, high-severity finding. Verify by asking whether the *objection* still holds against today's
text, not whether the *prescription* appears in it.

**FP-11: The finding repeats a decision the book already made.** `decision-matches.md` lists every
finding that matches an entry of the book's `decisions.md`. A finding that matches a DECIDED entry
is not reported and not argued again: to dispute it, cite the entry in one sentence. A finding that
matches `OPEN / fix owed` is reported only as a regression check of the agreed fix, and one that
matches `OPEN / decision owed` only as a reminder that an answer is owed. Never propose, as a fix,
an option the entry says was rejected. A match is a lead: read the entry's text in the table before
applying it.

**FP-12: A word judged without asking what job the sentence does.** Before calling a word choice
drift, decide what the sentence uses the word for. The same term can be legal as a *description*
of a problem or a result and illegal as the *criterion* that decides it (for example, a cookbook may
let "salty" describe how a dish turned out, while ruling that only the weight of salt decides how
much goes in). Flag only the job the book's rule forbids.
