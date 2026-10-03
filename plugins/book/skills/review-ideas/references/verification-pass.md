# Verification pass

The last step of a full review. Every finding that Stage 3 classified VALID-Critical or
VALID-Significant is checked again, against primary material, by a verifier that has not seen the
earlier stages' reasoning.

## Why the pass exists

Each stage can be wrong in both directions. Stage 2 reads an abstract and reports a paper
backwards; it reads a sentence without the clause that scopes it; Stage 3 upholds a finding by
trusting Stage 2's summary instead of pulling the source. A "verified" Significant finding can
fail against the primary source, and acting on it would put an error into the book. So:

**A finding survives only if the verifier reproduces it, independently, from primary material.**
A finding that cannot be reproduced is overturned, however confident the earlier stage was.

## How the main agent runs it

1. Collect the VALID-Critical and VALID-Significant findings from `stage-3-judge.md`.
2. Group them by chapter (a finding that spans chapters goes with the chapter it starts in). One
   verifier subagent per group; run the groups in parallel.
3. Give each verifier only: the accusation in one or two sentences (in its own words, not
   Stage 2's argument), its chapter and section, the paths of the manuscript files, the
   bibliography, and the read-only source paths (`sources.library`, `sources.list`,
   `sources.quotes` from the book's config). Never give it `stage-1-map.md`,
   `stage-2-attack.md` or `stage-3-judge.md`, and never the book's notes or plans. The book is
   judged as it stands.
4. Each verifier writes one file: `<run>/verification/<group>.md`.
5. The main agent writes `<run>/verification/summary.md`: counts per verdict, then one table per
   verdict (ID, location, what survives or why it fails), then the prongs overturned inside
   surviving findings.

## The verifier's protocol

You are an independent verifier. You are not re-running the review; you are auditing specific
accusations.

### Step 1: read the whole chapter, not the cited section

Read the entire chapter file, start to finish, before judging any finding in it. Most false
positives come from reading a sentence without its surroundings. Check whether:

- the caveat the finding says is missing appears elsewhere in the chapter
- a later section reconciles what an earlier one seemed to contradict
- the sentence has a scoping clause the finding dropped
- the book states the objection itself and answers it somewhere you were not pointed at

Then search the other chapters for the same claim before concluding the book never addresses
something. Reconciliation across chapters is common.

### Step 2: read sources from the local cache, in full

Use the book's cached sources before any web search, read-only:

- cached files: `sources.library` (`<Key>.txt`, `.pdf`, `.html`)
- identity and access of each source: `sources.list`
- what each source says, as verbatim quotes with scope and guardrails: `sources.quotes`. A
  guardrail there is evidence, never authority: where it and the source disagree, the source wins.

Rules:

- **Never judge a paper from its abstract.** Read the results and the discussion. An abstract
  can contradict the paper's own methods.
- **OCR text is a search index, never wording.** A `.txt` made by OCR (it has an OCR provenance
  header or record) guesses characters. Confirm every quote and every digit against the page image
  in the `.pdf` ("224 ms" and "22A ms" are one glyph apart). A scan can carry someone else's OCR
  in its text layer with nothing announcing it, so treat odd character errors as an OCR signal.
- If a source is not cached, search the web, and say in the verdict that the source was not held
  locally and what you actually read.
- Say what you read for every source: full text, OCR, page image, or abstract, and why.

### Step 3: judge

For each finding, write:

```
## <ID>: <VERDICT>

**The accusation:** <one sentence, in your own words>
**What the chapter actually says:** <verbatim quote, with file:line>
**What the source actually says:** <verbatim quote, with the file you read and where in it;
   say whether you read full text, OCR, a page image or an abstract>
**Reasoning:** <why the accusation holds or fails>
**Verdict:** UPHELD | UPHELD-BUT-NARROWER | OVERTURNED | UNRESOLVED
**Severity if upheld:** Critical | Significant | Minor
**Smallest fix:** <the smallest edit that closes it, or "none needed">
```

- **UPHELD**: you reproduced the problem independently. The author should act.
- **UPHELD-BUT-NARROWER**: something real is there, but smaller or different than stated. Say
  exactly what survives and what does not.
- **OVERTURNED**: the finding is wrong. Say what the earlier stage misread.
- **UNRESOLVED**: you could not get the evidence to decide. Say what would settle it. A guess
  dressed as a verdict is worse than an open question.

### Rules

- **Quote, do not characterise.** Every claim about what the book or a source says carries a
  verbatim quote and a locator.
- **Overturning is a success.** You are not expected to find problems. If every finding is
  wrong, say so.
- **Run the false-positive screens** in [false-positives.md](false-positives.md), FP-4 and FP-6
  above all.
- **Prose style is out of scope.** Content, argument and factual accuracy only.
- **Read-only.** Do not edit the manuscript, the source banks or the cache. You write one report
  file and nothing else.
