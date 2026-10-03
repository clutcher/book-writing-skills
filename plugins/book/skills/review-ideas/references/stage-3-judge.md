# Stage 3: Judge

You are the third and final reviewer in a 3-stage critical review of a book manuscript. Stage 1 (Map) mapped the book's content and structure. Stage 2 (Attack) attacked every claim, checked every fact, and found every inconsistency. Your job is to **judge**: triage Stage 2's findings, experience the book as a reader, and deliver the final assessment.

You hold two roles simultaneously:

1. **The Judge** -- you decide which of Stage 2's findings are genuine weaknesses and which are noise. You also catch what Stage 2 missed.
2. **The Reader** -- you experience the book as a target reader would, assessing engagement, practical value, and whether the book earns trust.

You are not checking writing style or prose quality. You are evaluating whether the book **works** -- whether its ideas land, whether a reader would trust the author, and whether the content delivers genuine value.

## What You Read

1. The entire manuscript: every manuscript file in the order the run gives you, plus the bibliography
2. Stage 1 output: `stage-1-map.md` and all files in `artifacts/`
3. Stage 2 output: `stage-2-attack.md` and updated `artifacts/mainstream-map.md`
4. `artifacts/decision-matches.md`: each Stage 2 finding matched against the book's `decisions.md`, with what the run may do for each match. This table is the only way the book's earlier decisions reach you; do not open `decisions.md` itself

Read the manuscript fresh, as a reader would. Let Stage 1 and Stage 2 inform your reading, but don't let them replace your own experience of the text.

## What You Produce

**`stage-3-judge.md`** -- your final assessment, organized in sections 3A through 3F, followed by a Chapter Health section and a Strengths section.

You also finalize the artifact files based on any corrections discovered during your review.

---

## Section 3A: Critique of Critique

This is the triage. Go through every finding from Stage 2 (referenced by finding ID) and classify it.

### Classification

For each Stage 2 finding, **re-read the relevant passage in the manuscript** before classifying. Stage 2 may have missed caveats, qualifications, or handling in adjacent paragraphs. Your triage must be based on what the book actually says, not on Stage 2's summary of what it says. If Stage 2 claims the book "ignores" an objection but you find the book addresses it two paragraphs later, that finding is NOISE.

Assign one classification:

- **DECIDED** -- the finding repeats an entry in `decision-matches.md` whose status is DECIDED. Do not triage it again: one line naming the entry (FP-11). A finding that matches an `OPEN / fix owed` entry is triaged as a regression check of the agreed fix; one that matches `OPEN / decision owed` is only a reminder that the author owes an answer.

- **VALID** -- genuine weakness that needs attention, verified against the actual manuscript text
  - **Critical**: Undermines the book's core argument, destroys credibility, or is factually wrong on something important
  - **Significant**: Weakens a section or chapter, creates confusion, or represents a notable gap
  - **Minor**: A real issue but one that most readers wouldn't notice or that has minimal impact on the argument
- **NOISE** -- technically true objection that isn't a real problem for this book, its audience, and its goals. Explain why it's noise. Common reasons: the book already addresses the objection (cite where), the objection doesn't apply to the target audience, or the objection attacks a simplified version of the argument rather than the full version.

Format for individual findings:

```markdown
### Finding [ID]: [VALID-Critical / VALID-Significant / VALID-Minor / NOISE]

**Stage 2 said:** [one-line summary of the finding]

**What the manuscript actually says:** [Brief quote or paraphrase of the relevant passage, including any caveats or handling from adjacent paragraphs that Stage 2 may have missed. Cite the specific location.]

**FP screens applied:** [List which of FP-1 through FP-12 you ran against this finding and the result of each (PASS = the FP does not apply / finding survives; FAIL = the FP applies and finding collapses). Required for every VALID classification. A VALID-Significant or VALID-Critical classification with no explicit FP-screen reasoning should be downgraded to NOISE pending verification.]

**Assessment:** [Why this classification. For VALID findings: why it matters despite the book's handling, and what direction a fix could take. For NOISE: what the book already does that addresses the objection, which FP screen the finding fails under, and why Stage 2 missed it.]
```

When multiple findings share the same nature and severity, group them:

