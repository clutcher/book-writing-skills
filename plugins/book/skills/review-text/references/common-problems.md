# Common Issues Review

Self-contained review targeting the problems that recur most often in non-fiction drafts. This is the go-to review for any chapter.

**What this review catches:** 6 frequent issues, plus the 4 cross-cutting cascade patterns that connect them. Fixing root causes (cascades) prevents downstream symptoms.

---

## How to Use This Review

0. Read the decisions index (`decisions.py index`, then `decisions.py show ID` for an entry) and the voice profile first. A finding that matches a DECIDED entry is not reported (`decisions.py match`).
1. Read the chapter once without stopping to mark issues
2. Read the Cascade Patterns section below to understand root causes
3. Re-read the chapter, checking each paragraph against the 6 issue categories
4. For each issue found, report using the output format at the end

---

## Cascade Patterns: Fix Root Causes First

Before scanning individual issues, understand how they connect. Four cascades drive the majority of problems. Fixing the upstream cause prevents downstream symptoms.

### Cascade A: Front-Loading Cascade (Most Common)

**Flow:** Answer front-loading (Issue 1) -> development becomes restatement (Issue 2) -> sentences become vague summaries (Issue 5) -> reader loses track (Issue 3)

**How it works:** When a section opens with its conclusion, every subsequent sentence can only rephrase what the reader already knows. The writer feels compelled to "develop" but has nowhere to go. This produces circular paragraphs, vague meta-commentary, and eventual flow breakdown.

**Fix:** Return to rule 1.3. Open with the question, not the answer. Let development build toward the conclusion.

### Cascade B: Example Reuse Cascade

**Flow:** Same example across chapters (Issue 4) -> same explanation repeated (Issue 2) -> reader feels chapter is redundant (Issue 3)

**How it works:** When the same family budget example appears in four chapters with a similar explanation, each chapter feels like it restates the previous. The example itself becomes the vehicle for restatement.

**Fix:** Per rule 2.15, one chapter owns each example fully. Other chapters reference briefly and show what is NEW in this chapter's context.

### Cascade C: Vocabulary-Flow Interaction

**Flow:** Complex word used (vocabulary issue) -> reader pauses to parse -> connector chain breaks (Issue 3)

**How it works:** Individual complex words don't just fail the plain-English test (rule 5.4). They interrupt the adjacency chain. When a reader stops to parse a rare or academic word, the connection to the previous sentence breaks.

**Fix:** Replace hard words with plain equivalents per rule 5.5 (`hard-words-criteria.md` says which words are worth flagging). Check that the simpler word preserves the adjacency chain.

### Cascade D: Wrong Framing Cascade

**Flow:** Text contradicts book's definition (Issue 6) -> argument built on wrong premise -> conclusion doesn't follow (false causation) -> reader confused (Issue 3)

**How it works:** When the text says "real saving requires..." but the book defines saving as "any money kept back from spending," the section builds on a contradicted premise. The conclusion cannot follow from a foundation the reader knows is wrong.

**Fix:** Per rule 2.17, verify each claim against the book's own definitions before building arguments on it.

---

## Issue 1: Answer Front-Loading

**Rules:** 1.3, 2.14

**What it is:** Opening a section or paragraph with the conclusion instead of the question. Disclosing what the section will prove before proving it. Describing the whole chapter in the first paragraph.

**Detection patterns:**

1. **Section opening states conclusion:** "This section establishes that X." Should be: "What does X require?" The opening should pose the question, not give the answer.
2. **Pre-announced evidence:** "Research confirms this strategy reflects expert behavior." Should let the research arrive as evidence without announcing the verdict first.
3. **Chapter preview paragraph:** First paragraph lists everything the chapter covers. Violates discovery-based development.
4. **Mechanical forward reference:** "The next subsection shows how..." Describes the next section's content instead of ending with an insight that leads naturally.
5. **Repeated defensive introduction:** Same "why this matters" framing appearing in chapter after chapter.
6. **Naming before evidence:** Paragraphs before an example or reasoning chain name the cause or mechanism that the evidence will demonstrate. This applies when building new concepts (Rule 2.5), not when working with known ones (Rule 2.6). "The failure comes from the timing" before the story that shows the timing gives the reader the answer before the evidence earns it.

**Test:** Read the section's opening. Does it frame what to explore (question/problem), or does it state what will be found (answer/conclusion)? "What does a late frost cost?" is a question. "A late frost erases most of the early planting gains" is the answer.

**Examples:**
- "This section establishes that a late frost erases most of the early planting gains" -- reveals the conclusion before building it
- "Research confirms this strategy reflects expert behavior" -- pre-announces evidence
- An opening paragraph that lists everything the chapter will cover, leaving nothing for the reader to discover
- "The next subsection shows how frost adds another cost" -- mechanical forward reference
- The same "why this matters" framing opening a third chapter in a row, which reads as defensive

---

## Issue 2: Restatement Instead of Advancement

