# Writing and Rewriting

This workflow applies the style guide to write new content or rewrite existing content. Writing and rewriting use the same rules. The only difference is whether you compose from scratch (Step 3a then Step 4a) or transform existing text (Step 3b then Step 4b). Both paths converge at verification and validation.

---

## Step 1: Load the rules and the voice

The one-liners of every rule are in `SKILL.md`, which is already in context. Before writing:

- Read the book's **voice profile** (`rules.voice`, or `profiles/default.md`). Rules marked "per
  the voice profile" take their form and numbers from it.
- Read the decisions index (`decisions.py index`) and open the entries for the chapter or
  topic (`decisions.py show ID`): a decided wording or a rejected option is not yours to change.
- For any hard case, read the full rule in `references/rules-explained.md`: a connector or causal
  word (4.2 three-way test), a coined term (3.9-3.14 and `coined-terms.md`), a person's name
  (2.7), naming before evidence (1.3, 2.5).

The steps below cite rules by number ("Rule 4.2 three-way causation test", "Rule 2.2 chain
table", "Rule 5.5 plain vocabulary"). The Step 6 scripts are a backstop for what scripts can
catch, not a substitute for applying the rules while you write.

---

## Writing in the thinking files

The thinking files (`thinking/`: stance, audience, argument and doubts files) are notes from the
author to the author and to the skills. They are never printed. The same loop holds there: plan,
draft, show, apply. What changes:

- **Rules that still hold:** the word and sentence rules of Sections 4 and 5 (plain words, one
  word per concept, honest causal words), the book's glossary and coined terms, and truth over
  punch: a claim in an argument file must survive a fact-check like a claim in a chapter.
- **Rules that do not hold:** the paragraph and sentence length limits of the voice profile, the
  topic-development-conclusion shape of a chapter paragraph, and the opening and summary rules of
  a chapter. A list, a short note or a one-line claim is fine.
- **The checks:** `${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py text <thinking file>` runs the same scripts;
  `sentence-and-paragraph-check.py` skips its length limits for every file in the thinking
  folders, and the other checks apply as they are.
- **Citations:** every `[Key]` in a thinking file must be in the sources list, as in the
  manuscript (`run-checks facts`).

---

## Step 2: Choose your path

Decide which path matches the request by the size of the change:

- **Micro-edit (word or phrase)** -- swap a word, fix punctuation, rename one term, tighten a clause without changing its idea. Go to **Step 3c (Micro-edit path)**. This path applies every rule that bears on the change; it skips only the paragraph-planning that cannot apply to a single word.
- **Writing new content** -- a fresh paragraph, section, or chapter from a prompt or outline. Continue with **Step 3a (Plan structure)** then **Step 4a (Draft)**.
- **Rewriting existing content** -- transforming text the user pasted, fixing flagged paragraphs, applying reader notes, tightening a draft at sentence level or larger. Skip to **Step 3b (Diagnose violations)** then **Step 4b (Fix)**.

The writing and rewriting paths converge at **Step 5 (Verify)** and **Step 6 (Validate)**. The micro-edit path uses a named subset of those, described in Step 3c.

If a request names a single word or phrase, it is a micro-edit. If it is ambiguous about scope (e.g., "improve this paragraph"), treat it as a rewrite -- a paragraph is not a micro-edit.

---

## Step 3c: Micro-edit path (word or phrase)

A one-word change does not get a paragraph-structure table, because there is no chain of paragraphs to plan. It still gets every rule that touches the change. The point of this path is to apply that rigor at the right size, so the change is neither skipped nor buried under ceremony built for sections.

**Step 3c.1: Check the change against the rules.** Check the new word or phrase against the Rules Summary and the two lookup tables in `rules-explained.md`: plain vocabulary (Rule 5.5), ASCII only (Rule 9.1), the punctuation the voice profile allows (Rule 4.16), names (Rule 2.7), term consistency with the book's glossary and decisions (Rule 2.4), and the formatting rules for terms and code identifiers (Rules 9.5-9.9). The one-liner is enough for most word-level edits.

**Step 3c.2: Read the full section for a hard-case token.** If the word you are touching is a connector or causal word (because / which / so / while -- Rule 4.2), a coined term (Section 3 density rules), or a person's name (Rule 2.7), read that rule's full section in `rules-explained.md` before changing it. These are the words whose one-liner is not enough to apply correctly, and where a "small" change does the most damage.

**Step 3c.3: Make the edit, then check the seam.** A word change can break the chain to its neighbors even when the word itself is right: a swapped connector can invert a causal link, a renamed term can dangle a later demonstrative. Run the post-edit seam check from Step 5: read the sentence before, the edited sentence, and the sentence after as a sequence, and confirm the connectors and references still hold in both directions.

**Step 3c.4: Validate.** Run only the validators the change can affect (Step 6): `ascii-normalize.py` always; `sentence-and-paragraph-check.py --connectors` if a connector changed; `term-density-check.py` if a coined term changed; `unclear-this-check.py` if a term a later sentence refers to changed. Skip the rest -- a punctuation fix does not need the full structural suite.

After the seam check and validators pass, the micro-edit is done. Do not run Steps 3a-4b; they are for content that has structure to plan.

---

## Step 3a: Plan structure (writing path)

Before writing, analyze the section's idea flow to ensure each paragraph follows from the previous in a logical chain rather than sitting side by side as parallel topics.

**Step 3a.1: Identify the core idea.** Find the single insight from which everything else flows. For example, "bread needs strong dough" leads to "strength comes from time" leads to "a slow overnight rise beats extra kneading."

**Step 3a.2: Map the paragraph chain.** For each planned paragraph, ask: "Does this follow FROM the previous, or is it a topic shift?" If rearranging paragraphs would not break the logic, the ideas are parallel topics, not a chain. Parallel topics need restructuring or moving to separate sections.

**Step 3a.3: Check idea size.** If an idea requires substantial development (examples, evidence, sub-points), it needs its own section. Mentioning a big idea briefly without development leaves readers hanging. Either develop it fully or move it where development fits.

**Step 3a.4: Check previous chapters.** Before explaining a concept, check if earlier chapters already cover it. If covered, use a brief back-reference: "An earlier chapter showed that a reward has to come soon after the action." Do not re-explain -- duplication wastes reader attention and creates maintenance burden when content diverges.

**Step 3a.5: Create paragraph structure table.** Before writing, create a table showing each paragraph's idea and its connection to the previous:

| P | Idea | Connection |
|---|------|------------|
| 1 | Why do most new habits fade within a month? | Topic -- poses question |
| 2 | A habit holds only when cue -> action -> reward repeats, because the reward is what teaches the cue | Answers question |
| 3 | What a cue is: the moment that starts the action | Develops "cue" from P2 |

If "Connection" column shows topic shifts rather than logical connections ("From X follows Y"), restructure before writing.

**Step 3a.6: Count content steps per paragraph.** For each planned paragraph, count the distinct steps of understanding it will contain. Each step must add something the previous did not. If a paragraph is planned at six sentences (inside the voice profile's range, Rule 3.4) but has only three content steps, the extra sentences will become restatement. Develop each step further with reasoning, arguments, or connections until the content steps match the sentence count.

**Step 3a.7: Present the plan to the user before drafting.** Show the paragraph structure table and get approval before writing any prose. Idea-level changes (reordering paragraphs, adding a missing idea, removing a weak one) are cheap. Paragraph rewrites after drafting are expensive because every sentence-level connection must be rebuilt. If the user adjusts the plan, update the table and re-verify connections before proceeding to draft.

---

## Step 4a: Draft sentence by sentence (writing path)

When writing new content, the process begins with understanding context: what chapter or section is this for, what comes before it, and what comes after it. The draft must apply the Topic -> Develop -> Conclude pattern at every level (Section 1 of the style guide), which means starting each unit by stating what it explores rather than what it concludes.

### Pre-Draft Checks (before writing each paragraph)

These checks prevent structural problems that are expensive to fix after drafting.

**Single-idea statement.** Before drafting a paragraph, state its ONE idea in one sentence. If you cannot state it in one sentence, the paragraph is trying to do too much and should be split. The idea is not the topic ("this paragraph is about retries") but the claim ("retries turn a short outage into a long one when every client retries at once"). Every sentence in the paragraph must develop this single idea. (Rule 3.3)

**Paragraph boundary connection.** Before starting a new paragraph, read the previous paragraph's last sentence. The new paragraph's first sentence must connect FROM that sentence as if they were adjacent sentences in the same paragraph. Paragraph breaks and section headings are visual separators, not logical breaks -- they do not weaken the connection requirement. If the previous paragraph ends with idea A and the new paragraph opens with idea B, the first sentence must explain why B follows from A. A paragraph that could be rearranged without breaking the logic is not connected. (Rule 2.2)

### During-Draft Checks (while writing each sentence)

**Connection validity.** Write each sentence starting from its connection to the previous sentence. Place the connector first, then add the new content. Connectors include discourse markers ("This means," "Because," "Yet," "So"), demonstrative references ("This difference," "The source," "Such scopes"), questions, and other connection techniques from Rule 2.2. Connectors are how each sentence establishes its place in the chain, not decoration added after drafting; how many and which ones is set by the voice profile. If you cannot find a connector, the sentence either restates the previous (no new understanding to connect to) or belongs elsewhere (topic shift). (Rule 4.2)

**Demonstrative reference antecedent.** When using "these X," "those X," "this Y," or "such Z" as a connector, the referenced concept X/Y/Z must appear in the adjacent previous sentence. "These techniques" requires the word "techniques" (or a clear synonym) in the sentence before. If the antecedent is missing, the reference is dangling and the reader cannot follow it. Either introduce the concept in the previous sentence first, or replace the demonstrative with an explicit noun phrase that stands on its own. (Rule 2.2, 12.2)

**Topic shift bridge.** When a sentence shifts to a different topic from what the previous sentence discussed, a connector word alone ("Yet," "But," "However") is not sufficient. The sentence must explain WHY the new topic follows from the previous one through an explicit logical bridge: cause ("because"), consequence ("which is why," "which means"), or contrast that names both sides ("X addresses one problem, but Y addresses another"). Without the bridge, the reader sees two adjacent ideas with no reason to be adjacent. (Rule 2.2)

After completing the draft, go to **Step 5: Verify**.

---

## Step 3b: Diagnose violations (rewriting path)

When rewriting existing content, identifying which specific rules the content violates preserves meaning better than wholesale rewrites. Before touching the text, scan it section by section against the style guide.

For each section of the rules in `SKILL.md`, list the violations you find. Use the rule numbers so the fix in Step 4b targets the specific rule:

**Section 1 (Structure):**
- Does each unit follow Topic -> Develop -> Conclude? (Rule 1.1)
- Is the answer front-loaded instead of the question? (Rule 1.3)
- Does development explain WHY through reasoning, or just restate? (Rule 1.4)
- Does the conclusion synthesize across sections, or recapitulate one section? (Rule 1.5)

**Section 2 (Flow):**
- Does each sentence build from the previous (chain test, Rule 2.2)?
- Are terms defined before use (Rule 2.4-2.6)?
- Are persons introduced before quoting, with the full name at first mention and later names per the voice profile (Rule 2.7)?
- Are claims grounded with [Abc99] citations (Rule 2.9)?
- Does each sentence add NEW understanding, or restate (Rule 2.13)?
- Does the opening pose a question, or state the answer (Rule 2.14)?

**Section 3 (Limits):**
- Sentence length inside the voice profile's range (Rule 3.6)?
- Paragraph length inside the voice profile's range (Rule 3.4)?
- One idea per paragraph (Rule 3.3)?
- At most one level of self-embedding in a sentence (Rule 3.8)?

**Section 4 (Prose Style):**
- "Because" used for characterization where "which" belongs (Rule 4.2 three-way test)?
- Right-branching clauses, or center-embedding (Rule 4.3)?
- Subject and verb close together (Rule 4.4)?
- Fronted inversions at the voice profile's rate, as a running gap, never two within the profile's paragraph gap (Rule 4.5)?
- Authoritative voice, no hedging "perhaps"/"it seems" (Rule 4.10)?
- Punctuation the voice profile allows (Rule 4.16)?

**Section 5 (Audience):**
- Plain (A2) vocabulary for non-technical words (Rules 5.4-5.5)? Common violations: "utilize" -> "use," "facilitate" -> "help," "commence" -> "begin." The full list is in the plain vocabulary table of `rules-explained.md`.
- Basic idea first, nuance after (Rule 5.3)?

**Sections 6-12 as applicable:**
- Forward references (Rule 6.3)?
- Headings frame questions / name concepts (Rule 8)?
- ASCII only (Rule 9.1)?
- Term consistency with book glossary (Rule 12.2)?
- Container-term drift: a new container word for things the book already names (`vocabulary-rules.md`; the book's watch list is `terms.watch_words.container_terms`)?

Group violations by sentence or paragraph so fixes batch together rather than rippling across multiple revisions.

---

## Step 4b: Apply fixes (rewriting path)

The rewrite must keep the same ideas while fixing the structural problems, which means expanding with more reasoning rather than adding new ideas when sentences or paragraphs are too short. For a sentence under the voice profile's minimum, expand with the explanation of WHY or join it with a related idea using a connector like "which" or "because." After applying fixes, verify against the specific rules that were violated to confirm the rewrite resolves the problems.

**Fixing paragraph length must follow idea boundaries, not mechanical counts.** The paragraph range serves the "1 idea per paragraph" rule (Rule 3.3), so fixes must respect idea structure rather than simply splitting at the maximum or combining adjacent short paragraphs. Often no new prose is needed at all: moving a paragraph break to the idea boundary fixes both neighbours.

For paragraphs under the minimum, first determine whether the paragraph contains a complete idea that needs more development or an incomplete fragment that belongs with another paragraph. If underdeveloped, expand with more reasoning or evidence. If a fragment, combine it with the paragraph whose idea it supports.

For paragraphs over the maximum, first identify how many distinct ideas the paragraph contains. If multiple ideas exist, split at the idea boundary where the topic shifts, ensuring each resulting paragraph has its own topic sentence. If only one idea with extensive development, find a natural subdivision such as "problem vs solution" or "mechanism vs implications" and split there with appropriate transitions. Never split mechanically at the maximum.

**Always show rewrites in context.** When presenting a rewritten paragraph, include the previous paragraph's last 1-2 sentences and the next paragraph's first 1-2 sentences. This makes chain breaks at paragraph boundaries visible before the user has to ask.

**When processing reader notes, preserve the reader's framing.** The reader chose their words for a reason. Express the reader's idea in their framing first ("the second cost is harder to notice"), then find the best linguistic form. Do not reinterpret into a different framing ("the first cost is the more visible one"): the reinterpretation may be technically similar but feel wrong to the reader because it shifts the perspective. Do not add sentences to repair an announcement sentence; cut or rewrite the announcement.

After applying fixes, go to **Step 5: Verify**.

---

## Step 5: Verify (both paths)

After drafting or rewriting, run the full verification checklist before presenting to the user:

1. **Chain table:** Build a table for each paragraph (Rule 2.2). Check that every sentence adds new understanding, connects via explicit connector, and builds FROM the previous sentence's conclusion (not just references the same concept).
2. **Causation audit:** For every "because" clause, verify true causation using the three-way test from Rule 4.2. If the relationship is characterization, switch to "which." If association, switch to "and/yet/but."
3. **Comparison audit:** For every comparison (using "while," "more than," "less than"), verify both sides use a common measure. If comparing across domains (capacity vs time, mechanism vs experience), restructure through a shared dimension like reader experience.
4. **Word count:** Count words per sentence against the voice profile (only the recognized exclusions of Rule 3.6 may run shorter, and that tolerance is chapter- or section-wide, not per paragraph). Count sentences per paragraph against the profile.
5. **Vocabulary check:** Scan every non-technical word for plain (A2) level. Common violations: "utilize" -> "use," "subsequently" -> "then," "approximately" -> "about" (the plain vocabulary table of `rules-explained.md`). Compound adjective modifiers ("two-to-three-hour-long") -> split into separate clause. A replacement word must itself be plain (`${CLAUDE_PLUGIN_ROOT}/skills/review-text/references/hard-words-criteria.md`).
6. **Paragraph boundary check:** Read the previous paragraph's last sentence, the draft, and the next paragraph's first sentence as a sequence. Verify chains hold at paragraph boundaries. Check that no demonstrative reference ("these X") lacks its antecedent across the boundary.
7. **Adjacency after rewrite (rewriting path only):** Rewriting a sentence or paragraph can break the chain to its neighbors. Check that the rewritten content still builds from the adjacent previous and sets up the adjacent next. Read the previous sentence/paragraph, then the rewritten content, then the next sentence/paragraph as a sequence to verify the chain holds in both directions.

Present at most 2 fully vetted options, in the format of `presenting-changes.md`. Do not present drafts that have not passed all applicable checks.

---

## Step 6: Validate (both paths)

Run the scripts listed in `SKILL.md` under "The text checks". The minimum set after any writing or rewriting task (`SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"`):

```bash
python3 $SCRIPTS/sentence-and-paragraph-check.py <file>               # sentence and paragraph limits
python3 $SCRIPTS/sentence-and-paragraph-check.py --connectors <file>  # connector misuse
python3 $SCRIPTS/ascii-normalize.py <file>                            # non-ASCII (then --fix)
python3 $SCRIPTS/unclear-this-check.py <file>                         # dangling "This/That/These/Those/The + noun"
python3 $SCRIPTS/word-for-two-things-check.py <file>                  # container-word drift
python3 $SCRIPTS/term-density-check.py                                # when a coined term was touched
```

When the text contains citations, run the check-facts skill's reference checks as well.

If any script reports violations, return to Step 4a or Step 4b to fix them, then re-run Step 5 and Step 6 until clean.

---

## Why this workflow is structured as passes

The style guide spans Sections 1-12. Reading every rule and trying to apply all of them simultaneously during drafting is the same overload a reader feels when a sentence asks too much at once. The pass structure mirrors how human writers actually work and how the review-text modes (common-problems / flow / all-problems) split their work:

- **Step 1 (Rules)** confirms the rules are already in context (they load with `SKILL.md`) so subsequent steps can reference them by number.
- **Step 3 (Plan or Diagnose)** focuses on structure-level rules (Sections 1, 2, 6 of the guide) without sentence-level concerns yet.
- **Step 4 (Draft or Fix)** focuses on sentence-level rules (Sections 2, 3, 4) during composition.
- **Step 5 (Verify)** is a targeted re-pass against the specific rules most likely to slip during drafting.
- **Step 6 (Validate)** catches what automated scripts can detect (limits, ASCII, demonstratives, containers, term density).

Each pass holds a smaller subset of rules in active attention, which is why the split exists.
