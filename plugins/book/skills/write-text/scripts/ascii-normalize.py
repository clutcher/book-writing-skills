#!/usr/bin/env python3
"""Find non-ASCII characters in markdown files and replace them with ASCII (rule 9.1).

With no path, every manuscript file of the book is checked. The default is a dry run that
reports what would change; --fix writes the files. Characters with no mapping are listed with
file, line and hex code; add a mapping to REPLACEMENTS when one turns up.

Mapped: box-drawing characters, arrows, curly quotes and guillemets, dashes, the ellipsis,
bullets, maths symbols, fractions, super- and subscripts, Greek letters, currency and legal
signs, check marks and the no-break space.

Exit codes: 0 all ASCII, 1 a file needs changes or holds unmapped characters, 2 the check
could not run.
"""

import argparse
import contextlib
import io
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from book_files import (ConfigError, SAMPLE_BOOK, add_config_arguments, config_for_targets,
                        is_english_book, markdown_files, skipped_for_language, tool_failed)
from terminal_colors import GREEN, NC, RED, YELLOW

BOX_DRAWING = {
    "\u250c": "+", "\u2510": "+", "\u2514": "+", "\u2518": "+", "\u251c": "+", "\u2524": "+",
    "\u252c": "+", "\u2534": "+", "\u253c": "+", "\u2500": "-", "\u2501": "-", "\u2502": "|",
    "\u2503": "|", "\u2554": "+", "\u2557": "+", "\u255a": "+", "\u255d": "+", "\u2560": "+",
    "\u2563": "+", "\u2566": "+", "\u2569": "+", "\u256c": "+", "\u2550": "=", "\u2551": "|",
}
ARROWS = {
    "\u2192": "->", "\u2190": "<-", "\u2191": "^", "\u2193": "v", "\u21d2": "=>", "\u21d0": "<=",
    "\u21d4": "<=>", "\u25b6": ">", "\u25c0": "<",
}
QUOTES = {
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'", "\u00ab": '"', "\u00bb": '"',
}
DASHES = {"\u2014": "--", "\u2013": "-", "\u2212": "-"}
OTHER_SYMBOLS = {
    "\u2026": "...", "\u2022": "*", "\u25e6": "-", "\u25aa": "*", "\u25b8": ">",
    "\u00d7": "x", "\u00f7": "/", "\u00b1": "+/-", "\u2260": "!=", "\u2264": "<=", "\u2265": ">=",
    "\u2248": "~=", "\u221e": "inf", "\u221a": "sqrt", "\u2211": "sum", "\u220f": "prod",
    "\u2208": "in", "\u2209": "not in", "\u2282": "subset", "\u2227": "and", "\u2228": "or",
    "\u00ac": "not", "\u00bd": "1/2", "\u2153": "1/3", "\u00bc": "1/4", "\u00be": "3/4",
    "\u00b2": "^2", "\u00b3": "^3", "\u00b9": "^1", "\u2070": "^0", "\u2074": "^4", "\u2075": "^5",
    "\u2080": "0", "\u2081": "1", "\u2082": "2", "\u2083": "3", "\u2084": "4",
    "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma", "\u03b4": "delta", "\u03bb": "lambda",
    "\u03bc": "mu", "\u03c0": "pi", "\u03c3": "sigma", "\u0394": "Delta", "\u03a3": "Sigma",
    "\u03a9": "Omega", "\u20ac": "EUR", "\u00a3": "GBP", "\u00a5": "JPY", "\u20bd": "RUB",
    "\u00a9": "(c)", "\u00ae": "(R)", "\u2122": "(TM)", "\u00b0": "deg",
    "\u2713": "[x]", "\u2717": "[ ]", "\u2714": "[x]", "\u2718": "[ ]", "\u2610": "[ ]",
    "\u2611": "[x]", "\u2612": "[x]", "\u00a0": " ",
}
GROUPS = (
    ("Box-drawing", BOX_DRAWING, "ASCII (+, -, |, =)"),
    ("Arrows", ARROWS, "ASCII (->, <-, ^, v)"),
    ("Curly quotes", QUOTES, "straight quotes"),
    ("Special dashes", DASHES, "hyphens"),
    ("Other symbols", OTHER_SYMBOLS, "ASCII words and signs"),
)
REPLACEMENTS = {char: text for _, table, _ in GROUPS for char, text in table.items()}


