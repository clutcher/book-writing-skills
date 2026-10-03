#!/usr/bin/env python3
"""Move an existing book into the standard layout, driven by a move plan the author can edit.

Two older layouts are found:

  old       settings in CLAUDE.md (`## Book Metadata`, `## Coined Terminology`), review/,
            research/, personal-review/, review/sources/ with fetch and OCR records beside
            each file
  previous  a book.yaml with author/, reasons/, vocabulary/, style/, sources/files/,
            sources/origin/, cover/, marketing/, reading-notes/, decisions.md, .book/inbox/

Two steps, each a dry run until --fix:

  existing.py draft [BOOK]   find the older layout and draft the move plan, a TSV file with one
                             row per path: `old path <TAB> new path or DROP <TAB> note`. A row
                             ending in `/` moves a whole folder; the most specific row wins; a
                             row whose new path equals the old one keeps the path where it is.
                             --fix writes the plan (default BOOK/move-plan.tsv); the author
                             edits it.
  existing.py move [BOOK]    carry the plan out:
                             - moves every file verbatim and checks that each one arrived
                               byte-identical (sha256 before and after); never writes over a file
                             - old layout: puts each source's fetch and OCR records
                               (<Key>.fetch.json, <Key>.ocr.json) into one file per key,
                               <sources.library_index>/<Key>.json
                             - removes what the plan marks DROP (--keep-dropped DIR moves it
                               there); a file another row moves into a DROP folder is kept
                             - old layout: writes book.yaml from the CLAUDE.md sections, plus
                               every path the plan did not send to its default, and checks
                               that it reads back to the same values
                             - previous layout: rewrites the keys of book.yaml line by line,
                               keeping comments: old key names get their new names, retired
                               keys go, a path key the move sent to its default goes, a path
                               the plan kept elsewhere is written, and the cover image paths
                               of `book:` follow their files; the rewrite must read back to the
                               intended values, and the old file is kept in the run folder
                             - points the sources list and quotes bank at their new paths
                               through the check-facts skill's entry-format-fix.py (only when
                               path lines are all it would change)
                             - points the Vale config at its moved styles folder
                             - adds the missing .gitignore lines
                             - writes a report and a TSV of every move with its sha256 to
                               <work.runs>/<YYYY-MM-DD-HHMM>-init-existing/, and moves the plan
                               there

Moving never edits a file. Nothing inside .git is read or touched. A plan with a problem
(a missing path, two files for one target, a target that exists, a folder that cannot be
written, a DROP folder that cannot be read, a dropped file that already exists in the
--keep-dropped folder) moves nothing. If a move still fails, the move stops there and writes
the report of what did move.

Exit 0 done (or a clean dry run), 1 a problem the report names, 2 the tool could not run.
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
from dataclasses import dataclass, field
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PLUGIN = SCRIPTS.parents[2]
ENTRY_FORMAT_FIX = PLUGIN / "skills" / "check-facts" / "scripts" / "entry-format-fix.py"
LIB = PLUGIN / "lib"
BOOK_CONFIG = LIB / "book_config.py"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True

from book_yaml import (ConfigLines, config_values, dump, metadata_comments, new_layout_paths,
                       plain_text, relative_or_none, same_values, scalar, settings_from_claude_md)
from book_config import (ACCEPTED_COUNTS_KEY, FALLBACK_FILE_NAME, LAYOUT_KEY, LAYOUT_NEW,
                         LAYOUT_OLD, LAYOUT_PREVIOUS, METADATA_PATH_KEYS,
                         OLD_ACCEPTED_COUNTS_FILE, PATH_KEYS,
                         PREVIOUS_LAYOUT_SIGNS, RETIRED_KEYS, ConfigError, canonical_key,
                         find_config_file, has_fallback_sections, load_config,
                         normalise_metadata_key, old_key_names, read_yaml_subset,
                         retired_key_names, with_new_key_names)
from new import THINKING_FILES, Plan, book_paths, gitignore_lines
from run_folders import next_run_folder

TOOL = "init-existing"
DROP = "DROP"
PLAN_FILE = "move-plan.tsv"
PLAN_HEADER = "# old path\tnew path or DROP\tnote"
NEVER_TOUCHED = ".git"
KEYS_NEVER_MOVED_WHOLE = {
    "work.dir": "holds everything else; its parts move one by one",
    "work.runs": "only its dated run folders move",
    "work.caches": "only the tool caches move",
    "readers_review.room": "outside the book folder",
}
KEYS_SHARING_A_FOLDER = {
    "sources.library_index": ("sources.library",
                              "the fetch and OCR records are merged, one file per key"),
    "cover.final": ("publishing.cover", "the older layout ships from the whole cover folder"),
    "publishing.sales_text": ("publishing.cover", "only the sales text files move"),
}
OLD_INBOX = "inbox"
OLD_INCOMING = "incoming"
DATED_NAME = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[-_T].*)?$")
INBOX_NAME = re.compile(r"^(?:.+-)?inbox$")
TOOL_CACHE_NAME = re.compile(r"^\.(?P<name>[\w-]+)-cache$")
ORIGIN_RECORD = re.compile(r"^(?P<key>[^/]+?)\.(?P<kind>fetch|ocr)\.json$")
STYLES_PATH_LINE = re.compile(r"^(\s*StylesPath\s*=\s*)(.*?)\s*$", re.M)
PACKAGES_LINE = re.compile(r"^\s*Packages\s*=\s*(.*?)\s*$", re.M)
BANK_PATH_CHANGES = {"cache-folder", "pointer-path"}
FIXER_COUNT_LINE = re.compile(r"^([a-z][a-z-]*)\s+(\d+)$")
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".ini", ".txt", ".tsv", ".json", ".sh", ".py", ".html"}
TEXT_NAMES = {".gitignore"}
MENTION_SIZE_LIMIT = 2_000_000
MENTIONS_SHOWN = 60
OLD_LAYOUT_SIGNS = (
    ("CLAUDE.md with ## Book Metadata or ## Coined Terminology",
     lambda root: has_fallback_sections(root / FALLBACK_FILE_NAME)),
    ("review/*-registry.md", lambda root: any((root / "review").glob("*-registry.md"))),
    ("review/sources/", lambda root: (root / "review" / "sources").is_dir()),
    ("research/", lambda root: (root / "research").is_dir()),
    ("personal-review/", lambda root: (root / "personal-review").is_dir()),
)


class PlanError(Exception):
    pass


@dataclass
class Row:
    old: str
    new: str
    note: str = ""
    line: int = 0

    @property
    def is_folder(self):
        return self.old.endswith("/")

    @property
    def drops(self):
        return self.new == DROP

    def covers(self, path):
        return path.startswith(self.old) if self.is_folder else path == self.old

    def target_of(self, path):
        if self.drops:
            return DROP
        return self.new + path[len(self.old):] if self.is_folder else self.new


@dataclass
class Book:
    root: Path
    files: list
    unreadable: list
    current: dict
    target: dict
    config: object

    @property
    def config_file(self):
        return self.config.config_file

    @property
    def raw_settings(self):
        if self.config_file is None or self.config_file.suffix == ".json":
            return {}
        return read_yaml_subset(self.config_file.read_text(encoding="utf-8"))

    def not_moved_whole(self):
        keys = dict(KEYS_NEVER_MOVED_WHOLE)
        for key, (other, why) in KEYS_SHARING_A_FOLDER.items():
            if self.current.get(key) and self.current.get(key) == self.current.get(other):
                keys[key] = why
        return keys


@dataclass
class Operations:
    moves: list = field(default_factory=list)
    merges: dict = field(default_factory=dict)
    drops: list = field(default_factory=list)
    stays: list = field(default_factory=list)
    done_rows: list = field(default_factory=list)
    problems: list = field(default_factory=list)


def sha256_of(path):
    if path.is_symlink():
        return hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def list_files(root, skip=()):
    files, unreadable = [], []

    def failed(error):
        unreadable.append(Path(error.filename).relative_to(root).as_posix() + "/")

    for folder, folders, names in os.walk(root, onerror=failed):
        relative = Path(folder).relative_to(root)
        if relative == Path("."):
            folders[:] = [name for name in folders if name != NEVER_TOUCHED]
        for name in names:
            path = (relative / name).as_posix()
            if path not in skip:
                files.append(path)
        for name in list(folders):
            if (Path(folder) / name).is_symlink():
                files.append((relative / name).as_posix())
                folders.remove(name)
    return sorted(files), sorted(unreadable)


def read_book(root, plan_path=None):
    try:
        config = load_config(start=root)
    except ConfigError as error:
        raise PlanError(f"the book's config could not be read: {error}") from error
    skip = set()
    if plan_path is not None:
        relative = relative_or_none(root, plan_path)
        if relative:
            skip.add(relative)
    files, unreadable = list_files(root, skip)
    current = {key: relative_or_none(root, value)
               for key, value in config.resolved_paths().items()}
    return Book(root, files, unreadable, current, new_layout_paths(), config)


def older_layout(root):
    config_file = find_config_file(root)
    if config_file is not None and config_file.parent == root:
        layout = load_config(config=config_file).layout
        if layout == LAYOUT_PREVIOUS:
            return layout, [f"{config_file.name} with " + ", ".join(
                sign for sign in PREVIOUS_LAYOUT_SIGNS if (root / sign).exists())]
        if layout == LAYOUT_NEW:
            return None, []
    signs = [name for name, found in OLD_LAYOUT_SIGNS if found(root)]
    return (LAYOUT_OLD, signs) if signs else (None, [])


def shown(path, is_folder):
    return path.rstrip("/") + "/" if is_folder else path


def key_rows(book):
    rows = []
    skipped = book.not_moved_whole()
    for key, old in book.current.items():
        new = book.target.get(key)
        if key in skipped or not old or not new or old in (".", new):
            continue
        path = book.root / old
        if not path.exists():
            continue
        is_folder = path.is_dir()
        rows.append(Row(shown(old, is_folder), shown(new, is_folder), f"{key}: the new default"))
    return rows


def child_rows(book, key, pattern, why):
    old, new = book.current.get(key), book.target.get(key)
    if not old or not new or old == new or not (book.root / old).is_dir():
        return []
    rows = []
    for child in sorted((book.root / old).iterdir()):
        if pattern.match(child.name) and not child.is_symlink():
            name = shown(child.name, child.is_dir())
            base = "" if old == "." else old.rstrip("/") + "/"
            rows.append(Row(base + name, new.rstrip("/") + "/" + name, why))
    return rows


def move_run_folder(book):
    runs = book.target.get("work.runs")
    return f"{runs.rstrip('/')}/{next_run_folder(book.root / runs, 'init', 'existing').name}"


def inbox_rows(book):
    old, new = book.current.get("work.runs"), book.target.get("work.runs")
    if not old or not new or not (book.root / old).is_dir():
        return []
    base = "" if old == "." else old.rstrip("/") + "/"
    holder = move_run_folder(book)
    return [Row(f"{base}{child.name}/", f"{holder}/{child.name}/",
                "staged entries of an older run: work state, kept in this move's run folder")
            for child in sorted((book.root / old).iterdir())
            if INBOX_NAME.match(child.name) and child.is_dir() and not child.is_symlink()]


def place_in_file(raw, dotted, default):
    section, _, name = dotted.partition(".")
    value = raw.get(section)
    if isinstance(value, dict) and value.get(name):
        return str(value[name])
    return default


def retired_rows(book):
    work = book.current.get("work.dir")
    if not work or work == ".":
        return []
    raw = book.raw_settings
    inbox = place_in_file(raw, "work.inbox", f"{work}/{OLD_INBOX}")
    incoming = place_in_file(raw, "sources.incoming", f"{inbox}/{OLD_INCOMING}")
    places = ((incoming, "sources.to_add", False,
               f"files added by hand (sources.incoming: {RETIRED_KEYS['sources.incoming']})"),
              (inbox, "work.runs", True,
               f"staged entries (work.inbox: {RETIRED_KEYS['work.inbox']})"))
    rows = []
    for old, key, keeps_name, why in places:
        relative = relative_or_none(book.root, book.root / old)
        new = book.target.get(key)
        if not relative or not new or not (book.root / relative).is_dir():
            continue
        if keeps_name:
            target = f"{move_run_folder(book)}/{Path(relative).name}/"
        else:
            target = f"{new}/"
        rows.append(Row(relative + "/", target, why))
    return rows


def accepted_counts_rows(book):
    work = book.current.get("work.dir")
    if not work or work == ".":
        return []
    old = (Path(work) / OLD_ACCEPTED_COUNTS_FILE).as_posix()
    if not (book.root / old).is_file():
        return []
    target = f"{move_run_folder(book)}/{OLD_ACCEPTED_COUNTS_FILE.name}"
    return [Row(old, target, f"the accepted counts ({ACCEPTED_COUNTS_KEY}: "
                             f"{RETIRED_KEYS[ACCEPTED_COUNTS_KEY]}); kept in the init run folder")]


def doubts_rows(book):
    argument = book.current.get("thinking.argument")
    doubts = book.target.get("thinking.doubts")
    if not argument or not doubts or book.current.get("thinking.doubts"):
        return []
    names = [name for (key, name) in THINKING_FILES if key == "thinking.doubts"]
    return [Row(f"{argument}/{name}", f"{doubts}/{name}", "a doubt, not a claim")
            for name in names if (book.root / argument / name).is_file()]


def tool_cache_rows(book):
    caches = book.target.get("work.caches")
    rows = []
    for child in sorted(book.root.iterdir()):
        found = TOOL_CACHE_NAME.match(child.name)
        if found and child.is_dir():
            rows.append(Row(child.name + "/", f"{caches}/{found.group('name')}/",
                            "a tool cache: work state"))
    return rows


def vale_settings(ini_path):
    text = ini_path.read_text(encoding="utf-8", errors="replace")
    styles = STYLES_PATH_LINE.search(text)
    packages = PACKAGES_LINE.search(text)
    styles_path = styles.group(2).strip() if styles else None
    names = [name.strip() for name in packages.group(1).split(",")] if packages else []
    return styles_path, [name for name in names if name]


def vale_rows(book):
    ini, new_ini = book.current.get("rules.vale_ini"), book.target.get("rules.vale_ini")
    new_style = book.target.get("rules.vale")
    if not ini or not (book.root / ini).is_file():
        return []
    styles_path, packages = vale_settings(book.root / ini)
    if not styles_path:
        return []
    styles = relative_or_none(book.root, ((book.root / ini).parent / styles_path).resolve())
    if not styles or styles == "." or not (book.root / styles).is_dir():
        return []
    rows = []
    new_styles = Path(new_ini).parent.as_posix() if new_ini else new_style
    if styles != new_styles:
        rows.append(Row(styles + "/", new_styles + "/",
                        "the Vale styles folder; vale.ini gets its new StylesPath"))
    for package in packages:
        if (book.root / styles / package).exists():
            rows.append(Row(f"{styles}/{package}/", DROP, "a Vale package: vale sync downloads it again"))
    return rows


def junk_rows(book):
    folders = sorted({str(Path(path).parent.as_posix()) for path in book.files
                      if "__pycache__" in Path(path).parts})
    tops = []
    for folder in folders:
        parts = Path(folder).parts
        top = Path(*parts[:parts.index("__pycache__") + 1]).as_posix()
        if top not in tops:
            tops.append(top)
    return [Row(top + "/", DROP, "Python bytecode") for top in tops]


def resolve(rows, path):
    best = None
    for row in rows:
        if row.covers(path) and (best is None or len(row.old) > len(best.old)):
            best = row
    return best


def without_redundant(rows):
    kept = []
    for row in sorted(rows, key=lambda item: len(item.old)):
        parent = resolve(kept, row.old)
        if parent and not row.drops and parent.target_of(row.old) == row.new:
            continue
        if not any(item.old == row.old for item in kept):
            kept.append(row)
    return kept


def stay_rows(book, rows):
    uncovered = [path for path in book.files if resolve(rows, path) is None]
    covered = set(book.files) - set(uncovered)
    result = []
    for path in uncovered:
        parts = Path(path).parts
        chosen = path
        for depth in range(1, len(parts)):
            folder = Path(*parts[:depth]).as_posix() + "/"
            if not any(other.startswith(folder) for other in covered):
                chosen = folder
                break
        if not any(existing.old == chosen or (existing.is_folder and chosen.startswith(existing.old))
                   for existing in result):
            note = "stays: no rule moves it"
            if chosen == FALLBACK_FILE_NAME and has_fallback_sections(book.root / chosen):
                note = "stays: its two settings sections become book.yaml"
            result.append(Row(chosen, chosen, note))
    for folder in book.unreadable:
        if resolve(rows, folder) is None:
            result.append(Row(folder, folder, "stays: the folder cannot be read"))
    return result


def draft_rows(book):
    rows = key_rows(book)
    rows += child_rows(book, "work.runs", DATED_NAME, "a dated run: work state, never a bank")
    rows += inbox_rows(book)
    rows += retired_rows(book)
    rows += accepted_counts_rows(book)
    rows += doubts_rows(book)
    rows += tool_cache_rows(book)
    rows += vale_rows(book)
    rows += junk_rows(book)
    rows = without_redundant(rows)
    rows += stay_rows(book, rows)
    return sorted(rows, key=lambda row: row.old)


def plan_notes(book, rows):
    files_old = book.current.get("sources.library")
    origin_new = book.target.get("sources.library_index")
    row = resolve(rows, files_old + "/") if files_old else None
    if not row or row.drops or row.old == row.new or not origin_new:
        return []
    if book.current.get("sources.library_index") != files_old:
        return []
    return [f"# {files_old}/<Key>.fetch.json and <Key>.ocr.json become {origin_new}/<Key>.json, "
            f"one file per key"]


def plan_text(rows, notes=()):
    lines = [PLAN_HEADER, *notes]
    lines += [f"{row.old}\t{row.new}\t{row.note}".rstrip("\t") for row in rows]
    return "\n".join(lines) + "\n"


def read_plan(path):
    rows, seen = [], set()
    for number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        cells = raw.split("\t")
        if len(cells) < 2:
            raise PlanError(f"line {number}: expected `old path<TAB>new path or DROP<TAB>note`")
        old, new = cells[0].strip(), cells[1].strip()
        note = cells[2].strip() if len(cells) > 2 else ""
        for value in (old, new):
            if value != DROP and (value.startswith(("/", "~")) or ".." in Path(value).parts
                                  or Path(value).parts[:1] == (NEVER_TOUCHED,)):
                raise PlanError(f"line {number}: {value!r} must be a path inside the book, "
                                f"outside {NEVER_TOUCHED}")
        if old == DROP or not old:
            raise PlanError(f"line {number}: the old path is missing")
        if new != DROP and old.endswith("/") != new.endswith("/"):
            raise PlanError(f"line {number}: a folder row ends in / on both sides")
        if old in seen:
            raise PlanError(f"line {number}: {old} has a second row")
        seen.add(old)
        rows.append(Row(old, new, note, number))
    return rows


def origin_record(book, source, target):
    files_old, files_new = book.current.get("sources.library"), book.target.get("sources.library")
    origin_new = book.target.get("sources.library_index")
    if not files_old or not origin_new or origin_new == files_new:
        return None
    if book.current.get("sources.library_index") != files_old:
        return None
    found = ORIGIN_RECORD.match(Path(source).name)
    if not found or Path(source).parent.as_posix() != files_old:
        return None
    if Path(target).parent.as_posix() != files_new:
        return None
    return found.group("key"), found.group("kind"), f"{origin_new}/{found.group('key')}.json"


def operations_for(book, rows):
    operations = Operations()
    present = set(book.files)
    for row in rows:
        if any(row.covers(path) for path in book.files) or row.old in book.unreadable:
            continue
        if row.old == row.new:
            continue
        if row.drops or (book.root / row.new).exists():
            operations.done_rows.append(row)
        else:
            operations.problems.append(f"line {row.line}: {row.old} does not exist")
    targets = {}
    for path in book.files:
        row = resolve(rows, path)
        target = row.target_of(path) if row else path
        if target == DROP:
            operations.drops.append(path)
            continue
        if target == path:
            operations.stays.append(path)
            continue
        record = origin_record(book, path, target)
        if record:
            key, kind, merged = record
            operations.merges.setdefault(merged, {})[kind] = path
            continue
        if target in targets:
            operations.problems.append(f"{path} and {targets[target]} both go to {target}")
        targets[target] = path
        if target in present or (book.root / target).exists():
            operations.problems.append(f"{path} -> {target}: the target already exists")
        operations.moves.append((path, target))
    for merged in operations.merges:
        if merged in targets or merged in present or (book.root / merged).exists():
            operations.problems.append(f"{merged}: the merged origin file already exists")
    for folder in book.unreadable:
        row = resolve(rows, folder)
        if row and not row.drops and row.target_of(folder) != folder:
            operations.problems.append(f"{folder}: cannot be read, so it cannot be moved and checked")
        elif row and row.drops:
            operations.problems.append(f"{folder}: cannot be read, so it cannot be dropped; remove "
                                       f"it by hand first (it may belong to another user, such as "
                                       f"root)")
    all_targets = set(targets) | set(operations.merges)
    for target in all_targets:
        for parent in Path(target).parents:
            if parent.as_posix() in all_targets:
                operations.problems.append(f"{parent.as_posix()} is a file target and a folder")
    check_origin_records(book, operations)
    check_writable(book, operations)
    return operations


def check_writable(book, operations):
    folders = {Path(source).parent for source, _ in operations.moves}
    folders |= {Path(source).parent for kinds in operations.merges.values()
                for source in kinds.values()}
    folders |= {Path(path).parent for path in operations.drops}
    for folder in sorted(folders):
        if not os.access(book.root / folder, os.W_OK | os.X_OK):
            shown_folder = folder.as_posix() if folder != Path(".") else "the book folder"
            operations.problems.append(f"{shown_folder}: cannot be written, so nothing can move "
                                       f"out of it")
    for source, _ in operations.moves:
        path = book.root / source
        if not path.is_symlink() and not os.access(path, os.R_OK):
            operations.problems.append(f"{source}: cannot be read, so it cannot be checked")
    targets = [target for _, target in operations.moves] + list(operations.merges)
    blocked = set()
    for target in targets:
        for parent in Path(target).parents:
            path = book.root / parent
            if not path.exists():
                continue
            if not path.is_dir():
                operations.problems.append(f"{target}: {parent.as_posix()} is a file, not a folder")
            elif not os.access(path, os.W_OK | os.X_OK) and parent not in blocked:
                blocked.add(parent)
                shown_folder = parent.as_posix() if parent != Path(".") else "the book folder"
                operations.problems.append(f"{shown_folder}: cannot be written, so nothing can "
                                           f"move into it")
            break


def check_keep_dropped(operations, keep_dropped):
    if not keep_dropped:
        return
    for path in operations.drops:
        if (Path(keep_dropped) / path).exists():
            operations.problems.append(f"{path}: already in {keep_dropped}; the move never "
                                       f"writes over a file")


def check_origin_records(book, operations):
    for merged, kinds in operations.merges.items():
        for kind, source in kinds.items():
            try:
                data = json.loads((book.root / source).read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                operations.problems.append(f"{source}: not readable JSON ({error})")
                continue
            if not isinstance(data, dict):
                operations.problems.append(f"{source}: not a JSON object")


def effective_path(rows, relative, is_folder):
    probe = shown(relative, is_folder)
    row = resolve(rows, probe)
    if row is None:
        return relative
    target = row.target_of(probe)
    return None if target == DROP else target.rstrip("/")


def book_yaml_settings(book, rows):
    claude_md = book.root / FALLBACK_FILE_NAME
    if has_fallback_sections(claude_md):
        settings = settings_from_claude_md(claude_md)
        comments = {f"book.{key}": text
                    for key, text in metadata_comments(claude_md.read_text(encoding="utf-8")).items()}
    else:
        settings, comments = {"version": 1}, {}
    settings.pop("work", None)
    settings.get("manuscript", {}).pop("dir", None)
    if "manuscript" in settings and not settings["manuscript"]:
        settings.pop("manuscript")
    for name in METADATA_PATH_KEYS:
        value = (settings.get("book") or {}).get(name)
        after = moved_value(book, rows, value)
        if after is not None:
            settings["book"][name] = after
            comments[f"book.{name}"] = "the file moved here with the move plan"
    skipped = book.not_moved_whole()
    for key, old in book.current.items():
        if key in skipped or not old or old == "." or not (book.root / old).exists():
            continue
        after = effective_path(rows, old, (book.root / old).is_dir())
        if after is None or after == book.target.get(key):
            continue
        node = settings
        parts = key.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = after
        comments[key] = "kept where the move plan left it"
    return settings, comments


def has_dotted(settings, dotted):
    node = settings
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def get_dotted(settings, dotted):
    node = settings
    for part in dotted.split("."):
        node = node[part]
    return node


def set_dotted(settings, dotted, value):
    parts = dotted.split(".")
    node = settings
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def pop_dotted(settings, dotted):
    parts = dotted.split(".")
    parents = [settings]
    for part in parts[:-1]:
        parents.append(parents[-1][part])
    parents[-1].pop(parts[-1])
    for depth in range(len(parts) - 1, 0, -1):
        if parents[depth] == {}:
            parents[depth - 1].pop(parts[depth - 1])


def rewritten_config(book, rows):
    text = book.config_file.read_text(encoding="utf-8")
    data = read_yaml_subset(text)
    editor = ConfigLines(text)
    expected = with_new_key_names(data)
    changes = []
    if LAYOUT_KEY in data:
        editor.remove(LAYOUT_KEY)
        expected.pop(LAYOUT_KEY, None)
        changes.append(f"removed {LAYOUT_KEY}: the folders now show the standard layout")
    for key in retired_key_names(data):
        editor.remove(key)
        changes.append(f"removed {key}: {RETIRED_KEYS[key]}")
    for old in old_key_names(data):
        new = canonical_key(old)
        if has_dotted(data, new):
            editor.remove(old)
            changes.append(f"removed {old}: {new} is also set, and the new name wins")
        else:
            editor.move(old, new)
            changes.append(f"renamed {old} -> {new}")
    path_changes(book, rows, editor, expected, changes)
    metadata_path_changes(book, rows, editor, expected, changes)
    new_text = editor.text()
    problems = []
    try:
        written = read_yaml_subset(new_text)
    except ConfigError as error:
        written, problems = None, [f"the rewritten file does not read: {error}"]
    if written is not None and plain_text(written) != plain_text(expected):
        problems.append("the rewritten file does not read back to the intended values")
    return new_text, changes, problems


def path_changes(book, rows, editor, expected, changes):
    skipped = book.not_moved_whole()
    for key in PATH_KEYS:
        old = book.current.get(key)
        if key in skipped or not old or old == "." or not (book.root / old).exists():
            continue
        after = effective_path(rows, old, (book.root / old).is_dir())
        default = book.target.get(key)
        if after is None:
            continue
        if has_dotted(expected, key):
            if after == default:
                editor.remove(key)
                pop_dotted(expected, key)
                changes.append(f"removed {key}: {after} is now its default")
            elif after != old:
                editor.set_value(key, after)
                set_dotted(expected, key, after)
                changes.append(f"{key}: {old} -> {after}")
        elif after != default:
            editor.add(key, [f"{key.rpartition('.')[2]}: {scalar(after)}"])
            set_dotted(expected, key, after)
            changes.append(f"added {key}: {after} (the move plan keeps it there)")


def metadata_path_changes(book, rows, editor, expected, changes):
    metadata = expected.get("book")
    if not isinstance(metadata, dict):
        return
    for raw_key in list(metadata):
        if normalise_metadata_key(str(raw_key)) not in METADATA_PATH_KEYS:
            continue
        after = moved_value(book, rows, metadata[raw_key])
        if after is None:
            continue
        changes.append(f"book.{raw_key}: {metadata[raw_key]} -> {after}")
        editor.set_value(f"book.{raw_key}", after)
        metadata[raw_key] = after


def book_yaml_text(settings, comments):
    head = ("# Written by the init skill (existing) from the CLAUDE.md sections `## Book Metadata`\n"
            "# and `## Coined Terminology`. Every key: the init skill, references/book-yaml.md.\n")
    return head + "\n" + dump(settings, comments) + "\n"


def moved_value(book, rows, value):
    if not isinstance(value, str) or not value or value.startswith(("/", "~")):
        return None
    relative = relative_or_none(book.root, book.root / value)
    if not relative or relative == "." or not (book.root / relative).exists():
        return None
    after = effective_path(rows, relative, (book.root / relative).is_dir())
    return after if after and after != relative else None


def compare_with_claude_md(book, text, rows=()):
    claude_md = book.root / FALLBACK_FILE_NAME
    if not has_fallback_sections(claude_md):
        return []
    old = config_values(load_config(config=claude_md))
    for name in METADATA_PATH_KEYS:
        after = moved_value(book, rows, old["book"].get(name))
        if after is not None:
            old["book"][name] = after
    with tempfile.TemporaryDirectory() as folder:
        written = Path(folder) / "book.yaml"
        written.write_text(text, encoding="utf-8")
        new = config_values(load_config(config=written))
    problems = []
    for key, value in old["book"].items():
        if plain_text(new["book"].get(key)) != value:
            problems.append(f"book.{key}: {value!r} reads back as {new['book'].get(key)!r}")
    if old["terms"] != new["terms"]:
        problems.append("terms: the coined terms read back differently")
    return problems


def move_file(root, source, target):
    source_path, target_path = root / source, root / target
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        source_path.rename(target_path)
        return
    except OSError:
        shutil.copy2(source_path, target_path, follow_symlinks=False)
    try:
        source_path.unlink()
    except OSError:
        target_path.unlink()
        raise


def merge_records(root, merged, kinds):
    data = {}
    for kind, source in sorted(kinds.items()):
        data[kind] = json.loads((root / source).read_text(encoding="utf-8"))
    path = root / merged
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    written = json.loads(path.read_text(encoding="utf-8"))
    return all(written.get(kind) == data[kind] for kind in kinds)


def drop_units(rows, operations, arrived):
    folder_rows = sorted({row.old for row in rows if row.drops and row.is_folder
                          and any(row.covers(path) for path in operations.drops)})
    whole_folders = []
    for folder in folder_rows:
        if any(folder.startswith(outer) for outer in whole_folders):
            continue
        if any(target.startswith(folder) for target in arrived):
            continue
        whole_folders.append(folder)
    single_files = [path for path in operations.drops
                    if not any(path.startswith(folder) for folder in whole_folders)]
    return sorted(whole_folders + single_files)


def drop_path(root, relative, keep_dropped):
    path = root / relative
    if keep_dropped:
        target = Path(keep_dropped) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))
    elif path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def remove_empty_folders(root, relatives):
    folders = set()
    for relative in relatives:
        folders.update(parent for parent in Path(relative).parents if parent != Path("."))
    for folder in sorted(folders, key=lambda item: len(item.parts), reverse=True):
        path = root / folder
        if path.is_dir() and not path.is_symlink() and not any(path.iterdir()):
            path.rmdir()


def fix_vale_config(book, rows):
    old_ini = book.current.get("rules.vale_ini")
    if not old_ini:
        return None
    new_ini = effective_path(rows, old_ini, False)
    if not new_ini or not (book.root / new_ini).is_file():
        return None
    text = (book.root / new_ini).read_text(encoding="utf-8")
    found = STYLES_PATH_LINE.search(text)
    if not found:
        return None
    old_styles = relative_or_none(book.root, ((book.root / old_ini).parent / found.group(2)).resolve())
    if old_styles is None:
        return None
    new_styles = effective_path(rows, old_styles, True)
    if not new_styles:
        return None
    wanted = os.path.relpath(book.root / new_styles, (book.root / new_ini).parent)
    wanted = Path(wanted).as_posix()
    if found.group(2) == wanted:
        return None
    fixed = text[:found.start(2)] + wanted + text[found.end(2):]
    (book.root / new_ini).write_text(fixed, encoding="utf-8")
    return f"{new_ini}: StylesPath {found.group(2)} -> {wanted}"


def run_bank_fixer(root, config_path, fix):
    command = [sys.executable, str(ENTRY_FORMAT_FIX), "--config", str(config_path)]
    if fix:
        command.append("--fix")
    result = subprocess.run(command, cwd=root, capture_output=True, encoding="utf-8", errors="replace")
    kinds = {}
    for line in result.stdout.splitlines():
        found = FIXER_COUNT_LINE.match(line.strip())
        if found:
            kinds[found.group(1)] = kinds.get(found.group(1), 0) + int(found.group(2))
    return result.returncode, kinds, result.stdout + result.stderr


def fix_bank_paths(root, config_path):
    if not ENTRY_FORMAT_FIX.is_file():
        return "SKIPPED: the check-facts skill's entry-format-fix.py was not found"
    config = load_config(config=config_path)
    if not (config.sources.list and config.sources.list.is_file()):
        return "no sources list: nothing to point at new paths"
    code, kinds, output = run_bank_fixer(root, config_path, fix=False)
    if code == 2:
        return f"FAILED: entry-format-fix.py could not run:\n{output.strip()[-600:]}"
    if not kinds:
        return "the banks already name the new paths"
    other = {kind: count for kind, count in kinds.items() if kind not in BANK_PATH_CHANGES}
    if other:
        listed = ", ".join(f"{kind} {count}" for kind, count in sorted(other.items()))
        return (f"NOT DONE: entry-format-fix.py would also change more than paths ({listed}). "
                f"Review its dry run and run it with --fix yourself; it rewrites the paths too.")
    code, kinds, output = run_bank_fixer(root, config_path, fix=True)
    listed = ", ".join(f"{kind} {count}" for kind, count in sorted(kinds.items()))
    return f"paths rewritten through entry-format-fix.py ({listed})"


def add_gitignore_lines(root, config_path, fix):
    plan = Plan(root)
    plan.append_lines(".gitignore", gitignore_lines(book_paths(root, config_path)))
    kind, path, payload, action = plan.items[0]
    added = payload if kind == "append" else ["(new file)"]
    if action == "keep":
        return []
    if fix:
        plan.apply()
    return added


def old_path_mentions(root, rows, skip_folders):
    wanted = [row.old for row in rows if row.old != row.new and not row.drops
              and not DATED_NAME.match(Path(row.old.rstrip("/")).name)]
    if not wanted:
        return []
    mentions = []
    files, _ = list_files(root)
    for relative in files:
        if any(relative.startswith(folder) for folder in skip_folders):
            continue
        path = root / relative
        if (path.suffix not in TEXT_SUFFIXES and path.name not in TEXT_NAMES) or path.is_symlink():
            continue
        try:
            if path.stat().st_size > MENTION_SIZE_LIMIT:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for old in wanted:
            count = len(re.findall(r"(?<![\w./-])" + re.escape(old), text))
            if count:
                mentions.append((relative, old, count))
    return mentions


def draft(args):
    root = Path(args.book).expanduser().resolve()
    plan_path = Path(args.plan) if args.plan else root / PLAN_FILE
    layout, signs = older_layout(root)
    if layout is None:
        print(f"{TOOL}: no older layout found in {root} (looked for: a book.yaml with "
              f"{', '.join(PREVIOUS_LAYOUT_SIGNS)}; or "
              f"{', '.join(name for name, _ in OLD_LAYOUT_SIGNS)})", file=sys.stderr)
        return 2
    book = read_book(root, plan_path)
    rows = draft_rows(book)
    text = plan_text(rows, plan_notes(book, rows))
    print(f"book folder: {root}\nolder layout: {layout} ({'; '.join(signs)})\n")
    print(text, end="")
    moving = sum(1 for row in rows if row.old != row.new)
    print(f"\n{len(rows)} row(s): {moving} move or drop, {len(rows) - moving} stay")
    if args.fix:
        if plan_path.exists() and not args.force:
            print(f"{TOOL}: {plan_path} exists; pass --force to write over it", file=sys.stderr)
            return 2
        plan_path.write_text(text, encoding="utf-8")
        print(f"wrote {plan_path}. Edit it, then: existing.py move {root}")
    else:
        print(f"dry run: pass --fix to write the plan to {plan_path}")
    return 0


class Report:
    def __init__(self):
        self.lines = []
        self.problem_count = 0

    def say(self, text=""):
        self.lines.append(text)
        print(text)

    def problem(self, text):
        self.problem_count += 1
        self.say(f"PROBLEM  {text}")


def move(args):
    root = Path(args.book).expanduser().resolve()
    plan_path = Path(args.plan) if args.plan else root / PLAN_FILE
    if not plan_path.is_file():
        print(f"{TOOL}: no move plan at {plan_path}; write one with: existing.py draft --fix",
              file=sys.stderr)
        return 2
    rows = read_plan(plan_path)
    book = read_book(root, plan_path)
    operations = operations_for(book, rows)
    check_keep_dropped(operations, args.keep_dropped)
    report = Report()
    report.say(f"# Move into the standard layout\n\nbook folder: {root}\nplan: {plan_path}\n")
    report.say(f"moves {len(operations.moves)}, origin files {len(operations.merges)} "
               f"(from {sum(len(kinds) for kinds in operations.merges.values())} records), "
               f"drops {len(operations.drops)}, stays {len(operations.stays)}, "
               f"rows already done {len(operations.done_rows)}")
    for problem in operations.problems:
        report.problem(problem)

    has_config = book.config_file is not None and book.config_file.parent == root
    config_changes = []
    if has_config and book.config_file.suffix == ".json":
        yaml_text = None
    elif has_config:
        yaml_text, config_changes, config_problems = rewritten_config(book, rows)
        for problem in config_problems:
            report.problem(f"{book.config_file.name}: {problem}")
    else:
        settings, comments = book_yaml_settings(book, rows)
        yaml_text = book_yaml_text(settings, comments)
        for difference in (same_values(settings, yaml_text)
                           + compare_with_claude_md(book, yaml_text, rows)):
            report.problem(f"book.yaml: {difference}")
    if operations.problems or report.problem_count:
        report.say("\nNothing was moved: fix the plan and run again.")
        return 1

    if not args.fix:
        report.say("\n## book.yaml that would be written\n")
        for change in config_changes:
            report.say(f"change {change}")
        if has_config and not config_changes:
            report.say("(no key to rename or path to change; the file stays as it is)")
        elif yaml_text is None:
            report.say("(book.json: left alone; rename its keys by hand)")
        else:
            report.say(yaml_text)
        for source, target in operations.moves[:MENTIONS_SHOWN]:
            report.say(f"move   {source} -> {target}")
        if len(operations.moves) > MENTIONS_SHOWN:
            report.say(f"... and {len(operations.moves) - MENTIONS_SHOWN} more moves")
        for merged, kinds in sorted(operations.merges.items())[:MENTIONS_SHOWN]:
            report.say(f"merge  {', '.join(sorted(kinds.values()))} -> {merged}")
        for path in operations.drops[:MENTIONS_SHOWN]:
            report.say(f"drop   {path}")
        report.say("\ndry run: nothing moved. Pass --fix to move.")
        return 0

    run_folder = next_run_folder(root / book.target["work.runs"], "init", "existing")
    stamp = run_folder.name
    hashes = {source: sha256_of(root / source) for source, _ in operations.moves}
    moved = []
    for source, target in operations.moves:
        try:
            move_file(root, source, target)
        except OSError as error:
            report.problem(f"{source} -> {target}: the move failed ({error.strerror}); the move "
                           f"stopped here, and {source} is still in its old place")
            break
        moved.append((source, target))
    if len(moved) < len(operations.moves):
        return stop_after_failed_move(root, book, plan_path, report, moved, hashes, stamp)
    moved_rows = []
    for source, target in operations.moves:
        after = sha256_of(root / target)
        if after != hashes[source]:
            report.problem(f"{source} -> {target}: sha256 changed ({hashes[source]} -> {after})")
        moved_rows.append(f"{source}\t{target}\t{after}")
    for merged, kinds in sorted(operations.merges.items()):
        if merge_records(root, merged, kinds):
            for kind, source in sorted(kinds.items()):
                (root / source).unlink()
                moved_rows.append(f"{source}\t{merged}#{kind}\tmerged")
        else:
            report.problem(f"{merged}: the merged records do not read back as the originals")
    arrived = [target for _, target in operations.moves] + list(operations.merges)
    dropped_tops = drop_units(rows, operations, arrived)
    for relative in dropped_tops:
        try:
            drop_path(root, relative.rstrip("/"), args.keep_dropped)
            moved_rows.append(f"{relative}\t{DROP}\t")
        except OSError as error:
            report.problem(f"{relative}: could not drop ({error.strerror}); remove it by hand")
    remove_empty_folders(root, [source for source, _ in operations.moves]
                         + [path for kinds in operations.merges.values() for path in kinds.values()]
                         + [path.rstrip("/") + "/x" for path in dropped_tops])

    report.say("\n## Settings and paths")
    config_path = book.config_file if has_config else root / "book.yaml"
    if yaml_text is None:
        report.say("book.json: left alone; rename its keys by hand")
    elif has_config and not config_changes:
        report.say(f"{config_path.name}: no key to rename or path to change")
    elif has_config:
        run_folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config_path, run_folder / f"{config_path.name}.before")
        config_path.write_text(yaml_text, encoding="utf-8")
        report.say(f"rewrote {config_path.name} (the old file: {config_path.name}.before in the "
                   f"run folder); it reads back to the intended values")
        for change in config_changes:
            report.say(f"  {change}")
    else:
        config_path.write_text(yaml_text, encoding="utf-8")
        report.say("wrote book.yaml; it reads back to the values of the CLAUDE.md sections")
    vale = fix_vale_config(book, rows)
    report.say(vale or "Vale config: nothing to point elsewhere")
    banks = fix_bank_paths(root, config_path)
    if banks.startswith(("FAILED", "NOT DONE")):
        report.problem(banks)
    else:
        report.say(f"sources banks: {banks}")
    added = add_gitignore_lines(root, config_path, fix=True)
    report.say(f".gitignore: added {', '.join(added)}" if added else ".gitignore: complete")
    check = subprocess.run([sys.executable, str(BOOK_CONFIG), "--config", str(config_path),
                            "check"], capture_output=True, encoding="utf-8", errors="replace", cwd=root)
    report.say(f"book_config.py check: exit {check.returncode}; "
               f"{(check.stdout.strip().splitlines() or [''])[-1]}")
    if check.returncode != 0:
        report.problem("book.yaml has keys no script reads:\n" + check.stdout)

    run_folder.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan_path), str(run_folder / PLAN_FILE))
    mentions = old_path_mentions(root, rows, [book.target["work.dir"] + "/",
                                              book.target["sources.library"] + "/"])
    report.say("\n## Files that still name an old path (update them by hand)")
    for relative, old, count in mentions[:MENTIONS_SHOWN]:
        report.say(f"{relative}\t{old}\t{count}")
    if len(mentions) > MENTIONS_SHOWN:
        report.say(f"... and {len(mentions) - MENTIONS_SHOWN} more")
    if not mentions:
        report.say("none")

    (run_folder / "moves.tsv").write_text("# old path\tnew path\tsha256\n"
                                          + "\n".join(moved_rows) + "\n", encoding="utf-8")
    report.say(f"\nmoves checked: {len(operations.moves)} byte-identical, "
               f"{report.problem_count} problem(s)")
    report.say(f"report, moves.tsv and the plan: {run_folder}")
    (run_folder / "move-report.md").write_text("\n".join(report.lines) + "\n", encoding="utf-8")
    return 1 if report.problem_count else 0


def stop_after_failed_move(root, book, plan_path, report, moved, hashes, stamp):
    run_folder = root / book.target["work.runs"] / stamp
    run_folder.mkdir(parents=True, exist_ok=True)
    rows = [f"{source}\t{target}\t{sha256_of(root / target)}" for source, target in moved]
    for source, target in moved:
        if sha256_of(root / target) != hashes[source]:
            report.problem(f"{source} -> {target}: sha256 changed")
    (run_folder / "moves.tsv").write_text("# old path\tnew path\tsha256\n" + "\n".join(rows) + "\n",
                                          encoding="utf-8")
    report.say(f"\n{len(moved)} file(s) moved before the failure; nothing was merged, dropped or "
               f"written. moves.tsv lists them. The plan stays at {plan_path}: fix the problem, "
               f"then run the same plan again to move the rest.")
    report.say(f"report and moves.tsv: {run_folder}")
    (run_folder / "move-report.md").write_text("\n".join(report.lines) + "\n", encoding="utf-8")
    return 1


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    steps = parser.add_subparsers(dest="step", required=True)
    for name, text in (("draft", "draft the move plan from the older layout"),
                       ("move", "carry out the move plan")):
        step = steps.add_parser(name, help=text)
        step.add_argument("book", nargs="?", default=".", help="the book folder (default: here)")
        step.add_argument("--plan", help=f"the move plan (default: BOOK/{PLAN_FILE})")
        step.add_argument("--fix", action="store_true", help="write (default: dry run)")
        if name == "draft":
            step.add_argument("--force", action="store_true", help="write over an existing plan")
        else:
            step.add_argument("--keep-dropped", metavar="DIR",
                              help="move what the plan drops into DIR instead of deleting it")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_arguments(argv)
    try:
        return draft(args) if args.step == "draft" else move(args)
    except (PlanError, ConfigError) as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
