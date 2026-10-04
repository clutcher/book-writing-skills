---
name: write-text
description: >-
  Writes and rewrites the author's prose of a book or paper, in the manuscript and in the
  thinking files: plan, draft, show, apply, then the text checks. Holds the prose rules, the
  voice profile and the text check scripts the other skills use. Use it when the author asks to
  write, draft, rewrite, polish, fix, tighten or edit the text, or pastes a paragraph with no
  instruction. To run the text checks, use run-checks; to review prose, use review-text; to
  answer open notes, use revise-from-notes.
argument-hint: "[what to write or change]"
---

# Write text

This skill writes and rewrites book prose. The rules below apply to any non-fiction book, and
to a paper as "A book or a paper" says. The book supplies its own voice, its own words (coined
terms, glossary, watch lists) and its own decisions. Nothing here is about one book.

## Before any work

1. **Find the book.** Every script finds `book.yaml` by walking up from the file it checks
   (`--config FILE` names it). Show the setup with
   `python3 ${CLAUDE_PLUGIN_ROOT}/lib/book_config.py show`.
2. **Read the voice profile.** The book's `rules.voice` file, or
   `${CLAUDE_PLUGIN_ROOT}/skills/write-text/profiles/default.md` when the book has none
   (`profiles/paper-voice.md` for a paper). Rules marked "per the voice profile" take their
   form and numbers from it.
3. **Read the author's position** on the topic (`thinking.stance`) and the audience
   (`thinking.audience`) before writing a claim or a recommendation.
4. **Read only the decisions index** (`python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py index`)
   and open the entries you need (`decisions.py show ID`). Never raise or re-propose an item
   marked DECIDED. Before proposing a change, match it:
   `python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py match "<change in a few words>"`.
5. **Read the glossary** (`rules.glossary`): it is the list of terms the book defines.
6. **Check the language.** The rules and checks are for English prose. For a book whose
   `book.language` is not English, the English-only checks print SKIPPED and exit 0; apply
   only the rules that do not depend on English words.

## Working rules with the author

- **Draft, show, then apply.** Show the full proposed text first, with visible formatting and
  what changed and why. Edit files only after the author approves. "Update" in a request is
  the step after approval, not part of the same turn.
- **Apply approved wording exactly.** Never refine approved text while applying it, even to fix
  a flaw you notice. Say what you noticed and ask.
- **A minimal change stays minimal.** Keep the author's words and add to them rather than
  replace them. Do not widen a word fix into a paragraph rewrite.
- **Rewrite rather than patch a patch.** When a passage has been patched twice, rewrite it from
  its idea, then check the seams (`references/write.md`, Step 5).
- **Truth over punch.** Every claim must survive a fact-check. Never attach a cause the book
  cannot show to an observation.
- **Keep copies in sync.** When the same text lives in two places (a definition and the
  glossary, a summary and the back cover), change both or say that the other is now stale.
- **Present changes the agreed way:** `references/presenting-changes.md`.

## Modes

This skill has no modes. Every writing or change verb runs the same loop: write, rewrite,
rework, rephrase, redraft, draft, polish, fix, improve, edit, tighten, refine, clean up, smooth
out, sharpen. So do "apply the style guide" and a pasted paragraph with no instruction (treat it
as a rewrite). Read and follow `references/write.md`. It sizes the work itself, from a
micro-edit of one word to a new chapter. In the thinking files the length and shape rules of a
chapter do not hold (`references/write.md`, "Writing in the thinking files").

Near cases go to a sibling skill: a prose review that writes notes is `review-text`; answering
notes already written is `revise-from-notes`; the words on the back cover and the store pages
are `prepare-sales-text`.

## Rules summary

Every rule as a one-liner. The full text, examples and tests are in
`references/rules-explained.md` under the same number; the numbers are join keys, so do not
renumber. Read the full section for a hard case: a connector (4.2), a coined term (3.9-3.14),
a person's name (2.7), naming before evidence (1.3).

### 1. Structure

1.1. Every unit follows Topic -> Develop -> Conclude.
1.2. Apply the pattern at every level: book, Part, chapter, section, paragraph, sentence.
1.3. The topic frames the question the unit answers; a transition ends with an insight that leads to the next topic.
1.4. Develop explains WHY through reasoning.
1.5. The conclusion connects ideas across sections into a whole the reader could anticipate.

### 2. Narration flow

