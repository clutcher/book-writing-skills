# The Vale check

Run [Vale](https://vale.sh) against the manuscript to catch generic prose hygiene issues -- passive voice, weak modifiers, hedging language, cliches, wordy phrases -- that the existing Python validation scripts don't try to cover. This check complements the review-text modes: it catches surface-level token issues; the qualitative reviews (common-problems, flow, all-problems, consistency, hard-words) still own structural and cross-document analysis.

**What this check catches:** Findings from packaged styles (`write-good`, `proselint`, `alex`), the skill-owned `PlainBook` base package, and whatever vocabulary package the book supplies. Surface patterns only -- not adjacency chains, not T-D-C structure, not term-density curves.

**Style ownership.** Custom Vale rules come from two places with different owners:

- `PlainBook` is **skill-owned**: plain-English and punctuation rules that suit any book. It lives in `${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts/vale/PlainBook/`, and `vale-sync.py --fix` copies it into the book's styles folder (the `StylesPath` of the book's Vale config). Do not edit the copy in the book; edit the skill.
- Each book's **own vocabulary rules are book-owned**. They live in the book's styles folder under their own package name, are declared in the book's Vale config (`rules.vale_ini`), and the skill does not provision them. If a book-specific rule does not fire, the fix belongs in the book, not here. The book documents what its own package checks, and each rule message cites the `decisions.md` entry it guards (an id, never a chapter and line, which go stale on the next edit).
- Upstream packages (write-good, proselint, alex) are downloaded by `vale sync` into the styles folder; the book's `.gitignore` keeps them out of git.

---

## How to run it

