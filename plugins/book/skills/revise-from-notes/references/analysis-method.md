# Analysis method

The note names **what the reader felt**. The analysis names the **cause**. Judge the flagged text inside its
paragraph and against the chapter, never as one sentence alone. The order below matters: the
framing is checked before any option is written.

## Tier first

| Tier | What it covers | Research | Context the options must show |
|---|---|---|---|
| **Surface** (`g`) | a plain-English word swap, a possessive, brackets, dashes, italics for a term, one jargon word, a typo, word order | **No.** But look in `decisions.md` for an earlier decision on the same word before you swap it | the full rewritten **sentence**, never a piece of it |
| **Flow** (`a` to `e`) | an unclear "this", repetition, a broken chain of ideas, a weak link, a paragraph whose topic-development-conclusion is broken, split or merge, a new order of sentences, naming a thing before showing it, two points of view in one paragraph | **Only** if a claim is part of the fix | the rewritten sentence **and its neighbours**, or the whole paragraph when three or more sentences move |
| **Content** (`f` and claims) | facts and citations, cause and mechanism, the causes and principles the book names, contradictions with the book's own definitions, a term used across the book, a concept used before the chapter that defines it | **Yes**: argument files (file and section), other chapters, the author's stance, and the web when a real-world fact is at stake | the rewritten sentence in its paragraph, **and** what the change rests on |

A note often moves up a tier while you work. A "vague word" can be a sentence carrying two ideas
(Flow). A new wording can turn out to touch a claim (Content). When in doubt, move up.

### Research triggers

A Surface or Flow note is really a **Content** note when the fix touches any of these:

- a word that an **earlier chapter defined or banned**, or a plain-English choice made earlier in
  the same chapter
- the **mechanism an earlier chapter stated**, which the new wording must still match
- a **claim that needs its source**: open the argument file for the topic (the file in the `thinking.argument`
  folder named for it) and the quotes file entry for each citation key; cite file and section
- the **author's stance** (`thinking.stance`), because a correction about belief never comes from
  the manuscript
- something **an earlier chapter must own first**
- a term the **same chapter introduces later**: scan the headings further down, not only the
  neighbours

Do not open research, other chapters or the web for a Surface note, or for a Flow note that hits
none of the triggers. When a trigger fires, look in the book's own files before the web: a
citation is usually already checked in the quotes file, a term is usually already in the
glossary.

## Root-cause labels

Labels combine: a note can be "`f`, plus `a`". `b` and `g` often come together; `d` often leads
to `e`.

| Label | Cause | Review to run (in the `review-text` skill) | Usual fix |
|---|---|---|---|
| **a** | **Structure**: wrong scope, a piece missing, parts in the wrong place | topic-development-conclusion; paragraph structure | restructure, or add the missing piece |
| **b** | **Announcement**: says an insight is coming ("From this comes an insight about...") instead of saying it | announcements and empty lead-ins | **delete** the announcement and state the claim |
| **c** | **Forward reference**: a term used before it is introduced | order of disclosure; introducing terms | move the term later, or introduce it first |
| **d** | **Compression**: one sentence or paragraph carries two ideas; the reasoning is hidden | one idea per sentence and per paragraph | split; bring the reasoning out |
| **e** | **Repetition**: the sentence adds nothing new; the chain of ideas breaks | the adjacency chain; repetition | cut it, or make it add something |
| **f** | **Frame or term drift**: the framing leaves the paragraph's or the chapter's point, or its words | wrong framing; one word per concept | go back to the book's own frame and word |
| **g** | **Surface**: register, format rules, an invented compound word | plain-English and format rules | swap the word or format locally |

Label to tier: **`g` is Surface. `a`, `b`, `c`, `d`, `e` are Flow. `f`, and anything touching a
claim, a coined term, a cause or principle the book names, or who said what, is Content.**

## Step 1: the paragraph's one idea (the Idea field)

Say what the paragraph is for before you judge the flagged sentence. A paragraph carries one
idea; the flagged sentence is one link in the chain that develops it.

- **Topic, development, conclusion:** name the topic sentence, the steps that develop it, and
  the conclusion or bridge to the next paragraph. Name the flagged sentence's role.
- **Adjacency chain:** for the flagged sentence and its neighbours, write what NEW
  understanding each one adds and what word or idea links it to the one before. An empty "new"
  cell shows repetition (`e`). An empty "link" cell shows a jump (`a`).

This map is the test every option must pass later.

## Step 2: check the framing

Do this before you write any option. See `framing-check.md`.

## Step 3: the root cause, not what the reader felt

Give the `a` to `g` label(s). The cause is often one layer down: a confusing word (`g`) can mean
a sentence in the wrong place (`a`); a missing link (`a`) can mean two ideas in one paragraph
(`d`) or a premise the book contradicts (`f`). Announcements and repetitions that look like
development are candidates for **removal**, not new wording.

## Step 4: the matching review

- **Surface**: the plain-English, format and possessive rules. The new word must keep the plain
  register **and** be the word the chapter already uses for the concept. Pick the word in use,
  not any correct synonym.
- **Flow**: the reviews for announcements, repetition, links, topic-development-conclusion and
  order of disclosure. Also check **one point of view per paragraph**: each paragraph develops
  its idea through one lens; a claim from another lens belongs in its own paragraph, or serves
  only as a result or an example.
- **Content**: the wrong-framing review and the research pass. Check every claim against the
  book's own definitions and the author's stance.

## Step 5: research (Content, and Flow touching a claim, only)

- **Cite the file and the section** you checked, not "per research". A Content fix that does
  not say what it rests on is not finished.
- **Check how the chapter already names the concept**, not only whether a new word is correct.
- **Keep the part of an argument that carries weight.** A clause may be the reason a general
  claim is allowed; cutting it breaks the claim.
- **For any claim about the whole chapter, search the whole chapter** with a pattern, not a
  spot check.
- **Numbers:** every figure must be one the source really gives, for the case the book uses it
  for. If the quotes file has a warning on the source, obey it. If no held source supports the
  figure, the figure goes. A new claim goes through the `check-facts` skill before it is applied.

Write down in the Analysis what the research showed.

## Depth

Analysis and Options are not one line each. The Analysis may carry several rules, numbered
sub-problems, and reasons that tie to linked notes. Options may carry conditions that depend on
linked notes ("If #6 takes its first option, then...").
