#!/usr/bin/env python3
"""Check that every source the book cites can be found: in the sources list and in the library.

Reads every manuscript file and every thinking file (the `thinking` folder, or, in a book with
no thinking folder, the stance, audience, argument and doubts files), finds each `[Key]`, `[Key1, Key2]`
and `[Key, p. 12]` outside fenced code, and asks two questions of each key:

  1. Does the sources list (sources.list) have an entry for it? The list is the one place a
     key resolves, for the manuscript and for the thinking files alike.
  2. Is there a copy in the library (sources.library: a file `<Key>.<ext>`), or a line for it
     in needed.txt in the sources-to-add folder (sources.to_add), so someone knows to get it?

Findings (exit codes and output shape: lib/check_contract.md):
  not-in-list       defect         a key is cited, and the sources list has no entry for it
  no-library-copy   defect         a listed key has no library copy and no needed.txt line
  waits-in-needed   informational  no library copy yet; needed.txt asks for it

A book with no sources list says SKIPPED: it does not use citations.
"""

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))

import script_tests
from book_config import ConfigError, add_config_arguments, config_from_args
from check_output import DEFECT, INFORMATIONAL, CheckReport, add_output_arguments, tool_failed
from citation_key import entry_keys, is_placeholder
from manuscript_text import cited_keys, prose_lines
from source_files import thinking_paths
from sources_to_add import needed_keys

TOOL = "cited-source-check"
CLASSES = {
    "not-in-list": DEFECT,
    "no-library-copy": DEFECT,
    "waits-in-needed": INFORMATIONAL,
}
INDEX_RECORD_ENDINGS = (".json",)
PLACES_SHOWN = 3




def places_by_key(paths, root):
    places = {}
    for path in paths:
        shown = shown_name(path, root)
        lines = prose_lines(Path(path).read_text(encoding="utf-8", errors="replace"))
        for number, line in enumerate(lines, 1):
            for key in cited_keys(line):
                places.setdefault(key, []).append(f"{shown}:{number}")
    return places


def shown_name(path, root):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(path)


def library_keys(library):
    library = Path(library) if library else None
    if library is None or not library.is_dir():
        return set()
    return {path.name.split(".", 1)[0] for path in library.iterdir()
            if path.is_file() and not path.name.endswith(INDEX_RECORD_ENDINGS)}


def where(places):
    shown = ", ".join(places[:PLACES_SHOWN])
    more = len(places) - PLACES_SHOWN
    return f"{shown} and {more} more" if more > 0 else shown


def add_findings(report, places, listed, copied, needed):
    for key in sorted(places, key=str.lower):
        if is_placeholder(key):
            continue
        if key not in listed:
            report.add(key, "not-in-list", f"cited at {where(places[key])}")
        elif key in copied:
            continue
        elif key in needed:
            report.add(key, "waits-in-needed", "no library copy yet; needed.txt asks for it")
        else:
            report.add(key, "no-library-copy",
                       "no library copy and no needed.txt line; download it (collect-sources)")


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true", help="run the tests on test books")
    add_config_arguments(parser)
    add_output_arguments(parser)
    return parser.parse_args(argv)


def main(argv=None):
    arguments = parse_arguments(argv)
    if arguments.self_test:
        return script_tests.run_self_test(__file__, "test_cited_source_check.py")
    report = CheckReport(TOOL, CLASSES)
    try:
        config = config_from_args(arguments)
        if report.skip_unless_present(config.sources.list, "sources list"):
            return report.emit(arguments.format)
        listed = set(entry_keys(Path(config.sources.list).read_text(encoding="utf-8"),
                                skip_fenced=True))
        manuscript = [item.path for item in config.manuscript_files()]
        if not manuscript:
            report.skip(f"no manuscript files at {config.manuscript.dir}")
            return report.emit(arguments.format)
        places = places_by_key(manuscript + thinking_paths(config), config.root)
    except (ConfigError, OSError) as error:
        return tool_failed(str(error), TOOL)
    add_findings(report, places, listed, library_keys(config.sources.library),
                 set(needed_keys(config.sources.to_add)))
    return report.emit(arguments.format)


if __name__ == "__main__":
    sys.exit(main())
