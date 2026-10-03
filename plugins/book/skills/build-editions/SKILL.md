---
name: build-editions
description: >-
  Builds the book from its Markdown manuscript into a print PDF for a KDP paperback, a PDF for
  screens and a checked EPUB 3 for ebook stores and Kindle. Use it when the author asks to
  build, make or export the book, a PDF, an EPUB or a Kindle file, a draft or a reviewer copy,
  one chapter as PDF, or a copy that shows what changed since the last review. For the cover
  files use design-cover; for the store texts use prepare-sales-text.
argument-hint: "[all|print|digital|epub] [--final|--reviewer-copy NAME|--changes-since COMMIT]"
---

# Build editions

Turn the manuscript into book files with pandoc, XeLaTeX and the EPUB writer, all in Docker.

Scripts live in `${CLAUDE_PLUGIN_ROOT}/skills/build-editions/scripts/`. Below, `build-book.sh` means
`${CLAUDE_PLUGIN_ROOT}/skills/build-editions/scripts/build-book.sh`.

## Modes

| Mode | Command | Output |
|------|---------|--------|
| `all` (default) | `build-book.sh` | print PDF, digital PDF and EPUB, built at the same time |
| `print` | `build-book.sh --edition print` | KDP paperback interior: two-sided, gutter margins |
| `digital` | `build-book.sh --edition digital` | screen PDF: one-sided, centred text block, live links, covers bound in |
| `epub` | `build-book.sh --edition epub` | EPUB 3 whose text flows to fit the screen, checked with epubcheck |

Flags that work with any mode:

| Flag | Output |
|------|--------|
| `--final` | no draft marks, no protection, fixed file name |
| `--reviewer-copy "Name"` | draft with the reviewer's name and PDF protection |
| `--changes-since <commit>` | PDF with everything new since that commit on a yellow background |

Always build drafts while working. Build `--final` only when the author asks for the file that
ships.

## Quick start

```bash
build-book.sh                                   # all three editions, as drafts
build-book.sh --edition print                   # one edition, faster to repeat
build-book.sh --final                           # the files that ship
build-book.sh --reviewer-copy "Jane Smith"      # protected draft for one reader
build-book.sh --top-level part --toc-depth 3    # a book in parts, deeper contents
build-book.sh --final --subtitle "A Complete Guide" --format 6x9
```

Run it from anywhere inside the book: it always builds the manuscript folder the config names.
To build another folder of the book, pass it as the last argument or with `--manuscript`.
`build-book.sh --show-settings` prints every value a build would use and stops, without Docker:
use it to check a new `book.yaml`.

## Where the settings come from

The script finds the book root by walking up to `book.yaml`. Every value is taken in this
order:

1. a command-line option (`--font garamond`), or `--set book.font=garamond`;
2. `book.yaml`, under `book:` (build settings), `manuscript:` and `work:` (folders), `tools:`
   (Docker image and TeX Live volume);
3. the built-in default.

`--config FILE` names a `book.yaml` directly. Every key, with its values and default, is in
[settings.md](references/settings.md). Paths come from the shared config reader
(`${CLAUDE_PLUGIN_ROOT}/lib/book_config.py paths --shell` and `metadata --shell`), so the
output goes to `.book/output/` unless `work.output` names another folder.

## Editions

The editions share nothing but their inputs, so `--edition all` builds them in parallel; the
total time is the time of the slowest one, not the sum. Two things make this safe. First, the TeX
Live volume is filled once **before** the parallel builds start: two installs into one volume at
the same time would break it. Second, each edition's output goes to its own log, printed whole
in a fixed order: three LaTeX logs mixed together cannot be read when something fails. `--sequential`
builds one at a time and shows each log live, which helps when you debug a failure. One
edition failing never stops the others; failures are listed again at the very end.

- **Why two screen formats.** A fixed-layout PDF reads badly on a phone; an EPUB whose
  text flows to fit the screen gives up the designed typography. Neither replaces the other.
