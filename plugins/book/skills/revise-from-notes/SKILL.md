---
name: revise-from-notes
description: >-
  Answers the open notes on a book's text, one decision at a time: the author's own reading
  notes and the notes the reviews and checks write (review-text, review-ideas, check-facts, the
  cover and sales-text reviews). Each note is checked against the text as it is now, then
  answered with a few small, true fixes shown in full context; the chosen fix goes into the
  text, the decision into decisions.md, and the note is deleted. Three modes - one-by-one
  (default), all-at-once, right-now (a thought said in the chat). Use when the author says they
  have notes, reading notes, comments on a chapter, review findings to go through, or a list of
  problems pasted from a reading app, also for notes on the back cover or store copy. For new
  text or a rewrite with no notes, use write-text; to produce new findings, use review-text or
  review-ideas. Stance: the smallest true fix wins, and the author picks it.
---

# Revise from notes

Notes sit next to the text: the author's thoughts from reading the book, and the findings that
review-text, review-ideas, check-facts and the cover and sales-text reviews write. You work
through them with the author, one decision at a time. A note says what a reader or a reviewer
met. Your job is to find what the text really needs, offer a few correct fixes, and apply the
one the author picks.

## Where notes live

| What | Where |
|---|---|
| Notes folder | `notes` in the book config (`book.yaml`), usually `notes/` |
| One notes file per text file | same file name as the manuscript file: `manuscript/120-chapter-2.md` -> `notes/120-chapter-2.md` |
| Notes about the whole book | `notes/whole-book.md` |
| Notes on the sales texts | same rule, named after the file in `publishing.sales_text`: `notes/back-cover.md` |
| Notes on the thinking files | same rule, named after the file in `thinking/`: `notes/claims.md` |
| Note heading (its id) | `## <file-name-without-.md> #<n> <short title>`, e.g. `## 120-chapter-2 #3 Two ideas in one sentence` |

**Only open notes live in the folder.** A resolved note is not marked done. It is removed, after
its change is in the text and its decision is in `decisions.md`. There is no status field and no
summary table: `$NOTES list` counts notes when you need a count (`$NOTES` is set in "The script" below).