```markdown
### Findings T-3, T-7, T-12: VALID-Minor (grouped)

**Stage 2 said:** All three flag rules from one country's building code presented as universal.

**Assessment:** Each is a real issue -- adding "in the United States" would fix all three. Minor because the book's primary audience won't notice, but readers elsewhere would.
```

### False-positive screens

Before classifying any finding as VALID (from Stage 2, or one you add as M-), run it against every pattern in [false-positives.md](false-positives.md) (FP-1 to FP-12). If a finding fits one, classify it as NOISE and name the pattern. FP-11 is yours alone: read `artifacts/decision-matches.md` and apply the book's earlier decisions to every finding it lists.

### What Stage 2 Missed

After triaging all of Stage 2's findings, identify weaknesses that Stage 2 failed to catch. These are findings that emerge from your fresh reading of the manuscript with the benefit of seeing what Stage 2 focused on. Before adding a missed finding, run it against every pattern in false-positives.md -- your own "missed" findings are subject to the same false-positive patterns as Stage 2's findings, and a large share of flagged M- findings collapse under those patterns.

**Start every missed finding with its own heading, `#### M-<n>: <the issue in one line>`** (`M-` for
"missed"), then these fields as a list under it. A script reads these headings to match your
findings against the book's decisions, so a finding written without one is never matched.

- **Location**
- **Severity** (critical/significant/minor)
- **Why Stage 2 likely missed it** (was looking at the wrong things, requires reader-perspective to see, etc.)

### Pattern Analysis

Look across all VALID findings (both from Stage 2 and your own missed findings):

- Are weaknesses clustered in certain chapters? Which chapters have the most critical/significant issues?
- Are weaknesses clustered around certain topics or types of claims?
- Is there a systemic pattern (e.g., consistently overclaims about one kind of evidence, consistently ignores counterarguments from one school, or states the positions it displaces less carefully than the positions it adopts)?
- Are certain types of issues more prevalent (factual, logical, consistency, coverage)?

---

## Section 3B: Reader Experience

Now set aside the analytical lens and read as the target reader the book names for itself (in its preface or introduction; if it names none, that is a finding). Someone intelligent and motivated but who hasn't thought deeply about this specific topic yet.

### Engagement

- Does the book open strong? Do the first pages earn continued reading?
- At what points (if any) does interest flag? What causes the dip -- too much theory? Repetition? Unclear relevance?
- Are there sections that feel like a chore to get through?
- Are there sections that genuinely excite or illuminate?
- Is there variety in the book's approach (reasoning, examples, history, practical guidance), or does it feel monotone?

### Trust and Authenticity

- Does the author's voice feel like a real practitioner?
- Are there moments that build trust (acknowledging complexity, admitting trade-offs, showing genuine experience)?
- Are there moments that erode trust (overclaiming, hand-waving, sounding theoretical rather than experienced)?
- Does the reader feel they're learning from someone who has done this, or from someone who has read about it?

### Emotional and Motivational Arc

- After reading, does the reader feel empowered to act differently? Or overwhelmed by rules?
- Does the book build conviction progressively, or does it assert conclusions?
- Is there a sense of momentum -- each chapter making the reader more capable?
- Are there passages that feel condescending or preachy?

### Adversarial Reader Perspectives

Beyond the target reader, read key arguments from three additional perspectives. These readers exist in the real audience -- if the book loses them, it loses reach and credibility.

**The Skeptic** -- a reader who disagrees with the thesis before starting:
- At what points would they stop reading? What claim would break their trust?
- Does the book earn skeptics through evidence, or alienate them through assertion?
- If a reader disagrees with one major claim, can they still get value from the rest?

**The Paradigm Outsider** -- a reader from a different school of thought in the book's field (a follower of the method the book argues against, or of a rival tradition):
- Where does the book assume its paradigm is the only valid one?
- Would a reader from a different tradition feel their approach was fairly represented?
- Are there places where engaging with the other paradigm would strengthen the argument?

**The Beginner** -- a reader at the lower end of the target audience:
- Where would they get lost due to assumed knowledge?
- Are there sections where the gap between "intelligent person who hasn't thought about this" and "what the text assumes" is too wide?
- Does the book build enough scaffolding for them, or does it assume mid-level experience?

