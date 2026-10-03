# General Review: Full 15-Category Systematic Scan

Self-contained review covering all 15 issue categories that recur across close readings of a manuscript. Use this for a comprehensive scan of any chapter.

**What this review catches:** Every issue type that shows up in practice, from structural problems to formatting violations. Categories are ordered by frequency and impact (the First group first).

**Rule source:** All rule numbers reference the Rules Summary in the write-text skill (`${CLAUDE_PLUGIN_ROOT}/skills/write-text/SKILL.md`, Sections 1-12), with the full text in `${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/rules-explained.md`. Rules marked "per the voice profile" are judged against the book's voice file.

---

## How to Use This Review

0. Read the decisions index (`decisions.py index`, then `decisions.py show ID` for an entry), the glossary and the voice profile first; never report a DECIDED item.
1. Read the chapter once without stopping
2. Re-read the chapter, scanning each paragraph against all 15 categories
3. For each issue found, report using the output format at the end
4. Group issues by section order for easy fixing

---

## First: Check First (Highest Impact)

### Category 1: Restatement Instead of Advancement

**Rules:** 2.13, 2.14, 2.15, 1.5, 11.4 (code examples)

**What it is:** The same idea appears twice or more -- rephrased but not advanced. Includes: adjacent sentences saying the same thing, paragraphs circling one point, summaries replaying sections sequentially, and re-explaining mechanisms from previous chapters.

**Root cause:** Most restatement traces to answer front-loading (Category 3). When the opening gives the answer, every subsequent sentence can only rephrase it.

**Detection criteria:**
- Two sentences that say the same thing in different words within 1-3 sentences of each other
- A paragraph that makes one point but uses 3+ sentences to circle around it
- Summary sections that recapitulate each section sequentially rather than connecting insights across sections
- Re-explaining a mechanism that was fully explained in a previous chapter
- Opening a section by restating what the previous section concluded

**Examples:**
- "Both loaves gain from the same rest, because the dough has time to relax whether the flour is white or whole wheat." -- restates the paragraph above
- "Dough needs a long rest before it goes into the oven..." after already saying "the dough must rest for hours before baking"
- Two adjacent sentences that make the same claim, once as a claim and once through the evidence
- The same phrase ("feeds the soil") appearing in sentence 1 and sentence 3 of the same paragraph
- A section repeating the same idea three times with the same examples
- A later chapter re-explaining a mechanism that an earlier chapter already developed in full

---

### Category 2: Broken Logical Flow / Disconnected Ideas

**Rules:** 2.1, 2.2, 2.3, 4.2, 4.15, 2.12

**What it is:** Sentences or paragraphs that feel disconnected from surrounding context. Ideas that appear without connection to what came before. The reader loses track of what is being discussed and why.

**Detection criteria:**
- A sentence whose subject has no referent in the previous 2 sentences
- Paragraphs that read as a list of statements rather than a developing argument
- "This" or "that" without a clear referent
- A paragraph where ideas jump between topics without connectors
- Reader would ask "where did that come from?" or "why are we talking about this now?"
- Section conclusions that shift framing from the section's actual content

**Examples:**
- "this debate" -- which debate? The referent never appears in the preceding sentences
- A paragraph on spring planting sits next to a paragraph on soil tests with nothing linking them, so the argument jumps
- The second paragraph of an introduction holds several ideas that are not connected to each other
- A paragraph about a family visit is followed by a paragraph about a tax rule, with no transition explaining the move
- The reader reaches the middle of a section and can no longer say what is being discussed or why
- Every paragraph from a given point to the end of the section is a standalone statement, so the passage needs rewriting into a chain of connected ideas

---

### Category 3: Forward Disclosure / Premature Conclusions

**Rules:** 1.3, 2.14, 6.3, 2.12

**What it is:** Revealing the answer before building the argument. Telling the reader what the section will prove before proving it. Disclosing content from future chapters or sections. Opening paragraphs that describe the whole chapter.

**Detection criteria:**
- Section opening that states the conclusion ("This section establishes that...")
- Sentences that preview research evidence before presenting it ("Research confirms...")
- Mentioning terms, principles, or ideas from chapters not yet read
- Summary-like first paragraphs that describe everything the chapter covers
- Transitions that explicitly name the next section's content ("The next subsection shows...")

