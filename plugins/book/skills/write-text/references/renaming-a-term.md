# Renaming a term or changing an explanation

When the book renames a term, or replaces the explanation behind one, the change does not end at
the words that were renamed. Each lesson below describes a place where the old account can
survive a careful vocabulary sweep.

## Fix the structure before the sentences

If the new account changes how the ideas are grouped (two causes become one cause with two
effects, a list of three becomes a list of two), change the headings and the grouping first.
Patching sentences inside a grouping that is itself wrong hardens the error, and many of the
patched sentences will move anyway when the structure is fixed.

## Four places the old account hides

1. **Descriptive references.** A rename leaves behind references that describe the old thing
   without naming it ("the second question on the list", a quoted checklist question). A grep for the
   retired words cannot find them. After a rename, search separately for descriptions of the
   renamed thing, then re-read by meaning.
2. **Neighbouring sentences.** Rewriting one sentence can strand the next one: "these causes",
   plural, refers to nothing once the sentence above stops naming two causes. After rewriting a
   sentence, read the one after it.
3. **Inventories built from retired words.** A list of sites made by grepping the old words
   misses sites that carry none of them and under-reports sites that carry one. Anchor each site
   by a quoted clause, not by a line number: the clause survives edits, the number does not.
4. **Arithmetic and shape.** A change of mechanism shows up in more than words:
   - an arithmetic implication that prices the old account ("no money left for ...");
   - a framing of the old threshold that uses none of the retired words ("how much rain the
     field can take before it floods");
   - a shape that encodes the old grouping (a two-item list claiming two results of two
     independent causes), which no word substitution repairs;
   - a sentence that states the opposite of the new mechanism.

## After the rename

- The decision, the retired wording and the reason belong in `decisions.md`, and the glossary
  entry and its invariants need the new account; suggest both to the author, and
  revise-from-notes records them. Keep the retired account's notes in `thinking/argument/`,
  marked as retired, so nobody revives it by accident.
- Update any Vale rule of the book that guards the old word.
- A thinking file, a note or a summary that still teaches the retired account will mislead the
  next reader of it; state an account once, in the place that defines it, and point to it from
  everywhere else.
