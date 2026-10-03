#!/usr/bin/env python3
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPOSITORY = TOOLS.parent
PLUGIN = REPOSITORY / "plugins" / "book"
LEAK_WORDS = REPOSITORY / ".workspace" / "leak" / "leak-words.txt"
SELF_CHECKS_TAKING_LEAK_WORDS = {"write-text"}
sys.dont_write_bytecode = True
sys.path.insert(0, str(PLUGIN / "lib"))

from command_runs import python_command, run_command

STEP_TIME_LIMIT = 1800
HELP_TIME_LIMIT = 60

DESCRIPTION = """Maintainer check for the whole plugin, run from anywhere in a checkout of the
repository:

  1. the lib tests
  2. every skill's self-check (a skill with no scripts/ folder needs none)
  3. every script answers --help with exit 0
  4. the leak scan over every published file (.workspace/leak/leak-words.txt, allowed lines in
     .workspace/leak/leak-allow.txt; private)
  5. every file a SKILL.md, a reference or a script names exists (tools/named-files-check.py)
  6. every skill has the same shape: frontmatter, modes, calls through ${CLAUDE_PLUGIN_ROOT}
  7. no __pycache__ folder and no .pyc file inside plugins/

--with-other-book also runs tools/other-book-check.py over every skill (slow).
A shell script is run with bash; without bash its --help step is SKIPPED."""

EPILOG = "exit codes: 0 every step passed, 1 a step failed."


class Steps:

    def __init__(self):
        self.failed = []

    def run(self, name, command, cwd=None):
        result = run_command(command, STEP_TIME_LIMIT, cwd=cwd)
        if result.passed:
            print(f"[OK]   {name}", flush=True)
            return
        print(f"[FAIL] {name}", flush=True)
        if result.timed_out:
            print(f"       TIMED OUT after {STEP_TIME_LIMIT}s")
        for line in result.output.splitlines()[-40:]:
            print(f"       {line}")
        self.failed.append(name)

    def fail(self, name, lines=()):
        print(f"[FAIL] {name}", flush=True)
        for line in lines:
            print(f"       {line}")
        self.failed.append(name)


def lib_tests(steps):
    print("== 1. lib tests ==")
    steps.run("lib tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
              cwd=PLUGIN / "lib")


def skill_self_checks(steps):
    print("== 2. skill self-checks ==")
    for skill in sorted(path for path in (PLUGIN / "skills").iterdir() if path.is_dir()):
        self_check = skill / "scripts" / "self-check.py"
        if self_check.is_file():
            steps.run(f"{skill.name} self-check",
                      python_command(self_check, *leak_words_arguments(skill)))
        elif not (skill / "scripts").is_dir():
            print(f"[OK]   {skill.name} has no scripts, so no self-check")
        else:
            steps.fail(f"{skill.name} has no scripts/self-check.py")


def leak_words_arguments(skill):
    if skill.name in SELF_CHECKS_TAKING_LEAK_WORDS and LEAK_WORDS.is_file():
        return ["--leak-words", LEAK_WORDS]
    return []


def scripts_with_help():
    places = [PLUGIN / "lib", TOOLS, *sorted((PLUGIN / "skills").glob("*/scripts"))]
    for place in places:
        for script in sorted(place.glob("*.py")) + sorted(place.glob("*.sh")):
            with script.open(encoding="utf-8", errors="replace") as handle:
                if handle.readline().startswith("#!"):
                    yield script


def help_command(script):
    if script.suffix == ".py":
        return python_command(script, "--help")
    bash = shutil.which("bash")
    return [bash, str(script), "--help"] if bash else None


def every_script_answers_help(steps):
    print("== 3. --help ==")
    failures = 0
    count = 0
    skipped = 0
    with tempfile.TemporaryDirectory() as empty_folder:
        for script in scripts_with_help():
            command = help_command(script)
            if command is None:
                skipped += 1
                continue
            count += 1
            if not run_command(command, HELP_TIME_LIMIT, cwd=empty_folder).passed:
                print(f"[FAIL] {script.relative_to(REPOSITORY).as_posix()} --help")
                failures += 1
    if skipped:
        print(f"SKIPPED {skipped} shell scripts: bash not found")
    if failures:
        steps.failed.append(f"--help ({failures})")
    else:
        print(f"[OK]   {count} scripts answer --help")


def no_bytecode(steps):
    print("== 7. no bytecode in the plugin ==")
    bytecode = [path for path in PLUGIN.rglob("*")
                if path.name == "__pycache__" or path.suffix == ".pyc"]
    if bytecode:
        steps.fail("bytecode inside the plugin:", [str(path) for path in bytecode])
    else:
        print("[OK]   no __pycache__")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="check-plugin.py", description=DESCRIPTION,
                                     epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--with-other-book", action="store_true",
                        help="also run tools/other-book-check.py over every skill (slow)")
    arguments = parser.parse_args(argv)
    steps = Steps()
    lib_tests(steps)
    skill_self_checks(steps)
    every_script_answers_help(steps)
    print("== 4. leak scan ==")
    steps.run("leak scan over published files", python_command(TOOLS / "leak-check.py"))
    print("== 5. named files exist ==")
    steps.run("named files", python_command(TOOLS / "named-files-check.py"))
    print("== 6. skill shape ==")
    steps.run("skill shape", python_command(TOOLS / "skill-shape-check.py"))
    no_bytecode(steps)
    if arguments.with_other_book:
        print("== 8. other-book check ==")
        steps.run("other-book check", python_command(TOOLS / "other-book-check.py"))
    print()
    if not steps.failed:
        print("check-plugin: every step passed")
        return 0
    print(f"check-plugin: {len(steps.failed)} step(s) failed: {', '.join(steps.failed)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
