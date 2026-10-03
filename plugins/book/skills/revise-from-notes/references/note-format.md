# Note format

## The notes file

One notes file per text file, in the folder `notes` from the book config. The notes file
has the same file name as the text file it is about: a manuscript file, a file in the thinking
folder (`thinking/argument/claims.md` -> `notes/claims.md`) or a sales-text file. Notes about the
whole book go in `whole-book.md`. Start a new file from `templates/notes-file.md`.

```markdown
# Notes: 120-chapter-2

Open notes only. How to work them: the revise-from-notes skill.

## 120-chapter-2 #1 A short title of the problem

...fields...

## 120-chapter-2 #2 Another short title

...fields...
```

Free text is allowed under the `#` title, before the first note. Every `##` heading after it must
be a note heading. The script's `check` (`scripts/open-notes.py`) reports any other `##` heading.

**What a notes file does not hold:** a status legend, a summary table of counts, a "Resolution"
field, or finished notes. A count is one
`list` of the script away, and a table that has to be kept up to date by hand goes wrong
quietly. A finished note is removed; its record is the
decision entry in `decisions.md`.

## The note id

`## <file-name-without-.md> #<n> <short title>`

- The file-name part must equal the notes file's own name (or `whole-book` in `whole-book.md`).
- `<n>` is unique in the file and is never used again, even after the note is removed, because
  the id lives on as an alias in `decisions.md`. Get a new id with the script's `next-id <file>`;
  it skips every number already used in the notes file or in a decision alias.
- When part of an open note is decided, its decision entry takes the note id as alias while the
  note stays open. `check` then shows `id-used-before` as advisory; that is expected.
- The short title names the problem, in plain words. No dash or colon between id and title;
  `check` reports one as `bad-heading`.
- To point at a finished note, cite its decision entry (`D-12`), not its old note id. `check`
  advises (`linked-note-missing`) on a `Linked` id that is no longer open.

## The fields

```markdown
## 120-chapter-2 #3 Short title

**From:** who wrote the note: `author`, or `<skill> <mode>, <YYYY-MM-DD HH:MM>`
**Tier:** Surface | Flow | Content   **Root cause:** a-g label(s)
**Paragraph:** where it is (section name), and why these paragraphs:

> The whole paragraph that holds the flagged text, copied word for word.
>
> The paragraph next to it, when the problem crosses the break.

**Text:** "the exact flagged sentence, copied from the paragraph above"
**Note:** the author's own words, never cleaned up
**Note (expanded):** the short note written out as the exact problem
**Idea:** the paragraph's one idea, and its topic / development / conclusion map
**Framing check:** does the text have the problem, and is the note's frame the book's frame?
**Analysis:** the rules, the chapter and the book's definitions, applied to the text
**Options:** pruned options, each in full context with its fit check
**Linked:** #4, #7 (why they are linked). Work them together.
```

## Rules for each field

- **Written when the note is created:** From, Tier, Root cause, Paragraph, Text, Note. An author may
  write only a heading, a Text quote and a Note. The script's `check` lists such notes as
  `not-analysed`; fill in the rest before showing the note.
- **Paragraph is a word-for-word quote, as a `>` block** (as the reader sees it: `*`, `_`,
  link addresses and footnote marks may be left out), one block paragraph per text
  paragraph, and it carries the neighbours: the sentence on each side, and the text across a
  heading when the note sits at a section break. Context travels with the note so it is never
  rebuilt later from one sentence. The script checks each quoted paragraph is still in the text;
  a long quote may leave out a middle part with `...`.
- **Text is in quotes**, copied from the paragraph. If there is no single flagged sentence (the
  note is about something missing), say so in plain words, without quotes.
- **From says where the note came from.** `author` for the author's own reading; for a review
  or a check, the skill, its mode and the run time, for example
  `review-text flow, <YYYY-MM-DD HH:MM>` or `check-facts all, <YYYY-MM-DD HH:MM>`. The run folder of that
  time holds the full report. `check` advises (`no-from`) on a note without From.
- **Note is the author's words exactly** (for a note from a skill, the finding as the review wrote it). Authors write short ("How long?", "Says who?").
  Write the exact problem in **Note (expanded)** before any analysis. Many wrong fixes come from
  guessing the intent.
- **Idea and Framing check** are required for Flow and Content notes. For a Surface note one
  line is enough: "idea of the paragraph not touched; a local word swap".
- **Linked** is added whenever notes share a paragraph, a frame, an idea or a root cause. Linked
  notes are fixed as one.
- **Point at text by quoting it**, not by line number. Line numbers move with every edit. If you
  use one as a quick pointer, give the section name with it.
- **Options** are shown as full sentences, never as "Option 2" alone, because option numbers in
  a file drift from the ones the author saw in chat.

## When the note is resolved

The exact applied text goes into the `Change` field of the decision entry, quoted, together with
which words carry a link to another chapter (so a later "reads better" edit does not delete
them). Then the note is removed. See SKILL.md, Step 4.
