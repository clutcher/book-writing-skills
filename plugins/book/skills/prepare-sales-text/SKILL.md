---
name: prepare-sales-text
description: >-
  Writes, reviews and keeps in step the words that sell a book: the back cover, the Amazon store
  description, the ebook description and the plain-text copy for other stores. Also chooses
  store keywords, categories and subject codes, and exports store files. Use it when the author
  asks to write, improve, review or score back-cover or store copy or a blurb, to choose or
  check keywords or categories, or to export a description. For the cover image use
  design-cover; for the book prose use write-text.
argument-hint: "[write|review|pick-keywords|export]"
---

# Prepare sales text

The words that sell a book are a different kind of text from the book. A chapter is read by
someone who has bought it and reads in order. A back cover or a store page is read by a stranger,
in seconds, out of order, before buying. This skill writes and checks that text, and chooses the
store data around it (keywords, categories, subject codes).

## Modes

| Mode | What it does |
|---|---|
| `write` (default) | drafts or rewrites the back cover, the store description or the ebook description, and keeps every surface in step (`sync-check.py`) |
| `review` | three kinds of review: the ten-lens copy review, the impression review, a comparison between versions; findings become notes |
| `pick-keywords` | chooses and checks store keywords and categories |
| `export` | generates the plain-text store description and the contents pages for other stores |

With no mode given, use `write` when the request asks for text; otherwise pick the one the
request names ("score the blurb" is `review`, "plain-text description" is `export`), or ask.

## Working rules

They are not optional.

1. **Draft, show, then apply.** Show the full new text, with the changed words in bold
   (`copy-diff.py --markdown`), say what changed and why, and wait for the author to approve.
   Only then edit a file. "Update" in a request means the step after approval. Apply the
   approved wording exactly; if you see a flaw while applying, ask.
2. **Decided items are not findings.** Read only the decisions index first, every time
   (`python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py index`), and open the entries you need
   (`decisions.py show ID`). Run `python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py match --text-file F` on every
   finding and every proposal. A DECIDED item is not raised again;
   to disagree, cite the entry in one sentence and stop. Never re-propose a rejected option.
3. **Truth over punch.** Every claim on a selling surface must survive a fact-check against the
   book. Write copy only from claims the book states and the book's fact-check has passed. No
   invented numbers; write "not verified" instead of an estimate.
4. **Rewrite, do not patch a patch.** When a span has been patched twice, write it again from its
   job. **A minimal change stays minimal:** when asked for one change, change one thing.
5. **All surfaces stay in step.** After any change to one surface, run the step check ("Keeping the surfaces in step" below).
6. **Cold reviewers.** In `review`, one subagent per lens, each with the surfaces and the
   references but no edit history and no other lens's findings.
7. **Plain A2 English, even on the cover**, except where `references/rules-transfer.md` says a
   rule turns around.
8. **Marketing advice needs evidence with a grade.** Quote only what
   `references/marketing-evidence.md` or `references/emphasis-evidence.md` grades, or say it is
   judgement. Never cite conversion evidence to justify copy.
9. **Measure; never quote a figure from memory or from old notes.** Word counts, character
   counts and bold spans come from the scripts in this session.

## What the skill reads from the book

All paths come from `book.yaml` (found by walking up from the working folder; `--config FILE`
overrides, `--set KEY=VALUE` overrides one value). Paths are relative to the book root.

