#!/usr/bin/env python3
"""Check that citation-links.lua reads citation keys the same way lib/citation_key.py does.

The Lua filter cannot import the Python rule, so it keeps its own copy of the key shape.
This check reads the shape out of the filter and runs it and lib's KEY_SHAPE over the
same sample keys. Any key the two judge differently is a defect: the filter would leave
a valid key unlinked, or link text that is not a key.
"""

import argparse
import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

from book_config import add_config_arguments
from check_output import DEFECT, CheckReport, add_output_arguments, tool_failed
from citation_key import KEY_SHAPE, derive

TOOL = "key-pattern-check"
CLASSES = {"key-shape-differs": DEFECT}
FILTER_FILE = Path(__file__).resolve().parents[1] / "assets" / "filters" / "citation-links.lua"
LUA_CONSTANTS = ("STEM_MAX_LETTERS", "STEM_PATTERN", "PLUS_SIGN", "YEAR_PATTERN",
                 "NO_YEAR_PATTERN", "LETTER_PATTERN")
LUA_CLASS_TO_REGEX = {"%d": r"\d", "%-": "-", "%a": "[A-Za-z]", "%l": "[a-z]", "%+": r"\+"}
SAMPLE_SURNAMES = [["Smith"], ["van Berg"], ["Owen-Price"], ["Adams", "Baker"],
                   ["Adams", "Baker", "Clark", "Davis", "Evans"], ["Rocha da Lima"], ["O"]]
EDGE_KEYS = ["Wal--", "Smi72a", "ABC+20", "vB99", "A" * 24 + "99", "A" * 25 + "99", "O'B99",
             "Smi1999", "smi99", "Smi99A", "+AB99", "AB+99b", "Ab-99", "Smi9"]


def lua_constants(text):
    found = {}
    for name in LUA_CONSTANTS:
        match = re.search(rf"^local {name} = (.+)$", text, re.M)
        if not match:
            raise ValueError(f"{FILTER_FILE.name} no longer declares {name}")
        found[name] = match.group(1).strip().strip("'\"")
    return found


def lua_pattern_to_regex(pattern):
    body = pattern.removeprefix("^")
    for lua_class, regex_class in LUA_CLASS_TO_REGEX.items():
        body = body.replace(lua_class, regex_class)
    return body


def filter_key_shape(constants):
    stem = lua_pattern_to_regex(constants["STEM_PATTERN"]).removesuffix("+")
    year = lua_pattern_to_regex(constants["YEAR_PATTERN"])
    no_year = lua_pattern_to_regex(constants["NO_YEAR_PATTERN"])
    letter = lua_pattern_to_regex(constants["LETTER_PATTERN"])
    plus = re.escape(constants["PLUS_SIGN"])
    return re.compile(rf"^{stem}{{1,{constants['STEM_MAX_LETTERS']}}}{plus}?(?:{year}|{no_year}){letter}?$")


def sample_keys():
    derived = [derive(surnames, year) for surnames in SAMPLE_SURNAMES for year in (1999, "--")]
    return derived + EDGE_KEYS


def run_check(report):
    shape = filter_key_shape(lua_constants(FILTER_FILE.read_text(encoding="utf-8")))
    for key in sample_keys():
        lib_accepts = bool(KEY_SHAPE.match(key))
        filter_accepts = bool(shape.match(key))
        if lib_accepts != filter_accepts:
            report.add(key, "key-shape-differs",
                       f"lib citation_key {'accepts' if lib_accepts else 'rejects'} it, "
                       f"citation-links.lua {'accepts' if filter_accepts else 'rejects'} it")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_config_arguments(parser)
    add_output_arguments(parser)
    parser.add_argument("--self-test", action="store_true", help="the same run; it reads no book data")
    args = parser.parse_args()
    report = CheckReport(TOOL, CLASSES)
    try:
        run_check(report)
    except (OSError, ValueError) as problem:
        return tool_failed(str(problem), TOOL)
    return report.emit(args.format)


if __name__ == "__main__":
    sys.exit(main())
