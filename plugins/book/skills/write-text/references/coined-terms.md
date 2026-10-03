# Coined terms: introducing, repeating and placing them

A book that coins a term (or borrows one from another field and gives it a new meaning) must
teach it. This file holds the method and the research behind rules 3.9 to 3.14 and behind
`term-density-check.py`. Examples come from an invented gardening book: the coined adjective
*open* and its antonym *closed*, as in "open soil" and "closed soil".

## The book's term registry

The terms live in the book config, never in this skill:

```yaml
terms:
  families:
    - {term: open, role: primary, also: [openness]}
    - {term: closed, role: antonym}
    - {term: ledger, role: borrowed}
  compounds: [open soil, closed soil, open bed]
```

| Role | Meaning | Learning phase |
|---|---|---|
| primary | a coined term, new to the reader | full: 10-15 encounters, then maintenance |
| antonym | the opposite of a coined term; its own word family | full, of its own |
| borrowed | known from another field; only the mapping is new | minimal |

Families drive the density report; compounds drive the drift check (a use of a family word in a
compound the book has not accepted). A book may have several primary and antonym pairs: list each
primary, then its antonym. Each antonym pairs with the nearest primary above it that has no
antonym yet.

## Running the check

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"
python3 $SCRIPTS/term-density-check.py                                 # whole manuscript
python3 $SCRIPTS/term-density-check.py --phases "1-3:learning,4-8:maintenance,9-10:deepening"
python3 $SCRIPTS/term-density-check.py --verbose                       # every match with context
python3 $SCRIPTS/term-density-check.py --debug                         # word positions and gaps
python3 $SCRIPTS/term-density-check.py --pages 280                     # page count override
python3 $SCRIPTS/term-density-check.py --terms "compost,mulch"         # ad-hoc terms, no drift check
python3 $SCRIPTS/term-density-check.py --pattern '*-ch-*.md' <folder>  # name the chapter files
python3 $SCRIPTS/term-density-check.py --first-use                     # first italic/bold use of each glossary term
```

`writing.term_phases` in book.yaml sets the default phases; `writing.words_per_page` sets the
page estimate (390 by default). Chapter order matters for phases, gaps and deserts: chapters
are the files the config classifies as chapters (`manuscript.chapter_pattern`), in chapter
order. Without a match the script reads every file in name order and warns; with `--pattern`
it refuses rather than guess.

The report shows per-chapter counts and density (with a phase column under `--phases`), a
phase summary with targets, per-term thresholds by role, gaps over 3,000 words inside one
chapter, where mentions sit (introduction, body, summary), distance statistics (minimum, median,
average, 90th percentile, maximum), antonym pairs within 100 words, paragraphs with more than two
mentions of one term, the ten largest gaps, and compound drift.

`--first-use` reports the first emphasised occurrence (*italic* per Rule 9.5, or **bold** for a
term defined in a blockquote) of each glossary entry under `## Defined terms`. Entries under
`## Usage and drift guards` guard a word's meaning (Rule 2.4) and are not italic candidates;
`--all-kinds` lists them too.

The distribution is expected to be **uneven**: dense in learning chapters, sparse in
maintenance, denser again where the meaning deepens.

## 1. What counts as a new term

**Word family** (Bauer and Nation 1993; Nation 2001): a base word plus its inflected and derived
forms (clean, cleans, cleaned, cleaner, unclean, cleanness). The framework covers single words
only; compounds, abbreviations and proper names are outside it. An antonym is a separate family:
"open" and "closed" each need their own encounters.

**Collocations and compounds** ("open soil", "green manure", "hungry gap") are multi-word
units, not family members. Their learning burden depends on transparency (Nation 1990, 2001):

| Compound | Burden | Why |
|---|---|---|
| Transparent ("open soil", once "open" is known) | near zero | the meaning is the sum of the parts |
| Becoming a name ("Open-Soil Gardening") | low | still transparent |
| Opaque ("green manure", "hungry gap") | full | the meaning is a metaphor that must be learned |

So transparent compounds count as encounters with the base term and need no threshold of their
own.

## 2. Antonym interference

Presenting related words together hinders learning (Tinkham 1993; replicated by Waring 1997),
most strongly when they are introduced at the same time.

