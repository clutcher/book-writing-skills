#!/usr/bin/env python3
"""Maintainer tool (repository only, never shipped in the plugin): find scripts that go blind when a book names its files differently.

Why: a checker that silently reads zero files reports a clean result, and a clean report
looks exactly like a passing one. A hardcoded chapter glob or a sorting function that returns
a sentinel instead of failing does this. An argparse sweep does not catch it; this does.

How: two synthetic books hold the SAME text under different file names, and each book's
book.yaml describes its own names:

    control/manuscript/   110-chapter-1.md   210-chapter-2.md   900-references.md
    variant/manuscript/   01-intro.md        02-basics.md       99-sources.md

Every script of every skill in this plugin runs against both. File names and paths are masked
out of the output before comparing, so a script that reads the same text twice gives the same
masked report twice. A difference means behaviour depends on what files are CALLED.

Each script runs a third time from a decoy folder that looks like another book (its own
book.yaml, glossary and bibliography). A script that reads config from the working
folder instead of the book it was pointed at picks up the decoy and reports on the wrong book.

Every run gets no input on stdin and a time limit, so a script that waits for input or for
the network is reported as TIMEOUT instead of stopping the check.

Verdicts:
    OK          masked output identical for both books
    GUIDED      the variant run refused AND named the flag that fixes it (correct handling
                of a book the script cannot read)
    DOCUMENTED  a known naming dependency with a working override, listed in this script
    LEAK-WARNED output changed with the working folder, but the script said so on stderr,
                naming the file it used (acceptable, like GUIDED)
    CWD-LEAK    output changed with the working folder, silently: reads the wrong book
    BLIND       the variant run produced nothing (or much less) and gave no way out
    DIFFERS     both produced output but it is not the same; read it and decide
    INERT       nothing on either book: this check says nothing about the script
    TIMEOUT     the script did not finish in time (waiting on input or the network)
    ERROR       the script could not run

BLIND and CWD-LEAK are defects and make the exit code 1. Run from any folder: all runs start
from a neutral empty folder, so verdicts do not depend on where you stand.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

SKILLS_DIR = Path(__file__).resolve().parents[1] / "plugins" / "book" / "skills"
COLOURS_ON = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def colour(code):
    return code if COLOURS_ON else ""


RED = colour("\033[0;31m")
GREEN = colour("\033[0;32m")
YELLOW = colour("\033[0;33m")
CYAN = colour("\033[0;36m")
NC = colour("\033[0m")

CHAPTER_1 = """# Chapter 1: What A Canal Carried

## 1.1 What A Barge Holds

Coal moved along the canal far more cheaply than it moved by road, which means the cost of
running every mill in the valley fell once the water arrived. Records report that 70% of the
tolls came from coal rather than from any other cargo. Rivera argued that a lock keeper
decided more than any engineer did [Riv19]. This matters.

This suggests something important. The whole cargo of a long run lets a barge pass every
wharf without stopping, while a split cargo forces the crew to tie up at each wharf and unload
part of the hold before going on. In The Working Waterway the argument is made at length, and a
related claim appears in [Zzz99] which no reference list contains.

## 1.2 What A Lock Means

The responsibility of each lock keeper is to hold the level behind a gate with an accurate
gauge, so that boatmen can predict the depth without sounding the bottom. Whole runs
follow from that discipline, and the split wholeness delay follows from skipping it.
"""

CHAPTER_2 = """# Chapter 2: What Upkeep Means

## 2.1 What An Inspection Checks

An inspection checks the banks rather than the boats, which means it should still hold after a
dry summer that leaves the water level unchanged. Short inspections are better.

> **A bank walk** is an inspection that follows one stretch of towpath on foot.

> **A stop plank** is a board that closes a channel while it is drained.

Okafor makes this point at length, and the same framework appears in other treatments
of the subject, where the mechanism is described in similar terms [Riv19].
"""

REFERENCES = """# References

[Riv19] Rivera, M.L. (2019). Lock Keepers and Their Ledgers. *Journal of
Invented Examples*, 3(1), 1-20.
"""

GLOSSARY = """# Glossary

## Defined terms

### bank walk -- Ch2 S2.1 (blockquote)

