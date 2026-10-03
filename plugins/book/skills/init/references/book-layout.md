# The book layout

One layout for every book, so every skill finds every file without being told. Each path is a
`book.yaml` key ([book-yaml.md](book-yaml.md)); a book that wants another name sets the key, and
every script follows it.

## Naming rules

- **Name a thing by what it holds or does**, in plain English a non-native reader understands on
  first sight: `sources/quotes.md`, not the name of the tool that writes it or the person who
  started it.
- **Every item in a folder matches the folder's name.** A folder called `sources` holds sources
  and nothing else; a file that fits no folder is a sign that a folder is missing, not a reason
  to put it somewhere near.
- **Dated files are work state.** A file with a date in its name is a verdict about the book as
  it was on that day. It lives in a run folder, `.book/runs/<YYYY-MM-DD-HHMM>-<skill>-<mode>/`,
  never beside the banks or the evidence, and what lasts from it moves into a bank or
  `rules/decisions.md`. Only the newest three runs of each skill and mode are kept
  (`${CLAUDE_PLUGIN_ROOT}/lib/run_folders.py`).

## The folders

| Path | Key | Holds | In git |
|---|---|---|---|
| `book.yaml` | - | Metadata, coined terms, any path that is not the default | yes |
| `CLAUDE.md` | - | What the book is, where things live, which skill to use, the working rules | yes |
| `manuscript/` | `manuscript.dir` | `NNN-name.md` files; the number prefix is the book order; `images/` inside | yes |
| `thinking/author/` | `thinking.stance`, `thinking.stance_details`, `thinking.audience` | `thinking/author/stance.md`, `thinking/author/stance-details.md`, `thinking/author/audience.md` | yes |
| `thinking/argument/` | `thinking.argument` | Why the book says what it says: `thinking/argument/claims.md` and one file per topic; `new.py` writes a starter `thinking/argument/claims.md` | yes |
| `thinking/doubts/` | `thinking.doubts` | `thinking/doubts/counterarguments.md`, `thinking/doubts/open-questions.md`; `new.py` writes both as starters | yes |
| `rules/decisions.md` | `rules.decisions` | Settled and open decisions: a generated `## Index`, then `## Details` (format: `${CLAUDE_PLUGIN_ROOT}/lib/decisions-format.md`) | yes |
| `rules/glossary.md` | `rules.glossary` | The terms the book defines, with their canonical wording | yes |
| `rules/voice.md` | `rules.voice` | The author's voice profile; `new.py` copies the write-text skill's default profile | yes |
| `rules/vale/` | `rules.vale`, `rules.vale_ini` | `vale.ini`, the book's own Vale rules, `config/vocabularies/Book/` word lists | yes |
| `sources/list.md` | `sources.list` | Who wrote what and where to get it; the one place a key resolves. A new list holds only its `## Entry format` header, so every facts check says SKIPPED until it has an entry or a file cites a `[Key]` | yes |
| `sources/quotes.md` | `sources.quotes` | What each source says: quotes, scope, guardrails | yes |
| `sources/library-index/` | `sources.library_index` | `<Key>.json`: how each library file was fetched and read | yes |
| `sources/library/` | `sources.library` | The copies of the sources; the collect-sources skill restores them | no |
| `publishing/cover/` | `publishing.cover`, `cover.*` | `design.py` (the artwork; `new.py` writes the smallest design), `font-widths/` and `final/` (what ships) | yes |
| `publishing/sales-text/` | `publishing.sales_text`, `sales_text.*` | `publishing/sales-text/back-cover.md` (the single source of that text), store texts, keywords; `new.py` writes the prepare-sales-text skill's starters | yes |
| `notes/` | `notes` | Open notes only, one file per manuscript file plus `whole-book.md` | yes |
| `.book/` | `work.*`, `sources.to_add` | `runs/`, `output/`, `caches/`, `sources-to-add/`: work state | no |

What stays out of git, and why (`templates/gitignore` is what `new.py` writes, filled with the
paths the book's `book.yaml` sets; a path outside the book folder gets no line):

- `sources/library/`: third-party files, often large, some under copyright. The collect-sources skill
  downloads them again (`restore`) and keeps the ones that cannot be downloaded again in a
  private backup (`sources.backup`).
- `.book/`: run reports, entries a run proposes, build output, caches and the files the author
  downloads by hand (`sources-to-add/`) all expire or can be made again.
- The Vale packages that `vale sync` downloads, and the write-text skill's base style copied into
  `rules/vale/` by `vale-sync.py`: both come back with one command. A new book has neither until
  `vale-sync.py --fix` runs once, so its Vale review says SKIPPED until then.

## The manuscript

The build reads the manuscript in natural order, so the prefix is the table of contents. Parts
sit at `X00`, chapters at `X10` steps, which leaves room to insert a file later; `000`-`099` is
front matter and `900`-`999` back matter. `new.py` writes a copyright page, a preface, one part,
one chapter and the references file, each in the shape the build and the writing checks accept.
The full convention, including raw LaTeX blocks and a manual contents page, is in
`${CLAUDE_PLUGIN_ROOT}/skills/build-editions/references/manuscript-layout.md`.

## No README or index files

A book holds no README or index file in any folder. A file that lists the files of a folder
falls behind as soon as a file is added without it. The book's `CLAUDE.md` describes the folders
in its "Where things live" table, and each file is named by what it holds, so a listing of the
folder is the index.

## Permissions for Claude Code

`new.py` writes `.claude/settings.json` with tools that need no approval: Glob, Grep, `wc` and
`ls`, which only look, and `mkdir`, which only makes folders. Claude Code already reads files
inside the book folder without asking, so the file does not allow Read or `cat`: a rule for them
would also open every other file on the machine, and a downloaded source could carry text that
asks for one. Anything else that writes still asks.
