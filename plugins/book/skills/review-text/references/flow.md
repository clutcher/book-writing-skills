# Idea Flow Review

Self-contained review focused on the logical flow of ideas at every level: chapter, section, paragraph, and sentence. This review checks whether ideas build in necessary order, whether adjacency chains hold, and whether the T-D-C pattern is applied correctly.

**What this review catches:** Broken adjacency chains, premature conclusions, restatement disguised as development, weak transitions, summaries that recapitulate instead of synthesize, and forward disclosure.

**For a paper** (`kind: paper`): a chapter here is one section of the paper, and the rules a
paper turns off ("A book or a paper" in the write-text `SKILL.md`) are not findings.
For a paper the abstract and the conclusion are the opening and the summary checked in
Sections 4-5, and a pointer to a later section by number is not forward disclosure.

---

## How to Use This Review

0. Read the decisions index first (`decisions.py index`, then `decisions.py show ID` for an entry); a finding that matches a DECIDED entry is not reported.
1. Read the chapter once without marking issues
2. On second read, check each section against Section 1 (T-D-C Pattern)
3. On third read, check paragraph-level and sentence-level adjacency (Section 2)
4. Check transitions between sections (Section 3)
5. Check openings and summaries specifically (Sections 4-5)
6. Check for forward disclosure (Section 6)
7. For each issue found, report using the output format at the end

---

## 1. T-D-C Pattern at Every Level (Rules 1.1-1.5, 6.4-6.6)

The book uses a single recursive pattern: Topic -> Develop -> Conclude. Check that it applies at every level.

### Chapter Level

- **Topic (opening):** Does the chapter open by posing a question or problem WITHOUT stating the answer? The opening should frame what to explore, not what will be found.
- **Develop (body sections):** Does each section advance the argument? Does each section build on the previous? Is the order necessary (rearranging would break logic)?
- **Conclude (summary):** Does the summary synthesize across sections into a new whole, or does it replay each section's conclusion sequentially?

### Section Level

- **Topic (first paragraph):** Does the first paragraph state what this section explores? Does it end with a question or tension that the section will resolve?
- **Develop (middle paragraphs):** Does each paragraph advance the section's argument? Does each paragraph build from the previous paragraph's conclusion?
- **Conclude (final paragraph):** Does the final paragraph synthesize the section's development? Does it end with an insight that leads naturally to the next section?

### Paragraph Level

- **Topic (first sentence):** Does the first sentence state what this paragraph addresses?
- **Develop (middle sentences):** Does each sentence add NEW understanding not present in the previous?
- **Conclude (final sentence):** Does the final sentence synthesize or transition?

### What to Flag

- Opening that states the answer: "This section establishes that X" (should be "What does X require?")
- Section without clear T-D-C: body paragraphs that sit side by side rather than building
- Summary that recapitulates: each summary sentence maps 1-to-1 to a section (P1 = S1, P2 = S2)
- Paragraph without topic sentence: reader cannot predict what the paragraph addresses
- Missing conclusion: paragraph trails off without synthesis or transition

---

## 2. Adjacency Chains (Rules 2.1-2.3, 2.13, 4.15)

Every sentence builds from the adjacent previous sentence and sets up the adjacent next. Every paragraph builds from the adjacent previous paragraph. This creates a chain where each link connects in both directions.

### Sentence-Level Chain

**Primary method: chain table.** Build a table for each paragraph:

| # | Sentence (shortened) | New understanding | Connector from previous |
|---|---|---|---|

This table reveals three kinds of problems at once: empty "Connector" cells show missing connectors (Rule 4.2), indistinguishable "New understanding" rows show restatement (Rule 2.13), and fewer distinct content steps than sentences shows filler that needs development with reasoning, arguments, or connections. Build the table first, then use the checks below for anything the table does not catch.

For each sentence, check:

