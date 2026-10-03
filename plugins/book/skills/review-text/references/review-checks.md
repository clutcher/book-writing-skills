# Book conventions a review can check

Conventions some books adopt, with the check that keeps each one honest. When a book adopts one,
its decision is in the decisions file (revise-from-notes records it when the author answers a
note); a review then checks it without arguing it again.

## Definition blockquotes, three kinds

Some books set formal definitions apart as blockquotes:

- **Labelled:** `> **The rule of X:** ...` with a bold label. Reserve it for the few
  foundational ideas of the book, so the form itself signals weight.
- **Bare:** `> A statement ...` with no label, for other principles and thesis
  statements.
- **Definition of a term:** `> **A term** is ...`, the defined term in bold at the start.

`definition-check.py` checks that every bolded single-line blockquote names a glossary term; a
bare blockquote is never flagged and never gets bold added. `--propose` lists blockquotes and
suggests which span to bold when bringing new material into the convention.

## Short supporting paragraphs

A Part divider overview is an advance organizer and works by staying short (two to four
sentences); a bibliography and an acknowledgments page are not argued prose. None of them is
held to the paragraph range of the voice profile. The check exempts them by file shape and by the
book's references path; `writing.paragraph_length_exempt` in book.yaml replaces the list, never a
hardcoded file name.

## Hidden questions

A sentence may be turned into a question only when the question and its answer are adjacent
sentences (`${CLAUDE_PLUGIN_ROOT}/skills/write-text/references/style-lessons.md`). A candidate
the author rejects is recorded by revise-from-notes when the note is answered, so it is not
proposed again; a review only writes the note.

## Ordering book-wide sweeps

- Order book-wide changes by the size of what they touch, smallest first.
- Sweeps that move paragraphs, and whole-book rhythm sweeps (fronted inversions, cadence), run
  last: they change the text every other sweep points at.
- After each book-wide sweep, add a guard (a Vale rule, a script list, a glossary usage entry)
  so the same drift is caught next time, and write settled terms back to the glossary.
