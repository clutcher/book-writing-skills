# Term formatting: italic, bold, monospace, quotes

The evidence behind rules 9.5-9.9: how key terms, concepts and code names are formatted across
book genres, publishers and style guides. The rules pick the trade and professional school
(italic at the formal definition, then roman).

---

## 1. The Common Convention

**Italic on first use of a new term** is the convention of the major style manuals used in book publishing (CMOS, APA), and the publishers and documentation guides that set code follow it too. Textbooks are the main exception (section 2).

| Publisher/Guide | New term (first use) | Subsequent uses | Bold for terms? | Code elements |
|-----------------|---------------------|-----------------|-----------------|---------------|
| CMOS | Italic | Roman | Only textbooks w/ glossary | N/A |
| APA | Italic | Roman | No | N/A |
| O'Reilly | Italic | Roman | No | Monospace |
| Microsoft Style Guide | Italic | Roman | No (UI only) | Monospace |

---

## 2. Three Schools of Term Formatting

A clear pattern emerges across book genres:

### Textbook School (bold for key terms)
- Uses **bold** on first introduction of defined terms
- Terms typically also appear in a glossary
- CMOS explicitly endorses this for textbooks
- Examples: *Campbell Biology* and most university science textbooks, and many reference works
- Rationale: Students scanning for definitions can quickly locate bold terms

### Trade/Professional School (italic for key terms)
- Uses *italic* on first introduction, then roman type
- No glossary dependency
- Standard across trade publishers and professional books
- Examples: Pinker, popular science with academic roots, most trade non-fiction
- Rationale: Italic signals "pay attention, this is being defined" without the visual weight of bold

### Minimal Formatting School (prose does the work)
- Relies on prose and context to introduce terms
- No systematic formatting for term introduction
- Examples: Feynman, Sagan, Kahneman, Gladwell
- Common in: Popular science, self-published, conversational-style books
- Rationale: Formatting interrupts reading flow; good prose makes terms clear without typographic crutches

---

## 3. Major Style Guide Standards

### Chicago Manual of Style (CMOS)

The dominant style guide in book publishing. Its chapter on italics says:

| Topic | Rule |
|-------|------|
| Italics for emphasis | Italic is the standard way to indicate emphasis. Use sparingly. |
| Overuse of italics | "Overused, italics quickly lose their force." |
| Bold for emphasis | Italic is preferred over bold for emphasis in running text. |
| Foreign words | Italicize unfamiliar foreign words; familiar ones set roman. |
| **Key terms** | **A key term may get italics when it is first introduced but not after that.** Boldface may be used for key terms in textbook text, particularly terms that appear in a glossary. |
| Words used as words | Italic for words referred to as words ("the word *rotation* means..."). |

### APA Publication Manual (7th Edition)

- "Use italics for the first case of a new or technical term, a key term, or a label."
- "Do not use double quotation marks to highlight a key term or phrase; instead, use italics."
- APA does NOT maintain a list of technical terms -- author determines what's technical to the audience.
- Bold is for headings only, not for key terms in running text.

