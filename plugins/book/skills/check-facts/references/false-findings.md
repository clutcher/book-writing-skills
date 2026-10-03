# Before applying a finding: verify it yourself

**Never apply a fact-check or review finding without re-reading the cached source yourself.** A
report is one agent's reading, and its confidence does not survive a second look. Some findings
do not survive verification, and some would make the book worse if applied: a correct citation moved onto a source that does not support it, a figure
narrowed until it is less accurate than before.

## Where false findings come from

- **Two similar cached files transposed**: the claim is in the other file, which the book already
  cites.
- **A grep the extraction defeated**: letterspacing, column interleave, line-break hyphenation
  ("con- structed"). Strip whitespace entirely, not merely normalise it, before concluding a term
  is absent. See `${CLAUDE_PLUGIN_ROOT}/skills/collect-sources/references/extraction-traps.md`.
- **Judging a paper from its abstract.** Read the results and the discussion. A paper can report a
  headline figure for one measure while the book's sentence is about another, where the paper found
  the opposite.
- **A paper can contradict its own abstract.** The methods section decides: an abstract can say
  "perceived" where the methods switch to measured data.
- **The accused sentence may BE the source's doctrine.** Before accepting that the book contradicts
  a source, check whether the sentence states the source's own rule.
- **The cache is not always the source.** A page of notes over a recording, an abstract, minutes,
  a transcript: a quote of the speaker cannot be refuted from someone else's notes. Check what
  artifact the cache is before calling a quote misattributed.
- **Scale.** Many findings that survive shrink: "nearly every X in the book" turns out to be eight;
  "no upper bound" ignores one stated two sections earlier. Ask what the finding claims about HOW
  MUCH before agreeing there is a problem.

## A confirmed finding still needs a second question

**Does the corrected fact refute the ARGUMENT, or only the EVIDENCE for it?** These call for
opposite repairs, and getting it backwards breaks a section. Read the paragraphs the passage
feeds before rewriting it, and **prefer a repair that keeps the claim and swaps the evidence**
when the claim still stands.

## How to work

1. For every finding, open `<sources.library>/<Key>.txt` (and the original where the text is
   doubtful) and confirm the quote or figure yourself before drafting a change.
2. If the source is not cached or is only an abstract, say so in the proposal rather than trusting
   the report.
3. Show the author the full sentence with the changed words marked, say whether the words are a
   quote or the book's own, and say what you verified. Apply only after the author agrees.
4. When a finding is dropped, record it as WITHDRAWN in the run report. When it could be raised
   again, write a note that suggests a decision ("Suggested decision: not a finding, because ..."),
   so revise-from-notes can record it and no later run derives it again.
