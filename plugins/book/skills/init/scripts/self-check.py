#!/usr/bin/env python3
"""Run the init skill's scripts on fixtures only and check what they must do.

new:      a dry run writes nothing; --fix writes the standard layout with no README or index
          file, a CLAUDE.md that names every folder and all eleven skills, and a book that
          book_config.py check accepts with no unknown key; every skill's main checks run on
          it, and run-checks.py all runs with no FAIL and finds only the starter's open work
          (the cover names generic fonts, the one-line description is not written), with
          every facts check SKIPPED while the source banks are empty; build-book.sh --show-settings lists the starter files in order; a
          second --fix changes nothing; a book in an older layout is refused; the author's
          name is safe in LaTeX; .gitignore follows the book's own paths.
old:      a copy of fixtures/old-book (settings in CLAUDE.md only) is drafted, dry-run moved
          (nothing changes), then moved: every file arrives byte-identical or merged into one
          origin file per key, book.yaml gives the same metadata and coined terms as the old
          CLAUDE.md, every file a path key named holds the same bytes at its new place, the
          banks name the new paths, the sources checks report the same findings before and
          after, and the same plan again does nothing. A plan with two files for one target, a
          folder that cannot be written, or a dropped file already in the --keep-dropped
          folder moves nothing.
previous: a copy of fixtures/previous-book (book.yaml with author/, reasons/, vocabulary/,
          style/, sources/files and origin, cover/, marketing/, reading-notes/, .book/inbox) is
          moved the same way; book.yaml keeps its comments, uses only new key names, names
          the moved cover files, and gives the same metadata and coined terms; the book reads
          as the new layout; the same plan again does nothing.
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
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PLUGIN = SCRIPTS.parents[2]
LIB = PLUGIN / "lib"
sys.path.insert(0, str(LIB))
sys.dont_write_bytecode = True

from check_output import DEFECT, INFORMATIONAL, CheckReport, add_output_arguments
from book_config import load_config

TOOL = "init-self-check"
CLASSES = {"case-failed": DEFECT, "case-passed": INFORMATIONAL}
OLD_BOOK = SCRIPTS / "fixtures" / "old-book"
PREVIOUS_BOOK = SCRIPTS / "fixtures" / "previous-book"
STORED_IGNORE_LIST = "gitignore"
RUN_CHECKS = PLUGIN / "skills" / "run-checks" / "scripts" / "run-checks.py"
SKILL_NAMES = sorted(path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md"))
FILES_CHANGED_AFTER_THE_MOVE = ("sources.list", "sources.quotes", "rules.vale_ini")
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
EXPECTED_MOVES = {
    "review/sources-registry.md": "sources/list.md",
    "review/fact-check-findings-registry.md": "sources/quotes.md",
    "review/glossary-registry.md": "rules/glossary.md",
    "review/sources/Smi99.pdf": "sources/library/Smi99.pdf",
    "review/sources/incoming/Lee20.pdf": ".book/sources-to-add/Lee20.pdf",
    "review/2025-01-02-030405/summary.md": ".book/runs/2025-01-02-030405/summary.md",
    "review/findings-inbox/Smi99.md": ".book/runs/<init run>/findings-inbox/Smi99.md",
    "personal-review/reader-notes-ch1.md": "notes/reader-notes-ch1.md",
    "research/flood-line.md": "thinking/argument/flood-line.md",
    "my-stance.md": "thinking/author/stance.md",
    "book-positioning.md": "thinking/author/audience.md",
    ".vale.ini": "rules/vale/vale.ini",
    ".vale/styles/BookRules/Very.yml": "rules/vale/BookRules/Very.yml",
    "cover/kdp-description.html": "publishing/sales-text/amazon.html",
    "cover/design_v1.py": "publishing/cover/design_v1.py",
    "output/a-fixture-book.pdf": ".book/output/a-fixture-book.pdf",
    ".link-check-cache/results.json": ".book/caches/link-check/results.json",
}
PREVIOUS_MOVES = {
    "author/stance.md": "thinking/author/stance.md",
    "author/positioning.md": "thinking/author/audience.md",
    "author/voice.md": "rules/voice.md",
    "reasons/claims.md": "thinking/argument/claims.md",
    "reasons/counterarguments.md": "thinking/doubts/counterarguments.md",
    "reasons/open-questions.md": "thinking/doubts/open-questions.md",
    "decisions.md": "rules/decisions.md",
    "vocabulary/glossary.md": "rules/glossary.md",
    "style/vale.ini": "rules/vale/vale.ini",
    "style/BookRules/Very.yml": "rules/vale/BookRules/Very.yml",
    "sources/files/Smi99.pdf": "sources/library/Smi99.pdf",
    "sources/origin/Smi99.json": "sources/library-index/Smi99.json",
    "cover/design.py": "publishing/cover/design.py",
    "cover/final/front.png": "publishing/cover/final/front.png",
    "cover/font-widths/sans.json": "publishing/cover/font-widths/sans.json",
    "marketing/back-cover.md": "publishing/sales-text/back-cover.md",
    "marketing/amazon.html": "publishing/sales-text/amazon.html",
    "reading-notes/110-chapter-1.md": "notes/110-chapter-1.md",
    ".book/inbox/list-entries.md": ".book/runs/<init run>/inbox/list-entries.md",
    ".book/inbox/incoming/mill-ledgers.pdf": ".book/sources-to-add/mill-ledgers.pdf",
    ".book/baselines/sources.json": ".book/runs/<init run>/sources.json",
}
STARTER_OPEN_WORK = {"font-check.py", "sync-check.py"}
PREVIOUS_YAML_KEEPS = ("toc: false  # the manuscript carries its own contents page",
                       "  backup: ~/fixture-sources-backup",
                       "  cover_front: publishing/cover/final/front.png",
                       "      reason: >-\n        A folded reason that runs\n        over two lines.")
OLD_KEY_LINES = ("author:", "reasons:", "marketing:", "  inbox:", "  files:", "  glossary:")
INIT_RUN_FOLDER = re.compile(r"\d{4}-\d{2}-\d{2}-\d{4}-init-existing(?:-\d+)?")
EXPECTED_DRAFT_ROWS = (
    "review/sources/\tsources/library/",
    ".vale/styles/write-good/\tDROP",
    "cover/__pycache__/\tDROP",
    "review/hard-words-tracking.md\treview/hard-words-tracking.md",
)


def source_script(name):
    return next((folder / name for folder in SOURCE_SCRIPT_FOLDERS if (folder / name).exists()),
                SOURCE_SCRIPT_FOLDERS[0] / name)


def run(command, cwd=None):
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(command, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", env=environment,
                          timeout=300)


def copy_fixture(fixture, target):
    shutil.copytree(fixture, target)
    stored_ignore_list = target / STORED_IGNORE_LIST
    if stored_ignore_list.exists():
        stored_ignore_list.rename(target / ".gitignore")


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
    old_copy = work / "refused"
    copy_fixture(OLD_BOOK, old_copy)
    refused = python(SCRIPTS / "new.py", old_copy, "--no-tools", "--fix")
    cases.expect("new: an older book's folder is refused", refused.returncode == 2,
                 refused.stdout[-200:])
    previous_copy = work / "refused-previous"
    copy_fixture(PREVIOUS_BOOK, previous_copy)
    previous_before = tree_hashes(previous_copy)
    refused = python(SCRIPTS / "new.py", previous_copy, "--no-tools", "--fix")
    cases.expect("new: a book in the previous layout is refused",
                 refused.returncode == 2 and tree_hashes(previous_copy) == previous_before,
                 refused.stderr[-200:])


def run_checks_cases(cases, book):
    facts = run([sys.executable, str(RUN_CHECKS), "facts", "--no-report"], cwd=book)
    check_lines = [line for line in facts.stdout.splitlines() if line.strip().startswith("[")]
    not_skipped = [line.strip() for line in check_lines if not line.strip().startswith("[SKIP]")]
    cases.expect("new: every facts check says SKIPPED while the source banks are empty",
                 facts.returncode == 0 and check_lines and not not_skipped,
                 "\n".join(not_skipped) + facts.stderr[-300:])
    every = run([sys.executable, str(RUN_CHECKS), "all", "--no-report", "--quiet"], cwd=book)
    found = [line.split("]", 1)[1].split()[0] for line in every.stdout.splitlines()
             if line.strip().startswith(("[FIND]", "[FAIL]"))]
    cases.expect("new: run-checks.py all finds only the starter's open work on the new book",
                 every.returncode in (0, 1) and set(found) <= STARTER_OPEN_WORK,
                 every.stdout[-600:] + every.stderr[-300:])


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


def findings(book):
    found = Counter()
    for script in SOURCES_CHECKS:
        result = python(source_script(script), "--format", "tsv", cwd=book)
        for line in result.stdout.splitlines():
            cells = line.split("\t")
            if len(cells) >= 2:
                found[(script, cells[0], cells[1])] += 1
    return found


def metadata_and_terms(book, config=None):
    chosen = ("--config", config) if config else ()
    metadata = python(LIB / "book_config.py", *chosen, "metadata", cwd=book).stdout
    shown = json.loads(python(LIB / "book_config.py", *chosen, "show", "--json", cwd=book).stdout
                       or "{}")
    return metadata, shown.get("terms", {})


def book_yaml_alone(book, work):
    folder = work / "book-yaml-alone"
    folder.mkdir()
    shutil.copy(book / "book.yaml", folder / "book.yaml")
    return folder / "book.yaml"


def moves_record(path):
    record = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        old, new, sha = (line.split("\t") + ["", ""])[:3]
        record[old] = (INIT_RUN_FOLDER.sub("<init run>", new.split("#", 1)[0]), sha)
    return record


def path_key_files(book):
    config = load_config(start=book)
    root = config.root
    found = {}
    for key, path in config.resolved_paths().items():
        if path is None or key in FILES_CHANGED_AFTER_THE_MOVE:
            continue
        path = Path(path)
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if path.is_file():
            found[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def same_path_key_files(before, after):
    return [f"{key}: {before[key]} -> {after.get(key)}" for key in before
            if after.get(key) != before[key]]


def old_book_cases(cases, work):
    book = work / "old-book"
    copy_fixture(OLD_BOOK, book)
    (book / "cover" / "__pycache__").mkdir()
    (book / "cover" / "__pycache__" / "design_v1.cpython-313.pyc").write_bytes(b"\x00bytecode")
    before = tree_hashes(book)
    old_findings = findings(book)
    old_metadata, old_terms = metadata_and_terms(book)
    old_key_files = path_key_files(book)

    draft = python(SCRIPTS / "existing.py", "draft", book, "--fix")
    plan_path = book / "move-plan.tsv"
    plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    absent = [row for row in EXPECTED_DRAFT_ROWS if row not in plan]
    cases.expect("old: draft finds the older layout and writes the plan",
                 draft.returncode == 0 and not absent, f"missing rows {absent} {draft.stderr[-300:]}")

    dry = python(SCRIPTS / "existing.py", "move", book)
    unchanged = {path: sha for path, sha in tree_hashes(book).items() if path != "move-plan.tsv"}
    cases.expect("old: a dry run moves nothing", dry.returncode == 0 and unchanged == before,
                 dry.stdout[-400:] + dry.stderr[-400:])

    moved = python(SCRIPTS / "existing.py", "move", book, "--fix")
    if not cases.expect("old: --fix moves with no problem", moved.returncode == 0,
                        moved.stdout[-600:] + moved.stderr[-600:]):
        return
    after = tree_hashes(book)
    runs = sorted((book / ".book/runs").glob("*/move-report.md"))
    record = moves_record(runs[0].parent / "moves.tsv") if runs else {}
    wrong = [f"{old} -> {new}" for old, new in EXPECTED_MOVES.items()
             if old in after or record.get(old, ("", ""))[0] != new]
    wrong += [f"{old}: sha256 {sha}" for old, (new, sha) in record.items()
              if sha not in ("merged", "") and sha != before.get(old)]
    lost = [path for path in before if path not in after and path not in record
            and not any(path.startswith(old) for old, (new, _) in record.items() if new == "DROP")]
    cases.expect("old: every file arrived byte-identical, was merged, dropped, or stayed",
                 not wrong and not lost, "; ".join(wrong + [f"lost {path}" for path in lost]))
    origin = json.loads((book / "sources/library-index/Smi99.json").read_text(encoding="utf-8"))
    fetch = json.loads((OLD_BOOK / "review/sources/Smi99.fetch.json").read_text(encoding="utf-8"))
    ocr = json.loads((OLD_BOOK / "review/sources/Smi99.ocr.json").read_text(encoding="utf-8"))
    cases.expect("old: fetch and OCR records merge into one origin file",
                 origin == {"fetch": fetch, "ocr": ocr}
                 and not (book / "review/sources/Smi99.fetch.json").exists(), str(origin))
    witness = book / "sources/library-index/Smi99.author-scan.json"
    cases.expect("old: a record whose key holds a dot merges into its own origin file",
                 witness.is_file() and not (book / "review/sources/Smi99.author-scan.fetch.json").exists()
                 and not (book / "sources/library/Smi99.author-scan.fetch.json").exists(),
                 str(sorted(path.name for path in (book / "sources/library-index").glob("*.json"))))
    cases.expect("old: DROP rows are gone",
                 not (book / "cover/__pycache__").exists()
                 and not (book / "rules/vale/write-good").exists()
                 and not (book / ".vale").exists(), "a dropped or emptied folder is still there")
    ignore_lines = (book / ".gitignore").read_text(encoding="utf-8").splitlines()
    cases.expect("old: the old .gitignore keeps its lines and gains only the missing ones",
                 ignore_lines[:2] == [".idea", "*.iml"] and ".book/" in ignore_lines
                 and "sources/library/" in ignore_lines and ".idea/" not in ignore_lines,
                 "\n".join(ignore_lines))
    new_metadata, new_terms = metadata_and_terms(book, book_yaml_alone(book, work))
    cases.expect("old: book.yaml gives the old metadata", new_metadata == old_metadata,
                 f"before:\n{old_metadata}\nafter:\n{new_metadata}")
    cases.expect("old: book.yaml gives the old coined terms", new_terms == old_terms,
                 f"{old_terms} != {new_terms}")
    changed = same_path_key_files(old_key_files, path_key_files(book))
    cases.expect("old: every file a path key named holds the same bytes at its new place",
                 not changed, "; ".join(changed))
    source_list = (book / "sources/list.md").read_text(encoding="utf-8")
    cases.expect("old: the sources list names the new cache and quotes paths",
                 "`sources/library/Smi99.txt`" in source_list
                 and "**Findings:** see `sources/quotes.md`" in source_list,
                 "cache or pointer line not rewritten")
    vale = (book / "rules/vale/vale.ini").read_text(encoding="utf-8")
    cases.expect("old: vale.ini points at the moved styles folder",
                 "StylesPath = .\n" in vale, vale[:120])
    cases.expect("old: the sources checks report the same findings before and after",
                 findings(book) == old_findings, f"{sorted(old_findings)} != {sorted(findings(book))}")
    cases.expect("old: the report, moves.tsv and the plan land in a run folder",
                 len(runs) == 1 and (runs[0].parent / "moves.tsv").is_file()
                 and (runs[0].parent / "move-plan.tsv").is_file() and not plan_path.exists(),
                 str(runs))
    if runs:
        settled = tree_hashes(book)
        again = python(SCRIPTS / "existing.py", "move", book, "--plan", runs[0].parent / "move-plan.tsv")
        cases.expect("old: the same plan again finds nothing to move",
                     again.returncode == 0 and "moves 0," in again.stdout and tree_hashes(book) == settled,
                     again.stdout[-300:])

    clash = work / "clash"
    copy_fixture(OLD_BOOK, clash)
    (clash / "move-plan.tsv").write_text("my-stance.md\tthinking/notes.md\nbook-positioning.md\t"
                                         "thinking/notes.md\n", encoding="utf-8")
    clash_before = tree_hashes(clash)
    refused = python(SCRIPTS / "existing.py", "move", clash, "--fix")
    cases.expect("old: two files for one target move nothing",
                 refused.returncode == 1 and tree_hashes(clash) == clash_before,
                 refused.stdout[-300:])
    old_book_refusal_cases(cases, work)
    old_book_drop_folder_cases(cases, work)


def old_book_drop_folder_cases(cases, work):
    book = work / "drop-folder"
    copy_fixture(OLD_BOOK, book)
    (book / "cover" / "png").mkdir(parents=True, exist_ok=True)
    (book / "cover" / "png" / "a.png").write_bytes(b"front cover")
    (book / "cover" / "old-notes.txt").write_text("old notes\n", encoding="utf-8")
    (book / "cover" / "store-text.html").write_text("<p>old</p>\n", encoding="utf-8")
    (book / "move-plan.tsv").write_text("cover/\tDROP\n"
                                        "cover/png/a.png\tcover/final/a.png\n"
                                        "cover/store-text.html\tDROP\n", encoding="utf-8")
    moved = python(SCRIPTS / "existing.py", "move", book, "--fix")
    kept = book / "cover" / "final" / "a.png"
    cases.expect("old: a file moved into a DROP folder is kept, and a DROP row inside a DROP "
                 "folder is no problem",
                 moved.returncode == 0 and kept.is_file() and kept.read_bytes() == b"front cover"
                 and not (book / "cover" / "old-notes.txt").exists()
                 and not (book / "cover" / "store-text.html").exists()
                 and not (book / "cover" / "png").exists(),
                 moved.stdout[-400:] + moved.stderr[-300:])

    if not folder_permissions_hold():
        print("SKIPPED  old: unreadable DROP folder (folder permissions do not stop this "
              "user)")
        return
    locked = work / "unreadable-drop"
    copy_fixture(OLD_BOOK, locked)
    (locked / "old-tool").mkdir()
    (locked / "old-tool" / "cache.bin").write_bytes(b"x")
    (locked / "move-plan.tsv").write_text("old-tool/\tDROP\n", encoding="utf-8")
    (locked / "old-tool").chmod(0o000)
    try:
        refused = python(SCRIPTS / "existing.py", "move", locked)
        cases.expect("old: the dry run names a DROP folder it cannot read",
                     refused.returncode == 1 and "cannot be dropped" in refused.stdout,
                     refused.stdout[-300:])
    finally:
        (locked / "old-tool").chmod(0o755)


def folder_permissions_hold():
    if sys.platform.startswith("win"):
        return False
    return not (hasattr(os, "geteuid") and os.geteuid() == 0)


def old_book_locked_folder_cases(cases, work):
    if not folder_permissions_hold():
        print("SKIPPED  old: a folder that cannot be written (folder permissions do not stop "
              "this user)")
        return
    locked = work / "locked"
    copy_fixture(OLD_BOOK, locked)
    python(SCRIPTS / "existing.py", "draft", locked, "--fix")
    (locked / "research").chmod(0o555)
    try:
        locked_before = tree_hashes(locked)
        refused = python(SCRIPTS / "existing.py", "move", locked, "--fix")
        cases.expect("old: a folder that cannot be written moves nothing",
                     refused.returncode == 1 and "cannot be written" in refused.stdout
                     and tree_hashes(locked) == locked_before, refused.stdout[-300:])
    finally:
        (locked / "research").chmod(0o755)


def old_book_refusal_cases(cases, work):
    old_book_locked_folder_cases(cases, work)

    kept = work / "keep-dropped"
    copy_fixture(OLD_BOOK, kept)
    python(SCRIPTS / "existing.py", "draft", kept, "--fix")
    earlier = work / "dropped-before" / ".vale" / "styles" / "write-good" / "Passive.yml"
    earlier.parent.mkdir(parents=True)
    earlier.write_text("kept from an earlier run\n", encoding="utf-8")
    kept_before = tree_hashes(kept)
    refused = python(SCRIPTS / "existing.py", "move", kept, "--fix", "--keep-dropped",
                     work / "dropped-before")
    cases.expect("old: --keep-dropped never writes over a file",
                 refused.returncode == 1 and tree_hashes(kept) == kept_before
                 and earlier.read_text(encoding="utf-8") == "kept from an earlier run\n",
                 refused.stdout[-300:])


def previous_cases(cases, work):
    book = work / "previous-book"
    copy_fixture(PREVIOUS_BOOK, book)
    before = tree_hashes(book)
    old_findings = findings(book)
    old_metadata, old_terms = metadata_and_terms(book)
    old_key_files = path_key_files(book)

    draft = python(SCRIPTS / "existing.py", "draft", book, "--fix")
    cases.expect("previous: draft finds the previous layout and writes the plan",
                 draft.returncode == 0 and "older layout: previous" in draft.stdout
                 and (book / "move-plan.tsv").is_file(), draft.stdout[-300:] + draft.stderr[-300:])
    dry = python(SCRIPTS / "existing.py", "move", book)
    unchanged = {path: sha for path, sha in tree_hashes(book).items() if path != "move-plan.tsv"}
    cases.expect("previous: a dry run moves nothing", dry.returncode == 0 and unchanged == before,
                 dry.stdout[-400:] + dry.stderr[-400:])
    moved = python(SCRIPTS / "existing.py", "move", book, "--fix")
    if not cases.expect("previous: --fix moves with no problem", moved.returncode == 0,
                        moved.stdout[-600:] + moved.stderr[-600:]):
        return
    after = tree_hashes(book)
    runs = sorted((book / ".book/runs").glob("*/move-report.md"))
    record = moves_record(runs[0].parent / "moves.tsv") if runs else {}
    wrong = [f"{old} -> {new}" for old, new in PREVIOUS_MOVES.items()
             if old in after or record.get(old, ("", ""))[0] != new]
    wrong += [f"{old}: sha256 {sha}" for old, (new, sha) in record.items()
              if sha not in ("merged", "") and sha != before.get(old)]
    lost = [path for path in before if path not in after and path not in record
            and not any(path.startswith(old) for old, (new, _) in record.items() if new == "DROP")]
    cases.expect("previous: every file arrived byte-identical, was dropped, or stayed",
                 not wrong and not lost, "; ".join(wrong + [f"lost {path}" for path in lost]))
    leftovers = [name for name in ("author", "reasons", "vocabulary", "style", "marketing",
                                   "reading-notes", "sources/files", "sources/origin", "cover",
                                   ".book/inbox", ".book/baselines") if (book / name).exists()]
    cases.expect("previous: no folder of the previous layout is left", not leftovers,
                 f"{leftovers}")
    cases.expect("previous: the old accepted counts go to the init run folder, not to rules/",
                 not (book / "rules" / "accepted-flags.json").exists(), "")
    yaml_text = (book / "book.yaml").read_text(encoding="utf-8")
    missing = [line for line in PREVIOUS_YAML_KEEPS if line not in yaml_text]
    old_words = [start for start in OLD_KEY_LINES
                 if any(line.startswith(start) for line in yaml_text.splitlines())]
    cases.expect("previous: book.yaml keeps its comments and values and uses new key names",
                 not missing and not old_words, f"missing {missing}, old keys {old_words}")
    check = python(LIB / "book_config.py", "check", "--format", "json", cwd=book)
    counts = json.loads(check.stdout or "{}").get("counts", {}) if check.stdout.startswith("{") else {}
    shown = json.loads(python(LIB / "book_config.py", "show", "--json", cwd=book).stdout or "{}")
    cases.expect("previous: the moved book reads as the new layout with no old or unknown key",
                 check.returncode == 0 and shown.get("layout") == "new"
                 and not {"old-key-name", "retired-key", "unknown-key"} & set(counts),
                 f"{counts} layout {shown.get('layout')}")
    new_metadata, new_terms = metadata_and_terms(book)
    expected_metadata = old_metadata.replace("cover/final/", "publishing/cover/final/")
    cases.expect("previous: book.yaml gives the old metadata, with the moved cover paths",
                 new_metadata == expected_metadata, f"before:\n{old_metadata}\nafter:\n{new_metadata}")
    cases.expect("previous: book.yaml gives the old coined terms", new_terms == old_terms,
                 f"{old_terms} != {new_terms}")
    changed = same_path_key_files(old_key_files, path_key_files(book))
    cases.expect("previous: every file a path key named holds the same bytes at its new place",
                 not changed, "; ".join(changed))
    cases.expect("previous: the sources checks report the same findings before and after",
                 findings(book) == old_findings, f"{sorted(old_findings)} != {sorted(findings(book))}")
    cases.expect("previous: the old book.yaml is kept in the run folder",
                 len(runs) == 1 and (runs[0].parent / "book.yaml.before").read_bytes()
                 == (PREVIOUS_BOOK / "book.yaml").read_bytes(), str(runs))
    if runs:
        settled = tree_hashes(book)
        again = python(SCRIPTS / "existing.py", "move", book, "--plan",
                       runs[0].parent / "move-plan.tsv")
        cases.expect("previous: the same plan again finds nothing to move",
                     again.returncode == 0 and "moves 0," in again.stdout
                     and tree_hashes(book) == settled, again.stdout[-300:])
    filled = python(SCRIPTS / "new.py", book, "--no-tools", "--fix")
    cases.expect("previous: new.py then adds only what the moved book lacks",
                 filled.returncode == 0 and all(after_hash == tree_hashes(book).get(path)
                                                for path, after_hash in after.items()
                                                if path != ".gitignore"),
                 filled.stdout[-300:] + filled.stderr[-300:])


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
        old_book_cases(cases, work)
        previous_cases(cases, work)
        tool_cases(cases, work)
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
