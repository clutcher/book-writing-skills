# Rules for lenses and skeptics

These rules hold for every agent in the review: lens agents in Stage A, skeptics in Stage C, and
the orchestrator in Stage D.

## The fixed process

1. **Try to prove yourself wrong.** Every blocker and major finding is checked again against the
   passage it quotes, with one question: "what is the strongest case that this is wrong?" A
   finding that does not survive is killed. No false finding reaches the author.
2. **Say how you know.** Every finding carries one tier:
   - `checked-in-text`: can be checked inside the manuscript (consistency, drift, a code
     desk-check).
   - `source-verified`: the cited source was fetched and read.
   - `recall-based`: depends on memory of outside works. It is hedged, never stated as fact.
3. **Truth before sales.** When the soundness of the main argument and the book's sales pull in
   different directions, soundness wins. Market advice shapes framing, never truth.
4. **Steelman both ways.** Before attacking an argument that goes against common practice, state
   its strongest version and judge it by its own logic, not by whether it agrees with the usual
   view. The same duty runs toward the book: before confirming "these passages contradict each
   other", build the strongest single reading under which all of them agree, using the whole
   text. Confirm only if no such reading exists on the page.
5. **No hidden gaps.** Log which sources were fetched and which code blocks were desk-checked
   (if the book has code), and which were only sampled. Less coverage is stated, never dressed up
   as full coverage. Known risk, stated once for a book with code: code is checked by reading
   only, so compile errors can survive. Every code finding is therefore capped at
   `checked-in-text`.
6. **See the whole book.** Some problems only show across chapters (the argument's path, a
   definition that drifts, a device that fades). Every lens agent and every skeptic reads the
   whole manuscript, start to end, before writing.
7. **Framing gate** (thesis and argument findings). Before writing or verifying such a finding,
   answer three questions in writing:
   - (a) Is the flagged sentence governed by a nearby limit, a sentence that explains how it
     works, or a model the book states elsewhere?
   - (b) Is it a problem the book sets up on purpose and solves later by showing, not by
     defending?
   - (c) Would the proposed fix add defensive text that answers a question the book never asks?

   A yes to any of them is stated inside the finding. A fix shaped like (c) is never proposed.

## Decided items

Read the `## Index` of `decisions.md` before the book, then the entries a finding touches.
What each status allows:

| Status | What you may do |
|---|---|
| DECIDED (any of the three) | Do not report it. If you think the decision is wrong, cite the entry in one sentence. Do not argue it again. |
| OPEN / fix owed | Say in `## Agreed fixes from earlier rounds` whether the fix landed. If it did not, or only in part, also report it as a **regression check** finding. Cite the entry. |
| OPEN / decision owed | Mention it only as a reminder that an answer is owed. Do not argue the options again. |
| OPEN / undiscussed | Report it normally, and cite the entry so its history comes with it. |

A finding that proposes, as its fix, the option an entry already rejected is not a finding.

**A skeptic's verdict is not the author's ruling.** "Killed" means the finding failed this check.
It does not make the item DECIDED in `decisions.md`. Only the author decides, when the findings come
back as notes and revise-from-notes answers them.

## Severity

- `blocker`: a real reviewer or reader will hit it, and it damages the book's credibility. Fix
  before print.
- `major`: likely to be hit, real damage, fixable now.
- `minor`: real, low impact.
- `nit`: mechanical, fixable in a batch.
- `strength`: Lens 9 only. Something to protect.

Severity follows the kind of damage. Damage to sales is lower than damage to credibility, and a
lens's weight caps what it can file. A packaging finding is never a blocker.

## Priority

**priority = how likely a real reader or critic is to hit it × how much damage it does × how
fixable it still is now.**

The last factor decides. Big rebuilds are off the table at this stage, but a broken main argument
is still reported, as a hidden risk: "here is the risk; decide whether to fix it before
print." A blocker that is cheap to fix is exactly the one most worth reporting.

## Verdicts

A skeptic returns exactly one verdict per finding:

- `confirmed`: the charge holds **on the merits**, against the book's own stated model, not only
  "a critic could quote this".
- `downgraded`: real, but less severe than filed. Give the new severity.
- `killed`: does not survive. Killed findings never appear in the report and never count.
- `rebuttable-misreading`: a hostile reviewer could quote it, but the text as written answers
  it. Reported as reviewer risk, with fix `none` by default. Never a blocker.

Write the verdict on its own line in the record: `**Verdict:** confirmed`. The status script reads
that line.

## Rules for every skeptic

- **Search every quoted line before it goes further.** A lens can quote a line that does not exist
  in the book, for example a line from an example the book marks as bad.
- **Read the full source, not the abstract.** A lens working from an abstract, or behind a
  paywall, can call a claim unsupported when the full text supports it. A fix that would make the
  book less accurate is killed.
- **Test every "never".** A claim that something is absent ("the book never defines this") is
  tested by searching every place it could be, before verifying anything else.
- **A finding the book cites holds only at the scale the source measured it.** A dose measured in
  a one-week trial says nothing about ten years of use; a result from one school says little about
  a whole country.
- **A general disclaimer in one chapter does not cover a claim where it is used.** It also cannot
  repair a claim the source does not make in any field. Moving a finding across fields is one
  question; misreporting the source is another.
- **Read the source's own limits.** A paper cited for "the effect holds for everyone" may contain
  the analysis that limits it to one group.
- **Search for the concern, not for the wording.** A finding says "the book never explains X".
  Search for the idea in any words, not for the finding's own phrase.
- **Read the whole unit that governs the sentence:** the paragraph, the section, any book-wide
  ruling in `decisions.md` about the words used. A sentence read alone can look wrong when its
  paragraph already limits it.
- **A whole-book style problem needs a counted checklist,** not another general pass: "cut the
  summary sentence that opens these N sections, rewrite these N chapter openings".

## Trust in the sources for the reviewer

The sources for the reviewer (`sources/sources-for-reviewer.md` in the room) is a list of neutral sources.
Its links and its bibliographic data can be used as they are. Its comments on what a source means
are leads only: confirm them against the fetched source before they change any verdict, in either
direction.

## Minor citations

Minor and nit findings skip Stage C. But a wrong fact in print is permanent. The orchestrator may
propose **one** batched fact-check agent for all `recall-based` minor citation findings, and the
author decides at the Stage C gate.
