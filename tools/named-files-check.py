#!/usr/bin/env python3
"""Maintainer tool: every plugin file that a SKILL.md or a reference names must exist.

Reads every SKILL.md and every Markdown file under a skill's references/ and templates/
folders, and under lib/; and every script, for the script names and plugin paths it names.
A name counts as a plugin file when it is:

  - a relative Markdown link target               [text](references/x.md)
  - a path under ${CLAUDE_PLUGIN_ROOT}            ${CLAUDE_PLUGIN_ROOT}/skills/x/scripts/y.py
  - a path that starts with skills/ or lib/       skills/sources/scripts/fetch.py
  - a path inside the skill                       references/x.md, scripts/y.py, assets/...
  - a bare script name                            fetch.py (found in the same skill's scripts/,
                                                   in lib/, or in another skill's scripts/)

A path with a placeholder in it (<...>, {...}, *, $NAME) is left alone, and so are names of
the book's own files and of the files a run writes, which live in the book and not in the
plugin (BOOK_FILES and RUN_FILE_PATTERNS below). A backticked bare `name.md` must be a file of
the same skill (its folder, references/, templates/ or profiles/) or of lib/.
Exit 0 when every name resolves, 1 when one does not, 2 when the tool itself failed.
"""

import argparse
import re
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "book"

BOOK_FILES = {
    "design.py", "decisions.md", "whole-book.md", "some-check.py", "fact-check.md",
    "decision-matches.md", "mainstream-map.md", "citation-report.md", "glossary-report.md",
    "citations-index.md", "hard-words-summary.md",
}
RUN_FILE_PATTERNS = (re.compile(r"^hard-words-ch\w+\.md$"),)

SKILL_FOLDERS = ("references", "scripts", "templates", "assets", "profiles", "fixtures", "tests")
MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")
PLUGIN_ROOT_PATH = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)")
PLUGIN_PATH = re.compile(r"(?<![\w./$}-])((?:skills|lib)/[\w./-]+)")
SKILL_PATH = re.compile(r"(?<![\w./$}-])((?:" + "|".join(SKILL_FOLDERS) + r")/[\w./-]+)")
SCRIPT_NAME = re.compile(r"(?<![\w./$}<-])([a-z][\w-]*\.(?:py|sh))\b")
VARIABLE_SCRIPT = re.compile(r"\$\{?[A-Za-z_]\w*\}?/([a-z][\w-]*\.(?:py|sh))\b")
BACKTICKED_MARKDOWN = re.compile(r"`([a-z][\w-]*\.md)`")
PLACEHOLDER = re.compile(r"[<>{}*$]|\.\.\.")


def texts_to_read():
    for skill_md in sorted(PLUGIN.glob("skills/*/SKILL.md")):
        yield skill_md
    for folder in ("references", "templates"):
        yield from sorted(PLUGIN.glob(f"skills/*/{folder}/**/*.md"))
    yield from sorted(PLUGIN.glob("lib/*.md"))


def skill_of(path):
    parts = path.relative_to(PLUGIN).parts
    return PLUGIN / "skills" / parts[1] if parts[0] == "skills" else None


def is_book_file(name):
    name = Path(name).name
    return name in BOOK_FILES or any(pattern.match(name) for pattern in RUN_FILE_PATTERNS)


def clean(target):
    return target.split("#", 1)[0].rstrip(".,;:)`'\"")


def exists_as_script(name, skill):
    places = [PLUGIN / "lib" / name, PLUGIN / "lib" / "tests" / name]
    if skill:
        places.extend([skill / "scripts" / name, skill / "scripts" / "tests" / name,
                       skill / "tests" / name])
    places.extend(PLUGIN.glob(f"skills/*/scripts/{name}"))
    return any(place.exists() for place in places)


def missing_names(text_file):
    skill = skill_of(text_file)
    text = text_file.read_text(encoding="utf-8")
    missing = set()
    for target in MARKDOWN_LINK.findall(text):
        target = clean(target)
        if not target or target.startswith(("http:", "https:", "mailto:", "#")) \
                or PLACEHOLDER.search(target) or is_book_file(target):
            continue
        if not (text_file.parent / target).exists():
            missing.add(target)
    for target in PLUGIN_ROOT_PATH.findall(text):
        target = clean(target)
        if PLACEHOLDER.search(target) or target.endswith("/"):
            continue
        if not (PLUGIN / target).exists():
            missing.add("${CLAUDE_PLUGIN_ROOT}/" + target)
    for target in PLUGIN_PATH.findall(text):
        target = clean(target)
        if PLACEHOLDER.search(target) or "." not in Path(target).name:
            continue
        if not (PLUGIN / target).exists():
            missing.add(target)
    if skill:
        for target in SKILL_PATH.findall(text):
            target = clean(target)
            if PLACEHOLDER.search(target) or "." not in Path(target).name:
                continue
            if not (skill / target).exists() and not (text_file.parent / target).exists():
                missing.add(target)
    for name in SCRIPT_NAME.findall(text) + VARIABLE_SCRIPT.findall(text):
        if is_book_file(name):
            continue
        if not exists_as_script(name, skill):
            missing.add(name)
    if skill:
        for name in BACKTICKED_MARKDOWN.findall(text):
            if is_book_file(name):
                continue
            if not any((skill / folder / name).exists() for folder in ("", "references",
                                                                     "templates", "profiles")) \
                    and not (text_file.parent / name).exists() \
                    and not (PLUGIN / "lib" / name).exists():
                missing.add(name)
    return sorted(missing)


def scripts_to_read():
    for pattern in ("skills/*/scripts/**/*.py", "skills/*/scripts/**/*.sh", "lib/*.py"):
        for path in sorted(PLUGIN.glob(pattern)):
            if "fixtures" not in path.parts:
                yield path


def missing_script_names(script):
    skill = skill_of(script)
    text = script.read_text(encoding="utf-8")
    missing = set()
    for name in SCRIPT_NAME.findall(text) + VARIABLE_SCRIPT.findall(text):
        if not is_book_file(name) and not exists_as_script(name, skill):
            missing.add(name)
    for target in PLUGIN_ROOT_PATH.findall(text):
        target = clean(target)
        if not PLACEHOLDER.search(target) and not target.endswith("/") \
                and not (PLUGIN / target).exists():
            missing.add("${CLAUDE_PLUGIN_ROOT}/" + target)
    return sorted(missing)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.parse_args(argv)
    if not PLUGIN.is_dir():
        print(f"named-files-check: no plugin at {PLUGIN}", file=sys.stderr)
        return 2
    problems = 0
    for text_file in texts_to_read():
        for name in missing_names(text_file):
            print(f"{text_file.relative_to(PLUGIN)}\tmissing\t{name}")
            problems += 1
    for script in scripts_to_read():
        for name in missing_script_names(script):
            print(f"{script.relative_to(PLUGIN)}\tmissing\t{name}")
            problems += 1
    print(f"TOTAL  {problems} missing")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
