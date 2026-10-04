#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS_DIR.parent
FIXTURES_DIR = SKILL_DIR / "tests" / "fixtures"
CLEAN_ROOM = SCRIPTS_DIR / "clean-room.py"
REVIEW_STATE = SCRIPTS_DIR / "review-state.py"
SKILL_FILE = SKILL_DIR / "SKILL.md"
SKILL_LINE_LIMIT = 300


class SelfCheck:
    def __init__(self, verbose):
        self.verbose = verbose
        self.failures = []
        self.passes = 0

    def expect(self, label, condition, detail=""):
        if condition:
            self.passes += 1
            if self.verbose:
                print(f"PASS    {label}")
        else:
            self.failures.append(label)
            print(f"FAIL    {label}" + (f": {detail}" if detail else ""))


def run(script, *arguments, cwd):
    completed = subprocess.run([sys.executable, str(script), *arguments], cwd=cwd,
                               capture_output=True, encoding="utf-8", errors="replace")
    return completed.returncode, completed.stdout + completed.stderr


def state(room, *arguments):
    return run(REVIEW_STATE, "--room", str(room), *arguments, cwd=room)


def status_json(room):
    code, output = state(room, "status", "--format", "json")
    return code, json.loads(output) if code == 0 else {}


def check_help(check):
    for script in (CLEAN_ROOM, REVIEW_STATE, Path(__file__)):
        code, output = run(script, "--help", cwd=SKILL_DIR)
        check.expect(f"{script.name} --help works", code == 0 and "usage" in output, output[-200:])
    for command in ("setup", "collect"):
        code, _ = run(CLEAN_ROOM, command, "--help", cwd=SKILL_DIR)
        check.expect(f"clean-room.py {command} --help works", code == 0)
    for command in ("status", "findings", "queue", "check"):
        code, _ = run(REVIEW_STATE, command, "--help", cwd=SKILL_DIR)
        check.expect(f"review-state.py {command} --help works", code == 0)


def check_skill_file(check):
    lines = SKILL_FILE.read_text(encoding="utf-8").splitlines() if SKILL_FILE.is_file() else []
    check.expect("SKILL.md exists and has frontmatter", lines[:1] == ["---"])
    check.expect(f"SKILL.md is at most {SKILL_LINE_LIMIT} lines", len(lines) <= SKILL_LINE_LIMIT,
                 f"{len(lines)} lines")


