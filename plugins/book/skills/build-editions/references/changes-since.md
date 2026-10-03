# The --changes-since copy: a copy that shows what changed

Renders the book in its current state with the text that changed since an older git commit on a
pastel-yellow background, so a reviewer sees what is new since they last read it without paging
back and forth. PDF editions only.

```bash
build-book.sh --changes-since abc1234                    # changes since abc1234; new state = files on disk
build-book.sh --changes-since v0.3 --changes-until v0.4        # between two commits
build-book.sh --reviewer-copy "Jane Smith" --changes-since review-2
```

## Behaviour

- Word-level inside prose paragraphs: only the changed or added words are highlighted.
- A whole-block highlight (a soft-yellow rounded box that breaks across pages) for paragraphs,
  headings, lists or code blocks that are entirely new.
- Removed text is not shown; each chapter is rendered in its new state.
- No margin marks; the highlight is the only signal.
- Code blocks are atomic: if any line changed, the whole block is boxed.
- Without `--changes-until`, the new state is the files on disk, uncommitted edits included; the build
  says which it used and how many manuscript files are uncommitted.
- `--changes-since <ref>` means "changed since that commit", so what that commit itself introduced is
  part of the baseline. To include its own changes, pass its parent (`<ref>^`).
- Headings and raw LaTeX blocks are never put inside the yellow box: a `\part` divider or a
  `\newpage` inside a `tcolorbox` would lose its page behaviour.

## Requirements

- The book must be inside a git repository; refs are resolved against
  `git rev-parse --show-toplevel`, so a book in a subfolder of a larger repository works.
- `python3` and `git` on the host (the marking runs outside Docker).
- The first diff build installs `soul`, `tcolorbox`, `environ` and `pdfcol` into the TeX Live
  volume (a few seconds, once).

## How it works

1. A rename map comes from `git diff --find-renames --name-status <from> [<to>]` (with a raised
   rename limit), so a moved or renumbered file is compared with its old path. Without it, a
   renamed file has no old version and every word shows as new. The old version is read with
   `git show <from>:<old path>` (straight to a file, because command substitution strips final
   newlines and would mark an unchanged last block as changed); the new one is the file on disk
   or `git show <to>:<path>`.
2. `scripts/diff-preprocess.py` compares blocks. A prose block with an old counterpart (similarity
   at least 0.3) gets a word-level diff; new blocks and changed code blocks get a fenced div. All
   marks carry the class `added`. Whitespace-only gaps between two changed runs are joined, so
   the highlight reads as one stretch. The marked files go to the build's temporary folder under
   their path in the book, so two files with the same name in different folders stay apart;
   nothing is written into the book.
3. `assets/filters/diff-mode.lua` turns `Span.added` into `\added{...}` and `Div.added` into an
   `addedblock` environment.
   - `soul` cannot re-typeset content that switches fonts or makes its own boxes (inline code,
     math, links, images, citations, raw LaTeX, strikeout) and fails with "Reconstruction
     failed", so that content is wrapped in `\mbox{}`. Footnotes cannot live in an `\mbox`, so
     they are lifted out of the highlight.
   - `soul` sets the character that ends a word through an 8-bit fallback font. Pandoc writes
     smart punctuation as Unicode, so a word-final closing quote, dash or ellipsis would drop off
     the page with only a "Missing character" warning. The filter writes those seven characters
     as macros the template registers with `soul`.
   - Any other character above U+00FF (an arrow, a comparison sign, a letter outside Latin-1) has
     no macro; the filter hands it to `soul`'s `\soulomit`, which passes it through untouched.
     That costs the highlight behind that one character, so it is applied only to the run of such
     characters that ends a word. Word-initial and word-internal characters, and every ASCII
     text, render exactly as before.
4. The template defines `\added` as a `soul` highlight (`#FFF9C4`, line-break safe) and
   `addedblock` as a page-breakable `tcolorbox` of the same colour, both only when the
   `diff-mode` flag is set, so other builds are not affected.

## Limits

- The colour is fixed at `#FFF9C4` (about 20:1 contrast with black text). Change
  `\definecolor{addedbg}` in the template for another shade.
- Markdown emphasis that straddles a diff boundary (a `**bold**` span where only half the words
  changed) may render the unchanged half outside the highlight.
- Rename detection works on content similarity. A file both renamed and rewritten past git's
  threshold (about half the content changed) is shown as all new, which is usually the honest
  result; keep the old file name for that build if you want it compared with its origin.
- There is no EPUB diff edition.
