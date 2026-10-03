# CLAUDE.md

This folder holds the paper *{{title}}* by {{author}}: its text, the evidence behind it, and the
settings the book plugin's skills read. `book.yaml` says `kind: paper`, so the skills treat the
manuscript as a research paper: each manuscript file is one numbered section, and the build
makes a PDF and, when asked, the source bundle for arXiv. A paper has no cover and no sales text.

## What the paper is

Write two or three sentences here: the question the paper answers, who it is for (the field and
the venue), and what a reader can do after reading it. Every skill reads this section to learn
the paper's aim.

## Where things live

This table describes the folders of the paper. Other folders here (code, data, scripts of the
study) are not part of the paper, and the skills do not read them.

| Path | Holds |
|---|---|
| `book.yaml` | The one config: metadata, the `paper:` settings, coined terms, and any path that is not the default |
| `manuscript/` | The paper, one `NNN-name.md` file per section; the number prefix is the order; `manuscript/010-abstract.md` is the abstract, `manuscript/900-references.md` the references; `images/` inside |
| `thinking/author/` | `thinking/author/stance.md` and `thinking/author/stance-details.md` (the author's positions), `thinking/author/audience.md` (who the paper is for and what it must show) |
| `thinking/argument/` | Why the paper says what it says: the main claims and one file per topic, named by what it holds |
| `thinking/doubts/` | Counterarguments and open questions |
| `rules/decisions.md` | Settled and open decisions: a generated `## Index`, then `## Details` |
| `rules/glossary.md` | The terms the paper defines, with their canonical wording |
| `rules/voice.md` | The voice of the paper |
| `rules/vale/` | `vale.ini`, the paper's own Vale rules, and `config/vocabularies/Book/` (accepted and rejected spellings) |
| `sources/` | `sources/list.md` (who wrote what, where to get it), `sources/quotes.md` (what each source says), `sources/library-index/` (one record per library file); `sources/library/` holds the copies and is kept out of git |
| `notes/` | Open notes only, one file per manuscript file, plus `whole-book.md` for notes on the whole paper |
| `.book/` | Work state, kept out of git: `runs/` (one folder per run, newest three per skill and mode), `output/` (the built paper), `caches/`, `sources-to-add/` |
| `.claude/` | `settings.json`: the tools Claude Code may use without asking |

## Which skill to use

Start a skill of the book plugin with `/book:<skill>`.

| Skill | Does |
|---|---|
| `/book:init` | Sets up a new book or paper, or adds what a folder lacks |
| `/book:write-text` | Writes and rewrites prose in `manuscript/` and `thinking/`: plan, draft, show, apply |
| `/book:review-text` | Reviews the prose of one section or of the whole paper; findings become notes |
| `/book:review-ideas` | Reviews the argument, structure and evidence (`editor`, or a cold `readers` review); findings become notes |
| `/book:check-facts` | Checks claims, quotes and numbers against the library copies; findings become notes |
| `/book:revise-from-notes` | Works through the open notes in `notes/`, one fix at a time, and records each decision |
| `/book:collect-sources` | Finds, downloads, backs up and restores the source library |
| `/book:build-editions` | Builds the paper PDF, and the arXiv source bundle when asked |
| `/book:run-checks` | Runs every script check of the plugin; the cover and sales-text checks say SKIPPED for a paper |

`/book:design-cover` and `/book:prepare-sales-text` are for books only.

## Working rules

- **Do not commit or push unless the author asks.** When a change cannot be undone, say so and
  copy the file before editing.
- **Draft, show, then apply.** Show the full proposed text first; edit files only after the
  author approves, and apply the approved words exactly.
- **A minimal change stays minimal**, and a passage patched twice is rewritten from its idea.
- **Truth over punch.** Every claim must survive a fact-check, and every number must match the
  data of the study.
- **Keep copies in sync.** When the same text lives in two places, change both.
- **Read only the decisions index first** (`## Index` in `rules/decisions.md`), then open the
  one entry you need under `## Details`. Never raise or re-propose an item marked DECIDED.
  `/book:run-checks setup` says when the index is out of date, and `setup --fix` rebuilds it.
- **`book.yaml` is data.** Check it after every edit with `/book:run-checks setup`.
