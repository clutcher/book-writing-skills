# EPUB identity, package metadata and template

## Identity rules

- **`epub_identifier` never changes.** Reading systems file bookmarks, reading position and
  highlights under the EPUB's `dc:identifier`, and a store reads a file with a new identifier as
  a new title, not an update. Not a corrected edition, not a rebuild: never. Left unset, pandoc
  makes up a random UUID on every build, which is exactly that failure, so the build warns.
  Before an ebook ISBN exists, set a `urn:uuid:`; when the ISBN arrives, replacing the value is
  the whole change. An ISBN in any punctuation is written as `urn:isbn:` with its ONIX scheme
  (`ISBN-13` or `ISBN-10`).
- **`publication_date` is the book's date, not the build's.** It gives `dc:date` and the year in
  `dc:rights`. Taken from the build clock, the rights line would move on the first rebuild after
  New Year while the printed copyright page still says the year before. Pandoc writes the build
  time separately as `dcterms:modified`, which is the one that should move.
- **`publisher` and `subjects`** are store and library discovery data, left out of the package
  when missing.
- **`language`** (BCP 47, default `en-US`) gives `dc:language` and the `xml:lang` on every file;
  hyphenation dictionaries and screen readers depend on it.

## One source for the package

The OPF metadata is written from one place: the `--epub-metadata` fragment the build writes into
its temporary settings folder. Nothing about the book's identity goes on the pandoc command line
beside it. A value given twice does not merge: the package ends up with two titles and two
creators holding the same text.

- The **subtitle** is a `dc:title` of type `subtitle`, never `dc:description`, which stores print
  as the blurb. `description` goes to `dc:description`.
- The **author** carries `opf:file-as` ("Surname, Given"), so libraries and Calibre shelve the book
  under the surname. The surname is the last word of `author`, the same rule that names the
  output file, so the shelf and the file name cannot disagree.
- A `<meta refines="...">` written into the fragment is thrown away (pandoc keeps only `ibooks:`
  and `calibre:` meta there). EPUB 3 refinements are asked for as `opf:` attributes on the `dc`
  elements (`opf:type`, `opf:file-as`, `opf:role`, `opf:scheme`), and pandoc writes the
  `<meta refines>` itself.
- Two values cannot go in the fragment and are passed separately: `accessibilitySummary` (it has
  no `dc` element) and `pagetitle`, which the navigation document takes its `<title>` from.

## Accessibility summary

`book.accessibility_summary` states only what has been established about this book. There is
**no default**: whether code and diagrams are text or pictures differs from book to book, so a
built-in sentence would be a false claim for some of them. Without the key the EPUB carries no
summary and the build warns, as it does for a missing `epub_identifier`. A book that is all text
might write: "This publication is fully textual, with a structured table of contents and
navigable headings throughout. Code listings and diagrams are preformatted text rather than
images. It has not been independently audited for accessibility conformance." There is
deliberately **no
`dcterms:conformsTo`**: a WCAG AA claim nobody has tested is the same defect as a check that
reports success without running. Change the summary only when something new is true, such as
an audit.

## The EPUB template copied into this skill

`assets/epub3-template.html` is pandoc's default epub3 template with three changes, and the EPUB
build requires it: were it missing, pandoc would use its own default and quietly bring the bugs
back.

1. **A `<title>` per file.** Pandoc sets the `pagetitle` variable to the file name of each chunk
   (`ch007.xhtml`), and a writer variable beats metadata, so every file was titled after its own
   file name in reader headers and bookmarks. The chunk's heading is available as `$title$`. The
   head line is guarded, `$if(title)$$title$$else$$pagetitle$$endif$`: `nav.xhtml` and
   `cover.xhtml` have no chunk heading and fall back to the book title from `pagetitle`.
2. **Cover alt text.** The cover page is made from an empty body through a fixed branch no Lua
   filter can reach, so its `<svg>` had no name while the package claimed
   `accessibilityFeature: alternativeText`. It now has `role="img"` and an `<svg><title>` of
   `Cover: $pagetitle$`, falling back to `Cover`. The name is derived from the book title, never
   written into the template.
3. **No `$highlighting-css$`** (see "One stylesheet" in [editions.md](editions.md)). The
   `<style>` element is written only when there is citation CSS to put in it, so no file gets an
   empty `<style>`.

One caveat: `$title$` renders the heading's inline markup, so a chapter heading in italics or
code would put an element inside `<title>`, which is invalid. Pandoc offers no plain-text form of
the chunk heading to a template. The failure is loud: epubcheck reports it as `RSC-005` errors.

The file ends in `.html` because it is an XHTML document and editors treat it as one; pandoc
takes `--template` by path, so the extension is free.

### Pin and drift check

The template was taken from **pandoc 3.8.3** (`pandoc --print-default-template=epub3` in the
`pandoc/extra` image), which is why `tools.pandoc_image` defaults to `pandoc/extra:3.8.3`. The
template file itself carries no comment about this: an HTML comment would ship inside every XHTML
file of every book.

After each EPUB build, the drift check compares the image's current default template with the
untouched copy kept beside it, `assets/epub3-template.pandoc-default.html`, and **warns** when
they differ. A stale template is something to go and look at, never a reason to hold back the
book. Without that unchanged copy the check says SKIPPED and prints the command to take one; it
never reports an agreement it did not establish.

**The two files are one thing and are refreshed together.** Refreshing only the unchanged copy
silences the warning without fixing anything. To refresh:

```bash
docker run --rm --entrypoint pandoc <tools.pandoc_image> --print-default-template=epub3 \
  > assets/epub3-template.pandoc-default.html
cp assets/epub3-template.pandoc-default.html assets/epub3-template.html
```

then apply the three changes above to `epub3-template.html` by hand, change
`tools.pandoc_image` in the plugin's default and in this file to the same pandoc version, and
run `scripts/self-check.py`: it applies the three changes to the unchanged copy and fails unless
the result is exactly the copied template, so nothing else can slip in.

The template comes from pandoc's templates, which are offered under GPL-2.0-or-later or
BSD-3-Clause; see `assets/epub3-template-LICENSE.txt`.
