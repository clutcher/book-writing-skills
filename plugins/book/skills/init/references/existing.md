# existing: moving an existing book into the layout

`existing.py` moves a book that grew its own layout into the one every skill expects
([book-layout.md](book-layout.md)). It knows two older layouts:

- **old**: no `book.yaml`; the settings live in `CLAUDE.md` (`## Book Metadata`,
  `## Coined Terminology`), with `review/`, `research/`, `personal-review/`, my-stance.md,
  book-positioning.md, `.vale/`, and fetch and OCR records beside each file in
  `review/sources/`.
- **previous**: a `book.yaml` beside `author/`, `reasons/`, `vocabulary/`, `style/`,
  `sources/files/`, `sources/origin/`, `cover/`, `marketing/`, `reading-notes/`,
  `decisions.md` and `.book/inbox/`, using the old key names (`reasons`, `author.*`,
  `marketing.*`, `sources.files`, ...).

It is built around one promise: **moving never changes a byte of the book.** Everything that does change a file (book.yaml, two kinds of path line, the
`.gitignore`) happens after the moves, as its own named step, and the report lists each one.

## Before you start

1. **Make a backup of the whole folder** (a zip next to it) and say where it is. `existing.py`
   deletes what the plan marks DROP, and a deletion cannot be undone from inside the book.
   `--keep-dropped DIR` moves dropped files to DIR instead, and refuses a file DIR already has.
2. **Save the checks from before the move.** Run the run-checks skill (`run-checks.py facts` and
   `run-checks.py text`) and keep their output: after the move they must report the same
   findings, and without this run there is nothing to compare with.
3. **Clean the source banks first.** Run the check-facts skill's `entry-format-fix.py` (dry run) on
   the old layout. If it reports changes, settle them before the move: the move rewrites bank lines
   only when path lines are all the fixer would change, so a bank with other pending fixes keeps
   its old paths until you run the fixer yourself.
4. **`existing.py move` never runs git and never commits**; the author commits the result.

## The steps

```bash
S=${CLAUDE_PLUGIN_ROOT}/skills/init/scripts
python3 $S/existing.py draft BOOK            # show the drafted plan
python3 $S/existing.py draft BOOK --fix      # write BOOK/move-plan.tsv; the author edits it
python3 $S/existing.py move BOOK             # dry run: what moves, merges, drops; the book.yaml
python3 $S/existing.py move BOOK --fix       # move, check, write the report
python3 $S/new.py BOOK --fix              # add what the layout still lacks; changes nothing that exists
```

Show the drafted plan to the author and wait. Every row is a decision about where a file lives,
and the author knows things the rules cannot: a folder that is really two things, a file that is
already dead.

## The move plan

A TSV file, one row per path: `old path <TAB> new path or DROP <TAB> note`. Lines starting with
`#` are comments.

- A row ending in `/` moves a whole folder, both sides ending in `/`.
- **The most specific row wins.** `review/sources/ -> sources/library/` and
  `review/sources/incoming/ -> .book/sources-to-add/` together send the files added by hand to
  `sources-to-add/` and the rest to the library.
- A row whose new path equals its old path keeps the path where it is. The draft lists every
  path no rule moves this way, so the plan shows the whole book.
- `DROP` removes the path. The draft proposes it only for what comes back by itself: Python
  bytecode, and Vale packages that `vale sync` downloads again. A file another row moves into a
  DROP folder (for example `cover/png/a.png -> publishing/cover/final/a.png` under `cover/ DROP`) is kept:
  the rest of that folder is dropped file by file. A DROP folder that cannot be read (often one
  owned by root) is a plan problem, named in the dry run; remove it by hand first.
- Nothing inside `.git` is read, listed or touched, and no path may leave the book folder.

The draft takes its rules from `lib/book_config.py`, never from a list of its own: every path
key whose older-layout default exists and differs from the standard default gets a row. Some keys
move in parts instead of whole: only the dated run folders of `work.runs`, only the
`*-inbox` folders of staged entries (they go into the move's own run folder,
`.book/runs/<YYYY-MM-DD-HHMM>-init-existing/`, which is pruned with the other init runs), only the
`.<name>-cache` folders at the root, only the sales-text files of `publishing.sales_text`. The
Vale styles folder named by `StylesPath` goes to `rules/vale/`, and the packages the Vale config
downloads are dropped.

A few rows come from what the previous layout kept under retired names: `.book/inbox/` (or
`work.inbox`) goes into the move's run folder as `.book/runs/<YYYY-MM-DD-HHMM>-init-existing/inbox/`; `.book/inbox/incoming/` (or
`sources.incoming`) goes to `.book/sources-to-add/`; `.book/baselines/sources.json` (accepted
counts, which no check reads any more) goes into the move's run folder; and `reasons/counterarguments.md` and
`reasons/open-questions.md` go to `thinking/doubts/`.

