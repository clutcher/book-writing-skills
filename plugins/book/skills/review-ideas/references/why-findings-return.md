# Why the same findings keep coming back

Five causes, each seen across many review runs. Each one has a rule in this skill that stops it.

1. **Findings are keyed by run-local ids.** The same idea is `R2-4` in one review, `N.12` in the
   reading notes and `IC-1` in another run. Nothing joins them, so each run finds it again.
   *Rule:* every run matches its findings against `decisions.md` (by alias, then by keyword)
   before Stage 3, and a new entry records every id the idea has had.
2. **Reviews read the flagged sentence, not the structure around it.** The disproof is usually a
   qualifier nearby: a clause one sentence later, a limit set in the same sentence, a split between
   two Parts one chapter away. *Rule:* FP-4 and the three-location check.
3. **Attribution is inferred from adjacency.** An author cited in one chapter is assumed to back a
   claim in the next. The disproof is one search of the citation list. *Rule:* FP-4 (the unit that
   governs an attribution is the chapter's citation list).
4. **Runs propose the option that was already rejected.** The reasoning that rejected it lives in a
   note the run never reads, so the strongest-looking fix is often the one already ruled out.
   *Rule:* FP-11; a decision entry names every rejected option in its `Why` field.
5. **Fixes are applied to the flagged sentence only.** The sweep corrects the cited line and leaves
   the same defect one line away, or applies one half of a two-part fix. *Rule:* when a finding is
   fixed, search the whole book for the same defect class, not just the reported location; and
   when checking an old fix, search for the concern, not the prescribed wording (FP-10).
