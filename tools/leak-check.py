#!/usr/bin/env python3
"""Maintainer tool: nothing of one book, one author's machine or one private memory ships.

Scans every published file (plugins/, tools/, .claude-plugin/, README.md, CLAUDE.md,
CHANGELOG.md, LICENSE, .gitignore) for the regular expressions in leak-words.txt (one per
line, blank lines and lines starting with # ignored). A binary file (a PDF, a font, an image)
is scanned through its printable strings, as `strings` shows them, so its metadata is checked
too. A line listed in leak-allow.txt (`relative/path<TAB>text the line contains`) is allowed:
the author's name in plugin.json is attribution, not a leak.

The two files are kept private, in the folder the environment variable BOOK_LEAK_LIST names,
or else in .workspace/leak/ of the repository. With no list, the check says SKIPPED.
Exit 0 when nothing leaks (or SKIPPED), 1 when a line does, 2 when the tool itself failed.
"""

import argparse
import os
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPOSITORY = TOOLS.parent
SKIPPED_FOLDERS = {"__pycache__"}
PUBLISHED_PATHS = ["plugins", "tools", ".claude-plugin", "README.md", "CLAUDE.md",
                   "CHANGELOG.md", "LICENSE", ".gitignore"]
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".pdf", ".ttf", ".otf", ".woff", ".woff2", ".epub",
                   ".zip", ".gz", ".ico", ".icc", ".icm"}
LEAK_LIST_VARIABLE = "BOOK_LEAK_LIST"
REPOSITORY_LEAK_FOLDER = REPOSITORY / ".workspace" / "leak"
PRINTABLE_STRING = re.compile(rb"[\x20-\x7e\t]{4,}")


def leak_list_folder():
    folder = os.environ.get(LEAK_LIST_VARIABLE)
    return Path(folder).expanduser() if folder else REPOSITORY_LEAK_FOLDER


def read_patterns(path):
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line and not line.startswith("#")]


def read_allowed(path):
    if not path.is_file():
        return []
    allowed = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "\t" in line:
            relative, text = line.split("\t", 1)
            allowed.append((relative.strip(), text))
    return allowed


def is_allowed(relative, line, allowed):
    return any(relative == allowed_path and text in line for allowed_path, text in allowed)


def published_files(start):
    return [start] if start.is_file() else sorted(start.rglob("*"))


def printable_strings(data):
    return "\n".join(found.decode("ascii") for found in PRINTABLE_STRING.findall(data))


def readable_text(path):
    data = path.read_bytes()
    if path.suffix.lower() in BINARY_SUFFIXES:
        return printable_strings(data)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return printable_strings(data)


def leaks(start, pattern, allowed):
    for path in published_files(start):
        if not path.is_file() or SKIPPED_FOLDERS & set(path.parts):
            continue
        relative = path.relative_to(REPOSITORY).as_posix()
        text = readable_text(path)
        for number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line) and not is_allowed(relative, line, allowed):
                yield f"{relative}:{number}: {line.strip()[:100]}"
        if pattern.search(path.name) and not is_allowed(relative, path.name, allowed):
            yield f"{relative}: file name"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--words", type=Path, default=leak_list_folder() / "leak-words.txt",
                        help="the leak list (default: leak-words.txt in $BOOK_LEAK_LIST, "
                             "else in .workspace/leak/)")
    parser.add_argument("--allow", type=Path, default=leak_list_folder() / "leak-allow.txt",
                        help="the allowed lines (default: leak-allow.txt beside the leak list)")
    parser.add_argument("paths", nargs="*", type=Path,
                        default=[REPOSITORY / name for name in PUBLISHED_PATHS])
    args = parser.parse_args(argv)
    if not args.words.is_file():
        print(f"SKIPPED no leak list at {args.words}; set {LEAK_LIST_VARIABLE} to the folder "
              f"holding leak-words.txt and leak-allow.txt, or pass --words FILE")
        return 0
    pattern = re.compile("|".join(f"(?:{word})" for word in read_patterns(args.words)))
    allowed = read_allowed(args.allow)
    found = [line for start in args.paths for line in leaks(start.resolve(), pattern, allowed)]
    for line in found:
        print(line)
    print(f"TOTAL  {len(found)} leak(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