2.1. Keep the flow smooth; restructure to give context first.
2.2. Each sentence and each paragraph builds from the one before and sets up the next; vary how.
2.3. Ideas build on earlier ideas; the order matters.
2.4. Define terms before use; one name and one word form for one concept across the book.
2.5. Core concepts: explain the mechanism first, then define ("X is ...").
2.6. Background concepts: a definition ("X is ...") is enough.
2.7. Introduce a person before quoting them; full name first, later mentions per the voice profile.
2.8. Develop with reasoning that explains the examples.
2.9. Ground claims with references (pandoc citations, e.g. [@Abc99]; `references/citing-in-prose.md`).
2.10. Grounding varies: introductions use narrative, evidence uses facts and quotes, conclusions refer back.
2.11. Every concept introduced is used later; later sections refer back to it.
2.12. Content serves its section's topic.
2.13. Each sentence and paragraph adds new understanding; restatement is not advancement.
2.14. Openings pose the question; summaries synthesize across sections.
2.15. Each idea has one home: an argument or example appears once within a Part.
2.16. Cite the originator of an idea, not the book that collected it.
2.17. Text agrees with the book's own definitions and thesis.

### 3. Limits

3.1. Length follows from the quality of the ideas and the argument.
3.2. One to three main ideas per section.
3.3. One idea per paragraph; sentences chain, each advancing from the last.
3.4. Paragraph length per the voice profile.
3.5. Ground an abstract paragraph with a concrete example or the reader's experience.
3.6. Sentence length per the voice profile; only named exceptions run short; the tolerance is chapter-wide.
3.7. About four items can be held at once.
3.8. At most one level of self-embedding in a sentence.
3.9. Each coined word family needs 10-15 learning encounters early, then about one per 10,000 words.
3.10. At most two mentions of one term per paragraph (a definition paragraph may need more).
3.11. Antonyms in one paragraph interfere while the reader is still learning them.
3.12. No chapter has zero mentions of a coined term; mention it in the chapter introduction.
3.13. Distribute coined terms front-loaded, with growing gaps, not evenly.
3.14. In learning and deepening chapters, put coined terms in the body of the argument.
3.15. One analytical lens per paragraph.

### 4. Prose style

4.1. Grammatically correct English always.
4.2. Connect every sentence to its neighbours; each connector clause delivers specific content (three-way test: cause, description, or association).
4.3. Use right-branching clauses; add to the end of a sentence.
4.4. Keep subject and verb close together.
4.5. Fronted inversions at the rate the voice profile sets, and varied.
4.6. Use "If ..., then ..." to lay out consequences.
4.7. Prepositions per the voice profile.
4.8. Nouns made from verbs per the voice profile.
4.9. Passive voice only with a purpose.
4.10. Write with authority that comes from the argument.
4.11. State trade-offs directly.
4.12. Use measured language; state substance directly; match claim strength to evidence.
4.13. Join related ideas when a sentence would fall under the profile's minimum.
4.14. Familiar words first, precise words after the idea is built.
4.15. Chain reasoning across sentences, and vary the cadence.
4.16. Punctuation per the voice profile: colons explain, no exclamation marks in argument, few parentheses.

### 5. Audience

5.1. Address the reader as an intelligent person who has not thought about this yet.
5.2. Readable for readers of English as a second language.
5.3. Basic idea first, nuance after.
5.4. Plain (A2) words for general vocabulary; technical terms are allowed.
5.5. Prefer common one- and two-syllable words (lookup table in `rules-explained.md`).
5.6. Write for the whole audience the book names.
5.7. Replace opaque phrasal verbs; keep the ones your reader reads without effort.
5.8. Rephrase a possessive on a word that ends in s.

### 6. Book architecture

6.1. Each Part covers its topic completely; nothing spills into later Parts.
6.2. Each level tells the level above what it contributes, not how it is built.
6.3. No forward references; backward references are welcome; end a chapter on a question, not a preview.
6.4. Each level of the book stays at one level of detail.
6.5. Principle chapters explain WHY; application chapters show HOW.
6.6. Synthesis chapters add no new teachable concepts; new evidence that grounds a synthesized claim is allowed.
6.7. Titles predict content at every level.
6.8. Use the dive-in-and-return rhythm only when the content forms a framework.

### 7. Teaching voice

7.1. "I" is allowed for the author's experience, discoveries and recommendations.
7.2. Questions may lead the reader to a conclusion.
7.3. Person per the voice profile, the same across the book.

### 8. Headings

