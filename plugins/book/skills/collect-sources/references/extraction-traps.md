# Extraction traps: why a grep miss is not "the source does not say this"

A cached `.txt` is the output of a tool, and tools guess. Before concluding that a source does
not contain a phrase or a figure, rule out the traps below. `quote-in-file-check.py` already tries
most of them; this file is for the reader doing it by hand, and for knowing what the checks mean.

## Layout mode interleaves columns

`fetch.py` extracts with `pdftotext -layout`. On a two-column paper, `-layout` keeps the visual
arrangement, so it **interleaves the two columns line by line**: a quoted sentence exists in the
cache broken across a column gap, and `grep -F` fails exactly as if the paper did not say it. An
interleave can even drop a negation and appear to reverse an author's position.

```bash
pdftotext "<files>/<Key>.pdf" -     # plain mode: content order, columns not interleaved
```

Plain mode for prose and quotes; `-layout` for tables, where column alignment is the information.

Some PDFs alternate columns in their own content stream, so both modes give the same broken text,
and page 1 may extract correctly while the body does not. When a phrase that crosses a line break
returns nothing on a two-column paper, check a body page, not the first page.

## Glyph substitutions to normalise before retrying

| Seen in the extraction | Means |
|---|---|
| `ﬁ` `ﬂ` as single glyphs | `fi`, `fl` |
| `V` inside a word ("eVect", "diVerence") | `ff` (a family of publisher PDFs) |
| `W` inside a word ("signiWcant") | `fi` (same family) |
| a word split across a line break | hyphenation |
| a missing space (`by108`) | run-together words |
| letters spaced apart | letterspacing: strip ALL whitespace before comparing |

The `V`/`W` case is the worst because the substitute is a plain letter and nothing looks wrong.
Try an 8-word window with the suspect letters wildcarded before deciding the source lacks a phrase.
A math font can drop test statistics silently: a paper that seems to report none has almost
certainly lost them in extraction. Render the page and look.

## OCR text

When a cached PDF extracts to almost nothing, the source is present and unsearchable, not
unreadable. Run `ocr.py --key <Key>`; it writes `<Key>.txt` with an `OCR-PROVENANCE` header, an
OCR origin record, and prints the `Access status: READABLE VIA OCR` line. It refuses to write
under 2000 characters (the scan needs a higher `--dpi`, or is unusable). A non-English scan needs
its tesseract language pack; say so rather than calling the scan unreadable.

- **`READABLE VIA OCR` supports searching, not quoting.** Every engine confuses rn/m, l/1, O/0; a
  quote found in OCR text shows the passage exists and is roughly worded so. Exact wording means
  looking at the page image.
- **Digits are a rule, not a matter of care.** "224 ms" and "22A ms" are one glyph apart, and once
  a figure is typed into the book nothing can catch it. **Every digit from an OCR text is confirmed
  against the page image before it enters the quotes bank or the book, and the entry says so.**
- **Three markers, all must agree**: the OCR origin record, the header in the `.txt`, and
  `READABLE VIA OCR` in the list. A partial marker is worse than none: it teaches that unmarked
  means clean. `ocr-marker-check.py` checks all three.