For each perspective, identify the 2-3 moments where that reader would most likely disengage, and whether the book could address their concern without weakening the argument for the primary audience.

### Memory and Retention

- Which ideas from the book would stick with a reader a month later?
- Are key points stated memorably, or buried in surrounding text?
- Does the book give the reader mental handles (frameworks, questions, metaphors) they can carry into their daily work?
- Are there formulations a reader would quote to a colleague?

---

## Section 3C: Practical Value

### The "So What?" Test

For each chapter, answer: after reading this, what can the reader DO that they couldn't do before? Be specific:

- **Chapter N**: [what the reader gains]
- If a chapter provides understanding without actionability, note that -- it may be fine (some chapters build foundation), but flag it if the reader expects practical guidance and gets only theory

### Actionability

- Are recommendations specific enough to follow? ("Soak the beans for twelve hours" vs. "prepare the beans properly")
- Could a reader use the book's advice tomorrow?
- Are there checklists, diagnostic questions, or decision frameworks the reader can use immediately?
- Do diagnostics and decision frameworks cover all levels the book teaches? A diagnostic introduced at the smallest level should have equivalents at every larger level the book gives advice for. Flag cases where the reader is told what to do at a level but not how to recognize when to do it.

### Applicability Range

- Does the advice apply to the reader's daily work (the routine, repeated tasks of the field)?
- Or does it mostly apply to rare, start-from-nothing decisions?
- Does the book acknowledge the gap between ideal and reality?

### Thinking vs. Recipes

- Does the book develop the reader's **judgment**, or does it give them **rules to follow**?
- Can the reader handle novel situations using the book's framework, or only situations the book explicitly covers?
- This isn't a criticism either way -- but it should match the book's stated goals

---

## Section 3D: Reader Anticipation

### Natural Objections

At each major claim, what will a skeptical (but fair) reader think? List the top objections and whether the book addresses them:

- **The claim** (with location)
- **The reader's likely objection**
- **Whether the book addresses it** (and where, if so)

Focus on objections that would cause a reader to put the book down or lose trust -- not minor quibbles.

### Prior Beliefs Required

What must the reader already believe for the book's argument to work?

- List the key assumptions
- Are these assumptions stated explicitly, or does the book take them for granted?
- If a reader disagrees with assumption X, does the entire argument fall apart, or can they still get value from the remaining content?

### Gotcha Moments

Are there points where a knowledgeable reader would catch the book in an apparent error, overstatement, or contradiction that would make them question everything that follows?

- The passage (with location)
- What the reader would catch
- Whether it's a genuine error or an appearance problem (and which is worse depends on context)

### Overcomplexity

Are there points the book makes harder than they need to be?

- The concept (with location)
- Why it feels overcomplicated
- How it could be simplified without losing substance

---

## Section 3E: Self-Consistency and Analogy Integrity

### Practicing What It Preaches

Stage 2 (section 2B) found individual instances where the book may violate its own advice. Your job here is different: make the **holistic** judgment that individual instances can't.

- Overall, does the book embody its own principles? Not "does section 3.2 violate rule X" but "does a reader finish this book thinking the author lives by these principles?"
- Where violations exist, are they visible enough to undermine the message?
- Is the overall impression one of integrity, or does the book preach what it doesn't practice?

### Central Metaphor Integrity

For the book's central metaphor (assess whichever recurring metaphor the book uses):

- Does the metaphor hold at every point where it's applied?
- Are there uses where the metaphor breaks down or misleads?
- Does the metaphor deepen understanding, or does it eventually become a distraction?
- Is it overused (reader fatigues) or underused (never fully developed)?

### Analogy Quality

For other analogies and metaphors used throughout:

- Do they clarify or confuse?
- Do any analogies contradict each other? (Two metaphors for the same concept that imply different things)
- Are there analogies that work initially but break down when the reader thinks harder?
- Are analogies appropriate for the audience? (Not condescending, not obscure)

---

## Section 3F: Positioning Assessment

### Expertise Demonstration

Based purely on the manuscript (not any external knowledge about the author):

- What level of expertise does the writing demonstrate?
- Where does the treatment signal deep experience? (Specificity of examples, nuance of trade-offs, awareness of failure modes, patterns across projects)
- Where does the treatment signal surface knowledge? (Generic advice, textbook explanations without practical grounding, lack of war stories)

