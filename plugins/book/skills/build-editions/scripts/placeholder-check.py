#!/usr/bin/env python3
"""List every place in the manuscript that still holds a placeholder, before a build.

A placeholder marks text that is not done yet: the book's placeholder text
(`book.placeholder_text`, default TO BE ASSIGNED, for an ISBN or a date still to come) and any
other text the book uses for the same purpose (`book.other_placeholders`, such as a TODO:
the author left in the text for later). The build never stops for a
placeholder and lists them after it finishes; this check lists them before, so a release
waits until every one is replaced.

Each text is matched as written, anywhere in a line, also in code and comments, the same way
the build looks for it.

Findings (exit codes and output shape: lib/check_contract.md):
  placeholder  defect  a line still holds a placeholder
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import BookConfig, ConfigError, add_config_arguments, config_from_args
from check_output import DEFECT, CheckReport, add_output_arguments, run_main, tool_failed

TOOL = "placeholder-check"
CLASSES = {"placeholder": DEFECT}
BUILT_IN_PLACEHOLDER = "TO BE ASSIGNED"


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser.parse_args(argv)


def read_placeholders(config: BookConfig) -> list[str]:
    placeholder = config.get("book.placeholder_text", None) or BUILT_IN_PLACEHOLDER
    others = config.get("book.other_placeholders", None) or []
    return [str(text) for text in (placeholder, *others) if str(text).strip()]


def find_placeholders(text: str, placeholders: list[str]) -> list[tuple[int, str]]:
    return [(number, placeholder)
            for number, line in enumerate(text.splitlines(), start=1)
            for placeholder in placeholders if placeholder in line]


def check_file(report: CheckReport, path: Path, root: Path, placeholders: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for number, placeholder in find_placeholders(text, placeholders):
        report.add(f"{path.relative_to(root)}:{number}", "placeholder",
                   f"still holds {placeholder!r}; replace it before a release build")


def self_test() -> int:
    text = "# Copyright\n\nISBN: TO BE ASSIGNED\n\nThe beds kept 40 TODO:rain mm of rain.\n"
    checks = [
        ("each placeholder is found on its line",
         find_placeholders(text, ["TO BE ASSIGNED", "TODO:"]),
         [(3, "TO BE ASSIGNED"), (5, "TODO:")]),
        ("a text with no placeholder gives nothing",
         find_placeholders("Plain text.\n", ["TO BE ASSIGNED"]), []),
    ]
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"{TOOL} self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    if arguments.self_test:
        return self_test()
    try:
        config = config_from_args(arguments)
        files = config.manuscript_files()
    except ConfigError as error:
        return tool_failed(str(error), TOOL)
    report = CheckReport(TOOL, CLASSES)
    if not files:
        report.skip(f"no manuscript files at {config.manuscript.dir}")
        return report.emit(arguments.format)
    placeholders = read_placeholders(config)
    for item in files:
        check_file(report, item.path, config.root, placeholders)
    return report.emit(arguments.format)


if __name__ == "__main__":
    run_main(main)
