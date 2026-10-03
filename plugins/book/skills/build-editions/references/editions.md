# What each edition changes, and why

The manuscript is the one source. The print PDF is the reference; the digital PDF and the EPUB
change only what a screen needs.

## The digital PDF

Same trim, fonts, chapter styles and ornaments as print. Only this differs:

- **One-sided**, so the blank pages that make chapters open on the right are gone.
- **Centred margins.** The text block keeps its exact print width and is centred instead of
  offset for a binding. Line breaks, leading and page breaks stay identical; only the
  horizontal position moves. (Widening the measure would change every line break.)
- **Coloured links.** Internal links and the PDF outline exist in print too, but in black;
  here they are visible. Citations become links to their bibliography entry (below).
- **Covers bound in**: `cover_front` as page 1 and `cover_back` as the last page, when set.
  Print covers go to KDP as a separate wrap, so the print edition never binds them in. The
  cover images must be cut to the trim with no bleed; crop in the cover's own vector source,
  not by cutting a bleed raster afterwards, or the bleed and trim numbers end up copied in two
  places.
- No KDP gutter applies, so the page-count second pass is skipped.

## The EPUB and raw LaTeX

Front matter and part dividers are written as ` ```{=latex} ` blocks so the print PDF can
control the page. Pandoc drops raw LaTeX for every writer except LaTeX, which would silently
delete the copyright page, the ISBN, the dedication, the epigraph and every part title from the
ebook.

`assets/filters/digital-mode.lua` translates them instead. It is not a LaTeX parser: it knows
one closed set of commands and **stops the build naming any command it does not know**, so a
new construct in the front matter stops the build instead of vanishing from the ebook.

- **Dropped with their arguments** (page layout, no meaning in a book whose text flows to fit the screen):
  `\thispagestyle`, `\setlength`, `\bookmarksetup`, `\pagestyle`, `\addcontentsline`,
  `\markboth`, `\phantomsection`, `\vspace`, `\pdfbookmark`, and spacing and size commands such
  as `\vfill`, `\newpage`, `\small`, `\begingroup`. A book adds more with
  `book.latex_commands_to_drop`. Layout commands are dropped across the whole block first, so a
  `\thispagestyle` before a `\part` never reaches the unknown-command check.
- **Translated**: `\part{...}`, `\begin{center}...\end{center}`, `\textit`, `\emph`, `\textbf`,
  `\textcopyright`, `\\` line breaks, `~`, and `\langtext{language}{text}`.
- **`\langtext{latin}{...}`** becomes a span with `lang="la"`, so a screen reader stops reading
  the passage with the book language's pronunciation (WCAG 3.1.2). The print template defines
  `\langtext` as a plain passthrough, because babel's `\foreignlanguage` needs that language
  installed in TeX Live. A language with no BCP 47 code **stops the build**: a wrong `lang` tag
  is worse than none, because it tells assistive technology to read with confidently wrong
  rules. Add codes with `book.language_codes`.
- **Parts are numbered** in document order, in Roman numerals, so a divider reads
  "Part II: Title" in the text and in the navigation, as LaTeX numbers it in print. Without
  this, part titles sit in the ebook navigation looking exactly like chapter titles.
- **Front-matter sections.** Pandoc splits an EPUB into files at headings and puts anything
  before the first heading into one synthetic section named after the book. The copyright page,
  dedication and epigraph have no headings, so each converted block gets its own hidden level-1
  heading: its own file, correct EPUB semantics and a navigation entry. The copyright page is
  recognised by its text (`book.copyright_markers`); the dedication and epigraph cannot be told
  apart by content, so they are named in document order (`book.front_matter_pages`).
- **EPUB semantics.** Each section carries its `epub:type` (`copyright-page`, `dedication`,
  `epigraph`, `preface`, `acknowledgments`, `part`, `chapter`, `bibliography`), which also
  decides the file's `frontmatter` / `bodymatter` / `backmatter` body type. The attribute must
  sit on the level-1 heading: pandoc copies a heading's attributes onto the section it wraps
  around it and reads the body type from there. Pandoc's front-matter list has no `epigraph`, so
  that page is named correctly and still counts as body matter; calling it a `dedication` to get
  the body type would be a false statement about what it is. Only the bibliography also gets a
  DPUB-ARIA `role`. Chapters and the bibliography also get a class, because the `epub:type` is
  removed from the heading once copied and a stylesheet needs something that stays.
- **A top-level heading the filter cannot place** is reported by name and left alone: it costs
  an attribute, not content, so the build finishes. Add it with `book.heading_types`. Headings
  are classified by what they say, not where they sit: a one-chapter build has no front matter
  before it.
- **Table header cells get `scope="col"`**, so a screen reader reads each cell against the right
  column heading. This holds for every book: each cell of a table's head row describes the
  column under it.

### The publisher emblem

An image placed with a `tikzpicture` (in print, anchored to the foot of the copyright page)
becomes a plain image at the end of the copyright section, with the alt text
`book.emblem_alt`. The filter uses the PNG next to the named PDF when there is one, else the
SVG. Prefer the PNG: some reading systems show inlined SVG as raw text or draw an `<img>`
pointing to an SVG as a blank square, while a transparent PNG renders everywhere. The
stylesheet inverts it in dark mode, which works where `prefers-color-scheme` is supported and
quietly does nothing elsewhere. Rule: the simplest asset that renders on every reader.

### ASCII diagrams

Box-drawing diagrams (code blocks with the class `ascii`) must never wrap, and Kindle ignores
`overflow-x`, so scrolling is no fallback. The filter measures each diagram and sets its own
font size so it fits a 36-column reference width (about a 6-inch reader column at 1em
monospace). Below 0.60em it still fits the diagram, because clipping would lose the right-hand
side, and names it on stderr so you can narrow it or redraw it as SVG.

## Code blocks are flattened for Kindle

Pandoc wraps every highlighted code line in `<span id="cbN-M">` opened by an empty deep-link
anchor. Desktop reading systems render this correctly; Amazon's KFX converter does not, and the
listings arrive on Kindle as loosely spaced prose. `scripts/flatten-code-lines.py` removes that
layer from the finished EPUB, before epubcheck and before AZW3, so both check what ships. Run
alone, the script only counts what it would remove; the build passes `--fix`, which rewrites the
EPUB in place.

It keeps the syntax-highlighting spans: the per-line wrapper alone breaks the Kindle rendering,
so bold keywords and italic comments stay.

This is the one place the pipeline rewrites its own output, and it is no precedent: highlighting
happens inside pandoc's HTML writer, after every Lua filter, and pandoc has no option to turn
the wrapper off. The script refuses to guess: a wrapper it cannot close is an error, and
highlighted code with no wrapper at all is an error too, because it means pandoc changed its
output and a silent no-op would ship the defect. A book with no highlighted code has nothing to
strip and passes; a `--highlight none` build passes `--allow-empty`.

## One stylesheet

`assets/epub3-template.html` does not emit pandoc's `$highlighting-css$`. Pandoc injects its own
highlighting stylesheet into every chapter head in addition to `--css`, and it selects more
tightly: `pre > code.sourceCode { white-space: pre }` beats `pre { white-space: pre-wrap }`, so
no listing ever wrapped and every wrapping rule in `epub.css` did nothing. It also set
`display: inline-block` on every line span (the direct cause of code reading as spaced text on
Kindle) and underlined every data type token. `epub.css` covers the token classes the monochrome
style emits. If a book ever needs colour highlighting, add it to `epub.css`; never restore the
injection.

### What `epub.css` does, and why

- **Body text belongs to the reader.** No body font and no body size: Kindle, Apple Books and
  Kobo apply the reader's own. Justification is left to the reader too; hyphenation is on for
  prose only (it acts only when the reader justifies, and uses `xml:lang` to pick a
  dictionary), and never for code, URLs or headings, where a broken token reads as another token.
- **First paragraph after a heading, block quote, code block, table or break is not indented.**
  Both `pre + p` and `div.sourceCode + p` are needed: highlighted code is wrapped in a div,
  diagrams are bare `pre`. These are adjacent-sibling rules, so anything new placed between a
  heading and its first paragraph must be added to the list in the same change.
- **Heading sizes in em.** The hierarchy is the author's, the base size the reader's; ratios
  follow the print edition's proportional headings. Chapter openings are centred; part titles
  centred with extra space above; the part overview paragraph centred, italic, unindented.
- **Code.** Everything a code block needs is on the bare `pre` element, and class rules only
  take away, because pandoc writes the `sourceCode` class only while highlighting is on. Code
  wraps (`pre-wrap`) with no hanging indent: `text-indent` acts on the first line of the block,
  and in a listing every line is a hard break, so a negative indent misaligns the first line
  against the rest. A left border frames the listing (no background: a fixed light fill stays
  light on a night theme, and Kindle does not invert it). Code is left-aligned even when the
  reader justifies prose, because stretched spaces in code look like the author's alignment.
- **Code font.** Three subset faces of JetBrains Mono ship inside the book, because in code the
  face is functional: column alignment holds diagrams together, and 0/O and 1/l must differ.
  The generic `monospace` is the fallback. Naming Courier New first would force a thin, narrow
  face over every device's better default.
- **Syntax highlighting is weight and slant only**, never colour: most e-ink panels are grey,
  and a fixed colour survives into night mode on a background it was not chosen for. Keywords,
  control flow and data types are bold, comments italic; identifiers, strings and numbers stay
  plain, and operators are left alone, or most of every block would be emphasised.
- **ASCII diagrams** keep `white-space: pre` and lose the padding and border, because the filter
  sized them against the full column width.
- **Front matter.** The helper headings are hidden with `display: none` (Kindle honours it); the
  selector is `h1.fm-heading`, because the section also carries that class and a bare
  `.fm-heading` would hide the whole copyright page. Centred text is set on the `p` itself, not
  inherited, because some mobile readers justify every `p`. Dedication and epigraph sit a little
  above the middle of the page with `margin-top: 25%` then `30vh` (percent is measured against
  the width, so it is only the floor; readers that understand `vh` take the second line). Flex
  centring was not used: Kindle handles it unevenly, and its failure is a collapsed box.
- **Long tokens.** Bare URLs (only `a.uri`, never citation links) and inline code may break
  mid-token, because on a phone a long URL otherwise runs off the screen.
- **Bibliography** entries get a hanging indent so the keys form a straight column. The same
  declarations that misalign code are correct here, because each entry is its own paragraph.
  Bibliography URLs keep the reader's own link style: they leave the book, and looking like
  links is the point.
- **Citation links** look like the printed citation, underlined, in the text colour
  (`a.citation`, selected by class: some reading engines drop attribute selectors). The bracket
  already says "this points to the bibliography"; a coloured token on every page would make the
  least important thing the loudest. Readers may still restyle links; that failure is harmless.
- **Tables** are small and tightly padded; **block quotes** italic, as in print.

## Citations become links on screen

Citations are written as plain text (`[Smi99]`) with no markdown link behind them. On paper that
is fine; on a screen it was the largest missing affordance. `assets/filters/citation-links.lua`
anchors each bibliography entry and turns every other `[Key]` into a link to it, in two passes
over the whole document, because a citation cannot be linked before the anchors are known.

- **The rule it protects:** a citation is either a link that lands on its entry, or plain text
  plus a warning. It is never a link that goes nowhere (pandoc would send a mistyped key to the
  top of the current chapter, and nobody would notice).
- **Visible text never changes.** A lone key links whole, brackets included, which gives an
  e-reader a tap target. In a group (`[Smi99, Wal--]`) only the keys link.
- **Only key-shaped text is considered.** The key shape in the filter must accept every key
  `${CLAUDE_PLUGIN_ROOT}/lib/citation_key.py` can make, and nothing else; `scripts/key-pattern-check.py` checks this.
  The bibliography decides what gets linked: a key-shaped token no entry backs becomes a warning.
  A bracket must hold keys and separators only, so a quoted `[a phrase]` is never a citation.
- **Anchor ids** are cut to letters, digits and hyphens (`[ABC+20]` anchors as `ref-ABC-20`): a
  `+` is not a valid XML name character, and pandoc repairs only ids that start wrong. One
  function makes both the anchor and the link, so they cannot disagree. Two keys that would give
  one id are reported, and the second is left unlinked.
- **Where it acts.** EPUB and HTML, plus any build with the `digital-edition` flag. A print build
  gets nothing from it. There is no condition in the build script: a second copy of that
  decision would sit where nobody looks when the two disagree.
- **Filter order matters.** `digital-mode.lua` runs first and turns raw front matter into blocks;
  `citation-links.lua` reads what it leaves.
- **The bibliography** is the level-1 heading `book.references_heading` (default `References`).
  Without it the filter links nothing and says why.
- **It always prints one summary line on stderr**:
  `linked N citations into M of T bibliography entries; U unresolved key(s), C uncited entry/entries.`
  A filter that linked nothing looks exactly like a filter never wired in; the line tells them
  apart. Different numbers from the last build are the thing to chase.

Both container runs mount the filter folder read-only at `/filters`: one mechanism, no copies in
the book.

## Bundled code font

`assets/fonts/JetBrainsMono-{Regular,Bold,Italic}.subset.ttf` (JetBrains Mono 2.304, SIL OFL 1.1
with no reserved font name, so a subset may keep the family name). `assets/fonts/OFL.txt` must
travel with them, and the licence block at the end of `epub.css` must stay identical to it:
embedding a font in an EPUB is redistribution.

The subset holds U+0020-007E, U+00A0, U+2013-2014, U+2018-201D and U+2026 only: no accented
letters, no box-drawing characters, no arrows. A book whose code uses any other character falls
back, glyph by glyph, to the device monospace and loses column alignment.
`scripts/code-font-check.py` lists such characters. To widen the subset, cut it again from the
full release, for example:

```bash
pyftsubset JetBrainsMono-Regular.ttf --output-file=JetBrainsMono-Regular.subset.ttf \
  --unicodes="U+0020-007E,U+00A0-00FF,U+2013-2014,U+2018-201D,U+2026,U+2190-21FF,U+2500-257F"
```

and do the same for Bold and Italic, then update the range in `code-font-check.py`.
