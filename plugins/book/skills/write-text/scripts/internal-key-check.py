#!/usr/bin/env python3
"""Find internal keys in the text a reader reads: ids that mean something only to whoever made them.

A decision id (D-12), a review finding id (L3-2) or a case number from the author's own list
means nothing to a reader, who must guess what it stands for. Rule 5.10 of write-text: name the
idea in words each time. This check reads the manuscript, or the files and folders given (a
draft, a note), and lists every token that has the shape of a key.

Not read: code (fenced blocks and code spans), citations, links, web addresses, HTML comments,
quotations in double quotes and blockquote lines, because a key there is code, a source's own
words or a link target.

The shapes it looks for:

  letters-dash-number  one or two capitals, a dash, an optional capital, a number:
                       D-12, R-3, P-A2, D-1.2 (the decision ids of decisions.md)
  letter-number-pair   a capital and a number, a dash, a number: L3-2 (review finding ids)

Settings in book.yaml:

  writing.internal_key_patterns  more shapes of the book's own keys, as Python regular
                                 expressions, e.g. ['\\bC\\d+\\b'] for numbered cases
  writing.internal_key_allow     tokens that are names in the field, not keys: [K-12, F-35]

Findings (exit codes and output shape: lib/check_contract.md):
  internal-key  defect  a token with the shape of an internal key in the text
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import script_tests
from book_config import BookConfig, ConfigError, add_config_arguments, config_from_args
from book_files import markdown_files
from check_output import DEFECT, CheckReport, add_output_arguments, run_main, tool_failed
from citations import hide_code

TOOL = "internal-key-check"
CLASSES = {"internal-key": DEFECT}

DEFAULT_KEY_SHAPES = (
    r"\b[A-Z]{1,2}-[A-Z]?\d+(?:\.\d+)*\b",
    r"\b[A-Z]\d+-\d+\b",
)
CITATION = re.compile(r"@\{[^}\n]*\}|@[\w:.#$%&+?<>~/-]+")
QUOTATION = re.compile(r'"[^"\n]*"')
BLOCKQUOTE_LINE = re.compile(r"^\s{0,3}>")


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="files or folders (default: the manuscript)")
    parser.add_argument("--self-test", action="store_true", help="run the tests on small books")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser.parse_args(argv)


def read_key_shapes(config: BookConfig) -> list[re.Pattern]:
    extra_shapes = config.get("writing.internal_key_patterns", None) or []
    try:
        return [re.compile(shape) for shape in (*DEFAULT_KEY_SHAPES, *extra_shapes)]
    except re.error as error:
        raise ConfigError(f"writing.internal_key_patterns holds a shape Python cannot read: "
                          f"{error}") from error


def hide_text_not_for_the_reader(text: str) -> list[str]:
    lines = hide_code(text).split("\n")
    return ["" if BLOCKQUOTE_LINE.match(line)
            else QUOTATION.sub(blank_out, CITATION.sub(blank_out, line)) for line in lines]


def blank_out(found: re.Match) -> str:
    return " " * len(found.group(0))


def find_keys(line: str, key_shapes: list[re.Pattern], allowed_tokens: set[str]) -> list[str]:
    found = {}
    for shape in key_shapes:
        for match in shape.finditer(line):
            if match.group(0) not in allowed_tokens:
                found.setdefault(match.start(), match.group(0))
    return [found[start] for start in sorted(found)]


def check_file(report: CheckReport, path: Path, key_shapes: list[re.Pattern],
               allowed_tokens: set[str]) -> None:
    text = Path(path).read_text(encoding="utf-8")
    for number, line in enumerate(hide_text_not_for_the_reader(text), start=1):
        for key in find_keys(line, key_shapes, allowed_tokens):
            report.add(f"{path}:{number}", "internal-key",
                       f"{key}: an internal key; name the idea it stands for in words (rule 5.10)")


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    if arguments.self_test:
        return script_tests.run_self_test(__file__, "test_internal_key_check.py")
    try:
        config = config_from_args(arguments, targets=arguments.paths)
        key_shapes = read_key_shapes(config)
        files = markdown_files(arguments.paths, config)
    except (ConfigError, FileNotFoundError) as error:
        return tool_failed(str(error), TOOL)
    allowed_tokens = set(config.get("writing.internal_key_allow", None) or [])
    report = CheckReport(TOOL, CLASSES)
    for path in files:
        check_file(report, path, key_shapes, allowed_tokens)
    return report.emit(arguments.format)


if __name__ == "__main__":
    run_main(main)