| Key | Default | What it is |
|---|---|---|
| `sales_text.back_cover` | `<publishing.sales_text>/back-cover.md` | the back cover, the single source (the cover design reads it) |
| `sales_text.amazon` | `<publishing.sales_text>/amazon.html` | the Amazon store description |
| `sales_text.keywords` | `<publishing.sales_text>/keywords-and-categories.md` | keywords, categories, subjects, category evidence |
| `sales_text.intended_impression` | `<publishing.sales_text>/intended-impression.md` | what the surfaces must signal |
| `sales_text.plain_description` | `<publishing.sales_text>/plain-description.txt` | generated plain-text description |
| `sales_text.contents`, `sales_text.contents_full` | `<publishing.sales_text>/contents.html`, `contents-full.html` | generated tables of contents |
| `sales_text.preface` | first front-matter file named `*preface*` | its opening paragraph is checked against the copy |
| `sales_text.retired_phrases` | none | wordings decided never to return (checked by `sync-check.py`) |
| `sales_text.shared_spans` | none | wordings that must stay identical on every selling surface |
| `sales_text.contents_skip` | none | file-name patterns left out of the exported table of contents |
| `sales_text.amazon_limit`, `keyword_slots`, `keyword_chars`, `categories_per_format` | 4000, 7, 50, 3 | store limits, so a store change needs no code change |
| `sales_text.sample_print_share`, `sample_ebook_share` | 0.2, 0.1 | the share of the book the free sample shows |
| `book.description` | none | the one-line ebook description (a selling surface) |

Also read: the decisions index (`rules.decisions`), the audience (`thinking.audience`), the
voice (`rules.voice`), the glossary (`rules.glossary`), and the manuscript
(`manuscript.dir`) for anything the copy claims. Missing book files: start from `templates/`.