- **Inherited OCR is the trap.** A scan can arrive with someone else's OCR already in its text
  layer: pdftotext gives an ordinary-looking extraction, no marker exists anywhere, and the
  errors are just as real (an author's own name misspelled on the title page is the tell). Only
  `scan-origin-check.py` finds these, from the PDF itself, and it grades rather than decides:
  a producer string alone over-reports (Ghostscript is a general distiller), full-page images
  alone over-report on figure-heavy papers, and a good OCR engine leaves the text clean enough to
  pass an error signature. Do not reason "the prose looks clean, so the text layer is real". Assume
  the text layer of a source older than about 1995 is machine-read until shown otherwise.
- **A prose note saying "OCR" is a claim to check**, never a marker: a note can say OCR about a
  born-digital book whose only "damage" is an italic digit. `scan-marker-sweep.py` reports such notes.
  Record a born-digital verdict in the entry's `Fetch note` so the next run does not triage it again.
- An HTML cache can carry OCR-style errors too (a host may serve OCR text as HTML), so HTML is no
  guarantee about digits. A re-typeset digitisation's page render is not an independent check on
  its own OCR.
- A PDF whose pages are partly without a text layer (`text-gap` in `scan-marker-sweep.py`) hides
  those pages from grep while every other page extracts perfectly.

## Corrupt statistics in born-digital files

"Is it a scan?" and "can I trust the characters?" are different questions. A born-digital PDF can
remap glyphs so its text layer turns `=` into `5`, minus into `2`, `<` into `,`: `n 5 16`,
`p , .001`. `statistic-integrity-check.py` finds this class. What to know:

- **A digit where an operator belongs** is the tell: `n 5 16` is `n = 16`, a leading `2` on a
  coefficient is a minus.
- **A statistic with no operator at all** (`p .001`) is worse: nothing looks odd.
- **A decimal point rendered as a colon** (`22:2`, `po0:001`) passes every sanity check a reader
  applies: it reads as a ratio or a typo. Any PDF whose statistics contain colons is re-read from
  a render. This is not confined to one publisher.
- **A symbol substituted by a printable character** (`¼` for `=`, a box glyph for `<`): a grep for
  the operator returns nothing on a paper that reports it; search for the bare number.
- **A Greek letter flattened to a Latin one** changes which statistic is named (epsilon-squared
  read as eta-squared). Check which one before quoting an effect size.
- **Digits and operators fail independently**: confirming the numbers is not enough if the
  comparison lost its direction.
- **A minus sign can vanish**, reversing a finding without changing a digit, and `r = 0.28` looks
  ordinary. It is caught only where the source contradicts itself (a sentence says "negative" while
  every value is unsigned; an interval printed largest-first), and one caught sign condemns the
  whole file: re-read every sign from a render.
- **A dropped trailing digit leaves a legal value** (`F(3, 111)` extracted as `F(3, 1)`): only
  arithmetic finds it. A df implausible for the stated N, or inconsistent with the paper's other
  tests, is the tell.
- **The claim is file-level**: "this extraction substitutes characters, re-read every figure from
  a render", never "this exact line is wrong". A few hits in a flagged file point at a copyright
  sign or a page range, always inside a file that genuinely remaps.
- **Subscripts vanish**: `t₁` and `t₂` both extract as `t`, so a statistic cannot be tied to the
  right analysis from text alone.
- **Some HTML splits every statistic one token per line**; search for the bare number.

## A flagged figure is a prompt to open the page, never a puzzle

- **A corruption can be layered.** Reading `p < 95` as one lost decimal point gives `p < .95`; the
  page can print `p < .05` (a lost point AND a misread digit). Never publish an inferred original;
  state the extraction and the page value.
- **A suspicious figure can be the source's own printing error**, faithfully extracted. Check the
  page before adding a key to a defect class.
- **Quote the source's loose wording as printed.** Correcting an author's notation (`p = 0.001`
  where convention writes `p < 0.001`) turns a quotation into a paraphrase.
- **Sanity-check degrees of freedom**: a paper can state N subjects while every df implies another
  number. Report the discrepancy; never choose the number that suits the argument.
- **Two-column extraction can manufacture a statistic**: a `p =` at the end of one line welded to
  an axis tick from the facing column reads `p = 60`. Render the page and look at what is beside it.
- **In a multi-article volume, read the column, not the running head.** A running head marks the
  page, not the paragraph, and it can turn over one page early, so a target article's last column
  can sit under a commentary head. The same holds for proceedings and festschrifts.

## The cache can hold the wrong document

- a later page on the same topic, by another author, that NAMES the cited author;
- a discussion thread ABOUT the source; every verdict drawn from it is void;
- an arXiv or publisher **abstract page** (HTTP 200, so "cached" proves nothing), while the full
  PDF sits beside it or was never fetched;
- a stub that is the whole public page (a catalog entry whose body is behind a paid edition);
- a **summary of recordings** (notes over a video): a quote of the speaker cannot be refuted from
  the notes;
- a **re-keyed transcript** of a printed paper (check `pdfinfo` Creator: a browser print of a web
  page is not the journal): it silently normalises punctuation, so it cannot settle a
  one-character quote claim until the version of record is read;
- a **translation** into another script, which reads as mojibake to an English quote.

Check the cached document's title against the entry before trusting anything drawn from it
(`quote-in-file-check.py` reports `identity-mismatch` and `cache-title-mismatch`). Record grep
traps you find (a line break inside a phrase, a hyphenated word) in the entry's `Fetch note`.
