#!/usr/bin/env python3
"""Run the init skill's scripts on fixtures only and check what they must do.

new:      a dry run writes nothing; --fix writes the standard layout with no README or index
          file, a CLAUDE.md that names every folder and all eleven skills, and a book that
          book_config.py check accepts with no unknown key; every skill's main checks run on
          it, and run-checks.py all runs with no FAIL and finds only the starter's open work
          (the one-line description is not written), with every facts check SKIPPED while
          the source banks are empty except the two that read only the book's own text; build-book.sh --show-settings lists the starter files in order; a
          second --fix changes nothing; the author's name is safe in LaTeX; .gitignore
          follows the book's own paths.
existing: on a folder that already holds a book, new.py --fix adds only what the book lacks:
          a deleted starter file comes back and nothing else changes, an existing .gitignore
          keeps its lines and gains only the missing ones, and chapters already in
          manuscript/ keep every byte and get no starter files beside them.
vale:     new.py --fix on a machine with no Docker copies the Vale style into the book,
          says SKIPPED for `vale sync`, and still makes the book.
tools:    toolchain-check.py answers in the check contract's shape.

Everything runs in a temporary folder; no real book, no network, no Docker call except the
tool check's `docker info`.

Classes:
  case-failed   defect         a script did something other than what the case expects
  case-passed   informational  one case that matched
Exit 0 when every case passes, 1 when one fails.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PLUGIN = SCRIPTS.parents[2]
LIB = PLUGIN / "lib"
sys.path.insert(0, str(LIB))
sys.dont_write_bytecode = True

from check_output import DEFECT, INFORMATIONAL, CheckReport, add_output_arguments

TOOL = "init-self-check"
CLASSES = {"case-failed": DEFECT, "case-passed": INFORMATIONAL}
RUN_CHECKS = PLUGIN / "skills" / "run-checks" / "scripts" / "run-checks.py"
SKILL_NAMES = sorted(path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md"))
WRITING = PLUGIN / "skills" / "write-text" / "scripts"
SOURCE_SCRIPT_FOLDERS = (PLUGIN / "skills" / "check-facts" / "scripts",
                         PLUGIN / "skills" / "collect-sources" / "scripts")
BUILD = PLUGIN / "skills" / "build-editions" / "scripts" / "build-book.sh"
OTHER_CHECKS = (
    ("check-facts", "citation-check.py"),
    ("write-text", "glossary-check.py"),
    ("revise-from-notes", "open-notes.py", "check"),
    ("design-cover", "back-copy.py"),
    ("design-cover", "cover-size.py", "--pages", "100"),
    ("prepare-sales-text", "sync-check.py"),
    ("prepare-sales-text", "keyword-check.py"),
    ("prepare-sales-text", "store-description-check.py"),
)
WRITING_CHECKS = ("ascii-normalize.py", "sentence-and-paragraph-check.py",
                  "unclear-this-check.py", "word-for-two-things-check.py", "word-sense-check.py",
                  "person-introduction-check.py")
WRITING_CHECKS_NEEDING_TERMS = ("definition-check.py", "term-density-check.py")
SOURCES_CHECKS = ("entry-format-check.py", "list-quotes-join-check.py", "files-hash-check.py",
                  "ocr-marker-check.py", "duplicate-source-check.py", "key-authors-check.py",
                  "list-bibliography-check.py", "citation-key-check.py")
NEW_BOOK_FOLDERS = ("thinking/argument", "thinking/doubts", "notes", "publishing/cover/final",
                    "publishing/cover/font-widths", "sources/library", "sources/library-index",
                    ".book/runs", ".book/output", ".book/caches", ".book/sources-to-add")
STARTER_FILES = ("000-copyright.md", "010-preface.md", "100-part-one.md", "110-chapter-1.md",
                 "900-references.md")
NEW_BOOK_FILES = ("book.yaml", "CLAUDE.md", ".gitignore", ".claude/settings.json",
                  "rules/decisions.md", "sources/list.md", "sources/quotes.md",
                  "rules/glossary.md", "rules/vale/vale.ini",
                  "rules/vale/config/vocabularies/Book/accept.txt",
                  "thinking/author/stance.md", "thinking/author/stance-details.md",
                  "thinking/author/audience.md", "thinking/argument/claims.md",
                  "thinking/doubts/counterarguments.md", "thinking/doubts/open-questions.md",
                  "rules/voice.md",
                  "publishing/cover/design.py",
                  "publishing/sales-text/back-cover.md", "publishing/sales-text/amazon.html",
                  "publishing/sales-text/keywords-and-categories.md",
                  "publishing/sales-text/intended-impression.md")
STARTER_OPEN_WORK = {"sync-check.py"}
STARTER_FONT_FAMILIES = ("DejaVu Serif", "DejaVu Sans")
FACTS_CHECKS_WITHOUT_SOURCES = ("uncited-claim-check.py", "stale-argument-pointer-check.py")


def source_script(name):
    return next((folder / name for folder in SOURCE_SCRIPT_FOLDERS if (folder / name).exists()),
                SOURCE_SCRIPT_FOLDERS[0] / name)


def run(command, cwd=None):
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(command, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", env=environment,
                          timeout=300)


def python(script, *arguments, cwd=None):
    return run([sys.executable, str(script), *map(str, arguments)], cwd=cwd)


def tree_hashes(root):
    hashes = {}
    for folder, folders, names in os.walk(root):
        folders[:] = [name for name in folders if name != ".git"]
        for name in names:
            path = Path(folder) / name
            hashes[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


class Cases:
    def __init__(self, report):
        self.report = report

    def expect(self, name, condition, detail=""):
        if condition:
            self.report.add(name, "case-passed", "ok")
        else:
            self.report.add(name, "case-failed", detail or "did not hold")
        return condition


def new_cases(cases, work):
    book = work / "new-book"
    dry = python(SCRIPTS / "new.py", book, "--title", "A Book: Tested", "--author", "Ada Example",
                 "--no-tools")
    cases.expect("new: dry run writes nothing", dry.returncode == 0 and not book.exists(),
                 dry.stdout[-300:] + dry.stderr[-300:])
    made = python(SCRIPTS / "new.py", book, "--title", "A Book: Tested", "--author", "Ada Example",
                  "--no-tools", "--fix")
    missing = [name for name in NEW_BOOK_FILES + tuple(f"manuscript/{starter}"
                                                       for starter in STARTER_FILES)
               if not (book / name).exists()]
    if not cases.expect("new: --fix writes the scaffold", made.returncode == 0 and not missing,
                        f"exit {made.returncode}, missing {missing} {made.stderr[-300:]}"):
        return
    missing_folders = [name for name in NEW_BOOK_FOLDERS if not (book / name).is_dir()]
    cases.expect("new: --fix makes the empty folders", not missing_folders,
                 f"missing {missing_folders}")
    index_files = [path.relative_to(book).as_posix() for path in book.rglob("*")
                   if path.name.lower() in ("readme.md", "index.md")]
    cases.expect("new: no folder gets a README or index file", not index_files, f"{index_files}")
    allowed_tools = json.loads((book / ".claude" / "settings.json").read_text(
        encoding="utf-8"))["permissions"]["allow"]
    reads_outside_the_book = [rule for rule in allowed_tools
                              if rule in ("Read", "Bash(cat:*)") or rule.startswith("Read(/")]
    cases.expect("new: .claude/settings.json does not allow reading files outside the book",
                 not reads_outside_the_book, f"{reads_outside_the_book}")
    claude_md = (book / "CLAUDE.md").read_text(encoding="utf-8")
    unnamed_skills = [name for name in SKILL_NAMES if f"`/book:{name}`" not in claude_md]
    cases.expect("new: CLAUDE.md names all eleven skills as /book: methods",
                 len(SKILL_NAMES) == 11 and not unnamed_skills, f"{SKILL_NAMES} {unnamed_skills}")
    folders = sorted({path.relative_to(book).parts[0] for path in book.iterdir()
                      if path.is_dir() and path.name not in (".claude",)}
                     | {"/".join(path.relative_to(book).parts[:2]) for path in book.glob("*/*")
                        if path.is_dir() and path.parent.name in ("thinking", "rules",
                                                                  "publishing", "sources")})
    undescribed = [name for name in folders if f"`{name}" not in claude_md]
    cases.expect("new: CLAUDE.md describes every folder", not undescribed, f"{undescribed}")
    check = python(LIB / "book_config.py", "check", "--format", "json", cwd=book)
    counts = json.loads(check.stdout or "{}").get("counts", {}) if check.stdout.startswith("{") else {}
    cases.expect("new: book_config.py check has no unknown key",
                 check.returncode == 0 and "unknown-key" not in counts, check.stdout[-400:])
    title = python(LIB / "book_config.py", "get", "book.title", cwd=book)
    cases.expect("new: book.yaml reads back the title", title.stdout.strip() == "A Book: Tested",
                 title.stdout)
    for script in WRITING_CHECKS:
        result = python(WRITING / script, cwd=book)
        cases.expect(f"new: writing {script} passes", result.returncode == 0,
                     result.stdout[-300:] + result.stderr[-300:])
    for script in WRITING_CHECKS_NEEDING_TERMS:
        result = python(WRITING / script, cwd=book)
        cases.expect(f"new: writing {script} runs without a crash",
                     result.returncode in (0, 2) and "Traceback" not in result.stderr,
                     result.stderr[-300:])
    for script in SOURCES_CHECKS:
        result = python(source_script(script), cwd=book)
        cases.expect(f"new: sources {script} reads the empty banks", result.returncode == 0,
                     result.stdout[-300:] + result.stderr[-300:])
    for skill, script, *arguments in OTHER_CHECKS:
        result = python(PLUGIN / "skills" / skill / "scripts" / script, *arguments, cwd=book)
        cases.expect(f"new: {skill} {script} runs on the new book", result.returncode == 0,
                     result.stdout[-300:] + result.stderr[-300:])
    decisions = python(LIB / "decisions.py", "check", cwd=book)
    cases.expect("new: decisions.md passes decisions.py check", decisions.returncode == 0,
                 decisions.stdout[-300:])
    if shutil.which("bash"):
        settings = run([shutil.which("bash"), str(BUILD), "--show-settings"], cwd=book)
        listed = next((line for line in settings.stdout.splitlines()
                       if line.startswith("MANUSCRIPT_FILES=")), "")
        wanted = " ".join(f"manuscript/{starter}" for starter in STARTER_FILES)
        cases.expect("new: build --show-settings lists the starter files in order",
                     settings.returncode == 0 and listed == f"MANUSCRIPT_FILES={wanted}",
                     listed or settings.stderr[-300:])
    else:
        print("SKIPPED  new: build --show-settings (bash not found; build-book.sh needs bash)")
    run_checks_cases(cases, book)
    before = tree_hashes(book)
    again = python(SCRIPTS / "new.py", book, "--no-tools", "--fix")
    cases.expect("new: a second --fix changes nothing",
                 again.returncode == 0 and tree_hashes(book) == before and "create" not in again.stdout,
                 again.stdout[-400:])
    nested = python(SCRIPTS / "new.py", book / "manuscript", "--no-tools", "--fix")
    cases.expect("new: a folder inside a book is refused",
                 nested.returncode == 2 and not (book / "manuscript" / "book.yaml").exists(),
                 nested.stderr[-200:])
    new_path_cases(cases, work)


def run_checks_cases(cases, book):
    facts = run([sys.executable, str(RUN_CHECKS), "facts", "--no-report"], cwd=book)
    check_lines = [line for line in facts.stdout.splitlines() if line.strip().startswith("[")]
    not_skipped = [line.strip() for line in check_lines if not line.strip().startswith("[SKIP]")]
    unexpected = [line for line in not_skipped
                  if not line.startswith(tuple(f"[OK  ] {name}"
                                               for name in FACTS_CHECKS_WITHOUT_SOURCES))]
    cases.expect("new: every facts check that needs sources says SKIPPED while the source "
                 "banks are empty, and the checks of the book's own text pass",
                 facts.returncode == 0 and check_lines and not unexpected
                 and len(not_skipped) == len(FACTS_CHECKS_WITHOUT_SOURCES),
                 "\n".join(not_skipped) + facts.stderr[-300:])
    every = run([sys.executable, str(RUN_CHECKS), "all", "--no-report", "--quiet"], cwd=book)
    found = [line.split("]", 1)[1].split()[0] for line in every.stdout.splitlines()
             if line.strip().startswith(("[FIND]", "[FAIL]"))]
    open_work = STARTER_OPEN_WORK if starter_fonts_installed() else STARTER_OPEN_WORK | {
        "font-check.py"}
    cases.expect("new: run-checks.py all finds only the starter's open work on the new book",
                 every.returncode in (0, 1) and set(found) <= open_work,
                 every.stdout[-600:] + every.stderr[-300:])


def starter_fonts_installed():
    if not shutil.which("fc-match"):
        return False
    return all(family in run(["fc-match", "-f", "%{family}", family]).stdout
               for family in STARTER_FONT_FAMILIES)


def new_path_cases(cases, work):
    book = work / "own-paths"
    book.mkdir()
    (book / "book.yaml").write_text("version: 1\nwork: .work\nsources:\n  library: ../outside-cache\n",
                                    encoding="utf-8")
    made = python(SCRIPTS / "new.py", book, "--author", "Ann ~ Lee \\ Co^", "--no-tools", "--fix")
    ignored = (book / ".gitignore").read_text(encoding="utf-8") if made.returncode == 0 else ""
    cases.expect("new: .gitignore follows the book's own paths",
                 ".work/" in ignored.splitlines() and ".book/" not in ignored
                 and "sources/library/" not in ignored and (work / "outside-cache").is_dir(),
                 made.stdout[-300:] + made.stderr[-300:])
    copyright_page = book / "manuscript" / "000-copyright.md"
    text = copyright_page.read_text(encoding="utf-8") if copyright_page.exists() else ""
    cases.expect("new: the author's name is escaped for LaTeX",
                 r"Ann \textasciitilde{} Lee \textbackslash{} Co\textasciicircum{}" in text, text)


def existing_book_cases(cases, work):
    starter_file_comes_back_case(cases, work)
    existing_ignore_list_case(cases, work)
    existing_chapters_case(cases, work)


def starter_file_comes_back_case(cases, work):
    book = work / "refilled-book"
    python(SCRIPTS / "new.py", book, "--title", "Rivers of Stone", "--author", "Ada Example",
           "--no-tools", "--fix")
    before = tree_hashes(book)
    (book / "rules" / "glossary.md").unlink()
    filled = python(SCRIPTS / "new.py", book, "--no-tools", "--fix")
    created = [line for line in filled.stdout.splitlines() if line.startswith("create")]
    cases.expect("existing: new.py then adds only what the book lacks",
                 filled.returncode == 0 and tree_hashes(book) == before
                 and created == ["create  rules/glossary.md"],
                 filled.stdout[-400:] + filled.stderr[-300:])


def existing_ignore_list_case(cases, work):
    book = work / "ignore-list-book"
    book.mkdir()
    (book / ".gitignore").write_text(".idea\n*.iml\n", encoding="utf-8")
    made = python(SCRIPTS / "new.py", book, "--no-tools", "--fix")
    ignore_lines = (book / ".gitignore").read_text(encoding="utf-8").splitlines()
    cases.expect("existing: an existing .gitignore keeps its lines and gains only the missing ones",
                 made.returncode == 0 and ignore_lines[:2] == [".idea", "*.iml"]
                 and ".book/" in ignore_lines and "sources/library/" in ignore_lines
                 and ".idea/" not in ignore_lines and "*.iml" not in ignore_lines[2:],
                 "\n".join(ignore_lines) + made.stderr[-300:])


def existing_chapters_case(cases, work):
    book = work / "chapters-book"
    chapters = {
        "010-introduction.md": "# Introduction\n\nThe river was here before the town.\r\n",
        "110-the-river.md": "# The River\n\nIn 1890 the water rose above the old mill.\n",
        "120-the-mill.md": "# The Mill\n\nThe mill ground corn for forty years.",
    }
    (book / "manuscript").mkdir(parents=True)
    for name, text in chapters.items():
        (book / "manuscript" / name).write_bytes(text.encode("utf-8"))
    before = {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
              for name, text in chapters.items()}
    made = python(SCRIPTS / "new.py", book, "--no-tools", "--fix")
    after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in (book / "manuscript").glob("*.md")}
    cases.expect("existing: chapters already in manuscript/ keep every byte and get no starter "
                 "files beside them",
                 made.returncode == 0 and after == before and (book / "book.yaml").is_file(),
                 f"{sorted(after)} {made.stderr[-300:]}")


def vale_cases(cases, work):
    book = work / "no-docker-book"
    folder_with_no_tools = work / "no-tools-on-path"
    folder_with_no_tools.mkdir()
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PATH=str(folder_with_no_tools))
    made = subprocess.run([sys.executable, str(SCRIPTS / "new.py"), str(book), "--fix"],
                          capture_output=True, encoding="utf-8", errors="replace",
                          env=environment, timeout=300)
    cases.expect("vale: new.py --fix copies the Vale style and says SKIPPED without Docker",
                 made.returncode == 0 and (book / "rules" / "vale" / "PlainBook").is_dir()
                 and "SKIPPED   docker not found" in made.stdout,
                 made.stdout[-400:] + made.stderr[-300:])


def tool_cases(cases, work):
    result = python(SCRIPTS / "toolchain-check.py", "--book", work, "--format", "json")
    try:
        parsed = json.loads(result.stdout)
    except ValueError:
        parsed = None
    cases.expect("tools: toolchain-check.py reports in the contract's JSON shape",
                 result.returncode == 0 and isinstance(parsed, dict), result.stdout[-300:])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    add_output_arguments(parser)
    args = parser.parse_args(argv)
    report = CheckReport(TOOL, CLASSES)
    cases = Cases(report)
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        new_cases(cases, work)
        existing_book_cases(cases, work)
        vale_cases(cases, work)
        tool_cases(cases, work)
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
