# Sources List

Where to read each source the book tracks: access only. Who wrote it, its title, year, DOI and ISBN live in its entry in `{{bibliography}}`, under the same key. What a source says goes to `{{quotes}}`; a verdict about the book goes to a dated run folder, never here. The check-facts and collect-sources skills read and write this file; its rules are in list-format.md of the check-facts skill.

## Entry format

```
### [<Key>]

**Access URLs:** where the source can be read: full text, abstract, mirrors
**Access status:** present only when something blocks or qualifies the reading
**Cached text:** `{{files}}/<Key>.txt` (fetched <date>, sha256 <hash>)
**Cached original:** `{{files}}/<Key>.pdf` (fetched <date>, sha256 <hash>, from <URL>)
**Record history:** key renames and corrections to this entry
**Supersedes:** the key this entry replaced, when a source moved to a new key
**Fetch note:** dead hosts, bot checks, extraction traps, what the cache really holds
**Note:** anything else durable: naming traps, attribution cautions, why an uncited source is kept
**Findings:** see `{{quotes}}`
```

The heading is only the key, which is also the key of the .bib entry. No field is required; each appears when it applies. One `---` line, with a blank line on each side, comes before every entry.
