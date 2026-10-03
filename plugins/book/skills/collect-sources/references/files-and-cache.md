# The cache of source files

## What the cache holds

For each citation key, in the book's `sources.library` folder:

| File | What it is |
|---|---|
| `<Key>.pdf` / `.html` / `.src.txt` | the **original** bytes as served |
| `<Key>.txt` | the **extraction**: `pdftotext -layout` output, or HTML reduced to text |
| `<Key>.layout.txt` | optional second extraction, when both modes are kept |

and an **origin record** for each key: what `fetch.py` requested and got (URL, HTTP status,
content type, both sha256 hashes, or the reason a fetch was rejected with a 300-character
sample), and, for an OCR text, the engine, dpi and pages. The records live in one file per key,
`<sources.library_index>/<Key>.json` = `{"fetch": {...}, "ocr": {...}}`; the origin folder is
tracked in git while `sources.library` is not. When `sources.library_index` is the same folder as
`sources.library`, or a bare folder is given to a script, the records are
`<Key>.fetch.json` and `<Key>.ocr.json` beside the cached files.

Every script reads both, through `${CLAUDE_PLUGIN_ROOT}/lib/source_files.py`. A cache line in the list names its
file as `<folder>/<name>`; the folder is the book's `sources.library` path relative to the book
root. In a book that keeps its library in its own folder, a line written with the default folder
(`sources/library`) still resolves, and `entry-format-fix.py --fix` rewrites it to the configured
folder.

Both files are required. Text extraction is lossy: it loses table structure, drops captions,
merges two-column layouts, and mangles ligatures and maths. When a later run disputes a quote,
the extraction is evidence about the extraction; only the original settles it.

## Why the cache exists

1. **Content drift is a finding.** A URL can keep resolving while what it serves changes under
   the citation. Without a snapshot that is invisible; with one, the hash mismatch shows it.
2. **Reproducibility.** A verified quote means little if nobody can see the bytes it was verified
   against.
3. **Work does not evaporate.** An agent that downloads a paper, reads it and moves on charges
   the next run the whole download again, and leaves a verdict nobody can re-examine.
4. **Cost.** Later check-facts runs read the cache instead of the network.

## The cache rule

**Any work that opens a source writes that source into the cache, through `fetch.py`. This binds
subagents exactly as it binds the main agent.**

1. Grep the list for the key. If `Cached text` is there, read that file: do not fetch.
2. If it is not cached, run `fetch.py --key <Key> --url <URL> --fix`, then read the file it
   wrote. Without `--fix` it only shows what it would fetch.
3. Return the `**Cached text:**` and `**Cached original:**` lines `fetch.py` printed and filed in
   the list entry, with the rest of the list data.
4. If `fetch.py` rejects the source (`paywalled`, `blocked`, `abstract-only`, `too-short`),
   report that as an attempt outcome, walk the free routes in `fetching.md`, and **never verify
   against the abstract instead**.

An agent that ends its turn having read a source that is not in the cache has not finished.
A confidence label with no cache behind it is worse than no label: it reads as verification.
The honest state of a source nobody holds is UNHELD, not "high confidence".

## Rules

- Fetch once, then read the cache. Refetch only to test whether a source changed, or when the cache is missing.
- On refetch, compare the sha256 with the list. **A mismatch is a finding in the run report**,
  never silently overwritten. Judge on the **extraction** hash: many HTML hosts embed per-request
  tokens, so two fetches of an unchanged page differ in the original and agree in the text.
- Never cache a paywalled abstract as the full text; `fetch.py` enforces this.
- A key with an extraction but no original is **incomplete**, not broken; leave it unless the
  original is needed, then `fetch.py --complete-partial --fix`.
- `fetch.py` extracts with `-layout`. That is right for tables and wrong for quoting a two-column
  paper; see `extraction-traps.md`. Storing plain text as `<Key>.txt` and layout text as
  `<Key>.layout.txt` would make quoting right by default, but it changes the cache for every key
  already held, so it is a decision for the book, not a silent change.