**Examples:**
- "This section establishes that a late frost erases most of the early planting gains" -- reveals the conclusion before building it
- "Research confirms this strategy reflects expert behavior" -- pre-announces evidence that should arrive naturally
- An opening paragraph that describes the whole chapter, introducing everything at once and leaving nothing to discover
- The same "why this matters" framing opening a third chapter in a row, which reads as defensive
- "The next subsection shows how frost adds another cost" -- mechanical forward reference
- Using a defined term before the section that introduces it

---

## Second: Check Second (Medium Frequency)

### Category 4: Vocabulary Too Complex for Target Audience

**Rules:** 5.4, 5.5, 5.2

**What it is:** General words above the plain (A2) level of Rule 5.4 that block the reader, which matters most when the audience includes readers of English as a second language. Academic register words with simpler synonyms. Uncommon idioms that don't translate well. Flag only what blocks your reader (`hard-words.md`).

**Detection criteria:**
- General words above A2 that a non-native reader would likely not know (a high level alone is not the test: see `hard-words-criteria.md`)
- Academic or literary words with common 1-2 syllable alternatives
- Idioms that require native-speaker cultural knowledge
- Technical jargon from a specific domain (physics, linguistics) used without explanation
- Multi-syllable words where a simpler synonym exists

**Vocabulary reference:** the plain-vocabulary table at the end of `${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/rules-explained.md`.

---

### Category 5: Missing Justification / Unsupported Claims

**Rules:** 2.9, 2.7, 2.16, 4.12

**What it is:** Statements presented as fact without references, arguments, or evidence. Claims that need attribution. Generalizations that feel "naked."

**Detection criteria:**
- A factual claim about how the body works without a citation
- Statements like "research shows" or "studies found" without specific references
- Assertions about common practice in a field without grounding in expert opinion
- Historical claims without dates or sources
- Overstated claims using absolutes ("always," "never," "no one")
- Introducing an expert or their work without explaining why their opinion matters

**Examples:**
- A section makes several claims about papers and books without a single reference, so the claims read as "naked"
- "proven effective" with nothing behind it, which reads as an unconfirmed claim
- "Beginners learn faster with short daily practice" placed after a study is mentioned, without saying whether the study is the source
- A cited source is credited with a distinction the book itself introduced, so the citation attributes a claim the source does not make
- An expert is quoted without introduction, leaving the reader unable to say who they are or why their opinion carries weight
- "an inverse relationship between ability and density" -- ability to do what? The compared quantity is never named
- "twice a week" stated as the common watering schedule, where the frequency is asserted rather than sourced

---

### Category 13: Wrong / Misleading Framing

**Rules:** 2.17, 2.12, 7.1

**What it is:** Text that contradicts the book's own definitions or thesis. Framing that shifts the argument in a direction the author disagrees with.

**Read first:** the glossary, the author's stance (`thinking.stance`) and the decisions index (`decisions.py index`). The author's framing corrections live there.

**Detection criteria:**
- Qualifiers ("true X", "real X") that create a false hierarchy inside a term the book defined broadly
- Framing solutions as failures in a section about identifying problems
- A position the stance file or `decisions.md` rejects, stated as if the book held it
- Vocabulary from the source domain of a metaphor used where the book's own terms are already defined
- Vocabulary only one outside author uses, where the book already names the property

**Examples:**
- "Real saving requires a separate account" -- contradicts a definition of saving as "any money kept back from spending"
- An outside author's label used as a quality word, when the book's own vocabulary already names that property
- A diet justified by weight loss in a book that justifies it by more even energy through the day

---

### Category 7: False Causation / Wrong Connectors

**Rules:** 4.2, 4.15, 4.12

**What it is:** Using "because" where there is no causal relationship. "Which" clauses that misattribute consequences. Connectors that promise a logical relationship that doesn't exist. Comparisons across different domains without a common measure.

**Three-way decision for every "because" clause.** Before flagging, determine which relationship holds:

| Relationship | Test | Correct connector |
|---|---|---|
| Causation: Y is the reason X happens | Remove Y. Does X stop being true? | because, due to, as |
| Characterization: Y describes what X is | Y adds a property or fact about X | which, where |
| Association: Y relates to X but neither causes nor describes it | Y is relevant context | and, yet, while, but |

