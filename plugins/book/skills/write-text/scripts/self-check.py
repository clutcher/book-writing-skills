#!/usr/bin/env python3
import argparse
import io
import re
import sys
import tokenize
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
PLUGIN = SKILL.parents[1]
REPOSITORY = SKILL.parents[3]
sys.path.insert(0, str(PLUGIN / "lib"))

from command_runs import python_command, run_command

TIME_LIMIT = 600
TEXT_SUFFIXES = {".md", ".py", ".sh", ".yaml"}
RUNNERS_WITHOUT_SELF_TEST = {"vale-run.py", "vale-sync.py"}
SCRIPTS_OF_OTHER_PLACES = {"reference-format-check.py", "reference-sort.py", "book_config.py",
                           "decisions.py", "citation_key.py"}
BOOK_FILE_NAMES = re.compile(r"^(decisions|CLAUDE|SKILL|voice|glossary|list|quotes|"
                             r"hard-words-summary|hard-words-ch\w+|check_contract|"
                             r"decisions-format)\.md$")
PACKAGE_FILES = ("EmDashWrap", "PhrasalVerbs", "PossessiveSEnding", "Substitutions",
                 "WeakModifiers")
ALWAYS_FORBIDDEN = (r"/home/", r"/Users/")
KEY_DERIVATION = re.compile(r"^\s*def\s+(derive|derive_key|key_for)\s*\(", re.MULTILINE)
HARDCODED_COUNT = re.compile(r"\b[0-9]+ (rules|sections)\b")
ALLOWED_COUNT = re.compile(r"[0-9]+-[0-9]+ (rules|sections)|top rules|[Cc]hapter [0-9]+ section")

DESCRIPTION = """Maintainer check for the write-text skill. Runs on the skill's own fixtures
only, never on a book.

  1. every script's --self-test passes and every script's --help exits 0
  2. every rule number in the SKILL.md Rules Summary has a section in
     references/rules-explained.md, and the other way round
  3. every script and reference file the skill text names exists
  4. the skill files are ASCII (the Vale rule files may hold the characters they match)
  5. no Python code comments (docstrings are fine)
  6. no home-folder path in the skill and no citation-key code outside lib/citation_key.py;
     with a leak list, none of its words either (the author's name, one book's words,
     private paths)
  7. (warning only) no hardcoded rule or section counts in the text

--with-other-book also runs tools/other-book-check.py of the repository on the write-text
scripts (slower; only in a checkout of the repository, SKIPPED elsewhere).
--leak-words FILE reads the leak list: one regular expression per line, blank lines ignored.
The list is kept outside the plugin, because it names the very words that must not ship.
Without --leak-words, or when the file is missing, the leak-list part of check 6 prints
SKIPPED."""

EPILOG = "exit codes: 0 all passed, 1 a check failed."


def parse_arguments(argv):
    parser = argparse.ArgumentParser(prog="self-check.py", description=DESCRIPTION,
                                     epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--with-other-book", action="store_true",
                        help="also run tools/other-book-check.py on the write-text scripts")
    parser.add_argument("--leak-words", type=Path, metavar="FILE",
                        help="the leak list (default: none, and that part is SKIPPED)")
    return parser.parse_args(argv)


def runnable_scripts():
    return [script for script in sorted(SCRIPTS.glob("*.py"))
            if script.name != "self-check.py"
            and script.read_text(encoding="utf-8").startswith("#!")]


def self_tests_and_help():
    problems = []
    for script in runnable_scripts():
        if not run_command(python_command(script, "--help"), TIME_LIMIT).passed:
            problems.append(f"{script.name} --help")
            continue
        if script.name in RUNNERS_WITHOUT_SELF_TEST:
            print(f"  [OK]   {script.name} --help")
            continue
        result = run_command(python_command(script, "--self-test"), TIME_LIMIT)
        if result.passed:
            print(f"  [OK]   {script.name}")
        else:
            problems.append(f"{script.name} --self-test\n"
                            + "\n".join(f"         {line}" for line in result.output.splitlines()))
    return problems


def rule_numbers():
    summary = set(re.findall(r"(?m)^(\d+\.\d+)\.\s",
                             (SKILL / "SKILL.md").read_text(encoding="utf-8")))
    detail = set(re.findall(r"(?m)^\*\*(\d+\.\d+)\.\s",
                            (SKILL / "references" / "rules-explained.md")
                            .read_text(encoding="utf-8")))

    def order(number):
        return tuple(int(part) for part in number.split("."))

    problems = []
    missing_detail = sorted(summary - detail, key=order)
    missing_summary = sorted(detail - summary, key=order)
    if missing_detail:
        problems.append("in the summary, no detailed section: " + ", ".join(missing_detail))
    if missing_summary:
        problems.append("detailed section, no summary line: " + ", ".join(missing_summary))
    if not problems:
        print(f"  [OK]   {len(summary)} rules; summary and detail match")
    return problems