1. **What does this sentence add?** State the NEW understanding not present in the previous sentence. If you cannot distinguish it from the previous sentence's contribution, it restates.
2. **Does it build FROM the previous?** The sentence should take what the previous established and advance it. **Independence test:** Remove S1 entirely. Does S2 still make sense on its own? If yes, S2 does not build from S1. Shared references (e.g., "This structure...") create the appearance of chaining, but two sentences that reference the same concept while making independent claims about it are parallel, not chained.
3. **Does it explicitly bridge to the previous?** The sentence must show HOW it connects, not just advance. A sentence that adds new understanding but lacks a visible bridge creates an implicit jump (Rule 2.2, bridge test). Check: does the sentence contain a connector, back-reference, or bridge phrase that signals its relationship to the previous sentence?
4. **Does it set up the next?** The sentence should end with something the next sentence can build from.

**Restatement test:** Three sentences that rephrase "a dry summer lowers the river" are one sentence of content with two restatements. Each sentence must advance.

**Wrong (restatement disguised as building):**
"A dry summer lowers the river. The water level drops week after week, which leaves the banks exposed. Because the summer is dry, the river is low."

Each sentence says "dry summer -> low river." Connectors create the appearance of flow, but no sentence advances beyond the first.

**Right (actual building):**
"A dry summer lowers the river. Because the water is shallow, it warms faster in the sun, and warm water holds less oxygen. The fish gather in the few deep pools, which means one hot week can kill a whole stretch of them."

S1 states the low water. S2 adds what the low water does. S3 adds where the fish go and what that costs.

### Paragraph-Level Chain

For each paragraph transition, check:

1. **Does this paragraph build from the previous paragraph's conclusion?** The first sentence of paragraph N must explicitly connect to the last sentence of paragraph N-1 through a connector, back-reference, or bridge phrase. An implicit topic shift -- even when the new paragraph advances -- breaks the chain.
2. **Is the connection logical?** "From X follows Y" vs a topic shift.
3. **Is the order necessary?** If two paragraphs could be swapped without breaking logic, they are parallel topics, not a chain.

### Post-Edit Seam Check

After any sentence or paragraph edit (rewrite, insertion, deletion, or reordering), verify both seams:

1. **Upstream seam:** Does the edited content explicitly bridge to what comes before it? Read the previous sentence/paragraph's conclusion, then the edited content. Is the relationship visible?
2. **Downstream seam:** Does what follows explicitly bridge from the edited content? Read the edited content's conclusion, then the next sentence/paragraph. Is the relationship visible?

This check matters because review fixes often focus on the edited content in isolation. The fix itself may be correct, but it breaks the chain at the seams where edited content meets unchanged content.

**Test:** After every edit, read three units: the one before, the edited one, and the one after. Check bridges at both boundaries. If either bridge is implicit, add an explicit connector or back-reference.

### What to Flag

- Sentence that adds no new understanding beyond the previous
- Sentence that advances but lacks an explicit bridge to the previous (implicit jump)
- Connector ("which," "because") linking a restatement rather than an advancement
- Paragraph whose first sentence has no explicit connection to the previous paragraph's conclusion
- Sequence of paragraphs that could be rearranged without breaking logic
- Supporting arguments that cluster in parallel around the central claim instead of chaining sequentially
- Broken seam after an edit: edited content disconnected from its neighbors
- Dangling demonstrative reference: "these X," "those X," or "this Y" where X/Y does not appear in the adjacent previous sentence. The reader cannot follow a reference to something not yet introduced.
- Topic shift with connector-only bridge: a connector word ("Yet," "But," "However") links two sentences about different topics without explaining WHY the new topic follows. The bridge must include the logical reason (cause, consequence, or explicit contrast naming both sides), not just a discourse marker.

---

## 3. Section Transitions (Rule 2.2)

Section and subsection headings are visual separators that help the reader navigate, but they do not break the sentence chain. The last sentence before a heading and the first sentence after it must connect with the same strength as any two adjacent sentences within a paragraph. Read them as if the heading were not there -- if the connection breaks, the flow is broken regardless of the heading.

### Check Each Transition

For each section boundary:

1. **Does the first sentence after the heading connect from the last sentence before the heading?** Read them as adjacent sentences. If the connection would fail within a paragraph, it fails across a heading too.
2. **What type of connection?** Transitions, signposting, conceptual continuation, building on conclusion, question, or contrast.
3. **Is the transition natural?** Does the previous section's final insight lead naturally to this section's first sentence?
4. **Are transitions varied?** Avoid starting consecutive sections with "The previous section..."

