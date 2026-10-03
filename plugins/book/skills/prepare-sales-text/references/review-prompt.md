# Ready-to-run review prompt

For a cold subagent reviewing the selling copy. Give it this prompt with the placeholders filled,
one lens per subagent (the lens text from `copy-review.md`), and no edit history. The
orchestrator merges the answers; subagents never see each other's findings.

Fill every `<PATH OF key>` with the path `sales-text-files.py` printed for that key, as an
absolute path. When the file is missing, write `(missing: key)` in its place, so the subagent
knows what it did not get and says so in its report. `${CLAUDE_PLUGIN_ROOT}` is the plugin
folder; write it out in full.

```
You are reviewing the selling copy of a book: the back cover, the store description and the
ebook description. I want a rigorous, honest review, not encouragement. If a surface is a 6
that thinks it is an 8, say so.

Your lens: <LENS NAME AND TEXT from copy-review.md>

Read these before writing one finding:
- ${CLAUDE_PLUGIN_ROOT}/skills/prepare-sales-text/references/copy-review.md
    (the lenses, cover rules C1-C3, the output format)
- ${CLAUDE_PLUGIN_ROOT}/skills/prepare-sales-text/references/rules-transfer.md
    (which writing rules apply, are off, or turn around)
- ${CLAUDE_PLUGIN_ROOT}/skills/prepare-sales-text/references/marketing-evidence.md and
  emphasis-evidence.md (graded evidence)
- <PATH OF rules.decisions>                (decided items are NOT findings)
- <PATH OF sales_text.intended_impression> and <PATH OF thinking.audience>
- <PATH OF rules.glossary>            (check every defined term the copy uses)
- <PATH OF sales_text.keywords>             (the category evidence)
If a line above says "(missing: ...)", say at the top of your report that you reviewed
without that file.

The surfaces, exactly as they are now (read nothing else about them):
<OUTPUT OF copy-stats.py --text>
<OUTPUT OF sync-check.py>

Rules of engagement:
- A decided item is not a finding. If your finding contradicts an entry in the decisions file, say
  so in one sentence, cite the entry id, and stop. Do not argue it again.
- Trust the surfaces above over any prose about them. Quote only text that appears above.
- No conversion evidence. No published randomised test of description wording against purchase
  exists; category conventions are descriptive, never an optimisation target.
- Lean only on evidence with a source and a grade. Where the book has its own fact-checked
  research on a point, it outranks marketing claims.
- Separate what the copy says from what the book can back. Say which chapter or section
  proves a claim, or that none does.
- If you cannot verify something, write "not verified". Never estimate a number.
- Report in the output format of copy-review.md, and end with a score out of 10 per surface
  and the reason.
```

After the subagents return, the orchestrator:

1. runs `python3 ${CLAUDE_PLUGIN_ROOT}/lib/decisions.py match --text-file F` on every finding and drops or relabels matches as the decision
   policy says;
2. merges duplicates across lenses, keeping the strictest severity and every lens id;
3. shows the author the ranked list with full-sentence suggestions, changed words in bold;
4. applies nothing until the author approves each item.
