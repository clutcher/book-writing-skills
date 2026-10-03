# Sources List

Where to read each source the book cites: identity and access only. What a source says goes to
`{{quotes}}`; a verdict about the book goes to a dated run folder, never here. The check-facts and
collect-sources skills read and write this file; its rules are in list-format.md of the check-facts skill.

## Entry format

```
### [<Key>] Author, "Short Title" (Year)

**Full title:** the exact title of the work
**Authors:** the full author list
**Year:** the year of the printing read (and the basis, for a web page)
**Edition:** which printing this is, and how it relates to another entry
**Venue:** journal, conference, publisher or platform
**Publisher:** when Venue carries something else
**DOI:** a bare DOI, the permanent identifier
**ISBN:** 13 digits, no hyphens
**Identifier:** an LCCN or OCLC number, for a work older than ISBNs
**DOI/URL:** the canonical landing page (a URL or a DOI, never a citation string)
**Access URLs:** where the source can be read: full text, abstract, mirrors
**Access status:** present only when something blocks or qualifies the reading
**Cached text:** `{{files}}/<Key>.txt` (fetched <date>, sha256 <hash>)
**Cached original:** `{{files}}/<Key>.pdf` (fetched <date>, sha256 <hash>, from <URL>)
**Record history:** key renames and corrections to this entry's own identity fields
**Fetch note:** dead hosts, bot checks, extraction traps, what the cache really holds
**Note:** anything else durable: naming traps, attribution cautions, why an uncited source is kept
**Findings:** see `{{quotes}}`
```

Only Full title, Authors and Year are required; every other field appears when it applies.
One `---` line, with a blank line on each side, comes before every entry.
