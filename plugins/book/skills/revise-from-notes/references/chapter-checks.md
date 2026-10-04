# Chapter checks: the chapter, the book, and the term files

The defects most often missed on the first pass are **larger than the paragraph**. Run these
after the fit check, on every Flow and Content note, and again on the applied text.

## Chapter guardrails

- **One word per concept in the chapter.** After choosing a word, search the rest of the chapter
  for the concept. Did the fix pick a synonym that now drifts from other sections? Pick the word
  the chapter already uses, and check it in the glossary.
- **Earlier chapters own their definitions.** The fix must match how earlier chapters defined the
  term, and anything it leans on must be introduced upstream. The term checks of the `write-text`
  skill show where each term is first used.
- **Words with many senses.** If the fix uses a word with many senses ("framework", "system",
  "mechanism") or a synonym for a word the book defines, run the `write-text` skill's check for it.
- **"This" after a heading.** If the fix sits near a heading, check that no "this" or "these"
  now points back across the heading at nothing.
- **Some words carry the link to another chapter.** When a fix pays off a callback
  (a named label, a coined term), write in the decision's `Change` field which words carry the
  link, so a later "reads better" edit does not remove them.
- **Sweeps are gates you run again, not tasks you close.** A note that **adds or restores a
  section** must re-run every earlier chapter-wide search (banned words, banned links, register)
  over the new text. New text is how earlier sweeps get undone. For a book-wide word sweep, use
  the `review-text` skill's `consistency` review.
- **Do not wear down sharp wording.** Say so when a later edit trades a sharp, deliberate phrase
  for a flatter one.
- **After a big rewrite, check every note it closed.** When one rewrite answers many notes at
  once, test each of those notes against the new text before you remove it, and search the whole
  manuscript for any label the rewrite retired.

## Term files: the one place a word is decided

Word drift is the problem that most often survives a second pass, because each note decided its
word alone. Do **not** keep a word list for reading notes. The book already has its term files.
**Look in them before deciding a word, and write the decision back after**, so the next note and
the next chapter get it.

| When the note touches | Look in (from the book config) |
|---|---|
| a defined term or its exact definition | the glossary, `rules.glossary` |
| a coined term or a compound made from it | the coined terms in `book.yaml` (`terms.families`, `terms.compounds`) |
| a plain-English word swap | `decisions.md`: earlier word decisions (`decisions.py match "<word>"`) |
| a word borrowed from another field | the book's term-mapping file (what the book uses, does not use, and why), if the book has one; else the glossary |
| a citation (`[@Key]`, `@Key`) or a fact | the quotes file `sources.quotes`, then the `.bib` entry `sources.bibliography` (authors, title, year) and the sources list `sources.list` (where to read it) |
| the reason the book says something | the `thinking.argument` folder, the file named for the topic |
| what the author believes | `thinking.stance` |

Files that hold decided answers carry no dates; the date lives in the decision entry.

**Write-back is required when a note settles a word.** The note is not resolved until the
decision is in its home, or the difference is shown to the author to decide:

- a defined term or its wording: the glossary (the author approves the definition line). A
  glossary entry may carry "Invariants" lines; a fix must keep every one of them
- a borrowed word from another field: the term-mapping file, if the book has one (else the glossary)
- a coined compound: `terms.compounds` in `book.yaml`
- a plain-English word decision: an entry in `decisions.md`

Without write-back, the same drift comes back three chapters later.

## Checks that find what the guardrails look for

Run these on the chapter before and after a Flow or Content fix. Each is in the `write-text` skill
(`WRITING_SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"`); each takes a file or a folder.

| Guardrail | Check |
|---|---|
| "this" or "these" with nothing to point back to | `python3 "$WRITING_SCRIPTS/unclear-this-check.py" <file>` |
| words with many senses ("framework", "system") | `python3 "$WRITING_SCRIPTS/word-for-two-things-check.py" <file>` |
| a word used in a sense the book decided to avoid, or a synonym of a defined word | `python3 "$WRITING_SCRIPTS/word-sense-check.py" <file>` |
| coined-term and compound drift | `python3 "$WRITING_SCRIPTS/term-density-check.py" <file>` |
| a term used before it is introduced | `python3 "$WRITING_SCRIPTS/term-density-check.py" --first-use` |
| announcements and connector misuse | `python3 "$WRITING_SCRIPTS/sentence-and-paragraph-check.py" --meta --connectors <file>` |
| a bolded definition with no glossary entry | `python3 "$WRITING_SCRIPTS/definition-check.py" <file>` |
| a glossary term used before its definition | `python3 "$WRITING_SCRIPTS/glossary-check.py"` |

**A check you run again and again belongs in a script or a style rule, not in a note.** If the
same kind of note keeps coming back, propose a check for the `write-text` skill instead of writing
the note again.

## Book-wide notes (`whole-book.md`)

- **Order by how much text the note changes, smallest first.** A cheap note that is already at a
  decision point goes early.
- **Sweeps that move paragraphs go late**, after the notes that change content stop moving
  paragraphs, or the sweep has to be done twice.
- **Sweeps over the rhythm of the whole book go last** (a sentence pattern repeated in many
  chapters), because every other fix changes the sentences they look at.
- **One owner per note.** If the author gives a note to another session, write that in the note
  so it is not picked up twice, and expect its text to change under you.
- **After each sweep, add a guard**: a style rule or a script check that fails when the pattern
  comes back. Write settled words back to the glossary.
- Record the order you agreed with the author in the notes file's free text at the top, and
  update it when notes close. It is working state, not a decision.
