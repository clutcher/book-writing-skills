# Hard-Words Review: Term Introduction for the Least Experienced Reader

Catches terms that **materially block** the least experienced reader the book targets from following the argument. The threshold is blocking, not polish: if the reader pauses briefly but the paragraph's conclusion still lands, that is not a hard-words gap. The chapter reviews (common-problems, flow, all-problems) catch prose issues; cross-chapter review catches consistency issues; this review catches the narrow case where a term's first use lacks the context that reader needs to continue reading.

Findings go where every review's findings go: one note per finding in the book's notes folder, with a `From:` line (`${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/note-format.md`). The paragraph walk and the triage stay in a run folder under the book's runs folder (`work.runs`). Items the author decides need no action become `decisions.md` entries when the note is answered, so no later run raises them again.

## Target Audience

The audience comes from the book, not from this skill. Read the audience section of the book's audience file (`thinking.audience`). It should say who the least experienced reader is (for a gardening book, for example: "someone who has kept a few pots on a balcony but never planted a bed") and give two lists:

- **What that reader knows** (do not flag): the basic vocabulary of the field at that level, including words that look technical but are standard for them.
- **What that reader may not know** (candidates for flags): the specialist vocabulary, named frameworks and historical figures outside broad circulation.

Do not flag a term from the first list unless the paragraph needs more than its basic sense. The second list is guidance, not exhaustive: the paragraph-centric review below decides whether a given use is a real gap. If the audience file has no such lists, ask the author for them before a full run and record them there.

## Relationship to Other Reviews

- `common-problems` / `all-problems`: prose style and structure. This review is term introduction only.
- `consistency`: terminology drift (same term, different usage across chapters). This review is term introduction (does the first use have enough context?).
- the **review-ideas** skill: content critique -- are the claims correct? This review is audience fit -- can the least experienced reader follow?

Hard-word issues overlap style issues when a term appears without any gloss in its first uses -- that is both a style Rule 2.4 violation and a hard-words problem. Both reviews flag it, from different angles.

## How to Run It

Every run writes into its own run folder, `<work.runs>/<YYYY-MM-DD-HHMM>-review-text-hard-words/`, made with `python3 ${CLAUDE_PLUGIN_ROOT}/lib/run_folders.py start review-text hard-words --fix` (it prints the folder and keeps only the newest three hard-words runs). `--resume` finds the stopped run with `run_folders.py latest review-text hard-words`; `--only-changed` gets its chapters from `run_folders.py changed review-text hard-words`. At the end, `run_folders.py record <run folder> <chapters read> --fix` writes the checksums the next `--only-changed` run compares against.

| User input | Scope |
|---|---|
| `hard-words` | the whole book |
| `hard-words <chapter file>` | one chapter, when the author names it |
| `hard-words --only-changed` | only the chapters changed since the last hard-words run; that run's chapter files are the baseline |
| `hard-words --resume` | continues the newest hard-words run that stopped, in its own folder, skipping chapters already done |

There is no recheck run. The revise-from-notes skill reads the text again before each note and removes a note whose problem is already gone.

**The baseline.** The decisions recorded for earlier hard-words notes are the baseline for MATCHED-BASELINE and REGRESSION. revise-from-notes puts the mode name `hard-words` in the keywords of every decision it records for a note whose `From:` line names this mode, so `decisions.py match "<term>"` finds them. With `--only-changed`, the last run's `hard-words-chN.md` files are a second baseline. Items already decided in `decisions.md` are never raised, in any run.

## Output Structure

```
<runs>/
+-- YYYY-MM-DD-HHMM-review-text-hard-words/
|   +-- hard-words-summary.md                  # summary: totals, regressions, cross-chapter findings
|   +-- hard-words-ch1.md                      # per-chapter: paragraph walk + triage
|   +-- hard-words-ch2.md
|   +-- ...
```

- **hard-words-summary.md** -- summary for the run. Totals by severity, regressions (if any), cross-chapter patterns, and a list of every affected chapter with a link to its per-chapter file.
- **hard-words-chN.md** -- per-chapter detail: the chapter's paragraph walk (see below) and the triage of every candidate.

Run folders are work state: they can be deleted, and they are not in git.

## Findings become notes