**Rules:** 2.13, 2.14, 2.15, 1.5, 11.4 (code examples)

**What it is:** Same idea appears twice or more -- rephrased but not advanced. Includes adjacent sentences saying the same thing, paragraphs circling one point, summaries replaying sections sequentially, and re-explaining mechanisms from previous chapters.

**Detection patterns:**

1. **Adjacent restatement:** Two sentences within 1-3 sentences that make the same claim in different words. Test: remove one sentence. Does the paragraph lose anything?
2. **Circular paragraph:** 5+ sentence paragraph where sentence 5 says essentially what sentence 1 said. The middle sentences rephrase rather than advance.
3. **Section recap in summary:** Summary paragraph where each sentence maps 1-to-1 to a section (P1 = section 1 conclusion, P2 = section 2 conclusion). This is recapitulation, not synthesis.
4. **Cross-chapter repetition:** Re-explaining a mechanism that was fully developed in a previous chapter.
5. **Same example, same explanation:** Using the same example (e.g., one family budget) in multiple chapters with the same reasoning.

**Test for sentences:** For each sentence, state what NEW understanding it adds beyond the previous sentence. If you cannot distinguish the contributions, one restates.

**Test for summaries:** If each summary sentence maps to exactly one section, the summary recapitulates rather than synthesizes. Synthesis connects ideas from multiple sections into a whole.

**Examples:**
- "Both loaves gain from the same long rest" -- restates the claim the paragraph above already made
- "A river carries soil to the sea" right after "the current moves earth downstream" -- the second image carries the first one's point again
- A section makes the same point three times, in the same order, with the same example
- A later chapter re-explains a mechanism that an earlier chapter already developed in full
- A chapter summary walks the sections in order and repeats each conclusion

---

## Issue 3: Disconnected Flow

**Rules:** 2.1, 2.2, 2.3, 4.2, 4.15, 2.12

**What it is:** Sentences or paragraphs that feel disconnected from surrounding context. Ideas appear without connection to what came before. Paragraphs read as lists of statements rather than developing arguments.

**Detection patterns:**

1. **Orphaned "this"/"that":** A demonstrative pronoun with no clear referent in the previous 2 sentences. Reader asks "this what?" This includes demonstrative + noun combinations ("these techniques," "those failures") where the noun does not appear in the adjacent previous sentence. The reader cannot follow a reference to something not yet introduced.
2. **List-of-statements paragraph:** Each sentence introduces a new fact or claim, but no sentence builds from the previous. Could be rearranged without breaking logic.
3. **Topic shift without bridge:** A paragraph or section suddenly changes subject without a transition sentence. A connector word alone ("Yet," "But," "However") is not sufficient for a topic shift -- the bridge must explain WHY the new topic follows from the previous one through cause, consequence, or explicit contrast naming both sides.
4. **Conclusion shifts framing:** The section was about X, but the conclusion evaluates Y.
5. **Reader question test:** At any point the reader would ask "where did that come from?" or "why are we talking about this now?"
6. **Implicit jump:** A sentence advances (adds new understanding) but lacks an explicit bridge showing HOW it connects to the previous sentence. The content is correct, the flow is broken. Test: does the sentence contain a connector, back-reference, or bridge phrase? If not, the reader must infer the connection.
7. **Broken seam after edit:** An edited sentence or paragraph disconnects from its neighbors. The fix itself may be correct, but it breaks the chain at the boundary where edited content meets unchanged content. After any edit, read three units: the one before, the edited one, the one after.
8. **Heading treated as logical break:** A section or subsection heading sits between two sentences that would not connect if the heading were removed. Headings are visual separators that help navigation, not logical breaks. The last sentence before a heading and the first sentence after it must connect with the same strength as adjacent sentences within a paragraph.

**Test:** For any paragraph, try rearranging the sentences. If order doesn't matter, the sentences are parallel topics, not a chain. They need restructuring.

**Examples:**
- "this debate" -- which debate? The referent never appears in the preceding sentences
- A paragraph on spring planting sits next to a paragraph on soil tests with nothing linking them, so the argument jumps
- The reader reaches the middle of a section and can no longer say what is being discussed or why
- Every paragraph from a given point to the end of the section is a standalone statement, with no sentence building on the one before
- A paragraph about a family visit is followed by a paragraph about a tax rule, with no transition explaining the move

---

## Issue 4: Example Problems

**Rules:** 2.15, 2.9, 11.4 (code examples)

**What it is:** Examples that are unrealistic, incomplete, do not show what the text claims, speak to only one part of the audience, or repeat across chapters with the same explanation. An example can be a case, a story, a worked calculation, a recipe, a figure or, in a book with code, a code listing.

**Detection patterns:**