- **Kindle needs no separate build.** KDP takes EPUB 3 and converts it itself, so the EPUB is
  the Kindle file. `--azw3` also makes a file to test on your own device (needs calibre).
- **The EPUB is skipped** in an all-editions run with `--reviewer-copy`, `--protected` or
  `--changes-since`: protection and diff highlighting exist only in the PDF, and an unprotected
  EPUB beside a protected PDF would undo the protection.

What each edition changes, and why, is in [editions.md](references/editions.md). The EPUB
package metadata and the EPUB template copied into this skill are in [epub.md](references/epub.md).

## Draft and final

| | Draft (default) | Final (`--final`) |
|--|--|--|
| Marks | diagonal DRAFT watermark, "DRAFT - date" footer, draft ID in the PDF | none |
| Copyright notice on the page edge | yes, when an author is set | no |
| Protection | yes: no copy, no print, no edit (`--unprotected` turns it off) | no |
| File name | `title-lastname-draft-TIMESTAMP.pdf` (`-draft-reviewer-` with `--reviewer-copy`) | `title-lastname.pdf` |

The digital PDF adds `-digital`; the EPUB ends in `.epub`; `--azw3` writes `.azw3` beside it.
Without a title and author the name is `book`. `--output <name>` sets the name yourself.
Protected drafts carry metadata: author, subject ("DRAFT for Name"), keywords (the unique draft
ID) and the copyright notice.

## Placeholders never block a build

Text such as `TO BE ASSIGNED` (for example an ISBN on the copyright page) never stops a build.
The build always writes its file, then lists every place the placeholder still appears, as
`file:line` with the line itself, **after** the last `Done!` line. A warning in the middle of
hundreds of build lines is a warning nobody reads. A final build is told plainly that
the file is not fit to publish; a draft gets the same list. An all-editions run prints one list
at the end for all three files. The text searched for is `book.placeholder_text`
(default `TO BE ASSIGNED`).

## Before you build

- Read the index of the book's decisions file when it exists (`rules.decisions` in
  `book.yaml`; `python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py index`, then
  `decisions.py show ID` for an entry). Build settings the author settled there
  (trim, body size, fonts, part pages) are not changed or re-proposed without being asked.
- Draft, show, then apply: when a setting change would change the page count or the look,
  build a draft, show the author the difference, and only then change `book.yaml`.
- Never commit, push or run git for the author. The `--changes-since` copy reads git history only.

## Requirements

- Docker, running. The image is `tools.pandoc_image` (pinned, default `pandoc/extra:3.8.3`);
  fonts and TeX packages are installed once into the Docker volume `tools.pandoc_volume`.
- bash 3.2 or newer for `build-book.sh` and the two settings files it sources: it starts
  pandoc and XeLaTeX in Docker and passes many settings through, and bash is on Linux and
  macOS already. On Windows the build needs WSL (Git Bash is not enough: it rewrites the
  container paths). Every other script of the skill is Python and runs anywhere.
- On Linux, pandoc runs as the calling user, so every file written into the book belongs to
  you; Docker Desktop on macOS and Windows does this by itself. Only the one-time TeX Live
  install, and the PDF protection step when `qpdf` is not installed on the host, run as root
  inside the container.