Every HIGH, MEDIUM and REGRESSION item becomes one note in the notes file of its manuscript file, with `**From:** review-text hard-words, <run time>`, the paragraph quoted word for word, the flagged sentence as Text, the issue as Note, and the suggested fix in Options. Get each id with `open-notes.py next-id <file>` (`${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/open-notes.py`). NO-ACTION and MATCHED-BASELINE items stay in the run folder only.

When the author answers a note, revise-from-notes records the decision with `hard-words` in its keywords (its rule for notes from a skill and mode), so a later run finds it with `decisions.py match`.

## Execution Pattern

### All chapters

Parallelize across chapters. One subagent per chapter, each producing one `hard-words-chN.md`. After all chapters complete, a merge step builds `hard-words-summary.md` and writes the notes.

Each per-chapter subagent receives:
- The chapter file path.
- the command `decisions.py match "<term>"` for prior-introduction lookup (it finds the hard-words decisions), and `decisions.py show ID` to open one.
- With `--only-changed`: the prior run's `hard-words-chN.md` for comparison.
- The workflow file path.

### One chapter

Run directly without parallelization.

## How to Review Each Chapter

The review is **paragraph-centric, not term-centric**. Terms do not flag themselves -- paragraphs either deliver their argument to the least experienced reader or they don't. The loop walks the chapter paragraph by paragraph; candidate terms are identified only when a paragraph has an unclear spot that careful reading does not resolve.

This matters because a term-list scan produces false positives in bulk: it flags every technical word regardless of whether the surrounding sentence defines it, whether the list context makes recognition unnecessary, or whether a following clause supplies the meaning. Paragraph-centric review filters at the source -- a term that is glossed inline, or sits as one of several parallel examples, never enters the candidate list in the first place.

### Step 1: Paragraph walk

Read the chapter paragraph by paragraph. For each paragraph:

1. **Read it once.** What is this paragraph arguing? State the conclusion in one phrase.
2. **Ask the least-experienced-reader question.** Imagining the least experienced reader the audience file names, can they follow the argument to the conclusion? Not "do they know every word" -- *can they follow the argument*.
3. **If yes, move on.** Do not list terms from this paragraph. No flag.
4. **If no, identify the specific sentence or phrase that blocks the reader.** This becomes a candidate.

A shorter candidate list built from careful paragraph reading is better than a long list that requires heavy triage. If you find yourself listing every technical term in a section, step back -- you are scanning, not reading. Return to the paragraph and ask whether the argument *actually* fails to land, not whether a term is unfamiliar in isolation.

### Step 2: Adjacency-gloss check

For each candidate, scan +/-3 sentences around the flagged term (including into the next paragraph if the term falls near a break) for any of the following forms of inline explanation:

- **Colon-definition.** `the water table: the level below which the ground is full of water...`
- **Parenthetical gloss.** `crop rotation (planting a different family of plants in each bed every year)`
- **Explanatory clause.** `which means`, `that is`, `defined as`, `in other words`, `i.e.`
- **Italicized-term + next-sentence definition.** `*compound interest*. Compound interest adds each year's interest to the sum before the next year's interest is worked out...`
- **Quoted source with embedded explanation.** The quoted excerpt explains the metaphor within the quote itself.
- **Concrete walkthrough.** The paragraph gives a worked example that shows the term's meaning in practice (`proofing -> the shaped dough sits for an hour and doubles in size before it goes into the oven`).
- **Positional definition.** Term placed alongside siblings in a way that defines each by position: `a sprain hurts the band that joins two bones, a strain hurts a muscle, and a fracture is a break in the bone itself`.

If any of these are present, default to **NO-ACTION** unless you can articulate a specific, concrete blocker -- in one sentence, what that reader cannot do after reading the adjacent gloss. "They still might wonder what X means in general" is not a blocker. "The paragraph's conclusion requires a fact the gloss does not supply" is.

### Step 3: Prior-introduction check

Term introduction is a *whole-book* property. A term introduced with a gloss in Chapter 1 can appear bare in Chapter 8 as long as the concept is still live for the reader. Before escalating any remaining candidate:

```bash
grep -n -i "<term>" <manuscript>/*.md | head -20
```

