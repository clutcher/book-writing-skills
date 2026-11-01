# Quotes Bank

What each source says: verified quotes, findings, scope and guardrails. Keyed exactly like `{{list}}`. The check-facts skill reads and writes this file; its rules are in quotes-format.md of the check-facts skill.

## Entry format

```
### [<Key>] Author, "Title" (Year)

**Verified quotes:**
- p. 12 (Results): "the exact words from the source"
**Key findings:** what the source establishes, as a fact about the source.
**Role:** why the source is on file: what it supports, and what it was considered and rejected for.
**Scope:** population, sample size, design limits.
**Guardrail:** a present-tense instruction: what it may not be cited for.
**Quote origin:** when the words belong to someone the source is itself quoting.
**Relation:** how this source bears on another key.
**Last verified:** YYYY-MM-DD
**Source:** see `{{list}}`
```

The field names are closed at these nine. `Last verified` is the one date in either bank.