| Pattern | Effect |
|---|---|
| Both introduced in one paragraph | interference: the reader confuses which is which |
| Base term first, contrast later in the section | moderate |
| Base term in one chapter, contrast in the next | best for retention (spacing) |
| Alternating four or more times in one paragraph | worst |

Define the primary term clearly before the contrast; alternate at most once per paragraph while
the reader is learning. After two or three chapters both terms are established and pairing them
reinforces rather than interferes.

## 3. How many encounters

| Threshold | Encounters | Source |
|---|---|---|
| Basic recognition | 6-10 | Kachroo 1962; Waring and Takaki 2003; Webb 2007 |
| Clear gains | 7+ | Horst, Cobb and Meara 1998 |
| Measurable incidental learning | 10+ | Webb 2007 |
| Full knowledge (form, meaning, use) | 20+ | Webb 2007 |
| Worth introducing an abbreviation | 5+ uses | house rule of this skill, no study |

The thresholds apply per word family.

## 4. Spacing: front-loaded, growing gaps

Forgetting is steepest right after learning (Ebbinghaus 1885), so early repetitions come close
together and later ones farther apart (Mace 1932; distributed practice: Bloom and Shuell 1981,
Cepeda et al. 2006). Within a chapter: define; use again within a paragraph or two; two more
uses in the section; a few more spread through the chapter; then natural uses in later chapters.

## 5. Two phases per term

| Phase | What governs | Target |
|---|---|---|
| Learning (the defining chapter plus two or three) | an absolute threshold | 10-15 encounters, front-loaded |
| Maintenance (the rest) | density | about one per 10,000 running words (a working figure of this skill, not a research finding); never zero in a chapter |

```
minimum_total          = learning (10-15) + maintenance
maintenance_encounters = remaining_words / 10,000
```

| Book | Words | Minimum total | Comfortable |
|---|---|---|---|
| ~160 pages | ~60,000 | ~16-21 | ~25-35 |
| ~250 pages | ~90,000 | ~19-24 | ~35-45 |
| ~400 pages | ~150,000 | ~25-30 | ~45-55 |

The comfortable column is about 1.5-2 times the minimum: above the threshold, below fatigue.
Page counts assume about 390 words per page; set `writing.words_per_page` for your trim size.

Per chapter: learning chapters 5-15 (the defining chapter highest; a definition paragraph may
hold 3-4 mentions), maintenance chapters 1-4, natural uses only, no gap over 3,000 words.

**Deepening a meaning.** Some books add a new layer of meaning to a term in a later chapter.
Related senses reinforce each other (the polysemy advantage: Rodd, Gaskell and Marslen-Wilson
2004), yet each sense is stored separately and switching costs something (Klein and Murphy
2001), and second-language learners know a word's further meanings later than its basic
form-meaning link (Gonzalez-Fernandez 2025, 314 learners).
So a deepening chapter needs more density than maintenance and less than learning. No study
gives a formula. **Phases follow meaning, not position:** a chapter that teaches something new
about what the term means is deepening, wherever it sits; a chapter that applies the known
meaning to new material is maintenance.

## 6. Under- and overuse

Below six or seven encounters most readers do not keep a term; after a long gap they start from
zero. Overuse reads as a slogan: fatigue, formulaic prose, and the risk that readers repeat the
term without understanding it. Keep the term consistent (no synonyms), natural, and at most two
mentions per paragraph after the learning phase, per term and for an antonym pair combined.

A borrowed term used once for an analogy needs no learning phase: the reader already holds the
idea and the book only activates it. Strong metaphors need fewer repetitions because they
attach to something the reader already knows.

## 7. Where the encounters sit

- **Structure beats position.** Ideas higher in a text's structure (openings, topic sentences,
  conclusions) are recalled better than details lower down (the levels effect: Kintsch and van
  Dijk 1978; Meyer 1975);
  signals such as headings and previews help memory of what they cue (Lorch 1989).
- **Depth of processing favours the body.** A term the reader derives from reasoning is
  processed deeply (Craik and Tulving 1975), partly generated by the reader (Slamecka and Graf
  1978), and carries higher involvement (Hulstijn and Laufer 2001). A summary mention allows
  mere recognition.