Also check `decisions.md` for the term (`decisions.py match "<term>"`).

Three outcomes:
1. **First use is in this chapter, nowhere earlier.** Normal triage applies.
2. **Earlier chapter introduces the term with a proper gloss.** NO-ACTION, note the prior introduction: `"first introduced in ChN:LL with mechanism description; back-reference implicit."`
3. **Earlier chapter uses the term without a gloss.** Flag the prior location, not this one.

### Step 4: Executed paraphrase test

For each candidate that survives adjacency-gloss and prior-introduction checks, perform the paraphrase test *by actually substituting*:

1. Write out the sentence with the term replaced by a plain-language paraphrase.
2. Re-read the paragraph including the substituted sentence.
3. State: does the conclusion still land?

The output of this test must include the actual substituted sentence. Without the substitution shown as evidence, the flag is not valid.

**Example (NO-ACTION):** (the sentences below are invented for illustration)

- Original: *"the baker raises the dough on a levain rather than on packet yeast."*
- Substituted: *"the baker raises the dough on a starter of flour and water kept alive from day to day rather than on packet yeast."*
- Re-read paragraph: conclusion ("the bread rises more slowly but stays fresh for days longer") still lands.
- Verdict: NO-ACTION. The adjacent sentence already supplies the gloss, and the paraphrased version preserves the argument.

**Example (HIGH):** (invented; the name and figure stand in for a real cited source)

- Original: *"Alex Doe showed in a field trial that mulched beds lose about 30 percent less water over a dry summer."*
- Substituted: *"[someone] showed in a field trial that mulched beds lose about 30 percent less water..."*
- Re-read paragraph: the claim lands, but the reader has no anchor for why to trust the trial. The paragraph treats the finding as load-bearing evidence; authority matters here.
- Verdict: HIGH. Credential fix needed on first mention.

### Step 5: Citation type distinction

For expert/person citations, classify first:

**(a) Bare bibkey, no prose name.** `[Abc99]`, `[BC01]`, `[DEF+05]` -- citation only, no appeal to authority. Skip Rule 2.7 analysis entirely; this is a bibliographic reference, not a credential claim.

**(b) Named in prose.** "<Author> defines...", "<Author> and <Author> demonstrated..." -- person attributed in the sentence. Apply Rule 2.7 check (full name on first mention, credential tied to substantive contribution).

For (b), also apply the load-bearing removal test:

1. Delete the person's name and any authority-claim phrase (`X showed that`, `X argues`, `According to X`).
2. Re-read the sentence. Does the argument still hold because the paragraph supplies data, a quote, math, or logic that grounds the claim?
3. If yes, the citation is **decorative** -- attribution, not authority appeal. NO-ACTION on the credential. A name without a credential is fine here.
4. If no -- if the argument now reads as a bare claim with nothing grounding it -- the citation is **load-bearing**. A credential is required.

Both worked examples below are invented; the names, titles, and bibkeys are placeholders for whatever the manuscript actually cites.

**Worked example (decorative, NO-ACTION):**

- Original: *"Rita Alvarez and Sam Ng, authors of* The Patient Garden*, coined the term dry margin [Abc99]."*
- Removed: *"The term dry margin was coined in* The Patient Garden *[Abc99]."*
- Argument still holds -- the book is a concrete reference; the authors' credential is decorative.

**Worked example (load-bearing, flag):**

- Original: *"Alex Doe showed in a field trial that mulched beds lose 30 percent less water over a dry summer [Def01]."*
- Removed: *"A field trial showed that mulched beds lose 30 percent less water over a dry summer [Def01]."*
- Argument weakened -- the specific trial result's credibility was carried by the named authority. Load-bearing -> credential needed.

### Step 6: Heuristics that default to NO-ACTION

Three patterns that routinely produce false positives. If the candidate matches any of these, default to NO-ACTION unless the adjacency-gloss check found a real gap.

**Pattern-name handle.** A named pattern (a standard method of the field, a coined term, or a trade term) with nearby explanatory text is a handle, not a gap. If the prose explains what the pattern does -- through an example, a quoted definition, or a mechanism sentence -- the name is just a label the reader can hold onto. Only flag when the name appears with no nearby explanation at all.

