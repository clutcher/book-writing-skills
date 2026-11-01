# Voice profile: default

This profile applies when a book has no voice file of its own (`rules.voice` in `book.yaml`). It holds neutral choices that suit most non-fiction books. A book replaces it by writing its own voice file with the same headings: the prose sections tell the writer how the author sounds, and the `## Settings` section gives the numbers the checks use.

The rules in `references/rules-explained.md` say *what* good prose does. This file says *how this author* does it. When the two meet, the rule sets the goal and the voice sets the form. Where a rule says "per the voice profile", read the matching section below.

## Sentences

- Aim for sentences of about 10 to 25 words. Longer sentences are fine for a chain of reasoning, if every clause hangs off the end of the one before it.
- Join two short sentences when they state one idea. Split a long sentence when it states two.
- Keep the subject and the verb close together.

## Paragraphs

- One idea per paragraph, usually three to eight sentences.
- A one- or two-sentence paragraph is a choice, not a habit: use it for a turn in the argument.

## Connecting sentences

- Show how each sentence relates to the one before it. Use plain connectors: *so*, *because*, *which means*, *but*, *then*.
- Vary the connector. The same connector in every sentence reads as a drum beat.

## Word order and constructions

- Use normal English word order. Fronted inversions ("From this came a rule") are allowed but not expected; the checks do not ask for them.
- Use active voice by default. Use passive voice when the actor does not matter.
- Prefer verbs to nouns made from verbs ("we pull the weeds", not "the removal of weeds"), unless the noun is the real subject.

## Prepositions

- Use the plain, common preposition ("by bank transfer", "kept at room temperature"). Formal forms such as "via" or "in case of" are allowed but not expected.
- Once a phrase is chosen ("for that reason"), use the same form across the book.

## Punctuation

- Colons introduce an explanation or an example.
- Semicolons are allowed but rare. Exclamation marks are not used in argument.
- Do not wrap a phrase in a pair of dashes. Use commas, a colon or a new sentence.

## Person

- "I" for the author's own experience and recommendations.
- "You" when the reader is doing something.
- "We" only when author and reader truly act together; never for people in general or a whole field.

## Names

- First mention of a person: the full name, with who they are and why they matter.
- Later mentions: the surname alone ("Doe argues ..."). Use the full name again when the person comes back after a long gap, for example in a later chapter.
- A work: the full title first; a short form only after that.

## Possessives

- Keep the possessive `'s` where it reads naturally. Rephrase a possessive on a word that already ends in "s" ("the design of Jones", not "Jones's design").

## Settings

sentence_min_words: 10
sentence_max_words: 25
sentence_review_below: 6
sentence_review_above: 40
sentence_target_share: 0.8
paragraph_min_sentences: 3
paragraph_max_sentences: 8
inversion_gap_words: 0
inversion_min_paragraph_gap: 3
inversions_per_section: 0