### Connection Techniques (from rule 2.2)

- **Transition:** Explicitly reference previous content ("This limit has consequences...")
- **Signposting:** Announce structure ("Three factors contribute...")
- **Conceptual continuation:** Start with next idea when connection is obvious
- **Build on conclusion:** Use previous conclusion as starting point
- **Question:** Open with a question the section answers
- **Contrast:** "While X..., Y..."

### What to Flag

- Missing transition: section starts a new topic with no connection to what came before
- Mechanical transition: "The next subsection shows how..." (describes content instead of connecting ideas)
- Abrupt transition: section ending that doesn't set up what comes next
- Repetitive transitions: same technique used for 3+ consecutive section boundaries
- Topic shift within a section without a bridge sentence

---

## 4. Opening Quality (Rules 1.3, 2.14)

Openings at every level must pose the question, not state the answer. This is the most important flow rule because answer front-loading causes cascading problems.

### Chapter Opening

- Does the first paragraph frame the central question the chapter explores?
- Does it avoid listing everything the chapter will cover?
- Does it avoid stating the conclusion?
- Does it make the reader curious about the answer?

### Section Opening

- Does the first paragraph of each section frame what the section explores?
- "What does X require?" (good: poses question)
- "This section establishes that X" (bad: states conclusion)
- "X is important because Y" (bad: gives the answer)

### Cognitive Basis

Front-loading the topic (rule 1.3) activates the reader's prediction mechanism: they know what to look for. Front-loading the answer satisfies prediction before development begins. Every development sentence then competes with an already-formed conclusion, which makes development read as restatement rather than discovery.

### What to Flag

- Section opening that states the conclusion before building it
- Chapter opening that previews all sections
- Opening that uses defensive framing ("why this matters") repeatedly
- Pre-announced evidence: "Research confirms..." before presenting the research

---

## 5. Summary Quality (Rules 1.5, 2.14, 6.6)

Summaries synthesize; they do not recapitulate.

### Synthesis vs Recapitulation

**Synthesis:** Each summary sentence draws from multiple sections to show how ideas form a whole the reader hasn't seen before. Ideas from different sections connect into a new insight.

**Recapitulation:** Each summary sentence maps 1-to-1 to a section. P1 restates the definition, P2 restates the mechanism, P3 restates the costs. This is sequential replay, not synthesis.

### Test

Map each summary sentence to the sections it references:
- If each sentence maps to exactly one section -> recapitulation (flag it)
- If each sentence connects ideas from 2+ sections -> synthesis (correct)

### Chapter Summary Checks

- Does the summary synthesize only (no new content)?
- Does it reference earlier sections abstractly, not verbatim?
- Does it transition forward to the next chapter appropriately?
- Does it avoid being too long (adding background re-explanations or technique repetitions)?

### What to Flag

- Summary where each sentence replays one section's conclusion in order
- Summary that adds new content not developed in the chapter
- Summary that is too long and repeats detailed mechanisms
- Summarization tables where connected prose would build a coherent schema
- Summary that restates the opening instead of showing what the development established

---

## 6. Forward Disclosure Detection (Rules 6.3, 2.4, 2.12)

Forward references break the dependency chain. The reader encounters terms, concepts, or conclusions from material not yet covered.

### Types of Forward Disclosure

1. **Term used before definition chapter:** Mentioning a term before the chapter that introduces it.
2. **Concept from future chapter:** Relying on an idea before the chapter that explains it.
3. **Forward reference to later section:** "As we will see in Section 3.4..." Describes future content instead of building toward it.
4. **Conclusion before evidence:** Stating the chapter's thesis in the opening before the development earns it.
5. **Naming before evidence for new concepts:** Paragraphs before evidence (an example, a reasoning chain, an analogy) name the cause, mechanism, or structural property that the evidence will demonstrate. This applies when the section builds a new concept (Rule 2.5), not when working with concepts the reader already knows (Rule 2.6). "The loaf failed because the kitchen was too cold" before the account that shows the cold discloses the naming. "Two loaves from the same dough rose very differently on the same day" preserves the puzzle for the evidence to resolve.

