# The glossary: format and rules

The glossary (path: `rules.glossary` in the book's config) is a **bank**: the source of
truth for the terms the book formally defines and their canonical wording. The review-ideas
skill (editor mode, map stage) seeds it, the author curates it, and `glossary-check.py` audits
the manuscript against it. It is not read by readers of the book.

## Entry format

```
### <term> -- <location> (<kind or attribution>)
**Canonical definition:** <the definition, in the book's own wording>
**Invariants:** <only when the term needs one; see below>
```

- **The heading is machine-read.** The text between term and location is the heading separator,
  ` -- ` by default (config `glossary_format.heading_separator`). Keep it exactly; do not turn it into
  a dash character.
- **A qualified term** has two separators: `### soil -- clay -- Ch12 S12.5` is the
  term "clay soil". The last part is always the location; the parts between term and
  location are qualifiers, read before the term.
- **Search forms.** The script searches the manuscript for the term as written, and derives other
  forms from a trailing parenthetical: `Soil Organic Matter (SOM)` searches both, `Foo (also: Bar)`
  searches both, and any other parenthetical such as `(principle)` is dropped from the search.
- **Fields** are `**Name:** value` lines. Only `Canonical definition` and `Invariants` are read.
  A seeded entry has only `**Canonical definition:** [TO CURATE]`; the author writes it, and adds
  an `Invariants` line only when the rule below needs one.

## The location notation is the book's choice

The location says where the manuscript defines the term. It is read with the regular expression
in `glossary_format.location_pattern`. The pattern must match at the start of the location and has
one of two named groups:

- `chapter`: a chapter number, matched against the chapter number of each manuscript file
  (`manuscript.chapter_pattern`);
- `file`: a word looked up in the manuscript file names, so `Preface` finds `040-preface.md`. The
  word must match whole parts of the name (the parts between `-` and `_`), so `word` does not
  find `000-foreword.md`.

The default reads `Ch3 S3.1`, `Ch.3`, `Chapter 3`, or a file word:

```
^(?:Ch(?:apter)?\.?\s*(?P<chapter>\d+)\b|(?P<file>[A-Za-z][\w-]*))
```

A book that writes `§3.1` sets, in `book.yaml`:

```yaml
glossary_format:
  location_pattern: '^(?:§(?P<chapter>\d+)|(?P<file>[A-Za-z][\w-]*))'
```

A location that names no manuscript file (for example `book usage` on a word-discipline entry) is
allowed: the term is still counted, only the used-before-defined check is skipped for it. The
review-ideas skill (editor mode, map stage) writes `Introduced` in the definitions index in this
same notation, so a seeded heading needs no rewriting. `glossary-seed.py` reports a new term whose
location names no manuscript file as `location-not-found`, so a wrong notation is seen before it
is written.

## Rules

- **Dateless.** The bank holds no dates, statuses, verdicts, counts or per-run findings. Git is
  its history. Drift findings live in the run's `stage-2-attack.md`; usage per file is computed
  live by `glossary-check.py`. Seeding never writes a "last seeded" date.
- **A seeded entry is a pointer, not the truth about usage.** Drift auditing always re-reads the
  manuscript; it never treats a `[TO CURATE]` entry as a statement of how the book uses a term.
- **Never overwrite curated fields.** Seeding adds missing entries only.
- **The glossary is canonical for definition wording.** Other files that need a definition (the
  author's stance notes, argument files) point to the glossary entry instead of restating it.
- **The trailing parenthetical is overloaded, on purpose.** It holds either a source kind
  (`blockquote`, `definition sentence`, `book usage`, `word discipline`, ...) or the name of whoever
  coined the term. Any tool that filters on it uses an exclusion list, never an allow list: an
  allow list drops the attributed terms.
- **Membership is not italic eligibility.** Kinds such as `word discipline` or `book usage` exist to
  stop ordinary words drifting; they are not new terms and do not get first-use italics.
- **Invariants only when needed.** An entry has an `Invariants` line only when the term has a
  competing meaning in the field that the definition alone does not block. Terms the book coins,
  and field terms used as-is, have no invariants: the definition is the constraint.
