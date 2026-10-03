# Whole-Book Review: Style Consistency Across Chapters

Self-contained review that reads the entire manuscript to find style issues that only emerge across chapter boundaries. Per-chapter reviews (common-problems, flow, all-problems) catch issues within a chapter. This review catches issues between chapters.

**For a paper** (`kind: paper`): a chapter here is one section of the paper, and the rules a
paper turns off ("A book or a paper" in the write-text `SKILL.md`) are not findings.
For a paper, skip Part Boundaries and the WHY/HOW chapter roles, and check Section 13 of the
rules (contributions, scoped claims, hedging, threats, numbers) across the sections.

## Table of Contents

- [1: Terminology Consistency](#1-terminology-consistency-rules-24-217) -- same name for same concept across all chapters (includes within-chapter near-synonym drift)
- [2: Example and Argument Ownership](#2-example-and-argument-ownership-rules-215-114) -- duplication, re-explanations disguised as back-references
- [3: Forward and Backward Reference Integrity](#3-forward-and-backward-reference-integrity-rules-63-23) -- forbidden forward refs, inaccurate backward refs
- [4: Thesis Hierarchy Integrity](#4-thesis-hierarchy-integrity-rules-121-123) -- concept hierarchy, back-reference validity, thesis direction
- [5: Part Boundaries](#5-part-boundaries-rules-61-62) -- topic leaks between Parts
- [6: Chapter-Level Structure Consistency](#6-chapter-level-structure-consistency-rules-64-66-11-15) -- WHY/HOW roles, T-D-C quality variation
- [7: Voice and Prose Consistency](#7-voice-and-prose-consistency-rules-41-416-71-73) -- tone shifts, person usage, prose patterns
- [8: Cross-Chapter Transitions](#8-cross-chapter-transitions) -- chapter boundary quality, momentum
- [9: Heading and Formatting Consistency](#9-heading-and-formatting-consistency-rules-81-85-95-99) -- heading patterns, italic/monospace/bold
- [10: Citation and Grounding Consistency](#10-citation-and-grounding-consistency-rules-29-210-216-35) -- citation density, primary sources, abstract grounding
- [11: Quantitative Consistency](#11-quantitative-consistency-scripts) -- script-based statistical outliers

**What this review catches:** Terminology drift, voice shifts, structural inconsistency, broken cross-references, Part boundary leaks, example duplication, chapter-level T-D-C quality variation, and coined term distribution problems.

**Scope:** All chapters read together. This review requires the full book in context.

---

## Relationship to the Review-Ideas Skill

The **review-ideas** skill checks content: ideas, arguments, facts, consistency of claims. This review checks style: whether the writing follows the same rules consistently across all chapters. Some dimensions overlap (example duplication, cross-references, Part structure) but the perspective differs -- review-ideas asks "does the content work?", this review asks "does the style-rule compliance hold across chapters?"

---

## How to Use This Review

0. Read the decisions index (`decisions.py index`, then `decisions.py show ID` for an entry), the glossary and the voice profile. Never report a DECIDED item; cite a matching OPEN item instead of re-raising it.
1. Run the validation scripts listed in Section 11 first -- quantitative data informs your qualitative reading
2. Read the entire manuscript cover to cover (all chapters in order), with the script data in mind
3. Check against each section below during or after reading
4. For each issue found, report using the output format at the end

Read all chapters before producing any output. Cross-chapter patterns only become visible after seeing the full book. Do not truncate findings -- comprehensive output is expected.

---

## 1. Terminology Consistency (Rules 2.4, 2.17)

Rule 2.4 requires the same name for the same concept across all chapters. This is the highest-priority cross-chapter check because terminology drift confuses readers who built their mental model around the original term.

### What to Check

For each significant concept in the book:
- Is the same term used every time the concept appears?
- When a term is defined in one chapter, do later chapters use that exact definition?
- Are there places where a synonym or near-synonym is used instead? (e.g., "stock" in one chapter, "broth" in another for the same concept)
- When abbreviations or shortened forms are used, is the pattern consistent?

### Naming Drift Patterns

Watch for:
- **Gradual synonym substitution:** "starter" in early chapters becomes "sourdough culture" in later chapters
- **Precision erosion:** A precisely defined term gets used loosely in later chapters
- **Scope drift:** A term defined narrowly in its home chapter gets applied more broadly elsewhere
- **Register shift:** Formal term in definition chapter, casual equivalent in later chapters

### What to Flag

- Concept called by different names in different chapters (with both locations)
- Term used with a meaning that doesn't match its definition chapter
- Informal shorthand used without establishing the equivalence

### Near-synonym drift (within-chapter)

Rule 2.4 targets cross-chapter drift. Within a single chapter, a subtler problem appears: multiple near-synonyms used interchangeably for the same concept. The reader has to decide whether they're the same or distinct. Drift families tend to look like these, which are illustrative rather than a checklist -- each book grows its own:

- habit / practice / routine / technique / method
- harvest / yield / crop
- diet / eating plan / regimen
- loan / debt / credit
- bed / plot / patch
- framework / approach / system (when self-referential)

**Procedure:**
1. For each chapter, identify its top 20 content nouns by author's eye (no automation -- ending forms and context prevent reliable counting).
2. Flag any pair or trio that share a concept.
3. Pick one canonical term per concept within that chapter. Replace the others.
4. Cross-check against the book glossary (`rules.glossary`): the canonical should match the glossary term.

Companion checks (`SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"`):

```bash
python3 $SCRIPTS/word-for-two-things-check.py  # container nouns used for outside tools AND the book's own ideas
python3 $SCRIPTS/word-sense-check.py           # words in a sense the book avoids (terms.watch_words.word_sense)
```

A word flagged by the first is a concrete case of the "framework / approach / system (when self-referential)" family above. The second only runs when the book lists an avoided sense; `decisions.md` says why the book avoids it.

---

## 2. Example and Argument Ownership (Rules 2.15, 11.4)

Rule 2.15 requires each idea to have one home -- arguments and examples appear once within a Part. In a book with code, Rule 11.4 applies the same to code examples. Either way, each example (a case, a story, a worked figure, a code listing) appears once; later chapters reference it briefly.

### What to Check

- Does any example appear in full in multiple chapters within the same Part?
- Does any argument (chain of reasoning reaching a conclusion) appear in substantially similar form in multiple chapters?
- When a concept from an earlier chapter is referenced, does the reference stay brief or does it re-develop the argument?
- Are back-references doing the work of full re-explanations?

### The Re-Explanation Test

For each back-reference to an earlier chapter:
- **Brief reference** (correct): "Chapter 2 established that compound interest grows faster than simple interest." One sentence, moves on.
- **Re-explanation** (violation): Three or more sentences re-developing the same argument with the same evidence. This is the earlier chapter's content leaking into the current chapter.

### What to Flag

- Same example appearing in full in multiple chapters (with both locations)
- Same argument chain developed in multiple chapters (with both locations)
- Back-references that expand into re-explanations (3+ sentences developing the same point)
- Assessment: intentional reinforcement with new angle, or accidental repetition

---

## 3. Forward and Backward Reference Integrity (Rules 6.3, 2.3)

Rule 6.3 forbids forward references and encourages backward references. This section checks every cross-chapter reference.

### Forward References

Scan for any instance where a chapter references content from a later chapter:
- "We will see in Chapter X..."
- "Chapter X will show..."
- Using a concept in an explanation before the chapter that defines it
- Relying on knowledge the reader doesn't have yet

### Backward References

For each backward reference ("As Chapter X showed..."):
- Does it accurately represent what Chapter X actually said?
- Does it point to the right chapter? (Chapter numbers may have shifted during writing)
- Is the reference specific enough that a reader could find the source?
- Does the reference over-simplify what the source chapter argued?

### What to Flag

- Any forward reference (with location and what it references)
- Backward reference that misrepresents the source chapter (with both locations)
- Backward reference pointing to wrong chapter number
- Concept used before its home chapter introduces it

---

## 4. Thesis Hierarchy Integrity (Rules 12.1-12.3)

Many non-fiction books rest on a hierarchy of ideas: some ideas are the ground, others are built on them. When the book defines one, every chapter must respect it, because prose that inverts or collapses the hierarchy erodes the central argument. Such a finding is more damaging than a prose-style issue because it affects the structure of the book, not just its surface. **When the book defines no hierarchy of ideas, skip this section** and check only back-references (Rule 12.2).

### Hierarchy map (defined by the book)

The map comes from the book (its `thinking/argument/` folder or `decisions.md`), never from this skill. If the author has one in mind but has not written it down, ask for it before running this section. A map lists the rungs from the root down; for each rung it says:

- what the rung holds, and the chapters that establish it;
- what it rests on (the rung above);
- if the book has a way to detect a problem, what that check actually measures;
- neighbouring topics that sit beside the main line and must not be confused with it.

Filled example (fictional, for a history book on city water supply, three rungs):
1. **Evidence:** records of wells, pipes and outbreaks (Ch1-2)
2. **Explanations:** why supply failed where it did, built only on that evidence (Ch3-6)
3. **Lessons:** what a city planner can take from the explanations today (Ch7)
- **Neighbouring topics:** sewage engineering, public-health law

### What to Check

For each chapter:
1. Does this chapter ground reasoning at the right rung -- not skipping up (a lower rung argued without the one it rests on) or down?
2. Does any sentence say a check measures one rung when it actually measures another?
3. Does any section drop a rung (reasoning that hides the rung it rests on)?
4. Do back-references to earlier chapters point to named, defined concepts (per Rule 12.2), or do they invoke informal phrasings?
5. Do sentences naming two rungs keep the thesis direction (the higher rung produces the lower one), per Rule 12.3?

### What to Flag

- Hierarchy inversions (a lower rung presented as the ground of a higher one, or a check described as measuring the wrong rung)
- Rung skips (a chapter argues a rung without grounding it in the one above)
- Back-references to informal phrasings not in the book's glossary
- Thesis-direction reversals (a lower rung described as using the higher one, instead of the higher one producing it)

---

## 5. Part Boundaries (Rules 6.1, 6.2)

Rule 6.1 requires each Part to cover its topic completely, with nothing leaking to later Parts. Rule 6.2 requires each level to hide its internal structure from the level above.

### What to Check

- Does each Part contain everything needed to understand its topic?
- Does any Part depend on content from a later Part?
- Do chapters within a Part form a coherent unit on their topic?
- Could each Part be understood independently of later Parts (given only prior Parts)?

### Part Boundary Assessment

For each Part boundary:
- Does the last chapter of Part N feel like a complete conclusion to Part N's topic?
- Does the first chapter of Part N+1 start fresh (with appropriate backward references)?
- Is there content in Part N+1 that logically belongs in Part N?
- Is there content in Part N that anticipates Part N+1 beyond a brief transition?

### What to Flag

- Content in a later Part that should be in an earlier Part (topic leaks forward)
- Content in an earlier Part that belongs in a later Part (premature coverage)
- A Part that cannot stand on its own without reading a later Part
- Chapters that feel misplaced in their Part

---

## 6. Chapter-Level Structure Consistency (Rules 6.4-6.6, 1.1-1.5)

Rules 6.4-6.6 require principle chapters to explain WHY, application chapters to show HOW, and synthesis chapters to synthesize only. Rule 1.1 requires T-D-C at every level, including chapter level.

### Structural Role Consistency

For each chapter:
- Is it a principle chapter (WHY), application chapter (HOW), or synthesis chapter?
- Does it maintain its role consistently, or does it shift between roles?
- Do principle chapters stay in WHY mode (not drifting into HOW)?
- Do application chapters stay in HOW mode (not re-arguing WHY)?
- Do synthesis chapters avoid introducing new content?

### Chapter-Level T-D-C Quality

Compare across all chapters:
- **Openings:** Do all chapters open by posing a question/problem, not stating the answer? Are some chapters weaker than others?
- **Summaries:** Do all chapter summaries synthesize across sections, or do some recapitulate section-by-section? Is summary quality consistent?
- **Body progression:** Do all chapters have necessary section ordering (rearranging would break logic)?

### Consistency of Quality

Flag chapters where:
- The opening quality is notably weaker than other chapters
- The summary quality is notably weaker than other chapters
- The T-D-C pattern is applied less rigorously than in other chapters
- The chapter feels structurally different from the rest of the book

### What to Flag

- Principle chapter that drifts into application territory
- Application chapter that re-argues principles
- Synthesis chapter that introduces new content
- Chapters with notably weaker openings or summaries
- Inconsistent T-D-C rigor across chapters

---

## 7. Voice and Prose Consistency (Rules 4.1-4.16, 7.1-7.3)

The book should feel like it was written by one person in one voice. Chapters written months apart can drift in tone, formality, sentence patterns, and vocabulary level.

### Voice Consistency

- Is the authorial stance (the one the voice profile and `thinking/author/stance.md` describe) consistent across all chapters?
- Are there chapters that feel more formal or more casual than others?
- Is the use of first person ("I") consistent in frequency and context across chapters?
- Is the use of "you" consistent with the voice profile? (Rule 7.3)
- Are there chapters that use "we" where others don't, against the voice profile? (Rule 7.3)

### Prose Pattern Consistency

- Are fronted inversions used at similar density across chapters? (Rule 4.5: the voice profile's floor, measured as a running gap, with the profile's minimum paragraph gap)
- Is the connector style consistent? (Same types of connectors, similar frequency)
- Is passive voice used at similar rates?
- Are conditional-consequential sequences (Rule 4.6) used consistently?

### Vocabulary Consistency

- Is vocabulary complexity consistent across chapters? (Rule 5.4: plain words)
- Are there chapters that use more complex vocabulary than others?
- Is the technical register consistent? (Rule 4.14: familiar first, precise after schema)

### Tone Shifts to Watch For

- Early chapters often more polished (written first, revised more)
- Later chapters sometimes more rushed or less rigorous
- Chapters written after a break may have a different rhythm
- Chapters on topics the author feels strongly about may be more assertive

### What to Flag

- Chapters with notably different voice or tone
- Inconsistent use of person (I/you/we/one) across chapters
- Chapters with significantly different inversion or connector frequency
- Vocabulary complexity outliers (chapters notably above or below A2)

---

## 8. Cross-Chapter Transitions

How chapters connect to each other at their boundaries.

### Chapter Endings

For each chapter ending:
- Does the final section synthesize the chapter's argument?
- Does the closing create a natural bridge to the next chapter?
- Is the bridge an open question in words the reader already has (correct, Rule 6.3) or a preview of the next chapter's content (a forward reference)?

### Chapter Openings After Prior Chapter

For each chapter opening (except Chapter 1):
- Does it connect to the previous chapter's conclusion?
- Is the connection explicit or must the reader infer it?
- Does the opening acknowledge the journey so far before posing the new question?

### Transition Quality

- Are chapter-to-chapter transitions varied? (Not all "The previous chapter showed...")
- Do transitions feel natural or mechanical?
- Does the book build momentum across chapters, or does each chapter feel standalone?

### What to Flag

- Chapter ending that doesn't set up the next chapter at all
- Chapter opening that ignores the previous chapter
- Mechanical transition ("In the previous chapter we saw... Now we will...")
- Missing sense of progression across chapters

---

## 9. Heading and Formatting Consistency (Rules 8.1-8.5, 9.5-9.9)

Per-chapter reviews check whether headings and formatting are correct. This section checks whether they're consistent across all chapters.

### Heading Pattern Consistency

- Do all chapter titles follow the same pattern? (e.g., all "What X Means" / "How to Y" or mixed?)
- Do section headings (##) follow the same depth and phrasing conventions across chapters?
- Is subsection (###) usage consistent? (Some chapters use them heavily, others not at all?)
- Do heading depths stay consistent? (Some chapters go to ####, others stop at ##?)

### Formatting Consistency

- Is italic-on-first-use for new concepts applied equally rigorously across all chapters?
- When the book shows code: is monospace for code names applied consistently? (Some chapters might be less rigorous)
- Is bold usage consistent? (Rule 9.8: headings only -- do any chapters use bold in running text?)
- Are list vs. prose decisions consistent? (Rule 9.2-9.3: some chapters might over-use lists where others use prose)

### What to Flag

- Chapters with heading patterns that differ from the book's dominant pattern
- Chapters where formatting rules are applied less rigorously
- Inconsistent heading depth across chapters

---

## 10. Citation and Grounding Consistency (Rules 2.9-2.10, 2.16, 3.5)

### Citation Density

Run the check-facts skill's completeness check (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/reference-format-check.py --completeness`) first to get per-chapter citation counts and orphaned entries.

Run the person-introduction check to find persons whose first mention (anywhere in the book) lacks a proper introduction, uses only a bare surname, or is re-introduced with full credentials after the first mention. Rule 2.7 is a whole-book property, so this check belongs to the cross-chapter review rather than any per-chapter pass:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts/person-introduction-check.py
python3 ${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts/person-introduction-check.py --bare-mentions
```

Then check qualitatively:
- Are some chapters well-grounded with citations while others make claims without references?
- Is the citation style consistent? (Some chapters might use narrative citations, others parenthetical)
- Are primary sources cited consistently? (Rule 2.16: some chapters might cite the originator, others cite secondary syntheses)
- Is the expert introduction pattern consistent? (Rule 2.7: introduce before quoting -- applied equally across chapters?)
- Are names used the way the `## Names` section of the voice profile says on later mentions? (Rule 2.7) When the voice asks for full names on later mentions or after long gaps, `--bare-mentions` lists every bare surname with a PRONOUN or EXPAND suggestion; verify each.

### Abstract Grounding

Rule 3.5 requires abstract paragraphs to be grounded with concrete examples or reader experience. Check consistency:
- Are there chapters with long abstract stretches without grounding?
- Are there chapters that ground every abstract point while others don't?
- Is the ratio of reasoning to examples roughly consistent across chapters?

### What to Flag

- Chapters with notably fewer citations than others (density outliers)
- Chapters where expert introduction is inconsistent with the rest of the book
- Chapters with long ungrounded abstract passages where other chapters ground consistently
- Inconsistent use of primary vs. secondary source citations

---

## 11. Quantitative Consistency (Scripts)

Run these scripts to get hard data before the qualitative review:

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"
python3 $SCRIPTS/sentence-and-paragraph-check.py --stats  # sentence and paragraph statistics per file
python3 $SCRIPTS/sentence-and-paragraph-check.py --style  # connectors and inversions per section
python3 $SCRIPTS/sentence-and-paragraph-check.py --inversions
python3 $SCRIPTS/term-density-check.py                    # coined terms; phases from writing.term_phases or --phases
```

Add the check-facts skill's `python3 ${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/reference-format-check.py --completeness` for per-chapter citation counts.

### What to Compare

Build a comparison table from the script output:

| Chapter | Sentence Compliance | Avg Sentence Length | Paragraph Compliance | Inversions/Section | Connectors/Section |
|---------|--------------------|--------------------|---------------------|-------------------|--------------------|
| Ch 1 | | | | | |
| Ch 2 | | | | | |
| ... | | | | | |

Flag chapters that are statistical outliers:
- Sentence compliance notably below the voice profile's `sentence_target_share`
- Average sentence length notably different from the book's mean
- Paragraph compliance notably below average
- Inversion or connector frequency notably different from the book's mean

---

## Output Format

For each issue found:

| Priority | Location | Text | Rule | Issue | Details |
|----------|----------|------|------|-------|---------|
| High/Medium/Low | Ch X + Ch Y | the words at fault in each chapter, quoted exactly | Rule number | Description | Specifics |

### Priority Levels

- **High:** Terminology drift between chapters (reader confusion), forward references, Part boundary breaks, example duplication across chapters
- **Medium:** Voice shifts between chapters, inconsistent T-D-C quality, weak cross-chapter transitions, structural role confusion (WHY vs HOW)
- **Low:** Minor quantitative inconsistency, varied inversion frequency, transition variety suggestions

### Summary

At the end, provide:
1. **Terminology consistency:** How many terms drift? Which are most problematic?
2. **Example ownership:** Any duplicated arguments or examples? How many re-explanations?
3. **Reference integrity:** How many forward references? How many inaccurate backward references?
4. **Part boundaries:** Do Parts contain their topics, or do they leak?
5. **Structural consistency:** Which chapters are structurally strongest/weakest?
6. **Voice consistency:** Is the voice uniform, or are there notable shifts?
7. **Transition quality:** Do chapters connect well at boundaries?
8. **Heading and formatting consistency:** Any chapters that deviate from the book's patterns?
9. **Citation and grounding consistency:** Any chapters with notably different citation density or grounding?
10. **Quantitative outliers:** Which chapters are statistical outliers and on what dimensions?

### Also Report What Works Well

Note chapters that connect seamlessly, terminology that stays perfectly consistent, transitions that build genuine momentum, and Parts that hold their topic cleanly. This tells the author what to protect during revision.