- Pattern names the book borrows from a cited source, where the quoted excerpt that accompanies the name supplies its meaning.
- For a cooking book, for example: roux, emulsion, braise -- basic training covers these at the name level.
- Terms the book coins itself, where the surrounding paragraph explains the structure the term names.

**Example-list item.** When the term is one of 2+ parallel examples making the same point, the reader needs to recognize *one* for the argument to land -- not all of them. Do not flag individual items in such lists.

(Invented illustrations of the shape, not quotes from any manuscript.)

- "one country taxes savings when the interest is paid, another when the money is taken out, a third not at all" -- three parallel tax rules. A reader who knows one gets the point.
- "a late frost, a dry May, a week of hail" -- three examples of "weather that ruins an early crop." Any one familiar example carries the argument.
- "one shop adds a delivery fee, another a card fee, a third a service charge at the till" -- three examples of the same hidden-charge pattern.

Only flag if the argument specifically requires identifying *this* item. A flag here should answer: "why does the paragraph fail to land if the reader skips this particular example?"

**Symmetric-treatment baseline.** If the subject of the flag is treated the same way as an adjacent similar subject that you accept, the flag is a field-insider artifact, not a gap for the least experienced reader.

- One author cited as "in *<book title>*"; two lines later, a second author cited as "co-author of *<book title>*." Both are name + book, in the same role, in the same argument. If the second treatment passes, so does the first.

### Step 7: Severity

- **HIGH** -- a reader who skips the term cannot reconstruct what the paragraph just argued. The argument collapses, not merely slows. Fix required before the chapter ships to review.
  - For person citations: authority is load-bearing (removal test fails) and the credential does not establish why to trust this source.
- **MEDIUM** -- the argument lands from surrounding mechanism, but the reader is **materially slowed**. "Materially slowed" means the reader must make a second pass at the sentence, or must back-reference to an earlier chapter they haven't seen yet, or must keep an unexplained term in mind through subsequent sentences that depend on it. Not simply "could be clearer."
  - Bias toward NO-ACTION when ambiguous. Every technical paragraph has terms a reader could pause on; that is not the threshold.
- **NO-ACTION** -- the gloss is adjacent, the term is illustrative, the reader can paraphrase successfully, or the usage matches one of the heuristic patterns above.
- **MATCHED-BASELINE** -- current finding lines up with an item `decisions.md` already holds as no-action or deferred. Applies whenever such entries or a prior run exist. With neither, it does not apply.
- **REGRESSION** -- a previously-fixed item where the fix was removed or weakened. Highest-priority output.

**Severity anchors** (use these shapes to calibrate; the situations are illustrative, not drawn from any particular manuscript):

*HIGH example.* A chapter names an author bare while leaning on that author's benchmark for a specific percentage figure. Removal test fails: without the named authority, the number has no grounding anywhere in the paragraph. The reader cannot evaluate whether to trust the finding. -> HIGH. Fix: add credential inline.

*MEDIUM example.* A chapter uses "APR" in one sentence and "APR figures" in the next without ever expanding the acronym to "annual percentage rate." The two paragraphs that follow depend on the APR/APY distinction. The reader can follow the first sentence but must back-reference to figure out which sentence defined which acronym. Materially slowed, not blocked. -> MEDIUM. Fix: add `(APR)` and `(APY)` on first use.

*NO-ACTION example (adjacent gloss).* A chapter uses a medical term of art that it never defines outright, but the very next sentence describes what that condition does in plain words. The gloss is adjacent and sufficient. -> NO-ACTION.

*NO-ACTION example (method-name handle).* A chapter names a farming method through a metaphor, and the quoted excerpt that immediately follows spells out what the metaphor means. -> NO-ACTION. Method name with nearby explanation.

*NO-ACTION example (bare bibkey).* A chapter cites `[Abc99]` at a "farmers in several regions arrived at the same method on their own" claim, with no author named in prose. The citation is a bibliographic reference, not an authority appeal. Rule 2.7 does not apply. -> NO-ACTION.

*NO-ACTION example (institution-level attribution suffices).* A chapter refers to "two nurses at a large city hospital" for a claim about where a practice originated. Institution + era + citation carry the weight for the reader; individual names add no anchor. -> NO-ACTION.