Sources: [APA Style Blog](https://blog.apastyle.org/apastyle/2015/04/using-italics-for-technical-or-key-terms.html), [APA Style: Use of Italics](https://apastyle.apa.org/style-grammar-guidelines/italics-quotations/italics)

### Butterick's Practical Typography

- Bold and italic are "mutually exclusive" -- do not combine them.
- Use as little as possible -- "they are tools for emphasis. But if everything is emphasized, then nothing is emphasized."
- With serif fonts: italic for gentle emphasis, bold for heavier emphasis.

Source: [Butterick's Practical Typography](https://practicaltypography.com/bold-or-italic.html)

---

## 4. Books That Show Code

This section matters only for a book that shows code or names code elements. The O'Reilly style guide is the most detailed public guide for such books; other publishers of technical books (Manning, No Starch Press, Pearson) follow the same pattern.

| Format | Used For |
|--------|----------|
| *Italic* | New terms, URLs, email addresses, filenames, file extensions |
| `Constant width` (monospace) | Program elements in text: names in the code, data types, keywords, commands |
| **`Constant width bold`** | Commands or text to be typed literally by the user |
| *`Constant width italic`* | Text that should be replaced with user-supplied values |

Key rules:
- New terms on first introduction: italic (not bold, not code font)
- Code identifiers in running text: monospace always, regardless of first vs. subsequent use
- Bold is NOT used for term introduction
- Some technical books set the names of named techniques in SMALL CAPS; that is a house style, not a general rule

Source: [O'Reilly Style Guide](https://oreillymedia.github.io/production-resources/styleguide/)

---

## 5. Popular Science / Non-Fiction Bestsellers

**This section is an impression from reading these books, not a survey.** No edition was
checked page by page, and editions differ. Before copying a house style from it, open the
book and look.

### Daniel Kahneman -- "Thinking, Fast and Slow" (2011)
- System 1 / System 2 **capitalized as proper names**, NOT italicized
- Key concepts (anchoring, availability heuristic, WYSIATI) introduced in regular text
- Italic sparingly for emphasis

### Nassim Taleb -- "Black Swan", "Antifragile"
- Coined terms (Black Swan, antifragile, Mediocristan, Extremistan) **capitalized as proper nouns**
- "Antifragile" italic when first coined/defined, then regular text
- Capitalization is the primary tool for marking coined concepts

### Malcolm Gladwell -- "The Tipping Point", "Outliers"
- Key concepts (The Law of the Few, Connectors, Mavens) **capitalized as proper names**, NOT italicized
- Storytelling carries emphasis rather than typographic signaling

### Steven Pinker -- "The Sense of Style"
- Technical linguistic terms italic on first use (academic convention)
- Key concepts italic on first use, then roman
- Advises sparing use of emphasis

### Carl Sagan and Richard Feynman
- Minimal typographic formatting for terms
- Ideas introduced entirely through prose, not typography
- Represent the "minimal formatting" school of popular science

---

## 6. The Concept Name vs. Code Name Distinction

The most important formatting distinction for technical books that discuss both concepts and code:

| Element Type | Format | Example |
|-------------|--------|---------|
| Abstract concept (first mention) | *Italic* | The idea of *crop rotation* means... |
| Abstract concept (subsequent) | Roman | Crop rotation matters because... |
| Name of a named method | Varies: *italic*, SMALL CAPS, or Capitalized | The *three sisters* method / the THREE SISTERS method |
| Code identifier | `Code font` always | The `Planting` record holds... |
| Code identifier in running text | `Code font` always | Call the `execute()` method |
| Concept that is also a code name | Depends on which is meant | *Italic* for the idea, `monospace` for the name in the code (Rule 9.7) |

The key rule: **context determines format**. When discussing the abstract concept, use italic (first mention) or roman. When discussing the actual code artifact, use code font.

---

## 7. Consolidated Formatting Rules

### Italic Uses

| Use Case | Convention | Authority |
|----------|-----------|-----------|
| New term, first introduction | Italic on first use, roman thereafter | CMOS, APA, O'Reilly, Microsoft, Google |
| Foreign words | Italic on first use if unfamiliar | CMOS, APA |
| Words used as words | Italic | CMOS, APA |
| Emphasis | Italic (use sparingly) | CMOS, Butterick |
| Book/work titles | Italic | Universal |
| Scientific names (genus/species) | Italic | CMOS |

### Bold Uses

| Use Case | Convention | Authority |
|----------|-----------|-----------|
| Key terms in textbooks with glossary | Bold on first use | CMOS |
| UI elements | Bold | Microsoft, Google |
| Run-in headings | Bold | CMOS, Google |
| Term introduction in trade non-fiction | NOT bold (use italic instead) | CMOS, all major publishers |

### Code Font / Monospace Uses

| Use Case | Convention | Authority |
|----------|-----------|-----------|
| Class names in running text | Code font always | O'Reilly, Google, Microsoft |
| Method/function names | Code font always | O'Reilly, Google, Microsoft |
| Variable names | Code font always | O'Reilly, Google, Microsoft |
| Keywords, statements, data types | Code font always | O'Reilly, Google, Microsoft |
| Filenames, paths | Code font (some use italic) | O'Reilly, Google |

### Quotation Marks Around Terms

| Use Case | Convention | Authority |
|----------|-----------|-----------|
| Ironic or non-standard usage (scare quotes) | Quotation marks | CMOS, SBL |
| Term definition | Do NOT use quotes (use italic) | APA explicitly, CMOS implicitly |
| Slang or colloquial usage | Quotation marks | CMOS |
| "So-called X" | Neither italic nor quotes needed | CMOS |

---

## 8. What NOT to Do

1. **Do not bold new terms in running text** -- unless writing a textbook with a glossary
2. **Do not use quotation marks to introduce new terms being defined** -- use italics instead (APA, Google, Microsoft explicit)
3. **Do not italicize after first use** -- the term reverts to roman
4. **Do not combine bold and italic** on the same element
5. **Do not over-format** -- "if everything is emphasized, then nothing is emphasized" (Butterick)

---

## 9. When the book is built with LaTeX

The LaTeX community strongly recommends semantic markup:

```latex
\newcommand{\newterm}[1]{\emph{#1}}        % First use of a defined term
\newcommand{\code}[1]{\texttt{#1}}         % Inline code
% \emph{} for general emphasis (built-in)
% Book titles: use \emph{} or \textit{}
```

The semantic `\newterm` command separates intent from presentation: if you later decide to add index entries, change visual style, or generate a glossary, you modify one command.

`\emph{}` is preferred over `\textit{}` because it carries semantic meaning and toggles correctly inside already-italic text.

---

## Sources

### Style Guides
- [Chicago Manual of Style FAQ](https://www.chicagomanualofstyle.org/qanda/data/faq/topics/ItalicsandQuotationMarks.html)
- [APA Style: Use of Italics](https://apastyle.apa.org/style-grammar-guidelines/italics-quotations/italics)
- [APA Blog: Technical Terms](https://blog.apastyle.org/apastyle/2015/04/using-italics-for-technical-or-key-terms.html)
- [Google Developer Documentation Style Guide](https://developers.google.com/style/text-formatting)
- [Microsoft Text Formatting Guidelines](https://learn.microsoft.com/en-us/contribute/content/text-formatting-guidelines)
- [Butterick's Practical Typography: Bold or Italic](https://practicaltypography.com/bold-or-italic.html)
- [SBL Handbook: Italics or Scare Quotes?](https://sblhs2.com/2016/09/15/italics-scare-quotes/)

### Publisher Guides
- [O'Reilly Style Guide](https://oreillymedia.github.io/production-resources/styleguide/)

### Typography
- [PerfectIt: 14 Places CMOS Asks for Italics](https://www.perfectit.com/blog/you-want-italics-where-14-places-the-chicago-manual-of-style-asks-for-italics/)
- [Daily Writing Tips: Functions of Boldface](https://www.dailywritingtips.com/the-functions-of-boldface/)

## What the writing rules take from this

- New term: *italic* at its formal definition, roman afterwards (not at earlier preview
  mentions; a compound whose adjective is already introduced needs no italic; background terms
  of the field stay plain).
- Code identifiers: `monospace` on every occurrence.
- Concept versus code artifact: italic (first) or roman for the idea, monospace for the code.
- No bold in running text; no quotation marks to define a term.
- A definition blockquote may open with the term in bold as the book's own convention; then
  `definition-check.py` keeps every bolded term traceable to the glossary.
