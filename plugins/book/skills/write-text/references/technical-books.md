# Extra rules for books that show code

Rules 5.6, 9.6, 9.7 and 11 as they apply to a technical book. A book with no code can skip this
file.

## Write for the whole technical audience (Rule 5.6)

A book for developers in general must not read as if written for one language community. Prefer
neutral terms ("function" where the language does not matter; "module" over a
language-specific packaging term). When a concept belongs to one ecosystem (access modifiers,
compilation units, dependency-injection containers), explain it briefly or use a universal
equivalent. Which kinds of example a book avoids (for instance code from one corner of the
audience) is the book's own decision, kept in its `decisions.md`. If the book uses one language
for its examples, say so once and say that the ideas carry over.

## Code names and concept names (Rules 9.6, 9.7)

- Every code identifier in running text (class, method, variable, keyword, data type, file name)
  is `monospace`, on every occurrence, because it names something the reader could find in code.
- The same word can be a concept or a code artifact: *italic* (first use) or roman for the idea,
  `monospace` for the artifact. The context decides which.

## Person in a coding scenario (Rule 7.3)

When the text places the reader in a coding scenario, "you" usually reads best ("When you add a
parameter to a function, you update every place that calls it"). The voice profile has the
final say.

## Code examples (Rule 11)

The rules 11.1-11.5 are in `rules-explained.md`. In practice:

- **Complete enough to read without guessing** (11.1): every variable declared or its origin
  obvious; what happens with a collection the example fills.
- **Looks like production code** (11.2): names and domain shapes the reader would meet at work.
- **Neutral constructs** (11.3): a plain number and a plain object unless the precision is the
  point; note equivalents when a language-specific construct is needed.
- **Once per Part** (11.4): one chapter owns an example; later chapters reference it briefly.
- **Shows exactly what the text claims** (11.5): if the text says logic is buried after detail,
  both the detail and the logic are in the example.

Minimalism for examples (`writing-research-basis.md`): start from working code, keep only what
the lesson needs, make the example about a task, and show the common error when the lesson is
about avoiding it.