8.1. A heading is a findable label that works as an index entry.
8.2. Chapter titles frame the central question.
8.3. Section titles (##) say what question the section answers ("What", "How").
8.4. Subsection titles (###) name a concept, an effect or a conclusion.
8.5. Plain language: a term, "The + noun phrase", or a statement.

### 9. Format

9.1. ASCII only (codes 32-126), except letters with accents (an e with an acute accent, an o with an umlaut) in names and words.
9.2. Prose for logical sequences.
9.3. Lists only for reference and scanning.
9.4. Turn three or more short bold-headed paragraphs in a row into connected prose.
9.5. A new term is *italic* at its formal definition, plain after.
9.6. Code names in running text are always `monospace`.
9.7. *Italic* for the concept, `monospace` for the code artifact.
9.8. No bold in running text.
9.9. Quotation marks around a term only for ironic or unusual use, never to define it.

### 10. Priority

10.1. When rules conflict: context first, then explicit structure, grounded argument, connected prose, authoritative voice.

### 11. Code examples (books with code)

11.1. Complete enough to read without guessing.
11.2. Looks like production code.
11.3. Constructs any reader of the audience can follow.
11.4. Each code example appears once within a Part.
11.5. Shows exactly what the text claims.

### 12. Book-level coherence

12.1. When the book defines a hierarchy of ideas, keep it in every sentence that names two levels.
12.2. Refer back only to a named concept in the glossary; otherwise restate the idea.
12.3. Keep the cause-and-effect direction the thesis states.

### 13. Papers (only for `kind: paper`)

13.1. The abstract states the problem, what was done, the main result and what it changes, within `paper.abstract_max_words`.
13.2. The introduction ends with a numbered list of contributions; each names the section that supports it.
13.3. Scope every claim to what the evidence shows: its data, setting and time.
13.4. Hedge precisely: say what is uncertain and why; one hedge per claim, none on a measured result.
13.5. Name the threats to validity openly, in their own section, with what was done about each.
13.6. Give every measured number with its uncertainty and its unit.
13.7. Point to every figure and table from the text, by its number or its label.

## A book or a paper

`kind` in `book.yaml` says which. A book uses Sections 1-12; a paper (`kind: paper`) also uses
Section 13, and its sections are what the rules call chapters. For a paper these are **off**:
1.2 at the book and Part levels; 3.9 and 3.12-3.14, the learning path of coined terms (a paper
defines each term once, before use: 2.4); 6.1, 6.5, 6.6, 6.8 (Parts, kinds of chapter); 7.1 (a
paper says "we"); 8.2. These **change**: 2.15 and 11.4 hold within the whole paper; for 2.14
the abstract and the conclusion open and sum up; 6.3 allows a pointer to a later section by
number; for 5.1 and 5.6 the reader is a researcher new to this paper, and 5.2-5.5 still hold;
8.3 allows the usual titles (Introduction, Method). `paper-check.py` runs only on a paper.

## The text checks

The text check scripts live here; run-checks, review-text and revise-from-notes call them from this folder.
All scripts: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts/<script> [paths] [--config FILE] [--set KEY=VALUE]`.
With no path they read the whole manuscript. Each has `--help`; each check also has
`--self-test` (the Vale runners `vale-run.py` and `vale-sync.py` do not). Exit codes
follow `${CLAUDE_PLUGIN_ROOT}/lib/check_contract.md`: 0 clean, 1 findings, 2 could not run.
Checks that list candidates for the author to judge exit 0. The prose checks
print text only (no `--format tsv` or `json`), so do not pipe them into a tool that expects
columns. For a book in another language, the English-only checks (`ascii-normalize.py`,
`sentence-and-paragraph-check.py`, `unclear-this-check.py`, `word-for-two-things-check.py`,
`person-introduction-check.py`, `paper-check.py`) print SKIPPED.

| Script | Rules | What it reports |
|---|---|---|
| `sentence-and-paragraph-check.py` | 3.4, 3.6 | Sentence and paragraph length against the voice profile. `--stats`, `--style`, `--verbose`. |
| `sentence-and-paragraph-check.py --connectors` | 4.2 | "because" that describes, circular "because", "while" across two measures. |
| `sentence-and-paragraph-check.py --meta` | 4.12 | Sentences that describe the text instead of arguing ("This chapter shows how"). |
| `sentence-and-paragraph-check.py --inversions` | 4.5 | Gaps, proximity and variety of fronted inversions. Run on the whole manuscript. |
| `ascii-normalize.py` | 9.1 | Non-ASCII characters other than letters with accents; `--fix` replaces them. |
| `unclear-this-check.py` | 2.2, 12.2 | A paragraph opening "This/That/These/Those/The + noun" whose noun is not in the sentence before. |
| `word-for-two-things-check.py` | 2.4 | One noun ("framework", "system") used both for named outside things and the book's own ideas; SKIPPED with no `outside_names`. |
| `word-sense-check.py` | 2.4 | Words used in a sense the book avoids (`terms.watch_words.word_sense`). |
| `person-introduction-check.py` | 2.7 | First mentions without the full name or an introduction; `--bare-mentions` lists bare surnames for a voice that wants full names later too. |
| `definition-check.py` | 2.4, 9.5 | Bold definition blockquotes whose term is not in the glossary; `--propose` suggests the bold span. |
| `term-density-check.py` | 3.9-3.14 | Coined-term density, phases (`--phases`), gaps, antonym pairs, compound drift; `--first-use`. SKIPPED on a paper, but for `--first-use`. |
| `paper-check.py` | 13.1, 13.2, 13.5, 13.7 | A paper only: the abstract length, the contribution list, a figure or table no sentence points to, the threats section. |
| `glossary-check.py` | 2.4, 12.2 | Every glossary term in the manuscript: first use against the definition's file, uses per file; `--report FILE` writes the report review-ideas reads. Format of the glossary: `${CLAUDE_PLUGIN_ROOT}/lib/glossary-format.md`. |
| `vale-run.py`, `vale-sync.py` | several | Vale in Docker (pinned image, files written as you). `vale-run.py` never writes; `vale-sync.py --fix` copies PlainBook into the book. See `references/vale-check.md`. |
| `self-check.py` | - | Maintainer check, not for book work: every self-test, rule numbers, file references, leak words (from `$BOOK_LEAK_LIST`, or `--leak-words FILE`). |

**For the whole book** run the run-checks skill once:
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py text` (a file or folder
after `text` checks only that part). **After every writing or rewriting task** run `ascii-normalize.py`, `sentence-and-paragraph-check.py`
(with `--connectors`), `unclear-this-check.py` and `word-for-two-things-check.py` on the
changed files, and `term-density-check.py` when coined terms were touched. A micro-edit runs only
the scripts its change can affect (`references/write.md`, Step 3c).

Citation keys, the bibliography and the source banks belong to the **check-facts** skill; the
content of claims belongs to the **review-ideas** skill.

## Book settings this skill reads

| Setting | Used for |
|---|---|
| `rules.voice` | Voice profile: prose habits and the numbers under `## Settings` |
| `writing.<setting>` | Overrides one voice number, e.g. `writing.sentence_min_words`; also `writing.term_phases`, `writing.words_per_page`, `writing.paragraph_length_exempt` |
| `terms.families`, `terms.compounds` | Coined terms and accepted compounds |
| `terms.watch_words.container_terms` | `book_terms` (the book's own words), `outside_names` (named outside things), `watchlist` (container nouns) |
| `terms.watch_words.people` | `aliases` (other names of a cited author), `eponyms` (laws or tests named after a person, to skip) |
| `terms.watch_words.word_sense` | `name`, `reason`, `words` of the avoided sense, `scope_targets` |
| `rules.glossary`, `rules.decisions` (the index), `thinking.stance`, `thinking.audience` | Read before writing |
| `rules.vale_ini`, `tools.vale_image` | Vale config and pinned image |

## References

| File | Holds |
|---|---|
| `rules-explained.md` | Every rule in full, the lookup tables, preferred patterns |
| `write.md` | The write workflow: micro-edit, write, rewrite, verify, check |
| `vale-check.md` | The Vale check: what it catches, the packages, how to read its output |
| `presenting-changes.md` | How to show proposed changes to the author |
| `coined-terms.md` | How to introduce and repeat coined terms; the density research |
| `term-formatting.md` | Italic, bold, monospace and quotes: publisher conventions |
| `citing-in-prose.md` | Naming authors and works in running text; representing positions fairly |
| `vocabulary-rules.md` | Container words, reserved words, choosing a substitute |
| `style-lessons.md` | Truth and precision lessons |
| `renaming-a-term.md` | What a rename or a changed explanation leaves behind |
| `why-the-rules-work.md` | The cognitive reasons behind the prose rules |
| `readability-scores.md` | What readability formulas measure and what they cannot |
| `writing-research-basis.md` | Rhetoric, cohesion, minimalism: evidence behind the rules |
| `organizing-a-catalog.md` | How to order a catalog of techniques or patterns |
| `technical-books.md` | Extra rules for books that show code |