Find the real paths with the shared config reader, never by guessing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/book_config.py" paths
```

The note format, with every field and its rules, is in `references/note-format.md`. A new notes
file starts from `templates/notes-file.md`.

## Before any note

1. **Read only the decisions index** (`python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py index`)
   and open the entries a note touches (`decisions.py show ID`). Never raise again an item marked
   DECIDED. If a note repeats one, say so in one sentence, cite the entry, and ask whether the
   author wants to reopen it.
2. **Load the rules of the `write-text` skill, and open the `common-problems` and `flow` reviews
   of the `review-text` skill** (`${CLAUDE_PLUGIN_ROOT}/skills/review-text/references/`; the flow
   review holds topic-development-conclusion, the adjacency chain and the seam check). They are
   how you analyse every note, not background. Every Analysis names the rule it applies, by rule name.
   Without them you cannot tell whether a rule applies or whether a fix breaks another rule.
3. **Read the author's stance and voice files** (`thinking.stance`, `rules.voice` in the config).
   A correction about what the book believes never comes from the manuscript alone.
4. **Run `read-first` for the note.** It names the section, the related decisions, the citation
   keys and whether each has an entry in the quotes file, the argument files to choose from
   (`thinking.argument`) and the doubts files (`thinking.doubts`):

```bash
NOTES="${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/open-notes.py"
python3 "$NOTES" read-first "120-chapter-2 #3"
```

## Four lessons that shape everything here

1. **Check the framing before you write any option.** Very often the right fix is none of the
   first ideas, because all of them were versions of a wrong idea. The check comes first, not as a
   late "deeper analysis" that argues against your own options (`references/framing-check.md`).
2. **The paragraph is the unit, and the chapter is the limit.** A fix that reads well as one
   sentence can break the link to its neighbours, lose the paragraph's one idea, or start a word
   drifting elsewhere in the chapter. The defects most often missed are chapter-sized.
3. **Small, true edits win.** The smallest change that fixes the real cause is usually chosen.
   Sentences that only announce or repeat are deleted, not reworded. A claim the author cannot
   stand behind is cut, not softened. Every claim must survive a fact check.
4. **Correct options matter; ranking them matters little.** Show few options, each one correct,
   each in its full context. Record the exact text that was applied.

## Step 1: give the note a tier

The tier decides how deep you go and whether you open research. Decide it first. Full table,
root-cause labels and the method are in `references/analysis-method.md`.

| Tier | Covers | Research | Show the option as |
|---|---|---|---|
| **Surface** | one word, plain-English swap, punctuation, italics, typo, word order | no, but look for an earlier decision on the same word | the full sentence |
| **Flow** | unclear "this", repetition, weak link, one sentence with two ideas, order of sentences, announcements | only if a claim is part of the fix | the sentence and its neighbours, or the whole paragraph when sentences move |
| **Content** | claims, citations, cause and mechanism, the book's defined terms, contradictions with the book's own definitions | yes | the paragraph, plus what the change rests on |

When in doubt, move the note up a tier. A Surface or Flow note becomes Content when the fix
touches a term an earlier chapter defined or banned, a claim that needs its source, the author's
stance, something an earlier chapter must own first, or a term the same chapter introduces later.

**Do not research a Surface note.** Over-researching a one-word swap is as wrong as not
researching a claim.

**What to read, when research runs.** Everything comes from the config, never from a fixed list:
the `thinking.argument` folder (pick the file for the topic by its name; cite file and section),
the quotes file `sources.quotes` for each citation key the paragraph uses, the glossary
`rules.glossary`, and the coined terms in `book.yaml`. Look in these before the web.

## Step 2: work the note

Follow the order in `references/analysis-method.md`:

0. **Read the text as it is now.** The text may have changed since the note was written. If the
   problem is already gone, show the author the current paragraph and the note, and on the
   author's yes delete the note (record a decision only when one was discussed). A note from a
   skill says where it came from in `From`; its run folder holds the full report.
1. Expand a short note ("Six?", "why?") into the exact problem. Never guess the intent silently.
2. Write the paragraph's one idea and its topic, development and conclusion.
3. **Framing check** (`references/framing-check.md`): does the text really have the problem? Is
   the note's frame the book's frame? Does the claim match the book's own definitions? Is every
   claim true?
4. Name the root cause, not what the reader felt (labels a to g).
5. Run the matching review from the `review-text` skill.
6. Research, only if the tier says so.
7. Build options (`references/options.md`): pruned, full sentences, bold on the change only,
   minimal edit and deletion offered as real options, a seven-point fit check on each.
8. Run the chapter checks (`references/chapter-checks.md`).

## Step 3: show the note

Show **one note per turn**, and wait for the author's decision before the next. Notes that share
a paragraph, a frame or a root cause are shown together, as one fix, because fixing them one by
one edits the same paragraph twice. When several sentence-level notes share a paragraph, move up
to one review of the section instead of edits one by one. After a group is applied, check each
note of the group against the final paragraph before you remove it.

Show six things, in this order:

1. the full paragraph, as it is now
2. the flagged sentence
3. the author's note, word for word
4. the paragraph's one idea
5. the analysis, with the framing check first
6. the options, each in context with its fit check

## Step 4: resolve the note

**Draft, show, then apply.** Never write into the manuscript before the author picks a fix.

1. Apply the chosen text to the manuscript. If the author changes the wording, apply their words.
2. Read the sentence before and after the edit (across a heading too). Run the chapter checks
   (`references/chapter-checks.md`) on the result, then the text checks on the file:
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/run-checks/scripts/run-checks.py text <file>`.
3. If the same text appears in another place (a summary, the back cover, the preface), keep every
   copy in step, or ask.
4. **Write back** any word decision to the book's term files (glossary, coined terms), so the
   next chapter gets it (`references/chapter-checks.md`).
5. **Record the decision** when the note was discussed (options were shown, or something was
   declined). A plain typo fix needs no entry. Dry run first, then `--fix`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/decisions.py" add \
  --title "Short title of the idea" --status "DECIDED / changed" \
  --alias "120-chapter-2 #3" --idea "what the note said the problem was" \
  --decision "what was decided" --change "the exact text applied, quoted" \
  --why "why, and every option that was rejected and why" \
  --refs "manuscript/120-chapter-2.md" --keywords "words, that, help matching"
