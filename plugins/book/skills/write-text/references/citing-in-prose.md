# Citing in prose: naming authors and works in running text

How a book names other books, papers and people inside its sentences. The names and titles in
the examples are invented. The format of citation keys and of the entries in the book's `.bib`
file belongs to the check-facts skill; this file is about the citation marks in the text and the
prose around them. Rules 2.7, 2.9 and 2.16 apply.

## How a citation is written: pandoc citations

The book cites with pandoc citations. The key is the key of an entry in the book's `.bib` file
(`sources.bibliography`, default `sources/references.bib`); the build turns each mark into the
book's citation style (`sources.citation_style`: `alpha` prints `[Abc99]`, `numeric` prints
`[1]`) and fills the references page from the `.bib` file.

| Written in the manuscript | What it means |
|---|---|
| `[@Abc99]` | one source |
| `[@Abc99; @Def01]` | two sources, in one pair of brackets, separated by `;` |
| `[@Abc99, p. 12]` | a source with a locator: `p.`, `pp.`, `ch.`, `sec.` after a comma |
| `[see @Abc99, ch. 2; @Def01]` | words before a key (a prefix) and a locator, per source |
| `@Abc99 says ...` | a narrative citation: the key stands in the sentence, with no brackets |
| `[-@Abc99]` | the year or label only, when the author is already named in the sentence |
| `@{Wal--}` | a key in braces, for a key the bare form cannot hold |

**Which keys need braces.** A bare key (`@Key`) is letters, digits and `_`, and may hold the
characters `: . # $ % & - + ? < > ~ /` only when a letter, a digit or `_` follows them (checked
with pandoc 3.8.3). So `@ABC+99` and `@Abc99a` work bare, and a key that ends in such a
character must be written in braces: a key with no year ends in `--`, so it is always
`@{Wal--}` and `[@{Wal--}, p. 3]`. Braces are always allowed: `@{Abc99}` is the same as
`@Abc99`.

**What is not a citation.** An `@` right after a letter, a digit, `.` or `\` is not a citation,
so an e-mail address (`name@example.org`) stays text. The build also reads a bare web address
(`https://example.org/@name/post`) and an e-mail-like word (`x_@Key`, `a-@Key`) as links, not
citations, while `-@Key`, `/@Key` and `_@Key` with nothing before them still cite. An `@` inside code (a code span or a code
block) is never a citation. The page that holds the references is only its heading and an empty
pandoc div, which the build fills:

```
# References

::: {#refs}
:::
```

Never type a reference entry by hand into that page. A source's authors, title, year and
identifiers live in its `.bib` entry; where to read it (links, the library copy) lives in the
sources list (`sources.list`).

## Two systems

| System | In the text | Common in |
|---|---|---|
| IEEE | [1], [2, p. 7] | computer science papers, engineering |
| APA | (Author, Year) | social sciences |
| Chicago notes | superscript numbers with footnotes | humanities |
| Chicago author-date | (Author Year) | sciences |
| BibTeX alpha | [Abc99], [ABCD99], [ABC+99] (written `[@Abc99]`) | academic computer science books |

Practitioner books mix a formal key with narrative mentions woven into the sentence. The key
says where the idea lives; the narrative carries authority and flow.

## Patterns for weaving a source into a sentence

| Pattern | Shape | Use |
|---|---|---|
| A. Author + title + verb | "Alex Doe, in *The Patient Garden*, argues that ..." | first mention with a quotation to follow |
| B. Title as subject | "*The Patient Garden* argues that ..." | when the work is better known than its author, or the idea is the work's thesis |
| C. Author as subject | "Doe argues that ..." | the main pattern when the author's authority matters |
| D. Parenthetical | "... (Doe, *The Patient Garden*)" | a light touch after the idea |
| E. "According to" | "According to Doe, ..." | rarely: it creates distance, and when the name is only decoration it can go |
| F. "As X writes" | "As Doe writes, '...'" | conversational flow around a quotation |

Prefer C and F for flow, B for iconic works, A before a direct quotation. Keep the key with the
narrative mention: "Doe [@Doe19] showed ...". Do not open a sentence with a key alone
("[@Abc99] says ..." or "@Abc99 says ..." when the style prints only a label) and do not mix
numbered and narrative citations in one sentence.

An authority phrase is only worth keeping when the authority carries the claim. Test it by
removing the name and the phrase ("X showed that"): if the sentence still stands on its data,
quote or logic, the name is decoration and may go; if it now reads as a bare claim, the name is
load-bearing and needs a proper introduction (Rule 2.7, `${CLAUDE_PLUGIN_ROOT}/skills/review-text/references/hard-words.md`, Step 5).

## Signal verbs by stance

- Neutral: writes, states, notes, observes, describes, explains, reports
- Arguing: argues, contends, asserts, claims, maintains, emphasizes
- Proposing: suggests, proposes, recommends, advocates, urges
- Analysing: analyses, examines, explores, investigates, evaluates
- Agreeing: confirms, agrees, supports, acknowledges, endorses
- Disagreeing: challenges, disputes, questions, criticizes, rejects, refutes
- Cautioning: warns, cautions, advises against

Choose the verb that matches what the source actually does. "Shows" and "proves" claim more
than "argues" and "suggests"; match the verb to the evidence (Rule 4.12).

## Titles and names

- Book titles in *italics*, title case. Article and chapter titles in "quotation marks", title
  case. An edition marker only when it matters: *The Patient Garden* (2nd ed.).
- First mention: the full name (and title where it matters). Later mentions: per the `## Names`
  section of the voice profile; the default is the surname or the title alone ("Doe also ...",
  "*The Patient Garden* also ..."), with the full name again after a long gap (Rule 2.7).
- Three or more authors: first author plus "et al." ("Okafor et al. describe ...").
- A well-known short form ("the Harrow report") only after the full form has been given.

## The citation key in print

The build sets the printed mark; these are the rules it follows. Set the bracketed key in the
body face, roman, at body size. A bracketed mark does not take on
the formatting of the text around it. Do not italicize it: italic usually means a title, and an
italic key reads as a title fragment. Do not give keys a font of their own. If keys ever need
to stand apart, a slightly smaller bracket applied in the build is the smallest change; the
default is to leave them as body text.

## Multiple sources

Group keys inside one pair of brackets, separated by semicolons: "... [@Abc99; @Def01]". The
build prints them as one mark ("[Abc99, Def01]"). Never write adjacent brackets
("[@Abc99][@Def01]").

## Representing a position the book disagrees with

A book that argues for one position must state the positions it displaces in their strongest
form, with the same care it gives its own: dated, quoted word for word from the primary source,
cited to the originator. A displaced position stated from memory, from a secondary summary or in
its weakest form makes the whole argument look like a straw man, and outside reviewers find
these first. Before rejecting a position, check that the sentence you reject is one its author
actually wrote.

Say which claims rest on evidence and which on the author's experience and judgment. Both are
legitimate; readers need to know which is which.

## Sources

O'Reilly style guide; Purdue OWL (in-text citations); *Technical Writing Essentials*
(referring to authors and titles); Chicago Manual of Style citation guide; IEEE citation guide;
Butterick, *Typography for Lawyers* (brackets take the formatting of the text outside them);
the pandoc manual, "Citation syntax".