When ambiguous between HIGH and MEDIUM, a mechanism-sentence structure around the term is the strongest signal toward MEDIUM. A bare term in a load-bearing sentence with no surrounding mechanism and a failed removal test is the strongest signal toward HIGH.

## Item Numbering

Inside a run, number items by chapter (`H8.1`, `M8.2`) so the summary can point at them. The lasting id is the note id the item gets when it becomes a note.

## Chapter Numbering Drift

After a structural restructure (chapters split, merged, renumbered), the chapter numbers in the item IDs no longer point to the same text. Before flagging regressions, build a numbering map at the top of the summary:

```markdown
## Numbering map

- Old Ch8 -> current Ch8 Sec 8.1-8.3 + current Ch9
- Old Ch9 -> current Ch10
```

Walk each fixed item forward through the map and verify the gloss still lives in the migrated text.

## Per-Chapter Report Format (`hard-words-chN.md`)

```markdown
# Hard words -- Chapter N -- <YYYY-MM-DD>

Run: [all chapters | one chapter | --only-changed | --resume]
Baseline: [path to prior run, or "fresh baseline"]

## Paragraph walk

One-line note per paragraph with the conclusion it argued and whether the least-experienced-reader question returned yes or no. Example:

- Sec N.1 para 1 -- argues that X causes Y; the reader can follow. Clean.
- Sec N.1 para 2 -- argues that Z mechanism explains W; "construal level" flagged as candidate (Step 1).
- Sec N.1 para 3 -- argues consequence of para 2; clean.

## Candidates triaged

For each candidate that passed Step 1:
- Term and location (`ChN:line`).
- Adjacency-gloss check outcome (what was found +/-3 sentences, if anything).
- Prior-introduction check outcome.
- Paraphrase test output -- **must include the substituted sentence**.
- Citation type (bare bibkey vs named-in-prose) for expert references.
- Load-bearing removal test output for named-in-prose expert references.
- Heuristic matches (pattern-name handle, example-list, symmetric treatment).
- Final verdict (HIGH / MEDIUM / NO-ACTION / MATCHED-BASELINE).

## Regressions

(Previously-fixed items where the fix was removed or weakened. Zero is valid.)

**R1** ChN:line -- term -- what was fixed, what is now, suggested restoration.

## HIGH

**HN.k** ChN:line -- term
- Issue: why the argument collapses without the fix (one-sentence concrete blocker).
- Suggested fix: concrete replacement or gloss.

## MEDIUM

**MN.k** ChN:line -- term
- Issue: what forces the reader's second pass (one sentence).
- Suggested fix: concrete replacement or gloss.

## No-action summary

Count of candidates downgraded at each step (adjacency-gloss, prior-introduction, paraphrase, citation-type, heuristics). This shows where filtering happened.

## Matched baseline

- ChN:line -- term -- matches `decisions.md` entry D-<n> (reason still holds).
```

## Summary Report Format (`hard-words-summary.md`)

```markdown
# Hard words -- <YYYY-MM-DD>

Run: [all chapters | one chapter | --only-changed | --resume]
Scope: [all chapters | chapter-N | chapters: X, Y, Z]
Baseline: [path or "fresh baseline"]
Notes written: N

## Numbering map

(Only if restructured since baseline.)

## Totals

| Category | Count |
|---|---|
| Regressions | N |
| New HIGH | N |
| New MEDIUM | N |
| Matched baseline | N |
| Clean chapters | N |
| Paragraphs walked | N |
| Candidates raised | N |
| Candidates filtered at Step 2-6 | N |

## Regressions (cross-chapter)

## Cross-chapter patterns

## Per-chapter links

- [Chapter 1](hard-words-ch1.md) -- N HIGH, N MEDIUM
- [Chapter 2](hard-words-ch2.md) -- N HIGH, N MEDIUM

## Follow-up
```

## Integration with Other Tools

- Run `sentence-and-paragraph-check.py` first -- paragraph/sentence issues often hide hard-word issues.
- After a fix lands, re-run `sentence-and-paragraph-check.py` on the modified file because added glosses can push sentences over the voice profile's maximum.
- When a fix lands, revise-from-notes records it as DECIDED / changed and removes the note; a later run checks it only for a regression.
