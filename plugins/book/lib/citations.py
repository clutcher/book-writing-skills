#!/usr/bin/env python3
import argparse
import re
import sys
sys.dont_write_bytecode = True
from dataclasses import dataclass
from pathlib import Path

BARE_KEY_PATTERN = r"\w(?:\w|[:.#$%&\-+?<>~/](?=\w)|[:/](?=/))*"
BRACED_KEY_PATTERN = r"[^\s{}]+"

BARE_KEY = re.compile(BARE_KEY_PATTERN)

CITATION = re.compile(
    r"(?<![^\W_])(?<![.\\])@(?:\{(?P<braced>" + BRACED_KEY_PATTERN + r")\}"
    r"|(?P<bare>" + BARE_KEY_PATTERN + r"))")

BRACKET_GROUP = re.compile(r"\[([^\[\]]*)\](?!\()")

FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")

HIDDEN_SPANS = (
    re.compile(r"<!--.*?-->", re.DOTALL),
    re.compile(r"\$\$.*?\$\$", re.DOTALL),
    re.compile(r"(?<![\\$])\$(?=\S)[^$\n]*?(?<=\S)\$(?!\d)"),
    re.compile(r"\]\([^)\n]*\)"),
    re.compile(r"<[A-Za-z][A-Za-z0-9+.-]*:[^>\s]*>"),
    re.compile(r"<[^>\s@]+@[^>\s]+>"),
    re.compile(r"(?<![\w/])(?:https?|ftp)://[^\s<>\[\]]+"),
    re.compile(r"[^\W_][\w.!#$%&'*+/=?^`{|}~-]*@(?=\w)"),
)

CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(?:(?!\n[ \t]*\n).)*?(?<!`)\1(?!`)", re.DOTALL)


@dataclass(frozen=True)
class Citation:
    key: str
    line: int
    column: int
    braced: bool
    in_brackets: bool
    prefix: str
    locator: str

    @property
    def written(self):
        return "@{" + self.key + "}" if self.braced else "@" + self.key


def needs_braces(key):
    found = BARE_KEY.match(key)
    return not (found and found.end() == len(key))


def citation_text(key):
    return "@{" + key + "}" if needs_braces(key) else "@" + key


def hide_code(text):
    lines = text.split("\n")
    fence = None
    for index, line in enumerate(lines):
        opened = FENCE_OPEN.match(line)
        if fence is None and opened:
            fence = opened.group(1)
            lines[index] = _blank(line)
        elif fence is not None:
            closes = re.match(r"^ {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*$",
                              line)
            lines[index] = _blank(line)
            if closes:
                fence = None
    hidden = "\n".join(lines)
    hidden = CODE_SPAN.sub(lambda found: _blank(found.group(0)), hidden)
    for pattern in HIDDEN_SPANS:
        hidden = pattern.sub(lambda found: _blank(found.group(0)), hidden)
    return hidden


def _blank(text):
    return re.sub(r"[^\n]", " ", text)


def find_citations(text):
    visible = hide_code(text)
    line_starts = [0] + [index + 1 for index, character in enumerate(visible)
                         if character == "\n"]
    bracketed = _bracketed_parts(visible)
    found = []
    for match in CITATION.finditer(visible):
        key = match.group("braced") or match.group("bare")
        line = _line_of(line_starts, match.start())
        part = bracketed.get(match.start())
        prefix, locator = ("", "") if part is None else part
        found.append(Citation(key, line, match.start() - line_starts[line - 1] + 1,
                              match.group("braced") is not None, part is not None,
                              prefix, locator))
    return found


def _bracketed_parts(visible):
    parts = {}
    for group in BRACKET_GROUP.finditer(visible):
        content_start = group.start(1)
        pieces, offset = [], 0
        for piece in group.group(1).split(";"):
            pieces.append((content_start + offset, piece))
            offset += len(piece) + 1
        located = []
        for start, piece in pieces:
            matches = list(CITATION.finditer(piece))
            if len(matches) != 1:
                located = []
                break
            match = matches[0]
            prefix = piece[:match.start()].strip()
            locator = piece[match.end():].strip().lstrip(",").strip()
            located.append((start + match.start(), prefix.rstrip("-").strip(), locator))
        for position, prefix, locator in located:
            parts[position] = (prefix, locator)
    return parts


def _line_of(line_starts, position):
    low, high = 0, len(line_starts) - 1
    while low < high:
        middle = (low + high + 1) // 2
        if line_starts[middle] <= position:
            low = middle
        else:
            high = middle - 1
    return low + 1


def cited_keys(text):
    keys = []
    for citation in find_citations(text):
        if citation.key not in keys:
            keys.append(citation.key)
    return keys


def rename_key(text, old_key, new_key):
    visible = hide_code(text)
    pieces, last, count = [], 0, 0
    for match in CITATION.finditer(visible):
        key = match.group("braced") or match.group("bare")
        if key != old_key:
            continue
        pieces.append(text[last:match.start()])
        pieces.append(citation_text(new_key))
        last = match.end()
        count += 1
    pieces.append(text[last:])
    return "".join(pieces), count


def main():
    parser = argparse.ArgumentParser(
        description="List the pandoc citations (@Key, [@Key, p. 3], @{Key}) in markdown files, "
                    "one per line: file, line, key, and whether it sits in brackets.")
    parser.add_argument("files", nargs="+", help="markdown files to read")
    args = parser.parse_args()
    for name in args.files:
        try:
            text = Path(name).read_text(encoding="utf-8")
        except OSError as error:
            sys.stderr.write(f"citations: {error}\n")
            return 2
        for citation in find_citations(text):
            form = "bracket" if citation.in_brackets else "narrative"
            print(f"{name}:{citation.line}\t{citation.key}\t{form}\t{citation.locator}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