### Credibility

- Is there anything in the text that would actively undermine the author's credibility? (Getting a well-known fact wrong, making a claim that practitioners would immediately dispute, showing unfamiliarity with standard tools or practices of the field)
- Are there missed opportunities to establish credibility? (Places where the author's experience could show through but doesn't)

### Differentiation

- What makes this book's perspective different from existing books in the same space?
- Is this differentiation clear to the reader, or would they wonder "why this book instead of the best-known books on the same shelf?"
- Does the book articulate its unique contribution?

---

## Chapter Health

Produce a summary table showing the health of each chapter based on all findings from all stages:

```markdown
| Chapter | Critical | Significant | Minor | Strongest Aspect | Weakest Aspect |
|---------|----------|-------------|-------|-----------------|----------------|
| Ch 1    | [count]  | [count]     | [count] | [brief note]  | [brief note]   |
| Ch 2    | [count]  | [count]     | [count] | [brief note]  | [brief note]   |
| ...     | ...      | ...         | ...   | ...             | ...            |
```

Below the table, identify:
- The strongest chapters (fewest issues, strongest arguments)
- The chapters that need the most work (most critical/significant issues)
- Any chapters that should be considered for restructuring, merging, or significant revision

---

## Strengths

This section is just as important as the critique. Identify what the book does well and must preserve through any revision:

- **Strongest arguments**: Which claims are rock-solid, well-evidenced, and compellingly presented?
- **Best examples**: Which examples perfectly illustrate their concepts?
- **Unique contributions**: What does this book offer that existing books don't?
- **Most memorable moments**: What would a reader quote or remember?
- **Structural successes**: Where does the book's organization particularly serve the reader?

Be specific. "Chapter 2 is strong" is useless. "The argument in Ch2 S2.3 that ties the cited survey to the three-step routine is the book's strongest evidence-based claim" is valuable.

---

## Artifact Finalization

Review the artifact files from Stage 1 (updated by Stage 2 where applicable). Make any corrections based on your own reading:

- If Stage 2 identified wrong attributions or dates in `citations-index.md`, mark them
- If you found additional stances, definitions, or claims that Stage 1 missed, add them
- If the mainstream mapping from Stage 2 needs corrections, update `mainstream-map.md`

Mark any changes you make with `[Stage 3 correction]` so the provenance is clear.

---

## Guidelines for This Stage

- **The triage is your most important job.** Stage 2 intentionally overproduces findings. Your classification determines what actually gets fixed. Be rigorous: NOISE doesn't mean wrong, it means not worth fixing in the context of this book's goals and audience. The most common reason a finding is NOISE: Stage 2 attacked a simplified version of the claim without reading the book's own caveats and handling in surrounding paragraphs. Always verify against the manuscript text before classifying.
- **Read as the reader, not as the reviewer.** Sections 3B-3D require you to set aside the analytical stance and experience the book naturally. Note your genuine reactions: where you were bored, confused, excited, skeptical, convinced.
- **Strengths are findings too.** A review that only lists problems gives the author no guidance on what to protect during revision. Be as specific about strengths as about weaknesses.
- **Don't relitigate Stage 2.** If Stage 2 flagged something and you disagree, classify it as NOISE with your reasoning. Don't write a counter-essay.
- **The chapter health table is a dashboard, not a verdict.** A chapter with many minor issues may be healthier than one with a single critical issue. The counts inform priority; they don't determine quality.
- **Every VALID-Critical and VALID-Significant finding goes to the verification pass.** Say so at the end of 3A with the list of their IDs. The pass checks each one against primary sources, blind to your reasoning ([verification-pass.md](verification-pass.md)); findings upheld from abstracts or from secondary quotes are the ones it most often overturns.
- **Your "missed" findings (M- prefix) are high-signal.** If something escaped both Stage 1 and Stage 2, it's likely subtle and important. Give these findings your best analysis.
- **Do not truncate or abbreviate.** Every Stage 2 finding must be triaged. Every section must be thorough. Comprehensive output is expected.
- **Read all files before writing.** Read the entire manuscript and all Stage 1 + Stage 2 output before producing any assessment.
