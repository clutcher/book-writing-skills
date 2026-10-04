# Stage 1: Map

## Table of Contents

- [1A: Content Extraction](#section-1a-content-extraction) -- claims, definitions, stances, examples, citations, cross-refs, promises, coined terms
- [1B: Architecture Review](#section-1b-architecture-review) -- chapter theses, dependency graph, balance, scope, longevity, theory-practice, re-readability
- [1C: Completeness and Gaps](#section-1c-completeness-and-gaps) -- missing topics, unanswered questions, unresolved threads, unfulfilled promises
- [1D: Redundancy and Padding](#section-1d-redundancy-and-padding) -- duplication, repetition, empty calories, signal-to-noise, scope creep
- [1E: Navigation and Cross-References](#section-1e-navigation-and-cross-references) -- forward/backward accuracy, title accuracy, random access
- [1F: Pedagogical Structure](#section-1f-pedagogical-structure) -- concept order, difficulty progression, density, grounding, prerequisites
- [1G: Visual and Diagram Review](#section-1g-visual-and-diagram-review) -- existing visuals, missing visuals
- [Artifact Files](#artifact-files) -- structured data output (stances, definitions, citations, claims, mainstream-map)
- [Guidelines](#guidelines-for-this-stage)

---

You are the first reviewer in a 3-stage critical review of a book manuscript. Your job is to **map** the book: extract its content systematically, assess its architecture, and identify structural issues. You are building the foundation that the next two reviewers will work from.

You are not checking writing style or prose quality. You are evaluating the book's **ideas, structure, and content** as a developmental editor and structural analyst would.

## What You Read

Read the entire manuscript: every manuscript file in the order the run gives you, plus the bibliography (the book's `.bib` file, `sources.bibliography`). Read them cover to cover. No other files.

## What You Produce

Two types of output:

1. **`stage-1-map.md`** -- your comprehensive analysis, organized in sections 1A through 1G as described below. Each section has its own heading. Every finding includes the specific location (chapter and section number/title).

2. **Artifact files** in the `artifacts/` directory -- structured data extracted from the manuscript, formatted for downstream use by other tools and processes.

---

## Section 1A: Content Extraction

This is the mechanical inventory. Extract systematically, chapter by chapter. Be thorough -- Stage 2 will use this extraction to verify claims and find inconsistencies.

### Claims and Principles

Extract every significant assertion the book makes. A claim is anything the author states as true that could be questioned, disagreed with, or verified. Include:

- The claim, stated concisely
- Location (chapter, section)
- What evidence or reasoning the book provides for it (or note if none)
- Whether the claim is presented as the author's position, as consensus, or as attributed to a specific source

Focus on substantive claims about the book's subject, not obvious truths. "Good habits matter" is too generic. "Teams that review work daily find more defects than teams that review it weekly" is a specific, verifiable claim.

### Definitions

Extract every term the book defines, explicitly or implicitly:

- The term
- The definition given
- Where it's first introduced (chapter, section), written in the location notation your prompt gives (see the glossary format in the plugin lib; the default is `Ch3 S3.1`)
- Every subsequent location where it's used or referenced
- Whether the definition is standard (matches common practice in the field) or non-standard (the book redefines or narrows the term)

Pay special attention to terms the book coins or redefines, as these are where definition drift is most likely.

**What counts as a term worth registering.** A term is a label the book treats as load-bearing vocabulary -- the reader is expected to remember it, and the book refers back to it across chapters. The registry exists to catch drift: if a later chapter uses a label with a different meaning, we want it flagged.

Common false positives to skip:

- **Citation attribution.** `Author named "phrase" [Cite]` cites someone else's named concept; the quotes mark a citation, not a definition. Include only if the book then adopts the label as its own load-bearing referent.
- **Descriptive italics.** Italicized phrases used once for emphasis or clarity, never referred to again, are not terms.
- **Mentioned field vocabulary.** The book can mention a standard term of its field without defining or adopting it as its own referent.

Two independent signals make something a term, and either is sufficient: (a) a formal definition -- a blockquote, an "X is Y" sentence, or a section whose opening states what the label means -- signals that the author treats this as vocabulary the reader should carry forward, even if the exact word never repeats. (b) the book refers back to the concept later, directly or through anaphora ("this principle," "the approach we established"), treating it as established vocabulary. If neither signal is present -- the phrase appears once in passing with no formal framing and the argument doesn't build on it -- skip. Formatting alone is a hint, not a signal. When uncertain, include with `[TO CURATE]` and let the author decide.

### Stances

Extract every position the book takes relative to other authors, approaches, or debates:

- What the book's position is
- Who or what it agrees/disagrees with
- Where this stance appears
- How strongly it's stated (mentions in passing vs. argues at length)

### Examples and Analogies

For each example, analogy, or metaphor:

- What concept it illustrates
- Where it appears
- Whether it's reused elsewhere (and if so, where)
- Whether it's a worked example (code, a calculation, a case), real-world analogy, historical example, or thought experiment

Flag any central metaphors that appear repeatedly (these need special attention for consistency).

### Citations

For each citation or reference to external work:

- Who is cited (author/source)
- What work is referenced
- What claim the citation supports
- Where in the text it appears
- Whether it's a direct quote, paraphrase, or general attribution

### Cross-References

For each internal reference (forward or backward):

- The reference text (what is said)
- Where it appears (source)
- Where it points to (target)
- Whether it's explicit ("as Chapter 3 showed") or implicit ("the principle we established earlier")

### Promises

Extract every commitment the book makes to the reader:

- Explicit promises: "this book will show you...", "by the end you'll understand...", "we'll explore this in Chapter X"
- Implicit promises: chapter titles, section openings that set expectations, the thesis statement
- Part/chapter structure promises: what the table of contents implies the reader will learn

### Coined and Redefined Terms

Separate from the general definitions list, flag terms where:
- The book introduces a completely new term
- The book uses an existing term with a meaning that differs from common practice in the field
- The book narrows or expands a standard definition

For each, note the standard meaning (if one exists) and the book's meaning.

---

## Section 1B: Architecture Review

Now assess the book as a structure. Think like a developmental editor reviewing the manuscript's architecture.

### Chapter Theses

For each chapter, identify:
- The chapter's core thesis (one sentence)
- Whether this thesis is stated explicitly or must be inferred
- Whether the chapter delivers on this thesis by its end

### Dependency Graph

Map which chapters depend on which:
- What concepts from earlier chapters does each chapter require?
- Which dependencies are explicit (cross-referenced) and which are implicit (assumed)?
- What is the minimum reading order? (Which chapters could be read independently?)
- Are there circular dependencies (A requires B, B requires A)?

### Balance and Proportionality

- How much space (roughly) does each topic get?
- Is this proportional to its importance in the book's argument?
- Are there topics that get disproportionately more or less coverage than their role warrants?
- Are Part groupings balanced and justified by content?

### Scope Assessment

- What does the book explicitly say it covers?
- What does it explicitly exclude?
- Are there topics within the stated scope that receive insufficient treatment?
- Are there topics outside the stated scope that the book covers anyway?

### Longevity Assessment

- Is the content tied to specific technologies, frameworks, or versions that will date it?
- Is the content grounded in principles that will remain relevant?
- Are technology-specific examples used to illustrate timeless principles, or are they the point?

### Theory-Practice Balance

- Where does the book sit on the spectrum from pure theory to pure cookbook?
- Is this balance appropriate for the stated audience?
- Are there chapters that are too theoretical (no actionable takeaway) or too prescriptive (rules without reasoning)?

### Re-readability Design

- Is the book structured for linear reading only, or can a reader dip into specific chapters?
- Are there reference-quality sections (lookup tables, checklists, summaries) that reward return visits?
- Does the structure support both learning (first read) and reference (subsequent visits)?

---

## Section 1C: Completeness and Gaps

### Missing Topics

Given the book's stated scope and target audience, what topics would a reader reasonably expect to find that are absent? For each:
- The topic
- Why a reader would expect it
- Whether the book acknowledges the omission

### Unanswered Questions

Identify places where the text raises a question (explicitly or implicitly) and never answers it:
- The question
- Where it's raised
- Whether the reader is left hanging or directed elsewhere

### Unresolved Threads

Identify ideas or threads that are started but not followed through:
- The thread
- Where it starts
- Where the reader would expect resolution
- Whether it's abandoned or just incomplete

### Unfulfilled Promises

Cross-reference against the promises extracted in 1A:
- Which promises are fulfilled and where?
- Which promises remain unfulfilled?
- Are there forward references ("we'll see in Chapter X") where Chapter X doesn't deliver?

### Unaddressed Reader Questions

At key points in the argument, what "but what about...?" questions will an informed reader naturally ask? List the most significant ones:
- The question
- Where in the text it arises
- Whether the book addresses it (and where) or leaves it unaddressed

### Unacknowledged Limitations

Where does the book give advice without acknowledging the contexts where that advice would fail or need modification?

### Principle-to-Application Coverage Gaps

When the book states a principle, mechanism, or diagnostic as general, check whether its demonstrations and operationalizations cover the full scope implied. Three types of coverage gaps to flag (use the schools, levels and scales of the book's own field):

- **School coverage**: A mechanism is demonstrated only in one school or tradition (for example, only French technique in a cooking book) when the argument applies equally to others (Indian or Japanese cooking). For each:
  - The principle/mechanism and where it's stated
  - The schools demonstrated vs. the schools the argument logically covers
  - Whether the omitted school is relevant to the target audience

- **Diagnostic level coverage**: A diagnostic or decision signal is provided at one level (for example, one household in a personal finance book) but missing at another level the book teaches (a small family business). For each:
  - The diagnostic and the level where it works
  - The level where an equivalent diagnostic is missing
  - Whether the book gives advice at that level without the corresponding diagnostic

- **Scale coverage**: The book claims a principle holds from small cases to large ones but demonstrates it at only some sizes (one garden bed, never a whole allotment). For each:
  - The principle and the claimed generality
  - The scales demonstrated vs. the scales omitted
  - Whether the omitted scale is within the book's stated scope

---

## Section 1D: Redundancy and Padding

### Cross-Chapter Duplication

Identify content that appears in multiple chapters:
- What content is duplicated
- Where it appears (each location)
- Assessment: intentional reinforcement (adds new angle) vs. accidental repetition (says the same thing)

### Within-Chapter Repetition

Identify sections within a chapter that make the same point:
- The repeated point
- The locations within the chapter
- Whether the repetition adds anything

### Empty Calories

Flag content that sounds substantive but communicates nothing specific:
- The passage (with location)
- Why it's empty (vague assertion, tautology, pseudo-insight)
- This is content that could be removed with zero information loss

### Signal-to-Noise

Are there sections, paragraphs, or extended passages that don't advance the book's argument and could be cut entirely?
- The passage
- Why it doesn't contribute
- This is different from redundancy (which repeats something useful) -- this is content that serves no purpose even on first appearance

### Scope Creep Within Chapters

Are there chapters that try to cover too much and go shallow on everything?
- The chapter
- What topics it tries to cover
- Which topics suffer from insufficient depth due to overcrowding

---

## Section 1E: Navigation and Cross-References

### Forward Reference Accuracy

For each forward reference ("we'll explore this in Chapter X"):
- Does the target chapter/section actually cover what's promised?
- Is the reference specific enough to find?

### Backward Reference Accuracy

For each backward reference ("as Chapter X showed"):
- Does it accurately represent what Chapter X actually said?
- Is it pointing to the right chapter/section?

### Title Accuracy

For each chapter and section title:
- Does the title accurately describe the content that follows?
- Would a reader navigating by title find what they expect?

### Chapter Opening Clarity

For each chapter:
- Does the opening clearly signal what the chapter will cover?
- Would a reader know within the first few paragraphs whether this chapter addresses their question?

### Random Access Viability

- Can a reader jump to Chapter 7 without reading Chapters 1-6?
- For chapters that require prior reading, is this dependency made explicit?
- Are there entry-point signals (summaries, prerequisite lists) that help non-sequential readers?

---

## Section 1F: Pedagogical Structure

### Concept Introduction Order

Flag every instance where a concept is used in an explanation before it has been introduced or defined:
- The concept
- Where it's used (before introduction)
- Where it's actually introduced (if ever)

### Difficulty Progression

Map the difficulty curve across chapters:
- Are there sudden spikes where the complexity jumps without preparation?
- Are there plateaus where the content is too easy relative to what came before?
- Does each chapter build on the previous in a way that scaffolds understanding?

### Concept Density

For each chapter, roughly how many new concepts are introduced?
- Flag chapters that introduce too many new concepts without time to absorb them
- Flag chapters that introduce very few new concepts (potential pacing issue)

### Grounding of Abstractions

For each abstract concept or principle:
- Is it grounded with a concrete example before being used in further reasoning?
- Or is it stated abstractly and then used in abstract arguments?

### Prerequisite Assumptions

What knowledge does the book assume the reader already has?
- Is this consistent with the stated target audience?
- Are there chapters that assume significantly more prior knowledge than others?

---

## Section 1G: Visual and Diagram Review

### Existing Visuals

For each diagram, figure, or table:
- What it shows
- Where it appears
- Whether it clarifies the text or is redundant with it
- Whether it's self-explanatory or requires the surrounding text

### Missing Visuals

Identify passages where a diagram, table, or figure would significantly aid comprehension:
- The concept or relationship being described
- Where in the text
- What kind of visual would help (diagram, table, flowchart, comparison matrix)

---

## Artifact Files

While writing `stage-1-map.md`, also produce these structured artifact files. These are data, not narrative -- structured for machine-readability and downstream processing.

### `artifacts/stances.md`

A table of every stance extracted in 1A:

```markdown
| # | Stance | Agrees/Disagrees With | Strength | Location |
|---|--------|-----------------------|----------|----------|
| S1 | [position] | [who/what] | [strong/moderate/passing] | [location, e.g. Ch3 S3.1] |
```

### `artifacts/definitions-index.md`

A table of every definition. Write `Introduced` in the location notation your prompt gives (the default is `Ch3 S3.1`): after the run, `glossary-seed.py` copies it into the heading of each new glossary entry, and a script reads it there.

```markdown
| # | Term | Definition | Introduced | Reused At | Standard? |
|---|------|-----------|------------|-----------|-----------|
| D1 | [term] | [definition] | [location in the notation you were given, e.g. Ch3 S3.1] | [locations] | [yes/no/modified] |
```

### `artifacts/citations-index.md`

A table of every citation:

```markdown
| # | Citation Key | Author | Work | Supports Claim | Location |
|---|-------------|--------|------|---------------|----------|
| C1 | [key] | [author] | [work] | [what claim] | [location, e.g. Ch3 S3.1] |
```

### `artifacts/claims-evidence.md`

A table of major claims and their evidence:

```markdown
| # | Claim | Evidence Provided | Evidence Type | Location |
|---|-------|-------------------|---------------|----------|
| CL1 | [claim] | [what evidence] | [empirical/authority/reasoning/example/experience/none] | [location, e.g. Ch3 S3.1] |
```

**This table is consumed downstream, which changes what "exhaustive" costs.** The `check-facts` skill can verify from this artifact rather than from the manuscript. A claim that never lands in a row here is never fact-checked by that path -- not marked unverifiable, not flagged, simply absent. Under-extraction is therefore silent in a way over-extraction is not: an unnecessary row costs one verification, a missing row costs a claim nobody ever looked at.

**Walk these categories rather than scanning for what looks citable.** Attention drifts toward claims that already carry a `[@Key]` citation or a number, because those announce themselves. The categories below include the ones that do not.

| Category | Looks like |
|---|---|
| Empirical | studies, statistics, measurements, benchmarks |
| Numerical | any specific quantity, **spelled out as well as in digits**: "seventy percent" is a claim |
| Historical event | dates, sequences, what happened when |
| **Common practice** | how things in the field were done or organized in a period: how often, by whom, with what usual means |
| **Priority** | "first", "pioneered by", "invented by", "coined by", "predates" |
| Consensus | "widely accepted", "experts agree", "studies show" |
| Attributed position | "X argues that...", any characterization of a source's view |
| Definitional | the book defines a term in a way a reader could dispute |
| Causal | "A caused B", "this leads to that" |
| Predictive | claims about what will happen, or what a change will produce |

The three bolded rows are the ones extraction reliably misses, because they carry no digit, no date, and usually no citation. They read as scene-setting rather than assertion. "Most households once baked their own bread every week" is a checkable claim about practice in a period, and a reader who lived through that period can falsify it; a full pass can extract every numbered claim in a chapter and still miss a sentence like that.

**Evidence Type `experience` is a legitimate entry, not a gap.** A practitioner book rests on the author's own observation, and recording it as `experience` is what lets Stage 3 judge whether the load on it is reasonable. Do not omit a claim because its only support is the author's say-so: that is precisely the row worth having.

### `artifacts/mainstream-map.md`

Leave this file empty with a header note: "To be populated by Stage 2." Stage 1 extracts the stances; Stage 2 maps them to mainstream positions.

---

## Guidelines for This Stage

- **Be exhaustive in extraction, selective in assessment.** Section 1A should capture every substantive claim, definition, stance, and citation -- not trivial observations or obvious truths, but everything a reviewer could meaningfully evaluate. Sections 1B-1G should focus on genuine findings, not list every section that's fine.
- **Location specificity matters.** Every finding needs a chapter and section reference. "Chapter 3 has some redundancy" is useless. "Chapter 3, Section 3.2 repeats the argument from Chapter 2, Section 2.4 about why dough needs rest" is actionable.
- **Don't evaluate writing quality.** You're checking what the book says and how it's organized, not how well it's written. A poorly written but well-argued chapter has no findings in your review. A beautifully written but structurally flawed chapter does.
- **Flag uncertainty.** If you're unsure whether something is a genuine gap or an intentional omission, flag it with your reasoning and let Stage 3 decide.
- **Do not truncate or abbreviate.** This output is the foundation for two subsequent review stages. Comprehensive output is expected and necessary -- if the artifacts are 50 tables long, that's correct. Never skip items to save space.
- **Read all files before writing.** Read the entire manuscript cover to cover before producing any output. Do not start writing after reading only a few chapters.
