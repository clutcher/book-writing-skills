# Vocabulary rules: container words, reserved words, substitutes

Rule 2.4 asks for one name per concept. These are the ways books break it without noticing, and
how to check. The book's own word lists live in `book.yaml` (`terms.watch_words`); its rulings
on particular words live in `decisions.md`.

## Do not coin a container for things already named

When the book needs to refer to a bundle of concepts it has already named, do not coin a new
container term for the bundle ("our framework", "the balance method"). Use the existing names
at the right scope: the book's title for the whole book, the name of a Part's topic for that
Part, the name of one idea for that idea.

Why: a container whose name does not predict its contents costs the reader an extra item without
saving one. And when the container word already means something else in the field (a
"system" is also the school system or the immune system the reader already knows), the reader gets no signal which sense is
meant, so the book's own bundle blurs with the outside thing.

Test before adding a container: do the existing names plus a phrase that says the scope already
cover every place the container would appear? If yes, do not add it.

**Check:** `word-for-two-things-check.py` flags container nouns ("framework", "mechanism",
"approach", "system", "structure", "tool", "discipline") used both for outside things and for the
book's own ideas. It knows the book's own words from `terms.families` and
`terms.watch_words.container_terms.book_terms`, and the outside things from `outside_names`
there (the named methods, schools or products the reader knows; with none, the check prints
SKIPPED); `watchlist` there replaces the default nouns.
It is a surfacer: expect false positives. Reserving a word (for example "framework" only for
outside frameworks) is a book decision: suggest it to the author, revise-from-notes records it in
`decisions.md`, and the book's own Vale package may guard it.

## Reserve the weight words of your core concepts

When every passing idea is called "a principle" (or "a law", "a rule", "a pattern"), the book's
few real principles lose their weight. Reserve the weight word for the concepts the book
actually builds on and for named, cited outside ones. A local idea gets a lighter word: idea,
link, point, requirement, distinction, effect, or a lead-in that previews the statement without
labelling it ("This reduces to ...").

What a book reserves is often a form, not only the word: a labelled definition blockquote, a
capitalized name. The reservation belongs in the glossary as a usage entry and in
`decisions.md` (both written through revise-from-notes), so reviews know it.

A blanket Vale rule on such a word usually over-flags its many legitimate uses; guard it through
the glossary and review instead.

## Check a substitute for collisions before swapping

Swapping one word for another can trade one collision for a worse one. Before replacing a word
across the book, grep for the substitute's other senses in the manuscript. Example: replacing
"diet" with "plan" collides with "meal plan" and "savings plan" in a book on health and money.

## Words used in an avoided sense

A book sometimes drops a framing on purpose (for example describing a dish as a list of separate
"flavours") and removes the word, only for a synonym to bring the framing back ("each note of the
sauce", "a single taste"). `word-sense-check.py` lists the watched words when they sit in the
grammar of that framing (quantifiers, splitting, owning, scoping). Its signal patterns are built
in and fit only this one kind of avoided sense: a thing described as a set of separate,
countable parts. For an avoided sense of another kind, search for the words directly or add a
rule to the book's own Vale style. The words, the name of the
avoided sense and the nouns for the scope signal (`scope_targets`) are in
`terms.watch_words.word_sense`; the reason belongs in `decisions.md`.

## One word form for a defined term

A defined phrase keeps its exact form everywhere, including slogans, summaries, boxes and the
back cover. A shortened form ("slow rise" for a defined "slow, cool rise")
is a new term the reader must reconcile, and it can change the claim.

## Name the category, not the current instance

When a statement is about a kind of thing, name the kind, not today's example of it: "any app
that tracks your spending", not the product that is popular this year. The book then does not
date, and the claim stays true when the instance changes.

## Do not invent compound terms

Do not coin labels such as "season-level choice" or "bed-level plan" in prose or in review
findings. Use the book's own defining clauses. An invented compound reads as a term the reader
missed.
