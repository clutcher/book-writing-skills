# The check contract

Every check in every skill of this plugin reports in the same shape and exits with the same
codes. `check_output.py` in this folder does the work; a check declares its finding classes and
calls it.

## Why

A check that is read through the wrong word looks exactly like a check that passed. If one
check says `hash-stale` and the caller greps for `mismatch`, the caller sees nothing and reports
"clean". Being more careful does not fix this. What fixes it is one contract: a caller reads the
exit code, and never needs to guess a keyword.

Do not add synonyms to the output so that more greps match. One name per idea.

## Exit codes

| Exit | Meaning |
|---|---|
| **0** | No defects. Informational and advisory findings may still be printed. |
| **1** | Defects are present. |
| **2** | The tool itself failed: input it cannot read, a missing file it needs, a crash. |

```bash
if ! python3 some-check.py; then echo "defects"; fi
```

A crash is a tool failure, never a finding. A script ends with `run_main(main)` from
`check_output.py`: an unexpected error then exits 2 with one line that names it, and the output
is written as UTF-8, so a Windows pipe cannot make a check crash on a character. A runner that
sees a Python `Traceback` from a check that exited 1 counts it as a failure, not as a finding.

Three states, not two. Many checks report counts that are not defects: a reading queue, a
download worklist, a state that is known and expected. If every non-zero count failed the run,
every run would fail and nobody would read the result.

**A check that cannot run prints `SKIPPED  <reason>` as its last line and exits 0.** Two cases:

- it needs an external tool (docker, bibtex, tesseract, vale, epubcheck, poppler) and does not
  find it;
- the book does not use the feature the check reads: no glossary, no sources list, no
  decisions file, no open notes, no `thinking/` folder. A book that does not use citations is
  not a book with citation defects.

A skipped check is not a passed check: whoever reports the run must say it was skipped, and why.
With `--format tsv` the standard output holds item lines only, so the `SKIPPED` line goes to the
error output; with `--format json` the reason is in the `skipped` field.

```python
report = CheckReport("glossary-check", CLASSES)
if report.skip_unless_present(config.rules.glossary, "glossary"):
    sys.exit(report.emit(args.format))
```

The reason names the feature and the path the check looked for, so an author who expected the
feature sees at once where the check looked. A file the check needs *because the book uses the
feature* (a sources list that names a missing library file) is still a defect or a tool failure,
never a skip.

## Three kinds of finding

**DEFECT: acting on it makes a file more correct.** A list entry disagrees with the file on
disk; a cached file has no entry; a field name is outside the closed list; an entry points at a
file that does not exist.

**INFORMATIONAL: an expected state, or a worklist.** Nothing is wrong; the number is printed so
it stays visible. A reading queue, a manual-download queue, the count of entries with no fetch
record.

**ADVISORY: needs a person, and never changes the exit code.** A pairing that a human must judge; a quote the
check could not find in a cached text that may be OCR; a "likely" or "ambiguous" grade the check
refuses to fix.

**The rule for hard cases: if a false positive would lead a person to change something that is
correct, the finding is ADVISORY, not DEFECT.** A check that enforces a rule stored in a bank can
put an error into the book when the stored rule is itself wrong.

## No accepted counts: a finding is reported until it is fixed

There is no baseline and no accepted count, in a check or in the book. A DEFECT or ADVISORY item
is reported on every run until the file is fixed; a runner that reads many checks (the run-checks
skill) shows every check with such an item as a finding. An accepted count hides the next item of
the same class, and a hidden item looks exactly like a fixed one.

So the category carries the judgment. A class whose items are an expected state, not a problem
(a source read and not cited, an entry with no person as author, a file added by hand), is
INFORMATIONAL: it is printed and counted, and it is never a finding. A class that marks a real
problem stays DEFECT or ADVISORY, however many items it has.

## Output shape

One line per item, tab-separated, so `cut -f` works without a regex:

```
<KEY>\t<class>\t<message>
```

Then the summary, always printed, always last:

```
<class>   <count>          one line per class that fired
TOTAL     <n> defects, <n> informational, <n> advisory
```

`--format tsv` prints the item lines only (and a skip on the error output). `--format json`
prints one object with the items, counts, totals and exit code. One parser, several output
formats; never one file written in several formats.

## What this contract does not change

- **Banks stay markdown.** They are read with grep (`grep -n '@Smi99' manuscript/*.md`), and
  their values are long prose.
- **No output synonyms.** One name per idea.
- **`--fix` keeps its meaning.** A check that refuses to fix a class keeps refusing.

## What is shared and what is not

Most finding classes belong to exactly one script, and stay there: a class name lives next to the
only code that can emit it. A few classes are emitted by more than one script, usually a checker
and the fixer over the same rule. Those are declared once, in `check_output.SHARED_CLASSES`, so a
rename cannot put a checker and its fixer out of step.

The test is "would two places have to agree?" If yes, the name goes in `SHARED_CLASSES`. If no, it
stays in its own script.

The machinery is never per script: the category constants, the summary, the exit-code rule and
the output formats all come from `check_output.py`.

## Writing a check

1. **Declare the classes and their categories as data near the top of the script**, importing any
   shared ones from `check_output.SHARED_CLASSES`.
2. **Let everything else derive from that declaration**: the item lines, the summary and the exit
   code. Deciding "is this a defect?" at each print call spreads one judgment over hundreds of
   places.
3. **Make an expected state INFORMATIONAL in the declaration**, so a runner that calls many
   checks does not need to know which state of each check is normal.

```python
from check_output import CheckReport, DEFECT, INFORMATIONAL, add_output_arguments

CLASSES = {"hash-stale": DEFECT, "reading-queue": INFORMATIONAL}

report = CheckReport("cache-check", CLASSES)
report.add("Smi99", "hash-stale", "the cached file changed since it was recorded")
sys.exit(report.emit(args.format))
```

**When converting an existing check, diff its findings before and after on real data.** A change
to *what* a check finds is a bug; only *how it reports* may change.

## A checker that reads zero files looks like a pass

A checker that silently reads zero files reports a clean result, and a clean report looks
exactly like a passing one. `tools/other-book-check.py` (in the plugin's repository, not
shipped with the plugin) runs every script against two made-up books with the same text under
different file names, each with its own book.yaml, masks the names out of the output and
compares. It also runs each script from a decoy folder that looks like another book, to catch
a script that reads the config of the working folder instead of the book it was given. Runs get
no stdin and a time limit.

| Verdict | Meaning |
|---|---|
| OK | same masked output for both books |
| GUIDED | the variant run refused and named the flag that fixes it (correct) |
| DOCUMENTED | a known naming dependency with a verified override |
| LEAK-WARNED | output changed with the working folder, but the script said so on stderr |
| CWD-LEAK | output changed with the working folder, silently (defect) |
| BLIND | the variant run produced nothing and gave no way out (defect) |
| DIFFERS | both produced output, not the same; read it |
| INERT | nothing on either book; the check says nothing about the script |
| TIMEOUT | did not finish without input (waits on stdin or the network) |
| ERROR | could not run |

A script that is given a file or a folder finds the config above it:
`config_from_args(args, targets=[...])`. A rule is stated once, in the module that executes
it; a docstring that still teaches a retired rule passes every test.