**Detection criteria:**
- **Characterization disguised as causation:** "Because" clause merely restates or redefines the left-hand descriptor without adding a mechanism. A `because` clause that grounds a descriptor in mechanism, evidence, or rationale IS legitimate causation, even when the left clause uses `is/are/means`. Test: does the right clause add information beyond what the descriptor already implies? If yes, keep `because`. If it only restates the descriptor in different words, switch to `which`. Example of real misuse: "Topic sentences help readability, because they appear at the start of paragraphs" describes WHERE they sit (characterization), not WHY that helps (mechanism).
- **Circular "because":** "Because" clause restates the main claim in different words. "Topic sentences are effective, because stating the subject first helps the reader" restates "effective" as "helps the reader" without explaining the mechanism. The "because" clause must add a reason the main clause did not already contain.
- **Correlation not causation:** "Because" linking two facts that co-occur but one does not cause the other
- **Comparison without common measure:** "While" or parallel structure comparing across different domains (sentence count vs word count, capacity vs time, mechanism vs experience). Both sides must be measurable through the same dimension. If no common measure exists, state each side independently.
- **Vague "which" clauses:** "which suggests something fundamental" -- gestures at meaning without naming it. The "which" clause must name the specific consequence, mechanism, or insight it adds.
- "From this emerges..." where the connection is asserted, not demonstrated

**Examples:**
- "The flaw becomes clear when you read the recipe card, because the oven loses heat each time the door opens" -- reading the card does not make the oven lose heat
- "The harvest came late because the village had a new mayor that year" -- false causation
- "This diet works because good habits are hard to describe" -- the "because" does not explain how the diet works
- "From this observation emerges a principle" -- asserted, not demonstrated
- "which suggests something fundamental about cooking" -- vague "which" clause

**Examples of comparison without common measure:**
- "Paragraphs contain 3-8 sentences, while sentences contain 10-25 words" -- sentence count and word count are different units; "while" implies comparison but these are separate rules at different levels
- Fix: "Both the paragraph limit and the sentence limit serve the reader's limited attention: the paragraph limit caps how long one idea develops, and the sentence limit caps how much each step contains." -- common measure: the reader's attention

---

### Category 11: Vague / Abstract Language ("Fluff")

**Rules:** 4.12, 2.13, 1.4

**What it is:** Phrases that promise substance without delivering. Meta-commentary that tells the reader what to think. Sentences that can be removed without losing information.

**Detection criteria:**
- "Something fundamental about..." -- what specifically?
- "Reveals something important about..." -- what is important?
- "This has implications for..." -- what implications?
- Sentences that describe what the text will do instead of doing it
- "This foundation establishes..." / "This connection explains..." -- meta rather than substance
- Sentences that can be removed without losing any information

**Examples:**
- "which suggests something fundamental about cooking" -- what specifically?
- "which reveals something important about its fundamental nature" -- what is important?
- "The structure has implications for how we plan meals" -- what implications?
- "Out of this necessity emerges a fundamental relationship" -- fluff; neither the necessity nor the relationship is named
- "enabling trust" dropped into a technical passage -- an abstract phrase standing in for a concrete mechanism

---

## Last: Check Last (Lower Frequency)

### Category 6: Term Introduction and Consistency Problems

**Rules:** 2.4, 2.5, 9.5, 9.6, 9.7

**What it is:** Using terms before defining them. Inconsistent terminology across chapters. Terms that a reader can confuse with a common meaning in their own field. Missing formatting conventions.

**Detection criteria:**
- A concept term used before its definition paragraph
- Same concept called different names in different chapters (two near-synonyms the book never equated)
- A term from one corner of the audience used universally (for a cooking book: "mise en place" where "preparing the ingredients" would reach every reader)
- Missing *italic* on first use of a concept term (rule 9.5)
- Abbreviation without expansion ("BMI" before spelling out "body mass index")
- A short form of a defined term that the reader can confuse with a common technical sense

**Examples:**
- "BMI" used without ever connecting it to the full term
- "a two-crop rotation" used before the section that introduces crop rotation
- A new term for a structural idea appears without warning, after chapters that used a different one
- "stock", "broth", and "base" used interchangeably for the same thing across sections
- "interest" used alone, where the reader may read it as the banking sense instead

