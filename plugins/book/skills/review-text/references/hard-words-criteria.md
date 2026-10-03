# When a word is worth flagging

Rules 5.2, 5.4, 5.5 and 5.7 ask for plain English that readers of English as a second language
can follow. This file says which words and phrases are worth a flag and which are not. It
applies to the write workflow, every review and every Vale rule.

## The test

Flag a word or phrase only when it is **opaque to your reader**: they cannot recover its meaning
and it blocks the sentence. Neither a high CEFR level nor being an idiom is enough on its own.
Word difficulty and comprehension difficulty come apart.

## Three kinds that look flaggable but are not

- **Standard collocations of the field and of academic English:** "account for", "draw on",
  "set out to", "carry out (research)", "pay off". The dictionary calls them idioms; a reader of
  the field meets them daily and reads them without effort.
- **Resultative phrasal verbs:** "end up", "turn out", "wind up". They mark a state reached after
  a process, which no plain verb carries. "The loan ends up costing twice the price even though
  no single payment looked large" loses its point as "the loan costs twice the price".
- **High level but transparent:** "which suggests" is B2, yet anyone who knows "suggest" reads it
  at once. Compare "come down to": A1 words, fully opaque.

## Hedges are not filler

"Suggests" marks an inference from evidence; "shows", "means" and "indicates" state a fact and
would overclaim. Never replace a hedge with a stronger verb to make a sentence plainer, and never
add a hedge-to-fact swap to a substitution rule.

## Figurative verbs are not defects

Natural figurative verbs ("the fog hides the valley", "the drought exposes old foundations") are
ordinary English. Replacing them with neutral verbs often reads flatter. Propose a change only
when it clearly adds precision ("hidden costs" -> "fees not shown on the bill", "exposes the
roots" -> "washes the soil off the roots"), and expect such proposals to be rejected often.

## Replacement words must be plain too

A replacement is only an improvement if it is itself plain. "Obscure", "conceal", "mask",
"subtler" and "bury" are harder than the "hide" they would replace.

## Why rules borrowed from Simplified Technical English over-flag

Simplified Technical English (ASD-STE100) was built for maintenance technicians reading manuals
with no shared technical register. A book reader in a field has one: a familiar compound of the
field is one item to them, not several. Ported unchanged, such rules flag the wrong things: a
noun-cluster check flags mostly compounds the reader already knows, and a long phrasal-verb list
flags mostly verbs the reader reads without effort. Keep such checks at suggestion level.

## Adding a rule

Before adding a vocabulary or phrase rule (a Vale rule or a lookup-table row), ask whether your
reader would stumble, not whether a dictionary calls the phrase idiomatic. Then:

- a word with one meaning (`utilize -> use`) may get a substitution;
- a word with several meanings gets an existence rule at suggestion level, and each hit is
  judged in its sentence.