**Find the real paths first.** File names in this skill (`decisions.md`, `amazon.html`,
`intended-impression.md` ...) are only the default names; a book can keep its files anywhere.
Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/prepare-sales-text/scripts/sales-text-files.py`: it prints every
key above with the real path in this book and whether the file exists. Use those paths, and
give them to every subagent. A missing file is said out loud, never skipped in silence.

Scripts live in `${CLAUDE_PLUGIN_ROOT}/skills/prepare-sales-text/scripts/`; every one has `--help`. Run
them as `python3 ${CLAUDE_PLUGIN_ROOT}/skills/prepare-sales-text/scripts/copy-stats.py --text`; this file
gives the script name only. `decisions.py` is in the shared lib:
`python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py`.
Checks follow the plugin's check contract: exit 0 clean, 1 defects, 2 the tool failed.

## Mode: write

For the back cover, the store description or the ebook description.

1. Read the decisions index (`decisions.py index`, then `decisions.py show ID`), the intended
   impression (`sales_text.intended_impression`), the audience file (`thinking.audience`), and
   the current surfaces (`copy-stats.py --text`). Read the category evidence
   in the keywords file (`sales_text.keywords`).
2. Read the part of the manuscript each claim comes from. Note where the book proves every
   claim (file and section). A claim with no home in the book does not go on the page.
3. Choose the job of each surface (`references/listing.md`): the back cover is read by someone
   holding the book; the store description by a stranger comparing books; the ebook description
   is one condensed line. They share the thesis, not the wording, and they must not contradict.
4. Draft. Apply `references/copy-review.md` cover rules C1-C3 and the split test while
   drafting, and `references/rules-transfer.md` for which writing rules hold. Put the pitch in
   the first two sentences. Make the bold spans full sentences that read as the pitch alone.
5. Measure the draft (`copy-stats.py DRAFT`) and check it (`store-description-check.py` for
   the store HTML). Store limits: `references/store-limits.md`.
6. Show the author the full text and the word-level diff against the current version. Offer at
   most two alternatives for any span that carries a real choice, as full sentences in context.
7. After approval, write the file, then keep the surfaces in step and run `export`. Propose entries for the
   decisions file (`decisions.py add`, dry run) for every option the author rejected with a reason.

Back cover format: `templates/back-cover.md`; the markdown it may use is set by the `design-cover`
skill (`${CLAUDE_PLUGIN_ROOT}/skills/design-cover/references/design-file.md`, "The back-cover text"), because the cover design reads the
file. Store HTML: `templates/amazon.html`.

## Mode: review

Three kinds of review; run the one asked for, or all three in this order.

**Copy review (the ten lenses).** `references/copy-review.md`.

1. Measure: `copy-stats.py --text` and `sync-check.py`. Their output is the only copy the
   reviewers see.
2. Run the split test first (does a block split into two halves that each make sense alone?),
   then the ten lenses: Stranger, Skeptic, Connector, Buyer,
   Marketer, Psychologist, Editor, Consistency Auditor, Non-Native Reader, Typographer of Text.
   One cold subagent per lens with `references/review-prompt.md`.
3. Match every finding against the decisions (`decisions.py match "<finding>"`); merge
   duplicates; drop what is decided.
4. Report in the format of `copy-review.md`: ranked findings, full-sentence suggestions, the
   three with the most impact, which are defects and which are author decisions, and a **score
   out of 10 per surface with the reason**.

**Impression review.** `references/impression-review.md`. Six questions (book, author, ideas,
authority, seriousness, category), answered from the surfaces alone, in buyer order: thumbnail,
front cover, store description, back cover, all together. Compare with
`intended-impression.md`; a gap in either direction is a finding. End with the one sentence a
stranger would use to describe the book. Run it after a copy review, and always after a
credential or a claim was added or removed.

**Comparison between versions.** `references/version-comparison.md`. For choosing between
drafts: a measured table of versions, each in full, their scan paths, word-level diffs
(`copy-diff.py`), what separates them, why each exists, what was considered and not taken, and a
score out of 10 per version. The working file goes to the review's run folder, never to the
sales-text folder (`publishing.sales_text`).

**The run folder.** Every review starts with
`python3 ${CLAUDE_PLUGIN_ROOT}/lib/run_folders.py start prepare-sales-text review --fix`, which
makes `<work.runs>/<YYYY-MM-DD-HHMM>-prepare-sales-text-review/` and keeps the newest three
review runs; the report and the lens files go there. `--resume` continues the newest review that
stopped (`run_folders.py latest prepare-sales-text review`), skipping lenses already written.
`--only-changed` reviews only the surfaces changed since the last review
(`run_folders.py changed prepare-sales-text review <surface files>`); a review ends with
`run_folders.py record <run folder> <surface files> --fix`.

**Findings become notes.** The report stays in the run folder. Every finding of a copy review
or an impression review that needs the author becomes one note. It goes in the notes file named
after its surface (the back cover, the store description, ...); a finding about all surfaces goes
to `whole-book.md`. Each note is in the format of `${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/references/note-format.md`, with
`**From:** prepare-sales-text review, <YYYY-MM-DD HH:MM>`. Get ids with
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/revise-from-notes/scripts/open-notes.py next-id <file>`.

Reviews propose; the author decides, with revise-from-notes. Apply nothing without approval.

## Mode: pick-keywords

`references/pick-keywords.md` and `references/store-limits.md`.

1. Read the decisions index (`decisions.py index`) and the keywords file (`sales_text.keywords`; template in `templates/`).
2. Keyword candidates come from what the title and subtitle do not say. Test each with
   `search-suggestions.py --online WORD ...` and record the answer with the date line it prints.
   It calls an unofficial Amazon endpoint; you run it at your own discretion. Without `--online`
   it prints the manual way: type each word into the Amazon search box, Books department, and
   note the suggestions with the date. Count each candidate in the manuscript; the interior is
   indexed, so agreement compounds.
3. Store rules: 7 slots, about 50 characters each (observed, not documented), no title,
   subtitle or category words, no other authors or their books (prohibited, zero tolerance), no
   quotes, no subjective or time-sensitive words. Read both KDP pages.
4. Categories: 3 per format, from the live browse tree with node ids, **confirmed in the live
   signed-in KDP picker before publishing, never taken from memory or from an agent's list.**
   Split formats deliberately.
5. BISAC or other subject codes for Google Books and others, from the current list.
6. Run `keyword-check.py`. Record chars used and new index words; record a replaced set with its
   numbers. Anything not verified is written "not verified".
7. Show the tables to the author; after approval write the file and propose decisions-file
   entries for judgement calls.

## Keeping the surfaces in step

Part of `write`, and of `review` when asked. The back cover, the store description, the ebook description and the preface opening must not
contradict each other. They are not copies.

1. Run `sync-check.py`. It reports retired wordings that came back (defect), shared wordings that
   changed, one quantity in two wordings, long word runs the preface opening repeats from a
   selling surface (rule C3), each surface's opening sentence and its bold scan path.
2. Run `copy-stats.py --text` and read all four texts side by side. Check by reading:
   - no surface claims what another denies, or states more strongly than the book does;
   - one noun for what the book delivers, one wording per quantity, lists in the book's order;
   - title, subtitle and author exactly as in the book config;
   - the preface's first paragraph moves forward from the copy instead of restarting it.
3. Report each disagreement with both texts quoted, and say which surface should move. A
   deliberate difference recorded in the decisions file (`decisions.py match`) is not a finding.
4. After approved changes, run `export` so the generated files follow.

## Mode: export

Generated files are never edited by hand.

- `plain-description.py --fix`: the plain-text store description for Google Books and other
  stores that take no markup, from the Amazon HTML.
- `table-of-contents.py --fix` and `table-of-contents.py --depth sections --fix`: an HTML
  table of contents for a landing page or a store page, from the manuscript headings (parts,
  chapters, sections; unnumbered sections such as a Summary stay unnumbered).

Without `--fix` both print to the screen, for a look first.

## Scripts

| Script | Mode | What it does |
|---|---|---|
| `sales-text-files.py` | all | the real path of every book file the skill reads or writes, and whether it exists |
| `copy-stats.py` | all | words, characters, blocks, longest block, bold scan path per surface; `--text` prints the texts; `--sample` shows how far the free sample reaches |
| `copy-diff.py OLD NEW` | write, review | word-level diff of two versions; `--markdown` bolds the changes |
| `store-description-check.py` | write, review | store limit incl. tags, allowed tags, prohibited content |
| `keyword-check.py` | pick-keywords | slots and categories against the store rules; chars used, new index words |
| `search-suggestions.py --online WORD...` | pick-keywords | what the Amazon search box suggests (network, only with --online) |
| `sync-check.py` | write | the mechanical part of cross-surface agreement |
| `plain-description.py` | export | plain-text description |
| `table-of-contents.py` | export | table of contents from the manuscript headings |
| `self-check.py` | - | runs every script on the fixture book in `tests/`; no real book, no network |

## References

| File | Holds |
|---|---|
| `references/copy-review.md` | the ten lenses, the split test (its heading there: "the decomposition test"), cover rules C1-C3, output format |
| `references/rules-transfer.md` | which writing rules apply harder, are suspended, or turn around on a cover |
| `references/impression-review.md` | the six-question impression review |
| `references/version-comparison.md` | comparing versions and choosing one |
| `references/review-prompt.md` | the prompt for each cold lens subagent |
| `references/listing.md` | surface map, buyer profile, reading the category, store description rules |
| `references/store-limits.md` | store limits and rules with sources; common beliefs with no Amazon source |
| `references/pick-keywords.md` | the keywords and categories method |
| `references/title-and-discoverability.md` | choosing a title and subtitle; discoverability |
| `references/marketing-evidence.md` | graded evidence on copy, purchase, reviews, persuasion, conversion tests |
| `references/emphasis-evidence.md` | graded evidence on bold, italic, capitals and colour |
| `references/launch-checklist.md` | packaging questions before and after launch |
| `templates/` | back cover, store HTML, keywords-and-categories, intended impression |

Run output (reviews, version comparisons) goes to the review's run folder
(`<work.runs>/<YYYY-MM-DD-HHMM>-prepare-sales-text-review/`), never into the sales-text folder and
never into this skill.