- **Signal consistently.** When only some chapters put the term in a prominent position, the
  others are recalled worse than if no chapter did (Lorch and Lorch 1996). Put the term in the
  introduction of every chapter.

| Zone | Job | Use |
|---|---|---|
| Introduction | primes the idea | always |
| Body | deep encoding through reasoning | learning and deepening chapters, where the term emerges from the argument |
| Summary | retrieval and consolidation | always |

In maintenance chapters an introduction-and-summary pattern is enough when the body argument
does not naturally call for the term.

## 8. Integrating a coined metaphor

- **Earn it.** Use the coined word only where it adds something no other word adds: it names the
  exact combination the book defined, names a specific property, or explains WHY by drawing on
  its source domain. If "good" or "well-built" could replace it without loss, it is not doing
  its job, and every such use dilutes the definition.
- **Place it where it serves the argument.** Terms dropped into existing explanations break the
  idea chain and the sentence chain and read like marketing. The summary is a safe
  position in maintenance chapters, because the argument has already landed there; naming is
  not explaining.
- **No forward vocabulary.** When a metaphor is disclosed in layers across
  chapters, a chapter may use only the vocabulary the reader has earned so far. Backward
  references are safe; a later layer's words are not.
- **A guardrail at every site where the metaphor states a fact about its source.** Wherever the book states
  a property of the source domain in its own voice, a reader from that field reads it as a claim.
  Check each such sentence against the source domain; keep claims about the book's own subject on
  that side of the comparison.
- **Name meanings, not lines.** A design note about the metaphor refers to the meaning by its
  number, not to a chapter and line, because line numbers go stale with every draft.
- **Keep the vocabulary small and registered.** Accept a new compound only by adding it to
  `terms.compounds`; the drift check flags every other form.

## What the research does not cover

No study compares bookend-only placement with body placement in textbooks; none uses coined
metaphors in first-language prose (they use second-language words or pseudo-words); none gives
spacing for a term that gains meanings over time; none separates a term that emerges from the
argument from one inserted into it. The rules above are inferred from adjacent findings.

## Sources

Bauer and Nation (1993) "Word Families". Nation (1990, 2001, 2013)
*Learning Vocabulary in Another Language*. Tinkham (1993) *System* 21(3). Waring (1997) *System*
25(2). Kachroo (1962). Waring and Takaki (2003) *Reading in a Foreign Language* 15(2). Webb
(2007) *Applied Linguistics* 28(1). Horst, Cobb and Meara (1998) *Reading in a Foreign Language*
11. Uchihara, Webb and Yanagisawa (2019) *Language Learning* 69(3). Ebbinghaus (1885). Mace
(1932). Bloom and Shuell (1981). Cepeda et al. (2006) *Psychological Bulletin* 132(3). Rodd,
Gaskell and Marslen-Wilson (2004) *Cognitive Science* 28. Klepousniotou and Baum (2007) *J.
Neurolinguistics* 20. Klein and Murphy (2001) *J. Memory and Language* 45. Srinivasan and
Rabagliati (2021) *Child Development Perspectives* 15. Gonzalez-Fernandez (2025) "How Is
Vocabulary Learnt? An Acquisitional Sequence of L2 Word Knowledge", *TESOL Quarterly* 59(2)
755-784, DOI 10.1002/tesq.3342. Bruner (1960) *The Process of Education*. Kintsch and van Dijk (1978) *Psychological
Review* 85. Meyer (1975). Craik and Lockhart (1972); Craik and Tulving (1975) *JEP: General*
104(3). Slamecka and Graf (1978). Hulstijn and Laufer (2001) *Language Learning* 51(3). Bjork
(1994). van den Broek et al. (2018) *Language Learning* 68(2), (2022) *Cognitive Science* 46(4).
Lowell, Pender and Binder (2020) *Reading Research Quarterly*. Lorch (1989) *Educational
Psychology Review* 1; Lorch and Lorch (1996) *J. Educational Psychology* 88(1). Ausubel (1960).
Glanzer and Cunitz (1966). Schuler, Kammerer and Becker (2025) *Applied Cognitive Psychology*.
Woloshyn, Pressley and Schneider (1990); Dunlosky et al. (2013). Wittrock (1974, 1992).