## What `move --fix` does, in order

1. **Checks the whole plan first.** A missing path, two files for one target, a target that
   already exists, a file target that is also a folder, a target under a path that is a file,
   an unreadable file or folder that would move, a folder that cannot be written (to move out
   of or into), a dropped file that is already in the `--keep-dropped` folder, or a fetch or OCR
   record that is not a JSON object: any one of them, and nothing moves.
2. **Moves every file byte for byte**, with a sha256 taken before and after. A changed hash is a
   problem in the report. If a move still fails (a disk error, a change made while the move runs),
   the move stops at that file, leaves it in its old place, writes the report and `moves.tsv` of
   what did move, and keeps the plan where it was; the same plan run again moves the rest.
3. **Merges origin records.** In the older layout each cached source had `<Key>.fetch.json` and
   `<Key>.ocr.json` beside it. They become one `sources/library-index/<Key>.json` holding
   `{"fetch": {...}, "ocr": {...}}`, the shape the source scripts read; the merged file is read
   back and compared with the originals before they are removed.
4. **Drops** what the plan says, then removes the folders the moves left empty.
5. **Writes `book.yaml`.**
   - *Old layout:* from the `## Book Metadata` and `## Coined Terminology` sections of
     `CLAUDE.md`, keeping each metadata line's trailing `# comment`, plus every path key the
     plan did not send to its default. It then reads the file back and compares every metadata
     value and every coined term with what `CLAUDE.md` gave (`false` and `"false"` count as the
     same value). A difference is a problem.
   - *Previous layout:* the existing `book.yaml` is rewritten line by line, so every comment and
     every value it does not touch keeps its bytes: an old key name gets its new name (when
     both are set, the old one goes, because the new one already wins); a retired key
     (`work.inbox`, `sources.incoming`) and a top-level `layout:` go; a path key the move sent
     to its default goes; a path the plan kept elsewhere is written. The old file is copied to
     the run folder as `book.yaml.before`, and the new one must read back to exactly the
     intended values, or nothing is written.
   - *Both:* `book.cover_front`, `book.cover_back` and `book.ebook_cover` follow their files to
     their new place.
6. **Points paths at their new places**: the Vale config's `StylesPath`, and the cache lines and
   `see ...` pointers of the sources banks through `entry-format-fix.py`.
7. **Adds the missing `.gitignore` lines** from the template.
8. **Writes the report** to `.book/runs/<YYYY-MM-DD-HHMM>-init-existing/`: `move-report.md` (what happened, every
   problem, the result of `book_config.py check`, and the files that still name an old path),
   `moves.tsv` (every move with its sha256) and the plan itself.

Running the same plan again (`--plan` pointing at the copy in the run folder) finds every row
done and moves nothing.

## What the move leaves to the author

- **`CLAUDE.md` stays as it was.** After an old-layout move its two settings sections are
  copies of `book.yaml`; remove them when you rewrite `CLAUDE.md` into the short form (`new.py`
  writes the template as a guide in a new folder). While both exist, `book.yaml` wins. Its
  folder table and skill names still describe the older layout until you rewrite them.
- **`decisions.md` keeps its format.** A file without a current `## Index` fails
  `run-checks.py setup` until `decisions.py check --fix` rebuilds the index.
- **Files that name an old path.** The report lists each file and each old path it names. The
  header of an old bank keeps its old `## Entry format` example until someone rewrites it.
- **Content that must be split or merged.** The move takes whole files. When one file must become
  two (notes into `thinking/argument/` and the quotes bank, a tracking file into
  `rules/decisions.md`), do it
  as a separate step, and follow the rules below.
- **Paths inside the manuscript.** A file the manuscript names by path (an image folder in a raw
  LaTeX block) keeps its place unless the manuscript is edited in the same step.

## Rules for any move of text between files

These hold for the move and for any migration done by hand after it:

- **Move text word for word.** A move that also rewrites mixes two changes, and no hash can prove the
  move was clean.
- **Split only at explicit markers**, such as a heading, never at a place a reader judged to be
  the end of a topic.
- **Check that the pieces rebuild the original exactly**: joined in order they must give the same
  bytes, for example
  `python3 -c "import hashlib, sys; print(hashlib.sha256(b''.join(open(name, 'rb').read() for name in sys.argv[1:])).hexdigest())" part-1.md part-2.md`
  against the original's hash (the same line on every system).
- **Keep dated verdicts apart; never move them into a bank.** A verdict about the book goes to a
  dated run folder; only what stays true (a quote, a guardrail, a decision) moves into a bank or
  `decisions.md`, and each such line is re-read against its source first.
- **Dry run first, every time.** The plan is data the author reviews; the move is one command
  after that review.
- **No routing table in code.** Where a file goes is written in the plan, where the author can
  see and change it, never in a script.