```

   Use `DECIDED / no change` when the author declines, and `DECIDED / not a finding` when the
   framing check shows the text never had the problem. When the note's `From:` line names a
   skill and a mode (for example `review-text hard-words`), put the mode name in `--keywords`:
   a later run of that mode finds its earlier answers with `decisions.py match`. If the author wants to think about it
   later, the note stays open and nothing is recorded. When only part of a note is decided,
   record that part (alias: the note id) and keep the rest of the note open.
6. **Remove the note** from its notes file. Remove the file when it has no notes left.

Rewrite, do not patch on a patch: if a paragraph needs a third fix, offer one clean rewrite of
the paragraph instead.

**Fixes owed that have landed.** An entry with the status `OPEN / fix owed` waits for a change in
the text. When a note or a review names such an entry as done, show the entry
(`decisions.py show ID`) and the text that now carries the fix. On the author's yes, close it,
dry run first:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/lib/decisions.py" set-status ID "DECIDED / changed" --fix
```

## Modes

| Mode | What it does |
|---|---|
| `one-by-one` (default) | takes the next open note from the notes files, one note per turn |
| `all-at-once` | reads a batch of notes, plans them as groups, then resolves them one by one |
| `right-now` | handles a thought the author says in the chat, without writing a note |

**one-by-one** (default). Notes already sit in the notes files. Run `$NOTES list`, take the
first open note (or the one the author names), read the text again (Step 2, item 0), fill in any missing fields (Tier, Root cause,
Paragraph, Idea, Framing check), and show it. One note per turn.

**all-at-once.** The author hands over a batch (written in the files, or pasted from a reading
app). First read the whole section the notes cover. Then, for every note: tier, paragraph with
neighbours, idea, framing check, analysis, pruned options, and links to other notes. Write all of
it into the notes files (ids from `$NOTES next-id <file>`). Then show a short plan: groups
of linked notes, single notes, and the order you suggest. After that, resolve them exactly as in
one-by-one, one note or one group per turn.

**right-now.** The author says a thought in the chat and wants it handled now. Same method, same
tiers, same one-at-a-time rule, same draft-show-apply. Nothing goes into the notes folder, but a
discussed decision still goes into `decisions.md`. If the author says "think about it later",
write it as a note in the notes folder so it is not lost.

## Book-wide notes

Notes in `whole-book.md` touch many files. Order them by how much text they change, smallest
first. Sweeps that move paragraphs, and sweeps over the rhythm of the whole book, go last.
After each sweep, add a check (a style rule or a script) so the problem cannot come back.
Details in `references/chapter-checks.md`.

## Sales texts

Notes on the back cover or store copy work the same way, with two changes: the `prepare-sales-text`
skill's rules decide which writing rules hold for copy, and every copy of the same text (back cover,
store description, ebook description) must stay in step.

## The script

```bash
NOTES="${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/open-notes.py"
python3 "$NOTES" list
```

It reads the config itself (`--config` to point at another `book.yaml`).

| Command | What it does |
|---|---|
| `list [--file NAME] [--format json]` | open notes per notes file |
| `check [--format text\|tsv\|json]` | every heading names a real manuscript, thinking or sales-text file; every quoted paragraph is still in the text word for word; no id repeats or reuses an id already in `decisions.md`; no resolved note was left behind; advises on a `Linked` id that is no longer open and on old field names |
| `next-id NAME` | the next free id for a file, skipping numbers already used in `decisions.md` |
| `read-first NOTE-ID` (a title after the id is ignored) | section, related decisions, citation keys, argument files, doubts files and author files for one note |

`check` follows the shared contract: exit 0 clean, 1 defects, 2 the tool failed. A
`paragraph-changed` defect means the author edited the text after writing the note: read the
new text and update the note's Paragraph before working on it. With no notes folder, `check`
prints `SKIPPED` and says where it looked; that is not a clean result. The run-checks skill runs
`check` with the other text checks (`run-checks.py text`).

`python3 "${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/self-check.py"` runs this skill's own
tests against its fixture book only.

## References

- `references/note-format.md`: the notes file, the note fields, and the rules for each field
- `references/analysis-method.md`: tiers, research triggers, root-cause labels, the five steps
- `references/framing-check.md`: how to test the note's own idea before writing options
- `references/options.md`: how to build and show options, and the seven-point fit check
- `references/chapter-checks.md`: chapter and book checks, term files and write-back, book-wide order
- `templates/notes-file.md`: a new notes file with one empty note