def normalise(text):
    return "".join(REPLACEMENTS.get(char, char) for char in text)


def unmapped_characters(text):
    found = []
    for number, line in enumerate(normalise(text).splitlines(), start=1):
        for char in line:
            if ord(char) > 127:
                found.append((number, char))
    return found


def check_file(path, fix):
    text = path.read_text(encoding="utf-8")
    non_ascii = sum(1 for char in text if ord(char) > 127)
    print(f"Processing: {GREEN}{path}{NC}")
    if not non_ascii:
        print(f"  {GREEN}No non-ASCII characters found{NC}")
        return True
    print(f"  Found {YELLOW}{non_ascii}{NC} non-ASCII characters")
    print("  Replacements:")
    for name, table, target in GROUPS:
        if any(char in text for char in table):
            print(f"    {YELLOW}{name}{NC} -> {target}")
    unmapped = unmapped_characters(text)
    if unmapped:
        print(f"  {RED}Unmapped characters found:{NC}")
        for number, char in unmapped:
            print(f"    line {number}: '{RED}{char}{NC}' (hex: {char.encode('utf-8').hex()})")
    normalised = normalise(text)
    if normalised == text:
        return not unmapped
    changed_lines = sum(1 for old, new in zip(text.splitlines(), normalised.splitlines())
                        if old != new)
    if fix:
        path.write_text(normalised, encoding="utf-8")
        print(f"  {GREEN}File updated{NC} ({changed_lines} lines)")
        return not unmapped
    print(f"  {YELLOW}Would modify{NC} {changed_lines} lines (dry run; --fix writes)")
    return False


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("paths", nargs="*", help="files or folders (default: the manuscript)")
    parser.add_argument("--fix", action="store_true", help="write the replacements")
    parser.add_argument("--check", action="store_true",
                        help="dry run; the default, kept for older command lines")
    parser.add_argument("--self-test", action="store_true",
                        help="check this script against the fixture book and exit")
    add_config_arguments(parser)
    return parser.parse_args(argv)


def run(argv):
    options = parse_arguments(argv)
    if options.self_test:
        return self_test()
    try:
        config = config_for_targets(options, options.paths)
        files = markdown_files(options.paths, config)
    except (ConfigError, FileNotFoundError) as error:
        return tool_failed(str(error), "ascii-normalize")
    if not is_english_book(config):
        return skipped_for_language(config, "ascii-normalize")
    fix = options.fix and not options.check
    needing_work = [path for path in files if not check_file(Path(path), fix)]
    print("=" * 40)
    file_word = "file" if len(files) == 1 else "files"
    print(f"Processed: {GREEN}{len(files)}{NC} {file_word}")
    if needing_work:
        print(f"Files with issues: {YELLOW}{len(needing_work)}{NC}")
    return 1 if needing_work else 0


def self_test():
    failures = []
    sample = "a \u201cquote\u201d \u2014 an arrow \u2192 and \u2603"
    if normalise(sample) != 'a "quote" -- an arrow -> and \u2603':
        failures.append(f"normalise gave {normalise(sample)!r}")
    if unmapped_characters(sample) != [(1, "\u2603")]:
        failures.append("the snowman was not reported as unmapped")
    if any(ord(char) > 127 for char in Path(__file__).read_text(encoding="utf-8")):
        failures.append("this script itself must stay ASCII, so it cannot normalise its table")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exit_code = run([str(SAMPLE_BOOK / "manuscript")])
    text = output.getvalue()
    if exit_code != 1:
        failures.append(f"folder run: exit {exit_code}, expected 1 (a curly quote is planted)")
    if text.count("Processing:") != 5:
        failures.append("folder run did not process every file of the fixture manuscript")
    if "Curly quotes" not in text or "Would modify" not in text:
        failures.append("folder run did not report the planted curly quotes")
    for line in failures:
        print(f"FAIL  {line}")
    print(f"self-test: {'PASS' if not failures else str(len(failures)) + ' failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