---

### Category 10: Wrong Paragraph Structure

**Rules:** 3.3, 3.4, 1.5, 2.2

**What it is:** Paragraphs broken at mechanical boundaries rather than idea boundaries. Multiple ideas in one paragraph. Single ideas split across two paragraphs.

**Detection criteria:**
- A paragraph that ends abruptly without a concluding or transition sentence
- Two paragraphs that each contain half of a single comparison or contrast
- A paragraph with 3+ distinct ideas (each needing its own development)
- Mechanical paragraph breaks (by list number, by example count) rather than by idea
- First sentence of new paragraph repeats last sentence of previous

**Examples:**
- Two consecutive paragraphs read as disconnected, and the idea in the first one stops mid-development
- A paragraph break falls at the second or third item of a list rather than at an idea boundary
- A paragraph ends without a conclusion, a transition, or either
- The first two paragraphs of a section make the same argument and belong in one paragraph

---

### Category 8: Overly Complex Sentences

**Rules:** 3.6, 4.3, 4.4, 3.8

**What it is:** Sentences longer than ~25 words with nested clauses. Multiple ideas packed into one sentence. Sentences requiring re-reading to parse.

**Detection criteria:**
- Sentences with 2+ embedded "which"/"where"/"who" clauses
- Sentences combining attribution + quotation + interpretation in one breath
- Noun phrases with 4+ modifiers ("periodic reassessments of household spending at fixed calendar intervals")
- Center-embedded structures (interrupting main clause with subordinate)
- Sentences where subject and verb are separated by 10+ words

**Examples:**
- "The shopping list becomes the only page the helper takes, where each ingredient is named without the steps, for the neighbour at the market, who can buy everything without ever reading the recipe." -- nested where/who
- "The author makes this point in the book when she writes that 'a garden is a promise' and that 'every promise can be broken,' which names what a dry summer costs" -- attribution + two quotes + interpretation in one sentence
- "through periodic reassessments of household spending at fixed calendar intervals" -- abstract noun pile

---

### Category 14: Missing Practical Perspective

**Rules:** 7.1, 3.5, 5.1

**What it is:** Text focuses on theory without connecting to the reader's practice. Missing the author's own experience where the voice profile and positioning call for it.

**Detection criteria:**
- A section that explains an idea but never says how it helps the reader in daily work
- Techniques explained without showing how they help day-to-day practice
- Missing first-person experience where it would strengthen the argument (per the voice profile)
- No mention of what the author has seen in their own work, where the audience file promises it
- Missing an ordered checklist of questions where the reader needs one to apply the idea
- Examples that don't feel real to the book's audience

**Examples:**
- A section covers how a technique helps one goal but never covers the reader's other main goal
- Techniques are presented without saying what each one does for the reader
- "reflects how experienced gardeners actually work" -- a generic appeal where the author's own experience would carry more weight
- An anecdote is told in the third person when it comes from the author's own experience and reads stronger in the first
- A training method is described from the textbook definition rather than from how the author applies it
- A section names the problem but stops before showing how it gets resolved in practice

---

### Category 15: Accuracy Against the Book's Own Definitions

**Rules:** 2.17, 2.9, 2.5

**What it is:** A domain term used in a way the book's own definition does not allow, two mechanisms mixed up, or a process described inaccurately against the glossary.

**Detection criteria:**
- A glossary term used in a sense its canonical definition or its invariants exclude
- Two named mechanisms of the book used as if they were the same
- A mechanism described as conditional when the book says it always runs, or the reverse
- Two frameworks from the field used in one chapter without saying how they relate
- A wording `decisions.md` records as retired (a retired account must not come back by accident)

**How to check:** for each technical term in the chapter, compare its use with its glossary entry and with the decisions (`decisions.py match "<term>"`, then `decisions.py show ID` for each match). Report the sentence, the entry and the difference.

---

### Category 9: Code Example Problems

**Rules:** 11.1, 11.2, 11.3, 11.4, 11.5, 2.15. **Applies when the book shows code** (`${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/technical-books.md`).

