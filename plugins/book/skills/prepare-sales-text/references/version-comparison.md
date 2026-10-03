# Comparing versions of the copy

Use this when a surface has two or more candidate versions and the author must choose one, or
when a new version replaces the shipping one. The output is a working document for ONE
decision; the decision itself goes to the decisions file, and the losing texts are not kept in the
book (the author's backups and git history hold them).

## The working document

Put it in the review's run folder (`<work.runs>/<YYYY-MM-DD-HHMM>-prepare-sales-text-review/`, as `<surface>-versions.md`), not in the
sales-text folder (`publishing.sales_text`). It holds:

1. **A table of the versions**: letter, word count, longest block, one line on what it is, and
   which one ships. Every number comes from `copy-stats.py` on that version, never from memory.
   Add the category's measured range for the surface (from the keywords file, `sales_text.keywords`) as a
   fact, not a target.
2. **Each version in full**, with the bold and italic spans marked, as it would render.
3. **The scan path of each version**: the bold spans read alone. Each must be a complete
   sentence that does not open on a pronoun, and the path must carry the pitch.
4. **A word-level diff** of each version against the shipping one (`copy-diff.py OLD NEW`, and
   `--markdown` for the form to show the author).
5. **"What separates them"**: the one or two differences the choice really turns on. Usually one
   sentence or one span decides it; name it.
6. **"Why <version> exists"** for every version after the first: what it fixes, with the reason
   for each change, and what it deliberately drops.
7. **"Considered and not taken"**: every alternative wording that was drafted and rejected, with
   the reason. This is the list that stops the same wording coming back next month.
8. **"What it still does not fix"**: known costs, and which of them are decided items.
9. **A score out of 10 per version with the reason**, from the ten lenses. Say what keeps it from
   the next point. Scores from different sessions are not comparable; re-score all versions in
   one pass.

## Rules

- **Measure every figure.** Word counts from the source; wrap, widows and empty space from the
  rendered image. A figure carried over from an older version's notes is marked "not
  re-measured".
- **Rewrite, do not patch a patch.** If a version needs a third round of small fixes on the same
  span, write the span again from its job.
- **A minimal change stays minimal.** When the author asks for one change, the new version
  differs from the old in that change only; everything else waits for a separate proposal.
- **Things that went missing by accident are recorded as such.** When a sentence disappears
  during drafting without a decision, say so, so it is not later defended as a choice.
- **Show before applying.** The author sees the full text of the chosen version with the
  changed words in bold, and approves it, before any file changes. Apply the approved wording
  exactly; raise a flaw found while applying as a question.
- **When the version is applied**, run `sync-check.py` so the other surfaces are checked against it, and
  propose `decisions.md` entries for everything in "considered and not taken" that the author
  wants kept out.
