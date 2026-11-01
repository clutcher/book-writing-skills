#!/usr/bin/env python3
"""Maintainer tool: every Markdown file the plugin copies into a book keeps each paragraph on one line.

Reads every .md file under a skill's templates/ and profiles/ folders: the files init, the
reviews and the sales text copy or fill into a book. A paragraph, a list item and a blockquote
paragraph must each be one line, never broken at a column.

These stay line-based and are never joined:

  - headings, tables, fenced code, pandoc fenced divs (:::), HTML and HTML comments
  - a bare > line, the break between two paragraphs of one blockquote
  - a field line that starts with a bold label, like **From:** or **Note:**
  - YAML front matter, link definitions, horizontal rules
  - a setting line, like sentence_min_words: 10 under a voice profile's ## Settings
  - a line that ends in a hard break (two spaces or a backslash)

Dry run by default: lists each broken paragraph. --fix joins the broken lines.
Exit 0 when every paragraph is one line (or after --fix), 1 when one is broken, 2 when the
tool itself failed.
"""

import argparse
import re
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
PLUGIN = REPOSITORY / "plugins" / "book"
BOOK_FILE_FOLDERS = ("templates", "profiles")

FENCE = re.compile(r"^\s*(```|~~~)")
LINE_BASED = re.compile(r"^\s*(#|\||:::|</?[A-Za-z][\w-]*(\s[^>]*)?/?>|\[[^\]]+\]:\s|(-{3,}|\*{3,}|_{3,}|>)\s*$)|^[a-z_][a-z0-9_.]*:\s")
FIELD_LINE = re.compile(r"^\s*\*\*[^*]+\*\*")
BLOCK_START = re.compile(r"^\s*([-*+]|\d+[.)])\s+|^\s*>")
QUOTE_MARK = re.compile(r"^\s*>\s?")
HARD_BREAK = re.compile(r"(  |\\)$")


class Markdown:

    def __init__(self, text):
        self.lines = text.split("\n")

    def joined(self):
        result = []
        open_block = False
        for line, is_prose in self.classified():
            if is_prose and open_block and self.continues(line, result[-1]):
                result[-1] = result[-1].rstrip() + " " + self.content_of(line)
                continue
            result.append(line)
            open_block = is_prose and not HARD_BREAK.search(line)
        return "\n".join(result)

    def classified(self):
        in_fence = False
        in_comment = False
        in_front_matter = self.lines[:1] == ["---"]
        for number, line in enumerate(self.lines):
            stripped = line.strip()
            if in_front_matter:
                in_front_matter = number == 0 or stripped != "---"
                yield line, False
            elif FENCE.match(line):
                in_fence = not in_fence
                yield line, False
            elif in_fence:
                yield line, False
            elif in_comment or stripped.startswith("<!--"):
                in_comment = "-->" not in stripped
                yield line, False
            else:
                yield line, bool(stripped) and not LINE_BASED.match(line)

    @staticmethod
    def continues(line, previous):
        if QUOTE_MARK.match(line):
            return QUOTE_MARK.match(previous) and QUOTE_MARK.sub("", line).strip() != ""
        return not BLOCK_START.match(line) and not FIELD_LINE.match(line)

    @staticmethod
    def content_of(line):
        return QUOTE_MARK.sub("", line, count=1).strip() if QUOTE_MARK.match(line) else line.strip()


def book_files():
    for folder in BOOK_FILE_FOLDERS:
        yield from sorted(PLUGIN.glob(f"skills/*/{folder}/**/*.md"))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="paragraph-lines-check.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fix", action="store_true", help="join the broken lines in place")
    arguments = parser.parse_args(argv)
    try:
        broken = []
        for path in book_files():
            text = path.read_text(encoding="utf-8")
            joined = Markdown(text).joined()
            if joined == text:
                continue
            broken.append(path)
            if arguments.fix:
                path.write_text(joined, encoding="utf-8")
    except OSError as error:
        print(f"paragraph-lines-check: {error}", file=sys.stderr)
        return 2
    for path in broken:
        verb = "joined" if arguments.fix else "broken paragraph lines in"
        print(f"{verb} {path.relative_to(REPOSITORY).as_posix()}")
    if broken and not arguments.fix:
        print(f"{len(broken)} file(s) break a paragraph across lines; run with --fix to join them")
        return 1
    print("every paragraph is one line" if not broken else f"joined {len(broken)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