def named_files():
    texts = [SKILL / "SKILL.md"] + sorted((SKILL / "references").glob("*.md"))
    missing = set()
    for text_file in texts:
        text = text_file.read_text(encoding="utf-8")
        for script in set(re.findall(r"(?<![\w./-])([a-z][a-z0-9_-]*\.(?:py|sh))\b", text)):
            if not (SCRIPTS / script).exists() and script not in SCRIPTS_OF_OTHER_PLACES:
                missing.add(f"{text_file.name}: scripts/{script}")
        for other in set(re.findall(r"skills/([a-z-]+/scripts/[\w.-]+\.(?:py|sh))", text)):
            if not (PLUGIN / "skills" / other).exists():
                missing.add(f"{text_file.name}: skills/{other}")
        for reference in set(re.findall(r"`(?:references/)?([a-z][a-z0-9-]*\.md)`", text)):
            found = ((SKILL / "references" / reference).exists()
                     or (SKILL / "profiles" / reference).exists()
                     or BOOK_FILE_NAMES.match(reference))
            if not found:
                missing.add(f"{text_file.name}: {reference}")
    for package_file in PACKAGE_FILES:
        if not (SCRIPTS / "vale" / "PlainBook" / f"{package_file}.yml").exists():
            missing.add(f"scripts/vale/PlainBook/{package_file}.yml")
    if not (SKILL / "profiles" / "default.md").exists():
        missing.add("profiles/default.md")
    problems = [f"named but missing: {line}" for line in sorted(missing)]
    if not problems:
        print("  [OK]   every named script and reference exists")
    return problems


def skill_files(suffixes=None):
    for path in sorted(SKILL.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if suffixes is None or path.suffix in suffixes:
            yield path


def ascii_only():
    problems = []
    for path in skill_files(TEXT_SUFFIXES):
        if "fixtures" in path.relative_to(SKILL).parts:
            continue
        if any(ord(character) > 127 for character in path.read_text(encoding="utf-8",
                                                                     errors="replace")):
            problems.append(f"non-ASCII characters in {path.relative_to(SKILL)}")
    if not problems:
        print("  [OK]   all skill files are ASCII")
    return problems


def no_code_comments():
    problems = []
    for script in sorted(SCRIPTS.glob("*.py")):
        source = script.read_text(encoding="utf-8")
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and not (token.start[0] == 1
                                                       and token.string.startswith("#!")):
                problems.append(f"comment at {script.name}:{token.start[0]}")
    if not problems:
        print("  [OK]   no comments")
    return problems


def nothing_of_one_book(leak_list):
    listed = []
    if leak_list is None:
        print("  SKIPPED no leak list given; pass --leak-words FILE")
    elif leak_list.is_file():
        listed = [line.strip() for line in leak_list.read_text(encoding="utf-8").splitlines()
                  if line.strip()]
    else:
        print(f"  SKIPPED no leak list at {leak_list}; pass --leak-words FILE")
    leaks = re.compile("|".join(list(ALWAYS_FORBIDDEN) + listed))
    problems = []
    for path in skill_files():
        if path.name == "self-check.py":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            if leaks.search(line):
                problems.append(f"{path.relative_to(SKILL)}:{number}: {line.strip()[:80]}")
        if path.suffix == ".py" and KEY_DERIVATION.search(text):
            problems.append(f"{path.relative_to(SKILL)}: derives citation keys outside "
                            f"lib/citation_key.py")
    if not problems:
        print(f"  [OK]   no book or machine text, no own key code ({len(listed)} listed leak words)")
    return problems


def hardcoded_counts():
    found = []
    for path in skill_files({".md"}):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if HARDCODED_COUNT.search(line) and not ALLOWED_COUNT.search(line):
                found.append(f"{path.relative_to(SKILL)}:{number}:{line}")
    if found:
        print("  [WARN] possible hardcoded counts (the Rules Summary is the only list):")
        for line in found:
            print(f"         {line}")
    else:
        print("  [OK]   none")


def other_book_check():
    tool = REPOSITORY / "tools/other-book-check.py"
    if not tool.is_file():
        print("  SKIPPED no tools/other-book-check.py (not a checkout of the plugin repository)")
        return []
    result = run_command(python_command(tool, "--skills-dir", SKILL.parent,
                                        "--only-skill", "write-text"), 3600)
    print(result.output, end="")
    return [] if result.passed else ["other-book check failed"]


def run_section(title, check):
    print(title, flush=True)
    problems = check()
    for problem in problems:
        print(f"  [FAIL] {problem}", flush=True)
    return not problems


def main(argv=None):
    arguments = parse_arguments(argv)
    sections = [
        ("== 1. Self-tests and --help ==", self_tests_and_help),
        ("== 2. Rule numbers: Rules Summary <-> rules-explained.md ==", rule_numbers),
        ("== 3. Named files exist ==", named_files),
        ("== 4. ASCII only ==", ascii_only),
        ("== 5. No Python code comments ==", no_code_comments),
        ("== 6. Nothing of one book or one machine ==",
         lambda: nothing_of_one_book(arguments.leak_words)),
    ]
    if arguments.with_other_book:
        sections.append(("== 8. Other-book check (write-text scripts) ==", other_book_check))
    passed = [run_section(title, check) for title, check in sections[:6]]
    print("== 7. Hardcoded rule or section counts (warning) ==")
    hardcoded_counts()
    passed += [run_section(title, check) for title, check in sections[6:]]
    print()
    if not all(passed):
        print("self-check: FAILED")
        return 1
    print("self-check: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