1. **Repeated across chapters:** The same example with the same explanation in 3+ chapters.
2. **Does not match the claim:** The text says the example shows a cause, a cost or a turning point, but the example as written does not show it.
3. **Missing pieces:** The reader must guess a step, a number or a fact the example needs. A worked budget that never says the monthly income; a recipe step that uses an ingredient the list never named.
4. **Unrealistic case:** A situation no reader would meet in life or work, where a real one would carry the point.
5. **Examples from one corner of the audience:** examples only one part of the book's audience knows.

**When the book shows code** (see `${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/technical-books.md`), also check:

- variables used without being declared, or read and then never used
- constructs of one language or framework presented as universal, or extra types the point does not need
- names no working code would use (cryptic abbreviations, a factory where a converter is meant)

**Test:** For each example, ask: (a) Can I read this without guessing at missing pieces? (b) Would a reader meet this in real life or work? (c) Does it show exactly what the text claims? (d) Has this same example appeared earlier in this Part?

**Examples:**
- A worked savings plan skips the interest rate, so the reader cannot check the final sum
- A story is said to show a turning point, but nothing in the story changes
- The same family budget appears in three chapters of one Part with the same explanation
- A garden example uses a plant that grows only in one climate, in a book written for readers everywhere

---

## Issue 5: Vague Language / Fluff

**Rules:** 4.12, 2.13, 1.4

**What it is:** Phrases that promise substance without delivering it. Meta-commentary that tells the reader what to think. Sentences that can be removed without losing information.

**Detection patterns:**

1. **"Something fundamental about...":** What specifically? Name it.
2. **"Reveals something important about...":** What is important? State the revelation.
3. **"This has implications for...":** What implications? Name them.
4. **Meta-commentary:** "This foundation establishes..." / "which emphasized the health benefit" -- describes what the text does instead of doing it.
5. **Removal test:** Delete the sentence. Does the paragraph lose any information? If not, the sentence is fluff.

**Test:** For any sentence containing "fundamental," "important," "implications," or "reveals," check whether the sentence names the specific thing it claims to reveal. If the answer is "something," the sentence needs to state what that something is.

**Examples:**
- "which suggests something fundamental about sleep" -- what specifically?
- "which reveals something important about its fundamental nature" -- what is important?
- "The structure has implications for how we plan meals" -- what implications?
- "which emphasized the health benefit" -- meta-commentary on a quote; let evidence speak

---

## Issue 6: Wrong Framing

**Rules:** 2.17, 2.12, 7.1

**What it is:** Text that contradicts the book's own definitions or thesis. Framing that shifts the argument in a direction the author disagrees with.

**Read first:** the glossary (`rules.glossary`), the author's stance (`thinking.stance`) and the decisions index (`decisions.py index`). The author's corrections of framing live there; this workflow does not repeat them.

**Detection patterns:**

1. **Contradicts own definition:** A qualifier ("true X", "real X") that narrows or ranks a term the book defined broadly. Any qualifier that creates a hierarchy contradicts the scope.
2. **Wrong section framing:** Discussing solutions in a section about problems, or vice versa.
3. **Author disagrees with framing:** a position the stance file or `decisions.md` rejects, stated as if the book held it.
4. **Wrong technique justification:** Justifying a technique from a perspective the book does not use for it.
5. **Copied vocabulary:** A term only one outside author uses, where the book's own vocabulary already names the property.
6. **Wrong mechanism:** Naming one mechanism when the text describes another, against the definitions in the glossary.

**Test:** For each claim about a principle, verify it matches the definition given in the chapter that owns that principle. For recommendations, verify against the author's documented positions.

**Examples:**
- "Real saving requires a separate account" -- contradicts a definition of saving as "any money kept back from spending"
- A side effect of a treatment presented as breaking a rule the book says it does not break
- An outside author's label used as a quality word, when the book's own vocabulary already names that property
- A diet justified by weight loss in a book that justifies it by more even energy through the day

---

## Companion Scripts

Run these to surface candidates for the issues above before the qualitative pass:

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"
python3 $SCRIPTS/unclear-this-check.py <file>                   # Issue 3: dangling "This/That/These/Those/The + noun"
python3 $SCRIPTS/sentence-and-paragraph-check.py --meta <file>  # Issue 5: meta-announcements
```

Both are recall-first surfacers: expect some false positives, scan flags manually.

---

## Output Format

For each issue found, report:

### Issue [N] -- [Issue Name]

**Location:** [section number and name, paragraph number]
**Text:** "[exact flagged text]"
**Cascade:** [A/B/C/D if this issue is part of a cascade pattern, or "standalone"]
**Decision:** [the matching `decisions.md` entry and its status, or "none"]
**Problem:** [why it matches the category -- be specific]
**Suggestion:** [concrete fix: rewrite, remove, restructure, or brief replacement text]

Group issues by section order (as they appear in the chapter), not by category. This makes fixing them in a single pass straightforward.

At the end, provide:
1. **Cascade analysis:** Which cascades are active in this chapter? What is the root cause?
2. **Summary count:** How many issues per category.
3. **Priority recommendation:** Which 3-5 fixes would have the highest impact (usually the cascade root causes).