**What it is:** Code examples that are unrealistic, incomplete, don't match the point being made, use constructs of one language only, or are repeated across chapters.

**Detection criteria:**
- Missing variable declarations or imports that make the example incomplete
- Examples that add types or layers the point does not need
- Constructs of one language (access modifiers, compilation units) presented as universal
- The same example used with the same explanation in 3+ chapters
- Examples only one part of the audience knows
- Examples that don't show what the text claims they show (e.g., "actual business logic" is missing)
- Using `CustomerFactory.createFrom()` instead of realistic patterns like mapper/converter
- Boolean parameters in examples when the text doesn't discuss that anti-pattern
- Short variable names like `ord_ln_qty` instead of full descriptive names

**Examples:**
- An `errors` collection is read but never created, and nothing is done with it afterwards
- An example claims business logic is buried, but no business logic appears in it
- An extra type or layer appears that the point does not need and the text never explains
- `CustomerFactory.createFrom()` where working code would name a converter or mapper
- The same `checkout` example appears in three chapters of one Part with the same explanation
- A toy example where an example drawn from real production code would carry the point better
- `ord_ln_qty` as an identifier, where the full descriptive name would be readable

---

### Category 12: Specific Style Guide Violations

**Rules:** 9.1-9.9, 4.2, 3.6, 7.3

**What it is:** Direct violations of formatting rules and conventions.

**Detection criteria:**
- When the book uses definition blockquotes: a definition not formatted as one (> prefix)
- When the book shows code: code names not in `monospace` backticks
- Bold used in running text for emphasis
- Sentences under the voice profile's minimum length
- Missing connectors between sentences, measured against the voice profile
- Punctuation the voice profile does not allow (semicolons, exclamation marks, dash pairs)
- Person used against the voice profile ("we", "you", "the reader")
- Summarization tables where prose with connectors would build one coherent picture
- Fronted inversions below the voice profile's floor, measured as a running gap, or two within the profile's paragraph gap

**Examples:**
- When the book uses definition blockquotes: a definition set as plain prose
- Sentences under the minimum length still present after a revision pass
- A table placed right after a definition, repeating what the definition already stated
- A summarization table where connected prose would build one coherent picture
- A fronted inversion whose word order reads as scrambled to a non-native reader

---

## Companion Scripts

Run these before the qualitative pass (`SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"`):

```bash
python3 $SCRIPTS/sentence-and-paragraph-check.py --connectors <file>  # Category 7
python3 $SCRIPTS/sentence-and-paragraph-check.py --meta <file>        # Category 11
```

Calibration: on a mature manuscript, most "because" flags are legitimate causation (a descriptor grounded in mechanism or rationale). Apply the three-way test per flag; do NOT treat every flag as a required fix. On new drafts expect a higher real-misuse rate: the check earns its keep at writing time. Both are recall-first surfacers: expect false positives, scan flags manually.

---

## Output Format

For each issue found, report:

### Issue [N] -- Category [X]: [Category Name]

**Section:** [section number and name]
**Text:** "[exact flagged text]"
**Rule:** [rule number(s) violated]
**Problem:** [why this matches the category -- be specific]
**Suggestion:** [concrete fix: rewrite the sentence, remove, restructure, etc.]

Group issues by section order (as they appear in the chapter), not by category. This makes it easy to fix them in a single pass through the manuscript.

---

## Summary Template

At the end, provide:

### Issue Count by Category

| Category | Count | Notes |
|----------|-------|-------|
| 1. Restatement | | |
| 2. Disconnected flow | | |
| 3. Forward disclosure | | |
| 4. Vocabulary | | |
| 5. Missing justification | | |
| 6. Term consistency | | |
| 7. False causation | | |
| 8. Complex sentences | | |
| 9. Code examples | | |
| 10. Wrong paragraphs | | |
| 11. Vague language | | |
| 12. Style violations | | |
| 13. Wrong framing | | |
| 14. Missing practical | | |
| 15. Accuracy against definitions | | |

### Most Systemic Issues

Which 3-5 categories appear most frequently? These indicate systemic patterns that may have a single root cause (see cascade patterns in the common review workflow).

### Strongest Sections

Which sections had the fewest issues? What makes them work well? This helps the author understand what to preserve.
