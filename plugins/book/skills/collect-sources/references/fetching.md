# Finding and fetching a source

Search is for finding the URL; it is never verification. Snippets paraphrase, round, and merge
papers with similar titles by the same authors, so a claim confirmed only by a search result is
not confirmed. Every source found is fetched into the cache with `fetch.py`.

## The ladder, in order

1. **The cache.** Grep the list; if `Cached text` exists, read it. Where the extraction is
   ambiguous, open the cached original, not the network.
2. **The list's URLs.** `fetch.py --keys <Key>` reads them. Skip entries marked `MANUAL FETCH
   REQUIRED` or `NO OPEN-ACCESS COPY` and report them as not read.
3. **The bibliography**, to decode the key into authors and title before searching.
4. **The book's own notes** (`thinking.argument`) and the quotes bank: faster than a web search, and they
   often hold exactly the verification needed. Treat them as pointers, not proof.
5. **Web search with `filetype:pdf` first**, then a plain search. A plain search ranks landing
   pages, paywalls and aggregators; `filetype:pdf` finds the document: author copies, course
   pages, repositories, proceedings, and papers that cite and quote the target. A paper recorded
   as having no open copy can still turn up this way, for example on a course page.
6. **Secondary citation.** If the original is truly unreachable, find works that quote the same
   passage. Several independent works quoting it identically is moderate evidence. Record every URL.
7. **General knowledge**, last, and said plainly: "not verified against the source". If the
   book's notes were written with a language model, the same training data may have produced both
   the claim and the "verification": that is circular, not a check.

## When the fetch tool is refused, try curl

A browsing tool can refuse a domain for its own safety reasons while a plain shell fetch works.
`fetch.py` already runs the ladder (plain fetch, then HTTP/1.1 with a browser User-Agent) and
keeps the bytes. The raw commands, for diagnosing a URL `fetch.py` reports as `failed` or
`blocked`:

```bash
curl -sSL --max-time 45 -o out.pdf -w 'http=%{http_code} bytes=%{size_download} type=%{content_type}\n' <url>
curl -sSL --http1.1 --max-time 45 -A 'Mozilla/5.0 (X11; Linux x86_64) Chrome/124.0' \
  -o out.pdf -w 'http=%{http_code} bytes=%{size_download} type=%{content_type}\n' <url>
```

Check `bytes` and `type`: a 200 of a few kilobytes of `text/html` is a check page, not the paper.
Whatever works goes back through `fetch.py --key <Key> --url <URL>` so the bytes are kept.

## When curl is blocked too, look for the site's API

A small 403 titled "Just a moment..." is a bot check. Many sites have an open API that serves the
same content: Wikipedia and other wikis (the MediaWiki API), the Internet Archive, many museum,
library and archive collections, and question-and-answer sites (for example Stack Exchange).
Look for the site's API page before giving up. A Wikipedia article, for example:

```bash
curl -sSL --compressed 'https://en.wikipedia.org/w/api.php?action=parse&page=<Title>&prop=wikitext&format=json'
```

Cite a forum or question-and-answer thread by crediting both parties when the claim spans them
(key it to the asker, name the answerer in the entry), and record the date, score and view count:
for a source with no review those are the only quality signals. Note the licence of the content
(wiki and question-and-answer text is often CC BY-SA), which matters for a printed book.

## When every index says closed, list the author's own files

Unpaywall, Semantic Scholar and OpenAlex report only what they index, and none indexes an
unlinked folder on a lab's web host. Enumerate the host through the Wayback CDX index and match
file names:

```bash
curl -s 'http://web.archive.org/cdx/search/cdx?url=<host>*&fl=original&collapse=urlkey&filter=original:.*\.pdf$&limit=3000'
```

This finds live-but-unlinked upload folders, dead older folders reachable only through Wayback,
papers you did not know to ask for, and hosts that are gone. Then two checks, because a file name
is not identity: read page 1 to confirm it is the paper, and note whether it is the version of
record or an author manuscript (fine to cite from, but its page numbers are not the published
ones; say so in the entry).

## When the wall is a check for a person, stop and hand it over

Some hosts show a checkbox meant for a person; a real browser does not help. **Do not engineer
around it**: no stealth plugins, no borrowed browser profiles. A pipeline that defeats checks for
people is not one whose provenance anyone should trust. Free and fetchable are different things:
a large open archive can still answer every script with a 403. Record which wall it is:

- `MANUAL FETCH REQUIRED (gate)`: free, but gated. `Access URLs` holds the direct link; `Cached
  text` holds `NOT YET FETCHED -- save the PDF above as <path>`. No sha256 before the file exists.
- `NO OPEN-ACCESS COPY`: checked, nothing free anywhere; needs a library.

Then `manual-downloads.py --fix` writes `<sources.to_add>/needed.txt`; point the author at it.
The author saves each file into that folder under any name, and `match-added-files.py` files it
under its key at the start of the next download run. Entries drop off the list once
cached. **Check Unpaywall before concluding anything is unreachable** (free, with an email
parameter):

```bash
curl -s "https://api.unpaywall.org/v2/<DOI>?email=<address>" | python3 -m json.tool | grep -A5 best_oa_location
```

## A paywalled paper of record: exhaust the routes, then ask

A preprint standing in for a paywalled paper can be a fine outcome, but it is **the author's
decision, never an agent's**: the author may have access, or may buy the paper.

1. **Exhaust the free routes**: the DOI, Unpaywall, PubMed Central, Europe PMC, the publisher's
   own PDF path, the author's institutional or personal page, the accepted manuscript in a
   repository, a `filetype:pdf` search on the exact title and surnames.
2. **If it is still unreachable, stop and surface it**: set the Access status, record the
   evidence (HTTP codes, Unpaywall `oa_status`, mirrors tried), put it on the download list. Do
   not substitute the preprint and do not report the claim verified.
3. **Ask plainly**: "the published version of X is behind a paywall; I tried these routes; can
   you reach it, do you want to buy it, or shall we cite the preprint?"
4. **If the author settles on the preprint**, the entry says verification was done against the
   preprint only, so a later run can see the paper of record was never read.

A subagent's job ends at reporting the wall with its evidence.

## No citation without a held source

The book must not carry a `[Key]` for a work nobody can produce. `NO OPEN-ACCESS COPY` or `NOT
CACHED` is not a permanent excuse: find an obtainable replacement (a later work by the same
originator stating the same idea counts), or reword the sentence so it makes no attributed claim.
An uncacheable citation reads as verified to every later check while nothing stands behind it.
Split by kind:

- **books and papers**: a replacement hunt;
- **videos and recorded talks**: ask the author for a transcript. Caption endpoints that return
  nothing or ask for a login are a check for a person, not something to engineer around. An
  automatic transcript is a search index, never wording authority: confirm a quote by ear at the
  timestamp. (`fetch.py` does not cache audio, so a talk's recording cannot be cached by script.)
- **slide decks on sharing sites**: ask the author to download the file.

## Link checks

`link-check.py` holds every URL in the bibliography and the list to what it resolves to today.
It is the only check whose answer lives on the network, so run it before a build that readers
will click through, not on every edit. Key rules: for a `doi.org` URL the authority is doi.org's
own redirect, never the publisher's answer to an anonymous client (a registered DOI whose landing
page 403s or 404s is not dead); a transport failure is never `dead` (an intercepting proxy can
answer every blocked host with one identical page); `bank-drift` is a failing bibliography URL
while the list already holds a working one. `--fix` writes only what the run verified, and never
touches a `Cached original` line, which records where bytes came from.