1. **Preflight.** Docker must be available (`docker --version`). Without it the runner prints `SKIPPED` and exits 0; say that Vale did not run.
2. **Sync once, then run the wrapper** from the book folder (or pass `--book DIR` / `--config FILE`). A path may be relative to where you stand or absolute, but it must be inside the book folder; with no path it checks the manuscript.
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts/vale-run.py --output JSON manuscript/<chapter-file>.md
   ```
   `vale-run.py` never writes into the book. When the book's copy of `PlainBook` is missing or differs from the skill's, it prints `SKIPPED` and exits 0; then run `vale-sync.py` (a dry run that says what it would copy) and, after the author agrees, `vale-sync.py --fix` (copies `PlainBook`, then `vale sync` for upstream packages). The image is `tools.vale_image` in the book config, pinned to a tag, and writes files as your user (on Linux it runs with your user id), so nothing it writes is owned by root. The Vale config and its `StylesPath` must be inside the book folder, because only that folder is mounted into the container.
3. **Read the JSON.** It groups alerts by file, each with line, column, message, severity (`error > warning > suggestion`), check name, the matched text and an `Action`.

Vale alerts are not a report of their own. In a review, alerts at warning and error level become notes like every other finding (the review-text skill, "Findings become notes"); `run-checks text` only counts them. A rule firing on a wording the author already accepted (`decisions.py match`) is not a finding.

## Which fixes are mechanical

Vale has no `--fix`. Decide from the JSON `Action.Name` field, never from the rule name:

- `Action.Name == "replace"`: a substitution with a concrete replacement in `Action.Params[0]`, for example
  ```json
  {"Action": {"Name": "replace", "Params": ["use"]}, "Span": [12, 18], "Match": "utilize",
   "Line": 3, "Check": "PlainBook.Substitutions"}
  ```
  The note may offer it as the fix. When the author picks it, edit the original token (or a longer unique context if `Match` is not unique in the file), then run Vale on the file again to confirm the fix made no new alert.
- Any other action: an existence rule that needs a person. `PlainBook.WeakModifiers`, `PlainBook.EmDashWrap`, `PlainBook.PhrasalVerbs`, `PlainBook.PossessiveSEnding`, `write-good.Passive` and the book package's existence rules are never fixed mechanically.

---

## What Vale Catches vs What It Doesn't

| Category | Vale catches? | Owner if not |
|----------|---------------|--------------|
| Passive voice, weak modifiers, hedging | YES (write-good, proselint) | -- |
| Cliches, redundancy, wordy phrases | YES (proselint subset) | -- |
| Insensitive language | YES (alex) | -- |
| A phrase wrapped in a pair of dashes | YES (PlainBook.EmDashWrap) | -- |
| Wordy phrases ("utilize"->"use", "in order to"->"to") with concrete replacements | YES (PlainBook.Substitutions, auto-fix eligible) | -- |
| Hedge/filler words ("obviously", "essentially", "basically") | YES (PlainBook.WeakModifiers) | -- |
| Opaque phrasal verbs ("comes down to") | YES (PlainBook.PhrasalVerbs, suggestion) | -- |
| Possessive on a word ending in s ("Jones's") | YES (PlainBook.PossessiveSEnding) | -- |
| Book-specific vocabulary rules (banned terms, term discipline, container drift) | YES (the book's own Vale package; see the book for what each rule checks) | `scripts/word-for-two-things-check.py` is authoritative for the container-drift semantic check |
| Sentence length, paragraph length | NO | `scripts/sentence-and-paragraph-check.py` |
| Reference formatting | NO | the check-facts skill |
| Non-ASCII characters | NO | `scripts/ascii-normalize.py` |
| Causation/characterization misuse (Rule 4.2) | NO | `scripts/sentence-and-paragraph-check.py --connectors` |
| Term density (phase-aware) | NO | `scripts/term-density-check.py` |
| Dangling demonstratives | NO | `scripts/unclear-this-check.py` |
| T-D-C structure, adjacency chains | NO | review-text `common-problems`, `flow`, `all-problems` |
| Cross-chapter terminology drift | NO | review-text `consistency` |
| Terms that block the least experienced reader | NO | review-text `hard-words` |

---

## Rule-to-Style-Guide Mapping

| Vale rule | Rule | Severity | Type |
|-----------|---------------------------|----------|------|
| `write-good.Passive` | Rule 4.9 (passive voice with a purpose) | suggestion | existence |
| `write-good.Weasel` | Rule 4.12 (measured language, no hedging) | warning | existence |
| `write-good.TooWordy` | Rule 5.5 (plain vocabulary, brevity) | warning | substitution |
| `write-good.E-Prime` | (not enforced -- passive overlaps) | suggestion | existence |
| `proselint.Misc` | various | varies | varies |
| `alex.*` | (cross-cutting safety) | suggestion | existence |
| `PlainBook.EmDashWrap` | Rules 4.16, 9.1 (no dash pairs) | warning | existence |
| `PlainBook.Substitutions` | Rule 5.5 (plain vocabulary, wordy-phrase swaps) | warning | substitution |
| `PlainBook.WeakModifiers` | Rules 4.10, 4.12 (authoritative voice, no hedging) | warning | existence |
| `PlainBook.PhrasalVerbs` | Rule 5.7 (opaque phrasal verbs) | suggestion | existence |
| `PlainBook.PossessiveSEnding` | Rule 5.8 (possessive on a word ending in s) | warning | existence |

The book's own Vale package maps to that book's `decisions.md` entries rather than to general rules. The book documents its own rule-to-decision mapping; the skill does not track it.

---

## Writing and Calibrating Vale Rules

- **Existence over substitution for any word with more than one meaning.** One swap cannot be right in every sense, and `action: replace` makes a wrong swap one keystroke away. Keep substitution for one-meaning words (`utilize -> use`). `Substitutions.yml` must never map a hedge: "suggests" marks an inference from evidence, and "shows" or "indicates" would overclaim.
- **A blanket existence rule that cannot tell senses apart belongs at suggestion level**, and the author judges each hit. Example: a rule on "bank" meant to catch the money sense also fires on every river bank.
- **Exceptions match the matched token, not the text around it.** To let an exception see the word before the match, capture it in the token (`\b(\w+ )?bank`). Shortening the token later breaks the exceptions silently.
- **`BlockIgnores` hides code fences**, so words inside code (including comments the book wrote) are never linted; a rule that must see them needs another check.
- **The bibliography gets the built-in style only** (`BasedOnStyles =` empty for the references file, which in a pandoc book holds only its heading and the `::: {#refs}` div), with `Vale.Spelling` and `Vale.Repetition` off: surnames and initials are source data, not prose. The same goes for a page of names such as the acknowledgments.
- **Calibrate upstream packages per rule, with a reason** written next to each `= NO` in the book's Vale config. Rules tuned for news or fiction (cliches, jargon, E-Prime, "So" at sentence start) often misfire on a long non-fiction book. A rule that conflicts with the book's own format (a diacritics rule against an ASCII-only book) is switched off, and the book's rule wins.
- **Before adding a vocabulary rule, ask whether your reader would stumble**, not whether a dictionary calls the phrase idiomatic (`${CLAUDE_PLUGIN_ROOT}/skills/review-text/references/hard-words-criteria.md`). Rules ported from Simplified Technical English over-flag readers who have a technical register.
- **Order of trust:** when Vale and a Python check flag the same thing, the Python check is authoritative for the semantic call; Vale is a recall-first net.

---

## Calibration

A rule that fires so often that it looks wrong for the book's voice is a candidate for `= NO` in the book's Vale config, after the author agrees. Say so in the run folder of the review, with the rule and its count, not in a note per alert.

---

## Companion Tooling

The Vale check pairs with existing scripts. After running Vale on a chapter, you can also run:

```bash
SCRIPTS="${CLAUDE_PLUGIN_ROOT}/skills/write-text/scripts"
python3 $SCRIPTS/sentence-and-paragraph-check.py <file>
python3 $SCRIPTS/unclear-this-check.py <file>
python3 $SCRIPTS/word-for-two-things-check.py <file>
```

Vale and the Python scripts have intentionally non-overlapping responsibilities. If you find drift (Vale flags something a Python script also flags), the Python script is authoritative for the semantic call.