### Allowed References

- Naming a term as the subject of investigation: "What does compound interest mean?" (the chapter that defines compound interest can name it in its title)
- Brief transition: "The next chapter examines..." without explaining what it concludes
- Backward references: "Chapter 2 established that compound interest grows faster than simple interest" (always allowed)

### What to Flag

- Any concept term used in explanations before the chapter/section that defines it
- Forward references that describe what a later section will prove
- Terms from the book's own vocabulary used casually before their defining chapter
- Conclusions stated before the evidence that supports them
- Paragraphs before evidence that name the mechanism or cause for a new concept the section introduces

---

## 7. Back-References and Term Introduction (Rules 2.3, 2.4-2.7, 2.11, 2.16)

### Back-References

- When concepts from earlier chapters are used, are they referenced? ("Chapter 2 established...")
- Are cross-references explicit or implicit? Explicit is preferred.
- Do examples connect back to principles established earlier?

### Term Introduction Sequence

For core concepts (what the book teaches):
1. Explain the mechanism first (what triggers it, what happens)
2. Define in "X is..." format
3. Only then use the term in other explanations

For background concepts (prerequisites):
- Definition in "X is..." format suffices

### Expert Introduction

- Are experts introduced before their ideas are cited?
- Does the introduction explain who they are and why their opinion matters?

### Citation Quality

- Are claims grounded with `[@Abc99]` citations?
- Are primary sources cited (the originator, not the synthesis that collected the idea)?
- Are "research shows" claims backed with specific references?

Companion check: the check-facts skill's citation check (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/citation-check.py`) verifies that every cited key is an entry in the book's `.bib` file.

### What to Flag

- Term used in explanations before its defining section
- Expert quoted without introduction
- "Research shows..." without specific citation
- Citing synthesis book for an idea that originated elsewhere

---

## 8. Term Formatting (Rules 9.5-9.9)

- New concept terms: *italic* on first use, plain text on all subsequent uses
- When the book shows code: code names in `monospace` always, and the idea kept apart from the code name (Rule 9.7)
- Bold in running text: avoid (headings and structural elements only)
- Quotation marks around terms: only for ironic or non-standard usage

### What to Flag

- New concept term not italicized on first use
- Concept term still italicized after first use
- Code name not in monospace (when the book shows code)
- Bold used for emphasis in running prose
- Quotation marks used to define a term (should use italic)

---

## Output Format

For each issue found:

| Priority | Location | Text | Rule | Issue | Suggested Fix |
|----------|----------|------|------|-------|---------------|
| High/Medium/Low | Section + paragraph | the words at fault, quoted exactly | Rule number | Description | How to fix |

### Priority Levels

- **High:** Broken T-D-C pattern, answer front-loading, summary recapitulation, forward disclosure of defined terms
- **Medium:** Weak adjacency chain (restatement disguised as building), missing transitions, term used before definition
- **Low:** Formatting issues, minor transition improvements, varied connection technique suggestions

### Also Report What Works Well

Note strong transitions, good back-references, well-executed T-D-C sections, and effective adjacency chains. This helps the author preserve what already works during revision.

### Summary

At the end, provide:
1. **T-D-C compliance:** Which sections follow the pattern correctly? Which don't?
2. **Adjacency chain quality:** Are chains mostly building or mostly restating?
3. **Transition quality:** Are transitions varied and natural?
4. **Opening/summary quality:** Do openings pose questions? Do summaries synthesize?
5. **Forward disclosure count:** How many forward references found?

---

## Companion Scripts

Run these for quantitative validation (`SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"`):

```bash
python3 $SCRIPTS/sentence-and-paragraph-check.py --stats <file>       # sentence and paragraph limits
python3 $SCRIPTS/sentence-and-paragraph-check.py --style <file>       # connectors and inversions per section
python3 $SCRIPTS/sentence-and-paragraph-check.py --connectors <file>  # the three-way test of Section 2
python3 $SCRIPTS/unclear-this-check.py <file>                         # unclear "this" of Section 2
```