## fetch.py

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/scripts"
python3 $SCRIPTS/fetch.py --all                                                # dry run: what has a URL, what is cached
python3 $SCRIPTS/fetch.py --key Smi99 --url https://example.org/paper.pdf --fix  # one source
python3 $SCRIPTS/fetch.py --key Smi99 --file ~/Downloads/paper.pdf --fix         # a file a person downloaded
python3 $SCRIPTS/fetch.py --keys Smi99,Jon01 --fix                             # URLs from the list
```

Dry run by default: without `--fix` nothing is downloaded or written. With `--fix` it downloads,
writes `<Key>.<ext>`, `<Key>.txt` and the origin record, files the cache lines in the list
entry, and makes `needed.txt` again. `--dry-run` is still accepted and wins over `--fix`.

A key becomes a file name, so `fetch.py`, `ocr.py` and `match-added-files.py` accept only a key
of letters, digits and `+ _ . -` that starts with a letter or digit. Any other key (with a slash
or `..`) is refused (`unsafe-key`) and nothing is written for it; fix the heading in the list.

`fetch.py` sends a User-Agent that names this project, opens only `http` and `https` addresses
(also after a redirect), and stops a download at `--max-bytes` (default 200 MB).

| Flag | Effect |
|---|---|
| `--force` | refetch keys already complete, to test whether a source changed |
| `--complete-partial` | fetch originals for keys holding only an extraction |
| `--max N` | hard cap per run (default 25): a big list must not be swept in one pass |
| `--delay S` | seconds between requests (default 2) |
| `--tries N` | candidate URLs per key (default 3), best first |
| `--min-chars N` | reject extractions shorter than this (default 2000) |
| `--allow-short` | accept a short extraction: right for a blog post, wrong for a paper |
| `--max-bytes N` | largest download accepted (default 200 MB) |

Outcomes: `cached`, `skipped` (complete), `incomplete` (text only), `would-fetch` (dry run),
`paywalled` (401/402/403), `blocked` (a bot check: respect it, see `fetching.md`),
`abstract-only`, `too-short`, `no-url`, `unsafe-key` (the key is not a plain file name), `failed`. URLs are tried best first: direct PDFs, then arXiv and PMC, then other hosts,
with `doi.org` and the big publisher hosts last. Video sites, social posts and shop pages are
never fetched: there is no text, and caching a landing page is worse than caching nothing.

## ocr.py

`ocr.py --key <Key>` is a dry run too: it says which PDF it would read and what it would write.
`--fix` runs the OCR and writes `<Key>.txt` and the OCR origin record. It replaces an existing
`<Key>.txt`, or an existing `<Key>.pdf` with the file named by `--pdf`, only with `--force`.

## Keeping the cache out of git: restore and backup

The cache is not in git: it is large, and many files belong to publishers. The list keeps what
is needed to get each file back, and two scripts do the rest:

- **`restore.py`** rebuilds missing files after a fresh checkout: first from the private backup
  (exact bytes), then from the network (the `from <URL>` of the Cached original, then the fetch
  record, then the DOI), verifying every download against the recorded sha256. It reports what
  could not be restored and why. A download whose bytes changed is not written: that is a finding.
- **`backup.py`** copies what cannot be downloaded again into `sources.backup`, a private folder
  outside the repository: manual downloads behind a check for a person, sources with no open copy,
  books known only by ISBN, OCR texts, anything with no download route. `--all` copies everything.
  It writes a `manifest.tsv` of names and hashes.

Run `backup.py --fix` after every manual download or OCR run, and `restore.py --fix` after a
fresh checkout. `files-hash-check.py` then confirms the cache lines describe the bytes.

## Reading and writing the banks as a team

- Both banks grow large. **Do not read either whole file into context**: grep them for the keys
  in hand. Read a full bank only for the cross-citation consistency pass and the summary.
- **Subagents never write a bank.** Each returns three blocks per key it checked: list data
  (identity, access, the cache lines), quotes data (quotes, findings, scope, guardrails), and the
  run-report verdict, staged as files in `<run folder>/proposed-entries/list/` and
  `<run folder>/proposed-entries/quotes/`. The run merges them at its end
  (`${CLAUDE_PLUGIN_ROOT}/lib/proposed_entries.py --run <run folder> --fix`), which also prevents write conflicts
  between parallel agents.
- **After writing, every cited key must have a list entry.** A gap makes the next `--only-changed` run
  verify the citation from scratch. Run
  `python3 ${CLAUDE_PLUGIN_ROOT}/skills/check-facts/scripts/cited-source-check.py`: it reads the
  manuscript files and the thinking files the book config names, splits multi-key brackets, accepts
  a key that starts with a lower-case particle, and reports every cited key with no list entry
  (`not-in-list`) or with no library copy and no `needed.txt` line (`no-library-copy`). It says
  SKIPPED when the book has no sources list, so a wrong folder name cannot pass by reading nothing.
  `list-bibliography-check.py` does the join by key and also finds near-miss pairs.
