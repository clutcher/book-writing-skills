#!/usr/bin/env python3
"""Maintainer tool: nothing of one book, one author's machine or one private memory ships.

Scans every published text file (plugins/, tools/, .claude-plugin/, README.md, CLAUDE.md) for the regular expressions in .workspace/leak/leak-words.txt (kept private)
(one per line, blank lines and lines starting with # ignored). A line listed in
.workspace/leak/leak-allow.txt (`relative/path<TAB>text the line contains`) is allowed: the author's
name in plugin.json is attribution, not a leak.
Exit 0 when nothing leaks, 1 when a line does, 2 when the tool itself failed.
"""

import argparse
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPOSITORY = TOOLS.parent
SKIPPED_FOLDERS = {"__pycache__"}
PUBLISHED_PATHS = ["plugins", "tools", ".claude-plugin", "README.md", "CLAUDE.md"]
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".pdf", ".ttf", ".otf", ".woff", ".woff2", ".epub",
                   ".zip", ".gz", ".ico", ".icc", ".icm"}


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


def leaks(start, pattern, allowed):
    for path in published_files(start):
        if not path.is_file() or SKIPPED_FOLDERS & set(path.parts) \
                or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        relative = path.relative_to(REPOSITORY).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line) and not is_allowed(relative, line, allowed):
                yield f"{relative}:{number}: {line.strip()[:100]}"
        if pattern.search(path.name) and not is_allowed(relative, path.name, allowed):
            yield f"{relative}: file name"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--words", type=Path, default=REPOSITORY / ".workspace" / "leak" / "leak-words.txt")
    parser.add_argument("--allow", type=Path, default=REPOSITORY / ".workspace" / "leak" / "leak-allow.txt")
    parser.add_argument("paths", nargs="*", type=Path,
                        default=[REPOSITORY / name for name in PUBLISHED_PATHS])
    args = parser.parse_args(argv)
    if not args.words.is_file():
        print(f"SKIPPED no leak list at {args.words}")
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
