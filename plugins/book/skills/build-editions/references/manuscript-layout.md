# Manuscript layout the build expects

## Files and order

- The build takes the book's files from the shared config reader (`manuscript_files` in
  `${CLAUDE_PLUGIN_ROOT}/lib/book_config.py`), then keeps those whose name matches `pattern` (default `*.md`) and leaves
  out those matching `exclude`. `build-book.sh --show-settings` prints the result as
  `MANUSCRIPT_FILES`.
- **Natural order is the default** (`manuscript.order: natural`): every `.md` file directly inside
  the manuscript folder, sorted 1, 2, 10, not 1, 10, 2. Then **the file-name prefix is the table
  of contents.**
- **A list sets the order by hand**: `manuscript.order: list` with `manuscript.files` naming each
  file, relative to the manuscript folder, in book order. Use it when the file names carry no
  number. A listed file that does not exist stops the build.
- With natural order, use a 3-digit ordering prefix, `NNN-name.md`. Parts sit at `X00`, chapters at `X10` steps
  (`110`, `120`, ...), which leaves room to insert a file later without renaming the rest.
- Suggested bands: `000`-`099` front matter (copyright, dedication, epigraph, contents, preface,
  acknowledgments), `100`-`899` parts and chapters, `900`-`999` back matter (references).
- **Each part is its own file**: the `\part{...}` raw block plus the short overview paragraph that
  the part divider shows ([part-pages.md](part-pages.md)).
- The bibliography is one file whose first line is the level-1 heading `book.references_heading`
  (default `# References`), one entry per paragraph, each opening with its `[Key]`. Its path is
  `manuscript.references` in `book.yaml`.

## Headings

- A chapter file opens with `# Chapter N: Title` (the word is `book.chapter_heading_word`); the EPUB
  filter recognises chapters by this shape.
- Other top-level headings (Preface, Acknowledgments, References, or any the book adds with
  `book.heading_types`) get their EPUB section type from their text.

## Raw LaTeX blocks

Front matter (copyright page, dedication, epigraph), part dividers and the manual table of
contents are ` ```{=latex} ` blocks, so the print PDF controls the page. Only the commands listed in
[editions.md](editions.md) may appear in them; anything else stops the EPUB build by design.

## A manual table of contents

When a book wants its own contents styling, it sets `toc: false` (so pandoc's automatic contents
are off and only one table of contents appears) and adds a front-matter file holding:

````markdown
```{=latex}
\pdfbookmark[0]{Contents}{toc}
\tableofcontents
\newpage
```
````

`\pdfbookmark` puts "Contents" into the PDF outline; the EPUB filter drops both commands, and the
EPUB gets pandoc's own navigation.