def check_setup(check, book, room, checks_file):
    code, output = run(CLEAN_ROOM, "setup", cwd=book)
    check.expect("setup dry run exits 0", code == 0, output)
    check.expect("setup dry run writes nothing", not room.exists())
    check.expect("setup dry run says so", "dry run" in output)

    code, output = run(CLEAN_ROOM, "setup", "--room", str(book / "inner"), cwd=book)
    check.expect("setup refuses a room inside the book", code == 2, output)

    code, output = run(CLEAN_ROOM, "--set", "readers_review.sources_for_reviewer=missing.md",
                       "setup", cwd=book)
    check.expect("setup fails without the sources for the reviewer",
                 code == 2 and "no sources for the reviewer found" in output, output)

    code, output = run(CLEAN_ROOM, "setup", "--checks", str(checks_file), "--fix", cwd=book)
    check.expect("setup --fix exits 0", code == 0, output)
    for relative in ("review/mechanical-checks.txt", "manuscript/010-preface.md", "manuscript/110-chapter-1.md", "sources/list.md", "sources/references.bib",
                     "sources/sources-for-reviewer.md", "decisions.md", "book/facts.md",
                     "book/back-cover.md", "REVIEW-PLAN.md", "CLAUDE.md", "plan/lenses.md",
                     "plan/readers.md", "plan/skeptic-rules.md", "plan/merge-and-verify.md",
                     "plan/templates/lens-report.md", "plan/templates/verification.md",
                     "room.json", ".claude/settings.local.json"):
        check.expect(f"room has {relative}", (room / relative).is_file())
    check.expect("room has no thinking files", not (room / "thinking").exists())
    if code != 0:
        return
    facts = (room / "book" / "facts.md").read_text(encoding="utf-8")
    check.expect("facts carry title and subtitle", "A Small Test Book" in facts and "Fixture" in facts)
    plan = (room / "REVIEW-PLAN.md").read_text(encoding="utf-8")
    check.expect("plan has no unfilled placeholders", "{{" not in plan)
    check.expect("plan lists four lenses", plan.count("`review/lens-") == 4)
    lenses = (room / "plan" / "lenses.md").read_text(encoding="utf-8")
    check.expect("custom lens rendered", "Lens 4: Legal risk" in lenses)
    check.expect("load-bearing sources filled", "@Abc20, @DE21" in lenses)
    check.expect("room lenses omit book.yaml how-to", "Changing the lenses" not in lenses)
    settings = json.loads((room / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    check.expect("settings switch the plugin off",
                 False in settings.get("enabledPlugins", {}).values())
    overrides = settings.get("skillOverrides", {})
    check.expect("settings switch this skill off", overrides.get("book:review-ideas") == "off")
    check.expect("settings switch extra skills off", overrides.get("some-other-writing-skill") == "off")
    room_state = json.loads((room / "room.json").read_text(encoding="utf-8"))
    check.expect("room.json has round 1 and four lenses",
                 room_state.get("round") == 1 and len(room_state.get("lenses", [])) == 4)


def check_refresh_without_results(check, book, room, checks_file):
    code, output = run(CLEAN_ROOM, "setup", "--checks", str(checks_file), "--fix", cwd=book)
    check.expect("refresh without results exits 0", code == 0, output)
    room_state = json.loads((room / "room.json").read_text(encoding="utf-8"))
    check.expect("refresh without results keeps round 1", room_state.get("round") == 1, room_state)
    check.expect("refresh without results archives nothing",
                 not list((book / ".book" / "runs").glob("*-review-ideas-readers*"))
                 and not (room / "archive").exists())
    check.expect("refresh without results keeps fresh mechanical checks",
                 (room / "review" / "mechanical-checks.txt").is_file())


def check_default_lenses(check, work):
    book = work / "default-book"
    room = work / "default-book-readers-review"
    shutil.copytree(FIXTURES_DIR / "book", book)
    config_file = book / "book.yaml"
    config_text = config_file.read_text(encoding="utf-8")
    config_file.write_text(config_text[:config_text.index("  lenses:")], encoding="utf-8")
    code, output = run(CLEAN_ROOM, "setup", "--fix", cwd=book)
    check.expect("setup with default lenses exits 0", code == 0, output)
    if code != 0:
        return
    lenses = (room / "plan" / "lenses.md").read_text(encoding="utf-8")
    plan = (room / "REVIEW-PLAN.md").read_text(encoding="utf-8")
    check.expect("default setup lists nine lenses", plan.count("`review/lens-") == 9)
    check.expect("main image filled", "Lens 8: Main image" in lenses
                 and "the river image in the title" in lenses)
    check.expect("unset values say where to look", "not set: find it in the book" in lenses)
    check.expect("no unfilled placeholders in room lenses", "{{" not in lenses)
    code, output = state(room, "findings")
    check.expect("findings fails loudly where no lens report is",
                 code == 2 and "no lens report" in output, output)


def check_paper_room(check, work):
    paper = work / "paper"
    room = work / "paper-readers-review"
    shutil.copytree(FIXTURES_DIR / "book", paper)
    code, output = run(CLEAN_ROOM, "--set", "kind=paper", "setup", "--fix", cwd=paper)
    check.expect("setup for a paper exits 0", code == 0, output)
    if code != 0:
        return
    back_cover = (room / "book" / "back-cover.md").read_text(encoding="utf-8")
    facts = (room / "book" / "facts.md").read_text(encoding="utf-8")
    check.expect("a paper room says a paper has no back cover", "A paper has no back cover" in back_cover)
    check.expect("a paper room says it is a paper", "a research paper" in facts, facts)


def check_state_progress(check, room):
    fixtures = FIXTURES_DIR / "review"
    review = room / "review"
    review.mkdir(exist_ok=True)

    code, status = status_json(room)
    check.expect("status starts in stage A", code == 0 and status["next"]["stage"] == "A")
    first_batch = status.get("next", {}).get("items", [])
    check.expect("blocker lenses come first", first_batch[:2] and "Lens 1" in first_batch[0]
                 and "Lens 2" in first_batch[1], first_batch)

    for name in ("lens-1-thesis-and-argument.md", "lens-2-correctness-and-evidence.md",
                 "lens-3-strengths-to-protect.md", "lens-4-legal-risk.md"):
        shutil.copy(fixtures / name, review / name)
    code, status = status_json(room)
    check.expect("a lens without coverage log is unfinished",
                 status["next"]["stage"] == "A" and status["lenses_finished"] == 3, status)

    with (review / "lens-4-legal-risk.md").open("a", encoding="utf-8") as lens_file:
        lens_file.write((fixtures / "lens-4-coverage.txt").read_text(encoding="utf-8"))
    code, status = status_json(room)
    check.expect("all lenses finished moves to stage B", status["next"]["stage"] == "B", status)

    code, output = state(room, "findings")
    rows = [line.split("\t") for line in output.strip().splitlines()]
    check.expect("findings lists six findings", len(rows) == 6, output)
    check.expect("findings carry severity", ["L1-1", "1", "blocker", "checked-in-text"] == rows[0][:4], rows[:1])

    shutil.copy(fixtures / "merge-map.md", review / "merge-map.md")
    code, status = status_json(room)
    check.expect("merge map moves to stage C wave 1",
                 status["next"]["stage"] == "C" and status["next"]["items"] == ["solo: L1-1"], status)

    (review / "verification").mkdir(exist_ok=True)
    shutil.copy(fixtures / "verification" / "L1-1.md", review / "verification" / "L1-1.md")
    code, status = status_json(room)
    check.expect("wave 2 groups by source family",
                 status["next"]["items"] == ["family: river studies: M1"], status)

    shutil.copy(fixtures / "verification" / "M1.md", review / "verification" / "M1.md")
    code, status = status_json(room)
    check.expect("all verdicts move to stage D", status["next"]["stage"] == "D", status)
    code, output = state(room, "check")
    check.expect("check is clean before the report", code == 0, output)

    shutil.copy(fixtures / "report-with-killed.md", review / "REVIEW-REPORT.md")
    code, output = state(room, "check")
    check.expect("check finds a killed finding in the report", code == 1 and "killed-in-report" in output, output)

    shutil.copy(fixtures / "report-with-killed-member.md", review / "REVIEW-REPORT.md")
    code, output = state(room, "check")
    check.expect("check finds a member of a killed merged finding in the report",
                 code == 1 and "killed-in-report" in output and "L2-1" in output, output)

    shutil.copy(fixtures / "report-clean.md", review / "REVIEW-REPORT.md")
    code, output = state(room, "check")
    check.expect("check is clean with the clean report", code == 0, output)
    code, status = status_json(room)
    check.expect("status says done", status["next"]["stage"] == "done", status)

    code, output = state(room, "queue")
    check.expect("queue shows verdicts", "L1-1\tblocker\t1\tsolo\tconfirmed" in output, output)


def check_broken_files(check, room):
    review = room / "review"
    broken = review / "lens-2-correctness-and-evidence.md"
    original = broken.read_text(encoding="utf-8")
    broken.write_text(original.replace("### L2-2", "### L5-2").replace("- **Severity:** major\n- **Tier:** recall-based\n- **Location:** `110", "- **Tier:** recall-based\n- **Location:** `110"), encoding="utf-8")
    code, output = state(room, "check")
    check.expect("check finds a finding in the wrong lens", code == 1 and "finding-in-wrong-lens" in output, output)
    check.expect("check finds a finding without severity", "finding-without-severity" in output, output)
    broken.write_text(original, encoding="utf-8")


def check_collect_and_next_round(check, book, room):
    code, output = run(CLEAN_ROOM, "collect", cwd=book)
    check.expect("collect dry run exits 0", code == 0, output)
    code, output = run(CLEAN_ROOM, "remove", "--fix", cwd=book)
    check.expect("remove refuses a room whose results are not collected",
                 code == 2 and room.is_dir(), output)
    code, output = run(CLEAN_ROOM, "collect", "--fix", cwd=book)
    collected = sorted((book / ".book" / "runs").glob("*-review-ideas-readers"))
    target = collected[0] if collected else book / ".book" / "runs" / "missing"
    check.expect("collect copies the report into a review-ideas readers run folder",
                 code == 0 and (target / "review" / "REVIEW-REPORT.md").is_file(), output)
    code, output = state(target, "findings")
    rows = output.strip().splitlines()
    check.expect("findings reads the collected run folder", code == 0 and len(rows) == 6, output)

    code, output = run(CLEAN_ROOM, "setup", "--fix", cwd=book)
    check.expect("second setup exits 0", code == 0, output)
    check.expect("second setup keeps the collected round 1 outside the room",
                 (target / "review" / "REVIEW-REPORT.md").is_file()
                 and len(list((book / ".book" / "runs").glob("*-review-ideas-readers*"))) == 1
                 and not (room / "archive").exists())
    room_state = json.loads((room / "room.json").read_text(encoding="utf-8"))
    check.expect("second setup starts round 2", room_state.get("round") == 2, room_state)
    check.expect("second setup starts an empty review", not (room / "review").exists()
                 or not any((room / "review").iterdir()))
    code, output = run(CLEAN_ROOM, "remove", "--fix", cwd=book)
    check.expect("remove takes the room away once its results are collected",
                 code == 0 and not room.exists(), output)


def check_folder_that_is_not_a_room(check, book, work):
    other_folder = work / "home-notes"
    other_folder.mkdir()
    (other_folder / "private.md").write_text("notes kept outside any book\n", encoding="utf-8")
    code, output = run(CLEAN_ROOM, "remove", "--room", str(other_folder), "--fix", cwd=book)
    check.expect("remove refuses a folder that setup did not make",
                 code == 2 and (other_folder / "private.md").is_file(), output)
    code, output = run(CLEAN_ROOM, "setup", "--room", str(other_folder), "--fix", cwd=book)
    check.expect("setup refuses a folder that holds other files",
                 code == 2 and sorted(path.name for path in other_folder.iterdir()) == ["private.md"],
                 output)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Self-check of the readers mode of the review-ideas skill. Uses only the fixture book in "
                    "tests/fixtures inside a temporary folder; never touches a real book.")
    parser.add_argument("--verbose", action="store_true", help="also print every passed check")
    parser.add_argument("--keep", action="store_true", help="keep the temporary folder and print its path")
    args = parser.parse_args(argv)
    check = SelfCheck(args.verbose)
    work = Path(tempfile.mkdtemp(prefix="readers-review-self-check-"))
    try:
        book = work / "book"
        room = work / "book-readers-review"
        shutil.copytree(FIXTURES_DIR / "book", book)
        check_help(check)
        check_skill_file(check)
        checks_file = work / "checks.txt"
        checks_file.write_text("citation checks: clean\n", encoding="utf-8")
        check_setup(check, book, room, checks_file)
        check_default_lenses(check, work)
        check_paper_room(check, work)
        check_folder_that_is_not_a_room(check, book, work)
        if room.is_dir():
            check_refresh_without_results(check, book, room, checks_file)
            check_state_progress(check, room)
            check_broken_files(check, room)
            check_collect_and_next_round(check, book, room)
    finally:
        if args.keep:
            print(f"kept    {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    print(f"TOTAL   {check.passes} passed, {len(check.failures)} failed")
    return 1 if check.failures else 0


if __name__ == "__main__":
    sys.exit(main())
