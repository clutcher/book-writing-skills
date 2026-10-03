#!/usr/bin/env python3
"""List characters in the manuscript's code that the bundled EPUB code font does not have.

The EPUB ships a subset of JetBrains Mono. A character outside the subset is drawn from the
reading device's own monospace font instead, glyph by glyph, which breaks the column
alignment of code and ASCII diagrams. Each such character is reported once per line, as
advisory: the fix is either to cut a wider subset (references/editions.md) or to change the
character in the manuscript, and only a person can choose.
"""

import argparse
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import ConfigError, add_config_arguments, config_from_args, manuscript_files
from check_output import ADVISORY, CheckReport, add_output_arguments, tool_failed

TOOL = "code-font-check"
CLASSES = {"missing-code-glyph": ADVISORY}
SUBSET_RANGES = [(0x20, 0x7E), (0xA0, 0xA0), (0x2013, 0x2014), (0x2018, 0x201D), (0x2026, 0x2026)]
FENCE = re.compile(r"^\s*(```+|~~~+)")
INLINE_CODE = re.compile(r"(`+)(.+?)\1")
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def in_subset(character):
    codepoint = ord(character)
    return any(low <= codepoint <= high for low, high in SUBSET_RANGES)


def code_lines(text):
    open_fence = None
    for number, line in enumerate(text.splitlines(), 1):
        fence = FENCE.match(line)
        if open_fence:
            if fence and fence.group(1)[0] == open_fence[0] and len(fence.group(1)) >= len(open_fence):
                open_fence = None
            else:
                yield number, line
        elif fence and "{=" not in line:
            open_fence = fence.group(1)
        else:
            for match in INLINE_CODE.finditer(line):
                yield number, match.group(2)


def missing_characters(text):
    for number, code in code_lines(text):
        missing = sorted({character for character in code if not in_subset(character) and character != "\t"})
        if missing:
            yield number, missing


def check_file(path, root, report):
    text = Path(path).read_text(encoding="utf-8")
    for number, missing in missing_characters(text):
        names = ", ".join(f"{character} U+{ord(character):04X}" for character in missing)
        report.add(f"{Path(path).relative_to(root)}:{number}", "missing-code-glyph",
                   f"not in the EPUB code font: {names}")


def self_test():
    sample = "Text with `a -> b` and `a → b`.\n\n```\n┌─┐ ok\nplain\n```\n\n```{=latex}\n\\vfill é\n```\n"
    found = list(missing_characters(sample))
    checks = [
        ("inline code outside the subset is found", found[0], (1, ["→"])),
        ("box-drawing in a code block is found", found[1], (4, ["─", "┌", "┐"])),
        ("raw LaTeX blocks are not code", len(found), 2),
        ("typographic quotes are in the subset", in_subset("“"), True),
    ]
    failures = [(name, got, expected) for name, got, expected in checks if got != expected]
    for name, got, expected in failures:
        print(f"FAIL  {name}: got {got!r}, expected {expected!r}")
    print(f"code-font-check self-test: {len(checks) - len(failures)}/{len(checks)} passed")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--self-test", action="store_true", help="run the built-in tests")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        config = config_from_args(args)
        files = manuscript_files(config)
    except ConfigError as problem:
        return tool_failed(str(problem), TOOL)
    report = CheckReport(TOOL, CLASSES)
    if not files:
        report.skip(f"no manuscript files at {config.manuscript.dir}")
        return report.emit(args.format)
    for item in files:
        check_file(item.path, config.root, report)
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
