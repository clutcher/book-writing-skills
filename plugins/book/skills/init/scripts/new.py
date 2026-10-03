#!/usr/bin/env python3
"""Set up a new book in a folder: book.yaml, the folders, starter files and a tool check.

Writes the standard layout (the init skill, references/book-layout.md) and nothing the book
already has:

  book.yaml                   only the keys a new author sets; every path keeps its default
  CLAUDE.md                   what the book is, every folder, the eleven skills, the rules
  .gitignore                  the source library, work state, downloaded Vale packages and
                              editor noise, at the paths the book uses (an existing
                              .gitignore only gains the lines it lacks)
  .claude/settings.json       read-only tools that need no approval
  manuscript/                 copyright page, preface, one part, one chapter, references
  thinking/author/            stance.md, stance-details.md, audience.md
  thinking/argument/          claims.md
  thinking/doubts/            counterarguments.md, open-questions.md
  rules/decisions.md          an empty `## Index` and `## Details`
  rules/glossary.md           the entry format, no entries
  rules/voice.md              a copy of the write-text skill's default voice profile
  rules/vale/                 vale.ini and empty word lists
  sources/list.md, quotes.md  the entry formats, no entries, so the facts checks say SKIPPED
  sources/library-index/, sources/library/
  publishing/cover/           the smallest design.py, font-widths/, final/
  publishing/sales-text/      the prepare-sales-text skill's starters
  notes/                      empty: open notes only
  .book/                      runs/, output/, caches/, sources-to-add/

The starter manuscript, the thinking/argument and thinking/doubts starters, the cover
design and the sales-text files are written only while the manuscript folder has no .md
file. No folder gets a README or index file.

An existing file is never changed, except that .gitignore gains missing lines. A folder
holding an older book (a CLAUDE.md with `## Book Metadata`, or a book.yaml in the previous
layout) is refused: use existing.py. So is a folder inside another book (a book.yaml above
it). A path the book.yaml puts outside the book folder is shown and made as a full path.
After writing, the write-text skill's vale-sync.py --fix copies the Vale style into
rules/vale and runs `vale sync` in Docker (without Docker it says SKIPPED and the book is still
made), then the tool check runs (toolchain-check.py). --no-tools skips both.

Dry run by default: prints what it would write. --fix writes.
Exit 0 done (or dry run), 2 the folder cannot take a new book.
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
LIB = Path(__file__).resolve().parents[3] / "lib"
TEMPLATES = SKILL / "templates"
MARKETING_TEMPLATES = SKILL.parent / "prepare-sales-text" / "templates"
DEFAULT_VOICE = SKILL.parent / "write-text" / "profiles" / "default.md"
VALE_SYNC = SKILL.parent / "write-text" / "scripts" / "vale-sync.py"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True

from book_yaml import new_layout_paths, relative_or_none, same_values, scalar
from book_config import (CONFIG_FILE_NAMES, GLOSSARY_HEADING_SEPARATOR, LAYOUT_NEW, ConfigError,
                         find_config_file, has_fallback_sections, load_config)
from decisions import render_template

TOOL = "new"
UNSET = "TO BE ASSIGNED"
WORD_LIST_FOLDER = Path("config") / "vocabularies" / "Book"
LATEX_SPECIAL = re.compile(r"[&%$#_{}\\~^]")
LATEX_WORDS = {"\\": r"\textbackslash{}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
MARKETING_FILES = {
    "sales_text.back_cover": "back-cover.md",
    "sales_text.amazon": "amazon.html",
    "sales_text.keywords": "keywords-and-categories.md",
    "sales_text.intended_impression": "intended-impression.md",
}
IGNORE_PLACES = {"sources_library": "sources.library", "work_dir": "work.dir",
                 "vale_dir": "rules.vale"}
AUTHOR_FILES = {
    "thinking.stance": ("Stance", "The author's position on each topic of the book, one short "
                                  "section per topic. The skills read it before writing a claim."),
    "thinking.stance_details": ("Stance details", "The reasoning and the stories behind each "
                                                  "position in stance.md."),
    "thinking.audience": ("Audience", "Who the book is for, what the reader should be able "
                                      "to do after it, and what the book must show."),
}
THINKING_FILES = {
    ("thinking.argument", "claims.md"): ("Claims", "The main claims of the book, one short "
                                                   "section each, with the reasons behind them. "
                                                   "A topic that grows gets its own file here."),
    ("thinking.doubts", "counterarguments.md"): ("Counterarguments", "The strongest arguments "
                                                                     "against the book, and "
                                                                     "how the book answers "
                                                                     "each one."),
    ("thinking.doubts", "open-questions.md"): ("Open questions", "Questions the book has not "
                                                                 "settled yet."),
}
COVER_FOLDERS = ("font-widths",)
EMPTY_FOLDERS = ("thinking.argument", "thinking.doubts", "notes", "publishing.cover",
                 "cover.final", "publishing.sales_text", "rules.vale", "work.runs",
                 "work.output", "work.caches", "sources.to_add")


class Plan:
    def __init__(self, root):
        self.root = root
        self.items = []

    def planned(self, path):
        return any(item[1] == path for item in self.items)

    def folder(self, relative):
        path = self.root / relative
        if self.planned(path):
            return
        self.items.append(("folder", path, None, "keep" if path.is_dir() else "create"))

    def file(self, relative, text):
        path = self.root / relative
        self.items.append(("file", path, text, "keep" if path.exists() else "create"))

    def append_lines(self, relative, lines):
        path = self.root / relative
        if not path.exists():
            self.file(relative, "\n".join(lines) + "\n")
            return
        have = {ignore_pattern(line) for line in path.read_text(encoding="utf-8").splitlines()}
        missing = [line for line in lines if line.strip() and not line.startswith("#")
                   and ignore_pattern(line) not in have]
        self.items.append(("append", path, missing, "add" if missing else "keep"))

    def show(self):
        for kind, path, payload, action in sorted(self.items, key=lambda item: item[1]):
            shown = shown_path(self.root, path) + ("/" if kind == "folder" else "")
            detail = ""
            if kind == "append" and payload:
                detail = f"  ({len(payload)} missing line(s): {', '.join(payload)})"
            print(f"{action:7} {shown}{detail}")

    def apply(self):
        for kind, path, payload, action in self.items:
            if action == "keep":
                continue
            if kind == "folder":
                path.mkdir(parents=True, exist_ok=True)
            elif kind == "file":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(payload, encoding="utf-8")
            else:
                text = path.read_text(encoding="utf-8")
                joiner = "" if text.endswith("\n") or not text else "\n"
                path.write_text(text + joiner + "\n".join(payload) + "\n", encoding="utf-8")

    def counts(self):
        result = {}
        for _, _, _, action in self.items:
            result[action] = result.get(action, 0) + 1
        return result


def shown_path(root, path):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def ignore_pattern(line):
    return line.strip().strip("/")


def template(name, **values):
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def latex_text(text):
    return LATEX_SPECIAL.sub(lambda found: LATEX_WORDS.get(found.group(0), "\\" + found.group(0)),
                             text)


def existing_config(root):
    return next((root / name for name in CONFIG_FILE_NAMES if (root / name).is_file()), None)


def names_left_unset(root, title, author):
    config_file = existing_config(root)
    if config_file is not None:
        book = load_config(config=config_file).book
        title, author = book.title or UNSET, book.author or UNSET
    return [name for name, value in (("title", title), ("author", author)) if value == UNSET]


def book_paths(root, config_file):
    if config_file is None:
        return new_layout_paths()
    config = load_config(config=config_file)
    return {key: relative_or_absolute(root, value)
            for key, value in config.resolved_paths().items()}


def relative_or_absolute(root, value):
    if value is None:
        return None
    return relative_or_none(root, value) or Path(value).resolve().as_posix()


def gitignore_lines(paths):
    blocks = []
    for block in template("gitignore").strip("\n").split("\n\n"):
        kept = [filled for filled in (ignore_line(line, paths) for line in block.splitlines())
                if filled is not None]
        if any(line.strip() and not line.startswith("#") for line in kept):
            blocks.append("\n".join(kept))
    return "\n\n".join(blocks).splitlines()


def ignore_line(line, paths):
    for name, key in IGNORE_PLACES.items():
        if "{{" + name + "}}" not in line:
            continue
        value = paths.get(key)
        if not value or Path(value).is_absolute():
            return None
        line = line.replace("{{" + name + "}}", value.rstrip("/"))
    return line


def vale_references_glob(paths):
    references = paths.get("manuscript.references")
    if not references:
        return "*references.md"
    if Path(references).is_absolute():
        return "*" + Path(references).name
    return references


def book_yaml_text(title, author, subtitle):
    text = template("book.yaml", title=scalar(title), author=scalar(author))
    if subtitle:
        text = text.replace("  subtitle: null", f"  subtitle: {scalar(subtitle)}", 1)
    problems = same_values({"book": {"title": title, "author": author,
                                     "subtitle": subtitle or None}}, text)
    if problems:
        raise ConfigError("the book.yaml template does not read back: " + "; ".join(problems))
    return text


def stub_text(heading, line):
    return f"# {heading}\n\n{line}\n"


def manuscript_is_empty(root, paths):
    folder = root / paths["manuscript.dir"]
    return not folder.is_dir() or not any(folder.glob("*.md"))


def plan_book(root, title, author, subtitle, year):
    plan = Plan(root)
    config_file = existing_config(root)
    if config_file is None:
        plan.file("book.yaml", book_yaml_text(title, author, subtitle))
    else:
        plan.file(config_file.name, "")
    paths = book_paths(root, config_file)

    plan.file("CLAUDE.md", template("CLAUDE.md", title=title, author=author))
    plan.append_lines(".gitignore", gitignore_lines(paths))
    plan.file(".claude/settings.json", template("claude-settings.json"))
    plan.file(paths["rules.decisions"], render_template())

    manuscript = Path(paths["manuscript.dir"])
    plan.folder(manuscript)
    starting = manuscript_is_empty(root, paths)
    if starting:
        references = Path(paths["manuscript.references"]).name
        for starter in sorted((TEMPLATES / "manuscript").glob("*.md")):
            name = references if starter.name.endswith("references.md") else starter.name
            plan.file(manuscript / name, template(f"manuscript/{starter.name}", year=year,
                                                  author=latex_text(author)))

    shown = {key: value for key, value in paths.items() if value}
    plan.file(paths["sources.list"], template("sources-list.md", files=shown["sources.library"],
                                              quotes=shown["sources.quotes"]))
    plan.file(paths["sources.quotes"], template("sources-quotes.md", list=shown["sources.list"]))
    plan.folder(paths["sources.library"])
    plan.folder(paths["sources.library_index"])
    plan.file(paths["rules.glossary"],
              template("glossary.md", separator=GLOSSARY_HEADING_SEPARATOR))

    vale_ini = Path(paths["rules.vale_ini"])
    if not (root / vale_ini).exists():
        for word_list in ("accept.txt", "reject.txt"):
            plan.file(vale_ini.parent / WORD_LIST_FOLDER / word_list, "")
    plan.file(vale_ini, template("vale.ini", references_file=vale_references_glob(paths)))

    if starting:
        plan.file(paths["cover.design"], template("cover/design.py"))
        for key, name in MARKETING_FILES.items():
            plan.file(paths[key], (MARKETING_TEMPLATES / name).read_text(encoding="utf-8"))

    for key, (heading, line) in AUTHOR_FILES.items():
        plan.file(paths[key], stub_text(heading, line))
    for (key, name), (heading, line) in THINKING_FILES.items():
        if starting and paths.get(key):
            plan.file(Path(paths[key]) / name, stub_text(heading, line))
    plan.file(paths["rules.voice"], DEFAULT_VOICE.read_text(encoding="utf-8"))
    for key in EMPTY_FOLDERS:
        plan.folder(paths[key])
    for name in COVER_FOLDERS:
        plan.folder(Path(paths["publishing.cover"]) / name)
    return plan


def older_layout(root):
    config_file = existing_config(root)
    if config_file is None:
        return None
    try:
        layout = load_config(config=config_file).layout
    except ConfigError:
        return None
    return None if layout == LAYOUT_NEW else layout


def run_vale_sync(root):
    print("\n== vale", flush=True)
    exit_code = subprocess.run([sys.executable, str(VALE_SYNC), "--book", str(root),
                                "--fix"]).returncode
    if exit_code != 0:
        print(f"note: vale-sync.py exited {exit_code}, so the Vale check stays SKIPPED; run "
              f"{VALE_SYNC} --fix in the book once the problem above is fixed")
    return exit_code


def run_tool_check(root, pull):
    command = [sys.executable, str(SCRIPTS / "toolchain-check.py"), "--book", str(root)]
    if pull:
        command.append("--pull")
    print("\n== tools", flush=True)
    return subprocess.run(command).returncode


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", nargs="?", default=".",
                        help="the folder of the new book (default: the working folder)")
    parser.add_argument("--title", help=f"the book title (default: {UNSET})")
    parser.add_argument("--author", help=f"the author's name (default: {UNSET})")
    parser.add_argument("--subtitle", help="the subtitle")
    parser.add_argument("--year", help="the year on the copyright page (default: this year)")
    parser.add_argument("--fix", action="store_true", help="write the files (default: dry run)")
    parser.add_argument("--no-tools", action="store_true",
                        help="skip the Vale sync and the tool check")
    parser.add_argument("--pull-images", action="store_true",
                        help="pull the pinned Docker images the book.yaml names")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_arguments(argv)
    root = Path(args.folder).expanduser().resolve()
    if root.exists() and not root.is_dir():
        print(f"{TOOL}: {root} is a file, not a folder", file=sys.stderr)
        return 2
    enclosing = find_config_file(root.parent) if existing_config(root) is None else None
    if enclosing is not None:
        print(f"{TOOL}: {root} is inside the book at {enclosing.parent}; run new.py on that "
              f"folder to add what it lacks", file=sys.stderr)
        return 2
    claude_md = root / "CLAUDE.md"
    if existing_config(root) is None and claude_md.is_file() and has_fallback_sections(claude_md):
        print(f"{TOOL}: {claude_md} holds an older book's settings; move it with existing.py first",
              file=sys.stderr)
        return 2
    older = older_layout(root)
    if older:
        print(f"{TOOL}: {root} holds a book in the {older} layout; move it with existing.py first",
              file=sys.stderr)
        return 2
    title = args.title or UNSET
    author = args.author or UNSET
    unset_names = names_left_unset(root, title, author)
    year = args.year or str(datetime.date.today().year)
    try:
        plan = plan_book(root, title, author, args.subtitle, year)
    except (ConfigError, KeyError) as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 2

    print(f"book folder: {root}")
    plan.show()
    counts = plan.counts()
    summary = ", ".join(f"{number} {action}" for action, number in sorted(counts.items()))
    if args.fix:
        plan.apply()
        print(f"\nwritten: {summary}")
    else:
        print(f"\ndry run: {summary}. Pass --fix to write.")
        if not args.no_tools:
            print("with --fix, vale-sync.py --fix then copies the Vale style into the book and "
                  "runs 'vale sync' in Docker")
    if unset_names:
        print(f"note: {' and '.join(unset_names)} not set yet; set them in book.yaml and CLAUDE.md")
    if args.fix and not args.no_tools:
        run_vale_sync(root)
    if not args.no_tools:
        run_tool_check(root if root.is_dir() else root.parent, args.pull_images)
    return 0


if __name__ == "__main__":
    sys.exit(main())