**Canonical definition:** an inspection that follows one stretch of towpath.
"""

BOOK_CONFIG = """version: 1
manuscript:
  dir: manuscript
  references: manuscript/{references}
  chapter_pattern: '{chapter_pattern}'
terms:
  families:
    - {{term: whole, role: primary, also: [wholeness]}}
    - {{term: split, role: antonym}}
  compounds: [whole cargo, split cargo, whole run]
"""

CONTROL = {
    "names": {"110-chapter-1.md": CHAPTER_1, "210-chapter-2.md": CHAPTER_2,
              "900-references.md": REFERENCES},
    "references": "900-references.md",
    "chapter_pattern": r"(?:^|-)chapter-(\d+)\.md$",
}
VARIANT = {
    "names": {"01-intro.md": CHAPTER_1, "02-basics.md": CHAPTER_2, "99-sources.md": REFERENCES},
    "references": "99-sources.md",
    "chapter_pattern": r"^0(\d)-[a-z]+\.md$",
}

NOT_APPLICABLE = {
    "self-check.py",
    "vale-run.py",
    "vale-sync.py",
    "build-book.sh",
    "book-settings.sh",
    "page-settings.sh",
}

EXTRA_ARGS = {}

POINTED_AT_BOOK_CONFIG = {"glossary-seed.py"}

DOCUMENTED_DEPENDENCIES = {}

RUN_SECONDS = 60

REFUSAL_RE = re.compile(r"\b(error|usage|cannot|could not|no such)\b", re.IGNORECASE)
LEAK_WARNING_RE = re.compile(
    r"warning[^\n]*(outside the directory|current directory|resolved against)", re.IGNORECASE)
OVERRIDE_RE = re.compile(r"--[a-z][a-z0-9-]*")

COLOURS = {"OK": GREEN, "GUIDED": GREEN, "LEAK-WARNED": GREEN, "DOCUMENTED": CYAN,
           "BLIND": RED, "CWD-LEAK": RED, "DIFFERS": YELLOW, "INERT": YELLOW,
           "TIMEOUT": RED, "ERROR": RED}
VERDICT_ORDER = ("OK", "GUIDED", "DOCUMENTED", "LEAK-WARNED", "CWD-LEAK", "BLIND", "DIFFERS",
                 "INERT", "TIMEOUT", "ERROR")
DEFECT_VERDICTS = ("BLIND", "CWD-LEAK")


def build_book(root, book):
    """A book folder with book.yaml, a glossary and the manuscript files; returns the
    manuscript folder, which is what every script is pointed at."""
    root = Path(root)
    manuscript = root / "manuscript"
    manuscript.mkdir(parents=True, exist_ok=True)
    (root / "rules").mkdir(exist_ok=True)
    (root / "rules" / "glossary.md").write_text(GLOSSARY, encoding="utf-8")
    (root / "book.yaml").write_text(BOOK_CONFIG.format(
        references=book["references"], chapter_pattern=book["chapter_pattern"]),
        encoding="utf-8")
    for filename, content in book["names"].items():
        (manuscript / filename).write_text(content, encoding="utf-8")
    return manuscript


def build_decoy(root):
    """A folder that LOOKS like another book, to catch config found from the working folder."""
    decoy = Path(root)
    for folder in ("manuscript", "rules", "sources"):
        (decoy / folder).mkdir(parents=True, exist_ok=True)
    (decoy / "book.yaml").write_text(
        "version: 1\nterms:\n  families:\n    - {term: zzdecoy, role: primary}\n"
        "  compounds: [zzdecoy bed]\n", encoding="utf-8")
    glossary = "# Glossary\n\n## Defined terms\n\n### zzdecoy -- Ch1 S1.1 (blockquote)\n"
    (decoy / "rules" / "glossary.md").write_text(glossary, encoding="utf-8")
    (decoy / "sources" / "list.md").write_text("# Sources\n", encoding="utf-8")
    (decoy / "manuscript" / "900-references.md").write_text(
        "# References\n\n[Zz99] Decoy, D. (1999). A Decoy Reference. *Nowhere*.\n",
        encoding="utf-8")
    return decoy


def masked_names(names):
    """Every form a file name can take in a report: full name, stem, and 'ChN' shorthand."""
    forms = set()
    for filename in names:
        stem = filename.rsplit(".", 1)[0]
        forms.update({filename, stem, stem.replace("chapter-", "Ch")})
    return sorted(forms, key=len, reverse=True)


def mask(text, names):
    """Remove every trace of the file names and paths so two runs compare on content."""
    out = re.sub(r"/[^\s:'\"]*(?:control|variant)[^\s:'\"]*", "PATH", text)
    for form in masked_names(names):
        out = out.replace(form, "FILE")
    out = re.sub(r"\033\[[0-9;]*m", "", out)
    return re.sub(r"\s+", " ", out).strip()


def run_script(script, target, names, cwd):
    """(masked output, problem) for one run; problem is None, 'TIMEOUT' or 'ERROR'."""
    command = ([sys.executable, str(script)] if script.suffix == ".py"
               else [shutil.which("bash") or "bash", str(script)])
    command += EXTRA_ARGS.get(script.name, [])
    if script.name in POINTED_AT_BOOK_CONFIG:
        command += ["--config", str(Path(target).parent / "book.yaml")]
    else:
        command += [str(target)]
    environment = dict(os.environ, NO_COLOR="1", PYTHONDONTWRITEBYTECODE="1")
    try:
        process = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace", cwd=str(cwd),
                                 stdin=subprocess.DEVNULL, timeout=RUN_SECONDS, env=environment)
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    except OSError:
        return None, "ERROR"
    return mask(process.stdout + process.stderr, names), None


def classify(control_out, variant_out):
    if control_out is None or variant_out is None:
        return "ERROR"
    if not control_out and not variant_out:
        return "INERT"
    if control_out == variant_out:
        return "OK"
    if REFUSAL_RE.search(variant_out) and OVERRIDE_RE.search(variant_out):
        return "GUIDED"
    if not variant_out or len(variant_out) < len(control_out) * 0.5:
        return "BLIND"
    return "DIFFERS"


def is_entry_point(script):
    """A runnable script: .py or .sh with a shebang. Helper modules have none."""
    if script.suffix not in (".py", ".sh"):
        return False
    with open(script, encoding="utf-8", errors="replace") as handle:
        return handle.readline().startswith("#!")


def find_scripts(skills_dir, only, only_skill=None):
    scripts = []
    for skill in sorted(Path(skills_dir).iterdir()):
        script_dir = skill / "scripts"
        if not script_dir.is_dir() or (only_skill and skill.name != only_skill):
            continue
        for script in sorted(script_dir.iterdir()):
            if script.name in NOT_APPLICABLE or not is_entry_point(script):
                continue
            if only and script.name != only:
                continue
            scripts.append(script)
    return scripts


def judge(script, books, neutral, decoy):
    control_target, variant_target = books
    control_out, control_problem = run_script(script, control_target, CONTROL["names"], neutral)
    variant_out, variant_problem = run_script(script, variant_target, VARIANT["names"], neutral)
    problem = control_problem or variant_problem
    if problem:
        return problem, control_out, variant_out
    verdict = classify(control_out, variant_out)
    if verdict == "DIFFERS" and script.name in DOCUMENTED_DEPENDENCIES:
        verdict = "DOCUMENTED"
    decoy_out, decoy_problem = run_script(script, control_target, CONTROL["names"], decoy)
    if not decoy_problem and decoy_out != control_out:
        verdict = "LEAK-WARNED" if LEAK_WARNING_RE.search(decoy_out) else "CWD-LEAK"
    return verdict, control_out, variant_out


def print_results(results, verbose):
    label = f'{"SCRIPT":<46} VERDICT'
    print(label)
    print("-" * len(label))
    for script, verdict, control_out, variant_out in results:
        name = f"{script.parent.parent.name}/{script.name}"
        print(f"{name:<46} {COLOURS.get(verdict, NC)}{verdict}{NC}")
        if verdict == "DOCUMENTED":
            print(f"    {DOCUMENTED_DEPENDENCIES[script.name]}")
        if verbose and verdict in ("BLIND", "DIFFERS", "CWD-LEAK"):
            print(f"    control: {(control_out or '')[:160]}")
            print(f"    variant: {(variant_out or '')[:160]}")
    counts = {verdict: sum(1 for r in results if r[1] == verdict) for verdict in VERDICT_ORDER}
    print()
    print("   ".join(f"{COLOURS[v]}{v}: {counts[v]}{NC}" for v in VERDICT_ORDER))
    if counts["INERT"]:
        print(f"\n{YELLOW}INERT scripts found nothing on either book, so this check says "
              f"nothing about them. That is a gap in the planted content, not a pass.{NC}")
    if counts["TIMEOUT"]:
        print(f"\n{RED}TIMEOUT scripts did not finish in {RUN_SECONDS}s with no input; they "
              f"wait for stdin or the network. Give them a dry-run path or list them in "
              f"NOT_APPLICABLE with a reason.{NC}")
    if counts["CWD-LEAK"]:
        print(f"\n{RED}CWD-LEAK: the script gave different output for the SAME book only "
              f"because it ran from a different folder, so it reads config from outside the "
              f"book it was given.{NC}")
    if counts["BLIND"]:
        print(f"\n{RED}BLIND: the script behaves differently only because the files are "
              f"named differently.{NC}")
    return 1 if any(counts[v] for v in DEFECT_VERDICTS) else 0


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("--verbose", action="store_true",
                        help="show both outputs for BLIND, DIFFERS and CWD-LEAK")
    parser.add_argument("--skills-dir", type=Path, default=SKILLS_DIR,
                        help="folder holding the skills (default: this plugin's skills)")
    parser.add_argument("--only", metavar="SCRIPT", help="check one script by file name")
    parser.add_argument("--only-skill", metavar="SKILL", help="check the scripts of one skill")
    parser.add_argument("--self-test", action="store_true",
                        help="test the masking and the verdicts, without running any script")
    return parser.parse_args(argv)


def run(argv):
    options = parse_arguments(argv)
    if options.self_test:
        return self_test()
    temporary = tempfile.mkdtemp(prefix="other-book-check-")
    try:
        books = (build_book(Path(temporary) / "control", CONTROL),
                 build_book(Path(temporary) / "variant", VARIANT))
        neutral = Path(temporary) / "neutral"
        neutral.mkdir()
        decoy = build_decoy(Path(temporary) / "decoy")
        scripts = find_scripts(options.skills_dir, options.only, options.only_skill)
        if not scripts:
            print(f"{RED}No scripts found under {options.skills_dir}{NC}", file=sys.stderr)
            return 2
        print(f"{CYAN}Other-book check{NC}")
        print(f"Skills dir: {options.skills_dir}")
        print(f"Scripts:    {len(scripts)}\n")
        results = [(script, *judge(script, books, neutral, decoy)) for script in scripts]
        return print_results(results, options.verbose)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def self_test():
    failures = []

    def expect(got, want, label):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    control = "/tmp/x/control/manuscript/110-chapter-1.md: 110-Ch1 has 3 hits"
    variant = "/tmp/x/variant/manuscript/01-intro.md: 01-intro has 3 hits"
    expect(mask(control, CONTROL["names"]), mask(variant, VARIANT["names"]),
           "masking removes paths, names and the ChN shorthand")
    expect(classify("a b c", "a b c"), "OK", "identical output")
    expect(classify("", ""), "INERT", "no output at all")
    expect(classify("long report " * 10, ""), "BLIND", "variant produced nothing")
    expect(classify("long report " * 10, "error: pass --pattern GLOB"), "GUIDED",
           "variant refused and named a flag")
    expect(classify("report one two", "report two one"), "DIFFERS", "same size, other text")
    expect(classify(None, "x"), "ERROR", "a run that did not happen")
    temporary = tempfile.mkdtemp(prefix="other-book-check-self-test-")
    try:
        manuscript = build_book(temporary, VARIANT)
        expect(sorted(p.name for p in manuscript.iterdir()), sorted(VARIANT["names"]),
               "the variant book holds the variant names")
        expect((Path(temporary) / "book.yaml").is_file(), True, "each book has its book.yaml")
        expect((Path(temporary) / "rules" / "glossary.md").is_file(), True,
               "each book keeps its glossary in the standard layout")
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
