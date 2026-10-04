# Voice profile: paper

This profile is for a research paper (`kind: paper` in `book.yaml`). The init skill copies it to
the paper's `rules/voice.md`, and the author changes that copy. It keeps the plain English of
the default profile and adds the habits a research paper needs: a stated list of
contributions, claims no larger than the evidence, precise hedging, open threats to validity,
and numbers with their uncertainty. The prose sections tell the writer how the paper sounds;
the `## Settings` section gives the numbers the checks use.

The rules in `references/rules-explained.md` say *what* good prose does, and Section 13 there
holds the rules that only a paper has. This file says *how this paper* does it. When the two
meet, the rule sets the goal and the voice sets the form.

## Sentences

- Aim for sentences of about 10 to 25 words. A longer sentence is fine for a definition or a
  chain of reasoning, if every clause hangs off the end of the one before it.
- One claim per sentence. A sentence that states a result and its cause states two claims;
  split it unless the cause is the point.
- Keep the subject and the verb close together.

## Paragraphs

- One idea per paragraph, usually two to six sentences. A paper paragraph is shorter than a
  book paragraph, because a reader looks for one point and moves on.
- The first sentence of a paragraph says its point. A reader who reads only first sentences
  should still follow the paper.
- A one-sentence paragraph is fine when it leads into a list.

## Contributions

- The introduction ends with a numbered list of contributions, each one item a reader can use
  or check, and each one naming the section that supports it.
- Every contribution in the list is shown in the paper. Nothing the paper shows is a larger
  contribution than the list says.
- The conclusion answers the question of the introduction; it does not add a new contribution.

## Claims and evidence

- Scope every claim to what the evidence shows: the data, the setting, the people and the
  time it comes from. "In our twelve beds" is a claim; "in gardens" is a different one.
- Say what kind of evidence stands behind a claim: measured, observed, reported by others, or
  reasoned. Do not let a reasoned claim read like a measured one.
- Separate the result from your reading of it. Give the number first, then what you think it
  means, and mark the second as yours.
- Cite the work that first had an idea, and say what it showed, not only that it exists.

## Hedging

- Hedge precisely, never vaguely. Say what is uncertain and why: "the effect held in both
  seasons we measured, and we did not measure a dry year" is precise; "this may possibly
  suggest" is vague.
- Use one hedge per claim, placed on the part that is uncertain. Two hedges on one claim
  ("may perhaps") hide what you know.
- Do not hedge what the evidence shows. A measured result is stated as measured.
- Prefer plain words of degree with a reason ("likely, because ...") to stacked qualifiers.

## Threats to validity

- Name every threat openly, in its own section: what could make the result wrong (internal),
  what could stop it holding elsewhere (external), and what could mean you measured something
  other than what you meant (construct).
- For each threat, say what you did to reduce it, or say plainly that it remains.
- A threat is not an apology. State it as a fact about the study, in the same voice as the
  results.

## Numbers

- Give every measured number with its uncertainty: a range, a standard deviation, a confidence
  interval, or the number of runs. Say which one it is.
- Give the unit every time, and the same unit across the paper.
- Report the size of an effect, not only whether a test found it. A p-value alone is not a
  result.
- Round to the precision the measurement supports. Three decimals on a noisy number claim a
  precision you do not have.

## Terms

- Define every term before its first use, in the sentence where it first appears or before it.
  A term the field already shares needs a citation, not a definition.
- One name for one thing across the whole paper, in the text, the figures and the tables.
- Spell out an abbreviation at its first use, and use it only when it appears several times.

## Words to avoid

- No marketing words: novel, groundbreaking, revolutionary, cutting-edge, state-of-the-art as
  praise, seamless, powerful, significant (unless it is a statistical result).
- No words that grade the reader: obviously, clearly, simply, of course.
- No intensifiers that add nothing: very, extremely, highly, truly.

## Connecting sentences

- Show how each sentence relates to the one before it. Use plain connectors: *so*, *because*,
  *which means*, *but*, *then*.
- Point to figures, tables and sections by their number ("Figure 2 shows ...", "Section 4
  describes ..."). Every figure and table is named in the text before or near where it appears.

## Word order and constructions

- Use normal English word order. Fronted inversions are not expected.
- Use active voice by default, with "we" as the actor. Use passive voice when the actor does
  not matter ("the soil was measured each morning").
- Prefer verbs to nouns made from verbs ("we measured", not "a measurement was performed").

## Prepositions

- Use the plain, common preposition. Once a phrase is chosen, use the same form across the
  paper.

## Punctuation

- Colons introduce an explanation, an example or a list.
- Semicolons are allowed but rare. No exclamation marks.
- Do not wrap a phrase in a pair of dashes. Use commas, a colon or a new sentence.

## Person

- "We" for what the authors did, found and think, also for a single author.
- "You" is not used; the paper describes, it does not instruct.
- Never "we" for people in general or for a whole field: name them ("developers", "earlier
  studies").

## Names

- Name a person by surname with the citation ("Doe [@Doe19] showed ..."). The full name is not
  needed.
- A work: cite it by key; give the title only when the title itself matters.

## Possessives

- Keep the possessive `'s` where it reads naturally. Rephrase a possessive on a word that
  already ends in "s".

## Settings

sentence_min_words: 10
sentence_max_words: 25
sentence_review_below: 6
sentence_review_above: 40
sentence_target_share: 0.8
paragraph_min_sentences: 2
paragraph_max_sentences: 6
inversion_gap_words: 0
inversion_min_paragraph_gap: 3
inversions_per_section: 0