- python3 (standard library only) for the helper scripts.
- Optional: `fc-match` and the body font installed on the host, for computed leading (without
  them the template's default leading is used and the build says so); `pdfinfo` or `qpdf` for
  the page count; java for epubcheck; calibre for `--azw3`; git for `--changes-since`.

A missing optional tool makes that one step say `SKIPPED` and why; it never fails the build.

## What is cached, and where

| Cache | Location | Cost when cold |
|-------|----------|----------------|
| TeX Live packages and fonts | Docker volume `tools.pandoc_volume` | minutes, once |
| fontconfig index | `.fontconfig-cache/` inside that volume | a few seconds, once |
| epubcheck | `~/.cache/book/build-editions/` (checked against a pinned sha256) | one download |

The fontconfig index lives in the volume, not the container, because the container is removed
after every run. It is refreshed with plain `fc-cache`, never `fc-cache -f`, which would throw
the cache away each time. To force a clean reinstall: `docker volume rm <tools.pandoc_volume>`.

Faster repeats: one chapter with `--pattern "<chapter file>.md" --final` (for example
`--pattern "110-*.md"` when files carry a number prefix); the full book without the
protection pass with `--unprotected`.

## The --changes-since copy

`--changes-since <ref>` renders each chapter in its new state with added and changed words on a
pastel-yellow background, so a reviewer sees what changed since they last read it.
`--changes-until <ref>` picks the new state (default: the files on disk). PDF only. Details, rename
handling and limits: [changes-since.md](references/changes-since.md).

## Scripts

| Script | Does |
|--------|------|
| `build-book.sh` | builds the editions (the only entry point you normally call) |
| `page-settings.sh`, `book-settings.sh` | sourced by `build-book.sh`: page geometry, fonts, checks of values; reading the book config |
| `compute-leading.py` | body leading from the font x-height and the text width ([leading-model.md](references/leading-model.md)) |
| `filter-settings.py` | writes the book settings the Lua filters read |
| `flatten-code-lines.py` | removes pandoc's per-line code markup from the EPUB, for Kindle (the build passes `--fix`) |
| `output_files.py` | finds the newest EPUB in the output folder for the two EPUB scripts |
| `epub-check.py` | runs epubcheck; SKIPPED without java |
| `diff-preprocess.py` | marks changed text for a `--changes-since` copy |
| `code-font-check.py` | lists characters in the manuscript's code that the bundled EPUB code font lacks |
| `key-pattern-check.py` | checks that the citation-link filter reads keys the same way `${CLAUDE_PLUGIN_ROOT}/lib/citation_key.py` does |
| `self-check.py` | runs every script's self-test on the fixtures in `scripts/fixtures/`; needs no Docker (the steps that read settings through `build-book.sh` need bash) |

Every Python script has `--help` and `--self-test`; those that read the book take
`--config`/`--set`.

## Rules that keep the build honest

- **One source for every edition.** Front matter and part dividers are raw LaTeX blocks, which
  pandoc drops for the EPUB. `assets/filters/digital-mode.lua` translates a closed set of
  commands and **stops the build on any command it does not know**, so the manuscript and the
  filter cannot drift apart without the build saying so. Add a command a book needs through
  `book.latex_commands_to_drop` rather than by editing the filter.
- **A step that did not run says so.** epubcheck without java, a template drift check without
  an unchanged copy of pandoc's own template, leading without the font: each prints SKIPPED or the fallback it used.
  Never report a check as passed when it was skipped.
- **The citation-link filter always prints its summary line** (`linked N citations into ...`).
  That line is the difference between a filter that linked nothing and one never wired in.
- **The EPUB template copied into this skill and the unchanged copy of pandoc's own template
  are one thing** and are refreshed together ([epub.md](references/epub.md)).
- **The EPUB identifier never changes** once a book is published ([epub.md](references/epub.md)).

## References

| File | Holds |
|------|-------|
| [settings.md](references/settings.md) | every config key and command-line option, structure mapping, page formats |
| [editions.md](references/editions.md) | what the digital PDF and the EPUB change, and why |
| [epub.md](references/epub.md) | EPUB identity and package metadata, the EPUB template copied into this skill |
| [page-styles.md](references/page-styles.md) | folios, typography, fonts, chapter/section/quote/page-number styles |
| [changes-since.md](references/changes-since.md) | how the changes copy works and its limits |
| [typography-research.md](references/typography-research.md) | the margin formula, the KDP gutter table, heading patterns |
| [leading-model.md](references/leading-model.md) | x-height, point size and leading |
| [print-specs.md](references/print-specs.md) | trim sizes, font choice evidence, print mistakes to avoid |
| [part-pages.md](references/part-pages.md) | when part divider pages earn their place |
| [tables.md](references/tables.md) | why a table column overflows in the PDF, and the fix |
| [manuscript-layout.md](references/manuscript-layout.md) | file naming, order and the manual table of contents |
